"""Feature-032 OODA event payloads.

:class:`OrganizationalActionEvent` mirrors the ``payload={...}`` dict built
at its live publish site in
:class:`babylon.engine.systems.ooda.OODASystem` (ooda.py:189-199).

:class:`StateRepressionEvent` / :class:`StateSurveillanceEvent` are
SPECULATIVE: no ``event_bus.publish(...)`` call exists yet for either.
``babylon.ooda.action_effects._resolve_repressive`` (lines 265-277) only
tags the ``EventType`` string onto ``ActionResult.events_generated``,
which is written but never read back to publish onto the bus. These
classes make ``_convert_bus_event_to_pydantic`` ready for that future
wiring (Program 17 item 1b, owner ruling b) — they will not appear in
real gameplay until a separate task adds the publish call.

The :class:`~babylon.models.events._legacy.SimulationEvent` base owns the
common ``event_type`` + ``tick`` + ``timestamp`` fields.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class OrganizationalActionEvent(SimulationEvent):
    """ORGANIZATIONAL_ACTION event payload (ooda.py:189-199).

    Emitted once per tick as a summary of the OODA resolution pass.
    """

    event_type: EventType = Field(default=EventType.ORGANIZATIONAL_ACTION)
    layer0_count: int
    action_count: int
    org_count: int


class StateRepressionEvent(SimulationEvent):
    """STATE_REPRESSION event payload (speculative; see module docstring)."""

    event_type: EventType = Field(default=EventType.STATE_REPRESSION)
    org_id: str
    target_id: str
    backfire_delta: float


class StateSurveillanceEvent(SimulationEvent):
    """STATE_SURVEILLANCE event payload (speculative; see module docstring)."""

    event_type: EventType = Field(default=EventType.STATE_SURVEILLANCE)
    org_id: str
    target_id: str
    backfire_delta: float


__all__ = [
    "OrganizationalActionEvent",
    "StateRepressionEvent",
    "StateSurveillanceEvent",
]
