"""Behavioral contracts for the revived Marxian views (ADR075 ruling 1 fills).

Until 2026-07-17 ``view_surplus_value`` and ``view_imperial_rent`` selected
from a permanently-empty ``fact_productivity_annual`` (the pathology that
seeded the Data Constitution), and ``view_rent_crisis`` was a cross-time/
cross-race Cartesian explosion. These contracts pin the healthy state:

- the productivity fill landed (17,336 rows via
  ``tools/load_productivity_annual.py``, BLS detailed industries 1988-2024);
- both value views compute real rates from it;
- the repaired rent-crisis view returns per-(year, race) slices with real
  (non-integer-division) ratios.

Requires the reference DB. View contracts skip on the ci-data subset (the
subset generator ships tables only — view rows there are advisory, per the
catalog sentinel design).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from babylon.sentinels.coverage.db_probe import _database_path

pytestmark = [
    pytest.mark.unit,
    pytest.mark.requires_reference_db,
    pytest.mark.skipif(
        not _database_path().is_file(),
        reason="reference DB absent (fetch-reference-db not run / drive unmounted)",
    ),
]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(f"file:{_database_path()}?mode=ro", uri=True)
    yield connection
    connection.close()


def _require_view(conn: sqlite3.Connection, name: str) -> None:
    """Skip (not fail) when running against the view-less ci-data subset."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'view' AND name = ?", (name,)
    ).fetchone()
    if row is None:
        pytest.skip(f"{name} absent — subset DB ships tables only")


class TestProductivityFill:
    def test_fill_landed_at_expected_scale(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM fact_productivity_annual").fetchone()[0]
        assert count >= 17_000, "the 2026-07-17 fill inserted 17,336 (industry, year) rows"

    def test_fill_spans_the_bls_series(self, conn: sqlite3.Connection) -> None:
        low, high = conn.execute(
            "SELECT MIN(t.year), MAX(t.year) FROM fact_productivity_annual p"
            " JOIN dim_time t ON p.time_id = t.time_id"
        ).fetchone()
        assert low <= 1988
        assert high >= 2024


class TestSurplusValueView:
    def test_view_is_alive(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_surplus_value")
        count = conn.execute("SELECT COUNT(*) FROM view_surplus_value").fetchone()[0]
        assert count >= 17_000

    def test_mining_2023_rate_of_exploitation(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_surplus_value")
        rate = conn.execute(
            "SELECT ROUND(rate_of_exploitation, 3) FROM view_surplus_value"
            " WHERE naics_code = '21' AND year = 2023"
        ).fetchone()[0]
        assert rate == 5.223  # s/v from BLS: output 500B-class vs compensation


class TestImperialRentView:
    def test_view_is_alive(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_imperial_rent")
        count = conn.execute("SELECT COUNT(*) FROM view_imperial_rent").fetchone()[0]
        assert count >= 17_000

    def test_mining_2023_labor_aristocracy_ratio(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_imperial_rent")
        ratio = conn.execute(
            "SELECT ROUND(labor_aristocracy_ratio, 3) FROM view_imperial_rent"
            " WHERE naics_code = '21' AND year = 2023"
        ).fetchone()[0]
        assert ratio == 0.161  # W_c / V_c for mining — deep below 1


class TestFundamentalTheoremCalibration:
    """U2 calibration check (Constitution III.12 redundant verification):

    the sim-side Fundamental Theorem formulas
    (``babylon.formulas.fundamental_theorem``,
    ``babylon.domain.dialectics.instances.value_form.compute_fundamental_theorem``)
    must reproduce ``view_imperial_rent``'s SQL-computed numbers exactly when
    fed the SAME (wages_core, value_produced) inputs — two independent
    derivations of one theorem must not disagree.
    """

    def test_mining_2023_reproduces_the_view_exactly(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_imperial_rent")
        wages_core, value_produced, imperial_rent, ratio = conn.execute(
            "SELECT wages_core_millions, value_produced_millions,"
            " imperial_rent_millions, labor_aristocracy_ratio FROM view_imperial_rent"
            " WHERE naics_code = '21' AND year = 2023"
        ).fetchone()

        from babylon.formulas.fundamental_theorem import (
            calculate_imperial_rent_gap,
            calculate_labor_aristocracy_ratio,
            is_labor_aristocracy,
        )

        assert calculate_imperial_rent_gap(wages_core, value_produced) == pytest.approx(
            imperial_rent
        )
        assert calculate_labor_aristocracy_ratio(wages_core, value_produced) == pytest.approx(ratio)
        assert is_labor_aristocracy(wages_core, value_produced) is (ratio > 1.0)

    def test_compute_fundamental_theorem_reproduces_the_view(
        self, conn: sqlite3.Connection
    ) -> None:
        _require_view(conn, "view_imperial_rent")
        wages_core, value_produced, imperial_rent, ratio = conn.execute(
            "SELECT wages_core_millions, value_produced_millions,"
            " imperial_rent_millions, labor_aristocracy_ratio FROM view_imperial_rent"
            " WHERE naics_code = '21' AND year = 2023"
        ).fetchone()

        from babylon.domain.dialectics.instances.value_form import compute_fundamental_theorem

        (reading,) = compute_fundamental_theorem((("mining_21_2023", wages_core, value_produced),))
        assert reading.phi_absolute == pytest.approx(imperial_rent)
        assert reading.labor_aristocracy_ratio == pytest.approx(ratio)
        assert reading.is_labor_aristocracy is (ratio > 1.0)


class TestRentCrisisView:
    def test_repaired_definition_is_installed(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_rent_crisis")
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = 'view_rent_crisis'"
        ).fetchone()[0]
        assert "fr.time_id = fi.time_id" in sql, "full-key join (repair 2026-07-17)"
        assert "* 12.0" in sql, "real division (integer-affinity rent truncated to 0)"

    def test_wayne_county_is_per_slice_not_cartesian(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_rent_crisis")
        count = conn.execute(
            "SELECT COUNT(*) FROM view_rent_crisis WHERE fips = '26163'"
        ).fetchone()[0]
        assert count == 14  # 14 ACS years x the 1 race present across all three facts

    def test_wayne_county_2023_totals(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_rent_crisis")
        row = conn.execute(
            "SELECT median_rent_usd, median_income_usd,"
            " ROUND(annual_rent_to_income_ratio, 3), total_renter_households"
            " FROM view_rent_crisis WHERE fips = '26163' AND year = 2023 AND race_code = 'T'"
        ).fetchone()
        assert row == (1087, 59521, 0.219, 246326)
