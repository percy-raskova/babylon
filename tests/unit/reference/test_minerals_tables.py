"""Behavioral contracts for the Program 22 Wave-1 minerals fills (ADR075 1c).

Pins the healthy post-fill state of the five USGS MCS surfaces loaded by
``python -m babylon_data.materials`` on 2026-07-17: the salient EAV refresh
(2024 gap closed), the T1/T3/Fig3 aggregate tables, and the authoritative
T4 criticality re-derivation (the legacy name-keyed dict had flagged 2/85).

Requires the reference DB; view contracts skip on the view-less ci-data
subset, exactly like ``test_marxian_views.py``.
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
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'view' AND name = ?", (name,)
    ).fetchone()
    if row is None:
        pytest.skip(f"{name} absent — subset DB ships tables only")


class TestObservationRefresh:
    def test_refresh_landed_through_2024(self, conn: sqlite3.Connection) -> None:
        count, low, high = conn.execute(
            "SELECT COUNT(*), MIN(t.year), MAX(t.year) FROM fact_commodity_observation o"
            " JOIN dim_time t ON o.time_id = t.time_id"
        ).fetchone()
        assert count >= 4_700  # 4,735 on 2026-07-17 (was 3,788 through 2023)
        assert low == 2020
        assert high == 2024


class TestCriticality:
    def test_thirty_of_85_commodities_flagged_from_t4(self, conn: sqlite3.Connection) -> None:
        total, critical = conn.execute(
            "SELECT COUNT(*), SUM(is_critical) FROM dim_commodity"
        ).fetchone()
        assert total == 85
        assert critical == 30  # 48 T4 minerals folded onto 30 family rows

    def test_rare_earths_family_row_carries_member_applications(
        self, conn: sqlite3.Connection
    ) -> None:
        is_critical, applications = conn.execute(
            "SELECT is_critical, primary_applications FROM dim_commodity WHERE name = 'Rare Earths'"
        ).fetchone()
        assert is_critical == 1
        assert "Neodymium" in applications  # element-prefixed member application


class TestAggregateTables:
    def test_mineral_production_five_years_three_types(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM fact_mineral_production").fetchone()[0]
        assert count == 15
        metals_2024 = conn.execute(
            "SELECT p.value_millions FROM fact_mineral_production p"
            " JOIN dim_time t ON p.time_id = t.time_id"
            " WHERE p.production_type = 'metals' AND t.year = 2024"
        ).fetchone()
        assert metals_2024 is not None
        assert float(metals_2024[0]) > 0

    def test_mineral_employment_sectors_and_honest_null_earnings(
        self, conn: sqlite3.Connection
    ) -> None:
        count = conn.execute("SELECT COUNT(*) FROM fact_mineral_employment").fetchone()[0]
        assert count == 25
        sectors = {
            row[0] for row in conn.execute("SELECT DISTINCT sector FROM fact_mineral_employment")
        }
        assert sectors == {
            "all_coal",
            "all_nonfuel",
            "chemicals",
            "stone_clay_glass",
            "primary_metal",
        }
        chemicals_earnings = conn.execute(
            "SELECT COUNT(*) FROM fact_mineral_employment"
            " WHERE sector = 'chemicals' AND avg_weekly_earnings_usd IS NOT NULL"
        ).fetchone()[0]
        assert chemicals_earnings == 0  # T1 has no chemicals earnings series

    def test_state_minerals_fifty_states(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM fact_state_minerals").fetchone()[0]
        assert count == 50
        alaska = conn.execute(
            "SELECT f.rank FROM fact_state_minerals f"
            " JOIN dim_state s ON f.state_id = s.state_id WHERE s.state_name = 'Alaska'"
        ).fetchone()
        assert alaska == (6,)

    def test_import_sources_loaded(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM dim_import_source").fetchone()[0]
        assert count == 43
        australia = conn.execute(
            "SELECT commodity_count FROM dim_import_source WHERE country = 'Australia'"
        ).fetchone()
        assert australia == (6,)


class TestCriticalMaterialsView:
    def test_view_is_alive(self, conn: sqlite3.Connection) -> None:
        _require_view(conn, "view_critical_materials")
        count = conn.execute("SELECT COUNT(*) FROM view_critical_materials").fetchone()[0]
        assert count >= 1_800  # 1,895 on 2026-07-17 (was 0-adjacent: 2 criticals)
