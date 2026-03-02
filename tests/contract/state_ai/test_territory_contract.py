"""Contract tests for territory effects (Feature 039 Phase 6).

Behavioral contracts BC-TE-001 through BC-TE-007 from
``specs/039-state-apparatus-ai/contracts/territory-effects.md``.

These tests validate INVEST, NEGLECT, DISPLACE, STRATEGIC_WITHDRAWAL,
SCORCHED_EARTH territory mutations and PROPAGANDIZE consciousness
resistance. All functions are pure (dict in, dict out) and use
StateApparatusAIDefines for thresholds.

See Also:
    :mod:`babylon.ooda.state_ai.territory_effects`: Implementation.
    ``specs/039-state-apparatus-ai/contracts/territory-effects.md``: Contract definitions.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.territory_effects import (
    compute_heat_accumulation,
    compute_propagandize_effect,
    resolve_displace,
    resolve_invest,
    resolve_neglect,
    resolve_scorched_earth,
    resolve_strategic_withdrawal,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NORMALIZATION_TOLERANCE: float = 1e-9


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    """Build StateApparatusAIDefines with optional overrides."""
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_territory(**overrides: Any) -> dict[str, Any]:
    """Create a baseline territory dict with sensible defaults.

    Args:
        **overrides: Fields to override on the default territory.

    Returns:
        Dict with standard territory attributes.
    """
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
# BC-TE-001: INVEST Increases Territory Economic Value
# ===========================================================================


class TestInvestIncreasesValue:
    """BC-TE-001: INVEST increases property_value_proxy.

    Reference: FR-E08, SC-008.
    Spec: territory-effects.md BC-TE-001.
    """

    def test_invest_eight_ticks_increases_value(self) -> None:
        """8 ticks of INVEST raises property_value_proxy by at least 8 * delta.

        Contract: property_value_proxy on T001 has increased by at least
        8 * defines.develop_infrastructure_boost from baseline.
        """
        defines = _make_defines()
        territory = _make_territory()
        baseline_pvp: float = territory["property_value_proxy"]

        max_ticks: int = 8
        for _tick in range(max_ticks):
            territory = resolve_invest(territory, defines)

        expected_min_increase = max_ticks * defines.develop_infrastructure_boost
        actual_increase = territory["property_value_proxy"] - baseline_pvp

        assert actual_increase >= expected_min_increase - _NORMALIZATION_TOLERANCE, (
            f"After {max_ticks} ticks of INVEST, property_value_proxy increased by "
            f"{actual_increase:.4f}, expected >= {expected_min_increase:.4f}"
        )

    def test_invest_monotonically_non_decreasing(self) -> None:
        """property_value_proxy is non-decreasing while INVEST actions continue.

        Invariant from contract: INVEST never decreases economic value.
        """
        defines = _make_defines()
        territory = _make_territory()
        prev_pvp: float = territory["property_value_proxy"]

        max_ticks: int = 12
        for tick in range(max_ticks):
            territory = resolve_invest(territory, defines)
            current_pvp: float = territory["property_value_proxy"]
            assert current_pvp >= prev_pvp, (
                f"Tick {tick}: property_value_proxy decreased from {prev_pvp} to "
                f"{current_pvp} — INVEST must be monotonically non-decreasing"
            )
            prev_pvp = current_pvp

    def test_invest_increases_rent_level(self) -> None:
        """INVEST increases rent_level proportionally to property value change.

        Contract: rent_level has increased proportionally to property_value_proxy.
        """
        defines = _make_defines()
        territory = _make_territory()
        baseline_rent: float = territory["rent_level"]

        max_ticks: int = 4
        for _tick in range(max_ticks):
            territory = resolve_invest(territory, defines)

        assert territory["rent_level"] > baseline_rent, (
            f"rent_level should increase after {max_ticks} INVEST ticks: "
            f"baseline={baseline_rent}, final={territory['rent_level']}"
        )


# ===========================================================================
# BC-TE-002: NEGLECT Degrades Territory Infrastructure
# ===========================================================================


class TestNeglectDecaysInfrastructure:
    """BC-TE-002: NEGLECT exponential decay with floor.

    Reference: FR-E08, SC-008.
    Spec: territory-effects.md BC-TE-002.
    """

    def test_neglect_twelve_ticks_follows_decay_curve(self) -> None:
        """12 ticks of NEGLECT decays infrastructure following exponential curve.

        Worked Example from contract: With decay_rate=0.05, quality_floor=0.1:
        After 12 ticks: 0.8 * (0.95)^12 = 0.431
        """
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.8)

        max_ticks: int = 12
        for _tick in range(max_ticks):
            territory = resolve_neglect(territory, defines)

        expected = 0.8 * (1.0 - defines.neglect_infrastructure_decay) ** max_ticks
        actual: float = territory["infrastructure_quality"]

        # Allow small floating point tolerance
        assert abs(actual - expected) < 0.001, (
            f"After {max_ticks} ticks of NEGLECT, infrastructure_quality={actual:.4f}, "
            f"expected ~{expected:.4f} (decay curve)"
        )

    def test_neglect_respects_quality_floor(self) -> None:
        """infrastructure_quality never falls below neglect_quality_floor.

        Invariant: infrastructure_quality >= defines.neglect_quality_floor at all times.
        """
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.8)

        # Apply many ticks — enough to approach the floor
        max_ticks: int = 100
        for tick in range(max_ticks):
            territory = resolve_neglect(territory, defines)
            quality: float = territory["infrastructure_quality"]
            assert quality >= defines.neglect_quality_floor, (
                f"Tick {tick}: infrastructure_quality={quality:.4f} dropped below "
                f"floor={defines.neglect_quality_floor}"
            )


# ===========================================================================
# BC-TE-003: DISPLACE Removes Population and Reduces Community
# ===========================================================================


class TestDisplaceRemovesPopulation:
    """BC-TE-003: DISPLACE removes population fraction.

    Reference: FR-E03, FR-E06, FR-E08.
    Spec: territory-effects.md BC-TE-003.
    """

    def test_displace_removes_population_fraction(self) -> None:
        """DISPLACE removes floor(population * displace_population_fraction).

        Contract: at least floor(1000 * fraction) displaced.
        """
        defines = _make_defines()
        territory = _make_territory(population=1000)

        result, displaced_count = resolve_displace(territory, defines)

        expected_displaced = int(1000 * defines.displace_population_fraction)
        assert displaced_count == expected_displaced, (
            f"Expected {expected_displaced} displaced, got {displaced_count}"
        )
        assert result["population"] == 1000 - expected_displaced, (
            f"Population should be {1000 - expected_displaced}, got {result['population']}"
        )

    def test_displace_reduces_collective_identity(self) -> None:
        """DISPLACE reduces collective_identity (consciousness disruption).

        Contract: collective_identity on affected community decreases.
        """
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.6)

        result, _ = resolve_displace(territory, defines)

        assert result["collective_identity"] < territory["collective_identity"], (
            f"collective_identity should decrease after DISPLACE: "
            f"before={territory['collective_identity']}, after={result['collective_identity']}"
        )

    def test_displace_empty_territory_no_displacement(self) -> None:
        """DISPLACE on empty territory produces zero displacement.

        Edge Case EC-003: population=0 -> displaced=0.
        """
        defines = _make_defines()
        territory = _make_territory(population=0)

        result, displaced_count = resolve_displace(territory, defines)

        assert displaced_count == 0, (
            f"Empty territory should produce 0 displaced, got {displaced_count}"
        )
        assert result["population"] == 0


# ===========================================================================
# BC-TE-004: STRATEGIC_WITHDRAWAL Hollows Territory
# ===========================================================================


class TestStrategicWithdrawalHollows:
    """BC-TE-004: STRATEGIC_WITHDRAWAL removes state presence.

    Reference: FR-E09, FR-B07.
    Spec: territory-effects.md BC-TE-004.
    """

    def test_strategic_withdrawal_zeros_state_investment(self) -> None:
        """STRATEGIC_WITHDRAWAL sets state_investment to 0.0.

        Contract: state_investment is set to 0.0 for T001.
        """
        defines = _make_defines()
        territory = _make_territory(state_investment=50.0)

        result, _ = resolve_strategic_withdrawal(territory, defines)

        assert result["state_investment"] == 0.0, (
            f"state_investment should be 0.0, got {result['state_investment']}"
        )

    def test_strategic_withdrawal_degrades_infrastructure(self) -> None:
        """STRATEGIC_WITHDRAWAL applies accelerated NEGLECT factor.

        Contract: infrastructure_quality degrades by accelerated factor
        (faster than standard NEGLECT decay).
        """
        defines = _make_defines()
        territory_sw = _make_territory(infrastructure_quality=0.7)
        territory_neglect = _make_territory(infrastructure_quality=0.7)

        result_sw, _ = resolve_strategic_withdrawal(territory_sw, defines)
        result_neglect = resolve_neglect(territory_neglect, defines)

        # Strategic withdrawal should degrade more than standard neglect
        assert result_sw["infrastructure_quality"] < result_neglect["infrastructure_quality"], (
            f"STRATEGIC_WITHDRAWAL ({result_sw['infrastructure_quality']:.4f}) should "
            f"degrade more than NEGLECT ({result_neglect['infrastructure_quality']:.4f})"
        )

    def test_strategic_withdrawal_asset_extraction_recovers_budget(self) -> None:
        """asset_extraction=True recovers a fraction of prior investment.

        Contract: state recovers a fraction of its prior investment as budget.
        """
        defines = _make_defines()
        initial_investment = 100.0
        territory = _make_territory(state_investment=initial_investment)

        _, budget_recovered = resolve_strategic_withdrawal(
            territory, defines, asset_extraction=True
        )

        expected = initial_investment * defines.strategic_withdrawal_asset_recovery
        assert abs(budget_recovered - expected) < _NORMALIZATION_TOLERANCE, (
            f"Budget recovered should be {expected:.2f}, got {budget_recovered:.2f}"
        )

    def test_strategic_withdrawal_no_extraction_recovers_nothing(self) -> None:
        """asset_extraction=False (default) recovers no budget."""
        defines = _make_defines()
        territory = _make_territory(state_investment=100.0)

        _, budget_recovered = resolve_strategic_withdrawal(
            territory, defines, asset_extraction=False
        )

        assert budget_recovered == 0.0, (
            f"No asset extraction should recover 0.0, got {budget_recovered}"
        )


# ===========================================================================
# BC-TE-005: SCORCHED_EARTH Destroys Infrastructure
# ===========================================================================


class TestScorchedEarthDestroys:
    """BC-TE-005: SCORCHED_EARTH destroys infrastructure.

    Reference: FR-E09, FR-B07.
    Spec: territory-effects.md BC-TE-005.
    """

    def test_scorched_earth_sets_quality_to_floor(self) -> None:
        """SCORCHED_EARTH sets infrastructure_quality to neglect_quality_floor.

        Contract: infrastructure_quality set to floor (immediate destruction).
        """
        defines = _make_defines()
        territory = _make_territory(infrastructure_quality=0.9)

        result, _ = resolve_scorched_earth(territory, defines)

        assert result["infrastructure_quality"] == defines.neglect_quality_floor, (
            f"infrastructure_quality should be {defines.neglect_quality_floor}, "
            f"got {result['infrastructure_quality']}"
        )

    def test_scorched_earth_core_higher_legitimacy_cost(self) -> None:
        """CORE territory has higher legitimacy cost than PERIPHERY.

        Contract: territory_type=CORE -> extreme legitimacy cost.
        """
        defines = _make_defines()
        territory_core = _make_territory(territory_type="CORE")
        territory_periphery = _make_territory(territory_type="PERIPHERY")

        _, cost_core = resolve_scorched_earth(territory_core, defines)
        _, cost_periphery = resolve_scorched_earth(territory_periphery, defines)

        assert cost_core > cost_periphery, (
            f"CORE cost ({cost_core}) should exceed PERIPHERY cost ({cost_periphery})"
        )

    def test_scorched_earth_periphery_lower_legitimacy_cost(self) -> None:
        """PERIPHERY territory has lower legitimacy cost.

        Contract: territory_type=PERIPHERY -> minimal legitimacy cost.
        Colonial asymmetry: peripheral destruction is cheaper.
        """
        defines = _make_defines()
        territory = _make_territory(territory_type="PERIPHERY")

        _, cost = resolve_scorched_earth(territory, defines)

        assert cost == defines.scorched_earth_legitimacy_periphery, (
            f"PERIPHERY legitimacy cost should be {defines.scorched_earth_legitimacy_periphery}, "
            f"got {cost}"
        )

    def test_scorched_earth_destroys_community_infrastructure(self) -> None:
        """SCORCHED_EARTH destroys all community infrastructure.

        Contract: community_infrastructure_quality set to 0.
        """
        defines = _make_defines()
        territory = _make_territory(community_infrastructure_quality=0.8)

        result, _ = resolve_scorched_earth(territory, defines)

        assert result["community_infrastructure_quality"] == 0.0, (
            f"community_infrastructure_quality should be 0.0, "
            f"got {result['community_infrastructure_quality']}"
        )


# ===========================================================================
# BC-TE-006: PRESENCE Edge Operational Profile Drives Heat
# ===========================================================================


class TestHeatAccumulation:
    """BC-TE-006: Operational profile drives heat.

    Reference: FR-E01, FR-E02.
    Spec: territory-effects.md BC-TE-006.
    """

    def test_high_profile_generates_more_heat(self) -> None:
        """HIGH_PROFILE presence accumulates heat faster than LOW_PROFILE.

        Contract: heat contribution from HIGH_PROFILE exceeds LOW_PROFILE
        by a measurable margin.
        """
        defines = _make_defines()

        heat_high_only = compute_heat_accumulation(
            current_heat=0.0,
            high_profile_count=1,
            low_profile_count=0,
            defines=defines,
        )

        heat_low_only = compute_heat_accumulation(
            current_heat=0.0,
            high_profile_count=0,
            low_profile_count=1,
            defines=defines,
        )

        assert heat_high_only > heat_low_only, (
            f"HIGH_PROFILE heat ({heat_high_only}) should exceed LOW_PROFILE heat ({heat_low_only})"
        )

    def test_heat_bounded_to_one(self) -> None:
        """Heat never exceeds 1.0 regardless of presence count.

        Invariant: heat bounded within [0.0, 1.0].
        """
        defines = _make_defines()

        heat = compute_heat_accumulation(
            current_heat=0.9,
            high_profile_count=50,
            low_profile_count=50,
            defines=defines,
        )

        assert heat <= 1.0, f"Heat should be bounded to 1.0, got {heat}"

    def test_heat_accumulates_over_ticks(self) -> None:
        """4 ticks of PRESENCE increase heat from 0.0.

        Contract: heat on T001 has increased from 0.0 after 4 ticks.
        """
        defines = _make_defines()
        heat = 0.0

        max_ticks: int = 4
        for _tick in range(max_ticks):
            heat = compute_heat_accumulation(
                current_heat=heat,
                high_profile_count=1,
                low_profile_count=1,
                defines=defines,
            )

        assert heat > 0.0, f"Heat should increase from 0.0 after {max_ticks} ticks of PRESENCE"


# ===========================================================================
# BC-TE-007: Territory Consciousness Resists PROPAGANDIZE
# ===========================================================================


class TestPropagandizeEffect:
    """BC-TE-007: Consciousness resistance to PROPAGANDIZE.

    Reference: FR-E04, FR-F03.
    Spec: territory-effects.md BC-TE-007.
    """

    def test_high_ci_resists_more(self) -> None:
        """High-consciousness territory resists PROPAGANDIZE more than low-CI.

        Contract: absolute CI decrease in low-CI territory > high-CI territory
        when PROPAGANDIZE applied with identical parameters.
        """
        defines = _make_defines()
        base_delta: float = 0.3

        effect_high_ci = compute_propagandize_effect(
            collective_identity=0.7,
            base_delta=base_delta,
            defines=defines,
        )

        effect_low_ci = compute_propagandize_effect(
            collective_identity=0.2,
            base_delta=base_delta,
            defines=defines,
        )

        assert effect_low_ci > effect_high_ci, (
            f"Low-CI territory effect ({effect_low_ci}) should exceed "
            f"high-CI territory effect ({effect_high_ci})"
        )

    def test_low_ci_nearly_full_effect(self) -> None:
        """Low-consciousness territory receives near-full PROPAGANDIZE effect.

        Contract: with CI=0.5 and base_delta=0.2, PROPAGANDIZE has near-full
        effectiveness because the effective delta is not bounded by CI.
        With CI=0.5, resistance = 0.5 * 0.5 = 0.25, effective = 0.2 * 0.75 = 0.15
        That is 75% of base_delta.
        """
        defines = _make_defines()
        base_delta: float = 0.2

        effect = compute_propagandize_effect(
            collective_identity=0.5,
            base_delta=base_delta,
            defines=defines,
        )

        # With CI=0.5, resistance = 0.5 * 0.5 = 0.25, effective = 0.2 * 0.75 = 0.15
        # That is 75% of base_delta, and below CI so no bounding
        assert effect >= base_delta * 0.5, (
            f"Low-resistance effect ({effect}) should be at least 50% of base_delta ({base_delta})"
        )
        # And the absolute effect is close to base_delta (within resistance margin)
        assert effect == pytest.approx(0.15), f"Expected ~0.15 effective delta, got {effect}"

    def test_ci_bounded_after_propagandize(self) -> None:
        """collective_identity stays >= 0.0 after PROPAGANDIZE.

        Invariant: collective_identity remains bounded within [0.0, 1.0].
        """
        defines = _make_defines()

        # Attempt a very large base_delta on a low-CI territory
        effect = compute_propagandize_effect(
            collective_identity=0.05,
            base_delta=0.5,
            defines=defines,
        )

        # Effect cannot exceed the current CI (would make CI negative)
        assert effect <= 0.05, f"Effect ({effect}) should not exceed current CI (0.05)"
        assert effect >= 0.0, f"Effect ({effect}) should be non-negative"
