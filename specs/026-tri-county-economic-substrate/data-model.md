# Data Model: 026-tri-county-economic-substrate

**Date**: 2026-02-26
**Branch**: `026-tri-county-economic-substrate`

## Entities

### HexEconomicState (NEW — frozen Pydantic model)

Per-hex economic state at a single simulation tick.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| h3_index | str | H3 resolution 7 cell ID | 15-char hex string, validated by h3 |
| county_fips | str | 5-digit county FIPS code | One of: 26163, 26125, 26099 |
| constant_capital | float | c — means of production value | >= 0.0 |
| variable_capital | float | v — wages (pre-circulation) | >= 0.0 |
| surplus_value | float | s — extracted surplus | >= 0.0 |
| employment | float | Allocated employment count | >= 0.0 |
| dept_shares | tuple[float, float, float, float] | Department I, IIa, IIb, III employment fractions | Each >= 0.0, sum = 1.0 |
| profit_rate | float | s / (c + v) | >= 0.0; NaN if c + v = 0 |
| exploitation_rate | float | s / v | >= 0.0; NaN if v = 0 |

**Lifecycle**: Created during hydration (Story 2), mutated during production (Story 3), circulation (Story 4), and equalization (Story 5). Each phase produces a new frozen copy via `model_copy()`.

**Identity**: `h3_index` is the unique key. No two hexes share an H3 index.

### HexGrid (NEW — frozen Pydantic model)

Collection of all hexes in the tri-county area with resolution hierarchy.

| Field | Type | Description |
|-------|------|-------------|
| hexes | dict[str, HexEconomicState] | h3_index → state mapping |
| county_hex_ids | dict[str, frozenset[str]] | county_fips → set of h3_indices |
| res6_parents | dict[str, str] | h3_index (r7) → h3_index (r6) |
| res5_parents | dict[str, str] | h3_index (r7) → h3_index (r5) |
| res6_children | dict[str, frozenset[str]] | h3_index (r6) → set of h3_indices (r7) |
| res5_children | dict[str, frozenset[str]] | h3_index (r5) → set of h3_indices (r7) |

**Identity**: Singleton per simulation run. Rebuilt on initialization.

### SubstrateConfig (NEW — frozen Pydantic model)

Configuration for the spatial economic substrate.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| county_fips_list | tuple[str, ...] | ("26163", "26125", "26099") | FIPS codes for tri-county area |
| h3_resolution | int | 7 | Base hex resolution |
| conservation_tolerance | float | 1e-10 | abs(diff) threshold for conservation checks |
| equalization_alpha | float | 0.01 | Capital migration speed coefficient |
| tick_count | int | 260 | Total simulation ticks (5 years) |
| log_conservation_warnings | bool | True | Enable runtime conservation logging |

### BoundaryFlowRegister (NEW — frozen Pydantic model)

Tracks value flows crossing the tri-county boundary.

| Field | Type | Description |
|-------|------|-------------|
| external_outflow_v | float | Total variable capital leaving tri-county via commute |
| external_inflow_v | float | Total variable capital entering tri-county via commute |
| net_flow | float | inflow - outflow (positive = net inbound) |

## Database Schema Extensions

### dim_census_tract (NEW table)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| tract_id | Integer | PK, auto | Internal ID |
| tract_geoid | String(11) | UNIQUE, NOT NULL | 11-char Census tract GEOID (state+county+tract) |
| county_id | Integer | FK → dim_county | Parent county |
| population | Integer | >= 0 | Total population (ACS B01003) |
| employed | Integer | >= 0 | Employed count (ACS B23025) |
| unemployed | Integer | >= 0 | Unemployed count (ACS B23025) |
| median_income | Integer | >= 0, NULLABLE | Median household income (ACS B19013) |
| data_year | Integer | NOT NULL | ACS vintage year |

### bridge_tract_h3 (NEW table)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| h3_index | String(15) | PK | H3 resolution 7 cell ID |
| tract_id | Integer | FK → dim_census_tract | Containing tract |
| coverage_pct | Float | NULLABLE | % of hex area within tract |

### bridge_county_h3 (EXISTING — extend)

Add resolution 7 records to existing table. No schema change needed — the `resolution` column already supports any H3 resolution value.

## Entity Relationships

```
DimCounty (26163, 26125, 26099)
    │
    ├── 1:N ── dim_census_tract (tract_geoid, population, employment, income)
    │               │
    │               └── 1:N ── bridge_tract_h3 (h3_index → tract_id)
    │
    ├── 1:N ── bridge_county_h3 (h3_index, resolution=7)
    │
    └── 1:N ── fact_lodes_commuter_flow (home_county_id ↔ work_county_id, total_jobs)

HexGrid
    │
    ├── contains ── HexEconomicState (h3_index, c, v, s, employment, dept_shares)
    │                   │
    │                   ├── produces ── profit_rate = s / (c + v)
    │                   └── produces ── exploitation_rate = s / v
    │
    ├── maps ── res6_parents (h3_r7 → h3_r6)
    ├── maps ── res5_parents (h3_r7 → h3_r5)
    │
    └── tracks ── BoundaryFlowRegister (external v flows)

SubstrateConfig
    └── parameterizes all substrate operations
```

## State Transitions

```
HexEconomicState lifecycle per tick:

    [Hydrated]
        │ (initial allocation from county QCEW via tract weights)
        ▼
    [Post-Production]
        │ Volume I: compute s/v per hex from dept composition
        │ Conservation: sum(c+v+s) before = sum(c+v+s) after
        ▼
    [Post-Circulation]
        │ Volume II: LODES OD matrix redistributes v across hexes
        │ Conservation: sum(v) before = sum(v) after (within 1e-10)
        ▼
    [Post-Equalization]
        │ Volume III: capital migrates based on profit rate gradient
        │ Conservation: sum(c) before = sum(c) after (within 1e-10)
        ▼
    [Tick Complete]
        │ Conservation check logged; aggregation to r6/r5 verified
        └─► Next tick starts at [Post-Production] with updated state
```

## Validation Rules

| Entity | Rule | Tier |
|--------|------|------|
| HexEconomicState | c, v, s >= 0 | Fail |
| HexEconomicState | sum(dept_shares) = 1.0 (within 1e-10) | Fail |
| HexEconomicState | profit_rate in [0, 2.0] | Expected; [0, 5.0] Warning; else Fail |
| HexGrid | No duplicate h3_index entries | Fail |
| HexGrid | Every hex has exactly one county assignment | Fail |
| HexGrid | Every r7 hex maps to exactly one r6 and r5 parent | Fail |
| Conservation | abs(sum_pre - sum_post) < 1e-10 per operation | Warning (logged, non-halting) |
| Aggregation | abs(sum(r7_children) - r6_parent_value) < 1e-10 | Warning (logged, non-halting) |
| BoundaryFlowRegister | net_flow = inflow - outflow (exact arithmetic check) | Fail |
