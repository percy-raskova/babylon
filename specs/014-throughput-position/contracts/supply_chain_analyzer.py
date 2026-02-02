"""SupplyChainAnalyzer protocol contract.

Feature: 014-throughput-position
Date: 2026-02-02
Phase: 1 (Contracts)

This module defines the SupplyChainAnalyzer protocol for computing
supply chain depth and wage share proxy.

TVT Extension Reference:
    - D = Σ(employment × depth) / Σ employment
    - λ_proxy = avg_wage / τ_through
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from babylon.economics.tensor import NoDataSentinel
    from babylon.economics.throughput.types import WageShareEstimate


class SupplyChainAnalyzer(Protocol):
    """Protocol for supply chain depth and wage share analysis.

    Computes:
    - D: Employment-weighted average supply chain depth for a county
    - λ_proxy: Wage share proxy for industry-county combinations

    Supply chain depth indicates where a county sits in the value chain:
    - D < 1.5: Extraction-oriented (mining, agriculture)
    - D ≈ 2.0: Manufacturing/transformation
    - D ≈ 3.0: Logistics/coordination
    - D > 4.0: Service/financial coordination

    TVT Extension Reference:
        - D = Σ(employment[naics] × depth[naics]) / Σ employment
        - λ_proxy = avg_wage / τ_through

    Example:
        >>> analyzer = DefaultSupplyChainAnalyzer(qcew_source)
        >>> depth = analyzer.compute_depth("36061", 2022)  # Manhattan
        >>> print(f"Manhattan D = {depth:.2f}")
        Manhattan D = 4.3  # Finance-heavy

    See Also:
        :class:`ThroughputCalculator`: Uses D in ThroughputMetrics
        :const:`NAICS_DEPTH_MAPPING`: Source mapping for depth values
    """

    def compute_depth(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute employment-weighted supply chain depth for a county.

        Formula: D = Σ(employment[naics] × depth[naics]) / Σ employment

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            D (0.0-5.0 scale), or NoDataSentinel if insufficient data.

        Raises:
            ValueError: If computed D is outside [0.0, 5.0] (indicates bug)

        Example:
            >>> analyzer.compute_depth("56037", 2022)  # Sweetwater County, WY
            0.8  # Coal mining county - extraction-oriented
            >>> analyzer.compute_depth("36061", 2022)  # Manhattan
            4.3  # Finance/services - coordination-oriented
        """
        ...

    def get_naics_depth(self, naics: str) -> float | None:
        """Get supply chain depth value for a NAICS sector.

        Depth values are theoretically derived from position in supply chain:
        - 0: Primary extraction (mining, agriculture)
        - 1-2: Transformation (manufacturing)
        - 3: Logistics/wholesale coordination
        - 4: Service/retail realization
        - 5: Financial/management coordination

        Args:
            naics: 2-digit NAICS sector code (e.g., "52" for Finance)

        Returns:
            Depth value (0.0-5.0), or None if unknown sector

        Example:
            >>> analyzer.get_naics_depth("21")  # Mining
            0.0
            >>> analyzer.get_naics_depth("52")  # Finance
            5.0
            >>> analyzer.get_naics_depth("99")  # Unknown
            None
        """
        ...

    def compute_wage_share_proxy(
        self, fips: str, naics: str, year: int
    ) -> WageShareEstimate | NoDataSentinel:
        """Compute wage share proxy for an industry-county combination.

        Formula: λ_proxy = avg_wage / τ_through

        λ_proxy measures what fraction of throughput is captured as wages.
        This is a proxy for true institutional λ (which would require union
        density and bargaining power data).

        Expected values:
        - Retail (NAICS 44-45): λ ≈ 0.05-0.10 (low capture)
        - Transport (NAICS 48-49): λ ≈ 0.15-0.25 (union effect)
        - Finance (NAICS 52): λ ≈ 0.30-0.50 (high capture)

        Args:
            fips: 5-character county FIPS code
            naics: 2-digit NAICS sector code
            year: Calendar year

        Returns:
            WageShareEstimate container, or NoDataSentinel if data unavailable.

        Note:
            λ_proxy > 1.0 indicates data quality issue (wages exceed throughput).
            This can happen with suppressed GDP or employment data.

        Example:
            >>> estimate = analyzer.compute_wage_share_proxy("26163", "44", 2022)
            >>> estimate.lambda_proxy
            0.08  # Retail workers capture ~8% of throughput
        """
        ...

    def get_sector_employment(
        self, fips: str, year: int
    ) -> dict[str, int] | NoDataSentinel:
        """Get employment by NAICS sector for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Dict mapping NAICS codes to employment counts (suppressed
            sectors excluded), or NoDataSentinel if county data unavailable.

        Example:
            >>> emp = analyzer.get_sector_employment("26163", 2022)
            >>> emp
            {'44': 45000, '52': 25000, '31': 80000, ...}
        """
        ...


__all__ = ["SupplyChainAnalyzer"]
