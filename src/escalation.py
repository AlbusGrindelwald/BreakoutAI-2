from __future__ import annotations

from dataclasses import dataclass

from src.models import EscalationDecision


@dataclass(frozen=True)
class TriggerRule:
    name: str
    reason: str
    keywords: tuple[str, ...]


TRIGGER_RULES: tuple[TriggerRule, ...] = (
    TriggerRule(
        name="explicit_human_request",
        reason="Customer explicitly requested a human handoff.",
        keywords=("agent", "human", "manager", "representative", "person"),
    ),
    TriggerRule(
        name="angry_or_complaint",
        reason="Customer expressed frustration or made a complaint.",
        keywords=("angry", "frustrated", "complaint", "terrible", "unacceptable", "upset"),
    ),
    TriggerRule(
        name="medical_question",
        reason="Customer asked a medical question that should be handled by a human.",
        keywords=("side effects", "safe", "pregnant", "medical", "allergy", "risk"),
    ),
    TriggerRule(
        name="pricing_negotiation",
        reason="Customer is negotiating price, which the SOP says to escalate.",
        keywords=("discount", "cheaper", "negotiate", "best price", "deal"),
    ),
)


def detect_escalation(message: str, unanswered_count: int = 0) -> EscalationDecision:
    normalized = message.lower()
    for rule in TRIGGER_RULES:
        if any(keyword in normalized for keyword in rule.keywords):
            return EscalationDecision(True, rule.reason, rule.name)

    if unanswered_count > 2:
        return EscalationDecision(
            True,
            "More than 2 questions were unanswered or outside the SOP.",
            "unanswered_question_limit",
        )

    return EscalationDecision(False)
