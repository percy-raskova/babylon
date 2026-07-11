"""Unit tests for institution graph query functions (Feature 040, Phase 9).

Validates:
- community_embeddedness() returns dict[str, float]
- Territory overlap correctly identified
- Empty results for no territory or no communities
"""

from __future__ import annotations

import pytest

from babylon.domain.institution.queries import community_embeddedness
from babylon.topology.graph import BabylonGraph

from .conftest import make_institution


def _build_graph_with_communities() -> BabylonGraph:
    """Build a test graph with community and territory nodes."""
    g = BabylonGraph()

    # Territory nodes
    g.add_node("T001", _node_type="territory")
    g.add_node("T002", _node_type="territory")
    g.add_node("T003", _node_type="territory")

    # Community nodes in T001 territory
    g.add_node(
        "comm_religious_t1",
        _node_type="community",
        community_type="religious",
        territory_id="T001",
    )
    g.add_node(
        "comm_labor_t1",
        _node_type="community",
        community_type="labor",
        territory_id="T001",
    )

    # Community nodes in T002 territory
    g.add_node(
        "comm_religious_t2",
        _node_type="community",
        community_type="religious",
        territory_id="T002",
    )
    g.add_node(
        "comm_ethnic_t2",
        _node_type="community",
        community_type="ethnic",
        territory_id="T002",
    )

    # Community nodes in T003 (not in institution territory)
    g.add_node(
        "comm_labor_t3",
        _node_type="community",
        community_type="labor",
        territory_id="T003",
    )
    g.add_node(
        "comm_ethnic_t3",
        _node_type="community",
        community_type="ethnic",
        territory_id="T003",
    )

    return g


class TestCommunityEmbeddedness:
    """community_embeddedness() query function."""

    def test_returns_dict(self) -> None:
        """Should return dict[str, float]."""
        graph = _build_graph_with_communities()
        inst = make_institution(territory_ids=["T001", "T002"], jurisdiction=None)
        result = community_embeddedness(inst, graph)
        assert isinstance(result, dict)

    def test_scores_in_range(self) -> None:
        """All scores should be in [0, 1]."""
        graph = _build_graph_with_communities()
        inst = make_institution(territory_ids=["T001", "T002"], jurisdiction=None)
        result = community_embeddedness(inst, graph)
        for score in result.values():
            assert 0.0 <= score <= 1.0

    @pytest.mark.math
    def test_full_overlap_single_type(self) -> None:
        """Religious communities in T001+T002: 2/2 = 1.0 when institution has both."""
        graph = _build_graph_with_communities()
        # Institution in T001 and T002 covers all religious communities (2/2)
        inst = make_institution(territory_ids=["T001", "T002"], jurisdiction=None)
        result = community_embeddedness(inst, graph)
        assert result.get("religious", 0.0) == 1.0

    @pytest.mark.math
    def test_partial_overlap(self) -> None:
        """Labor communities: 1 in T001, 1 in T003. Institution in T001 => 1/2 = 0.5."""
        graph = _build_graph_with_communities()
        inst = make_institution(territory_ids=["T001"], jurisdiction=None)
        result = community_embeddedness(inst, graph)
        assert result.get("labor", 0.0) == 0.5

    @pytest.mark.math
    def test_no_overlap(self) -> None:
        """Ethnic communities only in T002+T003, institution in T001 only."""
        graph = _build_graph_with_communities()
        inst = make_institution(territory_ids=["T001"], jurisdiction=None)
        result = community_embeddedness(inst, graph)
        # ethnic: 0 in T001 / 2 total = 0.0
        assert result.get("ethnic", 0.0) == 0.0

    def test_empty_territories(self) -> None:
        """Institution with no territories should return empty dict."""
        graph = _build_graph_with_communities()
        inst = make_institution(territory_ids=[], jurisdiction=None)
        result = community_embeddedness(inst, graph)
        assert result == {}

    def test_no_communities_in_graph(self) -> None:
        """Graph with no community nodes should return empty dict."""
        g = BabylonGraph()
        g.add_node("T001", _node_type="territory")
        graph = g
        inst = make_institution(territory_ids=["T001"], jurisdiction=None)
        result = community_embeddedness(inst, graph)
        assert result == {}

    @pytest.mark.math
    def test_all_three_territories(self) -> None:
        """Institution spanning all 3 territories should have full overlap."""
        graph = _build_graph_with_communities()
        inst = make_institution(
            territory_ids=["T001", "T002", "T003"],
            jurisdiction=None,
        )
        result = community_embeddedness(inst, graph)
        # All community types should be 1.0 (all nodes covered)
        assert result.get("religious", 0.0) == 1.0
        assert result.get("labor", 0.0) == 1.0
        assert result.get("ethnic", 0.0) == 1.0
