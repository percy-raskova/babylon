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
    spark roll) must still generate agitation every tick it is present."""

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
            "a persistently high repression_faced level must generate "
            "agitation even with zero wage/wealth/opposition-rate deltas -- "
            "the continuous term task #42-B wires, distinct from "
            "StruggleSystem's event-triggered repression_backfire spike"
        )

    def test_higher_repression_generates_more_agitation(self) -> None:
        """Monotonic: MIM labor-aristocracy:34-40 -- more state violence,
        more political energy, not less."""
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)

        low_graph = _graph_with_repression(repression_faced=0.1)
        ConsciousnessSystem().step(low_graph, services, TickContext(tick=1))
        low_agitation = low_graph.nodes[_WORKER_ID]["ideology"]["agitation"]

        high_graph = _graph_with_repression(repression_faced=0.9)
        ConsciousnessSystem().step(high_graph, services, TickContext(tick=1))
        high_agitation = high_graph.nodes[_WORKER_ID]["ideology"]["agitation"]

        assert high_agitation > low_agitation

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

    def test_compute_agitation_delta_called_with_repression_level(self) -> None:
        """Direct call-contract pin: ideology.py must pass this node's own
        repression_faced to compute_agitation_delta as repression_level."""
        from unittest.mock import patch

        from babylon.formulas.consciousness_routing import (
            compute_agitation_delta as _real_compute_agitation_delta,
        )

        graph = _graph_with_repression(repression_faced=0.42)
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()

        with patch(
            "babylon.engine.systems.ideology.compute_agitation_delta",
            wraps=_real_compute_agitation_delta,
        ) as spy:
            system.step(graph, services, TickContext(tick=1))

        calls_with_repression = [
            call for call in spy.call_args_list if call.kwargs.get("repression_level") == 0.42
        ]
        assert calls_with_repression, (
            "compute_agitation_delta must be called with "
            "repression_level=<this node's own repression_faced>; actual "
            f"calls: {spy.call_args_list}"
        )
