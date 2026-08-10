"""Deterministic graders.

These encode the parts of the policy that need NO semantic judgment: presence
of an opt-out, banned phrases, length, sender identification. They are fast,
free, and perfectly repeatable — the first line of the eval harness.
"""
from __future__ import annotations

import re

from .models import Finding, Message, Severity


def _check_rule(rule: dict, message: Message) -> Finding:
    rid = rule["id"]
    desc = rule["description"]
    sev = Severity.parse(rule["severity"])
    rtype = rule["type"]
    body = message.body
    text = f"{message.subject}\n{message.body}"

    if rtype == "must_match_any":
        patterns = rule["patterns"]
        ok = any(re.search(p, text, re.IGNORECASE) for p in patterns)
        detail = "" if ok else f"none of {patterns} present"
        return Finding(rid, desc, sev, ok, detail)

    if rtype == "must_not_contain_any":
        patterns = rule["patterns"]
        hits = [p for p in patterns if re.search(re.escape(p), text, re.IGNORECASE)]
        ok = not hits
        detail = "" if ok else f"banned phrase(s) found: {hits}"
        return Finding(rid, desc, sev, ok, detail)

    if rtype == "max_length":
        limit = int(rule["limit"])
        ok = len(body) <= limit
        detail = "" if ok else f"body length {len(body)} > limit {limit}"
        return Finding(rid, desc, sev, ok, detail)

    if rtype == "must_contain_context":
        fields = rule["fields"]
        missing = []
        for fld in fields:
            val = (getattr(message, fld, "") or "").strip()
            if not val or val.lower() not in text.lower():
                missing.append(fld)
        ok = not missing
        detail = "" if ok else f"missing / not referenced: {missing}"
        return Finding(rid, desc, sev, ok, detail)

    # Unknown rule type: do not silently pass a real check — flag it.
    return Finding(rid, desc, sev, False, f"unknown deterministic rule type: {rtype!r}")


def run_deterministic(policy: dict, message: Message) -> list:
    return [_check_rule(r, message) for r in policy.get("deterministic_rules", [])]
