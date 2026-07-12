"""Feature-040 institution event payloads.

Mirrors the plain-``BaseModel`` ``FactionShiftEvent``/``BonapartistModeEvent``
at ``babylon.models.entities.institution`` (lines 428-487), but as
:class:`~babylon.models.events._legacy.SimulationEvent` subclasses so they
can flow through ``_convert_bus_event_to_pydantic`` and carry the common
``event_type`` + ``tick`` + ``timestamp`` fields. ``old_fraction``/
``new_fraction`` are typed ``str`` here (not the ``RulingClassFraction``
enum) for JSON-payload consistency with the rest of the bus-event wire.

DEAD-UNTIL-WIRED: ``update_internal_balance()``
(``babylon.domain.institution.balance``) is called only from
``tests/unit/institution/test_balance.py`` — no engine System publishes
these events in production today. Widening the conversion whitelist makes
the converter ready; it does not make these events appear in real gameplay.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class InstitutionFactionShiftEvent(SimulationEvent):
    """INSTITUTION_FACTION_SHIFT event payload.

    Mirrors ``babylon.models.entities.institution.FactionShiftEvent``.
    """

    event_type: EventType = Field(default=EventType.INSTITUTION_FACTION_SHIFT)
    institution_id: str
    old_fraction: str
    new_fraction: str
    weights: dict[str, float]


class InstitutionBonapartistModeEvent(SimulationEvent):
    """INSTITUTION_BONAPARTIST_MODE event payload.

    Mirrors ``babylon.models.entities.institution.BonapartistModeEvent``.
    """

    event_type: EventType = Field(default=EventType.INSTITUTION_BONAPARTIST_MODE)
    institution_id: str
    bonapartist_weight: float = Field(ge=0.0, le=1.0)


__all__ = [
    "InstitutionBonapartistModeEvent",
    "InstitutionFactionShiftEvent",
]
