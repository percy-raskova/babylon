"""ObserverCallback type alias for GUI Protocol Extension.

This file defines the callback type used by GUI observers.

NOTE: The ObserverAdapterProtocol defined here is an OPTIONAL extension point.
For MVP implementation, the Simulation class directly manages callbacks via
_gui_callbacks list. A separate adapter class can be added later if needed
for advanced use cases (Qt signal bridging, mock testing, etc.).

Feature: 006-gui-protocol-extension
Date: 2026-01-31
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.protocols import SimulationState

# Type alias for GUI observer callbacks
ObserverCallback = Callable[[int, "SimulationState"], None]


@runtime_checkable
class ObserverAdapterProtocol(Protocol):
    """Protocol for thread-safe observer adapters.

    Implementations bridge the simulation engine's observer notifications
    to GUI callbacks, ensuring thread-safe delivery of immutable snapshots.

    Example:
        >>> adapter = ProtocolObserverAdapter(simulation)
        >>> adapter.register(my_gui_callback)
        >>> # ... simulation runs in another thread ...
        >>> adapter.notify(tick=5)  # Called by engine after step()
    """

    def register(self, callback: ObserverCallback) -> None:
        """Register a GUI callback for tick notifications.

        Thread-safe: may be called from any thread.

        Args:
            callback: Function to call with (tick, state) after each step.
        """
        ...

    def unregister(self, callback: ObserverCallback) -> None:
        """Remove a previously registered callback.

        Thread-safe: may be called from any thread.
        No-op if callback was not registered.

        Args:
            callback: The callback function to remove.
        """
        ...

    def notify(self, tick: int) -> None:
        """Notify all registered callbacks with current state.

        Thread-safe: creates snapshot before iteration.
        Exceptions in callbacks are logged but do not propagate.

        Args:
            tick: Current simulation tick number.
        """
        ...
