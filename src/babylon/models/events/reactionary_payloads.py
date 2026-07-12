"""Spec-071 reactionary/fascist-drift event payloads.

Each payload is a frozen Pydantic model mirroring the ``payload={...}`` dict
built at its publish site in
:class:`babylon.engine.systems.reactionary.FascistFactionSystem`. The
:class:`~babylon.models.events._legacy.SimulationEvent` base owns the
common ``event_type`` + ``tick`` + ``timestamp`` fields.

Naming convention: ``{EventType}Event`` (legacy suffix), matching the
majority of leaf event classes in ``_legacy.py``.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class FascistDriftEvent(SimulationEvent):
    """FASCIST_DRIFT event payload (reactionary.py:137-151).

    Emitted when a C_pb/C_la node's fascist pull crosses the drift
    threshold and its ``fascist_alignment`` is bumped.
    """

    event_type: EventType = Field(default=EventType.FASCIST_DRIFT)
    node_id: str
    fascist_pull: float
    fascist_alignment: float
    entitlement: float
    solidarity: float
    regime: str | None = None


class FascistRecruitmentEvent(SimulationEvent):
    """FASCIST_RECRUITMENT event payload (reactionary.py:162-173).

    Emitted when a drifted node's alignment crosses the recruitment
    threshold and it is captured by a fascist faction.
    """

    event_type: EventType = Field(default=EventType.FASCIST_RECRUITMENT)
    node_id: str
    faction_id: str
    fascist_alignment: float


class OrganizationalFractureEvent(SimulationEvent):
    """ORGANIZATIONAL_FRACTURE event payload (reactionary.py:262-274).

    Emitted per-member when a Labor Aristocracy member defects from a
    player organization during a crisis tick.
    """

    event_type: EventType = Field(default=EventType.ORGANIZATIONAL_FRACTURE)
    org_id: str
    member_id: str
    chauvinism: float
    defection_probability: float


class RedBrownCoupEvent(SimulationEvent):
    """RED_BROWN_COUP event payload (reactionary.py:276-287).

    Emitted when a majority of an organization's LA members defect in a
    single crisis tick.
    """

    event_type: EventType = Field(default=EventType.RED_BROWN_COUP)
    org_id: str
    defections: int
    member_count: int


__all__ = [
    "FascistDriftEvent",
    "FascistRecruitmentEvent",
    "OrganizationalFractureEvent",
    "RedBrownCoupEvent",
]
