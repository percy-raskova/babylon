---
date: "2026-01-05T12:30:00-08:00"
researcher: Claude
git_commit: f4e1ad9
branch: dev
repository: babylon
topic: "DOT Transportation Data Integration into Babylon Territory System"
tags: [research, codebase, transportation, infrastructure, dot, territory, networkx, circulatory-system, coercive-infrastructure]
status: complete
last_updated: "2026-01-05"
last_updated_by: Claude
revision: 2
revision_note: "Added Section 12: Circulatory System Datasets with API access analysis"
---

# Research: DOT Transportation Data Integration

**Date**: 2026-01-05T12:30:00-08:00
**Researcher**: Claude
**Git Commit**: f4e1ad9
**Branch**: dev
**Repository**: babylon

## Research Question

How can DOT transportation data (rail, aviation, marine, highways, pipelines) be incorporated into Babylon's territory system and 3NF database schema in a way that captures enough realism for simulation while minimizing storage overhead and optimizing for performance?

## Summary

The DOT data files contain high-quality infrastructure data but at vastly different granularities (19.5M highway segments vs 84 marine ports). The optimal integration strategy is **county-level aggregation**: compute per-county infrastructure metrics and store them as transport edges between FIPS-coded territories. This aligns with Babylon's existing 5-digit FIPS infrastructure (DimCounty, CensusCounty) and the planned Epoch 2 territory ID scheme (US-CA-037).

The key insight from the existing architecture is that **Babylon already separates physical adjacency (ADJACENCY edges) from administrative hierarchy (TENANCY edges)**. Transportation should be a third layer: **multi-modal transport edges encoding capacity by mode**, following the Victoria 3 model of infrastructure as a property that modifies territory connectivity.

## Detailed Findings

### 1. DOT Data Source Inventory

| Dataset | Records | Size | FIPS Key | Simulation Value |
|---------|---------|------|----------|------------------|
| HPMS (Highways) | 19,573,740 | 9.5GB | COUNTY_ID (5-digit) | High - routes, capacity |
| Rail Network | 302,689 | 87MB | STCNTYFIPS (5-digit) | High - freight/passenger |
| Aviation | 19,707 | 8.9MB | STATE_CODE + COUNTY_NAME | Medium - hub nodes |
| Pipeline Terminals | 1,401 | 1MB | STATE_FIPS + CNTY_FIPS | High - energy infrastructure |
| Military Bases | 824 | 7.7MB | stateNameCode | Medium - strategic nodes |
| Marine RoRo | 84 | 308KB | STATE + CITY | High - port capacity |
| Rail Intermodal | 241 | 328KB | STATE + ZIP | Medium - multimodal hubs |
| Air-to-Truck | ~100 | 316KB | STATE + ZIP | Low - intermodal |

**Key Observation**: Only rail and highway data have county FIPS codes directly. Others require geocoding or city-to-county lookup.

### 2. Current Babylon Territory Architecture

From `src/babylon/models/entities/territory.py:21-193`:

```python
class Territory(BaseModel):
    id: str  # Pattern: ^T[0-9]{3}$ (e.g., "T001")
    name: str
    sector_type: SectorType  # INDUSTRIAL, RESIDENTIAL, etc.
    territory_type: TerritoryType  # CORE, PERIPHERY, RESERVATION, etc.
    heat: Intensity  # State attention [0, 1]
    population: int
    biocapacity: Currency  # Metabolic rift system
```

**Gap**: No geographic identifiers (FIPS codes, coordinates). Current IDs are abstract game IDs.

From `ai-docs/decisions/ADR029_hybrid_graph_architecture.yaml:65-85`:

Epoch 2 will use FIPS-based IDs:
```yaml
Territory:
  id: str (e.g., 'US-CA-037' for LA County)
  area_sq_km: float
  bioregion: str
```

**Implication**: Transportation integration should use FIPS-based territory IDs, compatible with both current county-level data infrastructure and planned Epoch 2 schema.

### 3. Existing Data Layer Infrastructure

From `src/babylon/data/normalize/schema.py`:

**Geographic Dimensions**:
- `DimState`: 2-digit FIPS, name, abbreviation
- `DimCounty`: 5-digit FIPS, FK to DimState
- `DimMetroArea`: CBSA codes (MSA/CSA)
- `BridgeCountyMetro`: Many-to-many county-metro mapping

**Pattern**: The data layer already uses 5-digit FIPS as the canonical geographic key. Transportation data should use the same.

### 4. EdgeType and Graph Architecture

From `src/babylon/models/enums.py:54-80`:

```python
class EdgeType(StrEnum):
    EXPLOITATION = "exploitation"  # Value extraction
    SOLIDARITY = "solidarity"      # Class consciousness
    TENANCY = "tenancy"           # SocialClass → Territory
    ADJACENCY = "adjacency"       # Territory → Territory
```

From `src/babylon/engine/systems/territory.py`:

- **ADJACENCY** edges are used for heat spillover and population displacement routing
- Current system iterates edges to find adjacent territories
- No multi-edge support - only one edge per type between nodes

**Gap**: No transport-specific edge types. ADJACENCY is binary (connected/not connected) with no capacity or mode information.

### 5. Proposed Schema Design

#### 5.1 Transport Mode Dimension

```sql
CREATE TABLE DimTransportMode (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,  -- 'rail', 'road', 'air', 'sea', 'pipeline'
    name TEXT NOT NULL,
    transport_class TEXT,       -- 'freight', 'passenger', 'both'
    capacity_unit TEXT,         -- 'lane_miles', 'track_miles', 'flights', etc.
    base_cost_per_unit REAL     -- Relative cost coefficient
);

-- Static seed data
INSERT INTO DimTransportMode (code, name, transport_class, capacity_unit, base_cost_per_unit) VALUES
('rail', 'Railroad', 'both', 'track_miles', 1.0),
('road', 'Highway', 'both', 'lane_miles', 2.0),
('air', 'Aviation', 'both', 'flights', 0.5),
('sea', 'Marine', 'freight', 'port_capacity', 0.3),
('pipeline', 'Pipeline', 'freight', 'terminals', 0.1);
```

#### 5.2 Transport Infrastructure Fact Table

```sql
CREATE TABLE FactTransportInfrastructure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county_fips TEXT NOT NULL,                -- 5-digit FIPS
    mode_id INTEGER NOT NULL REFERENCES DimTransportMode(id),
    year INTEGER NOT NULL,

    -- Capacity metrics (mode-specific)
    total_miles REAL DEFAULT 0.0,             -- Track miles / lane miles
    facility_count INTEGER DEFAULT 0,          -- Airports, ports, terminals
    major_hub_count INTEGER DEFAULT 0,         -- Class I terminals, major airports

    -- Traffic metrics (where available)
    annual_volume REAL DEFAULT 0.0,           -- VMT, tonnage, passengers
    avg_daily_traffic REAL DEFAULT 0.0,       -- AADT for highways

    -- Quality metrics
    condition_index REAL DEFAULT 1.0,         -- 0-1 infrastructure quality
    congestion_ratio REAL DEFAULT 0.0,        -- 0-1 utilization level

    -- Derived game metrics
    effective_capacity REAL GENERATED ALWAYS AS (
        total_miles * (1.0 - congestion_ratio) * condition_index
    ) STORED,

    UNIQUE(county_fips, mode_id, year)
);

-- Indexes for common queries
CREATE INDEX idx_transport_county ON FactTransportInfrastructure(county_fips);
CREATE INDEX idx_transport_mode ON FactTransportInfrastructure(mode_id);
CREATE INDEX idx_transport_year ON FactTransportInfrastructure(year);
```

#### 5.3 Transport Edge Table (County-to-County Connectivity)

```sql
CREATE TABLE FactTransportEdge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_fips TEXT NOT NULL,                -- Origin county
    target_fips TEXT NOT NULL,                -- Destination county
    mode_id INTEGER NOT NULL REFERENCES DimTransportMode(id),
    year INTEGER NOT NULL,

    -- Edge metrics
    route_miles REAL DEFAULT 0.0,             -- Actual distance
    lane_count INTEGER DEFAULT 1,             -- Tracks / lanes
    functional_class TEXT,                    -- 'interstate', 'arterial', 'local'

    -- Capacity
    capacity_score REAL DEFAULT 1.0,          -- 0-10 scale
    bottleneck_factor REAL DEFAULT 1.0,       -- Reduction for chokepoints

    -- For simulation
    effective_capacity REAL GENERATED ALWAYS AS (
        capacity_score * bottleneck_factor
    ) STORED,

    UNIQUE(source_fips, target_fips, mode_id, year)
);

-- Spatial indexes
CREATE INDEX idx_edge_source ON FactTransportEdge(source_fips);
CREATE INDEX idx_edge_target ON FactTransportEdge(target_fips);
CREATE INDEX idx_edge_mode ON FactTransportEdge(mode_id);
```

### 6. Data Reduction Strategy

**Problem**: 19.5M highway segments cannot be stored as-is.

**Solution**: County-level aggregation using SQL in the ETL pipeline.

#### 6.1 Highway Data Aggregation (HPMS)

Key HPMS fields for aggregation:
- `COUNTY_ID`: 5-digit FIPS
- `F_SYSTEM`: Functional classification (1=Interstate, 2=Principal Arterial, etc.)
- `AADT`: Annual Average Daily Traffic
- `THROUGH_LANES`: Number of lanes
- `ROUTE_ID`: For inter-county edge detection

```sql
-- County infrastructure summary
SELECT
    COUNTY_ID AS county_fips,
    SUM(SectionLength) AS total_miles,
    SUM(SectionLength * THROUGH_LANES) AS lane_miles,
    SUM(AADT * SectionLength) / NULLIF(SUM(SectionLength), 0) AS weighted_aadt,
    COUNT(DISTINCT CASE WHEN F_SYSTEM = 1 THEN ROUTE_ID END) AS interstate_routes,
    COUNT(DISTINCT CASE WHEN NHS = 1 THEN ROUTE_ID END) AS nhs_routes
FROM HPMS_Spatial_All_Sections
WHERE StateID IS NOT NULL
GROUP BY COUNTY_ID;
```

**Reduction**: 19.5M rows → ~3,100 county rows (99.98% reduction)

#### 6.2 Rail Network Aggregation

Key rail fields:
- `STCNTYFIPS`: 5-digit county FIPS
- `RROWNER1`: Railroad owner (BNSF, UP, CSXT, NS, etc.)
- `MILES`: Segment length
- `TRACKS`: Number of tracks
- `PASSNGR`: Passenger service (Y/N)
- `STRACNET`: Strategic Rail Corridor Network (Y/N)

```sql
-- County rail summary
SELECT
    STCNTYFIPS AS county_fips,
    SUM(MILES) AS total_track_miles,
    SUM(MILES * TRACKS) AS track_lane_miles,
    COUNT(DISTINCT RROWNER1) AS railroad_count,
    SUM(CASE WHEN PASSNGR = 'Y' THEN MILES ELSE 0 END) AS passenger_miles,
    SUM(CASE WHEN STRACNET = 'Y' THEN MILES ELSE 0 END) AS strategic_miles
FROM North_American_Rail_Network_Lines
WHERE COUNTRY = 'US'
GROUP BY STCNTYFIPS;

-- Inter-county rail edges (routes crossing county boundaries)
SELECT DISTINCT
    a.STCNTYFIPS AS source_fips,
    b.STCNTYFIPS AS target_fips,
    a.RROWNER1 AS railroad,
    MIN(a.TRACKS) AS min_tracks  -- Bottleneck
FROM North_American_Rail_Network_Lines a
JOIN North_American_Rail_Network_Lines b
    ON a.TOFRANODE = b.FRFRANODE  -- Connected segments
    AND a.STCNTYFIPS != b.STCNTYFIPS  -- Cross county boundary
WHERE a.COUNTRY = 'US' AND b.COUNTRY = 'US'
GROUP BY a.STCNTYFIPS, b.STCNTYFIPS, a.RROWNER1;
```

**Reduction**: 302,689 rows → ~3,100 county rows + ~8,000 edge rows

#### 6.3 Aviation Data Aggregation

Key aviation fields:
- `STATE_CODE`, `COUNTY_NAME`: Geographic (requires lookup)
- `SITE_TYPE_CODE`: A=Airport, H=Heliport, etc.
- `OWNERSHIP_TYPE_CODE`: PU=Public, PR=Private
- `FACILITY_USE_CODE`: PU=Public Use, PR=Private Use

```sql
-- County aviation summary
SELECT
    c.fips AS county_fips,
    COUNT(*) AS total_facilities,
    SUM(CASE WHEN SITE_TYPE_CODE = 'A' THEN 1 ELSE 0 END) AS airports,
    SUM(CASE WHEN SITE_TYPE_CODE = 'H' THEN 1 ELSE 0 END) AS heliports,
    SUM(CASE WHEN OWNERSHIP_TYPE_CODE = 'PU' AND FACILITY_USE_CODE = 'PU' THEN 1 ELSE 0 END) AS public_use
FROM Aviation_Facilities a
JOIN DimCounty c ON a.STATE_CODE = c.state_fips AND LOWER(a.COUNTY_NAME) = LOWER(c.name)
GROUP BY c.fips;
```

**Reduction**: 19,707 rows → ~2,500 county rows (counties with airports)

#### 6.4 Other Sources

| Source | Strategy | Output Rows |
|--------|----------|-------------|
| Marine RoRo | Point-in-county assignment | ~60 county rows |
| Pipeline | Point-in-county assignment | ~500 county rows |
| Military | Point-in-county assignment | ~400 county rows |
| Rail Intermodal | Point-in-county assignment | ~200 county rows |

### 7. NetworkX Integration Patterns

From `src/babylon/models/world_state.py:108-159`:

Current pattern creates edges from Relationship objects:
```python
for rel in self.relationships:
    source, target = rel.edge_tuple
    G.add_edge(source, target, **rel.edge_data)
```

**Proposed Extension**: MultiDiGraph for multi-modal transport

```python
# Instead of DiGraph, use MultiDiGraph for transport layer
G_transport: nx.MultiDiGraph = nx.MultiDiGraph()

# Add edges with mode as key
G_transport.add_edge(
    'US-CA-037',  # LA County
    'US-CA-065',  # Riverside County
    key='rail',
    mode='rail',
    capacity=calculate_rail_capacity(source_fips, target_fips),
    bottleneck=min_tracks_along_route,
    railroads=['BNSF', 'UP']
)

G_transport.add_edge(
    'US-CA-037',
    'US-CA-065',
    key='road',
    mode='road',
    capacity=calculate_road_capacity(source_fips, target_fips),
    lane_miles=sum_lane_miles,
    interstates=['I-10', 'I-15']
)
```

**Mode-Filtered Routing**:
```python
def route_by_mode(G: nx.MultiDiGraph, source: str, target: str, mode: str) -> list[str]:
    """Find shortest path using only specified transport mode."""
    mode_edges = [
        (u, v, k) for u, v, k, d in G.edges(keys=True, data=True)
        if d.get('mode') == mode
    ]
    mode_graph = G.edge_subgraph(mode_edges)
    return nx.shortest_path(mode_graph, source, target, weight='cost')
```

### 8. Victoria 3 Model Comparison

From web research on Victoria 3's infrastructure system:

| Aspect | Victoria 3 | Babylon Proposal |
|--------|------------|------------------|
| Infrastructure metric | Single `infrastructure` value per state | Multi-modal capacity per county |
| Connection model | Adjacency-based (neighbors share) | Edge-based (explicit routes) |
| Bottleneck | Min capacity along path to capital | Bottleneck factor on edges |
| Transport modes | Abstracted (rail provides both) | Explicit (rail, road, air, sea, pipeline) |
| Update cost | Property on territory | Edge capacity (O(1) update) |

**Key Insight**: Victoria 3's model is simpler (single metric) but loses modal information. Babylon's imperial rent mechanics benefit from mode-specific infrastructure (e.g., rail for coal extraction, ports for export).

### 9. Implementation Phases

#### Phase 0: Schema Extensions (Pre-requisite)

1. Add transport dimension and fact tables to `src/babylon/data/normalize/schema.py`
2. Create migration for marxist-data-3NF.sqlite
3. Add transport mode enum to `src/babylon/models/enums.py`

#### Phase 1: ETL Pipeline (Data Ingestion)

1. Create `src/babylon/data/transport/` directory with:
   - `schema.py` - SQLAlchemy models
   - `loader.py` - DataLoader implementation
   - `aggregator.py` - County-level aggregation queries
2. Add to `ALL_LOADERS` in `src/babylon/data/cli.py`
3. Create `mise run data:transport` task

#### Phase 2: Edge Generation (County-to-County)

1. Compute inter-county edges from rail network topology
2. Compute inter-county edges from highway route continuity
3. Store in `FactTransportEdge` table

#### Phase 3: Territory Integration

1. Add `fips` field to Territory model (optional, for Epoch 2 prep)
2. Create `TransportLayer` class that loads edges from DB into NetworkX
3. Implement `get_transport_capacity(source_fips, target_fips, mode)` function

#### Phase 4: System Integration

1. Modify `ImperialRentSystem` to use transport capacity for extraction efficiency
2. Add transport as factor in population displacement routing
3. Create `TransportSystem` for infrastructure degradation mechanics

### 10. Performance Estimates

| Metric | Raw Data | Aggregated |
|--------|----------|------------|
| Highway storage | 9.5 GB | ~5 MB |
| Rail storage | 87 MB | ~2 MB |
| Aviation storage | 8.9 MB | ~500 KB |
| Total DB footprint | ~10 GB | ~10 MB |
| Query time (county lookup) | N/A | <1ms (indexed) |
| Graph load time | N/A | ~100ms (10K edges) |

### 11. Data Quality Considerations

**HPMS Completeness**:
- All public roads should be included
- `COUNTY_ID` available on all records
- `AADT` may be null for low-volume roads (use functional class as proxy)

**Rail Network Completeness**:
- Class I railroads well-documented
- Short line railroads may be incomplete
- `STCNTYFIPS` not null where `COUNTRY='US'`

**Aviation Completeness**:
- Public airports well-documented
- Private airports may be incomplete
- County names require lookup (no FIPS on source)

**Geocoding Requirements**:
- Marine facilities: Need city-to-county lookup
- Pipeline terminals: Have FIPS codes directly
- Military bases: Have state codes, need county assignment

## Architecture Documentation

### Current State (Epoch 1)

```
Territory (T001-T999)
    ↓ ADJACENCY edges
Territory (T001-T999)
    │
    └─ No FIPS codes
    └─ No transport capacity
    └─ Binary connectivity
```

### Proposed State (Epoch 2)

```
Territory (US-CA-037)
    │
    ├─ ADJACENCY edges (physical neighbors)
    │
    └─ TRANSPORT edges by mode:
        ├─ rail: {capacity: 150, railroads: [BNSF, UP]}
        ├─ road: {capacity: 500, interstates: [I-10]}
        └─ air: {capacity: 50, airports: [LAX]}
```

### Data Flow

```
DOT Geodatabases (87MB - 9.5GB)
        ↓ ETL (aggregation queries)
FactTransportInfrastructure (~3K rows per mode)
FactTransportEdge (~10K rows per mode)
        ↓ Load at simulation start
nx.MultiDiGraph (transport layer)
        ↓ Query during tick
ImperialRentSystem, PopulationSystem
```

## Code References

- `src/babylon/models/entities/territory.py:21-193` - Territory model (no FIPS currently)
- `src/babylon/models/world_state.py:108-159` - Graph serialization
- `src/babylon/models/enums.py:54-80` - EdgeType enum (needs TRANSPORT)
- `src/babylon/data/normalize/schema.py` - DimCounty with FIPS codes
- `src/babylon/data/loader_base.py:148-248` - DataLoader ABC pattern
- `src/babylon/engine/systems/territory.py:266-300` - ADJACENCY edge traversal pattern

## Historical Context (from ADRs)

- **ADR029**: Hybrid Graph Architecture proposes FIPS-based territory IDs (US-CA-037)
- **ADR029-A1**: Sovereignty as edges, not properties (model for transport capacity)
- **ADR017**: Fractal Topology allows county-level territories in Epoch 2

## Open Questions

1. **Edge vs Property**: Should transport capacity be on edges (adjacency-based) or properties (territory attributes)? Recommendation: Edges for inter-county flow, properties for local infrastructure.

2. **Temporal Granularity**: How often should transport data be updated? Options: Annual refresh (matches HPMS cycle) or static 2024 baseline.

3. **International Routes**: Should edges extend to Canadian/Mexican counties for border infrastructure? The rail network already includes cross-border segments.

4. **Air Network Abstraction**: Aviation doesn't follow adjacency - should hub airports create non-adjacent edges (LAX → JFK)?

5. **Infrastructure Destruction**: How should system events (RUPTURE, natural disasters) affect transport edges?

## Recommendations

1. **Start with Rail**: Rail network is cleanest (direct FIPS codes, manageable 302K rows, clear topology). Implement rail first as proof of concept.

2. **Defer Highway Detail**: HPMS has rich data but requires significant aggregation. Start with county totals, add inter-county edges in Phase 2.

3. **Use Existing FIPS Infrastructure**: Leverage DimCounty from census loader rather than creating new geographic tables.

4. **Design for MultiDiGraph**: Even if current NetworkX is DiGraph, schema should support multiple edge types between same territory pair.

5. **Consider KuzuDB Integration**: ADR029 plans KuzuDB for Epoch 2. Transport edges are a natural fit for graph queries (`MATCH path = (a)-[:TRANSPORT*..3]-(b) WHERE a.fips = 'US-CA-037'`).

---

## 12. Circulatory System Datasets: Comprehensive Inventory

Beyond static infrastructure, the simulation requires **flow data** - the actual movement of commodities, labor, and coercive state power. This section catalogs datasets that model Babylon's "circulatory system" of value extraction.

### 12.1 Dataset Summary Table

| Dataset | Records | API Available | Public Access | Priority | Simulation Value |
|---------|---------|---------------|---------------|----------|------------------|
| FAF (Freight Analysis Framework) | 132 zones × 42 commodities | ❌ CSV only | ✅ Public domain | **Critical** | Commodity O-D flows |
| LEHD LODES | ~3M census blocks | ⚠️ LED Tool only | ✅ Public domain | **Critical** | Labor commuter flows |
| National Bridge Inventory | 624,000+ bridges | ❌ ASCII files | ✅ Public domain | **High** | Chokepoints/vulnerabilities |
| Commodity Flow Survey 2022 | 12.2B tons | ✅ Census API | ✅ Public domain | **High** | Detailed shipment data |
| HIFLD Prison Boundaries | ~7,000 facilities | ✅ ArcGIS API | ✅ Public (Open tier) | **High** | Carceral geography |
| HIFLD Law Enforcement | ~18,000 stations | ✅ ArcGIS API | ✅ Public (Open tier) | **High** | Repression capacity |
| MIRTA (Military Installations) | ~800 sites | ✅ ArcGIS API | ✅ Public domain | **Medium** | Strategic nodes |
| HIFLD Electric Grid | Substations + Lines | ✅ ArcGIS API | ✅ Public (Open tier) | **Medium** | Energy infrastructure |
| FCC Broadband | County-level | ✅ BDC API | ✅ Public domain | **Medium** | Communication infrastructure |
| ICE Detention | 528+ facilities | ❌ FOIA only | ⚠️ FOIA/NGO data | **Medium** | Immigration enforcement |

### 12.2 Tier 1: Flow Data (Critical Priority)

#### 12.2.1 Freight Analysis Framework (FAF) 5.7.1

**Source**: Bureau of Transportation Statistics (BTS) + FHWA
**URL**: https://www.bts.gov/faf

**What it provides**:
- Origin-Destination commodity flows between 132 FAF zones (aggregated county groups)
- 42 SCTG commodity types (agriculture, minerals, manufactured goods, etc.)
- Annual tonnage and value ($) by transport mode
- Forecasts to 2050

**Simulation Value**: This IS the circulatory system - actual tonnage/value flows of commodities between regions. Maps directly to "value transfer" and "unequal exchange" in MLM-TW theory. Shows which regions extract from which.

**API Availability**: ❌ **NO REST API**
- Data available only as downloadable CSV and MS Access files
- BTS is developing a "multimodal assignment and flow visualization tool" (future)
- County-level experimental data available at https://www.bts.gov/faf/county

**Access Method**:
```bash
# Direct download (recommended)
wget https://www.bts.gov/sites/bts.dot.gov/files/2024-08/FAF5.7.1_Regional_Database.zip

# Or use data.gov catalog
curl "https://catalog.data.gov/api/3/action/package_search?q=freight+analysis+framework"
```

**Legal Status**: ✅ **Public Domain** - U.S. Government work, no restrictions

**Data Schema (relevant fields)**:
```
dms_orig    - Origin FAF zone (3-digit)
dms_dest    - Destination FAF zone (3-digit)
sctg2       - 2-digit commodity code
trade_type  - 1=domestic, 2=import, 3=export
tons        - Tonnage (thousands)
value       - Value (millions $)
tmiles      - Ton-miles
dms_mode    - Transport mode (1=truck, 2=rail, 3=water, etc.)
year        - Data year (2017-2024, forecasts to 2050)
```

---

#### 12.2.2 LEHD LODES (Origin-Destination Employment Statistics)

**Source**: Census Bureau / Local Employment Dynamics Partnership
**URL**: https://lehd.ces.census.gov/data/

**What it provides**:
- Where workers live vs. where they work (at census block level)
- Job counts by wage category (low/medium/high)
- Industry sector (NAICS 2-digit)
- Annual updates

**Simulation Value**: Models labor circulation - workers commuting from periphery neighborhoods to core employment centers. Essential for modeling class geography and "internal colonies" (ADR017).

**API Availability**: ⚠️ **PARTIAL - LED Extraction Tool only**
- No REST API for raw data
- LED Extraction Tool provides graphical query interface: https://ledextract.ces.census.gov/
- Raw CSV files downloadable by state

**Access Method**:
```bash
# Direct file download (by state)
wget https://lehd.ces.census.gov/data/lodes/LODES8/ca/od/ca_od_main_JT00_2021.csv.gz

# File naming convention:
# {state}_od_main_JT00_{year}.csv.gz  (Origin-Destination, all jobs)
# {state}_rac_S000_JT00_{year}.csv.gz (Residence Area Characteristics)
# {state}_wac_S000_JT00_{year}.csv.gz (Workplace Area Characteristics)
```

**Legal Status**: ✅ **Public Domain** - Census Bureau, no restrictions

**Data Schema (OD files)**:
```
w_geocode   - Work census block (15-digit)
h_geocode   - Home census block (15-digit)
S000        - Total jobs
SA01        - Jobs for workers age 29 or younger
SA02        - Jobs for workers age 30-54
SA03        - Jobs for workers age 55+
SE01        - Jobs with earnings $1,250/month or less
SE02        - Jobs with earnings $1,251-$3,333/month
SE03        - Jobs with earnings $3,333+/month
SI01        - Goods-producing industry jobs
SI02        - Trade/transportation/utilities jobs
SI03        - All other services jobs
```

**Aggregation Note**: Block-level data must be aggregated to county FIPS for Babylon integration:
```python
# Extract county from census block geocode
county_fips = geocode[:5]  # First 5 digits = state (2) + county (3)
```

---

#### 12.2.3 National Bridge Inventory (NBI)

**Source**: FHWA
**URL**: https://www.fhwa.dot.gov/bridge/nbi/ascii.cfm

**What it provides**:
- 624,000+ bridges on public roads
- Condition ratings (0-9 scale for deck, superstructure, substructure)
- Traffic counts (ADT)
- Route information, structure type, year built

**Simulation Value**: Bridges are **chokepoints** - critical infrastructure that when damaged/destroyed severs circulation. Essential for modeling supply chain disruption, strategic vulnerabilities, and infrastructure warfare.

**API Availability**: ❌ **NO REST API**
- ASCII fixed-width files downloadable by year
- InfoBridge web portal allows filtering/export: https://infobridge.fhwa.dot.gov/data
- BTS GeoData provides shapefile: https://geodata.bts.gov/datasets/national-bridge-inventory/about

**Access Method**:
```bash
# ASCII file download (annual)
wget https://www.fhwa.dot.gov/bridge/nbi/2024/delimited/allstates2024.zip

# GeoJSON from BTS
curl "https://geodata.bts.gov/datasets/national-bridge-inventory.geojson"
```

**Legal Status**: ✅ **Public Domain** - U.S. Government work

**Data Schema (relevant fields)**:
```
STATE_CODE_001        - State FIPS (2-digit)
COUNTY_CODE_003       - County FIPS (3-digit)
STRUCTURE_NUMBER_008  - Unique bridge ID
FEATURES_DESC_006A    - Feature crossed (river, road, etc.)
FACILITY_CARRIED_007  - Route carried (I-95, US-1, etc.)
ADT_029               - Average Daily Traffic
YEAR_ADT_030          - Year of ADT count
YEAR_BUILT_027        - Year built
DECK_COND_058         - Deck condition (0-9)
SUPERSTRUCTURE_COND_059 - Superstructure condition (0-9)
SUBSTRUCTURE_COND_060 - Substructure condition (0-9)
LOWEST_RATING         - Derived: min(deck, super, sub)
```

**Bottleneck Detection Query**:
```sql
-- Find critical bridges (high traffic, poor condition)
SELECT county_fips, COUNT(*) as vulnerable_bridges
FROM bridges
WHERE LOWEST_RATING <= 4 AND ADT > 10000
GROUP BY county_fips
ORDER BY vulnerable_bridges DESC;
```

---

### 12.3 Tier 2: Coercive Infrastructure (High Priority)

#### 12.3.1 HIFLD Prison Boundaries

**Source**: DHS Homeland Infrastructure Foundation-Level Data (HIFLD)
**URL**: https://hifld-geoplatform.opendata.arcgis.com/datasets/geoplatform::prison-boundaries/about

**What it provides**:
- ~7,000 correctional facilities (federal, state, local, private)
- Geographic boundaries (polygons)
- Facility type, security level, capacity
- Operating status

**Simulation Value**: Maps the **carceral geography** - where the state concentrates its capacity for coercive control. Directly feeds `Territory.operational_profile` (PENAL_COLONY type from territorial-schema.yaml). Prison density affects labor availability and local economies.

**API Availability**: ✅ **ArcGIS REST API + GeoServices**
- Feature Service: Query, filter, export
- Download formats: CSV, GeoJSON, Shapefile, KML
- WMS/WFS available

**Access Method**:
```bash
# GeoJSON download
curl "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Prison_Boundaries/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson" -o prisons.geojson

# Or use ArcGIS Hub download
# https://hifld-geoplatform.opendata.arcgis.com/datasets/geoplatform::prison-boundaries/
```

**Legal Status**: ✅ **Public Domain (HIFLD Open tier)**
- No registration required for Open data
- HIFLD Secure tier requires DHS Data Use Agreement (not needed for prisons)

**Data Schema**:
```
FACILITYID  - Unique identifier
NAME        - Facility name
ADDRESS     - Street address
CITY        - City
STATE       - State abbreviation
COUNTY      - County name (needs FIPS lookup)
COUNTYFIPS  - County FIPS (where available)
TYPE        - Facility type (FEDERAL, STATE, LOCAL, PRIVATE)
SECURELVL   - Security level
CAPACITY    - Bed capacity
POPULATION  - Current population (may be outdated)
STATUS      - Operating status
```

---

#### 12.3.2 HIFLD Local Law Enforcement Locations

**Source**: DHS HIFLD / National Geospatial-Intelligence Agency (NGA)
**URL**: https://hifld-geoplatform.hub.arcgis.com/datasets/geoplatform::local-law-enforcement-locations/about

**What it provides**:
- ~18,000 police stations, sheriff offices, campus police
- Geographic coordinates
- Agency name, type, jurisdiction

**Simulation Value**: Distributed frontline of state coercive power. Police density affects organizing capacity, response time to dissent, and surveillance coverage. Maps "repression" variable in Survival Calculus.

**API Availability**: ✅ **ArcGIS REST API + GeoServices**
- Feature Service with query support
- Multiple download formats
- NASA MapServer mirror available

**Access Method**:
```bash
# GeoJSON via ArcGIS Feature Service
curl "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Local_Law_Enforcement_Locations/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson" -o police_stations.geojson

# NASA mirror
curl "https://maps.nccs.nasa.gov/mapping/rest/services/hifld_open/law_enforcement/MapServer/0/query?where=1=1&f=geojson"
```

**Legal Status**: ✅ **Public Domain (HIFLD Open tier)**

**County Aggregation**:
```sql
-- Police station density per county
SELECT county_fips,
       COUNT(*) as station_count,
       COUNT(*) * 1.0 / county_population * 10000 as stations_per_10k
FROM law_enforcement
GROUP BY county_fips;
```

---

#### 12.3.3 MIRTA (Military Installations, Ranges, and Training Areas)

**Source**: DoD Defense Installation Spatial Data Infrastructure (DISDI)
**URL**: https://catalog.data.gov/dataset/military-installations-ranges-and-training-areas

**What it provides**:
- ~800 DoD sites (bases, installations, training areas)
- Boundaries (polygons) and point locations
- Installation name, component (Army, Navy, etc.)
- Site type (base, range, depot, etc.)

**Simulation Value**: Concentrated state violence capacity. Strategic nodes for modeling civil war scenarios, National Guard deployment, and geographic distribution of federal coercive power. Distinct from police (local) - these are federal/military command chains.

**API Availability**: ✅ **ArcGIS FeatureServer**
- REST API at: https://services7.arcgis.com/n1YM8pTrFmm7L4hs/arcgis/rest/services/mirta/FeatureServer
- MIRTA Viewer: https://geospatial.sec.usace.army.mil/arcgis/apps/experiencebuilder/experience/?id=8e2a2247222546f084fcae617d3a335e
- Download: CSV, GeoJSON, Shapefile, KML

**Access Method**:
```bash
# Direct download from DoD
wget https://www.acq.osd.mil/eie/Downloads/MIRTA/MIRTA.zip

# ArcGIS Feature Service query
curl "https://services7.arcgis.com/n1YM8pTrFmm7L4hs/arcgis/rest/services/mirta/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson"
```

**Legal Status**: ✅ **Public Domain**
- Publicly releasable locations only
- Classified installations excluded from public data

---

#### 12.3.4 ICE Detention Facilities

**Source**: DHS OHSS / FOIA releases / NGO compilations
**URLs**:
- Official: https://ohss.dhs.gov/khsm/ice-detentions
- Deportation Data Project: https://deportationdata.org/data/ice.html
- Vera Institute: https://www.vera.org/ice-detention-trends
- Marshall Project GitHub: https://github.com/themarshallproject/dhs_immigration_detention

**What it provides**:
- 528+ active detention facilities (only 189 officially acknowledged)
- Facility locations, capacity, operator (private vs. federal)
- 17 years of historical data (2008-2025)
- 25 ERO field office jurisdictions

**Simulation Value**: Second layer of coercive infrastructure distinct from criminal justice. Immigration detention represents selective labor removal - creates labor supply shocks in agriculture, construction, meat processing. Models transnational labor control.

**API Availability**: ❌ **NO OFFICIAL API**
- Official DHS data via OHSS portal (limited)
- FOIA releases compiled by NGOs (most complete)
- Vera Institute GitHub provides cleaned datasets
- Marshall Project provides historical geocoded data

**Access Method**:
```bash
# Marshall Project GitHub (historical + geocoded)
git clone https://github.com/themarshallproject/dhs_immigration_detention.git

# Deportation Data Project (most current)
# Download from: https://deportationdata.org/data/ice.html
# Requires accepting terms, manual download

# Vera Institute (via GitHub)
# Check their data tools page for latest releases
```

**Legal Status**: ⚠️ **Mixed**
- Official DHS data: Public domain
- FOIA releases: Public domain once released
- NGO compilations: Various licenses, check each source
- **Recommendation**: Use Marshall Project data (explicitly CC-licensed for reuse)

**Data Quality Note**: Government undercounts facility count. Vera found 528 active facilities vs. 189 officially listed. Use NGO data for completeness.

---

### 12.4 Tier 3: Supporting Infrastructure (Medium Priority)

#### 12.4.1 Commodity Flow Survey 2022

**Source**: Census Bureau + BTS
**URL**: https://www.census.gov/data/developers/data-sets/cfs.html

**What it provides**:
- 12.2 billion tons of goods, $18.0 trillion value
- Shipment origin/destination, commodity type, mode
- More granular than FAF (shipment-level vs. zone-level)

**Simulation Value**: Complements FAF with finer commodity detail. Shows actual business-to-business flows within supply chains.

**API Availability**: ✅ **Census Bureau API**
```
# API endpoint
https://api.census.gov/data/2022/cfsarea

# Example query
https://api.census.gov/data/2022/cfsarea?get=NAME,GEO_ID,COMM,VAL,TON&for=state:*&key=YOUR_KEY
```

**Legal Status**: ✅ **Public Domain**

**Requires**: Census API key (free registration at https://api.census.gov/data/key_signup.html)

---

#### 12.4.2 HIFLD Electric Grid Infrastructure

**Source**: DHS HIFLD
**URLs**:
- Substations: https://hifld-geoplatform.opendata.arcgis.com/datasets/755e8c8ae15a4c9abfceca7b2e95fb9a_0
- Transmission Lines: https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-power-transmission-lines

**What it provides**:
- Electric substations (69+ kV)
- Transmission lines
- Voltage ratings, operator information

**Simulation Value**: Power is upstream of everything - factories, surveillance, communication, hospitals. Substation density reveals grid resilience vs. single-point-of-failure vulnerabilities. Power outages cascade through all other systems.

**API Availability**: ✅ **ArcGIS REST API**
```bash
# Substations GeoJSON
curl "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Substations/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson"
```

**Legal Status**: ✅ **Public Domain (HIFLD Open)**

---

#### 12.4.3 FCC Broadband Coverage

**Source**: Federal Communications Commission
**URL**: https://broadbandmap.fcc.gov/data-download

**What it provides**:
- Broadband availability by location
- Speed tiers (25/3, 100/20, 1000/100 Mbps)
- Provider information
- County and census tract aggregations

**Simulation Value**: Digital infrastructure inequality. Affects organizing capacity (can workers communicate?), surveillance capability (can state monitor?), remote work accessibility, and financial flows.

**API Availability**: ✅ **BDC Public Data API**
- API spec: https://www.fcc.gov/sites/default/files/bdc-public-data-api-spec.pdf
- Requires username/token registration
- Rate limit: 10 calls/minute

**Access Method**:
```bash
# Data download portal (bulk files)
# https://broadbandmap.fcc.gov/data-download

# API requires registration - see spec PDF for endpoints
```

**Legal Status**: ✅ **Public Domain**

---

### 12.5 Proposed Schema Extensions

Building on Section 5's transport schema, add tables for circulatory system data:

```sql
-- ============================================
-- COMMODITY FLOW TABLES (from FAF/CFS)
-- ============================================

CREATE TABLE DimCommodity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sctg_code TEXT UNIQUE NOT NULL,  -- 2-digit SCTG code
    name TEXT NOT NULL,
    category TEXT,  -- 'agriculture', 'mining', 'manufacturing', etc.
    strategic_value TEXT  -- 'basic', 'intermediate', 'critical'
);

CREATE TABLE FactCommodityFlow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_fips TEXT NOT NULL,
    destination_fips TEXT NOT NULL,
    commodity_id INTEGER NOT NULL REFERENCES DimCommodity(id),
    year INTEGER NOT NULL,
    tons_thousands REAL,
    value_millions REAL,
    primary_mode TEXT,  -- 'truck', 'rail', 'water', 'air', 'pipeline', 'multimodal'
    UNIQUE(origin_fips, destination_fips, commodity_id, year)
);

-- ============================================
-- LABOR FLOW TABLES (from LODES)
-- ============================================

CREATE TABLE FactLaborFlow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_county_fips TEXT NOT NULL,
    work_county_fips TEXT NOT NULL,
    year INTEGER NOT NULL,
    total_jobs INTEGER,
    low_wage_jobs INTEGER,    -- <= $1,250/month
    mid_wage_jobs INTEGER,    -- $1,251-$3,333/month
    high_wage_jobs INTEGER,   -- > $3,333/month
    goods_producing_jobs INTEGER,
    service_jobs INTEGER,
    UNIQUE(home_county_fips, work_county_fips, year)
);

-- ============================================
-- COERCIVE INFRASTRUCTURE TABLES
-- ============================================

CREATE TABLE DimCoerciveType (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,  -- 'prison', 'jail', 'police', 'military', 'ice'
    name TEXT NOT NULL,
    category TEXT,  -- 'carceral', 'enforcement', 'military'
    command_chain TEXT  -- 'federal', 'state', 'local'
);

CREATE TABLE FactCoerciveInfrastructure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county_fips TEXT NOT NULL,
    coercive_type_id INTEGER NOT NULL REFERENCES DimCoerciveType(id),
    facility_count INTEGER DEFAULT 0,
    total_capacity INTEGER,  -- beds for prisons, personnel for police
    year INTEGER NOT NULL,
    UNIQUE(county_fips, coercive_type_id, year)
);

-- ============================================
-- CRITICAL INFRASTRUCTURE TABLES (chokepoints)
-- ============================================

CREATE TABLE FactBridgeVulnerability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county_fips TEXT NOT NULL,
    year INTEGER NOT NULL,
    total_bridges INTEGER,
    vulnerable_bridges INTEGER,  -- condition rating <= 4
    high_traffic_vulnerable INTEGER,  -- vulnerable AND ADT > 10000
    avg_condition REAL,
    total_adt INTEGER,
    UNIQUE(county_fips, year)
);

-- ============================================
-- COMMUNICATION INFRASTRUCTURE (FCC)
-- ============================================

CREATE TABLE FactBroadbandCoverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county_fips TEXT NOT NULL,
    year INTEGER NOT NULL,
    pct_25_3 REAL,   -- % with 25/3 Mbps access
    pct_100_20 REAL, -- % with 100/20 Mbps access
    pct_1000_100 REAL, -- % with gigabit access
    provider_count INTEGER,
    UNIQUE(county_fips, year)
);
```

### 12.6 NetworkX Integration for Circulatory System

```python
from enum import StrEnum
import networkx as nx

class CirculatoryEdgeType(StrEnum):
    """Edge types for circulatory system flows."""
    COMMODITY_FLOW = "commodity_flow"
    LABOR_FLOW = "labor_flow"
    COERCIVE_CAPACITY = "coercive_capacity"
    ENERGY_FLOW = "energy_flow"

def build_circulatory_graph(
    commodity_flows: list[dict],
    labor_flows: list[dict],
    coercive_facilities: list[dict],
) -> nx.MultiDiGraph:
    """Build multi-layer circulatory system graph.

    Layers:
    1. Commodity flows (FAF/CFS) - value extraction routes
    2. Labor flows (LODES) - worker circulation
    3. Coercive capacity (HIFLD) - repression infrastructure
    """
    G = nx.MultiDiGraph()

    # Layer 1: Commodity flows (directed by value transfer)
    for flow in commodity_flows:
        G.add_edge(
            flow["origin_fips"],
            flow["destination_fips"],
            key=f"commodity_{flow['commodity_code']}",
            edge_type=CirculatoryEdgeType.COMMODITY_FLOW,
            commodity=flow["commodity_code"],
            tons=flow["tons"],
            value=flow["value"],
            mode=flow["mode"],
        )

    # Layer 2: Labor flows (directed from home to work)
    for flow in labor_flows:
        G.add_edge(
            flow["home_fips"],
            flow["work_fips"],
            key="labor",
            edge_type=CirculatoryEdgeType.LABOR_FLOW,
            workers=flow["total_jobs"],
            low_wage=flow["low_wage_jobs"],
            high_wage=flow["high_wage_jobs"],
        )

    # Layer 3: Coercive capacity (node attributes, not edges)
    for facility in coercive_facilities:
        fips = facility["county_fips"]
        if fips not in G:
            G.add_node(fips)

        # Accumulate coercive capacity
        current = G.nodes[fips].get("coercive_capacity", 0)
        G.nodes[fips]["coercive_capacity"] = current + facility.get("capacity", 1)

        # Track by type
        ftype = facility["type"]  # 'prison', 'police', 'military'
        type_key = f"{ftype}_capacity"
        current_type = G.nodes[fips].get(type_key, 0)
        G.nodes[fips][type_key] = current_type + facility.get("capacity", 1)

    return G

def calculate_value_extraction(G: nx.MultiDiGraph, periphery_fips: str) -> float:
    """Calculate total value extracted from a periphery county.

    Value extraction = sum of outbound commodity value - inbound commodity value
    """
    outbound = sum(
        d.get("value", 0)
        for _, _, d in G.out_edges(periphery_fips, data=True)
        if d.get("edge_type") == CirculatoryEdgeType.COMMODITY_FLOW
    )
    inbound = sum(
        d.get("value", 0)
        for _, _, d in G.in_edges(periphery_fips, data=True)
        if d.get("edge_type") == CirculatoryEdgeType.COMMODITY_FLOW
    )
    return outbound - inbound  # Positive = net extraction (periphery)

def calculate_labor_drain(G: nx.MultiDiGraph, county_fips: str) -> dict:
    """Calculate labor drain from a county.

    Labor drain = workers commuting OUT - workers commuting IN
    Also tracks wage differential (are high-wage jobs leaving?)
    """
    outbound_workers = sum(
        d.get("workers", 0)
        for _, _, d in G.out_edges(county_fips, data=True)
        if d.get("edge_type") == CirculatoryEdgeType.LABOR_FLOW
    )
    inbound_workers = sum(
        d.get("workers", 0)
        for _, _, d in G.in_edges(county_fips, data=True)
        if d.get("edge_type") == CirculatoryEdgeType.LABOR_FLOW
    )

    outbound_high_wage = sum(
        d.get("high_wage", 0)
        for _, _, d in G.out_edges(county_fips, data=True)
        if d.get("edge_type") == CirculatoryEdgeType.LABOR_FLOW
    )
    inbound_high_wage = sum(
        d.get("high_wage", 0)
        for _, _, d in G.in_edges(county_fips, data=True)
        if d.get("edge_type") == CirculatoryEdgeType.LABOR_FLOW
    )

    return {
        "net_workers": inbound_workers - outbound_workers,  # Positive = net importer
        "net_high_wage": inbound_high_wage - outbound_high_wage,
        "is_bedroom_community": outbound_workers > inbound_workers * 1.5,
        "is_employment_center": inbound_workers > outbound_workers * 1.5,
    }
```

### 12.7 Data Loader Implementation Recommendations

Based on API availability analysis:

| Dataset | Recommended Approach | Rationale |
|---------|---------------------|-----------|
| **FAF** | Bulk CSV download + local cache | No API; data stable (annual updates) |
| **LODES** | Bulk CSV download by state | LED Tool not scriptable; files well-structured |
| **NBI** | ASCII download + InfoBridge for filtering | No API; InfoBridge useful for exploration |
| **CFS** | Census API | Official API with good coverage |
| **HIFLD (all)** | ArcGIS REST API | Full API support, GeoJSON export |
| **MIRTA** | ArcGIS REST API | Full API support |
| **ICE** | Marshall Project GitHub clone | Most complete, explicitly licensed |
| **FCC Broadband** | Bulk download (API requires auth) | API rate-limited; bulk files sufficient |

**Loader Pattern** (following existing `src/babylon/data/loader_base.py`):

```python
from babylon.data.loader_base import DataLoader
from babylon.data.transport.schema import FactCommodityFlow

class FAFLoader(DataLoader[FactCommodityFlow]):
    """Loader for Freight Analysis Framework data."""

    source_name = "faf"
    source_url = "https://www.bts.gov/faf"
    requires_api_key = False
    update_frequency = "annual"

    def download(self) -> Path:
        """Download FAF regional database."""
        url = "https://www.bts.gov/sites/bts.dot.gov/files/2024-08/FAF5.7.1_Regional_Database.zip"
        return self._download_and_extract(url)

    def parse(self, file_path: Path) -> Iterator[FactCommodityFlow]:
        """Parse FAF CSV into commodity flow records."""
        # Implementation follows existing loader patterns
        ...

class HIFLDLoader(DataLoader):
    """Loader for HIFLD ArcGIS data."""

    source_name = "hifld"
    base_url = "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services"
    requires_api_key = False

    def query_feature_service(
        self,
        service_name: str,
        where: str = "1=1",
        out_fields: str = "*",
    ) -> dict:
        """Query HIFLD ArcGIS Feature Service."""
        url = f"{self.base_url}/{service_name}/FeatureServer/0/query"
        params = {
            "where": where,
            "outFields": out_fields,
            "f": "geojson",
            "resultRecordCount": 10000,
        }
        # Pagination for large datasets
        ...
```

### 12.8 Legal and Ethical Considerations

| Dataset | Legal Status | Restrictions | Notes |
|---------|--------------|--------------|-------|
| FAF | Public Domain | None | U.S. Government work |
| LODES | Public Domain | None | Census Bureau |
| NBI | Public Domain | None | FHWA |
| CFS | Public Domain | API key required | Free registration |
| HIFLD Open | Public Domain | None | DHS explicitly public |
| HIFLD Secure | Restricted | DUA required | NOT NEEDED for our use |
| MIRTA | Public Domain | None | Unclassified only |
| ICE (Marshall) | CC-BY | Attribution | Cite Marshall Project |
| FCC | Public Domain | Rate limits | 10 req/min |

**All datasets used are publicly accessible government data or explicitly CC-licensed NGO compilations.**

No FOIA requests, scraping, or restricted access required.

### 12.9 Implementation Priority

**Phase 1 (Critical - Circulatory Flows)**:
1. FAF Loader - commodity O-D flows
2. LODES Loader - labor commuter flows
3. Add `FactCommodityFlow`, `FactLaborFlow` tables

**Phase 2 (High - Coercive Infrastructure)**:
4. HIFLD Prison Loader
5. HIFLD Law Enforcement Loader
6. Add `FactCoerciveInfrastructure` table

**Phase 3 (Medium - Supporting)**:
7. NBI Bridge Loader (chokepoints)
8. MIRTA Military Loader
9. Electric Grid Loader
10. FCC Broadband Loader

**Phase 4 (Integration)**:
11. Build circulatory MultiDiGraph
12. Integrate with ImperialRentSystem (value flows affect extraction)
13. Integrate with SurvivalSystem (coercive capacity affects P(S|R))
