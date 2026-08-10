"""CLI runner: evaluate example message cases against the policy.

Usage:
    python -m sdr_eval.run                      # runs every examples/*.json
    python -m sdr_eval.run examples/msg-01-clean.json
    POLICY=policies/outbound-policy.json python -m sdr_eval.run
"""
from __future__ import annotations

import glob
import json
import os
import sys

from .evaluate import evaluate
from .models import Lead, Message
from .policy import load_policy

_VERDICT_ICON = {
    "PASS": "PASS   ",
    "PASS_WITH_WARNINGS": "WARN   ",
    "BLOCK": "BLOCK  ",
    "ESCALATE": "ESCALATE",
}


def load_case(path: str):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    name = d.get("name", os.path.basename(path))
    return name, Lead.from_dict(d.get("lead", {})), Message.from_dict(d.get("message", {}))


def print_report(name: str, report) -> None:
    verdict = report.verdict()
    print("=" * 72)
    print(f"CASE: {name}")
    print(f"VERDICT: {_VERDICT_ICON.get(verdict, verdict)}   (worst severity: {report.max_severity().name})")
    print("-" * 72)
    for f in report.findings:
        status = "ok  " if f.passed else "FAIL"
        detail = f"  <- {f.detail}" if f.detail else ""
        print(f"  [{status}] {f.severity.name} {f.rule_id:<28} ({f.source}){detail}")
    print()


def main(argv) -> int:
    policy_path = os.environ.get("POLICY", "policies/outbound-policy.json")
    policy = load_policy(policy_path)
    paths = argv or sorted(glob.glob("examples/msg-*.json"))
    if not paths:
        print("No example cases found. Pass a path or add examples/msg-*.json.")
        return 1
    counts = {}
    for p in paths:
        name, lead, message = load_case(p)
        report = evaluate(policy, lead, message)
        print_report(name, report)
        counts[report.verdict()] = counts.get(report.verdict(), 0) + 1
    print("=" * 72)
    print("SUMMARY:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
