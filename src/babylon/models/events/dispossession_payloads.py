"""Program 17 Wave 1 item W1.1 dispossession/reserve-army/metabolism payloads.

Each payload is a frozen Pydantic model mirroring the ``payload={...}`` dict
built at its publish site. The
:class:`~babylon.models.events._legacy.SimulationEvent` base owns the
common ``event_type`` + ``tick`` + ``timestamp`` fields.

Publish sites:

- :class:`babylon.engine.systems.dispossession_events.DispossessionEventSystem`
  (DISPOSSESSION_EVENT, VALUE_TRANSFER)
- :class:`babylon.engine.systems.reserve_army.ReserveArmySystem`
  (RESERVE_ARMY_PRESSURE)
- :class:`babylon.domain.economics.tick.system.TickDynamicsSystem`
  (DISPOSSESSION_CASCADE — published via ``EventType.DISPOSSESSION_CASCADE.value``,
  a plain string, not the enum member; the converter's str-normalization
  path handles this transparently)
- :class:`babylon.engine.systems.metabolism.MetabolismSystem`
  (ECOLOGICAL_OVERSHOOT)

These five event families were emitted onto the bus but silently dropped by
``_convert_bus_event_to_pydantic`` before Wave 1 item W1.1 widened the
conversion whitelist.

Naming convention: ``{EventType}Event`` (legacy suffix), matching the
majority of leaf event classes in ``_legacy.py``. ``DISPOSSESSION_EVENT``'s
class is named ``DispossessionEvent`` (dropping the redundant repeated
"Event") rather than the literal ``DispossessionEventEvent``.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class DispossessionEvent(SimulationEvent):
    """DISPOSSESSION_EVENT event payload (dispossession_events.py:118-131).

    Emitted once per territory per tick recording the computed dispossession
    intensity and its component rates.
    """

    event_type: EventType = Field(default=EventType.DISPOSSESSION_EVENT)
    territory: str
    intensity: float
    foreclosure_rate: float
    eviction_rate: float
    displacement_rate: float


class ValueTransferEvent(SimulationEvent):
    """VALUE_TRANSFER event payload (dispossession_events.py:101-113).

    Emitted when a territory's dispossession intensity produces a positive
    wealth transfer, before the aggregate DISPOSSESSION_EVENT for the same
    territory/tick.
    """

    event_type: EventType = Field(default=EventType.VALUE_TRANSFER)
    territory: str
    total_transferred: float
    net_received: float
    deadweight_loss: float


class ReserveArmyPressureEvent(SimulationEvent):
    """RESERVE_ARMY_PRESSURE event payload (reserve_army.py:88-101).

    Emitted when a territory's reserve ratio produces positive wage
    pressure; ``median_wage`` mirrors the post-update node value.
    """

    event_type: EventType = Field(default=EventType.RESERVE_ARMY_PRESSURE)
    territory: str
    reserve_ratio: float
    wage_pressure: float
    median_wage: float


class DispossessionCascadeEvent(SimulationEvent):
    """DISPOSSESSION_CASCADE event payload (tick/system/__init__.py:944-955).

    Emitted when a county's Labor Aristocracy share decline crosses the
    highest configured milestone since the previous tick's baseline. The
    live publish site emits ``EventType.DISPOSSESSION_CASCADE.value`` (a
    string), not the enum member.
    """

    event_type: EventType = Field(default=EventType.DISPOSSESSION_CASCADE)
    fips: str
    cumulative_la_decline: float
    milestone_crossed: float
    current_la_share: float
    baseline_la_share: float


class EcologicalOvershootEvent(SimulationEvent):
    """ECOLOGICAL_OVERSHOOT event payload (metabolism.py:128-138).

    Emitted when total consumption exceeds total biocapacity beyond the
    configured overshoot threshold (Metabolic Rift, Slice 1.4).
    """

    event_type: EventType = Field(default=EventType.ECOLOGICAL_OVERSHOOT)
    overshoot_ratio: float
    total_consumption: float
    total_biocapacity: float


__all__ = [
    "DispossessionEvent",
    "ValueTransferEvent",
    "ReserveArmyPressureEvent",
    "DispossessionCascadeEvent",
    "EcologicalOvershootEvent",
]
