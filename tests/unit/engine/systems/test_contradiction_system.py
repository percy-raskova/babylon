"""Unit tests for the Lawverian ContradictionSystem rewire (Phase C1.3).

The rewrite replaces the saturating, add-only edge-``tension`` accumulator
with **fresh-per-tick** scale-free wealth-asymmetry gaps computed off the
:class:`~babylon.domain.dialectics.core.opposition.OppositionRegistry`. These tests
pin the new contract:

- per-edge ``tension`` is the current wealth-asymmetry gap, recomputed each
  tick (idempotent under a static graph — NOT accumulated);
- the registry snapshot is stashed on the graph attribute
  ``opposition_states`` (the cross-tick + consumer handoff channel — the
  bridged runner recreates ``TickContext`` each tick so ``persistent_data``
  is not a cross-tick channel there);
- ``contradiction_frames`` is derived from the registry (intensity ← gap,
  aspect_balance ← rate, principal_aspect ← leading_pole);
- RUPTURE fires on principal-gap > threshold AND rising (rate > 0), never on
  hitting a ceiling, never on a static or falling gap.
"""

from __future__ import annotations

import pytest

from babylon.domain.dialectics.core.coupling import StanceIntervention
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import (
    OPPOSITION_INTERVENTIONS_ATTR,
    ContradictionSystem,
)
from babylon.models.enums import EdgeType, EventType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _rupture_events(services: ServiceContainer) -> list[object]:
    return [e for e in services.event_bus.get_history() if e.type == EventType.RUPTURE]


class TestFreshEdgeTension:
    """Per-edge tension is the current wealth-asymmetry gap, not accumulated."""

    def test_exploitation_tension_equals_wealth_asymmetry_gap(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION, tension=0.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        # |30 - 10| / (10 + 30) = 0.5, fresh (not the 0.0 it started at).
        assert graph["worker"]["owner"]["tension"] == pytest.approx(0.5)

    def test_tension_is_not_accumulated_across_ticks(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION, tension=0.0)
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})
        first = graph["worker"]["owner"]["tension"]
        system.step(graph, services, {"tick": 2})
        second = graph["worker"]["owner"]["tension"]

        # Static graph -> identical gap both ticks (no add-only accumulation).
        assert first == pytest.approx(0.5)
        assert second == pytest.approx(0.5)

    def test_tenancy_rent_free_guard_gives_zero_tension(self) -> None:
        graph = BabylonGraph()
        graph.add_node("tenant", wealth=10.0)
        graph.add_node("land", node_type="territory", rent_level=0.0)
        graph.add_edge("tenant", "land", edge_type=EdgeType.TENANCY, tension=0.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph["tenant"]["land"]["tension"] == pytest.approx(0.0)


class TestRegistryStash:
    """The registry snapshot lands on the graph attribute ``opposition_states``."""

    def test_opposition_states_written_to_graph_attr(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 3})

        states = graph.graph["opposition_states"]
        assert set(states) == {"capital_labor", "wage", "tenancy", "atomization", "imperial"}
        assert states["capital_labor"]["gap"] == pytest.approx(0.5)
        assert states["capital_labor"]["tick"] == 3
        # capital_labor is the only non-zero gap -> it is the principal.
        assert states["capital_labor"]["is_principal"] is True

    def test_rate_carried_across_ticks_via_graph_attr(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})
        assert graph.graph["opposition_states"]["capital_labor"]["rate"] == pytest.approx(0.0)

        # Widen the gap: owner richer -> gap rises -> rate > 0.
        graph.nodes["owner"]["wealth"] = 90.0
        system.step(graph, services, {"tick": 2})
        cap = graph.graph["opposition_states"]["capital_labor"]
        assert cap["gap"] == pytest.approx(80.0 / 100.0)  # |90-10|/100 = 0.8
        assert cap["rate"] == pytest.approx(0.8 - 0.5)  # rose by 0.3


class TestContradictionFrames:
    """``contradiction_frames`` is derived from the registry states."""

    def test_frame_principal_maps_gap_rate_pole(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        frame = graph.graph["contradiction_frames"]["global"]
        principal = frame["principal"]
        assert principal["id"] == "capital_labor"
        assert principal["intensity"] == pytest.approx(0.5)  # intensity <- gap
        assert principal["aspect_balance"] == pytest.approx(0.0)  # aspect_balance <- rate (tick 1)
        assert principal["principal_aspect"] in ("a", "b")  # principal_aspect <- leading_pole


class TestRuptureGate:
    """RUPTURE = condition AND level: gap > threshold AND rate > 0."""

    def _extreme_graph(self, owner_wealth: float) -> BabylonGraph:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=1.0)
        graph.add_node("owner", wealth=owner_wealth)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        return graph

    def test_no_rupture_on_static_extreme_gap(self) -> None:
        # gap = 99/101 ~ 0.98 > 0.9 threshold, but rate = 0 (static) -> no rupture.
        graph = self._extreme_graph(100.0)
        services = ServiceContainer.create()
        system = ContradictionSystem()
        system.step(graph, services, {"tick": 1})
        system.step(graph, services, {"tick": 2})
        assert _rupture_events(services) == []

    def test_rupture_fires_when_gap_high_and_rising(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._extreme_graph(50.0)  # gap = 49/51 ~ 0.96 (rate 0 on tick 1)
        system.step(graph, services, {"tick": 1})
        assert _rupture_events(services) == []  # rising gate not yet satisfied

        graph.nodes["owner"]["wealth"] = 200.0  # gap = 199/201 ~ 0.99, rate > 0
        system.step(graph, services, {"tick": 2})
        ruptures = _rupture_events(services)
        assert len(ruptures) == 1
        assert ruptures[0].payload["opposition"] == "capital_labor"
        assert ruptures[0].payload["gap"] > 0.9
        assert ruptures[0].payload["rate"] > 0.0

    def test_no_rupture_when_gap_high_but_falling(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._extreme_graph(200.0)  # gap ~ 0.99
        system.step(graph, services, {"tick": 1})
        graph.nodes["owner"]["wealth"] = 100.0  # gap ~ 0.98, falling -> rate < 0
        system.step(graph, services, {"tick": 2})
        assert _rupture_events(services) == []

    def test_no_rupture_when_gap_low_but_rising(self) -> None:
        # The LEVEL half of the gate: rate > 0 alone must never fire —
        # quantity has not yet accumulated to the threshold (I.7).
        # Kills the mutant that deletes `gap > threshold` from _maybe_rupture.
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=12.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        system.step(graph, services, {"tick": 1})
        graph.nodes["owner"]["wealth"] = 14.0  # gap 0.09 -> 0.17: rising, far below 0.9
        system.step(graph, services, {"tick": 2})
        cap = graph.graph["opposition_states"]["capital_labor"]
        assert cap["rate"] > 0.0  # the rising precondition really holds
        assert cap["gap"] < float(services.defines.tension.rupture_gap_threshold)
        assert _rupture_events(services) == []


class TestStanceInterventions:
    """``opposition_interventions`` attr: applied post-step, consumed once."""

    def _labor_dominant_graph(self) -> BabylonGraph:
        # Worker richer than owner -> capital_labor balance < 0 -> leading_pole "a".
        graph = BabylonGraph()
        graph.add_node("worker", wealth=30.0)
        graph.add_node("owner", wealth=10.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        return graph

    def _dump(self, delta: float) -> dict[str, object]:
        return StanceIntervention(
            target_key="capital_labor", delta_balance=delta, source="test"
        ).model_dump()

    def test_no_intervention_leaves_the_natural_measure(self) -> None:
        graph = self._labor_dominant_graph()
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "a"

    def test_intervention_flips_leading_pole_through_the_system(self) -> None:
        graph = self._labor_dominant_graph()
        graph.graph[OPPOSITION_INTERVENTIONS_ATTR] = [self._dump(1.0)]

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        cap = graph.graph["opposition_states"]["capital_labor"]
        assert cap["leading_pole"] == "b"  # flipped from "a" by the +1.0 shove
        assert cap["balance"] == pytest.approx(0.5)  # clamp(-0.5 + 1.0)

    def test_interventions_are_consumed_once(self) -> None:
        graph = self._labor_dominant_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph.graph[OPPOSITION_INTERVENTIONS_ATTR] = [self._dump(1.0)]

        system.step(graph, services, {"tick": 1})
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "b"
        assert graph.graph[OPPOSITION_INTERVENTIONS_ATTR] == []  # cleared after use

        # Tick 2 with no fresh interventions: fresh measure only, NOT re-applied.
        system.step(graph, services, {"tick": 2})
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "a"


class TestWageValuePairsExtraction:
    """`_build_graph_inputs` lifts (w_paid, v_produced) off paid class nodes (D4)."""

    @staticmethod
    def _inputs(graph: BabylonGraph):  # type: ignore[no-untyped-def]

        return ContradictionSystem()._build_graph_inputs(graph)

    def test_pairs_extracted_from_nodes_carrying_both_attrs(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0, v_produced=5.0)
        graph.add_node("c2", w_paid=3.0, v_produced=4.0)
        pairs = self._inputs(graph).wage_value_pairs
        assert set(pairs) == {(6.0, 5.0), (3.0, 4.0)}

    def test_node_missing_v_produced_is_skipped(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0)  # no v_produced
        assert self._inputs(graph).wage_value_pairs == ()

    def test_inactive_node_skipped(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0, v_produced=5.0, active=False)
        assert self._inputs(graph).wage_value_pairs == ()

    def test_no_pairs_when_no_accounting_attrs(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        assert self._inputs(graph).wage_value_pairs == ()


class TestGraphInputIdPairs:
    """`_build_graph_inputs` carries node ids beside the float pairs (Program 19).

    The id-carrying fields feed the per-node pole measures; they are built in
    the SAME loops as the float pairs, so every skip rule (inactive endpoint,
    missing attr) applies identically to both.
    """

    @staticmethod
    def _inputs(graph: BabylonGraph):  # type: ignore[no-untyped-def]

        return ContradictionSystem()._build_graph_inputs(graph)

    def test_exploitation_id_pairs_carry_endpoint_ids(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        assert self._inputs(graph).exploitation_id_pairs == (("worker", "owner", 10.0, 30.0),)

    def test_wage_value_id_pairs_carry_node_id(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0, v_produced=5.0)
        assert self._inputs(graph).wage_value_id_pairs == (("c1", 6.0, 5.0),)

    def test_tenancy_id_pairs_carry_endpoint_ids(self) -> None:
        graph = BabylonGraph()
        graph.add_node("tenant", wealth=10.0)
        graph.add_node("land", node_type="territory", rent_level=4.0)
        graph.add_edge("tenant", "land", edge_type=EdgeType.TENANCY)
        assert self._inputs(graph).tenancy_id_pairs == (("tenant", "land", 10.0, 4.0),)

    def test_id_pairs_respect_the_same_skip_rules(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0, active=False)
        graph.add_node("owner", wealth=30.0)
        graph.add_node("ghost", w_paid=6.0, v_produced=5.0, active=False)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        inputs = self._inputs(graph)
        assert inputs.exploitation_id_pairs == ()
        assert inputs.wage_value_id_pairs == ()


class TestShadowPartition:
    """Program 19 Phase 1 (ADR070): the shadow partition node attrs + stash.

    The system writes ``sigma_capital_labor``/``sigma_wage`` per positioned
    node and ``derived_class_cell`` only when BOTH axes are positioned; the
    full per-node channel (including ``imperial``) is stashed on the
    ``pole_readings`` graph attribute — this tick's snapshot and next tick's
    tie-inertia source. UNPOSITIONED nodes are untouched (III.11: absence
    over fabrication); a node that LOSES its position gets honest ``None``.
    Zero adjudication reads any of this in Phase 1 — shadow only.
    """

    @staticmethod
    def _graph() -> BabylonGraph:
        # worker: exploited (source, capital dominant) AND underpaid (w<v).
        # owner: exploiter (target) AND overpaid (w>v) — the imperial bribe.
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0, w_paid=2.0, v_produced=18.0)
        graph.add_node("owner", wealth=30.0, w_paid=18.0, v_produced=2.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        return graph

    def test_sigma_attrs_written_per_positioned_axis(self) -> None:
        graph = self._graph()
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})
        assert graph.nodes["worker"]["sigma_capital_labor"] == pytest.approx(-0.5)
        assert graph.nodes["worker"]["sigma_wage"] == pytest.approx(-0.8)
        assert graph.nodes["owner"]["sigma_capital_labor"] == pytest.approx(0.5)
        assert graph.nodes["owner"]["sigma_wage"] == pytest.approx(0.8)

    def test_derived_class_cell_requires_both_axes(self) -> None:
        graph = self._graph()
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})
        assert graph.nodes["worker"]["derived_class_cell"] == "labor:exploited"
        assert graph.nodes["owner"]["derived_class_cell"] == "capital:bribed"

    def test_single_axis_node_gets_sigma_but_no_cell(self) -> None:
        graph = BabylonGraph()
        graph.add_node("solo", w_paid=18.0, v_produced=2.0)  # wage axis only
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})
        attrs = graph.nodes["solo"]
        assert attrs["sigma_wage"] == pytest.approx(0.8)
        assert "sigma_capital_labor" not in attrs
        assert "derived_class_cell" not in attrs

    def test_unpositioned_node_is_untouched(self) -> None:
        graph = self._graph()
        graph.add_node("bystander", wealth=5.0)
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})
        attrs = graph.nodes["bystander"]
        assert "sigma_capital_labor" not in attrs
        assert "sigma_wage" not in attrs
        assert "derived_class_cell" not in attrs

    def test_pole_readings_stashed_on_graph_attr(self) -> None:
        graph = self._graph()
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})
        stash = graph.graph["pole_readings"]
        assert set(stash) == {"capital_labor", "imperial", "wage"}
        assert stash["capital_labor"]["worker"]["side"] == "a"
        assert stash["imperial"]["owner"]["side"] == "b"  # core pole via the bribe
        assert stash["wage"]["worker"]["sigma"] == pytest.approx(-0.8)

    def test_zero_sigma_holds_previous_side_across_ticks(self) -> None:
        graph = self._graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        system.step(graph, services, {"tick": 1})  # owner: capital side (b)

        graph.update_node("worker", wealth=30.0)  # parity -> sigma 0.0 -> tie
        system.step(graph, services, {"tick": 2})

        stash = graph.graph["pole_readings"]
        assert stash["capital_labor"]["owner"]["sigma"] == pytest.approx(0.0)
        assert stash["capital_labor"]["owner"]["side"] == "b"  # held, not reset to a

    def test_depositioned_node_gets_honest_none(self) -> None:
        graph = self._graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        system.step(graph, services, {"tick": 1})

        graph.update_node("worker", active=False)  # drops out of every axis
        system.step(graph, services, {"tick": 2})

        attrs = graph.nodes["worker"]
        assert attrs["sigma_capital_labor"] is None
        assert attrs["sigma_wage"] is None
        assert attrs["derived_class_cell"] is None
