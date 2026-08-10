"""The guardrail loop — this is what turns evaluation into CONTROL.

draft -> evaluate -> decide:
  * PASS / PASS_WITH_WARNINGS -> APPROVED (safe to send)
  * ESCALATE (an S4 critical failure)  -> ESCALATED immediately (human review)
  * BLOCK -> feed the failures back to the agent as feedback and retry
  * still blocked after `max_attempts` -> ESCALATED (couldn't auto-fix)

The point: a compliance *score* doesn't stop a bad email — this loop does.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sdr_eval.evaluate import evaluate
from sdr_eval.llm import LLMClient
from sdr_eval.models import EvalReport, Lead, Message

from .agent import DraftAgent


@dataclass
class Decision:
    status: str  # "APPROVED" | "ESCALATED"
    message: Message
    report: EvalReport
    attempts: int
    reason: str = ""
    history: list = field(default_factory=list)


def guardrail_send(
    policy: dict,
    lead: Lead,
    product: dict,
    agent: DraftAgent | None = None,
    client: LLMClient | None = None,
    max_attempts: int = 3,
) -> Decision:
    client = client or LLMClient()
    agent = agent or DraftAgent(client)
    history: list = []
    feedback: str | None = None
    message: Message | None = None
    report: EvalReport | None = None

    for attempt in range(1, max_attempts + 1):
        message = agent.draft(lead, product, feedback)
        report = evaluate(policy, lead, message, client=client)
        verdict = report.verdict()
        history.append(
            {
                "attempt": attempt,
                "verdict": verdict,
                "failures": [f.rule_id for f in report.failures()],
            }
        )

        if verdict in ("PASS", "PASS_WITH_WARNINGS"):
            return Decision("APPROVED", message, report, attempt, "clean", history)
        if verdict == "ESCALATE":
            return Decision("ESCALATED", message, report, attempt,
                            "critical (S4) failure", history)

        # BLOCK -> build feedback and try again
        feedback = "; ".join(f"{f.rule_id}: {f.detail}" for f in report.failures())

    return Decision("ESCALATED", message, report, max_attempts,
                    f"unresolved after {max_attempts} attempts", history)
