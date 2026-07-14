"""Program 17 Wave 1 item W1.1 struggle-system event payloads.

Each payload is a frozen Pydantic model mirroring the ``payload={...}`` dict
built at its publish site in
:class:`babylon.engine.systems.struggle.StruggleSystem`. The
:class:`~babylon.models.events._legacy.SimulationEvent` base owns the
common ``event_type`` + ``tick`` + ``timestamp`` fields.

These five event families (POWER_VACUUM, REVOLUTIONARY_OFFENSIVE,
FASCIST_REVANCHISM, SPONTANEOUS_RIOT, PERIPHERAL_REVOLT) were emitted onto
the bus but silently dropped by ``_convert_bus_event_to_pydantic`` before
Wave 1 item W1.1 widened the conversion whitelist.

Naming convention: ``{EventType}Event`` (legacy suffix), matching the
majority of leaf event classes in ``_legacy.py``.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class PowerVacuumEvent(SimulationEvent):
    """POWER_VACUUM event payload (struggle.py:537-549).

    Emitted when the Comprador Bourgeoisie's wealth falls below its
    subsistence threshold, triggering the George Jackson bifurcation check
    against the Periphery Proletariat's revolutionary capacity.
    """

    event_type: EventType = Field(default=EventType.POWER_VACUUM)
    comprador_id: str
    comprador_wealth: float
    subsistence_threshold: float
    revolutionary_capacity: float
    jackson_threshold: float


class RevolutionaryOffensiveEvent(SimulationEvent):
    """REVOLUTIONARY_OFFENSIVE event payload (struggle.py:581-594).

    Emitted when a Comprador power vacuum resolves toward revolution
    (``revolutionary_capacity >= jackson_threshold``): the Periphery
    Proletariat's ``p_revolution`` is set to 1.0 and its agitation is
    boosted.
    """

    event_type: EventType = Field(default=EventType.REVOLUTIONARY_OFFENSIVE)
    periphery_id: str
    revolutionary_capacity: float
    agitation_boost: float
    narrative_hint: str


class FascistRevanchismEvent(SimulationEvent):
    """FASCIST_REVANCHISM event payload (struggle.py:630-645).

    Emitted when a Comprador power vacuum resolves toward reaction
    (``revolutionary_capacity < jackson_threshold``): the Labor Aristocracy's
    national identity and acquiescence are boosted. ``core_worker_id`` is
    ``None`` when no Labor Aristocracy node exists in the simulation.
    """

    event_type: EventType = Field(default=EventType.FASCIST_REVANCHISM)
    core_worker_id: str | None = None
    revolutionary_capacity: float
    identity_boost: float
    acquiescence_boost: float
    narrative_hint: str


class SpontaneousRiotEvent(SimulationEvent):
    """SPONTANEOUS_RIOT event payload (struggle.py:474-491).

    Emitted when a Lumpenproletariat node's volatility-vs-discipline riot
    risk crosses the ``spontaneous_riot_threshold``: wealth is destroyed
    without building solidarity.
    """

    event_type: EventType = Field(default=EventType.SPONTANEOUS_RIOT)
    node_id: str
    volatility: float
    organizational_discipline: float
    riot_risk: float
    wealth_before: float
    wealth_after: float
    narrative_hint: str


class PeripheralRevoltEvent(SimulationEvent):
    """PERIPHERAL_REVOLT event payload (struggle.py:702-718).

    Emitted when the Periphery Proletariat's ``P(S|R) > P(S|A)`` (Terminal
    Crisis Dynamics): all outgoing EXPLOITATION edges are severed, ending
    colonial extraction.
    """

    event_type: EventType = Field(default=EventType.PERIPHERAL_REVOLT)
    node_id: str
    edges_severed: int
    p_acquiescence: float
    p_revolution: float
    capital_labor_gap: float
    narrative_hint: str


__all__ = [
    "PowerVacuumEvent",
    "RevolutionaryOffensiveEvent",
    "FascistRevanchismEvent",
    "SpontaneousRiotEvent",
    "PeripheralRevoltEvent",
]
