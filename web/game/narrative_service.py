"""Spec-111: the LLM narrator at the bridge boundary.

Constitution II.5 (AI narrates, never adjudicates) + III.6 (model pinning)
+ III.11 (loud failure — no silent substitution).

Unlike ``game/narrator.py`` (which stays import-pure per Constitution III —
see its module docstring), this module sits AT the bridge boundary and MAY
import ``babylon.*``. It is the upgrade path from the template-based
:class:`~game.narrator.DeterministicNarrator` to the engine-side
``babylon.intelligence.ai.director.NarrativeDirector`` (+ RAG), gated behind the
``BABYLON_LLM_NARRATOR`` feature flag (default OFF).

Design:

* **Flag OFF** (default): :func:`is_enabled` is False, :meth:`NarrativeService.schedule`
  is a no-op, and :meth:`NarrativeService.augment_feed` returns its input
  unchanged. The Wire feed is byte-identical to the pre-spec-111 behavior.
* **Flag ON**: :meth:`NarrativeService.schedule` submits generation to a
  background thread pool so it NEVER blocks the caller (``resolve_tick``
  returns immediately; the narrative "lands" later). Results are cached
  in-process keyed by ``(session_id, tick)`` — no new persistence infra;
  the cache is intentionally ephemeral (process-local, lost on restart).
* **Narrative-only**: generation drives ``NarrativeDirector.on_tick(prev, new)``
  — the engine's existing ``SimulationObserver`` hook (observe, not step).
  This module never calls ``babylon.engine.simulation.step`` and never
  mutates the ``WorldState``/graph it is handed.
* **Loud degradation** (III.11): a failed/timed-out provider call produces a
  :class:`NarrativeResult` with ``degraded=True`` and the exception message —
  never a silently-substituted deterministic string dressed up as an LLM
  narrative. :meth:`NarrativeService.augment_feed` surfaces this explicitly
  under the ``llm_narrative`` key; it never touches the deterministic feed's
  own fields, so the fallback text callers already see is preserved as-is.
* **Model pinning** (III.6): every stored :class:`NarrativeResult` carries
  the ``model_id`` (``LLMConfig.CHAT_MODEL``) and ``prompt_version`` used to
  produce it.

RAG is deliberately NOT wired to a live ``PgVectorStore`` here: constructing
one requires a psycopg connection pool that does not otherwise exist at the
bridge boundary, and building one eagerly for every process would be new
infra beyond this spec's "no new infra" instruction.
``NarrativeService(rag_pipeline=...)`` accepts one for future wiring —
consistent with ``NarrativeDirector``'s own optional, backward-compatible
default of ``None``.
"""

from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from babylon.config.llm_config import LLMConfig
from babylon.intelligence.ai.director import NarrativeDirector
from babylon.intelligence.ai.llm_provider import DeepSeekClient, LLMProvider
from babylon.intelligence.ai.prompt_registry import get_prompt_registry

if TYPE_CHECKING:
    from babylon.intelligence.rag.rag_pipeline import RagPipeline
    from babylon.models.world_state import WorldState

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Feature flag
# --------------------------------------------------------------------------- #

FEATURE_FLAG_ENV = "BABYLON_LLM_NARRATOR"

# The prompt version pinned alongside every stored NarrativeResult
# (Constitution III.6). Auto-derived from the content hash of the narrator
# prompt artifacts (babylon.intelligence.ai.prompt_registry) — manual bumps
# are retired; editing CORPORATE_SYSTEM_PROMPT / LIBERATED_SYSTEM_PROMPT
# (src/babylon/data/game/prompts/narrator/*.txt) changes this automatically.
PROMPT_VERSION = get_prompt_registry().version()

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _env_flag_enabled() -> bool:
    """Read the raw ``BABYLON_LLM_NARRATOR`` environment variable, Django-independent."""
    return os.environ.get(FEATURE_FLAG_ENV, "").strip().lower() in _TRUE_VALUES


def is_enabled() -> bool:
    """Return whether the LLM narrator feature flag is set (default OFF).

    Checks the Django setting ``BABYLON_LLM_NARRATOR`` first (so
    per-environment settings modules are the source of truth); falls back
    to reading the ``BABYLON_LLM_NARRATOR`` environment variable directly
    when Django settings are not configured (e.g. this module imported
    outside the Django app).
    """
    try:
        from django.conf import settings as django_settings

        if django_settings.configured:
            return bool(getattr(django_settings, "BABYLON_LLM_NARRATOR", False))
    except ImportError:  # pragma: no cover — Django always available in web/
        pass
    return _env_flag_enabled()


# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class NarrativeResult:
    """A model-pinned narrative artifact for one resolved tick.

    Attributes:
        tick: The tick this narrative was generated for.
        model_id: The LLM model identifier used (Constitution III.6).
        prompt_version: The pinned prompt version used (Constitution III.6).
        degraded: True if generation failed/timed out — ``corporate``/
            ``liberated`` are then None and ``error`` explains why
            (Constitution III.11 — loud failure, never silent substitution).
        corporate: Generated CORPORATE-voice narrative text, if healthy.
        liberated: Generated LIBERATED-voice narrative text, if healthy.
        error: Exception message, if degraded.
    """

    tick: int
    model_id: str
    prompt_version: str
    degraded: bool
    corporate: str | None = None
    liberated: str | None = None
    error: str | None = None


class _ErrorTrackingLLM:
    """Wraps an LLMProvider, recording (never suppressing) its last failure.

    ``NarrativeDirector._generate_perspective`` already catches provider
    exceptions internally — a single perspective failing logs a warning and
    falls back to template text (``"[CORPORATE] uprising"``) so the rest of
    the tick's narrative isn't lost. That's the right behavior *inside* the
    director. But it means a caller of ``on_tick()`` can't tell a genuine
    LLM narrative from that internal fallback just by looking at the text.

    This wrapper re-raises after recording ``error``, so
    :meth:`NarrativeService._generate` can tell the two cases apart and
    surface an EXPLICIT ``degraded`` marker (Constitution III.11) instead of
    treating the director's silent internal fallback as if it were real
    LLM output.
    """

    def __init__(self, wrapped: LLMProvider) -> None:
        self._wrapped = wrapped
        self.error: str | None = None

    @property
    def name(self) -> str:
        """Provider identifier for logging (delegates to the wrapped provider)."""
        return self._wrapped.name

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Delegate to the wrapped provider; record and re-raise on failure."""
        try:
            return self._wrapped.generate(
                prompt, system_prompt=system_prompt, temperature=temperature
            )
        except Exception as exc:
            self.error = str(exc)
            raise


# --------------------------------------------------------------------------- #
# NarrativeService
# --------------------------------------------------------------------------- #


class NarrativeService:
    """Post-tick, non-blocking LLM narrative generation for the Wire feed.

    Wraps :class:`babylon.intelligence.ai.director.NarrativeDirector`. Generation is
    submitted to a background thread pool so callers (``EngineBridge.resolve_tick``)
    never block on network I/O; results land in an in-process cache read
    lazily by :meth:`augment_feed`.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        rag_pipeline: RagPipeline | None = None,
        max_workers: int = 2,
    ) -> None:
        """Initialize the service.

        Args:
            llm: Optional LLMProvider. If None, a :class:`DeepSeekClient` is
                constructed lazily on first use (reads DEEPSEEK_API_KEY from
                the environment — never read/echoed by this module).
            rag_pipeline: Optional RagPipeline for historical/theoretical
                context retrieval. None disables RAG (matches
                ``NarrativeDirector``'s own backward-compatible default).
            max_workers: Background thread pool size.
        """
        self._llm = llm
        self._rag_pipeline = rag_pipeline
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="narrative-service"
        )
        self._results: dict[tuple[UUID, int], NarrativeResult] = {}
        self._lock = threading.Lock()

    def _resolve_llm(self) -> LLMProvider:
        if self._llm is not None:
            return self._llm
        return DeepSeekClient()

    def schedule(
        self,
        session_id: UUID,
        previous_state: WorldState,
        new_state: WorldState,
    ) -> Future[None] | None:
        """Fire-and-forget: schedule narrative generation for a resolved tick.

        Never raises and never blocks the caller. No-op (returns None)
        when the feature flag is off — this is the hook ``resolve_tick``
        calls; its return value is intentionally discardable so callers
        that don't care about completion (production) and tests that do
        (via the returned Future) both work.

        Args:
            session_id: The game session UUID.
            previous_state: WorldState before the tick (the "observe" input —
                this method never calls ``step()``).
            new_state: WorldState after the tick.

        Returns:
            The submitted Future, or None if the flag is off.
        """
        if not is_enabled():
            return None
        return self._executor.submit(self._generate, session_id, previous_state, new_state)

    def _generate(
        self,
        session_id: UUID,
        previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Run NarrativeDirector.on_tick() and cache the result.

        Runs on a background thread. Any exception from the provider or
        the director is caught here (III.11 loud degradation — surfaced
        via ``NarrativeResult.degraded``/``error``, never re-raised into
        the thread pool where it would vanish silently).
        """
        tick = new_state.tick
        model_id = LLMConfig.CHAT_MODEL
        tracker = _ErrorTrackingLLM(self._resolve_llm())
        try:
            director = NarrativeDirector(
                use_llm=True,
                llm=tracker,
                rag_pipeline=self._rag_pipeline,
            )
            director.on_tick(previous_state, new_state)
            if tracker.error is not None:
                # Provider failed at least once; director swallowed it
                # internally (template fallback), so surface it here instead
                # (III.11 — explicit marker, never a silent substitution).
                raise RuntimeError(tracker.error)
            dual = director.dual_narratives.get(tick)
            # dual is None when this tick had no SIGNIFICANT_EVENT_TYPES —
            # an empty domain, not a failure (III.11): degraded stays False.
            result = NarrativeResult(
                tick=tick,
                model_id=model_id,
                prompt_version=PROMPT_VERSION,
                degraded=False,
                corporate=dual["corporate"] if dual else None,
                liberated=dual["liberated"] if dual else None,
            )
        except Exception as exc:  # noqa: BLE001 — III.11: never crash the pool, degrade loudly
            logger.warning(
                "NarrativeService generation failed session=%s tick=%d: %s",
                session_id,
                tick,
                exc,
            )
            result = NarrativeResult(
                tick=tick,
                model_id=model_id,
                prompt_version=PROMPT_VERSION,
                degraded=True,
                error=str(exc),
            )
        with self._lock:
            self._results[(session_id, tick)] = result

    def get_result(self, session_id: UUID, tick: int) -> NarrativeResult | None:
        """Return the cached NarrativeResult for (session_id, tick), if any.

        None means "not ready yet" (generation still in flight, or never
        scheduled) — distinct from a degraded result, which is a completed
        attempt that failed.
        """
        with self._lock:
            return self._results.get((session_id, tick))

    def augment_feed(self, feed: dict[str, Any], session_id: UUID, tick: int) -> dict[str, Any]:
        """Attach the LLM narrative to a WireFeed dict, additively.

        Never mutates ``feed`` in place; never removes or alters existing
        keys (the deterministic feed IS the loud-failure fallback, so it is
        always left intact). Behavior:

        * Flag OFF → returns ``feed`` unchanged (byte-identical parity).
        * Flag ON, no result cached yet → returns ``feed`` unchanged
          (nothing pending to show; not a failure, just not landed yet).
        * Flag ON, healthy result → adds ``feed["llm_narrative"]`` with
          ``degraded: False`` + the generated text + model pin.
        * Flag ON, degraded result → adds ``feed["llm_narrative"]`` with
          ``degraded: True`` + ``error`` + model pin (III.11 — explicit
          marker, never silently swapped in for the deterministic text).

        Args:
            feed: A WireFeed dict, e.g. from ``DeterministicNarrator.narrate``.
            session_id: The game session UUID.
            tick: The tick this feed's active story is for.

        Returns:
            A new dict — ``feed`` plus (maybe) an ``llm_narrative`` key.
        """
        if not is_enabled():
            return feed
        result = self.get_result(session_id, tick)
        if result is None:
            return feed

        augmented = dict(feed)
        augmented["llm_narrative"] = {
            "degraded": result.degraded,
            "model_id": result.model_id,
            "prompt_version": result.prompt_version,
            "corporate": result.corporate,
            "liberated": result.liberated,
            "error": result.error,
        }
        return augmented


__all__ = [
    "FEATURE_FLAG_ENV",
    "PROMPT_VERSION",
    "NarrativeResult",
    "NarrativeService",
    "is_enabled",
]
