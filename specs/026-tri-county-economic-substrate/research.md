# Research: 026-tri-county-economic-substrate

**Date**: 2026-02-26
**Branch**: `026-tri-county-economic-substrate`

## R1: H3 Resolution 7 Hex Generation for Tri-County Area

**Decision**: Extend existing `H3GridLoader` to support resolution 7, using TIGER/Line shapefiles already loaded by `TIGERCountyLoader`.

**Rationale**: The H3 infrastructure (library v4.2, loader, bridge table, TIGER loader) already exists and is tested. Resolution 7 (~5.16 km²) produces manageable hex counts per county. The `h3.polygon_to_cells()` function handles polygon→hex conversion natively.

**Alternatives Considered**:
- **New standalone spatial module**: Rejected — duplicates existing H3GridLoader logic
- **ArcGIS real-time boundary fetching**: Rejected — offline TIGER shapefiles are more reliable and already downloaded
- **Resolution 8 (~0.74 km²)**: Rejected — would produce ~14,000+ hexes, exceeding performance budget

**Expected Hex Counts** (estimated from county areas):
- Wayne County (1,585 km²): ~307 hexes at res 7
- Oakland County (2,345 km²): ~454 hexes at res 7
- Macomb County (1,239 km²): ~240 hexes at res 7
- Total: ~1,001 hexes (lower bound; boundary hexes may increase to ~1,200-1,500)

**Key API**: `h3.polygon_to_cells(polygon, res=7)` — takes a GeoJSON polygon, returns set of H3 cell IDs.

## R2: Census ACS Tract-Level Data for Demographic Weighting

**Decision**: Add a new `tract_loader.py` to `src/babylon/data/census/` using the existing `CensusAPIClient` pattern. Fetch ACS 5-year estimates at tract level for the three counties.

**Rationale**: Current Census loader only supports county-level data. Tract-level demographics (population, employment, income) are essential for within-county spatial inequality modeling. Census API supports tract-level queries by specifying `for=tract:*&in=state:26&in=county:163,125,099`.

**Alternatives Considered**:
- **Block-level data**: Rejected — too granular, Census only provides block-level counts (not income/employment), and mapping blocks to hexes is excessive
- **Uniform allocation within county**: Rejected — destroys spatial inequality signal, violates spec requirement for historical accuracy
- **LODES block crosswalk as proxy**: Considered as supplementary — block crosswalk has lat/lon for employment disaggregation, but lacks income/demographic data

**ACS Tables Required** (tract-level, 3 counties):
- B01003: Total population
- B23025: Employment status (employed, unemployed, not in labor force)
- B19013: Median household income
- B19001: Income distribution brackets
- B24080: Class of worker (private, government, self-employed)

**Schema Addition**: `dim_census_tract` table with fields: tract_geoid (11-char FIPS), county_id (FK), population, employment, unemployment_rate, median_income, data_year.

## R3: LODES Origin-Destination Disaggregation to Hex Level

**Decision**: Two-stage disaggregation: (1) county-to-county OD flows from existing `fact_lodes_commuter_flow`, (2) distribute to hex-to-hex using tract-level employment shares within each county.

**Rationale**: LODES publishes block-to-block OD data, but loading and processing millions of block pairs is prohibitively expensive. County-to-county flows (~9 pairs for 3 counties + external) are already loaded. Within-county distribution uses tract employment weights (from R2) to allocate commuters to hexes proportionally.

**Alternatives Considered**:
- **Block-level LODES OD**: Rejected — millions of records, processing time would exceed performance budget, and mapping every block to H3 hex is complex
- **Tract-level LODES OD**: Considered — Census publishes tract-level OD aggregates, but still ~thousands of pairs. Could be a future enhancement.
- **Gravity model**: Rejected — violates Constitution III.1 (No Magic Constants)

**Conservation Proof**:
Given county-to-county flow F(county_A, county_B) = N workers:
- Distribute N proportionally across hexes in county_B by employment weight
- Sum of hex-level flows from county_A hexes to county_B hexes = N
- Total flows preserved by construction

**Sparse Matrix Representation**: For ~1,500 hexes, the OD matrix is ~1,500 × 1,500 = 2.25M entries, but highly sparse (most hex pairs have zero flow). Use `scipy.sparse.csr_matrix` for memory efficiency and fast matrix-vector multiplication.

## R4: Volume I Production at Hex Level

**Decision**: Per-hex production is a decomposition of county-level ValueTensor4x3 using tract-level employment and wage weights. Each hex computes local s/v based on its allocated economic composition.

**Rationale**: Volume I production logic (Features 011, 021) operates on county-level ValueTensor4x3 and CountyEconomicState. For hex-level production, we decompose county aggregates to hexes using the same weights used for hydration (R2). The exploitation rate s/v at hex level varies based on departmental composition (manufacturing vs service hexes).

**Alternatives Considered**:
- **Independent hex-level production from raw data**: Rejected — no hex-level GDP/employment data exists; all data originates at county level or coarser
- **Uniform s/v across hexes within county**: Rejected — destroys spatial variation, violates Macomb manufacturing concentration requirement

**Decomposition Method**:
1. County has ValueTensor4x3 with (c, v, s) per department
2. Each hex has employment weights by department (from NAICS sector allocation)
3. Hex (c, v, s) = county (c, v, s) × hex_employment_share_in_department
4. Hex s/v = hex_s / hex_v (varies by departmental mix)

## R5: Volume III Equalization Mechanism

**Decision**: Per-tick capital migration between hexes using a simple profit-rate-gradient flow: capital moves from hexes with below-average profit rate to hexes with above-average profit rate, scaled by a migration coefficient.

**Rationale**: Volume III equalization (Feature 024) establishes that capital flows toward higher profit rates, tending to equalize the rate of profit across the economy. At hex level, this manifests as capital stock shifting from low-profit to high-profit hexes over time.

**Alternatives Considered**:
- **Full general equilibrium solver**: Rejected — computationally expensive, unnecessary for demonstrating directional capital flow
- **Discrete jump to average**: Rejected — too aggressive, would eliminate spatial variation immediately
- **Continuous differential equation**: Rejected — would require very small time steps, conflicts with tick-based simulation

**Migration Formula**:
```
delta_c[hex] = alpha * (r[hex] - r_avg) * c[hex]
```
Where:
- alpha = migration speed coefficient (calibrated to produce observable shift over 260 ticks)
- r[hex] = local profit rate s/(c+v) at hex
- r_avg = metro-wide average profit rate (weighted by hex capital stock)
- c[hex] = current capital stock at hex

**Conservation**: sum(delta_c) = alpha * sum((r[hex] - r_avg) * c[hex]) = alpha * (sum(r[hex]*c[hex]) - r_avg * sum(c[hex])) = alpha * (r_avg * C_total - r_avg * C_total) = 0. Capital migration is zero-sum by construction.

## R6: Performance Optimization Strategy

**Decision**: Vectorized NumPy/SciPy operations with sparse matrix representation for LODES OD flows.

**Rationale**: The performance budget (5.0s for ~1,500-2,500 hexes) requires avoiding Python loops over individual hexes. NumPy vectorization handles Volume I and III efficiently. Volume II (LODES matrix multiplication) is the dominant cost but scipy.sparse handles it well.

**Profiling Estimates**:
- Volume I (vectorized multiply): ~0.05s (N hex array operations)
- Volume II (sparse matmul): ~1-2s (csr_matrix @ dense vector, N×N sparse with ~5% density)
- Volume III (vectorized gradient): ~0.05s (N hex array operations)
- Conservation checks: ~0.01s (3 summations over N hexes)
- Aggregation (r7→r6→r5): ~0.05s (group-by-parent summation)
- Total estimate: ~1.2-2.2s (well within 5.0s budget)

**Alternatives Considered**:
- **GPU acceleration (CuPy)**: Rejected — unnecessary for N < 3,000; adds dependency complexity
- **Numba JIT compilation**: Considered for future if performance is tight; not needed initially
- **Parallel processing**: Rejected — GIL-limited for NumPy operations; multiprocessing overhead exceeds benefit for N < 3,000
