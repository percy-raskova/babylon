"""Behavioral-law tests for DispossessionEventSystem (Program 27 Phase 0, Task 11).

Laws evidenced directly by the source (grounding cited per-test):

  L1 (conservation):    when a value transfer fires, net_received +
                         deadweight_loss == transfer_amount, and territory
                         wealth drops by exactly transfer_amount.
  L2 (clamp):            transfer never exceeds pre-transfer wealth; wealth
                         after step() is always >= 0 and never increases.
  L3 (inactivity):        if all three activity rates (foreclosure/eviction/
                         displacement) are <= 0, the system does not touch
                         the node and publishes no events -- even when the
                         structural factors (concentrated_ownership,
                         absentee_landlord_share) are maximal.
  L4 (bounds+monotone):  stored dispossession_intensity is always in [0, 1],
                         and is monotonically non-decreasing in
                         foreclosure_rate holding all other inputs fixed.

Source under test: src/babylon/engine/systems/dispossession_events.py
Calculator: src/babylon/domain/economics/dispossession/intensity.py
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.kernel.event_bus import Event
from babylon.models.entities.territory import Territory
from babylon.models.enums import EventType, SectorType
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph

# Reuses the exact `_make_territory_graph` shape from
# tests/unit/engine/systems/test_dispossession_event_system.py: a real
# WorldState -> to_graph() round trip, never a hand-stamped _node_type.
TERRITORY_ID = "T001"

_UNIT_FLOAT = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_WEALTH = st.floats(min_value=0.0, max_value=1_000_000_000.0, allow_nan=False, allow_infinity=False)


def _make_territory_graph(attrs: dict[str, float]) -> BabylonGraph:
    """Build a to_graph()-shaped world with a single territory node.

    Mirrors tests/unit/engine/systems/test_dispossession_event_system.py's
    ``_make_territory_graph`` -- the project's real factory for this system,
    not a hand-stamped fixture.
    """
    state = WorldState(
        tick=0,
        territories={
            TERRITORY_ID: Territory(
                id=TERRITORY_ID,
                name="County Under Test",
                sector_type=SectorType.RESIDENTIAL,
                **attrs,
            ),
        },
    )
    return state.to_graph()


def _make_services() -> ServiceContainer:
    return ServiceContainer.create()


def _run(attrs: dict[str, float]) -> tuple[BabylonGraph, list[Event], list[Event]]:
    """Run one tick of DispossessionEventSystem, capturing both event kinds."""
    graph = _make_territory_graph(attrs)
    services = _make_services()
    disposition_events: list[Event] = []
    transfer_events: list[Event] = []
    services.event_bus.subscribe(
        EventType.DISPOSSESSION_EVENT, lambda e: disposition_events.append(e)
    )
    services.event_bus.subscribe(EventType.VALUE_TRANSFER, lambda e: transfer_events.append(e))
    system = DispossessionEventSystem()
    system.step(graph, services, TickContext(tick=1))
    return graph, disposition_events, transfer_events


class TestConservationLaw:
    """L1: net_received + deadweight_loss == transfer_amount; wealth drops
    by exactly transfer_amount.

    Grounding: dispossession_events.py:95-101 computes and clamps
    transfer_amount then does
    ``protocol.update_node(node_id, wealth=territory_wealth - transfer_amount)``;
    intensity.py:76-78's compute_value_transfer computes
    ``received = total_value - deadweight`` so received + deadweight ==
    total_value by construction.
    """

    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        foreclosure_rate=st.floats(
            min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        wealth=st.floats(
            min_value=1_000.0,
            max_value=1_000_000_000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_value_transfer_conserved(self, foreclosure_rate: float, wealth: float) -> None:
        graph, _disp_events, transfer_events = _run(
            {"foreclosure_rate": foreclosure_rate, "wealth": wealth}
        )

        assert len(transfer_events) == 1, "positive foreclosure_rate + wealth must transfer"
        payload = transfer_events[0].payload
        total = payload["total_transferred"]
        net = payload["net_received"]
        deadweight = payload["deadweight_loss"]

        assert net + deadweight == pytest.approx(total, rel=1e-9, abs=1e-6)
        assert graph.nodes[TERRITORY_ID]["wealth"] == pytest.approx(
            wealth - total, rel=1e-9, abs=1e-6
        )


class TestClampLaw:
    """L2: transfer_amount <= pre-transfer wealth; wealth after step() is
    always >= 0 and never increases.

    Grounding: dispossession_events.py:96
    ``transfer_amount = min(transfer_amount, territory_wealth)``.
    """

    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        foreclosure_rate=_UNIT_FLOAT,
        eviction_rate=_UNIT_FLOAT,
        displacement_rate=_UNIT_FLOAT,
        concentrated_ownership=_UNIT_FLOAT,
        absentee_landlord_share=_UNIT_FLOAT,
        wealth=_WEALTH,
    )
    def test_wealth_never_negative_or_increasing(
        self,
        foreclosure_rate: float,
        eviction_rate: float,
        displacement_rate: float,
        concentrated_ownership: float,
        absentee_landlord_share: float,
        wealth: float,
    ) -> None:
        graph, _disp_events, _transfer_events = _run(
            {
                "foreclosure_rate": foreclosure_rate,
                "eviction_rate": eviction_rate,
                "displacement_rate": displacement_rate,
                "concentrated_ownership": concentrated_ownership,
                "absentee_landlord_share": absentee_landlord_share,
                "wealth": wealth,
            }
        )

        wealth_after = graph.nodes[TERRITORY_ID]["wealth"]
        assert wealth_after >= 0.0
        # +epsilon: Currency's SnapToGrid quantization (see
        # TestInactivityLaw) can round wealth up by up to half a 10**-6
        # grid step at construction -- an unrelated determinism property.
        assert wealth_after <= wealth + 1e-5


class TestInactivityLaw:
    """L3: all three activity rates <= 0 => node untouched, no events --
    even when structural factors are maximal.

    Grounding: dispossession_events.py:75-76
    ``if foreclosure_rate <= 0.0 and eviction_rate <= 0.0 and
    displacement_rate <= 0.0: continue`` -- this gate reads only the three
    rate fields; concentrated_ownership/absentee_landlord_share are never
    consulted to decide activity, only to weight intensity once active.
    """

    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        concentrated_ownership=_UNIT_FLOAT,
        absentee_landlord_share=_UNIT_FLOAT,
        wealth=_WEALTH,
    )
    def test_zero_activity_rates_are_inert_even_with_structural_factors(
        self,
        concentrated_ownership: float,
        absentee_landlord_share: float,
        wealth: float,
    ) -> None:
        graph, disp_events, transfer_events = _run(
            {
                "foreclosure_rate": 0.0,
                "eviction_rate": 0.0,
                "displacement_rate": 0.0,
                "concentrated_ownership": concentrated_ownership,
                "absentee_landlord_share": absentee_landlord_share,
                "wealth": wealth,
            }
        )

        assert disp_events == []
        assert transfer_events == []
        assert "dispossession_intensity" not in graph.nodes[TERRITORY_ID]
        # approx, not ==: Currency (models/types.py) carries the SnapToGrid
        # AfterValidator (kernel/math.py quantize, 10**-6 grid) applied at
        # Territory construction -- an unrelated determinism property, not
        # something this law is about.
        assert graph.nodes[TERRITORY_ID]["wealth"] == pytest.approx(wealth, abs=1e-5)


class TestIntensityBoundsAndMonotonicityLaw:
    """L4: stored dispossession_intensity in [0, 1]; monotone non-decreasing
    in foreclosure_rate holding other inputs fixed.

    Grounding: intensity.py:48 ``return min(max(intensity, 0.0), 1.0)``
    clamps to [0, 1]; each per-type weight (weight_foreclosure et al. in
    config/defines/economy_labor.py) is declared ``ge=0.0`` so the
    pre-clamp weighted sum is non-decreasing in every rate, and clamping a
    non-decreasing function to a fixed interval preserves monotonicity.
    """

    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        foreclosure_rate=_UNIT_FLOAT,
        eviction_rate=_UNIT_FLOAT,
        displacement_rate=_UNIT_FLOAT,
    )
    def test_intensity_in_unit_interval(
        self, foreclosure_rate: float, eviction_rate: float, displacement_rate: float
    ) -> None:
        # At least one rate must be positive to activate the system (L3).
        if foreclosure_rate <= 0.0 and eviction_rate <= 0.0 and displacement_rate <= 0.0:
            foreclosure_rate = 0.5

        graph, _disp_events, _transfer_events = _run(
            {
                "foreclosure_rate": foreclosure_rate,
                "eviction_rate": eviction_rate,
                "displacement_rate": displacement_rate,
                "wealth": 0.0,
            }
        )

        intensity = graph.nodes[TERRITORY_ID]["dispossession_intensity"]
        assert 0.0 <= intensity <= 1.0

    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        low_rate=st.floats(min_value=0.01, max_value=0.49, allow_nan=False, allow_infinity=False),
        delta=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False),
        eviction_rate=_UNIT_FLOAT,
        displacement_rate=_UNIT_FLOAT,
    )
    def test_intensity_monotone_in_foreclosure_rate(
        self,
        low_rate: float,
        delta: float,
        eviction_rate: float,
        displacement_rate: float,
    ) -> None:
        high_rate = low_rate + delta

        graph_low, _, _ = _run(
            {
                "foreclosure_rate": low_rate,
                "eviction_rate": eviction_rate,
                "displacement_rate": displacement_rate,
                "wealth": 0.0,
            }
        )
        graph_high, _, _ = _run(
            {
                "foreclosure_rate": high_rate,
                "eviction_rate": eviction_rate,
                "displacement_rate": displacement_rate,
                "wealth": 0.0,
            }
        )

        intensity_low = graph_low.nodes[TERRITORY_ID]["dispossession_intensity"]
        intensity_high = graph_high.nodes[TERRITORY_ID]["dispossession_intensity"]
        assert intensity_high >= intensity_low - 1e-9
