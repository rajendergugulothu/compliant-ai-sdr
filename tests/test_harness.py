"""Deterministic checks and fail-open / fail-closed judge behavior."""
from sdr_eval.evaluate import evaluate
from sdr_eval.judge import run_judge
from sdr_eval.models import Lead, Message

LEAD = Lead("Dana Ruiz", "Northwind", "VP Ops", "runs 200 trucks", "dana@northwind.example")


def _msg(body, subject="Hi"):
    return Message(subject, body, sender_name="Raj", sender_company="Acme Analytics")


def _clean_body():
    return ("Hi Dana,\n\nNoticed your team runs 200 trucks. We help cut routing time.\n"
            "\n- Raj, Acme Analytics\nReply STOP to unsubscribe.")


def test_clean_message_passes(policy, mock_client):
    r = evaluate(policy, LEAD, _msg(_clean_body()), client=mock_client, fail_closed=False)
    assert r.verdict() == "PASS"


def test_missing_optout_blocks(policy, mock_client):
    body = "Hi Dana,\n\nWe help cut routing time.\n\n- Raj, Acme Analytics"
    r = evaluate(policy, LEAD, _msg(body), client=mock_client, fail_closed=False)
    assert r.verdict() == "BLOCK"
    assert any(f.rule_id == "OPT_OUT_PRESENT" and not f.passed for f in r.findings)


def test_banned_phrase_blocks(policy, mock_client):
    body = _clean_body().replace("We help", "We guaranteed you'll help")
    r = evaluate(policy, LEAD, _msg(body), client=mock_client, fail_closed=False)
    assert r.verdict() == "BLOCK"
    assert any(f.rule_id == "NO_BANNED_PHRASES" and not f.passed for f in r.findings)


def test_judge_dev_fail_open(policy, mock_client):
    findings = run_judge(policy, LEAD, _msg(_clean_body()), client=mock_client, fail_closed=False)
    assert findings and all(f.passed for f in findings)


def test_judge_prod_fail_closed(policy, mock_client):
    findings = run_judge(policy, LEAD, _msg(_clean_body()), client=mock_client, fail_closed=True)
    assert findings and all(not f.passed for f in findings)
    # a clean email now escalates because the judge could not verify it
    r = evaluate(policy, LEAD, _msg(_clean_body()), client=mock_client, fail_closed=True)
    assert r.verdict() == "ESCALATE"
