"""Contract tests for WO-42: the narrator attributed-block cache.

The cache makes III.6 executable at the vault boundary: prose is keyed
``(entity, tick, model_pin)`` via the previously-dead
:func:`~babylon.intelligence.providers.prose_cache_key`, persisted as
attributed ``{narrative}`` vault pages, and switching providers can never
corrupt the record — it only writes new attributed blocks. Ports the
surviving behavioral contracts of the legacy web narrator estate
(``test_narration_record.py`` durability/idempotence,
``test_narrator.py::TestProviderSwap`` pin attribution,
``NarrativeService`` non-blocking schedule + degraded-loud): the
deterministic baked page is now the fully-informative fallback (R4), so
the Wire-feed template specifics die with the web client.
"""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from babylon.intelligence.providers import (
    MockNarrator,
    MuteProvider,
    NarrationResult,
    ProviderEndpoint,
    ProviderHealth,
    ProviderKind,
    ProviderUnavailable,
    prose_cache_key,
)
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.narrator_cache import (
    CachedNarrative,
    NarratorCache,
    NarratorSideProcess,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from babylon.intelligence.providers import EmbeddingResult
    from babylon.projection.view_models import CountyView


class _PinnedScriptedProvider:
    """NarratorProvider-shaped test double whose result pin follows its
    endpoint pin (the invariant the real ``OpenAICompatProvider`` holds by
    construction and ``MockNarrator`` does not)."""

    def __init__(self, pin: str, text: str) -> None:
        self.endpoint = ProviderEndpoint(
            kind=ProviderKind.MOCK,
            base_url="about:mock",
            chat_model=pin,
            embed_model="mock",
        )
        self._text = text
        self.call_count = 0

    def narrate(
        self,
        system: str,  # noqa: ARG002 — NarratorProvider shape
        prompt: str,  # noqa: ARG002 — NarratorProvider shape
        *,
        max_tokens: int = 512,  # noqa: ARG002 — NarratorProvider shape
        temperature: float = 0.7,  # noqa: ARG002 — NarratorProvider shape
    ) -> NarrationResult:
        self.call_count += 1
        return NarrationResult(
            text=self._text,
            model_pin=self.endpoint.chat_model,
            provider=ProviderKind.MOCK,
        )

    def embed(self, texts: Sequence[str]) -> EmbeddingResult:  # noqa: ARG002
        raise ProviderUnavailable("scripted lane cannot embed")

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, kind=ProviderKind.MOCK, detail="scripted")


class _FailingProvider(_PinnedScriptedProvider):
    """A lane whose transport always fails — the III.11 degraded path."""

    def narrate(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> NarrationResult:
        self.call_count += 1
        raise ProviderUnavailable("scripted transport failure")


@pytest.fixture
def cache(tmp_path: Path) -> NarratorCache:
    return NarratorCache(tmp_path / "vault")


class TestCacheKeyStructure:
    def test_key_helper_is_the_canonical_iii6_triple(self) -> None:
        assert prose_cache_key("county/26163", 12, "pin-a") == "county/26163:12:pin-a"

    def test_distinct_pins_are_distinct_entries(self, cache: NarratorCache) -> None:
        cache.narrate(_PinnedScriptedProvider("pin-a", "Alpha."), "county/26163", 12)
        cache.narrate(_PinnedScriptedProvider("pin-b", "Beta."), "county/26163", 12)
        entry_a = cache.get("county/26163", 12, "pin-a")
        entry_b = cache.get("county/26163", 12, "pin-b")
        assert entry_a is not None and entry_a.text == "Alpha."
        assert entry_b is not None and entry_b.text == "Beta."

    def test_distinct_ticks_are_distinct_entries(self, cache: NarratorCache) -> None:
        provider = _PinnedScriptedProvider("pin-a", "Tick prose.")
        cache.narrate(provider, "county/26163", 12)
        cache.narrate(provider, "county/26163", 13)
        assert cache.get("county/26163", 12, "pin-a") is not None
        assert cache.get("county/26163", 13, "pin-a") is not None
        assert provider.call_count == 2

    def test_unwritten_key_reads_as_absent(self, cache: NarratorCache) -> None:
        assert cache.get("county/26163", 99, "pin-a") is None


class TestCacheHitSemantics:
    def test_second_narrate_on_same_key_never_respends_the_provider(
        self, cache: NarratorCache
    ) -> None:
        provider = _PinnedScriptedProvider("pin-a", "Once only.")
        first = cache.narrate(provider, "county/26163", 12)
        second = cache.narrate(provider, "county/26163", 12)
        assert provider.call_count == 1
        assert isinstance(first, CachedNarrative) and isinstance(second, CachedNarrative)
        assert second.text == first.text == "Once only."

    def test_cache_survives_a_fresh_cache_instance(self, tmp_path: Path) -> None:
        """Persistence is the vault, not process memory (legacy
        ``NarrationRecord`` durability contract, re-homed)."""
        root = tmp_path / "vault"
        provider = _PinnedScriptedProvider("pin-a", "Durable prose.")
        NarratorCache(root).narrate(provider, "county/26163", 12)
        reopened = NarratorCache(root).get("county/26163", 12, "pin-a")
        assert reopened is not None
        assert reopened.text == "Durable prose."
        assert provider.call_count == 1


class TestMuteLegalPath:
    def test_mute_narration_writes_no_block(self, cache: NarratorCache) -> None:
        """R4: silence is legal and honest — an empty narration is never
        materialized as a fabricated attributed block."""
        assert cache.narrate(MuteProvider(), "county/26163", 12) is None
        assert cache.get("county/26163", 12, "mute") is None
        assert cache.blocks_for("county/26163", 12) == ()

    def test_mute_leaves_the_vault_narrative_free(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        NarratorCache(root).narrate(MuteProvider(), "county/26163", 12)
        assert not (root / "narrative").exists()


class TestModelPinSurvivesDeprecation:
    def test_switching_pins_adds_blocks_and_never_corrupts_the_old(
        self, cache: NarratorCache, tmp_path: Path
    ) -> None:
        """III.6: a deprecated pin's block outlives its provider byte-for-byte."""
        cache.narrate(_PinnedScriptedProvider("deprecated-pin", "Old attributed prose."), "c/1", 7)
        old_page = next((tmp_path / "vault" / "narrative").rglob("*.md"))
        old_bytes = old_page.read_bytes()

        cache.narrate(_PinnedScriptedProvider("successor-pin", "New attributed prose."), "c/1", 7)

        assert old_page.read_bytes() == old_bytes
        blocks = cache.blocks_for("c/1", 7)
        assert [entry.model_pin for entry in blocks] == ["deprecated-pin", "successor-pin"]
        assert all(not entry.degraded for entry in blocks)

    def test_pathological_pin_names_round_trip(self, cache: NarratorCache) -> None:
        """Real pins carry path-hostile characters (``@cf/meta/llama-...``)."""
        pin = "@cf/meta/llama-3.1-8b-instruct-fast"
        cache.narrate(_PinnedScriptedProvider(pin, "Cloud prose."), "county/26163", 12)
        entry = cache.get("county/26163", 12, pin)
        assert entry is not None
        assert entry.model_pin == pin
        assert entry.text == "Cloud prose."


class TestDegradedLoud:
    def test_transport_failure_records_a_visible_degraded_entry(self, cache: NarratorCache) -> None:
        """III.11: a failed generation is a recorded, visible fact — never a
        silently-absent one (legacy ``NARRATOR DEGRADED`` beat, re-homed)."""
        entry = cache.narrate(_FailingProvider("pin-a", ""), "county/26163", 12)
        assert entry is not None
        assert entry.degraded is True
        assert "scripted transport failure" in entry.error
        assert entry.text == ""
        stored = cache.get("county/26163", 12, "pin-a")
        assert stored is not None and stored.degraded is True

    def test_degraded_entry_is_retried_and_healed_not_cached_forever(
        self, cache: NarratorCache
    ) -> None:
        """A degraded entry is a recorded failure, not prose — the same key
        retries and a later healthy generation supersedes it (legacy
        ``update_or_create`` idempotence, re-homed)."""
        cache.narrate(_FailingProvider("pin-a", ""), "county/26163", 12)
        healed = cache.narrate(
            _PinnedScriptedProvider("pin-a", "Recovered prose."), "county/26163", 12
        )
        assert healed is not None and healed.degraded is False
        stored = cache.get("county/26163", 12, "pin-a")
        assert stored is not None
        assert stored.degraded is False
        assert stored.text == "Recovered prose."

    def test_degraded_page_renders_as_absence_not_prose(
        self, cache: NarratorCache, tmp_path: Path
    ) -> None:
        cache.narrate(_FailingProvider("pin-a", ""), "county/26163", 12)
        page = next((tmp_path / "vault" / "narrative").rglob("*.md")).read_text(encoding="utf8")
        assert "{absence}" in page
        assert "{narrative}" not in page


class TestNarrativePageShape:
    def test_page_carries_an_attributed_narrative_fence(
        self, cache: NarratorCache, tmp_path: Path
    ) -> None:
        cache.narrate(_PinnedScriptedProvider("pin-a", "Attributed prose."), "county/26163", 12)
        page = next((tmp_path / "vault" / "narrative").rglob("*.md")).read_text(encoding="utf8")
        assert "```{narrative} pin-a" in page
        assert "Attributed prose." in page
        assert "model_pin: pin-a" in page

    def test_prose_containing_backtick_fences_round_trips(self, cache: NarratorCache) -> None:
        """LLM output is untrusted text: a prose body containing ``` lines
        must not break the page's own fence."""
        hostile = "It said:\n```{narrative} fake\ninjected\n```\nand moved on."
        cache.narrate(_PinnedScriptedProvider("pin-a", hostile), "county/26163", 12)
        entry = cache.get("county/26163", 12, "pin-a")
        assert entry is not None
        assert entry.text == hostile

    def test_prose_is_never_rendered_through_jinja(self, cache: NarratorCache) -> None:
        """Template-injection guard: LLM text goes onto the page verbatim,
        so Jinja syntax in prose stays inert literal text."""
        injection = "Ignore {{ 4 * 4 }} and {% raise %}."
        cache.narrate(_PinnedScriptedProvider("pin-a", injection), "county/26163", 12)
        entry = cache.get("county/26163", 12, "pin-a")
        assert entry is not None
        assert entry.text == injection


class TestNarratorOffFullyInformative:
    def test_baked_page_is_complete_without_any_narrator(
        self, tmp_path: Path, wayne_county_view: CountyView
    ) -> None:
        """R4 made executable: the deterministic dossier is the fully
        informative surface; no narrator object exists in this test."""
        materializer = VaultMaterializer(tmp_path / "vault")
        page = materializer.bake_county(wayne_county_view, tick=500).read_text(encoding="utf8")
        assert "{narrative}" not in page
        for row in ("population: 1749343", "median_wage: 18.500000", "legitimacy: 0.420000"):
            assert row in page


class TestSideProcess:
    def test_schedule_returns_a_future_and_lands_in_the_cache(self, cache: NarratorCache) -> None:
        side = NarratorSideProcess(cache, provider=MockNarrator(responses=["Landed prose."]))
        try:
            future = side.schedule("county/26163", 12, system="sys", prompt="p")
            assert isinstance(future, Future)
            entry = future.result(timeout=10)
            assert entry is not None and entry.text == "Landed prose."
            assert cache.get("county/26163", 12, "mock") is not None
        finally:
            side.close()

    def test_schedule_never_raises_on_a_failing_lane(self, cache: NarratorCache) -> None:
        side = NarratorSideProcess(cache, provider=_FailingProvider("pin-a", ""))
        try:
            future = side.schedule("county/26163", 12, system="sys", prompt="p")
            assert future is not None
            entry = future.result(timeout=10)
            assert entry is not None and entry.degraded is True
        finally:
            side.close()

    def test_schedule_after_close_degrades_without_raising(self, cache: NarratorCache) -> None:
        side = NarratorSideProcess(cache, provider=MockNarrator())
        side.close()
        assert side.schedule("county/26163", 12, system="sys", prompt="p") is None
