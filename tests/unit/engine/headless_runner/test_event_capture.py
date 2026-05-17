"""Spec-065 T066/T067: EventCapture unit tests."""

from __future__ import annotations

from babylon.engine.headless_runner.event_capture import EngineEvent, EventCapture


class _MockEvent:
    """Stub mimicking an engine EventBus event payload."""

    def __init__(
        self,
        *,
        event_type: str = "TestEvent",
        entity_ids: tuple[str, ...] = (),
        severity: str = "info",
    ) -> None:
        self.event_type = event_type
        self.affected_entity_ids = entity_ids
        self.severity = severity


# ----------------------------------------------------------------------
# T066: capture appends in emission order
# ----------------------------------------------------------------------


class TestCaptureAppendsInOrder:
    def test_set_tick_then_on_event_preserves_order(self) -> None:
        cap = EventCapture()
        cap.set_tick(3)
        cap.on_event(_MockEvent(event_type="A", entity_ids=("e1",)))
        cap.on_event(_MockEvent(event_type="B", entity_ids=("e2",)))
        cap.set_tick(4)
        cap.on_event(_MockEvent(event_type="C", entity_ids=("e3",)))

        drained = cap.drain()
        assert len(drained) == 3
        assert [e.tick for e in drained] == [3, 3, 4]
        assert [e.event_type for e in drained] == ["A", "B", "C"]
        assert [e.entity_ids for e in drained] == [("e1",), ("e2",), ("e3",)]

    def test_negative_tick_raises(self) -> None:
        cap = EventCapture()
        try:
            cap.set_tick(-1)
        except ValueError as exc:
            assert "non-negative" in str(exc)
        else:
            raise AssertionError("Expected ValueError for negative tick")


# ----------------------------------------------------------------------
# T067: determinism — same input → byte-identical drain
# ----------------------------------------------------------------------


class TestEmissionOrderDeterministic:
    def test_two_captures_same_input_same_output(self) -> None:
        events = [
            _MockEvent(event_type="A", entity_ids=("e1",)),
            _MockEvent(event_type="B", entity_ids=("e2",)),
            _MockEvent(event_type="A", entity_ids=("e3",), severity="warning"),
        ]

        cap1 = EventCapture()
        cap1.set_tick(5)
        for ev in events:
            cap1.on_event(ev)
        d1 = cap1.drain()

        cap2 = EventCapture()
        cap2.set_tick(5)
        for ev in events:
            cap2.on_event(ev)
        d2 = cap2.drain()

        # Pydantic frozen models with identical fields → equal.
        assert d1 == d2

    def test_drain_does_not_clear_buffer(self) -> None:
        """drain() returns a snapshot; calling twice yields the same data."""
        cap = EventCapture()
        cap.set_tick(1)
        cap.on_event(_MockEvent(event_type="A"))
        d1 = cap.drain()
        d2 = cap.drain()
        assert d1 == d2


# ----------------------------------------------------------------------
# EngineEvent model itself
# ----------------------------------------------------------------------


class TestEngineEventModel:
    def test_construct_with_required_fields(self) -> None:
        ev = EngineEvent(tick=5, event_type="X")
        assert ev.tick == 5
        assert ev.event_type == "X"
        assert ev.entity_ids == ()
        assert ev.severity == "info"
        assert ev.details == {}

    def test_severity_literal_enforced(self) -> None:
        # Valid severities work
        for sev in ("info", "warning", "error", "critical"):
            EngineEvent(tick=0, event_type="X", severity=sev)  # type: ignore[arg-type]

    def test_negative_tick_rejected(self) -> None:
        from pydantic import ValidationError

        try:
            EngineEvent(tick=-1, event_type="X")
        except ValidationError:
            pass
        else:
            raise AssertionError("Expected ValidationError for negative tick")
