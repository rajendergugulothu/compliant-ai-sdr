"""HubSpot adapter (fake backend): note on approve, task on escalate, idempotent upsert."""
import json

from sdr_agent.adapters import HubSpotCRM
from sdr_eval.models import Lead

LEAD = Lead("Dana Ruiz", "Northwind", "VP Ops", "runs 200 trucks", "dana@northwind.example")


def _crm(tmp_path):
    return HubSpotCRM(store=str(tmp_path / "hs.json"))  # no token -> fake mode


def test_approved_logs_note(tmp_path):
    crm = _crm(tmp_path)
    cid = crm.upsert_contact(LEAD)
    crm.log_note(cid, "Compliant outbound queued.")
    db = json.load(open(crm.store, encoding="utf-8"))
    assert any(n["contact_id"] == cid and "queued" in n["note"] for n in db["notes"])


def test_escalated_creates_task(tmp_path):
    crm = _crm(tmp_path)
    cid = crm.upsert_contact(LEAD)
    crm.create_task(cid, "Review escalated outbound")
    db = json.load(open(crm.store, encoding="utf-8"))
    assert any(t["contact_id"] == cid for t in db["tasks"])


def test_upsert_is_idempotent(tmp_path):
    crm = _crm(tmp_path)
    cid1 = crm.upsert_contact(LEAD)
    cid2 = crm.upsert_contact(LEAD)  # same email -> same contact, no duplicate
    assert cid1 == cid2
    db = json.load(open(crm.store, encoding="utf-8"))
    assert len(db["contacts"]) == 1
