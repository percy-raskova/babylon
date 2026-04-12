"""Data source and computation protocols for the Tri-County Economic Substrate.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Defines Protocol interfaces for dependency injection across all spatial
data sources and hex-level computation engines.

See Also:
    :mod:`babylon.economics.substrate.types`: Substrate type definitions.
    :mod:`babylon.economics.tensor_hierarchy.protocols`: Level 1/2 tensor protocols.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from babylon.config.defines import RentCircuitDefines
    from babylon.economics.substrate.types import (
        BoundaryFlowRegister,
        HexGrid,
        TractWeight,
    )
    from babylon.economics.tensor import NoDataSentinel

# =============================================================================
# SOURCE PROTOCOLS
# =============================================================================


@runtime_checkable
class SpatialSubstrateSource(Protocol):
    """Protocol for generating H3 hex meshes from county boundary polygons.

    Data Source:
        TIGER/Line Shapefiles (US Census Bureau).
        https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html

    Example:
        >>> source = DefaultSpatialSubstrateSource(tiger_loader)
        >>> grid = source.generate_hex_mesh(["26163", "26125", "26099"])
        >>> len(grid.hexes) > 0
        True
    """

    def generate_hex_mesh(self, county_fips_list: Sequence[str], resolution: int = 7) -> HexGrid:
        """Generate H3 hex mesh for given counties.

        Args:
            county_fips_list: FIPS codes for counties to cover.
            resolution: H3 resolution level (default 7).

        Returns:
            HexGrid with hex-to-county assignments and resolution hierarchy.

        Raises:
            ValueError: If county boundary data unavailable.
        """
        ...

    def get_county_boundary(self, county_fips: str) -> Any:
        """Return Shapely polygon for county boundary.

        Args:
            county_fips: 5-digit county FIPS code.

        Returns:
            Shapely Polygon or MultiPolygon geometry.
        """
        ...


@runtime_checkable
class TractDemographicSource(Protocol):
    """Protocol for loading tract-level Census ACS demographic data.

    Provides tract-level weights for allocating county economic aggregates
    down to individual H3 hexes.

    Data Source:
        American Community Survey (ACS) 5-year estimates.
        Tables B01003 (population), B23025 (employment), B19013 (income).

    Example:
        >>> source = DefaultTractDemographicSource(session_factory)
        >>> weights = source.get_tract_weights("26163", 2022)
        >>> isinstance(weights, dict)
        True
    """

    def get_tract_weights(
        self, county_fips: str, year: int
    ) -> dict[str, TractWeight] | NoDataSentinel:
        """Return tract-level demographic weights for allocation.

        Args:
            county_fips: 5-digit county FIPS code.
            year: ACS vintage year.

        Returns:
            Mapping of tract_geoid to TractWeight, or NoDataSentinel
            if ACS data unavailable for the requested county/year.
        """
        ...

    def get_tract_to_hex_mapping(
        self, county_fips: str, resolution: int = 7
    ) -> dict[str, list[str]]:
        """Return tract_geoid to list of H3 indices mapping.

        Args:
            county_fips: 5-digit county FIPS code.
            resolution: H3 resolution level (default 7).

        Returns:
            Dict mapping tract_geoid to list of H3 cell IDs contained
            within that tract.
        """
        ...


@runtime_checkable
class CommuterFlowSource(Protocol):
    """Protocol for loading county-to-county commuter flow data.

    Data Source:
        LEHD Origin-Destination Employment Statistics (LODES).
        https://lehd.ces.census.gov/data/

    Example:
        >>> source = DefaultCommuterFlowSource(session_factory)
        >>> flows = source.get_county_od_flows(["26163", "26125", "26099"], 2021)
        >>> all(count >= 0 for count in flows.values())
        True
    """

    def get_county_od_flows(
        self, county_fips_list: Sequence[str], year: int
    ) -> dict[tuple[str, str], int]:
        """Return county-to-county OD flows.

        Args:
            county_fips_list: Counties in the study area.
            year: LODES vintage year.

        Returns:
            Mapping of (home_county, work_county) to worker count.
            Includes flows to/from external counties.
        """
        ...

    def get_external_flows(
        self, county_fips_list: Sequence[str], year: int
    ) -> BoundaryFlowRegister:
        """Return aggregate flows crossing study area boundary.

        Args:
            county_fips_list: Counties defining the study area boundary.
            year: LODES vintage year.

        Returns:
            BoundaryFlowRegister with inflow, outflow, and net flow totals.
        """
        ...


# =============================================================================
# COMPUTATION PROTOCOLS
# =============================================================================


@runtime_checkable
class HexProductionComputer(Protocol):
    """Protocol for computing Volume I production at hex level.

    Computes per-hex surplus value and exploitation rate from department
    composition and capital stocks.

    Example:
        >>> computer = DefaultHexProductionComputer()
        >>> post_grid = computer.compute_production(grid)
        >>> abs(sum_capital(pre_grid) - sum_capital(post_grid)) < 1e-10
        True
    """

    def compute_production(self, grid: HexGrid) -> HexGrid:
        """Compute per-hex surplus value, exploitation rate.

        Conservation: sum(c+v+s) preserved within 1e-10.

        Args:
            grid: HexGrid with initial capital stocks and department shares.

        Returns:
            New HexGrid with updated surplus_value, profit_rate,
            and exploitation_rate fields.
        """
        ...


@runtime_checkable
class HexCirculationComputer(Protocol):
    """Protocol for computing Volume II wage circulation at hex level.

    Redistributes variable capital (wages) from production hexes to
    residence hexes via commuter OD matrix.

    Example:
        >>> computer = DefaultHexCirculationComputer()
        >>> od = computer.build_od_matrix(grid, commuter_source, 2021)
        >>> post_grid, boundary = computer.circulate_wages(grid, od)
    """

    def build_od_matrix(self, grid: HexGrid, commuter_source: CommuterFlowSource, year: int) -> Any:
        """Build hex-to-hex OD sparse matrix from county flows and tract weights.

        Args:
            grid: HexGrid with hex-to-county assignments.
            commuter_source: Source of county-level commuter flow data.
            year: LODES vintage year for flow data.

        Returns:
            Sparse matrix (N_hexes x N_hexes) with row-normalized commute
            shares. Type is ``scipy.sparse.csr_matrix`` but declared as
            ``Any`` to avoid hard dependency in protocol definition.
        """
        ...

    def circulate_wages(
        self, grid: HexGrid, od_matrix: Any
    ) -> tuple[HexGrid, BoundaryFlowRegister]:
        """Redistribute variable capital (v) from production to residence hexes.

        Conservation: sum(v) preserved within 1e-10.

        Args:
            grid: HexGrid with production-phase variable capital values.
            od_matrix: Sparse OD matrix from :meth:`build_od_matrix`.

        Returns:
            Tuple of (updated HexGrid with redistributed v,
            BoundaryFlowRegister tracking external flows).
        """
        ...


@runtime_checkable
class HexEqualizationComputer(Protocol):
    """Protocol for computing Volume III capital equalization at hex level.

    Migrates constant capital between hexes based on profit rate gradient,
    modeling the tendency of the rate of profit to equalize.

    Formula: ``delta_c[hex] = alpha * (r[hex] - r_avg) * c[hex]``

    Conservation: ``sum(delta_c) = 0`` by construction.

    Example:
        >>> computer = DefaultHexEqualizationComputer()
        >>> post_grid = computer.equalize_capital(grid, alpha=0.01)
    """

    def equalize_capital(
        self,
        grid: HexGrid,
        alpha: float = 0.01,
        rent_defines: RentCircuitDefines | None = None,
    ) -> HexGrid:
        """Migrate capital between hexes based on profit rate gradient.

        When ``rent_defines`` is provided and hexes carry a
        ``tenure_composition``, ground rent is extracted from ``v`` and
        ``s`` before capital migration (FR-010, Feature 043).

        Args:
            grid: HexGrid with current capital stocks and profit rates.
            alpha: Capital migration speed coefficient (default 0.01).
            rent_defines: Optional RentCircuitDefines for ground rent
                extraction. None disables rent (backward compatible).

        Returns:
            New HexGrid with updated constant capital stocks.
        """
        ...


@runtime_checkable
class ConservationChecker(Protocol):
    """Protocol for runtime conservation invariant checking.

    Verifies that capital quantities are preserved across operations,
    logging warnings when violations exceed tolerance (default 1e-10).

    Example:
        >>> checker = DefaultConservationChecker(tolerance=1e-10)
        >>> checker.check_total_capital(pre_grid, post_grid, "production")
        True
    """

    def check_total_capital(self, pre_grid: HexGrid, post_grid: HexGrid, operation: str) -> bool:
        """Check sum(c+v+s) conservation across an operation.

        Args:
            pre_grid: HexGrid state before the operation.
            post_grid: HexGrid state after the operation.
            operation: Name of the operation (for logging).

        Returns:
            True if conservation holds within tolerance, False otherwise.
        """
        ...

    def check_variable_capital(self, pre_grid: HexGrid, post_grid: HexGrid, operation: str) -> bool:
        """Check sum(v) conservation across an operation.

        Args:
            pre_grid: HexGrid state before the operation.
            post_grid: HexGrid state after the operation.
            operation: Name of the operation (for logging).

        Returns:
            True if conservation holds within tolerance, False otherwise.
        """
        ...

    def check_hierarchical_aggregation(self, grid: HexGrid, target_resolution: int) -> bool:
        """Check that r7 hex sums equal parent resolution values.

        Args:
            grid: HexGrid at base resolution 7.
            target_resolution: Parent resolution to check (5 or 6).

        Returns:
            True if aggregation is consistent, False otherwise.
        """
        ...


@runtime_checkable
class ResolutionAggregator(Protocol):
    """Protocol for multi-resolution spatial aggregation.

    Aggregates hex-level values to coarser H3 resolutions (r6, r5)
    using the parent-child hierarchy stored in HexGrid.

    Example:
        >>> aggregator = DefaultResolutionAggregator()
        >>> r6_totals = aggregator.aggregate(grid, target_resolution=6)
        >>> len(r6_totals) < len(grid.hexes)
        True
    """

    def aggregate(self, grid: HexGrid, target_resolution: int) -> dict[str, float]:
        """Sum hex values to parent resolution.

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to summed total capital.
        """
        ...

    def compute_weighted_profit_rate(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, float]:
        """Capital-weighted average profit rate at parent resolution.

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to capital-weighted profit rate.
        """
        ...


__all__ = [
    "CommuterFlowSource",
    "ConservationChecker",
    "HexCirculationComputer",
    "HexEqualizationComputer",
    "HexProductionComputer",
    "ResolutionAggregator",
    "SpatialSubstrateSource",
    "TractDemographicSource",
]
