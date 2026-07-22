"""Source-level pins for migration 0038 (T5 Unit U2's ``v_national_trend``).

No database needed — pure text assertions on the migration file itself,
mirroring ``test_no_stored_aggregate_rows.py``'s scan idiom. The
database-backed proof (the view actually creates and its ``LAG`` windows
compute correctly against real rows) lives in
``tests/integration/persistence/test_tick_summary_trend_view.py`` per the
test-estate law (ADR074: Postgres-connected tests are integration tier).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "babylon"
    / "persistence"
    / "migrations"
    / "0038_tick_summary_trend.sql"
)


@pytest.fixture
def sql() -> str:
    return _MIGRATION.read_text(encoding="utf8")


@pytest.fixture
def view_body(sql: str) -> str:
    """Just the ``CREATE VIEW ... FROM tick_summary;`` statement — excludes
    the file's explanatory header comments (which legitimately NAME the
    permanently-NULL columns while explaining why they are excluded)."""
    start = sql.index("CREATE VIEW v_national_trend AS")
    end = sql.index("FROM tick_summary;", start) + len("FROM tick_summary;")
    return sql[start:end]


class TestGuardedOnTickSummaryPresence:
    """``tick_summary`` is a spec-037 bootstrap table, not migration-created —
    a migrations-only database must not hard-fail here (0033's guard idiom)."""

    def test_guarded_on_to_regclass(self, sql: str) -> None:
        assert "to_regclass('tick_summary') IS NOT NULL" in sql

    def test_view_ddl_lives_inside_the_guard(self, sql: str) -> None:
        guard_start = sql.index("to_regclass('tick_summary') IS NOT NULL")
        end_marker = sql.index("END", guard_start)
        guarded_body = sql[guard_start:end_marker]
        assert "DROP VIEW IF EXISTS v_national_trend" in guarded_body
        assert "CREATE VIEW v_national_trend AS" in guarded_body


class TestViewShape:
    """``DROP VIEW IF EXISTS`` + ``CREATE VIEW`` — never ``CREATE OR REPLACE``
    (which forbids changing a view's declared column set, the 0030 idiom)."""

    def test_drop_then_create_never_create_or_replace(self, sql: str) -> None:
        assert "DROP VIEW IF EXISTS v_national_trend" in sql
        assert "CREATE VIEW v_national_trend AS" in sql
        assert "CREATE OR REPLACE VIEW v_national_trend" not in sql

    def test_reads_from_tick_summary(self, sql: str) -> None:
        assert "FROM tick_summary" in sql

    def test_one_view_only(self, sql: str) -> None:
        """Kept to ONE view — tick_summary has no per-scope breakdown to
        window separately (unlike the county/state/national hex aggregates)."""
        assert sql.count("CREATE VIEW") == 1


class TestLagWindows:
    """Deterministic per-session, per-tick ``LAG`` deltas — the DeclaredView
    ``order_by`` contract (Constitution III.13) lives on the registry entry,
    not inside the view itself (matching 0030's own views)."""

    def test_four_lag_windows_partitioned_and_ordered_correctly(self, view_body: str) -> None:
        assert view_body.count("LAG(") == 4
        assert view_body.count("PARTITION BY session_id ORDER BY tick") == 4

    def test_windows_cover_imperial_rent_price_and_market_corrections(self, view_body: str) -> None:
        for column in ("imperial_rent", "price_log", "fictitious_log", "market_corrections"):
            assert column in view_body, column
        for delta in (
            "imperial_rent_delta",
            "price_log_delta",
            "fictitious_log_delta",
            "market_corrections_delta",
        ):
            assert delta in view_body, delta

    def test_never_windows_the_permanently_null_columns(self, view_body: str) -> None:
        """A trend of a column no engine system computes yet is not a signal."""
        for column in (
            "total_c",
            "total_v",
            "total_s",
            "exploitation_rate",
            "profit_rate",
            "co_optive_edge_count",
            "conservation_check",
        ):
            assert column not in view_body, column
