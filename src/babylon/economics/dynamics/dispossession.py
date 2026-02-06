"""Composite dispossession risk calculator for class dynamics.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

Implements FR-003 and FR-006: Composite dispossession risk from foreclosure,
bankruptcy, and eviction rates with pathway-specific weighting per
research.md section 3a.

Weights:
    LA->P rate: 0.6*foreclosure + 0.3*bankruptcy + 0.1*eviction
    P->L component: 0.1*foreclosure + 0.3*bankruptcy + 0.6*eviction

See Also:
    :mod:`babylon.economics.dynamics.data_sources`: DispossessionCalculator protocol
    :mod:`babylon.economics.dynamics.hardcoded_data`: MVP data source
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.economics.dynamics.types import DispossessionRisk
from babylon.economics.tensor import NoDataSentinel

if TYPE_CHECKING:
    from babylon.economics.dynamics.data_sources import DispossessionDataSource

# Composite weighting factors (research.md §3a)
_FORECLOSURE_WEIGHT_LA_TO_P: float = 0.6
_BANKRUPTCY_WEIGHT_LA_TO_P: float = 0.3
_EVICTION_WEIGHT_LA_TO_P: float = 0.1

_FORECLOSURE_WEIGHT_P_TO_L: float = 0.1
_BANKRUPTCY_WEIGHT_P_TO_L: float = 0.3
_EVICTION_WEIGHT_P_TO_L: float = 0.6


class DefaultDispossessionCalculator:
    """Default implementation of DispossessionCalculator.

    Computes composite dispossession risk using three data sources
    with pathway-specific weights. Returns NoDataSentinel with
    distinct messages per missing data source (CHK030 pattern).

    Args:
        data_source: Provider of foreclosure, bankruptcy, eviction rates.

    Example:
        >>> calc = DefaultDispossessionCalculator(HardcodedNationalDispossessionSource())
        >>> result = calc.compute(fips="26163", year=2015)
        >>> isinstance(result, DispossessionRisk)
        True
    """

    def __init__(self, data_source: DispossessionDataSource) -> None:
        """Initialize with dispossession data source.

        Args:
            data_source: Provider of dispossession rates.
        """
        self._data_source = data_source

    def compute(self, fips: str, year: int) -> DispossessionRisk | NoDataSentinel:
        """Compute composite dispossession risk for a county-year.

        Returns distinct NoDataSentinel messages for each missing source
        to aid debugging.

        Args:
            fips: County FIPS code.
            year: Calendar year.

        Returns:
            DispossessionRisk or NoDataSentinel if any source unavailable.
        """
        foreclosure = self._data_source.get_foreclosure_rate(fips, year)
        if foreclosure is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Foreclosure rate unavailable for {fips}/{year}",
            )

        bankruptcy = self._data_source.get_bankruptcy_rate(fips, year)
        if bankruptcy is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Bankruptcy rate unavailable for {fips}/{year}",
            )

        eviction = self._data_source.get_eviction_rate(fips, year)
        if eviction is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Eviction rate unavailable for {fips}/{year}",
            )

        # Composite weighting per research.md §3a
        la_to_p = (
            _FORECLOSURE_WEIGHT_LA_TO_P * foreclosure
            + _BANKRUPTCY_WEIGHT_LA_TO_P * bankruptcy
            + _EVICTION_WEIGHT_LA_TO_P * eviction
        )
        p_to_l = (
            _FORECLOSURE_WEIGHT_P_TO_L * foreclosure
            + _BANKRUPTCY_WEIGHT_P_TO_L * bankruptcy
            + _EVICTION_WEIGHT_P_TO_L * eviction
        )

        return DispossessionRisk(
            fips=fips,
            year=year,
            foreclosure_risk=foreclosure,
            bankruptcy_risk=bankruptcy,
            eviction_risk=eviction,
            la_to_p_rate=la_to_p,
            p_to_l_component=p_to_l,
            foreclosure_available=True,
            bankruptcy_available=True,
            eviction_available=True,
        )


__all__ = ["DefaultDispossessionCalculator"]
