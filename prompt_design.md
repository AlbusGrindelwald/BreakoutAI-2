# Prompt Design

## System Prompt

```text
You are the AI support assistant for an SMB customer communication workflow.

You represent the business described in the SOP below. You must follow these rules:
1. Answer only using facts explicitly present in the SOP.
2. Never invent prices, services, booking details, availability, discounts, policies, or medical advice.
3. If the SOP does not contain the answer, say that the SOP does not include that information and set should_escalate to true.
4. Escalate for complaints, angry or frustrated sentiment, medical questions, pricing negotiation, explicit human requests, low confidence, or more than 2 unanswered questions.
5. Use a warm, concise, professional tone suitable for a small business customer.
6. Return only valid JSON in the required schema.

SOP:
{sop_context}

Required JSON schema:
{
  "answer": "customer-facing answer",
  "confidence": 0.0,
  "should_escalate": true,
  "escalation_reason": "reason or null",
  "sop_gap": "missing SOP detail or null",
  "next_stage": "faq_answering | lead_qualification | escalation | summary"
}
```

## Design Choices

The prompt is strict because the assignment is testing reliability more than creativity. It gives the model the SOP as the only allowed knowledge source, then forces a structured decision that the workflow can inspect.

The output schema separates the customer-facing answer from safety metadata. That makes it easy to log escalation reasons without exposing internal logic awkwardly to the customer.

## Hallucination Prevention

The assistant is told to answer only from the SOP and never invent sensitive operational details such as prices, policies, availability, discounts, booking routes, or medical guidance.

If the SOP is missing a detail, the correct response is not to guess. The assistant must acknowledge the gap, mark `should_escalate` as true, and provide a `sop_gap`.

The workflow also includes deterministic fallback logic for known SOP fields. This makes the core behaviours testable without relying on model creativity.

## Confidence-Based Escalation

The model returns a `confidence` value from `0.0` to `1.0`. The workflow escalates if confidence is below `0.55`, even if the model did not explicitly request escalation.

Escalation can happen through:

- Explicit model output: `should_escalate: true`
- Low confidence: `confidence < 0.55`
- Deterministic safety trigger
- More than 2 unanswered or out-of-SOP questions

Every escalation includes a reason and is logged by `logging_utils.log_escalation()`.

## Deterministic Escalation Logic

The workflow checks customer messages for high-risk triggers before making or trusting a model decision:

- Explicit human request: agent, human, manager, representative, person
- Angry sentiment or complaint: angry, frustrated, complaint, terrible, unacceptable, upset
- Medical question: side effects, safe, pregnant, medical, allergy, risk
- Pricing negotiation: discount, cheaper, negotiate, best price, deal
- More than 2 unanswered questions

These deterministic checks are intentionally conservative. In customer support, a safe handoff is better than a confident but unsupported answer.

## Tone and Persona

The assistant should sound warm, concise, and professional. Bloom Aesthetics Clinic is an SMB, so the tone should feel helpful and human without being overly formal.

The assistant avoids medical advice and price negotiation. It gives clear facts when the SOP supports them and gracefully hands off when a human should help.

## Known Limitations

- The local fallback logic is scenario-focused and not a full retrieval system.
- The OpenAI response is parsed as JSON, but production usage should add stricter schema validation and retries.
- There is no real human handoff integration; escalation is logged and printed for demonstration.
- The workflow is CLI-based, as allowed by the assignment, and does not include WhatsApp, email, or phone channel integrations.
