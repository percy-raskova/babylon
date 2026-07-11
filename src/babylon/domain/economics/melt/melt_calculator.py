"""MELTCalculator service for computing national MELT (τ).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This module implements the MELT (Monetary Expression of Labor Time) computation
per TVT Axiom B3: τ = GDP / L.

TVT Axiom Reference:
    - B3: MELT (τ) bridges labor-time and money-price domains
    - B4: Single-System Temporalism - one τ per currency zone
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from babylon.domain.economics.protocol_kit import CachedSource
from babylon.domain.economics.tensor import NoDataSentinel
from babylon.formulas.constants import HOURS_PER_YEAR

if TYPE_CHECKING:
    from babylon.domain.economics.melt.data_sources import BEADataSource, QCEWDataSource

# Constants
MIN_YEAR: int = 2010
MAX_YEAR: int = 2024

# Sanity range constants (empirically derived from BEA/QCEW 2010-2024)
EXPECTED_TAU_MIN: float = 55.0
EXPECTED_TAU_MAX: float = 75.0
WARNING_TAU_MIN: float = 40.0
WARNING_TAU_MAX: float = 100.0
FAIL_TAU_MIN: float = 20.0
FAIL_TAU_MAX: float = 200.0


class MELTCalculator(Protocol):
    """Protocol for MELT (Monetary Expression of Labor Time) computation.

    MELT (τ) bridges the labor-time and money-price domains per TVT Axiom B3:

        τ = GDP / L

    where:
        - GDP = National Gross Domestic Product (current dollars, from BEA)
        - L = Total labor hours = employment × 2080 hours/year (from QCEW)

    The resulting τ represents dollars per labor-hour at the national level.
    Within a single currency zone, there is ONE national MELT (no regional
    variation) because PPP = MER domestically (no ERDI differential).

    TVT Axiom Reference:
        - B3: τ = GDP / L (definition)
        - B4: Single τ per currency zone (no regional MELT)

    Example:
        >>> calculator = DefaultMELTCalculator(bea_source, qcew_source)
        >>> tau = calculator.get_melt(2022)
        >>> if tau:  # Not NoDataSentinel
        ...     print(f"MELT for 2022: ${tau:.2f}/labor-hour")
        MELT for 2022: $65.00/labor-hour

    See Also:
        :class:`NationalParameters`: Uses τ as a field
        :class:`BasketVisibilityCalculator`: Companion service for γ_basket
    """

    def get_melt(self, year: int) -> float | NoDataSentinel:
        """Compute national MELT for a given year.

        Formula: τ = GDP / (employment × 2080)

        Args:
            year: Calendar year (2010-2024 for available data)

        Returns:
            τ in $/labor-hour if data available, or NoDataSentinel with
            descriptive reason if data unavailable.

        Raises:
            ValueError: If year is outside the supported range [2010, 2030]

        Example:
            >>> tau = calculator.get_melt(2022)
            >>> tau
            65.0
            >>> tau = calculator.get_melt(2005)
            >>> tau.reason
            'Year 2005 outside data range [2010, 2024]'
        """
        ...

    def validate_melt(self, tau: float) -> tuple[bool, str | None]:
        """Validate MELT against sanity ranges per FR-010.

        Sanity Ranges (empirically derived from BEA/QCEW 2010-2024):
            - Expected: $55-75/hour (typical US MELT 2010-2024)
            - Warning: $40-100/hour (unusual but possible)
            - Fail: <$20 or >$200/hour (indicates error)

        Args:
            tau: MELT value to validate ($/labor-hour)

        Returns:
            Tuple of (valid, message):
            - valid=True, message=None: Within expected range
            - valid=True, message=str: Warning (unusual value)
            - valid=False, message=str: Fail (invalid value)

        Example:
            >>> calculator.validate_melt(65.0)
            (True, None)
            >>> calculator.validate_melt(45.0)
            (True, 'WARNING: MELT τ=45.0 outside expected range [55, 75]')
            >>> calculator.validate_melt(15.0)
            (False, 'MELT τ=15.0 outside valid range [20, 200]')
        """
        ...

    @property
    def data_range(self) -> tuple[int, int]:
        """Return the valid year range for MELT computation.

        Returns:
            Tuple of (min_year, max_year) for available data

        Example:
            >>> calculator.data_range
            (2010, 2024)
        """
        ...


class DefaultMELTCalculator(CachedSource[float]):
    """Default implementation of MELTCalculator using BEA GDP and QCEW employment.

    This calculator computes τ = GDP / (employment × 2080) using real data
    sources. It follows the service pattern established by CapitalStockCalculator
    in Feature 012.

    Args:
        bea_source: Data source for GDP values
        qcew_source: Data source for employment values

    TVT Axiom Reference:
        - B3: τ = GDP / L

    Example:
        >>> from babylon.domain.economics.melt import DefaultMELTCalculator
        >>> calculator = DefaultMELTCalculator(bea_source, qcew_source)
        >>> tau = calculator.get_melt(2022)
        >>> print(f"τ = ${tau:.2f}/labor-hour")
        τ = $65.00/labor-hour
    """

    def __init__(
        self,
        bea_source: BEADataSource,
        qcew_source: QCEWDataSource,
    ) -> None:
        """Initialize with data sources.

        Args:
            bea_source: Data source for GDP values
            qcew_source: Data source for employment values
        """
        super().__init__()
        self._bea_source = bea_source
        self._qcew_source = qcew_source

    def get_melt(self, year: int) -> float | NoDataSentinel:
        """Compute national MELT for a given year.

        Formula: τ = GDP / (employment × 2080)

        CHK030: Returns distinct error messages for GDP vs employment data:
            - "GDP data unavailable for year {year}"
            - "Employment data unavailable for year {year}"

        Args:
            year: Calendar year (2010-2024 for available data)

        Returns:
            τ in $/labor-hour if data available, or NoDataSentinel with
            descriptive reason if data unavailable.
        """
        # Validate year range
        if year < MIN_YEAR or year > MAX_YEAR:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Year {year} outside data range [{MIN_YEAR}, {MAX_YEAR}]",
            )

        # Get GDP (CHK030: distinct error message for GDP)
        gdp = self._bea_source.get_gdp(year)
        if gdp is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"GDP data unavailable for year {year}",
            )

        # Get employment (CHK030: distinct error message for employment)
        employment = self._qcew_source.get_national_employment(year)
        if employment is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Employment data unavailable for year {year}",
            )

        # Avoid division by zero
        if employment == 0:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Zero employment for year {year}",
            )

        # Compute τ = GDP / (employment × 2080)
        total_labor_hours = employment * HOURS_PER_YEAR
        tau = gdp / total_labor_hours

        return tau

    def validate_melt(self, tau: float) -> tuple[bool, str | None]:
        """Validate MELT against sanity ranges per FR-010.

        Args:
            tau: MELT value to validate ($/labor-hour)

        Returns:
            Tuple of (valid, message)
        """
        # Fail range: <$20 or >$200/hour
        if tau < FAIL_TAU_MIN or tau > FAIL_TAU_MAX:
            return (
                False,
                f"MELT τ={tau:.1f} outside valid range [{FAIL_TAU_MIN}, {FAIL_TAU_MAX}]",
            )

        # Warning range: $40-100/hour but outside expected
        if tau < EXPECTED_TAU_MIN or tau > EXPECTED_TAU_MAX:
            return (
                True,
                f"WARNING: MELT τ={tau:.1f} outside expected range "
                f"[{EXPECTED_TAU_MIN}, {EXPECTED_TAU_MAX}]",
            )

        # Expected range: $55-75/hour
        return (True, None)

    @property
    def data_range(self) -> tuple[int, int]:
        """Return the valid year range for MELT computation.

        Returns:
            Tuple of (min_year, max_year) for available data
        """
        return (MIN_YEAR, MAX_YEAR)


__all__ = ["DefaultMELTCalculator", "MELTCalculator"]
