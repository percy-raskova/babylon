"""Data source protocols and implementations for the MarxianHydrator.

This module defines the protocols that abstract data access for QCEW wage data
and BEA industry ratios, enabling dependency injection and testability.

Protocols:
    QCEWDataSource: Fetches county-level wage data by NAICS code.
    BEADataSource: Provides industry-level c/v and s/v ratios.

Implementations:
    SQLiteQCEWSource: Queries the 3NF normalized QCEW database via SQLAlchemy.

Example:
    >>> from babylon.economics.adapters import QCEWDataSource, BEADataSource
    >>> class MyQCEWSource:
    ...     def fetch_county_wages(self, fips: str, year: int) -> list[tuple[str, float, int]]:
    ...         return [("336111", 1000000.0, 500)]  # (naics, wages, employment)

See Also:
    :mod:`babylon.economics.hydrator`: Uses these protocols for transformation.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@runtime_checkable
class QCEWDataSource(Protocol):
    """Protocol for fetching QCEW (Quarterly Census of Employment and Wages) data.

    Implementations provide county-level wage data by NAICS industry code.
    The protocol enables dependency injection for testing with mock data.

    Example:
        >>> class SQLiteQCEWSource:
        ...     def fetch_county_wages(self, fips_code: str, year: int):
        ...         # Query fact_qcew_annual with dim_county join
        ...         return [(naics, wages, employment), ...]
    """

    def fetch_county_wages(self, fips_code: str, year: int) -> list[tuple[str, float, int]]:
        """Fetch wage data for a county-year.

        Args:
            fips_code: 5-digit FIPS county code (e.g., "26163" for Wayne County).
            year: Data year (e.g., 2022).

        Returns:
            List of (naics_code, total_wages, employment) tuples.
            naics_code: 2-6 digit NAICS industry code.
            total_wages: Annual wages for the industry in the county.
            employment: Average annual employment count.
        """
        ...


@runtime_checkable
class BEADataSource(Protocol):
    """Protocol for fetching BEA (Bureau of Economic Analysis) industry ratios.

    Implementations provide industry-level ratios for deriving constant capital
    and surplus value from variable capital (wages).

    Example:
        >>> class SQLiteBEASource:
        ...     def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        ...         # Query fact_bea_national_industry with bridge_naics_bea
        ...         return computed_ratio or None
    """

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the surplus value to variable capital ratio (s/v) for an industry.

        The s/v ratio represents the rate of surplus value extraction.
        A ratio of 1.0 means surplus value equals wages paid.

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Data year.

        Returns:
            s/v ratio, or None if data is unavailable for this industry.
        """
        ...

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the constant to variable capital ratio (c/v) for an industry.

        The c/v ratio represents the organic composition of capital.
        Higher ratios indicate more capital-intensive production.

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Data year.

        Returns:
            c/v ratio, or None if data is unavailable for this industry.
        """
        ...


# =============================================================================
# IMPLEMENTATIONS
# =============================================================================


class SQLiteQCEWSource:
    """QCEW data source reading from 3NF normalized SQLite database.

    Queries the FactQcewAnnual table with joins to dimension tables
    (DimCounty, DimIndustry, DimTime) to fetch county-level wage data.

    This implementation queries the production database schema using raw SQL
    for performance and simplicity. The query:
    1. Joins fact table with county, industry, and time dimensions
    2. Filters by FIPS code and year
    3. Aggregates wages across ownership types
    4. Returns only records with non-null wage data

    Args:
        session: SQLAlchemy Session for database queries.

    Example:
        >>> from sqlalchemy.orm import Session
        >>> source = SQLiteQCEWSource(session)
        >>> records = source.fetch_county_wages("26163", 2022)
        >>> for naics, wages, employment in records:
        ...     print(f"{naics}: ${wages:,.0f}")
    """

    def __init__(self, session: Session) -> None:
        """Initialize with SQLAlchemy session.

        Args:
            session: SQLAlchemy session for database queries.
        """
        self._session = session

    def fetch_county_wages(self, fips_code: str, year: int) -> list[tuple[str, float, int]]:
        """Fetch wage data for a county-year from the 3NF schema.

        Queries the normalized QCEW schema, joining:
        - FactQcewAnnual (fact table with wages, employment)
        - DimCounty (to filter by FIPS code)
        - DimIndustry (to get NAICS codes)
        - DimTime (to filter by year)

        Aggregates across ownership types (private, government) to get
        total wages and employment per NAICS code.

        Args:
            fips_code: 5-digit FIPS county code (e.g., "26163" for Wayne County).
            year: Data year (e.g., 2022).

        Returns:
            List of (naics_code, total_wages, employment) tuples.
            naics_code: NAICS industry code (2-6 digits).
            total_wages: Annual wages for the industry in the county.
            employment: Average annual employment count.
        """
        # Use raw SQL for performance and explicit control over the query
        query = """
            SELECT
                di.naics_code,
                COALESCE(SUM(f.total_wages_usd), 0.0) as total_wages,
                COALESCE(SUM(f.employment), 0) as employment
            FROM fact_qcew_annual f
            JOIN dim_county dc ON f.county_id = dc.county_id
            JOIN dim_industry di ON f.industry_id = di.industry_id
            JOIN dim_time dt ON f.time_id = dt.time_id
            WHERE dc.fips = :fips
              AND dt.year = :year
              AND dt.is_annual = 1
              AND f.total_wages_usd IS NOT NULL
            GROUP BY di.naics_code
            ORDER BY total_wages DESC
        """

        result = self._session.execute(
            __import__("sqlalchemy").text(query),
            {"fips": fips_code, "year": year},
        )

        # Convert to list of tuples with proper types
        records: list[tuple[str, float, int]] = []
        for row in result:
            naics_code = str(row[0])
            total_wages = float(row[1])
            employment = int(row[2])
            records.append((naics_code, total_wages, employment))

        return records


class InterpolatingBEASource:
    """BEA data source with temporal interpolation.

    This implementation queries the 3NF normalized BEA tables and applies
    temporal interpolation when exact year data is unavailable. Compensation
    (variable capital) is derived from nationally-aggregated QCEW wages for
    all NAICS codes mapping to the same BEA industry, ensuring the BEA
    numerator and QCEW denominator are at the same aggregation level.

    The interpolation algorithm:
    1. Query for exact year match
    2. If no match, find nearest available year within max_delta
    3. If still no match, return None

    For inter-year data:
    - Linear interpolation between the two nearest years
    - Extrapolation beyond known years (up to max_delta) uses nearest value

    Args:
        session: SQLAlchemy Session for database queries.
        max_delta: Maximum years to search for data (default 5).

    Example:
        >>> source = InterpolatingBEASource(session, max_delta=5)
        >>> ratio = source.get_sv_ratio("336111", 2023)  # May interpolate from 2022
    """

    # Default maximum years for interpolation
    DEFAULT_MAX_DELTA: int = 5

    def __init__(self, session: Session, max_delta: int = DEFAULT_MAX_DELTA) -> None:
        """Initialize with SQLAlchemy session and interpolation parameters.

        Args:
            session: SQLAlchemy session for database queries.
            max_delta: Maximum years to search for data. If no data exists
                within ±max_delta years, returns None.
        """
        self._session = session
        self._max_delta = max_delta
        # Cache for available years per industry to avoid repeated queries
        self._year_cache: dict[str, list[int]] = {}
        # Cache for national wages: (bea_industry_id, year) -> total_wages_usd
        self._wages_cache: dict[tuple[int, int], float] = {}
        # Whether the pre-aggregated wages table has been verified/created
        self._wages_table_ready: bool = False

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the surplus value to variable capital ratio (s/v) with interpolation.

        The s/v ratio is derived from BEA + QCEW data:
        s/v = (value_added - compensation) / compensation

        Where:
        - value_added = gross_output - intermediate_inputs (from BEA)
        - compensation = national QCEW wages for all NAICS in same BEA industry

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Target data year.

        Returns:
            Interpolated s/v ratio, or None if no data available within max_delta.
        """
        return self._get_interpolated_ratio(naics_code, year, "sv")

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the constant to variable capital ratio (c/v) with interpolation.

        The c/v ratio is derived from BEA + QCEW data:
        c/v = intermediate_inputs / compensation

        Where:
        - intermediate_inputs = from BEA national industry accounts (our "c")
        - compensation = national QCEW wages for all NAICS in same BEA industry

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Target data year.

        Returns:
            Interpolated c/v ratio, or None if no data available within max_delta.
        """
        return self._get_interpolated_ratio(naics_code, year, "cv")

    def _get_interpolated_ratio(self, naics_code: str, year: int, ratio_type: str) -> float | None:
        """Get ratio with temporal interpolation.

        Args:
            naics_code: NAICS code to look up.
            year: Target year.
            ratio_type: "sv" or "cv".

        Returns:
            Interpolated ratio or None.
        """
        # Get available years for this industry
        available_years = self._get_available_years(naics_code)
        if not available_years:
            return None

        # Check for exact match first
        if year in available_years:
            return self._query_ratio(naics_code, year, ratio_type)

        # Find nearest years within max_delta
        years_before = [y for y in available_years if y < year]
        years_after = [y for y in available_years if y > year]

        nearest_before = max(years_before) if years_before else None
        nearest_after = min(years_after) if years_after else None

        # Check if we're within max_delta
        before_in_range = nearest_before is not None and (year - nearest_before <= self._max_delta)
        after_in_range = nearest_after is not None and (nearest_after - year <= self._max_delta)

        if before_in_range and after_in_range:
            # Type narrowing: we know both are not None due to the checks above
            assert nearest_before is not None
            assert nearest_after is not None

            # Interpolate between two years
            ratio_before = self._query_ratio(naics_code, nearest_before, ratio_type)
            ratio_after = self._query_ratio(naics_code, nearest_after, ratio_type)

            if ratio_before is not None and ratio_after is not None:
                # Linear interpolation
                weight = (year - nearest_before) / (nearest_after - nearest_before)
                return ratio_before + weight * (ratio_after - ratio_before)
            elif ratio_before is not None:
                return ratio_before
            elif ratio_after is not None:
                return ratio_after
            else:
                return None

        elif before_in_range and nearest_before is not None:
            # Extrapolate from earlier year (use nearest value)
            return self._query_ratio(naics_code, nearest_before, ratio_type)

        elif after_in_range and nearest_after is not None:
            # Extrapolate from later year (use nearest value)
            return self._query_ratio(naics_code, nearest_after, ratio_type)

        else:
            # No data within max_delta
            return None

    def _get_available_years(self, naics_code: str) -> list[int]:
        """Get list of available years for a NAICS code.

        Joins through dim_industry to resolve naics_code -> industry_id,
        then through bridge_naics_bea to find matching BEA industries.

        Args:
            naics_code: NAICS code to look up.

        Returns:
            Sorted list of years with data.
        """
        if naics_code in self._year_cache:
            return self._year_cache[naics_code]

        query = """
            SELECT DISTINCT dt.year
            FROM fact_bea_national_industry f
            JOIN bridge_naics_bea bnb ON f.bea_industry_id = bnb.bea_industry_id
            JOIN dim_industry di ON bnb.industry_id = di.industry_id
            JOIN dim_time dt ON f.time_id = dt.time_id
            WHERE di.naics_code = :naics_code
              AND dt.is_annual = 1
            ORDER BY dt.year
        """

        result = self._session.execute(
            __import__("sqlalchemy").text(query),
            {"naics_code": naics_code},
        )

        years = [int(row[0]) for row in result]
        self._year_cache[naics_code] = years
        return years

    def _query_ratio(self, naics_code: str, year: int, ratio_type: str) -> float | None:
        """Query BEA ratio for a specific NAICS code and year.

        Two-step approach:
        1. Get BEA industry data (GO, II, VA) for the NAICS code
        2. Get national QCEW wages for ALL NAICS in the same BEA industry
           (ensures BEA numerator and QCEW denominator at same aggregation level)

        Args:
            naics_code: NAICS code to look up.
            year: Specific year to query.
            ratio_type: "sv" or "cv".

        Returns:
            Computed ratio or None.
        """
        # Step 1: Get BEA industry data for this NAICS code
        bea_query = """
            SELECT
                f.bea_industry_id,
                f.gross_output_millions,
                f.intermediate_inputs_millions,
                f.value_added_millions
            FROM fact_bea_national_industry f
            JOIN bridge_naics_bea bnb ON f.bea_industry_id = bnb.bea_industry_id
            JOIN dim_industry di ON bnb.industry_id = di.industry_id
            JOIN dim_time dt ON f.time_id = dt.time_id
            WHERE di.naics_code = :naics_code
              AND dt.year = :year
              AND dt.is_annual = 1
        """

        result = self._session.execute(
            __import__("sqlalchemy").text(bea_query),
            {"naics_code": naics_code, "year": year},
        )

        row = result.fetchone()
        if row is None:
            return None

        bea_industry_id_raw = row[0]
        go_raw = row[1]
        ii_raw = row[2]
        va_raw = row[3]

        if bea_industry_id_raw is None or go_raw is None or ii_raw is None or va_raw is None:
            return None

        bea_industry_id: int = int(bea_industry_id_raw)
        intermediate_inputs_m: float = float(ii_raw)
        value_added_m: float = float(va_raw)

        # Step 2: Get national QCEW wages for ALL NAICS in this BEA industry
        national_wages = self._query_national_wages(bea_industry_id, year)
        if national_wages is None or national_wages <= 0:
            return None

        # Convert wages from dollars to millions for consistent units
        compensation_m: float = national_wages / 1e6

        if ratio_type == "sv":
            # s/v = (value_added - compensation) / compensation
            surplus_m = value_added_m - compensation_m
            if surplus_m < 0:
                return 0.0
            return surplus_m / compensation_m

        elif ratio_type == "cv":
            # c/v = intermediate_inputs / compensation
            return intermediate_inputs_m / compensation_m

        return None

    def _query_national_wages(self, bea_industry_id: int, year: int) -> float | None:
        """Get total national QCEW wages for all NAICS codes in a BEA industry.

        Uses a pre-aggregated cache table to avoid scanning the 43M-row
        fact_qcew_annual table at query time. The cache table is created
        on first use and persists in the SQLite database.

        Args:
            bea_industry_id: BEA industry foreign key.
            year: Data year.

        Returns:
            Total national wages in dollars, or None if unavailable.
        """
        cache_key = (bea_industry_id, year)
        if cache_key in self._wages_cache:
            return self._wages_cache[cache_key]

        # Ensure the pre-aggregated table exists
        self._ensure_wages_aggregate_table()

        wages_query = """
            SELECT total_wages_usd
            FROM _cache_national_wages_bea
            WHERE bea_industry_id = :bea_industry_id
              AND year = :year
        """

        result = self._session.execute(
            __import__("sqlalchemy").text(wages_query),
            {"bea_industry_id": bea_industry_id, "year": year},
        )

        row = result.fetchone()
        if row is None or row[0] is None:
            self._wages_cache[cache_key] = 0.0
            return None

        total_wages: float = float(row[0])
        self._wages_cache[cache_key] = total_wages
        return total_wages if total_wages > 0 else None

    def _ensure_wages_aggregate_table(self) -> None:
        """Create the pre-aggregated national wages table if it doesn't exist.

        Collapses ~43M fact_qcew_annual rows into ~800 summary rows grouped
        by (bea_industry_id, year). Uses indexed per-industry lookups to avoid
        full table scans on the large QCEW table. One-time cost ~80s on first
        run, then all subsequent queries are instant.
        """
        if self._wages_table_ready:
            return

        sa = __import__("sqlalchemy")

        # Check if table already exists
        check = self._session.execute(
            sa.text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='_cache_national_wages_bea'"
            )
        )
        if check.fetchone() is not None:
            self._wages_table_ready = True
            return

        logger.info("Building national wages aggregate table (one-time, ~80s)...")

        self._build_wages_table_indexed()
        self._wages_table_ready = True

    def _build_wages_table_indexed(self) -> None:
        """Build aggregate table using indexed per-industry lookups.

        Strategy: instead of one massive JOIN over 43M rows, we:
        1. Load the 466-row bridge table into Python
        2. Load annual time_ids (~35 rows) into Python
        3. Execute ~16K small indexed queries (fast with idx_qcew_industry_time)
        4. Aggregate industry -> bea_industry in Python
        5. Write ~800 result rows into a persistent cache table
        """
        sa = __import__("sqlalchemy")
        import time as _time

        t0 = _time.perf_counter()

        # Load dimension tables (instant)
        bridge_rows = self._session.execute(
            sa.text("SELECT industry_id, bea_industry_id FROM bridge_naics_bea")
        ).fetchall()
        ind_to_bea: dict[int, int] = {int(r[0]): int(r[1]) for r in bridge_rows}
        industry_ids = list(ind_to_bea.keys())

        time_rows = self._session.execute(
            sa.text("SELECT time_id, year FROM dim_time WHERE is_annual = 1")
        ).fetchall()

        # Aggregate per (industry_id, time_id) using index
        result: dict[tuple[int, int], float] = {}
        wage_query = sa.text(
            "SELECT SUM(total_wages_usd) FROM fact_qcew_annual "
            "WHERE industry_id = :iid AND time_id = :tid "
            "AND total_wages_usd IS NOT NULL"
        )

        max_years = len(time_rows)
        for year_idx, (tid, year) in enumerate(time_rows):
            for ind_id in industry_ids:
                row = self._session.execute(wage_query, {"iid": ind_id, "tid": int(tid)}).fetchone()
                if row and row[0]:
                    bea_id = ind_to_bea[ind_id]
                    key = (bea_id, int(year))
                    result[key] = result.get(key, 0.0) + float(row[0])

            if (year_idx + 1) % 5 == 0 or year_idx == max_years - 1:
                elapsed = _time.perf_counter() - t0
                logger.info(
                    "  Aggregating year %d/%d (%.0fs elapsed, %d entries)...",
                    year_idx + 1,
                    max_years,
                    elapsed,
                    len(result),
                )

        # Create and populate the cache table
        self._session.execute(
            sa.text(
                "CREATE TABLE _cache_national_wages_bea ("
                "  bea_industry_id INTEGER NOT NULL,"
                "  year INTEGER NOT NULL,"
                "  total_wages_usd REAL NOT NULL,"
                "  PRIMARY KEY (bea_industry_id, year)"
                ")"
            )
        )

        insert_stmt = sa.text(
            "INSERT INTO _cache_national_wages_bea "
            "(bea_industry_id, year, total_wages_usd) "
            "VALUES (:bea_id, :year, :wages)"
        )
        for (bea_id, year), wages in result.items():
            self._session.execute(insert_stmt, {"bea_id": bea_id, "year": year, "wages": wages})

        self._session.commit()
        elapsed = _time.perf_counter() - t0
        logger.info("Aggregate table ready: %d entries in %.0fs", len(result), elapsed)


__all__ = [
    "BEADataSource",
    "InterpolatingBEASource",
    "QCEWDataSource",
    "SQLiteQCEWSource",
]
