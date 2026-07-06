"""Spec-105 liveness gate: runtime assertion that counties_alive > 0,
counties_with_population == counties_alive, and total_v > 0 at the
terminal tick.

Generalizes the Michigan-constant ``83`` liveness check to any scope
by deriving ``N_scope = len(config.scope_fips)``. Unlike the STEP-0
guard (spec-102, which catches the hex-rows-exist-but-zero-counties
contention bug), this gate catches silent county drops and population
death at any scale (tri-county N=3, Michigan N=83, national N=3156).
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.headless_runner.runner import (
    LivenessGateFailure,
    _assert_liveness_or_raise,
)


def _ts(
    *,
    alive: int = 3,
    pop: int | None = None,
    total_v: float = 1000.0,
) -> dict[str, Any]:
    """Build a minimal terminal_state dict for testing."""
    if pop is None:
        pop = alive
    return {
        "counties_alive": alive,
        "counties_with_population": pop,
        "total_v": total_v,
    }


class TestLivenessGate:
    """Tests for ``_assert_liveness_or_raise``."""

    def test_passes_when_all_alive_with_population(self) -> None:
        _assert_liveness_or_raise(terminal_state=_ts(alive=3, pop=3), n_scope=3)
        _assert_liveness_or_raise(terminal_state=_ts(alive=83, pop=83), n_scope=83)
        _assert_liveness_or_raise(terminal_state=_ts(alive=3156, pop=3156), n_scope=3156)

    def test_fails_on_silent_zero(self) -> None:
        """counties_alive == 0 is the critical silent-zero failure."""
        with pytest.raises(LivenessGateFailure, match="counties_alive=0"):
            _assert_liveness_or_raise(terminal_state=_ts(alive=0, pop=0, total_v=0.0), n_scope=3)

    def test_fails_on_population_death(self) -> None:
        """counties_with_population < counties_alive means some counties
        lost their living population — the closed-drain extinction class."""
        with pytest.raises(LivenessGateFailure, match="population"):
            _assert_liveness_or_raise(terminal_state=_ts(alive=83, pop=50), n_scope=83)

    def test_fails_on_zero_total_v(self) -> None:
        """total_v == 0 with counties_alive > 0 is a value-zeroing failure."""
        with pytest.raises(LivenessGateFailure, match="total_v"):
            _assert_liveness_or_raise(terminal_state=_ts(alive=3, pop=3, total_v=0.0), n_scope=3)

    def test_warns_but_does_not_fail_when_alive_below_n_scope(self) -> None:
        """Some counties may lack hex cells (unhydrated) — this is an
        informational warning, not a gate failure."""
        # 3128 alive out of 3156 scope — should NOT raise
        _assert_liveness_or_raise(terminal_state=_ts(alive=3128, pop=3128), n_scope=3156)

    def test_fails_when_alive_exceeds_n_scope(self) -> None:
        """More alive counties than the scope defines — data corruption."""
        with pytest.raises(LivenessGateFailure, match="exceeds"):
            _assert_liveness_or_raise(terminal_state=_ts(alive=100, pop=100), n_scope=83)
