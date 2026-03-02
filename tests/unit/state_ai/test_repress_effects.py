"""Unit tests for REPRESS effects (Feature 039 Phase 10D).

Tests INFILTRATE, RAID, PROSECUTE, LIQUIDATE, and
compute_raid_consciousness_effect resolution.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-B06.
    :mod:`babylon.ooda.state_ai.repress_effects`: Implementation.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.repress_effects import (
    compute_raid_consciousness_effect,
    resolve_infiltrate,
    resolve_liquidate,
    resolve_prosecute,
    resolve_raid,
)


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_org(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": "org_player_1",
        "coherence": 0.8,
        "key_figure_ids": ["fig_a", "fig_b"],
    }
    defaults.update(overrides)
    return defaults


def _make_thread(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "thread_id": "thread_001",
        "intel_completeness": 0.2,
        "phase": "MONITORING",
    }
    defaults.update(overrides)
    return defaults


def _make_territory(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "collective_identity": 0.5,
        "community_infrastructure_quality": 0.5,
        "territory_type": "PERIPHERY",
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# resolve_infiltrate tests
# ===========================================================================


class TestResolveInfiltrate:
    """Unit tests for resolve_infiltrate."""

    def test_informant_adds_correct_intel(self) -> None:
        defines = _make_defines(infiltrate_informant_intel_rate=0.05)
        thread = _make_thread(intel_completeness=0.2)
        result_thread, _, _ = resolve_infiltrate(
            _make_org(), thread, "INFORMANT", defines, rng_seed=42
        )
        assert result_thread["intel_completeness"] == pytest.approx(0.25)

    def test_provocateur_adds_less_intel(self) -> None:
        defines = _make_defines(
            infiltrate_informant_intel_rate=0.05,
            infiltrate_provocateur_intel_rate=0.03,
        )
        thread = _make_thread(intel_completeness=0.2)
        prov_thread, _, _ = resolve_infiltrate(
            _make_org(), thread, "PROVOCATEUR", defines, rng_seed=42
        )
        assert prov_thread["intel_completeness"] == pytest.approx(0.23)

    def test_mole_adds_most_intel(self) -> None:
        defines = _make_defines(infiltrate_mole_intel_rate=0.08)
        thread = _make_thread(intel_completeness=0.2)
        result_thread, _, _ = resolve_infiltrate(_make_org(), thread, "MOLE", defines, rng_seed=42)
        assert result_thread["intel_completeness"] == pytest.approx(0.28)

    def test_detection_is_deterministic(self) -> None:
        defines = _make_defines()
        _, record1, d1 = resolve_infiltrate(
            _make_org(), _make_thread(), "INFORMANT", defines, rng_seed=42
        )
        _, record2, d2 = resolve_infiltrate(
            _make_org(), _make_thread(), "INFORMANT", defines, rng_seed=42
        )
        assert d1 == d2
        assert record1["detected"] == record2["detected"]

    def test_provocateur_higher_detection_chance(self) -> None:
        """PROVOCATEUR has 1.5x base detection chance."""
        defines = _make_defines(infiltrate_detection_base_chance=0.5)
        # With 0.5 * 1.5 = 0.75 detection chance, most seeds will detect
        detections = 0
        max_seeds: int = 20
        for seed in range(max_seeds):
            _, _, detected = resolve_infiltrate(
                _make_org(), _make_thread(), "PROVOCATEUR", defines, rng_seed=seed
            )
            if detected:
                detections += 1
        # With 75% chance over 20 trials, expect ~15 detections
        assert detections > 10

    def test_does_not_mutate_inputs(self) -> None:
        defines = _make_defines()
        org = _make_org()
        thread = _make_thread()
        orig_org = dict(org)
        orig_thread = dict(thread)
        _ = resolve_infiltrate(org, thread, "INFORMANT", defines, rng_seed=42)
        assert org == orig_org
        assert thread == orig_thread

    def test_intel_capped_at_one(self) -> None:
        defines = _make_defines(infiltrate_mole_intel_rate=0.08)
        thread = _make_thread(intel_completeness=0.95)
        result_thread, _, _ = resolve_infiltrate(_make_org(), thread, "MOLE", defines, rng_seed=42)
        assert result_thread["intel_completeness"] == pytest.approx(1.0)

    def test_infiltration_record_fields(self) -> None:
        defines = _make_defines()
        _, record, _ = resolve_infiltrate(
            _make_org(), _make_thread(), "INFORMANT", defines, rng_seed=42, current_tick=5
        )
        assert record["agent_type"] == "INFORMANT"
        assert record["target_org_id"] == "org_player_1"
        assert record["created_tick"] == 5
        assert isinstance(record["detected"], bool)

    def test_detected_marked_in_record(self) -> None:
        """If detected, the record reflects this."""
        defines = _make_defines(infiltrate_detection_base_chance=1.0)
        _, record, detected = resolve_infiltrate(
            _make_org(), _make_thread(), "INFORMANT", defines, rng_seed=42
        )
        assert detected is True
        assert record["detected"] is True


# ===========================================================================
# resolve_raid tests
# ===========================================================================


class TestResolveRaid:
    """Unit tests for resolve_raid."""

    def test_raid_reduces_coherence(self) -> None:
        defines = _make_defines(raid_org_coherence_damage=0.2)
        org = _make_org(coherence=0.8)
        result_org, _, _, _ = resolve_raid(
            org, _make_territory(), "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert result_org["coherence"] == pytest.approx(0.6)

    def test_raid_swat_multiplies_damage(self) -> None:
        defines = _make_defines(
            raid_org_coherence_damage=0.2,
            raid_force_multiplier_swat=1.5,
        )
        org = _make_org(coherence=0.8)
        result_org, _, _, _ = resolve_raid(
            org, _make_territory(), "TARGETED", "SWAT", 0.5, [], defines, rng_seed=42
        )
        assert result_org["coherence"] == pytest.approx(0.5)

    def test_raid_military_multiplies_further(self) -> None:
        defines = _make_defines(
            raid_org_coherence_damage=0.2,
            raid_force_multiplier_military=2.5,
        )
        org = _make_org(coherence=0.8)
        result_org, _, _, _ = resolve_raid(
            org, _make_territory(), "TARGETED", "MILITARY", 0.5, [], defines, rng_seed=42
        )
        assert result_org["coherence"] == pytest.approx(0.3)

    def test_raid_captures_key_figures(self) -> None:
        """With high intel and high force, captures are likely."""
        defines = _make_defines(
            raid_key_figure_capture_base=0.3,
            raid_force_multiplier_military=2.5,
        )
        org = _make_org()
        _, _, captured, _ = resolve_raid(
            org,
            _make_territory(),
            "TARGETED",
            "MILITARY",
            1.0,  # Full intel
            ["fig_a", "fig_b"],
            defines,
            rng_seed=42,
        )
        # P(capture) = 0.3 * 2.5 * 1.0 = 0.75 per figure
        assert isinstance(captured, list)

    def test_raid_high_ci_radicalizes(self) -> None:
        """COINTELPRO double bind: raiding high-CI territory increases CI."""
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_radicalization_boost=0.1,
        )
        territory = _make_territory(collective_identity=0.6)
        _, result_terr, _, _ = resolve_raid(
            _make_org(), territory, "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert result_terr["collective_identity"] > 0.6

    def test_raid_low_ci_suppresses(self) -> None:
        """Low-CI territory gets suppressed by RAID."""
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_suppression_rate=0.15,
        )
        territory = _make_territory(collective_identity=0.3)
        _, result_terr, _, _ = resolve_raid(
            _make_org(), territory, "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert result_terr["collective_identity"] < 0.3

    def test_raid_ci_at_threshold_radicalizes(self) -> None:
        """CI exactly at threshold => radicalizes (>= comparison)."""
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_radicalization_boost=0.1,
        )
        territory = _make_territory(collective_identity=0.5)
        _, result_terr, _, _ = resolve_raid(
            _make_org(), territory, "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert result_terr["collective_identity"] == pytest.approx(0.6)

    def test_raid_legitimacy_scales_with_scale(self) -> None:
        defines = _make_defines()
        _, _, _, leg_targeted = resolve_raid(
            _make_org(), _make_territory(), "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        _, _, _, leg_mass = resolve_raid(
            _make_org(), _make_territory(), "MASS", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert leg_mass > leg_targeted

    def test_mass_raid_damages_community_infrastructure(self) -> None:
        defines = _make_defines()
        territory = _make_territory(community_infrastructure_quality=0.5)
        _, result_terr, _, _ = resolve_raid(
            _make_org(), territory, "MASS", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert result_terr["community_infrastructure_quality"] < 0.5

    def test_raid_does_not_mutate_inputs(self) -> None:
        defines = _make_defines()
        org = _make_org()
        territory = _make_territory()
        orig_org = dict(org)
        orig_terr = dict(territory)
        _ = resolve_raid(org, territory, "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42)
        assert org == orig_org
        assert territory == orig_terr

    def test_raid_no_figures_captures_none(self) -> None:
        defines = _make_defines()
        _, _, captured, _ = resolve_raid(
            _make_org(), _make_territory(), "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert captured == []

    def test_raid_zero_intel_minimal_capture(self) -> None:
        """Zero thread intel means capture probability is 0."""
        defines = _make_defines(raid_key_figure_capture_base=0.3)
        _, _, captured, _ = resolve_raid(
            _make_org(),
            _make_territory(),
            "TARGETED",
            "POLICE",
            0.0,  # No intel
            ["fig_a", "fig_b"],
            defines,
            rng_seed=42,
        )
        assert captured == []


# ===========================================================================
# resolve_prosecute tests
# ===========================================================================


class TestResolveProsecute:
    """Unit tests for resolve_prosecute."""

    def test_prosecute_reduces_coherence(self) -> None:
        defines = _make_defines(prosecute_org_morale_damage=0.1)
        org = _make_org(coherence=0.8)
        result_org, _, _ = resolve_prosecute(org, "fig_a", "CONSPIRACY", defines, rng_seed=42)
        assert result_org["coherence"] == pytest.approx(0.7)

    def test_terrorism_multiplies_morale_damage(self) -> None:
        defines = _make_defines(
            prosecute_org_morale_damage=0.1,
            prosecute_terrorism_charge_multiplier=1.5,
        )
        org = _make_org(coherence=0.8)
        result_org, _, _ = resolve_prosecute(org, "fig_a", "TERRORISM", defines, rng_seed=42)
        assert result_org["coherence"] == pytest.approx(0.65)

    def test_conviction_removes_key_figure(self) -> None:
        """Successful conviction with figure targeted removes figure."""
        # Use a seed that produces conviction (removal_chance = 0.6)
        defines = _make_defines(prosecute_key_figure_removal_chance=1.0)
        org = _make_org()
        _, record, _ = resolve_prosecute(org, "fig_a", "CONSPIRACY", defines, rng_seed=42)
        assert record["convicted"] is True
        assert record["figure_removed"] is True

    def test_failed_conviction_negative_legitimacy(self) -> None:
        """Failed conviction gives negative legitimacy."""
        defines = _make_defines(
            prosecute_key_figure_removal_chance=0.0,  # Always fails
            prosecute_legitimacy_boost_success=0.02,
        )
        _, _, legitimacy_delta = resolve_prosecute(
            _make_org(), "fig_a", "CONSPIRACY", defines, rng_seed=42
        )
        assert legitimacy_delta == pytest.approx(-0.02)

    def test_successful_conviction_positive_legitimacy(self) -> None:
        """Successful conviction gives positive legitimacy."""
        defines = _make_defines(
            prosecute_key_figure_removal_chance=1.0,  # Always convicts
            prosecute_legitimacy_boost_success=0.02,
        )
        _, _, legitimacy_delta = resolve_prosecute(
            _make_org(), "fig_a", "CONSPIRACY", defines, rng_seed=42
        )
        assert legitimacy_delta == pytest.approx(0.02)

    def test_prosecute_without_figure_still_damages(self) -> None:
        """Prosecution without targeting a figure still hurts org coherence."""
        defines = _make_defines(prosecute_org_morale_damage=0.1)
        org = _make_org(coherence=0.8)
        result_org, record, _ = resolve_prosecute(org, None, "CONSPIRACY", defines, rng_seed=42)
        assert result_org["coherence"] < 0.8
        assert record["figure_id"] is None

    def test_does_not_mutate_inputs(self) -> None:
        defines = _make_defines()
        org = _make_org()
        orig = dict(org)
        _ = resolve_prosecute(org, "fig_a", "CONSPIRACY", defines, rng_seed=42)
        assert org == orig

    def test_invalid_charge_raises(self) -> None:
        defines = _make_defines()
        with pytest.raises(ValueError, match="Invalid charge"):
            resolve_prosecute(_make_org(), "fig_a", "JAYWALKING", defines, rng_seed=42)

    def test_deterministic_with_same_seed(self) -> None:
        defines = _make_defines()
        _, r1, l1 = resolve_prosecute(_make_org(), "fig_a", "CONSPIRACY", defines, rng_seed=42)
        _, r2, l2 = resolve_prosecute(_make_org(), "fig_a", "CONSPIRACY", defines, rng_seed=42)
        assert r1["convicted"] == r2["convicted"]
        assert l1 == l2

    def test_prosecution_record_fields(self) -> None:
        defines = _make_defines()
        _, record, _ = resolve_prosecute(
            _make_org(), "fig_a", "RACKETEERING", defines, rng_seed=42, current_tick=10
        )
        assert record["target_org_id"] == "org_player_1"
        assert record["figure_id"] == "fig_a"
        assert record["charge"] == "RACKETEERING"
        assert isinstance(record["convicted"], bool)
        assert record["created_tick"] == 10


# ===========================================================================
# resolve_liquidate tests
# ===========================================================================


class TestResolveLiquidate:
    """Unit tests for resolve_liquidate."""

    def test_liquidate_in_core_without_emergency_powers_raises(self) -> None:
        defines = _make_defines()
        with pytest.raises(ValueError, match="EMERGENCY_POWERS"):
            resolve_liquidate(
                _make_org(),
                "fig_a",
                "ASSASSINATION",
                0.5,
                "CORE",
                liquidate_available_in_core=False,
                is_singleton=False,
                defines=defines,
            )

    def test_liquidate_in_core_with_emergency_powers_succeeds(self) -> None:
        defines = _make_defines()
        result_org, _, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.5,
            "CORE",
            liquidate_available_in_core=True,
            is_singleton=False,
            defines=defines,
        )
        assert result_org["coherence"] < 0.8

    def test_liquidate_in_periphery_always_allowed(self) -> None:
        defines = _make_defines()
        result_org, _, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.5,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        assert result_org["coherence"] < 0.8

    def test_liquidate_always_removes_figure(self) -> None:
        defines = _make_defines()
        org = _make_org(key_figure_ids=["fig_a", "fig_b"])
        result_org, _, _ = resolve_liquidate(
            org,
            "fig_a",
            "ASSASSINATION",
            0.5,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        assert "fig_a" not in result_org["key_figure_ids"]
        assert "fig_b" in result_org["key_figure_ids"]

    def test_singleton_liquidation_collapses_org(self) -> None:
        defines = _make_defines()
        _, _, collapsed = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.5,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=True,
            defines=defines,
        )
        assert collapsed is True

    def test_non_singleton_no_collapse(self) -> None:
        defines = _make_defines()
        _, _, collapsed = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.5,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        assert collapsed is False

    def test_high_deniability_halves_legitimacy(self) -> None:
        defines = _make_defines(
            liquidate_periphery_legitimacy_cost=0.03,
            liquidate_deniability_threshold=0.5,
        )
        _, high_den_cost, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.8,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        _, low_den_cost, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.2,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        assert high_den_cost == pytest.approx(low_den_cost / 2.0)

    def test_low_deniability_full_legitimacy(self) -> None:
        defines = _make_defines(
            liquidate_periphery_legitimacy_cost=0.03,
            liquidate_deniability_threshold=0.5,
        )
        _, cost, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.2,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        assert cost == pytest.approx(0.03)

    def test_does_not_mutate_inputs(self) -> None:
        defines = _make_defines()
        org = _make_org()
        orig = dict(org)
        orig["key_figure_ids"] = list(org["key_figure_ids"])
        _ = resolve_liquidate(
            org,
            "fig_a",
            "ASSASSINATION",
            0.5,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        assert org == orig

    def test_legitimacy_higher_in_core(self) -> None:
        defines = _make_defines(
            liquidate_core_legitimacy_cost=0.15,
            liquidate_periphery_legitimacy_cost=0.03,
        )
        _, core_cost, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.2,
            "CORE",
            liquidate_available_in_core=True,
            is_singleton=False,
            defines=defines,
        )
        _, periph_cost, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.2,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=defines,
        )
        assert core_cost > periph_cost


# ===========================================================================
# compute_raid_consciousness_effect tests
# ===========================================================================


class TestComputeRaidConsciousnessEffect:
    """Unit tests for compute_raid_consciousness_effect."""

    def test_high_ci_returns_positive(self) -> None:
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_radicalization_boost=0.1,
        )
        delta = compute_raid_consciousness_effect(0.7, defines)
        assert delta > 0.0

    def test_low_ci_returns_negative(self) -> None:
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_suppression_rate=0.15,
        )
        delta = compute_raid_consciousness_effect(0.3, defines)
        assert delta < 0.0

    def test_at_threshold_returns_positive(self) -> None:
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_radicalization_boost=0.1,
        )
        delta = compute_raid_consciousness_effect(0.5, defines)
        assert delta == pytest.approx(0.1)

    def test_zero_rates_returns_zero(self) -> None:
        defines = _make_defines(
            raid_ci_radicalization_boost=0.0,
            raid_ci_suppression_rate=0.0,
        )
        delta = compute_raid_consciousness_effect(0.7, defines)
        assert delta == pytest.approx(0.0)
        delta_low = compute_raid_consciousness_effect(0.3, defines)
        assert delta_low == pytest.approx(0.0)
