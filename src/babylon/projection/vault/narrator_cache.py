"""The narrator attributed-block cache — III.6 at the vault boundary (WO-42).

:func:`~babylon.intelligence.providers.prose_cache_key` was shipped with the
provider seam as the canonical ``(entity, tick, model_pin)`` cache key and
then never called — this module is its call site. Generated prose persists
as its own attributed vault pages under ``narrative/<entity>/``, one page
per key, each carrying a ``{narrative}`` fence the TUI already dispatches
(:mod:`babylon.tui.directives`). Switching providers can never corrupt the
record: a new pin writes a NEW page; the deprecated pin's page stays
byte-identical (III.6).

Design commitments:

* **The deterministic page is the fallback** (R4): a mute/empty narration
  writes nothing — the dossier pages are fully informative without any
  narrator, so silence is honest data-absence, never a fabricated block.
* **Degraded is recorded, not silent** (III.11): a transport failure
  writes a visible degraded page (an ``{absence}`` fence naming the
  error). A degraded entry is a recorded failure, not prose — the same
  key retries, and a later healthy generation supersedes it in place
  (the vault's git history keeps the failure on the record).
* **LLM text never meets Jinja.** Narrative pages are assembled with
  plain string building, NOT the sandbox template environment — prose is
  untrusted text, and rendering it through a template engine would turn
  ``{{ ... }}`` in model output into an injection surface. Fences grow to
  outrun any backtick runs inside the prose, so hostile output cannot
  close the page's own block.
* **Determinism boundary:** narrative pages exist only when a narrator is
  configured — the byte-identity gates (qa:regression, the two-bake
  vault e2e) run narrator-OFF and never see this subtree. Commit
  timestamps still pin to sim time via
  :func:`~babylon.projection.vault.git_backend.commit_page`.

The async seam (design-canon S5: narration is a side process, never on
the tick path) is :class:`NarratorSideProcess`: fire-and-forget
scheduling onto a single worker thread — one worker, deliberately, so
narrative commits to the shared dulwich repo serialize with each other;
:mod:`~babylon.projection.vault.git_backend` serializes them against the
tick baker's own commits.

Doctrine-conditioning of prompts is DEFERRED past v1 (charter P0 batch);
callers supply ``(system, prompt)`` and this module treats them as opaque.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, ConfigDict

from babylon.intelligence.providers import (
    ProviderUnavailable,
    prose_cache_key,
    resolve_provider,
)
from babylon.projection.vault.git_backend import commit_page, init_vault

if TYPE_CHECKING:
    from babylon.intelligence.providers import NarratorProvider

logger = logging.getLogger("babylon.projection.vault.narrator_cache")

#: The vault subtree all narrator pages live under — disjoint from every
#: deterministic dossier path, so the byte-identity gates never see it.
_NARRATIVE_ROOT: Final[str] = "narrative"

#: Frontmatter keys, in the fixed order they are written (deterministic
#: page shape for a given entry).
_FRONTMATTER_KEYS: Final[tuple[str, ...]] = (
    "entity",
    "tick",
    "model_pin",
    "provider",
    "degraded",
)


class CachedNarrative(BaseModel):
    """One attributed narrator block, as recorded in the vault.

    ``degraded=True`` means the generation FAILED and ``error`` names why
    (III.11 — a visible record, never a silent absence); ``text`` is then
    empty. A healthy entry carries the prose and an empty ``error``.
    """

    model_config = ConfigDict(frozen=True)

    entity_id: str
    tick: int
    model_pin: str
    provider: str
    text: str
    degraded: bool = False
    error: str = ""


def _pin_slug(model_pin: str) -> str:
    """A filesystem-safe, collision-resistant slug for a model pin.

    Real pins carry path-hostile characters (``@cf/meta/llama-3.1-...``),
    so the readable part is sanitized and an 8-hex content hash keeps two
    pins that sanitize identically from colliding. Deterministic — the
    same pin always yields the same slug.

    :param model_pin: the raw model pin.
    :returns: ``<sanitized>-<8-hex-sha256>``.
    """
    readable = re.sub(r"[^A-Za-z0-9._-]", "-", model_pin).strip("-") or "pin"
    digest = hashlib.sha256(model_pin.encode("utf8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def _fence_for(text: str) -> str:
    """A backtick fence strictly longer than any backtick run in ``text``.

    LLM output is untrusted: prose containing ``` lines must not be able
    to close the page's own block. Markdown closes a fence only on a run
    at least as long as the opener, so outrunning the longest interior
    run by one keeps the body verbatim.

    :param text: the fence body.
    :returns: the fence string (minimum three backticks).
    """
    runs = re.findall(r"`+", text)
    longest = max((len(run) for run in runs), default=0)
    return "`" * max(3, longest + 1)


def _render_narrative_page(entry: CachedNarrative) -> str:
    """Assemble one narrator page — plain string building, never Jinja.

    Prose is untrusted model output; routing it through a template engine
    would make ``{{ ... }}`` in that output an injection surface (the
    sandbox environment is for OUR templates, not THEIR text). See the
    module docstring.

    :param entry: the block to materialize.
    :returns: the exact page text.
    """
    values = {
        "entity": entry.entity_id,
        "tick": str(entry.tick),
        "model_pin": entry.model_pin,
        "provider": entry.provider,
        "degraded": "true" if entry.degraded else "false",
    }
    frontmatter = "\n".join(f"{key}: {values[key]}" for key in _FRONTMATTER_KEYS)
    if entry.degraded:
        body = f"narrator degraded — {entry.error}".rstrip()
        fence = _fence_for(body)
        block = f"{fence}{{absence}} {entry.model_pin}\n{body}\n{fence}"
    else:
        fence = _fence_for(entry.text)
        block = f"{fence}{{narrative}} {entry.model_pin}\n{entry.text}\n{fence}"
    return f"---\n{frontmatter}\n---\n\n{block}\n"


def _parse_narrative_page(content: str) -> CachedNarrative | None:
    """Parse a narrator page back into its :class:`CachedNarrative`.

    The inverse of :func:`_render_narrative_page` for pages that function
    wrote. A page that does not parse is treated as absent and reported
    loudly in the log — never a silent half-read (III.11).

    :param content: the page text.
    :returns: the parsed entry, or ``None`` if the shape is foreign.
    """
    match = re.match(r"^---\n(.*?)\n---\n\n(.*)$", content, flags=re.DOTALL)
    if match is None:
        return None
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    if not all(key in fields for key in _FRONTMATTER_KEYS):
        return None

    block = match.group(2)
    fence_match = re.match(
        r"^(`{3,})\{(narrative|absence)\}[^\n]*\n(.*)\n\1\n$", block, flags=re.DOTALL
    )
    if fence_match is None:
        return None
    degraded = fields["degraded"] == "true"
    body = fence_match.group(3)
    return CachedNarrative(
        entity_id=fields["entity"],
        tick=int(fields["tick"]),
        model_pin=fields["model_pin"],
        provider=fields["provider"],
        text="" if degraded else body,
        degraded=degraded,
        error=body.removeprefix("narrator degraded — ") if degraded else "",
    )


class NarratorCache:
    """The persistent ``(entity, tick, model_pin)``-keyed narrator store.

    :param vault_root: the vault repository root (initialized idempotently,
        same as :class:`~babylon.projection.vault.materializer.VaultMaterializer`).
    """

    def __init__(self, vault_root: Path) -> None:
        init_vault(vault_root)
        self._vault_root = vault_root
        self._lock = threading.Lock()

    def _page_path(self, entity_id: str, tick: int, model_pin: str) -> Path:
        relative = f"{_NARRATIVE_ROOT}/{entity_id}/{tick}--{_pin_slug(model_pin)}.md"
        return self._vault_root / relative

    def get(self, entity_id: str, tick: int, model_pin: str) -> CachedNarrative | None:
        """Read one cached block by its III.6 key.

        :returns: the entry, or ``None`` when that key was never written
            (or its page does not parse — logged loudly, treated as absent).
        """
        path = self._page_path(entity_id, tick, model_pin)
        try:
            content = path.read_text(encoding="utf8")
        except FileNotFoundError:
            return None
        entry = _parse_narrative_page(content)
        if entry is None or entry.model_pin != model_pin:
            logger.error(
                "unparseable or mismatched narrative page at %s (key %s) — treating as absent",
                path,
                prose_cache_key(entity_id, tick, model_pin),
            )
            return None
        return entry

    def blocks_for(self, entity_id: str, tick: int) -> tuple[CachedNarrative, ...]:
        """Every healthy attributed block for ``(entity, tick)``, all pins.

        Sorted by ``model_pin`` for a deterministic display order; degraded
        entries are excluded (they render as absence, not prose — callers
        wanting the failure record read :meth:`get` by pin).

        :returns: possibly-empty tuple of healthy entries.
        """
        directory = self._vault_root / _NARRATIVE_ROOT / entity_id
        if not directory.is_dir():
            return ()
        entries: list[CachedNarrative] = []
        for path in sorted(directory.glob(f"{tick}--*.md")):
            entry = _parse_narrative_page(path.read_text(encoding="utf8"))
            if entry is not None and entry.tick == tick and not entry.degraded:
                entries.append(entry)
        return tuple(sorted(entries, key=lambda entry: entry.model_pin))

    def narrate(
        self,
        provider: NarratorProvider,
        entity_id: str,
        tick: int,
        *,
        system: str = "",
        prompt: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> CachedNarrative | None:
        """Produce-or-recall the attributed block for one III.6 key.

        Cache discipline: a healthy cached entry is returned WITHOUT
        spending the provider again; a degraded cached entry is a recorded
        failure, so the same key retries and a success supersedes it in
        place. An empty narration (the mute lane) writes nothing and
        returns ``None`` — silence is honest (R4).

        :param provider: the narrator lane; its ``endpoint.chat_model`` is
            the cache key's pin (equal to the result's reported pin for
            every real lane, by seam construction).
        :param entity_id: the subject page id (e.g. ``county/26163``).
        :param tick: the committed tick the prose narrates.
        :param system: opaque system text (doctrine-conditioning deferred).
        :param prompt: opaque prompt text.
        :param max_tokens: generation budget, passed through.
        :param temperature: sampling temperature, passed through.
        :returns: the (possibly degraded) entry, or ``None`` for silence.
        """
        pin = provider.endpoint.chat_model
        with self._lock:
            cached = self.get(entity_id, tick, pin)
            if cached is not None and not cached.degraded:
                return cached
            try:
                result = provider.narrate(
                    system, prompt, max_tokens=max_tokens, temperature=temperature
                )
            except ProviderUnavailable as exc:
                entry = CachedNarrative(
                    entity_id=entity_id,
                    tick=tick,
                    model_pin=pin,
                    provider=provider.endpoint.kind.value,
                    text="",
                    degraded=True,
                    error=str(exc),
                )
                self._write(entry)
                logger.warning(
                    "narrator degraded for %s: %s", prose_cache_key(entity_id, tick, pin), exc
                )
                return entry
            if result.text == "":
                return None
            entry = CachedNarrative(
                entity_id=entity_id,
                tick=tick,
                model_pin=result.model_pin,
                provider=result.provider.value,
                text=result.text,
            )
            self._write(entry)
            return entry

    def _write(self, entry: CachedNarrative) -> None:
        relative = (
            f"{_NARRATIVE_ROOT}/{entry.entity_id}/{entry.tick}--{_pin_slug(entry.model_pin)}.md"
        )
        verb = "degraded" if entry.degraded else "narrate"
        commit_page(
            self._vault_root,
            relative,
            _render_narrative_page(entry),
            tick=entry.tick,
            message=f"{verb}: {prose_cache_key(entry.entity_id, entry.tick, entry.model_pin)}",
        )


class NarratorSideProcess:
    """Fire-and-forget narration off the tick path (design-canon S5).

    One worker thread, deliberately: narrative commits to the shared
    dulwich repo serialize with each other, and
    :meth:`schedule` never blocks and never raises — the tick loop must
    not know or care whether narration is running (II.5: AI observes).

    :param cache: the cache all generations land in.
    :param provider: the narrator lane; ``None`` resolves lazily via
        :func:`~babylon.intelligence.providers.resolve_provider` ON THE
        WORKER THREAD (the health-probe walk never delays a caller).
    """

    def __init__(self, cache: NarratorCache, provider: NarratorProvider | None = None) -> None:
        self._cache = cache
        self._provider = provider
        self._provider_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="narrator-cache")

    def _resolve(self) -> NarratorProvider:
        with self._provider_lock:
            if self._provider is None:
                self._provider = resolve_provider()
            return self._provider

    def _run(self, entity_id: str, tick: int, system: str, prompt: str) -> CachedNarrative | None:
        try:
            return self._cache.narrate(
                self._resolve(), entity_id, tick, system=system, prompt=prompt
            )
        except Exception:  # noqa: BLE001 — III.11: loud in the log, never a dead pool thread
            logger.exception("narrator side-process failed for %s @ tick %d", entity_id, tick)
            return None

    def schedule(
        self, entity_id: str, tick: int, *, system: str, prompt: str
    ) -> Future[CachedNarrative | None] | None:
        """Submit one generation; never blocks, never raises.

        :returns: the Future (tests may await it), or ``None`` when the
            side process is already closed — logged, not raised, so a
            shutdown race can never take down the caller.
        """
        try:
            return self._executor.submit(self._run, entity_id, tick, system, prompt)
        except RuntimeError:
            logger.warning(
                "narrator side-process is closed; dropping %s @ tick %d", entity_id, tick
            )
            return None

    def close(self) -> None:
        """Drain and shut down the worker (idempotent)."""
        self._executor.shutdown(wait=True)


__all__ = [
    "CachedNarrative",
    "NarratorCache",
    "NarratorSideProcess",
]
