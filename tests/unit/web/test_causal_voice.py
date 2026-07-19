"""Deterministic causal voice — frame→beat rendering (spec-116 FR-4.1).

Pure-function tests: no Django, no DB, no engine. The templates are the
behavioral contract the narration panel and Wire render — pinned
byte-for-byte so a copy change is a conscious diff, never drift.
"""

from __future__ import annotations

import pytest

from game.causal_voice import (
    CAUSAL_MODEL_ID,
    CAUSAL_PROMPT_VERSION,
    CausalBeatSpec,
    render_frame_beats,
)


def _pulse_frame() -> dict[str, object]:
    return {
        "pattern": "TICK_PULSE",
        "tick": 12,
        "deltas": {
            "pool": {"before": 100.0, "after": 70.0},
            "wage": {"before": 0.20, "after": 0.20},
            "p_rev": {"before": 0.30, "after": 0.45},
        },
    }


def _shock_frame() -> dict[str, object]:
    """Literal frame matching CausalChainObserver._build_frame's shape."""
    return {
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


@pytest.mark.unit
class TestPulseRendering:
    def test_pulse_renders_three_causal_sentences(self) -> None:
        beats = render_frame_beats([_pulse_frame()])

        assert beats == [
            CausalBeatSpec(
                beat_id="causal-pulse-t12",
                headline="The week's ledger, tick 12.",
                body=(
                    "The imperial rent pool fell from 100.00 to 70.00. "
                    "The super-wage rate held at 0.2000. "
                    "Peak revolutionary probability rose from 0.300 to 0.450."
                ),
                register="wire",
            )
        ]

    def test_rendering_is_deterministic(self) -> None:
        assert render_frame_beats([_pulse_frame()]) == render_frame_beats([_pulse_frame()])


@pytest.mark.unit
class TestShockRendering:
    def test_shock_renders_the_causal_chain(self) -> None:
        beats = render_frame_beats([_shock_frame()])

        assert len(beats) == 1
        beat = beats[0]
        assert beat.beat_id == "causal-shock-t10"
        assert beat.register == "analysis"
        assert beat.headline == "Shock, austerity, radicalization — the causal chain closed."
        assert beat.body == (
            "The rent pool crashed 30.0% at tick 10. "
            "In the aftermath the super-wage rate was cut from 0.2000 to 0.1500. "
            "Peak revolutionary probability climbed from 0.300 to 0.450 — "
            "the shock is being answered."
        )


@pytest.mark.unit
class TestPulseVeilGate:
    """G4 Finding 2 (adversarial review): the "pool" (imperial_rent_pool)
    sentence formats a real value-axis number into narration prose — the
    same class of leak :data:`_VEILED_APOLOGIST_REFUTATION`
    (``engine_bridge.py``) already fixes for the social_class inspector.
    ``veil_tier`` defaults to ``2`` (fully unlocked) so every pre-existing
    call site (this suite's other tests) stays byte-identical. Below Tier
    1 the pool sentence must not name real numbers; wage/p_rev stay
    visible — money-form and political axes are never gated (veil.py)."""

    def test_default_veil_tier_is_unlocked_byte_identical_to_before_g4(self) -> None:
        beats = render_frame_beats([_pulse_frame()])
        assert "100.00" in beats[0].body
        assert "70.00" in beats[0].body

    def test_tier_zero_veils_the_pool_sentence_but_not_wage_or_p_rev(self) -> None:
        body = render_frame_beats([_pulse_frame()], veil_tier=0)[0].body
        assert "100.00" not in body
        assert "70.00" not in body
        assert "0.2000" in body  # wage rate — money-form, never gated
        assert "0.300" in body
        assert "0.450" in body  # p_rev — political axis, never gated

    def test_tier_one_unlocks_the_pool_sentence(self) -> None:
        body = render_frame_beats([_pulse_frame()], veil_tier=1)[0].body
        assert "100.00" in body
        assert "70.00" in body


@pytest.mark.unit
class TestShockVeilGate:
    """Same leak, the SHOCK_DOCTRINE pattern's rent-pool-crash sentence
    (the pool's percentage drop is itself a value-axis relation)."""

    def test_default_veil_tier_is_unlocked_byte_identical_to_before_g4(self) -> None:
        body = render_frame_beats([_shock_frame()])[0].body
        assert "30.0%" in body

    def test_tier_zero_veils_the_pool_crash_percentage(self) -> None:
        body = render_frame_beats([_shock_frame()], veil_tier=0)[0].body
        assert "30.0%" not in body
        assert "0.2000" in body  # wage — still visible
        assert "0.1500" in body
        assert "0.300" in body  # p_rev — still visible
        assert "0.450" in body

    def test_tier_one_unlocks_the_pool_crash_percentage(self) -> None:
        body = render_frame_beats([_shock_frame()], veil_tier=1)[0].body
        assert "30.0%" in body


@pytest.mark.unit
class TestContractLimits:
    def test_beat_ids_fit_the_64_char_column(self) -> None:
        beats = render_frame_beats([_pulse_frame(), _shock_frame()])
        assert all(len(b.beat_id) <= 64 for b in beats)
        # 5200-tick horizon worst case
        assert len(f"causal-pulse-t{5200}") <= 64

    def test_model_pins_fit_their_columns(self) -> None:
        assert CAUSAL_MODEL_ID == "deterministic-causal-v1"
        assert len(CAUSAL_MODEL_ID) <= 128
        assert len(CAUSAL_PROMPT_VERSION) == 12  # content hash, <= 32-char column
        int(CAUSAL_PROMPT_VERSION, 16)  # hex — raises if not

    def test_unknown_pattern_is_loud(self) -> None:
        with pytest.raises(ValueError, match="unknown causal frame pattern"):
            render_frame_beats([{"pattern": "NOT_A_PATTERN"}])
