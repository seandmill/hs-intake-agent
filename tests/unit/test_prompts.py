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

import pytest

from app.prompts import get_prompt

PROMPT_NAMES = (
    "lead_classifier",
    "booking_prep",
    "estimate_followup",
    "human_handoff",
)


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_get_prompt_loads_non_empty(name: str) -> None:
    prompt = get_prompt(name)
    assert prompt
    assert isinstance(prompt, str)


def test_lead_classifier_contains_key_phrases() -> None:
    prompt = get_prompt("lead_classifier")
    assert "Dallas-Fort Worth" in prompt
    assert "requires_human" in prompt


def test_reply_prompts_require_customer_facing_output() -> None:
    for name in ("booking_prep", "estimate_followup", "human_handoff"):
        prompt = get_prompt(name)
        assert "Write only the message the customer will read" in prompt
