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

#: G4 (Finding 2, adversarial review): ``imperial_rent_pool`` is a Tier-1
#: value-axis field (``game.veil.TIER1_VALUE_RELATION_FIELDS``) — naming its
#: real before/after numbers (or even just its direction of travel) in prose
#: is the same class of leak as the numbers themselves. Below Tier 1 this
#: ONE placeholder replaces the "pool" sentence regardless of moved/held —
#: the same fixed-veiled-phrasing precedent as
#: ``_VEILED_APOLOGIST_REFUTATION`` (``engine_bridge.py``). "wage"/"p_rev"
#: are never gated (money-form / political axis per veil.py's registry), so
#: they keep their real per-tick sentences at every tier.
_PULSE_POOL_VEILED: str = (
    "Your cadre cannot yet see through the money-form — study Doctrine to "
    "reveal the imperial rent pool's movement."
)

_SHOCK_HEADLINE: str = "Shock, austerity, radicalization — the causal chain closed."

#: Split from the former single ``_SHOCK_BODY`` so the pool-crash clause
#: (the ONLY value-axis relation in this frame — a percentage drop of
#: ``imperial_rent_pool``) can be veiled independently of the wage/p_rev
#: aftermath clause, which stays real at every tier (G4 Finding 2).
_SHOCK_POOL_SENTENCE: str = "The rent pool crashed {drop:.1f}% at tick {crash_tick}."
_SHOCK_POOL_SENTENCE_VEILED: str = (
    "Your cadre cannot yet see through the money-form — study Doctrine to "
    "reveal the rent pool's crash at tick {crash_tick}."
)
_SHOCK_AFTERMATH_SENTENCE: str = (
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
            _PULSE_POOL_VEILED,
            _SHOCK_HEADLINE,
            _SHOCK_POOL_SENTENCE,
            _SHOCK_POOL_SENTENCE_VEILED,
            _SHOCK_AFTERMATH_SENTENCE,
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


def render_frame_beats(
    frames: Sequence[Mapping[str, Any]], *, veil_tier: int = 2
) -> list[CausalBeatSpec]:
    """Render observer frames into beat specs, preserving frame order.

    :param frames: ``CausalChainObserver.latest_frames`` for one tick.
    :param veil_tier: G4 (Finding 2, adversarial review): the requesting
        player org's Veil-of-Money tier (``game.veil.compute_veil_tier``).
        Defaults to ``2`` (fully unlocked) so every pre-G4 direct call
        site (every test in this suite bar the veil-gate ones) stays
        byte-identical — the real player-facing caller
        (``EngineBridge._persist_causal_beats_safe``) always supplies the
        session's real tier. Below Tier 1, the "pool" (imperial_rent_pool)
        sentence in both patterns is replaced with a fixed veiled
        placeholder — see :data:`_PULSE_POOL_VEILED`/
        :data:`_SHOCK_POOL_SENTENCE_VEILED`.
    :returns: One :class:`CausalBeatSpec` per frame.
    :raises ValueError: On a frame pattern this voice has no template for —
        loud failure (Constitution III.11), surfaced by the caller's
        best-effort log, never a silently dropped frame.
    """
    beats: list[CausalBeatSpec] = []
    for frame in frames:
        pattern = frame.get("pattern")
        if pattern == "TICK_PULSE":
            beats.append(_render_pulse(frame, veil_tier))
        elif pattern == "SHOCK_DOCTRINE":
            beats.append(_render_shock(frame, veil_tier))
        else:
            raise ValueError(f"unknown causal frame pattern: {pattern!r}")
    return beats


def _render_pulse(frame: Mapping[str, Any], veil_tier: int) -> CausalBeatSpec:
    """Render a TICK_PULSE frame into the per-tick heartbeat beat."""
    tick = int(frame["tick"])
    deltas: Mapping[str, Mapping[str, Any]] = frame["deltas"]
    sentences: list[str] = []
    for metric in _METRIC_ORDER:
        if metric == "pool" and veil_tier < 1:
            sentences.append(_PULSE_POOL_VEILED)
            continue
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


def _render_shock(frame: Mapping[str, Any], veil_tier: int) -> CausalBeatSpec:
    """Render a SHOCK_DOCTRINE frame into the pattern-analysis beat."""
    nodes = {n["type"]: n for n in frame["causal_graph"]["nodes"]}
    shock = nodes["ECONOMIC_SHOCK"]
    austerity = nodes["AUSTERITY_RESPONSE"]
    radical = nodes["RADICALIZATION"]
    crash_tick = int(shock["tick"])
    if veil_tier < 1:
        pool_sentence = _SHOCK_POOL_SENTENCE_VEILED.format(crash_tick=crash_tick)
    else:
        pool_sentence = _SHOCK_POOL_SENTENCE.format(
            drop=abs(float(shock["data"]["drop_percent"])), crash_tick=crash_tick
        )
    aftermath_sentence = _SHOCK_AFTERMATH_SENTENCE.format(
        wage_before=float(austerity["data"]["wage_before"]),
        wage_after=float(austerity["data"]["wage_after"]),
        p_before=float(radical["data"]["p_rev_before"]),
        p_after=float(radical["data"]["p_rev_after"]),
    )
    return CausalBeatSpec(
        beat_id=f"causal-shock-t{crash_tick}",
        headline=_SHOCK_HEADLINE,
        body=f"{pool_sentence} {aftermath_sentence}",
        register="analysis",
    )
