"""Source-level pins for migration 0041 (M6 Task 41's trend widening).

Migration ``0041_trend_playability.sql`` re-declares ``v_national_trend``
to window the five LIVE playability columns migration 0035 added to
``tick_summary`` (written by ``build_tick_summary_kwargs``'s county-dedup
pass — genuinely computed, unlike the permanently-NULL c/v/s columns the
view's own rationale excludes) plus their five ``LAG`` deltas.

No database needed — pure text assertions on the migration file itself
(the ``test_tick_summary_trend_migration.py`` idiom for 0038, which this
file deliberately does NOT touch: 0038 is applied history, immutable).
The database-backed proof lives in
``tests/integration/persistence/test_tick_summary_trend_view.py`` per the
test-estate law (ADR074: Postgres-connected tests are integration tier).

NOTE the migration NUMBER is a recorded contract deviation: the M6
contract (pinned 2026-07-28, pre-P26-merge) allocated "0039", but P26
landed ``0039_domain_contracts.sql`` + ``0040_receipts_vocabulary.sql``
first — the runner globs ``00*.sql`` in sorted order, so the next free
slot is 0041 (maps contract §5-style deviation, recorded in the M6
contract §5).
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
    / "0041_trend_playability.sql"
)

#: The five live playability series 0035 added and this migration windows.
_PLAYABILITY_COLUMNS = (
    "crisis_pop_share",
    "bifurcation_score_mean",
    "wage_compression_mean",
    "capital_stock_total",
    "unemployment_rate_mean",
)


@pytest.fixture
def sql() -> str:
    return _MIGRATION.read_text(encoding="utf8")


@pytest.fixture
def view_body(sql: str) -> str:
    """Just the ``CREATE VIEW ... FROM tick_summary;`` statement."""
    start = sql.index("CREATE VIEW v_national_trend AS")
    end = sql.index("FROM tick_summary;", start) + len("FROM tick_summary;")
    return sql[start:end]


class TestGuardedOnTickSummaryPresence:
    """``tick_summary`` is a spec-037 bootstrap table, not migration-created —
    a migrations-only database must not hard-fail here (0038's guard idiom)."""

    def test_guarded_on_to_regclass(self, sql: str) -> None:
        assert "to_regclass('tick_summary') IS NOT NULL" in sql

    def test_view_ddl_lives_inside_the_guard(self, sql: str) -> None:
        guard_start = sql.index("to_regclass('tick_summary') IS NOT NULL")
        end_marker = sql.index("END", guard_start)
        guarded_body = sql[guard_start:end_marker]
        assert "DROP VIEW IF EXISTS v_national_trend" in guarded_body
        assert "CREATE VIEW v_national_trend AS" in guarded_body


class TestViewShape:
    """DROP+CREATE, never CREATE OR REPLACE (Postgres forbids OR REPLACE
    from changing a view's declared column set — the whole point here)."""

    def test_never_create_or_replace(self, view_body: str) -> None:
        # Scanned over the DDL statement only — the header comment
        # legitimately NAMES the forbidden idiom while explaining why
        # (the ban-sentinel comment-awareness lesson, M4 gotcha).
        assert "CREATE OR REPLACE" not in view_body

    def test_keeps_the_original_ten_columns(self, view_body: str) -> None:
        for column in (
            "session_id",
            "tick",
            "imperial_rent",
            "imperial_rent_delta",
            "price_log",
            "price_log_delta",
            "fictitious_log",
            "fictitious_log_delta",
            "market_corrections",
            "market_corrections_delta",
        ):
            assert column in view_body, f"original column {column} dropped"

    def test_windows_every_playability_column_with_its_lag_delta(self, view_body: str) -> None:
        for column in _PLAYABILITY_COLUMNS:
            assert column in view_body, f"playability column {column} missing"
            assert f"{column}_delta" in view_body, f"{column}_delta missing"
            assert f"LAG({column})" in view_body, f"LAG window for {column} missing"

    def test_deltas_partition_by_session_order_by_tick(self, view_body: str) -> None:
        # 4 original deltas + 5 playability deltas = 9 LAG windows.
        assert view_body.count("PARTITION BY session_id ORDER BY tick") == 9, (
            "every one of the 9 deltas must window per-session, per-tick"
        )
