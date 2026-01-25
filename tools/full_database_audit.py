#!/usr/bin/env python3
"""Run comprehensive database audit queries and export to CSV."""

from __future__ import annotations

import csv
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from babylon.data.reference.database import get_normalized_session_factory

# Output directory
OUTPUT_DIR = Path("data/diagnostics")
TODAY = datetime.now().strftime("%Y%m%d")

QUERIES = {
    # =============================================================================
    # SECTION 1: COMPLETE TABLE INVENTORY
    # =============================================================================
    "01_all_tables_inventory": """
SELECT * FROM (
SELECT 'dim_state' as table_name, 'dimension' as table_type, (SELECT COUNT(*) FROM dim_state) as row_count
UNION ALL SELECT 'dim_county', 'dimension', (SELECT COUNT(*) FROM dim_county)
UNION ALL SELECT 'dim_metro_area', 'dimension', (SELECT COUNT(*) FROM dim_metro_area)
UNION ALL SELECT 'dim_geographic_hierarchy', 'dimension', (SELECT COUNT(*) FROM dim_geographic_hierarchy)
UNION ALL SELECT 'dim_cfs_area', 'dimension', (SELECT COUNT(*) FROM dim_cfs_area)
UNION ALL SELECT 'dim_country', 'dimension', (SELECT COUNT(*) FROM dim_country)
UNION ALL SELECT 'dim_import_source', 'dimension', (SELECT COUNT(*) FROM dim_import_source)
UNION ALL SELECT 'dim_industry', 'dimension', (SELECT COUNT(*) FROM dim_industry)
UNION ALL SELECT 'dim_sector', 'dimension', (SELECT COUNT(*) FROM dim_sector)
UNION ALL SELECT 'dim_ownership', 'dimension', (SELECT COUNT(*) FROM dim_ownership)
UNION ALL SELECT 'dim_income_bracket', 'dimension', (SELECT COUNT(*) FROM dim_income_bracket)
UNION ALL SELECT 'dim_employment_status', 'dimension', (SELECT COUNT(*) FROM dim_employment_status)
UNION ALL SELECT 'dim_worker_class', 'dimension', (SELECT COUNT(*) FROM dim_worker_class)
UNION ALL SELECT 'dim_occupation', 'dimension', (SELECT COUNT(*) FROM dim_occupation)
UNION ALL SELECT 'dim_education_level', 'dimension', (SELECT COUNT(*) FROM dim_education_level)
UNION ALL SELECT 'dim_housing_tenure', 'dimension', (SELECT COUNT(*) FROM dim_housing_tenure)
UNION ALL SELECT 'dim_rent_burden', 'dimension', (SELECT COUNT(*) FROM dim_rent_burden)
UNION ALL SELECT 'dim_commute_mode', 'dimension', (SELECT COUNT(*) FROM dim_commute_mode)
UNION ALL SELECT 'dim_poverty_category', 'dimension', (SELECT COUNT(*) FROM dim_poverty_category)
UNION ALL SELECT 'dim_energy_table', 'dimension', (SELECT COUNT(*) FROM dim_energy_table)
UNION ALL SELECT 'dim_energy_series', 'dimension', (SELECT COUNT(*) FROM dim_energy_series)
UNION ALL SELECT 'dim_wealth_class', 'dimension', (SELECT COUNT(*) FROM dim_wealth_class)
UNION ALL SELECT 'dim_asset_category', 'dimension', (SELECT COUNT(*) FROM dim_asset_category)
UNION ALL SELECT 'dim_fred_series', 'dimension', (SELECT COUNT(*) FROM dim_fred_series)
UNION ALL SELECT 'dim_commodity', 'dimension', (SELECT COUNT(*) FROM dim_commodity)
UNION ALL SELECT 'dim_commodity_metric', 'dimension', (SELECT COUNT(*) FROM dim_commodity_metric)
UNION ALL SELECT 'dim_sctg_commodity', 'dimension', (SELECT COUNT(*) FROM dim_sctg_commodity)
UNION ALL SELECT 'dim_time', 'dimension', (SELECT COUNT(*) FROM dim_time)
UNION ALL SELECT 'dim_gender', 'dimension', (SELECT COUNT(*) FROM dim_gender)
UNION ALL SELECT 'dim_data_source', 'dimension', (SELECT COUNT(*) FROM dim_data_source)
UNION ALL SELECT 'dim_race', 'dimension', (SELECT COUNT(*) FROM dim_race)
UNION ALL SELECT 'dim_coercive_type', 'dimension', (SELECT COUNT(*) FROM dim_coercive_type)
UNION ALL SELECT 'bridge_county_metro', 'bridge', (SELECT COUNT(*) FROM bridge_county_metro)
UNION ALL SELECT 'bridge_cfs_county', 'bridge', (SELECT COUNT(*) FROM bridge_cfs_county)
UNION ALL SELECT 'fact_census_income', 'fact', (SELECT COUNT(*) FROM fact_census_income)
UNION ALL SELECT 'fact_census_median_income', 'fact', (SELECT COUNT(*) FROM fact_census_median_income)
UNION ALL SELECT 'fact_census_employment', 'fact', (SELECT COUNT(*) FROM fact_census_employment)
UNION ALL SELECT 'fact_census_worker_class', 'fact', (SELECT COUNT(*) FROM fact_census_worker_class)
UNION ALL SELECT 'fact_census_occupation', 'fact', (SELECT COUNT(*) FROM fact_census_occupation)
UNION ALL SELECT 'fact_census_hours', 'fact', (SELECT COUNT(*) FROM fact_census_hours)
UNION ALL SELECT 'fact_census_housing', 'fact', (SELECT COUNT(*) FROM fact_census_housing)
UNION ALL SELECT 'fact_census_rent', 'fact', (SELECT COUNT(*) FROM fact_census_rent)
UNION ALL SELECT 'fact_census_rent_burden', 'fact', (SELECT COUNT(*) FROM fact_census_rent_burden)
UNION ALL SELECT 'fact_census_education', 'fact', (SELECT COUNT(*) FROM fact_census_education)
UNION ALL SELECT 'fact_census_gini', 'fact', (SELECT COUNT(*) FROM fact_census_gini)
UNION ALL SELECT 'fact_census_commute', 'fact', (SELECT COUNT(*) FROM fact_census_commute)
UNION ALL SELECT 'fact_census_poverty', 'fact', (SELECT COUNT(*) FROM fact_census_poverty)
UNION ALL SELECT 'fact_census_income_sources', 'fact', (SELECT COUNT(*) FROM fact_census_income_sources)
UNION ALL SELECT 'fact_qcew_annual', 'fact', (SELECT COUNT(*) FROM fact_qcew_annual)
UNION ALL SELECT 'fact_qcew_state_annual', 'fact', (SELECT COUNT(*) FROM fact_qcew_state_annual)
UNION ALL SELECT 'fact_qcew_metro_annual', 'fact', (SELECT COUNT(*) FROM fact_qcew_metro_annual)
UNION ALL SELECT 'fact_productivity_annual', 'fact', (SELECT COUNT(*) FROM fact_productivity_annual)
UNION ALL SELECT 'fact_trade_monthly', 'fact', (SELECT COUNT(*) FROM fact_trade_monthly)
UNION ALL SELECT 'fact_energy_annual', 'fact', (SELECT COUNT(*) FROM fact_energy_annual)
UNION ALL SELECT 'fact_fred_national', 'fact', (SELECT COUNT(*) FROM fact_fred_national)
UNION ALL SELECT 'fact_fred_wealth_levels', 'fact', (SELECT COUNT(*) FROM fact_fred_wealth_levels)
UNION ALL SELECT 'fact_fred_wealth_shares', 'fact', (SELECT COUNT(*) FROM fact_fred_wealth_shares)
UNION ALL SELECT 'fact_fred_industry_unemployment', 'fact', (SELECT COUNT(*) FROM fact_fred_industry_unemployment)
UNION ALL SELECT 'fact_fred_state_unemployment', 'fact', (SELECT COUNT(*) FROM fact_fred_state_unemployment)
UNION ALL SELECT 'fact_commodity_observation', 'fact', (SELECT COUNT(*) FROM fact_commodity_observation)
UNION ALL SELECT 'fact_state_minerals', 'fact', (SELECT COUNT(*) FROM fact_state_minerals)
UNION ALL SELECT 'fact_mineral_production', 'fact', (SELECT COUNT(*) FROM fact_mineral_production)
UNION ALL SELECT 'fact_mineral_employment', 'fact', (SELECT COUNT(*) FROM fact_mineral_employment)
UNION ALL SELECT 'fact_coercive_infrastructure', 'fact', (SELECT COUNT(*) FROM fact_coercive_infrastructure)
UNION ALL SELECT 'fact_broadband_coverage', 'fact', (SELECT COUNT(*) FROM fact_broadband_coverage)
UNION ALL SELECT 'fact_commodity_flow', 'fact', (SELECT COUNT(*) FROM fact_commodity_flow)
) ORDER BY table_type, table_name
""",
    # =============================================================================
    # SECTION 2: NEW TENSOR TABLES
    # =============================================================================
    "02_tensor_tables_check": """
SELECT 'dim_bea_industry' as table_name, (SELECT COUNT(*) FROM dim_bea_industry) as row_count
UNION ALL SELECT 'fact_bea_national_industry', (SELECT COUNT(*) FROM fact_bea_national_industry)
UNION ALL SELECT 'bridge_naics_bea', (SELECT COUNT(*) FROM bridge_naics_bea)
UNION ALL SELECT 'dim_county_geometry', (SELECT COUNT(*) FROM dim_county_geometry)
UNION ALL SELECT 'bridge_county_h3', (SELECT COUNT(*) FROM bridge_county_h3)
UNION ALL SELECT 'fact_bea_county_gdp', (SELECT COUNT(*) FROM fact_bea_county_gdp)
""",
    # =============================================================================
    # SECTION 3: GEOGRAPHIC COVERAGE
    # =============================================================================
    "03_geographic_coverage": """
SELECT 'states' as entity, (SELECT COUNT(*) FROM dim_state) as count
UNION ALL SELECT 'counties', (SELECT COUNT(*) FROM dim_county)
UNION ALL SELECT 'metro_areas', (SELECT COUNT(*) FROM dim_metro_area)
UNION ALL SELECT 'countries', (SELECT COUNT(*) FROM dim_country)
UNION ALL SELECT 'cfs_areas', (SELECT COUNT(*) FROM dim_cfs_area)
""",
    "04_county_state_distribution": """
SELECT
    s.state_abbrev,
    s.state_name,
    COUNT(c.county_id) as county_count
FROM dim_state s
LEFT JOIN dim_county c ON s.state_id = c.state_id
GROUP BY s.state_abbrev, s.state_name
ORDER BY county_count DESC
""",
    # =============================================================================
    # SECTION 4: TEMPORAL COVERAGE
    # =============================================================================
    "05_time_dimension_coverage": """
SELECT
    MIN(year) as min_year,
    MAX(year) as max_year,
    COUNT(*) as total_time_records,
    SUM(CASE WHEN is_annual THEN 1 ELSE 0 END) as annual_records,
    SUM(CASE WHEN month IS NOT NULL THEN 1 ELSE 0 END) as monthly_records,
    SUM(CASE WHEN quarter IS NOT NULL AND month IS NULL THEN 1 ELSE 0 END) as quarterly_records
FROM dim_time
""",
    "06_fact_table_year_coverage": """
SELECT 'fact_qcew_annual' as fact_table, MIN(t.year) as min_year, MAX(t.year) as max_year, COUNT(DISTINCT t.year) as year_count
FROM fact_qcew_annual f JOIN dim_time t ON f.time_id = t.time_id
UNION ALL
SELECT 'fact_census_income', MIN(t.year), MAX(t.year), COUNT(DISTINCT t.year)
FROM fact_census_income f JOIN dim_time t ON f.time_id = t.time_id
UNION ALL
SELECT 'fact_fred_national', MIN(t.year), MAX(t.year), COUNT(DISTINCT t.year)
FROM fact_fred_national f JOIN dim_time t ON f.time_id = t.time_id
UNION ALL
SELECT 'fact_trade_monthly', MIN(t.year), MAX(t.year), COUNT(DISTINCT t.year)
FROM fact_trade_monthly f JOIN dim_time t ON f.time_id = t.time_id
UNION ALL
SELECT 'fact_commodity_flow', MIN(year), MAX(year), COUNT(DISTINCT year)
FROM fact_commodity_flow
""",
    # =============================================================================
    # SECTION 5: INDUSTRY & CLASSIFICATION COVERAGE
    # =============================================================================
    "07_industry_by_level": """
SELECT
    naics_level,
    COUNT(*) as industry_count,
    SUM(CASE WHEN has_qcew_data THEN 1 ELSE 0 END) as with_qcew,
    SUM(CASE WHEN has_productivity_data THEN 1 ELSE 0 END) as with_productivity,
    SUM(CASE WHEN has_fred_data THEN 1 ELSE 0 END) as with_fred
FROM dim_industry
GROUP BY naics_level
ORDER BY naics_level
""",
    "08_class_composition_coverage": """
SELECT
    class_composition,
    COUNT(*) as industry_count
FROM dim_industry
WHERE class_composition IS NOT NULL
GROUP BY class_composition
ORDER BY industry_count DESC
""",
    "09_sector_summary": """
SELECT
    sector_code,
    sector_name,
    class_composition
FROM dim_sector
ORDER BY sector_code
""",
    # =============================================================================
    # SECTION 6: QCEW DATA QUALITY
    # =============================================================================
    "10_qcew_county_coverage_by_year": """
SELECT
    t.year,
    COUNT(DISTINCT q.county_id) as counties_with_data,
    COUNT(*) as total_records,
    SUM(q.employment) as total_employment,
    ROUND(SUM(q.total_wages_usd) / 1e9, 2) as total_wages_billions
FROM fact_qcew_annual q
JOIN dim_time t ON q.time_id = t.time_id
GROUP BY t.year
ORDER BY t.year
""",
    "11_qcew_by_class_composition": """
SELECT
    sec.class_composition,
    t.year,
    SUM(q.employment) as employment,
    ROUND(SUM(q.total_wages_usd) / 1e9, 2) as wages_billions,
    COUNT(DISTINCT q.county_id) as counties
FROM fact_qcew_annual q
JOIN dim_industry i ON q.industry_id = i.industry_id
JOIN dim_sector sec ON i.sector_code = sec.sector_code
JOIN dim_time t ON q.time_id = t.time_id
WHERE sec.class_composition IS NOT NULL
GROUP BY sec.class_composition, t.year
ORDER BY t.year, employment DESC
""",
    # =============================================================================
    # SECTION 7: CENSUS DATA QUALITY
    # =============================================================================
    "12_census_coverage_by_year_race": """
SELECT
    t.year,
    r.race_label,
    COUNT(DISTINCT f.county_id) as counties
FROM fact_census_income f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_race r ON f.race_id = r.race_id
GROUP BY t.year, r.race_label
ORDER BY t.year, r.race_label
""",
    "13_census_gini_sample": """
SELECT
    c.county_name,
    s.state_abbrev,
    t.year,
    g.gini_coefficient
FROM fact_census_gini g
JOIN dim_county c ON g.county_id = c.county_id
JOIN dim_state s ON c.state_id = s.state_id
JOIN dim_time t ON g.time_id = t.time_id
WHERE t.year = (SELECT MAX(year) FROM dim_time WHERE is_annual = TRUE)
ORDER BY g.gini_coefficient DESC
LIMIT 50
""",
    # =============================================================================
    # SECTION 8: FRED DATA QUALITY
    # =============================================================================
    "14_fred_series_inventory": """
SELECT
    fs.series_code,
    fs.title as series_name,
    (SELECT COUNT(*) FROM fact_fred_national fn WHERE fn.series_id = fs.series_id) as observation_count,
    (SELECT MIN(t.year) FROM fact_fred_national fn JOIN dim_time t ON fn.time_id = t.time_id WHERE fn.series_id = fs.series_id) as min_year,
    (SELECT MAX(t.year) FROM fact_fred_national fn JOIN dim_time t ON fn.time_id = t.time_id WHERE fn.series_id = fs.series_id) as max_year
FROM dim_fred_series fs
ORDER BY fs.series_code
""",
    "15_fred_wealth_class_summary": """
SELECT
    wc.class_label,
    wc.percentile_min,
    wc.percentile_max,
    COUNT(DISTINCT fl.time_id) as observation_count,
    ROUND(AVG(fl.value_millions), 2) as avg_wealth_millions
FROM fact_fred_wealth_levels fl
JOIN dim_wealth_class wc ON fl.wealth_class_id = wc.wealth_class_id
GROUP BY wc.class_label, wc.percentile_min, wc.percentile_max
ORDER BY wc.percentile_min
""",
    # =============================================================================
    # SECTION 9: TRADE & COMMODITIES
    # =============================================================================
    "16_trade_by_world_system_tier": """
SELECT
    c.world_system_tier,
    t.year,
    ROUND(SUM(f.imports_usd_millions), 2) as total_imports_millions,
    ROUND(SUM(f.exports_usd_millions), 2) as total_exports_millions,
    ROUND(SUM(f.imports_usd_millions) - SUM(f.exports_usd_millions), 2) as trade_deficit_millions
FROM fact_trade_monthly f
JOIN dim_country c ON f.country_id = c.country_id
JOIN dim_time t ON f.time_id = t.time_id
WHERE c.world_system_tier IS NOT NULL
GROUP BY c.world_system_tier, t.year
ORDER BY t.year, c.world_system_tier
""",
    "17_commodity_flow_summary": """
SELECT
    sc.sctg_code,
    sc.sctg_name,
    sc.category,
    sc.strategic_value,
    COUNT(*) as flow_records,
    ROUND(SUM(cf.value_millions), 2) as total_value_millions
FROM fact_commodity_flow cf
JOIN dim_sctg_commodity sc ON cf.sctg_id = sc.sctg_id
GROUP BY sc.sctg_code, sc.sctg_name, sc.category, sc.strategic_value
ORDER BY total_value_millions DESC
""",
    # =============================================================================
    # SECTION 10: COERCIVE INFRASTRUCTURE
    # =============================================================================
    "18_coercive_infrastructure_summary": """
SELECT
    ct.type_name,
    ct.category,
    COUNT(DISTINCT ci.county_id) as counties_with_facilities,
    SUM(ci.facility_count) as total_facilities,
    SUM(ci.total_capacity) as total_capacity
FROM fact_coercive_infrastructure ci
JOIN dim_coercive_type ct ON ci.coercive_type_id = ct.coercive_type_id
GROUP BY ct.type_name, ct.category
ORDER BY total_facilities DESC
""",
    # =============================================================================
    # SECTION 11: BEA TENSOR DATA
    # =============================================================================
    "19_bea_national_accounting_check": """
SELECT
    bi.bea_code,
    bi.industry_name,
    t.year,
    n.gross_output_millions,
    n.intermediate_inputs_millions,
    n.value_added_millions,
    (n.intermediate_inputs_millions + n.value_added_millions) as computed_go,
    ABS(n.gross_output_millions - (n.intermediate_inputs_millions + n.value_added_millions)) as discrepancy,
    ROUND(100.0 * ABS(n.gross_output_millions - (n.intermediate_inputs_millions + n.value_added_millions)) / NULLIF(n.gross_output_millions, 0), 4) as discrepancy_pct
FROM fact_bea_national_industry n
JOIN dim_bea_industry bi ON n.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON n.time_id = t.time_id
ORDER BY t.year, bi.bea_code
""",
    "20_bea_county_gdp_coverage": """
SELECT
    t.year,
    COUNT(DISTINCT g.county_id) as counties_with_data,
    COUNT(DISTINCT g.bea_industry_id) as industries,
    COUNT(*) as total_records,
    ROUND(SUM(g.gdp_millions), 2) as total_gdp_millions
FROM fact_bea_county_gdp g
JOIN dim_time t ON g.time_id = t.time_id
GROUP BY t.year
ORDER BY t.year
""",
    "21_naics_bea_bridge_coverage": """
SELECT
    i.naics_level,
    COUNT(DISTINCT i.industry_id) as total_industries,
    COUNT(DISTINCT b.industry_id) as mapped_industries,
    COUNT(DISTINCT i.industry_id) - COUNT(DISTINCT b.industry_id) as unmapped,
    ROUND(100.0 * COUNT(DISTINCT b.industry_id) / NULLIF(COUNT(DISTINCT i.industry_id), 0), 2) as coverage_pct
FROM dim_industry i
LEFT JOIN bridge_naics_bea b ON i.industry_id = b.industry_id
GROUP BY i.naics_level
ORDER BY i.naics_level
""",
    # =============================================================================
    # SECTION 12: SPATIAL INFRASTRUCTURE
    # =============================================================================
    "22_county_geometry_coverage": """
SELECT
    COUNT(DISTINCT c.county_id) as total_counties,
    COUNT(DISTINCT g.county_id) as counties_with_geometry,
    COUNT(DISTINCT c.county_id) - COUNT(DISTINCT g.county_id) as missing_geometry,
    ROUND(100.0 * COUNT(DISTINCT g.county_id) / NULLIF(COUNT(DISTINCT c.county_id), 0), 2) as coverage_pct
FROM dim_county c
LEFT JOIN dim_county_geometry g ON c.county_id = g.county_id
""",
    "23_h3_grid_stats": """
SELECT
    resolution,
    COUNT(DISTINCT h3_index) as hex_count,
    COUNT(DISTINCT county_id) as counties_covered,
    ROUND(AVG(coverage_pct), 2) as avg_coverage_pct,
    ROUND(MIN(coverage_pct), 2) as min_coverage_pct,
    ROUND(MAX(coverage_pct), 2) as max_coverage_pct
FROM bridge_county_h3
GROUP BY resolution
""",
    # =============================================================================
    # SECTION 13: DEFLATOR CHECK
    # =============================================================================
    "24_deflator_series": """
SELECT
    fs.series_code,
    fs.title as series_name,
    MIN(t.year) as min_year,
    MAX(t.year) as max_year,
    COUNT(*) as observation_count
FROM fact_fred_national fn
JOIN dim_fred_series fs ON fn.series_id = fs.series_id
JOIN dim_time t ON fn.time_id = t.time_id
WHERE fs.series_code IN ('GDPDEF', 'CPIAUCSL', 'PCEPI')
GROUP BY fs.series_code, fs.title
""",
    # =============================================================================
    # SECTION 14: DETROIT TEST CASE
    # =============================================================================
    "25_detroit_counties_qcew": """
SELECT
    c.county_fips as fips,
    c.county_name,
    t.year,
    sec.class_composition,
    SUM(q.employment) as employment,
    ROUND(SUM(q.total_wages_usd) / 1e6, 2) as wages_millions
FROM fact_qcew_annual q
JOIN dim_county c ON q.county_id = c.county_id
JOIN dim_industry i ON q.industry_id = i.industry_id
JOIN dim_sector sec ON i.sector_code = sec.sector_code
JOIN dim_time t ON q.time_id = t.time_id
WHERE c.county_fips IN ('26163', '26125')
GROUP BY c.county_fips, c.county_name, t.year, sec.class_composition
ORDER BY c.county_fips, t.year, sec.class_composition
""",
    "26_detroit_bea_gdp": """
SELECT
    c.county_fips as fips,
    c.county_name,
    bi.bea_code,
    bi.industry_name,
    t.year,
    g.gdp_millions
FROM fact_bea_county_gdp g
JOIN dim_county c ON g.county_id = c.county_id
JOIN dim_bea_industry bi ON g.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON g.time_id = t.time_id
WHERE c.county_fips IN ('26163', '26125')
ORDER BY c.county_fips, t.year, bi.bea_code
""",
    "27_detroit_tensor_derivation": """
WITH national_ratios AS (
    SELECT
        n.bea_industry_id,
        n.time_id,
        n.intermediate_inputs_millions / NULLIF(n.gross_output_millions, 0) as c_ratio,
        n.value_added_millions / NULLIF(n.gross_output_millions, 0) as va_ratio
    FROM fact_bea_national_industry n
)
SELECT
    c.county_fips as territory,
    c.county_name,
    bi.bea_code,
    t.year,
    ROUND((g.gdp_millions / NULLIF(nr.va_ratio, 0)) * nr.c_ratio, 2) as c_millions,
    ROUND(g.gdp_millions, 2) as va_millions,
    ROUND(nr.c_ratio, 4) as c_ratio_used,
    ROUND(nr.va_ratio, 4) as va_ratio_used
FROM fact_bea_county_gdp g
JOIN national_ratios nr ON g.bea_industry_id = nr.bea_industry_id AND g.time_id = nr.time_id
JOIN dim_county c ON g.county_id = c.county_id
JOIN dim_bea_industry bi ON g.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON g.time_id = t.time_id
WHERE c.county_fips IN ('26163', '26125')
ORDER BY c.county_fips, t.year, bi.bea_code
""",
    # =============================================================================
    # SECTION 15: DATA SOURCE INVENTORY
    # =============================================================================
    "28_data_sources": """
SELECT
    source_code,
    source_name,
    source_agency,
    coverage_start_year,
    coverage_end_year,
    source_url
FROM dim_data_source
ORDER BY source_code
""",
}


def run_audit() -> None:
    """Run all audit queries and export to CSVs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session_factory = get_normalized_session_factory()
    results: dict[str, str] = {}
    csv_files: list[Path] = []
    errors: list[str] = []

    with session_factory() as session:
        for query_name, query_sql in QUERIES.items():
            csv_path = OUTPUT_DIR / f"{query_name}.csv"
            print(f"Running {query_name}...")

            try:
                result = session.execute(text(query_sql))
                rows = result.fetchall()
                columns = list(result.keys())

                # Write CSV
                with open(csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(rows)

                csv_files.append(csv_path)
                results[query_name] = f"OK ({len(rows)} rows)"
                print(f"  -> {len(rows)} rows")

            except Exception as e:
                error_msg = str(e).split("\n")[0][:100]
                results[query_name] = f"FAILED: {error_msg}"
                errors.append(f"{query_name}: {error_msg}")
                print(f"  -> FAILED: {error_msg}")

    # Create zip file
    zip_path = OUTPUT_DIR / f"full-database-audit-{TODAY}.zip"
    print(f"\nCreating {zip_path}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for csv_path in csv_files:
            zf.write(csv_path, csv_path.name)

    # Print summary
    print("\n" + "=" * 70)
    print("DATABASE AUDIT RESULTS SUMMARY")
    print("=" * 70)

    passed = sum(1 for s in results.values() if s.startswith("OK"))
    failed = sum(1 for s in results.values() if s.startswith("FAILED"))

    print(f"\nTotal queries: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if errors:
        print(f"\n--- ERRORS ({len(errors)}) ---")
        for err in errors:
            print(f"  {err}")

    print("\n--- QUERY RESULTS ---")
    for query_name, status in results.items():
        status_icon = "✓" if status.startswith("OK") else "✗"
        print(f"{status_icon} {query_name}: {status}")

    print(f"\nExported to: {zip_path}")
    print(f"Zip contains: {len(csv_files)} CSV files")
    print(f"Zip size: {zip_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    run_audit()
