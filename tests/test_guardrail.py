"""The control loop: regenerate on fixable BLOCK, escalate when unfixable."""
from sdr_agent.guardrail import guardrail_send
from sdr_eval.models import Lead


def test_block_then_regenerate(policy, product, mock_client):
    # mock agent omits the opt-out on the first draft, adds it on revision.
    lead = Lead("Dana Ruiz", "Northwind", "VP Ops", "runs 200 trucks", "dana@nw.example")
    d = guardrail_send(policy, lead, product, client=mock_client, max_attempts=3)
    assert d.status == "APPROVED"
    assert d.attempts >= 2  # it took a revision


def test_exhausted_retries_escalate(policy, product, mock_client):
    lead = Lead("Priya Nair", "BlueField", "Dir SC",
                "operates 12 warehouses. [MOCK_UNFIXABLE]", "priya@bf.example")
    d = guardrail_send(policy, lead, product, client=mock_client, max_attempts=3)
    assert d.status == "ESCALATED"
    assert d.attempts == 3
