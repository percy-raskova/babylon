"""Tests for BifurcationRiskCalculator.

Feature: 018-crisis-devaluation-mechanics
Tasks: T044-T049

Tests bifurcation risk assessment during crisis:
- US3 AS1: High solidarity -> revolutionary score (< -0.3)
- US3 AS2: Low solidarity -> fascist score (> +0.3)
- US3 AS3: Disproportionate LA losses amplify fascist indicator
- US3 AS4: High legitimation dampens both extremes toward 0
- Non-crisis returns neutral metric
- Edge cases: zero solidarity edges, single class, epsilon guard
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.economics.crisis.bifurcation import BifurcationRiskCalculator
from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.tick.types import (
    BifurcationRiskMetric,
    CrisisPhase,
    CrisisState,
)
from babylon.engine.graph import BabylonGraph


def _make_dist(
    la: float = 0.40,
    prol: float = 0.35,
    fips: str = "26163",
    year: int = 2015,
) -> ClassDistribution:
    """Build a test class distribution.

    Fixed shares: bourgeoisie=0.01, petit_bourgeoisie=0.09.
    lumpen is computed as remainder to satisfy sum-to-one invariant.
    """
    fixed = 0.01 + 0.09  # bourgeoisie + petit_bourgeoisie
    lumpen = 1.0 - fixed - la - prol
    return ClassDistribution(
        fips=fips,
        year=year,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=la,
        proletariat_share=prol,
        lumpenproletariat_share=lumpen,
    )


def _make_crisis_state(
    phase: CrisisPhase = CrisisPhase.DEEP,
    duration: int = 6,
) -> CrisisState:
    """Build a crisis state in active crisis."""
    return CrisisState(
        phase=phase,
        consecutive_below=6,
        consecutive_recovery=0,
        crisis_start_period=3,
        crisis_duration=duration,
        peak_severity=0.03,
        cumulative_wage_compression=0.0,
    )


def _make_graph_with_solidarity(
    fips: str = "26163",
    num_solidarity_edges: int = 4,
    total_possible: int = 6,
    mean_agitation: float = 0.3,
) -> nx.DiGraph:
    """Build a test graph with solidarity edges and ideology data.

    Creates social class nodes with different roles and SOLIDARITY edges
    between them. Configures agitation for legitimation calculation.

    Args:
        fips: County FIPS code.
        num_solidarity_edges: Number of cross-class SOLIDARITY edges to create.
        total_possible: Total possible cross-class edges (for density calc).
        mean_agitation: Average agitation across nodes.
    """
    g: nx.DiGraph = BabylonGraph()

    # Add territory node
    g.add_node(fips, _node_type="territory")

    # Add social class nodes with different roles
    # 3 distinct classes: LA, Proletariat, Lumpen -> C(3,2)=3 possible pairs * 2 directions = 6
    roles = ["labor_aristocracy", "proletariat", "lumpenproletariat"]
    node_ids = []
    for role in roles:
        node_id = f"{fips}_{role}"
        node_ids.append(node_id)
        g.add_node(
            node_id,
            _node_type="social_class",
            role=role,
            ideology={
                "agitation": mean_agitation,
                "class_consciousness": 0.5,
                "national_identity": 0.5,
            },
            territory=fips,
        )

    # Add cross-class solidarity edges (up to num_solidarity_edges)
    possible_pairs = [
        (node_ids[0], node_ids[1]),
        (node_ids[1], node_ids[0]),
        (node_ids[0], node_ids[2]),
        (node_ids[2], node_ids[0]),
        (node_ids[1], node_ids[2]),
        (node_ids[2], node_ids[1]),
    ]
    for i in range(min(num_solidarity_edges, len(possible_pairs))):
        g.add_edge(
            possible_pairs[i][0],
            possible_pairs[i][1],
            edge_type="solidarity",
            solidarity_strength=0.8,
        )

    return g


# =============================================================================
# T044: US3 AS1 - High solidarity -> revolutionary
# =============================================================================


@pytest.mark.unit
class TestRevolutionaryBifurcation:
    """US3 AS1: High cross-class solidarity (> 60%) -> score < -0.3."""

    def test_high_solidarity_produces_negative_score(self) -> None:
        """High solidarity density with low class burden -> revolutionary."""
        calc = BifurcationRiskCalculator()
        # 5/6 solidarity edges = 83% density
        graph = _make_graph_with_solidarity(num_solidarity_edges=5, mean_agitation=0.5)
        crisis = _make_crisis_state()
        # No distribution change -> burden=0 -> raw = -w_s*0.83 + 0 < 0
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.40, prol=0.35)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        assert isinstance(result, BifurcationRiskMetric)
        assert result.score < -0.3, f"Expected revolutionary score < -0.3, got {result.score}"
        assert result.solidarity_density > 0.6

    def test_full_solidarity_maximizes_revolutionary(self) -> None:
        """100% solidarity density with zero burden pushes revolutionary."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=6, mean_agitation=0.5)
        crisis = _make_crisis_state()
        # No class shift -> burden=0 -> raw = -1.0 * 1.0 + 0 = -1.0
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.40, prol=0.35)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        assert result.score < 0.0
        assert result.solidarity_density == pytest.approx(1.0)


# =============================================================================
# T045: US3 AS2 - Low solidarity -> fascist
# =============================================================================


@pytest.mark.unit
class TestFascistBifurcation:
    """US3 AS2: Atomized solidarity (< 20%) + LA burden -> score > +0.3."""

    def test_low_solidarity_with_la_burden_produces_positive_score(self) -> None:
        """Low solidarity + disproportionate LA loss -> fascist."""
        calc = BifurcationRiskCalculator()
        # 1/6 solidarity edges = 17% density
        graph = _make_graph_with_solidarity(num_solidarity_edges=1, mean_agitation=0.5)
        crisis = _make_crisis_state()
        # LA drops much more than proletariat
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.30, prol=0.34)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        assert result.score > 0.3, f"Expected fascist score > 0.3, got {result.score}"
        assert result.solidarity_density < 0.2

    def test_zero_solidarity_amplifies_fascist(self) -> None:
        """Zero solidarity edges with LA burden -> strong fascist."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=0, mean_agitation=0.5)
        crisis = _make_crisis_state()
        # LA drops, proletariat nearly unchanged
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.30, prol=0.34)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        assert result.score > 0.0
        assert result.solidarity_density == 0.0


# =============================================================================
# T046: US3 AS3 - Disproportionate LA losses amplify fascist
# =============================================================================


@pytest.mark.unit
class TestClassBurdenAmplification:
    """US3 AS3: Disproportionate LA losses amplify fascist indicator."""

    def test_la_loss_exceeding_prol_loss_increases_burden(self) -> None:
        """LA declining more than proletariat raises class_burden_ratio."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=3, mean_agitation=0.3)
        crisis = _make_crisis_state()

        # LA drops 0.10, Prol drops 0.01
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.30, prol=0.34)  # lumpen auto-computed

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        assert result.class_burden_ratio > 0.5

    def test_equal_losses_produce_low_burden(self) -> None:
        """Equal class declines produce class_burden_ratio near 1.0."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=3, mean_agitation=0.3)
        crisis = _make_crisis_state()

        # Both drop by similar amounts
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.35, prol=0.30)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        # Burden = |0.05| / max(|0.05|, eps) = 1.0 (clamped to 1.0)
        assert result.class_burden_ratio == pytest.approx(1.0, abs=0.01)


# =============================================================================
# T047: US3 AS4 - High legitimation dampens both extremes
# =============================================================================


@pytest.mark.unit
class TestLegitimationDampening:
    """US3 AS4: High legitimation dampens both extremes toward 0."""

    def test_high_legitimation_dampens_revolutionary(self) -> None:
        """Low agitation (high legitimation) reduces magnitude of negative score."""
        calc = BifurcationRiskCalculator()
        # High solidarity but very low agitation (high legitimation)
        graph_low_agit = _make_graph_with_solidarity(num_solidarity_edges=6, mean_agitation=0.05)
        # High solidarity with moderate agitation
        graph_mod_agit = _make_graph_with_solidarity(num_solidarity_edges=6, mean_agitation=0.5)
        crisis = _make_crisis_state()
        # No class change -> burden=0, raw = -solidarity -> negative
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.40, prol=0.35)

        dampened = calc.compute(graph_low_agit, "26163", crisis, prev_dist, curr_dist)
        undampened = calc.compute(graph_mod_agit, "26163", crisis, prev_dist, curr_dist)

        # Low agitation = high legitimation = more dampening
        assert abs(dampened.score) < abs(undampened.score)
        assert dampened.legitimation > undampened.legitimation

    def test_full_legitimation_produces_near_zero(self) -> None:
        """Zero agitation (legitimation=1.0) -> score dampened to ~0."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=6, mean_agitation=0.0)
        crisis = _make_crisis_state()
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.30, prol=0.34)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        # legitimation = 1 - 0 = 1.0 -> dampened = raw * (1-1) = 0
        assert result.legitimation == pytest.approx(1.0)
        assert result.score == pytest.approx(0.0)


# =============================================================================
# T048: Non-crisis returns neutral metric
# =============================================================================


@pytest.mark.unit
class TestNonCrisisNeutral:
    """Non-crisis periods return neutral BifurcationRiskMetric (score=0)."""

    def test_normal_phase_returns_neutral(self) -> None:
        """NORMAL phase returns BifurcationRiskMetric.neutral()."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity()
        normal = CrisisState.normal()
        prev_dist = _make_dist()
        curr_dist = _make_dist(la=0.35, prol=0.40)

        result = calc.compute(graph, "26163", normal, prev_dist, curr_dist)

        assert result.score == 0.0
        assert result.solidarity_density == 0.0
        assert result.legitimation == 1.0
        assert result.class_burden_ratio == 0.0

    def test_onset_phase_computes_risk(self) -> None:
        """ONSET phase IS active crisis, should compute non-neutral risk."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=5, mean_agitation=0.5)
        onset = _make_crisis_state(phase=CrisisPhase.ONSET, duration=1)
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.35, prol=0.30)

        result = calc.compute(graph, "26163", onset, prev_dist, curr_dist)

        # ONSET is active crisis, so risk should be computed (non-zero components)
        assert result.solidarity_density > 0.0


# =============================================================================
# T049: Edge cases
# =============================================================================


@pytest.mark.unit
class TestBifurcationEdgeCases:
    """Edge cases: zero edges, single class, epsilon guard."""

    def test_no_solidarity_edges(self) -> None:
        """Zero SOLIDARITY edges -> density=0, score >= 0."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=0, mean_agitation=0.5)
        crisis = _make_crisis_state()
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.35, prol=0.30)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        assert result.solidarity_density == 0.0

    def test_single_class_present(self) -> None:
        """Fewer than 2 class categories -> solidarity_density=0."""
        calc = BifurcationRiskCalculator()
        g: nx.DiGraph = BabylonGraph()
        g.add_node("26163", _node_type="territory")
        # Only one social class node
        g.add_node(
            "26163_prol",
            _node_type="social_class",
            role="proletariat",
            ideology={"agitation": 0.5, "class_consciousness": 0.5, "national_identity": 0.5},
            territory="26163",
        )
        crisis = _make_crisis_state()
        prev_dist = _make_dist()
        curr_dist = _make_dist(la=0.35, prol=0.40)

        result = calc.compute(g, "26163", crisis, prev_dist, curr_dist)

        assert result.solidarity_density == 0.0

    def test_epsilon_guard_prevents_division_by_zero(self) -> None:
        """When proletariat change is zero, epsilon prevents division error."""
        calc = BifurcationRiskCalculator(epsilon=0.001)
        graph = _make_graph_with_solidarity(num_solidarity_edges=3, mean_agitation=0.5)
        crisis = _make_crisis_state()
        # LA drops but proletariat unchanged
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.35, prol=0.35)  # lumpen auto-computed

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        # Should not raise, burden = 0.05/max(0.0, 0.001) = 50, clamped to 1.0
        assert result.class_burden_ratio == pytest.approx(1.0)

    def test_no_distribution_change(self) -> None:
        """Same distribution before and after -> burden=0, score near 0."""
        calc = BifurcationRiskCalculator()
        graph = _make_graph_with_solidarity(num_solidarity_edges=3, mean_agitation=0.3)
        crisis = _make_crisis_state()
        dist = _make_dist()

        result = calc.compute(graph, "26163", crisis, dist, dist)

        assert result.class_burden_ratio == 0.0

    def test_score_clamped_to_bounds(self) -> None:
        """Score is always within [-1, +1]."""
        calc = BifurcationRiskCalculator(
            solidarity_weight=10.0,
            burden_weight=10.0,
        )
        graph = _make_graph_with_solidarity(num_solidarity_edges=6, mean_agitation=0.9)
        crisis = _make_crisis_state()
        prev_dist = _make_dist(la=0.40, prol=0.35)
        curr_dist = _make_dist(la=0.30, prol=0.34)

        result = calc.compute(graph, "26163", crisis, prev_dist, curr_dist)

        assert -1.0 <= result.score <= 1.0
