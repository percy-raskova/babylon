"""The NarrationEnvelope — one append-only record per committed tick.

Standard §5 (the density/narrator lane; ADR176 rulings 26/27's substrate)
and the design-inputs dossier's direction: the deterministic fallback
*already exists and is better than templates* — this module adds the
CONTRACT. One JSONL record per committed tick carrying the deterministic
summary, the folded severity, per-event lines, the tick's player acts, the
numeric deltas, and an ``entities[]`` proper-noun dictionary. This is the
artifact the Rust engine must emit (it closes the BSL standard's OQ-32) —
specified Python-first so the goldens exist before the port.

Everything is a pure function of the tick's own committed content: no
wall clock, no randomness, no LLM. The serialized form is compact JSON
with sorted keys — the SAME convention ``docs/reference/
determinism-contract.rst`` pins for ``ContentDigest`` — so identical ticks
produce identical BYTES.

The four-tier consumption ladder (bulletin every tick / dispatch on
salience / chapter every 52 / the Book at close) reads FROM these records;
the ladder itself lands with the narrator lane, not here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from babylon.game.chronicle_adapter import summarize_event
from babylon.models.enums.events import EventType
from babylon.models.event_severity import resolve_severity

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from babylon.kernel.event_bus import Event

__all__ = [
    "ENTITY_PAYLOAD_KEYS",
    "EnvelopeEvent",
    "JsonlNarrationSink",
    "NarrationEnvelope",
    "NarrationSink",
    "envelope_from_tick",
    "envelope_jsonl_line",
]

#: The DECLARED payload keys scanned for proper nouns (``entities[]``).
#: A key absent here never contributes an entity — widen deliberately, never
#: by pattern-matching arbitrary ``*_id`` fields (an undeclared scan would
#: silently change the wire record when any system adds a payload key).
ENTITY_PAYLOAD_KEYS: tuple[str, ...] = (
    "class_id",
    "comprador_id",
    "entity_id",
    "faction_id",
    "host_id",
    "incumbent_id",
    "institution_id",
    "member_id",
    "node_id",
    "org_id",
    "payer_id",
    "periphery_id",
    "receiver_id",
    "source_id",
    "sovereign_id",
    "target_id",
    "territory_id",
)

_SEVERITY_RANK: dict[str, int] = {"informational": 0, "warning": 1, "critical": 2}


class EnvelopeEvent(BaseModel):
    """One bus event's line in the envelope: type, tier, bespoke summary."""

    model_config = ConfigDict(frozen=True)

    event_type: str
    severity: str
    summary: str


class NarrationEnvelope(BaseModel):
    """One committed tick's narration record (see the module docstring)."""

    model_config = ConfigDict(frozen=True)

    tick: int = Field(ge=0)
    replay_identity_hash: str = Field(min_length=64, max_length=64)
    severity: str
    summary: str
    events: tuple[EnvelopeEvent, ...]
    player_acts: tuple[str, ...]
    deltas: dict[str, float | int | None]
    entities: tuple[str, ...]


def envelope_from_tick(
    *,
    tick: int,
    replay_identity_hash: str,
    events: Sequence[Event],
    summary_row: Mapping[str, Any],
    player_acts: Sequence[str],
) -> NarrationEnvelope:
    """Build one tick's envelope — a pure function of committed content.

    :param tick: The committed tick.
    :param replay_identity_hash: The tick's replay-identity stamp (the same
        value ``tick_commit`` carries).
    :param events: This tick's raw bus history, in emission order.
    :param summary_row: The tick-summary aggregate row the session already
        computes (``build_tick_summary_kwargs``); only its numeric content
        (and honest ``None``\\ s) enters ``deltas``.
    :param player_acts: The tick's resolved player actions, compact
        ``org:verb`` strings, in submission order.
    :returns: The frozen envelope.
    """
    envelope_events: list[EnvelopeEvent] = []
    entities: set[str] = set()
    top_rank = 0
    top_summary: str | None = None
    for event in events:  # loop bound: len(events)
        event_type = EventType(event.type)
        tier = resolve_severity(event_type).tier
        line = summarize_event(event_type, event.tick, event.payload)
        envelope_events.append(
            EnvelopeEvent(event_type=event_type.value, severity=tier, summary=line)
        )
        rank = _SEVERITY_RANK[tier]
        if top_summary is None or rank > top_rank:
            top_rank = rank
            top_summary = line
        for key in ENTITY_PAYLOAD_KEYS:  # loop bound: len(ENTITY_PAYLOAD_KEYS)
            value = event.payload.get(key)
            if isinstance(value, str) and value:
                entities.add(value)

    severity = "informational" if top_summary is None else _tier_name(top_rank)
    summary = (
        top_summary
        if top_summary is not None
        else f"tick {tick}: no events — structural drift only"
    )
    deltas = {
        key: value
        for key, value in summary_row.items()
        if value is None or (isinstance(value, int | float) and not isinstance(value, bool))
    }
    return NarrationEnvelope(
        tick=tick,
        replay_identity_hash=replay_identity_hash,
        severity=severity,
        summary=summary,
        events=tuple(envelope_events),
        player_acts=tuple(player_acts),
        deltas=deltas,
        entities=tuple(sorted(entities)),
    )


def _tier_name(rank: int) -> str:
    for name, value in _SEVERITY_RANK.items():
        if value == rank:
            return name
    msg = f"unknown severity rank {rank}"  # pragma: no cover — ranks are closed
    raise ValueError(msg)  # pragma: no cover


def envelope_jsonl_line(envelope: NarrationEnvelope) -> str:
    """Serialize one envelope to its canonical single-line JSON form.

    Compact separators, sorted keys — the determinism contract's
    ``ContentDigest`` serialization convention, applied here so identical
    ticks produce identical bytes and the goldens are byte-pinnable.
    """
    return json.dumps(envelope.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


class NarrationSink(Protocol):
    """Where committed-tick envelopes go (the session's emission seam)."""

    def emit(self, envelope: NarrationEnvelope) -> None:
        """Receive one committed tick's envelope."""
        ...


class JsonlNarrationSink:
    """Append-only JSONL writer — the production sink beside the vault.

    :param path: The ``narration.jsonl`` file (parent created as needed).
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def emit(self, envelope: NarrationEnvelope) -> None:
        """Append one canonical line (create-on-first-write, never truncate)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(envelope_jsonl_line(envelope) + "\n")
