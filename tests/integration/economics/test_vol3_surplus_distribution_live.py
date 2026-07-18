"""U1 acceptance (design §4): `s = p + i + r + t` has NEVER evaluated in a
shipped run. This is the first test that makes it do so end-to-end, over the
real reference DB, and pins SC-001 — the identity holds within
DISTRIBUTION_EPSILON for 100% of observations, not merely on average.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from babylon.domain.economics.distribution.types import DISTRIBUTION_EPSILON
from babylon.domain.economics.tick.graph_bridge import (
    TICK_DYNAMICS_KEY,
    _reconstruct_tick_state,
)

if TYPE_CHECKING:
    from babylon.domain.economics.tick.types import SimulationTickState
    from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

WAYNE_FIPS = "26163"
#: Ticks driven through ``step`` before the capturing pass. Tick 0 is itself a
#: year boundary (bootstraps 2010); after 52 calls ``state.tick == 52``, which is
#: the NEXT boundary — the tick the capturing pass runs and observes (2011).
_TICKS_BEFORE_CAPTURE = 52


def _run_to_year_boundary_capturing_graph() -> BabylonGraph:
    """Run a Wayne-scoped simulation to a year boundary; return the LIVE graph.

    The final tick is executed through the same three calls
    ``simulation_engine.step`` makes (`simulation_engine.py:519-537`) —
    ``to_graph`` → ``_restore_graph_context`` → ``_DEFAULT_ENGINE.run_tick`` —
    rather than through ``step`` itself, for one reason only: ``step`` discards
    the graph and returns a ``WorldState``, and the round trip that produces that
    ``WorldState`` destroys every quantity this task exists to observe (see the
    observation-point note in the plan). Same engine, same systems, same order;
    the only difference is that the graph the systems wrote is handed back
    instead of thrown away.
    """
    from babylon.engine.context import TickContext
    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.engine.services import ServiceContainer
    from babylon.engine.simulation_engine import (
        _DEFAULT_ENGINE,
        _restore_graph_context,
        step,
    )
    from babylon.reference.database import get_normalized_session_factory
    from tests.integration.economics.conftest import build_wayne_world_state

    overrides, leontief_session = _build_economics_overrides(
        session_factory=get_normalized_session_factory(),
        scope_fips=frozenset({WAYNE_FIPS}),
    )
    try:
        state, sim_config, defines = build_wayne_world_state()
        persistent: dict[str, object] = {}
        for _ in range(_TICKS_BEFORE_CAPTURE):
            state = step(state, sim_config, persistent, defines, calculator_overrides=overrides)
        assert state.tick == _TICKS_BEFORE_CAPTURE, (
            f"expected tick {_TICKS_BEFORE_CAPTURE} before the capturing pass, "
            f"got {state.tick} — the capturing pass must land on a year boundary"
        )
        graph = state.to_graph()
        _restore_graph_context(graph, persistent)
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=state.tick, persistent_data=dict(persistent))
        _DEFAULT_ENGINE.run_tick(graph, services, context)
        return graph
    finally:
        if leontief_session is not None:
            leontief_session.close()


def _tick_state_from(graph: BabylonGraph) -> SimulationTickState:
    """Read the published tick state off a LIVE post-tick graph.

    Deliberately NOT ``read_tick_state_from_graph``: that function rebuilds each
    ``CountyEconomicState`` from ``tick_``-prefixed territory-node attrs using a
    field list that carries neither ``surplus_distribution`` nor
    ``rent_extraction`` (`graph_bridge.py:201-290`), so it would report a dark
    Vol III layer no matter how correct U1's wiring is. ``_reconstruct_tick_state``
    reads the real objects straight out of the graph attribute.
    """
    tick_data = graph.get_graph_attr(TICK_DYNAMICS_KEY)
    assert tick_data is not None, (
        f"{TICK_DYNAMICS_KEY} was never published onto the graph — "
        "TickDynamicsSystem did not complete a year-boundary pass"
    )
    tick_state = _reconstruct_tick_state(tick_data)
    assert tick_state is not None, f"{TICK_DYNAMICS_KEY} published an empty payload"
    return tick_state


def test_surplus_distribution_is_non_none_for_at_least_one_county_year() -> None:
    """The headline U1 criterion: the county financial layer actually fires."""
    tick_state = _tick_state_from(_run_to_year_boundary_capturing_graph())
    live = [
        county
        for county in tick_state.county_states.values()
        if county.surplus_distribution is not None
    ]
    assert live, (
        "surplus_distribution is None for every county after crossing a year "
        "boundary — the Vol III county layer is still dark (design §1.1)"
    )


def test_sc001_identity_holds_for_one_hundred_percent_of_observations() -> None:
    """SC-001: s = p + i + r + t within DISTRIBUTION_EPSILON, every observation.

    Asserted as a universal, not a sample statistic: one violating county-year
    is a violated accounting identity, however many others hold.
    """
    tick_state = _tick_state_from(_run_to_year_boundary_capturing_graph())
    observed = 0
    violations: list[tuple[str, float]] = []
    for fips, county in sorted(tick_state.county_states.items()):
        d = county.surplus_distribution
        if d is None:
            continue
        observed += 1
        residual = abs(
            d.total_surplus_produced
            - (d.profit_of_enterprise + d.interest_payments + d.ground_rent + d.taxes_on_surplus)
        )
        if residual > DISTRIBUTION_EPSILON:
            violations.append((fips, residual))
    assert not violations, f"SC-001 violated (residual > {DISTRIBUTION_EPSILON}): {violations}"
    # A universal over an empty domain is vacuously true — SC-001 is only
    # proven if the run actually produced distributions to check.
    assert observed > 0, (
        "SC-001 checked zero observations: no county-year carried a "
        "surplus_distribution, so the identity was never exercised"
    )


def test_tick_ground_rent_carries_a_non_zero_real_figure() -> None:
    """U1.5's repoint proved in a real run, not against a hand-built model.

    Read off the LIVE post-tick graph: ``_reconstruct_territory``
    (`models/world_state.py:232-252`) strips every ``tick_``-prefixed attr on the
    way back into a ``WorldState``, so a post-``step`` ``to_graph()`` would show
    ``0.0`` here for every territory regardless of U1.5.
    """
    graph = _run_to_year_boundary_capturing_graph()
    rents = [
        graph.nodes[node_id].get("tick_ground_rent", 0.0)
        for node_id in graph.nodes
        if graph.nodes[node_id].get("_node_type") == "territory"
    ]
    assert rents, "no territory nodes on the graph — the run built no counties"
    assert any(rent > 0.0 for rent in rents), (
        "every tick_ground_rent is 0.0 — the Path A repoint (U1.5) did not "
        "reach a real FRED B230RC0Q173SBEA-backed figure in a live run"
    )
