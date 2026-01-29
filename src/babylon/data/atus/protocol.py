"""Protocol definition for reproductive labor data loaders.

This module defines the abstract protocol that all reproduction data loaders
must implement. The protocol enables dependency injection, allowing the
shadow labor service to work with mock data, ATUS data, or other sources.

**Protocol Pattern:**

The ReproductionLoaderProtocol follows the same adapter pattern used
elsewhere in the Babylon data layer (QCEWDataSource, BEADataSource).
This enables:
1. Testing with MockReproductionLoader (no external dependencies)
2. Future integration with real ATUS data
3. Alternative data sources (ILO, World Bank time-use surveys)

See Also:
    :mod:`babylon.data.atus.mock_loader`: Mock implementation.
    :mod:`babylon.economics.adapters`: Similar adapter patterns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from babylon.data.atus.models import ATUSHouseholdSummary


class ReproductionLoaderProtocol(ABC):
    """Abstract protocol for reproductive labor data loaders.

    All reproduction data loaders must implement this interface to work
    with the ShadowLaborService. This enables dependency injection and
    easy testing with mock data.

    **Required Methods:**
    - load_county_summary: Get reproductive labor hours for a county-year.
    - get_shadow_wage: Get replacement cost wage for shadow labor valuation.

    **Implementation Notes:**
    - Mock loader returns national averages (no county variation)
    - Future ATUS loader will provide county-level variation
    - Regional wage differences can be modeled in get_shadow_wage

    Example:
        >>> class MyLoader(ReproductionLoaderProtocol):
        ...     def load_county_summary(self, fips_code: str, year: int) -> ATUSHouseholdSummary:
        ...         # Load from database/API
        ...         ...
        ...     def get_shadow_wage(self, fips_code: str, year: int) -> float:
        ...         # Return BLS wage for the area
        ...         ...
    """

    @abstractmethod
    def load_county_summary(
        self,
        fips_code: str,
        year: int,
    ) -> ATUSHouseholdSummary:
        """Load reproductive labor hours summary for a county-year.

        Args:
            fips_code: 5-digit FIPS county code.
            year: Data year (>= 2003 for ATUS).

        Returns:
            ATUSHouseholdSummary with reproductive labor hours breakdown.

        Raises:
            ValueError: If FIPS code invalid or year out of range.
            DataNotFoundError: If no data available for county-year.
        """
        ...

    @abstractmethod
    def get_shadow_wage(
        self,
        fips_code: str,
        year: int,
    ) -> float:
        """Get shadow wage (replacement cost) for a county-year.

        The shadow wage represents the market cost to replace unpaid
        household labor. Default is BLS home health aide median wage.

        Args:
            fips_code: 5-digit FIPS county code.
            year: Data year for wage lookup.

        Returns:
            Hourly wage rate for shadow labor valuation (USD/hour).
        """
        ...


__all__ = [
    "ReproductionLoaderProtocol",
]
