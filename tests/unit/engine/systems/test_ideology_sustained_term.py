"""System-level test for the Task 2 (B) sustained wage-value defect term.

TDD Red Phase: ``ConsciousnessSystem`` does not yet read
``GameDefines.consciousness.sustained_exploitation_sensitivity`` or fold
:func:`~babylon.formulas.sustained_exploitation.
sustained_exploitation_agitation` into ``new_agitation`` (``ideology.py``).

The property under test is exactly the bug named in the spec
(``docs/superpowers/plans/2026-07-18-null-play-political-coupling.md``):
today, once wage/wealth/opposition deltas all reach zero (a material steady
state), ``agitation`` decays to zero and ``class_consciousness`` freezes
forever -- EVEN IF the wage-value defect (``opposition_states["wage"]
["balance"]``) stays persistently negative (labor permanently on the losing
side). This test builds exactly that steady state and asserts consciousness
keeps moving tick over tick.

One-tick lag: ``ConsciousnessSystem`` (@17.0) reads the wage snapshot
``ContradictionSystem`` (@18.0) wrote LAST tick. The test injects
``opposition_states`` directly onto the graph before each ``step()`` call
(as :class:`TestWageOppositionCrisisGate` in ``test_ideology.py`` already
does), which is the correct way to exercise this read given that lag.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.models.entity_registry import LABOR_ARISTOCRACY_ID, PERIPHERY_WORKER_ID
from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph


def _graph_with_worker() -> BabylonGraph:
    """A periphery worker with an incoming SOLIDARITY edge from an already-
    revolutionary source (as ``TestConsciousnessSystemWealthTracking.
    test_wealth_extraction_routes_to_fascism_without_solidarity``'s sibling
    test does in ``test_ideology.py``) -- without this, agitation routes
    entirely to ``national_identity`` (the fascist path, ``solidarity_
    pressure == 0``) and ``class_consciousness`` cannot move at all,
    regardless of how much agitation is generated.
    """
    graph = BabylonGraph()
    graph.add_node(
        PERIPHERY_WORKER_ID,
        wealth=1.0,
        ideology={
            "class_consciousness": 0.5,
            "national_identity": 0.5,
            "agitation": 0.0,
        },
        _node_type="social_class",
    )
    graph.add_node(
        LABOR_ARISTOCRACY_ID,
        wealth=0.5,
        ideology={
            "class_consciousness": 0.9,
            "national_identity": 0.1,
            "agitation": 0.0,
        },
        _node_type="social_class",
    )
    graph.add_edge(
        LABOR_ARISTOCRACY_ID,
        PERIPHERY_WORKER_ID,
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=0.8,
    )
    return graph


def _steady_state_losing_wage_state() -> dict[str, object]:
    """A persistent, UNCHANGING wage defect: rate == 0.0 (no delta), balance
    < 0.0 (labor permanently on the losing side). Under the pre-Task-2
    formula this generates ZERO agitation every tick (the bug); Task 2's
    level term must generate non-zero agitation from ``balance`` alone.
    """
    return {
        "key": "wage",
        "tick": 1,
        "gap": 0.4,
        "balance": -0.4,
        "rate": 0.0,
        "leading_pole": "a",
        "is_principal": False,
    }


@pytest.mark.unit
class TestSustainedWageDefectDrivesAgitation:
    """Task 2 (B): the sustained wage-value defect must drive agitation even
    when all first-difference terms are zero (steady state)."""

    def test_steady_state_negative_balance_generates_nonzero_agitation(self) -> None:
        graph = _graph_with_worker()
        graph.graph["opposition_states"] = {"wage": _steady_state_losing_wage_state()}
        defines = GameDefines()
        assert defines.consciousness.sustained_exploitation_sensitivity > 0.0, (
            "provisional default must be nonzero or this term is inert by construction"
        )
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[PERIPHERY_WORKER_ID]["ideology"]
        assert ideology["agitation"] > 0.0, (
            "a persistently negative wage-value balance (labor permanently "
            "losing) must generate agitation even with zero rate/wage/wealth "
            "deltas -- this is the exact property broken by the pure-first-"
            "difference formula (consciousness_routing.compute_agitation_delta)"
        )

    def test_class_consciousness_moves_tick_over_tick_under_steady_state(self) -> None:
        """The headline property: consciousness must NOT freeze under null
        play while the wage-value defect persists, even though every OTHER
        input (wage, wealth, opposition rate) is held perfectly constant.
        """
        graph = _graph_with_worker()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        persistent: dict[str, object] = {}

        consciousness_over_time: list[float] = []
        for tick in range(1, 6):
            # Re-inject the SAME steady-state snapshot every tick -- material
            # conditions are frozen, only the sustained defect persists.
            graph.graph["opposition_states"] = {"wage": _steady_state_losing_wage_state()}
            context = TickContext(tick=tick, persistent_data=persistent)
            system.step(graph, services, context)
            persistent = context.persistent_data
            consciousness_over_time.append(
                graph.nodes[PERIPHERY_WORKER_ID]["ideology"]["class_consciousness"]
            )

        assert consciousness_over_time == sorted(consciousness_over_time), (
            "class_consciousness must be monotonically non-decreasing under "
            "a persistent, unrelieved wage-value defect"
        )
        assert consciousness_over_time[-1] > consciousness_over_time[0], (
            "class_consciousness must actually MOVE tick over tick under "
            "null-play steady state -- the exact property that is broken "
            "today (agitation decays to zero once deltas vanish)"
        )

    def test_zero_sensitivity_reproduces_the_pre_task_2_frozen_behavior(self) -> None:
        """Characterization: with the coefficient dialed to zero, the old
        frozen-agitation behavior is exactly reproduced -- confirms this is
        an ADDED term, not a replacement of the existing sign-gate/rate path.
        """
        graph = _graph_with_worker()
        defines = GameDefines(
            consciousness=GameDefines().consciousness.model_copy(
                update={"sustained_exploitation_sensitivity": 0.0}
            )
        )
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        graph.graph["opposition_states"] = {"wage": _steady_state_losing_wage_state()}
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[PERIPHERY_WORKER_ID]["ideology"]
        assert ideology["agitation"] == pytest.approx(0.0), (
            "with sensitivity=0.0 the new term contributes nothing, and "
            "rate=0.0 keeps the existing wage_deterioration term silent too "
            "-- so agitation must be exactly zero, matching pre-Task-2 behavior"
        )
