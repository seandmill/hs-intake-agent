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

"""Unit tests for the deterministic, cred-free parts of the workflow."""

import pytest

from app.policy import decide_route
from app.schemas import IntakeDecision
from app.tools import lookup_service_area, save_lead_draft


@pytest.mark.parametrize(
    ("city", "expected"),
    [
        ("Plano", "in_area"),
        ("plano", "in_area"),
        ("  Fort Worth  ", "in_area"),
        ("Austin", "out_of_area"),
        (None, "unknown"),
        ("", "unknown"),
    ],
)
def test_lookup_service_area(city: str | None, expected: str) -> None:
    assert lookup_service_area(city) == expected


def test_save_lead_draft_returns_id_and_persists() -> None:
    handoff = {"intent": "book_service", "trade": "hvac"}
    draft_id = save_lead_draft(handoff)
    assert draft_id.startswith("lead_")
    # Distinct calls produce distinct ids.
    assert save_lead_draft(handoff) != draft_id


@pytest.mark.parametrize(
    ("intent", "requires_human", "expected"),
    [
        ("book_service", False, "book"),
        ("estimate_follow_up", False, "estimate"),
        ("billing", False, "human"),
        ("review_request", False, "human"),
        ("membership", False, "human"),
        ("human", False, "human"),
    ],
)
def test_decide_route_by_intent(
    intent: str, requires_human: bool, expected: str
) -> None:
    decision = IntakeDecision(
        intent=intent, urgency="normal", trade="hvac", requires_human=requires_human
    )
    assert decide_route(decision) == expected


def test_requires_human_overrides_bookable_intent() -> None:
    """A refund framed as a booking must still escalate to a human."""
    decision = IntakeDecision(
        intent="book_service",
        urgency="normal",
        trade="hvac",
        requires_human=True,
    )
    assert decide_route(decision) == "human"
