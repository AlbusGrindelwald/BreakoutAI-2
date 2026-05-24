from __future__ import annotations

import logging
from typing import Iterable

from src.escalation import detect_escalation
from src.logging_utils import log_escalation
from src.models import (
    AgentResponse,
    ConversationSummary,
    ConversationTurn,
    EscalationDecision,
    LeadQualificationState,
)
from src.openrouter_client import OpenRouterWorkflowClient, OpenRouterWorkflowError
from src.prompts import build_system_prompt
from src.sop_loader import sop_to_context


LOW_CONFIDENCE_THRESHOLD = 0.55
logger = logging.getLogger("support_workflow")


class SupportWorkflow:
    def __init__(
        self,
        sop: dict,
        ai_client: OpenRouterWorkflowClient | None = None,
    ) -> None:
        self.sop = sop
        self.sop_context = sop_to_context(sop)
        self.ai_client = ai_client
        self.turns: list[ConversationTurn] = []
        self.unanswered_count = 0
        self.lead_state = LeadQualificationState()
        self.sop_gaps: list[str] = []

    def answer_faq(self, customer_message: str) -> AgentResponse:
        rule_decision = detect_escalation(customer_message, self.unanswered_count)
        if rule_decision.should_escalate:
            answer = self._handoff_answer(rule_decision.reason)
            self._record_turn(customer_message, answer, rule_decision)
            log_escalation(rule_decision.reason, rule_decision.trigger)
            return AgentResponse(
                answer=answer,
                confidence=1.0,
                should_escalate=True,
                escalation_reason=rule_decision.reason,
                sop_gap=None,
                next_stage="escalation",
            )

        response = self._model_or_local_answer(customer_message)
        if response.sop_gap:
            self.sop_gaps.append(response.sop_gap)
            self.unanswered_count += 1

        if response.confidence < LOW_CONFIDENCE_THRESHOLD and not response.should_escalate:
            response.should_escalate = True
            response.escalation_reason = "Model confidence was below the safe-answer threshold."
            response.next_stage = "escalation"

        if response.should_escalate:
            log_escalation(response.escalation_reason, "model_or_sop_gap")

        escalation_decision = (
            EscalationDecision(
                True,
                response.escalation_reason or "AI response required escalation.",
                "model_or_sop_gap",
            )
            if response.should_escalate
            else None
        )
        self._record_turn(customer_message, response.answer, escalation_decision, response.sop_gap)
        return response

    def qualify_lead(self, answers: dict[str, str] | None = None) -> LeadQualificationState:
        if answers:
            self.lead_state.business_type = answers.get("business_type")
            self.lead_state.team_size = answers.get("team_size")
            self.lead_state.current_tools = answers.get("current_tools")
            self.lead_state.reason_for_enquiry = answers.get("reason_for_enquiry")
        return self.lead_state

    def qualification_questions(self) -> list[str]:
        return [
            "What type of business or customer need are you contacting us about?",
            "Roughly how many people are involved in making this booking decision?",
            "Are you currently using WhatsApp, a website form, or another channel to book appointments?",
        ]

    def summarize_conversation(self) -> ConversationSummary:
        customer_text = " ".join(turn.customer for turn in self.turns)
        if any(word in customer_text.lower() for word in ("botox", "price", "cost")):
            intent = "Customer asked about Botox pricing or service information."
        elif self.lead_state.collected_details():
            intent = "Customer completed lead qualification."
        else:
            intent = "Customer contacted support with a general enquiry."

        recommended_next_action = "Continue standard support flow."
        if any(turn.escalation.should_escalate for turn in self.turns):
            recommended_next_action = "Hand off to a human agent with the escalation reason and transcript."
        elif self.lead_state.collected_details():
            recommended_next_action = "Use the collected qualification details for follow-up."

        return ConversationSummary(
            customer_intent=intent,
            key_details=self.lead_state.collected_details(),
            sop_gaps=self.sop_gaps,
            recommended_next_action=recommended_next_action,
        )

    def run_scripted_conversation(self, messages: Iterable[str]) -> list[AgentResponse]:
        return [self.answer_faq(message) for message in messages]

    def _model_or_local_answer(self, customer_message: str) -> AgentResponse:
        if self.ai_client:
            try:
                return self.ai_client.decide(build_system_prompt(self.sop_context), customer_message)
            except OpenRouterWorkflowError as exc:
                logger.warning("OpenRouter API unavailable or rate-limited; using local fallback.")
        return self._local_answer(customer_message)

    def _local_answer(self, customer_message: str) -> AgentResponse:
        normalized = customer_message.lower()
        services = {service["name"].lower(): service["price"] for service in self.sop["services"]}

        if "botox" in normalized and any(word in normalized for word in ("price", "cost", "how much")):
            return AgentResponse(
                answer=f"Botox starts {services['botox']} at {self.sop['business']}.",
                confidence=0.95,
                should_escalate=False,
                escalation_reason=None,
                sop_gap=None,
                next_stage="lead_qualification",
            )
        if "filler" in normalized and any(word in normalized for word in ("price", "cost", "how much")):
            return AgentResponse(
                answer=f"Fillers start {services['fillers']} at {self.sop['business']}.",
                confidence=0.95,
                should_escalate=False,
                escalation_reason=None,
                sop_gap=None,
                next_stage="lead_qualification",
            )
        if "consultation" in normalized:
            return AgentResponse(
                answer="Consultations are free. You can book via WhatsApp or the website.",
                confidence=0.9,
                should_escalate=False,
                escalation_reason=None,
                sop_gap=None,
                next_stage="lead_qualification",
            )
        if "hour" in normalized or "open" in normalized:
            return AgentResponse(
                answer=f"{self.sop['business']} is open {self.sop['hours']}.",
                confidence=0.9,
                should_escalate=False,
                escalation_reason=None,
                sop_gap=None,
                next_stage="lead_qualification",
            )
        if "book" in normalized or "appointment" in normalized:
            return AgentResponse(
                answer=f"Booking is available {self.sop['booking']} {self.sop['cancellation']}",
                confidence=0.9,
                should_escalate=False,
                escalation_reason=None,
                sop_gap=None,
                next_stage="lead_qualification",
            )

        gap = "The SOP does not contain the requested detail."
        return AgentResponse(
            answer=f"I do not have that detail in the SOP for {self.sop['business']}. I will hand this to a human agent so they can confirm it accurately.",
            confidence=0.35,
            should_escalate=True,
            escalation_reason="Question is outside the available SOP.",
            sop_gap=gap,
            next_stage="escalation",
        )

    def _record_turn(
        self,
        customer_message: str,
        agent_answer: str,
        escalation_decision=None,
        sop_gap: str | None = None,
    ) -> None:
        self.turns.append(
            ConversationTurn(
                customer=customer_message,
                agent=agent_answer,
                escalation=escalation_decision or detect_escalation(customer_message),
                sop_gap=sop_gap,
            )
        )

    def _handoff_answer(self, reason: str | None) -> str:
        return "Thanks for flagging that. I am going to hand this over to a human agent so they can help properly."
