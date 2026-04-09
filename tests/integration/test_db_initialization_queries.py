"""Integration tests for database initialization queries.

Validates that the reference 3NF SQLite database contains sufficient data
to hydrate the game's starting state for Michigan's 83 counties. Each test
class corresponds to a query from the initialization artifact, and every
test that can't be written reveals a schema or data gap.

These tests are *read-only* against ``data/sqlite/marxist-data-3NF.sqlite``.
They are skipped gracefully when the database file is missing (CI without
the data artifact).

Markers:
    integration: I/O-bound database tests.
    ledger: Economic/political state validation.
    empirical: Requires the real reference dataset.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DB_CANDIDATES = [
    Path("data/sqlite/marxist-data-3NF.sqlite"),
    Path("data/babylon.db"),
]

MICHIGAN_ABBREV = "MI"
MICHIGAN_COUNTY_COUNT = 83  # Real counties (FIPS 26001–26165)
# Pseudo-county 26999 exists for statewide unallocated data; we expect 84 total rows.
MICHIGAN_TOTAL_ROWS = 84

# Wayne / Oakland / Macomb — the Detroit tri-county core
WAYNE_FIPS = "26163"
OAKLAND_FIPS = "26125"
MACOMB_FIPS = "26099"

# The latest year where QCEW, BEA, Census, and FRED all overlap for Michigan.
# BEA county GDP maxes at 2023; QCEW goes to 2024; Census income to 2023.
HYDRATION_YEAR = 2023

# Minimum time-series depth required for TRPF trending (years).
MIN_TRPF_YEARS = 10

# Income bracket IDs for the bourgeois proxy (>=$150k).
# bracket_id 15 = "$150,000 to $199,999", 16 = "$200,000 or more"
HIGH_INCOME_BRACKET_IDS = (15, 16)

# FIRE sector codes (Finance/Insurance = 52, Real Estate = 53)
FIRE_SECTOR_CODES = ("52", "53")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _find_db() -> Path | None:
    for candidate in _DB_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


@pytest.fixture(scope="module")
def db() -> sqlite3.Connection:
    """Read-only connection to the 3NF reference database.

    Skips the entire module when the database file is absent.
    """
    db_path = _find_db()
    if db_path is None:
        pytest.skip(f"Reference database not found; searched {[str(p) for p in _DB_CANDIDATES]}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def michigan_state_id(db: sqlite3.Connection) -> int:
    """Resolve Michigan's surrogate state_id once per module."""
    row = db.execute(
        "SELECT state_id FROM dim_state WHERE state_abbrev = ?",
        (MICHIGAN_ABBREV,),
    ).fetchone()
    assert row is not None, "dim_state missing Michigan row"
    return row["state_id"]


@pytest.fixture(scope="module")
def hydration_time_id(db: sqlite3.Connection) -> int:
    """Resolve the annual time_id for the hydration year."""
    row = db.execute(
        "SELECT time_id FROM dim_time WHERE year = ? AND is_annual = 1",
        (HYDRATION_YEAR,),
    ).fetchone()
    assert row is not None, f"dim_time missing annual row for {HYDRATION_YEAR}"
    return row["time_id"]


# ===========================================================================
# 1. Base Topology (Territories)
# ===========================================================================


@pytest.mark.integration
@pytest.mark.ledger
@pytest.mark.empirical
class TestBaseTopology:
    """Query 1: Michigan county geography hydration."""

    def test_michigan_has_all_83_counties_plus_statewide(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """dim_county contains 83 real Michigan counties + 1 statewide pseudo."""
        rows = db.execute(
            "SELECT count(*) AS n FROM dim_county WHERE state_id = ?",
            (michigan_state_id,),
        ).fetchone()
        assert rows is not None
        assert rows["n"] == MICHIGAN_TOTAL_ROWS

    def test_no_duplicate_fips(self, db: sqlite3.Connection, michigan_state_id: int) -> None:
        """Each county has a unique 5-digit FIPS — no duplicates."""
        rows = db.execute(
            """
            SELECT fips, count(*) AS n
            FROM dim_county WHERE state_id = ?
            GROUP BY fips HAVING n > 1
            """,
            (michigan_state_id,),
        ).fetchall()
        assert len(rows) == 0, f"Duplicate FIPS codes: {[dict(r) for r in rows]}"

    def test_geometry_exists_for_real_counties(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """Counties with real FIPS (not 26999) have centroid geometry."""
        rows = db.execute(
            """
            SELECT c.fips, cg.centroid_lat, cg.centroid_lon
            FROM dim_county c
            LEFT JOIN dim_county_geometry cg ON c.county_id = cg.county_id
            WHERE c.state_id = ? AND c.fips != '26999'
            """,
            (michigan_state_id,),
        ).fetchall()
        missing = [dict(r) for r in rows if r["centroid_lat"] is None]
        assert len(missing) == 0, (
            f"{len(missing)} Michigan counties missing geometry: "
            f"{[m['fips'] for m in missing[:5]]}..."
        )

    def test_tri_county_core_present(self, db: sqlite3.Connection) -> None:
        """Wayne, Oakland, and Macomb counties are present."""
        for fips in (WAYNE_FIPS, OAKLAND_FIPS, MACOMB_FIPS):
            row = db.execute(
                "SELECT county_name FROM dim_county WHERE fips = ?", (fips,)
            ).fetchone()
            assert row is not None, f"FIPS {fips} missing from dim_county"


# ===========================================================================
# 2. Economic Base (QCEW)
# ===========================================================================


@pytest.mark.integration
@pytest.mark.ledger
@pytest.mark.empirical
class TestEconomicBase:
    """Query 2: QCEW employment/wages hydration for Michigan."""

    def test_qcew_has_michigan_data_for_hydration_year(
        self, db: sqlite3.Connection, michigan_state_id: int, hydration_time_id: int
    ) -> None:
        """fact_qcew_annual contains Michigan rows for the hydration year."""
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_qcew_annual q
            JOIN dim_county c ON q.county_id = c.county_id
            WHERE c.state_id = ? AND q.time_id = ?
            """,
            (michigan_state_id, hydration_time_id),
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, f"No QCEW data for Michigan in {HYDRATION_YEAR}"

    def test_qcew_covers_majority_of_counties(
        self, db: sqlite3.Connection, michigan_state_id: int, hydration_time_id: int
    ) -> None:
        """QCEW data should cover at least 80 of 83 real counties."""
        row = db.execute(
            """
            SELECT count(DISTINCT c.fips) AS n
            FROM fact_qcew_annual q
            JOIN dim_county c ON q.county_id = c.county_id
            WHERE c.state_id = ? AND q.time_id = ? AND c.fips != '26999'
            """,
            (michigan_state_id, hydration_time_id),
        ).fetchone()
        assert row is not None
        assert row["n"] >= 80, f"Only {row['n']} counties have QCEW data; expected ≥80"

    def test_qcew_time_series_depth_for_trpf(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """QCEW must span at least MIN_TRPF_YEARS for trend analysis."""
        rows = db.execute(
            """
            SELECT DISTINCT t.year
            FROM fact_qcew_annual q
            JOIN dim_county c ON q.county_id = c.county_id
            JOIN dim_time t ON q.time_id = t.time_id
            WHERE c.state_id = ?
            ORDER BY t.year
            """,
            (michigan_state_id,),
        ).fetchall()
        years = [r["year"] for r in rows]
        assert len(years) >= MIN_TRPF_YEARS, (
            f"Only {len(years)} QCEW years; need ≥{MIN_TRPF_YEARS} for TRPF trending"
        )

    def test_qcew_wages_are_positive_for_wayne_county(
        self, db: sqlite3.Connection, hydration_time_id: int
    ) -> None:
        """Wayne County (Detroit core) should have non-trivial wages."""
        row = db.execute(
            """
            SELECT SUM(q.total_wages_usd) AS total_wages
            FROM fact_qcew_annual q
            JOIN dim_county c ON q.county_id = c.county_id
            WHERE c.fips = ? AND q.time_id = ?
            """,
            (WAYNE_FIPS, hydration_time_id),
        ).fetchone()
        assert row is not None
        assert row["total_wages"] is not None
        assert row["total_wages"] > 0, "Wayne County wages should be positive"


# ===========================================================================
# 3. Surplus Value & County GDP (BEA)
# ===========================================================================


@pytest.mark.integration
@pytest.mark.ledger
@pytest.mark.empirical
class TestSurplusValue:
    """Query 3: BEA county GDP hydration for exploitation-rate derivation."""

    def test_bea_county_gdp_has_michigan_data(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """fact_bea_county_gdp contains Michigan rows for the hydration year."""
        # BEA maxes at 2023; use that directly.
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_bea_county_gdp g
            JOIN dim_county c ON g.county_id = c.county_id
            JOIN dim_time t ON g.time_id = t.time_id
            WHERE c.state_id = ? AND t.year = ?
            """,
            (michigan_state_id, HYDRATION_YEAR),
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, f"No BEA county GDP for Michigan in {HYDRATION_YEAR}"

    def test_bea_time_series_depth_for_trpf(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """BEA data must also span enough years for TRPF trending."""
        rows = db.execute(
            """
            SELECT DISTINCT t.year
            FROM fact_bea_county_gdp g
            JOIN dim_county c ON g.county_id = c.county_id
            JOIN dim_time t ON g.time_id = t.time_id
            WHERE c.state_id = ?
            ORDER BY t.year
            """,
            (michigan_state_id,),
        ).fetchall()
        years = [r["year"] for r in rows]
        assert len(years) >= MIN_TRPF_YEARS, (
            f"Only {len(years)} BEA years; need ≥{MIN_TRPF_YEARS} for TRPF"
        )

    def test_exploitation_rate_is_derivable_for_wayne(self, db: sqlite3.Connection) -> None:
        """We can compute local s = GDP − Wages for Wayne County.

        This is the Imputation 2 smoke test: if both tables have data
        for the same county/year, the surplus-value query is feasible.
        """
        row = db.execute(
            """
            SELECT
                SUM(g.gdp_millions) AS gdp,
                SUM(q.total_wages_usd) / 1000000.0 AS wages
            FROM fact_bea_county_gdp g
            JOIN dim_county c ON g.county_id = c.county_id
            JOIN dim_time t_g ON g.time_id = t_g.time_id
            JOIN fact_qcew_annual q ON q.county_id = c.county_id
            JOIN dim_time t_q ON q.time_id = t_q.time_id
            WHERE c.fips = ?
              AND t_g.year = ?
              AND t_q.year = ?
              AND t_g.is_annual = 1
              AND t_q.is_annual = 1
            """,
            (WAYNE_FIPS, HYDRATION_YEAR, HYDRATION_YEAR),
        ).fetchone()
        assert row is not None
        assert row["gdp"] is not None, "BEA GDP missing for Wayne County"
        assert row["wages"] is not None, "QCEW wages missing for Wayne County"
        # Both should be non-trivial
        assert row["gdp"] > 0
        assert row["wages"] > 0


# ===========================================================================
# 4. National Wealth Distribution (FRED)
# ===========================================================================


@pytest.mark.integration
@pytest.mark.ledger
@pytest.mark.empirical
class TestWealthDistribution:
    """Imputation 1: FRED wealth data for county-level imputation."""

    def test_fred_wealth_classes_have_babylon_mapping(self, db: sqlite3.Connection) -> None:
        """All wealth classes map to a Babylon class position."""
        rows = db.execute("SELECT percentile_code, babylon_class FROM dim_wealth_class").fetchall()
        assert len(rows) >= 4, "Expected at least 4 wealth classes"
        for r in rows:
            assert r["babylon_class"] is not None, (
                f"Wealth class {r['percentile_code']} has no babylon_class mapping"
            )

    def test_fred_wealth_levels_have_data(self, db: sqlite3.Connection) -> None:
        """fact_fred_wealth_levels contains data for the hydration year."""
        # FRED wealth is quarterly — check for any 2023 data
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_fred_wealth_levels f
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year = ?
            """,
            (HYDRATION_YEAR,),
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, f"No FRED wealth data for {HYDRATION_YEAR}"

    def test_fred_wealth_time_series_depth(self, db: sqlite3.Connection) -> None:
        """FRED wealth data spans enough years for historical context."""
        rows = db.execute(
            """
            SELECT DISTINCT t.year
            FROM fact_fred_wealth_levels f
            JOIN dim_time t ON f.time_id = t.time_id
            ORDER BY t.year
            """
        ).fetchall()
        years = [r["year"] for r in rows]
        assert len(years) >= MIN_TRPF_YEARS, (
            f"Only {len(years)} FRED wealth years; need ≥{MIN_TRPF_YEARS}"
        )

    def test_census_high_income_proxy_has_michigan_data(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """Census income brackets ≥$150k exist for Michigan counties.

        These are the proxy for spatializing national wealth (Imputation 1).
        """
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_census_income ci
            JOIN dim_county c ON ci.county_id = c.county_id
            JOIN dim_time t ON ci.time_id = t.time_id
            WHERE c.state_id = ?
              AND ci.bracket_id IN (?, ?)
              AND t.year = ?
            """,
            (michigan_state_id, *HIGH_INCOME_BRACKET_IDS, HYDRATION_YEAR),
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, f"No Census high-income bracket data for Michigan in {HYDRATION_YEAR}"


# ===========================================================================
# 5. Inter-County Tribute Edges (Institutional Ownership + FIRE hubs)
# ===========================================================================


@pytest.mark.integration
@pytest.mark.ledger
@pytest.mark.empirical
class TestTributeEdges:
    """Imputation 3: Data prerequisites for financial gravity model."""

    def test_institutional_ownership_exists_for_michigan(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """fact_census_institutional_ownership has Michigan data.

        Even if sparse, at least some rows should exist.
        """
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_census_institutional_ownership io
            JOIN dim_county c ON io.county_id = c.county_id
            WHERE c.state_id = ?
            """,
            (michigan_state_id,),
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, "No institutional ownership data for Michigan at all"

    @pytest.mark.xfail(
        reason=(
            "DATA GAP: absentee_owned column exists but is uniformly 0 across all "
            "6,570 rows. Census ACS does not directly provide absentee ownership "
            "breakdowns; this field requires a supplementary ETL from CoreLogic, "
            "ATTOM, or similar property-record sources. Tracked as a known gap for "
            "the Tribute edge imputation model."
        ),
        strict=True,
    )
    def test_institutional_ownership_has_absentee_field(self, db: sqlite3.Connection) -> None:
        """The absentee_owned column exists and has non-null data."""
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_census_institutional_ownership
            WHERE absentee_owned IS NOT NULL AND absentee_owned > 0
            """
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, "No non-zero absentee_owned values in dataset"

    def test_fire_sector_industries_exist(self, db: sqlite3.Connection) -> None:
        """dim_industry contains Finance (52) and Real Estate (53) sectors."""
        row = db.execute(
            """
            SELECT count(DISTINCT sector_code) AS n
            FROM dim_industry
            WHERE sector_code IN ('52', '53')
            """
        ).fetchone()
        assert row is not None
        assert row["n"] == 2, "Expected both FIRE sector codes (52, 53) in dim_industry"

    def test_qcew_has_location_quotient_for_fire(
        self, db: sqlite3.Connection, michigan_state_id: int, hydration_time_id: int
    ) -> None:
        """QCEW rows for FIRE sectors include lq_employment (location quotient).

        This is the gravitational proxy for identifying parasitic financial hubs.
        """
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_qcew_annual q
            JOIN dim_county c ON q.county_id = c.county_id
            JOIN dim_industry i ON q.industry_id = i.industry_id
            WHERE c.state_id = ?
              AND q.time_id = ?
              AND i.sector_code IN ('52', '53')
              AND q.lq_employment IS NOT NULL
            """,
            (michigan_state_id, hydration_time_id),
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, "No QCEW rows with lq_employment for FIRE sectors in Michigan"

    def test_lodes_commuter_flow_exists_for_michigan(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """fact_lodes_commuter_flow has Michigan inter-county labor flows.

        LODES provides the commuting graph that supplements the financial
        gravity model for edge construction.
        """
        row = db.execute(
            """
            SELECT count(*) AS n
            FROM fact_lodes_commuter_flow lf
            JOIN dim_county c ON lf.home_county_id = c.county_id
            WHERE c.state_id = ?
            """,
            (michigan_state_id,),
        ).fetchone()
        assert row is not None
        assert row["n"] > 0, "No LODES commuter flow data for Michigan"


# ===========================================================================
# 6. Cross-Source Overlap (Critical for Imputation Feasibility)
# ===========================================================================


@pytest.mark.integration
@pytest.mark.ledger
@pytest.mark.empirical
class TestCrossSourceOverlap:
    """Verify that different federal sources overlap in time and space.

    The imputation models (surplus value, wealth spatialization, tribute)
    all require joining across QCEW, BEA, Census, and FRED. If any source
    has a gap for the hydration year, the imputation query will silently
    return NULLs.
    """

    def test_qcew_and_bea_overlap_for_hydration_year(
        self, db: sqlite3.Connection, michigan_state_id: int
    ) -> None:
        """Both QCEW and BEA have data for the same county in the same year."""
        row = db.execute(
            """
            SELECT count(DISTINCT c.fips) AS n
            FROM dim_county c
            JOIN fact_qcew_annual q ON q.county_id = c.county_id
            JOIN dim_time tq ON q.time_id = tq.time_id
            JOIN fact_bea_county_gdp g ON g.county_id = c.county_id
            JOIN dim_time tg ON g.time_id = tg.time_id
            WHERE c.state_id = ?
              AND tq.year = ? AND tq.is_annual = 1
              AND tg.year = ? AND tg.is_annual = 1
            """,
            (michigan_state_id, HYDRATION_YEAR, HYDRATION_YEAR),
        ).fetchone()
        assert row is not None
        assert row["n"] >= 60, (
            f"Only {row['n']} counties have both QCEW and BEA data in "
            f"{HYDRATION_YEAR}; expected ≥60 for viable exploitation-rate derivation"
        )

    def test_dim_time_spans_full_range(self, db: sqlite3.Connection) -> None:
        """dim_time covers at least 1990–2024 for historical depth."""
        row = db.execute("SELECT MIN(year) AS lo, MAX(year) AS hi FROM dim_time").fetchone()
        assert row is not None
        assert row["lo"] <= 1995, f"dim_time starts at {row['lo']}; expected ≤1995"
        assert row["hi"] >= 2023, f"dim_time ends at {row['hi']}; expected ≥2023"

    def test_data_source_registry_has_major_agencies(self, db: sqlite3.Connection) -> None:
        """dim_data_source tracks the provenance of each federal dataset."""
        rows = db.execute("SELECT source_code FROM dim_data_source").fetchall()
        codes = {r["source_code"] for r in rows}
        # We don't assert exact codes, but at least some should be there
        assert len(codes) >= 3, (
            f"Only {len(codes)} data sources registered; "
            "expected provenance for QCEW, BEA, Census, FRED, etc."
        )
