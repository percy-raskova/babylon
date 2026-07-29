"""Behavioral laws for DecompositionSystem (P27 Phase-0 coverage backfill, Task 11).

Read end-to-end before writing: ``src/babylon/engine/systems/decomposition.py``
(``DecompositionSystem.step``, lines 110-223, and ``_execute_decomposition``,
lines 263-369 -- the population/wealth split at 293-301 and the transfer
writes at 323-336).

Laws pinned (each traces to a specific source range -- see per-test
docstrings for file:line grounding):

  L1 -- bounded population split: under the SHIPPED DEFAULT carceral
        coefficients (``enforcer_fraction=0.15``, ``proletariat_fraction=0.85``,
        ``territory.py:278-289`` -- these sum to exactly ``1.0``), the total
        population handed to the two targets never exceeds the source LA's
        pre-decomposition population, and loses at most 1 unit per target to
        ``int()`` truncation (``decomposition.py:298-299``:
        ``int(la_population * fraction)`` for each of the two independent
        floor operations).
  L2 -- monotone accumulation: the enforcer and internal-proletariat targets'
        ``population`` and ``wealth`` never DECREASE across a decomposing
        step -- ``decomposition.py:323-336`` writes ``current_pop + gain`` /
        ``current_wealth + gain`` (enforcer) and a flat non-negative
        ``proletariat_pop`` / ``proletariat_wealth`` (internal proletariat),
        both additive, never subtractive.
  L3 -- one-time idempotence: once ``_decomposition_complete`` is set in
        ``context.persistent_data`` (written at ``decomposition.py:222`` after
        a successful run), a subsequent ``step()`` call is a full no-op --
        the early ``return`` at ``decomposition.py:128-129`` fires before any
        read of the graph.
  L4 -- inactivity on absent/exhausted source: with no
        ``SocialRole.LABOR_ARISTOCRACY`` node present, or an LA node with
        ``population <= 0``, ``step()`` mutates NOTHING and publishes no
        ``CLASS_DECOMPOSITION`` event -- ``_execute_decomposition`` returns
        ``False`` at ``decomposition.py:281-282`` (no LA found) or
        ``:290-291`` (population <= 0) strictly BEFORE the first
        ``graph.update_node``/``graph.add_node`` call.

Caveat (NOT a law): decomposition does NOT zero the source LA's own
``population``/``wealth`` attributes -- only ``active`` flips to ``False``
(``decomposition.py:339``, ``graph.update_node(la_id, active=False)``). A
naive "total population summed over every node is conserved across the step"
law is therefore FALSE: the LA's population value is left in place on its
(now-inactive) node while the SAME magnitude is additively copied onto the
enforcer/internal-proletariat targets, so the graph-wide raw sum of
``population`` actually GROWS by construction. Only the source-vs-targets
bound (L1) and the per-target monotonicity (L2) hold; a whole-graph
conservation law would be a false positive.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines import CarceralDefines, GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.decomposition import DecompositionSystem
from babylon.kernel.event_bus import Event
from babylon.models.enums import EventType, SocialRole
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

# Baseline enforcer/internal-proletariat starting state, matching the
# project's real fixture shape (tests/unit/engine/systems/test_la_decomposition.py
# ``_create_pre_crisis_circuit``): enforcers exist at genesis with a small
# population, internal proletariat is dormant (pop 0, inactive) until fed.
_ENFORCER_POP_BEFORE = 50
_ENFORCER_WEALTH_BEFORE = 100.0


def _services(carceral: CarceralDefines | None = None) -> ServiceContainer:
    defines = GameDefines().model_copy(update={"carceral": carceral or CarceralDefines()})
    return ServiceContainer.create(defines=defines)


def _system() -> DecompositionSystem:
    return DecompositionSystem()


def _decomposing_context(tick: int = 200) -> TickContext:
    """A context whose SUPERWAGE_CRISIS delay has already elapsed.

    Mirrors ``test_la_decomposition.py``'s ``_create_test_context``: setting
    ``_superwage_crisis_tick`` far enough in the past (100 ticks) clears even
    the max-allowed ``decomposition_delay`` (520, ``territory.py:298-302``),
    so ``should_decompose`` (``decomposition.py:204-208``) is unconditionally
    ``True`` regardless of which carceral defines a given test uses.
    """
    return TickContext(tick=tick, persistent_data={"_superwage_crisis_tick": tick - 100})


def _la_graph(
    la_population: int,
    la_wealth: float,
    *,
    la_active: bool = True,
) -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node(
        "C_w",
        _node_type="social_class",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=la_wealth,
        population=la_population,
        active=la_active,
    )
    graph.add_node(
        "Enforcer",
        _node_type="social_class",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=_ENFORCER_WEALTH_BEFORE,
        population=_ENFORCER_POP_BEFORE,
        active=True,
    )
    graph.add_node(
        "Int_P",
        _node_type="social_class",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=0.0,
        population=0,
        active=False,
    )
    return graph


class TestBoundedPopulationSplitLaw:
    """L1: total population handed to the two targets never exceeds the
    source LA's pre-decomposition population (default fractions sum to
    exactly 1.0, ``territory.py:278-289``), and the two independent
    ``int()`` floors (``decomposition.py:298-299``) lose at most 1 unit
    each."""

    @given(
        la_population=st.integers(min_value=1, max_value=200_000),
        la_wealth=st.floats(
            min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25, deadline=None)
    def test_population_transferred_never_exceeds_source(
        self, la_population: int, la_wealth: float
    ) -> None:
        graph = _la_graph(la_population, la_wealth)
        services = _services()

        _system().step(graph, services, _decomposing_context())

        enforcer_gain = graph.nodes["Enforcer"]["population"] - _ENFORCER_POP_BEFORE
        proletariat_pop = graph.nodes["Int_P"]["population"]
        total_transferred = enforcer_gain + proletariat_pop

        assert 0 <= total_transferred <= la_population
        # Two floor truncations of fractions summing to 1.0 lose < 1 each.
        assert total_transferred >= la_population - 2

    @given(
        la_wealth=st.floats(
            min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25, deadline=None)
    def test_wealth_transferred_conserved_under_default_fractions(self, la_wealth: float) -> None:
        """Wealth (a float, no truncation) is split exactly under fractions
        that sum to 1.0 -- unlike population, this is an equality, not merely
        a bound (``decomposition.py:300-301``: ``la_wealth * fraction`` for
        each target, with no clamp in between)."""
        graph = _la_graph(la_population=1_000, la_wealth=la_wealth)
        services = _services()

        _system().step(graph, services, _decomposing_context())

        enforcer_wealth_gain = graph.nodes["Enforcer"]["wealth"] - _ENFORCER_WEALTH_BEFORE
        proletariat_wealth = graph.nodes["Int_P"]["wealth"]
        total_transferred = enforcer_wealth_gain + proletariat_wealth

        assert total_transferred == pytest.approx(la_wealth, rel=1e-9, abs=1e-9)


class TestMonotoneAccumulationLaw:
    """L2: the enforcer and internal-proletariat targets' population/wealth
    never decrease across a decomposing step -- both writes at
    ``decomposition.py:323-336`` are additive over the pre-step value."""

    @given(
        la_population=st.integers(min_value=1, max_value=200_000),
        la_wealth=st.floats(
            min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25, deadline=None)
    def test_targets_never_regress(self, la_population: int, la_wealth: float) -> None:
        graph = _la_graph(la_population, la_wealth)
        services = _services()

        _system().step(graph, services, _decomposing_context())

        assert graph.nodes["Enforcer"]["population"] >= _ENFORCER_POP_BEFORE
        assert graph.nodes["Enforcer"]["wealth"] >= _ENFORCER_WEALTH_BEFORE
        assert graph.nodes["Int_P"]["population"] >= 0
        assert graph.nodes["Int_P"]["wealth"] >= 0.0
        # LA itself is deactivated but its own population/wealth fields are
        # left untouched (see module docstring caveat) -- assert the specific
        # thing the source actually does, not the conservation shape one
        # might expect from a "transfer".
        assert graph.nodes["C_w"]["active"] is False
        assert graph.nodes["C_w"]["population"] == la_population
        assert graph.nodes["C_w"]["wealth"] == la_wealth


class TestOneTimeIdempotenceLaw:
    """L3: once ``_decomposition_complete`` is set, a subsequent ``step()``
    is a full no-op -- the early ``return`` at ``decomposition.py:128-129``
    fires before any graph access."""

    def test_second_step_after_completion_is_a_no_op(self) -> None:
        graph = _la_graph(la_population=1_000, la_wealth=500.0)
        services = _services()
        system = _system()
        context = _decomposing_context(tick=200)

        system.step(graph, services, context)
        assert context.persistent_data.get("_decomposition_complete") is True

        enforcer_pop_after_first = graph.nodes["Enforcer"]["population"]
        enforcer_wealth_after_first = graph.nodes["Enforcer"]["wealth"]
        prole_pop_after_first = graph.nodes["Int_P"]["population"]
        prole_wealth_after_first = graph.nodes["Int_P"]["wealth"]

        second_context = TickContext(tick=300, persistent_data=context.persistent_data)
        system.step(graph, services, second_context)

        assert graph.nodes["Enforcer"]["population"] == enforcer_pop_after_first
        assert graph.nodes["Enforcer"]["wealth"] == enforcer_wealth_after_first
        assert graph.nodes["Int_P"]["population"] == prole_pop_after_first
        assert graph.nodes["Int_P"]["wealth"] == prole_wealth_after_first


class TestInactivityLaw:
    """L4: with no LABOR_ARISTOCRACY node present, or one with
    ``population <= 0``, ``step()`` mutates nothing and publishes no
    CLASS_DECOMPOSITION event -- both early-return branches
    (``decomposition.py:281-282``, ``:290-291``) fire before any write."""

    def test_no_labor_aristocracy_node_writes_nothing(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "Enforcer",
            _node_type="social_class",
            role=SocialRole.CARCERAL_ENFORCER,
            wealth=_ENFORCER_WEALTH_BEFORE,
            population=_ENFORCER_POP_BEFORE,
            active=True,
        )
        graph.add_node(
            "Int_P",
            _node_type="social_class",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=0.0,
            population=0,
            active=False,
        )
        services = _services()
        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CLASS_DECOMPOSITION, lambda e: captured_events.append(e)
        )

        _system().step(graph, services, _decomposing_context())

        assert graph.nodes["Enforcer"]["population"] == _ENFORCER_POP_BEFORE
        assert graph.nodes["Enforcer"]["wealth"] == _ENFORCER_WEALTH_BEFORE
        assert graph.nodes["Int_P"]["population"] == 0
        assert graph.nodes["Int_P"]["active"] is False
        assert captured_events == []

    def test_zero_population_labor_aristocracy_writes_nothing(self) -> None:
        graph = _la_graph(la_population=0, la_wealth=500.0)
        services = _services()
        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CLASS_DECOMPOSITION, lambda e: captured_events.append(e)
        )

        _system().step(graph, services, _decomposing_context())

        assert graph.nodes["C_w"]["active"] is True
        assert graph.nodes["Enforcer"]["population"] == _ENFORCER_POP_BEFORE
        assert graph.nodes["Int_P"]["population"] == 0
        assert captured_events == []
