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

    T1.1 U1/U2 (``ai/_inbox/t11-seam-severity-design.md``) retargeted severity
    onto ``babylon.models.event_severity``'s derived kind x terminal_proximity
    taxonomy, replacing the hand-copied ``_EVENT_SEVERITY`` dict this test
    previously exercised directly. The pure rule is not a rubber stamp of the
    old hand tiers: a CROSSING is binary critical-or-informational, so several
    members below moved tier (design §2's disclosed drift table) — each with
    a declared rationale in ``event_severity._DRIFT_RATIONALES``.
    """

    def test_critical_events_classified_as_critical(self) -> None:
        for event_type in (
            "economic_crisis",
            "class_decomposition",
            "superwage_crisis",
            "uprising",
            "endgame_reached",
            "red_brown_coup",
            # DRIFT (warning -> critical): PATTERN inheriting
            # BIFURCATION_THRESHOLD's tier — detecting this pattern means the
            # RED_OGV terminal-endgame track is live.
            "red_settler_trap_detected",
            # DRIFT (warning -> critical): a completed hostile capture, same
            # axis as red_brown_coup.
            "fascist_recruitment",
            # DRIFT (warning -> critical): PATTERN inheriting
            # ENDGAME_REACHED's tier — directly endgame-axis content.
            "pattern_shift",
        ):
            assert _classify_event(event_type) == "critical", event_type

    def test_warning_events_classified_as_warning(self) -> None:
        # Only ACT-kind verb resolutions stay at warning under the pure rule
        # (a CROSSING is binary critical-or-informational — there is no
        # warning tier for one).
        for event_type in ("state_repression",):
            assert _classify_event(event_type) == "warning", event_type

    def test_informational_events_classified_as_informational(self) -> None:
        for event_type in (
            "surplus_extraction",
            "imperial_subsidy",
            "consciousness_transmission",
            # DRIFT (warning -> informational): a reversible precursor to
            # fascist_recruitment's completed capture (above), not the
            # violation itself.
            "excessive_force",
            # DRIFT (warning -> informational): a single member's defection —
            # only accumulates into red_brown_coup (critical) once a majority
            # is reached.
            "organizational_fracture",
        ):
            assert _classify_event(event_type) == "informational", event_type

    def test_unknown_events_default_to_warning(self) -> None:
        """Constitution III.11 (Loud Failure): the T1.1 single-source floor is
        "warning", never the legacy quiet "informational" default — matching
        babylon.tui.chronicle_salience's identical floor on the Archive
        surface."""
        assert _classify_event("unknown_made_up_event_type") == "warning"
        assert _classify_event("") == "warning"


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
