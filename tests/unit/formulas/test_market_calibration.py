"""Calibration behavioral contracts for the market scissors (ADR078).

Model-derived contracts ONLY (Constitution III.12 / ADR074 item 6): every
band below is derived from the default ``MarketDefines`` dynamics, never
from unverifiable empirical literals. True FRED/NBER numeric anchors stay
deferred until their data files land as deterministic artifacts (recorded
in ADR078's deferred list) — a number this file cannot trace to the model
itself does not belong here.

These are the contracts a rewrite must reproduce (the III.12 rewrite test):
1. Restoration — the law of value closes an opened scissors on historical,
   not instantaneous, time (half-life band).
2. No limit cycle — zero drive admits no self-sustaining oscillation.
3. Sustained euphoria fires the correction; the cooldown spaces snaps.
4. Balanced growth NEVER fires it — a bubble requires divergence, not size.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import MarketDefines
from babylon.formulas.market import (
    calculate_correction_snap,
    calculate_growth_drive,
    calculate_overhang,
    calculate_scissors_step,
    calculate_serviceable_divergence,
)

pytestmark = pytest.mark.math

_MAX_TICKS = 520  # one canonical run — every loop below is bounded by it


def _decay_run(defines: MarketDefines, initial: float) -> list[float]:
    """Zero-drive trajectory of the price oscillator from ``initial``."""
    log, vel = initial, 0.0
    trajectory: list[float] = []
    for _ in range(_MAX_TICKS):  # fixed bound
        log, vel = calculate_scissors_step(
            log,
            vel,
            0.0,
            reversion=defines.price_reversion,
            damping=defines.price_damping,
            max_abs_log=defines.max_abs_log,
        )
        trajectory.append(log)
    return trajectory


def _envelope_half_life(trajectory: list[float], threshold: float) -> int:
    """Last tick |log| still exceeded ``threshold`` — the DECAY envelope.

    First-crossing would measure the underdamped swing through zero, not
    restoration; the envelope is when the divergence PERMANENTLY halves.
    """
    return max((i + 1 for i, log in enumerate(trajectory) if abs(log) > threshold), default=0)


class TestRestoration:
    def test_half_life_is_historical_not_instantaneous(self) -> None:
        """The price envelope halves within [4, 100] ticks under defaults.

        Below 4 the law of value would act like an instantaneous market
        clearer (no divergence could ever be observed); above 100 a plain
        price swing would outlive a fifth of the canonical 520-tick run.
        Measured 8 at the ADR078 defaults.
        """
        half_life = _envelope_half_life(_decay_run(MarketDefines(), initial=0.5), 0.25)
        assert 4 <= half_life <= 100

    def test_bubbles_outlive_price_swings(self) -> None:
        """The LOAD-BEARING gravity asymmetry (Capital Vol. III part 5):
        the fictitious envelope half-life strictly exceeds the price one."""
        d = MarketDefines()
        price = _envelope_half_life(_decay_run(d, initial=0.5), 0.25)
        log, vel = 0.5, 0.0
        fict_traj: list[float] = []
        for _ in range(_MAX_TICKS):  # fixed bound
            log, vel = calculate_scissors_step(
                log,
                vel,
                0.0,
                reversion=d.fictitious_reversion,
                damping=d.fictitious_damping,
                max_abs_log=d.max_abs_log,
            )
            fict_traj.append(log)
        assert _envelope_half_life(fict_traj, 0.25) > price

    def test_zero_drive_settles_to_par(self) -> None:
        trajectory = _decay_run(MarketDefines(), initial=0.5)
        assert abs(trajectory[-1]) < 1e-3

    def test_no_limit_cycle_amplitude_never_grows(self) -> None:
        """Peak |log| over successive 52-tick windows is non-increasing."""
        trajectory = _decay_run(MarketDefines(), initial=0.5)
        windows = [
            max(abs(x) for x in trajectory[i : i + 52])
            for i in range(0, _MAX_TICKS, 52)  # fixed bound: 10 windows
        ]
        assert all(
            later <= earlier + 1e-12 for earlier, later in zip(windows, windows[1:], strict=False)
        )


def _euphoria_run(defines: MarketDefines, surplus_growth: float) -> list[int]:
    """Ticks at which the correction fires under constant surplus growth.

    Reproduces the system's fire discipline (overhang + cooldown) against
    the pure laws — the engine test battery covers the graph wiring; this
    contract pins the DYNAMICS: does sustained euphoria actually reach the
    serviceability line, and how are snaps spaced once it does.
    """
    log, vel = 0.0, 0.0
    surplus_ema = 1.0
    surplus = 1.0
    last_fire: int | None = None
    fires: list[int] = []
    for tick in range(1, _MAX_TICKS + 1):  # fixed bound
        surplus *= 1.0 + surplus_growth
        drive = calculate_growth_drive(
            surplus, surplus_ema, sensitivity=defines.fictitious_drive_sensitivity
        )
        log, vel = calculate_scissors_step(
            log,
            vel,
            drive,
            reversion=defines.fictitious_reversion,
            damping=defines.fictitious_damping,
            max_abs_log=defines.max_abs_log,
        )
        serviceable = calculate_serviceable_divergence(
            None,
            base=defines.correction_threshold_base,
            slope=defines.correction_profit_slope,
        )
        overhang = calculate_overhang(log, serviceable)
        cooled = last_fire is None or tick - last_fire >= defines.correction_cooldown_ticks
        if overhang > 0.0 and cooled:
            log, vel = calculate_correction_snap(log, vel, severity=defines.correction_severity)
            fires.append(tick)
            last_fire = tick
        surplus_ema = (
            defines.surplus_ema_alpha * surplus + (1.0 - defines.surplus_ema_alpha) * surplus_ema
        )
    return fires


class TestCorrectionDiscipline:
    def test_sustained_euphoria_fires_within_a_canonical_run(self) -> None:
        fires = _euphoria_run(MarketDefines(), surplus_growth=0.05)
        assert fires, "5%/tick surplus growth never breached serviceability in 520 ticks"
        assert fires[0] <= _MAX_TICKS

    def test_cooldown_spaces_consecutive_snaps(self) -> None:
        defines = MarketDefines()
        fires = _euphoria_run(defines, surplus_growth=0.05)
        assert len(fires) >= 2, "sustained euphoria should re-inflate after the snap"
        gaps = [b - a for a, b in zip(fires, fires[1:], strict=False)]
        assert all(gap >= defines.correction_cooldown_ticks for gap in gaps)

    def test_balanced_growth_never_fires(self) -> None:
        """Zero RELATIVE surplus growth (flat flow) opens no scissors at all.

        A large economy is not a bubble: the trigger is divergence of claims
        from realized surplus, and with a flat flow the drive is zero.
        """
        fires = _euphoria_run(MarketDefines(), surplus_growth=0.0)
        assert fires == []

    def test_boundedness_under_extreme_defines(self) -> None:
        """No defines-reachable parameterization escapes the rail."""
        defines = MarketDefines(
            fictitious_drive_sensitivity=5.0,
            fictitious_reversion=0.0,
            fictitious_damping=0.0,
        )
        log, vel = 0.0, 0.0
        surplus, surplus_ema = 1.0, 1.0
        for _ in range(_MAX_TICKS):  # fixed bound
            surplus *= 1.10
            drive = calculate_growth_drive(
                surplus, surplus_ema, sensitivity=defines.fictitious_drive_sensitivity
            )
            log, vel = calculate_scissors_step(
                log,
                vel,
                drive,
                reversion=defines.fictitious_reversion,
                damping=defines.fictitious_damping,
                max_abs_log=defines.max_abs_log,
            )
            surplus_ema = (
                defines.surplus_ema_alpha * surplus
                + (1.0 - defines.surplus_ema_alpha) * surplus_ema
            )
            assert abs(log) <= defines.max_abs_log + 1e-12
