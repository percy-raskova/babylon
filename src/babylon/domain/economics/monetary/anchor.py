"""Monetary anchor: real federal data calibrating the scissors oscillator.

Design: ``docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md`` §3.3,
owner decision D1 — *Volume III calibrates; the scissors integrates.*

Where real data exists (2010-2024) these functions expose the log-space target
and the serviceability tightener the oscillator is pulled toward. Past the data
horizon — roughly 85% of a 2010-2109 campaign — they return
:class:`~babylon.domain.economics.tensor.NoDataSentinel` and the oscillator
continues unchanged on its own endogenous dynamics. **Absence is the normal
steady state, not an error path** (Constitution III.11: no fabricated zeros, no
substituted defaults).

Pure functions of their arguments: no RNG, no wall clock, no I/O. This module
lives in ``domain/`` and imports nothing from ``engine/``; the engine reads it.
"""

from __future__ import annotations

import math
from typing import Final

from babylon.domain.economics.credit.types import FictitiousCapitalStock
from babylon.domain.economics.distribution.types import SurplusValueDistribution
from babylon.domain.economics.tensor import NoDataSentinel

NATIONAL_FIPS: Final[str] = "USA"
"""FIPS placeholder for national-scope sentinels.

Matches the convention already used by
:class:`~babylon.domain.economics.monetary.converter.DefaultValueBasisConverter`.
"""

UNKNOWN_YEAR: Final[int] = 0
"""Year marker used when the absent input is the thing that carries the year.

Not a data value. When the stock or distribution itself is ``None`` there is no
year to report, and fabricating a plausible one would violate III.11.
"""


def fictitious_anchor(
    stock: FictitiousCapitalStock | None,
    real_output: float | None,
) -> float | NoDataSentinel:
    """Log-space target the fictitious oscillator is pulled toward.

    ``log(stock.ratio_to_real(real_output))`` — the real financialization ratio
    expressed in the same log space the scissors integrates in.

    :param stock: Published national fictitious capital stock, or ``None`` when
        no stock reached the graph this tick (the normal case past 2024).
    :param real_output: Real output the claims are drawn against, or ``None``
        when no output observable exists.
    :returns: The finite log-space anchor, or a :class:`NoDataSentinel` naming
        the specific absence. Never a fabricated zero, never ``inf``/``nan``.
    """
    if stock is None:
        return NoDataSentinel(
            fips=NATIONAL_FIPS,
            year=UNKNOWN_YEAR,
            reason="fictitious_anchor: no FictitiousCapitalStock published this tick",
        )
    if real_output is None:
        return NoDataSentinel(
            fips=NATIONAL_FIPS,
            year=stock.year,
            reason=f"fictitious_anchor: no real output observable for {stock.year}",
        )
    if not math.isfinite(real_output) or real_output <= 0.0:
        return NoDataSentinel(
            fips=NATIONAL_FIPS,
            year=stock.year,
            reason=(
                f"fictitious_anchor: non-positive real output ({real_output}) "
                f"for {stock.year}; log-ratio undefined"
            ),
        )
    ratio = stock.ratio_to_real(real_output)
    if not math.isfinite(ratio) or ratio <= 0.0:
        return NoDataSentinel(
            fips=NATIONAL_FIPS,
            year=stock.year,
            reason=(
                f"fictitious_anchor: zero total claims (total_claims) for "
                f"{stock.year}; log-ratio undefined"
            ),
        )
    return math.log(ratio)


def serviceability_anchor(
    distribution: SurplusValueDistribution | None,
) -> float | NoDataSentinel:
    """Real interest burden ``i / s`` — how much surplus is already spoken for.

    Tightens :func:`babylon.formulas.market.calculate_serviceable_divergence`
    beyond its existing profit-rate slope: a financialised county services a
    smaller claims structure at the same rate of profit. Vol. III part 3 (the
    falling rate) meeting part 5 (fictitious capital).

    Guards the denominator itself rather than delegating to
    :attr:`SurplusValueDistribution.financialization_share`, which returns a
    silent ``0.0`` at zero surplus — indistinguishable from a county that
    genuinely pays no interest (Constitution III.11).

    Both ``total_surplus_produced`` and ``interest_payments`` are constrained
    only by ``ge=0`` (no upper bound, no ``allow_inf_nan=False``), so ``+inf``
    is a valid field value and a bare ``<= 0.0`` comparison is not a
    finiteness guard. Mirrors :func:`fictitious_anchor`'s two-guard shape:
    the denominator is checked for finiteness before dividing, and the
    computed ratio is checked again before it leaves the function — never a
    fabricated zero (``x / inf``) or a raw ``inf`` escaping the
    ``float | NoDataSentinel`` contract.

    :param distribution: Published surplus distribution, or ``None`` when no
        distribution was computed this tick (the normal case past 2024).
    :returns: The interest burden as a fraction of surplus produced, or a
        :class:`NoDataSentinel` naming the specific absence.
    """
    if distribution is None:
        return NoDataSentinel(
            fips=NATIONAL_FIPS,
            year=UNKNOWN_YEAR,
            reason="serviceability_anchor: no SurplusValueDistribution computed this tick",
        )
    surplus = distribution.total_surplus_produced
    if not math.isfinite(surplus) or surplus <= 0.0:
        if math.isfinite(surplus):
            reason = (
                f"serviceability_anchor: zero surplus produced in "
                f"{distribution.fips_code} {distribution.year}; "
                "interest burden undefined"
            )
        else:
            reason = (
                f"serviceability_anchor: non-finite surplus produced ({surplus}) "
                f"in {distribution.fips_code} {distribution.year}; "
                "interest burden undefined"
            )
        return NoDataSentinel(
            fips=distribution.fips_code,
            year=distribution.year,
            reason=reason,
        )
    ratio = distribution.interest_payments / surplus
    if not math.isfinite(ratio):
        return NoDataSentinel(
            fips=distribution.fips_code,
            year=distribution.year,
            reason=(
                f"serviceability_anchor: non-finite interest burden "
                f"({distribution.interest_payments} / {surplus}) in "
                f"{distribution.fips_code} {distribution.year}; "
                "interest burden undefined"
            ),
        )
    return ratio
