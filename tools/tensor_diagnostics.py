#!/usr/bin/env python3
"""Run tensor readiness diagnostic queries and export to CSV."""

from __future__ import annotations

import csv
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from babylon.reference.database import get_normalized_session_factory

# Output directory
OUTPUT_DIR = Path("data/diagnostics")
TODAY = datetime.now().strftime("%Y%m%d")

QUERIES = {
    "01_table_counts": """
SELECT * FROM (
    SELECT 'dim_bea_industry' as table_name, (SELECT COUNT(*) FROM dim_bea_industry) as row_count
    UNION ALL SELECT 'fact_bea_national_industry', (SELECT COUNT(*) FROM fact_bea_national_industry)
    UNION ALL SELECT 'bridge_naics_bea', (SELECT COUNT(*) FROM bridge_naics_bea)
    UNION ALL SELECT 'dim_county_geometry', (SELECT COUNT(*) FROM dim_county_geometry)
    UNION ALL SELECT 'bridge_county_h3', (SELECT COUNT(*) FROM bridge_county_h3)
    UNION ALL SELECT 'fact_bea_county_gdp', (SELECT COUNT(*) FROM fact_bea_county_gdp)
    UNION ALL SELECT 'dim_county', (SELECT COUNT(*) FROM dim_county)
    UNION ALL SELECT 'dim_industry', (SELECT COUNT(*) FROM dim_industry)
    UNION ALL SELECT 'fact_qcew_annual', (SELECT COUNT(*) FROM fact_qcew_annual)
)
""",
    "02_deflator_check": """
SELECT
    fs.series_code,
    fs.title as series_name,
    MIN(t.year) as min_year,
    MAX(t.year) as max_year,
    COUNT(*) as observation_count
FROM fact_fred_national fn
JOIN dim_fred_series fs ON fn.series_id = fs.series_id
JOIN dim_time t ON fn.time_id = t.time_id
WHERE fs.series_code = 'GDPDEF'
GROUP BY fs.series_code, fs.title
""",
    "03_bea_national_sample": """
SELECT
    bi.bea_code,
    bi.industry_name,
    t.year,
    n.gross_output_millions,
    n.intermediate_inputs_millions,
    n.value_added_millions,
    (n.intermediate_inputs_millions + n.value_added_millions) as computed_go,
    ABS(n.gross_output_millions - (n.intermediate_inputs_millions + n.value_added_millions)) as discrepancy
FROM fact_bea_national_industry n
JOIN dim_bea_industry bi ON n.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON n.time_id = t.time_id
WHERE t.year = 2023
ORDER BY bi.bea_code
""",
    "04_bea_national_totals_by_year": """
SELECT
    t.year,
    SUM(n.gross_output_millions) as total_go,
    SUM(n.intermediate_inputs_millions) as total_ii,
    SUM(n.value_added_millions) as total_va,
    SUM(n.intermediate_inputs_millions) + SUM(n.value_added_millions) as computed_go,
    ABS(SUM(n.gross_output_millions) - (SUM(n.intermediate_inputs_millions) + SUM(n.value_added_millions))) as discrepancy,
    ROUND(100.0 * ABS(SUM(n.gross_output_millions) - (SUM(n.intermediate_inputs_millions) + SUM(n.value_added_millions))) / SUM(n.gross_output_millions), 4) as discrepancy_pct
FROM fact_bea_national_industry n
JOIN dim_time t ON n.time_id = t.time_id
GROUP BY t.year
ORDER BY t.year
""",
    "05_concordance_coverage": """
SELECT
    i.naics_level,
    COUNT(DISTINCT i.industry_id) as total_industries,
    COUNT(DISTINCT b.industry_id) as mapped_industries,
    COUNT(DISTINCT i.industry_id) - COUNT(DISTINCT b.industry_id) as unmapped,
    ROUND(100.0 * COUNT(DISTINCT b.industry_id) / COUNT(DISTINCT i.industry_id), 2) as coverage_pct
FROM dim_industry i
LEFT JOIN bridge_naics_bea b ON i.industry_id = b.industry_id
GROUP BY i.naics_level
ORDER BY i.naics_level
""",
    "06_county_geometry_coverage": """
SELECT
    COUNT(DISTINCT c.county_id) as total_counties,
    COUNT(DISTINCT g.county_id) as counties_with_geometry,
    COUNT(DISTINCT c.county_id) - COUNT(DISTINCT g.county_id) as missing_geometry
FROM dim_county c
LEFT JOIN dim_county_geometry g ON c.county_id = g.county_id
""",
    "07_h3_grid_stats": """
SELECT
    resolution,
    COUNT(DISTINCT h3_index) as hex_count,
    COUNT(DISTINCT county_id) as counties_covered,
    ROUND(AVG(coverage_pct), 2) as avg_coverage_pct
FROM bridge_county_h3
GROUP BY resolution
""",
    "08_county_gdp_coverage": """
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
    "09_county_gdp_industry_detail": """
SELECT
    bi.bea_code,
    bi.industry_name,
    COUNT(DISTINCT g.county_id) as counties_with_data,
    ROUND(SUM(g.gdp_millions), 2) as total_gdp_millions
FROM fact_bea_county_gdp g
JOIN dim_bea_industry bi ON g.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON g.time_id = t.time_id
WHERE t.year = 2023
GROUP BY bi.bea_code, bi.industry_name
ORDER BY bi.bea_code
""",
    "10_detroit_test_case": """
SELECT
    c.county_fips as fips,
    c.county_name,
    t.year,
    bi.bea_code,
    g.gdp_millions as bea_gdp,
    q.total_wages_usd / 1e6 as qcew_wages_millions,
    g.gdp_millions - (q.total_wages_usd / 1e6) as implied_surplus_millions
FROM fact_bea_county_gdp g
JOIN dim_county c ON g.county_id = c.county_id
JOIN dim_bea_industry bi ON g.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON g.time_id = t.time_id
LEFT JOIN fact_qcew_annual q ON c.county_id = q.county_id AND t.time_id = q.time_id
LEFT JOIN dim_industry i ON q.industry_id = i.industry_id
LEFT JOIN bridge_naics_bea bnb ON i.industry_id = bnb.industry_id AND bnb.bea_industry_id = g.bea_industry_id
WHERE c.county_fips IN ('26163', '26125')
  AND t.year = 2023
  AND bi.bea_code = '31G'
ORDER BY c.county_fips, bi.bea_code
""",
    "11_tensor_query_test": """
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
    NULL as v_millions,
    ROUND(g.gdp_millions, 2) as va_millions,
    ROUND(nr.c_ratio, 4) as c_ratio,
    ROUND(nr.va_ratio, 4) as va_ratio
FROM fact_bea_county_gdp g
JOIN national_ratios nr ON g.bea_industry_id = nr.bea_industry_id AND g.time_id = nr.time_id
JOIN dim_county c ON g.county_id = c.county_id
JOIN dim_bea_industry bi ON g.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON g.time_id = t.time_id
WHERE c.county_fips IN ('26163', '26125')
  AND t.year = 2023
ORDER BY c.county_fips, bi.bea_code
""",
    "12_qcew_bea_join_test": """
SELECT
    c.county_fips as fips,
    c.county_name,
    bi.bea_code,
    bi.industry_name as bea_industry,
    COUNT(DISTINCT i.industry_id) as naics_industries_mapped,
    SUM(q.total_wages_usd) / 1e6 as total_wages_millions,
    SUM(q.employment) as total_employment
FROM fact_qcew_annual q
JOIN dim_county c ON q.county_id = c.county_id
JOIN dim_industry i ON q.industry_id = i.industry_id
JOIN bridge_naics_bea bnb ON i.industry_id = bnb.industry_id
JOIN dim_bea_industry bi ON bnb.bea_industry_id = bi.bea_industry_id
JOIN dim_time t ON q.time_id = t.time_id
WHERE c.county_fips IN ('26163', '26125')
  AND t.year = 2023
GROUP BY c.county_fips, c.county_name, bi.bea_code, bi.industry_name
ORDER BY c.county_fips, bi.bea_code
""",
}


def run_diagnostics() -> None:
    """Run all diagnostic queries and export to CSVs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session_factory = get_normalized_session_factory()
    results: dict[str, str] = {}  # query_name -> status
    csv_files: list[Path] = []

    with session_factory() as session:
        for query_name, query_sql in QUERIES.items():
            csv_path = OUTPUT_DIR / f"{query_name}.csv"
            print(f"Running {query_name}...")

            try:
                result = session.execute(text(query_sql))
                rows = result.fetchall()
                columns = result.keys()

                # Write CSV
                with open(csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(rows)

                csv_files.append(csv_path)
                results[query_name] = f"OK ({len(rows)} rows)"
                print(f"  -> {len(rows)} rows")

            except Exception as e:
                results[query_name] = f"FAILED: {e}"
                print(f"  -> FAILED: {e}")

    # Create zip file
    zip_path = OUTPUT_DIR / f"tensor-readiness-{TODAY}.zip"
    print(f"\nCreating {zip_path}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for csv_path in csv_files:
            zf.write(csv_path, csv_path.name)

    # Print summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC RESULTS SUMMARY")
    print("=" * 60)

    for query_name, status in results.items():
        status_icon = "✓" if status.startswith("OK") else "✗"
        print(f"{status_icon} {query_name}: {status}")

    print(f"\nExported to: {zip_path}")
    print(f"Zip size: {zip_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    run_diagnostics()
