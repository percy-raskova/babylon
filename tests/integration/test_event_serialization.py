"""Spec 061 T045 / FR-012: serialized events expose id/severity/title/body.

Verifies that the bridge-layer ``_serialize_event`` helper produces the
spec-061 EventSerializer-compatible shape: every event has a stable
``id``, a three-bucket ``severity``, non-empty ``title``, present (but
possibly empty) ``body``, and the legacy ``type``/``tick``/``data``
triple is preserved.

Direct unit-style tests against the bridge helpers — no live DB needed.
"""

from __future__ import annotations

import uuid
from typing import Any

from web.game.engine_bridge import (
    _classify_event,
    _humanize_event_type,
    _serialize_event,
)


class _StubEvent:
    """Minimal event object that quacks like a SimulationEvent."""

    def __init__(
        self,
        event_type: str,
        tick: int = 0,
        narrative: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.event_type = event_type
        self.tick = tick
        self.narrative = narrative
        self.data = data or {}

    def model_dump(self, exclude: set[str] | None = None) -> dict[str, Any]:
        return self.data


class TestSeveritySchema:
    """FR-012: severity is one of the canonical three buckets.

    Every key exercised here is a real ``EventType.value`` (the Seam
    Observatory's ``check_severity_vocabulary`` gate now enforces that
    ``_EVENT_SEVERITY`` cannot key on a non-EventType string). The prior
    version of this test asserted eight drifted strings that no engine event
    ever carried — false confidence the Program-17 seam work removed.
    """

    def test_critical_events_classified_as_critical(self) -> None:
        for event_type in (
            "economic_crisis",
            "class_decomposition",
            "superwage_crisis",
            "uprising",
            "endgame_reached",
        ):
            assert _classify_event(event_type) == "critical", event_type

    def test_warning_events_classified_as_warning(self) -> None:
        for event_type in (
            "state_repression",
            "red_settler_trap_detected",
            "excessive_force",
        ):
            assert _classify_event(event_type) == "warning", event_type

    def test_informational_events_classified_as_informational(self) -> None:
        for event_type in (
            "surplus_extraction",
            "imperial_subsidy",
            "consciousness_transmission",
        ):
            assert _classify_event(event_type) == "informational", event_type

    def test_unknown_events_default_to_informational(self) -> None:
        assert _classify_event("unknown_made_up_event_type") == "informational"
        assert _classify_event("") == "informational"


class TestSerializedEventShape:
    """T045 / FR-012: serialized events carry id/severity/title/body."""

    def test_event_includes_severity_title_body_id(self) -> None:
        session_id = uuid.uuid4()
        event = _StubEvent(
            event_type="economic_crisis",
            tick=7,
            narrative="Market crash in periphery sector III.",
            data={"region": "26163", "magnitude": 0.42},
        )
        out = _serialize_event(event, session_id)

        # Required spec 061 fields
        assert out["id"] != ""
        assert out["type"] == "economic_crisis"
        assert out["tick"] == 7
        assert out["severity"] == "critical"
        assert out["title"] == "Economic Crisis"  # _humanize
        assert out["body"] == "Market crash in periphery sector III."
        # Legacy fields preserved
        assert out["data"] == {"region": "26163", "magnitude": 0.42}

    def test_id_is_deterministic_across_calls(self) -> None:
        """Constitution III.7 — same (session, tick, type, data) → same id."""
        session_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        event = _StubEvent(event_type="surplus_extraction", tick=3, data={"amount": 10.0})
        out_a = _serialize_event(event, session_id)
        out_b = _serialize_event(event, session_id)
        assert out_a["id"] == out_b["id"]

    def test_id_differs_across_sessions(self) -> None:
        event = _StubEvent(event_type="surplus_extraction", tick=0, data={"x": 1})
        out_a = _serialize_event(event, uuid.uuid4())
        out_b = _serialize_event(event, uuid.uuid4())
        assert out_a["id"] != out_b["id"]

    def test_body_defaults_to_empty_string_when_no_narrative(self) -> None:
        event = _StubEvent(event_type="wage_payment", tick=0, data={"amt": 1.0})
        out = _serialize_event(event, uuid.uuid4())
        assert out["body"] == ""
        # Empty body is still a string — the frontend can `if (event.body)` cleanly.
        assert isinstance(out["body"], str)

    def test_humanize_event_type(self) -> None:
        assert _humanize_event_type("economic_crisis") == "Economic Crisis"
        assert _humanize_event_type("imperial_subsidy") == "Imperial Subsidy"
        assert _humanize_event_type("rupture") == "Rupture"
