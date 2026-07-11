---
date: "2026-01-05T16:30:00-08:00"
researcher: Claude
git_commit: c72ef65
branch: dev
repository: babylon
topic: "DimGeographicHierarchy Applications Across Data Sources"
tags: [research, codebase, geographic-hierarchy, disaggregation, data-loaders, circulatory-system]
status: complete
last_updated: "2026-01-05"
last_updated_by: Claude
revision: 1
---

# Research: DimGeographicHierarchy Applications

**Date**: 2026-01-05T16:30:00-08:00
**Researcher**: Claude
**Git Commit**: c72ef65
**Branch**: dev
**Repository**: babylon

## Research Question

Which data sources in `src/babylon/data/` or planned future loaders could benefit from the state-to-county disaggregation infrastructure provided by `DimGeographicHierarchy`?

## Summary

The `DimGeographicHierarchy` table provides allocation weights (population_weight, employment_weight) for distributing state-level data to county-level representation. After analyzing all existing loaders and planned future loaders, I found:

**Current Primary Use Case**:
- **Census CFS (Commodity Flow Survey)**: Just implemented - uses geographic hierarchy to disaggregate state-level commodity flows to county-level.

**Potential Future Use Cases**:
- **FAF (Freight Analysis Framework)**: If zone-level data needs county distribution.

**Not Applicable**:
- Most loaders either already provide county-level data or provide data at levels where state-to-county disaggregation isn't meaningful.

## Detailed Findings

### 1. Existing Loader Inventory

| Loader | Geographic Level | Needs Disaggregation? | Rationale |
|--------|-----------------|----------------------|-----------|
| `census/loader_3nf.py` | County | No | Census ACS provides county-level data directly |
| `qcew/loader_3nf.py` | County, State, MSA | No | QCEW provides all three levels directly |
| `energy/loader_3nf.py` | National | No | National-level energy data not meaningful at county level |
| `trade/loader_3nf.py` | Country | No | International trade data, not US sub-national |
| `materials/loader_3nf.py` | National/Global | No | USGS commodity data at national level |
| `fred/loader_3nf.py` | National/State | No | FRED provides both levels; state-to-county not meaningful for most series |
| `mirta/loader.py` | Point → County | No | Already aggregates military installations to county level |
| `fcc/loader.py` | County | No | FCC BDC provides county-level broadband data |
| `cfs/loader.py` | State → County | **Yes** | Uses DimGeographicHierarchy for disaggregation |
| `geography/loader.py` | N/A | N/A | Creates the hierarchy itself |

### 2. Analysis of Key Plans

#### Census Loader Enhancement Plan (`thoughts/plans/2025-01-05_census-loader-enhancement.md`)

**Focus**: Multi-year historical data, race/ethnicity disaggregation, metro area support.

**Geographic Direction**: The Census plan involves **AGGREGATION** (county → metro area), not **DISAGGREGATION**:
- `BridgeCountyMetro` maps counties TO metro areas
- Census ACS already provides county-level data directly
- No need for state-to-county distribution

**Conclusion**: Census loader does NOT need DimGeographicHierarchy.

#### QCEW API Migration Plan (`thoughts/shared/plans/2026-01-05-qcew-api-migration.md`)

**Focus**: Hybrid API + file-based loading, multi-geographic support (County, State, MSA).

**Geographic Levels**:
- County (agglvl_code 70-78) → `FactQcewAnnual`
- State (agglvl_code 20-28) → `FactQcewStateAnnual`
- MSA/Micro/CSA (agglvl_code 30-58) → `FactQcewMetroAnnual`

**Key Quote from Plan**:
> "API provides rolling 5 years... State-level and County-level data both available"

**Conclusion**: QCEW provides county-level data directly from the API. No disaggregation needed.

#### DOT Transportation Integration Research (`thoughts/shared/research/2026-01-05-dot-transportation-integration.md`)

**Focus**: Transportation infrastructure and circulatory system data integration.

**FAF (Freight Analysis Framework)**:
> "132 FAF zones × 42 commodities... County-level experimental data available at https://www.bts.gov/faf/county"

**Insight**: FAF zones are multi-county aggregates. If loading zone-level FAF data and wanting county distribution, DimGeographicHierarchy weights could help. However, county-level experimental data now exists, reducing this need.

**LODES (Commuter Flows)**:
> "~3M census blocks... Block-level data must be aggregated to county FIPS"

**Direction**: LODES goes the opposite direction - it needs AGGREGATION from census blocks UP to county level, not disaggregation DOWN.

### 3. When DimGeographicHierarchy Is Useful

The geographic hierarchy is useful when:

1. **Source data is at state level, target schema is at county level**
2. **No county-level source exists** (or API doesn't provide it)
3. **Proportional distribution is meaningful** (e.g., commodity flows, employment, population-based metrics)

Current cases where this applies:

| Source | Source Level | Target Level | Weight Used | Implemented? |
|--------|--------------|--------------|-------------|--------------|
| Census CFS | State | County | employment (origin), population (destination) | **Yes** (just completed) |
| FAF (if needed) | FAF Zone | County | population_weight or employment_weight | No (experimental county data exists) |

### 4. Future Considerations

#### FAF Zone-to-County Disaggregation

If the FAF zone-level data is more complete than experimental county data, a `FAFLoader` could use DimGeographicHierarchy:

```python
# FAF zones cover multiple counties
# Disaggregate using employment weight for production/shipping
# Disaggregate using population weight for consumption/receiving

def disaggregate_faf_to_county(
    faf_flow: FAFZoneFlow,
    hierarchy: dict[str, DimGeographicHierarchy],
) -> list[FactCommodityFlow]:
    """Distribute FAF zone flow to constituent counties."""
    origin_counties = get_counties_in_faf_zone(faf_flow.origin_zone)
    dest_counties = get_counties_in_faf_zone(faf_flow.dest_zone)

    # Similar to CFS disaggregation pattern
    ...
```

#### Metro-Area to County Disaggregation

Some future data sources might provide MSA-level data. The `BridgeCountyMetro` table already maps counties to metros. Combined with DimGeographicHierarchy weights, this could enable:

```
MSA aggregate → constituent counties (using weights)
```

However, this is speculative - no current data sources require this.

### 5. Relationship to Other Geographic Infrastructure

| Table | Purpose | Direction |
|-------|---------|-----------|
| `DimGeographicHierarchy` | State → County allocation weights | **Disaggregation** (down) |
| `BridgeCountyMetro` | County → Metro Area mapping | **Aggregation** (up) |
| `DimCounty` | County dimension (5-digit FIPS) | Reference |
| `DimState` | State dimension (2-digit FIPS) | Reference |
| `DimMetroArea` | MSA/Micropolitan/CSA dimension | Reference |

### 6. Recommendations

1. **Current Implementation Complete**: The CFS loader successfully uses DimGeographicHierarchy for state-to-county disaggregation.

2. **No Other Immediate Use Cases**: Existing loaders don't require this pattern because:
   - Census, QCEW, FCC provide county-level data
   - FRED, Energy, Materials, Trade operate at national/international levels
   - MIRTA aggregates points to counties

3. **Future FAF Integration**: If a FAFLoader is implemented, consider:
   - First check if county-level FAF data is sufficient
   - If not, use DimGeographicHierarchy for zone-to-county distribution
   - Weight selection: employment_weight for production origins, population_weight for consumption destinations

4. **Maintain Hierarchy Accuracy**: The hierarchy weights are derived from Census employment and QCEW employment data. Keep weights current when source data updates.

## Code References

- `src/babylon/data/geography/loader.py` - Creates DimGeographicHierarchy
- `src/babylon/data/cfs/loader.py` - Uses DimGeographicHierarchy for disaggregation
- `src/babylon/data/normalize/schema.py:DimGeographicHierarchy` - Schema definition
- `thoughts/shared/plans/2026-01-05-circulatory-api-loaders.md` - Implementation plan

## Conclusion

The DimGeographicHierarchy infrastructure is well-suited for its current purpose (Census CFS state-to-county disaggregation). Other data sources don't currently require this pattern because they either:
- Already provide county-level data
- Operate at levels where county disaggregation isn't meaningful
- Aggregate UP to higher geographic levels rather than disaggregating DOWN

Future use cases may emerge with FAF or other zone-based datasets, but no immediate action is needed beyond the completed CFS implementation.
