"""Fill the docs with real evaluation numbers — no copy-paste.

After `make suite` with a real key writes eval_suite/results.json, run
`python -m eval_suite.publish` (or `make publish`) to replace the block between
<!-- EVAL:START --> and <!-- EVAL:END --> in README.md and docs/case-study.md.

Refuses to publish mock results (backend must be a real model).
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "eval_suite", "results.json")
TARGETS = [os.path.join(ROOT, "README.md"), os.path.join(ROOT, "docs", "case-study.md")]
PATTERN = re.compile(r"(<!-- EVAL:START -->)(.*?)(<!-- EVAL:END -->)", re.DOTALL)


def _block(r: dict) -> str:
    def pct(x):
        return f"{x*100:.1f}%" if x is not None else "n/a"
    cost = r.get("cost_per_message_usd")
    cost_s = f"${cost:.5f}" if cost else "n/a"
    return (
        "\n"
        f"Measured with **{r.get('model','?')}** over {r.get('n','?')} cases "
        f"({r.get('attacks','?')} adversarial, {r.get('benign','?')} benign):\n\n"
        "| Metric | Deterministic + LLM judge |\n"
        "|---|---|\n"
        f"| Violation catch rate | {pct(r.get('violation_catch_rate'))} |\n"
        f"| Attack success rate | {pct(r.get('attack_success_rate'))} |\n"
        f"| False-positive rate | {pct(r.get('false_positive_rate'))} |\n"
        f"| Escalation rate | {pct(r.get('escalation_rate'))} |\n"
        f"| Latency / message | {r.get('avg_latency_ms',0):.0f} ms |\n"
        f"| Cost / message | {cost_s} |\n\n"
        "_Generated from `eval_suite/results.json` by `make publish`._\n"
    )


def main() -> int:
    if not os.path.exists(RESULTS):
        print("No results.json — run `make suite` first (with ANTHROPIC_API_KEY).")
        return 1
    r = json.load(open(RESULTS, encoding="utf-8"))
    if r.get("backend") == "mock":
        print("Refusing to publish MOCK results. Run `make suite` with ANTHROPIC_API_KEY set.")
        return 1
    block = _block(r)
    for path in TARGETS:
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        if not PATTERN.search(text):
            print(f"skip {os.path.basename(path)} (no EVAL markers)")
            continue
        new = PATTERN.sub(lambda m: m.group(1) + block + m.group(3), text)
        open(path, "w", encoding="utf-8").write(new)
        print(f"updated {os.path.basename(path)}")
    print("Done. Review the diff and commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
