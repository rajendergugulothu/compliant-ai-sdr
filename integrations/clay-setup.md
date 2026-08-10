# Clay setup (enrichment)

Goal: produce a small set of **verified** facts per lead that the agent may use.
Garbage or speculative enrichment becomes fabrication risk downstream, so keep
this column trustworthy.

## Minimal Clay table
| Column | Source | Notes |
|---|---|---|
| name | import / CRM | prospect full name |
| company | import / CRM | |
| role | enrichment (title finder) | |
| verified_facts | enrichment + manual review | 1–2 short, checkable facts only |

## Recommended
- Add a "confidence" column; drop low-confidence facts before they reach `verified_facts`.
- Use a Clay **HTTP API / webhook** action to POST each row to your pipeline endpoint
  (the n8n webhook), then write the returned verdict back to a "compliance_status" column.
- Never pass raw scraped blobs into `verified_facts` — that's the injection surface
  the red-team suite attacks.

## Mapping into this repo
In `sdr_agent/adapters.py`:
```python
class EnrichmentProvider:
    def enrich(self, lead):
        data = call_clay(lead)          # your Clay API call
        lead.enrichment = data["verified_facts"]
        return lead
```
