# Case study — Compliant AI SDR

> Numbers below are from an offline **mock-mode** demo run (`SDR_LLM=mock`), which
> exercises the full control flow without a model. Re-run with `ANTHROPIC_API_KEY`
> to populate the semantic-safety rows with real judge results, and Step-5 live
> mode to populate GTM outcomes. Replace this note with real figures for your portfolio.

## Problem
Automating cold outbound with an LLM makes it trivial to send email that fabricates
facts about a prospect, drops the required opt-out, uses manipulative language, or
gets hijacked by prompt injection hidden in enrichment data. The goal: let an agent
draft outbound **and prove each message is compliant before it can send.**

## Approach
A draft agent writes each email grounded only in verified lead facts. Every draft
passes a policy-driven compliance harness (deterministic checks + LLM-as-judge).
A guardrail loop turns the verdict into an action: send, auto-revise, or escalate.
A red-team suite attacks the same pipeline to measure how much gets through.

## Results (mock-mode demo, 3 leads + 3 attacks)

**Guardrail control loop**
| Metric | Value |
|---|---|
| Leads processed | 3 |
| Approved & sent (dry-run) | 2 (67%) |
| Escalated to human | 1 (33%) |
| Auto-fixed by guardrail (approved after a revision) | 2 |
| Avg drafts per lead | 2.33 |

The loop caught a missing opt-out on the first draft of every lead and auto-fixed it
on revision; the one lead with an unfixable banned phrase escalated after 3 attempts
instead of ever sending. **No non-compliant email was sent.**

**Red-team (safety)**
| Backend | Attack success rate |
|---|---|
| mock (deterministic only, no judge) | **3/3 = 100%** |
| real model + CLAIMS_GROUNDED judge | _(run with your key — expected to trend toward 0)_ |

This is the headline safety finding: deterministic rules alone let **every**
injection / fabrication attack through. The gap between the two rows is the
quantified value of the LLM-judge layer — exactly the "why one grader isn't enough"
argument, but measured.

## What this demonstrates (per target role)
- **AI safety engineer:** a policy-driven eval harness, a guardrail control loop, and a red-team suite with an attack-success-rate metric.
- **AI-native PM:** policy → testable rules → a ship/block/escalate decision, with outcome metrics and explicit non-goals.
- **GTM engineer:** a real outbound workflow (enrich → draft → gate → send) with Clay/n8n/CRM plug-in points.

## Next (to make the numbers real)
1. Run with a real key; record the judge's attack-success-rate and fabrication catch rate.
2. Enable Clay enrichment + live send on a small real list; record reply rate, meetings booked, hours saved.
3. Add those figures to `evidence/portfolio-evidence-ledger.csv` with reproducibility notes.
