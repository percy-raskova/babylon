"""Tests for EventBus and Event dataclass.

RED Phase: These tests define the contract for the event system.
The EventBus enables decoupled communication between simulation components.

Test Intent:
- Event is an immutable frozen dataclass
- EventBus supports publish/subscribe pattern
- Event history is maintained for replay/debugging
"""

from datetime import datetime

import pytest


class TestEvent:
    """Test Event dataclass behavior."""

    def test_event_creation_with_required_fields(self) -> None:
        """Event can be created with type, tick, and payload."""
        from babylon.engine.event_bus import Event

        event = Event(type="test_event", tick=1, payload={"key": "value"})

        assert event.type == "test_event"
        assert event.tick == 1
        assert event.payload == {"key": "value"}

    def test_event_has_timestamp(self) -> None:
        """Event automatically gets a timestamp."""
        from babylon.engine.event_bus import Event

        before = datetime.now()
        event = Event(type="test", tick=0, payload={})
        after = datetime.now()

        assert before <= event.timestamp <= after

    def test_event_is_frozen_immutable(self) -> None:
        """Event is immutable (frozen dataclass)."""
        from babylon.engine.event_bus import Event

        event = Event(type="test", tick=0, payload={})

        with pytest.raises(AttributeError):
            event.type = "modified"  # type: ignore[misc]

    def test_event_equality(self) -> None:
        """Two events with same values are equal (except timestamp)."""
        from babylon.engine.event_bus import Event

        timestamp = datetime.now()
        event1 = Event(type="test", tick=1, payload={"a": 1}, timestamp=timestamp)
        event2 = Event(type="test", tick=1, payload={"a": 1}, timestamp=timestamp)

        assert event1 == event2


class TestEventBus:
    """Test EventBus publish/subscribe behavior."""

    def test_handler_receives_published_event(self) -> None:
        """A subscribed handler receives the published event."""
        from babylon.engine.event_bus import Event, EventBus

        bus = EventBus()
        received_events: list[Event] = []

        def handler(event: Event) -> None:
            received_events.append(event)

        bus.subscribe("tick", handler)
        event = Event(type="tick", tick=1, payload={"value": 42})
        bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0] == event

    def test_multiple_subscribers_all_called(self) -> None:
        """Multiple subscribers to the same event type are all notified."""
        from babylon.engine.event_bus import Event, EventBus

        bus = EventBus()
        calls: list[str] = []

        def handler_a(_event: Event) -> None:
            calls.append("A")

        def handler_b(_event: Event) -> None:
            calls.append("B")

        bus.subscribe("tick", handler_a)
        bus.subscribe("tick", handler_b)
        bus.publish(Event(type="tick", tick=1, payload={}))

        assert "A" in calls
        assert "B" in calls
        assert len(calls) == 2

    def test_subscribers_only_receive_matching_event_type(self) -> None:
        """Subscribers only receive events of the type they subscribed to."""
        from babylon.engine.event_bus import Event, EventBus

        bus = EventBus()
        tick_events: list[Event] = []
        other_events: list[Event] = []

        def tick_handler(event: Event) -> None:
            tick_events.append(event)

        def other_handler(event: Event) -> None:
            other_events.append(event)

        bus.subscribe("tick", tick_handler)
        bus.subscribe("other", other_handler)

        bus.publish(Event(type="tick", tick=1, payload={}))
        bus.publish(Event(type="other", tick=1, payload={}))

        assert len(tick_events) == 1
        assert len(other_events) == 1

    def test_publish_to_type_with_no_subscribers_does_not_error(self) -> None:
        """Publishing to an event type with no subscribers is a no-op."""
        from babylon.engine.event_bus import Event, EventBus

        bus = EventBus()
        # Should not raise
        bus.publish(Event(type="no_subscribers", tick=0, payload={}))

    def test_history_stores_events_in_order(self) -> None:
        """Event history preserves chronological order."""
        from babylon.engine.event_bus import Event, EventBus

        bus = EventBus()

        event1 = Event(type="a", tick=1, payload={"order": 1})
        event2 = Event(type="b", tick=2, payload={"order": 2})
        event3 = Event(type="a", tick=3, payload={"order": 3})

        bus.publish(event1)
        bus.publish(event2)
        bus.publish(event3)

        history = bus.get_history()

        assert len(history) == 3
        assert history[0] == event1
        assert history[1] == event2
        assert history[2] == event3

    def test_clear_history_empties_event_log(self) -> None:
        """clear_history removes all stored events."""
        from babylon.engine.event_bus import Event, EventBus

        bus = EventBus()
        bus.publish(Event(type="test", tick=1, payload={}))
        bus.publish(Event(type="test", tick=2, payload={}))

        assert len(bus.get_history()) == 2

        bus.clear_history()

        assert len(bus.get_history()) == 0

    def test_get_history_returns_copy(self) -> None:
        """get_history returns a copy, not the internal list."""
        from babylon.engine.event_bus import Event, EventBus

        bus = EventBus()
        bus.publish(Event(type="test", tick=1, payload={}))

        history = bus.get_history()
        history.clear()  # Modify the returned list

        # Internal history should be unaffected
        assert len(bus.get_history()) == 1

    def test_event_bus_initially_empty(self) -> None:
        """A new EventBus has no history and no subscribers."""
        from babylon.engine.event_bus import EventBus

        bus = EventBus()

        assert bus.get_history() == []
