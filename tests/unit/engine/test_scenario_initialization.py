"""Tests for scenario genesis - ensuring simulations start alive.

TDD RED phase tests for the "Born Dead" bug fix.
Scenarios must initialize with:
- Territory entities (for production)
- TENANCY edges (worker → territory)
- Biocapacity = max_biocapacity (fully charged)
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios import (
    create_imperial_circuit_scenario,
    create_two_node_scenario,
)
from babylon.models.entity_registry import (
    COMPRADOR_ID,
    LABOR_ARISTOCRACY_ID,
    PERIPHERY_WORKER_ID,
)
from babylon.models.enums import EdgeType
from tests.constants import TestConstants

TC = TestConstants


@pytest.mark.unit
class TestTwoNodeScenarioGenesis:
    """Tests for create_two_node_scenario() initialization."""

    def test_scenario_has_territory(self) -> None:
        """Scenario must include at least one Territory."""
        state, _, _ = create_two_node_scenario()
        assert len(state.territories) >= 1, "Scenario must have at least one territory"

    def test_scenario_has_positive_biocapacity(self) -> None:
        """total_biocapacity must be > 0 at genesis."""
        state, _, _ = create_two_node_scenario()
        assert state.total_biocapacity > 0, "Genesis must have positive biocapacity"

    def test_biocapacity_equals_max_biocapacity(self) -> None:
        """At genesis, biocapacity should equal max_biocapacity (fully charged)."""
        state, _, _ = create_two_node_scenario()
        for territory_id, territory in state.territories.items():
            assert territory.biocapacity == territory.max_biocapacity, (
                f"Territory {territory_id} not fully charged: "
                f"biocapacity={territory.biocapacity}, max={territory.max_biocapacity}"
            )

    def test_worker_has_tenancy_edge(self) -> None:
        """Worker must have TENANCY edge to territory for production."""
        state, _, _ = create_two_node_scenario()
        graph = state.to_graph()
        worker_id = PERIPHERY_WORKER_ID

        has_tenancy = any(
            edge_data.get("edge_type") == EdgeType.TENANCY
            for _, _, edge_data in graph.out_edges(worker_id, data=True)
        )
        assert has_tenancy, f"Worker {worker_id} has no TENANCY edge to territory"

    def test_genesis_state_converts_to_graph_without_collision(self) -> None:
        """Design B regression: the genesis state must survive ``to_graph()``.

        The scenario historically carried a SOLIDARITY relationship on the
        same (owner, worker) pair as the WAGES edge. BabylonGraph stores one
        edge per (source, target) pair, and the WAGES payload (added last,
        identical key set) fully overwrote the SOLIDARITY payload — the
        solidarity edge was silently dead in every graph conversion. The
        Design B pre-scan turned that silent merge into a ``ValueError``;
        the builder now emits only the edges that were ever live in graph
        form, preserving dynamics byte-for-byte (two_node.json baseline).
        """
        state, _, _ = create_two_node_scenario()

        graph = state.to_graph()  # must not raise (pre-scan clean)

        # The effective owner->worker edge was ALWAYS wages-typed (last
        # writer won the merge) — pin that the fix preserved it.
        owner_worker_types = [
            edge_data.get("edge_type")
            for _, target, edge_data in graph.out_edges(COMPRADOR_ID, data=True)
            if target == PERIPHERY_WORKER_ID
        ]
        assert owner_worker_types == [EdgeType.WAGES], (
            f"expected exactly one WAGES edge owner->worker, got {owner_worker_types}"
        )
        # No SOLIDARITY relationship remains in the model list either.
        solidarity_rels = [r for r in state.relationships if r.edge_type == EdgeType.SOLIDARITY]
        assert solidarity_rels == [], (
            "two-node scenario must not carry a SOLIDARITY relationship: with "
            "only two entities every candidate pair collides with EXPLOITATION "
            "or WAGES (see create_two_node_scenario)"
        )


@pytest.mark.unit
class TestImperialCircuitScenarioGenesis:
    """Tests for create_imperial_circuit_scenario() initialization."""

    def test_scenario_has_territories(self) -> None:
        """Scenario must include territories for periphery and core."""
        state, _, _ = create_imperial_circuit_scenario()
        assert len(state.territories) >= 2, (
            "Imperial circuit needs at least 2 territories (periphery + core)"
        )

    def test_scenario_has_positive_biocapacity(self) -> None:
        """total_biocapacity must be > 0 at genesis."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.total_biocapacity > 0, "Genesis must have positive biocapacity"

    def test_biocapacity_equals_max_biocapacity(self) -> None:
        """At genesis, biocapacity should equal max_biocapacity (fully charged)."""
        state, _, _ = create_imperial_circuit_scenario()
        for territory_id, territory in state.territories.items():
            assert territory.biocapacity == territory.max_biocapacity, (
                f"Territory {territory_id} not fully charged: "
                f"biocapacity={territory.biocapacity}, max={territory.max_biocapacity}"
            )

    def test_periphery_worker_has_tenancy_edge(self) -> None:
        """Periphery worker (C001) must have TENANCY edge to territory."""
        state, _, _ = create_imperial_circuit_scenario()
        graph = state.to_graph()
        worker_id = PERIPHERY_WORKER_ID

        has_tenancy = any(
            edge_data.get("edge_type") == EdgeType.TENANCY
            for _, _, edge_data in graph.out_edges(worker_id, data=True)
        )
        assert has_tenancy, f"Periphery worker {worker_id} has no TENANCY edge"

    def test_labor_aristocracy_has_tenancy_edge(self) -> None:
        """Labor aristocracy (C004) must have TENANCY edge to territory."""
        state, _, _ = create_imperial_circuit_scenario()
        graph = state.to_graph()
        worker_id = LABOR_ARISTOCRACY_ID

        has_tenancy = any(
            edge_data.get("edge_type") == EdgeType.TENANCY
            for _, _, edge_data in graph.out_edges(worker_id, data=True)
        )
        assert has_tenancy, f"Labor aristocracy {worker_id} has no TENANCY edge"
