"""Marxian analytical views for normalized database.

Creates SQL views for common analytical queries:
- Imperial rent calculation
- Surplus value calculation
- Labor aristocracy detection
- Unequal exchange analysis
- Class composition breakdown
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

# =============================================================================
# VIEW DEFINITIONS
# =============================================================================

VIEWS: dict[str, str] = {
    # View 1: Imperial Rent (Φ = W_c - V_c)
    "view_imperial_rent": """
        SELECT
            i.naics_code,
            i.industry_title,
            i.class_composition,
            t.year,
            p.labor_compensation_millions_usd AS wages_core_millions,
            p.sectoral_output_millions_usd AS value_produced_millions,
            (p.labor_compensation_millions_usd - p.sectoral_output_millions_usd) AS imperial_rent_millions,
            CASE
                WHEN p.sectoral_output_millions_usd > 0
                THEN p.labor_compensation_millions_usd / p.sectoral_output_millions_usd
                ELSE NULL
            END AS labor_aristocracy_ratio
        FROM fact_productivity_annual p
        JOIN dim_industry i ON p.industry_id = i.industry_id
        JOIN dim_time t ON p.time_id = t.time_id
        WHERE t.is_annual = 1
    """,
    # View 2: Surplus Value (S = Output - Labor Compensation)
    "view_surplus_value": """
        SELECT
            i.naics_code,
            i.industry_title,
            i.sector_code,
            i.class_composition,
            t.year,
            p.sectoral_output_millions_usd AS gross_output,
            p.labor_compensation_millions_usd AS variable_capital,
            (p.sectoral_output_millions_usd - p.labor_compensation_millions_usd) AS surplus_value,
            CASE
                WHEN p.labor_compensation_millions_usd > 0
                THEN (p.sectoral_output_millions_usd - p.labor_compensation_millions_usd) / p.labor_compensation_millions_usd
                ELSE NULL
            END AS rate_of_exploitation,
            p.hours_worked_millions,
            p.labor_productivity_index / 100.0 AS productivity_level
        FROM fact_productivity_annual p
        JOIN dim_industry i ON p.industry_id = i.industry_id
        JOIN dim_time t ON p.time_id = t.time_id
        WHERE t.is_annual = 1
    """,
    # View 3: Trade Annual (replaces denormalized table)
    "view_trade_annual": """
        SELECT
            c.country_id,
            c.country_name,
            c.world_system_tier,
            t.year,
            SUM(f.imports_usd_millions) AS imports_total,
            SUM(f.exports_usd_millions) AS exports_total,
            SUM(f.imports_usd_millions) - SUM(f.exports_usd_millions) AS trade_balance
        FROM fact_trade_monthly f
        JOIN dim_country c ON f.country_id = c.country_id
        JOIN dim_time t ON f.time_id = t.time_id
        WHERE t.month IS NOT NULL
        GROUP BY c.country_id, c.country_name, c.world_system_tier, t.year
    """,
    # View 4: Unequal Exchange by World-System Tier
    "view_unequal_exchange": """
        SELECT
            c.world_system_tier,
            t.year,
            SUM(f.imports_usd_millions) AS total_imports,
            SUM(f.exports_usd_millions) AS total_exports,
            SUM(f.imports_usd_millions) - SUM(f.exports_usd_millions) AS trade_deficit,
            CASE
                WHEN SUM(f.exports_usd_millions) > 0
                THEN (SUM(f.imports_usd_millions) - SUM(f.exports_usd_millions)) / SUM(f.exports_usd_millions)
                ELSE NULL
            END AS unequal_exchange_ratio
        FROM fact_trade_monthly f
        JOIN dim_country c ON f.country_id = c.country_id
        JOIN dim_time t ON f.time_id = t.time_id
        WHERE c.is_region = 0
          AND c.world_system_tier IS NOT NULL
        GROUP BY c.world_system_tier, t.year
    """,
    # View 5: Class Composition by County
    "view_class_composition": """
        SELECT
            c.fips,
            c.county_name,
            s.state_name,
            wc.marxian_class,
            SUM(f.worker_count) AS total_workers
        FROM fact_census_worker_class f
        JOIN dim_county c ON f.county_id = c.county_id
        JOIN dim_state s ON c.state_id = s.state_id
        JOIN dim_worker_class wc ON f.class_id = wc.class_id
        WHERE wc.marxian_class IS NOT NULL
        GROUP BY c.fips, c.county_name, s.state_name, wc.marxian_class
    """,
    # View 6: Rent Crisis (High rent-burden areas)
    "view_rent_crisis": """
        SELECT
            c.fips,
            c.county_name,
            s.state_name,
            fr.median_rent_usd,
            fi.median_income_usd,
            CASE
                WHEN fi.median_income_usd > 0
                THEN (fr.median_rent_usd * 12) / fi.median_income_usd
                ELSE NULL
            END AS annual_rent_to_income_ratio,
            SUM(CASE WHEN rb.is_cost_burdened = 1 THEN fb.household_count ELSE 0 END) AS cost_burdened_households,
            SUM(CASE WHEN rb.is_severely_burdened = 1 THEN fb.household_count ELSE 0 END) AS severely_burdened_households,
            SUM(fb.household_count) AS total_renter_households
        FROM fact_census_rent fr
        JOIN fact_census_median_income fi ON fr.county_id = fi.county_id AND fr.source_id = fi.source_id
        JOIN fact_census_rent_burden fb ON fr.county_id = fb.county_id AND fr.source_id = fb.source_id
        JOIN dim_rent_burden rb ON fb.burden_id = rb.burden_id
        JOIN dim_county c ON fr.county_id = c.county_id
        JOIN dim_state s ON c.state_id = s.state_id
        GROUP BY c.fips, c.county_name, s.state_name, fr.median_rent_usd, fi.median_income_usd
    """,
    # View 7: Wealth Concentration by Class
    "view_wealth_concentration": """
        SELECT
            wc.percentile_label,
            wc.babylon_class,
            ac.category_label,
            t.year,
            t.quarter,
            SUM(f.value_millions) AS total_wealth_millions,
            AVG(fs.share_percent) AS avg_share_percent
        FROM fact_fred_wealth_levels f
        JOIN dim_wealth_class wc ON f.wealth_class_id = wc.wealth_class_id
        JOIN dim_asset_category ac ON f.category_id = ac.category_id
        JOIN dim_time t ON f.time_id = t.time_id
        LEFT JOIN fact_fred_wealth_shares fs ON
            f.wealth_class_id = fs.wealth_class_id AND
            f.category_id = fs.category_id AND
            f.time_id = fs.time_id
        GROUP BY wc.percentile_label, wc.babylon_class, ac.category_label, t.year, t.quarter
    """,
    # View 8: Critical Materials by Import Source
    "view_critical_materials": """
        SELECT
            c.name AS commodity_name,
            c.is_critical,
            c.marxian_interpretation,
            m.name AS metric_name,
            m.category,
            t.year,
            o.value,
            o.value_text
        FROM fact_commodity_observation o
        JOIN dim_commodity c ON o.commodity_id = c.commodity_id
        JOIN dim_commodity_metric m ON o.metric_id = m.metric_id
        JOIN dim_time t ON o.time_id = t.time_id
        WHERE c.is_critical = 1
    """,
    # View 9: Energy Consumption by Sector
    "view_energy_consumption": """
        SELECT
            et.title AS table_title,
            et.category,
            et.marxian_interpretation,
            es.series_name,
            es.units,
            t.year,
            f.value
        FROM fact_energy_annual f
        JOIN dim_energy_series es ON f.series_id = es.series_id
        JOIN dim_energy_table et ON es.table_id = et.table_id
        JOIN dim_time t ON f.time_id = t.time_id
    """,
    # View 10: Labor Type by County
    "view_labor_type": """
        SELECT
            c.fips,
            c.county_name,
            s.state_name,
            o.labor_type,
            SUM(f.worker_count) AS total_workers
        FROM fact_census_occupation f
        JOIN dim_county c ON f.county_id = c.county_id
        JOIN dim_state s ON c.state_id = s.state_id
        JOIN dim_occupation o ON f.occupation_id = o.occupation_id
        WHERE o.labor_type IS NOT NULL
        GROUP BY c.fips, c.county_name, s.state_name, o.labor_type
    """,
}


def create_views(engine: Engine) -> int:
    """Create all analytical views in the database.

    Args:
        engine: SQLAlchemy engine for the normalized database

    Returns:
        Number of views created
    """
    count = 0
    with engine.connect() as conn:
        for view_name, view_sql in VIEWS.items():
            try:
                # Drop existing view
                conn.execute(text(f"DROP VIEW IF EXISTS {view_name}"))
                # Create new view
                conn.execute(text(f"CREATE VIEW {view_name} AS {view_sql}"))
                conn.commit()
                count += 1
            except Exception as e:
                print(f"Error creating view {view_name}: {e}")

    return count


def drop_views(engine: Engine) -> int:
    """Drop all analytical views from the database.

    Args:
        engine: SQLAlchemy engine for the normalized database

    Returns:
        Number of views dropped
    """
    count = 0
    with engine.connect() as conn:
        for view_name in VIEWS:
            try:
                conn.execute(text(f"DROP VIEW IF EXISTS {view_name}"))
                conn.commit()
                count += 1
            except Exception as e:
                print(f"Error dropping view {view_name}: {e}")

    return count


__all__ = [
    "VIEWS",
    "create_views",
    "drop_views",
]
