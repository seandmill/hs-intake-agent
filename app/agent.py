# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Home Services Intake Showcase — an ADK 2.0 graph workflow.

The graph controls the critical path. LLM nodes are used only for language
understanding (classification and reply drafting); routing and safety decisions
are made by deterministic function nodes.

    START -> normalize_lead -> classifier_agent -> policy_gate
          -> {book | estimate | human} -> format_handoff
"""

import os

import google.auth
from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.models import Gemini
from google.adk.workflow import START, Workflow
from google.genai import types

from app.policy import decide_route
from app.schemas import DispatchHandoff, IntakeDecision, LeadPayload
from app.tools import lookup_service_area, save_lead_draft

# Fall back to the Application Default Credentials project so the agent runs
# without setup both locally and on Agent Runtime.
_, adc_project = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", adc_project)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
# gemini-flash-latest is served from the "global" endpoint. Pin it so the model
# resolves regardless of the deployment region (Agent Runtime injects the region,
# e.g. us-central1, where this model alias is not published).
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

MODEL = "gemini-flash-latest"


def _model() -> Gemini:
    return Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3))


def _text_of(node_input: object) -> str:
    """Extract plain text from a string or a ``types.Content`` node input."""
    if isinstance(node_input, str):
        return node_input.strip()
    parts = getattr(node_input, "parts", None)
    if parts:
        return "".join(p.text for p in parts if getattr(p, "text", None)).strip()
    return str(node_input).strip()


# ---------- Deterministic nodes ----------


def normalize_lead(node_input: object) -> Event:
    """Clean the inbound message and stash it for downstream nodes."""
    payload = LeadPayload(source="chat", message=_text_of(node_input))
    return Event(
        output=payload.message,
        state={"lead_message": payload.message, "lead_source": payload.source},
    )


def policy_gate(ctx: Context, node_input: IntakeDecision) -> Event:
    """Apply the safety policy and choose a route.

    Billing, refunds, cancellations, complaints, and anything the classifier
    flags as ``requires_human`` always go to the human handoff, regardless of the
    model's intent. The decision is persisted so the handoff node can reuse it.
    """
    decision = (
        node_input
        if isinstance(node_input, IntakeDecision)
        else IntakeDecision.model_validate(node_input)
    )
    route = decide_route(decision)

    lead_message = ctx.state.get("lead_message", "")
    missing = ", ".join(decision.missing_fields) if decision.missing_fields else "none"
    context = (
        f"Customer message:\n{lead_message}\n\n"
        "Classification:\n"
        f"- intent: {decision.intent}\n"
        f"- urgency: {decision.urgency}\n"
        f"- trade: {decision.trade}\n"
        f"- service_city: {decision.service_city or 'unknown'}\n"
        f"- missing_fields: {missing}\n"
        f"- requires_human: {decision.requires_human}"
    )

    return Event(
        output=context,
        route=route,
        state={"decision": decision.model_dump(), "recommended_route": route},
    )


def format_handoff(ctx: Context, node_input: object) -> Event:
    """Build the structured dispatcher handoff from the drafted reply + decision.

    The customer-facing reply was already emitted by the routed reply agent, so
    this node only produces the structured handoff as workflow output (for
    programmatic use / dispatcher tooling), not user-facing content.
    """
    decision = IntakeDecision.model_validate(ctx.state.get("decision", {}))
    route = ctx.state.get("recommended_route", "human")
    lead_message = ctx.state.get("lead_message", "")
    agent_reply = _text_of(node_input)

    handoff = DispatchHandoff(
        customer_message=lead_message,
        summary=decision.summary,
        intent=decision.intent,
        urgency=decision.urgency,
        trade=decision.trade,
        service_city=decision.service_city,
        service_area_status=lookup_service_area(decision.service_city),
        requires_human=decision.requires_human or route == "human",
        missing_fields=decision.missing_fields,
        recommended_route=route,
        agent_reply=agent_reply,
        draft_id="",
    )
    handoff.draft_id = save_lead_draft(handoff.model_dump())
    return Event(output=handoff.model_dump())


# ---------- LLM nodes ----------

classifier_agent = LlmAgent(
    name="lead_classifier",
    model=_model(),
    instruction=(
        "You classify an inbound home-services lead for a Dallas-Fort Worth "
        "company. Read the customer's message and return structured output only.\n"
        "Routing rules:\n"
        "- Use 'book_service' when the customer wants a repair, install, or visit.\n"
        "- Use 'estimate_follow_up' when they reference an existing quote or estimate.\n"
        "- Use 'billing' for invoices, payments, refunds, or charges.\n"
        "- Use 'human' for cancellations, complaints, legal/permit/insurance issues, "
        "or anything ambiguous or unsafe to handle automatically.\n"
        "Set requires_human=true for any refund, discount, cancellation, complaint, "
        "or safety concern. Be conservative: when unsure, prefer requires_human=true.\n"
        "List concrete missing_fields (such as 'service address', 'phone', "
        "'preferred time') only when they are genuinely absent from the message. "
        "Extract service_city when a city is named."
    ),
    output_schema=IntakeDecision,
)

booking_prep_agent = LlmAgent(
    name="booking_prep",
    model=_model(),
    instruction=(
        "Write only the message the customer will read — no internal notes, labels, "
        "or headings. The customer wants to book home service.\n"
        "Acknowledge the issue, reflect the trade and urgency you understood, and ask "
        "for any missing details needed to schedule. Offer to get them on the books.\n"
        "Never confirm a specific appointment time and never quote a binding price; "
        "say a team member will confirm availability. Keep it under 90 words."
    ),
)

estimate_followup_agent = LlmAgent(
    name="estimate_followup",
    model=_model(),
    instruction=(
        "Write only the message the customer will read — no internal notes, labels, "
        "or headings. The customer has an open estimate.\n"
        "Invite their questions and offer to help them move forward. Answer only "
        "general, non-binding questions.\n"
        "Do NOT change prices, offer discounts, or make financing promises. If the "
        "customer asks about a price change, discount, or complaint, say you will "
        "connect them with a team member. Keep it under 90 words."
    ),
)

human_handoff_agent = LlmAgent(
    name="human_handoff",
    model=_model(),
    instruction=(
        "Write only the message the customer will read — no internal notes, labels, "
        "or headings. This path handles billing, refunds, cancellations, complaints, "
        "and unclear or sensitive requests.\n"
        "Do NOT attempt to resolve the issue, quote prices, process refunds, or make "
        "commitments. Acknowledge the request and set the expectation that a team "
        "member will follow up shortly. Keep it under 80 words."
    ),
)


# ---------- Root workflow ----------

root_agent = Workflow(
    name="hs_intake_showcase",
    edges=[
        (START, normalize_lead),
        (normalize_lead, classifier_agent),
        (classifier_agent, policy_gate),
        (
            policy_gate,
            {
                "book": booking_prep_agent,
                "estimate": estimate_followup_agent,
                "human": human_handoff_agent,
            },
        ),
        (booking_prep_agent, format_handoff),
        (estimate_followup_agent, format_handoff),
        (human_handoff_agent, format_handoff),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
