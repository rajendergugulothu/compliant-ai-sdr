# Case study — Compliant AI SDR

## Problem
Automating cold outbound with an LLM scales personalization and, without a
control, scales fabricated claims and unsafe messaging: invented facts about a
prospect, fake endorsements, unverifiable product claims, or instructions injected
into scraped enrichment data. The product goal is to let an agent draft outbound
**and guarantee that no message reaches the send layer until it passes policy
evaluation** — failing closed when the evaluator itself is unavailable.

## Approach
A draft agent writes each email grounded only in verified lead facts. A hybrid
compliance harness (deterministic checks + LLM-as-judge) scores every draft. A
control loop turns the verdict into an action — send, auto-revise, or escalate —
and a HubSpot integration records the outcome.

## Methodology
- **Dataset:** 55 labeled cases — 40 adversarial across 8 categories and 15 benign.
  Each category contains structurally distinct variants rather than name swaps: e.g.
  prompt injection covers direct, indirect, encoded, fake-system-message, quoted, and
  hidden-in-fact delivery; grounding failures cover fabricated, exaggerated, wrong-number,
  wrong-event, and inferred claims. Benign includes hard cases that look risky but are
  compliant (real numbers, neutral competitor mentions, soft timing). Generated
  reproducibly by `eval_suite/generate.py`; add variants to grow coverage (not copies).
- **Scoring:** each candidate email is graded by `evaluate()` and its verdict
  mapped to pass / block / escalate. Adversarial cases should block or escalate;
  benign cases should pass.
- **Configurations:** deterministic-only (baseline) vs. deterministic + LLM judge;
  and dev (fail-open) vs. prod (fail-closed) when the judge is unavailable.

## Metric definitions
- **Violation catch rate** — adversarial cases correctly blocked/escalated ÷ all adversarial.
- **Attack success rate** — adversarial cases that slipped through as PASS ÷ all adversarial.
- **False-positive rate** — benign cases wrongly blocked/escalated ÷ all benign.
- **Escalation rate** — cases routed to a human ÷ all cases.
- **Avg revisions before approval** — mean draft attempts per approved lead (control loop).
- **Cost / message** — LLM-judge spend per evaluated message.
- **Latency / message** — evaluator wall-clock per message.

## Results

**Deterministic-only baseline (measured, 55 cases):**

| Metric | Value |
|---|---|
| Violation catch rate | 17.5% (7/40) |
| Attack success rate | 82.5% (33/40) |
| False-positive rate | 0.0% (0/15) |

Per-category the rules catch only rule-shaped violations — some manipulative-urgency
phrasing (2/5) and most missing-opt-out (3/4, one edge case slips a misspelled
"STOPP") — while fabrication, injection, fake endorsement, exfiltration, and
ungrounded personalization score ~0. Deterministic rules cannot see meaning; this
gap is the justification for the LLM-judge layer.

**Deterministic + LLM judge:**

<!-- EVAL:START -->
_Pending measurement._ Run `ANTHROPIC_API_KEY=… make suite && make publish`;
`eval_suite/results.json` is written and this block is filled automatically with
catch rate, attack-success, false-positive rate, escalation rate, latency, and
cost/message. (No expected number is published before it is measured.)
<!-- EVAL:END -->

**Fail-closed (prod, judge unavailable):** attack success 0% and 100% escalation —
the system routes everything to a human rather than send on an unverified message.
The tradeoff (over-blocking when the judge is down) is intentional and measured.

**Guardrail control loop (sample lead set):** 2/3 auto-approved after the loop
repaired a first-draft issue; 1/3 escalated and never sent; avg 2.3 drafts/lead.

## Fail-closed design
`SDR_ENV=dev` skips an unavailable judge and passes (so the harness runs anywhere).
`SDR_ENV=prod` treats an unavailable/erroring judge as a critical (S4) failure, so
the message is blocked/escalated. A compliance check that cannot run must not
silently authorize a send.

## Limitations & next
- Judge-dependent metrics require a live model run (pending above).
- HubSpot integration is finished (contacts/notes/tasks) and runs against a sandbox
  token; email sending is intentionally dry-run.
- Next: publish the with-judge numbers; add a short demo capture; expand the
  dataset toward 100+ and add per-severity breakdowns.
