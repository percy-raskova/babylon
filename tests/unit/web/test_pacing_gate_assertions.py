"""Tests for the null-play survival assertion wrapper (G1 gate, spec-116).

These are fast, stub-only unit tests of the *assertion logic* the standing
520-tick nationwide pacing gate (``tests/integration/engine/test_pacing_gate_g1.py``)
applies to a real ``ProbeResult``. Per the G1 brief, the stub here exercises
ONLY the wrapper's own correctness — it is never a substitute for actually
running the real gate (see the integration-tier test for that evidence).
"""

from __future__ import annotations

import pytest

from game.management.commands.pacing_probe import AXES, ProbeResult, assert_null_play_survival

pytestmark = pytest.mark.unit


def _stub_result(
    ticks_completed: int = 520,
    first_recognition: dict[str, int | None] | None = None,
    axis_curves: dict[str, list[list[float]]] | None = None,
) -> ProbeResult:
    """Build a minimal, otherwise-passing stub ``ProbeResult``."""
    return ProbeResult(
        ticks_completed=ticks_completed,
        first_recognition=first_recognition or dict.fromkeys(AXES),
        final_pattern=None,
        axis_curves=axis_curves or {axis: [[520, 0.5]] for axis in AXES},
        event_counts={},  # type: ignore[arg-type]
    )


def test_passing_stub_raises_nothing() -> None:
    """A stub that satisfies the contract raises no AssertionError."""
    assert_null_play_survival(_stub_result(), expected_ticks=520)


def test_wrong_tick_count_fails() -> None:
    """``ticks_completed`` must equal the requested horizon exactly."""
    result = _stub_result(ticks_completed=519)
    with pytest.raises(AssertionError, match="ticks_completed"):
        assert_null_play_survival(result, expected_ticks=520)


def test_any_axis_recognized_fails() -> None:
    """A latched ``first_recognition`` on any single axis fails the gate."""
    recognition = dict.fromkeys(AXES)
    recognition["fascist_consolidation"] = 400
    result = _stub_result(first_recognition=recognition)
    with pytest.raises(AssertionError, match="fascist_consolidation"):
        assert_null_play_survival(result, expected_ticks=520)


def test_gate_blindness_progress_at_one_fails_even_without_recognition() -> None:
    """A progress value hitting 1.0 fails the gate even if ``first_recognition``
    never latched it.

    This is the "gate-blindness" case: ``EndgameDetector`` only records
    ``recognized_pattern`` for the single first-matched axis in FR-033
    priority order each tick, so a lower-priority axis quietly reaching
    1.0 progress alongside a higher-priority match would never appear in
    ``first_recognition``. The wrapper must catch this independently by
    scanning ``axis_curves`` directly, not by trusting the latch alone.
    """
    curves = {axis: [[520, 0.5]] for axis in AXES}
    curves["red_ogv"] = [[260, 0.7], [520, 1.0]]
    result = _stub_result(first_recognition=dict.fromkeys(AXES), axis_curves=curves)
    with pytest.raises(AssertionError, match="red_ogv"):
        assert_null_play_survival(result, expected_ticks=520)


def test_progress_exactly_below_one_passes() -> None:
    """The boundary: 0.9999 progress passes, 1.0 does not."""
    curves = {axis: [[520, 0.9999]] for axis in AXES}
    result = _stub_result(axis_curves=curves)
    assert_null_play_survival(result, expected_ticks=520)
