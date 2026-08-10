# Build plan — Steps 1 → 6

Each step is a shippable increment. Step 1 is done; the rest extend it.

## Step 1 — Compliance eval harness ✅ (done)
Policy-driven graders (deterministic + LLM-judge), severity → verdict, CLI runner,
5 example cases. This is the differentiator and it's built first on purpose.
**Done when:** `python -m sdr_eval.run` blocks the bad cases and passes the clean one. ✅

## Step 2 — The draft agent ✅ (built)
`sdr_agent/agent.py` — writes an email grounded only in the provided facts, and
revises when the guardrail returns feedback. Real mode uses the LLM; mock mode uses
deterministic templates so it runs offline.
- **Done when:** `draft(lead)` produces an email scored end to end. ✅

## Step 3 — The guardrail loop ✅ (built)
`sdr_agent/guardrail.py` — on `BLOCK`, feed findings back and regenerate (max N);
on `ESCALATE` (S4) or exhausted retries, queue for a human. Evaluation → control.
- **Done when:** a bad first draft is auto-revised to passing, or escalated. ✅
  (Verified: opt-out auto-fixed on revision; unfixable banned phrase escalates after 3.)

## Step 4 — Red-teaming ✅ (built)
`sdr_agent/redteam.py` — injection / fake-endorsement / exfiltration attacks through
the same guardrail, reporting attack-success rate. Ready to also drive via
**Promptfoo / Garak** for the safety-eng story.
- **Done when:** you have an attack-success-rate number. ✅
  (Mock: 100% — no judge; re-run with a key to measure the judge closing the gap.)

## Step 5 — GTM integration — Partially complete
`sdr_agent/adapters.py` + `integrations/`. The path is `enrichment → draft → gate →
CRM → send`, gated throughout. Maturity:
- ✅ HubSpot contacts / notes / tasks (real CRM v3 API + local fake backend; idempotent upsert by email)
- ✅ n8n starter workflow (`integrations/n8n-workflow.json`)
- ⏳ Clay enrichment (plug-in point in `EnrichmentProvider.enrich`)
- ⏳ live email provider (`EmailSender` is dry-run by design)
- ⏳ hosted `/run-lead` endpoint for n8n to call
- **Done when:** a lead flows enrichment → compliant CRM record → queued email on your stack.

## Step 6 — Outcome measurement ✅ (built)
`sdr_agent/metrics.py` + `docs/case-study.md` — approval/escalation/auto-fix rates,
avg drafts, block reasons from the run log. Reply/meeting metrics await live send.
- **Done when:** a one-page case study with **real** numbers exists (feeds the evidence ledger).
  (Written with demo numbers; swap in real-key + live-send figures.)

## How this maps to the roadmap
Steps 1–4 are your **September** eval/red-team work; Step 5 is **October's** GTM +
agent build; Step 6 is **November's** outcomes. Projects B and C reuse this harness.
