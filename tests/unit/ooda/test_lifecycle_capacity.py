"""Tests for lifecycle-modified action capacity (Feature 032).

Verifies that lifecycle composition affects action effectiveness
and elder legitimacy provides consciousness bonus.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import OODADefines, OrganizationDefines
from babylon.models.enums import EdgeType, OrgType
from babylon.ooda.lifecycle_capacity import (
    compute_lifecycle_modifier,
    elder_legitimacy_bonus,
)
from babylon.topology.graph import BabylonGraph


def _build_lifecycle_graph(
    org_id: str = "org_1",
    members: list[dict[str, Any]] | None = None,
) -> nx.DiGraph[str]:
    """Build a graph with an org and lifecycle-phased members."""
    graph = BabylonGraph()
    graph.add_node(
        org_id,
        _node_type="organization",
        id=org_id,
        org_type=OrgType.POLITICAL_FACTION.value,
    )

    if members:
        for member in members:
            mid = member["id"]
            graph.add_node(
                mid,
                _node_type="person",
                lifecycle_phase=member.get("lifecycle_phase", "adult"),
            )
            graph.add_edge(org_id, mid, edge_type=EdgeType.MEMBERSHIP.value)

    return graph


class TestComputeLifecycleModifier:
    """Lifecycle composition affects action effectiveness."""

    def test_youth_only_zero_capacity(self) -> None:
        """Organization with only youth members has zero capacity."""
        org_defines = OrganizationDefines()
        members = [
            {"id": "p1", "lifecycle_phase": "youth"},
            {"id": "p2", "lifecycle_phase": "youth"},
        ]
        graph = _build_lifecycle_graph(members=members)

        modifier = compute_lifecycle_modifier("org_1", graph, org_defines)

        assert modifier == pytest.approx(0.0)

    def test_adult_only_full_capacity(self) -> None:
        """Organization with only adult members has full capacity."""
        org_defines = OrganizationDefines()
        members = [
            {"id": "p1", "lifecycle_phase": "adult"},
            {"id": "p2", "lifecycle_phase": "adult"},
        ]
        graph = _build_lifecycle_graph(members=members)

        modifier = compute_lifecycle_modifier("org_1", graph, org_defines)

        assert modifier == pytest.approx(1.0)

    def test_mixed_phases_weighted_average(self) -> None:
        """Mixed youth/adult/elder gives weighted average capacity."""
        org_defines = OrganizationDefines()
        # 1 youth (0.0), 1 adult (1.0), 1 elder (0.2)
        # = (0 + 1.0 + 0.2) / 3 = 0.4
        members = [
            {"id": "p1", "lifecycle_phase": "youth"},
            {"id": "p2", "lifecycle_phase": "adult"},
            {"id": "p3", "lifecycle_phase": "elder"},
        ]
        graph = _build_lifecycle_graph(members=members)

        modifier = compute_lifecycle_modifier("org_1", graph, org_defines)

        # Expected: (0/3)*0 + (1/3)*1.0 + (1/3)*0.2 = 0.333 + 0.067 = 0.4
        assert modifier == pytest.approx(0.4, abs=0.01)

    def test_no_members_zero_capacity(self) -> None:
        """Organization with no members has zero capacity."""
        org_defines = OrganizationDefines()
        graph = _build_lifecycle_graph(members=None)

        modifier = compute_lifecycle_modifier("org_1", graph, org_defines)

        assert modifier == pytest.approx(0.0)

    def test_elder_contributes_partial(self) -> None:
        """Elder-only org contributes elder_capacity_factor (0.2)."""
        org_defines = OrganizationDefines()
        members = [
            {"id": "p1", "lifecycle_phase": "elder"},
            {"id": "p2", "lifecycle_phase": "elder"},
        ]
        graph = _build_lifecycle_graph(members=members)

        modifier = compute_lifecycle_modifier("org_1", graph, org_defines)

        assert modifier == pytest.approx(org_defines.elder_capacity_factor)


class TestElderLegitimacyBonus:
    """Elder presence provides CI delta multiplier."""

    def test_elder_presence_bonus(self) -> None:
        """Non-zero elder proportion multiplies CI delta by elder_legitimacy_multiplier."""
        ooda_defines = OODADefines()
        org_defines = OrganizationDefines()

        members = [
            {"id": "p1", "lifecycle_phase": "adult"},
            {"id": "p2", "lifecycle_phase": "elder"},
        ]
        graph = _build_lifecycle_graph(members=members)

        bonus = elder_legitimacy_bonus("org_1", graph, org_defines, ooda_defines)

        assert bonus == pytest.approx(ooda_defines.elder_legitimacy_multiplier)

    def test_no_elder_no_bonus(self) -> None:
        """Zero elder proportion gives multiplier of 1.0 (no bonus)."""
        ooda_defines = OODADefines()
        org_defines = OrganizationDefines()

        members = [
            {"id": "p1", "lifecycle_phase": "adult"},
            {"id": "p2", "lifecycle_phase": "youth"},
        ]
        graph = _build_lifecycle_graph(members=members)

        bonus = elder_legitimacy_bonus("org_1", graph, org_defines, ooda_defines)

        assert bonus == pytest.approx(1.0)

    def test_no_members_no_bonus(self) -> None:
        """No members gives multiplier of 1.0."""
        ooda_defines = OODADefines()
        org_defines = OrganizationDefines()
        graph = _build_lifecycle_graph(members=None)

        bonus = elder_legitimacy_bonus("org_1", graph, org_defines, ooda_defines)

        assert bonus == pytest.approx(1.0)

    def test_elder_only_bonus(self) -> None:
        """All-elder org gets the bonus."""
        ooda_defines = OODADefines()
        org_defines = OrganizationDefines()

        members = [{"id": "p1", "lifecycle_phase": "elder"}]
        graph = _build_lifecycle_graph(members=members)

        bonus = elder_legitimacy_bonus("org_1", graph, org_defines, ooda_defines)

        assert bonus == pytest.approx(ooda_defines.elder_legitimacy_multiplier)
