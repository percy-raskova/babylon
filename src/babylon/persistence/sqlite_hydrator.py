"""SQLite → Postgres hydration for Spec 062 immutable_reference_* tables.

Reads the 3NF SQLite fixture at ``data/sqlite/marxist-data-3NF.sqlite``
and copies a year-range slice of each canonical reference series into the
session-scoped ``immutable_reference_*`` Postgres tables.

This is the load-bearing implementation of FR-001 / FR-004 / FR-005 that
the MVP ``copy_reference_series`` stub left for later.

The hydrator is deliberately READ-ONLY against SQLite (``mode=ro`` URI).
Writes go through a single Postgres transaction so a partial copy on
error rolls back cleanly.

See Also:
    ``specs/062-cross-scale-integration/contracts/reference_series.yaml``.
    :mod:`babylon.persistence.postgres_initialization`.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from babylon.persistence import PostgresRuntime

logger = logging.getLogger(__name__)


# Years that the FRED rate series produces an annual snapshot via averaging
# the monthly observations (frequency='Monthly' in dim_fred_series).
DEFAULT_FRED_SERIES: tuple[str, ...] = (
    "FEDFUNDS",  # Effective Federal Funds Rate
    "CPIAUCSL",  # CPI (used by some downstream calibration)
    "UNRATE",  # National unemployment rate
)


def _sqlite_readonly(sqlite_path: Path) -> sqlite3.Connection:
    """Open the SQLite reference DB read-only."""
    return sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True, check_same_thread=False)


def hydrate_session_references(
    *,
    session_id: UUID,
    start_year: int,
    end_year: int,
    sqlite_path: Path,
    runtime: PostgresRuntime,
    counties: Iterable[str] | None = None,
    fred_series: Iterable[str] = DEFAULT_FRED_SERIES,
) -> dict[str, int]:
    """Copy every reference series for the session year-range.

    Args:
        session_id: Owning session UUID.
        start_year: First year (inclusive).
        end_year: Last year (inclusive).
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        runtime: PostgresRuntime to write through.
        counties: Optional iterable of 5-digit county FIPS codes to
            restrict QCEW / rent hydration. When None, all counties are
            copied (large — ~3000 counties × 16 years × hundreds of
            industries can exceed 100M rows for QCEW).
        fred_series: FRED series codes to copy. Defaults to FEDFUNDS, CPI,
            UNRATE.

    Returns:
        ``{series_id: row_count_copied}`` map.
    """
    if not sqlite_path.is_file():
        raise FileNotFoundError(sqlite_path)
    sqlite_conn = _sqlite_readonly(sqlite_path)
    counts: dict[str, int] = {}
    try:
        with (
            runtime._pool.connection() as pg,  # noqa: SLF001
            pg.transaction(),
        ):
            counts["bea_io"] = _copy_bea_io(sqlite_conn, pg, session_id, start_year, end_year)
            counts["melt_tau"] = _copy_melt_tau(sqlite_conn, pg, session_id, start_year, end_year)
            counts["basket_gamma"] = _copy_basket_gamma(
                sqlite_conn, pg, session_id, start_year, end_year
            )
            counts["erdi"] = _copy_erdi(sqlite_conn, pg, session_id, start_year, end_year)
            counts["hickel_drain"] = _copy_hickel_drain(
                sqlite_conn, pg, session_id, start_year, end_year
            )
            counts["ricci_unequal"] = _copy_ricci_unequal(
                sqlite_conn, pg, session_id, start_year, end_year
            )
            counts["faf_freight"] = _copy_faf_freight(
                sqlite_conn, pg, session_id, start_year, end_year
            )
            counts["qcew_employment"] = _copy_qcew(
                sqlite_conn,
                pg,
                session_id,
                start_year,
                end_year,
                counties,
            )
            counts["bea_reis_rent"] = _copy_rent(
                sqlite_conn,
                pg,
                session_id,
                start_year,
                end_year,
                counties,
            )
            counts["fred_rates"] = _copy_fred(
                sqlite_conn,
                pg,
                session_id,
                start_year,
                end_year,
                fred_series,
            )
    finally:
        sqlite_conn.close()
    logger.info("Hydrated reference series for session %s: %s rows", session_id, counts)
    return counts


# ─────────────── per-series copy helpers ──────────────────────────────


def _year_id_range(
    sqlite_conn: sqlite3.Connection, start_year: int, end_year: int
) -> dict[int, int]:
    """Return ``{year: time_id}`` for is_annual rows in the year-range."""
    rows = sqlite_conn.execute(
        "SELECT time_id, year FROM dim_time "
        "WHERE is_annual = 1 AND year BETWEEN ? AND ? ORDER BY year",
        (start_year, end_year),
    ).fetchall()
    return {y: t for t, y in rows}


def _copy_bea_io(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
) -> int:
    """Copy BEA I-O matrices as JSONB blobs (one per (year, kind))."""
    year_ids = _year_id_range(sqlite_conn, start_year, end_year)
    if not year_ids:
        return 0
    # Aggregate per (year, table_type_id) into a sparse-JSON shape.
    placeholders = ",".join("?" * len(year_ids.values()))
    rows = sqlite_conn.execute(
        f"""
        SELECT dt.year, c.table_type_id,
               c.source_industry_id, c.target_industry_id, c.coefficient
        FROM fact_bea_io_coefficient c
        JOIN dim_time dt ON c.time_id = dt.time_id
        WHERE c.time_id IN ({placeholders})
        """,  # noqa: S608 — placeholder-count helper emits only ? tokens; values bound
        tuple(year_ids.values()),
    ).fetchall()
    # Group by (year, table_type_id) → list of (src, dst, coef).
    matrices: dict[tuple[int, int], list[tuple[int, int, float]]] = {}
    for year, kind, src, dst, coef in rows:
        matrices.setdefault((year, kind), []).append((src, dst, coef))
    # table_type_id mapping: 1=make, 2=use, 3=imports (heuristic — varies by DB).
    # For the MVP we serialize raw triples under matrix_kind='intermediate'
    # since downstream consumption is mainly the imports-on-domestic ratio.
    n = 0
    import json

    for (year, _kind), triples in matrices.items():
        pg.execute(
            "INSERT INTO immutable_reference_bea_io "
            "(session_id, year, matrix_kind, coefficients, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, matrix_kind) DO NOTHING",
            (
                str(session_id),
                year,
                "intermediate",
                json.dumps(triples[:5000]),  # Cap to avoid 100k+ row payloads
                "BEA Make-Use-Imports 2010-2024 (fact_bea_io_coefficient)",
            ),
        )
        n += 1
    return n


def _copy_melt_tau(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
) -> int:
    """Synthesize MELT τ from BLS productivity index (annual)."""
    year_ids = _year_id_range(sqlite_conn, start_year, end_year)
    if not year_ids:
        return 0
    # Use CPIAUCSL-derived annual average as the price-of-labor-time proxy.
    rows = sqlite_conn.execute(
        """
        SELECT dt.year, AVG(f.value) AS tau
        FROM fact_fred_national f
        JOIN dim_fred_series dfs ON f.series_id = dfs.series_id
        JOIN dim_time dt ON f.time_id = dt.time_id
        WHERE dfs.series_code = 'CPIAUCSL'
          AND dt.year BETWEEN ? AND ?
        GROUP BY dt.year
        """,
        (start_year, end_year),
    ).fetchall()
    n = 0
    for year, tau in rows:
        if tau is None or tau <= 0:
            continue
        pg.execute(
            "INSERT INTO immutable_reference_melt_tau "
            "(session_id, year, tau, canonical_source) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (session_id, year) DO NOTHING",
            (
                str(session_id),
                year,
                float(tau),
                "BLS CPIAUCSL annual average (proxy for MELT τ)",
            ),
        )
        n += 1
    return n


def _copy_basket_gamma(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
) -> int:
    """Basket γ: constant per year for the MVP (real derivation is Spec 015).

    Uses the Hickel α coefficient as the closest proxy.
    """
    rows = sqlite_conn.execute(
        "SELECT dt.year, AVG(h.alpha) "
        "FROM fact_hickel_erdi_annual h "
        "JOIN dim_time dt ON h.time_id = dt.time_id "
        "WHERE dt.year BETWEEN ? AND ? AND h.alpha IS NOT NULL "
        "GROUP BY dt.year",
        (start_year, end_year),
    ).fetchall()
    n = 0
    for year, alpha in rows:
        if alpha is None:
            continue
        gamma = max(0.0, min(1.0, float(alpha)))  # clamp to [0,1] per CHECK
        pg.execute(
            "INSERT INTO immutable_reference_basket_gamma "
            "(session_id, year, gamma, canonical_source) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (session_id, year) DO NOTHING",
            (
                str(session_id),
                year,
                gamma,
                "Hickel α (alpha) as basket-visibility proxy",
            ),
        )
        n += 1
    return n


def _copy_erdi(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
) -> int:
    """Hickel ERDI ratios per partner_node_id (international aggregates)."""
    rows = sqlite_conn.execute(
        "SELECT dt.year, h.scale_type, h.erdi "
        "FROM fact_hickel_erdi_annual h "
        "JOIN dim_time dt ON h.time_id = dt.time_id "
        "WHERE dt.year BETWEEN ? AND ? AND h.erdi IS NOT NULL AND h.erdi > 0",
        (start_year, end_year),
    ).fetchall()
    n = 0
    for year, scale_type, erdi in rows:
        if not scale_type or erdi is None or erdi <= 0:
            continue
        pg.execute(
            "INSERT INTO immutable_reference_erdi "
            "(session_id, year, partner_node_id, erdi_ratio, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, partner_node_id) DO NOTHING",
            (
                str(session_id),
                year,
                str(scale_type),
                float(erdi),
                "Hickel ERDI annual (fact_hickel_erdi_annual)",
            ),
        )
        n += 1
    return n


def _copy_hickel_drain(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
) -> int:
    """Hickel annual Φ drain in USD billions → USD."""
    rows = sqlite_conn.execute(
        "SELECT dt.year, h.scale_type, h.annual_drain_usd_billions "
        "FROM fact_hickel_erdi_annual h "
        "JOIN dim_time dt ON h.time_id = dt.time_id "
        "WHERE dt.year BETWEEN ? AND ? AND h.annual_drain_usd_billions IS NOT NULL",
        (start_year, end_year),
    ).fetchall()
    n = 0
    for year, scale_type, billions in rows:
        if not scale_type or billions is None:
            continue
        phi = max(0.0, float(billions) * 1e9)
        pg.execute(
            "INSERT INTO immutable_reference_hickel_drain "
            "(session_id, year, partner_node_id, phi_year, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, partner_node_id) DO NOTHING",
            (
                str(session_id),
                year,
                str(scale_type),
                phi,
                "Hickel annual drain × 1e9 USD (fact_hickel_erdi_annual.annual_drain_usd_billions)",
            ),
        )
        n += 1
    return n


def _copy_ricci_unequal(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
) -> int:
    """Bilateral trade aggregates by country and year (bulk insert)."""
    rows = sqlite_conn.execute(
        """
        SELECT dt.year, c.country_name,
               SUM(t.imports_usd_millions + t.exports_usd_millions) AS bilateral
        FROM fact_trade_monthly t
        JOIN dim_time dt ON t.time_id = dt.time_id
        JOIN dim_country c ON t.country_id = c.country_id
        WHERE dt.year BETWEEN ? AND ?
        GROUP BY dt.year, c.country_name
        """,
        (start_year, end_year),
    ).fetchall()
    payload = [
        (
            str(session_id),
            year,
            str(name)[:64],
            float(bilateral) * 1e6,
            "Census bilateral trade (fact_trade_monthly) USD",
        )
        for year, name, bilateral in rows
        if bilateral is not None and bilateral >= 0
    ]
    if not payload:
        return 0
    with pg.cursor() as cur:
        cur.executemany(
            "INSERT INTO immutable_reference_ricci_unequal "
            "(session_id, year, partner_node_id, bilateral_value, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, partner_node_id) DO NOTHING",
            payload,
        )
    return len(payload)


def _copy_faf_freight(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
) -> int:
    """FAF freight totals by CFS area and year (bulk insert)."""
    rows = sqlite_conn.execute(
        """
        SELECT year, origin_cfs_area_id, SUM(tons_thousands) AS tons
        FROM fact_faf_commodity_flow
        WHERE year BETWEEN ? AND ?
        GROUP BY year, origin_cfs_area_id
        """,
        (start_year, end_year),
    ).fetchall()
    payload = [
        (
            str(session_id),
            int(year),
            f"cfs_{int(origin)}",
            float(tons) * 1000.0,
            "FAF commodity flow (fact_faf_commodity_flow.tons_thousands)",
        )
        for year, origin, tons in rows
        if tons is not None and tons >= 0
    ]
    if not payload:
        return 0
    with pg.cursor() as cur:
        cur.executemany(
            "INSERT INTO immutable_reference_faf_freight "
            "(session_id, year, partner_node_id, tons, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, partner_node_id) DO NOTHING",
            payload,
        )
    return len(payload)


def _copy_qcew(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
    counties: Iterable[str] | None,
) -> int:
    """QCEW annual employment per (county_fips, naics).

    Uses ``cursor.executemany`` with a batched payload so the 57k-row
    tri-county slice completes in a few seconds rather than minutes.
    """
    cnty_filter = ""
    params: list[Any] = [start_year, end_year]
    if counties is not None:
        county_list = list(counties)
        if not county_list:
            return 0
        cnty_filter = f"AND dc.fips IN ({','.join('?' * len(county_list))})"
        params.extend(county_list)
    sql = f"""
        SELECT dt.year, dc.fips AS county_fips,
               di.naics_code AS naics_code,
               SUM(q.employment) AS employment
        FROM fact_qcew_annual q
        JOIN dim_time dt ON q.time_id = dt.time_id
        JOIN dim_county dc ON q.county_id = dc.county_id
        JOIN dim_industry di ON q.industry_id = di.industry_id
        WHERE dt.year BETWEEN ? AND ?
          {cnty_filter}
          AND q.employment IS NOT NULL AND q.employment > 0
        GROUP BY dt.year, dc.fips, di.naics_code
    """  # noqa: S608 — placeholder-count helper emits only ? tokens; values bound
    try:
        rows = sqlite_conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such column" in str(exc):
            sql = sql.replace(
                "di.naics_code AS naics_code",
                "CAST(di.industry_id AS TEXT) AS naics_code",
            )
            rows = sqlite_conn.execute(sql, params).fetchall()
        else:
            raise

    payload = [
        (
            str(session_id),
            int(year),
            str(fips),
            str(naics),
            int(emp),
            "BLS QCEW annual (fact_qcew_annual)",
        )
        for year, fips, naics, emp in rows
        if emp is not None and emp >= 0
    ]
    if not payload:
        return 0
    with pg.cursor() as cur:
        cur.executemany(
            "INSERT INTO immutable_reference_qcew_employment "
            "(session_id, year, county_fips, naics_code, employment, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, county_fips, naics_code) DO NOTHING",
            payload,
        )
    return len(payload)


def _copy_rent(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
    counties: Iterable[str] | None,
) -> int:
    """Median rent per (county_fips, year) — proxy for BEA REIS rent."""
    cnty_filter = ""
    params: list[Any] = [start_year, end_year]
    if counties is not None:
        county_list = list(counties)
        if not county_list:
            return 0
        cnty_filter = f"AND dc.fips IN ({','.join('?' * len(county_list))})"
        params.extend(county_list)
    sql = f"""
        SELECT dt.year, dc.fips AS county_fips, AVG(r.median_rent_usd) AS rent
        FROM fact_census_rent r
        JOIN dim_time dt ON r.time_id = dt.time_id
        JOIN dim_county dc ON r.county_id = dc.county_id
        WHERE dt.year BETWEEN ? AND ? {cnty_filter}
        GROUP BY dt.year, dc.fips
    """  # noqa: S608 — placeholder-count helper emits only ? tokens; values bound
    rows = sqlite_conn.execute(sql, params).fetchall()
    n = 0
    for year, fips, rent in rows:
        if rent is None or rent < 0:
            continue
        pg.execute(
            "INSERT INTO immutable_reference_bea_reis_rent "
            "(session_id, year, county_fips, rent, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, county_fips) DO NOTHING",
            (
                str(session_id),
                int(year),
                str(fips),
                float(rent),
                "Census ACS median rent (fact_census_rent — BEA REIS proxy)",
            ),
        )
        n += 1
    return n


def _copy_fred(
    sqlite_conn: sqlite3.Connection,
    pg: Any,
    session_id: UUID,
    start_year: int,
    end_year: int,
    fred_series: Iterable[str],
) -> int:
    """FRED national series annual averages."""
    series_codes = tuple(fred_series)
    if not series_codes:
        return 0
    placeholders = ",".join("?" * len(series_codes))
    rows = sqlite_conn.execute(
        f"""
        SELECT dfs.series_code, dt.year, AVG(f.value) AS rate
        FROM fact_fred_national f
        JOIN dim_fred_series dfs ON f.series_id = dfs.series_id
        JOIN dim_time dt ON f.time_id = dt.time_id
        WHERE dfs.series_code IN ({placeholders})
          AND dt.year BETWEEN ? AND ?
        GROUP BY dfs.series_code, dt.year
        """,  # noqa: S608 — placeholder-count helper emits only ? tokens; values bound
        (*series_codes, start_year, end_year),
    ).fetchall()
    n = 0
    for code, year, rate in rows:
        if rate is None:
            continue
        pg.execute(
            "INSERT INTO immutable_reference_fred_rates "
            "(session_id, year, series_id, rate, canonical_source) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, year, series_id) DO NOTHING",
            (
                str(session_id),
                int(year),
                str(code),
                float(rate),
                "FRED national annual average (fact_fred_national)",
            ),
        )
        n += 1
    return n


__all__ = ["hydrate_session_references", "DEFAULT_FRED_SERIES"]
