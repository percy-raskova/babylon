"""Accounting exposure of ImperialRentSystem's wages phase (Phase D4).

The wages phase's COMPUTATION is unchanged; it now additionally writes two
per-tick bookkeeping attrs on each worker class it pays: ``w_paid`` (the
total wages actually transferred, productivity + super-wage bonus, capped at
what the employer can afford) and ``v_produced`` (the productivity the class
generated). These are the (w, v) pair the value-form ``wage``/``imperial``
oppositions read — the wage⇄value counit defect Φ made observable.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EdgeType, SocialRole

pytestmark = pytest.mark.topology


def _wages_graph(
    bourgeoisie_wealth: float = 1000.0,
    la_production: float = 5.0,
    *,
    worker_active: bool = True,
) -> nx.DiGraph[str]:
    graph = BabylonGraph()
    graph.add_node(
        "bourgeoisie", wealth=bourgeoisie_wealth, role=SocialRole.CORE_BOURGEOISIE, active=True
    )
    graph.add_node("worker", wealth=0.0, role=SocialRole.LABOR_ARISTOCRACY, active=worker_active)
    graph.add_edge("bourgeoisie", "worker", edge_type=EdgeType.WAGES)
    if la_production > 0:
        graph.graph["la_production"] = {"worker": la_production}
    return graph


def _tick_context() -> dict[str, Any]:
    return {
        "tribute_inflow": 100.0,
        "wages_outflow": 0.0,
        "subsidy_outflow": 0.0,
        "current_pool": 100.0,
        "wage_rate": 0.52,  # super_wage_rate = 0.52/52 = 0.01 → bonus = 100*0.01 = 1.0
        "repression_level": 0.5,
    }


class TestWageAccountingAttrs:
    """The paid worker node carries (w_paid, v_produced) after the wages phase."""

    def test_w_paid_and_v_produced_written(self) -> None:
        graph = _wages_graph(la_production=5.0)
        ImperialRentSystem()._process_wages_phase(
            graph, ServiceContainer.create(), {"tick": 1}, _tick_context()
        )
        # productivity 5.0 + bonus 1.0 = total wages 6.0.
        assert graph.nodes["worker"]["w_paid"] == pytest.approx(6.0)
        assert graph.nodes["worker"]["v_produced"] == pytest.approx(5.0)

    def test_w_paid_equals_the_wealth_actually_transferred(self) -> None:
        # w_paid is the accounting mirror of the wage transfer (== value_flow).
        graph = _wages_graph(la_production=5.0)
        ImperialRentSystem()._process_wages_phase(
            graph, ServiceContainer.create(), {"tick": 1}, _tick_context()
        )
        assert graph.nodes["worker"]["w_paid"] == pytest.approx(graph.nodes["worker"]["wealth"])

    def test_w_paid_exceeds_v_produced_when_bribe_flows(self) -> None:
        # The super-wage bonus is the imperial bribe: W > V (Fundamental Theorem).
        graph = _wages_graph(la_production=5.0)
        ImperialRentSystem()._process_wages_phase(
            graph, ServiceContainer.create(), {"tick": 1}, _tick_context()
        )
        assert graph.nodes["worker"]["w_paid"] > graph.nodes["worker"]["v_produced"]

    def test_capped_wages_reflected_in_w_paid(self) -> None:
        # Employer can only afford 0.5; total wages capped there → w_paid = 0.5,
        # but v_produced stays the full productivity (100.0).
        graph = _wages_graph(bourgeoisie_wealth=0.5, la_production=100.0)
        ImperialRentSystem()._process_wages_phase(
            graph, ServiceContainer.create(), {"tick": 1}, _tick_context()
        )
        assert graph.nodes["worker"]["w_paid"] == pytest.approx(0.5)
        assert graph.nodes["worker"]["v_produced"] == pytest.approx(100.0)

    def test_no_accounting_attrs_on_unpaid_inactive_worker(self) -> None:
        # A worker who is not paid (inactive) carries no (w_paid, v_produced).
        graph = _wages_graph(la_production=5.0, worker_active=False)
        ImperialRentSystem()._process_wages_phase(
            graph, ServiceContainer.create(), {"tick": 1}, _tick_context()
        )
        assert "w_paid" not in graph.nodes["worker"]
        assert "v_produced" not in graph.nodes["worker"]

    def test_computation_unchanged(self) -> None:
        # Regression: the wealth/effective_wealth math is exactly as before —
        # this commit is bookkeeping only.
        graph = _wages_graph(la_production=5.0)
        services = ServiceContainer.create()
        ImperialRentSystem()._process_wages_phase(graph, services, {"tick": 1}, _tick_context())
        ppp = graph.nodes["worker"]["ppp_multiplier"]
        nominal = graph.nodes["worker"]["wealth"]
        assert graph.nodes["worker"]["effective_wealth"] == pytest.approx(
            nominal + nominal * (ppp - 1.0)
        )
        assert graph.nodes["bourgeoisie"]["wealth"] == pytest.approx(1000.0 - 6.0)
