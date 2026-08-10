"""Severity -> verdict mapping is the core decision logic."""
from sdr_eval.models import EvalReport, Finding, Lead, Message, Severity


def _report(*findings):
    return EvalReport(lead=Lead("A", "B"), message=Message("s", "b"), findings=list(findings))


def _fail(sev):
    return Finding("R", "d", sev, passed=False)


def _ok(sev):
    return Finding("R", "d", sev, passed=True)


def test_clean_passes():
    assert _report(_ok(Severity.S4)).verdict() == "PASS"


def test_s1_warns():
    assert _report(_fail(Severity.S1)).verdict() == "PASS_WITH_WARNINGS"


def test_s2_blocks():
    assert _report(_fail(Severity.S2)).verdict() == "BLOCK"


def test_s3_blocks():
    assert _report(_fail(Severity.S3)).verdict() == "BLOCK"


def test_s4_escalates():
    assert _report(_fail(Severity.S4), _ok(Severity.S1)).verdict() == "ESCALATE"
