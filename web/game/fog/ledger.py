"""Track 1 / Task 3 (2026-07-18): the intel ledger.

A session-scoped, event-sourced record of INVESTIGATE resolutions. Each
:class:`IntelEntry` is one append-only fact: "at ``tick_observed``, this
``field_group`` on this ``node_id`` looked like ``value_snapshot``."
Visibility — whether a reader sees that snapshot exact, quantized, or not at
all — is the PURE FUNCTION :func:`read_intel` of ``(ledger, tick)``. Nothing
here runs a decay simulation, mutates engine state, or feeds back into the
tick hash.

**Distinct from the engine-side scalar.** ``territory.py:221-233`` has its
own ``investigation_intel`` field that lives inside the tick hash — that is
the engine's own bookkeeping and is untouched by this module. This ledger is
a bridge/session-layer concept: it exists only to answer "what does the
player org currently know, and how fresh is it," never to influence the
simulation.

**Import-boundary note.** Like :mod:`game.fog.reach`, this module imports
nothing from ``babylon.*`` — it is a pure Python/Pydantic package, decoupled
from the engine by construction, not just by the web import-boundary test
(``tests/unit/web/test_import_boundary.py``). Coefficients
(``intel_staleness_ticks`` / ``intel_unknown_ticks``, both
``GameDefines.epistemic_horizon.*``) are supplied explicitly by the caller.

**API for Task 4.** ``apply_fog(payload, node_type, node_id, reach, ledger,
tick)`` is expected to call :func:`read_intel` once per masked field group on
an out-of-reach node, and splice ``reading.value_snapshot`` (or ``None``)
into the payload according to ``reading.tier`` — mirroring the
``vision_masked``/``vision_approx`` idiom ``engine_bridge._apply_class_vision_gate``
already uses for the class-vision gate.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

VisibilityTier = Literal["exact", "approximate", "unknown"]

#: Mirrors ``engine_bridge._MUD_QUANTUM`` (:1748) — the corpus's "±0.2 margin
#: of error" (fog-of-war.yaml:335) needs 0.4-wide buckets to honor that
#: margin without shipping twice the precision the corpus allows. Duplicated
#: here (not imported) because ``engine_bridge.py`` will import THIS package
#: in Task 4 — importing back from it would cycle. If Task 4 extracts a
#: shared quantization helper, this constant/function should be replaced by
#: that import rather than kept as a second copy.
_MUD_QUANTUM = 0.4


def _quantize(value: float) -> float:
    """One value onto the Mud grid — see ``engine_bridge._mud_quantize``
    (:1751-1762) for the byte-identical algorithm and its rounding rationale
    (explicit half-up, clamped to [0, 1])."""
    return min(1.0, max(0.0, math.floor(value / _MUD_QUANTUM + 0.5) * _MUD_QUANTUM))


class IntelEntry(BaseModel):
    """One append-only observation fact from an INVESTIGATE resolution.

    Attributes:
        node_id: The graph node this observation is about.
        field_group: Caller-defined grouping key for the observed fields
            (e.g. ``"political"``) — lets one INVESTIGATE resolution cover
            several related fields with one aging clock.
        tick_observed: The simulation tick this snapshot was taken at.
        value_snapshot: The observed field values, verbatim, at
            ``tick_observed``. Always the TRUE values as of that tick — any
            masking/quantization happens only at read time
            (:func:`read_intel`), never at write time.
    """

    model_config = ConfigDict(frozen=True)

    node_id: str
    field_group: str
    tick_observed: int
    value_snapshot: dict[str, Any] = Field(default_factory=dict)


class IntelLedger(BaseModel):
    """Session-scoped, append-only ledger of :class:`IntelEntry` facts.

    Immutable (frozen Pydantic model): :meth:`append` returns a NEW ledger
    rather than mutating in place, so a ledger value can be threaded through
    a session/request without aliasing surprises.
    """

    model_config = ConfigDict(frozen=True)

    entries: tuple[IntelEntry, ...] = Field(default_factory=tuple)

    def append(self, entry: IntelEntry) -> IntelLedger:
        """Return a NEW ledger with ``entry`` appended — never mutates ``self``."""
        return IntelLedger(entries=(*self.entries, entry))

    def latest(self, node_id: str, field_group: str) -> IntelEntry | None:
        """The most-recent (highest ``tick_observed``) entry for
        ``(node_id, field_group)``, or ``None`` if that pair was never
        observed (honest absence, Constitution III.11 — never a fabricated
        default snapshot)."""
        candidates = [
            entry
            for entry in self.entries
            if entry.node_id == node_id and entry.field_group == field_group
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda entry: entry.tick_observed)


class IntelReading(BaseModel):
    """The rendered result of reading the ledger at a given tick.

    Attributes:
        tier: ``"exact"`` (fresh — verbatim ``value_snapshot``),
            ``"approximate"`` (aged — numeric leaves quantized), or
            ``"unknown"`` (never observed, or too stale — ``value_snapshot``
            and ``tick_observed`` are both ``None``).
        tick_observed: The tick the underlying entry was recorded at, or
            ``None`` for ``tier == "unknown"``.
        value_snapshot: The rendered snapshot (verbatim or quantized), or
            ``None`` for ``tier == "unknown"``.
    """

    model_config = ConfigDict(frozen=True)

    tier: VisibilityTier
    tick_observed: int | None
    value_snapshot: dict[str, Any] | None


def _quantize_snapshot(value_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Quantize numeric leaves of a snapshot for the "approximate" tier.

    Non-numeric fields (strings, None, nested structures) pass through
    unchanged — mirroring ``_apply_class_vision_gate``'s
    ``isinstance(value, int | float)`` guard, which never claims false
    precision loss for a field it cannot honestly quantize.
    """
    return {
        field: _quantize(float(value)) if isinstance(value, int | float) else value
        for field, value in value_snapshot.items()
    }


def read_intel(
    ledger: IntelLedger,
    node_id: str,
    field_group: str,
    tick: int,
    staleness_ticks: int,
    unknown_ticks: int,
) -> IntelReading:
    """Pure function: ``(ledger, tick)`` -> a rendered :class:`IntelReading`.

    Age is ``tick - entry.tick_observed``. Age ``<= staleness_ticks`` is
    exact; ``staleness_ticks < age <= unknown_ticks`` is approximate
    (quantized); ``age > unknown_ticks``, or no entry at all, is unknown.

    Args:
        ledger: The session's :class:`IntelLedger`.
        node_id: The node to read intel about.
        field_group: The field group to read (see :class:`IntelEntry`).
        tick: The current simulation tick.
        staleness_ticks: ``GameDefines.epistemic_horizon.intel_staleness_ticks``
            — entries no older than this render exact.
        unknown_ticks: ``GameDefines.epistemic_horizon.intel_unknown_ticks``
            — entries no older than this (but past ``staleness_ticks``)
            render approximate; older renders unknown.

    Returns:
        The rendered :class:`IntelReading`.

    Raises:
        ValueError: If the latest entry's ``tick_observed`` is after
            ``tick`` — a future-dated observation is a determinism bug
            (or clock skew), never something to silently misclassify
            (Constitution III.11: loud failure, not a quiet best-effort).
    """
    entry = ledger.latest(node_id, field_group)
    if entry is None:
        return IntelReading(tier="unknown", tick_observed=None, value_snapshot=None)

    age = tick - entry.tick_observed
    if age < 0:
        raise ValueError(
            f"Intel entry for ({node_id!r}, {field_group!r}) was observed at "
            f"tick {entry.tick_observed}, after the query tick {tick} — "
            "a future-dated observation, not a valid age"
        )

    if age <= staleness_ticks:
        return IntelReading(
            tier="exact",
            tick_observed=entry.tick_observed,
            value_snapshot=dict(entry.value_snapshot),
        )
    if age <= unknown_ticks:
        return IntelReading(
            tier="approximate",
            tick_observed=entry.tick_observed,
            value_snapshot=_quantize_snapshot(entry.value_snapshot),
        )
    return IntelReading(tier="unknown", tick_observed=None, value_snapshot=None)


def ledger_from_events(rows: list[dict[str, Any]]) -> IntelLedger:
    """Fold persisted INVESTIGATE-resolution rows into an :class:`IntelLedger`.

    Track 1 / Task 3 (2026-07-18): THE ledger's writer — before this
    function existed, ``IntelLedger`` was constructed exactly once, empty,
    as a module constant (``engine_bridge._EMPTY_INTEL_LEDGER``), and never
    appended to. Pure fold, no I/O, no globals, no ``babylon.*`` import (see
    the module docstring's import-boundary note) — ``rows`` are plain
    dicts the caller (``engine_bridge.py``) has ALREADY queried from the
    persisted ``action_result`` table and ALREADY filtered to successful
    ``ActionType.MAP_NETWORK`` (INVESTIGATE) resolutions; this module never
    performs that filter itself; it would need ``ActionType`` to do so).

    Each row must supply:

    * ``tick`` (int) — the tick the INVESTIGATE resolved at, becomes
      ``IntelEntry.tick_observed``.
    * ``target_id`` (str) — the investigated node's id, becomes
      ``IntelEntry.node_id``.
    * ``field_group`` (str) — MUST equal
      ``game.fog.filter.political_field_group(node_type)`` for the
      target's real ``_node_type`` (e.g. ``"territory:political"``) — the
      exact key :func:`apply_fog`'s ``read_intel`` call derives. A
      mismatched group silently makes the entry unreachable, which is why
      the writer (``engine_bridge._investigate_field_snapshot``) derives
      it with that SAME helper rather than formatting the string itself.
    * ``value_snapshot`` (dict) — the revealed fields' TRUE values as of
      ``tick``, captured by the writer off the live post-tick graph at
      resolution time (never recomputed later — that is what lets a stale
      reading show what the player actually learned, not the current
      truth).

    A row missing any of these (or with an empty ``value_snapshot``) is
    skipped — Constitution III.11: a partial/malformed persisted row never
    fabricates a fake observation. Row order does not matter:
    :meth:`IntelLedger.latest` reduces by ``tick_observed`` regardless of
    append order, so out-of-order rows (e.g. a non-chronological DB read)
    still resolve correctly.

    Args:
        rows: Already-filtered persisted INVESTIGATE-resolution rows.

    Returns:
        A new :class:`IntelLedger` with one entry per valid row.
    """
    ledger = IntelLedger()
    for row in rows:
        target_id = row.get("target_id")
        field_group = row.get("field_group")
        tick_observed = row.get("tick")
        value_snapshot = row.get("value_snapshot")
        if not target_id or not field_group or tick_observed is None or not value_snapshot:
            continue
        ledger = ledger.append(
            IntelEntry(
                node_id=str(target_id),
                field_group=str(field_group),
                tick_observed=int(tick_observed),
                value_snapshot=dict(value_snapshot),
            )
        )
    return ledger


__all__ = [
    "IntelEntry",
    "IntelLedger",
    "IntelReading",
    "VisibilityTier",
    "ledger_from_events",
    "read_intel",
]
