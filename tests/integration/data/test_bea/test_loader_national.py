"""Integration tests for BEA national industry loader.

Tests against actual database with real BEA national industry data.
Requires the actual BEA data files and database to be present.

Extracted from tests/unit/data/test_bea/test_loader_national.py
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from babylon.data.bea.loader_national import BEANationalLoader
from babylon.data.loader_base import LoadStats

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@pytest.mark.integration
class TestActualDatabaseLoading:
    """Integration tests against actual database.

    These tests require the actual BEA data files and database to be present.
    Uses a single data load for all tests to avoid FK constraint issues.
    """

    @pytest.fixture(scope="class")
    def loaded_data(self) -> LoadStats:
        """Load BEA data once for all tests in this class.

        This avoids repeated load/clear cycles that cause FK constraint issues.
        """
        from babylon.data.reference.database import get_normalized_session_factory

        loader = BEANationalLoader(data_dir=Path("data"))
        session_factory = get_normalized_session_factory()

        with session_factory() as session:
            # Clear and load once
            stats = loader.load(session, reset=True, verbose=False)
            return stats

    @pytest.fixture
    def session(self, loaded_data: LoadStats) -> Session:
        """Get a database session (data already loaded by loaded_data fixture)."""
        from babylon.data.reference.database import get_normalized_session_factory

        session_factory = get_normalized_session_factory()
        return session_factory()

    @pytest.fixture
    def stats(self, loaded_data: LoadStats) -> LoadStats:
        """Return the load statistics."""
        return loaded_data

    def test_load_creates_industries(self, stats: LoadStats) -> None:
        """Should create BEA industry dimension records."""
        assert stats.dimensions_loaded.get("dim_bea_industry", 0) > 50

    def test_load_creates_facts(self, stats: LoadStats) -> None:
        """Should create fact records for each industry-year combination."""
        assert stats.facts_loaded.get("fact_bea_national_industry", 0) > 1000

    def test_accounting_identity_holds(self, session: Session) -> None:
        """Gross output should equal intermediate inputs + value added."""
        from sqlalchemy import text

        # Query to check accounting identity (data already loaded via fixture)
        result = session.execute(
            text("""
                SELECT
                    AVG(ABS(gross_output_millions -
                        (intermediate_inputs_millions + value_added_millions)))
                FROM fact_bea_national_industry
                WHERE gross_output_millions IS NOT NULL
                AND intermediate_inputs_millions IS NOT NULL
                AND value_added_millions IS NOT NULL
            """)
        ).scalar()

        # Average discrepancy should be less than $10M (rounding errors)
        assert result is not None
        assert float(result) < 10.0

    def test_all_hierarchy_levels_populated(self, session: Session) -> None:
        """Should have industries at all 4 hierarchy levels."""
        from sqlalchemy import text

        # Data already loaded via fixture
        result = session.execute(
            text("SELECT DISTINCT bea_level FROM dim_bea_industry ORDER BY bea_level")
        ).fetchall()

        levels = [row[0] for row in result]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels
        assert 4 in levels

    def test_years_span_expected_range(self, session: Session) -> None:
        """Should have data from late 1990s to recent years."""
        from sqlalchemy import text

        # Data already loaded via fixture
        result = session.execute(
            text("""
                SELECT MIN(t.year), MAX(t.year)
                FROM fact_bea_national_industry f
                JOIN dim_time t ON f.time_id = t.time_id
            """)
        ).fetchone()

        assert result is not None
        min_year, max_year = result
        assert min_year <= 2000
        assert max_year >= 2020
