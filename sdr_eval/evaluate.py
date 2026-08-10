"""Combine deterministic + judge findings into one EvalReport."""
from __future__ import annotations

from .deterministic import run_deterministic
from .judge import run_judge
from .llm import LLMClient
from .models import EvalReport, Lead, Message


def evaluate(policy: dict, lead: Lead, message: Message, client: LLMClient | None = None) -> EvalReport:
    findings = run_deterministic(policy, message) + run_judge(policy, lead, message, client=client)
    return EvalReport(lead=lead, message=message, findings=findings)
