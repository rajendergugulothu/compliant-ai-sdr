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
- **Dataset:** 64 labeled cases — 48 adversarial (6 each across 8 categories:
  fabricated facts, prompt injection, fake endorsements, unsupported product
  claims, manipulative urgency, missing opt-out, data exfiltration, ungrounded
  personalization) and 16 benign compliant emails. Generated reproducibly by
  `eval_suite/generate.py`; scale freely toward 100+.
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

**Deterministic-only baseline (measured, 64 cases):**

| Metric | Value |
|---|---|
| Violation catch rate | 25.0% (12/48) |
| Attack success rate | 75.0% (36/48) |
| False-positive rate | 0.0% (0/16) |

Per-category: manipulative urgency 6/6 and missing opt-out 6/6 (the rule-shaped
categories); fabrication, injection, fake endorsement, unsupported claims,
exfiltration, and ungrounded personalization all **0/6** — deterministic rules
cannot see meaning. This gap is the justification for the LLM-judge layer.

**Deterministic + LLM judge:** _Pending measurement._ Run
`ANTHROPIC_API_KEY=… make suite`; `eval_suite/results.json` is written with catch
rate, attack-success, false-positive rate, cost/message, and latency. Record the
figures here (do not publish an expected number).

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
