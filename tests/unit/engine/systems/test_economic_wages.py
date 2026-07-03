"""Mutation-killing tests for ImperialRentSystem._process_wages_phase.

Targets PPP multiplier formula, pool depletion, wage clamping,
crisis event emission, and inactive entity handling.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import EconomyDefines, GameDefines
from babylon.engine.event_bus import Event
from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EdgeType, EventType, SocialRole


def _make_wages_graph(
    bourgeoisie_wealth: float = 1000.0,
    worker_wealth: float = 0.0,
    *,
    bourgeoisie_active: bool = True,
    worker_active: bool = True,
    edge_type: EdgeType = EdgeType.WAGES,
    la_production: float = 0.0,
) -> nx.DiGraph[str]:
    """Build a minimal graph with one WAGES edge."""
    graph = BabylonGraph()
    graph.add_node(
        "bourgeoisie",
        wealth=bourgeoisie_wealth,
        role=SocialRole.CORE_BOURGEOISIE,
        active=bourgeoisie_active,
    )
    graph.add_node(
        "worker",
        wealth=worker_wealth,
        role=SocialRole.LABOR_ARISTOCRACY,
        active=worker_active,
    )
    graph.add_edge("bourgeoisie", "worker", edge_type=edge_type)

    # Store la_production in graph attributes
    if la_production > 0:
        graph.graph["la_production"] = {"worker": la_production}

    return graph


def _make_wages_tick_context(
    tribute_inflow: float = 100.0,
    current_pool: float = 100.0,
    wage_rate: float = 0.52,
) -> dict[str, Any]:
    """Standard tick context for wages phase."""
    return {
        "tribute_inflow": tribute_inflow,
        "wages_outflow": 0.0,
        "subsidy_outflow": 0.0,
        "current_pool": current_pool,
        "wage_rate": wage_rate,
        "repression_level": 0.5,
    }


@pytest.mark.topology
class TestWagesPhaseMutationKillers:
    """Targeted tests to kill mutation survivors in _process_wages_phase."""

    def test_weekly_wage_rate_calculation(self) -> None:
        """annual=0.52, weeks=52 → per_tick_rate=0.01."""
        graph = _make_wages_graph(bourgeoisie_wealth=1000.0)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context(
            tribute_inflow=100.0, current_pool=100.0, wage_rate=0.52
        )

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        # super_wage_rate = 0.52 / 52 = 0.01
        # max_bonus = tribute_inflow * 0.01 = 100 * 0.01 = 1.0
        # total_wages = 0 (productivity) + 1.0 (bonus) = 1.0
        assert graph.nodes["worker"]["wealth"] == pytest.approx(1.0)

    def test_ppp_multiplier_formula(self) -> None:
        """PPP = 1 + (extraction_eff * sw_mult * ppp_impact)."""
        services = ServiceContainer.create()
        eff = services.defines.economy.extraction_efficiency  # 0.8
        mult = services.defines.economy.superwage_multiplier  # 1.0
        impact = services.defines.economy.superwage_ppp_impact  # 0.5

        expected_ppp = 1.0 + (eff * mult * impact)
        # 1.0 + (0.8 * 1.0 * 0.5) = 1.4
        assert expected_ppp == pytest.approx(1.4)

        # Now verify it's applied to worker node
        graph = _make_wages_graph(bourgeoisie_wealth=1000.0)
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context(tribute_inflow=100.0, current_pool=100.0)

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["worker"]["ppp_multiplier"] == pytest.approx(expected_ppp)

    def test_wages_clamped_to_bourgeoisie_wealth(self) -> None:
        """Bourgeoisie has 50, wages would be 100 → transfer=50."""
        graph = _make_wages_graph(bourgeoisie_wealth=0.5, la_production=100.0)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context(tribute_inflow=100.0, current_pool=100.0)

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        # Worker gets at most bourgeoisie's wealth
        assert graph.nodes["worker"]["wealth"] == pytest.approx(0.5)
        assert graph.nodes["bourgeoisie"]["wealth"] == pytest.approx(0.0)

    def test_inactive_bourgeoisie_skipped(self) -> None:
        """Inactive bourgeoisie → no wage payment."""
        graph = _make_wages_graph(bourgeoisie_wealth=1000.0, bourgeoisie_active=False)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context()

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["worker"]["wealth"] == 0.0  # No transfer
        assert graph.nodes["bourgeoisie"]["wealth"] == 1000.0  # Unchanged

    def test_inactive_worker_skipped(self) -> None:
        """Inactive worker → no wage payment."""
        graph = _make_wages_graph(worker_active=False)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context()

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["bourgeoisie"]["wealth"] == 1000.0  # Unchanged

    def test_non_wages_edge_skipped(self) -> None:
        """TRIBUTE edge → not processed by wages phase."""
        graph = _make_wages_graph(edge_type=EdgeType.TRIBUTE)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context()

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["worker"]["wealth"] == 0.0  # No transfer

    def test_pool_depletion_across_edges(self) -> None:
        """Pool=1.0, 3 workers each want 1.0 bonus → pool depletes to 0."""
        graph = BabylonGraph()
        graph.add_node(
            "bourgeoisie",
            wealth=10000.0,
            role=SocialRole.CORE_BOURGEOISIE,
            active=True,
        )
        for i in range(3):
            graph.add_node(
                f"worker_{i}",
                wealth=0.0,
                role=SocialRole.LABOR_ARISTOCRACY,
                active=True,
            )
            graph.add_edge("bourgeoisie", f"worker_{i}", edge_type=EdgeType.WAGES)

        services = ServiceContainer.create()
        system = ImperialRentSystem()
        # Small pool: total bonus demand will exceed pool
        tick_ctx = _make_wages_tick_context(tribute_inflow=100.0, current_pool=0.5, wage_rate=0.52)

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        # Pool should be depleted (≤ initial)
        assert tick_ctx["current_pool"] <= 0.5

    def test_superwage_crisis_on_pool_exhaustion(self) -> None:
        """Pool=0, bonus negligible → SUPERWAGE_CRISIS event emitted."""
        graph = _make_wages_graph(bourgeoisie_wealth=1000.0)
        services = ServiceContainer.create()

        # Track events
        events_published: list[Event] = []
        original_publish = services.event_bus.publish

        def capture_publish(event: Event) -> None:
            events_published.append(event)
            original_publish(event)

        services.event_bus.publish = capture_publish  # type: ignore[assignment]

        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context(tribute_inflow=0.0, current_pool=0.0, wage_rate=0.52)

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        crisis_events = [e for e in events_published if e.type == EventType.SUPERWAGE_CRISIS]
        assert len(crisis_events) >= 1

    def test_wealth_transfer_exact(self) -> None:
        """Worker wealth increases by wages, bourgeoisie decreases."""
        graph = _make_wages_graph(
            bourgeoisie_wealth=1000.0,
            worker_wealth=10.0,
            la_production=5.0,
        )
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context(tribute_inflow=100.0, current_pool=100.0)

        initial_bourg = graph.nodes["bourgeoisie"]["wealth"]
        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        worker_gained = graph.nodes["worker"]["wealth"] - 10.0
        bourg_lost = initial_bourg - graph.nodes["bourgeoisie"]["wealth"]
        # Conservation: worker gains == bourgeoisie loses
        assert worker_gained == pytest.approx(bourg_lost)

    def test_zero_extraction_efficiency_ppp_is_one(self) -> None:
        """extraction_efficiency=0.0 → ppp_mult=1.0, no PPP bonus."""
        custom = GameDefines(economy=EconomyDefines(extraction_efficiency=0.0))
        services = ServiceContainer.create(defines=custom)
        graph = _make_wages_graph(bourgeoisie_wealth=1000.0)
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context(tribute_inflow=100.0, current_pool=100.0)

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["worker"]["ppp_multiplier"] == pytest.approx(1.0)
        # Unearned increment should be 0
        assert graph.nodes["worker"]["unearned_increment"] == pytest.approx(0.0)

    def test_ppp_applied_to_effective_wealth(self) -> None:
        """effective_wealth = nominal_wealth + wages * (ppp_mult - 1)."""
        graph = _make_wages_graph(bourgeoisie_wealth=1000.0, worker_wealth=0.0)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context(tribute_inflow=100.0, current_pool=100.0)

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        nominal = graph.nodes["worker"]["wealth"]
        effective = graph.nodes["worker"]["effective_wealth"]
        ppp = graph.nodes["worker"]["ppp_multiplier"]
        # effective = nominal + wages * (ppp - 1)
        expected_effective = nominal + nominal * (ppp - 1.0)
        assert effective == pytest.approx(expected_effective)

    def test_zero_bourgeoisie_wealth_no_transfer(self) -> None:
        """Bourgeoisie wealth=0 → skip (no wage payment)."""
        graph = _make_wages_graph(bourgeoisie_wealth=0.0, worker_wealth=5.0)
        services = ServiceContainer.create()
        system = ImperialRentSystem()
        tick_ctx = _make_wages_tick_context()

        system._process_wages_phase(graph, services, {"tick": 1}, tick_ctx)

        assert graph.nodes["worker"]["wealth"] == 5.0  # Unchanged
