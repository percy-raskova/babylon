"""Frame -> prose entailment eval (G6 / Viable Game spec S7 line 266).

Viable Game spec S7 line 266 contracts a "frame->prose entailment eval (ai
marker)". Before this file, the word "entailment" appeared nowhere in
src/ or tests/: the ``ai`` suite tests narrative *style* (NarrativeCommissar,
``test_judge.py``) and plumbing, never frame-grounding. This is that missing
asset: it drives the REAL :class:`~babylon.engine.observers.causal.CausalChainObserver`
over a real (if minimal) small-scenario tick transition, feeds the resulting
REAL frame's facts through the REAL :class:`~babylon.intelligence.ai.director.NarrativeDirector`
prose-generation path against a LIVE, locally-running Ollama model, and
mechanically asserts **entailment**: prose subseteq frame. Every checkable
factual claim (number, named entity) in the generated prose must trace back
to the frame's data. Style is free; facts are not (Constitution: AI parses/
narrates only, the engine adjudicates the math).

Seam-gap finding (read before touching this file)
--------------------------------------------------
There is NO production code path that threads a
:class:`CausalChainObserver` frame (a plain ``dict`` -- ``TICK_PULSE`` /
``SHOCK_DOCTRINE``) into :class:`NarrativeDirector`. The director's only
public entry point, ``on_tick(previous_state, new_state)``, builds its
prompt exclusively from ``new_state.events`` (typed ``SimulationEvent``
objects) via ``DialecticalPromptBuilder.build_context_block`` -- it has
never seen a causal-chain frame. The frame's only production consumer is
``web/game/causal_voice.py`` (a deterministic, non-LLM template renderer)
plus ``schema_validator.py``. Per the G6 brief, this is reported rather
than silently patched around with a production change: **no src/ file is
touched by this eval.**

The bridge used here (test-only): each scenario constructs a real
:class:`~babylon.models.events.CrisisEvent` (``EventType.ECONOMIC_CRISIS``,
a member of ``NarrativeDirector.SIGNIFICANT_EVENT_TYPES``) whose fields are
DERIVED, by construction, from the exact same pool/wage/p_rev numbers the
:class:`CausalChainObserver` snapshots into its frame -- ``pool_ratio =
pool_after / pool_before``, ``wage_delta = wage_after - wage_before``,
``aggregate_tension = p_rev_after`` (a documented proxy, not an independent
fact). This keeps the WorldState transition internally coherent (as a real
tick from the full 30-system engine would produce: events are computed FROM
state) without inventing a frame in the JSON-dict sense (the frame itself
is never hand-written -- it is what the real, unmodified
``CausalChainObserver._build_frame`` / ``_build_pulse_frame`` computes from
these real ``WorldState`` transitions). The director then runs its REAL,
unmodified ``on_tick`` -> ``build_context_block`` -> ``build_system_prompt``
-> ``LLMProvider.generate`` pipeline, with the LLMProvider being a real,
live Ollama-backed adapter (``_LiveOllamaProvider`` below) -- no mocked LLM
response anywhere in the eval proper.

Model selection
----------------
``src/babylon/config/llm_config.py`` never names a local Ollama CHAT model
-- ``LLMConfig`` only wires ``deepseek``/``workers_ai``/``mock`` for chat;
Ollama is wired ONLY for RAG embeddings (``embeddinggemma:latest``). So
"whichever model the ai-suite/NarrativeDirector config already names" does
not resolve to an Ollama chat model; one had to be picked from the locally
available set (``ollama list``): Qwen3, deepseek-r1:8b,
llama3.2-vision:11b, maobot-nano, mlmlml, marxist-grpo, embeddinggemma,
functiongemma. Empirical elimination (see the report for full transcripts):
``Qwen3`` OOMs on this box (needs 28.5 GiB, 25.5 GiB available);
``maobot-nano`` is fine-tuned into an unrelated "AI liberation from the
cloud" persona that hijacks the Marxist-political-economy framing entirely
(off-topic for this game, rejected despite echoing numbers correctly);
``marxist-grpo`` is on-topic but emits ``<think>...</think>`` reasoning
inline in ``content`` (needs stripping) and is slower (~19s/call).
``mlmlml:latest`` is on-topic, fast (~6-11s/call), and returns clean prose
with no reasoning-tag stripping needed -- selected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pytest
from openai import OpenAI

from babylon.engine.observers.causal import CausalChainObserver
from babylon.intelligence.ai.director import NarrativeDirector
from babylon.intelligence.ai.llm_provider import LLMProvider
from babylon.models import GlobalEconomy, SimulationConfig, SocialClass, SocialRole, WorldState
from babylon.models.entity_registry import PERIPHERY_WORKER_ID
from babylon.models.events import CrisisEvent

# =============================================================================
# Live Ollama model selection (see module docstring for the elimination trail)
# =============================================================================

_OLLAMA_MODEL = "mlmlml:latest"
_OLLAMA_BASE_URL = "http://localhost:11434/v1"
_OLLAMA_TIMEOUT_SECONDS = 120.0

# Fixed static upper bound (repo Power-of-10 rule): a small local model
# occasionally degenerates into echoing the input context block verbatim
# (observed empirically) instead of narrating it. Retrying a bounded number
# of times biases toward substantive prose without an unbounded loop. Even
# an exhausted-retry echo is harmless to the entailment check below (an
# echo's numbers are, by construction, already in the frame) -- this is a
# quality bias, not a correctness requirement.
_MAX_GENERATION_ATTEMPTS = 3
_DEGENERATE_ECHO_MARKERS = (
    "MATERIAL CONDITIONS",
    "RECENT EVENTS",
    "HISTORICAL & THEORETICAL CONTEXT",
)


class _LiveOllamaProvider:
    """Test-only :class:`LLMProvider` (Protocol-conforming) for a live,
    locally-running Ollama daemon via its OpenAI-compatible endpoint.

    Not production code: ``babylon.intelligence.ai.llm_provider`` only
    wires ``DeepSeekClient`` / ``WorkersAIClient`` / ``MockLLM`` -- there is
    no Ollama chat provider in ``src/`` (see module docstring). This eval
    needs a REAL, live model call, so it speaks to Ollama directly, mirroring
    ``DeepSeekClient``'s ``OpenAI(api_key=..., base_url=...)`` construction
    pattern (Ollama's OpenAI-compatible endpoint ignores the API key).
    """

    def __init__(self, model: str = _OLLAMA_MODEL, base_url: str = _OLLAMA_BASE_URL) -> None:
        self._model = model
        self._client = OpenAI(
            api_key="ollama-local", base_url=base_url, timeout=_OLLAMA_TIMEOUT_SECONDS
        )

    @property
    def name(self) -> str:
        """Provider identifier for logging."""
        return f"ollama:{self._model}"

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text synchronously via live Ollama (bounded content-retry)."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_text = ""
        for _attempt in range(_MAX_GENERATION_ATTEMPTS):
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
            )
            content = response.choices[0].message.content
            if not content:
                continue
            last_text = content
            if not any(marker in content for marker in _DEGENERATE_ECHO_MARKERS):
                return content
        return last_text


# =============================================================================
# Mechanical entailment core (pure, deterministic -- TDD'd first)
# =============================================================================

# Only decimal-point or percent-suffixed tokens are treated as "quantities."
# Bare integers (tick numbers, ordinals, list markers, narrative flourishes
# like "a three-tick pattern") are deliberately EXCLUDED from strict
# grounding: every real quantity in this domain (pool, wage, p_revolution,
# their ratios/deltas) is formatted with a decimal point or a percent sign
# throughout the codebase (see DialecticalPromptBuilder._format_event and
# CausalChainObserver._build_frame) -- requiring a decimal/percent targets
# exactly the axis "no invented numbers" cares about, without flagging
# ordinary English numbering as a fabrication.
_NUMBER_RE = re.compile(r"-?\d+\.\d+%?|-?\d+%")

# 2+ consecutive Title-Case words (e.g. "Federal Reserve", "Rothschild
# Consortium"): a precise, low-false-positive proxy for "named institution
# not present in our facts." Deliberately does NOT match single
# thematic-vocabulary words (Proletariat, Bourgeoisie) or ALL-CAPS economic
# jargon (GDP, IMF) -- those produce too many false positives for a
# regex-only check and are not what this eval targets (see report concerns).
_MULTIWORD_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")

# Sentence-initial capitalized function words the regex above will greedily
# absorb into a match ("The Rothschild Consortium", "The Proletariat").
# Stripped from the LEADING edge of a candidate before whitelist/reporting
# so a lone capitalized common word ("The Proletariat" -> "Proletariat")
# correctly falls back to "single thematic word, not flagged."
_LEADING_STOPWORDS = frozenset(
    {"The", "A", "An", "This", "That", "These", "Those", "In", "On", "At", "As", "It", "Its"}
)

# Phrases drawn from the CONTEXT BLOCK's own vocabulary (section headers,
# the event's own type name) that a faithful narration may legitimately
# echo. These are NOT part of the narrower CausalChainObserver frame's JSON
# schema (which only has pool/wage/p_rev), but they ARE part of what the
# director's real context_block gives the model -- echoing them is not
# invention, it is quotation of the real input.
_STYLE_PHRASE_WHITELIST = frozenset(
    {
        "Global Tension",
        "Material Conditions",
        "Historical Context",
        "Theoretical Context",
        "Economic Crisis",
        "Recent Events",
    }
)

# Scale-aware tolerance: an absolute floor (handles raw ratio-scale [0, 1]
# rounding, e.g. 0.6667 -> "0.67") PLUS a relative component (handles
# percent-scale [0, 100] rounding, e.g. 66.6667 -> "67%", a 0.33 absolute
# gap the flat floor alone would reject). Real false positive hit during
# this eval's development: a faithfully echoed "67%" (from pool_ratio =
# 200/300 = 0.6667) was flagged ungrounded under a flat 0.02 tolerance --
# fixed by scaling the allowance with the ground-truth value's own
# magnitude, so ratio-scale and percent-scale surface forms of the SAME
# underlying quantity are both covered without tracking which form a
# given prose token used.
_NUMERIC_ABS_TOLERANCE = 0.02
_NUMERIC_REL_TOLERANCE = 0.01


@dataclass(frozen=True)
class EntailmentViolation:
    """A single fact in the prose that does not trace to the frame's data."""

    kind: str  # "number" | "entity"
    claim: str


def _tick_pulse_quantities(frame: dict[str, object]) -> dict[str, float]:
    """Named quantities derivable from a real TICK_PULSE frame."""
    deltas = frame["deltas"]  # type: ignore[index]
    pool = deltas["pool"]  # type: ignore[index]
    wage = deltas["wage"]  # type: ignore[index]
    p_rev = deltas["p_rev"]  # type: ignore[index]
    pool_before, pool_after = float(pool["before"]), float(pool["after"])
    wage_before, wage_after = float(wage["before"]), float(wage["after"])
    p_rev_before, p_rev_after = float(p_rev["before"]), float(p_rev["after"])
    return {
        "tick": float(frame["tick"]),  # type: ignore[arg-type]
        "pool_before": pool_before,
        "pool_after": pool_after,
        "pool_delta": pool_after - pool_before,
        "pool_ratio": (pool_after / pool_before) if pool_before else 0.0,
        "wage_before": wage_before,
        "wage_after": wage_after,
        "wage_delta": wage_after - wage_before,
        "p_rev_before": p_rev_before,
        "p_rev_after": p_rev_after,
        "p_rev_delta": p_rev_after - p_rev_before,
    }


def _shock_doctrine_quantities(frame: dict[str, object]) -> dict[str, float]:
    """Named quantities derivable from a real SHOCK_DOCTRINE frame.

    Includes ``pool_ratio`` (``pool_after / pool_before``): this is the
    exact quantity the bridging ``CrisisEvent.pool_ratio`` carries (see
    ``_run_shock_doctrine_scenario``), and ``DialecticalPromptBuilder.
    _format_event`` renders it into the context block as e.g. "Pool ratio
    at 0.67 (67%)" -- omitting it here previously caused a real false
    positive: a faithfully-echoed "0.67" was flagged as ungrounded because
    only the raw pool_before/pool_after were in the allowed-number set, not
    their ratio.
    """
    causal_graph = frame["causal_graph"]  # type: ignore[index]
    nodes = {n["type"]: n for n in causal_graph["nodes"]}  # type: ignore[index]
    shock_data = nodes["ECONOMIC_SHOCK"]["data"]
    austerity_data = nodes["AUSTERITY_RESPONSE"]["data"]
    radical_data = nodes["RADICALIZATION"]["data"]
    pool_before, pool_after = float(shock_data["pool_before"]), float(shock_data["pool_after"])
    wage_before, wage_after = (
        float(austerity_data["wage_before"]),
        float(austerity_data["wage_after"]),
    )
    p_rev_before, p_rev_after = (
        float(radical_data["p_rev_before"]),
        float(radical_data["p_rev_after"]),
    )
    return {
        "shock_tick": float(nodes["ECONOMIC_SHOCK"]["tick"]),
        "austerity_tick": float(nodes["AUSTERITY_RESPONSE"]["tick"]),
        "radical_tick": float(nodes["RADICALIZATION"]["tick"]),
        "pool_before": pool_before,
        "pool_after": pool_after,
        "pool_ratio": (pool_after / pool_before) if pool_before else 0.0,
        "drop_percent": float(shock_data["drop_percent"]),
        "wage_before": wage_before,
        "wage_after": wage_after,
        "wage_delta": wage_after - wage_before,
        "p_rev_before": p_rev_before,
        "p_rev_after": p_rev_after,
        "p_rev_delta": p_rev_after - p_rev_before,
    }


def frame_quantities(frame: dict[str, object]) -> dict[str, float]:
    """Dispatch to the pattern-specific quantity extractor.

    :raises ValueError: if ``frame["pattern"]`` is not a recognized
        CausalChainObserver pattern.
    """
    pattern = frame.get("pattern")
    if pattern == "TICK_PULSE":
        return _tick_pulse_quantities(frame)
    if pattern == "SHOCK_DOCTRINE":
        return _shock_doctrine_quantities(frame)
    raise ValueError(f"unknown causal frame pattern: {pattern!r}")


def _allowed_numbers(quantities: dict[str, float]) -> set[float]:
    """Surface-form-tolerant ground truth: raw, *100, and /100 variants.

    An LLM may render the same fact as a raw ratio (``0.70``), a percentage
    (``70%``), or (rarely) a permille-like fraction -- generating all three
    scaled forms up front means a single float-equality-with-tolerance check
    at extraction time handles the phrasing variance the brief asks for,
    without needing to know in advance which surface form the model chose.
    """
    allowed: set[float] = set()
    for value in quantities.values():
        allowed.add(round(value, 6))
        allowed.add(round(value * 100, 6))
        allowed.add(round(value / 100, 6))
    return allowed


def extract_numeric_claims(prose: str) -> list[float]:
    """Extract checkable numeric tokens (decimal or percent) from prose."""
    claims: list[float] = []
    for match in _NUMBER_RE.finditer(prose):
        token = match.group(0)
        claims.append(float(token.rstrip("%")))
    return claims


def extract_entity_claims(prose: str) -> list[str]:
    """Extract checkable named-entity-like tokens from prose.

    Strips leading sentence-initial function words ("The", "A", ...) that
    the regex greedily absorbs, then discards anything that collapses to a
    single word (ordinary capitalized vocabulary, not a named institution),
    matches the style-phrase whitelist, or is immediately followed by a
    colon (a markdown/structural section-header label -- e.g.
    ``**Event Analysis:**``, ``*   **Next Steps:**`` -- which local models
    commonly emit to structure a response; a formatting label is not a
    factual claim about a named institution, empirically observed in real
    live-Ollama output during this eval's development).
    """
    claims: list[str] = []
    for match in _MULTIWORD_PROPER_NOUN_RE.finditer(prose):
        tail = prose[match.end() : match.end() + 4].lstrip("*")
        if tail.startswith(":"):
            continue
        words = match.group(0).split()
        while words and words[0] in _LEADING_STOPWORDS:
            words.pop(0)
        if len(words) < 2:
            continue
        candidate = " ".join(words)
        if candidate not in _STYLE_PHRASE_WHITELIST:
            claims.append(candidate)
    return claims


def _claim_is_grounded(claim: float, allowed: set[float]) -> bool:
    for allowed_value in allowed:
        tolerance = max(_NUMERIC_ABS_TOLERANCE, abs(allowed_value) * _NUMERIC_REL_TOLERANCE)
        if abs(claim - allowed_value) <= tolerance:
            return True
    return False


def check_entailment(prose: str, frame: dict[str, object]) -> list[EntailmentViolation]:
    """Return every factual claim in ``prose`` that does not trace to ``frame``.

    An empty result means the prose entails the frame (prose subseteq frame):
    every checkable number and named entity mentioned is grounded in the
    frame's own data (or its documented derived forms / style vocabulary).

    :param prose: Generated (or hand-constructed) narrative text.
    :param frame: A real ``CausalChainObserver`` frame dict (``TICK_PULSE``
        or ``SHOCK_DOCTRINE`` shape).
    :returns: List of violations; empty if the prose is fully entailed.
    """
    quantities = frame_quantities(frame)
    allowed = _allowed_numbers(quantities)

    violations: list[EntailmentViolation] = []
    for claim in extract_numeric_claims(prose):
        if not _claim_is_grounded(claim, allowed):
            violations.append(EntailmentViolation(kind="number", claim=str(claim)))
    for entity in extract_entity_claims(prose):
        violations.append(EntailmentViolation(kind="entity", claim=entity))
    return violations


# =============================================================================
# Real small-scenario tick-run builders (drive the REAL observer + director)
# =============================================================================


def _build_state(
    tick: int,
    pool: float,
    wage: float,
    p_rev: float,
    events: tuple[CrisisEvent, ...] = (),
) -> WorldState:
    """A real, minimal (but valid) WorldState -- same construction shape as
    ``tests/unit/engine/observers/test_causal_chain.py::create_state``, the
    house pattern for testing this exact observer.
    """
    economy = GlobalEconomy(imperial_rent_pool=pool, current_super_wage_rate=wage)
    entity = SocialClass(
        id=PERIPHERY_WORKER_ID,
        name="Proletariat",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        p_revolution=p_rev,
    )
    return WorldState(
        tick=tick,
        economy=economy,
        entities={PERIPHERY_WORKER_ID: entity},
        events=list(events),
    )


def _run_tick_pulse_scenario(
    *,
    pool_before: float,
    pool_after: float,
    wage_before: float,
    wage_after: float,
    p_rev_before: float,
    p_rev_after: float,
    tick: int,
) -> tuple[dict[str, object], str]:
    """Drive the REAL CausalChainObserver + REAL NarrativeDirector (live
    Ollama) over a real 2-tick transition. Returns the observer's real
    TICK_PULSE frame and the director's real generated prose.
    """
    state_before = _build_state(tick - 1, pool_before, wage_before, p_rev_before)
    crisis_event = CrisisEvent(
        tick=tick,
        pool_ratio=round(pool_after / pool_before, 4),
        aggregate_tension=p_rev_after,
        decision="AUSTERITY" if wage_after < wage_before else "STABLE",
        wage_delta=round(wage_after - wage_before, 4),
    )
    state_after = _build_state(tick, pool_after, wage_after, p_rev_after, events=(crisis_event,))

    observer = CausalChainObserver()
    observer.on_simulation_start(state_before, SimulationConfig())
    observer.on_tick(state_before, state_after)
    frame = next(f for f in observer.latest_frames if f["pattern"] == "TICK_PULSE")

    director = NarrativeDirector(use_llm=True, llm=_LiveOllamaProvider())
    director.on_simulation_start(state_before, SimulationConfig())
    director.on_tick(state_before, state_after)
    assert director.narrative_log, (
        "director produced no prose for the tick (significant-event gate?)"
    )
    return frame, director.narrative_log[-1]


def _run_shock_doctrine_scenario(
    *,
    pool_before: float,
    pool_after: float,
    wage_before: float,
    wage_after: float,
    p_rev_before: float,
    p_rev_after: float,
    crash_tick: int,
) -> tuple[dict[str, object], str]:
    """Drive the REAL CausalChainObserver + REAL NarrativeDirector (live
    Ollama) over a real 3-tick Shock Doctrine transition. Returns the
    observer's real SHOCK_DOCTRINE frame and the director's real generated
    prose for the radicalization tick.
    """
    austerity_tick = crash_tick + 1
    radical_tick = crash_tick + 2

    state_pre = _build_state(crash_tick, pool_before, wage_before, p_rev_before)
    state_crash = _build_state(austerity_tick, pool_after, wage_before, p_rev_before)
    crisis_event = CrisisEvent(
        tick=radical_tick,
        pool_ratio=round(pool_after / pool_before, 4),
        aggregate_tension=p_rev_after,
        decision="AUSTERITY",
        wage_delta=round(wage_after - wage_before, 4),
    )
    state_radical = _build_state(
        radical_tick, pool_after, wage_after, p_rev_after, events=(crisis_event,)
    )

    observer = CausalChainObserver()
    observer.on_simulation_start(state_pre, SimulationConfig())
    observer.on_tick(state_pre, state_crash)
    observer.on_tick(state_crash, state_radical)
    frame = next(f for f in observer.latest_frames if f["pattern"] == "SHOCK_DOCTRINE")

    director = NarrativeDirector(use_llm=True, llm=_LiveOllamaProvider())
    director.on_simulation_start(state_pre, SimulationConfig())
    director.on_tick(state_pre, state_crash)
    director.on_tick(state_crash, state_radical)
    assert director.narrative_log, "director produced no prose for the radicalization tick"
    return frame, director.narrative_log[-1]


# =============================================================================
# TEST: LLMProvider protocol compliance (cheap, no network)
# =============================================================================


@pytest.mark.unit
class TestLiveOllamaProviderProtocol:
    def test_satisfies_llm_provider_protocol(self) -> None:
        assert isinstance(_LiveOllamaProvider(), LLMProvider)


# =============================================================================
# TEST: mechanical entailment helper (pure, hand-crafted -- TDD red-first)
# =============================================================================


@pytest.mark.unit
class TestNumericEntailmentHelper:
    """No LLM, no observer, no director: pure function tests for the
    mechanical core, using hand-crafted (not LLM-generated) frame + prose
    pairs -- exactly the "mocked-response unit test for the extraction
    helper" the brief calls for."""

    _TICK_PULSE_FRAME: dict[str, object] = {
        "pattern": "TICK_PULSE",
        "tick": 12,
        "deltas": {
            "pool": {"before": 100.0, "after": 70.0},
            "wage": {"before": 0.20, "after": 0.20},
            "p_rev": {"before": 0.30, "after": 0.45},
        },
    }

    def test_prose_with_only_grounded_numbers_has_no_violations(self) -> None:
        prose = (
            "The imperial rent pool fell from 100.00 to 70.00. "
            "The super-wage rate held at 0.2000. "
            "Peak revolutionary probability rose from 0.300 to 0.450, a 70% ratio."
        )
        assert check_entailment(prose, self._TICK_PULSE_FRAME) == []

    def test_paraphrased_prose_with_no_numbers_has_no_violations(self) -> None:
        """Style freedom: a prose that names no quantities at all trivially
        entails the frame (there is nothing ungrounded to claim)."""
        prose = "The pool contracted sharply while revolutionary sentiment climbed."
        assert check_entailment(prose, self._TICK_PULSE_FRAME) == []

    def test_fabricated_number_is_flagged(self) -> None:
        prose = "The pool ultimately stabilized at 312.47 units after the shock."
        violations = check_entailment(prose, self._TICK_PULSE_FRAME)
        assert violations == [EntailmentViolation(kind="number", claim="312.47")]

    def test_percent_form_of_a_grounded_ratio_is_not_flagged(self) -> None:
        prose = "The pool now sits at 70% of its prior level."
        assert check_entailment(prose, self._TICK_PULSE_FRAME) == []

    def test_unknown_pattern_is_loud(self) -> None:
        with pytest.raises(ValueError, match="unknown causal frame pattern"):
            check_entailment("anything", {"pattern": "NOT_A_PATTERN"})

    def test_shock_doctrine_pool_ratio_percent_is_not_flagged(self) -> None:
        """Regression test for a real false positive hit during this eval's
        development against live Ollama: a real generation faithfully
        echoed the pool ratio ("a pool ratio of 0.67") that
        DialecticalPromptBuilder._format_event renders from the bridging
        CrisisEvent -- but ``_shock_doctrine_quantities`` originally derived
        only pool_before/pool_after, never their ratio, so the faithfully
        echoed number had no matching ground truth. Fixed by deriving
        ``pool_ratio`` alongside the other SHOCK_DOCTRINE quantities."""
        shock_frame: dict[str, object] = {
            "pattern": "SHOCK_DOCTRINE",
            "causal_graph": {
                "nodes": [
                    {
                        "id": "shock_t20",
                        "type": "ECONOMIC_SHOCK",
                        "tick": 20,
                        "data": {"pool_before": 300.0, "pool_after": 200.0, "drop_percent": -33.3},
                    },
                    {
                        "id": "austerity_t21",
                        "type": "AUSTERITY_RESPONSE",
                        "tick": 21,
                        "data": {"wage_before": 0.3, "wage_after": 0.1},
                    },
                    {
                        "id": "radical_t22",
                        "type": "RADICALIZATION",
                        "tick": 22,
                        "data": {"p_rev_before": 0.1, "p_rev_after": 0.6},
                    },
                ],
                "edges": [],
            },
        }
        prose = "The economic crisis shows a pool ratio of 0.67, a 67% level, after austerity."
        assert check_entailment(prose, shock_frame) == []


@pytest.mark.unit
class TestEntityEntailmentHelper:
    _SHOCK_FRAME: dict[str, object] = {
        "pattern": "SHOCK_DOCTRINE",
        "causal_graph": {
            "nodes": [
                {
                    "id": "shock_t10",
                    "type": "ECONOMIC_SHOCK",
                    "tick": 10,
                    "data": {"pool_before": 100.0, "pool_after": 70.0, "drop_percent": -30.0},
                },
                {
                    "id": "austerity_t11",
                    "type": "AUSTERITY_RESPONSE",
                    "tick": 11,
                    "data": {"wage_before": 0.20, "wage_after": 0.15},
                },
                {
                    "id": "radical_t12",
                    "type": "RADICALIZATION",
                    "tick": 12,
                    "data": {"p_rev_before": 0.30, "p_rev_after": 0.45},
                },
            ],
            "edges": [
                {"source": "shock_t10", "target": "austerity_t11", "relation": "TRIGGERS_REACTION"},
                {
                    "source": "austerity_t11",
                    "target": "radical_t12",
                    "relation": "CAUSES_RADICALIZATION",
                },
            ],
        },
    }

    def test_fabricated_entity_is_flagged(self) -> None:
        prose = "The Rothschild Consortium intervened to stabilize the pool at 70.00."
        violations = check_entailment(prose, self._SHOCK_FRAME)
        assert EntailmentViolation(kind="entity", claim="Rothschild Consortium") in violations

    def test_style_phrase_whitelist_is_not_flagged(self) -> None:
        prose = "The Economic Crisis deepened; Global Tension remained low even as the pool crashed 30.0%."
        assert check_entailment(prose, self._SHOCK_FRAME) == []

    def test_single_thematic_words_are_not_flagged(self) -> None:
        """Proletariat/Bourgeoisie etc. are single capitalized words -- the
        entity check only fires on 2+-word proper-noun-like sequences, so
        ordinary Marxist-theory vocabulary is never mistaken for an invented
        named institution."""
        prose = "The Proletariat responded as the Bourgeoisie enacted austerity."
        assert check_entailment(prose, self._SHOCK_FRAME) == []

    def test_markdown_section_headers_are_not_flagged(self) -> None:
        """Regression test for a real false positive hit during this eval's
        development against live Ollama (mlmlml): a real generation
        structured its answer with bold markdown section headers
        ("**Event Analysis:**", "*   **Next Steps:**"). These are
        formatting labels, not claims about named institutions -- the
        colon-lookahead check must exclude them."""
        prose = (
            "**Event Analysis:**\n\nThe pool crashed 30.0%.\n\n"
            "*   **Next Steps:** The proletariat organizes."
        )
        assert check_entailment(prose, self._SHOCK_FRAME) == []


# =============================================================================
# TEST: real observer + real director + live Ollama (ai-marked; slow)
# =============================================================================

# Module-scoped fixtures: each live scenario calls Ollama exactly ONCE,
# single-flight (no xdist), and its (frame, prose) pair is reused by every
# assertion that needs it -- including the negative-control corruption test,
# which reuses pulse_scenario_a's real prose rather than issuing a fresh call.


@pytest.fixture(scope="module")
def shock_scenario_a() -> tuple[dict[str, object], str]:
    return _run_shock_doctrine_scenario(
        pool_before=100.0,
        pool_after=70.0,
        wage_before=0.20,
        wage_after=0.15,
        p_rev_before=0.30,
        p_rev_after=0.45,
        crash_tick=10,
    )


@pytest.fixture(scope="module")
def shock_scenario_b() -> tuple[dict[str, object], str]:
    return _run_shock_doctrine_scenario(
        pool_before=300.0,
        pool_after=200.0,
        wage_before=0.30,
        wage_after=0.10,
        p_rev_before=0.10,
        p_rev_after=0.60,
        crash_tick=20,
    )


@pytest.fixture(scope="module")
def pulse_scenario_a() -> tuple[dict[str, object], str]:
    return _run_tick_pulse_scenario(
        pool_before=200.0,
        pool_after=190.0,
        wage_before=0.25,
        wage_after=0.25,
        p_rev_before=0.20,
        p_rev_after=0.22,
        tick=1,
    )


@pytest.fixture(scope="module")
def pulse_scenario_b() -> tuple[dict[str, object], str]:
    return _run_tick_pulse_scenario(
        pool_before=50.0,
        pool_after=48.0,
        wage_before=0.10,
        wage_after=0.12,
        p_rev_before=0.40,
        p_rev_after=0.38,
        tick=1,
    )


@pytest.mark.ai
class TestLiveShockDoctrineEntailment:
    def test_shock_scenario_a_prose_entails_frame(
        self, shock_scenario_a: tuple[dict[str, object], str]
    ) -> None:
        frame, prose = shock_scenario_a
        assert frame["pattern"] == "SHOCK_DOCTRINE"
        violations = check_entailment(prose, frame)
        assert violations == [], f"ungrounded facts: {violations}\n--- prose ---\n{prose}"

    def test_shock_scenario_b_prose_entails_frame(
        self, shock_scenario_b: tuple[dict[str, object], str]
    ) -> None:
        frame, prose = shock_scenario_b
        assert frame["pattern"] == "SHOCK_DOCTRINE"
        violations = check_entailment(prose, frame)
        assert violations == [], f"ungrounded facts: {violations}\n--- prose ---\n{prose}"


@pytest.mark.ai
class TestLiveTickPulseEntailment:
    def test_pulse_scenario_a_prose_entails_frame(
        self, pulse_scenario_a: tuple[dict[str, object], str]
    ) -> None:
        frame, prose = pulse_scenario_a
        assert frame["pattern"] == "TICK_PULSE"
        violations = check_entailment(prose, frame)
        assert violations == [], f"ungrounded facts: {violations}\n--- prose ---\n{prose}"

    def test_pulse_scenario_b_prose_entails_frame(
        self, pulse_scenario_b: tuple[dict[str, object], str]
    ) -> None:
        frame, prose = pulse_scenario_b
        assert frame["pattern"] == "TICK_PULSE"
        violations = check_entailment(prose, frame)
        assert violations == [], f"ungrounded facts: {violations}\n--- prose ---\n{prose}"


@pytest.mark.ai
class TestNegativeControlOnRealProse:
    """The mutation-validation of the eval itself: take REAL, live-generated
    prose (known-good, asserted clean above) and deliberately corrupt it
    with a fabricated number and a fabricated named entity. This MUST fail
    -- if it doesn't, the entailment check is not actually checking
    anything."""

    def test_corrupted_real_prose_fails_entailment(
        self, pulse_scenario_a: tuple[dict[str, object], str]
    ) -> None:
        frame, prose = pulse_scenario_a
        corrupted = (
            prose
            + " The Halliburton Solidarity Bureau intervened, "
            + "stabilizing the pool at 941.23 units."
        )
        violations = check_entailment(corrupted, frame)
        assert any(v.kind == "number" for v in violations), violations
        assert any(v.kind == "entity" for v in violations), violations
