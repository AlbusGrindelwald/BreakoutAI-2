from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Stage = Literal["faq_answering", "lead_qualification", "escalation", "summary"]


@dataclass
class CustomerMessage:
    text: str


@dataclass
class EscalationDecision:
    should_escalate: bool = False
    reason: str | None = None
    trigger: str | None = None


@dataclass
class AgentResponse:
    answer: str
    confidence: float
    should_escalate: bool
    escalation_reason: str | None
    sop_gap: str | None
    next_stage: Stage


@dataclass
class LeadQualificationState:
    business_type: str | None = None
    team_size: str | None = None
    current_tools: str | None = None
    reason_for_enquiry: str | None = None

    def collected_details(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "business_type": self.business_type,
                "team_size": self.team_size,
                "current_tools": self.current_tools,
                "reason_for_enquiry": self.reason_for_enquiry,
            }.items()
            if value
        }


@dataclass
class ConversationSummary:
    customer_intent: str
    key_details: dict[str, str] = field(default_factory=dict)
    sop_gaps: list[str] = field(default_factory=list)
    recommended_next_action: str = "Continue standard support flow."


@dataclass
class ConversationTurn:
    customer: str
    agent: str
    escalation: EscalationDecision = field(default_factory=EscalationDecision)
    sop_gap: str | None = None
