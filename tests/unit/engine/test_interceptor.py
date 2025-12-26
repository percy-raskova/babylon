"""Tests for the Event Interceptor pattern.

Epoch 1→2 Bridge: These tests verify the Chain of Responsibility pattern
for event processing, enabling adversarial mechanics.
"""

from dataclasses import FrozenInstanceError

import pytest

from babylon.engine.event_bus import Event, EventBus
from babylon.engine.interceptor import (
    BlockedEvent,
    EventInterceptor,
    InterceptResult,
    SimpleWorldContext,
    WorldContext,
)

# =============================================================================
# TEST FIXTURES: Sample Interceptors
# =============================================================================


class PassThroughInterceptor(EventInterceptor):
    """Interceptor that allows all events."""

    @property
    def name(self) -> str:
        return "pass_through"

    @property
    def priority(self) -> int:
        return 50

    def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
        return InterceptResult.allow(event)


class BlockingInterceptor(EventInterceptor):
    """Interceptor that blocks all events."""

    def __init__(self, reason: str = "Blocked by test interceptor") -> None:
        self._reason = reason

    @property
    def name(self) -> str:
        return "blocker"

    @property
    def priority(self) -> int:
        return 100

    def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
        return InterceptResult.block(self._reason)


class ModifyingInterceptor(EventInterceptor):
    """Interceptor that modifies event payload."""

    @property
    def name(self) -> str:
        return "modifier"

    @property
    def priority(self) -> int:
        return 75

    def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
        modified = Event(
            type=event.type,
            tick=event.tick,
            payload={**event.payload, "modified": True},
        )
        return InterceptResult.modify(modified, "Added modified flag")


class ConditionalInterceptor(EventInterceptor):
    """Interceptor that blocks only AGITATE events."""

    @property
    def name(self) -> str:
        return "conditional"

    @property
    def priority(self) -> int:
        return 80

    def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
        if event.type == "AGITATE":
            return InterceptResult.block("AGITATE actions are blocked")
        return InterceptResult.allow(event)


class PriorityInterceptor(EventInterceptor):
    """Interceptor with configurable priority for testing order."""

    def __init__(self, name: str, priority: int) -> None:
        self._name = name
        self._priority = priority
        self.was_called = False
        self.call_order: int | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
        self.was_called = True
        return InterceptResult.allow(event)


# =============================================================================
# TESTS: InterceptResult
# =============================================================================


class TestInterceptResult:
    """Tests for the InterceptResult container."""

    def test_allow_creates_passing_result(self) -> None:
        """Allow() creates result with event and no reason."""
        event = Event(type="test", tick=1, payload={})
        result = InterceptResult.allow(event)

        assert result.event is event
        assert result.reason == ""
        assert not result.is_blocked
        assert not result.is_modified

    def test_block_creates_blocking_result(self) -> None:
        """Block() creates result with None event and reason."""
        result = InterceptResult.block("Security forces intervened")

        assert result.event is None
        assert result.reason == "Security forces intervened"
        assert result.is_blocked
        assert not result.is_modified

    def test_block_requires_reason(self) -> None:
        """Block() raises ValueError if reason is empty."""
        with pytest.raises(ValueError, match="reason cannot be empty"):
            InterceptResult.block("")

    def test_modify_creates_modified_result(self) -> None:
        """Modify() creates result with new event and reason."""
        modified = Event(type="test", tick=1, payload={"value": 2})
        result = InterceptResult.modify(modified, "Reduced effectiveness")

        assert result.event is modified
        assert result.reason == "Reduced effectiveness"
        assert not result.is_blocked
        assert result.is_modified

    def test_modify_allows_empty_reason(self) -> None:
        """Modify() allows empty reason (optional)."""
        event = Event(type="test", tick=1, payload={})
        result = InterceptResult.modify(event)

        assert result.event is event
        assert result.reason == ""

    def test_blocked_result_validation(self) -> None:
        """Direct construction with None event requires reason."""
        with pytest.raises(ValueError, match="must have a reason"):
            InterceptResult(event=None, reason="")

    def test_result_is_frozen(self) -> None:
        """InterceptResult is immutable."""
        event = Event(type="test", tick=1, payload={})
        result = InterceptResult.allow(event)

        with pytest.raises(FrozenInstanceError):
            result.reason = "modified"  # type: ignore[misc]


# =============================================================================
# TESTS: EventInterceptor ABC
# =============================================================================


class TestEventInterceptor:
    """Tests for the EventInterceptor abstract base class."""

    def test_default_priority_is_100(self) -> None:
        """Default priority is 100."""

        # PassThroughInterceptor overrides to 50, so use a minimal impl
        class DefaultPriorityInterceptor(EventInterceptor):
            @property
            def name(self) -> str:
                return "default"

            def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
                return InterceptResult.allow(event)

        assert DefaultPriorityInterceptor().priority == 100

    def test_name_is_abstract(self) -> None:
        """Name property must be implemented."""
        with pytest.raises(TypeError, match="abstract"):

            class MissingName(EventInterceptor):  # type: ignore[abstract]
                def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
                    return InterceptResult.allow(event)

            MissingName()

    def test_intercept_is_abstract(self) -> None:
        """Intercept method must be implemented."""
        with pytest.raises(TypeError, match="abstract"):

            class MissingIntercept(EventInterceptor):  # type: ignore[abstract]
                @property
                def name(self) -> str:
                    return "missing"

            MissingIntercept()


# =============================================================================
# TESTS: EventBus Interceptor Chain
# =============================================================================


class TestEventBusInterceptorChain:
    """Tests for EventBus interceptor integration."""

    def test_no_interceptors_fast_path(self) -> None:
        """Events emit directly when no interceptors registered."""
        bus = EventBus()
        received: list[Event] = []
        bus.subscribe("test", received.append)

        event = Event(type="test", tick=1, payload={"value": 42})
        bus.publish(event)

        assert len(received) == 1
        assert received[0] is event
        assert len(bus.get_history()) == 1

    def test_register_interceptor(self) -> None:
        """Interceptors can be registered."""
        bus = EventBus()
        interceptor = PassThroughInterceptor()

        bus.register_interceptor(interceptor)

        assert bus.interceptor_count == 1

    def test_unregister_interceptor(self) -> None:
        """Interceptors can be unregistered."""
        bus = EventBus()
        interceptor = PassThroughInterceptor()
        bus.register_interceptor(interceptor)

        bus.unregister_interceptor(interceptor)

        assert bus.interceptor_count == 0

    def test_unregister_unknown_interceptor_raises(self) -> None:
        """Unregistering unknown interceptor raises ValueError."""
        bus = EventBus()
        interceptor = PassThroughInterceptor()

        with pytest.raises(ValueError):
            bus.unregister_interceptor(interceptor)

    def test_passing_interceptor_allows_event(self) -> None:
        """Pass-through interceptor allows event emission."""
        bus = EventBus()
        bus.register_interceptor(PassThroughInterceptor())
        received: list[Event] = []
        bus.subscribe("test", received.append)

        event = Event(type="test", tick=1, payload={})
        bus.publish(event)

        assert len(received) == 1
        assert len(bus.get_history()) == 1

    def test_blocking_interceptor_stops_event(self) -> None:
        """Blocking interceptor prevents event emission."""
        bus = EventBus()
        bus.register_interceptor(BlockingInterceptor("Test block reason"))
        received: list[Event] = []
        bus.subscribe("test", received.append)

        event = Event(type="test", tick=1, payload={})
        bus.publish(event)

        assert len(received) == 0
        assert len(bus.get_history()) == 0

    def test_blocked_event_recorded_in_audit(self) -> None:
        """Blocked events are recorded with reason."""
        bus = EventBus()
        bus.register_interceptor(BlockingInterceptor("Security detained organizers"))

        event = Event(type="AGITATE", tick=5, payload={"target": "factory"})
        bus.publish(event)

        blocked = bus.get_blocked_events()
        assert len(blocked) == 1
        assert blocked[0].event is event
        assert blocked[0].interceptor_name == "blocker"
        assert blocked[0].reason == "Security detained organizers"

    def test_modifying_interceptor_transforms_event(self) -> None:
        """Modifying interceptor changes event before emission."""
        bus = EventBus()
        bus.register_interceptor(ModifyingInterceptor())
        received: list[Event] = []
        bus.subscribe("test", received.append)

        event = Event(type="test", tick=1, payload={"original": True})
        bus.publish(event)

        assert len(received) == 1
        assert received[0].payload["original"] is True
        assert received[0].payload["modified"] is True
        assert received[0] is not event  # Different object

    def test_interceptor_chain_priority_order(self) -> None:
        """Interceptors run in priority order (higher first)."""
        bus = EventBus()
        call_order: list[str] = []

        class OrderTracker(EventInterceptor):
            def __init__(self, name: str, priority: int) -> None:
                self._name = name
                self._priority = priority

            @property
            def name(self) -> str:
                return self._name

            @property
            def priority(self) -> int:
                return self._priority

            def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
                call_order.append(self._name)
                return InterceptResult.allow(event)

        bus.register_interceptor(OrderTracker("low", 10))
        bus.register_interceptor(OrderTracker("high", 100))
        bus.register_interceptor(OrderTracker("medium", 50))

        event = Event(type="test", tick=1, payload={})
        bus.publish(event)

        assert call_order == ["high", "medium", "low"]

    def test_blocking_stops_chain_early(self) -> None:
        """Blocking interceptor prevents later interceptors from running."""
        bus = EventBus()

        high = PriorityInterceptor("high", 100)
        low = PriorityInterceptor("low", 10)
        blocker = BlockingInterceptor()  # priority 100

        bus.register_interceptor(low)
        bus.register_interceptor(blocker)  # Same priority as high
        bus.register_interceptor(high)

        event = Event(type="test", tick=1, payload={})
        bus.publish(event)

        # Blocker runs first (or tied with high), blocks chain
        assert low.was_called is False

    def test_conditional_blocking(self) -> None:
        """Interceptor can block some events but allow others."""
        bus = EventBus()
        bus.register_interceptor(ConditionalInterceptor())
        received: list[Event] = []
        bus.subscribe("AGITATE", received.append)
        bus.subscribe("ORGANIZE", received.append)

        bus.publish(Event(type="AGITATE", tick=1, payload={}))
        bus.publish(Event(type="ORGANIZE", tick=1, payload={}))

        assert len(received) == 1
        assert received[0].type == "ORGANIZE"

    def test_context_passed_to_interceptor(self) -> None:
        """World context is passed to interceptors."""
        bus = EventBus()
        received_context: list[WorldContext | None] = []

        class ContextCapture(EventInterceptor):
            @property
            def name(self) -> str:
                return "context_capture"

            def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
                received_context.append(context)
                return InterceptResult.allow(event)

        bus.register_interceptor(ContextCapture())
        context = SimpleWorldContext(tick=42)

        bus.publish(Event(type="test", tick=1, payload={}), context=context)

        assert len(received_context) == 1
        assert received_context[0] is context
        assert received_context[0].tick == 42

    def test_clear_blocked_events(self) -> None:
        """Blocked events can be cleared."""
        bus = EventBus()
        bus.register_interceptor(BlockingInterceptor())

        bus.publish(Event(type="test", tick=1, payload={}))
        assert len(bus.get_blocked_events()) == 1

        bus.clear_blocked_events()
        assert len(bus.get_blocked_events()) == 0

    def test_modification_chaining(self) -> None:
        """Multiple modifying interceptors chain correctly."""
        bus = EventBus()

        class AddFieldInterceptor(EventInterceptor):
            def __init__(self, field: str, value: int, priority: int) -> None:
                self._field = field
                self._value = value
                self._priority = priority

            @property
            def name(self) -> str:
                return f"add_{self._field}"

            @property
            def priority(self) -> int:
                return self._priority

            def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
                modified = Event(
                    type=event.type,
                    tick=event.tick,
                    payload={**event.payload, self._field: self._value},
                )
                return InterceptResult.modify(modified, f"Added {self._field}")

        bus.register_interceptor(AddFieldInterceptor("first", 1, 100))
        bus.register_interceptor(AddFieldInterceptor("second", 2, 50))

        received: list[Event] = []
        bus.subscribe("test", received.append)

        bus.publish(Event(type="test", tick=1, payload={}))

        assert len(received) == 1
        assert received[0].payload == {"first": 1, "second": 2}


# =============================================================================
# TESTS: SimpleWorldContext
# =============================================================================


class TestSimpleWorldContext:
    """Tests for the SimpleWorldContext implementation."""

    def test_default_values(self) -> None:
        """Default context has tick 0 and empty data."""
        context = SimpleWorldContext()
        assert context.tick == 0
        assert context.data == {}

    def test_custom_values(self) -> None:
        """Context can be created with custom values."""
        context = SimpleWorldContext(
            tick=42,
            data={"surveillance": 0.8, "territory": "factory_district"},
        )
        assert context.tick == 42
        assert context.data["surveillance"] == 0.8


# =============================================================================
# TESTS: BlockedEvent
# =============================================================================


class TestBlockedEvent:
    """Tests for the BlockedEvent audit record."""

    def test_blocked_event_captures_all_fields(self) -> None:
        """BlockedEvent captures event, interceptor, reason, and time."""
        event = Event(type="AGITATE", tick=5, payload={})
        blocked = BlockedEvent(
            event=event,
            interceptor_name="state_security",
            reason="High surveillance territory",
        )

        assert blocked.event is event
        assert blocked.interceptor_name == "state_security"
        assert blocked.reason == "High surveillance territory"
        assert blocked.blocked_at is not None

    def test_blocked_event_is_frozen(self) -> None:
        """BlockedEvent is immutable."""
        event = Event(type="test", tick=1, payload={})
        blocked = BlockedEvent(event=event, interceptor_name="test", reason="test")

        with pytest.raises(FrozenInstanceError):
            blocked.reason = "modified"  # type: ignore[misc]
