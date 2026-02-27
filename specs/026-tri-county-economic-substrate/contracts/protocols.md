# Protocol Contracts: 026-tri-county-economic-substrate

**Date**: 2026-02-26

## Overview

All protocols follow the established `Protocol + Default` pattern. Each protocol is `@runtime_checkable` for duck-typing support. Default implementations read from SQLite 3NF schema. Mock implementations are provided in test conftest for unit tests.

## Source Protocols

### SpatialSubstrateSource

Provides H3 hex mesh generation from county boundary polygons.

```python
@runtime_checkable
class SpatialSubstrateSource(Protocol):
    def generate_hex_mesh(
        self, county_fips_list: Sequence[str], resolution: int = 7
    ) -> HexGrid:
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
        """Return Shapely polygon for county boundary."""
        ...
```

**Default**: `DefaultSpatialSubstrateSource` — reads TIGER shapefiles via `TIGERCountyLoader`, uses `h3.polygon_to_cells()`.

### TractDemographicSource

Provides tract-level Census ACS demographic data for allocation weighting.

```python
@runtime_checkable
class TractDemographicSource(Protocol):
    def get_tract_weights(
        self, county_fips: str, year: int
    ) -> dict[str, TractWeight] | NoDataSentinel:
        """Return tract-level demographic weights for allocation.

        Args:
            county_fips: 5-digit county FIPS code.
            year: ACS vintage year.

        Returns:
            Mapping of tract_geoid to TractWeight, or NoDataSentinel.
        """
        ...

    def get_tract_to_hex_mapping(
        self, county_fips: str, resolution: int = 7
    ) -> dict[str, list[str]]:
        """Return tract_geoid to list of H3 indices mapping."""
        ...
```

**Default**: `DefaultTractDemographicSource` — reads from `dim_census_tract` + `bridge_tract_h3`.

### CommuterFlowSource

Provides county-to-county commuter flow data for hex-level disaggregation.

```python
@runtime_checkable
class CommuterFlowSource(Protocol):
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
        """Return aggregate flows crossing study area boundary."""
        ...
```

**Default**: `DefaultCommuterFlowSource` — reads from `fact_lodes_commuter_flow`.

## Computation Protocols

### HexProductionComputer

Computes Volume I production at hex level.

```python
@runtime_checkable
class HexProductionComputer(Protocol):
    def compute_production(self, grid: HexGrid) -> HexGrid:
        """Compute per-hex surplus value, exploitation rate.

        Conservation: sum(c+v+s) preserved within 1e-10.

        Returns:
            New HexGrid with updated (s, v, c, profit_rate, exploitation_rate).
        """
        ...
```

**Default**: `DefaultHexProductionComputer` — vectorized NumPy on hex arrays.

### HexCirculationComputer

Computes Volume II wage circulation at hex level.

```python
@runtime_checkable
class HexCirculationComputer(Protocol):
    def build_od_matrix(
        self, grid: HexGrid, commuter_source: CommuterFlowSource, year: int
    ) -> sparse.csr_matrix:
        """Build hex-to-hex OD sparse matrix from county flows + tract weights.

        Returns:
            Sparse matrix (N_hexes x N_hexes) with row-normalized commute shares.
        """
        ...

    def circulate_wages(
        self, grid: HexGrid, od_matrix: sparse.csr_matrix
    ) -> tuple[HexGrid, BoundaryFlowRegister]:
        """Redistribute variable capital (v) from production to residence hexes.

        Conservation: sum(v) preserved within 1e-10.

        Returns:
            (updated HexGrid, BoundaryFlowRegister for external flows).
        """
        ...
```

**Default**: `DefaultHexCirculationComputer` — scipy sparse matrix multiplication.

### HexEqualizationComputer

Computes Volume III capital equalization at hex level.

```python
@runtime_checkable
class HexEqualizationComputer(Protocol):
    def equalize_capital(
        self, grid: HexGrid, alpha: float = 0.01
    ) -> HexGrid:
        """Migrate capital between hexes based on profit rate gradient.

        Formula: delta_c[hex] = alpha * (r[hex] - r_avg) * c[hex]
        Conservation: sum(delta_c) = 0 by construction.

        Returns:
            New HexGrid with updated capital stocks.
        """
        ...
```

**Default**: `DefaultHexEqualizationComputer` — vectorized NumPy gradient computation.

### ConservationChecker

Runtime conservation invariant checking.

```python
@runtime_checkable
class ConservationChecker(Protocol):
    def check_total_capital(
        self, pre_grid: HexGrid, post_grid: HexGrid, operation: str
    ) -> bool:
        """Check sum(c+v+s) conservation. Log warning if violated."""
        ...

    def check_variable_capital(
        self, pre_grid: HexGrid, post_grid: HexGrid, operation: str
    ) -> bool:
        """Check sum(v) conservation. Log warning if violated."""
        ...

    def check_hierarchical_aggregation(
        self, grid: HexGrid, target_resolution: int
    ) -> bool:
        """Check r7 sums = r6/r5 parent values. Log warning if violated."""
        ...
```

**Default**: `DefaultConservationChecker` — logs via `logging.getLogger(__name__)`.

### ResolutionAggregator

Multi-resolution aggregation.

```python
@runtime_checkable
class ResolutionAggregator(Protocol):
    def aggregate(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, float]:
        """Sum hex values to parent resolution.

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: 5 or 6.

        Returns:
            Mapping of parent h3_index to summed total capital.
        """
        ...

    def compute_weighted_profit_rate(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, float]:
        """Capital-weighted average profit rate at parent resolution."""
        ...
```

**Default**: `DefaultResolutionAggregator` — group-by-parent summation via resolution hierarchy.
