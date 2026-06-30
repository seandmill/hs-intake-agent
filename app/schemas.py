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

"""Typed data contracts for the home-services intake workflow."""

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal[
    "book_service",
    "estimate_follow_up",
    "review_request",
    "membership",
    "billing",
    "human",
]
Urgency = Literal["emergency", "urgent", "normal", "unknown"]
Trade = Literal[
    "hvac",
    "plumbing",
    "electrical",
    "pest",
    "roofing",
    "garage_door",
    "pool",
    "unknown",
]
Route = Literal["book", "estimate", "human"]
ServiceAreaStatus = Literal["in_area", "out_of_area", "unknown"]


class LeadPayload(BaseModel):
    """A normalized inbound lead ready for classification."""

    source: str = Field(
        default="chat",
        description="Where the lead came from, e.g. chat, web_form, sms, lsa.",
    )
    message: str = Field(description="The cleaned inbound customer message.")


class IntakeDecision(BaseModel):
    """Structured classification produced by the classifier agent."""

    intent: Intent = Field(description="The primary intent of the customer message.")
    urgency: Urgency = Field(description="How time-sensitive the request appears.")
    trade: Trade = Field(description="The home-services trade the request maps to.")
    service_city: str | None = Field(
        default=None,
        description="City mentioned by the customer, if any (e.g. Plano).",
    )
    requires_human: bool = Field(
        default=False,
        description=(
            "True if the request involves billing, refunds, cancellations, "
            "complaints, or anything unsafe to handle autonomously."
        ),
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Intake fields still needed before a human can act.",
    )
    summary: str = Field(
        default="",
        description="A one-line summary of what the customer wants.",
    )


class DispatchHandoff(BaseModel):
    """The structured handoff a CSR or dispatcher receives."""

    customer_message: str
    summary: str
    intent: str
    urgency: str
    trade: str
    service_city: str | None
    service_area_status: ServiceAreaStatus
    requires_human: bool
    missing_fields: list[str]
    recommended_route: Route
    agent_reply: str
    draft_id: str
