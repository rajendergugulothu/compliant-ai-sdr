"""Score the evaluation dataset against the compliance harness and report metrics.

Metrics:
  * Violation catch rate  — of adversarial cases, how many were BLOCK/ESCALATE.
  * Attack success rate    — of adversarial cases, how many slipped through as PASS.
  * False-positive rate     — of benign cases, how many were wrongly BLOCK/ESCALATE.
  * Escalation rate         — share routed to a human.
  * Avg latency / message   — evaluator wall-clock (meaningful with the real judge).
  * Cost / message          — LLM judge spend (meaningful with the real judge).
  * Per-category catch rate.

Run:
    python -m eval_suite.generate      # (re)build cases.json
    python -m eval_suite.run           # mock baseline (deterministic-only)
    ANTHROPIC_API_KEY=... python -m eval_suite.run     # full, with LLM judge
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict

from sdr_eval.evaluate import evaluate
from sdr_eval.llm import LLMClient
from sdr_eval.models import Lead, Message
from sdr_eval.policy import load_policy

CASES = os.path.join(os.path.dirname(__file__), "cases.json")
RESULTS = os.path.join(os.path.dirname(__file__), "results.json")


def _verdict_class(v: str) -> str:
    if v in ("PASS", "PASS_WITH_WARNINGS"):
        return "pass"
    if v == "ESCALATE":
        return "escalate"
    return "block"


def run() -> dict:
    if not os.path.exists(CASES):
        print("No cases.json — run: python -m eval_suite.generate")
        return {}
    policy = load_policy("policies/outbound-policy.json")
    cases = json.load(open(CASES, encoding="utf-8"))
    client = LLMClient()

    n = len(cases)
    attacks = [c for c in cases if c["kind"] == "attack"]
    benign = [c for c in cases if c["kind"] == "benign"]
    caught = 0
    leaked = 0
    false_pos = 0
    escalations = 0
    latencies = []
    cost_total = 0.0
    per_cat = defaultdict(lambda: {"total": 0, "caught": 0})

    for c in cases:
        lead = Lead.from_dict(c["lead"])
        msg = Message.from_dict(c["message"])
        t0 = time.perf_counter()
        report = evaluate(policy, lead, msg, client=client)
        latencies.append(time.perf_counter() - t0)
        if client.last_cost:
            cost_total += client.last_cost
        cls = _verdict_class(report.verdict())
        if cls == "escalate":
            escalations += 1

        if c["kind"] == "attack":
            per_cat[c["category"]]["total"] += 1
            if cls in ("block", "escalate"):
                caught += 1
                per_cat[c["category"]]["caught"] += 1
            else:
                leaked += 1
        else:  # benign
            if cls in ("block", "escalate"):
                false_pos += 1

    catch_rate = caught / len(attacks) if attacks else 0
    attack_success = leaked / len(attacks) if attacks else 0
    fpr = false_pos / len(benign) if benign else 0
    avg_latency = sum(latencies) / n if n else 0
    cost_per_msg = cost_total / n if n else 0

    print("=" * 64)
    print(f"EVALUATION SUITE  |  backend={client.name}  model={client.model}")
    print("=" * 64)
    print(f"Cases ........................ {n}  ({len(attacks)} adversarial, {len(benign)} benign)")
    print(f"Violation catch rate ......... {catch_rate*100:5.1f}%   ({caught}/{len(attacks)})")
    print(f"Attack success rate .......... {attack_success*100:5.1f}%   ({leaked}/{len(attacks)})")
    print(f"False-positive rate .......... {fpr*100:5.1f}%   ({false_pos}/{len(benign)})")
    print(f"Escalation rate .............. {escalations/n*100:5.1f}%   ({escalations}/{n})")
    print(f"Avg latency / message ........ {avg_latency*1000:6.1f} ms")
    if client.is_mock:
        print(f"Cost / message ............... n/a (mock — run with ANTHROPIC_API_KEY)")
    else:
        print(f"Cost / message ............... ${cost_per_msg:.5f}   (total ${cost_total:.4f})")
    print("-" * 64)
    print("Catch rate by category:")
    for cat, d in sorted(per_cat.items()):
        rate = d["caught"] / d["total"] * 100 if d["total"] else 0
        print(f"   {cat:<28} {rate:5.1f}%  ({d['caught']}/{d['total']})")
    if client.is_mock:
        print("-" * 64)
        print("NOTE: mock = DETERMINISTIC-ONLY baseline (LLM judge unavailable).")
        print("Judge-dependent categories (fabrication, injection, endorsement,")
        print("unsupported claims, exfiltration, irrelevant) are PENDING until you")
        print("run with a real key. That gap is the point of the hybrid design.")
    print("=" * 64)

    results = {
        "backend": client.name, "model": client.model, "n": n,
        "attacks": len(attacks), "benign": len(benign),
        "violation_catch_rate": catch_rate, "attack_success_rate": attack_success,
        "false_positive_rate": fpr, "escalation_rate": escalations / n if n else 0,
        "avg_latency_ms": avg_latency * 1000,
        "cost_per_message_usd": None if client.is_mock else cost_per_msg,
        "per_category": {k: v for k, v in per_cat.items()},
    }
    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {RESULTS}")
    return results


if __name__ == "__main__":
    run()
