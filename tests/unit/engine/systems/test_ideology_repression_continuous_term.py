"""System-level tests for the task #42-B continuous repression agitation term.

``repression_faced`` (:class:`~babylon.models.entities.social_class.SocialClass`,
``Probability`` in ``[0, 1]``) is already a continuous, standing LEVEL -- not
an event. ``StruggleSystem`` @16 already reads it for an EVENT-triggered
spike (``repression_backfire``, gated on an ``EXCESSIVE_FORCE`` RNG roll,
see ``struggle.py``'s ``spark_probability``/``_update_agitation``), but
nothing reads it as a *standing* per-tick agitation contribution in
``ConsciousnessSystem`` @17 -- the same de-delta family of gap as task #42-A's
``class_wage_balance`` (ADR082's "repression -> consciousness edge... not
drawn" bullet; MIM ``labor-aristocracy:34-40``: "the lack of violent conflict
itself is a fundamental reason for the lack of political consciousness among
the workers").

This module pins the wiring: ``ConsciousnessSystem`` must read
``repression_faced`` off each ``social_class`` node and feed it into
``compute_agitation_delta`` as the ``repression_level`` keyword, presence-gated
(``None`` when the node has no ``repression_faced`` attribute at all -- an
explicit "no data", never a fabricated fallback default) exactly like task
#42-A's ``wage_balance`` gate.

**Task #42 fix wave 1 correction (review MEDIUM-2, 2026-07-20):** the
reviewer proved the ENTIRE +0.00012 tick-1 canonical baseline drift was this
term measuring ``SocialClass``'s own AMBIENT model default
(``repression_faced=0.5``, stamped on every class from tick 1 with no
repression EVENT) as if it were signal. The fix passes the PRODUCED excess
above ``DEFAULT_REPRESSION_FACED`` (``max(0, repression_faced -
DEFAULT_REPRESSION_FACED)``), never the raw level -- this module's tests
below were updated accordingly: the ambient-default and below-default cases
now pin an EXACT zero contribution, the two-point monotonicity fixture moved
both points above the baseline (a below-baseline point contributes zero by
construction, so it no longer tests monotonicity of the produced term), and
the call-contract pin now asserts the EFFECTIVE (post-subtraction) value.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.topology.graph import BabylonGraph

_WORKER_ID = "worker_repression_1"


def _fresh_ideology() -> dict[str, float]:
    return {"class_consciousness": 0.0, "national_identity": 0.5, "agitation": 0.0}


def _graph_with_repression(*, repression_faced: float | None) -> BabylonGraph:
    """A single social_class node with no wage/wealth motion at all -- every
    OTHER agitation source pinned at zero so any nonzero agitation this tick
    is attributable ONLY to the repression term."""
    graph = BabylonGraph()
    extra: dict[str, float] = {}
    if repression_faced is not None:
        extra["repression_faced"] = repression_faced
    graph.add_node(
        _WORKER_ID,
        wealth=1.0,
        ideology=_fresh_ideology(),
        _node_type="social_class",
        **extra,
    )
    return graph


@pytest.mark.unit
class TestRepressionFacedDrivesContinuousAgitation:
    """The headline property: a standing repression LEVEL (no event, no
    spark roll) must still generate agitation every tick it is PRODUCED
    above the ambient baseline."""

    def test_repression_faced_generates_agitation_with_no_other_stimulus(self) -> None:
        graph = _graph_with_repression(repression_faced=0.8)
        defines = GameDefines()
        assert defines.consciousness.repression_level_sensitivity > 0.0, (
            "provisional default must be nonzero or this term is inert by construction"
        )
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_WORKER_ID]["ideology"]
        assert ideology["agitation"] > 0.0, (
            "a repression_faced level ABOVE the ambient baseline (0.8 > "
            "DEFAULT_REPRESSION_FACED=0.5) must generate agitation even "
            "with zero wage/wealth/opposition-rate deltas -- the continuous "
            "term task #42-B wires, distinct from StruggleSystem's "
            "event-triggered repression_backfire spike"
        )

    def test_higher_repression_generates_more_agitation(self) -> None:
        """Monotonic in the PRODUCED excess: MIM labor-aristocracy:34-40 --
        more state violence, more political energy, not less. Both fixture
        values sit ABOVE DEFAULT_REPRESSION_FACED=0.5 (task #42 fix wave 1)
        so this genuinely tests monotonicity of the produced term -- a
        below-baseline point would contribute exactly zero by construction
        and no longer distinguish "some repression" from "none produced"."""
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)

        low_graph = _graph_with_repression(repression_faced=0.6)
        ConsciousnessSystem().step(low_graph, services, TickContext(tick=1))
        low_agitation = low_graph.nodes[_WORKER_ID]["ideology"]["agitation"]

        high_graph = _graph_with_repression(repression_faced=0.9)
        ConsciousnessSystem().step(high_graph, services, TickContext(tick=1))
        high_agitation = high_graph.nodes[_WORKER_ID]["ideology"]["agitation"]

        assert high_agitation > low_agitation > 0.0

    def test_absent_repression_faced_contributes_exactly_zero(self) -> None:
        """No repression_faced attribute at all (never stamped on this node)
        must be an explicit "no data" -- zero contribution, not a fabricated
        fallback default (e.g. the model's own 0.5 default, or
        DEFAULT_REPRESSION_FACED as struggle.py/survival.py use it) that
        would silently generate baseline agitation for every unstamped node."""
        graph = _graph_with_repression(repression_faced=None)
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_WORKER_ID]["ideology"]
        assert ideology["agitation"] == pytest.approx(0.0), (
            "a node with no repression_faced attribute must generate zero "
            "agitation from this term -- presence-gated exactly like task "
            "#42-A's wage_balance, not defaulted to a nonzero moderate level"
        )

    def test_repression_faced_exactly_at_ambient_default_contributes_exactly_zero(
        self,
    ) -> None:
        """Task #42 fix wave 1 (review MEDIUM-2), finding (a): a class whose
        repression_faced sits EXACTLY at the canonical ambient baseline
        (SocialClass's own model default, DEFAULT_REPRESSION_FACED=0.5) has
        PRODUCED zero repression -- no POGROM/VIGILANTISM has ever fired on
        it -- and must contribute EXACTLY zero agitation, not
        repression_faced * sensitivity (the pre-fix behavior that measured
        the ambient default as signal, proven to be the entire +0.00012
        tick-1 canonical drift)."""
        defines = GameDefines()
        graph = _graph_with_repression(repression_faced=defines.DEFAULT_REPRESSION_FACED)
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_WORKER_ID]["ideology"]
        assert ideology["agitation"] == 0.0
        assert ideology["national_identity"] == 0.5
        assert ideology["class_consciousness"] == 0.0

    def test_repression_faced_below_ambient_default_contributes_exactly_zero(self) -> None:
        """A class with LESS repression than the ambient baseline (0.1 <
        DEFAULT_REPRESSION_FACED=0.5) must floor at zero, never a negative
        contribution -- the ``max(0.0, ...)`` in ideology.py's
        effective_repression computation."""
        defines = GameDefines()
        graph = _graph_with_repression(repression_faced=0.1)
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_WORKER_ID]["ideology"]
        assert ideology["agitation"] == 0.0

    def test_repression_above_default_routes_via_bifurcation_law_unchanged(self) -> None:
        """Task #42 fix wave 1 (review finding b): produced repression
        (0.8, i.e. 0.3 above the 0.5 baseline) must still generate positive
        agitation, routed by the SAME bifurcation law as every other
        agitation source (ADR016_fascist_bifurcation) -- zero solidarity
        here means it lands entirely on national_identity (the fascist
        pole), never class_consciousness. Proves the fix only changed WHICH
        repression counts as signal, not how the resulting energy is
        routed."""
        defines = GameDefines()
        graph = _graph_with_repression(repression_faced=0.8)
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_WORKER_ID]["ideology"]
        assert ideology["agitation"] > 0.0
        assert ideology["national_identity"] > 0.5, "zero solidarity -> fascist pole"
        assert ideology["class_consciousness"] == pytest.approx(0.0), (
            "revolutionary pole untouched -- no solidarity edge to route through"
        )

    def test_repression_term_is_deterministic(self) -> None:
        """Task #42 fix wave 1, finding (c): identical inputs must produce
        an identical result every time (Constitution III.7)."""
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)

        graph_a = _graph_with_repression(repression_faced=0.75)
        ConsciousnessSystem().step(graph_a, services, TickContext(tick=1))
        result_a = dict(graph_a.nodes[_WORKER_ID]["ideology"])

        graph_b = _graph_with_repression(repression_faced=0.75)
        ConsciousnessSystem().step(graph_b, services, TickContext(tick=1))
        result_b = dict(graph_b.nodes[_WORKER_ID]["ideology"])

        assert result_a == result_b

    def test_zero_sensitivity_reproduces_pre_task_42b_behavior(self) -> None:
        """Characterization: with the coefficient dialed to zero, repression
        contributes nothing -- confirms this is an ADDED term."""
        graph = _graph_with_repression(repression_faced=0.9)
        defines = GameDefines(
            consciousness=GameDefines().consciousness.model_copy(
                update={"repression_level_sensitivity": 0.0}
            )
        )
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()
        system.step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_WORKER_ID]["ideology"]
        assert ideology["agitation"] == pytest.approx(0.0)

    def test_compute_agitation_delta_called_with_effective_repression_above_baseline(
        self,
    ) -> None:
        """Direct call-contract pin, corrected task #42 fix wave 1 (review
        MEDIUM-2): ideology.py must pass the PRODUCED excess above
        DEFAULT_REPRESSION_FACED (0.75 - 0.5 = 0.25), never the raw
        repression_faced (0.75) -- reading the raw level was the exact
        pre-fix defect that measured the ambient default as signal."""
        from unittest.mock import patch

        from babylon.formulas.consciousness_routing import (
            compute_agitation_delta as _real_compute_agitation_delta,
        )

        defines = GameDefines()
        graph = _graph_with_repression(repression_faced=0.75)
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()

        with patch(
            "babylon.engine.systems.ideology.compute_agitation_delta",
            wraps=_real_compute_agitation_delta,
        ) as spy:
            system.step(graph, services, TickContext(tick=1))

        calls_with_repression = [
            call
            for call in spy.call_args_list
            if call.kwargs.get("repression_level") == pytest.approx(0.25)
        ]
        assert calls_with_repression, (
            "compute_agitation_delta must be called with repression_level="
            "<repression_faced - DEFAULT_REPRESSION_FACED>, the PRODUCED "
            f"excess, never the raw level; actual calls: {spy.call_args_list}"
        )
