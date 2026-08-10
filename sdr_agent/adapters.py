"""Integration points (the GTM layer).

The chosen GTM path is: Lead -> n8n -> AI SDR -> compliance gate -> HubSpot -> dry-run email.

- HubSpotCRM: a real HubSpot CRM v3 adapter (contacts, notes, tasks). It runs
  against your HubSpot with a token, and falls back to a LOCAL FAKE backend
  (JSON on disk) when no token is set — so the whole flow runs and is testable
  offline. Point it at a HubSpot **sandbox** by exporting SDR_HUBSPOT_TOKEN.
- EmailSender: dry-run by default. Nothing sends real email until you wire a
  provider and pass live=True.
- EnrichmentProvider: where Clay plugs in (pass-through stub).
"""
from __future__ import annotations

import json
import os

from sdr_eval.models import Lead, Message

HUBSPOT_BASE = "https://api.hubapi.com"


class EnrichmentProvider:
    """Where Clay plugs in. Given a partial lead, return an enriched lead."""

    def enrich(self, lead: Lead) -> Lead:
        # TODO(clay): POST lead to your Clay table/API, read back VERIFIED facts only.
        return lead


class EmailSender:
    """Dry-run by default. Set live=True and wire your provider to actually send."""

    def __init__(self, live: bool = False) -> None:
        self.live = live

    def send(self, lead: Lead, message: Message) -> dict:
        if not self.live:
            return {"sent": False, "mode": "dry-run",
                    "to": lead.name, "subject": message.subject}
        # TODO(email): integrate your sending provider (SendGrid/SES/HubSpot email).
        raise NotImplementedError("Wire your email provider before enabling live send.")


class HubSpotCRM:
    """HubSpot CRM adapter. Real when SDR_HUBSPOT_TOKEN is set, else local fake.

    Real methods use the HubSpot CRM v3 REST API. Fake methods persist to
    runs/hubspot_fake.json so the pipeline is fully demonstrable without an account.
    """

    def __init__(self, token: str | None = None, store: str = "runs/hubspot_fake.json") -> None:
        self.token = token or os.environ.get("SDR_HUBSPOT_TOKEN")
        self.fake = not self.token
        self.store = store
        if self.fake:
            os.makedirs(os.path.dirname(store), exist_ok=True)
            if not os.path.exists(store):
                self._write({"contacts": {}, "by_key": {}, "notes": [], "tasks": []})

    # -- public API (same surface in real + fake mode) --
    def upsert_contact(self, lead: Lead) -> str:
        """Idempotent: keyed on lead.crm_key (email when available). Re-running the
        workflow updates the same contact instead of creating duplicates."""
        if self.fake:
            db = self._read()
            db.setdefault("by_key", {})
            cid = db["by_key"].get(lead.crm_key)          # reuse existing id if seen
            if not cid:
                cid = f"fake-{abs(hash(lead.crm_key)) % 100000}"
                db["by_key"][lead.crm_key] = cid
            db["contacts"][cid] = {"name": lead.name, "company": lead.company,
                                   "role": lead.role, "email": lead.email}
            self._write(db)
            return cid
        return self._hs_upsert_contact(lead)

    def log_note(self, contact_id: str, text: str) -> None:
        if self.fake:
            db = self._read(); db["notes"].append({"contact_id": contact_id, "note": text}); self._write(db)
            return
        self._hs_create_note(contact_id, text)

    def create_task(self, contact_id: str, title: str) -> None:
        if self.fake:
            db = self._read(); db["tasks"].append({"contact_id": contact_id, "title": title}); self._write(db)
            return
        self._hs_create_task(contact_id, title)

    # -- fake persistence --
    def _read(self) -> dict:
        with open(self.store, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, db: dict) -> None:
        with open(self.store, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)

    # -- real HubSpot CRM v3 calls (used when a token is present) --
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _hs_upsert_contact(self, lead: Lead) -> str:
        """Genuine upsert: find an existing contact by email, PATCH it if found,
        otherwise POST a new one. Idempotent so retries don't duplicate records."""
        import requests
        first, _, last = lead.name.partition(" ")
        props = {"firstname": first, "lastname": last or first,
                 "company": lead.company, "jobtitle": lead.role}
        if lead.email:
            props["email"] = lead.email
            # 1) search for an existing contact with this email
            search = requests.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
                headers=self._headers(),
                json={"filterGroups": [{"filters": [
                    {"propertyName": "email", "operator": "EQ", "value": lead.email}]}],
                    "properties": ["email"], "limit": 1},
                timeout=20)
            search.raise_for_status()
            results = search.json().get("results", [])
            if results:  # 2) update the existing record
                cid = results[0]["id"]
                requests.patch(f"{HUBSPOT_BASE}/crm/v3/objects/contacts/{cid}",
                               headers=self._headers(), json={"properties": props},
                               timeout=20).raise_for_status()
                return cid
        # 3) no match (or no email) -> create
        r = requests.post(f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
                          headers=self._headers(), json={"properties": props}, timeout=20)
        r.raise_for_status()
        return r.json()["id"]

    def _hs_create_note(self, contact_id: str, text: str) -> None:
        import requests
        payload = {
            "properties": {"hs_note_body": text, "hs_timestamp": _now_ms_placeholder()},
            "associations": [{
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
            }],
        }
        r = requests.post(f"{HUBSPOT_BASE}/crm/v3/objects/notes",
                          headers=self._headers(), json=payload, timeout=20)
        r.raise_for_status()

    def _hs_create_task(self, contact_id: str, title: str) -> None:
        import requests
        payload = {
            "properties": {"hs_task_subject": title, "hs_task_status": "NOT_STARTED",
                           "hs_timestamp": _now_ms_placeholder()},
            "associations": [{
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 204}],
            }],
        }
        r = requests.post(f"{HUBSPOT_BASE}/crm/v3/objects/tasks",
                          headers=self._headers(), json=payload, timeout=20)
        r.raise_for_status()


def _now_ms_placeholder() -> str:
    # HubSpot wants an epoch-ms timestamp. Compute it at call time in your integration;
    # kept as a helper so the adapter has no import-time clock dependency.
    import time
    return str(int(time.time() * 1000))
