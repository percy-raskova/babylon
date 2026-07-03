"""Grundrisse cyclical arc against the Lawverian opposition registry (C1.7).

This is the successor of the dormant dialectics layer's Grundrisse 4-cycle
integration test (``tests/unit/engine/dialectics/test_grundrisse_cycle.py``,
retired with ``engine/dialectics/`` per ``project/06-lawverian-dialectics.md``
§5 item 6). The dormant test wired four ``Dialectic`` objects
(Production -> Circulation -> Distribution -> Consumption -> Production) into a
``World`` and asserted that a 10-tick ``tick()`` run evolved state, stayed
bounded, and produced no invariant violations — the Picard fixed-point reading
``W_{n+1} = T(W_n)`` in which each moment reads the *previous* tick's state.

The registry rewrite carries that intent forward, not the machinery. Here the
canonical circuit is a wealth trajectory through the four Grundrisse moments
(Production concentrates surplus in capital; Circulation realizes it;
Distribution pays wages back to labor; Consumption depletes labor's stock), and
:class:`~babylon.engine.systems.contradiction.ContradictionSystem` measures the
resulting contradiction dynamics off the live graph each tick. The behavioral
claims this suite pins (scope C1.7 D):

- **multi-tick step**: the system runs a 10-tick arc, all five catalog
  oppositions present every tick with exactly one principal;
- **gap/rate evolution**: the capital_labor gap develops and — crucially — can
  *fall* during the Distribution moment (it is NOT the old add-only ratchet)
  and is never pinned at the saturating 1.0;
- **previous-tick reading**: the rate at tick ``n`` is ``gap_n - gap_{n-1}``,
  proving the cross-tick snapshot handoff (the fixed-point "reads previous"
  invariant) works through ``ContradictionSystem``'s graph-attr channel;
- **principal selection**: Mao's fast-developing contradiction overtakes a
  larger-but-static one, then cedes the principal role when it stabilizes;
- **rupture gating** (§9.4 "condition AND level"): RUPTURE fires only when the
  principal gap exceeds threshold AND is rising — never on a static extreme.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.models.enums import EdgeType, EventType

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures / helpers — the Grundrisse circuit as a live wealth graph
# ---------------------------------------------------------------------------

_EXPLOITATION = ("worker", "owner")  # source=labor (pole A), target=capital (pole B)
_WAGES = ("employer", "worker2")  # source=employer, target=worker (re-oriented to labor=A)
_TENANCY = ("tenant", "land")  # source=tenant (pole A), target=territory rent_level (pole B)


def _build_circuit_graph() -> nx.DiGraph[str]:
    """A single-county circuit with the three live wealth-asymmetry edges.

    capital_labor starts as the dominant contradiction (gap 0.5); wage
    (0.05) and tenancy (0.25) start subordinate and static so capital_labor
    is the unambiguous principal until a test deliberately perturbs another.
    """
    graph = BabylonGraph()
    graph.add_node("worker", wealth=10.0)
    graph.add_node("owner", wealth=30.0)
    graph.add_node("employer", wealth=21.0)
    graph.add_node("worker2", wealth=19.0)
    graph.add_node("tenant", wealth=10.0)
    graph.add_node("land", node_type="territory", rent_level=6.0)
    graph.add_edge(*_EXPLOITATION, edge_type=EdgeType.EXPLOITATION, tension=0.0)
    graph.add_edge(*_WAGES, edge_type=EdgeType.WAGES, tension=0.0)
    graph.add_edge(*_TENANCY, edge_type=EdgeType.TENANCY, tension=0.0)
    return graph


def _cap_labor(graph: nx.DiGraph[str]) -> dict[str, object]:
    """The capital_labor opposition state stashed after the latest step."""
    return graph.graph["opposition_states"]["capital_labor"]


def _principal_key(graph: nx.DiGraph[str]) -> str:
    """Key of the opposition marked principal this tick."""
    states = graph.graph["opposition_states"]
    return next(key for key, state in states.items() if state["is_principal"])


def _ruptures(services: ServiceContainer) -> list[object]:
    return [e for e in services.event_bus.get_history() if e.type == EventType.RUPTURE]


# The four Grundrisse moments as (worker_delta, owner_delta) on the
# EXPLOITATION pair. Production/Consumption widen the gap (capital gains /
# labor depletes); Distribution narrows it (wages flow back to labor);
# Circulation is pure realization (no stock change). Ten ticks = 2.5 turns.
_GRUNDRISSE_DELTAS: tuple[tuple[float, float], ...] = (
    (0.0, 10.0),  # 1 Production   — surplus accrues to capital
    (0.0, 0.0),  # 2 Circulation  — realization only
    (10.0, 0.0),  # 3 Distribution — wages paid back to labor (gap falls)
    (-5.0, 0.0),  # 4 Consumption  — labor depletes subsistence
    (0.0, 10.0),  # 5 Production
    (0.0, 0.0),  # 6 Circulation
    (10.0, 0.0),  # 7 Distribution
    (-5.0, 0.0),  # 8 Consumption
    (0.0, 10.0),  # 9 Production
    (0.0, 0.0),  # 10 Circulation
)


class TestGrundrisseArc:
    """The 10-tick circuit: all oppositions present, capital_labor leads."""

    def test_ten_tick_cycle_keeps_five_oppositions_and_one_principal(self) -> None:
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        for tick, (dw, do) in enumerate(_GRUNDRISSE_DELTAS, start=1):
            graph.nodes["worker"]["wealth"] += dw
            graph.nodes["owner"]["wealth"] += do
            system.step(graph, services, {"tick": tick})

            states = graph.graph["opposition_states"]
            assert set(states) == {
                "capital_labor",
                "wage",
                "tenancy",
                "atomization",
                "imperial",
            }
            assert sum(1 for s in states.values() if s["is_principal"]) == 1
            assert all(s["tick"] == tick for s in states.values())
            # capital_labor stays the principal contradiction across the arc.
            assert _principal_key(graph) == "capital_labor"

    def test_gap_develops_and_stays_off_the_saturating_ceiling(self) -> None:
        """The core inertness-bug fix: the gap moves and never pins at 1.0."""
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        seen: list[float] = []
        for tick, (dw, do) in enumerate(_GRUNDRISSE_DELTAS, start=1):
            graph.nodes["worker"]["wealth"] += dw
            graph.nodes["owner"]["wealth"] += do
            system.step(graph, services, {"tick": tick})
            seen.append(_cap_labor(graph)["gap"])  # type: ignore[arg-type]

        assert max(seen) < 1.0  # never saturates (the old accumulator pinned here)
        assert min(seen) > 0.0
        assert len({round(g, 6) for g in seen}) > 1  # the gap actually develops


class TestNonRatchetAndPreviousReading:
    """Gaps fall during Distribution; rate reads the previous tick's snapshot."""

    def test_gap_falls_during_distribution(self) -> None:
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        # Baseline moment (10, 30) -> gap 0.5; first step establishes the
        # snapshot the following ticks read for their rate.
        system.step(graph, services, {"tick": 1})
        assert _cap_labor(graph)["gap"] == pytest.approx(0.5)

        # Production moment: capital gains, gap widens, rate > 0.
        graph.nodes["owner"]["wealth"] += 10.0  # (10, 40) -> 0.6
        system.step(graph, services, {"tick": 2})
        after_production = _cap_labor(graph)["gap"]
        assert after_production == pytest.approx(0.6)
        assert _cap_labor(graph)["rate"] == pytest.approx(0.1)  # 0.6 - 0.5

        # Distribution moment: wages flow to labor, gap FALLS, rate < 0.
        graph.nodes["worker"]["wealth"] += 20.0  # (30, 40) -> 1/7
        system.step(graph, services, {"tick": 3})
        assert _cap_labor(graph)["gap"] < after_production  # not a ratchet
        assert _cap_labor(graph)["rate"] < 0.0

    def test_rate_is_gap_delta_from_previous_tick(self) -> None:
        """Picard fixed-point: tick n reads tick n-1 via the graph-attr snapshot."""
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})  # (10, 30) -> gap 0.5, rate 0
        assert _cap_labor(graph)["gap"] == pytest.approx(0.5)
        assert _cap_labor(graph)["rate"] == pytest.approx(0.0)

        graph.nodes["owner"]["wealth"] = 90.0  # (10, 90) -> gap 0.8
        system.step(graph, services, {"tick": 2})
        assert _cap_labor(graph)["gap"] == pytest.approx(0.8)
        assert _cap_labor(graph)["rate"] == pytest.approx(0.3)  # 0.8 - 0.5


class TestPrincipalSelection:
    """Mao: the fast-developing contradiction leads, then cedes when it stalls."""

    def test_fast_developing_wage_overtakes_then_cedes(self) -> None:
        # Phase D5 migrated the wage measure from WAGES-edge endpoint wealth
        # to the true (w_paid, v_produced) defect pair on paid class nodes,
        # and the imperial opposition reads the SAME pairs until real
        # periphery data lands (their gaps are pinned equal by
        # test_value_form_bridged). The overtake is therefore asserted on
        # the wage/imperial defect family, not on "wage" alone — the tie
        # between the twinned measures breaks lexicographically.
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        # Tick 1: baseline — capital_labor (0.5) is principal; the wage
        # defect starts small: w_paid 21 vs v_produced 19 -> |21-19|/40 = 0.05.
        graph.nodes["worker2"]["w_paid"] = 21.0
        graph.nodes["worker2"]["v_produced"] = 19.0
        system.step(graph, services, {"tick": 1})
        assert _principal_key(graph) == "capital_labor"

        # Tick 2: the wage defect jumps 0.05 -> 0.45 (rate 0.40) while
        # capital_labor holds at 0.5 (rate 0). Score = 0.45*(1+10*0.40) =
        # 2.25 beats capital_labor 0.5 -> the fast-developing defect leads.
        graph.nodes["worker2"]["w_paid"] = 29.0
        graph.nodes["worker2"]["v_produced"] = 11.0  # |29-11|/40 = 0.45
        system.step(graph, services, {"tick": 2})
        wage = graph.graph["opposition_states"]["wage"]
        assert wage["gap"] == pytest.approx(0.45)
        assert wage["rate"] == pytest.approx(0.40)
        assert _principal_key(graph) in ("wage", "imperial")

        # Tick 3: the defect holds (rate -> 0), its static gap 0.45 < 0.5
        # -> the principal role returns to capital_labor.
        system.step(graph, services, {"tick": 3})
        assert graph.graph["opposition_states"]["wage"]["rate"] == pytest.approx(0.0)
        assert _principal_key(graph) == "capital_labor"


class TestRuptureGating:
    """RUPTURE requires the principal gap high AND rising (§9.4)."""

    def test_no_rupture_through_the_benign_cycle(self) -> None:
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        for tick, (dw, do) in enumerate(_GRUNDRISSE_DELTAS, start=1):
            graph.nodes["worker"]["wealth"] += dw
            graph.nodes["owner"]["wealth"] += do
            system.step(graph, services, {"tick": tick})
        # Hegemony holds: the pacified circuit never crosses the 0.9 gate.
        assert _ruptures(services) == []

    def test_rupture_fires_once_when_crisis_is_rising_not_when_static(self) -> None:
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        # Two benign ticks (gap ~0.5) — below threshold, no rupture.
        system.step(graph, services, {"tick": 1})
        system.step(graph, services, {"tick": 2})
        assert _ruptures(services) == []

        # Crisis: capital seizes almost everything -> gap 0.98, rising -> RUPTURE.
        graph.nodes["owner"]["wealth"] = 1000.0
        system.step(graph, services, {"tick": 3})
        ruptures = _ruptures(services)
        assert len(ruptures) == 1
        assert ruptures[0].payload["opposition"] == "capital_labor"
        assert ruptures[0].payload["gap"] > 0.9
        assert ruptures[0].payload["rate"] > 0.0

        # Hold the extreme gap static (rate 0): the LEVEL is high but the
        # CONDITION (rising) is not met -> no NEW rupture.
        system.step(graph, services, {"tick": 4})
        assert len(_ruptures(services)) == 1


# ---------------------------------------------------------------------------
# E6 — Grundrisse fixed-point reading (§9.4 port)
# ---------------------------------------------------------------------------


def _regime(graph: nx.DiGraph[str]) -> str:
    """The fixed-point regime ContradictionSystem stashed this tick."""
    return graph.graph["dialectical_regime"]["regime"]  # type: ignore[no-any-return]


# Simple reproduction: the four moments net to ZERO change per cycle, so the
# capital_labor gap is a fixed point of the COMPOSITE map T⁴ (it returns every
# four ticks) while still swinging WITHIN the cycle.
_SIMPLE_REPRODUCTION: tuple[tuple[float, float], ...] = (
    (0.0, 10.0),  # 1 Production   — surplus accrues to capital (gap widens)
    (0.0, 0.0),  # 2 Circulation  — realization only
    (0.0, -10.0),  # 3 Distribution — returned to circulation (gap narrows back)
    (0.0, 0.0),  # 4 Consumption  — no stock change
)


class TestFixedPointReading:
    """§9.4: the tick is one Picard iteration; its convergence IS the regime."""

    def test_orbit_is_a_t4_fixed_point(self) -> None:
        """The simple-reproduction cycle repeats the gap every four ticks."""
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        after_production: list[float] = []
        for turn in range(3):
            for moment, (dw, do) in enumerate(_SIMPLE_REPRODUCTION):
                graph.nodes["worker"]["wealth"] += dw
                graph.nodes["owner"]["wealth"] += do
                system.step(graph, services, {"tick": turn * 4 + moment + 1})
                if moment == 0:  # the Production moment
                    after_production.append(_cap_labor(graph)["gap"])  # type: ignore[arg-type]

        # T⁴ fixed point: the gap at the same moment repeats across turns.
        assert after_production[0] == pytest.approx(after_production[1])
        assert after_production[1] == pytest.approx(after_production[2])

    def test_steady_state_reads_reproduction(self) -> None:
        """A self-reproducing state (W = T(W), rate ~ 0) classifies as reproduction."""
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})  # establish the snapshot
        system.step(graph, services, {"tick": 2})  # no wealth change -> rate ~ 0
        assert _cap_labor(graph)["rate"] == pytest.approx(0.0)
        assert _regime(graph) == "reproduction"

    def test_wage_cut_perturbation_breaks_the_orbit_into_crisis(self) -> None:
        """A wage-cut perturbation (owner seizes wealth) drives the gap up -> crisis."""
        graph = _build_circuit_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})
        assert _regime(graph) == "reproduction"

        graph.nodes["owner"]["wealth"] = 90.0  # (10, 90) -> gap 0.8, rising
        system.step(graph, services, {"tick": 2})
        assert _cap_labor(graph)["rate"] > 0.0
        assert _regime(graph) == "crisis"
