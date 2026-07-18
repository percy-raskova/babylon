"""U1 acceptance (design §4): `s = p + i + r + t` has NEVER evaluated in a
shipped run. This is the first test that makes it do so end-to-end, over the
real reference DB, and pins SC-001 — the identity holds within
DISTRIBUTION_EPSILON for 100% of observations, not merely on average.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from babylon.domain.economics.distribution.types import DISTRIBUTION_EPSILON
from babylon.domain.economics.tick.graph_bridge import (
    TICK_DYNAMICS_KEY,
    _reconstruct_tick_state,
)

if TYPE_CHECKING:
    from babylon.domain.economics.tensor_registry import TensorRegistry
    from babylon.domain.economics.tick.types import SimulationTickState
    from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

WAYNE_FIPS = "26163"
#: Ticks driven through ``step`` before the capturing pass. Tick 0 is itself a
#: year boundary (bootstraps 2010); after 52 calls ``state.tick == 52``, which is
#: the NEXT boundary — the tick the capturing pass runs and observes (2011).
_TICKS_BEFORE_CAPTURE = 52

#: Relative tolerance for the SC-001 residual, applied on top of the absolute
#: ``DISTRIBUTION_EPSILON`` floor.
#:
#: Derivation (Constitution III.12 / tolerance-policy rule): the residual is a
#: sum-and-difference of four IEEE-754 binary64 magnitudes. Each term carries at
#: most 0.5 ulp of representation error, and the four-term summation plus the
#: outer subtraction accumulate at most ~5 roundings, so the worst-case residual
#: is bounded by ~5 · 2^-53 · |s| ≈ 5.6e-16 · |s|. ``1e-12`` leaves ~3.5 orders
#: of headroom over that bound, and remains far tighter than any real accounting
#: breach: on Wayne's ~3.5e9 surplus it admits at most ~0.0035 units of slack,
#: so a mis-distribution of even one unit is still caught.
#:
#: Why relative at all: ``DISTRIBUTION_EPSILON`` is an ABSOLUTE 1e-9, while
#: Wayne's real 2011 surplus is ~3.5e9 labor-hours, where one ulp is ~4.8e-7 —
#: 500x the epsilon. The current residual is exactly 0.0 only by fortuitous
#: cancellation; as U3-U6 add counties and shift magnitudes, an absolute-only
#: comparison would go red for pure floating-point reasons and report a
#: non-existent accounting-identity breach.
_SC001_RELATIVE_TOLERANCE = 1e-12

#: Tensor-year fallback window mirroring ``TickDynamicsSystem._get_best_tensor_year``
#: (``domain/economics/tick/system/__init__.py``): the system reads the county
#: surplus at the first of ``[year, year-1, year-2]`` the registry can serve.
_TENSOR_YEAR_FALLBACK = (0, -1, -2)


def _run_to_year_boundary_capturing_graph() -> tuple[BabylonGraph, TensorRegistry]:
    """Run a Wayne-scoped simulation to a year boundary; return the LIVE graph.

    Returns the hydrated ``TensorRegistry`` alongside the graph so SC-001 can
    cross-check the distributed surplus against the INDEPENDENT source that fed
    it (``ValueTensor4x3.total_s``) rather than against a computed property's
    own definition.

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
        tensor_registry = overrides["tensor_registry"]
        assert tensor_registry is not None, (
            "_build_economics_overrides wired no tensor_registry for "
            f"{WAYNE_FIPS} — the county surplus source is absent, so SC-001 "
            "cannot be cross-checked against production's input"
        )
        # The registry is an in-memory (fips, year) cache, so it stays readable
        # after the Leontief session closes below.
        return graph, tensor_registry
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
    graph, _registry = _run_to_year_boundary_capturing_graph()
    tick_state = _tick_state_from(graph)
    live = [
        county
        for county in tick_state.county_states.values()
        if county.surplus_distribution is not None
    ]
    assert live, (
        "surplus_distribution is None for every county after crossing a year "
        "boundary — the Vol III county layer is still dark (design §1.1)"
    )


def _best_tensor_surplus(registry: TensorRegistry, fips: str, year: int) -> float | None:
    """Independently re-read the county surplus production consumed.

    Mirrors ``TickDynamicsSystem._get_best_tensor_year`` +
    ``_get_county_surplus``: the first of ``[year, year-1, year-2]`` the
    registry can serve, read as ``ValueTensor4x3.total_s``. This is the SOURCE
    side of the SC-001 cross-check — deliberately reached without going through
    the distribution object, so a fabricated or drifted surplus is detectable.
    """
    from babylon.domain.economics.tensor import NoDataSentinel

    for offset in _TENSOR_YEAR_FALLBACK:
        tensor = registry.get(fips, year + offset)
        if isinstance(tensor, NoDataSentinel):
            continue
        total_s = getattr(tensor, "total_s", None)
        if total_s is not None:
            return float(total_s)
    return None


def test_sc001_identity_holds_for_one_hundred_percent_of_observations() -> None:
    """SC-001: s = p + i + r + t, every observation, against a real source.

    Asserted as a universal, not a sample statistic: one violating county-year
    is a violated accounting identity, however many others hold.

    Three things are asserted, because the residual alone proves nothing.
    ``profit_of_enterprise`` is a ``@computed_field`` defined as
    ``s - i - r - t`` (``distribution/types.py``), so
    ``s - (p + i + r + t)`` substitutes to ``s - ((s-i-r-t)+i+r+t)`` — an
    algebraic tautology that is 0.0 for ANY inputs, including all-zero or
    fabricated ones. So:

    1. **Substance** — every distributed term is finite and strictly positive.
       An all-zero or partially-dark distribution turns this red; the tautology
       would not have noticed.
    2. **Provenance** — ``total_surplus_produced`` is cross-checked against the
       independently re-read ``ValueTensor4x3.total_s`` that fed it, so the
       assertion pins production against source rather than against itself.
    3. **Closure** — the residual, on a magnitude-scaled tolerance.
    """
    graph, registry = _run_to_year_boundary_capturing_graph()
    tick_state = _tick_state_from(graph)
    observed = 0
    violations: list[tuple[str, float]] = []
    for fips, county in sorted(tick_state.county_states.items()):
        d = county.surplus_distribution
        if d is None:
            continue
        observed += 1

        # (1) Substance: no term may be dark, fabricated-zero, or non-finite.
        for name, value in (
            ("total_surplus_produced", d.total_surplus_produced),
            ("interest_payments", d.interest_payments),
            ("ground_rent", d.ground_rent),
            ("taxes_on_surplus", d.taxes_on_surplus),
            ("profit_of_enterprise", d.profit_of_enterprise),
        ):
            assert math.isfinite(value), f"{fips}/{d.year}: {name} is not finite ({value})"
            assert value > 0.0, (
                f"{fips}/{d.year}: {name} is {value} — a distributed term is "
                "dark or zero, so SC-001's identity is being satisfied "
                "vacuously rather than by a real decomposition"
            )

        # (2) Provenance: the surplus being distributed is the surplus the
        # tensor registry actually holds for this county-year.
        source_surplus = _best_tensor_surplus(registry, fips, d.year)
        assert source_surplus is not None, (
            f"{fips}/{d.year}: the tensor registry serves no total_s for any "
            "year in the [y, y-1, y-2] fallback window, yet a "
            "surplus_distribution exists — its surplus has no source"
        )
        source_gap = abs(d.total_surplus_produced - source_surplus)
        assert source_gap <= max(
            DISTRIBUTION_EPSILON, abs(source_surplus) * _SC001_RELATIVE_TOLERANCE
        ), (
            f"{fips}/{d.year}: distributed surplus {d.total_surplus_produced} "
            f"does not match the ValueTensor4x3 total_s {source_surplus} that "
            f"fed it (gap {source_gap}) — the financial layer is distributing "
            "a number the production layer never produced"
        )

        # (3) Closure, on a magnitude-scaled tolerance (see
        # _SC001_RELATIVE_TOLERANCE for the derivation).
        residual = abs(
            d.total_surplus_produced
            - (d.profit_of_enterprise + d.interest_payments + d.ground_rent + d.taxes_on_surplus)
        )
        tolerance = max(
            DISTRIBUTION_EPSILON, abs(d.total_surplus_produced) * _SC001_RELATIVE_TOLERANCE
        )
        if residual > tolerance:
            violations.append((fips, residual))
    assert not violations, f"SC-001 violated (residual exceeds tolerance): {violations}"
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
    graph, _registry = _run_to_year_boundary_capturing_graph()
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
