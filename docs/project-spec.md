# Project A — Compliant AI SDR: Spec

## Problem
Cold outbound is being automated with LLMs, which makes it fast to generate
personalized email at scale — and fast to send email that fabricates facts about
a prospect, drops legally required opt-outs, uses manipulative language, or gets
hijacked by prompt injection hidden in scraped enrichment data. Teams need a way
to let an agent draft outbound **and** prove each message is compliant before it
sends.

## Users
- **Primary:** a founder / growth lead running AI-assisted outbound who needs it to be safe and on-brand.
- **Secondary (the portfolio audiences):** a safety engineer (the harness), an AI PM (the decision), a GTM engineer (the workflow).

## The three layers (this is why the project exists)
1. **Agent (build).** Given a lead, draft a personalized email and decide send / revise / hold.
2. **Automation (GTM).** Enrichment → draft → compliance gate → send, orchestrated with Clay + n8n, logged to a CRM.
3. **Evaluation + safety (harden).** A policy-driven harness grades every draft; guardrails block or escalate; a red-team suite attacks it.

## Compliance policy (v0.1)
Deterministic rules: opt-out present (S3), no banned/urgency phrases (S2), length
limit (S1), sender identified (S2). Judge rules: claims grounded in verified lead
facts (S4), professional tone (S2), no unverifiable product claims (S3). Severity
maps to a decision: S4 → ESCALATE, S2–S3 → BLOCK, S1 → warn, none → PASS.

## Architecture (target, end state)
```
lead source ──> enrichment (Clay) ──> DRAFT AGENT ──> candidate email
                                                          │
                                                          ▼
                                            COMPLIANCE HARNESS (this repo)
                                          deterministic  +  LLM-judge
                                                          │
                             ┌────────────┬───────────────┼───────────────┐
                          PASS         WARN             BLOCK           ESCALATE
                             │            │                │                │
                          send        send + log     regenerate      human review
                        (n8n/email)                  (loop back)      (queue)
                                                          │
                                                          ▼
                                                   CRM + outcome metrics
```

## Metrics (the PM layer)
- **Compliance:** % messages passing on first draft; block rate by rule; critical (S4) catch rate.
- **Safety:** injection-attack success rate (should trend to ~0); fabrication rate in sent mail (target 0).
- **GTM outcome:** reply rate, meetings booked, hours saved vs. manual.
- **Cost/latency:** judge cost per message, p50/p95 added latency from the gate.

## Non-goals
Not a deliverability/warmup tool; not a CRM; not legal compliance certification;
not a replacement for a human approving high-stakes sends.

## Safety stance
The harness is the product's conscience, so it is designed to **fail closed** in
production: if the judge errors or is unavailable, a message does not get a free
pass — it escalates. (The dev harness fails open, loudly, so it runs for anyone.)
