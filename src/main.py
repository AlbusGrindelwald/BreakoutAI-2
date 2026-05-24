from __future__ import annotations

import argparse
import sys

from src.config import load_settings
from src.logging_utils import configure_logging
from src.openrouter_client import OpenRouterWorkflowClient
from src.sop_loader import load_sop
from src.workflow import SupportWorkflow


DEMO_MESSAGES = {
    "in_sop": ["What are your Botox prices?"],
    "out_of_scope": ["Do you offer laser hair removal memberships?"],
    "escalation": ["I am really frustrated. This is unacceptable and I want to complain."],
    "qualification": ["What are your Botox prices?"],
}


def build_workflow() -> SupportWorkflow:
    settings = load_settings()
    sop = load_sop(settings.sop_path)
    client = (
        OpenRouterWorkflowClient(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            app_name=settings.app_name,
            site_url=settings.site_url,
        )
        if settings.has_openrouter_key
        else None
    )
    return SupportWorkflow(sop=sop, ai_client=client)


def print_response(response) -> None:
    print(f"AI: {response.answer}")
    print(f"Confidence: {response.confidence:.2f}")
    print(f"Escalate: {response.should_escalate}")
    if response.escalation_reason:
        print(f"Escalation reason: {response.escalation_reason}")
    if response.sop_gap:
        print(f"SOP gap: {response.sop_gap}")
    print(f"Next stage: {response.next_stage}")


def print_summary(summary) -> None:
    key_details = summary.key_details or "None collected"
    sop_gaps = ", ".join(summary.sop_gaps) if summary.sop_gaps else "None"
    print("\nSummary")
    print(f"- Customer intent: {summary.customer_intent}")
    print(f"- Key details: {key_details}")
    print(f"- SOP gaps: {sop_gaps}")
    print(f"- Recommended next action: {summary.recommended_next_action}")


def run_demo(name: str) -> None:
    workflow = build_workflow()
    for message in DEMO_MESSAGES[name]:
        print(f"Customer: {message}")
        response = workflow.answer_faq(message)
        print_response(response)

    if name == "qualification":
        print("\nLead qualification questions")
        for question in workflow.qualification_questions():
            print(f"- {question}")
        workflow.qualify_lead(
            {
                "business_type": "Individual aesthetics customer",
                "team_size": "1 decision maker",
                "current_tools": "WhatsApp",
                "reason_for_enquiry": "Interested in Botox pricing and appointment booking",
            }
        )

    print_summary(workflow.summarize_conversation())


def run_interactive() -> None:
    workflow = build_workflow()
    print("Bloom Aesthetics Clinic support workflow. Type 'summary' to finish.")
    while True:
        message = input("Customer: ").strip()
        if not message:
            continue
        if message.lower() in {"summary", "end", "quit", "exit"}:
            break
        response = workflow.answer_faq(message)
        print_response(response)
        if response.next_stage == "lead_qualification" and not response.should_escalate:
            print("Qualification questions:")
            answers = {}
            fields = ["business_type", "team_size", "current_tools"]
            for field, question in zip(fields, workflow.qualification_questions()):
                answers[field] = input(f"{question} ").strip()
            workflow.qualify_lead(answers)
    print_summary(workflow.summarize_conversation())


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="AI customer support workflow demo")
    parser.add_argument("--demo", choices=sorted(DEMO_MESSAGES), help="Run a scripted demo")
    parser.add_argument("--interactive", action="store_true", help="Run an interactive session")
    args = parser.parse_args(argv)

    if args.demo:
        run_demo(args.demo)
        return 0
    if args.interactive:
        run_interactive()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
