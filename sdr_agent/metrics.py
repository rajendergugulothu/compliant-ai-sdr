"""Outcome metrics (the PM layer). Reads runs/runs.jsonl and reports.

Computable offline: approval rate, escalation rate, auto-fix rate (approved but
needed >1 attempt), average attempts, block reasons. Reply/meeting metrics are
marked NA because they require real sending (Step 5 live mode).

Usage: python -m sdr_agent.metrics
"""
from __future__ import annotations

import json
import os
from collections import Counter

RUN_LOG = "runs/runs.jsonl"


def load_runs(path: str = RUN_LOG) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def report(path: str = RUN_LOG) -> None:
    runs = load_runs(path)
    if not runs:
        print("No runs found. Run: python -m sdr_agent.pipeline")
        return

    total = len(runs)
    approved = [r for r in runs if r["status"] == "APPROVED"]
    escalated = [r for r in runs if r["status"] == "ESCALATED"]
    auto_fixed = [r for r in approved if r["attempts"] > 1]
    avg_attempts = sum(r["attempts"] for r in runs) / total

    block_reasons = Counter()
    for r in runs:
        for h in r.get("history", []):
            for rule in h.get("failures", []):
                block_reasons[rule] += 1

    def pct(n):
        return f"{100 * n / total:.0f}%"

    print("=" * 60)
    print("COMPLIANT AI SDR — OUTCOME METRICS")
    print("=" * 60)
    print(f"Leads processed .............. {total}")
    print(f"Approved & sent .............. {len(approved)}  ({pct(len(approved))})")
    print(f"Escalated to human ........... {len(escalated)}  ({pct(len(escalated))})")
    print(f"Auto-fixed by guardrail ...... {len(auto_fixed)}  (approved after a revision)")
    print(f"Avg drafts per lead .......... {avg_attempts:.2f}")
    print("-" * 60)
    print("Compliance issues caught (by rule, across all attempts):")
    for rule, n in block_reasons.most_common():
        print(f"   {rule:<28} {n}")
    print("-" * 60)
    print("Safety: fabrications / injections that reached SENT .. "
          "(needs real LLM judge to score; see red-team report)")
    print("GTM outcome: reply rate / meetings booked ............ NA (needs live send)")
    print("=" * 60)


if __name__ == "__main__":
    report()
