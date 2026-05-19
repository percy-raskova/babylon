"""Spec-070 event-payload validation tests (T034).

Verifies each Pydantic payload class against its corresponding
JSON-Schema in ``contracts/balkanization_events.json``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums import EventType
from babylon.models.events.balkanization_payloads import (
    CivilWarDeclaredPayload,
    DualPowerActivePayload,
    FactionVictoryPayload,
    FragmentedCollapseEndgamePayload,
    RedOgvEndgamePayload,
    RedSettlerTrapDetectedPayload,
    SecessionDeclaredPayload,
    SovereignCollapsePayload,
    TerritoryTransitionPayload,
)

pytestmark = pytest.mark.unit


def test_sovereign_collapse_payload_basic() -> None:
    payload = SovereignCollapsePayload(
        tick=5,
        sovereign_id="SOV_USA_FED",
        trigger="legitimacy_zero",
        claimed_territories_count=42,
    )
    assert payload.event_type is EventType.SOVEREIGN_COLLAPSE
    assert payload.trigger == "legitimacy_zero"
    assert payload.claimed_territories_count == 42


def test_sovereign_collapse_rejects_bad_trigger() -> None:
    with pytest.raises(ValidationError):
        SovereignCollapsePayload(
            tick=5,
            sovereign_id="SOV_USA_FED",
            trigger="not_a_real_trigger",  # type: ignore[arg-type]
        )


def test_sovereign_collapse_rejects_malformed_sovereign_id() -> None:
    with pytest.raises(ValidationError):
        SovereignCollapsePayload(
            tick=5,
            sovereign_id="lower_case",
            trigger="legitimacy_zero",
        )


def test_territory_transition_with_null_endpoints() -> None:
    """Greenfield Territories may transition from None (unclaimed)."""

    payload = TerritoryTransitionPayload(
        tick=0,
        territory_id="HEX_001",
        from_sovereign_id=None,
        to_sovereign_id="SOV_USA_FED",
        reason="influence_flip",
    )
    assert payload.from_sovereign_id is None


def test_faction_victory_clamps_share() -> None:
    with pytest.raises(ValidationError):
        FactionVictoryPayload(
            tick=10,
            faction_id="FAC_DECOLONIAL",
            aggregate_influence_share=1.5,
        )


def test_secession_declared_requires_non_empty_contiguous_set() -> None:
    with pytest.raises(ValidationError):
        SecessionDeclaredPayload(
            tick=5,
            secessionist_faction_id="FAC_DECOLONIAL",
            parent_sovereign_id="SOV_USA_FED",
            contiguous_territory_ids=(),
        )
    payload = SecessionDeclaredPayload(
        tick=5,
        secessionist_faction_id="FAC_DECOLONIAL",
        parent_sovereign_id="SOV_USA_FED",
        contiguous_territory_ids=("HEX_001", "HEX_002"),
    )
    assert payload.observer_triggered is False


def test_civil_war_declared_default_count() -> None:
    payload = CivilWarDeclaredPayload(
        tick=20,
        parent_sovereign_id="SOV_USA_FED",
        secessionist_faction_id="FAC_DECOLONIAL",
    )
    assert payload.contested_territory_count == 0


def test_red_settler_trap_payload_only_settler_stances() -> None:
    """ABOLISH never enters the trap (per FR-034); reject it at the
    payload boundary."""

    with pytest.raises(ValidationError):
        RedSettlerTrapDetectedPayload(
            tick=12,
            faction_id="FAC_WORKERS_CONGRESS",
            class_reduction=0.7,
            colonial_stance="abolish",  # type: ignore[arg-type]
        )
    # UPHOLD + IGNORE accepted.
    for stance in ("uphold", "ignore"):
        payload = RedSettlerTrapDetectedPayload(
            tick=12,
            faction_id="FAC_WORKERS_CONGRESS",
            class_reduction=0.7,
            colonial_stance=stance,  # type: ignore[arg-type]
        )
        assert payload.colonial_stance == stance


def test_dual_power_active_requires_two_competing_sovereigns() -> None:
    with pytest.raises(ValidationError):
        DualPowerActivePayload(
            tick=15,
            territory_id="HEX_001",
            competing_sovereign_ids=("SOV_USA",),
        )
    payload = DualPowerActivePayload(
        tick=15,
        territory_id="HEX_001",
        competing_sovereign_ids=("SOV_USA", "SOV_DETROIT"),
        control_level_sum=1.2,
    )
    assert len(payload.competing_sovereign_ids) == 2


def test_red_ogv_endgame_payload_records_pedagogy_message() -> None:
    payload = RedOgvEndgamePayload(
        tick=300,
        ignore_aligned_sovereign_share=0.85,
        class_tension=0.15,
        aggregate_habitability=0.3,
        habitability_slope=-0.01,
        user_facing_message="The Workers' Congress holds power; the land is dying.",
    )
    assert payload.event_type is EventType.RED_OGV_ENDGAME
    assert "Workers' Congress" in payload.user_facing_message


def test_fragmented_collapse_requires_three_sovereigns() -> None:
    with pytest.raises(ValidationError):
        FragmentedCollapseEndgamePayload(
            tick=400,
            surviving_sovereign_count=2,
            configuration_duration_ticks=15,
        )
    payload = FragmentedCollapseEndgamePayload(
        tick=400,
        surviving_sovereign_count=4,
        configuration_duration_ticks=15,
        insurgent_or_occupation_count=2,
    )
    assert payload.surviving_sovereign_count == 4


def test_all_payloads_have_frozen_config() -> None:
    payload = FactionVictoryPayload(
        tick=10,
        faction_id="FAC_DECOLONIAL",
        aggregate_influence_share=0.7,
    )
    with pytest.raises(ValidationError):
        payload.aggregate_influence_share = 0.9  # type: ignore[misc]
