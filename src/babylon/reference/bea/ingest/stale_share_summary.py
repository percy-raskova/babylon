"""Compute the ``StaleShareFallbackSummary`` for SC-008 (spec-068 T058).

SC-008 requires that the audit report classifies every (county, year)
row by concordance-coverage status, with uncovered employment < 1% of
QCEW employment to pass.

The summary aggregates per-(county, year) lookups into:
  - ``total_county_year_lookups``: count of (county, year) pairs with QCEW
    employment mapped through ``bridge_naics_bea``.
  - ``forward_filled_lookups``: pairs where at least one BEA industry was
    forward-filled (data exists within 5 years but not for the exact year).
  - ``global_default_lookups``: pairs where at least one BEA industry fell
    back to ``GLOBAL_FALLBACK_SHARE`` (no data within 5 years).
  - ``affected_employment_fraction``: employment-weighted fraction in
    global-default industries (the SC-008 gate metric).

The computation is SQL-based for efficiency — a single multi-join query
over ``fact_qcew_annual``, ``bridge_naics_bea``, and
``fact_bea_national_industry`` replaces 45 000 per-county service calls.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from babylon.reference.bea.ingest.audit_report import StaleShareFallbackSummary

log = logging.getLogger(__name__)

_MAX_FORWARD_FILL_YEARS = 5


def compute_stale_share_fallback_summary(
    session: Session,
    years: range,
) -> StaleShareFallbackSummary:
    """Compute the stale-share fallback summary for the given year range.

    Args:
        session: SQLAlchemy session against the reference DB.
        years: Inclusive year range (e.g., ``range(2010, 2025)``).

    Returns:
        ``StaleShareFallbackSummary`` with aggregate fallback stats.
    """
    if not years:
        return StaleShareFallbackSummary(
            total_county_year_lookups=0,
            forward_filled_lookups=0,
            global_default_lookups=0,
            affected_employment_fraction=1.0,
        )

    start_year = years.start
    end_year = years.stop - 1

    query = text(
        """
        WITH bea_coverage AS (
            SELECT b.bea_industry_id, t.year,
                   CASE
                       WHEN EXISTS(
                           SELECT 1 FROM fact_bea_national_industry f
                           JOIN dim_time t2 ON t2.time_id = f.time_id
                           WHERE f.bea_industry_id = b.bea_industry_id
                             AND t2.year = t.year
                       ) THEN 'direct'
                       WHEN EXISTS(
                           SELECT 1 FROM fact_bea_national_industry f
                           JOIN dim_time t2 ON t2.time_id = f.time_id
                           WHERE f.bea_industry_id = b.bea_industry_id
                             AND t2.year BETWEEN t.year - :max_ff AND t.year - 1
                       ) THEN 'forward_fill'
                       ELSE 'global_default'
                   END AS coverage
            FROM (SELECT DISTINCT bea_industry_id FROM bridge_naics_bea) b
            CROSS JOIN (
                SELECT DISTINCT year FROM dim_time
                WHERE is_annual = 1 AND year >= :yr_start AND year <= :yr_end
            ) t
        ),
        county_year_employment AS (
            SELECT dc.fips, t.year,
                   SUM(fq.employment) AS total_emp,
                   SUM(CASE WHEN bc.coverage = 'global_default'
                            THEN fq.employment ELSE 0 END) AS uncovered_emp,
                   SUM(CASE WHEN bc.coverage = 'forward_fill'
                            THEN fq.employment ELSE 0 END) AS forward_fill_emp
            FROM fact_qcew_annual fq
            JOIN dim_county dc ON dc.county_id = fq.county_id
            JOIN dim_time t ON t.time_id = fq.time_id
            JOIN bridge_naics_bea b ON b.industry_id = fq.industry_id
            JOIN bea_coverage bc
              ON bc.bea_industry_id = b.bea_industry_id AND bc.year = t.year
            WHERE t.year >= :yr_start AND t.year <= :yr_end
            GROUP BY dc.fips, t.year
        )
        SELECT
            COUNT(*) AS total_lookups,
            COALESCE(SUM(CASE WHEN forward_fill_emp > 0 THEN 1 ELSE 0 END), 0)
                AS forward_filled_lookups,
            COALESCE(SUM(CASE WHEN uncovered_emp > 0 THEN 1 ELSE 0 END), 0)
                AS global_default_lookups,
            CASE WHEN SUM(total_emp) > 0
                 THEN CAST(SUM(uncovered_emp) AS FLOAT) / SUM(total_emp)
                 ELSE 1.0
            END AS affected_fraction
        FROM county_year_employment
        """
    )

    row = session.execute(
        query,
        {
            "yr_start": start_year,
            "yr_end": end_year,
            "max_ff": _MAX_FORWARD_FILL_YEARS,
        },
    ).one()

    total_lookups = int(row.total_lookups or 0)
    forward_filled = int(row.forward_filled_lookups or 0)
    global_default = int(row.global_default_lookups or 0)
    # NOTE: ``or 1.0`` would treat 0.0 as falsy (Python gotcha) — use
    # explicit None check so a true 0.0 fraction is preserved.
    affected = float(row.affected_fraction) if row.affected_fraction is not None else 1.0

    log.info(
        "stale_share_fallback_summary: total=%d ff=%d gd=%d affected=%.6f",
        total_lookups,
        forward_filled,
        global_default,
        affected,
    )

    return StaleShareFallbackSummary(
        total_county_year_lookups=total_lookups,
        forward_filled_lookups=forward_filled,
        global_default_lookups=global_default,
        affected_employment_fraction=affected,
    )


__all__ = ["compute_stale_share_fallback_summary"]
