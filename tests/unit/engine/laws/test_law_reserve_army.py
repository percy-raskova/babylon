"""Behavioral law for ReserveArmySystem (P27 Phase-0 backfill, section 8.4).

Laws pinned (grounded by reading step() + DefaultWagePressureCalculator
end-to-end -- src/babylon/engine/systems/reserve_army.py,
src/babylon/domain/economics/reserve_army/calculator.py):

  L1 -- inactivity on zero reserve_ratio: reserve_ratio == 0.0 (the model
       default, and the value when the attribute is absent -- see
       Territory's field default in models/entities/territory.py) leaves
       median_wage byte-unchanged and emits no RESERVE_ARMY_PRESSURE event
       for ANY starting median_wage (reserve_army.py:80-81, the
       'if reserve_ratio <= 0.0: continue' guard fires before any mutation
       or publish).
  L2 -- wage_pressure is clamped to [0, wage_pressure_ceiling]: the calculator
       normalizes the sigmoid into [0, 1] and scales by ceiling
       (calculator.py:64-65); with the default ceiling (0.5,
       defines.yaml:415) median_wage can never be driven to zero or below
       when it started positive, since '1.0 - wage_pressure' stays > 0
       (reserve_army.py:106).
  L3 -- monotonicity: for a fixed defines config, a strictly larger
       reserve_ratio produces a wage_pressure that is never smaller (the
       sigmoid raw = 1 / (1 + exp(-k * (ratio - r0))) is strictly
       increasing in ratio for k > 0, and the affine normalize/clamp in
       calculator.py:64-65 preserves that ordering) -- hence never a larger
       resulting median_wage.
  L4 -- event/node agreement: when an event IS published, its payload
       median_wage field equals the node's post-step median_wage exactly
       (reserve_army.py:106 computes updates['median_wage']; line 118
       reads back updates.get('median_wage', ...) for the same event) --
       the event is a mirror of the mutation, never a stale or divergent
       read.

Caveats (not laws):
  - L3 is only weak (>=), not strict, because the calculator clamps at
    the ceiling -- two sufficiently large ratios both saturate to the same
    wage_pressure.
  - The negative branch of 'if reserve_ratio <= 0.0: continue'
    (reserve_army.py:80-81) is defensive code with no reachable in-domain
    input: Territory's reserve_ratio field is constrained ge=0.0, so only
    the == 0.0 boundary is exercised through the real factory. L1 below
    tests that boundary, not the negative case.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.reserve_army import ReserveArmySystem
from babylon.models.entities.territory import Territory
from babylon.models.enums import EventType, SectorType
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph

# Reserve ratio is a fraction of the labor force, [0, 1] by domain
# construction (docstring of DefaultWagePressureCalculator.compute_wage_pressure).
_RATIO_STRATEGY = st.floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
)
# Territory (the real Pydantic model -- models/entities/territory.py)
# constrains reserve_ratio >= 0.0, so the only in-domain non-positive value
# reachable through the real factory is the boundary 0.0 itself (the
# system's own default when the attribute is absent). Negative ratios never
# occur in production data; the '<= 0.0' guard's negative branch is
# defensive code with no reachable in-domain input, not a law to pin.
_ARBITRARY_WAGE_STRATEGY = st.floats(
    min_value=1.0,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)


def _make_territory_graph(
    territories: dict[str, dict[str, float]],
) -> BabylonGraph:
    """Build a to_graph-shaped test graph with territory nodes.

    Mirrors tests/unit/engine/systems/test_reserve_army_system.py's
    _make_territory_graph -- nodes carry the exact
    _node_type='territory' marker production writes
    (WorldState.to_graph), never a hand-stamped string
    (vocabulary-sentinel law).
    """
    state = WorldState(
        tick=0,
        territories={
            node_id: Territory(
                id=node_id,
                name=f"County {node_id}",
                sector_type=SectorType.RESIDENTIAL,
                **attrs,
            )
            for node_id, attrs in territories.items()
        },
    )
    return state.to_graph()


def _make_services() -> ServiceContainer:
    """Minimal DB-free service container (default GameDefines)."""
    return ServiceContainer.create()


class TestReserveArmyInactivityLaw:
    """L1 -- zero reserve_ratio is a strict no-op, for any starting wage."""

    @given(wage=_ARBITRARY_WAGE_STRATEGY)
    @settings(max_examples=25, deadline=None)
    def test_zero_ratio_leaves_wage_unchanged(self, wage: float) -> None:
        graph = _make_territory_graph({"T001": {"reserve_ratio": 0.0, "median_wage": wage}})
        # Territory's median_wage field is quantized onto the 1e-5 grid at
        # construction (Currency = Annotated[float, ..., SnapToGrid] --
        # models/types.py:104-111); read the STORED value back rather than
        # comparing against the raw hypothesis input, which may not itself
        # sit on the grid.
        before = graph.nodes["T001"]["median_wage"]
        services = _make_services()
        system = ReserveArmySystem()

        events_received: list[object] = []
        services.event_bus.subscribe(
            EventType.RESERVE_ARMY_PRESSURE,
            lambda e: events_received.append(e),
        )

        system.step(graph, services, TickContext(tick=1))

        assert graph.nodes["T001"]["median_wage"] == before
        assert "wage_pressure" not in graph.nodes["T001"]
        assert len(events_received) == 0


class TestReserveArmyBoundLaw:
    """L2 -- wage_pressure stays within [0, ceiling]; wage never hits zero."""

    @given(ratio=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=25, deadline=None)
    def test_wage_pressure_bounded_and_wage_stays_positive(self, ratio: float) -> None:
        graph = _make_territory_graph({"T001": {"reserve_ratio": ratio, "median_wage": 1000.0}})
        services = _make_services()
        ceiling = services.defines.reserve_army.wage_pressure_ceiling
        system = ReserveArmySystem()

        system.step(graph, services, TickContext(tick=1))

        node = graph.nodes["T001"]
        pressure = node.get("wage_pressure", 0.0)
        assert 0.0 <= pressure <= ceiling
        assert node["median_wage"] > 0.0


class TestReserveArmyMonotonicityLaw:
    """L3 -- a larger reserve_ratio never produces a smaller wage_pressure."""

    @given(
        ratio_low=_RATIO_STRATEGY,
        ratio_delta=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_higher_ratio_never_produces_lower_pressure(
        self, ratio_low: float, ratio_delta: float
    ) -> None:
        ratio_high = min(1.0, ratio_low + ratio_delta)

        graph_low = _make_territory_graph(
            {"T001": {"reserve_ratio": ratio_low, "median_wage": 1000.0}}
        )
        graph_high = _make_territory_graph(
            {"T002": {"reserve_ratio": ratio_high, "median_wage": 1000.0}}
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph_low, services, TickContext(tick=1))
        system.step(graph_high, services, TickContext(tick=1))

        pressure_low = graph_low.nodes["T001"].get("wage_pressure", 0.0)
        pressure_high = graph_high.nodes["T002"].get("wage_pressure", 0.0)

        assert pressure_high >= pressure_low - 1e-12


class TestReserveArmyEventAgreementLaw:
    """L4 -- the published event's median_wage mirrors the node's post-step value."""

    @given(ratio=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=25, deadline=None)
    def test_event_median_wage_matches_node(self, ratio: float) -> None:
        graph = _make_territory_graph({"T001": {"reserve_ratio": ratio, "median_wage": 1000.0}})
        services = _make_services()
        system = ReserveArmySystem()

        events_received: list[object] = []
        services.event_bus.subscribe(
            EventType.RESERVE_ARMY_PRESSURE,
            lambda e: events_received.append(e),
        )

        system.step(graph, services, TickContext(tick=1))

        assert len(events_received) == 1
        event = events_received[0]
        assert event.payload["median_wage"] == graph.nodes["T001"]["median_wage"]
