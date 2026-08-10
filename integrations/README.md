# Integrations (the GTM path)

The finished go-to-market path is:

```
New lead → n8n → verified context → AI SDR agent → compliance gate
                                                         │
                          ┌──────────────┬───────────────┼───────────────┐
                        PASS           BLOCK           ESCALATE
                          │              │                 │
                   HubSpot contact   regenerate       HubSpot task
                   + note            (feedback loop)   (human review)
                          │
                   dry-run email queue
```

Nothing sends real email — the email step is dry-run until you deliberately wire
a provider. HubSpot is the one **finished** integration.

## HubSpot (the chosen, finished integration)
`sdr_agent/adapters.py :: HubSpotCRM` speaks the HubSpot CRM v3 API (contacts,
notes, tasks). It runs in two modes automatically:

- **Fake (default):** no token → writes to `runs/hubspot_fake.json`, so the whole
  pipeline runs and is verifiable offline.
- **Live (sandbox):** export a private-app token and it hits HubSpot for real:
  ```bash
  export SDR_HUBSPOT_TOKEN=pat-...      # HubSpot > Settings > Integrations > Private Apps
  python -m sdr_agent.pipeline
  ```
  On PASS it upserts the contact and logs a note; on ESCALATE it creates a task
  for a human. Use a **sandbox / test account** — no need to email real people.

Required token scopes: `crm.objects.contacts.write`, plus notes/tasks write.

## n8n (orchestration)
`n8n-workflow.json` is an importable starter: webhook → call the pipeline endpoint
→ branch on `APPROVED` / `ESCALATED`. Replace the two placeholder nodes with your
HubSpot + human-queue (Slack/ticket) nodes. Expose the pipeline as an HTTP endpoint
at `/run-lead` that runs `guardrail_send` on one lead and returns `{status, ...}`.

## Clay (enrichment)
`EnrichmentProvider.enrich()` is the plug-in point — call Clay and map results onto
`Lead.enrichment` (verified facts only; that field is treated as ground truth by
the judge). See `clay-setup.md`.

## Email
`EmailSender(live=True)` is intentionally `NotImplementedError` until you wire a
provider, so the pipeline cannot send by accident.
