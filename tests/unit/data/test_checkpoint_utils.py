"""Unit tests for checkpoint verification utilities."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.reference.checkpoint_utils import (
    count_checkpoints,
    count_checkpoints_by_year,
    get_checkpoint_details,
    get_checkpoint_summary,
    get_incomplete_work_units,
    get_total_row_count,
    verify_checkpoint_coverage,
)
from babylon.data.reference.database import NormalizedBase
from babylon.data.reference.schema import IngestCheckpoint


@pytest.fixture
def utils_session() -> Generator[Session, None, None]:
    """Create session with checkpoint table for testing."""
    engine = create_engine("duckdb:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


def add_checkpoint(
    session: Session,
    source: str,
    year: int,
    state_fips: str,
    table_id: str = "file",
    race_code: str = "T",
    row_count: int = 100,
) -> None:
    """Helper to add a checkpoint record."""
    checkpoint = IngestCheckpoint(
        source_code=source,
        year=year,
        state_fips=state_fips,
        table_id=table_id,
        race_code=race_code,
        row_count=row_count,
    )
    session.add(checkpoint)
    session.flush()


class TestCountCheckpoints:
    """Tests for count_checkpoints function."""

    def test_returns_zero_for_empty(self, utils_session: Session) -> None:
        """Returns 0 when no checkpoints exist."""
        result = count_checkpoints(utils_session, "materials")
        assert result == 0

    def test_counts_only_specified_source(self, utils_session: Session) -> None:
        """Counts only checkpoints for the specified source."""
        add_checkpoint(utils_session, "materials", 0, "hash1")
        add_checkpoint(utils_session, "materials", 0, "hash2")
        add_checkpoint(utils_session, "qcew", 0, "hash3")

        assert count_checkpoints(utils_session, "materials") == 2
        assert count_checkpoints(utils_session, "qcew") == 1
        assert count_checkpoints(utils_session, "energy") == 0


class TestCountCheckpointsByYear:
    """Tests for count_checkpoints_by_year function."""

    def test_filters_by_year(self, utils_session: Session) -> None:
        """Filters checkpoints by year."""
        add_checkpoint(utils_session, "qcew", 2020, "06")
        add_checkpoint(utils_session, "qcew", 2020, "36")
        add_checkpoint(utils_session, "qcew", 2021, "06")

        assert count_checkpoints_by_year(utils_session, "qcew", 2020) == 2
        assert count_checkpoints_by_year(utils_session, "qcew", 2021) == 1
        assert count_checkpoints_by_year(utils_session, "qcew", 2022) == 0


class TestGetTotalRowCount:
    """Tests for get_total_row_count function."""

    def test_returns_zero_for_empty(self, utils_session: Session) -> None:
        """Returns 0 when no checkpoints exist."""
        result = get_total_row_count(utils_session, "materials")
        assert result == 0

    def test_sums_row_counts(self, utils_session: Session) -> None:
        """Sums row counts across all checkpoints."""
        add_checkpoint(utils_session, "materials", 0, "hash1", row_count=100)
        add_checkpoint(utils_session, "materials", 0, "hash2", row_count=250)
        add_checkpoint(utils_session, "materials", 0, "hash3", row_count=50)

        result = get_total_row_count(utils_session, "materials")
        assert result == 400

    def test_only_counts_specified_source(self, utils_session: Session) -> None:
        """Only sums row counts for the specified source."""
        add_checkpoint(utils_session, "materials", 0, "hash1", row_count=100)
        add_checkpoint(utils_session, "qcew", 0, "hash2", row_count=1000)

        assert get_total_row_count(utils_session, "materials") == 100
        assert get_total_row_count(utils_session, "qcew") == 1000


class TestGetCheckpointSummary:
    """Tests for get_checkpoint_summary function."""

    def test_empty_summary(self, utils_session: Session) -> None:
        """Returns empty summary when no checkpoints exist."""
        summary = get_checkpoint_summary(utils_session, "materials")

        assert summary.source_code == "materials"
        assert summary.checkpoint_count == 0
        assert summary.total_rows == 0
        assert summary.years == []
        assert summary.unique_states == 0

    def test_full_summary(self, utils_session: Session) -> None:
        """Returns complete summary with all metrics."""
        add_checkpoint(utils_session, "qcew", 2020, "06", row_count=100)
        add_checkpoint(utils_session, "qcew", 2020, "36", row_count=150)
        add_checkpoint(utils_session, "qcew", 2021, "06", row_count=200)

        summary = get_checkpoint_summary(utils_session, "qcew")

        assert summary.source_code == "qcew"
        assert summary.checkpoint_count == 3
        assert summary.total_rows == 450
        assert summary.years == [2020, 2021]
        assert summary.unique_states == 2

    def test_excludes_year_zero_from_years(self, utils_session: Session) -> None:
        """Year 0 (used for non-year work units) is excluded from years list."""
        add_checkpoint(utils_session, "materials", 0, "hash1")  # File-based
        add_checkpoint(utils_session, "materials", 0, "hash2")  # File-based

        summary = get_checkpoint_summary(utils_session, "materials")

        assert summary.years == []  # Year 0 excluded
        assert summary.checkpoint_count == 2


class TestVerifyCheckpointCoverage:
    """Tests for verify_checkpoint_coverage function."""

    def test_returns_true_when_matches(self, utils_session: Session) -> None:
        """Returns True when checkpoint count matches expected."""
        add_checkpoint(utils_session, "materials", 0, "hash1")
        add_checkpoint(utils_session, "materials", 0, "hash2")

        assert verify_checkpoint_coverage(utils_session, "materials", 2) is True

    def test_returns_false_when_mismatch(self, utils_session: Session) -> None:
        """Returns False when checkpoint count doesn't match."""
        add_checkpoint(utils_session, "materials", 0, "hash1")

        assert verify_checkpoint_coverage(utils_session, "materials", 2) is False


class TestGetIncompleteWorkUnits:
    """Tests for get_incomplete_work_units function."""

    def test_returns_all_when_none_completed(self, utils_session: Session) -> None:
        """Returns all expected states when none are completed."""
        expected_states = ["06", "36", "48"]

        incomplete = get_incomplete_work_units(utils_session, "qcew", expected_states, 2020)

        assert set(incomplete) == {"06", "36", "48"}

    def test_returns_empty_when_all_completed(self, utils_session: Session) -> None:
        """Returns empty list when all expected states are completed."""
        expected_states = ["06", "36"]

        add_checkpoint(utils_session, "qcew", 2020, "06")
        add_checkpoint(utils_session, "qcew", 2020, "36")

        incomplete = get_incomplete_work_units(utils_session, "qcew", expected_states, 2020)

        assert incomplete == []

    def test_returns_only_incomplete(self, utils_session: Session) -> None:
        """Returns only states without checkpoints."""
        expected_states = ["06", "36", "48"]

        add_checkpoint(utils_session, "qcew", 2020, "36")  # Only 36 completed

        incomplete = get_incomplete_work_units(utils_session, "qcew", expected_states, 2020)

        assert set(incomplete) == {"06", "48"}

    def test_year_isolation(self, utils_session: Session) -> None:
        """Checkpoints for other years don't affect result."""
        expected_states = ["06"]

        # Checkpoint for different year
        add_checkpoint(utils_session, "qcew", 2021, "06")

        # Should still be incomplete for 2020
        incomplete = get_incomplete_work_units(utils_session, "qcew", expected_states, 2020)

        assert incomplete == ["06"]


class TestGetCheckpointDetails:
    """Tests for get_checkpoint_details function."""

    def test_returns_empty_for_no_checkpoints(self, utils_session: Session) -> None:
        """Returns empty list when no checkpoints exist."""
        details = get_checkpoint_details(utils_session, "materials")
        assert details == []

    def test_returns_all_fields(self, utils_session: Session) -> None:
        """Returns all checkpoint fields as dictionaries."""
        add_checkpoint(
            utils_session,
            "materials",
            2020,
            "hash123",
            table_id="file",
            race_code="T",
            row_count=500,
        )

        details = get_checkpoint_details(utils_session, "materials")

        assert len(details) == 1
        detail = details[0]
        assert detail["source_code"] == "materials"
        assert detail["year"] == 2020
        assert detail["state_fips"] == "hash123"
        assert detail["table_id"] == "file"
        assert detail["race_code"] == "T"
        assert detail["row_count"] == 500
        assert "checkpoint_id" in detail
        assert "completed_at" in detail

    def test_ordered_by_year_and_state(self, utils_session: Session) -> None:
        """Results are ordered by year, then state_fips."""
        add_checkpoint(utils_session, "qcew", 2021, "48")
        add_checkpoint(utils_session, "qcew", 2020, "36")
        add_checkpoint(utils_session, "qcew", 2020, "06")

        details = get_checkpoint_details(utils_session, "qcew")

        # Should be ordered: 2020-06, 2020-36, 2021-48
        assert details[0]["year"] == 2020
        assert details[0]["state_fips"] == "06"
        assert details[1]["year"] == 2020
        assert details[1]["state_fips"] == "36"
        assert details[2]["year"] == 2021
        assert details[2]["state_fips"] == "48"
