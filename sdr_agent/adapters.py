"""Pluggable integration points (the GTM layer).

Everything here is a stub with a clean interface and a clear TODO where your real
Clay / CRM / email credentials go. Nothing sends real email by default — the
EmailSender is dry-run, so running the pipeline is always safe.
"""
from __future__ import annotations

import json
import os

from sdr_eval.models import Lead, Message


class EnrichmentProvider:
    """Where Clay plugs in. Given a partial lead, return an enriched lead.

    The stub is pass-through. To go live, call Clay's API / webhook here and map
    the returned fields onto Lead.enrichment (verified facts only!)."""

    def enrich(self, lead: Lead) -> Lead:
        # TODO(clay): POST lead to your Clay table / API, read back verified facts.
        return lead


class EmailSender:
    """Dry-run by default. Set live=True and wire your provider to actually send."""

    def __init__(self, live: bool = False) -> None:
        self.live = live

    def send(self, lead: Lead, message: Message) -> dict:
        if not self.live:
            return {"sent": False, "mode": "dry-run",
                    "to": lead.name, "subject": message.subject}
        # TODO(email): integrate your sending provider (e.g. SendGrid/SES) here.
        raise NotImplementedError("Wire your email provider before enabling live send.")


class CRMLogger:
    """Where Salesforce/HubSpot plugs in. Stub appends JSONL to a local file."""

    def __init__(self, path: str = "runs/crm.jsonl") -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, record: dict) -> None:
        # TODO(crm): upsert this record to your CRM instead of / in addition to file.
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
