# BabylonDB Data Infrastructure Gaps - Implementation Plan

## Status: PLANNED

| Phase | Name | Status | Dependencies |
|-------|------|--------|--------------|
| 1 | Land Cover (NLCD) | PLANNED | None |
| 2 | Hydrology (NHD) | PLANNED | None |
| 3 | Elevation (3DEP) | PLANNED | None |
| 4 | Agriculture (NASS) | PLANNED | None |
| 5 | Climate (NOAA CDO) | PLANNED | None |
| 6 | Transportation (DOT) | PLANNED | Existing data in data/dot/ |
| 7 | Schema Integration | PLANNED | Phases 1-6 |

---

## Context

BabylonDB currently has comprehensive economic and demographic data infrastructure:
- **Census**: ACS 5-year employment, demographics, race/gender disaggregation
- **QCEW**: Quarterly employment/wages by industry (hybrid API + file)
- **FRED**: Macroeconomic time series (GDP, inflation, unemployment)
- **Energy**: State-level energy production/consumption (EIA API)
- **Trade**: International trade flows (Census Bureau)
- **Materials**: Raw materials production
- **HIFLD**: Critical infrastructure (prisons, police, electric grid)
- **FCC**: Broadband coverage
- **MIRTA**: Mass transit infrastructure

**What's Missing**: Physical geography, agriculture, climate, and transportation loaders.

The game specs already reference terrain barriers (RIVER, MOUNTAIN in kinetic-warfare.yaml, balkanization-spec.yaml) but no data exists to populate them.

---

## Phase 1: Land Cover (USGS NLCD)

### Purpose
National Land Cover Database provides county-level breakdown of land types: forest, wetland, developed, agricultural, barren, water, etc.

### Data Source
- **API**: USGS MRLC (Multi-Resolution Land Characteristics)
- **Format**: GeoTIFF raster, but statistics available via WCS/STAC
- **Coverage**: 30m resolution, nationwide
- **Update Frequency**: Every 2-3 years (2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021)

### Schema Additions

```python
# Dimension Table
class DimLandCover(Base):
    """Land cover classification (Anderson Level II)."""
    __tablename__ = "dim_land_cover"

    id: Mapped[int] = mapped_column(primary_key=True)
    nlcd_code: Mapped[int] = mapped_column(unique=True)  # 11, 21, 22, 23, 24, 31, 41, 42, 43, 52, 71, 81, 82, 90, 95
    name: Mapped[str]  # "Open Water", "Developed, Open Space", etc.
    category: Mapped[str]  # "Water", "Developed", "Forest", "Shrubland", "Herbaceous", "Planted/Cultivated", "Wetlands"
    game_terrain_type: Mapped[str | None]  # Maps to game terrain: "WATER", "URBAN", "FOREST", "WETLAND", "AGRICULTURAL", "BARREN"

# Fact Table
class FactCountyLandCover(Base):
    """County-level land cover composition."""
    __tablename__ = "fact_county_land_cover"

    id: Mapped[int] = mapped_column(primary_key=True)
    county_fips: Mapped[str] = mapped_column(ForeignKey("dim_county.fips"))
    land_cover_id: Mapped[int] = mapped_column(ForeignKey("dim_land_cover.id"))
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.id"))

    area_sq_km: Mapped[float]  # Area in square kilometers
    percent_of_county: Mapped[float]  # Percentage of total county area
```

### Implementation Tasks

1. Create `src/babylon/data/nlcd/` module:
   - `__init__.py`
   - `api_client.py` - NLCD statistics API client
   - `loader_3nf.py` - 3NF loader following existing patterns
   - `schema.py` - Raw/intermediate schema if needed

2. Add DimLandCover and FactCountyLandCover to `src/babylon/data/normalize/schema.py`

3. Create tests:
   - `tests/unit/data/test_nlcd_loader.py`
   - `tests/integration/data/test_nlcd_integration.py`

### Game Integration
- Forest coverage affects guerrilla warfare effectiveness (cover)
- Wetland/water affects movement costs
- Urban density affects surveillance/control
- Agricultural land determines food production potential

---

## Phase 2: Hydrology (USGS NHD/3DHP)

### Purpose
National Hydrography Dataset provides rivers, lakes, watersheds, and drainage areas. Critical for:
- Natural barriers affecting movement
- Water resources for agriculture/population
- Flooding vulnerability

### Data Source
- **API**: USGS 3DHP (replacing NHD) or NHD MapServer
- **Format**: GeoJSON via REST API
- **Coverage**: All US water features
- **Key Features**: Flowlines (rivers/streams), Waterbodies (lakes/reservoirs), Watersheds (HUC boundaries)

### Schema Additions

```python
# Dimension Table
class DimWaterFeatureType(Base):
    """Water feature classification."""
    __tablename__ = "dim_water_feature_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)  # "STREAM", "RIVER", "LAKE", "RESERVOIR", "WETLAND"
    name: Mapped[str]
    is_barrier: Mapped[bool]  # Does this impede land movement?
    is_navigable: Mapped[bool]  # Can watercraft use this?

# Fact Table
class FactCountyHydrology(Base):
    """County-level hydrology summary."""
    __tablename__ = "fact_county_hydrology"

    id: Mapped[int] = mapped_column(primary_key=True)
    county_fips: Mapped[str] = mapped_column(ForeignKey("dim_county.fips"))
    water_feature_type_id: Mapped[int] = mapped_column(ForeignKey("dim_water_feature_type.id"))

    total_length_km: Mapped[float | None]  # For linear features (rivers)
    total_area_sq_km: Mapped[float | None]  # For areal features (lakes)
    count: Mapped[int]  # Number of features
    major_feature_name: Mapped[str | None]  # Name of largest feature (e.g., "Mississippi River")
```

### Implementation Tasks

1. Create `src/babylon/data/hydrology/` module:
   - `__init__.py`
   - `api_client.py` - NHD/3DHP API client
   - `loader_3nf.py` - 3NF loader
   - `schema.py` - Raw schema

2. Add dimension and fact tables to normalized schema

3. Create tests

### Game Integration
- Rivers as natural barriers (crossing requires bridges/infrastructure)
- Lakes as impassable terrain
- Major rivers as supply routes (Mississippi, Ohio, Columbia)
- Watershed boundaries for regional organization

---

## Phase 3: Elevation (USGS 3DEP)

### Purpose
3D Elevation Program provides terrain elevation data. Critical for:
- Mountain barriers
- Terrain difficulty for movement
- Line-of-sight for communications/surveillance

### Data Source
- **API**: USGS 3DEP elevation service
- **Format**: Raster statistics via OGC services
- **Coverage**: 1m to 30m resolution nationwide
- **Key Metrics**: Min, max, mean elevation; slope; terrain ruggedness

### Schema Additions

```python
# Fact Table (no new dimension needed - uses existing DimCounty)
class FactCountyTerrain(Base):
    """County-level terrain characteristics."""
    __tablename__ = "fact_county_terrain"

    id: Mapped[int] = mapped_column(primary_key=True)
    county_fips: Mapped[str] = mapped_column(ForeignKey("dim_county.fips"))

    elevation_min_m: Mapped[float]
    elevation_max_m: Mapped[float]
    elevation_mean_m: Mapped[float]
    elevation_std_m: Mapped[float]  # Terrain variability
    slope_mean_deg: Mapped[float]  # Average slope
    slope_max_deg: Mapped[float]
    terrain_ruggedness_index: Mapped[float]  # TRI metric

    # Derived game metrics
    is_mountainous: Mapped[bool]  # elevation_max - elevation_min > 1000m
    is_coastal: Mapped[bool]  # elevation_min < 10m and borders ocean
```

### Implementation Tasks

1. Create `src/babylon/data/elevation/` module

2. Add FactCountyTerrain to normalized schema

3. Create tests

### Game Integration
- Mountainous terrain as barriers (Appalachians, Rockies, Sierra Nevada)
- Coastal vs inland distinction
- Terrain difficulty affects military operations
- Elevation affects climate/agriculture suitability

---

## Phase 4: Agriculture (USDA NASS)

### Purpose
National Agricultural Statistics Service provides county-level agricultural data:
- Crop production (acres, yield, value)
- Livestock inventory
- Farm economics

### Data Source
- **API**: USDA NASS Quick Stats API
- **Format**: JSON/CSV
- **Coverage**: All US counties
- **Update Frequency**: Annual surveys, Census of Agriculture every 5 years

### Schema Additions

```python
# Dimension Tables
class DimCommodity(Base):
    """Agricultural commodity classification."""
    __tablename__ = "dim_commodity"

    id: Mapped[int] = mapped_column(primary_key=True)
    commodity_code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]  # "CORN", "SOYBEANS", "WHEAT", "CATTLE", etc.
    category: Mapped[str]  # "GRAIN", "OILSEED", "LIVESTOCK", "DAIRY", "FRUIT", "VEGETABLE"
    is_staple: Mapped[bool]  # Critical for food security
    calories_per_unit: Mapped[float | None]  # For food security calculations

class DimStatistic(Base):
    """Agricultural statistic type."""
    __tablename__ = "dim_ag_statistic"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)  # "AREA PLANTED", "AREA HARVESTED", "PRODUCTION", "YIELD", "VALUE"
    name: Mapped[str]
    unit: Mapped[str]  # "ACRES", "BU", "$", "HEAD"

# Fact Table
class FactCountyAgriculture(Base):
    """County-level agricultural production."""
    __tablename__ = "fact_county_agriculture"

    id: Mapped[int] = mapped_column(primary_key=True)
    county_fips: Mapped[str] = mapped_column(ForeignKey("dim_county.fips"))
    commodity_id: Mapped[int] = mapped_column(ForeignKey("dim_commodity.id"))
    statistic_id: Mapped[int] = mapped_column(ForeignKey("dim_ag_statistic.id"))
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.id"))

    value: Mapped[float]
    cv_percent: Mapped[float | None]  # Coefficient of variation (data quality)
```

### Implementation Tasks

1. Create `src/babylon/data/nass/` module:
   - `__init__.py`
   - `api_client.py` - NASS Quick Stats API client
   - `loader_3nf.py` - 3NF loader
   - `schema.py` - Raw schema

2. Add dimension and fact tables to normalized schema

3. Create tests

### Game Integration
- Agricultural output → food security → survival probability
- Cash crop vs subsistence farming distinction
- Agricultural labor → class composition
- Farm crisis events (drought, blight) affect rural regions

---

## Phase 5: Climate (NOAA CDO)

### Purpose
Climate Data Online provides historical and normal climate data:
- Temperature (monthly normals, extremes)
- Precipitation (monthly totals, drought indices)
- Growing season length

### Data Source
- **API**: NOAA Climate Data Online (CDO) API
- **Format**: JSON
- **Coverage**: Climate divisions (maps to counties)
- **Key Datasets**: Climate Normals 1991-2020, GHCN-Daily

### Schema Additions

```python
# Dimension Table
class DimClimateDivision(Base):
    """NOAA climate division (aggregation unit)."""
    __tablename__ = "dim_climate_division"

    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[str] = mapped_column(unique=True)  # State FIPS + division number
    state_fips: Mapped[str] = mapped_column(ForeignKey("dim_state.fips"))
    name: Mapped[str]

# Fact Table
class FactClimateNormals(Base):
    """30-year climate normals by county."""
    __tablename__ = "fact_climate_normals"

    id: Mapped[int] = mapped_column(primary_key=True)
    county_fips: Mapped[str] = mapped_column(ForeignKey("dim_county.fips"))
    month: Mapped[int]  # 1-12, or 0 for annual

    temp_mean_f: Mapped[float]
    temp_max_f: Mapped[float]
    temp_min_f: Mapped[float]
    precip_inches: Mapped[float]
    heating_degree_days: Mapped[float]
    cooling_degree_days: Mapped[float]
    growing_degree_days: Mapped[float | None]

    # Derived
    koppen_zone: Mapped[str | None]  # Climate classification (Cfa, Dfb, BSk, etc.)
    usda_hardiness_zone: Mapped[str | None]  # Plant hardiness zone
```

### Implementation Tasks

1. Create `src/babylon/data/climate/` module:
   - `__init__.py`
   - `api_client.py` - NOAA CDO API client (requires API key)
   - `loader_3nf.py` - 3NF loader
   - `schema.py` - Raw schema

2. Add dimension and fact tables to normalized schema

3. Create tests

### Game Integration
- Climate affects agricultural potential
- Extreme temperatures affect survival/energy needs
- Drought conditions trigger agricultural crises
- Heating/cooling degree days affect energy consumption

---

## Phase 6: Transportation (DOT)

### Purpose
Load existing DOT transportation data from `data/dot/` directory into 3NF schema.

### Data Source
- **Location**: `data/dot/` (already downloaded)
- **Format**: CSV/Shapefile
- **Contents**: Interstate highways, rail lines, airports, ports

### Schema Additions

```python
# Dimension Tables
class DimTransportMode(Base):
    """Transportation mode classification."""
    __tablename__ = "dim_transport_mode"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)  # "HIGHWAY", "RAIL", "AIR", "PORT", "PIPELINE"
    name: Mapped[str]
    is_freight: Mapped[bool]
    is_passenger: Mapped[bool]

class DimRoadClass(Base):
    """Road classification (functional class)."""
    __tablename__ = "dim_road_class"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[int]  # 1-7 functional class
    name: Mapped[str]  # "Interstate", "Principal Arterial", etc.
    capacity_factor: Mapped[float]  # Relative throughput capacity

# Fact Tables
class FactCountyRoads(Base):
    """County-level road network summary."""
    __tablename__ = "fact_county_roads"

    id: Mapped[int] = mapped_column(primary_key=True)
    county_fips: Mapped[str] = mapped_column(ForeignKey("dim_county.fips"))
    road_class_id: Mapped[int] = mapped_column(ForeignKey("dim_road_class.id"))

    total_miles: Mapped[float]
    lane_miles: Mapped[float]

class FactCountyTransportNodes(Base):
    """Major transport nodes (airports, ports, rail yards)."""
    __tablename__ = "fact_county_transport_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    county_fips: Mapped[str] = mapped_column(ForeignKey("dim_county.fips"))
    transport_mode_id: Mapped[int] = mapped_column(ForeignKey("dim_transport_mode.id"))

    node_count: Mapped[int]
    total_capacity: Mapped[float | None]  # Mode-specific capacity metric
    major_node_name: Mapped[str | None]  # Name of largest node
```

### Implementation Tasks

1. Investigate existing `data/dot/` contents and structure

2. Create `src/babylon/data/transportation/` module:
   - `__init__.py`
   - `loader_3nf.py` - 3NF loader for local files
   - `schema.py` - Raw schema

3. Add dimension and fact tables to normalized schema

4. Create tests

### Game Integration
- Highway network defines supply lines
- Rail network for bulk freight (coal, grain, military equipment)
- Airports as strategic nodes (military, evacuation)
- Ports for international trade/military projection

---

## Phase 7: Schema Integration

### Purpose
Integrate all new tables into the unified 3NF schema and update LoaderConfig.

### Tasks

1. Add all new dimension tables to `schema.py`:
   - DimLandCover
   - DimWaterFeatureType
   - DimCommodity
   - DimStatistic (agricultural)
   - DimClimateDivision
   - DimTransportMode
   - DimRoadClass

2. Add all new fact tables to `schema.py`:
   - FactCountyLandCover
   - FactCountyHydrology
   - FactCountyTerrain
   - FactCountyAgriculture
   - FactClimateNormals
   - FactCountyRoads
   - FactCountyTransportNodes

3. Update `LoaderConfig` with new configuration options:
   - nlcd_years: list[int]
   - nass_commodities: list[str]
   - climate_normals_period: str
   - api_keys for new services

4. Update `__all__` exports in normalize module

5. Add integration test for full schema creation

---

## API Keys Required

| Service | Key Required | Registration URL |
|---------|--------------|------------------|
| USGS NLCD | No | - |
| USGS NHD/3DHP | No | - |
| USGS 3DEP | No | - |
| USDA NASS | Yes | https://quickstats.nass.usda.gov/api |
| NOAA CDO | Yes | https://www.ncdc.noaa.gov/cdo-web/token |

---

## Implementation Order Rationale

1. **Land Cover (NLCD)** first - Most straightforward API, establishes pattern
2. **Hydrology (NHD)** second - Similar pattern, builds on Phase 1
3. **Elevation (3DEP)** third - Completes physical geography trio
4. **Agriculture (NASS)** fourth - New API pattern (requires key)
5. **Climate (NOAA)** fifth - Also requires API key, builds on NASS pattern
6. **Transportation (DOT)** sixth - Local file loading, different pattern
7. **Schema Integration** last - Ties everything together

---

## Success Criteria

- [ ] All 7 new dimension tables created and populated
- [ ] All 7 new fact tables created and populated
- [ ] Unit tests for each loader (mocked API responses)
- [ ] Integration tests for each loader (real API calls, skipped in CI)
- [ ] Documentation in `ai-docs/epochs/epoch2/data-infrastructure.yaml` updated
- [ ] `ai-docs/state.yaml` updated with new capabilities
- [ ] Full schema can be loaded without errors

---

## Estimated New Schema Size

| Category | Dimensions | Facts | Rows (est.) |
|----------|------------|-------|-------------|
| Land Cover | 1 | 1 | ~45,000 (3,143 counties × 15 cover types) |
| Hydrology | 1 | 1 | ~15,000 (3,143 counties × ~5 feature types) |
| Terrain | 0 | 1 | ~3,143 (one per county) |
| Agriculture | 2 | 1 | ~500,000 (varies by commodity/year) |
| Climate | 1 | 1 | ~37,716 (3,143 counties × 12 months) |
| Transportation | 2 | 2 | ~25,000 (roads + nodes) |
| **Total** | **7** | **7** | **~625,000** |

This approximately doubles the current schema's fact table count and adds significant geographic context for the simulation.
