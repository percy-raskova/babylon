"""Unit tests for territory effects (Feature 039 Phase 6, US4).

Tests all territory effect calculations: INVEST, NEGLECT, DISPLACE,
STRATEGIC_WITHDRAWAL, SCORCHED_EARTH, heat accumulation, and
PROPAGANDIZE consciousness resistance.

See Also:
    ``specs/039-state-apparatus-ai/contracts/territory-effects.md``: TE-01 through TE-07.
    ``specs/039-state-apparatus-ai/tasks.md``: T057-T064, T083.
    :mod:`babylon.ooda.state_ai.territory_effects`: Implementation under test.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.territory_effects import (
    assess_territory_threat,
    check_recruit_effectiveness,
    compute_heat_accumulation,
    compute_heat_decay,
    compute_propagandize_effect,
    compute_scorched_earth_legitimacy,
    resolve_displace,
    resolve_eviction_cascade,
    resolve_invest,
    resolve_neglect,
    resolve_scorched_earth,
    resolve_strategic_withdrawal,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    """Build StateApparatusAIDefines with optional overrides."""
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_territory(**overrides: Any) -> dict[str, Any]:
    """Create a baseline territory dict with sensible defaults."""
    defaults: dict[str, Any] = {
        "property_value_proxy": 1.0,
        "infrastructure_quality": 0.8,
        "population": 1000,
        "collective_identity": 0.6,
        "community_infrastructure_quality": 0.5,
        "rent_level": 0.3,
        "state_investment": 50.0,
        "heat": 0.0,
        "territory_type": "PERIPHERY",
        "v_reproduction": 0.5,
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# resolve_invest tests
# ===========================================================================


class TestResolveInvest:
    """Unit tests for resolve_invest (TE-01)."""

    def test_invest_increases_property_value_proxy(self) -> None:
        """INVEST adds develop_infrastructure_boost to property_value_proxy."""
        defines = _make_defines()
        territory = _make_territory(property_value_proxy=1.0)

        result = resolve_invest(territory, defines)

        expected = 1.0 + defines.develop_infrastructure_boost
        assert result["property_value_proxy"] == pytest.approx(expected), (
            f"Expected {expected}, got {result['property_value_proxy']}"
        )

    def test_invest_does_not_mutate_input(self) -> None:
        """resolve_invest returns a new dict; original is unchanged."""
        defines = _make_defines()
        territory = _make_territory(property_value_proxy=1.0)
        original_pvp = territory["property_value_proxy"]

        _ = resolve_invest(territory, defines)

        assert territory["property_value_proxy"] == original_pvp, (
            "Original territory should not be mutated"
        )

    def test_invest_from_zero_baseline(self) -> None:
        """INVEST on zero property_value_proxy starts from zero."""
        defines = _make_defines()
        territory = _make_territory(property_value_proxy=0.0, rent_level=0.0)

        result = resolve_invest(territory, defines)

        assert result["property_value_proxy"] == pytest.approx(defines.develop_infrastructure_boost)
        # rent_level should seed from zero
        assert result["rent_level"] > 0.0

    def test_invest_increases_rent_level(self) -> None:
        """INVEST raises rent_level proportionally."""
        defines = _make_defines()
        territory = _make_territory(property_value_proxy=1.0, rent_level=0.3)

        result = resolve_invest(territory, defines)

        assert result["rent_level"] > 0.3

    def test_invest_preserves_other_fields(self) -> None:
        """INVEST does not modify population, infrastructure_quality, etc."""
        defines = _make_defines()
        territory = _make_territory()

        result = resolve_invest(territory, defines)

        assert result["population"] == territory["population"]
        assert result["infrastructure_quality"] == territory["infrastructure_quality"]
        assert result["collective_identity"] == territory["collective_identity"]

    def test_invest_iterated_monotonic(self) -> None:
        """Iterated INVEST never decreases property_value_proxy."""
        defines = _make_defines()
        territory = _make_territory()
        prev_pvp: float = territory["property_value_proxy"]

        max_ticks: int = 20
        for _tick in range(max_ticks):
            territory = resolve_invest(territory, defines)
            assert territory["property_value_proxy"] >= prev_pvp
            prev_pvp = territory["property_value_proxy"]

    def test_invest_custom_delta(self) -> None:
        """Custom develop_infrastructure_boost is respected."""
        defines = _make_defines(develop_infrastructure_boost=0.25)
        territory = _make_territory(property_value_proxy=2.0)

        result = resolve_invest(territory, defines)

        assert result["property_value_proxy"] == pytest.approx(2.25)


# ===========================================================================
# resolve_neglect tests
# ===========================================================================


class TestResolveNeglect:
    """Unit tests for resolve_neglect (TE-02)."""

    def test_neglect_applies_exponential_decay(self) -> None:
        """NEGLECT multiplies quality by (1 - decay_rate)."""
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.8)

        result = resolve_neglect(territory, defines)

        expected = 0.8 * (1.0 - defines.neglect_infrastructure_decay)
        assert result["infrastructure_quality"] == pytest.approx(expected)

    def test_neglect_does_not_mutate_input(self) -> None:
        """resolve_neglect returns a new dict; original is unchanged."""
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.8)

        _ = resolve_neglect(territory, defines)

        assert territory["infrastructure_quality"] == 0.8

    def test_neglect_respects_floor(self) -> None:
        """NEGLECT cannot reduce quality below neglect_quality_floor."""
        defines = _make_defines(neglect_quality_floor=0.1)
        # Start at the floor
        territory = _make_territory(infrastructure_quality=0.1)

        result = resolve_neglect(territory, defines)

        assert result["infrastructure_quality"] >= 0.1

    def test_neglect_floor_enforced_at_low_quality(self) -> None:
        """NEGLECT on quality slightly above floor stays at floor."""
        defines = _make_defines(
            neglect_infrastructure_decay=0.5,  # Aggressive decay
            neglect_quality_floor=0.1,
        )
        territory = _make_territory(infrastructure_quality=0.15)

        result = resolve_neglect(territory, defines)

        # 0.15 * 0.5 = 0.075, which is below floor 0.1
        assert result["infrastructure_quality"] == 0.1

    def test_neglect_default_infrastructure_quality(self) -> None:
        """NEGLECT with missing field uses default 1.0."""
        defines = _make_defines()
        territory: dict[str, Any] = {"territory_type": "PERIPHERY"}

        result = resolve_neglect(territory, defines)

        expected = 1.0 * (1.0 - defines.neglect_infrastructure_decay)
        assert result["infrastructure_quality"] == pytest.approx(expected)

    def test_neglect_preserves_other_fields(self) -> None:
        """NEGLECT does not modify population, property_value_proxy, etc."""
        defines = _make_defines()
        territory = _make_territory()

        result = resolve_neglect(territory, defines)

        assert result["population"] == territory["population"]
        assert result["property_value_proxy"] == territory["property_value_proxy"]

    def test_neglect_custom_decay_rate(self) -> None:
        """Custom neglect_infrastructure_decay is respected."""
        defines = _make_defines(neglect_infrastructure_decay=0.2)
        territory = _make_territory(infrastructure_quality=1.0)

        result = resolve_neglect(territory, defines)

        assert result["infrastructure_quality"] == pytest.approx(0.8)


# ===========================================================================
# resolve_displace tests
# ===========================================================================


class TestResolveDisplace:
    """Unit tests for resolve_displace (TE-03)."""

    def test_displace_removes_correct_population(self) -> None:
        """DISPLACE removes floor(population * fraction)."""
        defines = _make_defines(displace_population_fraction=0.1)
        territory = _make_territory(population=1000)

        result, displaced = resolve_displace(territory, defines)

        assert displaced == 100
        assert result["population"] == 900

    def test_displace_fractional_population_floors(self) -> None:
        """DISPLACE with non-integer result uses floor."""
        defines = _make_defines(displace_population_fraction=0.1)
        territory = _make_territory(population=55)

        result, displaced = resolve_displace(territory, defines)

        assert displaced == 5  # floor(55 * 0.1) = floor(5.5) = 5
        assert result["population"] == 50

    def test_displace_reduces_collective_identity(self) -> None:
        """DISPLACE reduces CI by displace_ci_reduction."""
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.6)

        result, _ = resolve_displace(territory, defines)

        expected = max(0.0, 0.6 - defines.displace_ci_reduction)
        assert result["collective_identity"] == pytest.approx(expected)

    def test_displace_ci_cannot_go_negative(self) -> None:
        """DISPLACE does not reduce CI below 0.0."""
        defines = _make_defines(displace_ci_reduction=0.5)
        territory = _make_territory(collective_identity=0.1)

        result, _ = resolve_displace(territory, defines)

        assert result["collective_identity"] == 0.0

    def test_displace_reduces_community_infrastructure(self) -> None:
        """DISPLACE reduces community_infrastructure_quality."""
        defines = _make_defines()
        territory = _make_territory(community_infrastructure_quality=0.5)

        result, _ = resolve_displace(territory, defines)

        expected = max(0.0, 0.5 - defines.displace_community_infra_reduction)
        assert result["community_infrastructure_quality"] == pytest.approx(expected)

    def test_displace_community_infra_cannot_go_negative(self) -> None:
        """DISPLACE does not reduce community_infrastructure_quality below 0."""
        defines = _make_defines(displace_community_infra_reduction=0.8)
        territory = _make_territory(community_infrastructure_quality=0.2)

        result, _ = resolve_displace(territory, defines)

        assert result["community_infrastructure_quality"] == 0.0

    def test_displace_does_not_mutate_input(self) -> None:
        """resolve_displace returns a new dict."""
        defines = _make_defines()
        territory = _make_territory()
        original_pop = territory["population"]

        _ = resolve_displace(territory, defines)

        assert territory["population"] == original_pop

    def test_displace_zero_population(self) -> None:
        """DISPLACE on empty territory produces 0 displaced."""
        defines = _make_defines()
        territory = _make_territory(population=0)

        result, displaced = resolve_displace(territory, defines)

        assert displaced == 0
        assert result["population"] == 0

    def test_displace_custom_fraction(self) -> None:
        """Custom displace_population_fraction is respected."""
        defines = _make_defines(displace_population_fraction=0.5)
        territory = _make_territory(population=200)

        result, displaced = resolve_displace(territory, defines)

        assert displaced == 100
        assert result["population"] == 100


# ===========================================================================
# resolve_strategic_withdrawal tests
# ===========================================================================


class TestResolveStrategicWithdrawal:
    """Unit tests for resolve_strategic_withdrawal (TE-04)."""

    def test_withdrawal_zeros_state_investment(self) -> None:
        """STRATEGIC_WITHDRAWAL sets state_investment to 0."""
        defines = _make_defines()
        territory = _make_territory(state_investment=75.0)

        result, _ = resolve_strategic_withdrawal(territory, defines)

        assert result["state_investment"] == 0.0

    def test_withdrawal_accelerated_decay(self) -> None:
        """STRATEGIC_WITHDRAWAL degrades infrastructure faster than NEGLECT."""
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.7)

        result, _ = resolve_strategic_withdrawal(territory, defines)

        # Accelerated: 0.7 * (1.0 - 0.05 * 2.0) = 0.7 * 0.9 = 0.63
        expected_decay_rate = (
            defines.neglect_infrastructure_decay * defines.strategic_withdrawal_decay_multiplier
        )
        expected = 0.7 * (1.0 - expected_decay_rate)
        assert result["infrastructure_quality"] == pytest.approx(expected)

    def test_withdrawal_accelerated_decay_respects_floor(self) -> None:
        """Accelerated decay cannot push below neglect_quality_floor."""
        defines = _make_defines(
            neglect_infrastructure_decay=0.4,
            strategic_withdrawal_decay_multiplier=3.0,
            neglect_quality_floor=0.1,
        )
        territory = _make_territory(infrastructure_quality=0.2)

        result, _ = resolve_strategic_withdrawal(territory, defines)

        # 0.4 * 3.0 = 1.2, clamped to 1.0 -> quality = 0.2 * 0.0 = 0.0 -> floor 0.1
        assert result["infrastructure_quality"] >= defines.neglect_quality_floor

    def test_withdrawal_asset_extraction_recovers_budget(self) -> None:
        """asset_extraction=True returns fraction of state_investment."""
        defines = _make_defines(strategic_withdrawal_asset_recovery=0.5)
        territory = _make_territory(state_investment=100.0)

        _, budget = resolve_strategic_withdrawal(territory, defines, asset_extraction=True)

        assert budget == pytest.approx(50.0)

    def test_withdrawal_no_extraction_returns_zero(self) -> None:
        """Default (no asset_extraction) returns 0.0 budget."""
        defines = _make_defines()
        territory = _make_territory(state_investment=100.0)

        _, budget = resolve_strategic_withdrawal(territory, defines)

        assert budget == 0.0

    def test_withdrawal_does_not_mutate_input(self) -> None:
        """resolve_strategic_withdrawal returns a new dict."""
        defines = _make_defines()
        territory = _make_territory(state_investment=50.0)

        _ = resolve_strategic_withdrawal(territory, defines)

        assert territory["state_investment"] == 50.0

    def test_withdrawal_zero_investment_no_recovery(self) -> None:
        """No investment means no budget recovery even with asset_extraction."""
        defines = _make_defines()
        territory = _make_territory(state_investment=0.0)

        _, budget = resolve_strategic_withdrawal(territory, defines, asset_extraction=True)

        assert budget == 0.0

    def test_withdrawal_decay_multiplier_effect(self) -> None:
        """Higher multiplier means faster degradation."""
        defines_fast = _make_defines(strategic_withdrawal_decay_multiplier=5.0)
        defines_slow = _make_defines(strategic_withdrawal_decay_multiplier=1.5)
        territory_fast = _make_territory(infrastructure_quality=0.8)
        territory_slow = _make_territory(infrastructure_quality=0.8)

        result_fast, _ = resolve_strategic_withdrawal(territory_fast, defines_fast)
        result_slow, _ = resolve_strategic_withdrawal(territory_slow, defines_slow)

        assert result_fast["infrastructure_quality"] < result_slow["infrastructure_quality"]


# ===========================================================================
# resolve_scorched_earth tests
# ===========================================================================


class TestResolveScorchedEarth:
    """Unit tests for resolve_scorched_earth (TE-05)."""

    def test_scorched_earth_sets_quality_to_floor(self) -> None:
        """SCORCHED_EARTH sets infrastructure_quality to neglect_quality_floor."""
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.9)

        result, _ = resolve_scorched_earth(territory, defines)

        assert result["infrastructure_quality"] == defines.neglect_quality_floor

    def test_scorched_earth_already_at_floor(self) -> None:
        """SCORCHED_EARTH on territory already at floor is idempotent."""
        defines = _make_defines()
        territory = _make_territory(
            infrastructure_quality=defines.neglect_quality_floor,
        )

        result, _ = resolve_scorched_earth(territory, defines)

        assert result["infrastructure_quality"] == defines.neglect_quality_floor

    def test_scorched_earth_destroys_community_infrastructure(self) -> None:
        """SCORCHED_EARTH sets community_infrastructure_quality to 0."""
        defines = _make_defines()
        territory = _make_territory(community_infrastructure_quality=0.8)

        result, _ = resolve_scorched_earth(territory, defines)

        assert result["community_infrastructure_quality"] == 0.0

    def test_scorched_earth_zeros_state_investment(self) -> None:
        """SCORCHED_EARTH sets state_investment to 0."""
        defines = _make_defines()
        territory = _make_territory(state_investment=100.0)

        result, _ = resolve_scorched_earth(territory, defines)

        assert result["state_investment"] == 0.0

    def test_scorched_earth_core_legitimacy_cost(self) -> None:
        """CORE territory has the defined core legitimacy cost."""
        defines = _make_defines()
        territory = _make_territory(territory_type="CORE")

        _, cost = resolve_scorched_earth(territory, defines)

        assert cost == defines.scorched_earth_legitimacy_core

    def test_scorched_earth_periphery_legitimacy_cost(self) -> None:
        """PERIPHERY territory has the defined periphery legitimacy cost."""
        defines = _make_defines()
        territory = _make_territory(territory_type="PERIPHERY")

        _, cost = resolve_scorched_earth(territory, defines)

        assert cost == defines.scorched_earth_legitimacy_periphery

    def test_scorched_earth_does_not_mutate_input(self) -> None:
        """resolve_scorched_earth returns a new dict."""
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.9)

        _ = resolve_scorched_earth(territory, defines)

        assert territory["infrastructure_quality"] == 0.9

    def test_scorched_earth_unknown_territory_type_defaults_periphery(self) -> None:
        """Unknown territory_type defaults to PERIPHERY cost."""
        defines = _make_defines()
        territory = _make_territory(territory_type="UNKNOWN")

        _, cost = resolve_scorched_earth(territory, defines)

        assert cost == defines.scorched_earth_legitimacy_periphery


# ===========================================================================
# compute_heat_accumulation tests
# ===========================================================================


class TestComputeHeatAccumulation:
    """Unit tests for compute_heat_accumulation (TE-06)."""

    def test_high_profile_heat_rate(self) -> None:
        """One HIGH_PROFILE adds high_profile_heat_rate to heat."""
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.0,
            high_profile_count=1,
            low_profile_count=0,
            defines=defines,
        )

        assert heat == pytest.approx(defines.high_profile_heat_rate)

    def test_low_profile_heat_rate(self) -> None:
        """One LOW_PROFILE adds low_profile_heat_rate to heat."""
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.0,
            high_profile_count=0,
            low_profile_count=1,
            defines=defines,
        )

        assert heat == pytest.approx(defines.low_profile_heat_rate)

    def test_mixed_profiles_additive(self) -> None:
        """Heat from multiple profiles is additive."""
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.0,
            high_profile_count=2,
            low_profile_count=3,
            defines=defines,
        )

        expected = 2 * defines.high_profile_heat_rate + 3 * defines.low_profile_heat_rate
        assert heat == pytest.approx(expected)

    def test_heat_capped_at_one(self) -> None:
        """Heat is bounded to 1.0."""
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.95,
            high_profile_count=10,
            low_profile_count=0,
            defines=defines,
        )

        assert heat == 1.0

    def test_heat_floor_at_zero(self) -> None:
        """Heat does not go below 0.0 even with zero counts."""
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.0,
            high_profile_count=0,
            low_profile_count=0,
            defines=defines,
        )

        assert heat == 0.0

    def test_heat_additive_with_existing(self) -> None:
        """Heat adds to current_heat."""
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.3,
            high_profile_count=1,
            low_profile_count=0,
            defines=defines,
        )

        assert heat == pytest.approx(0.3 + defines.high_profile_heat_rate)

    def test_heat_zero_counts_returns_current(self) -> None:
        """Zero counts leave heat unchanged."""
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.5,
            high_profile_count=0,
            low_profile_count=0,
            defines=defines,
        )

        assert heat == pytest.approx(0.5)


# ===========================================================================
# compute_propagandize_effect tests
# ===========================================================================


class TestComputePropagandizeEffect:
    """Unit tests for compute_propagandize_effect (TE-07)."""

    def test_zero_ci_no_reduction_possible(self) -> None:
        """CI=0.0 means no resistance but also nothing to reduce."""
        defines = _make_defines()

        effect = compute_propagandize_effect(
            collective_identity=0.0,
            base_delta=0.3,
            defines=defines,
        )

        # CI=0.0 -> effect is bounded to current CI, so zero
        assert effect == pytest.approx(0.0)

    def test_low_ci_full_effective_delta(self) -> None:
        """Very low CI=0.01 with no resistance gets near-full delta applied."""
        defines = _make_defines(consciousness_resistance_factor=0.0)

        effect = compute_propagandize_effect(
            collective_identity=0.5,
            base_delta=0.3,
            defines=defines,
        )

        # resistance_factor=0 means zero resistance -> full delta
        assert effect == pytest.approx(0.3)

    def test_high_ci_reduced_effect(self) -> None:
        """High CI reduces PROPAGANDIZE effect."""
        defines = _make_defines(consciousness_resistance_factor=0.5)

        effect = compute_propagandize_effect(
            collective_identity=0.8,
            base_delta=0.3,
            defines=defines,
        )

        # resistance = 0.8 * 0.5 = 0.4, effective = 0.3 * (1 - 0.4) = 0.3 * 0.6 = 0.18
        assert effect == pytest.approx(0.18)

    def test_maximum_resistance(self) -> None:
        """CI=1.0 with max resistance_factor=1.0 -> zero effect."""
        defines = _make_defines(consciousness_resistance_factor=1.0)

        effect = compute_propagandize_effect(
            collective_identity=1.0,
            base_delta=0.5,
            defines=defines,
        )

        assert effect == pytest.approx(0.0)

    def test_effect_bounded_by_current_ci(self) -> None:
        """Effect cannot exceed current CI (would make CI negative)."""
        defines = _make_defines()

        effect = compute_propagandize_effect(
            collective_identity=0.05,
            base_delta=0.5,
            defines=defines,
        )

        assert effect <= 0.05

    def test_negative_base_delta_clamped_to_zero(self) -> None:
        """Negative base_delta produces zero effect (propagandize cannot increase CI)."""
        defines = _make_defines()

        effect = compute_propagandize_effect(
            collective_identity=0.5,
            base_delta=-0.1,
            defines=defines,
        )

        assert effect == 0.0

    def test_effect_non_negative(self) -> None:
        """Effect is always >= 0."""
        defines = _make_defines()

        effect = compute_propagandize_effect(
            collective_identity=0.5,
            base_delta=0.3,
            defines=defines,
        )

        assert effect >= 0.0


# ===========================================================================
# compute_scorched_earth_legitimacy tests
# ===========================================================================


class TestComputeScorchedEarthLegitimacy:
    """Unit tests for compute_scorched_earth_legitimacy."""

    def test_core_returns_core_cost(self) -> None:
        """CORE territory returns scorched_earth_legitimacy_core."""
        defines = _make_defines()

        cost = compute_scorched_earth_legitimacy("CORE", defines)

        assert cost == defines.scorched_earth_legitimacy_core

    def test_periphery_returns_periphery_cost(self) -> None:
        """PERIPHERY territory returns scorched_earth_legitimacy_periphery."""
        defines = _make_defines()

        cost = compute_scorched_earth_legitimacy("PERIPHERY", defines)

        assert cost == defines.scorched_earth_legitimacy_periphery

    def test_core_costs_more_than_periphery(self) -> None:
        """CORE always costs more than PERIPHERY (colonial asymmetry)."""
        defines = _make_defines()

        cost_core = compute_scorched_earth_legitimacy("CORE", defines)
        cost_periphery = compute_scorched_earth_legitimacy("PERIPHERY", defines)

        assert cost_core > cost_periphery

    def test_unknown_type_defaults_to_periphery(self) -> None:
        """Unknown territory type defaults to periphery cost."""
        defines = _make_defines()

        cost = compute_scorched_earth_legitimacy("UNKNOWN_TYPE", defines)

        assert cost == defines.scorched_earth_legitimacy_periphery

    def test_custom_costs(self) -> None:
        """Custom legitimacy costs are respected."""
        defines = _make_defines(
            scorched_earth_legitimacy_core=0.5,
            scorched_earth_legitimacy_periphery=0.01,
        )

        assert compute_scorched_earth_legitimacy("CORE", defines) == pytest.approx(0.5)
        assert compute_scorched_earth_legitimacy("PERIPHERY", defines) == pytest.approx(0.01)


# ===========================================================================
# compute_heat_decay tests
# ===========================================================================


class TestComputeHeatDecay:
    """Unit tests for compute_heat_decay."""

    def test_no_presence_decays_heat(self) -> None:
        defines = _make_defines()
        result = compute_heat_decay(0.5, has_presence=False, defines=defines)
        assert result == pytest.approx(0.5 - defines.heat_decay_rate)

    def test_with_presence_no_decay(self) -> None:
        defines = _make_defines()
        result = compute_heat_decay(0.5, has_presence=True, defines=defines)
        assert result == pytest.approx(0.5)

    def test_decay_bounded_at_zero(self) -> None:
        defines = _make_defines()
        result = compute_heat_decay(0.01, has_presence=False, defines=defines)
        assert result == 0.0

    def test_custom_decay_rate(self) -> None:
        defines = _make_defines(heat_decay_rate=0.2)
        result = compute_heat_decay(0.5, has_presence=False, defines=defines)
        assert result == pytest.approx(0.3)

    def test_zero_heat_stays_zero(self) -> None:
        defines = _make_defines()
        result = compute_heat_decay(0.0, has_presence=False, defines=defines)
        assert result == 0.0

    def test_full_heat_decays(self) -> None:
        defines = _make_defines()
        result = compute_heat_decay(1.0, has_presence=False, defines=defines)
        assert result == pytest.approx(1.0 - defines.heat_decay_rate)


# ===========================================================================
# check_recruit_effectiveness tests
# ===========================================================================


class TestCheckRecruitEffectiveness:
    """Unit tests for check_recruit_effectiveness."""

    def test_with_presence_full_effectiveness(self) -> None:
        defines = _make_defines()
        result = check_recruit_effectiveness(True, 0.8, defines)
        assert result == pytest.approx(0.8)

    def test_no_presence_severely_penalized(self) -> None:
        defines = _make_defines(recruit_no_presence_penalty=0.9)
        result = check_recruit_effectiveness(False, 1.0, defines)
        assert result == pytest.approx(0.1)

    def test_zero_base_effectiveness_unchanged(self) -> None:
        defines = _make_defines()
        result = check_recruit_effectiveness(False, 0.0, defines)
        assert result == pytest.approx(0.0)

    def test_no_penalty_configured(self) -> None:
        defines = _make_defines(recruit_no_presence_penalty=0.0)
        result = check_recruit_effectiveness(False, 0.5, defines)
        assert result == pytest.approx(0.5)

    def test_full_penalty_configured(self) -> None:
        defines = _make_defines(recruit_no_presence_penalty=1.0)
        result = check_recruit_effectiveness(False, 1.0, defines)
        assert result == pytest.approx(0.0)


# ===========================================================================
# assess_territory_threat tests
# ===========================================================================


class TestAssessTerritoryThreat:
    """Unit tests for assess_territory_threat."""

    def test_zero_ci_zero_heat(self) -> None:
        defines = _make_defines()
        result = assess_territory_threat(0.0, 0.0, defines)
        assert result == pytest.approx(0.0)

    def test_high_ci_high_heat(self) -> None:
        defines = _make_defines()
        result = assess_territory_threat(0.8, 0.9, defines)
        assert result > 0.5

    def test_heat_above_escalation_gets_bonus(self) -> None:
        defines = _make_defines(heat_escalation_threshold=0.6)
        below = assess_territory_threat(0.5, 0.5, defines)
        above = assess_territory_threat(0.5, 0.7, defines)
        # Same CI, heat above threshold should produce higher threat
        assert above > below

    def test_bounded_zero_to_one(self) -> None:
        defines = _make_defines()
        result = assess_territory_threat(1.0, 1.0, defines)
        assert 0.0 <= result <= 1.0

    def test_ci_only_contributes_half(self) -> None:
        defines = _make_defines()
        result = assess_territory_threat(1.0, 0.0, defines)
        assert result == pytest.approx(0.5)

    def test_heat_only_contributes_half(self) -> None:
        defines = _make_defines()
        result = assess_territory_threat(0.0, 1.0, defines)
        # Heat=1.0 > threshold=0.6, so bonus applies too
        assert result >= 0.5


# ===========================================================================
# resolve_eviction_cascade tests
# ===========================================================================


class TestResolveEvictionCascade:
    """Unit tests for resolve_eviction_cascade."""

    def test_population_distributed_evenly(self) -> None:
        defines = _make_defines()
        source = _make_territory(population=0)
        neighbors = [_make_territory(population=100), _make_territory(population=100)]
        _, updated = resolve_eviction_cascade(source, neighbors, 100, defines)
        assert updated[0]["population"] == 150
        assert updated[1]["population"] == 150

    def test_remainder_goes_to_first_neighbors(self) -> None:
        defines = _make_defines()
        source = _make_territory(population=0)
        neighbors = [
            _make_territory(population=0),
            _make_territory(population=0),
            _make_territory(population=0),
        ]
        _, updated = resolve_eviction_cascade(source, neighbors, 10, defines)
        # 10 / 3 = 3 each, remainder 1 to first neighbor
        assert updated[0]["population"] == 4
        assert updated[1]["population"] == 3
        assert updated[2]["population"] == 3

    def test_neighbor_ci_reduced(self) -> None:
        defines = _make_defines(eviction_scatter_ci_loss=0.1)
        source = _make_territory()
        neighbors = [_make_territory(collective_identity=0.5)]
        _, updated = resolve_eviction_cascade(source, neighbors, 50, defines)
        assert updated[0]["collective_identity"] == pytest.approx(0.4)

    def test_ci_bounded_at_zero(self) -> None:
        defines = _make_defines(eviction_scatter_ci_loss=0.5)
        source = _make_territory()
        neighbors = [_make_territory(collective_identity=0.1)]
        _, updated = resolve_eviction_cascade(source, neighbors, 50, defines)
        assert updated[0]["collective_identity"] == 0.0

    def test_no_neighbors_returns_empty(self) -> None:
        defines = _make_defines()
        source = _make_territory()
        updated_source, updated_neighbors = resolve_eviction_cascade(source, [], 100, defines)
        assert len(updated_neighbors) == 0

    def test_zero_displaced_returns_empty_neighbors(self) -> None:
        defines = _make_defines()
        source = _make_territory()
        neighbors = [_make_territory()]
        _, updated_neighbors = resolve_eviction_cascade(source, neighbors, 0, defines)
        assert len(updated_neighbors) == 0

    def test_source_community_infra_reduced(self) -> None:
        defines = _make_defines(displace_community_infra_reduction=0.3)
        source = _make_territory(community_infrastructure_quality=0.5)
        neighbors = [_make_territory()]
        updated_source, _ = resolve_eviction_cascade(source, neighbors, 50, defines)
        assert updated_source["community_infrastructure_quality"] == pytest.approx(0.2)

    def test_does_not_mutate_inputs(self) -> None:
        defines = _make_defines()
        source = _make_territory(population=100)
        neighbor = _make_territory(population=200)
        original_pop = neighbor["population"]
        _ = resolve_eviction_cascade(source, [neighbor], 50, defines)
        assert neighbor["population"] == original_pop
