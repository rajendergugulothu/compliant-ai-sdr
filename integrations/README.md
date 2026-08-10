# Integrations (the GTM layer)

These wire the compliance-gated agent into a real go-to-market stack. They're the
Step 5 pieces — provided as clean plug-in points, not live connections, because
they need **your** accounts and keys. Nothing here sends real email until you
explicitly enable it.

## The shape
```
Clay (enrichment) ──> n8n (orchestration) ──> this repo's pipeline ──> CRM + send
```

- **Clay** — builds the verified lead facts. In `sdr_agent/adapters.py`,
  `EnrichmentProvider.enrich()` is where you call Clay and map results onto
  `Lead.enrichment`. Only put **verified** facts there — the judge treats anything
  in that field as ground truth.
- **n8n** — orchestrates the flow and calls the pipeline. See `n8n-workflow.json`
  for an importable starter (webhook -> HTTP call -> branch on APPROVED/ESCALATED).
- **CRM** (HubSpot/Salesforce) — `CRMLogger.log()` currently appends JSONL; swap in
  an upsert to your CRM.
- **Email** — `EmailSender(live=True)` is intentionally `NotImplementedError` until
  you wire a provider, so you can't send by accident.

## To go live (checklist)
1. Fill `EnrichmentProvider.enrich()` with your Clay call.
2. Implement `EmailSender.send()` for your provider and construct `EmailSender(live=True)` in `pipeline.py`.
3. Point `CRMLogger` at your CRM.
4. Import `n8n-workflow.json` into n8n and set the webhook + expose the pipeline as an HTTP endpoint.
5. Keep the guardrail between draft and send — that's the whole point.

See `clay-setup.md` for the Clay table setup.
