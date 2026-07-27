"""Boundary-authoritative county attrs persist between boundaries (ADR140).

Spec-109 A7's design: the year boundary stamps LEVEL/RATE facts
(``tick_phi_hour``, ``tick_taxes_on_surplus``, ...) onto territory nodes and
non-boundary ticks accrue flows against them. On the headless runner's ONE
persistent graph that holds; through ``simulation_engine.step()`` — the qa
harness API — the per-tick WorldState round-trip wipes territory node attrs,
so every non-boundary tick used to see a bare territory: ``_accrue_flows``
no-opped and PolicySystem's ``_fiscal_terrain`` summed an empty domain 51
ticks out of 52. The U13 goldens (mitterrand's funding identity, syriza's
ceiling contact) read that terrain every tick, which is how the capstone
surfaced the gap.

Parity fix under test, AT THE SEAM: on a non-boundary tick,
``TickDynamicsSystem.step`` re-stamps the county attrs from the persisted
``SimulationTickState`` (the ``tick_dynamics`` graph attr the Feature-020
context bridge restores each tick) — the SAME values the boundary landed,
never interpolated (Constitution III.11: annual-resolution facts stay flat
between boundaries). The graph is built the way ``step()`` builds it: a
fresh ``to_graph()`` (bare territories) plus the restored graph attr.

Byte-safety for the six: scenarios without calculators never produce a
``SimulationTickState`` (no melt_calculator ⟹ boundary early-return, no
``tick_dynamics`` attr), so the re-stamp finds nothing and no-ops; the
re-stamped attrs are read only by PolicySystem (agenda-gated no-op in the
six) and appear in no checkpoint or dense column — proven by
``qa:regression`` staying byte-identical.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Mirror the import path used by tools/*.py and its existing unit tests
# (see tests/unit/tools/test_shared_signature.py).
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402

from babylon.domain.economics.tick.system import TickDynamicsSystem  # noqa: E402
from babylon.engine.context import TickContext  # noqa: E402
from babylon.engine.scenarios.single_county import (  # noqa: E402
    create_single_county_scenario,
)
from babylon.engine.services import ServiceContainer  # noqa: E402
from babylon.models.world_state import WorldState  # noqa: E402

pytestmark = pytest.mark.unit


def _boundary_graph_and_services() -> tuple[Any, Any, Any]:
    """Run the annual boundary once on the Wayne fixture's live graph."""
    state, config, defines = create_single_county_scenario()
    overrides = rt.build_single_county_overrides(defines)
    services = ServiceContainer.create(config, defines, **overrides)
    graph = state.to_graph()
    TickDynamicsSystem().step(graph, services, TickContext(tick=0))
    assert graph.get_graph_attr("tick_dynamics") is not None
    return graph, services, state


class TestCountyAttrsPersistBetweenBoundaries:
    """The Wayne fixture's fiscal facts survive the WorldState round-trip."""

    def test_non_boundary_tick_restamps_onto_a_round_tripped_graph(self) -> None:
        graph, services, _state = _boundary_graph_and_services()
        stamped = dict(graph.get_node("T001").attributes)
        assert "tick_phi_hour" in stamped, "boundary must stamp the fixture"

        # The step() round-trip: territory node attrs die, the tick_dynamics
        # graph attr is restored by the Feature-020 context bridge.
        reloaded = WorldState.from_graph(graph, tick=1).to_graph()
        assert "tick_phi_hour" not in reloaded.get_node("T001").attributes
        reloaded.set_graph_attr("tick_dynamics", graph.get_graph_attr("tick_dynamics"))

        TickDynamicsSystem().step(reloaded, services, TickContext(tick=1))

        attrs = reloaded.get_node("T001").attributes
        assert "tick_phi_hour" in attrs, (
            "non-boundary ticks must re-stamp the boundary-authoritative "
            "county attrs from the persisted SimulationTickState "
            "(spec-109 A7 parity through step(); ADR140)"
        )
        assert "tick_taxes_on_surplus" in attrs
        assert "tick_total_surplus" in attrs

    def test_restamped_values_are_the_boundary_values_verbatim(self) -> None:
        """LEVELS re-stamp flat — never interpolated (III.11)."""
        graph, services, _state = _boundary_graph_and_services()
        boundary = dict(graph.get_node("T001").attributes)

        reloaded = WorldState.from_graph(graph, tick=1).to_graph()
        reloaded.set_graph_attr("tick_dynamics", graph.get_graph_attr("tick_dynamics"))
        TickDynamicsSystem().step(reloaded, services, TickContext(tick=1))

        attrs = reloaded.get_node("T001").attributes
        assert attrs["tick_phi_hour"] == boundary["tick_phi_hour"]
        assert attrs["tick_total_surplus"] == boundary["tick_total_surplus"]
        assert attrs["tick_taxes_on_surplus"] == boundary["tick_taxes_on_surplus"]

    def test_stateless_graph_stays_bare(self) -> None:
        """No persisted SimulationTickState ⟹ nothing re-stamps (III.11)."""
        state, config, defines = create_single_county_scenario()
        services = ServiceContainer.create(config, defines)
        graph = state.to_graph()
        assert graph.get_graph_attr("tick_dynamics") is None

        TickDynamicsSystem().step(graph, services, TickContext(tick=1))

        assert "tick_phi_hour" not in graph.get_node("T001").attributes
