"""Event system for decoupled communication in the simulation.

This module provides a publish/subscribe event bus that enables loose coupling
between simulation components. Events are immutable data objects that carry
information about state changes.

Sprint 3: Central Committee (Dependency Injection)
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    """Immutable event representing a simulation occurrence.

    Events are frozen dataclasses to ensure they cannot be modified
    after creation, maintaining integrity of the event history.

    Attributes:
        type: Event type identifier (e.g., "tick", "rupture", "synthesis")
        tick: Simulation tick when the event occurred
        payload: Event-specific data dictionary
        timestamp: Wall-clock time when event was created
    """

    type: str
    tick: int
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """Publish/subscribe event bus for simulation components.

    The EventBus enables decoupled communication between systems.
    Components can subscribe to specific event types and will be
    notified when events of that type are published.

    All published events are stored in history for replay/debugging.

    Example:
        >>> bus = EventBus()
        >>> def on_tick(event: Event) -> None:
        ...     print(f"Tick {event.tick}: {event.payload}")
        >>> bus.subscribe("tick", on_tick)
        >>> bus.publish(Event(type="tick", tick=1, payload={"value": 42}))
        Tick 1: {'value': 42}
    """

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to receive events of a specific type.

        Args:
            event_type: The type of events to subscribe to
            handler: Callable that receives Event objects
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribed handlers.

        The event is stored in history regardless of whether
        there are any subscribers.

        Args:
            event: The event to publish
        """
        self._history.append(event)

        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            handler(event)

    def get_history(self) -> list[Event]:
        """Get a copy of all published events.

        Returns:
            List of events in chronological order (oldest first)
        """
        return list(self._history)

    def clear_history(self) -> None:
        """Remove all events from history."""
        self._history.clear()
