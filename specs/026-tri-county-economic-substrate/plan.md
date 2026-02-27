# Implementation Plan: Multi-Resolution Economic Tensor Substrate (Vols I-III Integration)

**Branch**: `026-tri-county-economic-substrate` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/026-tri-county-economic-substrate/spec.md`

## Summary

Integrate Capital Volumes I (Production), II (Circulation), and III (Equalization) onto an H3 resolution 7 spatial mesh covering Wayne, Oakland, and Macomb counties. County-level QCEW data is allocated to ~1,600-2,500 hex cells using Census ACS tract-level demographic weights. Wages circulate between hexes via LODES commute flows. Capital equalizes across hexes based on local profit rates. Conservation invariants are checked at runtime with logged warnings.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models), NumPy (tensor ops), SciPy (sparse matrices), h3 4.2 (spatial indexing), geopandas (shapefiles), shapely (geometry), SQLAlchemy 2.x (ORM), NetworkX 3.x (graph)
**Storage**: SQLite (`data/sqlite/marxist-data-3NF.sqlite` via `NormalizedBase` ORM); in-memory for simulation state
**Testing**: pytest with markers (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.math`)
**Target Platform**: Linux development workstation (8+ cores, 16+ GB RAM)
**Project Type**: Single Python package (`src/babylon/`)
**Performance Goals**: Full simulation tick (Volumes I-III) for ~1,600-2,500 res 7 hexes in < 5.0 seconds; no single Volume > 3.0 seconds
**Constraints**: Conservation of Value within 1e-10 tolerance across all operations; runtime conservation logging (non-halting)
**Scale/Scope**: 3 counties, ~1,600-2,500 H3 res 7 hexes, 260 ticks (5 years), ~130×130 CFS flow matrix, LODES OD sparse matrix

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I.2 Imperial Rent (Phi) | PASS | ImperialRentField computed from GeographicFlow in Feature 025; wired to hex-level via CFS-to-county-to-hex mapping |
| I.3 TRPF with Counter-Tendencies | PASS | Volume III equalization computes profit rate convergence; counter-tendencies from Feature 024 |
| I.4 George Jackson Bifurcation | PASS | Macomb County data isolated to test white working-class bellwether dynamics |
| I.5 Department III | PASS | Visibility tensor from Feature 015/025 includes g_33; reproduction requirements in tensor hierarchy |
| II.2 Primitives vs Derived | PASS | Uses federal statistical primitives (TIGER, ACS, LODES, QCEW) to compute derived values (v, s, r) |
| II.6 State is Data, Engine is Transform | PASS | Hex economic state is frozen Pydantic; engine transforms via pure functions |
| III.1 No Magic Constants | PASS | Commute flows from LODES OD matrices; allocation weights from Census ACS; no arbitrary gravity variables |
| III.2 Falsifiability Required | PASS | Value conservation equation (abs(diff) < 1e-10) and directional capital shift (Wayne decreases, Oakland increases) |
| III.4 Data Source Traceability | PASS | TIGER, QCEW, ACS, LODES are approved federal sources per III.4 |
| IV Detroit Test Case | PASS | Wayne/Oakland/Macomb is the Article IV test geography |
| VI.1 Material Base First | PASS | Explicitly defers superstructural/electoral logic |
| VIII.7 Superstructure Before Base | NOT TRIGGERED | Electoral mechanics deferred |

**Gate Result**: PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/026-tri-county-economic-substrate/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal protocols)
│   └── protocols.md     # Protocol interfaces for hex-level computation
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/economics/substrate/          # NEW: Hex-level spatial economic substrate
├── __init__.py                           # Package exports
├── types.py                              # HexEconomicState, HexGrid, SubstrateConfig
├── protocols.py                          # Source/computer protocols for hex operations
├── spatial.py                            # H3 res 7 mesh generation, county assignment
├── hydrator.py                           # QCEW→hex allocation via Census ACS tract weights
├── production.py                         # Volume I: per-hex surplus value, s/v computation
├── circulation.py                        # Volume II: LODES-based wage redistribution
├── equalization.py                       # Volume III: capital migration, profit rate convergence
├── aggregation.py                        # Multi-resolution aggregation (r7→r6→r5)
├── conservation.py                       # Runtime conservation checking and logging
└── validation.py                         # Three-tier validation for substrate operations

src/babylon/data/census/                  # EXTEND: Add tract-level ACS loader
└── tract_loader.py                       # NEW: Tract-level ACS demographic data

src/babylon/data/h3/                      # EXTEND: Add res 7 support
└── loader.py                             # MODIFY: Extend DEFAULT_H3_RESOLUTIONS to include 7

src/babylon/data/reference/               # EXTEND: Add tract schema
└── schema.py                             # MODIFY: Add DimCensusTract, bridge_tract_h3

tests/unit/economics/substrate/           # NEW: Unit tests
├── test_spatial.py
├── test_hydrator.py
├── test_production.py
├── test_circulation.py
├── test_equalization.py
├── test_aggregation.py
└── test_conservation.py

tests/integration/economics/              # NEW: Integration tests
└── test_substrate_pipeline.py            # End-to-end tick pipeline test
```

**Structure Decision**: New `substrate/` package under `src/babylon/economics/` following the established pattern (parallel to `tensor_hierarchy/`, `circulation/`, `distribution/`). Extends existing `data/census/`, `data/h3/`, and `data/reference/` packages rather than duplicating infrastructure.

## Key Design Decisions

### 1. Hex-Level vs County-Level State

Existing infrastructure (Features 021-024) operates at **county level** via `CountyEconomicState`. Feature 026 introduces **hex-level** computation via a new `HexEconomicState` that decomposes county-level aggregates to H3 res 7 hexes.

**Approach**: `HexEconomicState` is a lightweight frozen Pydantic model containing (c, v, s, employment, profit_rate, county_fips, h3_index). It does NOT replicate the full `CountyEconomicState` — it holds only the values needed for spatial production/circulation/equalization.

### 2. LODES Disaggregation Strategy

Current LODES data is county-to-county. For hex-to-hex circulation:
1. Load county-to-county OD flows from existing `fact_lodes_commuter_flow`
2. Disaggregate to hex-to-hex using Census block crosswalk (`bridge_lodes_block`) + H3 mapping
3. Result: sparse matrix (N_hexes × N_hexes) where N ≈ 1,600-2,500

**Conservation guarantee**: Disaggregation preserves county-level flow totals by distributing proportionally based on tract-level employment weights.

### 3. Census Tract-Level Data

Current Census ACS loader is county-only. For tract-level demographic weights:
- Add `tract_loader.py` to `src/babylon/data/census/`
- New schema: `dim_census_tract` (tract GEOID, county_id, population, employment, median_income)
- Fetch from Census API using existing `CensusAPIClient` patterns
- Tract-to-hex mapping via spatial join (tract polygon centroids → H3 res 7 cell)

### 4. Multi-Resolution Aggregation

H3 natively supports hierarchical resolution via `h3.cell_to_parent()`:
- Res 7 hex → `cell_to_parent(h3_index, 6)` → Res 6 parent
- Res 6 hex → `cell_to_parent(h3_index, 5)` → Res 5 parent

Aggregation is pure summation of child hex values. Conservation verified by `abs(sum(children) - parent) < 1e-10`.

### 5. Performance Strategy

The 5.0-second budget for ~2,000 hexes across 3 Volumes requires vectorized computation:
- **Volume I (Production)**: Vectorized NumPy operations on hex arrays (~0.1s expected)
- **Volume II (Circulation)**: Sparse matrix multiplication (scipy.sparse.csr_matrix @ v_vector) (~2-3s expected, dominant cost)
- **Volume III (Equalization)**: Vectorized profit rate comparison + capital reallocation (~0.5s expected)
- **Conservation checks**: O(N) summation (~0.01s)

### 6. Boundary Flow Register

For LODES commute flows crossing the tri-county boundary:
- Aggregate external flows into a single "external" sink/source node
- Track total outflow (v leaving tri-county) and total inflow (v entering)
- Conservation check: internal_v + outflow - inflow = original total_v

## Complexity Tracking

No constitution violations to justify.

## Existing Infrastructure Reuse

| Component | Exists | Reuse Strategy |
|-----------|--------|----------------|
| H3 library (v4.2) | Yes (pyproject.toml) | Direct use |
| H3GridLoader (res 3/4/5) | Yes (data/h3/loader.py) | Extend to res 7 |
| TIGERCountyLoader | Yes (data/tiger/loader.py) | Use for boundary polygons |
| BridgeCountyH3 table | Yes (schema.py) | Add res 7 records |
| QCEW loader | Yes (data/qcew/) | Read county totals |
| Census ACS loader | Yes (data/census/) | Extend with tract loader |
| LODES loader | Yes (data/lodes/) | Read county OD flows, disaggregate |
| Tensor hierarchy | Yes (economics/tensor_hierarchy/) | Consume GeographicFlow, InterIndustry |
| Throughput position | Yes (economics/throughput/) | Consume π, τ_through per county |
| Volume I types | Yes (economics/reserve_army/, working_day/, dispossession/) | Wire to hex level |
| Volume II types | Yes (economics/circulation/) | Wire circulation to hex level |
| Volume III types | Yes (economics/distribution/, credit/, rent/) | Wire equalization to hex level |
| CountyEconomicState | Yes (economics/tick/types.py) | Source county aggregates for decomposition |
| Graph bridge | Yes (economics/tick/graph_bridge.py) | Persist hex-level results |
| NoDataSentinel | Yes (economics/tensor.py) | Error handling pattern |
| Three-tier validation | Yes (tensor_hierarchy/validation.py) | Validation pattern |
| Protocol + Default pattern | Yes (all economics modules) | DI architecture |
