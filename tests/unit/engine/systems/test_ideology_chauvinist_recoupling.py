"""System-level tests for the Consciousness Recoupling correction
(``docs/superpowers/specs/2026-07-18-consciousness-recoupling-design.md``,
§2/§5.4/§7), branch ``fix/null-play-coupling``.

TDD Red Phase: ``ConsciousnessSystem`` does not yet call
:func:`~babylon.formulas.sustained_exploitation.sustained_exploitation_magnitude`
or compute ``chauvinist_pressure`` -- these tests fail against the CURRENT
(pre-correction) code because a positive wage-value ``balance`` still
generates exactly zero agitation.

The defect (spec §1): ``sustained_exploitation_agitation`` returns 0.0
whenever ``balance >= 0`` -- and the ratified theory holds ``balance > 0``
for every wage-earning class inside US borders, so the term never fires and
the engine produces no political motion under null play.

The correction (spec §2): a positive balance does not suppress political
energy -- it redirects it. Balance SIGN feeds the bifurcation DIRECTION
(via ``chauvinist_pressure`` reducing ``effective_solidarity`` in
:func:`~babylon.formulas.consciousness_routing.route_agitation_to_ternary`);
balance MAGNITUDE (via :func:`~babylon.formulas.sustained_exploitation.
sustained_exploitation_magnitude`, non-monotonic per §5.4) drives intensity
on either branch.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph

# Node ids for this module's fixtures only.
_VANGUARD_ID = "vanguard-source"
_EXPLOITED_ID = "class-exploited"
_BRIBED_ID = "class-bribed"

# Symmetric |balance| = 0.5 in opposite directions:
#   exploited: w_paid=50,  v_produced=150 -> (50-150)/200  = -0.5
#   bribed:    w_paid=150, v_produced=50  -> (150-50)/200  = +0.5
_EXPLOITED_W_PAID = 50.0
_EXPLOITED_V_PRODUCED = 150.0
_BRIBED_W_PAID = 150.0
_BRIBED_V_PRODUCED = 50.0

# Solidarity edge strength shared by both classes -- moderate (0.6), enough
# that UNBIASED effective_solidarity (0.6) favors revolutionary (> 0.5), so
# any flip to fascist-dominant for the bribed class is attributable to
# chauvinist_pressure, not an absence of solidarity.
_SOLIDARITY_STRENGTH = 0.6


def _fresh_ideology() -> dict[str, float]:
    return {"class_consciousness": 0.0, "national_identity": 0.0, "agitation": 0.0}


def _graph_with_symmetric_balances() -> BabylonGraph:
    """One revolutionary vanguard source feeding equal SOLIDARITY strength
    into two classes with identical |balance| but opposite sign."""
    graph = BabylonGraph()
    graph.add_node(
        _VANGUARD_ID,
        wealth=1.0,
        ideology={"class_consciousness": 0.9, "national_identity": 0.1, "agitation": 0.0},
        _node_type="social_class",
    )
    graph.add_node(
        _EXPLOITED_ID,
        wealth=1.0,
        ideology=_fresh_ideology(),
        _node_type="social_class",
        w_paid=_EXPLOITED_W_PAID,
        v_produced=_EXPLOITED_V_PRODUCED,
    )
    graph.add_node(
        _BRIBED_ID,
        wealth=1.0,
        ideology=_fresh_ideology(),
        _node_type="social_class",
        w_paid=_BRIBED_W_PAID,
        v_produced=_BRIBED_V_PRODUCED,
    )
    graph.add_edge(
        _VANGUARD_ID,
        _EXPLOITED_ID,
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=_SOLIDARITY_STRENGTH,
    )
    graph.add_edge(
        _VANGUARD_ID,
        _BRIBED_ID,
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=_SOLIDARITY_STRENGTH,
    )
    return graph


@pytest.mark.unit
class TestDirectionFlip:
    """Acceptance criterion 1: two classes, identical |balance|, opposite
    sign, in the SAME graph. Negative -> revolutionary-dominant. Positive ->
    fascist-dominant. Both receive IDENTICAL incoming solidarity, so the
    divergence is attributable ONLY to balance sign."""

    def test_negative_balance_class_accumulates_more_revolutionary_than_fascist(self) -> None:
        graph = _graph_with_symmetric_balances()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_EXPLOITED_ID]["ideology"]
        assert ideology["class_consciousness"] > ideology["national_identity"], (
            "exploited class (balance=-0.5) must accumulate more revolutionary "
            "than fascist consciousness this tick"
        )
        assert ideology["class_consciousness"] > 0.0

    def test_positive_balance_class_accumulates_more_fascist_than_revolutionary(self) -> None:
        graph = _graph_with_symmetric_balances()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_BRIBED_ID]["ideology"]
        assert ideology["national_identity"] > ideology["class_consciousness"], (
            "bribed class (balance=+0.5) must accumulate more fascist than "
            "revolutionary consciousness this tick -- the exact correction "
            "this spec makes: a positive balance REDIRECTS agitation, it "
            "does not suppress it"
        )
        assert ideology["national_identity"] > 0.0

    def test_the_two_classes_diverge_in_opposite_directions(self) -> None:
        """Cross-class comparison: the exploited class's revolutionary GAIN
        must exceed the bribed class's revolutionary gain, and vice versa
        for fascist gain -- the classes are not just individually
        r-leaning/f-leaning, they diverge relative to EACH OTHER."""
        graph = _graph_with_symmetric_balances()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        exploited = graph.nodes[_EXPLOITED_ID]["ideology"]
        bribed = graph.nodes[_BRIBED_ID]["ideology"]

        assert exploited["class_consciousness"] > bribed["class_consciousness"]
        assert bribed["national_identity"] > exploited["national_identity"]


@pytest.mark.unit
class TestMotionUnderSteadyStatePositiveBalance:
    """Acceptance criterion 3 (the headline property): a steady state with
    every OTHER delta at zero (no wage/wealth change, no opposition-rate
    movement, no solidarity edges at all) and a PERSISTENT POSITIVE balance
    must still produce tick-over-tick movement -- toward fascism. This is
    the exact property broken today (the sign-gated formula returns 0.0 for
    balance >= 0, so agitation stays permanently at its decayed floor)."""

    def _isolated_bribed_graph(self) -> BabylonGraph:
        """No solidarity edges at all -- isolates the sustained-magnitude
        term (Change 1) from the chauvinist_pressure routing bias (Change
        2): even with solidarity_pressure=0 (which alone would already
        route 100% fascist), the headline bug is that agitation was EXACTLY
        ZERO for balance >= 0, so nothing moved at all, in any direction.
        """
        graph = BabylonGraph()
        graph.add_node(
            _BRIBED_ID,
            wealth=1.0,
            ideology=_fresh_ideology(),
            _node_type="social_class",
            w_paid=_BRIBED_W_PAID,
            v_produced=_BRIBED_V_PRODUCED,
        )
        return graph

    def test_national_identity_moves_tick_over_tick_under_null_play(self) -> None:
        graph = self._isolated_bribed_graph()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        persistent: dict[str, object] = {}

        national_identity_over_time: list[float] = []
        for tick in range(1, 6):
            context = TickContext(tick=tick, persistent_data=persistent)
            system.step(graph, services, context)
            persistent = context.persistent_data
            national_identity_over_time.append(
                graph.nodes[_BRIBED_ID]["ideology"]["national_identity"]
            )

        assert national_identity_over_time == sorted(national_identity_over_time), (
            "national_identity must be monotonically non-decreasing under a "
            "persistent positive wage-value balance"
        )
        assert national_identity_over_time[-1] > national_identity_over_time[0], (
            "THE headline property: national_identity must actually MOVE "
            "tick over tick under null-play steady state with a persistent "
            "positive balance -- if this is flat, the correction has NOT "
            "fixed the null-play defect this spec exists to resolve"
        )

    def test_class_consciousness_stays_flat_while_national_identity_moves(self) -> None:
        """With zero incoming solidarity, effective_solidarity is already 0
        before chauvinist_pressure is even applied -- so class_consciousness
        (revolutionary) must stay at its baseline while national_identity
        (fascist) is the only axis that moves. Confirms the movement is
        DIRECTED, not generic noise."""
        graph = self._isolated_bribed_graph()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_BRIBED_ID]["ideology"]
        assert ideology["class_consciousness"] == pytest.approx(0.0)
        assert ideology["national_identity"] > 0.0
