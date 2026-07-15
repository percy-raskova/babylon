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
  in-process keyed by ``(session_id, tick)`` for fast reads by
  :meth:`augment_feed`. Since program-20 Track B (task B4), completed
  generations are ALSO durably written to ``game.models.NarrationRecord``
  (see :meth:`NarrativeService._persist`) so narrator beats survive a
  process restart — the in-process cache stays as-is; persistence is
  additive, not a replacement.
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
from babylon.intelligence.ai.llm_provider import LLMProvider, build_llm_provider
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
#
# STARTUP COUPLING (deliberate, III.11): this module-level read means Django
# app boot — via EngineBridge.__init__ -> NarrativeService() -> this import —
# now depends on the prompt/archetype artifacts being present and valid,
# REGARDLESS of the feature flag. A missing/malformed artifact fails the whole
# app loudly at startup rather than silently at first narration. The artifacts
# are committed and pinned by tests (test_prompt_registry, test_event_archetypes).
PROMPT_VERSION = get_prompt_registry().version()

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})

# NarrationRecord.headline's list-view budget (Constitution/task-B4 brief).
_HEADLINE_MAX_CHARS = 120


def _split_headline_body(text: str, tick: int) -> tuple[str, str]:
    """Derive a ``(headline, body)`` pair from one generated narrative's text.

    Multi-line text: the headline is the first line (truncated to
    ``_HEADLINE_MAX_CHARS``), and the body is everything after it.
    Single-line text has no natural headline/body split, so the body
    becomes the full text and the headline falls back to a generic
    ``"Tick {tick}"`` marker — rather than truncating the one line twice
    (once for the headline, once implicitly for the body) or duplicating
    it in both fields.
    """
    if "\n" in text:
        first_line, rest = text.split("\n", 1)
        return first_line[:_HEADLINE_MAX_CHARS], rest
    return f"Tick {tick}", text


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
            llm: Optional LLMProvider. If None, a provider is constructed
                lazily on first use via
                :func:`babylon.intelligence.ai.llm_provider.build_llm_provider`
                (selects on ``LLMConfig.PROVIDER``; reads its credentials
                from the environment — never read/echoed by this module).
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
        return build_llm_provider()

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
        """Run NarrativeDirector.on_tick(), persist, and cache the result.

        Runs on a background thread. Any exception from the provider or
        the director is caught here (III.11 loud degradation — surfaced
        via ``NarrativeResult.degraded``/``error``, never re-raised into
        the thread pool where it would vanish silently).

        Persistence (:meth:`_persist`, task B4) is called INSIDE the try
        block for the success path deliberately: a caller-supplied
        ``session_id`` with no backing ``GameSession`` row is a real bug
        (the session was never created, or was deleted out from under an
        in-flight generation), not something to skip with a quiet log
        line. Letting ``GameSession.DoesNotExist`` propagate here reuses
        the SAME ``except Exception`` handler immediately below —
        already-tested machinery for provider failures — so a missing
        session turns an otherwise-successful generation into an explicit
        ``degraded`` result (III.11: you can generate all the text you
        want, but if it can't be durably recorded, the tick's narration
        didn't really complete).

        The degraded branch persists its own (single, visible) record
        too. If THAT persist attempt also fails — e.g. the session is
        ALSO missing when generation itself already failed — there is
        nowhere further to escalate to without breaking the
        "``schedule()`` never raises" contract the thread pool relies on,
        so it is logged at ERROR (distinct from the WARNING already
        logged for the generation failure) and swallowed rather than
        re-raised. Consequence for ``NarrationRecord`` readers: a
        ``degraded=True`` in-memory :class:`NarrativeResult` (and hence a
        ``degraded: true`` marker in ``augment_feed``'s output) does NOT
        guarantee a corresponding persisted row exists — on this
        double-failure path the durability failure is visible only in
        ERROR logs today, so "no NarrationRecord for (session, tick)"
        can mean quiet-tick OR failed-persist, distinguishable only via
        the log stream.
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
            self._persist(result, session_id, tick)
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
            try:
                self._persist(result, session_id, tick)
            except Exception as persist_exc:  # noqa: BLE001 — see docstring above
                # NOTE for NarrationRecord readers: after this swallow, the
                # in-memory result is still cached degraded=True below, but NO
                # row was persisted — durability failure on this path is
                # visible only in this ERROR log (see docstring).
                logger.error(
                    "NarrativeService degraded-beat persistence ALSO failed session=%s tick=%d: %s",
                    session_id,
                    tick,
                    persist_exc,
                )
        with self._lock:
            self._results[(session_id, tick)] = result

    @staticmethod
    def _record_specs(result: NarrativeResult, tick: int) -> list[tuple[str, str, str, str, str]]:
        """Map a NarrativeResult onto ``(beat_id, headline, body, register, error)`` tuples.

        Pure/static (no Django dependency) so it's independently testable.
        Returns ``[]`` when there is nothing to persist: a healthy
        generation with an empty domain (no SIGNIFICANT_EVENT_TYPES this
        tick — ``corporate``/``liberated`` both None) has no beat to
        record (III.11 — never fabricate content that wasn't produced).
        """
        if result.degraded:
            error_text = result.error or ""
            return [(f"wire-{tick}", "NARRATOR DEGRADED", error_text, "wire", error_text)]
        if result.corporate is None and result.liberated is None:
            return []
        specs: list[tuple[str, str, str, str, str]] = []
        for register, text in (("wire", result.corporate), ("analysis", result.liberated)):
            headline, body = _split_headline_body(text or "", tick)
            specs.append((f"{register}-{tick}", headline, body, register, ""))
        return specs

    def _persist(self, result: NarrativeResult, session_id: UUID, tick: int) -> None:
        """Durably write this generation's beats to ``NarrationRecord`` (task B4).

        A healthy generation with actual narrative text writes TWO
        records — corporate text under ``register="wire"``, liberated
        text under ``register="analysis"`` (the v1 register mapping; see
        ``NarrationRecord``'s docstring for the rationale and the future
        Gramscian-triptych extension). A degraded generation writes
        exactly ONE record (``register="wire"``, ``degraded=True``,
        headline ``"NARRATOR DEGRADED"``, body = the error string —
        III.11: visible, never silent). An empty-domain healthy
        generation (no significant event this tick) writes nothing.

        Runs on a background thread (the ``ThreadPoolExecutor`` in
        :attr:`_executor`) — Django hands out a fresh per-thread
        connection automatically, but a long-lived thread pool can end up
        reusing threads whose connections have gone stale, so
        ``close_old_connections()`` is called defensively first (no
        existing call site in this codebase to mirror — this is the
        first Django ORM access from a non-request thread — so this
        follows Django's own documented guidance for background-thread
        DB access).

        Writes are wrapped in ``transaction.atomic()`` and keyed
        idempotently via ``update_or_create`` on
        ``(session, tick, beat_id)`` — a replayed/re-scheduled generation
        for the same tick UPDATES its existing record(s) rather than
        raising a uniqueness violation or duplicating rows.

        GameSession lookup (``GameSession.objects.get(pk=session_id)``)
        is intentionally LOUD: it is allowed to raise
        ``GameSession.DoesNotExist`` rather than being caught here and
        downgraded to a log warning. See :meth:`_generate`'s docstring
        for how callers handle that.
        """
        records = self._record_specs(result, tick)
        if not records:
            return

        from django.db import close_old_connections, transaction

        from .models import GameSession, NarrationRecord

        close_old_connections()
        with transaction.atomic():
            session = GameSession.objects.get(pk=session_id)
            for beat_id, headline, body, register, error_text in records:
                NarrationRecord.objects.update_or_create(
                    session=session,
                    tick=tick,
                    beat_id=beat_id,
                    defaults={
                        "scope": NarrationRecord.Scope.TICK,
                        "subject_ref": None,
                        "headline": headline,
                        "body": body,
                        "register": register,
                        "model_id": result.model_id,
                        "prompt_version": result.prompt_version,
                        "degraded": result.degraded,
                        "error": error_text,
                    },
                )

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
