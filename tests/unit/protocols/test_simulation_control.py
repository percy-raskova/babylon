"""Unit tests for SimulationControl protocol (T040).

This test validates that:
- SimulationControl is a runtime_checkable Protocol
- Simulation class is an instance of SimulationControl
- Protocol methods are callable via protocol type

See Also:
    - spec.md#SC-004: Protocol methods callable
    - spec.md#SC-005: mypy type-check protocols
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.snapshots import HexState, TerritoryState
from babylon.protocols import SimulationControl


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


class TestSimulationControlProtocol:
    """Test SimulationControl protocol compliance."""

    def test_simulation_is_instance_of_simulation_control(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify Simulation is instance of SimulationControl (T040 core test)."""
        sim = simulation_with_territory
        assert isinstance(sim, SimulationControl)

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify SimulationControl protocol is runtime_checkable."""
        state = WorldState()
        config = SimulationConfig()
        sim = Simulation(state, config)

        # This would fail if @runtime_checkable wasn't applied
        result = isinstance(sim, SimulationControl)
        assert result is True

    def test_non_simulation_is_not_instance(self) -> None:
        """Verify non-Simulation objects are not instances of SimulationControl."""

        class NotASimulation:
            pass

        obj = NotASimulation()
        assert not isinstance(obj, SimulationControl)


class TestSimulationControlMethodsCallable:
    """Test that SimulationControl methods are callable via protocol type (SC-004)."""

    def test_step_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify step() callable via SimulationControl type."""

        def advance_simulation(sim: SimulationControl, n: int = 1) -> None:
            sim.step(n)

        # Should not raise
        advance_simulation(simulation_with_territory)
        assert simulation_with_territory.get_current_tick() == 1

        advance_simulation(simulation_with_territory, 5)
        assert simulation_with_territory.get_current_tick() == 6

    def test_reset_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify reset() callable via SimulationControl type."""

        def reset_simulation(sim: SimulationControl) -> None:
            sim.reset()

        # Advance, then reset
        simulation_with_territory.step(10)
        assert simulation_with_territory.get_current_tick() == 10

        reset_simulation(simulation_with_territory)
        assert simulation_with_territory.get_current_tick() == 0


class TestSimulationControlInterfaceStability:
    """Test that GUI code can depend on SimulationControl interface."""

    def test_gui_control_function_accepts_simulation_control(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify GUI-style control function works with SimulationControl parameter."""

        def on_step_button_click(sim: SimulationControl) -> None:
            """Example GUI handler that depends only on protocol."""
            sim.step()

        def on_fast_forward_click(sim: SimulationControl, ticks: int) -> None:
            """Example GUI handler for fast-forward."""
            sim.step(ticks)

        def on_reset_click(sim: SimulationControl) -> None:
            """Example GUI handler for reset."""
            sim.reset()

        # These should work because Simulation implements SimulationControl
        on_step_button_click(simulation_with_territory)
        assert simulation_with_territory.get_current_tick() == 1

        on_fast_forward_click(simulation_with_territory, 10)
        assert simulation_with_territory.get_current_tick() == 11

        on_reset_click(simulation_with_territory)
        assert simulation_with_territory.get_current_tick() == 0

    def test_mock_simulation_control_can_be_created(self) -> None:
        """Verify a mock SimulationControl can be used for testing."""

        class MockSimulationControl:
            """Mock implementation for GUI testing."""

            def __init__(self) -> None:
                self._tick = 0
                self.step_calls: list[int] = []
                self.reset_calls = 0

            def step(self, n: int = 1) -> None:
                self._tick += n
                self.step_calls.append(n)

            def reset(self) -> None:
                self._tick = 0
                self.reset_calls += 1

        mock = MockSimulationControl()

        # Mock should be instance of SimulationControl protocol
        assert isinstance(mock, SimulationControl)

        # GUI code should work with mock
        def gui_step_handler(sim: SimulationControl) -> None:
            sim.step()

        gui_step_handler(mock)
        assert mock.step_calls == [1]

    def test_combined_protocol_usage(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify Simulation can be used as both SimulationState and SimulationControl."""
        from babylon.protocols import SimulationState

        # Simulation implements both protocols
        assert isinstance(simulation_with_territory, SimulationState)
        assert isinstance(simulation_with_territory, SimulationControl)

        def run_and_display(
            state: SimulationState,
            control: SimulationControl,
            ticks: int,
        ) -> str:
            """Example function using both protocol interfaces."""
            control.step(ticks)
            current_tick = state.get_current_tick()
            return f"Completed tick {current_tick}"

        # Same object can be passed for both parameters
        result = run_and_display(
            simulation_with_territory,
            simulation_with_territory,
            5,
        )
        assert result == "Completed tick 5"
