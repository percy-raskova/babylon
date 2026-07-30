"""The production grounding filter (Standard §5; rulings 26/27's guardrail).

The law: narration may use ONLY the proper nouns and numbers its grounded
inputs supplied — the prompt/system text (built from real chronicle
summaries) plus the tick envelope's ``entities[]`` dictionary and numeric
deltas. A new proper noun or number REJECTS the generation, and the
rejection publishes through the cache's existing degraded machinery — a
visible ``{absence}`` page NAMING the offender (III.11: honest absence,
never smoothed-over invention).

Deterministic set arithmetic over tokens — no linguistics, no model in the
loop.
"""

from __future__ import annotations

import pytest

from babylon.projection.narration_grounding import (
    GroundingContext,
    ground_check,
    grounding_from_inputs,
)

pytestmark = [pytest.mark.unit]


def _context() -> GroundingContext:
    return grounding_from_inputs(
        system="You are the Narrator: observe and write one grounded beat.",
        prompt="Tick 3 committed. C_periphery yields 12.50 in surplus to C_core.",
        entities=("C_core", "C_periphery"),
        numbers=(12.5, 3),
    )


class TestGroundCheck:
    def test_grounded_text_passes(self) -> None:
        text = "C_periphery bleeds again: 12.50 in surplus flows to C_core."
        assert ground_check(text, _context()) is None

    def test_new_proper_noun_rejects_naming_the_offender(self) -> None:
        offense = ground_check("The spirit of Chicago stirs in C_core.", _context())
        assert offense is not None
        assert "Chicago" in offense

    def test_new_number_rejects_naming_the_offender(self) -> None:
        offense = ground_check("C_core extracts 73.5 in tribute.", _context())
        assert offense is not None
        assert "73.5" in offense

    def test_sentence_initial_common_words_never_reject(self) -> None:
        assert ground_check("The surplus flows. Nothing else moved.", _context()) is None

    def test_number_formatting_variants_of_grounded_values_pass(self) -> None:
        # 12.5 was declared; "12.50" and "12.5" both render it.
        assert ground_check("A flow of 12.5 recorded.", _context()) is None
        assert ground_check("A flow of 12.50 recorded.", _context()) is None

    def test_small_integers_are_not_treated_as_inventions(self) -> None:
        """Counting words ('two edges', 'one flow') and single digits are
        prose mechanics, not data claims — the filter targets INVENTED
        DATA, and every declared number stays checkable."""
        assert ground_check("One flow, then another; 3 remains the tick.", _context()) is None


class TestCacheIntegration:
    def test_ungrounded_generation_writes_a_degraded_absence_page(self, tmp_path) -> None:
        from babylon.intelligence.providers import (
            NarrationResult,
            ProviderEndpoint,
            ProviderKind,
        )
        from babylon.projection.vault.narrator_cache import NarratorCache

        class _UngroundedProvider:
            endpoint = ProviderEndpoint(
                kind=ProviderKind.MOCK,
                base_url="mock://",
                chat_model="mock-pin",
                embed_model="mock-embed",
            )

            def narrate(self, _system, _prompt, *, max_tokens=512, temperature=0.7):
                del max_tokens, temperature
                return NarrationResult(
                    text="The ghost of Chicago demands 99.9 in tribute.",
                    model_pin="mock-pin",
                    provider=ProviderKind.MOCK,
                )

        cache = NarratorCache(tmp_path)
        entry = cache.narrate(
            _UngroundedProvider(),
            "county/26163",
            3,
            system="observe",
            prompt="Tick 3 committed. C_core stands.",
            grounding=grounding_from_inputs(
                system="observe",
                prompt="Tick 3 committed. C_core stands.",
                entities=("C_core",),
                numbers=(3,),
            ),
        )
        assert entry is not None
        assert entry.degraded is True
        assert "Chicago" in (entry.error or "") or "99.9" in (entry.error or "")
        # And a healthy regeneration can supersede the recorded failure —
        # the degraded entry is a retryable record, not a tombstone.
