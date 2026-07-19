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
    :returns: The log-space anchor, or a :class:`NoDataSentinel` naming the
        specific absence. Never a fabricated zero.
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
    if stock.total_claims <= 0.0:
        return NoDataSentinel(
            fips=NATIONAL_FIPS,
            year=stock.year,
            reason=(
                f"fictitious_anchor: zero total_claims for {stock.year}, "
                "financialization ratio undefined"
            ),
        )
    return math.log(stock.ratio_to_real(real_output))
