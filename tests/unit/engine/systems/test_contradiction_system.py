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
from babylon.domain.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
)
from babylon.domain.dialectics.instances.catalog import GraphInputs
from babylon.domain.economics.working_day.types import WorkingDayState
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import (
    FUNDAMENTAL_THEOREM_ATTR,
    OPPOSITION_INTERVENTIONS_ATTR,
    ContradictionSystem,
)
from babylon.models.enums import EdgeType, EventType, NodeType
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

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        # |30 - 10| / (10 + 30) = 0.5, fresh (not the 0.0 it started at).
        assert graph["worker"]["owner"]["tension"] == pytest.approx(0.5)

    def test_tension_is_not_accumulated_across_ticks(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION, tension=0.0)
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, TickContext(tick=1))
        first = graph["worker"]["owner"]["tension"]
        system.step(graph, services, TickContext(tick=2))
        second = graph["worker"]["owner"]["tension"]

        # Static graph -> identical gap both ticks (no add-only accumulation).
        assert first == pytest.approx(0.5)
        assert second == pytest.approx(0.5)

    def test_tenancy_rent_free_guard_gives_zero_tension(self) -> None:
        graph = BabylonGraph()
        graph.add_node("tenant", wealth=10.0)
        graph.add_node("land", node_type="territory", rent_level=0.0)
        graph.add_edge("tenant", "land", edge_type=EdgeType.TENANCY, tension=0.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        assert graph["tenant"]["land"]["tension"] == pytest.approx(0.0)


class TestRegistryStash:
    """The registry snapshot lands on the graph attribute ``opposition_states``."""

    def test_opposition_states_written_to_graph_attr(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=3))

        states = graph.graph["opposition_states"]
        # price_value joined the canonical channel in ADR078 (zero-gap here:
        # this graph carries no market axis); the four Vol III money axes
        # joined in U5.2 (zero-gap here: this graph carries no Vol III data).
        assert set(states) == {
            "capital_labor",
            "wage",
            "tenancy",
            "atomization",
            "imperial",
            "price_value",
            "surplus_distribution",
            "debt_spiral",
            "credit",
            "financial",
        }
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

        system.step(graph, services, TickContext(tick=1))
        assert graph.graph["opposition_states"]["capital_labor"]["rate"] == pytest.approx(0.0)

        # Widen the gap: owner richer -> gap rises -> rate > 0.
        graph.nodes["owner"]["wealth"] = 90.0
        system.step(graph, services, TickContext(tick=2))
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

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

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
        system.step(graph, services, TickContext(tick=1))
        system.step(graph, services, TickContext(tick=2))
        assert _rupture_events(services) == []

    def test_rupture_fires_when_gap_high_and_rising(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._extreme_graph(50.0)  # gap = 49/51 ~ 0.96 (rate 0 on tick 1)
        system.step(graph, services, TickContext(tick=1))
        assert _rupture_events(services) == []  # rising gate not yet satisfied

        graph.nodes["owner"]["wealth"] = 200.0  # gap = 199/201 ~ 0.99, rate > 0
        system.step(graph, services, TickContext(tick=2))
        ruptures = _rupture_events(services)
        assert len(ruptures) == 1
        assert ruptures[0].payload["opposition"] == "capital_labor"
        assert ruptures[0].payload["gap"] > 0.9
        assert ruptures[0].payload["rate"] > 0.0

    def test_no_rupture_when_gap_high_but_falling(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._extreme_graph(200.0)  # gap ~ 0.99
        system.step(graph, services, TickContext(tick=1))
        graph.nodes["owner"]["wealth"] = 100.0  # gap ~ 0.98, falling -> rate < 0
        system.step(graph, services, TickContext(tick=2))
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
        system.step(graph, services, TickContext(tick=1))
        graph.nodes["owner"]["wealth"] = 14.0  # gap 0.09 -> 0.17: rising, far below 0.9
        system.step(graph, services, TickContext(tick=2))
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
        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "a"

    def test_intervention_flips_leading_pole_through_the_system(self) -> None:
        graph = self._labor_dominant_graph()
        graph.graph[OPPOSITION_INTERVENTIONS_ATTR] = [self._dump(1.0)]

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        cap = graph.graph["opposition_states"]["capital_labor"]
        assert cap["leading_pole"] == "b"  # flipped from "a" by the +1.0 shove
        assert cap["balance"] == pytest.approx(0.5)  # clamp(-0.5 + 1.0)

    def test_interventions_are_consumed_once(self) -> None:
        graph = self._labor_dominant_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph.graph[OPPOSITION_INTERVENTIONS_ATTR] = [self._dump(1.0)]

        system.step(graph, services, TickContext(tick=1))
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "b"
        assert graph.graph[OPPOSITION_INTERVENTIONS_ATTR] == []  # cleared after use

        # Tick 2 with no fresh interventions: fresh measure only, NOT re-applied.
        system.step(graph, services, TickContext(tick=2))
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "a"


class TestWageValuePairsExtraction:
    """`_build_graph_inputs` lifts (w_paid, v_produced) off paid class nodes (D4)."""

    @staticmethod
    def _inputs(graph: BabylonGraph):  # type: ignore[no-untyped-def]

        return ContradictionSystem()._build_graph_inputs(graph, ServiceContainer.create())

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


class _FixedProductivitySource:
    """Minimal ``productivity_data_source`` double: a fixed state, any args."""

    def __init__(self, state: WorkingDayState | None) -> None:
        self._state = state

    def get_working_day_state(
        self, fips_code: str, naics_sector: str, year: int
    ) -> WorkingDayState | None:
        return self._state


class TestVolumeOneProductionRatios:
    """`_build_graph_inputs` derives Vol I U6's two new ``GraphInputs`` ratios.

    ``wealth_subsistence_ratio`` (``value_usevalue``, Ch. 1) and
    ``surplus_strategy_ratio`` (``absolute_relative_surplus``, Chs. 10/12/15).
    """

    @staticmethod
    def _inputs(
        graph: BabylonGraph,
        services: ServiceContainer | None = None,
        tick: int = 0,
    ):  # type: ignore[no-untyped-def]
        return ContradictionSystem()._build_graph_inputs(
            graph, services if services is not None else ServiceContainer.create(), tick
        )

    def test_wealth_subsistence_ratio_is_a_ratio_of_sums(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "c1", node_type=NodeType.SOCIAL_CLASS, wealth=30.0, subsistence_threshold=10.0
        )
        graph.add_node(
            "c2", node_type=NodeType.SOCIAL_CLASS, wealth=10.0, subsistence_threshold=10.0
        )
        ratio = self._inputs(graph).wealth_subsistence_ratio
        assert ratio == pytest.approx(2.0)  # (30+10) / (10+10)

    def test_wealth_subsistence_ratio_skips_inactive_and_non_class_nodes(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "c1",
            node_type=NodeType.SOCIAL_CLASS,
            wealth=30.0,
            subsistence_threshold=10.0,
            active=False,
        )
        # `subsistence_threshold` deliberately omitted here: Territory declares no such
        # field (vocabulary sentinel, check:vocabulary) and _wealth_subsistence_ratio's
        # own graph.query_nodes(node_type=SOCIAL_CLASS) filter excludes this node by
        # TYPE alone -- any attribute it carried would be irrelevant to what this test
        # proves (a non-class node's wealth never contributes to the ratio).
        graph.add_node("land", node_type=NodeType.TERRITORY, wealth=1000.0)
        assert self._inputs(graph).wealth_subsistence_ratio is None

    def test_wealth_subsistence_ratio_none_when_no_classes(self) -> None:
        assert self._inputs(BabylonGraph()).wealth_subsistence_ratio is None

    def test_surplus_strategy_ratio_unwired_is_none(self) -> None:
        assert self._inputs(BabylonGraph()).surplus_strategy_ratio is None

    def test_surplus_strategy_ratio_wired_from_productivity_data_source(self) -> None:
        # avg_weekly_hours == the default relative_hours_threshold (40.0),
        # intensity at its own baseline (1.0) -> ratio exactly at parity.
        state = WorkingDayState(
            fips_code="00000",
            naics_sector="00",
            year=2022,
            avg_weekly_hours=40.0,
            labor_intensity_index=1.0,
        )
        services = ServiceContainer.create(productivity_data_source=_FixedProductivitySource(state))
        ratio = self._inputs(BabylonGraph(), services, tick=0).surplus_strategy_ratio
        assert ratio == pytest.approx(1.0)


class TestGraphInputIdPairs:
    """`_build_graph_inputs` carries node ids beside the float pairs (Program 19).

    The id-carrying fields feed the per-node pole measures; they are built in
    the SAME loops as the float pairs, so every skip rule (inactive endpoint,
    missing attr) applies identically to both.
    """

    @staticmethod
    def _inputs(graph: BabylonGraph):  # type: ignore[no-untyped-def]

        return ContradictionSystem()._build_graph_inputs(graph, ServiceContainer.create())

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


class TestFundamentalTheoremStash:
    """U2 (Vol I value-production program): the Fundamental Theorem, computed.

    ``_step_registry`` reuses the SAME ``wage_value_id_pairs`` triples
    ``_build_graph_inputs`` already extracts for the ``wage``/``imperial``
    oppositions (Phase D4) — zero new graph traversal — and stashes one
    :class:`ClassPhiReading` per paid class node on the
    ``fundamental_theorem`` graph attribute.
    """

    def test_stash_written_for_paid_class_nodes(self) -> None:
        graph = BabylonGraph()
        graph.add_node("owner", wealth=30.0, w_paid=120.0, v_produced=100.0)
        graph.add_node("worker", wealth=10.0, w_paid=60.0, v_produced=100.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        report = graph.graph[FUNDAMENTAL_THEOREM_ATTR]
        assert set(report.keys()) == {"owner", "worker"}
        assert report["owner"]["phi_absolute"] == pytest.approx(20.0)
        assert report["owner"]["is_labor_aristocracy"] is True
        assert report["worker"]["phi_absolute"] == pytest.approx(-40.0)
        assert report["worker"]["is_labor_aristocracy"] is False

    def test_stash_omits_unpaid_nodes(self) -> None:
        graph = BabylonGraph()
        graph.add_node("bystander", wealth=5.0)  # no w_paid/v_produced

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        assert graph.graph[FUNDAMENTAL_THEOREM_ATTR] == {}

    def test_stash_recomputed_fresh_each_tick(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0, v_produced=5.0)
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, TickContext(tick=1))
        first = graph.graph[FUNDAMENTAL_THEOREM_ATTR]["c1"]["phi_absolute"]

        graph.update_node("c1", w_paid=9.0, v_produced=5.0)
        system.step(graph, services, TickContext(tick=2))
        second = graph.graph[FUNDAMENTAL_THEOREM_ATTR]["c1"]["phi_absolute"]

        assert first == pytest.approx(1.0)
        assert second == pytest.approx(4.0)

    def test_phi_absolute_resolved_from_the_formula_registry(self) -> None:
        """``_stash_fundamental_theorem`` injects ``services.formulas.get(
        "phi_absolute")`` rather than relying on
        ``compute_fundamental_theorem``'s own direct-import default — the
        registered formula is a genuine, hot-swappable production
        dependency, not a registered-but-unconsumed entry (spec §6.2).
        Proven by swapping in an obviously-different callable and checking
        the stash reflects IT."""
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=120.0, v_produced=100.0)
        services = ServiceContainer.create()
        services.formulas.register("phi_absolute", lambda w, v: 2.0 * w - v)

        ContradictionSystem().step(graph, services, TickContext(tick=1))

        # 2*120 - 100 = 140, NOT the real formula's 120-100=20.
        assert graph.graph[FUNDAMENTAL_THEOREM_ATTR]["c1"]["phi_absolute"] == pytest.approx(140.0)


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
        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))
        assert graph.nodes["worker"]["sigma_capital_labor"] == pytest.approx(-0.5)
        assert graph.nodes["worker"]["sigma_wage"] == pytest.approx(-0.8)
        assert graph.nodes["owner"]["sigma_capital_labor"] == pytest.approx(0.5)
        assert graph.nodes["owner"]["sigma_wage"] == pytest.approx(0.8)

    def test_derived_class_cell_requires_both_axes(self) -> None:
        graph = self._graph()
        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))
        assert graph.nodes["worker"]["derived_class_cell"] == "labor:exploited"
        assert graph.nodes["owner"]["derived_class_cell"] == "capital:bribed"

    def test_single_axis_node_gets_sigma_but_no_cell(self) -> None:
        graph = BabylonGraph()
        graph.add_node("solo", w_paid=18.0, v_produced=2.0)  # wage axis only
        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))
        attrs = graph.nodes["solo"]
        assert attrs["sigma_wage"] == pytest.approx(0.8)
        assert "sigma_capital_labor" not in attrs
        assert "derived_class_cell" not in attrs

    def test_unpositioned_node_is_untouched(self) -> None:
        graph = self._graph()
        graph.add_node("bystander", wealth=5.0)
        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))
        attrs = graph.nodes["bystander"]
        assert "sigma_capital_labor" not in attrs
        assert "sigma_wage" not in attrs
        assert "derived_class_cell" not in attrs

    def test_pole_readings_stashed_on_graph_attr(self) -> None:
        graph = self._graph()
        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))
        stash = graph.graph["pole_readings"]
        # price_value joined the shared-defect pole family in ADR078.
        assert set(stash) == {"capital_labor", "imperial", "price_value", "wage"}
        assert stash["capital_labor"]["worker"]["side"] == "a"
        assert stash["imperial"]["owner"]["side"] == "b"  # core pole via the bribe
        assert stash["wage"]["worker"]["sigma"] == pytest.approx(-0.8)

    def test_zero_sigma_holds_previous_side_across_ticks(self) -> None:
        graph = self._graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        system.step(graph, services, TickContext(tick=1))  # owner: capital side (b)

        graph.update_node("worker", wealth=30.0)  # parity -> sigma 0.0 -> tie
        system.step(graph, services, TickContext(tick=2))

        stash = graph.graph["pole_readings"]
        assert stash["capital_labor"]["owner"]["sigma"] == pytest.approx(0.0)
        assert stash["capital_labor"]["owner"]["side"] == "b"  # held, not reset to a

    def test_depositioned_node_gets_honest_none(self) -> None:
        graph = self._graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        system.step(graph, services, TickContext(tick=1))

        graph.update_node("worker", active=False)  # drops out of every axis
        system.step(graph, services, TickContext(tick=2))

        attrs = graph.nodes["worker"]
        assert attrs["sigma_capital_labor"] is None
        assert attrs["sigma_wage"] is None
        assert attrs["derived_class_cell"] is None


class TestShadowChannel:
    """Shadow opposition states ride their own graph attr (ADR077, Program 23)."""

    @staticmethod
    def _registry_with_shadow() -> OppositionRegistry[GraphInputs]:
        canon = BoundOpposition(
            spec=OppositionSpec(key="canon", pole_a="a-pole", pole_b="b-pole"),
            measure=lambda _inputs: GapReading(gap=0.4, balance=-0.2),
        )
        ghost = BoundOpposition(
            spec=OppositionSpec(key="ghost", pole_a="a-pole", pole_b="b-pole"),
            measure=lambda _inputs: GapReading(gap=0.9, balance=0.5),
            shadow=True,
        )
        return OppositionRegistry(bindings=[canon, ghost])

    def _services(self) -> ServiceContainer:
        return ServiceContainer.create(opposition_registry=self._registry_with_shadow())

    @staticmethod
    def _graph() -> BabylonGraph:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        return graph

    def test_shadow_states_land_on_their_own_attr(self) -> None:
        graph = self._graph()
        ContradictionSystem().step(graph, self._services(), TickContext(tick=1))
        assert set(graph.graph["opposition_states"]) == {"canon"}
        assert set(graph.graph["shadow_opposition_states"]) == {"ghost"}
        assert graph.graph["shadow_opposition_states"]["ghost"]["gap"] == pytest.approx(0.9)
        assert graph.graph["shadow_opposition_states"]["ghost"]["is_principal"] is False

    def test_shadow_rate_continuity_through_shadow_attr(self) -> None:
        graph = self._graph()
        services = self._services()
        system = ContradictionSystem()
        system.step(graph, services, TickContext(tick=1))
        # Perturb the stashed shadow gap so tick 2's rate must read it back.
        stash = dict(graph.graph["shadow_opposition_states"])
        stash["ghost"] = {**stash["ghost"], "gap": 0.6}
        graph.set_graph_attr("shadow_opposition_states", stash)
        system.step(graph, services, TickContext(tick=2))
        assert graph.graph["shadow_opposition_states"]["ghost"]["rate"] == pytest.approx(0.3)

    def test_frames_never_name_a_shadow_key(self) -> None:
        graph = self._graph()
        ContradictionSystem().step(graph, self._services(), TickContext(tick=1))
        frame = graph.graph["contradiction_frames"]["global"]
        assert frame["principal"]["id"] == "canon"
        assert frame["secondary"]["id"] == "canon"

    def test_no_shadow_bindings_writes_no_shadow_attr(self) -> None:
        """Pre-ADR077 graphs stay byte-identical: no key unless shadows exist."""
        graph = self._graph()
        canon_only = OppositionRegistry(
            bindings=[
                BoundOpposition(
                    spec=OppositionSpec(key="canon", pole_a="a-pole", pole_b="b-pole"),
                    measure=lambda _inputs: GapReading(gap=0.4, balance=-0.2),
                )
            ]
        )
        services = ServiceContainer.create(opposition_registry=canon_only)
        ContradictionSystem().step(graph, services, TickContext(tick=1))
        assert "shadow_opposition_states" not in graph.graph


class TestPriceValueEndToEnd:
    """Default registry + fresh market axis → CANONICAL state (ADR078)."""

    def test_market_axis_feeds_the_canonical_opposition(self) -> None:
        import math

        from babylon.config.defines import GameDefines

        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        graph.set_graph_attr(
            "market",
            {
                "price_log": 0.5,
                "price_velocity": 0.0,
                "fictitious_log": 0.0,
                "fictitious_velocity": 0.0,
                "surplus_ema": 1.0,
                "value_ema": 2.0,
                "tick": 1,
            },
        )
        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        scale = GameDefines().market.scissors_balance_scale
        # Promotion (ADR078): price_value rides the CANONICAL channel — the
        # sixth opposition, competing for principal. The empty shadow channel
        # writes no attr at all (only-when-present contract).
        states = graph.graph["opposition_states"]
        assert set(states) == {
            "capital_labor",
            "wage",
            "tenancy",
            "atomization",
            "imperial",
            "price_value",
            "surplus_distribution",
            "debt_spiral",
            "credit",
            "financial",
        }
        assert states["price_value"]["balance"] == pytest.approx(math.tanh(0.5 / scale))
        # task #42-C / Vol I U6 / Vol II U5: national, the three
        # production-layer shadow bindings AND the four circulation-layer
        # shadow bindings now register — but this graph builds no FACTION/
        # INFLUENCES data, no social_class-typed nodes, no
        # productivity_data_source and no ``tick_dynamics`` county-layer
        # data, so all eight read the honest absent zero.
        shadow_states = graph.graph["shadow_opposition_states"]
        assert set(shadow_states) == {
            "national",
            "value_usevalue",
            "labor_laborpower",
            "absolute_relative_surplus",
            "circulation",
            "realization",
            "reproduction",
            "disproportionality",
        }
        for key in shadow_states:
            assert shadow_states[key]["gap"] == 0.0
            assert shadow_states[key]["balance"] == 0.0


class TestNationalAxisEndToEnd:
    """Default registry + FACTION/INFLUENCES data → the shadow channel (task #42-C)."""

    def test_no_factions_reads_absent(self) -> None:
        """The 5 canonical scenarios build no BalkanizationFaction at all —
        this is their permanent, by-construction reading."""
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        assert "national" not in graph.graph["opposition_states"]
        national = graph.graph["shadow_opposition_states"]["national"]
        assert national["gap"] == 0.0
        assert national["balance"] == 0.0
        assert national["is_principal"] is False

    def test_faction_stance_feeds_the_shadow_channel(self) -> None:
        """Two factions, weighted by their INFLUENCES reach: UPHOLD (weight
        0.3) and ABOLISH (weight 0.7) over the same Territory. Weighted mean
        chauvinism score = (0.3*1.0 + 0.7*0.0) / 1.0 = 0.3; balance =
        1 - 2*0.3 = 0.4 (internationalism, pole B, leads)."""
        graph = BabylonGraph()
        graph.add_node("HEX_001", NodeType.TERRITORY)
        graph.add_node("FAC_UPHOLD", NodeType.FACTION, colonial_stance="uphold")
        graph.add_node("FAC_ABOLISH", NodeType.FACTION, colonial_stance="abolish")
        graph.add_edge("FAC_UPHOLD", "HEX_001", EdgeType.INFLUENCES, influence_level=0.3)
        graph.add_edge("FAC_ABOLISH", "HEX_001", EdgeType.INFLUENCES, influence_level=0.7)

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        national = graph.graph["shadow_opposition_states"]["national"]
        assert national["balance"] == pytest.approx(0.4)
        assert national["gap"] == pytest.approx(0.4)
        assert national["is_principal"] is False

    def test_zero_influence_faction_contributes_nothing(self) -> None:
        """A faction with no territorial reach carries no weight — the
        intensive-aggregation guard (a lone UPHOLD faction with zero
        influence must not swing the reading against a weighted ABOLISH one)."""
        graph = BabylonGraph()
        graph.add_node("HEX_001", NodeType.TERRITORY)
        graph.add_node("FAC_UNPLACED", NodeType.FACTION, colonial_stance="uphold")
        graph.add_node("FAC_ABOLISH", NodeType.FACTION, colonial_stance="abolish")
        graph.add_edge("FAC_ABOLISH", "HEX_001", EdgeType.INFLUENCES, influence_level=0.5)
        # FAC_UNPLACED has no INFLUENCES edge at all.

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        national = graph.graph["shadow_opposition_states"]["national"]
        assert national["balance"] == pytest.approx(1.0)  # ABOLISH alone -> full internationalism

    def test_unrecognized_stance_is_skipped_not_fabricated(self) -> None:
        graph = BabylonGraph()
        graph.add_node("HEX_001", NodeType.TERRITORY)
        graph.add_node("FAC_BAD", NodeType.FACTION, colonial_stance="not-a-real-stance")
        graph.add_edge("FAC_BAD", "HEX_001", EdgeType.INFLUENCES, influence_level=0.9)

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        national = graph.graph["shadow_opposition_states"]["national"]
        assert national["gap"] == 0.0
        assert national["balance"] == 0.0

    def test_reading_is_order_independent_of_graph_construction(self) -> None:
        """Constitution III.7: the same logical graph, built by inserting its
        three factions (mixed stances, unequal INFLUENCES weights) in a
        different order, must yield a BIT-IDENTICAL ``national`` reading —
        ``==`` on the floats, not ``pytest.approx``. Unsorted float
        accumulation over graph-insertion order is order-sensitive (0.1
        UPHOLD + 0.2 IGNORE + 0.7 ABOLISH sums to a different last bit of
        ``weight_total`` depending on visitation order); sorting both the
        FACTION-node loop and the INFLUENCES-edge loop by id fixes it."""

        def build(order: list[tuple[str, str, float]]) -> BabylonGraph:
            graph = BabylonGraph()
            graph.add_node("HEX_001", NodeType.TERRITORY)
            for faction_id, stance, weight in order:
                graph.add_node(faction_id, NodeType.FACTION, colonial_stance=stance)
                graph.add_edge(faction_id, "HEX_001", EdgeType.INFLUENCES, influence_level=weight)
            return graph

        forward = [
            ("FAC_A", "uphold", 0.1),
            ("FAC_B", "ignore", 0.2),
            ("FAC_C", "abolish", 0.7),
        ]
        graph_forward = build(forward)
        graph_reversed = build(list(reversed(forward)))

        ContradictionSystem().step(graph_forward, ServiceContainer.create(), TickContext(tick=1))
        ContradictionSystem().step(graph_reversed, ServiceContainer.create(), TickContext(tick=1))

        national_forward = graph_forward.graph["shadow_opposition_states"]["national"]
        national_reversed = graph_reversed.graph["shadow_opposition_states"]["national"]

        assert national_forward["balance"] == national_reversed["balance"]
        assert national_forward["gap"] == national_reversed["gap"]

    def test_national_never_feeds_frames_or_rupture(self) -> None:
        """Observe-only (shadow discipline): even a maximally chauvinist
        reading never becomes the principal contradiction or a frame."""
        graph = BabylonGraph()
        graph.add_node("HEX_001", NodeType.TERRITORY)
        graph.add_node("FAC_UPHOLD", NodeType.FACTION, colonial_stance="uphold")
        graph.add_edge("FAC_UPHOLD", "HEX_001", EdgeType.INFLUENCES, influence_level=1.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), TickContext(tick=1))

        assert "national" not in graph.graph["opposition_states"]
        frame = graph.graph["contradiction_frames"]["global"]
        assert frame["principal"]["id"] != "national"
