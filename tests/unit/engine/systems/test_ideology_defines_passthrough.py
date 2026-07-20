"""Regression tests: task #42 fix wave 1 (review MEDIUM-1) -- every
``consciousness_routing`` formula call in ``ConsciousnessSystem.step``'s
per-node loop must thread the run's live ``defines=`` through.

The review found the ``defines=`` fix landed for ``compute_agitation_delta``
(task #42-A) was a ONE-INSTANCE patch of a class-wide bug: two sibling calls
in the SAME per-node loop -- ``route_agitation_to_ternary`` and
``compute_exploitation_visibility`` -- still omitted it, silently falling
back to ``ConsciousnessDefines()``'s own schema defaults regardless of what
``services.defines``/``defines.yaml`` says. Latent today only because a
canonical run's ``defines.yaml`` IS generated from the schema (so the two
happen to be numerically identical); the defect is real for the modding path
the repo explicitly promises. ``compute_reification_buffer`` takes no
``defines`` parameter at all -- correctly excluded, not a regression.

This module pins BOTH remaining call sites with the same call-contract spy
pattern already used for ``compute_agitation_delta`` in
``test_ideology_repression_continuous_term.py`` /
``test_ideology_sustained_term.py``. The class-wide gate against regrowth is
``babylon.sentinels.defines_passthrough`` (``mise run check:defines-passthrough``).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.formulas.consciousness_routing import (
    compute_exploitation_visibility as _real_compute_exploitation_visibility,
)
from babylon.formulas.consciousness_routing import (
    route_agitation_to_ternary as _real_route_agitation_to_ternary,
)
from babylon.topology.graph import BabylonGraph

_WORKER_ID = "worker_defines_passthrough"


def _graph_with_worker() -> BabylonGraph:
    """A single social_class node; the exact stimulus doesn't matter here --
    both watched functions run unconditionally every tick for every active
    social_class node, so any node suffices to observe the call contract."""
    graph = BabylonGraph()
    graph.add_node(
        _WORKER_ID,
        wealth=1.0,
        ideology={"class_consciousness": 0.0, "national_identity": 0.5, "agitation": 0.1},
        _node_type="social_class",
    )
    return graph


@pytest.mark.unit
class TestRouteAgitationToTernaryDefinesPassthrough:
    """``route_agitation_to_ternary`` (``ideology.py`` ~:335) must receive
    the run's live ``services.defines.consciousness``."""

    def test_called_with_run_defines(self) -> None:
        graph = _graph_with_worker()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()

        with patch(
            "babylon.engine.systems.ideology.route_agitation_to_ternary",
            wraps=_real_route_agitation_to_ternary,
        ) as spy:
            system.step(graph, services, TickContext(tick=1))

        assert spy.call_args_list, "route_agitation_to_ternary was never called"
        for call in spy.call_args_list:
            assert call.kwargs.get("defines") is defines.consciousness, (
                "route_agitation_to_ternary must receive the run's live "
                "services.defines.consciousness -- omitting it silently "
                f"falls back to schema defaults; actual call: {call}"
            )


@pytest.mark.unit
class TestComputeExploitationVisibilityDefinesPassthrough:
    """``compute_exploitation_visibility`` (``ideology.py`` ~:358) must
    receive the run's live ``services.defines.consciousness``."""

    def test_called_with_run_defines(self) -> None:
        graph = _graph_with_worker()
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        system = ConsciousnessSystem()

        with patch(
            "babylon.engine.systems.ideology.compute_exploitation_visibility",
            wraps=_real_compute_exploitation_visibility,
        ) as spy:
            system.step(graph, services, TickContext(tick=1))

        assert spy.call_args_list, "compute_exploitation_visibility was never called"
        for call in spy.call_args_list:
            assert call.kwargs.get("defines") is defines.consciousness, (
                "compute_exploitation_visibility must receive the run's live "
                "services.defines.consciousness -- omitting it silently "
                f"falls back to schema defaults; actual call: {call}"
            )
