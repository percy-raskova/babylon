"""P25 electoral-machine event payloads (U2, ADR128; the-electoral-question.md §5.4).

Thirteen typed events for the ambient machine: the election clock (ELECTION_HELD /
GOVERNMENT_FORMED), the policy pipeline and its ceiling (POLICY_ENACTED / STRUCK /
PREEMPTED, CAPITAL_STRIKE), the hope/betrayal loop (HOPE_SPIKE, DELIVERY_GAP_CROSSED,
DISILLUSION_WINDOW_OPEN), the legitimation circuit (LEGITIMATION_REFRESH,
ELECTIONS_SUSPENDED), and the conjuncture/doctrine arms (POPULAR_FRONT_CALLED,
LINE_STRUGGLE_SPLIT). Publishers arrive with U8-U12; severity derives through
``resolve_severity`` rows declared in ``event_severity.SEVERITY_TAXONOMY``.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class ElectionHeldEvent(SimulationEvent):
    """ELECTION_HELD — the ISA_POLITICAL apparatus ran its clocked circuit (U10)."""

    event_type: EventType = Field(default=EventType.ELECTION_HELD)
    sovereign_id: str
    jurisdiction_level: str = ""
    turnout: float = 0.0
    competitiveness: float = 0.0
    winning_coalition: str = ""


class GovernmentFormedEvent(SimulationEvent):
    """GOVERNMENT_FORMED — the elected configuration perturbed FactionBalance (U10)."""

    event_type: EventType = Field(default=EventType.GOVERNMENT_FORMED)
    sovereign_id: str
    governing_coalition: str = ""
    faction_balance_shift: float = 0.0


class PolicyEnactedEvent(SimulationEvent):
    """POLICY_ENACTED — a LEGISLATE agenda item survived the gauntlet; overlay lands next tick (U9)."""

    event_type: EventType = Field(default=EventType.POLICY_ENACTED)
    sovereign_id: str
    policy_axis: str = ""
    magnitude: float = 0.0
    delivery_ratio: float = 1.0


class PolicyStruckEvent(SimulationEvent):
    """POLICY_STRUCK — an RSA_JUDICIAL institution voided an overlay past its class-balance tolerance (U9)."""

    event_type: EventType = Field(default=EventType.POLICY_STRUCK)
    sovereign_id: str
    policy_axis: str = ""
    striking_institution: str = ""


class PolicyPreemptedEvent(SimulationEvent):
    """POLICY_PREEMPTED — a higher sovereign on the ADMINISTERS DAG nullified a lower overlay (U9)."""

    event_type: EventType = Field(default=EventType.POLICY_PREEMPTED)
    sovereign_id: str
    policy_axis: str = ""
    preempting_sovereign: str = ""


class CapitalStrikeEvent(SimulationEvent):
    """CAPITAL_STRIKE — policy incidence past capital_tolerance; the equalization operator migrates capital out (U9)."""

    event_type: EventType = Field(default=EventType.CAPITAL_STRIKE)
    sovereign_id: str
    incidence: float = 0.0
    tolerance: float = 0.0
    outflow: float = 0.0


class DeliveryGapCrossedEvent(SimulationEvent):
    """DELIVERY_GAP_CROSSED — an incumbent's promise-delivery gap crossed the betrayal threshold for a class (U9/U10)."""

    event_type: EventType = Field(default=EventType.DELIVERY_GAP_CROSSED)
    class_id: str
    incumbent_id: str = ""
    gap: float = 0.0
    betrayal_integral: float = 0.0


class HopeSpikeEvent(SimulationEvent):
    """HOPE_SPIKE — a viable platform raised a class's believed acquiescence arithmetic H(c) (U8)."""

    event_type: EventType = Field(default=EventType.HOPE_SPIKE)
    class_id: str
    hope: float = 0.0
    platform_id: str = ""


class DisillusionWindowOpenEvent(SimulationEvent):
    """DISILLUSION_WINDOW_OPEN — H collapsed (loss/suspension/betrayal); boosted conversion routes by T-7 (U10)."""

    event_type: EventType = Field(default=EventType.DISILLUSION_WINDOW_OPEN)
    class_id: str
    window_ticks: int = 0
    bridges_present: bool = False


class LegitimationRefreshEvent(SimulationEvent):
    """LEGITIMATION_REFRESH — the election-day consent write: turnout x competitiveness (U10)."""

    event_type: EventType = Field(default=EventType.LEGITIMATION_REFRESH)
    territory_id: str
    refresh: float = 0.0
    legitimation_index: float = 0.0


class ElectionsSuspendedEvent(SimulationEvent):
    """ELECTIONS_SUSPENDED — the bonapartist mode suspended the clock; the ritual is dead (U10)."""

    event_type: EventType = Field(default=EventType.ELECTIONS_SUSPENDED)
    sovereign_id: str
    legitimation_index: float = 0.0


class PopularFrontCalledEvent(SimulationEvent):
    """POPULAR_FRONT_CALLED — fascist_consolidation crossed the trigger; every line faces the forced choice (U12)."""

    event_type: EventType = Field(default=EventType.POPULAR_FRONT_CALLED)
    axis_progress: float = 0.0
    trigger: float = 0.0


class LineStruggleSplitEvent(SimulationEvent):
    """LINE_STRUGGLE_SPLIT — a congress line-change resolved as a split; branch assets shed (U11)."""

    event_type: EventType = Field(default=EventType.LINE_STRUGGLE_SPLIT)
    org_id: str
    old_stance: str = ""
    new_stance: str = ""
    assets_retained: float = 0.0
