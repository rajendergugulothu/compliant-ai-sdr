"""End-to-end pipeline (the finished GTM path):

    Lead -> (Clay enrich) -> AI SDR draft -> compliance gate -> decision
        PASS      -> HubSpot: upsert contact + log note      -> dry-run email
        ESCALATE  -> HubSpot: upsert contact + create task    -> human queue

Writes a run log to runs/runs.jsonl. HubSpot uses your sandbox when
SDR_HUBSPOT_TOKEN is set, otherwise a local fake backend (runs/hubspot_fake.json).

Usage:
    python -m sdr_agent.pipeline                     # mock LLM + fake HubSpot
    SDR_ENV=prod python -m sdr_agent.pipeline         # fail-closed if judge unavailable
    ANTHROPIC_API_KEY=... SDR_HUBSPOT_TOKEN=... python -m sdr_agent.pipeline
"""
from __future__ import annotations

import json
import os

from sdr_eval.llm import LLMClient
from sdr_eval.models import Lead
from sdr_eval.policy import load_policy

from .adapters import EmailSender, EnrichmentProvider, HubSpotCRM
from .guardrail import guardrail_send

RUN_LOG = "runs/runs.jsonl"


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(leads_path="data/leads.json", product_path="config/product.json",
        policy_path="policies/outbound-policy.json") -> list:
    policy = load_policy(policy_path)
    product = _load_json(product_path)
    leads = [Lead.from_dict(d) for d in _load_json(leads_path)]

    client = LLMClient()
    enricher = EnrichmentProvider()
    sender = EmailSender(live=False)
    crm = HubSpotCRM()

    os.makedirs("runs", exist_ok=True)
    open(RUN_LOG, "w").close()

    env = os.environ.get("SDR_ENV", "dev")
    print(f"LLM backend: {client.name} | env: {env} | HubSpot: "
          f"{'FAKE (local)' if crm.fake else 'LIVE (sandbox token)'}\n" + "=" * 72)
    records = []
    for lead in leads:
        lead = enricher.enrich(lead)
        decision = guardrail_send(policy, lead, product, client=client)
        contact_id = crm.upsert_contact(lead)

        if decision.status == "APPROVED":
            crm.log_note(contact_id, f"Compliant outbound queued. Subject: {decision.message.subject}")
            send_result = sender.send(lead, decision.message)
            action = "SENT (dry-run) + HubSpot note"
        else:
            crm.create_task(contact_id, f"Review escalated outbound for {lead.name} ({decision.reason})")
            send_result = {"sent": False, "mode": "escalated"}
            action = "ESCALATED -> HubSpot task"

        record = {
            "lead": lead.name, "company": lead.company, "status": decision.status,
            "attempts": decision.attempts, "reason": decision.reason,
            "verdict": decision.report.verdict(),
            "failures_final": [f.rule_id for f in decision.report.failures()],
            "history": decision.history, "subject": decision.message.subject,
            "hubspot_contact": contact_id, "action": action, "send": send_result,
        }
        records.append(record)
        with open(RUN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        print(f"{lead.name:<14} {lead.company:<22} {decision.status:<10} "
              f"attempts={decision.attempts}  {action}")
        if decision.status == "ESCALATED":
            print(f"   reason: {decision.reason}; final failures: {record['failures_final']}")

    print("=" * 72)
    print(f"Wrote {len(records)} records to {RUN_LOG}")
    return records


if __name__ == "__main__":
    run()
