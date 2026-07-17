"""MarketScissorsSystem battery — Program 23 Phase-1 shadow (ADR077).

Pins the axis contract: honest absence without a value substrate, seed-at-
value on first observation, oscillator dynamics (boom opens the scissors,
the law of value closes them), determinism, and the byte-safe WorldState
round-trip (absent axis writes no metadata key).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, CONSEQUENCE_SYSTEMS
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.market_scissors import MarketScissorsSystem
from babylon.models.market import MarketState
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _paid_worker(graph: BabylonGraph, node_id: str, w_paid: float, v_produced: float) -> None:
    graph.add_node(
        node_id,
        wealth=1.0,
        active=True,
        w_paid=w_paid,
        v_produced=v_produced,
        _node_type="social_class",
    )


def _step(graph: BabylonGraph, services: ServiceContainer, tick: int) -> None:
    MarketScissorsSystem().step(graph, services, {"tick": tick})


class TestWiring:
    def test_system_is_registered(self) -> None:
        assert any(isinstance(s, MarketScissorsSystem) for s in _DEFAULT_SYSTEMS)

    def test_system_is_classified_as_consequence(self) -> None:
        assert MarketScissorsSystem in CONSEQUENCE_SYSTEMS

    def test_runs_immediately_before_contradiction_system(self) -> None:
        """The registry must measure a FRESH scissors (same-tick ordering)."""
        types = [type(s) for s in _DEFAULT_SYSTEMS]
        assert types.index(MarketScissorsSystem) == types.index(ContradictionSystem) - 1

    def test_oscillator_formula_is_the_engine(self) -> None:
        """Guard against re-orphaning the formulas (the P21 idiom)."""
        import babylon.engine.systems.market_scissors as module

        assert hasattr(module, "calculate_scissors_step")


class TestHonestAbsence:
    def test_no_value_substrate_writes_no_market_key(self) -> None:
        graph = BabylonGraph()
        graph.add_node("territory", node_type="territory", rent_level=0.0)
        _step(graph, ServiceContainer.create(), tick=1)
        assert "market" not in graph.graph

    def test_inactive_accounting_nodes_do_not_count(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "ghost", wealth=1.0, active=False, w_paid=1.0, v_produced=2.0, _node_type="social_class"
        )
        _step(graph, ServiceContainer.create(), tick=1)
        assert "market" not in graph.graph


class TestSeeding:
    def test_first_observation_seeds_at_value(self) -> None:
        graph = BabylonGraph()
        _paid_worker(graph, "w1", w_paid=0.8, v_produced=1.0)
        _paid_worker(graph, "w2", w_paid=0.5, v_produced=1.0)
        _step(graph, ServiceContainer.create(), tick=7)

        state = graph.graph["market"]
        assert state["price_log"] == 0.0
        assert state["price_velocity"] == 0.0
        assert state["fictitious_log"] == 0.0
        assert state["fictitious_velocity"] == 0.0
        assert state["value_ema"] == pytest.approx(2.0)
        assert state["surplus_ema"] == pytest.approx(0.7)
        assert state["tick"] == 7


class TestDynamics:
    @staticmethod
    def _run(growth: float, ticks: int) -> dict[str, float]:
        """Seed then advance with per-tick multiplicative v_produced growth."""
        graph = BabylonGraph()
        _paid_worker(graph, "w1", w_paid=0.8, v_produced=1.0)
        services = ServiceContainer.create()
        v = 1.0
        for tick in range(1, ticks + 1):  # fixed bound
            graph.update_node("w1", v_produced=v, w_paid=0.8 * v)
            _step(graph, services, tick)
            v *= 1.0 + growth
        return dict(graph.graph["market"])

    def test_constant_flow_keeps_price_at_value(self) -> None:
        state = self._run(growth=0.0, ticks=30)
        assert state["price_log"] == pytest.approx(0.0, abs=1e-12)

    def test_boom_opens_the_scissors(self) -> None:
        state = self._run(growth=0.02, ticks=30)
        assert state["price_log"] > 0.0
        assert state["fictitious_log"] > 0.0

    def test_law_of_value_closes_the_scissors_after_the_boom(self) -> None:
        """Freeze growth after a boom: the divergence decays — the correction."""
        graph = BabylonGraph()
        _paid_worker(graph, "w1", w_paid=0.8, v_produced=1.0)
        services = ServiceContainer.create()
        v = 1.0
        for tick in range(1, 31):  # boom
            graph.update_node("w1", v_produced=v, w_paid=0.8 * v)
            _step(graph, services, tick)
            v *= 1.02
        peak = abs(graph.graph["market"]["price_log"])
        for tick in range(31, 200):  # stagnation: drive decays to zero
            graph.update_node("w1", v_produced=v, w_paid=0.8 * v)
            _step(graph, services, tick)
        settled = abs(graph.graph["market"]["price_log"])
        assert peak > 0.0
        assert settled < peak / 2.0

    def test_two_runs_identical(self) -> None:
        assert self._run(growth=0.013, ticks=40) == self._run(growth=0.013, ticks=40)


class TestRoundTrip:
    def test_absent_axis_writes_no_metadata_key(self) -> None:
        state = WorldState(tick=1)
        assert "market" not in state.to_graph().graph

    def test_set_axis_survives_round_trip(self) -> None:
        axis = MarketState(
            price_log=0.12,
            price_velocity=-0.01,
            fictitious_log=0.4,
            fictitious_velocity=0.02,
            surplus_ema=3.5,
            value_ema=11.0,
            tick=42,
        )
        state = WorldState(tick=1, market=axis)
        rebuilt = WorldState.from_graph(state.to_graph(), tick=1)
        assert rebuilt.market == axis

    def test_market_state_is_frozen(self) -> None:
        axis = MarketState(
            price_log=0.0,
            price_velocity=0.0,
            fictitious_log=0.0,
            fictitious_velocity=0.0,
            surplus_ema=0.0,
            value_ema=0.0,
            tick=0,
        )
        with pytest.raises(ValidationError):
            axis.price_log = 1.0  # type: ignore[misc]
