"""Unit tests for SimulationState protocol (T039).

This test validates that:
- SimulationState is a runtime_checkable Protocol
- Simulation class is an instance of SimulationState
- Protocol methods are callable via protocol type

See Also:
    - spec.md#SC-004: Protocol methods callable
    - spec.md#SC-005: mypy type-check protocols
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.snapshots import HexState, SimulationSnapshot, TerritoryState
from babylon.protocols import SimulationState


@pytest.fixture
def simulation_with_territory() -> Simulation:
    """Create a simulation with MVP territory state."""
    state = WorldState()
    config = SimulationConfig()
    sim = Simulation(state, config)

    territory = TerritoryState(
        territory_id="26163",
        controlling_polity="26163",
        hex_claims=frozenset(["8528a9c9bffffff"]),
        tick=0,
        profit_rate=0.15,
        equilibrium_r=0.15,
    )
    hexes = {"8528a9c9bffffff": HexState(h3_index="8528a9c9bffffff")}
    sim._initialize_mvp_territories(territories={"26163": territory}, hexes=hexes)

    return sim


class TestSimulationStateProtocol:
    """Test SimulationState protocol compliance."""

    def test_simulation_is_instance_of_simulation_state(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify Simulation is instance of SimulationState (T039 core test)."""
        sim = simulation_with_territory
        assert isinstance(sim, SimulationState)

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify SimulationState protocol is runtime_checkable."""
        # This test verifies the @runtime_checkable decorator is present
        # by successfully using isinstance()
        state = WorldState()
        config = SimulationConfig()
        sim = Simulation(state, config)

        # This would fail if @runtime_checkable wasn't applied
        result = isinstance(sim, SimulationState)
        assert result is True

    def test_non_simulation_is_not_instance(self) -> None:
        """Verify non-Simulation objects are not instances of SimulationState."""

        class NotASimulation:
            pass

        obj = NotASimulation()
        assert not isinstance(obj, SimulationState)


class TestSimulationStateMethodsCallable:
    """Test that SimulationState methods are callable via protocol type (SC-004)."""

    def test_get_current_tick_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_current_tick() callable via SimulationState type."""

        def query_tick(sim: SimulationState) -> int:
            return sim.get_current_tick()

        result = query_tick(simulation_with_territory)
        assert result == 0

    def test_get_snapshot_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_snapshot() callable via SimulationState type."""

        def query_snapshot(sim: SimulationState) -> SimulationSnapshot:
            return sim.get_snapshot()

        result = query_snapshot(simulation_with_territory)
        assert isinstance(result, SimulationSnapshot)
        assert "26163" in result.territories

    def test_get_territory_state_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_territory_state() callable via SimulationState type."""

        def query_territory(sim: SimulationState, tid: str) -> TerritoryState | None:
            return sim.get_territory_state(tid)

        result = query_territory(simulation_with_territory, "26163")
        assert result is not None
        assert result.territory_id == "26163"

    def test_get_hexes_for_territory_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_hexes_for_territory() callable via SimulationState type."""

        def query_hexes(sim: SimulationState, tid: str) -> set[str]:
            return sim.get_hexes_for_territory(tid)

        result = query_hexes(simulation_with_territory, "26163")
        assert "8528a9c9bffffff" in result


class TestSimulationStateInterfaceStability:
    """Test that GUI code can depend on SimulationState interface."""

    def test_gui_render_function_accepts_simulation_state(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify GUI-style function works with SimulationState parameter."""

        def render_map(sim: SimulationState) -> list[str]:
            """Example GUI render function that depends only on protocol."""
            snapshot = sim.get_snapshot()
            rendered = []
            for tid, territory in snapshot.territories.items():
                rendered.append(f"{tid}: rate={territory.profit_rate:.2f}")
            return rendered

        # This should work because Simulation implements SimulationState
        result = render_map(simulation_with_territory)
        assert len(result) == 1
        assert "26163" in result[0]

    def test_mock_simulation_state_can_be_created(self) -> None:
        """Verify a mock SimulationState can be used for testing."""

        class MockSimulationState:
            """Mock implementation for GUI testing."""

            def get_current_tick(self) -> int:
                return 42

            def get_snapshot(self) -> SimulationSnapshot:
                return SimulationSnapshot(tick=42, territories={}, hexes={}, edges=[])

            def get_territory_state(self, territory_id: str) -> TerritoryState | None:
                return None

            def get_hexes_for_territory(self, territory_id: str) -> set[str]:
                return set()

        mock = MockSimulationState()

        # Mock should be instance of SimulationState protocol
        assert isinstance(mock, SimulationState)

        # GUI code should work with mock
        def gui_display_tick(sim: SimulationState) -> str:
            return f"Tick: {sim.get_current_tick()}"

        assert gui_display_tick(mock) == "Tick: 42"
