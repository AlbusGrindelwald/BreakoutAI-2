from src.config import load_settings
from src.escalation import detect_escalation
from src.openrouter_client import OpenRouterWorkflowError, parse_confidence
from src.workflow import SupportWorkflow


SOP = {
    "business": "Bloom Aesthetics Clinic",
    "hours": "Mon-Sat, 9 am-7 pm",
    "services": [
        {"name": "Botox", "price": "from £200"},
        {"name": "Fillers", "price": "from £250"},
        {"name": "Consultations", "price": "free"},
    ],
    "booking": "Via WhatsApp or website.",
    "cancellation": "24hr cancellation required.",
    "escalate_if": [
        "complaint",
        "medical question",
        "pricing negotiation",
        "> 2 unanswered questions",
    ],
}


def test_complaint_triggers_escalation():
    decision = detect_escalation("I want to make a complaint, this is terrible.")
    assert decision.should_escalate
    assert decision.trigger == "angry_or_complaint"


def test_medical_question_triggers_escalation():
    decision = detect_escalation("Is Botox safe if I have an allergy?")
    assert decision.should_escalate
    assert decision.trigger == "medical_question"


def test_pricing_negotiation_triggers_escalation():
    decision = detect_escalation("Can you give me a discount or cheaper price?")
    assert decision.should_escalate
    assert decision.trigger == "pricing_negotiation"


def test_explicit_human_request_triggers_escalation():
    decision = detect_escalation("Please connect me to a human representative.")
    assert decision.should_escalate
    assert decision.trigger == "explicit_human_request"


def test_more_than_two_unanswered_questions_triggers_escalation():
    decision = detect_escalation("Do you offer something else?", unanswered_count=3)
    assert decision.should_escalate
    assert decision.trigger == "unanswered_question_limit"


def test_known_sop_botox_price_does_not_trigger_escalation():
    decision = detect_escalation("What are your Botox prices?")
    assert not decision.should_escalate


def test_out_of_scope_summary_recommends_handoff():
    workflow = SupportWorkflow(SOP)
    workflow.answer_faq("Do you offer laser hair removal memberships?")
    summary = workflow.summarize_conversation()
    assert summary.sop_gaps == ["The SOP does not contain the requested detail."]
    assert summary.recommended_next_action.startswith("Hand off")


def test_openrouter_failure_falls_back_to_local_answer():
    class FailingClient:
        def decide(self, system_prompt, user_message):
            raise OpenRouterWorkflowError("quota exceeded")

    workflow = SupportWorkflow(SOP, ai_client=FailingClient())
    response = workflow.answer_faq("What are your Botox prices?")
    assert response.answer == "Botox starts from £200 at Bloom Aesthetics Clinic."
    assert not response.should_escalate


def test_openrouter_settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/free")

    settings = load_settings()

    assert settings.openrouter_api_key == "test-openrouter-key"
    assert settings.openrouter_model == "openrouter/free"
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert settings.has_openrouter_key


def test_openrouter_confidence_parser_handles_strings():
    assert parse_confidence("0.87") == 0.87
    assert parse_confidence("0,87") == 0.87
    assert parse_confidence(",") == 0.5
