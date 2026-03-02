"""Unit tests for CO-OPT effects (Feature 039 Phase 8, US6).

Tests PROPAGANDIZE, INCORPORATE, DIVIDE, and BRIBE action resolution.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-B05.
    :mod:`babylon.ooda.state_ai.co_opt_effects`: Implementation.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.co_opt_effects import (
    compute_incorporate_probability,
    resolve_bribe,
    resolve_divide,
    resolve_propagandize,
)


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_territory(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "collective_identity": 0.5,
        "settler_collective_identity": 0.3,
        "population": 1000,
        "heat": 0.0,
    }
    defaults.update(overrides)
    return defaults


def _make_target(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "wealth": 10.0,
        "r_tendency": 0.5,
        "l_tendency": 0.3,
        "f_tendency": 0.2,
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# resolve_propagandize tests
# ===========================================================================


class TestResolvePropagandize:
    """Unit tests for resolve_propagandize."""

    def test_we_are_all_americans_reduces_ci(self) -> None:
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5)
        result = resolve_propagandize(territory, "we_are_all_americans", 1.0, defines)
        assert result["collective_identity"] < 0.5

    def test_ci_never_below_zero(self) -> None:
        defines = _make_defines(propagandize_base_delta=0.5)
        territory = _make_territory(collective_identity=0.01)
        result = resolve_propagandize(territory, "we_are_all_americans", 1.0, defines)
        assert result["collective_identity"] >= 0.0

    def test_threat_narrative_raises_settler_ci(self) -> None:
        defines = _make_defines()
        territory = _make_territory(settler_collective_identity=0.3)
        result = resolve_propagandize(territory, "threat_narrative", 1.0, defines)
        assert result["settler_collective_identity"] > 0.3

    def test_threat_narrative_preserves_target_ci(self) -> None:
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5)
        result = resolve_propagandize(territory, "threat_narrative", 1.0, defines)
        assert result["collective_identity"] == 0.5

    def test_reform_is_working_has_moderate_effect(self) -> None:
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5)
        result_reform = resolve_propagandize(territory, "reform_is_working", 1.0, defines)
        result_direct = resolve_propagandize(
            _make_territory(collective_identity=0.5),
            "we_are_all_americans",
            1.0,
            defines,
        )
        # reform_is_working has 0.7x multiplier vs 1.0x for we_are_all_americans
        reform_decrease = 0.5 - result_reform["collective_identity"]
        direct_decrease = 0.5 - result_direct["collective_identity"]
        assert reform_decrease < direct_decrease

    def test_unknown_narrative_uses_default_multiplier(self) -> None:
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5)
        result = resolve_propagandize(territory, "unknown_narrative", 1.0, defines)
        assert result["collective_identity"] < 0.5

    def test_zero_intensity_no_effect(self) -> None:
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5)
        result = resolve_propagandize(territory, "we_are_all_americans", 0.0, defines)
        assert result["collective_identity"] == pytest.approx(0.5)

    def test_does_not_mutate_input(self) -> None:
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5)
        _ = resolve_propagandize(territory, "we_are_all_americans", 1.0, defines)
        assert territory["collective_identity"] == 0.5

    def test_high_ci_resists_more(self) -> None:
        defines = _make_defines()
        high_ci = _make_territory(collective_identity=0.8)
        low_ci = _make_territory(collective_identity=0.2)
        result_high = resolve_propagandize(high_ci, "we_are_all_americans", 1.0, defines)
        result_low = resolve_propagandize(low_ci, "we_are_all_americans", 1.0, defines)
        high_decrease = 0.8 - result_high["collective_identity"]
        low_decrease = 0.2 - result_low["collective_identity"]
        assert low_decrease > high_decrease


# ===========================================================================
# compute_incorporate_probability tests
# ===========================================================================


class TestComputeIncorporateProbability:
    """Unit tests for compute_incorporate_probability."""

    def test_formula_basic(self) -> None:
        """p = (1 - coherence) * (1 - ci) * max(offer, base)."""
        defines = _make_defines(incorporate_base_attractiveness=0.3)
        p = compute_incorporate_probability(0.2, 0.3, 0.8, defines)
        expected = (1.0 - 0.2) * (1.0 - 0.3) * 0.8
        assert p == pytest.approx(expected)

    def test_perfect_coherence_zero_probability(self) -> None:
        defines = _make_defines()
        p = compute_incorporate_probability(1.0, 0.5, 0.8, defines)
        assert p == pytest.approx(0.0)

    def test_perfect_ci_zero_probability(self) -> None:
        defines = _make_defines()
        p = compute_incorporate_probability(0.5, 1.0, 0.8, defines)
        assert p == pytest.approx(0.0)

    def test_zero_coherence_zero_ci_max_probability(self) -> None:
        defines = _make_defines()
        p = compute_incorporate_probability(0.0, 0.0, 1.0, defines)
        assert p == pytest.approx(1.0)

    def test_offer_below_base_uses_base(self) -> None:
        defines = _make_defines(incorporate_base_attractiveness=0.5)
        p = compute_incorporate_probability(0.0, 0.0, 0.1, defines)
        # Should use 0.5 (base), not 0.1 (offer)
        assert p == pytest.approx(0.5)

    def test_bounded_zero_to_one(self) -> None:
        defines = _make_defines()
        p = compute_incorporate_probability(0.0, 0.0, 1.0, defines)
        assert 0.0 <= p <= 1.0


# ===========================================================================
# resolve_divide tests
# ===========================================================================


class TestResolveDivide:
    """Unit tests for resolve_divide."""

    def test_solidaristic_to_transactional(self) -> None:
        defines = _make_defines()
        assert resolve_divide("solidaristic", True, defines) == "transactional"

    def test_transactional_to_antagonistic(self) -> None:
        defines = _make_defines()
        assert resolve_divide("transactional", True, defines) == "antagonistic"

    def test_antagonistic_stays_antagonistic(self) -> None:
        defines = _make_defines()
        assert resolve_divide("antagonistic", True, defines) == "antagonistic"

    def test_unknown_edge_type_unchanged(self) -> None:
        defines = _make_defines()
        assert resolve_divide("exploitation", True, defines) == "exploitation"

    def test_no_surveil_blocks_divide(self) -> None:
        defines = _make_defines(divide_requires_prior_surveil=True)
        assert resolve_divide("solidaristic", False, defines) == "solidaristic"

    def test_surveil_not_required_when_disabled(self) -> None:
        defines = _make_defines(divide_requires_prior_surveil=False)
        assert resolve_divide("solidaristic", False, defines) == "transactional"

    def test_full_degradation_chain(self) -> None:
        defines = _make_defines()
        edge = "solidaristic"
        edge = resolve_divide(edge, True, defines)
        assert edge == "transactional"
        edge = resolve_divide(edge, True, defines)
        assert edge == "antagonistic"
        edge = resolve_divide(edge, True, defines)
        assert edge == "antagonistic"  # Bottom of chain


# ===========================================================================
# resolve_bribe tests
# ===========================================================================


class TestResolveBribe:
    """Unit tests for resolve_bribe."""

    def test_bribe_increases_wealth(self) -> None:
        defines = _make_defines()
        target = _make_target(wealth=10.0)
        result = resolve_bribe(target, 5.0, defines)
        assert result["wealth"] == pytest.approx(15.0)

    def test_bribe_reduces_r_tendency(self) -> None:
        defines = _make_defines(bribe_consciousness_shift=0.05)
        target = _make_target(r_tendency=0.5)
        result = resolve_bribe(target, 5.0, defines)
        assert result["r_tendency"] == pytest.approx(0.45)

    def test_bribe_increases_l_tendency(self) -> None:
        defines = _make_defines(bribe_liberal_increase=0.03)
        target = _make_target(l_tendency=0.3)
        result = resolve_bribe(target, 5.0, defines)
        assert result["l_tendency"] == pytest.approx(0.33)

    def test_r_tendency_bounded_at_zero(self) -> None:
        defines = _make_defines(bribe_consciousness_shift=0.5)
        target = _make_target(r_tendency=0.01)
        result = resolve_bribe(target, 5.0, defines)
        assert result["r_tendency"] == 0.0

    def test_l_tendency_bounded_at_one(self) -> None:
        defines = _make_defines(bribe_liberal_increase=0.5)
        target = _make_target(l_tendency=0.9)
        result = resolve_bribe(target, 5.0, defines)
        assert result["l_tendency"] == 1.0

    def test_marks_transactional_edge(self) -> None:
        defines = _make_defines()
        target = _make_target()
        result = resolve_bribe(target, 5.0, defines)
        assert result["_state_transactional"] is True

    def test_does_not_mutate_input(self) -> None:
        defines = _make_defines()
        target = _make_target(wealth=10.0)
        _ = resolve_bribe(target, 5.0, defines)
        assert target["wealth"] == 10.0

    def test_zero_bribe_only_consciousness(self) -> None:
        defines = _make_defines()
        target = _make_target(wealth=10.0)
        result = resolve_bribe(target, 0.0, defines)
        assert result["wealth"] == pytest.approx(10.0)
        assert result["r_tendency"] < target["r_tendency"]
