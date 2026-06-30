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

"""Deterministic routing policy for the intake workflow.

This is intentionally pure (no I/O, no LLM, no GCP) so the safety-critical
routing decision is simple to read, test, and audit.
"""

from app.schemas import IntakeDecision, Route


def decide_route(decision: IntakeDecision) -> Route:
    """Choose the workflow route, enforcing the human-escalation safety policy.

    Billing, refunds, cancellations, complaints, and anything the classifier
    flags as ``requires_human`` always go to the human handoff, regardless of the
    model's intent.
    """
    if decision.requires_human or decision.intent == "billing":
        return "human"
    if decision.intent == "book_service":
        return "book"
    if decision.intent == "estimate_follow_up":
        return "estimate"
    return "human"
