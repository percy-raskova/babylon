"""Mutation-killing tests for ImperialRentSystem._process_tribute_phase.

Targets wealth transfer arithmetic, active checks, edge filtering,
zero-wealth guard, default value fallback, and value_flow recording.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EdgeType, SocialRole


def _make_tribute_graph(
    source_wealth: float = 100.0,
    target_wealth: float = 0.0,
    *,
    source_active: bool = True,
    target_active: bool = True,
    edge_type: EdgeType = EdgeType.TRIBUTE,
    target_role: SocialRole = SocialRole.CORE_BOURGEOISIE,
) -> nx.DiGraph[str]:
    """Build a minimal graph with one TRIBUTE edge."""
    graph = BabylonGraph()
    graph.add_node(
        "comprador",
        wealth=source_wealth,
        role=SocialRole.COMPRADOR_BOURGEOISIE,
        active=source_active,
    )
    graph.add_node(
        "core_bourg",
        wealth=target_wealth,
        role=target_role,
        active=target_active,
    )
    graph.add_edge("comprador", "core_bourg", edge_type=edge_type)
    return graph


def _make_tick_context() -> dict[str, float]:
    """Standard tick context dict for tribute phase."""
    return {
        "tribute_inflow": 0.0,
        "wages_outflow": 0.0,
        "subsidy_outflow": 0.0,
        "current_pool": 0.0,
        "wage_rate": 0.52,
        "repression_level": 0.5,
    }


@pytest.mark.topology
class TestTributePhaseMutationKillers:
    """Targeted tests to kill mutation survivors in _process_tribute_phase."""

    def test_tribute_wealth_transfer_exact(self) -> None:
        """wealth=100, cut=0.9 → source keeps 90, target gets 10."""
        graph = _make_tribute_graph(source_wealth=100.0, target_wealth=0.0)
        services = ServiceContainer.create()
        # Default comprador_cut = 0.90
        cut = services.defines.economy.comprador_cut
        system = ImperialRentSystem()
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["comprador"]["wealth"] == pytest.approx(100.0 * cut)
        expected_tribute = 100.0 - (100.0 * cut)
        assert graph.nodes["core_bourg"]["wealth"] == pytest.approx(expected_tribute)

    def test_zero_wealth_no_transfer(self) -> None:
        """wealth=0 → continue (no transfer)."""
        graph = _make_tribute_graph(source_wealth=0.0, target_wealth=50.0)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["comprador"]["wealth"] == 0.0
        assert graph.nodes["core_bourg"]["wealth"] == 50.0  # Unchanged

    def test_negative_wealth_no_transfer(self) -> None:
        """wealth=-5 → continue (no transfer)."""
        graph = _make_tribute_graph(source_wealth=-5.0, target_wealth=50.0)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["comprador"]["wealth"] == -5.0  # Unchanged
        assert graph.nodes["core_bourg"]["wealth"] == 50.0  # Unchanged

    def test_inactive_source_skipped(self) -> None:
        """Source active=False → no transfer."""
        graph = _make_tribute_graph(source_wealth=100.0, source_active=False)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["comprador"]["wealth"] == 100.0  # Unchanged
        assert graph.nodes["core_bourg"]["wealth"] == 0.0  # Unchanged

    def test_inactive_target_skipped(self) -> None:
        """Target active=False → no transfer."""
        graph = _make_tribute_graph(target_wealth=0.0, target_active=False)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["core_bourg"]["wealth"] == 0.0  # Unchanged

    def test_non_tribute_edge_skipped(self) -> None:
        """WAGES edge → not processed by tribute phase."""
        graph = _make_tribute_graph(
            source_wealth=100.0,
            edge_type=EdgeType.WAGES,
        )
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["comprador"]["wealth"] == 100.0  # Unchanged

    def test_target_default_wealth(self) -> None:
        """Target with no wealth key → defaults to 0.0, receives tribute."""
        graph = BabylonGraph()
        graph.add_node(
            "comprador",
            wealth=100.0,
            role=SocialRole.COMPRADOR_BOURGEOISIE,
            active=True,
        )
        graph.add_node(
            "core_bourg",
            role=SocialRole.CORE_BOURGEOISIE,
            active=True,
            # No "wealth" key
        )
        graph.add_edge("comprador", "core_bourg", edge_type=EdgeType.TRIBUTE)

        services = ServiceContainer.create()
        system = ImperialRentSystem()
        cut = services.defines.economy.comprador_cut
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        expected_tribute = 100.0 - (100.0 * cut)
        assert graph.nodes["core_bourg"]["wealth"] == pytest.approx(expected_tribute)

    def test_multiple_tribute_edges(self) -> None:
        """3 TRIBUTE edges all transfer correctly."""
        graph = BabylonGraph()
        graph.add_node("core_bourg", wealth=0.0, role=SocialRole.CORE_BOURGEOISIE, active=True)
        for i in range(3):
            node_id = f"comprador_{i}"
            graph.add_node(
                node_id,
                wealth=100.0,
                role=SocialRole.COMPRADOR_BOURGEOISIE,
                active=True,
            )
            graph.add_edge(node_id, "core_bourg", edge_type=EdgeType.TRIBUTE)

        services = ServiceContainer.create()
        system = ImperialRentSystem()
        cut = services.defines.economy.comprador_cut
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        tribute_per = 100.0 - (100.0 * cut)
        # Core bourgeoisie receives tribute from all 3
        assert graph.nodes["core_bourg"]["wealth"] == pytest.approx(3 * tribute_per)
        # Each comprador keeps their cut
        for i in range(3):
            assert graph.nodes[f"comprador_{i}"]["wealth"] == pytest.approx(100.0 * cut)

    def test_cut_fraction_zero_source_keeps_nothing(self) -> None:
        """cut=0.0 → source keeps 0, target gets all wealth."""
        graph = _make_tribute_graph(source_wealth=100.0, target_wealth=0.0)
        from babylon.config.defines import EconomyDefines, GameDefines

        custom_defines = GameDefines(economy=EconomyDefines(comprador_cut=0.0))
        services = ServiceContainer.create(defines=custom_defines)
        system = ImperialRentSystem()
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["comprador"]["wealth"] == pytest.approx(0.0)
        assert graph.nodes["core_bourg"]["wealth"] == pytest.approx(100.0)

    def test_value_flow_recorded(self) -> None:
        """edge['value_flow'] set to tribute amount after transfer."""
        graph = _make_tribute_graph(source_wealth=100.0, target_wealth=0.0)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        cut = services.defines.economy.comprador_cut
        tick_ctx = _make_tick_context()

        system._process_tribute_phase(graph, services, {"tick": 1}, tick_ctx)

        expected_tribute = 100.0 - (100.0 * cut)
        edge_data = graph.edges["comprador", "core_bourg"]
        assert edge_data["value_flow"] == pytest.approx(expected_tribute)
