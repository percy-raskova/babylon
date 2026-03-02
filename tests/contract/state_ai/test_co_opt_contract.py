"""Contract tests for CO-OPT effects (Feature 039 Phase 8, US6).

Behavioral contracts for PROPAGANDIZE, INCORPORATE, DIVIDE, and BRIBE
actions. Tests verify that state ideological warfare tools produce
measurable effects bounded by game balance constraints.

See Also:
    :mod:`babylon.ooda.state_ai.co_opt_effects`: Implementation.
    ``specs/039-state-apparatus-ai/spec.md``: FR-B05, US6.
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
# BC-US6-001: PROPAGANDIZE Decreases Collective Identity
# ===========================================================================


class TestPropagandizeContract:
    """PROPAGANDIZE reduces CI, high-CI resists more."""

    def test_propagandize_four_ticks_decreases_ci(self) -> None:
        """4 ticks of PROPAGANDIZE measurably decreases CI (SC-009)."""
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5)
        max_ticks: int = 4
        for _tick in range(max_ticks):
            territory = resolve_propagandize(
                territory, "we_are_all_americans", intensity=0.8, defines=defines
            )
        assert territory["collective_identity"] < 0.5, (
            f"CI should decrease after {max_ticks} ticks of PROPAGANDIZE"
        )

    def test_high_ci_resists_more_than_low_ci(self) -> None:
        """High-CI territory resists PROPAGANDIZE more effectively."""
        defines = _make_defines()
        high_ci = _make_territory(collective_identity=0.8)
        low_ci = _make_territory(collective_identity=0.2)

        high_ci = resolve_propagandize(high_ci, "we_are_all_americans", 0.8, defines)
        low_ci = resolve_propagandize(low_ci, "we_are_all_americans", 0.8, defines)

        high_decrease = 0.8 - high_ci["collective_identity"]
        low_decrease = 0.2 - low_ci["collective_identity"]
        assert low_decrease > high_decrease, (
            f"Low-CI decrease ({low_decrease}) should exceed high-CI decrease ({high_decrease})"
        )

    def test_propagandize_ci_bounded(self) -> None:
        """CI never goes below 0.0 after PROPAGANDIZE."""
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.01)
        max_ticks: int = 20
        for _tick in range(max_ticks):
            territory = resolve_propagandize(
                territory, "we_are_all_americans", intensity=1.0, defines=defines
            )
        assert territory["collective_identity"] >= 0.0

    def test_threat_narrative_raises_settler_ci(self) -> None:
        """THREAT_NARRATIVE raises settler CI instead of reducing target CI."""
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.5, settler_collective_identity=0.3)
        territory = resolve_propagandize(territory, "threat_narrative", 0.8, defines)
        assert territory["settler_collective_identity"] > 0.3
        assert territory["collective_identity"] == 0.5  # Target CI unchanged


# ===========================================================================
# BC-US6-002: INCORPORATE Removes Leadership
# ===========================================================================


class TestIncorporateContract:
    """INCORPORATE probability inversely proportional to coherence and CI."""

    def test_low_coherence_low_ci_high_acceptance(self) -> None:
        """Low coherence + low CI = high acceptance probability."""
        defines = _make_defines()
        p = compute_incorporate_probability(
            coherence=0.1,
            collective_identity=0.1,
            offer_attractiveness=0.8,
            defines=defines,
        )
        assert p > 0.3, f"Expected high acceptance, got {p}"

    def test_high_coherence_high_ci_low_acceptance(self) -> None:
        """High coherence + high CI = low acceptance probability."""
        defines = _make_defines()
        p = compute_incorporate_probability(
            coherence=0.9,
            collective_identity=0.9,
            offer_attractiveness=0.8,
            defines=defines,
        )
        assert p < 0.1, f"Expected low acceptance, got {p}"

    def test_probability_bounded_zero_to_one(self) -> None:
        """Acceptance probability stays within [0.0, 1.0]."""
        defines = _make_defines()
        p = compute_incorporate_probability(0.0, 0.0, 1.0, defines)
        assert 0.0 <= p <= 1.0


# ===========================================================================
# BC-US6-003: DIVIDE Degrades Solidarity Edges
# ===========================================================================


class TestDivideContract:
    """DIVIDE degrades edges: SOLIDARISTIC -> TRANSACTIONAL -> ANTAGONISTIC."""

    def test_solidaristic_degrades_to_transactional(self) -> None:
        """One DIVIDE step: SOLIDARISTIC -> TRANSACTIONAL."""
        defines = _make_defines()
        result = resolve_divide("solidaristic", has_prior_surveil=True, defines=defines)
        assert result == "transactional"

    def test_transactional_degrades_to_antagonistic(self) -> None:
        """One DIVIDE step: TRANSACTIONAL -> ANTAGONISTIC."""
        defines = _make_defines()
        result = resolve_divide("transactional", has_prior_surveil=True, defines=defines)
        assert result == "antagonistic"

    def test_four_ticks_complete_degradation(self) -> None:
        """4 ticks of DIVIDE: SOLIDARISTIC -> ANTAGONISTIC."""
        defines = _make_defines()
        edge = "solidaristic"
        max_ticks: int = 4
        for _tick in range(max_ticks):
            edge = resolve_divide(edge, has_prior_surveil=True, defines=defines)
        assert edge == "antagonistic"

    def test_divide_requires_surveil(self) -> None:
        """DIVIDE without prior SURVEIL has no effect."""
        defines = _make_defines(divide_requires_prior_surveil=True)
        result = resolve_divide("solidaristic", has_prior_surveil=False, defines=defines)
        assert result == "solidaristic"


# ===========================================================================
# BC-US6-004: BRIBE Creates Material Dependency
# ===========================================================================


class TestBribeContract:
    """BRIBE transfers material resources and shifts consciousness."""

    def test_bribe_increases_wealth(self) -> None:
        """BRIBE increases target wealth."""
        defines = _make_defines()
        target = _make_target(wealth=10.0)
        result = resolve_bribe(target, bribe_amount=5.0, defines=defines)
        assert result["wealth"] == pytest.approx(15.0)

    def test_bribe_reduces_revolutionary_tendency(self) -> None:
        """BRIBE reduces r_tendency."""
        defines = _make_defines()
        target = _make_target(r_tendency=0.5)
        result = resolve_bribe(target, bribe_amount=5.0, defines=defines)
        assert result["r_tendency"] < 0.5

    def test_bribe_increases_liberal_tendency(self) -> None:
        """BRIBE increases l_tendency."""
        defines = _make_defines()
        target = _make_target(l_tendency=0.3)
        result = resolve_bribe(target, bribe_amount=5.0, defines=defines)
        assert result["l_tendency"] > 0.3

    def test_bribe_marks_transactional_edge(self) -> None:
        """BRIBE marks target for TRANSACTIONAL edge creation."""
        defines = _make_defines()
        target = _make_target()
        result = resolve_bribe(target, bribe_amount=5.0, defines=defines)
        assert result.get("_state_transactional") is True
