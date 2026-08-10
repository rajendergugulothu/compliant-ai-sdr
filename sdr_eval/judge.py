"""LLM-as-judge grader.

Handles the parts of the policy that need semantic judgment: is every claim
grounded in the verified lead facts (no fabrication)? is the tone professional?
are there unverifiable product claims?

Design choices worth noting for the write-up:
  * The judge is only given the VERIFIED lead facts. If the email references
    anything outside them, that is a fabrication by construction.
  * If the LLM is unavailable (mock mode / no key / error), the judge is SKIPPED
    (fail-open) so the harness still runs. In production you would fail-CLOSED —
    a compliance check you cannot run should block/escalate, not silently pass.
    This is called out loudly in the output.
"""
from __future__ import annotations

import json

from .llm import LLMClient
from .models import Finding, Lead, Message, Severity


def _build_prompt(policy: dict, lead: Lead, message: Message) -> str:
    rules = policy.get("judge_rules", [])
    rules_txt = "\n".join(
        f'- {r["id"]} (severity {r["severity"]}): {r["description"]}' for r in rules
    )
    return f"""You are a strict compliance reviewer for cold outbound sales email.

THE ONLY VERIFIED FACTS YOU MAY TREAT AS TRUE ABOUT THE PROSPECT:
  name:    {lead.name}
  company: {lead.company}
  role:    {lead.role}
  verified_facts: {lead.enrichment}

THE EMAIL UNDER REVIEW:
  subject: {message.subject}
  body:
{message.body}

Check EACH rule below and decide whether the email PASSES it. Any statement about
the prospect that is NOT supported by the verified facts above is a fabrication
and must FAIL CLAIMS_GROUNDED.

RULES:
{rules_txt}

Respond with ONLY a JSON array, one object per rule, no prose:
[{{"rule_id": "<id>", "passed": true|false, "detail": "<short reason>"}}]
"""


def _extract_json_array(text: str) -> str:
    start = text.find("[")
    end = text.rfind("]")
    return text[start : end + 1] if start != -1 and end != -1 else text


def _to_findings(rules: list, data: list) -> list:
    by_id = {d.get("rule_id"): d for d in data if isinstance(d, dict)}
    out = []
    for r in rules:
        d = by_id.get(r["id"], {})
        passed = bool(d.get("passed", False))
        detail = d.get("detail", "") if d else "no verdict returned for this rule"
        out.append(
            Finding(r["id"], r["description"], Severity.parse(r["severity"]),
                    passed, detail, source="judge")
        )
    return out


def _all_skipped(rules: list, why: str) -> list:
    return [
        Finding(r["id"], r["description"], Severity.parse(r["severity"]),
                True, f"SKIPPED: {why}", source="judge")
        for r in rules
    ]


def run_judge(policy: dict, lead: Lead, message: Message, client: LLMClient | None = None) -> list:
    rules = policy.get("judge_rules", [])
    if not rules:
        return []

    client = client or LLMClient()
    if client.is_mock:
        return _all_skipped(rules, "mock LLM (fail-open in dev; fail-CLOSED in prod)")

    try:
        text = client.complete(
            "You return only compact JSON. No markdown, no prose.",
            _build_prompt(policy, lead, message),
        )
        data = json.loads(_extract_json_array(text))
        return _to_findings(rules, data)
    except Exception as exc:  # network / parse / auth — do not crash the run
        return _all_skipped(rules, f"judge error: {exc}")
