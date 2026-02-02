# Research: Throughput Position and Domestic Value Geography

**Feature**: 014-throughput-position
**Date**: 2026-02-02
**Phase**: 0 (Research)

## Executive Summary

This research document captures findings on data source availability and format specifications needed to implement throughput position (π) and domestic value geography analysis. Both required data sources (BEA county GDP and QCEW county-by-NAICS employment) are available via public APIs with free access.

## Data Source Research

### 1. BEA CAGDP1 (County Annual GDP)

**Source**: Bureau of Economic Analysis (BEA)
**Official URL**: https://apps.bea.gov/api/data/
**Documentation**: https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf

#### Access Details

- **API Key Required**: YES (free registration at https://apps.bea.gov/api/signup/)
- **Format**: JSON (primary), XML
- **Rate Limits**: Not explicitly documented, standard API best practices apply
- **Cost**: Free

#### Example API Call

```
https://apps.bea.gov/api/data/?UserID=YOUR_API_KEY&method=GetData&datasetname=Regional&TableName=CAGDP1&LineCode=1&GeoFIPS=COUNTY&Year=2022&ResultFormat=JSON
```

#### Data Availability

- **Years Available**: 2001-2023 (complete time series)
- **Geographic Coverage**: All US counties (~3,143)
- **Industry Detail**: 63 industries at 2-digit NAICS via different LineCode values
- **Latest Release**: December 4, 2024 (2023 data)
- **Next Release**: December 3, 2025 (2024 data)

#### Key Fields

| Field | Description | Example |
|-------|-------------|---------|
| `GeoFIPS` | 5-character FIPS code | "26163" (Wayne County) |
| `GeoName` | Geographic area name | "Wayne County, MI" |
| `LineCode` | Statistic/industry code | 1 (All industry total) |
| `Unit` | Unit of measurement | "thousands of chained 2012 dollars" |
| Year columns | GDP values by year | 2001, 2002, ..., 2023 |

#### FIPS Code Notes

BEA uses custom FIPS codes for Virginia independent cities (e.g., combines Fairfax County 51059, Fairfax City 51600, and Falls Church 51610 into pseudo-code 51919). Need to handle these mappings in implementation.

#### Official Python Client

BEA provides official Python library: `beaapi` (https://github.com/us-bea/beaapi)

### 2. BLS QCEW (Quarterly Census of Employment and Wages)

**Source**: Bureau of Labor Statistics (BLS)
**Official URL**: https://www.bls.gov/cew/
**Documentation**: https://www.bls.gov/cew/additional-resources/open-data/

#### Access Details

- **API Key Required**: NO
- **Format**: CSV (direct file access via URL pattern)
- **Cost**: Free
- **Coverage**: ~95% of U.S. jobs

#### URL Pattern

```
https://data.bls.gov/cew/data/api/{YEAR}/{QUARTER}/area/{AREA_CODE}.csv
```

Examples:
- Wayne County Q1 2024: `https://data.bls.gov/cew/data/api/2024/1/area/26163.csv`
- Annual averages: `https://data.bls.gov/cew/data/api/2023/a/area/26163.csv`

#### Data Availability

- **Years Available**: 1990-present (NAICS codes)
- **Most Recent**: Q2 2025 (as of February 2026)
- **Publication Lag**: 5-6 months after quarter end
- **Quarterly and Annual**: Both available

#### Key Fields

| Field | Description | Type |
|-------|-------------|------|
| `area_fips` | 5-character FIPS code | String |
| `industry_code` | NAICS industry code (2-6 digits) | String |
| `agglvl_code` | Aggregation level code | String |
| `own_code` | Ownership code (5=Private) | String |
| `month1_emplvl` | Employment, 1st month of quarter | Integer |
| `month2_emplvl` | Employment, 2nd month of quarter | Integer |
| `month3_emplvl` | Employment, 3rd month of quarter | Integer |
| `avg_wkly_wage` | Average weekly wage | Float |
| `total_qtrly_wages` | Total quarterly wages | Float |

#### Filtering for County 2-Digit NAICS

```python
agglvl_code == '74'  # County, Sector (2-digit NAICS), by Ownership
own_code == '5'      # Private ownership
```

#### Data Suppression Warning

Approximately 60% of private-sector county-level data is suppressed for confidentiality protection. Small counties and concentrated industries will have gaps. Check `disclosure_code` field.

## NAICS Depth Mapping Validation

The spec defines NAICS-to-depth mapping based on supply chain position. This mapping is theoretically derived, not empirically calibrated:

| NAICS | Industry | Depth | Rationale |
|-------|----------|-------|-----------|
| 11 | Agriculture | 0 | Primary extraction |
| 21 | Mining | 0 | Primary extraction |
| 22 | Utilities | 2 | Infrastructure coordination |
| 23 | Construction | 2 | Secondary transformation |
| 31-33 | Manufacturing | 1.5 | Average of primary (1) and secondary (2) |
| 42 | Wholesale | 3 | Distribution coordination |
| 44-45 | Retail | 4 | Final realization point |
| 48-49 | Transportation | 3 | Logistics coordination |
| 51 | Information | 4 | Knowledge coordination |
| 52 | Finance | 5 | Highest coordination (money capital) |
| 53 | Real Estate | 5 | Highest coordination (fictitious capital) |
| 54 | Professional Services | 4 | Knowledge coordination |
| 55 | Management | 5 | Highest coordination (control) |
| 56 | Admin/Support | 3 | Service coordination |
| 61 | Education | 4 | Social reproduction |
| 62 | Healthcare | 4 | Social reproduction |
| 71 | Entertainment | 4 | Final realization |
| 72 | Accommodation/Food | 4 | Final realization |
| 81 | Other Services | 3 | Mixed coordination |
| 92 | Government | 4 | Social coordination |

**Theoretical Basis**: Depth values derive from position in supply chain funnel:
- **Depth 0**: Value creation at extraction points (mines, farms, wells)
- **Depth 1-2**: Transformation (refineries, factories)
- **Depth 3**: Logistics coordination (ports, warehouses)
- **Depth 4**: Service/realization (retail, healthcare, education)
- **Depth 5**: Financial coordination (banks, management, real estate)

## Integration with Feature 013

Feature 014 depends on Feature 013's `MELTCalculator` for national MELT (τ):

```python
from babylon.economics.melt import DefaultMELTCalculator

# Get national MELT
tau_national = melt_calculator.get_melt(2022)

# Compute throughput position
pi = tau_through / tau_national
```

The MELTCalculator is already implemented at:
- `src/babylon/economics/melt/melt_calculator.py`

## Detroit Metro Validation Data Points

For the Wayne County (26163) vs Oakland County (26125) validation case:

**Expected Findings** (to be validated with real data):

| Metric | Oakland (26125) | Wayne (26163) | Expected Relation |
|--------|-----------------|---------------|-------------------|
| π (throughput position) | Higher | Lower | Oakland > Wayne |
| D (supply chain depth) | Higher | Lower | Oakland > Wayne |
| Industry mix | Finance, Management | Manufacturing legacy | Oakland more coordination |
| LA share (from Feature 013) | Higher | Lower | Oakland > Wayne |

**Rationale**: Oakland County contains suburban corporate headquarters and financial services, representing coordination chokepoints with high π. Wayne County contains Detroit's manufacturing legacy, representing value creation with lower throughput accumulation.

## Data Quality Considerations

### BEA CAGDP1 Issues

1. **Virginia Independent Cities**: Custom FIPS codes require mapping
2. **Small County Suppression**: Some small counties may have suppressed GDP data
3. **Real vs Nominal GDP**: CAGDP1 uses "chained 2012 dollars" - may need nominal GDP for λ calculation

### QCEW Issues

1. **60% Suppression Rate**: Many county-sector combinations are suppressed
2. **Publication Lag**: 5-6 months means 2025 Q4 data unavailable until mid-2026
3. **Employment vs Wages**: Both needed for λ calculation

## Recommended Implementation Approach

### Phase 3 Implementation Order

1. **NAICS Depth Mapping** (FR-003): Frozen constant, no data dependency
2. **Types** (ThroughputMetrics, WageShareEstimate): Pure Pydantic models
3. **BEA County GDP Loader**: New data source protocol + implementation
4. **QCEW County NAICS Loader**: Extend existing QCEW patterns
5. **ThroughputCalculator**: Core π and τ_through computation
6. **SupplyChainAnalyzer**: Depth (D) computation
7. **Wage Share Proxy**: λ_proxy calculation

### MVP Approach

For MVP, consider:
1. Pre-downloaded CSV files rather than live API calls
2. Focus on Detroit metro (Wayne + Oakland) for validation
3. Annual data (simpler than quarterly aggregation)
4. 2022 as reference year (most stable recent data)

## Unresolved Questions

1. **Real vs Nominal GDP**: Should τ_through use real or nominal county GDP?
   - Spec uses GDP/L which typically assumes nominal
   - Feature 013 uses nominal GDP for national MELT
   - **Recommendation**: Use nominal for consistency

2. **Employment Count**: Should employment use headcount or FTE?
   - QCEW provides headcount
   - Feature 013 uses headcount × 2080 hours/year
   - **Recommendation**: Use headcount for consistency

3. **Government Employment**: Include or exclude NAICS 92?
   - Government has different wage dynamics
   - **Recommendation**: Include for comprehensive analysis, note in limitations

## References

- BEA API Documentation: https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf
- BEA County GDP Landing: https://www.bea.gov/data/gdp/gdp-county-metro-and-other-areas
- QCEW Open Data: https://www.bls.gov/cew/additional-resources/open-data/
- QCEW CSV Layouts: https://www.bls.gov/cew/about-data/downloadable-file-layouts/
- BEA Python Library: https://github.com/us-bea/beaapi
- QCEW Aggregation Codes: https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm
