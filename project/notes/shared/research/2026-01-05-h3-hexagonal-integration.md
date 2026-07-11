---
date: 2026-01-05T14:45:37-05:00
researcher: Claude
git_commit: c6d1f72a51ca24c68bf9fed1a196f149584e29ec
branch: dev
repository: babylon
topic: "H3 Hexagonal Coordinate System Integration for Map Visualization"
tags: [research, h3, hexagonal, geography, database, networkx, visualization]
status: complete
last_updated: 2026-01-05
last_updated_by: Claude
---

# Research: H3 Hexagonal Coordinate System Integration for Map Visualization

**Date**: 2026-01-05T14:45:37-05:00
**Researcher**: Claude
**Git Commit**: c6d1f72a51ca24c68bf9fed1a196f149584e29ec
**Branch**: dev
**Repository**: babylon

## Research Question

How can Uber's H3 hexagonal coordinate system be integrated into Babylon to:
1. Enable map visualization with fractal-like zooming
2. Integrate with the existing database schema (3NF normalized)
3. Maintain compatibility with NetworkX and the topology system
4. Support multiple granularity levels for the territory system

## Summary

H3 is an excellent fit for Babylon's geographic needs. Key findings:

1. **H3 naturally maps to Babylon's Territory system**: H3 cells become Territory nodes, `grid_ring()` creates ADJACENCY edges
2. **Fractal zooming via aperture 7**: Each H3 cell has 7 children at finer resolution, enabling seamless zoom levels
3. **Resolution 4 matches counties**: ~1,770 km² avg area aligns with existing `dim_county` grain
4. **DuckDB H3 extension**: Native SQL H3 functions align perfectly with Epoch 3 database evolution plans
5. **FCC already provides H3 data**: `download_state_hexagons()` in `src/babylon/data/fcc/downloader.py` already downloads H3-aggregated coverage data
6. **NetworkX integration is straightforward**: H3 cells are node IDs, neighbor functions create edges

## Detailed Findings

### 1. H3 Fundamentals

**What is H3?**
- Discrete Global Grid System (DGGS) by Uber
- Divides Earth into hierarchical hexagonal cells
- 16 resolution levels (0-15) with aperture 7 subdivision
- 64-bit integer or 15-character hex string identifiers
- Apache 2.0 license, mature Python bindings (h3-py)

**Why Hexagons?**
- Equidistant neighbors: All 6 neighbors same distance from center (unlike squares with 2 distances)
- Optimal tessellation: No gaps, no overlaps
- Smoother gradients: Better for diffusion/heat modeling
- Isotropic: No directional bias in spatial analysis

**Aperture 7 Hierarchy:**
```
Parent (1 cell)
    │
    └── 7 Children (each ~1/7 the area)
            │
            └── 49 Grandchildren
```

### 2. Resolution Levels and Babylon Mapping

| Resolution | Avg Area (km²) | Avg Edge (km) | Total Cells | Babylon Use Case |
|------------|----------------|---------------|-------------|------------------|
| **0** | 4,357,449 | 1,281 | 122 | Global view, continental |
| **1** | 609,788 | 483 | 842 | Major regions |
| **2** | 86,802 | 183 | 5,882 | Large states/provinces |
| **3** | 12,393 | 69 | 41,162 | Small states |
| **4** | 1,770 | 26 | 288,122 | **Counties** (matches `dim_county`) |
| **5** | 253 | 9.9 | 2,016,842 | Large cities, MSAs |
| **6** | 36 | 3.7 | 14,117,882 | City districts |
| **7** | 5.2 | 1.4 | 98,825,162 | Neighborhoods |
| **8** | 0.74 | 0.53 | 691,776,122 | Superblocks |
| **9** | 0.11 | 0.20 | 4.8 billion | City blocks |

**Recommended Resolution Strategy for Babylon:**
- **Res 2-3**: Epoch 1 (50 state-level territories)
- **Res 4**: Epoch 2 (3,000 county-level territories)
- **Res 5-6**: Epoch 2+ (70,000 city/township territories)
- **Res 7-9**: Epoch 3 (fine-grained urban simulation)

### 3. Current Babylon Geography State

**Territory Model** (`src/babylon/models/entities/territory.py:21-193`):
- ID pattern: `^T[0-9]{3}$` (abstract, not geographic)
- `sector_type`: SectorType enum (industrial, residential, etc.)
- `territory_type`: TerritoryType enum (CORE, PERIPHERY, sink nodes)
- NO latitude/longitude fields
- NO H3 index field

**Database Schema** (`src/babylon/data/normalize/schema.py`):
- `dim_state`: 50 states + territories (FIPS codes)
- `dim_county`: 3,000+ counties (5-digit FIPS)
- `dim_metro_area`: MSA/CSA codes
- Geographic grain: County-level via FIPS
- NO H3 columns currently

**FCC Loader Already Uses H3** (`src/babylon/data/fcc/downloader.py:450-516`):
```python
def download_state_hexagons(
    state_fips: str,
    output_dir: Path,
    ...
) -> list[Path]:
    """Download H3 hexagon coverage data for a state.

    Downloads Hexagon Coverage GIS files from the State category.
    These contain H3 hexagon-aggregated coverage data suitable for
    Uber H3 spatial analysis.
    """
```

**Epoch 2 Plans** (`ai-docs/epoch2/epoch2-persistence.yaml`):
- 74,000 Territory nodes planned (50 states + 3,000 counties + 70,000 cities)
- KuzuDB or DuckDB for persistence
- Fog of War system with filtered views

### 4. H3 Python API (h3-py)

**Installation:**
```python
pip install h3
```

**Core Functions:**

| Function | Purpose | Example |
|----------|---------|---------|
| `latlng_to_cell(lat, lng, res)` | Convert coordinates to H3 | `h3.latlng_to_cell(37.77, -122.42, 9)` |
| `cell_to_latlng(h)` | Get cell center coordinates | Returns `(37.77, -122.42)` |
| `grid_ring(h, k)` | Get cells at exact distance k | k=1 returns 6 neighbors |
| `grid_disk(h, k)` | Get cells within distance k | k=1 returns 7 cells (center + neighbors) |
| `are_neighbor_cells(h1, h2)` | Check adjacency | Returns `bool` |
| `cell_to_parent(h, res)` | Navigate up hierarchy | Coarser resolution |
| `cell_to_children(h, res)` | Navigate down hierarchy | Returns 7 cells |
| `compact_cells(cells)` | Merge siblings to parents | Storage optimization |
| `uncompact_cells(cells, res)` | Expand to target resolution | Full granularity |
| `geo_to_cells(polygon, res)` | Fill polygon with cells | For county boundaries |

**Data Types:**
- Default: 15-character hex string (`'8928308280fffff'`)
- Integer API: 64-bit unsigned (`578536630256664575`)
- For performance-critical code: `from h3.api.basic_int import *`

### 5. H3-NetworkX Integration

**Pattern: H3 Cells as Graph Nodes**
```python
import h3
import networkx as nx

def create_h3_graph(center_lat: float, center_lng: float,
                    resolution: int, k_rings: int) -> nx.Graph:
    """Create NetworkX graph from H3 cells."""
    center = h3.latlng_to_cell(center_lat, center_lng, resolution)
    cells = h3.grid_disk(center, k_rings)

    G = nx.Graph()
    for cell in cells:
        G.add_node(cell,
                   _node_type="territory",
                   lat_lng=h3.cell_to_latlng(cell),
                   resolution=resolution)

    # Add ADJACENCY edges
    for cell in cells:
        for neighbor in h3.grid_ring(cell, 1):
            if neighbor in cells:
                G.add_edge(cell, neighbor, edge_type="adjacency")

    return G
```

**Compatibility with Babylon's GraphProtocol:**
- H3 cell strings serve as node IDs (replaces `T001` pattern)
- `grid_ring()` generates ADJACENCY edges automatically
- `cell_to_parent()`/`cell_to_children()` enable multi-resolution hierarchy
- All current graph algorithms (centrality, components, percolation) work unchanged

**Multi-Resolution Graph Pattern:**
```python
# Create hierarchical graph with parent-child edges
G = nx.DiGraph()

for cell_fine in cells_resolution_9:
    G.add_node(cell_fine, resolution=9, node_type='fine')

    parent = h3.cell_to_parent(cell_fine, 7)
    G.add_node(parent, resolution=7, node_type='coarse')
    G.add_edge(cell_fine, parent, edge_type='hierarchy')
```

### 6. Database Schema Integration

**Option A: Add H3 Column to dim_county**
```sql
ALTER TABLE dim_county ADD COLUMN h3_res4 TEXT;  -- 15-char hex string

-- Populate via centroid (requires lat/lng lookup)
UPDATE dim_county
SET h3_res4 = h3_latlng_to_cell_string(centroid_lat, centroid_lng, 4);
```

**Option B: New H3 Dimension Table**
```sql
CREATE TABLE dim_h3_cell (
    h3_cell_id INTEGER PRIMARY KEY,  -- Surrogate key
    h3_index TEXT NOT NULL UNIQUE,   -- 15-char hex (e.g., '842a100ffffffff')
    h3_int BIGINT NOT NULL,          -- 64-bit integer representation
    resolution INTEGER NOT NULL,
    parent_h3_index TEXT,            -- Foreign key to coarser resolution
    centroid_lat REAL,
    centroid_lng REAL,
    area_km2 REAL,

    -- Bridge to existing geography
    county_id INTEGER REFERENCES dim_county(county_id),
    state_id INTEGER REFERENCES dim_state(state_id)
);

CREATE INDEX idx_h3_resolution ON dim_h3_cell(resolution);
CREATE INDEX idx_h3_parent ON dim_h3_cell(parent_h3_index);
```

**Option C: DuckDB with Native H3 (Epoch 3)**

DuckDB has a community H3 extension that aligns with Babylon's planned migration:

```sql
-- Install H3 extension
INSTALL h3 FROM community;
LOAD h3;

-- Convert county centroids to H3
SELECT
    county_id,
    county_name,
    h3_latlng_to_cell(centroid_lat, centroid_lng, 4) as h3_cell,
    h3_latlng_to_cell_string(centroid_lat, centroid_lng, 4) as h3_string
FROM dim_county;

-- Spatial queries via H3
SELECT
    h3_grid_disk(h3_cell, 2) as neighborhood_cells
FROM territories
WHERE territory_type = 'CORE';
```

**Bridge Strategy:**
1. **Epoch 1**: No H3 (abstract territories)
2. **Epoch 2**: Add `h3_index` to Territory model, populate from county centroids
3. **Epoch 3**: Migrate to DuckDB, use native H3 functions, support fine-grained resolution

### 7. Visualization Integration

**DearPyGui Canvas Pattern:**

DearPyGui supports `draw_polygon()` for rendering hexagons:

```python
import dearpygui.dearpygui as dpg
import h3

def render_h3_cell(cell: str, parent: int, scale: float = 100.0):
    """Render single H3 cell as polygon."""
    boundary = h3.cell_to_boundary(cell)  # [(lat, lng), ...]

    # Convert to screen coordinates (simplified)
    points = [(lng * scale, lat * scale) for lat, lng in boundary]

    # Get color based on territory state
    heat = get_territory_heat(cell)
    color = heat_to_color(heat)

    dpg.draw_polygon(points, color=color, fill=color, parent=parent)

def create_map_window():
    with dpg.window(label="Territory Map"):
        with dpg.drawlist(width=800, height=600) as drawlist:
            for cell in visible_cells:
                render_h3_cell(cell, drawlist)
```

**Alternative: Web-Based Visualization**

For richer map features, consider:
- **Folium + H3**: `h3.cells_to_geo()` generates GeoJSON for Leaflet
- **Kepler.gl**: Native H3 support, interactive 3D visualization
- **deck.gl H3HexagonLayer**: WebGL-accelerated hexagon rendering

### 8. Resolution Selection for Babylon

**Epoch 1 (Current): Abstract Territories**
- Continue using `T001` style IDs
- No H3 integration needed yet
- Focus on mechanics validation

**Epoch 2 (The Game): County-Scale Geography**
- Use Resolution 4 (~1,770 km², matches counties)
- ~288,000 cells for continental US
- Practical for 74,000 territory target
- Bridge via `dim_county.h3_res4` column

**Epoch 3 (The Platform): Multi-Resolution**
- Support resolutions 4-9 dynamically
- Zoom: Res 4 (country) → Res 7 (neighborhood)
- Use `compact_cells()`/`uncompact_cells()` for efficient storage
- DuckDB H3 extension for native queries

### 9. Key Integration Points

| Babylon Component | H3 Integration Point |
|-------------------|---------------------|
| Territory.id | Change from `T001` to H3 hex string |
| ADJACENCY edges | Generate via `h3.grid_ring(cell, 1)` |
| TerritorySystem | Heat spillover via adjacent H3 cells |
| dim_county | Add `h3_res4` column for bridge |
| WorldState.to_graph() | H3 cells as node IDs |
| GraphProtocol | No changes needed (string IDs work) |
| DearPyGui | `draw_polygon()` with `cell_to_boundary()` |
| DuckDB (Epoch 3) | Native `h3_*` SQL functions |

## Code References

- `src/babylon/data/fcc/downloader.py:450-516` - Existing H3 hexagon download function
- `src/babylon/models/entities/territory.py:21-193` - Territory model (needs H3 field)
- `src/babylon/models/world_state.py:108-275` - WorldState graph conversion
- `src/babylon/data/normalize/schema.py:35-80` - Geographic dimension tables
- `src/babylon/engine/systems/territory.py:266-311` - Heat spillover (maps to H3 adjacency)
- `ai-docs/database-spec.yaml:85-116` - DuckDB evolution plans (aligns with H3)
- `ai-docs/topology-system.yaml:146-172` - Graph abstraction layer (compatible with H3)

## Architecture Documentation

**Current Pattern:**
```
Territory (abstract) ←→ NetworkX Node ←→ WorldState
     │
     └── ADJACENCY edges (manual creation)
```

**With H3:**
```
Territory (H3 cell) ←→ NetworkX Node ←→ WorldState
     │                      │
     │                      └── h3.cell_to_latlng() for coordinates
     └── ADJACENCY edges via h3.grid_ring()
            │
            └── Multi-resolution via cell_to_parent()/cell_to_children()
```

**Database Evolution:**
```
Epoch 1: SQLite (dim_county via FIPS)
           │
           v
Epoch 2: SQLite + h3_res4 column on dim_county
           │
           v
Epoch 3: DuckDB + H3 extension (native spatial queries)
```

## Historical Context (from thoughts/)

No prior H3 research found in thoughts directory. This is the first comprehensive H3 integration analysis.

Related existing documentation:
- `ai-docs/territorial-schema.yaml` - Settler-colonial geography concepts (OGV/OPC/Frontier)
- `ai-docs/carceral-geography.yaml` - Heat dynamics, eviction pipeline
- `ai-docs/epoch2/epoch2-persistence.yaml` - 74,000 territory node target

## Related Research

- `thoughts/shared/plans/2026-01-05-circulatory-api-loaders.md` - HIFLD/MIRTA infrastructure loaders (provides facility coordinates for H3 conversion)
- `ai-docs/database-spec.yaml` - Database evolution roadmap

## Open Questions

1. **Resolution Choice**: Should Babylon use a single resolution or support dynamic multi-resolution?
   - Single resolution (res 4) is simpler but limits zoom
   - Multi-resolution requires managing parent-child relationships

2. **ID Migration**: How to transition from `T001` to H3 hex strings?
   - Breaking change for existing scenarios
   - Could support both during transition period

3. **Performance at Scale**: How does NetworkX perform with 74,000+ H3 nodes?
   - May need to profile and consider graph database (KuzuDB) earlier

4. **Visualization Library**: DearPyGui canvas vs web-based (Kepler.gl/deck.gl)?
   - DearPyGui keeps everything local (current approach)
   - Web-based offers richer interactivity but adds complexity

5. **Centroid Data**: Where to source lat/lng for county centroids?
   - Census TIGER/Line shapefiles have county polygons
   - Could use `h3.geo_to_cells()` to fill county boundaries

## Sources

- [H3 Official Documentation](https://h3geo.org/)
- [h3-py GitHub Repository](https://github.com/uber/h3-py)
- [H3 Resolution Table](https://h3geo.org/docs/core-library/restable/)
- [H3-DuckDB Extension](https://github.com/isaacbrodsky/h3-duckdb)
- [Uber H3 Blog Post](https://www.uber.com/en-US/blog/h3/)
- [CARTO: 10 Powerful Uses of H3](https://carto.com/blog/h3-spatial-indexes-10-use-cases)
- [NetworkX Geospatial Examples](https://networkx.org/documentation/stable/auto_examples/geospatial/index.html)
