"""Contract: MELTCalculator service protocol.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This contract defines the interface for computing national MELT (τ)
from BEA GDP and QCEW employment data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from babylon.economics.tensor import NoDataSentinel


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

        Sanity Ranges:
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
