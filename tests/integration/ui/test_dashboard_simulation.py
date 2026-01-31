"""Integration tests for dashboard-simulation end-to-end updates.

Tests the complete flow from simulation tick to UI update,
verifying that MapViewport and InspectorPanel receive updates.

Feature: 007-god-mode-dashboard

TDD Status: RED Phase - These tests are written BEFORE implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

# Import modules that WILL exist - tests will fail initially
try:
    from babylon.ui.dashboard.main_window import DashboardWindow
    from babylon.ui.dashboard.observer import DashboardObserver

    MODULES_EXIST = True
except ImportError:
    MODULES_EXIST = False
    DashboardWindow = None  # type: ignore[misc, assignment]
    DashboardObserver = None  # type: ignore[misc, assignment]

try:
    from babylon.ui.dashboard.testing import MockSimulation

    MOCK_EXISTS = True
except ImportError:
    MOCK_EXISTS = False
    MockSimulation = None  # type: ignore[misc, assignment]


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not MODULES_EXIST, reason="Dashboard modules not yet implemented"),
]


class TestEndToEndTickUpdates:
    """T035: Integration tests for end-to-end tick updates."""

    @pytest.fixture
    def simulation_with_observer(
        self,
        qtbot: QtBot,
    ):
        """Create simulation and dashboard with observer registered."""
        simulation = MockSimulation.with_detroit_territories()
        window = DashboardWindow(simulation=simulation)
        qtbot.addWidget(window)

        return simulation, window

    def test_simulation_step_updates_map_colors(
        self,
        qtbot: QtBot,
        simulation_with_observer,
    ) -> None:
        """Simulation step should trigger map color update."""
        simulation, window = simulation_with_observer

        # Track map updates
        update_calls = []
        original_update = window.map_viewport.update_colors
        window.map_viewport.update_colors = lambda snap: (
            update_calls.append(snap),
            original_update(snap),
        )[1]

        # Step simulation
        simulation.step()

        # Wait for observer throttle + signal propagation
        qtbot.wait(100)

        # Map should have been updated
        assert len(update_calls) >= 1

    def test_simulation_step_updates_inspector_if_selected(
        self,
        qtbot: QtBot,
        simulation_with_observer,
    ) -> None:
        """Simulation step should update inspector if territory is selected."""
        simulation, window = simulation_with_observer

        # Select a territory first (set both signal AND internal state)
        wayne_id = "26163"
        wayne_territory = simulation.get_territory(wayne_id)
        window.hex_bridge._selected_territory_id = wayne_id  # Set internal state
        window.hex_bridge.territory_selected.emit(wayne_territory)

        # Track inspector updates
        update_calls = []
        original_display = window.inspector_panel.display_territory
        window.inspector_panel.display_territory = lambda t: (
            update_calls.append(t),
            original_display(t),
        )[1]

        # Step simulation
        simulation.step()

        # Wait for updates
        qtbot.wait(100)

        # Inspector should have been updated with new territory state
        assert len(update_calls) >= 1

    def test_rapid_steps_coalesce_updates(
        self,
        qtbot: QtBot,
        simulation_with_observer,
    ) -> None:
        """Rapid simulation steps should coalesce to avoid UI flooding."""
        simulation, window = simulation_with_observer

        # Track map updates
        update_calls = []
        original_update = window.map_viewport.update_colors
        window.map_viewport.update_colors = lambda snap: (
            update_calls.append(snap),
            original_update(snap) if original_update else None,
        )[1]

        # Rapid steps (faster than 30 FPS)
        for _ in range(10):
            simulation.step()
            qtbot.wait(5)  # 5ms between steps = 200 FPS

        # Wait for throttle to complete
        qtbot.wait(100)

        # Should have significantly fewer updates than steps
        # (first immediate + coalesced)
        assert len(update_calls) <= 5  # Much less than 10

    def test_status_bar_shows_current_tick(
        self,
        qtbot: QtBot,
        simulation_with_observer,
    ) -> None:
        """Status bar should show current tick after step."""
        simulation, window = simulation_with_observer

        # Step simulation
        simulation.step()
        simulation.step()

        # Wait for updates
        qtbot.wait(100)

        # Status bar should show tick
        status_text = window.statusBar().currentMessage()
        assert "Tick" in status_text
        # Tick should be > 0 after steps
        assert "2" in status_text or "1" in status_text

    def test_window_close_unregisters_observer(
        self,
        qtbot: QtBot,
        simulation_with_observer,
    ) -> None:
        """Closing window should unregister observer from simulation."""
        simulation, window = simulation_with_observer

        # Count initial observers
        initial_count = len(simulation._observers)

        # Close window
        window.close()

        # Wait for cleanup
        qtbot.wait(50)

        # Observer should be unregistered
        assert len(simulation._observers) < initial_count


class TestDashboardObserverIntegration:
    """Tests for DashboardObserver integration with simulation."""

    def test_observer_receives_tick_notifications(
        self,
        qtbot: QtBot,
    ) -> None:
        """Observer should receive on_tick calls from simulation."""
        simulation = MockSimulation.with_detroit_territories()
        observer = DashboardObserver(simulation=simulation)
        # Note: DashboardObserver is QObject not QWidget, don't use addWidget

        # Register observer
        simulation.register_observer(observer)

        # Track tick signals
        ticks_received = []
        observer.tick_processed.connect(lambda tick, _snap: ticks_received.append(tick))

        # Step simulation
        simulation.step()

        # Wait for throttle
        qtbot.wait(100)

        # Should have received tick notification
        assert len(ticks_received) >= 1
        assert ticks_received[0] == 1  # First step goes to tick 1

    def test_multiple_observers_all_notified(
        self,
        qtbot: QtBot,
    ) -> None:
        """Multiple observers should all receive notifications."""
        simulation = MockSimulation.with_detroit_territories()

        observer1 = DashboardObserver(simulation=simulation)
        observer2 = DashboardObserver(simulation=simulation)
        # Note: DashboardObserver is QObject not QWidget, don't use addWidget

        simulation.register_observer(observer1)
        simulation.register_observer(observer2)

        # Track ticks for each observer
        ticks1 = []
        ticks2 = []
        observer1.tick_processed.connect(lambda tick, _snap: ticks1.append(tick))
        observer2.tick_processed.connect(lambda tick, _snap: ticks2.append(tick))

        # Step simulation
        simulation.step()

        # Wait for throttle
        qtbot.wait(100)

        # Both should have received notification
        assert len(ticks1) >= 1
        assert len(ticks2) >= 1


class TestDashboardObserverErrorHandling:
    """Tests for observer error handling (ADR003: AI failures don't break game)."""

    def test_observer_error_does_not_stop_simulation(
        self,
        qtbot: QtBot,
    ) -> None:
        """Observer errors should be logged but not stop simulation."""
        simulation = MockSimulation.with_detroit_territories()

        # Create observer that will error
        observer = DashboardObserver(simulation=simulation)
        # Note: DashboardObserver is QObject not QWidget, don't use addWidget

        simulation.register_observer(observer)

        # Track that the signal was emitted
        error_handler_called = []

        def error_handler(t, s):
            error_handler_called.append(t)
            raise ValueError("Test error")

        observer.tick_processed.connect(error_handler)

        # Step should not raise (errors in signal handlers are caught by Qt)
        # Use capture_exceptions to prevent pytest-qt from failing the test
        with qtbot.capture_exceptions() as exceptions:
            simulation.step()
            qtbot.wait(50)

        # Simulation should continue
        assert simulation.get_current_tick() == 1
        # Error handler was called
        assert len(error_handler_called) >= 1
        # Exception was raised (caught by Qt, captured by qtbot)
        assert len(exceptions) >= 1

    def test_observer_cleanup_on_unregister(
        self,
        qtbot: QtBot,
    ) -> None:
        """Unregistering observer should clean up resources."""
        simulation = MockSimulation.with_detroit_territories()
        observer = DashboardObserver(simulation=simulation)
        # Note: DashboardObserver is QObject not QWidget, don't use addWidget

        simulation.register_observer(observer)
        initial_count = len(simulation._observers)

        simulation.unregister_observer(observer)

        assert len(simulation._observers) == initial_count - 1


__all__ = []
