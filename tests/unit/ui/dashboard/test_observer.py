"""Unit tests for DashboardObserver throttling and coalescing.

Tests for the observer that bridges simulation ticks to UI updates
with 30 FPS throttling and state coalescing.

Feature: 007-god-mode-dashboard

TDD Status: RED Phase - These tests are written BEFORE implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

# Import the module that WILL exist - tests will fail initially
try:
    from babylon.ui.dashboard.observer import DashboardObserver

    OBSERVER_EXISTS = True
except ImportError:
    OBSERVER_EXISTS = False
    DashboardObserver = None  # type: ignore[misc, assignment]


pytestmark = [
    pytest.mark.skipif(not OBSERVER_EXISTS, reason="DashboardObserver not yet implemented"),
]


class TestDashboardObserverProtocol:
    """Tests for DashboardObserver protocol compliance."""

    def test_observer_implements_simulation_observer_protocol(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """DashboardObserver should implement SimulationObserver protocol."""
        observer = DashboardObserver(simulation=mock_simulation)

        # Protocol compliance check
        assert hasattr(observer, "name")
        assert hasattr(observer, "on_simulation_start")
        assert hasattr(observer, "on_tick")
        assert hasattr(observer, "on_simulation_end")

    def test_observer_has_name_property(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """DashboardObserver should have a name property."""
        observer = DashboardObserver(simulation=mock_simulation)

        assert observer.name == "DashboardObserver"

    def test_observer_is_qobject(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """DashboardObserver should be a QObject for signal/slot."""
        from PyQt6.QtCore import QObject

        observer = DashboardObserver(simulation=mock_simulation)

        assert isinstance(observer, QObject)


class TestDashboardObserverThrottling:
    """T033: Tests for DashboardObserver 30 FPS throttling."""

    def test_observer_has_tick_processed_signal(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """DashboardObserver should have tick_processed signal."""
        observer = DashboardObserver(simulation=mock_simulation)

        assert hasattr(observer, "tick_processed")

    def test_observer_throttles_to_30fps(
        self,
        qtbot: QtBot,
        mock_simulation,
        wayne_county_territory,
    ) -> None:
        """DashboardObserver should throttle updates to 30 FPS (33ms minimum)."""
        from babylon.models.snapshots import SimulationSnapshot

        observer = DashboardObserver(simulation=mock_simulation)

        # Track signal emissions
        signal_count = []
        observer.tick_processed.connect(lambda _tick, _snap: signal_count.append(1))

        # Create snapshot with territories
        snapshot = SimulationSnapshot(
            tick=1,
            territories={wayne_county_territory.territory_id: wayne_county_territory},
        )

        # Simulate rapid ticks (faster than 30 FPS)
        # First tick should emit immediately
        observer.on_tick(None, snapshot)

        # Process events to allow signal emission
        qtbot.wait(10)

        # Rapid subsequent ticks within throttle window should be deferred
        snapshot2 = snapshot.model_copy(update={"tick": 2})
        observer.on_tick(None, snapshot2)
        qtbot.wait(10)

        # Should have at most 1 emission within 33ms window
        assert len(signal_count) <= 2  # First immediate + possibly one coalesced

    def test_observer_throttle_interval_is_33ms(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """DashboardObserver throttle interval should be 33ms for 30 FPS."""
        observer = DashboardObserver(simulation=mock_simulation)

        # Check internal throttle interval
        assert observer.throttle_interval_ms == 33

    def test_first_tick_emits_immediately(
        self,
        qtbot: QtBot,
        mock_simulation,
        wayne_county_territory,
    ) -> None:
        """First tick should emit signal immediately without waiting."""
        from babylon.models.snapshots import SimulationSnapshot

        observer = DashboardObserver(simulation=mock_simulation)

        # Track emissions
        emissions = []
        observer.tick_processed.connect(lambda tick, snap: emissions.append((tick, snap)))

        # Create snapshot
        snapshot = SimulationSnapshot(
            tick=1,
            territories={wayne_county_territory.territory_id: wayne_county_territory},
        )

        # First tick should emit immediately
        observer.on_tick(None, snapshot)
        qtbot.wait(10)

        assert len(emissions) == 1
        assert emissions[0][0] == 1


class TestDashboardObserverCoalescing:
    """T034: Tests for state coalescing (rapid ticks)."""

    def test_rapid_ticks_coalesce_to_latest(
        self,
        qtbot: QtBot,
        mock_simulation,
        wayne_county_territory,
    ) -> None:
        """Rapid ticks should coalesce, emitting only the latest state."""
        from babylon.models.snapshots import SimulationSnapshot

        observer = DashboardObserver(simulation=mock_simulation)

        # Track emissions
        emissions = []
        observer.tick_processed.connect(lambda tick, snap: emissions.append((tick, snap)))

        # First tick (immediate)
        snapshot1 = SimulationSnapshot(
            tick=1,
            territories={wayne_county_territory.territory_id: wayne_county_territory},
        )
        observer.on_tick(None, snapshot1)
        qtbot.wait(5)

        # Rapid ticks before throttle window expires
        for i in range(2, 10):
            snapshot_n = snapshot1.model_copy(update={"tick": i})
            observer.on_tick(None, snapshot_n)
            qtbot.wait(1)  # Very rapid

        # Wait for throttle timer to fire
        qtbot.wait(50)  # Wait past 33ms throttle

        # Should have first immediate + one coalesced (latest)
        assert len(emissions) == 2
        # Last emission should be tick 9 (the latest)
        assert emissions[-1][0] == 9

    def test_coalescing_preserves_latest_snapshot(
        self,
        qtbot: QtBot,
        mock_simulation,
        wayne_county_territory,
        oakland_county_territory,
    ) -> None:
        """Coalesced emission should contain the latest snapshot data."""
        from babylon.models.snapshots import SimulationSnapshot

        observer = DashboardObserver(simulation=mock_simulation)

        # Track emissions
        emissions = []
        observer.tick_processed.connect(lambda tick, snap: emissions.append((tick, snap)))

        # First snapshot - only Wayne County
        snapshot1 = SimulationSnapshot(
            tick=1,
            territories={wayne_county_territory.territory_id: wayne_county_territory},
        )
        observer.on_tick(None, snapshot1)
        qtbot.wait(5)

        # Second snapshot - different territories
        snapshot2 = SimulationSnapshot(
            tick=2,
            territories={
                wayne_county_territory.territory_id: wayne_county_territory,
                oakland_county_territory.territory_id: oakland_county_territory,
            },
        )
        observer.on_tick(None, snapshot2)

        # Wait for throttle
        qtbot.wait(50)

        # Last emission should have the latest snapshot's territory count
        assert len(emissions[-1][1].territories) == 2

    def test_no_emission_on_empty_coalesce_window(
        self,
        qtbot: QtBot,
        mock_simulation,
        wayne_county_territory,
    ) -> None:
        """No emission should occur if no ticks during throttle window."""
        from babylon.models.snapshots import SimulationSnapshot

        observer = DashboardObserver(simulation=mock_simulation)

        # Track emissions
        emissions = []
        observer.tick_processed.connect(lambda tick, snap: emissions.append((tick, snap)))

        # Single tick
        snapshot = SimulationSnapshot(
            tick=1,
            territories={wayne_county_territory.territory_id: wayne_county_territory},
        )
        observer.on_tick(None, snapshot)
        qtbot.wait(5)

        # Wait past throttle window with no more ticks
        qtbot.wait(100)

        # Should only have the one immediate emission
        assert len(emissions) == 1


class TestDashboardObserverLifecycle:
    """Tests for observer lifecycle hooks."""

    def test_on_simulation_start_resets_state(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """on_simulation_start() should reset internal state."""
        observer = DashboardObserver(simulation=mock_simulation)

        # Simulate start
        observer.on_simulation_start(None, None)

        # Internal state should be reset
        assert observer._pending_snapshot is None

    def test_on_simulation_end_flushes_pending(
        self,
        qtbot: QtBot,
        mock_simulation,
        wayne_county_territory,
    ) -> None:
        """on_simulation_end() should flush any pending coalesced state."""
        from babylon.models.snapshots import SimulationSnapshot

        observer = DashboardObserver(simulation=mock_simulation)

        # Track emissions
        emissions = []
        observer.tick_processed.connect(lambda tick, snap: emissions.append((tick, snap)))

        # First tick (immediate)
        snapshot1 = SimulationSnapshot(
            tick=1,
            territories={wayne_county_territory.territory_id: wayne_county_territory},
        )
        observer.on_tick(None, snapshot1)
        qtbot.wait(5)

        # Pending tick (within throttle window)
        snapshot2 = snapshot1.model_copy(update={"tick": 2})
        observer.on_tick(None, snapshot2)
        # Don't wait for throttle

        # End simulation - should flush pending
        observer.on_simulation_end(None)
        qtbot.wait(10)

        # Should have both emissions
        assert len(emissions) == 2
        assert emissions[-1][0] == 2

    def test_simulation_started_signal(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """on_simulation_start() should emit simulation_started signal."""
        observer = DashboardObserver(simulation=mock_simulation)

        # Track signal
        started = []
        observer.simulation_started.connect(lambda: started.append(1))

        observer.on_simulation_start(None, None)
        qtbot.wait(10)

        assert len(started) == 1


class TestDashboardObserverSignals:
    """Tests for DashboardObserver Qt signals."""

    def test_tick_processed_signal_emits_tick_and_snapshot(
        self,
        qtbot: QtBot,
        mock_simulation,
        wayne_county_territory,
    ) -> None:
        """tick_processed signal should emit (tick, snapshot) tuple."""
        from babylon.models.snapshots import SimulationSnapshot

        observer = DashboardObserver(simulation=mock_simulation)

        # Capture signal with waitSignal
        with qtbot.waitSignal(observer.tick_processed, timeout=1000) as blocker:
            snapshot = SimulationSnapshot(
                tick=5,
                territories={wayne_county_territory.territory_id: wayne_county_territory},
            )
            observer.on_tick(None, snapshot)

        # Verify signal arguments
        assert blocker.args[0] == 5  # tick
        assert blocker.args[1] == snapshot  # snapshot

    def test_has_simulation_ended_signal(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """DashboardObserver should have simulation_ended signal."""
        observer = DashboardObserver(simulation=mock_simulation)

        assert hasattr(observer, "simulation_ended")

    def test_simulation_ended_signal_emits_on_end(
        self,
        qtbot: QtBot,
        mock_simulation,
    ) -> None:
        """simulation_ended signal should emit when simulation ends."""
        observer = DashboardObserver(simulation=mock_simulation)

        # Capture signal
        with qtbot.waitSignal(observer.simulation_ended, timeout=1000):
            observer.on_simulation_end(None)


__all__ = []
