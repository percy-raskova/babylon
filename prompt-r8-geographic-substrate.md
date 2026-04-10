# Task: R8 Geographic Substrate — Data Model and Initialization Pipeline

## Context

Babylon's spatial system uses H3 hexagons at resolution 7 (~5.16 km², ~2.3 km diameter) as the gameplay resolution. The player sees and acts at R7. The economics engine computes at R7. All existing code — `HexEconomicState`, `TerrainClassification`, `InfrastructureLinkState`, `VertexState`, edge capacity computation — operates at R7.

This task adds a **resolution 8 substrate** (~0.74 km², ~860m diameter, 7 cells per R7 parent) as a read-only geographic data layer. R8 is a *measurement* resolution, not a gameplay resolution. It holds the physical geography at higher fidelity than R7 can resolve, and its data aggregates upward to produce more accurate R7 attributes. R8 data is computed once from geographic data sources at scenario creation time and is immutable during gameplay.

The relationship between R8 and R7 is analogous to QCEW delivering data in dollars while the tensor stores labor-hours — R8 is the native resolution of geographic truth, R7 is the native resolution of game mechanics, and there is a well-defined aggregation step between them.

## Architecture Decisions (settled, do not re-litigate)

1. **R8 is never rendered to the player.** It exists purely as a computational substrate. A god-mode debug view may render R8 cells for troubleshooting, but this is a developer tool, not a gameplay feature.

2. **R8 is immutable during gameplay.** No game action modifies R8 data. When in-game R8 mutation is eventually needed (e.g., BUILD_INFRASTRUCTURE laying pipe, contamination spreading), the mutable state will be promoted to a separate Postgres runtime table. For now, R8 is static reference data.

3. **R8 lives in Postgres, not only SQLite.** The canonical source data is ingested from geographic files into SQLite, but the engine reads from Postgres at runtime. The initialization pipeline copies R8 reference data into a scenario-level Postgres table (`hex_r8_reference`) shared across game sessions. This avoids cross-database queries during R7 aggregation.

4. **Elevation is a stub.** The `elevation_m` field exists on every R8 record with the correct type (`float | None`). Default is `None` (not 0.0, since 0.0 is valid — sea level). Code that would consume elevation checks `if elevation is not None` before proceeding. Data source is eventually USGS 3DEP or SRTM. Not populated for MVP.

5. **R8 is scenario-level, not session-level.** The `hex_r8_reference` table is populated once per scenario (tri-county Detroit, full Michigan, etc.) and shared across all game sessions using that scenario. It does NOT get the `(tick, entity_id)` composite key — it has no tick dimension.

## What R8 Stores Per Cell

Each R8 record represents one H3 resolution 8 hexagonal cell.

### Core Fields

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `h3_index` | `str` (PK) | Computed | H3 R8 cell index |
| `parent_h3` | `str` (FK, indexed) | Computed via `h3.cell_to_parent(h3_index, 7)` | R7 parent for fast aggregation |
| `county_fips` | `str(5)` | Inherited from R7 parent's county assignment | For filtering |
| `terrain_type` | `str` enum | NHD water polygons, NE physical data | `LAND`, `WATER`, or `RESOURCE` |
| `water_fraction` | `float [0,1]` | NHD polygon intersection | Fraction of R8 cell covered by water — R8 cells can straddle riverbanks |
| `elevation_m` | `float | None` | Stub — `None` until DEM ingestion | Eventual source: USGS 3DEP or SRTM |

### Utility Presence Flags

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `has_water_service` | `bool` | TIGER/HIFLD utility data or proxy | Potable water service present |
| `has_sewer` | `bool` | TIGER/HIFLD or proxy | Sanitary sewer service present |
| `has_electric` | `bool` | HIFLD electric service territories | Electrical distribution present |
| `has_gas` | `bool` | HIFLD or proxy | Natural gas service present |
| `has_broadband` | `bool` | FCC BDC data | Broadband internet available |

For MVP, utility presence flags may be initialized as `True` for all LAND cells in the tri-county area and `False` for WATER cells, with a `TODO` to refine from actual utility coverage data. This matches the existing pattern where `visibility_g33` defaults to 1.0 and `internet_quality` defaults from county-level FCC data.

### Linear Feature Crossings (separate table)

Infrastructure features that physically pass through each R8 cell. This is the high-fidelity substrate that gets aggregated into R7 edge infrastructure inventories.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `h3_index` | `str` (FK) | R8 cell this feature passes through | |
| `feature_type` | `str` enum | Classification | `HIGHWAY`, `ARTERIAL`, `LOCAL_ROAD`, `RAIL`, `PIPELINE`, `TRANSMISSION` |
| `feature_name` | `str | None` | NE/HIFLD attribute | e.g., "I-75", "CSX Main Line" |
| `source_dataset` | `str` | Provenance | `NE_10M_ROADS`, `NE_10M_RAILROADS`, `HIFLD_TRANSMISSION`, etc. |
| `source_feature_id` | `str | None` | Original feature ID from source data | For audit trail |

## R8 → R7 Aggregation Rules

These aggregation functions run once during game initialization, producing R7 attributes from R8 substrate data. The R7 attributes then feed into existing systems.

### Terrain Classification

Query the 7 R8 children of each R7 hex. Compute:
- `water_coverage_fraction` = count(R8 children where terrain_type == WATER) / 7
- `resource_coverage_fraction` = count(R8 children where terrain_type == RESOURCE) / 7
- R7 `terrain_type` = WATER if water_coverage_fraction > 0.5, RESOURCE if resource_coverage_fraction > 0.5 (and water is not), else LAND

This refines the existing `TerrainClassification` model which already has `water_coverage_fraction` and `resource_coverage_fraction` fields.

### Infrastructure Edge Routing

For each linear feature that passes through R8 cells:
1. Get the sequence of R8 cells the feature crosses (from the linear feature crossings table)
2. For each pair of consecutive R8 cells in the sequence, check if they have *different* R7 parents
3. Where R7 parents differ, the feature crosses an R7 edge — assign the feature to that R7 edge's infrastructure inventory

This replaces or refines the existing NE → R7 edge snapping algorithm in `SpatialSnapper.snap_linear_features()`. The R8 substrate makes the snapping more accurate because you know exactly which part of the R7 boundary the feature crosses, not just that it's "near" the boundary.

### Utility Coverage

For each R7 hex, compute utility coverage as fraction of LAND-type R8 children with each utility:
- `water_service_coverage` = count(R8 LAND children with has_water_service) / count(R8 LAND children)
- Same pattern for sewer, electric, gas, broadband

These become fields on `HexEconomicState` or a new `HexInfrastructureQuality` model attached to the R7 hex. Utility coverage affects effective habitability — a LAND hex where only 2/7 R8 children have water service has constrained population capacity.

## Database Schema

### SQLite Reference Database (ingestion target)

```sql
CREATE TABLE hex_r8 (
    h3_index TEXT PRIMARY KEY,
    parent_h3 TEXT NOT NULL,
    county_fips TEXT NOT NULL,
    terrain_type TEXT NOT NULL CHECK (terrain_type IN ('LAND', 'WATER', 'RESOURCE')),
    water_fraction REAL NOT NULL DEFAULT 0.0 CHECK (water_fraction BETWEEN 0.0 AND 1.0),
    elevation_m REAL,  -- NULL = not yet populated (stub)
    has_water_service INTEGER NOT NULL DEFAULT 1,  -- SQLite boolean
    has_sewer INTEGER NOT NULL DEFAULT 1,
    has_electric INTEGER NOT NULL DEFAULT 1,
    has_gas INTEGER NOT NULL DEFAULT 1,
    has_broadband INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_hex_r8_parent ON hex_r8(parent_h3);
CREATE INDEX idx_hex_r8_county ON hex_r8(county_fips);

CREATE TABLE hex_r8_linear_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    h3_index TEXT NOT NULL REFERENCES hex_r8(h3_index),
    feature_type TEXT NOT NULL,
    feature_name TEXT,
    source_dataset TEXT NOT NULL,
    source_feature_id TEXT
);

CREATE INDEX idx_r8_features_hex ON hex_r8_linear_features(h3_index);
CREATE INDEX idx_r8_features_type ON hex_r8_linear_features(feature_type);
```

### Postgres Runtime Database (scenario-level reference)

```sql
CREATE TABLE hex_r8_reference (
    h3_index TEXT PRIMARY KEY,
    parent_h3 TEXT NOT NULL,
    county_fips VARCHAR(5) NOT NULL,
    terrain_type VARCHAR(10) NOT NULL CHECK (terrain_type IN ('LAND', 'WATER', 'RESOURCE')),
    water_fraction REAL NOT NULL DEFAULT 0.0 CHECK (water_fraction BETWEEN 0.0 AND 1.0),
    elevation_m REAL,  -- NULL = stub
    has_water_service BOOLEAN NOT NULL DEFAULT TRUE,
    has_sewer BOOLEAN NOT NULL DEFAULT TRUE,
    has_electric BOOLEAN NOT NULL DEFAULT TRUE,
    has_gas BOOLEAN NOT NULL DEFAULT TRUE,
    has_broadband BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_r8_ref_parent ON hex_r8_reference(parent_h3);
CREATE INDEX idx_r8_ref_county ON hex_r8_reference(county_fips);

CREATE TABLE hex_r8_linear_features_reference (
    id SERIAL PRIMARY KEY,
    h3_index TEXT NOT NULL REFERENCES hex_r8_reference(h3_index),
    feature_type VARCHAR(20) NOT NULL,
    feature_name TEXT,
    source_dataset VARCHAR(50) NOT NULL,
    source_feature_id TEXT
);

CREATE INDEX idx_r8_feat_ref_hex ON hex_r8_linear_features_reference(h3_index);
```

## Pydantic Models

Create these in `src/babylon/economics/substrate/r8_types.py` (or `src/babylon/infrastructure/r8_types.py` — use your judgment on which package owns this):

```python
class HexR8State(BaseModel):
    """Per-cell geographic state at H3 resolution 8.
    
    Read-only reference data. Immutable during gameplay.
    Aggregates upward to R7 HexEconomicState and TerrainClassification.
    """
    model_config = ConfigDict(frozen=True)
    
    h3_index: str  # R8 cell ID
    parent_h3: str  # R7 parent cell ID
    county_fips: str  # 5-digit FIPS
    terrain_type: str  # LAND | WATER | RESOURCE
    water_fraction: float  # [0.0, 1.0]
    elevation_m: float | None  # stub: None until DEM data
    has_water_service: bool
    has_sewer: bool
    has_electric: bool
    has_gas: bool
    has_broadband: bool

class R8LinearFeature(BaseModel):
    """A linear infrastructure feature passing through an R8 cell."""
    model_config = ConfigDict(frozen=True)
    
    h3_index: str
    feature_type: str  # HIGHWAY, ARTERIAL, LOCAL_ROAD, RAIL, PIPELINE, TRANSMISSION
    feature_name: str | None
    source_dataset: str
    source_feature_id: str | None
```

## Implementation Tasks

### Task 1: Pydantic Models
Create `HexR8State` and `R8LinearFeature` models. Add validators:
- `h3_index` must be valid H3 index at resolution 8
- `parent_h3` must be valid H3 index at resolution 7
- `parent_h3` must equal `h3.cell_to_parent(h3_index, 7)`
- `county_fips` must be 5 digits
- `terrain_type` must be in `{'LAND', 'WATER', 'RESOURCE'}`

### Task 2: R8 Mesh Generation
Create a function that takes a set of R7 hex indices and generates their R8 children:
```python
def generate_r8_mesh(r7_indices: set[str]) -> list[HexR8State]:
    """Generate R8 cells for all R7 parents.
    
    For each R7 hex, call h3.cell_to_children(r7_hex, 8) to get 7 R8 children.
    Initialize all with terrain_type=LAND, all utilities True, elevation None.
    """
```

### Task 3: Terrain Classification from Geographic Data
Create a function that takes R8 cells and water body polygons (from NHD/TIGER) and classifies terrain:
```python
def classify_r8_terrain(
    r8_cells: list[HexR8State],
    water_polygons: list[Polygon],  # Shapely
) -> list[HexR8State]:
    """Classify each R8 cell by terrain type.
    
    For each R8 cell, compute the fraction of cell area covered by water polygons.
    If water_fraction > 0.5, classify as WATER.
    Else classify as LAND.
    RESOURCE classification is deferred (no data source for tri-county).
    """
```

### Task 4: R8 → R7 Aggregation Functions
```python
def aggregate_terrain(r8_cells: list[HexR8State]) -> dict[str, TerrainClassification]:
    """Aggregate R8 terrain data to R7 TerrainClassification.
    
    Group R8 cells by parent_h3. For each R7 parent:
    - water_coverage_fraction = count(WATER children) / total children
    - terrain_type = WATER if fraction > 0.5, else LAND
    """

def aggregate_utility_coverage(r8_cells: list[HexR8State]) -> dict[str, dict[str, float]]:
    """Aggregate R8 utility flags to R7 coverage fractions.
    
    Group by parent_h3. For each utility type, compute fraction of LAND
    children that have service. Returns {r7_hex: {utility_type: fraction}}.
    """

def aggregate_infrastructure_routing(
    r8_features: list[R8LinearFeature],
    r8_cells: list[HexR8State],
) -> dict[tuple[str, str], list[InfrastructureLinkState]]:
    """Determine which R7 edges each linear feature crosses.
    
    For each feature, trace its R8 cells. Where consecutive R8 cells have
    different R7 parents, the feature crosses that R7 edge.
    Returns {(r7_hex_a, r7_hex_b): [infrastructure_links]}.
    """
```

### Task 5: SQLite and Postgres Schema
Create migration scripts for both databases. The SQLite table goes alongside the existing reference data tables. The Postgres table follows the existing `hex_cell` pattern as scenario-level reference data.

### Task 6: Initialization Pipeline Integration
Wire the R8 substrate into the existing game initialization flow:
1. After R7 hex mesh generation (Feature 026), generate R8 children
2. Classify R8 terrain from geographic data
3. Populate R8 linear features from NE/HIFLD data
4. Copy R8 data from SQLite → Postgres `hex_r8_reference`
5. Run R8 → R7 aggregation to produce refined `TerrainClassification` and infrastructure edge inventories
6. Proceed with existing R7 initialization (economic tensor hydration, etc.)

## Constraints

- Do NOT modify existing R7 data models or break existing tests. The R8 layer produces inputs to existing R7 structures, it doesn't replace them.
- Do NOT render R8 in the frontend. A debug/god-mode view is acceptable as a separate endpoint but is not required for this task.
- Do NOT populate elevation data. The field exists, the type is correct, the value is `None`.
- Do NOT implement in-game R8 mutation. R8 is frozen reference data for this implementation.
- RESOURCE terrain type classification is deferred — tri-county Detroit has no meaningful resource hexes (southeastern Michigan is flat). Initialize the code path but expect zero RESOURCE cells in the test case.
- Utility presence flags default to `True` for LAND, `False` for WATER in the tri-county MVP. Refining from actual utility data is a future task.
- Linear feature ingestion from Natural Earth is the MVP data source. HIFLD refinement is future work.

## Row Count Estimates

| Scope | R7 hexes | R8 hexes | R8 features (est.) |
|-------|----------|----------|-------------------|
| Tri-county Detroit | ~1,500 | ~10,500 | ~30,000–50,000 |
| Michigan | ~30,000 | ~210,000 | ~500,000–1,000,000 |
| Full US | ~2,300,000 | ~16,100,000 | ~50,000,000+ |

All within SQLite and Postgres single-instance comfort zones at tri-county and state scale.

## Testing

- Generate R8 mesh for tri-county, verify each R7 hex has exactly 7 R8 children
- Verify `h3.cell_to_parent(r8, 7) == parent_h3` for all R8 cells
- Classify terrain using NHD/TIGER water polygons, verify Lake St. Clair and Detroit River hexes are WATER
- Aggregate to R7 and verify water_coverage_fraction is consistent with existing TerrainClassification results
- Verify conservation: sum of R8 LAND cells across all R7 parents matches expected habitable area
- Verify that I-75 traces a continuous path through R8 cells and crosses the expected R7 edges between Wayne and Oakland counties

## Existing Code References

- `src/babylon/infrastructure/h3_mesh.py` — R7 edge and vertex enumeration
- `src/babylon/infrastructure/types.py` — TerrainClassification, InfrastructureLinkState, VertexState
- `src/babylon/infrastructure/protocols.py` — TerrainClassifier, SpatialSnapper protocols
- `src/babylon/economics/substrate/types.py` — HexEconomicState, HexGrid, TractWeight
- `src/babylon/economics/substrate/protocols.py` — SpatialSubstrateSource
