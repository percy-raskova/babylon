"""Unit tests for checkpoint skip behavior across data loaders.

Tests verify that loaders correctly skip work units when checkpoints exist
and process work units when checkpoints are missing.
"""

from __future__ import annotations

import hashlib
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.reference.database import NormalizedBase
from babylon.data.reference.schema import IngestCheckpoint

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def checkpoint_session() -> Generator[Session, None, None]:
    """Create session with checkpoint table for testing."""
    from sqlalchemy import event

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: object, _connection_record: object) -> None:
        import sqlite3

        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


def get_file_hash(path: Path) -> str:
    """Create a short hash of file path for checkpoint key.

    Matches the implementation in loaders (MD5 of path string, first 16 chars).
    """
    return hashlib.md5(str(path).encode()).hexdigest()[:16]


class MockFileLoader(DataLoader):
    """Mock loader for testing file-based checkpoint behavior."""

    def __init__(self) -> None:
        super().__init__()
        self.processed_files: list[Path] = []
        self.skipped_files: list[Path] = []

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Process files, skipping those with checkpoints."""
        stats = LoadStats(source="mock_file")
        files_arg = kwargs.get("files")
        files: list[Path] = list(cast(Iterable[Path], files_arg)) if files_arg else []

        if reset:
            self._clear_checkpoints(session, "mock_file")
            session.flush()

        for file_path in files:
            file_hash = get_file_hash(file_path)

            if self._is_completed(session, "mock_file", 0, file_hash, "file", "T"):
                self.skipped_files.append(file_path)
                continue

            # Simulate processing
            self.processed_files.append(file_path)
            stats.facts_loaded["files"] = stats.facts_loaded.get("files", 0) + 1

            # Mark as completed
            self._mark_completed(session, "mock_file", 0, file_hash, "file", "T", 1)
            session.flush()

        return stats

    def get_dimension_tables(self) -> list[type]:
        return []

    def get_fact_tables(self) -> list[type]:
        return []


class MockSeriesLoader(DataLoader):
    """Mock loader for testing series-based checkpoint behavior."""

    def __init__(self) -> None:
        super().__init__()
        self.processed_series: list[str] = []
        self.skipped_series: list[str] = []

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Process series, skipping those with checkpoints."""
        stats = LoadStats(source="mock_series")
        codes_arg = kwargs.get("series_codes")
        series_codes: list[str] = list(cast(Iterable[str], codes_arg)) if codes_arg else []

        if reset:
            self._clear_checkpoints(session, "mock_series")
            session.flush()

        for series_code in series_codes:
            if self._is_completed(session, "mock_series", 0, series_code, "series", "T"):
                self.skipped_series.append(series_code)
                continue

            # Simulate processing
            self.processed_series.append(series_code)
            stats.facts_loaded["series"] = stats.facts_loaded.get("series", 0) + 1

            # Mark as completed
            self._mark_completed(session, "mock_series", 0, series_code, "series", "T", 1)
            session.flush()

        return stats

    def get_dimension_tables(self) -> list[type]:
        return []

    def get_fact_tables(self) -> list[type]:
        return []


class MockStateYearLoader(DataLoader):
    """Mock loader for testing state/year-based checkpoint behavior."""

    def __init__(self) -> None:
        super().__init__()
        self.processed_units: list[tuple[int, str]] = []
        self.skipped_units: list[tuple[int, str]] = []

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Process state/year combos, skipping those with checkpoints."""
        stats = LoadStats(source="mock_state_year")
        years_arg = kwargs.get("years")
        states_arg = kwargs.get("states")
        years: list[int] = list(cast(Iterable[int], years_arg)) if years_arg else []
        states: list[str] = list(cast(Iterable[str], states_arg)) if states_arg else []

        if reset:
            for year in years:
                self._clear_checkpoints(session, "mock_state_year", year)
            session.flush()

        for year in years:
            for state_fips in states:
                if self._is_completed(session, "mock_state_year", year, state_fips, "api", "T"):
                    self.skipped_units.append((year, state_fips))
                    continue

                # Simulate processing
                self.processed_units.append((year, state_fips))
                stats.facts_loaded["api"] = stats.facts_loaded.get("api", 0) + 1

                # Mark as completed
                self._mark_completed(session, "mock_state_year", year, state_fips, "api", "T", 1)
                session.flush()

        return stats

    def get_dimension_tables(self) -> list[type]:
        return []

    def get_fact_tables(self) -> list[type]:
        return []


# =============================================================================
# FILE-BASED SKIP BEHAVIOR TESTS
# =============================================================================


class TestFileBasedSkipBehavior:
    """Tests for file-based checkpoint skip behavior."""

    def test_skip_when_file_checkpoint_exists(self, checkpoint_session: Session) -> None:
        """Loader skips file when checkpoint already exists."""
        loader = MockFileLoader()
        file1 = Path("/data/file1.csv")
        file_hash = get_file_hash(file1)

        # Pre-populate checkpoint
        loader._mark_completed(checkpoint_session, "mock_file", 0, file_hash, "file", "T", 100)
        checkpoint_session.flush()

        # Load with reset=False to preserve checkpoint
        loader.load(checkpoint_session, reset=False, files=[file1])

        assert file1 in loader.skipped_files
        assert file1 not in loader.processed_files

    def test_process_when_file_checkpoint_missing(self, checkpoint_session: Session) -> None:
        """Loader processes file when no checkpoint exists."""
        loader = MockFileLoader()
        file1 = Path("/data/file1.csv")

        # Load without prior checkpoint
        loader.load(checkpoint_session, reset=False, files=[file1])

        assert file1 in loader.processed_files
        assert file1 not in loader.skipped_files

    def test_partial_file_set_skips_completed_only(self, checkpoint_session: Session) -> None:
        """Loader skips only completed files, processes remaining."""
        loader = MockFileLoader()
        file1 = Path("/data/file1.csv")
        file2 = Path("/data/file2.csv")
        file3 = Path("/data/file3.csv")

        # Pre-populate checkpoint for file2 only
        file2_hash = get_file_hash(file2)
        loader._mark_completed(checkpoint_session, "mock_file", 0, file2_hash, "file", "T", 50)
        checkpoint_session.flush()

        # Load all three files
        loader.load(checkpoint_session, reset=False, files=[file1, file2, file3])

        assert file1 in loader.processed_files
        assert file2 in loader.skipped_files
        assert file3 in loader.processed_files
        assert len(loader.processed_files) == 2
        assert len(loader.skipped_files) == 1

    def test_reset_true_clears_and_processes_all(self, checkpoint_session: Session) -> None:
        """reset=True clears checkpoints and processes all files."""
        loader = MockFileLoader()
        file1 = Path("/data/file1.csv")
        file2 = Path("/data/file2.csv")

        # Pre-populate both checkpoints
        for f in [file1, file2]:
            loader._mark_completed(
                checkpoint_session, "mock_file", 0, get_file_hash(f), "file", "T", 100
            )
        checkpoint_session.flush()

        # Verify checkpoints exist
        count = checkpoint_session.query(IngestCheckpoint).count()
        assert count == 2

        # Load with reset=True
        loader.load(checkpoint_session, reset=True, files=[file1, file2])

        # Both should be processed (checkpoints cleared)
        assert file1 in loader.processed_files
        assert file2 in loader.processed_files
        assert len(loader.skipped_files) == 0

    def test_creates_checkpoint_after_processing(self, checkpoint_session: Session) -> None:
        """Loader creates checkpoint after processing a file."""
        loader = MockFileLoader()
        file1 = Path("/data/file1.csv")
        file_hash = get_file_hash(file1)

        # Verify no checkpoint exists
        assert not loader._is_completed(checkpoint_session, "mock_file", 0, file_hash, "file", "T")

        # Process file
        loader.load(checkpoint_session, reset=False, files=[file1])

        # Verify checkpoint now exists
        assert loader._is_completed(checkpoint_session, "mock_file", 0, file_hash, "file", "T")

    def test_file_path_change_creates_new_work_unit(self, checkpoint_session: Session) -> None:
        """Changing file path means different hash, treated as new file."""
        loader = MockFileLoader()
        file_original = Path("/data/file1.csv")
        file_moved = Path("/data/archive/file1.csv")

        # Process original file
        loader.load(checkpoint_session, reset=False, files=[file_original])
        assert file_original in loader.processed_files

        # Clear tracked files
        loader.processed_files = []
        loader.skipped_files = []

        # Process moved file - should be treated as new
        loader.load(checkpoint_session, reset=False, files=[file_moved])
        assert file_moved in loader.processed_files
        assert file_moved not in loader.skipped_files


# =============================================================================
# SERIES-BASED SKIP BEHAVIOR TESTS
# =============================================================================


class TestSeriesBasedSkipBehavior:
    """Tests for series-based checkpoint skip behavior (e.g., Energy loader)."""

    def test_skip_when_series_checkpoint_exists(self, checkpoint_session: Session) -> None:
        """Loader skips series when checkpoint already exists."""
        loader = MockSeriesLoader()
        series_code = "SWTC"

        # Pre-populate checkpoint
        loader._mark_completed(
            checkpoint_session, "mock_series", 0, series_code, "series", "T", 100
        )
        checkpoint_session.flush()

        # Load with reset=False
        loader.load(checkpoint_session, reset=False, series_codes=[series_code])

        assert series_code in loader.skipped_series
        assert series_code not in loader.processed_series

    def test_process_when_series_checkpoint_missing(self, checkpoint_session: Session) -> None:
        """Loader processes series when no checkpoint exists."""
        loader = MockSeriesLoader()
        series_code = "SWTC"

        loader.load(checkpoint_session, reset=False, series_codes=[series_code])

        assert series_code in loader.processed_series
        assert series_code not in loader.skipped_series

    def test_partial_series_set_skips_completed_only(self, checkpoint_session: Session) -> None:
        """Loader skips only completed series, processes remaining."""
        loader = MockSeriesLoader()
        series_codes = ["SWTC", "TXRC", "CLTC"]

        # Pre-populate checkpoint for TXRC only
        loader._mark_completed(checkpoint_session, "mock_series", 0, "TXRC", "series", "T", 50)
        checkpoint_session.flush()

        # Load all series
        loader.load(checkpoint_session, reset=False, series_codes=series_codes)

        assert "SWTC" in loader.processed_series
        assert "TXRC" in loader.skipped_series
        assert "CLTC" in loader.processed_series
        assert len(loader.processed_series) == 2
        assert len(loader.skipped_series) == 1


# =============================================================================
# STATE/YEAR-BASED SKIP BEHAVIOR TESTS
# =============================================================================


class TestStateYearBasedSkipBehavior:
    """Tests for state/year-based checkpoint skip behavior (e.g., QCEW API)."""

    def test_skip_when_state_year_checkpoint_exists(self, checkpoint_session: Session) -> None:
        """Loader skips state/year combo when checkpoint exists."""
        loader = MockStateYearLoader()

        # Pre-populate checkpoint for California 2021
        loader._mark_completed(checkpoint_session, "mock_state_year", 2021, "06", "api", "T", 100)
        checkpoint_session.flush()

        # Load with reset=False
        loader.load(checkpoint_session, reset=False, years=[2021], states=["06"])

        assert (2021, "06") in loader.skipped_units
        assert (2021, "06") not in loader.processed_units

    def test_process_when_state_year_checkpoint_missing(self, checkpoint_session: Session) -> None:
        """Loader processes state/year combo when no checkpoint exists."""
        loader = MockStateYearLoader()

        loader.load(checkpoint_session, reset=False, years=[2021], states=["06"])

        assert (2021, "06") in loader.processed_units
        assert (2021, "06") not in loader.skipped_units

    def test_partial_states_skips_completed_only(self, checkpoint_session: Session) -> None:
        """Loader skips only completed states, processes remaining."""
        loader = MockStateYearLoader()
        year = 2021
        states = ["06", "36", "48"]  # CA, NY, TX

        # Pre-populate checkpoint for NY only
        loader._mark_completed(checkpoint_session, "mock_state_year", year, "36", "api", "T", 50)
        checkpoint_session.flush()

        # Load all states for year
        loader.load(checkpoint_session, reset=False, years=[year], states=states)

        assert (year, "06") in loader.processed_units
        assert (year, "36") in loader.skipped_units
        assert (year, "48") in loader.processed_units
        assert len(loader.processed_units) == 2
        assert len(loader.skipped_units) == 1

    def test_year_isolation_in_checkpoints(self, checkpoint_session: Session) -> None:
        """Checkpoints for different years are isolated."""
        loader = MockStateYearLoader()

        # Pre-populate checkpoint for CA 2021 only
        loader._mark_completed(checkpoint_session, "mock_state_year", 2021, "06", "api", "T", 100)
        checkpoint_session.flush()

        # Load CA for 2021 and 2022
        loader.load(checkpoint_session, reset=False, years=[2021, 2022], states=["06"])

        # 2021 should be skipped, 2022 should be processed
        assert (2021, "06") in loader.skipped_units
        assert (2022, "06") in loader.processed_units

    def test_reset_clears_by_year(self, checkpoint_session: Session) -> None:
        """reset=True clears checkpoints only for years being loaded, then re-processes."""
        loader = MockStateYearLoader()

        # Pre-populate checkpoints for multiple years
        for year in [2020, 2021, 2022]:
            loader._mark_completed(
                checkpoint_session, "mock_state_year", year, "06", "api", "T", 100
            )
        checkpoint_session.flush()

        # Verify 3 checkpoints exist
        count = checkpoint_session.query(IngestCheckpoint).count()
        assert count == 3

        # Load only 2021 with reset=True
        loader.load(checkpoint_session, reset=True, years=[2021], states=["06"])

        # 2020 and 2022 checkpoints should still exist (untouched)
        remaining = checkpoint_session.query(IngestCheckpoint).all()
        years_remaining = {cp.year for cp in remaining}
        assert 2020 in years_remaining
        assert 2022 in years_remaining

        # 2021 should have been processed (not skipped)
        assert (2021, "06") in loader.processed_units
        assert (2021, "06") not in loader.skipped_units

        # Checkpoint for 2021 is recreated after processing
        assert 2021 in years_remaining


# =============================================================================
# CHECKPOINT VERIFICATION HELPERS
# =============================================================================


class TestCheckpointVerificationHelpers:
    """Tests for checkpoint state verification utilities."""

    def test_count_checkpoints_by_source(self, checkpoint_session: Session) -> None:
        """Can count checkpoints for a specific source."""
        loader = MockFileLoader()

        # Create checkpoints for different sources
        loader._mark_completed(checkpoint_session, "materials", 0, "hash1", "file", "T", 100)
        loader._mark_completed(checkpoint_session, "materials", 0, "hash2", "file", "T", 100)
        loader._mark_completed(checkpoint_session, "qcew", 0, "hash3", "file", "T", 100)
        checkpoint_session.flush()

        # Count by source
        materials_count = (
            checkpoint_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .count()
        )
        qcew_count = (
            checkpoint_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "qcew")
            .count()
        )

        assert materials_count == 2
        assert qcew_count == 1

    def test_get_checkpoint_row_count_total(self, checkpoint_session: Session) -> None:
        """Can sum row counts across checkpoints for a source."""
        loader = MockFileLoader()

        # Create checkpoints with different row counts
        loader._mark_completed(checkpoint_session, "materials", 0, "hash1", "file", "T", 100)
        loader._mark_completed(checkpoint_session, "materials", 0, "hash2", "file", "T", 250)
        checkpoint_session.flush()

        # Sum row counts
        from sqlalchemy import func

        total_rows = (
            checkpoint_session.query(func.sum(IngestCheckpoint.row_count))
            .filter(IngestCheckpoint.source_code == "materials")
            .scalar()
        )

        assert total_rows == 350

    def test_verify_no_duplicate_checkpoints(self, checkpoint_session: Session) -> None:
        """Verify UPSERT behavior prevents duplicates."""
        loader = MockFileLoader()
        file_hash = "same_hash"

        # Mark same work unit completed multiple times
        loader._mark_completed(checkpoint_session, "test", 0, file_hash, "file", "T", 100)
        checkpoint_session.flush()
        loader._mark_completed(checkpoint_session, "test", 0, file_hash, "file", "T", 200)
        checkpoint_session.flush()
        loader._mark_completed(checkpoint_session, "test", 0, file_hash, "file", "T", 300)
        checkpoint_session.flush()

        # Should only have 1 checkpoint (with latest row_count)
        count = (
            checkpoint_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "test")
            .count()
        )
        assert count == 1

        checkpoint = (
            checkpoint_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "test")
            .first()
        )
        assert checkpoint is not None
        assert checkpoint.row_count == 300  # Latest value

    def test_checkpoint_timestamp_tracking(self, checkpoint_session: Session) -> None:
        """Checkpoints include completion timestamp."""
        loader = MockFileLoader()

        loader._mark_completed(checkpoint_session, "test", 0, "hash1", "file", "T", 100)
        checkpoint_session.flush()

        checkpoint = checkpoint_session.query(IngestCheckpoint).first()
        assert checkpoint is not None
        assert checkpoint.completed_at is not None
