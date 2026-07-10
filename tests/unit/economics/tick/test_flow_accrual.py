"""Tests for TickDynamicsSystem per-tick flow accrual (spec-109 A7, owner item 25 pt.2).

Binding design (Option B, owner-approved): between year boundaries, the annual
pipeline stays flat for LEVELS/RATES/ENUMS (``tick_capital_stock``,
``tick_median_wage`` itself, ``tick_class_distribution``, ...) — those are
annual-resolution facts (QCEW/BEA) and interpolating them mid-year would
fabricate sub-annual observations (Constitution III.11). Only FLOW quantities
(the county's imperial rent and wage bill, both naturally annual totals)
accrue per tick, at ``annual_value / WEEKS_PER_YEAR``, mirroring the
``ImperialRentSystem`` / ``distribute_phi_week_to_counties`` precedent
(annual-rate-divided-by-weeks-per-year is already how every other per-tick
economic flow in this engine works).

The accrual lands in a DISTINCT ``flow_``-prefixed attr namespace so the
boundary-authoritative ``tick_`` values are never clobbered between
boundaries, and so a year-boundary recompute can reset/true-up the counter
with no double-counting (see ``TestBoundaryCloseOutAndReset``).
"""

from __future__ import annotations

import pytest

from babylon.economics.tick.system import TickDynamicsSystem
from babylon.engine.context import TickContext
from babylon.engine.graph import BabylonGraph
from babylon.formulas.constants import HOURS_PER_YEAR, WEEKS_PER_YEAR
from tests.unit.economics.tick.conftest import WAYNE_FIPS
from tests.unit.economics.tick.test_system import _make_graph_with_state, _make_services

# A T-labelled node distinct from the real FIPS (the b57faee6 shape).
T_LABEL = "T001"


def _territory_with_boundary_state(
    graph: BabylonGraph,
    node_id: str = T_LABEL,
    *,
    phi_hour: float = 3.5,
    median_wage: float = 21.0,
    employment: float = 500_000.0,
) -> None:
    """Add a territory node carrying boundary-authoritative ``tick_`` state.

    Mirrors what ``write_tick_state_to_graph`` would have stamped at the last
    year boundary (or what session bootstrap would have stamped) — the
    precondition ``_accrue_flows``/``_reset_flow_accrual`` read.
    """
    graph.add_node(
        node_id,
        _node_type="territory",
        county_fips=WAYNE_FIPS,
        tick_phi_hour=phi_hour,
        tick_median_wage=median_wage,
        tick_employment=employment,
        tick_capital_stock=1.0e9,  # a LEVEL — must stay untouched by flow accrual
    )


@pytest.mark.unit
class TestAccrueFlowsEmptyDomain:
    """No boundary state yet -> silent no-op (Constitution III.11: empty domain,
    not a Loud Failure — a fresh session/scenario with no prior annual
    computation genuinely has no flow to derive yet)."""

    def test_no_op_on_empty_graph(self) -> None:
        graph = BabylonGraph()
        system = TickDynamicsSystem()

        system._accrue_flows(graph)  # must not raise

        assert list(graph.query_nodes()) == []

    def test_no_op_when_territory_has_no_boundary_state(self) -> None:
        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory", county_fips=WAYNE_FIPS)
        system = TickDynamicsSystem()

        system._accrue_flows(graph)

        assert "flow_phi_accrued" not in graph.nodes[T_LABEL]
        assert "flow_wage_accrued" not in graph.nodes[T_LABEL]

    def test_non_territory_nodes_are_skipped(self) -> None:
        graph = BabylonGraph()
        graph.add_node("prole_1", _node_type="social_class", tick_phi_hour=99.0)
        system = TickDynamicsSystem()

        system._accrue_flows(graph)

        assert "flow_phi_accrued" not in graph.nodes["prole_1"]


@pytest.mark.unit
class TestAccrueFlowsSlice:
    """One call = one 1/WEEKS_PER_YEAR slice of the implied annual total."""

    def test_first_call_writes_one_slice_of_phi(self) -> None:
        graph = BabylonGraph()
        _territory_with_boundary_state(graph, phi_hour=3.5)
        system = TickDynamicsSystem()

        system._accrue_flows(graph)

        annual_phi = 3.5 * HOURS_PER_YEAR
        assert graph.nodes[T_LABEL]["flow_phi_accrued"] == pytest.approx(
            annual_phi / WEEKS_PER_YEAR
        )

    def test_first_call_writes_one_slice_of_wages(self) -> None:
        graph = BabylonGraph()
        _territory_with_boundary_state(graph, median_wage=21.0, employment=500_000.0)
        system = TickDynamicsSystem()

        system._accrue_flows(graph)

        annual_wage = 21.0 * HOURS_PER_YEAR * 500_000.0
        assert graph.nodes[T_LABEL]["flow_wage_accrued"] == pytest.approx(
            annual_wage / WEEKS_PER_YEAR
        )

    def test_second_call_adds_a_second_slice(self) -> None:
        graph = BabylonGraph()
        _territory_with_boundary_state(graph)
        system = TickDynamicsSystem()

        system._accrue_flows(graph)
        first = graph.nodes[T_LABEL]["flow_phi_accrued"]
        system._accrue_flows(graph)
        second = graph.nodes[T_LABEL]["flow_phi_accrued"]

        assert second == pytest.approx(2 * first)
        assert second > first  # the visible G3 symptom: the value MOVES

    def test_does_not_mutate_boundary_authoritative_tick_attrs(self) -> None:
        """Flow accrual writes only ``flow_``-prefixed attrs — the annual
        ``tick_`` facts (levels/rates/enums) stay flat between boundaries."""
        graph = BabylonGraph()
        _territory_with_boundary_state(graph)
        before = dict(graph.nodes[T_LABEL])
        system = TickDynamicsSystem()

        system._accrue_flows(graph)

        for key in ("tick_phi_hour", "tick_median_wage", "tick_employment", "tick_capital_stock"):
            assert graph.nodes[T_LABEL][key] == before[key]

    def test_multiple_territories_accrue_independently(self) -> None:
        graph = BabylonGraph()
        _territory_with_boundary_state(graph, node_id="T001", phi_hour=3.5)
        _territory_with_boundary_state(graph, node_id="T002", phi_hour=7.0)
        system = TickDynamicsSystem()

        system._accrue_flows(graph)

        assert graph.nodes["T002"]["flow_phi_accrued"] == pytest.approx(
            2 * graph.nodes["T001"]["flow_phi_accrued"]
        )


@pytest.mark.unit
class TestResetFlowAccrual:
    def test_zeroes_existing_accrual(self) -> None:
        graph = BabylonGraph()
        _territory_with_boundary_state(graph)
        system = TickDynamicsSystem()
        system._accrue_flows(graph)
        assert graph.nodes[T_LABEL]["flow_phi_accrued"] > 0

        system._reset_flow_accrual(graph)

        assert graph.nodes[T_LABEL]["flow_phi_accrued"] == 0.0
        assert graph.nodes[T_LABEL]["flow_wage_accrued"] == 0.0

    def test_no_op_without_boundary_state(self) -> None:
        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory", county_fips=WAYNE_FIPS)
        system = TickDynamicsSystem()

        system._reset_flow_accrual(graph)

        assert "flow_phi_accrued" not in graph.nodes[T_LABEL]


@pytest.mark.unit
class TestConservation:
    """The load-bearing invariant: WEEKS_PER_YEAR slices sum to the annual
    total with no drift at the boundary true-up (binding design point 5)."""

    def test_fifty_two_ticks_of_phi_sum_to_the_annual_total(self) -> None:
        graph = BabylonGraph()
        phi_hour = 3.5
        _territory_with_boundary_state(graph, phi_hour=phi_hour)
        system = TickDynamicsSystem()

        for _ in range(WEEKS_PER_YEAR):
            system._accrue_flows(graph)

        annual_phi = phi_hour * HOURS_PER_YEAR
        # Tolerance: WEEKS_PER_YEAR float additions of a fixed-magnitude
        # slice: worst-case ULP drift is O(WEEKS_PER_YEAR) * epsilon relative
        # to the running magnitude — see test_value_conservation.py's
        # tolerance-derivation style for the same accumulation shape.
        tol = max(1e-9, 1e-13 * abs(annual_phi))
        assert graph.nodes[T_LABEL]["flow_phi_accrued"] == pytest.approx(annual_phi, abs=tol)

    def test_fifty_two_ticks_of_wages_sum_to_the_annual_total(self) -> None:
        graph = BabylonGraph()
        median_wage, employment = 21.0, 500_000.0
        _territory_with_boundary_state(graph, median_wage=median_wage, employment=employment)
        system = TickDynamicsSystem()

        for _ in range(WEEKS_PER_YEAR):
            system._accrue_flows(graph)

        annual_wage = median_wage * HOURS_PER_YEAR * employment
        tol = max(1e-6, 1e-13 * abs(annual_wage))
        assert graph.nodes[T_LABEL]["flow_wage_accrued"] == pytest.approx(annual_wage, abs=tol)

    def test_close_out_then_reset_completes_one_year_at_exactly_annual_total(self) -> None:
        """51 non-boundary slices + 1 boundary close-out slice = WEEKS_PER_YEAR
        slices = the full annual total, then reset zeroes for the new year —
        the exact sequence ``step()`` runs across one 52-tick year."""
        graph = BabylonGraph()
        phi_hour = 3.5
        _territory_with_boundary_state(graph, phi_hour=phi_hour)
        system = TickDynamicsSystem()

        for _ in range(WEEKS_PER_YEAR - 1):  # ticks 1..51 (non-boundary)
            system._accrue_flows(graph)
        system._accrue_flows(graph)  # tick 52's close-out slice (pre-recompute)

        annual_phi = phi_hour * HOURS_PER_YEAR
        tol = max(1e-9, 1e-13 * abs(annual_phi))
        assert graph.nodes[T_LABEL]["flow_phi_accrued"] == pytest.approx(annual_phi, abs=tol)

        system._reset_flow_accrual(graph)  # tick 52's post-recompute reset

        assert graph.nodes[T_LABEL]["flow_phi_accrued"] == 0.0


@pytest.mark.unit
class TestStepWiresFlowAccrual:
    """Integration through the public ``step()`` entrypoint."""

    def test_non_boundary_tick_accrues_flow_without_touching_tick_attrs(self) -> None:
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()  # WAYNE_FIPS, phi_hour=3.50, tick=year 2015 state
        context = TickContext(tick=1)

        old_k = graph.nodes[WAYNE_FIPS]["tick_capital_stock"]
        system.step(graph, services, context)

        assert graph.nodes[WAYNE_FIPS]["tick_capital_stock"] == pytest.approx(old_k)
        annual_phi = 3.50 * HOURS_PER_YEAR
        assert graph.nodes[WAYNE_FIPS]["flow_phi_accrued"] == pytest.approx(
            annual_phi / WEEKS_PER_YEAR
        )

    def test_successive_non_boundary_ticks_move_the_flow_value(self) -> None:
        """The G3 symptom, at the ``step()`` level: the value MOVES tick over tick."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()

        system.step(graph, services, TickContext(tick=1))
        after_tick_1 = graph.nodes[WAYNE_FIPS]["flow_phi_accrued"]
        system.step(graph, services, TickContext(tick=2))
        after_tick_2 = graph.nodes[WAYNE_FIPS]["flow_phi_accrued"]

        assert after_tick_2 > after_tick_1

    def test_boundary_tick_resets_flow_after_recompute(self) -> None:
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        # Pretend 51 non-boundary ticks already ran this year.
        for _ in range(WEEKS_PER_YEAR - 1):
            system._accrue_flows(graph)
        assert graph.nodes[WAYNE_FIPS]["flow_phi_accrued"] > 0

        system.step(graph, services, TickContext(tick=WEEKS_PER_YEAR))

        # Recompute succeeded (calculators wired) -> reset ran.
        assert graph.nodes[WAYNE_FIPS]["flow_phi_accrued"] == 0.0

    def test_boundary_tick_with_no_calculators_still_closes_out_but_does_not_reset(self) -> None:
        """When ``melt_calculator`` is None the annual recompute never runs
        (unchanged legacy behavior) — but the close-out call already ran
        before that check, so a pre-existing flow is trued up, not silently
        dropped, and NOT reset (there is no new year to reset into)."""
        system = TickDynamicsSystem()
        services = _make_services(melt_calculator=None)
        graph = _make_graph_with_state()

        system.step(graph, services, TickContext(tick=WEEKS_PER_YEAR))

        annual_phi = 3.50 * HOURS_PER_YEAR
        assert graph.nodes[WAYNE_FIPS]["flow_phi_accrued"] == pytest.approx(
            annual_phi / WEEKS_PER_YEAR
        )

    def test_calculator_free_scenario_with_no_territories_is_untouched(self) -> None:
        """Byte-identical guard for qa:regression's 5 abstract scenarios:
        no territory nodes at all -> _accrue_flows is a true no-op, zero
        graph mutations, at both boundary and non-boundary ticks."""
        system = TickDynamicsSystem()
        services = _make_services(melt_calculator=None)
        graph = BabylonGraph()
        graph.add_node("P_W", _node_type="social_class", wealth=5.0)

        system.step(graph, services, TickContext(tick=1))
        system.step(graph, services, TickContext(tick=WEEKS_PER_YEAR))

        assert set(graph.nodes["P_W"].keys()) == {"_node_type", "wealth"}
