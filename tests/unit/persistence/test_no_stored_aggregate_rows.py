"""FR-019 enforcement: no stored aggregate tables (T045).

Spec 062 forbids any persisted ``dynamic_county_*``, ``dynamic_state_*``, or
``dynamic_national_*`` table. Aggregation is on-read via the
v_county/state/national_value_aggregate views.

This test scans the migration SQL files for any matching CREATE TABLE
statement. The companion integration test (deferred to Phase 5
integration coverage) introspects the live Postgres schema.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path("src/babylon/persistence/migrations").resolve()


@pytest.mark.cross_scale
class TestNoStoredAggregateTables:
    """Migration files must not declare aggregate tables above hex level."""

    @pytest.fixture
    def all_migration_sql(self) -> str:
        return "\n".join(
            sql_file.read_text() for sql_file in sorted(MIGRATIONS_DIR.glob("00*.sql"))
        )

    def test_no_dynamic_county_table(self, all_migration_sql: str) -> None:
        assert not re.search(
            r"CREATE\s+TABLE[^;]*dynamic_county_",
            all_migration_sql,
            re.IGNORECASE,
        ), "FR-019 violated: dynamic_county_* table declared"

    def test_no_dynamic_state_table(self, all_migration_sql: str) -> None:
        assert not re.search(
            r"CREATE\s+TABLE[^;]*dynamic_state_",
            all_migration_sql,
            re.IGNORECASE,
        ), "FR-019 violated: dynamic_state_* table declared"

    def test_no_dynamic_national_table(self, all_migration_sql: str) -> None:
        assert not re.search(
            r"CREATE\s+TABLE[^;]*dynamic_national_",
            all_migration_sql,
            re.IGNORECASE,
        ), "FR-019 violated: dynamic_national_* table declared"

    def test_aggregation_views_are_views_not_tables(self, all_migration_sql: str) -> None:
        """The four aggregate names ARE views — not tables."""
        for view_name in (
            "v_county_value_aggregate",
            "v_state_value_aggregate",
            "v_national_value_aggregate",
            "v_global_phi_balance",
        ):
            assert f"CREATE OR REPLACE VIEW {view_name}" in all_migration_sql, (
                f"View {view_name} missing from migrations"
            )
            assert not re.search(
                rf"CREATE\s+TABLE[^;]*\b{view_name}\b",
                all_migration_sql,
                re.IGNORECASE,
            ), f"FR-019 violated: {view_name} declared as a table, not a view"
