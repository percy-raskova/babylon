"""Event system for decoupled communication in the simulation.

This module provides a publish/subscribe event bus that enables loose coupling
between simulation components. Events are immutable data objects that carry
information about state changes.

Sprint 3: Central Committee (Dependency Injection)
Epoch 1→2 Bridge: Added EventInterceptor pattern for adversarial mechanics.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.engine.interceptor import (
        BlockedEvent,
        EventInterceptor,
        WorldContext,
    )

logger = logging.getLogger(__name__)


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

    Epoch 1→2 Bridge: Supports optional interceptor chain for adversarial
    mechanics. If no interceptors are registered, events flow through with
    zero overhead (backwards compatible).

    The interceptor chain processes events before emission:
    - Interceptors are sorted by priority (higher runs first)
    - Each interceptor can ALLOW, BLOCK, or MODIFY the event
    - If blocked, the event is logged and not emitted
    - If modified, the modified event continues through the chain

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
        self._interceptors: list[EventInterceptor] = []
        self._blocked_events: list[BlockedEvent] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to receive events of a specific type.

        Args:
            event_type: The type of events to subscribe to
            handler: Callable that receives Event objects
        """
        self._subscribers[event_type].append(handler)

    def register_interceptor(self, interceptor: EventInterceptor) -> None:
        """Register an interceptor to process events before emission.

        Interceptors are sorted by priority (higher first) each time
        an event is published. Multiple interceptors with the same
        priority execute in registration order.

        Args:
            interceptor: The interceptor to register.

        Example:
            >>> from babylon.engine.interceptor import EventInterceptor
            >>> bus = EventBus()
            >>> bus.register_interceptor(my_security_interceptor)
        """
        self._interceptors.append(interceptor)

    def unregister_interceptor(self, interceptor: EventInterceptor) -> None:
        """Remove an interceptor from the chain.

        Args:
            interceptor: The interceptor to remove.

        Raises:
            ValueError: If the interceptor is not registered.
        """
        self._interceptors.remove(interceptor)

    def publish(self, event: Event, context: WorldContext | None = None) -> None:
        """Publish an event to all subscribed handlers.

        If interceptors are registered, the event passes through the
        interceptor chain first. If any interceptor blocks the event,
        it is logged to the blocked events audit channel and not emitted.

        The event is stored in history only if it passes all interceptors.

        Args:
            event: The event to publish.
            context: Optional world context for interceptors.
                    Required for Epoch 2 adversarial mechanics.
        """
        # Fast path: no interceptors = zero overhead for Epoch 1
        if not self._interceptors:
            self._history.append(event)
            self._emit_to_handlers(event)
            return

        # Slow path: run through interceptor chain
        processed_event = self._process_interceptors(event, context)

        if processed_event is not None:
            # Event passed all interceptors - emit to subscribers
            self._history.append(processed_event)
            self._emit_to_handlers(processed_event)

    def _process_interceptors(self, event: Event, context: WorldContext | None) -> Event | None:
        """Process event through the interceptor chain.

        Args:
            event: The event to process.
            context: Optional world context for interceptors.

        Returns:
            The (possibly modified) event if allowed, None if blocked.
        """
        # Import here to avoid circular import at module level
        from babylon.engine.interceptor import BlockedEvent

        current_event: Event = event

        # Sort by priority (higher first), stable sort preserves registration order
        sorted_interceptors = sorted(
            self._interceptors,
            key=lambda i: i.priority,
            reverse=True,
        )

        for interceptor in sorted_interceptors:
            result = interceptor.intercept(current_event, context)

            if result.is_blocked:
                # BLOCKED - log to audit channel and stop
                blocked_record = BlockedEvent(
                    event=event,  # Log original event for auditability
                    interceptor_name=interceptor.name,
                    reason=result.reason,
                )
                self._blocked_events.append(blocked_record)

                logger.warning(
                    "Event %s BLOCKED by %s: %s",
                    event.type,
                    interceptor.name,
                    result.reason,
                )
                return None

            if result.is_modified:
                # MODIFIED - log and continue with new event
                logger.info(
                    "Event %s MODIFIED by %s: %s",
                    current_event.type,
                    interceptor.name,
                    result.reason,
                )

            # Continue with (possibly modified) event
            # result.event is guaranteed non-None here since not blocked
            assert result.event is not None
            current_event = result.event

        return current_event

    def _emit_to_handlers(self, event: Event) -> None:
        """Emit event to all subscribed handlers.

        Args:
            event: The event to emit.
        """
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            handler(event)

    def get_history(self) -> list[Event]:
        """Get a copy of all published events.

        Returns:
            List of events in chronological order (oldest first).
        """
        return list(self._history)

    def get_blocked_events(self) -> list[BlockedEvent]:
        """Get a copy of all blocked events.

        The blocked events audit channel records every event that was
        stopped by an interceptor, including the blocking reason.

        Returns:
            List of BlockedEvent records in chronological order.
        """
        # Import here to satisfy type checker when called
        from babylon.engine.interceptor import BlockedEvent  # noqa: F401

        return list(self._blocked_events)

    def clear_history(self) -> None:
        """Remove all events from history."""
        self._history.clear()

    def clear_blocked_events(self) -> None:
        """Remove all blocked event records."""
        self._blocked_events.clear()

    @property
    def interceptor_count(self) -> int:
        """Number of registered interceptors."""
        return len(self._interceptors)
