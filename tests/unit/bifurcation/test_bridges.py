"""Tests for community bridge detection (US3, Feature 033).

Tests cover:
- ``detect_bridges``: INSTITUTIONAL_EXCLUSION communities spanning
  contradiction axes with consciousness-weighted potential.

Test scenarios:
1. DISABLED community spanning colonial axis
2. INCARCERATED community spanning patriarchal axis
3. Community spanning BOTH axes simultaneously
4. Same-side-only members (no bridge)
5. CONTRADICTION_PAIR community excluded by category filter
6. LIFECYCLE_PHASE community excluded by category filter
7. High CI bridge (high weighted_potential)
8. Low CI bridge (low weighted_potential / assimilated)
9. Empty hypergraph → empty list
10. Multiple bridges across different axes
11. Member count verification
"""

from __future__ import annotations

import pytest

from babylon.bifurcation.consciousness import consciousness_sigmoid
from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import (
    CommunityState,
)
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType, ContradictionType, EdgeMode

from .factories import (
    build_test_hypergraph,
    make_community_state,
)

# Dummy contradictions for testing
colonial_contradiction = Contradiction(
    id="colonial",
    type=ContradictionType.IMPERIAL,
    aspect_a=CommunityType.SETTLER,
    aspect_b=CommunityType.NEW_AFRIKAN,
    intensity=0.5,
    principal_aspect="a",
    identity=0.1,
    form_of_struggle=EdgeMode.EXTRACTIVE,
)

patriarchal_contradiction = Contradiction(
    id="patriarchal",
    type=ContradictionType.GENDER,
    aspect_a=CommunityType.PATRIARCHAL,
    aspect_b=CommunityType.WOMEN,
    intensity=0.5,
    principal_aspect="a",
    identity=0.1,
    form_of_struggle=EdgeMode.EXTRACTIVE,
)
TEST_CONTRADICTIONS = [colonial_contradiction, patriarchal_contradiction]

# =============================================================================
# Helpers
# =============================================================================


def _make_states(
    *entries: tuple[CommunityType, float, float],
) -> dict[CommunityType, CommunityState]:
    """Build community_states from (type, ci, infrastructure) tuples.

    Args:
        entries: Variable number of (CommunityType, ci, infrastructure) tuples.

    Returns:
        Community states dict.
    """
    states: dict[CommunityType, CommunityState] = {}
    for comm_type, ci, infra in entries:
        states[comm_type] = make_community_state(
            community_type=comm_type,
            ci=ci,
            infrastructure=infra,
        )
    return states


# =============================================================================
# Tests: detect_bridges
# =============================================================================


class TestDetectBridges:
    """Tests for the detect_bridges function."""

    @pytest.mark.topology
    def test_disabled_spanning_colonial_axis(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """DISABLED community with SETTLER + NEW_AFRIKAN members bridges colonial axis."""
        from babylon.bifurcation.bridges import detect_bridges

        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.SETTLER, CommunityType.DISABLED},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
        }
        community_states = _make_states(
            (CommunityType.DISABLED, 0.5, 0.5),
            (CommunityType.SETTLER, 0.3, 0.3),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 1
        bridge = bridges[0]
        assert bridge.community_type == CommunityType.DISABLED
        assert "colonial" in bridge.axes_spanned
        assert bridge.weighted_potential > 0.0

    @pytest.mark.topology
    def test_incarcerated_spanning_patriarchal_axis(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """INCARCERATED community with PATRIARCHAL + WOMEN members bridges patriarchal axis."""
        from babylon.bifurcation.bridges import detect_bridges

        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.PATRIARCHAL, CommunityType.INCARCERATED},
            "A002": {CommunityType.WOMEN, CommunityType.INCARCERATED},
        }
        community_states = _make_states(
            (CommunityType.INCARCERATED, 0.6, 0.4),
            (CommunityType.PATRIARCHAL, 0.3, 0.3),
            (CommunityType.WOMEN, 0.4, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 1
        bridge = bridges[0]
        assert bridge.community_type == CommunityType.INCARCERATED
        assert "patriarchal" in bridge.axes_spanned

    @pytest.mark.topology
    def test_community_spanning_both_axes(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """QUEER community with members from both sides of BOTH axes."""
        from babylon.bifurcation.bridges import detect_bridges

        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.SETTLER, CommunityType.QUEER},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.QUEER},
            "A003": {CommunityType.PATRIARCHAL, CommunityType.QUEER},
            "A004": {CommunityType.WOMEN, CommunityType.QUEER},
        }
        community_states = _make_states(
            (CommunityType.QUEER, 0.5, 0.5),
            (CommunityType.SETTLER, 0.3, 0.3),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
            (CommunityType.PATRIARCHAL, 0.3, 0.3),
            (CommunityType.WOMEN, 0.4, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 1
        bridge = bridges[0]
        assert bridge.community_type == CommunityType.QUEER
        assert "colonial" in bridge.axes_spanned
        assert "patriarchal" in bridge.axes_spanned
        assert len(bridge.axes_spanned) == 2

    @pytest.mark.topology
    def test_no_bridge_same_side_only(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """DISABLED community with only marginalized members does NOT bridge."""
        from babylon.bifurcation.bridges import detect_bridges

        # All members are NEW_AFRIKAN (marginalized) — no hegemonic members
        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
            "A003": {CommunityType.CHICANO, CommunityType.DISABLED},
        }
        community_states = _make_states(
            (CommunityType.DISABLED, 0.5, 0.5),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
            (CommunityType.CHICANO, 0.4, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 0

    @pytest.mark.topology
    def test_no_bridge_contradiction_pair_excluded(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """CONTRADICTION_PAIR community (NEW_AFRIKAN) excluded even if spanning."""
        from babylon.bifurcation.bridges import detect_bridges

        # NEW_AFRIKAN is CONTRADICTION_PAIR, not INSTITUTIONAL_EXCLUSION
        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.SETTLER, CommunityType.NEW_AFRIKAN},
            "A002": {CommunityType.NEW_AFRIKAN},
        }
        community_states = _make_states(
            (CommunityType.NEW_AFRIKAN, 0.5, 0.5),
            (CommunityType.SETTLER, 0.3, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 0

    @pytest.mark.topology
    def test_no_bridge_lifecycle_phase_excluded(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """LIFECYCLE_PHASE community (YOUTH) excluded by category filter."""
        from babylon.bifurcation.bridges import detect_bridges

        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.SETTLER, CommunityType.YOUTH},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.YOUTH},
        }
        community_states = _make_states(
            (CommunityType.YOUTH, 0.5, 0.5),
            (CommunityType.SETTLER, 0.3, 0.3),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 0

    @pytest.mark.topology
    def test_high_ci_bridge_weighted_potential(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """High CI=0.8, infrastructure=0.7 yields high weighted_potential."""
        from babylon.bifurcation.bridges import detect_bridges

        ci = 0.8
        infrastructure = 0.7
        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.SETTLER, CommunityType.DISABLED},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
        }
        community_states = _make_states(
            (CommunityType.DISABLED, ci, infrastructure),
            (CommunityType.SETTLER, 0.3, 0.3),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 1
        bridge = bridges[0]

        # Expected sigmoid value
        expected_sigmoid = consciousness_sigmoid(
            ci,
            bifurcation_defines.consciousness_sigmoid_midpoint,
            bifurcation_defines.consciousness_sigmoid_steepness,
        )
        expected_potential = infrastructure * expected_sigmoid

        assert bridge.collective_identity == ci
        assert abs(bridge.sigmoid_ci - expected_sigmoid) < 1e-6
        assert bridge.infrastructure == infrastructure
        assert abs(bridge.weighted_potential - expected_potential) < 1e-6
        # At CI=0.8, sigmoid should be near 1.0, so potential ≈ 0.7
        assert bridge.weighted_potential > 0.6

    @pytest.mark.topology
    def test_low_ci_bridge_weighted_potential(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Low CI=0.1, infrastructure=0.7 yields low weighted_potential (assimilated)."""
        from babylon.bifurcation.bridges import detect_bridges

        ci = 0.1
        infrastructure = 0.7
        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.SETTLER, CommunityType.DISABLED},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
        }
        community_states = _make_states(
            (CommunityType.DISABLED, ci, infrastructure),
            (CommunityType.SETTLER, 0.3, 0.3),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 1
        bridge = bridges[0]

        expected_sigmoid = consciousness_sigmoid(
            ci,
            bifurcation_defines.consciousness_sigmoid_midpoint,
            bifurcation_defines.consciousness_sigmoid_steepness,
        )
        expected_potential = infrastructure * expected_sigmoid

        assert bridge.collective_identity == ci
        assert abs(bridge.sigmoid_ci - expected_sigmoid) < 1e-6
        assert abs(bridge.weighted_potential - expected_potential) < 1e-6
        # At CI=0.1 (well below midpoint=0.4), sigmoid near zero → low potential
        assert bridge.weighted_potential < 0.1

    @pytest.mark.topology
    def test_empty_hypergraph_returns_empty(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Empty hypergraph returns empty bridge list."""
        import xgi  # type: ignore[import-untyped]

        from babylon.bifurcation.bridges import detect_bridges

        H: xgi.Hypergraph = xgi.Hypergraph()
        community_states: dict[CommunityType, CommunityState] = {}
        agent_memberships: dict[str, set[CommunityType]] = {}

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert bridges == []

    @pytest.mark.topology
    def test_multiple_bridges(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Multiple INSTITUTIONAL_EXCLUSION communities each spanning different axes."""
        from babylon.bifurcation.bridges import detect_bridges

        agent_memberships: dict[str, set[CommunityType]] = {
            # DISABLED bridges colonial
            "A001": {CommunityType.SETTLER, CommunityType.DISABLED},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
            # INCARCERATED bridges patriarchal
            "A003": {CommunityType.PATRIARCHAL, CommunityType.INCARCERATED},
            "A004": {CommunityType.WOMEN, CommunityType.INCARCERATED},
        }
        community_states = _make_states(
            (CommunityType.DISABLED, 0.5, 0.5),
            (CommunityType.INCARCERATED, 0.6, 0.4),
            (CommunityType.SETTLER, 0.3, 0.3),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
            (CommunityType.PATRIARCHAL, 0.3, 0.3),
            (CommunityType.WOMEN, 0.4, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 2
        bridge_types = {b.community_type for b in bridges}
        assert CommunityType.DISABLED in bridge_types
        assert CommunityType.INCARCERATED in bridge_types

        disabled_bridge = next(b for b in bridges if b.community_type == CommunityType.DISABLED)
        assert "colonial" in disabled_bridge.axes_spanned

        incarcerated_bridge = next(
            b for b in bridges if b.community_type == CommunityType.INCARCERATED
        )
        assert "patriarchal" in incarcerated_bridge.axes_spanned

    @pytest.mark.topology
    def test_member_count(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Bridge member_count matches hyperedge member count."""
        from babylon.bifurcation.bridges import detect_bridges

        agent_memberships: dict[str, set[CommunityType]] = {
            "A001": {CommunityType.SETTLER, CommunityType.DISABLED},
            "A002": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
            "A003": {CommunityType.FIRST_NATIONS, CommunityType.DISABLED},
            "A004": {CommunityType.DISABLED},
        }
        community_states = _make_states(
            (CommunityType.DISABLED, 0.5, 0.5),
            (CommunityType.SETTLER, 0.3, 0.3),
            (CommunityType.NEW_AFRIKAN, 0.5, 0.3),
            (CommunityType.FIRST_NATIONS, 0.5, 0.3),
        )
        H = build_test_hypergraph(agent_memberships, community_states)

        bridges = detect_bridges(
            H=H,
            community_states=community_states,
            contradictions=TEST_CONTRADICTIONS,
            agent_memberships=agent_memberships,
            defines=bifurcation_defines,
        )

        assert len(bridges) == 1
        # 4 agents are in the DISABLED hyperedge
        assert bridges[0].member_count == 4
