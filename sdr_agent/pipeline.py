"""End-to-end pipeline: for each lead, enrich -> draft-through-guardrail ->
send (dry-run) or escalate -> log. Writes a run log to runs/runs.jsonl.

Usage:
    python -m sdr_agent.pipeline                    # mock LLM if no key
    SDR_LLM=mock python -m sdr_agent.pipeline        # force mock
    ANTHROPIC_API_KEY=... python -m sdr_agent.pipeline
"""
from __future__ import annotations

import json
import os

from sdr_eval.llm import LLMClient
from sdr_eval.models import Lead
from sdr_eval.policy import load_policy

from .adapters import CRMLogger, EmailSender, EnrichmentProvider
from .guardrail import guardrail_send

RUN_LOG = "runs/runs.jsonl"


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(leads_path="data/leads.json", product_path="config/product.json",
        policy_path="policies/outbound-policy.json") -> list:
    policy = load_policy(policy_path)
    product = _load_json(product_path)
    leads = [Lead.from_dict(d) for d in _load_json(leads_path)]

    client = LLMClient()
    enricher = EnrichmentProvider()
    sender = EmailSender(live=False)
    crm = CRMLogger()

    os.makedirs("runs", exist_ok=True)
    open(RUN_LOG, "w").close()  # fresh log each run

    print(f"LLM backend: {client.name}\n" + "=" * 72)
    records = []
    for lead in leads:
        lead = enricher.enrich(lead)
        decision = guardrail_send(policy, lead, product, client=client)

        if decision.status == "APPROVED":
            send_result = sender.send(lead, decision.message)
            action = "SENT (dry-run)" if not send_result["sent"] else "SENT"
        else:
            send_result = {"sent": False, "mode": "escalated"}
            action = "ESCALATED -> human queue"

        record = {
            "lead": lead.name,
            "company": lead.company,
            "status": decision.status,
            "attempts": decision.attempts,
            "reason": decision.reason,
            "verdict": decision.report.verdict(),
            "failures_final": [f.rule_id for f in decision.report.failures()],
            "history": decision.history,
            "subject": decision.message.subject,
            "action": action,
            "send": send_result,
        }
        records.append(record)
        crm.log(record)
        with open(RUN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        print(f"{lead.name:<14} {lead.company:<22} {decision.status:<10} "
              f"attempts={decision.attempts}  {action}")
        if decision.status == "ESCALATED":
            print(f"   reason: {decision.reason}; final failures: {record['failures_final']}")

    print("=" * 72)
    print(f"Wrote {len(records)} records to {RUN_LOG}")
    return records


if __name__ == "__main__":
    run()
