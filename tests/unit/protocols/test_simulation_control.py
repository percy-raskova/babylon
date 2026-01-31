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
        from babylon.protocols import ObserverCallback

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

            def register_observer(self, callback: ObserverCallback) -> None:
                pass

            def unregister_observer(self, callback: ObserverCallback) -> None:
                pass

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


# =============================================================================
# Feature 006-gui-protocol-extension: Observer Registration Tests (T006-T010)
# =============================================================================


class TestCallbackReceivesTick:
    """T006: callback receives tick and state after step()."""

    def test_callback_invoked_on_step(self, simulation_with_territory: Simulation) -> None:
        """Callback is invoked when step() is called."""
        from babylon.models.snapshots import SimulationSnapshot

        received_calls: list[tuple[int, SimulationSnapshot]] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            received_calls.append((tick, snapshot))

        simulation_with_territory.register_observer(callback)
        simulation_with_territory.step()

        assert len(received_calls) == 1

    def test_callback_receives_tick_number(self, simulation_with_territory: Simulation) -> None:
        """Callback receives correct tick number."""
        from babylon.models.snapshots import SimulationSnapshot

        received_ticks: list[int] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            received_ticks.append(tick)

        simulation_with_territory.register_observer(callback)
        simulation_with_territory.step(3)

        # After step(3), callbacks invoked at ticks 1, 2, 3
        assert received_ticks == [1, 2, 3]

    def test_callback_receives_snapshot(self, simulation_with_territory: Simulation) -> None:
        """Callback receives SimulationSnapshot (not live reference)."""
        from babylon.models.snapshots import SimulationSnapshot

        received_snapshots: list[SimulationSnapshot] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            received_snapshots.append(snapshot)

        simulation_with_territory.register_observer(callback)
        simulation_with_territory.step()

        assert len(received_snapshots) == 1
        snapshot = received_snapshots[0]
        # Verify it's a SimulationSnapshot by type check
        assert isinstance(snapshot, SimulationSnapshot)


class TestUnregisteredCallback:
    """T007: unregistered callback not invoked."""

    def test_unregistered_callback_not_invoked(self, simulation_with_territory: Simulation) -> None:
        """Callback is not invoked after unregister."""
        from babylon.models.snapshots import SimulationSnapshot

        call_count = 0

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            nonlocal call_count
            call_count += 1

        simulation_with_territory.register_observer(callback)
        simulation_with_territory.step()
        assert call_count == 1

        simulation_with_territory.unregister_observer(callback)
        simulation_with_territory.step()
        assert call_count == 1  # Not invoked again

    def test_unregister_unknown_callback_noop(self, simulation_with_territory: Simulation) -> None:
        """Unregistering unknown callback is a no-op."""
        from babylon.models.snapshots import SimulationSnapshot

        def unknown_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            pass

        # Should not raise
        simulation_with_territory.unregister_observer(unknown_callback)


class TestMultipleObservers:
    """T008: multiple observers invoked in registration order."""

    def test_multiple_observers_invoked(self, simulation_with_territory: Simulation) -> None:
        """All registered observers are invoked."""
        from babylon.models.snapshots import SimulationSnapshot

        invoked: list[str] = []

        def callback_a(tick: int, snapshot: SimulationSnapshot) -> None:
            invoked.append("A")

        def callback_b(tick: int, snapshot: SimulationSnapshot) -> None:
            invoked.append("B")

        simulation_with_territory.register_observer(callback_a)
        simulation_with_territory.register_observer(callback_b)
        simulation_with_territory.step()

        assert "A" in invoked
        assert "B" in invoked

    def test_observers_invoked_in_registration_order(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Observers are invoked in the order they were registered."""
        from babylon.models.snapshots import SimulationSnapshot

        invoked: list[str] = []

        def callback_a(tick: int, snapshot: SimulationSnapshot) -> None:
            invoked.append("A")

        def callback_b(tick: int, snapshot: SimulationSnapshot) -> None:
            invoked.append("B")

        def callback_c(tick: int, snapshot: SimulationSnapshot) -> None:
            invoked.append("C")

        simulation_with_territory.register_observer(callback_a)
        simulation_with_territory.register_observer(callback_b)
        simulation_with_territory.register_observer(callback_c)
        simulation_with_territory.step()

        assert invoked == ["A", "B", "C"]


class TestDuplicateRegistration:
    """T009: duplicate registration is idempotent (invoked once)."""

    def test_duplicate_registration_invoked_once(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Duplicate registration invokes callback only once per tick."""
        from babylon.models.snapshots import SimulationSnapshot

        call_count = 0

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            nonlocal call_count
            call_count += 1

        simulation_with_territory.register_observer(callback)
        simulation_with_territory.register_observer(callback)  # Duplicate
        simulation_with_territory.register_observer(callback)  # Triple

        simulation_with_territory.step()

        # Should only be invoked once
        assert call_count == 1


class TestCallbackException:
    """T010: callback exception logged but simulation continues."""

    def test_callback_exception_does_not_halt_simulation(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Exception in callback does not prevent simulation from continuing."""
        from babylon.models.snapshots import SimulationSnapshot

        def bad_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            raise RuntimeError("Callback failed!")

        simulation_with_territory.register_observer(bad_callback)

        # Should NOT raise - simulation continues
        simulation_with_territory.step()
        simulation_with_territory.step()

        # Verify simulation advanced
        assert simulation_with_territory.get_current_tick() == 2

    def test_callback_exception_logged(
        self,
        simulation_with_territory: Simulation,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Exception in callback is logged as warning."""
        import logging

        from babylon.models.snapshots import SimulationSnapshot

        def bad_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            raise RuntimeError("Oops!")

        simulation_with_territory.register_observer(bad_callback)

        with caplog.at_level(logging.WARNING):
            simulation_with_territory.step()

        assert "Observer callback failed" in caplog.text

    def test_callback_exception_other_callbacks_still_invoked(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Exception in one callback does not prevent other callbacks."""
        from babylon.models.snapshots import SimulationSnapshot

        results: list[str] = []

        def callback1(tick: int, snapshot: SimulationSnapshot) -> None:
            results.append("callback1")

        def bad_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            raise RuntimeError("Fail!")

        def callback2(tick: int, snapshot: SimulationSnapshot) -> None:
            results.append("callback2")

        simulation_with_territory.register_observer(callback1)
        simulation_with_territory.register_observer(bad_callback)
        simulation_with_territory.register_observer(callback2)

        simulation_with_territory.step()

        # Both good callbacks were invoked
        assert results == ["callback1", "callback2"]


class TestObserverProtocolExtension:
    """T037: Verify protocol implementations with isinstance() check."""

    def test_simulation_control_has_observer_methods(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Verify Simulation has register/unregister observer methods."""
        assert hasattr(simulation_with_territory, "register_observer")
        assert hasattr(simulation_with_territory, "unregister_observer")
        assert callable(simulation_with_territory.register_observer)
        assert callable(simulation_with_territory.unregister_observer)

    def test_mock_simulation_control_with_observers(self) -> None:
        """Verify mock SimulationControl can include observer methods."""

        from babylon.protocols import ObserverCallback

        class MockSimulationControlWithObservers:
            """Mock with observer support for GUI testing."""

            def __init__(self) -> None:
                self._tick = 0
                self._callbacks: list[ObserverCallback] = []

            def step(self, n: int = 1) -> None:
                self._tick += n

            def reset(self) -> None:
                self._tick = 0

            def register_observer(self, callback: ObserverCallback) -> None:
                self._callbacks.append(callback)

            def unregister_observer(self, callback: ObserverCallback) -> None:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)

        mock = MockSimulationControlWithObservers()
        assert isinstance(mock, SimulationControl)
