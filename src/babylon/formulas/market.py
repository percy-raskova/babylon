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
    "calculate_correction_snap",
    "calculate_ema",
    "calculate_growth_drive",
    "calculate_overhang",
    "calculate_scissors_balance",
    "calculate_scissors_step",
    "calculate_serviceable_divergence",
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


def calculate_serviceable_divergence(
    profit_rate: float | None,
    *,
    base: float,
    slope: float,
    interest_burden: float | None = None,
    interest_slope: float = 0.0,
) -> float:
    """Log fictitious/real divergence the rate of profit can service (ADR078).

    ``base + slope * max(profit_rate, 0) - interest_slope * max(interest_burden, 0)``,
    floored at 0: a healthy rate of profit carries a larger claims
    structure; its FALL is what turns an existing bubble into an unpayable
    one — Vol. III part 3 (the falling rate) meeting part 5 (fictitious
    capital). A financialised county's own interest burden (interest
    payments relative to capital, U6) tightens the same threshold
    independent of the profit rate — a second, orthogonal claim on the
    credit system's tolerance. A loss-making, debt-free economy still
    services the base (the credit system's intrinsic tolerance is a floor,
    not a debt).

    :param profit_rate: Realized rate of profit, or ``None`` when no profit
        observable exists this tick — the base alone is used (honest
        absence, Constitution III.11; no rate is fabricated).
    :param base: Serviceable log-divergence at zero profit and zero
        interest burden (>= 0).
    :param slope: Additional serviceable log-divergence per unit profit rate.
    :param interest_burden: Interest-payments-to-capital ratio, or ``None``
        when no territory carries the accounting pair — the term drops out
        entirely (honest absence, III.11), matching pre-U6 behavior exactly.
    :param interest_slope: Serviceable log-divergence LOST per unit
        interest burden (a ``MarketDefines.correction_interest_slope``
        coefficient).
    :returns: The serviceable log-divergence, floored at 0.
    """
    profit_term = 0.0 if profit_rate is None else slope * max(profit_rate, 0.0)
    interest_term = 0.0 if interest_burden is None else interest_slope * max(interest_burden, 0.0)
    return max(base + profit_term - interest_term, 0.0)


def calculate_overhang(fictitious_log: float, serviceable: float) -> float:
    """Unserviceable excess of the fictitious log-ratio (the crisis trigger).

    :param fictitious_log: ``ln(fictitious capitalization / real)``.
    :param serviceable: Output of :func:`calculate_serviceable_divergence`.
    :returns: ``max(fictitious_log - serviceable, 0)`` — undervalued claims
        (a negative log) never overhang; only excess claims trigger the snap.
    """
    return max(fictitious_log - serviceable, 0.0)


def calculate_correction_snap(
    log_ratio: float, velocity: float, *, severity: float
) -> tuple[float, float]:
    """The correction: one violent re-identification of form with substance.

    Closes ``severity`` of the log ratio toward par and kills UPWARD momentum;
    downward momentum survives (panic overshoot is real — the crash does not
    stop at equilibrium). Antisymmetric by construction: a negative ratio
    snaps toward zero from below under the same law.

    :param log_ratio: Current ``ln(form / substance)``.
    :param velocity: Current d(log_ratio)/dt.
    :param severity: Fraction of the ratio closed in one snap, in [0, 1].
    :returns: ``(log_ratio * (1 - severity), min(velocity, 0.0))``.
    """
    return log_ratio * (1.0 - severity), min(velocity, 0.0)
