"""Behavioral laws for ControlRatioSystem (P27 Phase-0 coverage backfill,
Task 11).

Read end-to-end before writing:
``src/babylon/engine/systems/control_ratio.py`` (``ControlRatioSystem.step``,
lines 105-173, plus the two aggregation helpers it calls,
``_count_enforcer_population`` lines 52-61 and
``_count_prisoner_population_and_org`` lines 64-83), and the coefficients it
reads, ``src/babylon/config/defines/territory.py::CarceralDefines``
(lines 248-315).

Laws pinned (each traces to a specific source range -- see per-test
docstrings for file:line grounding):

  L1 -- clamp/threshold: ``CONTROL_RATIO_CRISIS`` fires iff
        ``prisoner_pop > enforcer_pop * control_capacity`` -- for ANY
        (enforcer_pop, control_capacity, prisoner_pop) triple, once the
        decomposition-delay gate is open (``control_ratio.py:150``'s
        ``if prisoner_pop <= max_controllable: return`` is the exact
        boundary; the exactly-at-capacity case is a documented no-crisis
        boundary, mirrored from the existing example test
        ``test_exactly_at_capacity_no_crisis``).
  L2 -- inactivity on empty input: when there are zero eligible prisoners
        (no ``INTERNAL_PROLETARIAT``/``LUMPENPROLETARIAT`` node present, or
        one present with ``population=0``), the step is a full no-op --
        ``control_ratio.py:141``'s ``if prisoner_pop == 0: return`` fires
        before any capacity read or persistent-state write, so neither
        ``CONTROL_RATIO_CRISIS`` nor ``TERMINAL_DECISION`` is ever emitted
        and no ``_control_crisis_emitted``/``_control_ratio_crisis_tick`` key
        is written into ``context.persistent_data``.
  L3 -- monotonicity: ``avg_organization`` (the population-weighted mean
        computed at ``control_ratio.py:171``,
        ``prisoner_org_sum / prisoner_pop``, fed by the accumulation loop at
        ``control_ratio.py:76-82``) is non-decreasing in any one prisoner
        node's ``organization`` value, holding every population fixed --
        the textbook monotonicity property of a weighted arithmetic mean.
        NOTE (caveat, not a law): this system never clamps
        ``avg_organization`` to ``[0, 1]`` itself -- that range only holds
        because upstream ``SocialClass.organization`` is a ``Probability``
        field (``models/entities/social_class.py:355-358``); a hand-built
        graph with out-of-domain organization values (as this system reads
        raw dict attributes with no validation) would produce an
        out-of-domain weighted mean too, so only the *relative* monotonicity
        is asserted, not absolute boundedness.
  L4 -- idempotency/latch: for ANY unstable state, repeating ``step()``
        across successive ticks on the SAME ``persistent_data`` dict fires
        ``CONTROL_RATIO_CRISIS`` at most once and ``TERMINAL_DECISION`` at
        most once, never more -- the ``_control_crisis_emitted`` guard
        (``control_ratio.py:154,158``) latches the crisis emission, and the
        ``_terminal_decision_emitted`` guard (``control_ratio.py:124,173``)
        makes every subsequent call an immediate no-op.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines import CarceralDefines, GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.control_ratio import ControlRatioSystem
from babylon.kernel.event_bus import Event
from babylon.models.enums import EventType, SocialRole
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _services(carceral: CarceralDefines | None = None) -> ServiceContainer:
    defines = GameDefines().model_copy(update={"carceral": carceral or CarceralDefines()})
    return ServiceContainer.create(defines=defines)


def _enforcer(graph: BabylonGraph, node_id: str, population: int) -> None:
    graph.add_node(
        node_id,
        _node_type="social_class",
        role=SocialRole.CARCERAL_ENFORCER,
        population=population,
        active=True,
        organization=0.0,
    )


def _prisoner(
    graph: BabylonGraph,
    node_id: str,
    role: SocialRole,
    population: int,
    organization: float,
) -> None:
    graph.add_node(
        node_id,
        _node_type="social_class",
        role=role,
        population=population,
        active=True,
        organization=organization,
    )


def _captured(services: ServiceContainer, event_type: EventType) -> list[Event]:
    captured: list[Event] = []
    services.event_bus.subscribe(event_type, lambda e: captured.append(e))
    return captured


class TestCrisisThresholdClampLaw:
    """L1: for ANY (enforcer_pop, control_capacity, prisoner_pop), the crisis
    fires iff ``prisoner_pop > enforcer_pop * control_capacity``
    (``control_ratio.py:150``)."""

    @given(
        enforcer_pop=st.integers(min_value=0, max_value=1_000),
        control_capacity=st.integers(min_value=1, max_value=20),
        prisoner_pop=st.integers(min_value=0, max_value=20_000),
    )
    @settings(max_examples=25, deadline=None)
    def test_crisis_iff_prisoners_exceed_capacity(
        self, enforcer_pop: int, control_capacity: int, prisoner_pop: int
    ) -> None:
        graph = BabylonGraph()
        _enforcer(graph, "Enforcer", enforcer_pop)
        _prisoner(graph, "Int_P", SocialRole.INTERNAL_PROLETARIAT, prisoner_pop, 0.0)

        services = _services(CarceralDefines(control_capacity=control_capacity))
        crisis_events = _captured(services, EventType.CONTROL_RATIO_CRISIS)

        # Default control_ratio_delay=52; decomposition happened at tick 0,
        # so tick=52 is exactly the delay-gate-open boundary
        # (control_ratio.py:132-133).
        context = TickContext(tick=52, persistent_data={"_class_decomposition_tick": 0})

        ControlRatioSystem().step(graph, services, context)

        expect_crisis = prisoner_pop > enforcer_pop * control_capacity
        assert len(crisis_events) == (1 if expect_crisis else 0)


class TestInactivityOnEmptyPrisonersLaw:
    """L2: zero eligible prisoners is a full no-op
    (``control_ratio.py:141``'s early return)."""

    @given(
        enforcer_pop=st.integers(min_value=0, max_value=1_000),
        include_zero_pop_prisoner=st.booleans(),
    )
    @settings(max_examples=25, deadline=None)
    def test_no_prisoners_is_a_full_noop(
        self, enforcer_pop: int, include_zero_pop_prisoner: bool
    ) -> None:
        graph = BabylonGraph()
        _enforcer(graph, "Enforcer", enforcer_pop)
        if include_zero_pop_prisoner:
            _prisoner(graph, "Int_P", SocialRole.INTERNAL_PROLETARIAT, 0, 0.5)

        services = _services()
        crisis_events = _captured(services, EventType.CONTROL_RATIO_CRISIS)
        terminal_events = _captured(services, EventType.TERMINAL_DECISION)

        context = TickContext(tick=52, persistent_data={"_class_decomposition_tick": 0})

        ControlRatioSystem().step(graph, services, context)

        assert crisis_events == []
        assert terminal_events == []
        assert "_control_crisis_emitted" not in context.persistent_data
        assert "_control_ratio_crisis_tick" not in context.persistent_data


class TestAvgOrganizationMonotonicityLaw:
    """L3: avg_organization (control_ratio.py:171) is non-decreasing in one
    prisoner node's organization, holding populations fixed. Uses
    control_capacity=1 and enforcer_pop=0 (no enforcer node at all) so ANY
    positive total prisoner population unconditionally exceeds
    max_controllable=0, guaranteeing the crisis fires regardless of the
    hypothesis-generated population split; control_ratio_delay=0 and
    terminal_decision_delay=0 so a SINGLE step() call both raises the crisis
    and (since ``tick < crisis_tick + 0`` is false the instant crisis_tick is
    set to the same tick) immediately emits TERMINAL_DECISION too."""

    @given(
        pop_a=st.integers(min_value=1, max_value=1_000),
        org_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        pop_b=st.integers(min_value=1, max_value=1_000),
        org_b_low=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        org_b_high=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_avg_organization_nondecreasing_in_one_input(
        self,
        pop_a: int,
        org_a: float,
        pop_b: int,
        org_b_low: float,
        org_b_high: float,
    ) -> None:
        org_lo, org_hi = sorted((org_b_low, org_b_high))

        def _avg_organization(org_b: float) -> float:
            graph = BabylonGraph()
            _prisoner(graph, "Int_P", SocialRole.INTERNAL_PROLETARIAT, pop_a, org_a)
            _prisoner(graph, "Lumpen", SocialRole.LUMPENPROLETARIAT, pop_b, org_b)

            carceral = CarceralDefines(
                control_capacity=1, control_ratio_delay=0, terminal_decision_delay=0
            )
            services = _services(carceral)
            terminal_events = _captured(services, EventType.TERMINAL_DECISION)

            context = TickContext(tick=0, persistent_data={"_class_decomposition_tick": 0})
            ControlRatioSystem().step(graph, services, context)

            assert len(terminal_events) == 1, "fixture must reach TERMINAL_DECISION"
            avg_org = terminal_events[0].payload["avg_organization"]
            assert isinstance(avg_org, float)
            return avg_org

        avg_lo = _avg_organization(org_lo)
        avg_hi = _avg_organization(org_hi)

        assert avg_hi >= avg_lo - 1e-9


class TestIdempotentLatchLaw:
    """L4: repeating step() over successive ticks on the SAME
    persistent_data dict fires each of CONTROL_RATIO_CRISIS and
    TERMINAL_DECISION at most once -- the ``_control_crisis_emitted`` /
    ``_terminal_decision_emitted`` guards (control_ratio.py:124,154,158,173)
    latch them shut."""

    @given(
        enforcer_pop=st.integers(min_value=0, max_value=1_000),
        control_capacity=st.integers(min_value=1, max_value=20),
        excess=st.integers(min_value=1, max_value=1_000),
    )
    @settings(max_examples=25, deadline=None)
    def test_crisis_and_terminal_each_fire_at_most_once(
        self, enforcer_pop: int, control_capacity: int, excess: int
    ) -> None:
        # prisoner_pop is always strictly above max_controllable, for any
        # generated (enforcer_pop, control_capacity) pair.
        prisoner_pop = enforcer_pop * control_capacity + excess

        graph = BabylonGraph()
        _enforcer(graph, "Enforcer", enforcer_pop)
        _prisoner(graph, "Int_P", SocialRole.INTERNAL_PROLETARIAT, prisoner_pop, 0.9)

        carceral = CarceralDefines(control_capacity=control_capacity)  # default delays: 52, 1
        services = _services(carceral)
        crisis_events = _captured(services, EventType.CONTROL_RATIO_CRISIS)
        terminal_events = _captured(services, EventType.TERMINAL_DECISION)

        # One TickContext, mutated tick-in-place across calls (matching the
        # existing example test's pattern,
        # ``test_crisis_emitted_once_on_repeated_steps``) -- constructing a
        # FRESH TickContext per tick from the same outer dict would silently
        # discard the in-place ``persistent_data`` writes ControlRatioSystem
        # depends on, since pydantic validates/copies the dict on
        # construction.
        context = TickContext(tick=52, persistent_data={"_class_decomposition_tick": 0})
        system = ControlRatioSystem()
        for tick in (52, 53, 54):
            context["tick"] = tick
            system.step(graph, services, context)

        assert len(crisis_events) == 1
        assert len(terminal_events) == 1
