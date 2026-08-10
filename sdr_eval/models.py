"""Core data models: leads, messages, findings, and the evaluation report.

The verdict logic here is the heart of the harness: it turns a list of
per-rule findings into a single product decision (PASS / BLOCK / ESCALATE),
weighted by severity. That mapping is exactly the "severity model -> decision"
idea from the dependable-ai-systems week.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    S0 = 0  # informational
    S1 = 1  # low
    S2 = 2  # moderate
    S3 = 3  # high
    S4 = 4  # critical

    @classmethod
    def parse(cls, s: str) -> "Severity":
        return cls[s.strip().upper()]


@dataclass
class Lead:
    """What we ACTUALLY know about a prospect. `enrichment` is the set of
    verified facts a compliant message may reference — nothing else."""
    name: str
    company: str
    role: str = ""
    enrichment: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Lead":
        return Lead(
            name=d.get("name", ""),
            company=d.get("company", ""),
            role=d.get("role", ""),
            enrichment=d.get("enrichment", ""),
        )


@dataclass
class Message:
    subject: str
    body: str
    sender_name: str = ""
    sender_company: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Message":
        return Message(
            subject=d.get("subject", ""),
            body=d.get("body", ""),
            sender_name=d.get("sender_name", ""),
            sender_company=d.get("sender_company", ""),
        )


@dataclass
class Finding:
    rule_id: str
    description: str
    severity: Severity
    passed: bool
    detail: str = ""
    source: str = "deterministic"  # "deterministic" | "judge"


@dataclass
class EvalReport:
    lead: Lead
    message: Message
    findings: list = field(default_factory=list)

    def failures(self) -> list:
        return [f for f in self.findings if not f.passed]

    def max_severity(self) -> Severity:
        return max((f.severity for f in self.failures()), default=Severity.S0)

    def verdict(self) -> str:
        """Turn findings into a product decision.

        - no failures                -> PASS
        - worst failure is S1        -> PASS_WITH_WARNINGS (send, but note it)
        - worst failure is S2 or S3  -> BLOCK (fix / regenerate before sending)
        - worst failure is S4        -> ESCALATE (block AND route to a human)
        """
        fails = self.failures()
        if not fails:
            return "PASS"
        m = self.max_severity()
        if m == Severity.S4:
            return "ESCALATE"
        if m >= Severity.S2:
            return "BLOCK"
        return "PASS_WITH_WARNINGS"
