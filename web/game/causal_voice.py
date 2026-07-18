"""Deterministic causal voice — frame→beat templates (spec-116 FR-4.1, design §6).

Renders ``CausalChainObserver`` frames into ``NarrationRecord`` beat specs
with fixed templates: pure data + pure functions — no Django, no engine
imports, no randomness. The same frame always renders the same bytes, so
beat ids stay stable across refetches (the panel's ``mergeBeats`` dedups by
id) and re-runs. Copy lives in module-level data constants, not
conditionals (spec-116 Constraints); the only branching is on the frame's
own before/after arithmetic.

LLM garnish (``NarrativeService``) remains a separate, flag-gated channel
(``BABYLON_LLM_NARRATOR``). Absent a model, these templates are what the
narration panel serves — nothing is ever empty (design §6).

:data:`CAUSAL_PROMPT_VERSION` is a content hash of the template constants —
the same pin discipline as the LLM path's ``prompt_version`` (Constitution
III.6): a copy edit changes the hash, so persisted rows carry the exact
template generation that rendered them.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

#: ``NarrationRecord.model_id`` pin for deterministic causal beats.
CAUSAL_MODEL_ID: str = "deterministic-causal-v1"

_PULSE_HEADLINE: str = "The week's ledger, tick {tick}."

#: Per-metric sentence templates when the value moved ({verb} = rose|fell).
_PULSE_MOVED: dict[str, str] = {
    "pool": "The imperial rent pool {verb} from {before:.2f} to {after:.2f}.",
    "wage": "The super-wage rate {verb} from {before:.4f} to {after:.4f}.",
    "p_rev": "Peak revolutionary probability {verb} from {before:.3f} to {after:.3f}.",
}

#: Per-metric sentence templates when the value held exactly.
_PULSE_HELD: dict[str, str] = {
    "pool": "The imperial rent pool held at {after:.2f}.",
    "wage": "The super-wage rate held at {after:.4f}.",
    "p_rev": "Peak revolutionary probability held at {after:.3f}.",
}

_SHOCK_HEADLINE: str = "Shock, austerity, radicalization — the causal chain closed."

_SHOCK_BODY: str = (
    "The rent pool crashed {drop:.1f}% at tick {crash_tick}. "
    "In the aftermath the super-wage rate was cut from {wage_before:.4f} to {wage_after:.4f}. "
    "Peak revolutionary probability climbed from {p_before:.3f} to {p_after:.3f} — "
    "the shock is being answered."
)

#: Content hash of every template above — the deterministic prompt_version pin.
CAUSAL_PROMPT_VERSION: str = hashlib.sha256(
    "\n".join(
        [
            _PULSE_HEADLINE,
            *(_PULSE_MOVED[k] for k in sorted(_PULSE_MOVED)),
            *(_PULSE_HELD[k] for k in sorted(_PULSE_HELD)),
            _SHOCK_HEADLINE,
            _SHOCK_BODY,
        ]
    ).encode("utf-8")
).hexdigest()[:12]

#: Fixed render order for pulse sentences (deterministic bytes).
_METRIC_ORDER: tuple[str, ...] = ("pool", "wage", "p_rev")


class CausalBeatSpec(NamedTuple):
    """One rendered beat, ready for ``NarrationRecord`` persistence.

    :param beat_id: Deterministic id, <= 64 chars (``narration_record`` column).
    :param headline: Rendered headline text.
    :param body: Rendered body text (3 causal sentences).
    :param register: ``NarrationRecord.Register`` value — ``"wire"`` or ``"analysis"``.
    """

    beat_id: str
    headline: str
    body: str
    register: str


def render_frame_beats(frames: Sequence[Mapping[str, Any]]) -> list[CausalBeatSpec]:
    """Render observer frames into beat specs, preserving frame order.

    :param frames: ``CausalChainObserver.latest_frames`` for one tick.
    :returns: One :class:`CausalBeatSpec` per frame.
    :raises ValueError: On a frame pattern this voice has no template for —
        loud failure (Constitution III.11), surfaced by the caller's
        best-effort log, never a silently dropped frame.
    """
    beats: list[CausalBeatSpec] = []
    for frame in frames:
        pattern = frame.get("pattern")
        if pattern == "TICK_PULSE":
            beats.append(_render_pulse(frame))
        elif pattern == "SHOCK_DOCTRINE":
            beats.append(_render_shock(frame))
        else:
            raise ValueError(f"unknown causal frame pattern: {pattern!r}")
    return beats


def _render_pulse(frame: Mapping[str, Any]) -> CausalBeatSpec:
    """Render a TICK_PULSE frame into the per-tick heartbeat beat."""
    tick = int(frame["tick"])
    deltas: Mapping[str, Mapping[str, Any]] = frame["deltas"]
    sentences: list[str] = []
    for metric in _METRIC_ORDER:
        before = float(deltas[metric]["before"])
        after = float(deltas[metric]["after"])
        if after == before:
            sentences.append(_PULSE_HELD[metric].format(after=after))
        else:
            verb = "rose" if after > before else "fell"
            sentences.append(_PULSE_MOVED[metric].format(verb=verb, before=before, after=after))
    return CausalBeatSpec(
        beat_id=f"causal-pulse-t{tick}",
        headline=_PULSE_HEADLINE.format(tick=tick),
        body=" ".join(sentences),
        register="wire",
    )


def _render_shock(frame: Mapping[str, Any]) -> CausalBeatSpec:
    """Render a SHOCK_DOCTRINE frame into the pattern-analysis beat."""
    nodes = {n["type"]: n for n in frame["causal_graph"]["nodes"]}
    shock = nodes["ECONOMIC_SHOCK"]
    austerity = nodes["AUSTERITY_RESPONSE"]
    radical = nodes["RADICALIZATION"]
    crash_tick = int(shock["tick"])
    body = _SHOCK_BODY.format(
        drop=abs(float(shock["data"]["drop_percent"])),
        crash_tick=crash_tick,
        wage_before=float(austerity["data"]["wage_before"]),
        wage_after=float(austerity["data"]["wage_after"]),
        p_before=float(radical["data"]["p_rev_before"]),
        p_after=float(radical["data"]["p_rev_after"]),
    )
    return CausalBeatSpec(
        beat_id=f"causal-shock-t{crash_tick}",
        headline=_SHOCK_HEADLINE,
        body=body,
        register="analysis",
    )
