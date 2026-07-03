"""Tests for Layer 0 automatic metabolism (Feature 032).

Verifies that Business orgs auto-record metabolism and non-Business
orgs are skipped.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from babylon.engine.graph import BabylonGraph
from babylon.models.enums import ActionType, OrgType
from babylon.ooda.layer0 import process_layer0


def _make_services() -> MagicMock:
    """Create a mock ServiceContainer."""
    services = MagicMock()
    services.event_bus = None
    return services


class TestLayer0Processing:
    """Business orgs auto-record metabolism."""

    def test_business_org_generates_result(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "ford",
            _node_type="organization",
            org_type=OrgType.BUSINESS.value,
            territory_ids=["detroit"],
        )
        results = process_layer0(graph, _make_services())
        assert len(results) == 1
        assert results[0].action.org_id == "ford"
        assert results[0].action.action_type == ActionType.EMPLOY
        assert results[0].success is True
        assert results[0].direct_effects.get("auto_metabolism") is True

    def test_non_business_orgs_skipped(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "fbi",
            _node_type="organization",
            org_type=OrgType.STATE_APPARATUS.value,
        )
        graph.add_node(
            "rev_faction",
            _node_type="organization",
            org_type=OrgType.POLITICAL_FACTION.value,
        )
        results = process_layer0(graph, _make_services())
        assert len(results) == 0

    def test_no_orgs_returns_empty(self) -> None:
        graph = BabylonGraph()
        graph.add_node("territory_1", _node_type="territory")
        results = process_layer0(graph, _make_services())
        assert results == []

    def test_multiple_business_orgs(self) -> None:
        graph = BabylonGraph()
        for i in range(3):
            graph.add_node(
                f"biz_{i}",
                _node_type="organization",
                org_type=OrgType.BUSINESS.value,
                territory_ids=[f"terr_{i}"],
            )
        results = process_layer0(graph, _make_services())
        assert len(results) == 3

    def test_target_is_first_territory(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "corp",
            _node_type="organization",
            org_type=OrgType.BUSINESS.value,
            territory_ids=["main_hq", "branch_1"],
        )
        results = process_layer0(graph, _make_services())
        assert results[0].action.target_id == "main_hq"

    def test_no_territory_uses_org_id(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "corp",
            _node_type="organization",
            org_type=OrgType.BUSINESS.value,
        )
        results = process_layer0(graph, _make_services())
        assert results[0].action.target_id == "corp"
