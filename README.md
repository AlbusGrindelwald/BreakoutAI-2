# AI Customer Support Workflow

Python CLI prototype for the Closira AI Engineering Intern assignment. It simulates an AI-powered customer support workflow for Bloom Aesthetics Clinic, using SOP-grounded answers, lead qualification, escalation detection, and structured conversation summaries.

The CLI uses OpenRouter through its OpenAI-compatible API. Without a configured OpenRouter key, it falls back to deterministic local logic so the demos and tests remain runnable.

If the API returns a quota, rate-limit, billing, or authentication error, the CLI logs a warning and safely falls back to the local SOP-grounded demo logic instead of crashing.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set:

```text
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=http://localhost
OPENROUTER_APP_NAME=Bloom Aesthetics Support Workflow
```

## Run the Workflow

```bash
python -m src.main --demo in_sop
python -m src.main --demo out_of_scope
python -m src.main --demo escalation
python -m src.main --demo qualification
python -m src.main --interactive
```

## Assignment Stage Mapping

1. FAQ answering: `SupportWorkflow.answer_faq()` answers only from `data/sop.json`.
2. Lead qualification: `qualification_questions()` asks structured questions and `qualify_lead()` stores responses.
3. Escalation detection: `src/escalation.py` applies deterministic safety triggers; model responses can also escalate through structured JSON.
4. Conversation summary: `summarize_conversation()` produces customer intent, collected details, SOP gaps, and next action.

## SOP Data

The AI operates only on `data/sop.json`, which contains:

- Business: Bloom Aesthetics Clinic
- Hours: Mon-Sat, 9 am-7 pm
- Services: Botox from £200, Fillers from £250, Consultations free
- Booking: WhatsApp or website
- Cancellation: 24hr cancellation required
- Escalation rules: complaint, medical question, pricing negotiation, or more than 2 unanswered questions

## Tests

```bash
python -m pytest
```

Tests are API-free and focus on deterministic escalation behaviour.

## Trade-Offs and Limitations

- The local fallback is intentionally simple and supports only the assignment scenarios.
- Production retrieval would need stronger SOP search, richer state tracking, analytics, and human handoff integration.
- The OpenRouter path requests JSON output, but production code should add retries and stricter schema validation.

## Video Walkthrough Checklist

- Show `data/sop.json`.
- Show `prompt_design.md` and explain SOP grounding.
- Run `python -m src.main --demo in_sop`.
- Run `python -m src.main --demo escalation`.
- Show generated summary output.
- Run `python -m pytest`.
