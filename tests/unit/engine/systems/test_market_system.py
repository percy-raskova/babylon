"""MarketScissorsSystem battery — Program 23 Phase-1 shadow (ADR077).

Pins the axis contract: honest absence without a value substrate, seed-at-
value on first observation, oscillator dynamics (boom opens the scissors,
the law of value closes them), determinism, and the byte-safe WorldState
round-trip (absent axis writes no metadata key).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines, MarketDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, CONSEQUENCE_SYSTEMS
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.market_scissors import (
    MARKET_CORRECTION_SHOCK_ATTR,
    MarketScissorsSystem,
)
from babylon.models.enums import EventType, SocialRole
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
    MarketScissorsSystem().step(graph, services, TickContext(tick=tick))


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


def _enabled_services(**overrides: object) -> ServiceContainer:
    """Services with the Phase-2 feedback gate open (ADR078)."""
    market = MarketDefines(feedback_enabled=True, **overrides)  # type: ignore[arg-type]
    return ServiceContainer.create(defines=GameDefines(market=market))


def _euphoric_graph(fictitious_log: float = 1.5) -> BabylonGraph:
    """A value substrate plus an already-opened fictitious bubble."""
    graph = BabylonGraph()
    _paid_worker(graph, "worker", w_paid=0.8, v_produced=1.0)
    graph.add_node(
        "bourgeois",
        wealth=100.0,
        active=True,
        role=SocialRole.CORE_BOURGEOISIE.value,
        _node_type="social_class",
    )
    graph.add_node(
        "metropole",
        active=True,
        median_wage=1000.0,
        _node_type="territory",
    )
    graph.add_node(
        "hinterland",
        active=True,
        rent_level=0.0,
        _node_type="territory",
    )
    graph.graph["market"] = MarketState(
        price_log=0.3,
        price_velocity=0.05,
        fictitious_log=fictitious_log,
        fictitious_velocity=0.05,
        surplus_ema=0.2,
        value_ema=1.0,
        tick=9,
    ).model_dump()
    return graph


def _county_worker(
    graph: BabylonGraph, node_id: str, fips: str, w_paid: float, v_produced: float
) -> None:
    graph.add_node(
        node_id,
        wealth=1.0,
        active=True,
        w_paid=w_paid,
        v_produced=v_produced,
        county_fips=fips,
        _node_type="social_class",
    )


class TestCountyAxis:
    """ADR078: per-county scissors — the axis under the map lens."""

    @staticmethod
    def _county_graph() -> BabylonGraph:
        graph = BabylonGraph()
        _county_worker(graph, "detroit_labor", "26163", w_paid=0.8, v_produced=1.0)
        _county_worker(graph, "la_labor", "06037", w_paid=0.5, v_produced=1.0)
        _paid_worker(graph, "placeless", w_paid=0.9, v_produced=1.0)  # national only
        graph.add_node(
            "t_wayne", active=True, county_fips="26163", median_wage=900.0, _node_type="territory"
        )
        graph.add_node("t_orphan", active=True, _node_type="territory")
        return graph

    def test_county_axes_seed_alongside_the_national(self) -> None:
        graph = self._county_graph()
        _step(graph, ServiceContainer.create(), tick=1)
        county = graph.graph["market_county"]
        assert set(county) == {"06037", "26163"}
        assert county["26163"]["value_ema"] == pytest.approx(1.0)
        assert county["26163"]["surplus_ema"] == pytest.approx(0.2)
        # The national axis integrates ALL paid workers, placeless included.
        assert graph.graph["market"]["value_ema"] == pytest.approx(3.0)

    def test_no_county_data_writes_no_county_key(self) -> None:
        graph = BabylonGraph()
        _paid_worker(graph, "w1", w_paid=0.8, v_produced=1.0)
        _step(graph, ServiceContainer.create(), tick=1)
        assert "market_county" not in graph.graph

    def test_territory_projection_carries_the_county_reading(self) -> None:
        graph = self._county_graph()
        services = ServiceContainer.create()
        _step(graph, services, tick=1)
        graph.update_node("detroit_labor", v_produced=1.1, w_paid=0.88)
        _step(graph, services, tick=2)
        wayne = graph.get_node("t_wayne")
        assert wayne is not None
        assert wayne.attributes["price_divergence"] == pytest.approx(
            graph.graph["market_county"]["26163"]["price_log"]
        )
        orphan = graph.get_node("t_orphan")
        assert orphan is not None
        assert "price_divergence" not in orphan.attributes  # honest absence

    def test_vanished_county_substrate_drops_its_axis(self) -> None:
        graph = self._county_graph()
        services = ServiceContainer.create()
        _step(graph, services, tick=1)
        graph.update_node("detroit_labor", active=False)
        _step(graph, services, tick=2)
        county = graph.graph["market_county"]
        assert "26163" not in county
        wayne = graph.get_node("t_wayne")
        assert wayne is not None
        assert wayne.attributes["price_divergence"] is None  # de-positioned: honest null

    def test_county_axis_is_deterministic_under_permuted_insertion(self) -> None:
        def run(reverse: bool) -> dict[str, dict[str, float]]:
            graph = BabylonGraph()
            entries = [
                ("a", "26163", 0.8, 1.0),
                ("b", "06037", 0.5, 1.0),
                ("c", "36061", 0.7, 1.0),
            ]
            for node_id, fips, w, v in reversed(entries) if reverse else entries:
                _county_worker(graph, node_id, fips, w_paid=w, v_produced=v)
            services = ServiceContainer.create()
            for tick in range(1, 6):  # fixed bound
                _step(graph, services, tick)
            return dict(graph.graph["market_county"])

        assert run(reverse=False) == run(reverse=True)

    def test_county_axes_round_trip_on_world_state(self) -> None:
        axis = MarketState(
            price_log=0.05,
            price_velocity=0.0,
            fictitious_log=0.1,
            fictitious_velocity=0.0,
            surplus_ema=0.2,
            value_ema=1.0,
            tick=3,
        )
        state = WorldState(tick=1, market_county={"26163": axis})
        rebuilt = WorldState.from_graph(state.to_graph(), tick=1)
        assert rebuilt.market_county == {"26163": axis}

    def test_absent_county_axes_write_no_metadata_key(self) -> None:
        assert "market_county" not in WorldState(tick=1).to_graph().graph

    def test_price_divergence_is_a_declared_transient_field(self) -> None:
        """The projected attr must ride TERRITORY_EXCLUDED_FIELDS or the very
        next from_graph hits the extra='forbid' landmine (the wage_pressure
        precedent). The full-graph round-trip property test enforces the
        general rule; this pins the membership."""
        from babylon.models.world_state import TERRITORY_EXCLUDED_FIELDS

        assert "price_divergence" in TERRITORY_EXCLUDED_FIELDS


class TestCorrection:
    """ADR078: the snap and its material-base consequences."""

    def test_disabled_gate_is_inert(self) -> None:
        """feedback_enabled=False (explicit — the default is True since the
        ADR078 ceremony): the bubble advances but NOTHING fires."""
        graph = _euphoric_graph()
        disabled = ServiceContainer.create(
            defines=GameDefines(market=MarketDefines(feedback_enabled=False))
        )
        _step(graph, disabled, tick=10)
        state = graph.graph["market"]
        assert state["corrections"] == 0
        assert state["last_correction_tick"] is None
        assert graph.get_node("bourgeois").attributes["wealth"] == 100.0
        assert "reserve_ratio" not in graph.get_node("metropole").attributes
        assert MARKET_CORRECTION_SHOCK_ATTR not in graph.graph

    def test_overhang_fires_the_snap(self) -> None:
        graph = _euphoric_graph()
        services = _enabled_services()
        events: list[object] = []
        services.event_bus.subscribe(EventType.MARKET_CORRECTION, events.append)
        before = graph.graph["market"]["fictitious_log"]

        _step(graph, services, tick=10)

        state = graph.graph["market"]
        assert state["corrections"] == 1
        assert state["last_correction_tick"] == 10
        assert state["fictitious_log"] < before * 0.5  # severity 0.6
        assert len(events) == 1

    def test_snap_evaporates_claim_holder_wealth_only(self) -> None:
        graph = _euphoric_graph()
        _step(graph, _enabled_services(), tick=10)
        assert graph.get_node("bourgeois").attributes["wealth"] < 100.0
        assert graph.get_node("worker").attributes["wealth"] == 1.0

    def test_snap_swells_the_reserve_army_where_wages_exist(self) -> None:
        graph = _euphoric_graph()
        _step(graph, _enabled_services(), tick=10)
        assert graph.get_node("metropole").attributes["reserve_ratio"] > 0.0
        assert "reserve_ratio" not in graph.get_node("hinterland").attributes

    def test_snap_stamps_the_wealth_axis_shock(self) -> None:
        graph = _euphoric_graph()
        _step(graph, _enabled_services(), tick=10)
        stamp = graph.graph[MARKET_CORRECTION_SHOCK_ATTR]
        assert stamp["tick"] == 10
        assert stamp["overhang"] > 0.0

    def test_cooldown_suppresses_the_second_snap(self) -> None:
        graph = _euphoric_graph()
        services = _enabled_services()
        _step(graph, services, tick=10)
        # Re-inflate the bubble immediately: still inside the cooldown window.
        state = dict(graph.graph["market"])
        state["fictitious_log"] = 1.5
        graph.graph["market"] = state
        _step(graph, services, tick=11)
        assert graph.graph["market"]["corrections"] == 1

    def test_cooldown_elapse_permits_the_next_snap(self) -> None:
        graph = _euphoric_graph()
        services = _enabled_services()
        _step(graph, services, tick=10)
        state = dict(graph.graph["market"])
        state["fictitious_log"] = 1.5
        graph.graph["market"] = state
        _step(graph, services, tick=18)  # cooldown_ticks=8 elapsed
        assert graph.graph["market"]["corrections"] == 2

    def test_healthy_profit_rate_services_the_bubble(self) -> None:
        """tick_profit_rate=0.3 → serviceable 0.55 + 4·0.3 = 1.75 > 1.5."""
        graph = _euphoric_graph(fictitious_log=1.5)
        graph.update_node("metropole", tick_profit_rate=0.3)
        _step(graph, _enabled_services(), tick=10)
        assert graph.graph["market"]["corrections"] == 0

    def test_no_overhang_no_snap(self) -> None:
        graph = _euphoric_graph(fictitious_log=0.3)
        _step(graph, _enabled_services(), tick=10)
        assert graph.graph["market"]["corrections"] == 0

    def test_correction_is_deterministic(self) -> None:
        def run() -> tuple[dict[str, object], float]:
            graph = _euphoric_graph()
            _step(graph, _enabled_services(), tick=10)
            return dict(graph.graph["market"]), float(
                graph.get_node("bourgeois").attributes["wealth"]
            )

        assert run() == run()


class TestRoundTripFrozen:
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
