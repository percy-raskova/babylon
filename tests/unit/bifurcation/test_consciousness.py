"""Tests for consciousness-weighted solidarity (US1, Feature 033).

Tests cover:
- ``consciousness_sigmoid``: boundary values, breakage cliff, configurable
  midpoint/steepness, overflow clamp safety.
- ``consciousness_weighted_solidarity``: high-CI edge, low-CI edge,
  no-marginalized-community case, multi-community agent case.
"""

from __future__ import annotations

import math

import networkx as nx
import pytest

from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import (
    CommunityState,
)
from babylon.models.enums import CommunityType, EdgeType
from babylon.topology.graph import BabylonGraph

from .factories import (
    assign_communities_to_graph,
    build_test_hypergraph,
    make_community_state,
)

# =============================================================================
# consciousness_sigmoid
# =============================================================================


class TestConsciousnessSigmoid:
    """Tests for the consciousness_sigmoid function."""

    @pytest.mark.unit
    def test_ci_zero_near_zero(self) -> None:
        """CI=0.0 with midpoint=0.4, steepness=10 yields near-zero."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        result = consciousness_sigmoid(collective_identity=0.0, midpoint=0.4, steepness=10.0)
        # 1 / (1 + exp(-10 * (0 - 0.4))) = 1 / (1 + exp(4)) ~ 0.018
        assert result < 0.05
        assert result >= 0.0

    @pytest.mark.unit
    def test_ci_half_approximately_073(self) -> None:
        """CI=0.5 with midpoint=0.4, steepness=10 yields ~0.73."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        result = consciousness_sigmoid(collective_identity=0.5, midpoint=0.4, steepness=10.0)
        # 1 / (1 + exp(-10 * (0.5 - 0.4))) = 1 / (1 + exp(-1)) ~ 0.731
        expected = 1.0 / (1.0 + math.exp(-1.0))
        assert abs(result - expected) < 0.01

    @pytest.mark.unit
    def test_ci_one_near_one(self) -> None:
        """CI=1.0 with midpoint=0.4, steepness=10 yields near-1.0."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        result = consciousness_sigmoid(collective_identity=1.0, midpoint=0.4, steepness=10.0)
        # 1 / (1 + exp(-10 * (1.0 - 0.4))) = 1 / (1 + exp(-6)) ~ 0.9975
        assert result > 0.99
        assert result <= 1.0

    @pytest.mark.unit
    def test_at_midpoint_equals_half(self) -> None:
        """At CI=midpoint, sigmoid should equal exactly 0.5."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        result = consciousness_sigmoid(collective_identity=0.4, midpoint=0.4, steepness=10.0)
        assert abs(result - 0.5) < 1e-10

    @pytest.mark.unit
    def test_breakage_cliff_low_ci(self) -> None:
        """CI=0.1 (assimilated) with default params yields < 0.05."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        result = consciousness_sigmoid(collective_identity=0.1, midpoint=0.4, steepness=10.0)
        # 1 / (1 + exp(-10 * (0.1 - 0.4))) = 1 / (1 + exp(3)) ~ 0.047
        assert result < 0.05

    @pytest.mark.unit
    def test_breakage_cliff_high_ci(self) -> None:
        """CI=0.8 (oppositional) with default params yields > 0.98."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        result = consciousness_sigmoid(collective_identity=0.8, midpoint=0.4, steepness=10.0)
        # 1 / (1 + exp(-10 * (0.8 - 0.4))) = 1 / (1 + exp(-4)) ~ 0.982
        assert result > 0.98

    @pytest.mark.unit
    def test_configurable_midpoint(self) -> None:
        """Midpoint=0.6 shifts the cliff rightward."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        # At the midpoint, always 0.5
        result_at_mid = consciousness_sigmoid(collective_identity=0.6, midpoint=0.6, steepness=10.0)
        assert abs(result_at_mid - 0.5) < 1e-10

        # CI=0.4 with midpoint=0.6 should be low (below the cliff)
        result_below = consciousness_sigmoid(collective_identity=0.4, midpoint=0.6, steepness=10.0)
        assert result_below < 0.15

    @pytest.mark.unit
    def test_configurable_steepness(self) -> None:
        """Higher steepness makes sharper transitions."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        # Very high steepness: CI just above midpoint should be near 1
        steep_above = consciousness_sigmoid(collective_identity=0.45, midpoint=0.4, steepness=50.0)
        gentle_above = consciousness_sigmoid(collective_identity=0.45, midpoint=0.4, steepness=5.0)
        # Steeper sigmoid produces higher value for same offset above midpoint
        assert steep_above > gentle_above

        # Very high steepness: CI just below midpoint should be near 0
        steep_below = consciousness_sigmoid(collective_identity=0.35, midpoint=0.4, steepness=50.0)
        gentle_below = consciousness_sigmoid(collective_identity=0.35, midpoint=0.4, steepness=5.0)
        assert steep_below < gentle_below

    @pytest.mark.unit
    def test_overflow_clamp_large_positive_ci(self) -> None:
        """Large CI with high steepness does not raise OverflowError."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        # steepness=50, ci=1.0, midpoint=0.0 => exponent = -50*1.0 = -50
        # Without clamp, this could overflow with extreme params
        result = consciousness_sigmoid(collective_identity=1.0, midpoint=0.0, steepness=50.0)
        assert result <= 1.0
        assert result > 0.99

    @pytest.mark.unit
    def test_overflow_clamp_large_negative_exponent(self) -> None:
        """CI=0.0 with midpoint=1.0 and high steepness is clamped, not overflow."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        # exponent = -50 * (0.0 - 1.0) = 50 => exp(50) is huge
        result = consciousness_sigmoid(collective_identity=0.0, midpoint=1.0, steepness=50.0)
        assert result >= 0.0
        assert result < 0.01

    @pytest.mark.unit
    def test_return_type_is_float(self) -> None:
        """Sigmoid always returns a Python float."""
        from babylon.bifurcation.consciousness import consciousness_sigmoid

        result = consciousness_sigmoid(collective_identity=0.5, midpoint=0.4, steepness=10.0)
        assert isinstance(result, float)


# =============================================================================
# consciousness_weighted_solidarity
# =============================================================================


def _build_solidarity_graph(
    agents: dict[str, dict[str, float]],
    edges: list[tuple[str, str, float]],
) -> nx.DiGraph:
    """Build a DiGraph with social_class nodes and SOLIDARITY edges.

    Args:
        agents: Node ID to attribute dict (must include 'wealth').
        edges: (source, target, solidarity_strength) triples.

    Returns:
        DiGraph with configured nodes and edges.
    """
    G: nx.DiGraph = BabylonGraph()
    for node_id, attrs in agents.items():
        G.add_node(node_id, _node_type="social_class", **attrs)
    for src, tgt, strength in edges:
        G.add_edge(
            src,
            tgt,
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=strength,
        )
    return G


class TestConsciousnessWeightedSolidarity:
    """Tests for consciousness_weighted_solidarity function."""

    @pytest.mark.unit
    def test_high_ci_edge_near_full_weight(self) -> None:
        """Both agents in high-CI marginalized communities -> near-full weight."""
        from babylon.bifurcation.consciousness import (
            consciousness_weighted_solidarity,
        )

        defines = BifurcationDefines()

        # Two agents, both in NEW_AFRIKAN community with CI=0.8
        agents = {
            "A": {"wealth": 20.0},
            "B": {"wealth": 20.0},
        }
        graph = _build_solidarity_graph(agents, [("A", "B", 0.9)])

        memberships: dict[str, set[CommunityType]] = {
            "A": {CommunityType.NEW_AFRIKAN},
            "B": {CommunityType.NEW_AFRIKAN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.8),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = consciousness_weighted_solidarity(
            source_id="A",
            target_id="B",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # solidarity_strength=0.9, sigmoid(min(0.8, 0.8))~0.982
        # weight = 0.9 * 0.982 ~ 0.884
        assert result.weight > 0.8
        assert result.weight <= 1.0

    @pytest.mark.unit
    def test_low_ci_edge_near_zero_weight(self) -> None:
        """Agents in assimilated communities (CI=0.1) -> near-zero weight."""
        from babylon.bifurcation.consciousness import (
            consciousness_weighted_solidarity,
        )

        defines = BifurcationDefines()

        agents = {
            "A": {"wealth": 50.0},
            "B": {"wealth": 50.0},
        }
        graph = _build_solidarity_graph(agents, [("A", "B", 0.8)])

        memberships: dict[str, set[CommunityType]] = {
            "A": {CommunityType.NEW_AFRIKAN},
            "B": {CommunityType.NEW_AFRIKAN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.1),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = consciousness_weighted_solidarity(
            source_id="A",
            target_id="B",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # solidarity_strength=0.8, sigmoid(min(0.1, 0.1))~0.047
        # weight = 0.8 * 0.047 ~ 0.038
        assert result.weight < 0.05

    @pytest.mark.unit
    def test_no_marginalized_communities_near_zero(self) -> None:
        """Agents with no marginalized community memberships -> near-zero weight.

        When agents only belong to hegemonic or no communities, their
        effective CI is 0, and sigmoid(0) with midpoint=0.4 is near-zero.
        """
        from babylon.bifurcation.consciousness import (
            consciousness_weighted_solidarity,
        )

        defines = BifurcationDefines()

        agents = {
            "A": {"wealth": 100.0},
            "B": {"wealth": 100.0},
        }
        graph = _build_solidarity_graph(agents, [("A", "B", 0.7)])

        # Only hegemonic community memberships (SETTLER is hegemonic)
        memberships: dict[str, set[CommunityType]] = {
            "A": {CommunityType.SETTLER},
            "B": {CommunityType.SETTLER},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.5),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = consciousness_weighted_solidarity(
            source_id="A",
            target_id="B",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # No marginalized communities => CI=0 => sigmoid(0)~0.018
        # weight = 0.7 * 0.018 ~ 0.013
        assert result.weight < 0.05

    @pytest.mark.unit
    def test_multi_community_agent_uses_mean_ci(self) -> None:
        """Agent in multiple marginalized communities uses mean CI."""
        from babylon.bifurcation.consciousness import (
            consciousness_weighted_solidarity,
        )

        defines = BifurcationDefines()

        agents = {
            "A": {"wealth": 20.0},
            "B": {"wealth": 20.0},
        }
        graph = _build_solidarity_graph(agents, [("A", "B", 0.8)])

        # Agent A is in two marginalized communities with different CI
        # Agent B is in one marginalized community
        memberships: dict[str, set[CommunityType]] = {
            "A": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
            "B": {CommunityType.NEW_AFRIKAN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.9),
            CommunityType.DISABLED: make_community_state(CommunityType.DISABLED, ci=0.3),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = consciousness_weighted_solidarity(
            source_id="A",
            target_id="B",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # Agent A mean CI: (0.9 + 0.3) / 2 = 0.6
        # Agent B mean CI: 0.9
        # min(0.6, 0.9) = 0.6
        # sigmoid(0.6, midpoint=0.4, steepness=10) = 1/(1+exp(-10*(0.6-0.4)))
        #   = 1/(1+exp(-2)) ~ 0.881
        # weight = 0.8 * 0.881 ~ 0.705
        assert 0.6 < result.weight < 0.8

    @pytest.mark.unit
    def test_asymmetric_ci_uses_min(self) -> None:
        """When source and target have different CI, min is used."""
        from babylon.bifurcation.consciousness import (
            consciousness_weighted_solidarity,
        )

        defines = BifurcationDefines()

        agents = {
            "A": {"wealth": 20.0},
            "B": {"wealth": 20.0},
        }
        graph = _build_solidarity_graph(agents, [("A", "B", 1.0)])

        # Agent A in high-CI community, Agent B in low-CI community
        memberships: dict[str, set[CommunityType]] = {
            "A": {CommunityType.NEW_AFRIKAN},
            "B": {CommunityType.WOMEN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.9),
            CommunityType.WOMEN: make_community_state(CommunityType.WOMEN, ci=0.15),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = consciousness_weighted_solidarity(
            source_id="A",
            target_id="B",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # min(0.9, 0.15) = 0.15
        # sigmoid(0.15, 0.4, 10) = 1/(1+exp(-10*(0.15-0.4))) = 1/(1+exp(2.5)) ~ 0.076
        # weight = 1.0 * 0.076 ~ 0.076
        assert result.weight < 0.1

    @pytest.mark.unit
    def test_solidarity_strength_scales_result(self) -> None:
        """The edge's solidarity_strength scales the sigmoid output."""
        from babylon.bifurcation.consciousness import (
            consciousness_weighted_solidarity,
        )

        defines = BifurcationDefines()

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.8),
        }

        memberships: dict[str, set[CommunityType]] = {
            "A": {CommunityType.NEW_AFRIKAN},
            "B": {CommunityType.NEW_AFRIKAN},
        }

        # Build with low solidarity_strength
        graph_low = _build_solidarity_graph(
            {"A": {"wealth": 20.0}, "B": {"wealth": 20.0}},
            [("A", "B", 0.3)],
        )
        assign_communities_to_graph(graph_low, memberships)
        H_low = build_test_hypergraph(memberships, community_states)

        result_low = consciousness_weighted_solidarity(
            source_id="A",
            target_id="B",
            graph=graph_low,
            H=H_low,
            community_states=community_states,
            defines=defines,
        )

        # Build with high solidarity_strength
        graph_high = _build_solidarity_graph(
            {"A": {"wealth": 20.0}, "B": {"wealth": 20.0}},
            [("A", "B", 0.9)],
        )
        assign_communities_to_graph(graph_high, memberships)
        H_high = build_test_hypergraph(memberships, community_states)

        result_high = consciousness_weighted_solidarity(
            source_id="A",
            target_id="B",
            graph=graph_high,
            H=H_high,
            community_states=community_states,
            defines=defines,
        )

        # Higher solidarity_strength => higher weighted result
        assert result_high.weight > result_low.weight
        # Ratio should be approximately 0.9/0.3 = 3x
        ratio = result_high.weight / result_low.weight
        assert 2.5 < ratio < 3.5


# =============================================================================
# anisotropic_observation_error (FR-009)
# =============================================================================


@pytest.mark.unit
class TestAnisotropicObservationError:
    """FR-009: State intelligence observes l/f better than r."""

    def test_returns_valid_ternary(self) -> None:
        """Observed consciousness is a valid simplex point."""
        from babylon.bifurcation.consciousness import anisotropic_observation_error
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.5, l=0.3, f=0.2)
        observed = anisotropic_observation_error(tc, rng_seed=42)

        assert isinstance(observed, TernaryConsciousness)
        # Simplex constraint: validator enforces this, but verify explicitly
        assert abs(float(observed.r) + float(observed.l) + float(observed.f) - 1.0) < 1e-4

    def test_r_has_higher_error_than_lf_ratio(self) -> None:
        """Over many samples, r deviation > l/f ratio deviation (anisotropic)."""
        from babylon.bifurcation.consciousness import anisotropic_observation_error
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.4, l=0.35, f=0.25)
        true_lf_ratio = float(tc.f) / (float(tc.l) + float(tc.f))

        r_deviations: list[float] = []
        lf_ratio_deviations: list[float] = []
        max_samples = 200

        for seed in range(max_samples):
            obs = anisotropic_observation_error(tc, rng_seed=seed)
            r_deviations.append(abs(float(obs.r) - float(tc.r)))
            obs_lf_ratio = float(obs.f) / (float(obs.l) + float(obs.f))
            lf_ratio_deviations.append(abs(obs_lf_ratio - true_lf_ratio))

        mean_r_dev = sum(r_deviations) / len(r_deviations)
        mean_lf_dev = sum(lf_ratio_deviations) / len(lf_ratio_deviations)

        # r should have higher average deviation than l/f ratio
        assert mean_r_dev > mean_lf_dev

    def test_deterministic_with_seed(self) -> None:
        """Same seed produces same observed consciousness."""
        from babylon.bifurcation.consciousness import anisotropic_observation_error
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.3, l=0.5, f=0.2)
        obs1 = anisotropic_observation_error(tc, rng_seed=99)
        obs2 = anisotropic_observation_error(tc, rng_seed=99)

        assert float(obs1.r) == float(obs2.r)
        assert float(obs1.l) == float(obs2.l)
        assert float(obs1.f) == float(obs2.f)

    def test_different_seeds_produce_different_results(self) -> None:
        """Different seeds produce different observations."""
        from babylon.bifurcation.consciousness import anisotropic_observation_error
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.4, l=0.35, f=0.25)
        obs1 = anisotropic_observation_error(tc, rng_seed=1)
        obs2 = anisotropic_observation_error(tc, rng_seed=2)

        # At least one component should differ
        differs = (
            float(obs1.r) != float(obs2.r)
            or float(obs1.l) != float(obs2.l)
            or float(obs1.f) != float(obs2.f)
        )
        assert differs

    def test_observation_stays_in_bounds(self) -> None:
        """Observed components stay in [0, 1] even for extreme inputs."""
        from babylon.bifurcation.consciousness import anisotropic_observation_error
        from babylon.models.entities.consciousness import TernaryConsciousness

        # Near-corner cases
        extreme_cases = [
            TernaryConsciousness(r=0.95, l=0.03, f=0.02),
            TernaryConsciousness(r=0.02, l=0.95, f=0.03),
            TernaryConsciousness(r=0.02, l=0.03, f=0.95),
        ]

        max_seeds = 50
        for tc in extreme_cases:
            for seed in range(max_seeds):
                obs = anisotropic_observation_error(tc, rng_seed=seed)
                assert 0.0 <= float(obs.r) <= 1.0
                assert 0.0 <= float(obs.l) <= 1.0
                assert 0.0 <= float(obs.f) <= 1.0
