"""Market-scissors dynamics: price⟷value divergence as a damped-driven oscillator.

Program 23 (ADR077). Prices are the phenomenal form of value; the law of
value is the restoring force pulling the log price-to-value ratio back to
zero, while demand pull (value-output growth) and return-chasing speculation
(surplus growth + price momentum) drive it away. Crisis theory as mechanism:
the correction is the deterministic snap-back of an opened scissors — in
Phase 1 it is only OBSERVED, never fed back (owner-gated Phase 2).

All functions are pure, per-tick-unit (implicit dt = 1 tick), and
deterministic (Constitution III.7). Coefficients come from
``GameDefines.market`` (:class:`babylon.config.defines.MarketDefines`) —
never hardcoded at call sites.
"""

from __future__ import annotations

import math

__all__ = [
    "calculate_ema",
    "calculate_growth_drive",
    "calculate_scissors_balance",
    "calculate_scissors_step",
]

_GROWTH_EPSILON = 1e-9
"""Below this anchor a growth ratio is undefined — honest zero drive (III.11)."""


def calculate_ema(previous: float, value: float, *, alpha: float) -> float:
    """Exponential moving average step.

    :param previous: The prior EMA value.
    :param value: This tick's observation.
    :param alpha: Blend weight in (0, 1]; 1 tracks the raw value.
    :returns: ``alpha * value + (1 - alpha) * previous``.
    """
    return alpha * value + (1.0 - alpha) * previous


def calculate_growth_drive(current: float, previous: float, *, sensitivity: float) -> float:
    """Relative-growth drive term: ``sensitivity * (current - previous) / previous``.

    :param current: This tick's flow (value output or realized surplus).
    :param previous: The prior anchor (EMA) of the same flow.
    :param sensitivity: Drive gain (a ``MarketDefines`` coefficient).
    :returns: The signed drive; 0.0 when the anchor is ~zero — no growth
        signal is fabricated from an absent base (Constitution III.11).
    """
    if previous <= _GROWTH_EPSILON:
        return 0.0
    return sensitivity * (current - previous) / previous


def calculate_scissors_step(
    log_ratio: float,
    velocity: float,
    drive: float,
    *,
    reversion: float,
    damping: float,
    max_abs_log: float,
) -> tuple[float, float]:
    """One semi-implicit Euler step of the damped-driven scissors oscillator.

    ``x'' = drive - reversion * x - damping * x'`` in log-ratio space; the
    reversion term IS the law of value (gravitation of price to value,
    Capital Vol. III ch. 10). The velocity integrates first, then the
    position (semi-implicit — better energy behavior than explicit Euler at
    dt = 1). Hitting the ``max_abs_log`` rail zeroes the velocity so the
    clamp cannot pump energy into the system.

    :param log_ratio: Current ``ln(form / substance)`` — e.g. ln(price / value).
    :param velocity: Current d(log_ratio)/dt.
    :param drive: External drive (see :func:`calculate_growth_drive`).
    :param reversion: Restoring stiffness (>= 0).
    :param damping: Velocity damping (>= 0).
    :param max_abs_log: Hard clamp on ``|log_ratio|`` (> 0).
    :returns: ``(new_log_ratio, new_velocity)``.
    """
    acceleration = drive - reversion * log_ratio - damping * velocity
    new_velocity = velocity + acceleration
    new_log = log_ratio + new_velocity
    if new_log > max_abs_log:
        return max_abs_log, 0.0
    if new_log < -max_abs_log:
        return -max_abs_log, 0.0
    return new_log, new_velocity


def calculate_scissors_balance(log_ratio: float, *, scale: float) -> float:
    """Map a log ratio onto the opposition ``Balance`` in [-1, 1].

    Positive = the form pole (price) dominates its substance (value).

    :param log_ratio: ``ln(form / substance)``.
    :param scale: tanh scale (> 0); smaller saturates sooner.
    :returns: ``tanh(log_ratio / scale)``, clamped to [-1, 1] against float
        edge rounding.
    """
    return max(-1.0, min(1.0, math.tanh(log_ratio / scale)))
