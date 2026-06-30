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

"""Mock, in-memory tools.

These stand in for the real integrations a client engagement would attach
(service-area / dispatch boundaries, and a CRM write such as ServiceTitan,
Housecall Pro, or Jobber). They keep all data inside the demo boundary so the
showcase is safe to run and share publicly.
"""

import uuid

# A small slice of Dallas-Fort Worth metro cities used as a stand-in for a real
# service-area boundary check.
_DFW_SERVICE_AREA: frozenset[str] = frozenset(
    {
        "dallas",
        "fort worth",
        "arlington",
        "plano",
        "frisco",
        "irving",
        "garland",
        "mckinney",
        "denton",
        "richardson",
        "allen",
        "carrollton",
        "lewisville",
        "grand prairie",
        "mesquite",
        "euless",
        "bedford",
        "grapevine",
        "flower mound",
        "rockwall",
    }
)

# Stands in for a CRM record store. In a real engagement this would be a write
# to the client's field-service management system.
_SAVED_LEADS: dict[str, dict] = {}


def lookup_service_area(city: str | None) -> str:
    """Check whether a city is inside the mock DFW service area.

    Returns one of ``in_area``, ``out_of_area``, or ``unknown``.
    """
    if not city:
        return "unknown"
    return "in_area" if city.strip().lower() in _DFW_SERVICE_AREA else "out_of_area"


def save_lead_draft(handoff: dict) -> str:
    """Simulate persisting a structured lead/handoff record to a CRM.

    Returns a generated draft id. The record is kept in memory only.
    """
    draft_id = f"lead_{uuid.uuid4().hex[:10]}"
    _SAVED_LEADS[draft_id] = handoff
    return draft_id
