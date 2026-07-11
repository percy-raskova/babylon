"""Hardcoded national dispossession rates for the MVP implementation.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

This module provides national-average dispossession rates by year (2007-2020)
from ATTOM/CoreLogic (foreclosure), US Courts (bankruptcy), and Eviction Lab.
These are hardcoded behind the DispossessionDataSource protocol to enable
future replacement with per-county data loaders (FE-007).

See Also:
    :mod:`babylon.domain.economics.dynamics.data_sources`: DispossessionDataSource protocol
    ``specs/016-class-dynamics-engine/research.md``: Section 3 data tables
"""

from __future__ import annotations

# Foreclosure rates by year (% of all households, ATTOM/CoreLogic)
# Expressed as decimals (e.g., 1.8% = 0.018)
_FORECLOSURE_RATES: dict[int, float] = {
    2007: 0.018,
    2008: 0.023,
    2009: 0.028,
    2010: 0.046,
    2011: 0.035,
    2012: 0.025,
    2013: 0.015,
    2014: 0.010,
    2015: 0.006,
    2016: 0.005,
    2017: 0.005,
    2018: 0.005,
    2019: 0.004,
    2020: 0.0015,
}

# Bankruptcy rates by year (personal filings per household, US Courts)
_BANKRUPTCY_RATES: dict[int, float] = {
    2007: 0.007,
    2008: 0.008,
    2009: 0.010,
    2010: 0.013,
    2011: 0.011,
    2012: 0.009,
    2013: 0.008,
    2014: 0.007,
    2015: 0.006,
    2016: 0.006,
    2017: 0.006,
    2018: 0.006,
    2019: 0.006,
    2020: 0.004,
}

# Eviction rates by year (% of renter households, Eviction Lab)
_EVICTION_RATES: dict[int, float] = {
    2007: 0.064,
    2008: 0.065,
    2009: 0.064,
    2010: 0.070,
    2011: 0.072,
    2012: 0.070,
    2013: 0.067,
    2014: 0.066,
    2015: 0.063,
    2016: 0.061,
    2017: 0.062,
    2018: 0.062,
    2019: 0.060,
    2020: 0.020,
}


class HardcodedNationalDispossessionSource:
    """Hardcoded national dispossession rates for MVP implementation.

    Returns national averages regardless of FIPS code. Returns None
    for years outside 2007-2020 range.

    Example:
        >>> source = HardcodedNationalDispossessionSource()
        >>> source.get_foreclosure_rate("26163", 2010)
        0.046
        >>> source.get_foreclosure_rate("26163", 2005) is None
        True
    """

    def get_foreclosure_rate(self, _fips: str, year: int) -> float | None:
        """Get national foreclosure rate for a year.

        Args:
            _fips: County FIPS code (ignored in MVP).
            year: Calendar year.

        Returns:
            Foreclosure rate or None if year out of range.
        """
        return _FORECLOSURE_RATES.get(year)

    def get_bankruptcy_rate(self, _fips: str, year: int) -> float | None:
        """Get national bankruptcy rate for a year.

        Args:
            _fips: County FIPS code (ignored in MVP).
            year: Calendar year.

        Returns:
            Bankruptcy rate or None if year out of range.
        """
        return _BANKRUPTCY_RATES.get(year)

    def get_eviction_rate(self, _fips: str, year: int) -> float | None:
        """Get national eviction rate for a year.

        Args:
            _fips: County FIPS code (ignored in MVP).
            year: Calendar year.

        Returns:
            Eviction rate or None if year out of range.
        """
        return _EVICTION_RATES.get(year)


__all__ = ["HardcodedNationalDispossessionSource"]
