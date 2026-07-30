"""The NarrationEnvelope contract (Standard §5; ADR176 rulings 26/27 lane).

One append-only JSONL record per committed tick: deterministic summary,
severity, per-event lines, player acts, numeric deltas, and the
``entities[]`` proper-noun dictionary — the artifact the Rust engine must
emit (it closes the BSL standard's OQ-32), specified Python-first so the
goldens exist before the port. Everything here is a pure function of the
tick's own committed content: same inputs, same JSON BYTES (compact,
sorted keys — the determinism contract's serialization convention).
"""

from __future__ import annotations

import json

import pytest

from babylon.kernel.event_bus import Event
from babylon.projection.narration_envelope import (
    NarrationEnvelope,
    envelope_from_tick,
    envelope_jsonl_line,
)

pytestmark = [pytest.mark.unit]


def _uprising(tick: int = 3) -> Event:
    return Event(
        type="uprising",
        tick=tick,
        payload={"node_id": "C_proletariat", "trigger": "wage_cut", "agitation": 0.7},
    )


def _surplus(tick: int = 3) -> Event:
    return Event(
        type="surplus_extraction",
        tick=tick,
        payload={"source_id": "C_periphery", "target_id": "C_core", "amount": 12.5},
    )


class TestEnvelopeBuilder:
    def test_same_inputs_same_bytes(self) -> None:
        """The whole point: byte-deterministic over the tick's content."""
        kwargs: dict = {
            "tick": 3,
            "determinism_hash": "a" * 64,
            "events": (_uprising(), _surplus()),
            "summary_row": {"tick": 3, "avg_wealth": 1.25, "uprising_count": 1},
            "player_acts": ("ORG001:mobilize",),
        }
        first = envelope_jsonl_line(envelope_from_tick(**kwargs))
        second = envelope_jsonl_line(envelope_from_tick(**kwargs))
        assert first == second
        parsed = json.loads(first)
        assert parsed["tick"] == 3

    def test_severity_folds_to_the_loudest_event(self) -> None:
        """UPRISING is critical in the severity vocabulary; the envelope's
        top-line severity is the max across the tick's events."""
        envelope = envelope_from_tick(
            tick=3,
            determinism_hash="a" * 64,
            events=(_surplus(), _uprising()),
            summary_row={},
            player_acts=(),
        )
        assert envelope.severity == "critical"
        assert any(e.severity == "critical" for e in envelope.events)

    def test_summary_is_the_loudest_events_bespoke_line(self) -> None:
        """The bulletin line comes from the chronicle's own deterministic
        builder for the top-severity event — never a fabricated sentence."""
        envelope = envelope_from_tick(
            tick=3,
            determinism_hash="a" * 64,
            events=(_surplus(), _uprising()),
            summary_row={},
            player_acts=(),
        )
        assert "C_proletariat" in envelope.summary  # the uprising, not the flow

    def test_quiet_tick_is_honest(self) -> None:
        envelope = envelope_from_tick(
            tick=9,
            determinism_hash="b" * 64,
            events=(),
            summary_row={"avg_wealth": 1.0},
            player_acts=(),
        )
        assert envelope.severity == "informational"
        assert "no events" in envelope.summary

    def test_entities_collects_sorted_unique_proper_nouns(self) -> None:
        envelope = envelope_from_tick(
            tick=3,
            determinism_hash="a" * 64,
            events=(_uprising(), _surplus(), _uprising()),
            summary_row={},
            player_acts=(),
        )
        assert envelope.entities == ("C_core", "C_periphery", "C_proletariat")

    def test_deltas_keep_numbers_and_honest_nulls_only(self) -> None:
        """The deltas block is the tick-summary aggregate row projected to
        numeric content — strings/objects stay out of the wire record."""
        envelope = envelope_from_tick(
            tick=3,
            determinism_hash="a" * 64,
            events=(),
            summary_row={
                "avg_wealth": 1.25,
                "uprising_count": 1,
                "phase": "expansion",
                "nested": {"x": 1},
                "gap": None,
            },
            player_acts=(),
        )
        assert envelope.deltas == {"avg_wealth": 1.25, "uprising_count": 1, "gap": None}

    def test_player_acts_ride_verbatim(self) -> None:
        envelope = envelope_from_tick(
            tick=3,
            determinism_hash="a" * 64,
            events=(),
            summary_row={},
            player_acts=("ORG001:mobilize", "ORG001:educate"),
        )
        assert envelope.player_acts == ("ORG001:mobilize", "ORG001:educate")

    def test_frozen(self) -> None:
        envelope = envelope_from_tick(
            tick=1, determinism_hash="c" * 64, events=(), summary_row={}, player_acts=()
        )
        with pytest.raises(Exception):  # noqa: B017, PT011 - pydantic frozen error class
            envelope.tick = 2  # type: ignore[misc]


class TestJsonlLine:
    def test_canonical_compact_sorted(self) -> None:
        """Compact separators + sorted keys — the SAME serialization
        convention the determinism contract pins for ContentDigest."""
        envelope = envelope_from_tick(
            tick=1, determinism_hash="c" * 64, events=(), summary_row={}, player_acts=()
        )
        line = envelope_jsonl_line(envelope)
        assert "\n" not in line
        parsed = json.loads(line)
        # Canonicality pinned structurally: the line IS its own canonical
        # re-serialization (compact separators + sorted keys), so no
        # whitespace or key-order variant can ever slip through.
        assert line == json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_round_trips(self) -> None:
        envelope = envelope_from_tick(
            tick=4,
            determinism_hash="d" * 64,
            events=(_uprising(4),),
            summary_row={"avg_wealth": 2.0},
            player_acts=("ORG001:strike",),
        )
        parsed = NarrationEnvelope.model_validate(json.loads(envelope_jsonl_line(envelope)))
        assert parsed == envelope
