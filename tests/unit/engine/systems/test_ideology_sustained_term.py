"""System-level test for the Task 2 (B) sustained wage-value defect term.

Defect fix (branch ``fix/null-play-coupling``, 948e46ad follow-up): the term
originally read the GLOBAL ``opposition_states["wage"]["balance"]`` -- an
unweighted arithmetic mean of an intensive quantity over ALL classes -- and
broadcast the identical value to every node's agitation. That both (1) is a
variance error under this repo's own type theorem ("intensives restrict but
never sum") and (2) erases the theory: a bribed labor aristocracy (balance >
0) and an exploited periphery worker (balance < 0) radicalized at identical
rates, and since the mean folds them together it also never went negative in
practice, leaving the term permanently inert.

The fix computes EACH CLASS's OWN balance from that class's OWN ``w_paid`` /
``v_produced`` node attributes (written by ``EconomicSystem``,
``engine/systems/economic.py:501-502``, on ticks it actually paid that class)
via the SAME :func:`~babylon.formulas.contradiction.
calculate_wealth_asymmetry_balance` the catalog uses -- no mean, no
aggregation, so the class differential survives into ``class_consciousness``.

The property under test is exactly the bug named in the spec
(``docs/superpowers/plans/2026-07-18-null-play-political-coupling.md``):
today, once wage/wealth/opposition deltas all reach zero (a material steady
state), ``agitation`` decays to zero and ``class_consciousness`` freezes
forever -- EVEN IF a class's own wage-value defect stays persistently
negative (that class permanently on the losing side). This test builds
exactly that steady state and asserts consciousness keeps moving tick over
tick -- and that it does so ONLY for the losing class, not the bribed one.
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

# Steady-state (w_paid, v_produced) positions used throughout this module.
# PERIPHERY_WORKER: wage BELOW value produced -> negative balance -> losing.
# LABOR_ARISTOCRACY: wage ABOVE value produced -> positive balance -> the
# imperial bribe -> must contribute ZERO sustained agitation (Cope's
# crisis-gating, ideology.py:108-120). The magnitudes are chosen so the
# UNWEIGHTED MEAN of the two classes' balances is itself >= 0 -- reproducing
# the exact old global-mean bug (a bribed core large enough to fold an
# exploited periphery's negative balance back above zero, keeping the
# ``balance < 0`` gate permanently closed under a mean) -- see
# ``TestPerClassSustainedTermDifferentiation.
# test_same_global_mean_would_have_masked_this_but_per_class_does_not``.
_EXPLOITED_W_PAID = 50.0
_EXPLOITED_V_PRODUCED = 100.0
_BRIBED_W_PAID = 300.0
_BRIBED_V_PRODUCED = 100.0


def _graph_with_worker(*, stamp_wage_value: bool = True) -> BabylonGraph:
    """A periphery worker with an incoming SOLIDARITY edge from an already-
    revolutionary source (as ``TestConsciousnessSystemWealthTracking.
    test_wealth_extraction_routes_to_fascism_without_solidarity``'s sibling
    test does in ``test_ideology.py``) -- without this, agitation routes
    entirely to ``national_identity`` (the fascist path, ``solidarity_
    pressure == 0``) and ``class_consciousness`` cannot move at all,
    regardless of how much agitation is generated.

    ``stamp_wage_value``: when True (default), both nodes carry ``w_paid``/
    ``v_produced`` positioning the worker as exploited (losing) and the
    labor aristocracy as bribed -- the per-class fields the fixed code reads.
    """
    graph = BabylonGraph()
    worker_extra: dict[str, float] = {}
    aristocracy_extra: dict[str, float] = {}
    if stamp_wage_value:
        worker_extra = {"w_paid": _EXPLOITED_W_PAID, "v_produced": _EXPLOITED_V_PRODUCED}
        aristocracy_extra = {"w_paid": _BRIBED_W_PAID, "v_produced": _BRIBED_V_PRODUCED}
    graph.add_node(
        PERIPHERY_WORKER_ID,
        wealth=1.0,
        ideology={
            "class_consciousness": 0.5,
            "national_identity": 0.5,
            "agitation": 0.0,
        },
        _node_type="social_class",
        **worker_extra,
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
        **aristocracy_extra,
    )
    graph.add_edge(
        LABOR_ARISTOCRACY_ID,
        PERIPHERY_WORKER_ID,
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=0.8,
    )
    return graph


def _steady_state_losing_wage_state() -> dict[str, object]:
    """A GLOBAL wage-opposition snapshot with rate == 0.0 (no delta).

    This now exercises ONLY the pre-existing, unchanged ``wage_deterioration``
    RATE-gated term (``ideology.py:125``), which stays silent at ``rate ==
    0.0`` regardless of sign -- it is injected here purely to prove that
    term is NOT what's driving agitation in these tests. The per-class
    sustained term is driven by ``w_paid``/``v_produced`` node attributes
    (see ``_graph_with_worker``), not by this global snapshot.
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


@pytest.mark.unit
class TestPerClassSustainedTermDifferentiation:
    """The property the GLOBAL-mean wiring could never express: two classes
    in the SAME graph, with DIFFERENT wage/value positions, must radicalize
    at DIFFERENT rates. A class with wage below value produced (exploited)
    gains sustained agitation; a class with wage above value (the bribed
    labor aristocracy) gains none -- even in the same tick, same graph.
    """

    def test_exploited_class_radicalizes_while_bribed_class_routes_to_nation(self) -> None:
        """Superseded by the Consciousness Recoupling correction
        (``docs/superpowers/specs/2026-07-18-consciousness-recoupling-design.md``,
        branch ``fix/null-play-coupling``): a positive balance no longer
        generates ZERO agitation -- it generates agitation that routes to
        the fascist pole (``national_identity``) instead of the
        revolutionary one. See ``test_ideology_chauvinist_recoupling.py``
        for the dedicated direction-flip/steady-state tests.
        """
        graph = _graph_with_worker()
        defines = GameDefines()
        assert defines.consciousness.sustained_exploitation_sensitivity > 0.0
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        exploited_ideology = graph.nodes[PERIPHERY_WORKER_ID]["ideology"]
        bribed_ideology = graph.nodes[LABOR_ARISTOCRACY_ID]["ideology"]

        assert exploited_ideology["agitation"] > 0.0, (
            "the exploited class (w_paid < v_produced, negative per-class "
            "balance) must generate sustained agitation from its OWN wage-"
            "value position"
        )
        assert bribed_ideology["agitation"] > 0.0, (
            "the bribed class (w_paid > v_produced, positive per-class "
            "balance -- the imperial bribe) must now generate NONZERO "
            "sustained agitation (Consciousness Recoupling correction): a "
            "positive balance redirects agitation to the fascist pole, it "
            "does not suppress it"
        )
        assert bribed_ideology["national_identity"] > 0.0, (
            "the bribed class's agitation must route toward national_identity "
            "(fascist), not class_consciousness (no incoming solidarity edge "
            "on the labor-aristocracy node itself in this fixture)"
        )
        assert bribed_ideology["class_consciousness"] == pytest.approx(0.9), (
            "with zero incoming solidarity on the bribed node, "
            "effective_solidarity is already 0 -- class_consciousness must "
            "stay at its baseline, unaffected by chauvinist_pressure clamping"
        )

    def test_same_global_mean_would_have_masked_this_but_per_class_does_not(self) -> None:
        """Sanity check on the fixture: the two classes' balances average to
        something >= 0 (the old global-mean bug's exact failure mode -- the
        bribed core folds the exploited periphery's negative balance back
        toward/above zero, so the ``balance < 0`` gate never opens under a
        mean). The per-class fix must still differentiate them despite that.
        """
        from babylon.formulas.contradiction import calculate_wealth_asymmetry_balance

        exploited_balance = calculate_wealth_asymmetry_balance(
            _EXPLOITED_V_PRODUCED, _EXPLOITED_W_PAID
        )
        bribed_balance = calculate_wealth_asymmetry_balance(_BRIBED_V_PRODUCED, _BRIBED_W_PAID)
        mean_balance = (exploited_balance + bribed_balance) / 2.0
        assert mean_balance >= 0.0, (
            "fixture must reproduce the exact global-mean failure mode this "
            "fix eliminates -- if this fails, the fixture no longer "
            "demonstrates the defect and should be recalibrated"
        )

        graph = _graph_with_worker()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        assert graph.nodes[PERIPHERY_WORKER_ID]["ideology"]["agitation"] > 0.0, (
            "despite the global mean being >= 0 (which would have kept the "
            "old wiring's gate permanently closed), the per-class fix still "
            "generates agitation for the exploited class"
        )
