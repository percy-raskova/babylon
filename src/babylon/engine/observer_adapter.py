"""ProtocolObserverAdapter for thread-safe GUI callback delivery.

This module provides a thread-safe bridge between the simulation engine's
observer notifications and GUI callbacks.

Feature: 006-gui-protocol-extension
Date: 2026-01-31

Thread Safety Architecture:
    1. _lock protects _callbacks list during register/unregister
    2. notify() creates snapshot BEFORE iterating callbacks
    3. Callbacks receive SimulationSnapshot (frozen), NOT SimulationState reference
    4. Callback exceptions are caught and logged (per ADR003)

Why This Matters:
    - GUI callbacks NEVER hold a reference to mutable Simulation internals
    - Snapshot is created at a single consistent point in time
    - GUI thread can process the snapshot at leisure without races
    - Complete isolation between engine thread and GUI thread

See Also:
    - data-model.md#ProtocolObserverAdapter: Class specification
    - plan.md#Per-Tick Update Rule: Notification sequence
    - research.md#1: PyQt6 thread communication research
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.models.snapshots import SimulationSnapshot
    from babylon.protocols import ObserverCallback
    from babylon.protocols.simulation_state import SimulationState

logger = logging.getLogger(__name__)


class ProtocolObserverAdapter:
    """Thread-safe bridge between simulation and GUI callbacks.

    This adapter ensures GUI callbacks receive frozen snapshots rather than
    live references to mutable simulation state, providing complete thread
    safety for cross-thread GUI integration.

    Attributes:
        _simulation: Reference to simulation for snapshot creation.
        _callbacks: Registered GUI callbacks.
        _lock: Synchronization for callback list modification.

    Example:
        >>> from babylon.engine.simulation import Simulation
        >>> sim = Simulation.from_sqlite(["26163"])
        >>> adapter = ProtocolObserverAdapter(sim)
        >>>
        >>> def my_callback(tick: int, snapshot: SimulationSnapshot) -> None:
        ...     print(f"Tick {tick}: {len(snapshot.territories)} territories")
        >>>
        >>> adapter.register(my_callback)
        >>> # ... simulation runs in another thread ...
        >>> adapter.notify(tick=5)  # Called by engine after step()
    """

    def __init__(self, simulation: SimulationState) -> None:
        """Initialize adapter with simulation reference.

        Args:
            simulation: Simulation instance implementing SimulationState protocol.
                       Used to create snapshots via get_snapshot().
        """
        self._simulation = simulation
        self._callbacks: list[ObserverCallback] = []
        self._lock = threading.Lock()

    def register(self, callback: ObserverCallback) -> None:
        """Register a GUI callback for tick notifications.

        Thread-safe: may be called from any thread.
        Idempotent: duplicate registration is ignored (callback invoked once per tick).

        Args:
            callback: Function to call with (tick, snapshot) after each step().
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unregister(self, callback: ObserverCallback) -> None:
        """Remove a previously registered callback.

        Thread-safe: may be called from any thread.
        No-op if callback was not registered.

        Args:
            callback: The callback function to remove.
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def notify(self, tick: int) -> None:
        """Notify all registered callbacks with frozen snapshot.

        Thread-safe: creates snapshot before iteration, exceptions logged.
        Callbacks receive immutable snapshot, not live simulation reference.

        Critical: Snapshot is created BEFORE iterating callbacks. This ensures:
        1. All callbacks see the same consistent state
        2. GUI code cannot race with engine mutations
        3. Callback processing time does not affect snapshot consistency

        Args:
            tick: Current simulation tick number.
        """
        # Create snapshot while simulation is in consistent state
        # This MUST happen before copying the callback list
        snapshot: SimulationSnapshot = self._simulation.get_snapshot()

        # Copy callback list under lock to prevent modification during iteration
        with self._lock:
            callbacks = list(self._callbacks)

        # Notify outside lock (callbacks may take time)
        for callback in callbacks:
            try:
                callback(tick, snapshot)  # Frozen snapshot, not self
            except Exception as e:
                logger.warning("Observer callback failed: %s", e)
