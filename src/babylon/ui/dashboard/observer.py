"""DashboardObserver for throttled simulation updates.

This module provides the DashboardObserver that bridges simulation ticks
to UI updates with 30 FPS throttling and state coalescing.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QObject, QTimer, pyqtSignal  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.snapshots import SimulationSnapshot
    from babylon.models.world_state import WorldState
    from babylon.protocols import SimulationState

logger = logging.getLogger(__name__)

# 30 FPS = 33.33ms per frame, rounded to 33ms
THROTTLE_INTERVAL_MS = 33


class DashboardObserver(QObject):  # type: ignore[misc]
    """Observer that bridges simulation ticks to UI with throttling.

    This observer implements the SimulationObserver protocol and throttles
    updates to 30 FPS (33ms minimum interval) to prevent UI flooding during
    rapid simulation steps.

    Signals:
        tick_processed: Emitted when a tick should update UI (int tick, SimulationSnapshot).
        simulation_started: Emitted when simulation starts.
        simulation_ended: Emitted when simulation ends.

    Example:
        >>> observer = DashboardObserver(simulation=sim)
        >>> observer.tick_processed.connect(window.update_from_snapshot)
        >>> simulation.register_observer(observer)
    """

    # Signals
    tick_processed = pyqtSignal(int, object)  # (tick, SimulationSnapshot)
    simulation_started = pyqtSignal()
    simulation_ended = pyqtSignal()

    def __init__(
        self,
        simulation: SimulationState,
        parent: QObject | None = None,
    ) -> None:
        """Initialize DashboardObserver.

        Args:
            simulation: Simulation state for snapshot creation.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._simulation = simulation
        self._throttle_interval_ms = THROTTLE_INTERVAL_MS

        # Throttle state
        self._pending_snapshot: SimulationSnapshot | None = None
        self._pending_tick: int = 0
        self._is_throttling = False

        # Create throttle timer
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._emit_pending)

        logger.debug("DashboardObserver initialized with %dms throttle", THROTTLE_INTERVAL_MS)

    @property
    def name(self) -> str:
        """Observer identifier for logging.

        Returns:
            Observer name string.
        """
        return "DashboardObserver"

    @property
    def throttle_interval_ms(self) -> int:
        """Get the throttle interval in milliseconds.

        Returns:
            Throttle interval (33ms for 30 FPS).
        """
        return self._throttle_interval_ms

    def on_simulation_start(
        self,
        initial_state: WorldState | None,  # noqa: ARG002 - Protocol requires this arg
        config: SimulationConfig | None,  # noqa: ARG002 - Protocol requires this arg
    ) -> None:
        """Handle simulation start.

        Resets internal state and emits simulation_started signal.

        Args:
            initial_state: Initial world state (may be None from tests).
            config: Simulation configuration (may be None from tests).
        """
        logger.debug("Simulation started")

        # Reset throttle state
        self._pending_snapshot = None
        self._pending_tick = 0
        self._is_throttling = False
        self._throttle_timer.stop()

        self.simulation_started.emit()

    def on_tick(
        self,
        previous_state: WorldState | None,  # noqa: ARG002 - Protocol requires this arg
        new_state: WorldState | SimulationSnapshot | None,
    ) -> None:
        """Handle simulation tick with throttling.

        First tick emits immediately, subsequent ticks within the throttle
        window are coalesced and the latest state is emitted when the
        throttle timer fires.

        Args:
            previous_state: Previous world state (may be None).
            new_state: New state (WorldState or SimulationSnapshot).
        """
        # Handle both WorldState and SimulationSnapshot
        if new_state is None:
            return

        # Get tick and snapshot from new_state
        tick = new_state.tick if hasattr(new_state, "tick") else 0

        # Convert WorldState to SimulationSnapshot if needed
        raw_snapshot = new_state.to_snapshot() if hasattr(new_state, "to_snapshot") else new_state
        snapshot = cast("SimulationSnapshot", raw_snapshot)

        logger.debug("Tick %d received, throttling=%s", tick, self._is_throttling)

        if not self._is_throttling:
            # First tick in window - emit immediately
            self._emit_tick(tick, snapshot)

            # Start throttle window
            self._is_throttling = True
            self._throttle_timer.start(self._throttle_interval_ms)
        else:
            # Subsequent tick - coalesce (store latest)
            self._pending_snapshot = snapshot
            self._pending_tick = tick
            logger.debug("Coalescing tick %d", tick)

    def on_simulation_end(
        self,
        final_state: WorldState | None,  # noqa: ARG002 - Protocol requires this arg
    ) -> None:
        """Handle simulation end.

        Flushes any pending coalesced state and emits simulation_ended signal.

        Args:
            final_state: Final world state (may be None from tests).
        """
        logger.debug("Simulation ended")

        # Flush any pending coalesced state
        if self._pending_snapshot is not None:
            self._emit_tick(self._pending_tick, self._pending_snapshot)
            self._pending_snapshot = None
            self._pending_tick = 0

        # Stop throttle timer
        self._throttle_timer.stop()
        self._is_throttling = False

        self.simulation_ended.emit()

    def _emit_pending(self) -> None:
        """Emit pending coalesced state when throttle timer fires."""
        self._is_throttling = False

        if self._pending_snapshot is not None:
            self._emit_tick(self._pending_tick, self._pending_snapshot)
            self._pending_snapshot = None
            self._pending_tick = 0

    def _emit_tick(self, tick: int, snapshot: SimulationSnapshot) -> None:
        """Emit tick_processed signal.

        Args:
            tick: Current tick number.
            snapshot: Simulation snapshot.
        """
        logger.debug("Emitting tick_processed for tick %d", tick)
        self.tick_processed.emit(tick, snapshot)


__all__ = [
    "DashboardObserver",
    "THROTTLE_INTERVAL_MS",
]
