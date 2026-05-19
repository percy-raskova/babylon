"""Spec-070 balkanization event payloads (T033, FR-022, FR-023, FR-026,
FR-028, FR-029a, FR-031, FR-034, FR-035).

Each payload is a frozen Pydantic model mirroring its JSON Schema in
``specs/070-balkanization/contracts/balkanization_events.json``. The
:class:`~babylon.models.events._legacy.SimulationEvent` base owns the
common ``event_type`` + ``tick`` + ``timestamp`` fields; spec-070
payloads inherit it.

Naming convention: ``{EventType}Payload`` to disambiguate from the
``GameOutcome`` enum values (e.g., ``RedOgvEndgamePayload`` carries
data for the ``EventType.RED_OGV_ENDGAME`` event, NOT the
``GameOutcome.RED_OGV`` enum literal).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class SovereignCollapsePayload(SimulationEvent):
    """FR-023 sovereign-collapse event payload."""

    event_type: Literal[EventType.SOVEREIGN_COLLAPSE] = EventType.SOVEREIGN_COLLAPSE
    sovereign_id: str = Field(pattern=r"^SOV_[A-Z][A-Z0-9_]*$")
    trigger: Literal[
        "legitimacy_zero",
        "ecological_overshoot",
        "nuclear_exchange",
        "general_uprising",
    ]
    claimed_territories_count: int = Field(default=0, ge=0)


class TerritoryTransitionPayload(SimulationEvent):
    """FR-022 territory-transition event payload."""

    event_type: Literal[EventType.TERRITORY_TRANSITION] = EventType.TERRITORY_TRANSITION
    territory_id: str
    from_sovereign_id: str | None = None
    to_sovereign_id: str | None = None
    from_winning_faction_id: str | None = None
    to_winning_faction_id: str | None = None
    reason: Literal[
        "influence_flip",
        "collapse_partition",
        "fracture",
        "conquest",
    ]


class FactionVictoryPayload(SimulationEvent):
    """FR-026 faction-victory event payload."""

    event_type: Literal[EventType.FACTION_VICTORY] = EventType.FACTION_VICTORY
    faction_id: str = Field(pattern=r"^FAC_[A-Z][A-Z0-9_]*$")
    aggregate_influence_share: float = Field(ge=0.0, le=1.0)


class SecessionDeclaredPayload(SimulationEvent):
    """FR-029a (2) secession-declared event payload."""

    event_type: Literal[EventType.SECESSION_DECLARED] = EventType.SECESSION_DECLARED
    secessionist_faction_id: str = Field(pattern=r"^FAC_[A-Z][A-Z0-9_]*$")
    parent_sovereign_id: str = Field(pattern=r"^SOV_[A-Z][A-Z0-9_]*$")
    contiguous_territory_ids: tuple[str, ...] = Field(min_length=1)
    observer_triggered: bool = False


class CivilWarDeclaredPayload(SimulationEvent):
    """FR-028 civil-war-declared event payload."""

    event_type: Literal[EventType.CIVIL_WAR_DECLARED] = EventType.CIVIL_WAR_DECLARED
    parent_sovereign_id: str
    secessionist_faction_id: str
    contested_territory_count: int = Field(default=0, ge=0)


class RedSettlerTrapDetectedPayload(SimulationEvent):
    """FR-034 red-settler-trap diagnostic event payload."""

    event_type: Literal[EventType.RED_SETTLER_TRAP_DETECTED] = EventType.RED_SETTLER_TRAP_DETECTED
    faction_id: str = Field(pattern=r"^FAC_[A-Z][A-Z0-9_]*$")
    class_reduction: float = Field(ge=0.0, le=1.0)
    colonial_stance: Literal["uphold", "ignore"]


class DualPowerActivePayload(SimulationEvent):
    """FR-035 dual-power-active diagnostic event payload."""

    event_type: Literal[EventType.DUAL_POWER_ACTIVE] = EventType.DUAL_POWER_ACTIVE
    territory_id: str
    competing_sovereign_ids: tuple[str, ...] = Field(min_length=2)
    control_level_sum: float = Field(default=0.0, ge=0.0)


class RedOgvEndgamePayload(SimulationEvent):
    """FR-031 RED_OGV endgame event payload (the settler-socialist trap)."""

    event_type: Literal[EventType.RED_OGV_ENDGAME] = EventType.RED_OGV_ENDGAME
    ignore_aligned_sovereign_share: float = Field(ge=0.0, le=1.0)
    class_tension: float
    aggregate_habitability: float
    habitability_slope: float
    user_facing_message: str = ""


class FragmentedCollapseEndgamePayload(SimulationEvent):
    """FR-032a FRAGMENTED_COLLAPSE endgame event payload."""

    event_type: Literal[EventType.FRAGMENTED_COLLAPSE_ENDGAME] = (
        EventType.FRAGMENTED_COLLAPSE_ENDGAME
    )
    surviving_sovereign_count: int = Field(ge=3)
    configuration_duration_ticks: int = Field(ge=10)
    insurgent_or_occupation_count: int = Field(default=1, ge=1)


__all__ = [
    "CivilWarDeclaredPayload",
    "DualPowerActivePayload",
    "FactionVictoryPayload",
    "FragmentedCollapseEndgamePayload",
    "RedOgvEndgamePayload",
    "RedSettlerTrapDetectedPayload",
    "SecessionDeclaredPayload",
    "SovereignCollapsePayload",
    "TerritoryTransitionPayload",
]
