"""Feature-030 lifecycle/legitimation/inheritance event payloads.

Each payload is a frozen Pydantic model mirroring the ``payload={...}`` dict
built at its publish site in
:class:`babylon.engine.systems.lifecycle.LifecycleSystem`. The
:class:`~babylon.models.events._legacy.SimulationEvent` base owns the
common ``event_type`` + ``tick`` + ``timestamp`` fields.

Naming convention: ``{EventType}Event`` (legacy suffix), matching the
majority of leaf event classes in ``_legacy.py``.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class LifecycleTransitionEvent(SimulationEvent):
    """LIFECYCLE_TRANSITION event payload (lifecycle.py:126-138).

    Emitted every tick a territory's D/P/D' population state updates.
    """

    event_type: EventType = Field(default=EventType.LIFECYCLE_TRANSITION)
    territory_id: str
    pop_d: float
    pop_p: float
    pop_d_prime: float
    dependency_ratio: float


class LegitimationCrisisEvent(SimulationEvent):
    """LEGITIMATION_CRISIS event payload (lifecycle.py:143-152).

    Emitted the tick a territory's legitimation classification transitions
    into CRISIS.
    """

    event_type: EventType = Field(default=EventType.LEGITIMATION_CRISIS)
    territory_id: str
    legitimation_index: float


class LegitimationRecoveryEvent(SimulationEvent):
    """LEGITIMATION_RECOVERY event payload (lifecycle.py:154-163).

    Emitted the tick a territory's legitimation classification recovers
    from CRISIS to STABLE. Same shape as :class:`LegitimationCrisisEvent`;
    added for consistency (owner ruling on Program 17 item 1b).
    """

    event_type: EventType = Field(default=EventType.LEGITIMATION_RECOVERY)
    territory_id: str
    legitimation_index: float


class InheritanceTransferEvent(SimulationEvent):
    """INHERITANCE_TRANSFER event payload (lifecycle.py:172-184).

    Emitted when D' deaths trigger an inheritance flow.
    """

    event_type: EventType = Field(default=EventType.INHERITANCE_TRANSFER)
    territory_id: str
    total_transferred: float
    care_consumed: float
    net_inheritance: float
    inheritance_gini: float


__all__ = [
    "InheritanceTransferEvent",
    "LegitimationCrisisEvent",
    "LegitimationRecoveryEvent",
    "LifecycleTransitionEvent",
]
