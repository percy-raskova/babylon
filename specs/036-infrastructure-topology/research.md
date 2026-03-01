# Research: Infrastructure Topology Layer

**Feature**: 036-infrastructure-topology
**Date**: 2026-03-01
**Status**: Complete

## R1: H3 Edge and Vertex Enumeration

**Decision**: Build new H3 edge/vertex utilities from scratch.

**Rationale**: The codebase has zero H3 adjacency/edge operations. No calls to `h3.cells_to_directed_edge()`, `h3.are_neighbor_cells()`, `h3.grid_disk()`, or any edge enumeration functions. The existing `HexGrid` model (`economics/substrate/types.py`) contains no adjacency data -- only hex-to-county mappings and resolution hierarchy (r7 -> r6 -> r5). The tri-county mesh generation (`economics/substrate/spatial.py:generate_tri_county_mesh()`) polyfills county polygons to H3 cells but does not compute neighbor relationships.

**What exists**:
- `h3.geo_to_cells(geojson, resolution)` -- polyfill polygon to cell set (used in `loader.py`, `h3_spatial.py`)
- `h3.cell_to_latlng(cell)` -- cell centroid (used in `loader.py`)
- `h3.cell_to_parent(h3_id, target_res)` -- resolution coarsening (used in `spatial.py`)
- `generate_h3_cells(geometry, resolution)` -- Shapely polygon to H3 cell set (`data/h3/loader.py`)
- `wkt_to_geometry(wkt)` -- WKT string to Shapely geometry (`data/h3/loader.py`)

**What must be built**:
- Edge enumeration: for each cell, find all 6 neighbors via `h3.grid_disk(cell, 1)`, create directed edges as `(cell_a, cell_b)` ordered pairs
- Vertex enumeration: identify triple junctions where 3 hexes meet (each vertex shared by exactly 3 cells)
- Adjacency graph construction: build a NetworkX graph from the H3 edge set
- Spatial snapping: map Natural Earth linear features (roads, railroads) to H3 edges, and point features (airports, ports) to H3 vertices

**Alternatives considered**:
- Use `h3.cells_to_directed_edge()` for edge IDs: H3 library provides directed edge handles, but we need edges as `(source_h3, target_h3)` pairs to integrate with GraphProtocol. Using H3 native edge IDs adds a translation layer with no benefit.
- Store adjacency in `HexGrid`: Would require modifying the existing frozen Pydantic model. Better to build a separate `InfrastructureGraph` that references the same H3 cell IDs.

---

## R2: GraphProtocol Integration for Infrastructure Edges

**Decision**: Add new `EdgeType` members for infrastructure and store infrastructure attributes as named edge attributes (Pattern A from the codebase).

**Rationale**: The GraphProtocol uses a triple key `(source, target, edge_type)` for edge identity. Edges carry a `weight: float = 1.0` slot (currently unused by any system) plus arbitrary named attributes in the `attributes` dict. The dominant pattern for domain-specific weights is named attributes (e.g., `solidarity_strength` on SOLIDARITY edges, `value_flow` on EXPLOITATION edges), not the generic `weight` slot.

**Key findings**:
- `EdgeType` (StrEnum, `models/enums.py:64-101`) has 16 members. Adding `INFRASTRUCTURE`, `ADJACENCY` (already exists), and new types is straightforward.
- `Relationship` model (`models/entities/relationship.py`) serializes via `edge_data` property to dict. The `from_graph()` reconstruction only reads 6 named fields -- extra attributes are lost on round-trip.
- The `NetworkXAdapter.wrap()` normalizes `edge_type` -> `_edge_type` at wrap time.
- The `weight` slot on `GraphEdge` is populated from NetworkX edge data but never read by field systems.

**Architecture decision**: Infrastructure capacity should be stored as a named attribute (e.g., `infrastructure_capacity`) rather than overloading the generic `weight` slot. This avoids breaking existing systems that may eventually use `weight` for different purposes, and follows the established pattern.

**Round-trip persistence**: To survive `to_graph()`/`from_graph()` cycles, infrastructure edges need either (a) a new `Relationship` subclass or (b) infrastructure edges stored separately from `WorldState.relationships`. Option (b) is preferred since infrastructure is a parallel layer to social relationships, not a social relationship itself.

**Alternatives considered**:
- Use the `weight` slot directly: Rejected because `weight` is a single float, but infrastructure edges need per-flow-category capacity (freight, commuter, consciousness). Named attributes support this.
- Add infrastructure fields to `Relationship`: Rejected because infrastructure is not a social relationship -- it's physical substrate. Mixing them violates the separation principle.

---

## R3: Weighted Laplacian Integration

**Decision**: Modify `FieldDerivativeSystem._collect_neighbor_fields()` and `_compute_node_derivatives()` to optionally weight by infrastructure-derived edge capacity.

**Rationale**: The current Laplacian in `field_derivative.py:162-165` is `sum_j(f(j) - f(i))` -- purely unweighted. The spec (FR-030) requires upgrading to a weighted Laplacian where edge weights derive from infrastructure capacity. The curvature computation (`curvature.py`) similarly uses unweighted hop-count distances and uniform neighbor probability measures.

**Integration points identified**:
1. `_collect_neighbor_fields()` (`field_derivative.py:195-232`): Currently scans all edges for topology only. Must also collect the infrastructure capacity attribute from each edge.
2. `_compute_node_derivatives()` (`field_derivative.py:133-192`): The Laplacian sum must become `sum_j(w_ij * (f(j) - f(i)))` where `w_ij` is infrastructure-derived edge weight.
3. `_probability_measure()` (`curvature.py:85-116`): Currently distributes `(1-alpha)` uniformly across neighbors. Must distribute proportional to edge weight for weighted curvature.
4. `_graph_distance()` (`curvature.py:119-140`): Currently uses `nx.shortest_path_length` without weight parameter. Must pass `weight=` for weighted shortest paths.

**Approach**: Add an `edge_weight_attr: str | None` parameter to the field derivative methods. When `None` (default), behavior is unchanged (unweighted). When set to e.g. `"infrastructure_capacity"`, the Laplacian and curvature use that attribute. This preserves backward compatibility.

**Alternatives considered**:
- Always use weighted Laplacian: Rejected because existing tests depend on unweighted behavior, and early ticks before infrastructure initialization would have undefined weights.
- Compute weights in a pre-pass system: Viable but adds complexity. Simpler to read edge attributes directly in the field derivative system.

---

## R4: GameDefines Pattern for Infrastructure Constants

**Decision**: Add `InfrastructureDefines` and `TerrainDefines` sub-models to `GameDefines` following the existing pattern.

**Rationale**: All simulation coefficients are centralized in `GameDefines` (`config/defines.py`), a frozen Pydantic model composed of ~25 domain-specific `*Defines` sub-models. Each uses `Field()` with provenance-tagged descriptions. The pattern for adding new sub-models is documented and consistent.

**Pattern to follow**:
1. Declare frozen `BaseModel` with `ConfigDict(frozen=True)` before `GameDefines` in `defines.py`
2. Add docstring referencing spec file and FR numbers
3. Use structured provenance tags: `"Game design: ..."`, `"Engineering: ..."`, or real-world citation
4. Add field to `GameDefines` with `default_factory`
5. Add to `_from_yaml_dict()` method
6. Add YAML section to `defines.yaml`

**Constants needed** (organized by sub-model):

`InfrastructureDefines`:
- Per-type capacity coefficients (HIGHWAY, ARTERIAL, LOCAL_ROAD, RAIL, etc.)
- Natural capacity derivation from population density
- Minimum capacity threshold for snapping filter (EC-006)
- Biocapacity depletion rates per stock type
- OPSEC throughput-surveillance tradeoff ratio

`TerrainDefines`:
- Majority-coverage threshold for terrain classification (default 0.5)
- Biocapacity initial stock values per type (SYNTHETIC flagged)
- Internet access broadband penetration threshold
- Default surveillance coupling by ISP type (SYNTHETIC)

---

## R5: Natural Earth Data Loader Architecture

**Decision**: Create a new `NaturalEarthLoader` in `src/babylon/data/natural_earth/` following the `DataLoader` ABC pattern, but operating read-only against the external SQLite database (no ingestion into the 3NF schema).

**Rationale**: Unlike `FCCBroadbandLoader` (which ingests CSV data into the 3NF SQLite via `FactBroadbandCoverage`), the Natural Earth data is already in SQLite format and is large (423MB). Copying it into the 3NF database would be wasteful. The loader should read directly from the NE SQLite and produce in-memory spatial objects (Shapely geometries) that can be snapped to the H3 mesh.

**Key findings about NE data** (verified against v5.1.2):
- All geometry is stored as BLOB in GEOMETRY column (SpatiaLite format)
- Michigan interstates identifiable in `ne_10m_roads_north_america` via `prefix`/`number`/`class` columns
- Great Lakes in `ne_10m_lakes` (scalerank 0). Lake St. Clair MISSING from `ne_10m_lakes` -- check `ne_10m_lakes_north_america` supplement
- DTW airport: scalerank 3, iata_code DTW, natlscale 75.0
- Detroit port: scalerank 4, natlscale 50.0
- Geography regions featurecla types: Range/mtn, Plateau, Desert, Valley, Basin, Wetlands, Delta, Depression (no RESOURCE hexes expected for Detroit tri-county)
- NA supplement tables provide finer detail: `ne_10m_roads_north_america`, `ne_10m_railroads_north_america`, `ne_10m_rivers_north_america`, `ne_10m_lakes_north_america`

**Architecture**: Protocol-based reader with methods per feature type:
- `load_lakes(bbox) -> list[LakeFeature]`
- `load_rivers(bbox) -> list[RiverFeature]`
- `load_roads(bbox) -> list[RoadFeature]`
- `load_railroads(bbox) -> list[RailroadFeature]`
- `load_airports(bbox) -> list[AirportFeature]`
- `load_ports(bbox) -> list[PortFeature]`
- `load_geography_regions(bbox) -> list[RegionFeature]`

Each method queries the NE SQLite with a bounding box filter, converts SpatiaLite GEOMETRY blobs to Shapely objects via `shapely.wkb.loads()`, and returns typed feature dataclasses.

**Alternatives considered**:
- Ingest into 3NF like other loaders: Rejected because NE data is static (terrain doesn't change during simulation), already in SQLite, and large. Read-only access avoids duplication.
- Use GeoJSON files instead of SQLite: Rejected because the user already has the SQLite and it's more efficient for spatial queries.

---

## R6: FCC Broadband to Hex Mapping

**Decision**: Use county-level broadband coverage from `FactBroadbandCoverage` and assign uniformly to all hexes within each county.

**Rationale**: The `FCCBroadbandLoader` stores county-level broadband penetration percentages (pct_25_3, pct_100_20, pct_1000_100) in `fact_broadband_coverage`. The hex mesh assigns each hex to a county via `county_hex_ids` in `HexGrid`. For MVP, uniform county-level assignment is sufficient (A-009 in spec). The `pct_25_3` column (percentage with at least 25/3 Mbps) is the natural threshold for `internet_access: bool`, and `pct_100_20` can inform `internet_quality: float`.

**Mapping logic**:
1. Query `fact_broadband_coverage` for each county FIPS in the tri-county set
2. For each hex assigned to that county (via `HexGrid.county_hex_ids`):
   - `internet_access = (pct_25_3 / 100.0) >= threshold` (threshold from `TerrainDefines`)
   - `internet_quality = pct_100_20 / 100.0` (clamped to [0, 1])
   - `surveillance_coupling = default_coupling` (SYNTHETIC from `TerrainDefines`)

**Alternatives considered**:
- FCC BDC hexagon download: `FCCBDCClient.download_state_hexagons()` exists in the downloader but no loader ingests those files. Building this would provide sub-county resolution but requires FCC API credentials and additional implementation. Deferred per A-009.
- Tract-level interpolation: Would require TIGER tract geometries mapped to H3 cells. More precise but adds complexity beyond MVP needs.

---

## R7: Spatial Snapping Algorithm

**Decision**: Line-to-edge snapping via Shapely intersection; point-to-vertex snapping via nearest-neighbor.

**Rationale**: Need to assign Natural Earth linear features (roads, railroads, rivers) to H3 edges, and point features (airports, ports) to H3 vertices. H3 cell boundaries are hexagonal polygons retrievable via `h3.cell_to_boundary()`.

**Algorithm -- Linear features to edges**:
1. For each H3 edge (pair of adjacent cells), compute the shared boundary segment as a Shapely LineString
2. Buffer each edge segment by a configurable tolerance (e.g., hex_diameter * 0.3)
3. For each NE linear feature geometry, test intersection with each buffered edge
4. Assign the feature to all edges it intersects

**Algorithm -- Point features to vertices**:
1. For each H3 vertex (triple junction), compute position as centroid of the 3 adjacent cell centroids
2. For each NE point feature, find the nearest vertex within a tolerance radius
3. Assign the feature to that vertex

**Performance**: The tri-county mesh has ~1,500-2,500 cells at resolution 7, yielding ~4,500-7,500 edges and ~3,000-5,000 vertices. NE features for the Detroit area are O(100) roads, O(50) railroads, O(5) airports, O(10) ports. Brute-force intersection is O(features * edges) = O(100 * 7,500) = O(750,000) -- fast enough without spatial indexing for MVP.

**Alternatives considered**:
- R-tree spatial index: Overkill for MVP scale. Can be added later if national-scale mesh requires it.
- Snap to cells instead of edges: Cells contain economic state; edges carry flow. Infrastructure affects flow, so edge assignment is correct.
