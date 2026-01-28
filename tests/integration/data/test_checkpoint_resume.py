"""Integration tests for checkpoint resume capability across data loaders.

Tests verify that real loaders correctly resume from checkpoints after
partial loads and handle reset behavior properly.
"""

from __future__ import annotations

import hashlib
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.loader_base import LoaderConfig
from babylon.data.materials.loader_3nf import MaterialsLoader
from babylon.data.reference.database import NormalizedBase
from babylon.data.reference.schema import (
    FactCommodityObservation,
    IngestCheckpoint,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def integration_session() -> Generator[Session, None, None]:
    """Create session with full schema for integration testing."""
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


@pytest.fixture
def materials_csv_dir(tmp_path: Path) -> Path:
    """Create temporary directory with commodity CSV files."""
    csv_dir = tmp_path / "raw_mats"
    csv_dir.mkdir()
    # Create the commodities subdirectory where loader expects files
    commodities_dir = csv_dir / "commodities"
    commodities_dir.mkdir()
    return csv_dir


def create_commodity_csv(
    csv_dir: Path, commodity_code: str, years: list[int], metric_value: float = 100.0
) -> Path:
    """Create a minimal commodity CSV file for testing.

    Args:
        csv_dir: Path to raw_mats directory.
        commodity_code: Commodity code (used in filename).
        years: List of years to include.
        metric_value: Base value for metrics.

    Returns:
        Path to created CSV file.
    """
    # Create in commodities subdirectory with expected naming pattern
    commodities_dir = csv_dir / "commodities"
    file_path = commodities_dir / f"mcs2025-{commodity_code}_salient.csv"
    content = "DataSource,Commodity,Year,Production,Imports,Exports\n"

    for year in years:
        content += f"MCS2025,{commodity_code.title()},{year},{metric_value},{metric_value * 0.5},{metric_value * 0.2}\n"

    file_path.write_text(content)
    return file_path


def get_file_hash(path: Path) -> str:
    """Create a short hash of file path for checkpoint key."""
    return hashlib.md5(str(path).encode()).hexdigest()[:16]


# =============================================================================
# MATERIALS LOADER RESUME TESTS
# =============================================================================


@pytest.mark.integration
class TestMaterialsLoaderResume:
    """Integration tests for Materials loader checkpoint resume behavior."""

    def test_resume_after_partial_file_load(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """Loader resumes from checkpoint, skipping already-processed files."""
        # Create 3 CSV files
        file1 = create_commodity_csv(materials_csv_dir, "lithium", [2020, 2021])
        file2 = create_commodity_csv(materials_csv_dir, "cobalt", [2020, 2021])
        file3 = create_commodity_csv(materials_csv_dir, "nickel", [2020, 2021])

        config = LoaderConfig(materials_years=[2020, 2021])
        loader = MaterialsLoader(config)

        # Pre-populate checkpoint for file1 (simulating partial prior load)
        file1_hash = get_file_hash(file1)
        loader._mark_completed(integration_session, "materials", 0, file1_hash, "file", "T", 6)
        integration_session.flush()

        # Load with reset=False to preserve checkpoint
        _stats = loader.load(
            integration_session,
            reset=False,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # Check checkpoint state
        checkpoints = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .all()
        )
        assert len(checkpoints) == 3  # All 3 files now have checkpoints

        # File1 should have been skipped (original checkpoint preserved)
        file1_checkpoint = next(cp for cp in checkpoints if cp.state_fips == file1_hash)
        assert file1_checkpoint.row_count == 6  # Original count unchanged

        # File2 and File3 should have new checkpoints
        processed_hashes = {get_file_hash(file2), get_file_hash(file3)}
        for cp in checkpoints:
            if cp.state_fips != file1_hash:
                assert cp.state_fips in processed_hashes

    def test_reset_true_clears_and_reprocesses_all(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """reset=True clears checkpoints and reprocesses all files."""
        # Create 2 CSV files
        file1 = create_commodity_csv(materials_csv_dir, "lithium", [2020])
        file2 = create_commodity_csv(materials_csv_dir, "cobalt", [2020])

        config = LoaderConfig(materials_years=[2020])
        loader = MaterialsLoader(config)

        # Pre-populate checkpoints for both files
        for f in [file1, file2]:
            loader._mark_completed(
                integration_session, "materials", 0, get_file_hash(f), "file", "T", 100
            )
        integration_session.flush()

        # Verify checkpoints exist
        initial_count = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .count()
        )
        assert initial_count == 2

        # Load with reset=True
        _stats = loader.load(
            integration_session,
            reset=True,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # Both files should have been processed (checkpoints cleared then recreated)
        # Check that fact data was loaded
        fact_count = integration_session.query(FactCommodityObservation).count()
        assert fact_count > 0

        # Checkpoints should exist again (recreated after processing)
        final_count = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .count()
        )
        assert final_count == 2

    def test_reset_false_skips_completed_files(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """reset=False skips files with existing checkpoints."""
        # Create 2 CSV files (used by loader via directory discovery)
        create_commodity_csv(materials_csv_dir, "lithium", [2020])
        create_commodity_csv(materials_csv_dir, "cobalt", [2020])

        config = LoaderConfig(materials_years=[2020])
        loader = MaterialsLoader(config)

        # First load - process both files
        _stats1 = loader.load(
            integration_session,
            reset=True,
            verbose=False,
            data_path=materials_csv_dir,
        )

        initial_checkpoints = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .all()
        )
        assert len(initial_checkpoints) == 2

        # Second load with reset=False
        _stats2 = loader.load(
            integration_session,
            reset=False,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # No new data should be loaded (all files skipped)
        # Both files had checkpoints, so they should be skipped
        final_checkpoints = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .all()
        )
        assert len(final_checkpoints) == 2

        # Checkpoint row counts should be unchanged
        for initial_cp in initial_checkpoints:
            final_cp = next(
                cp for cp in final_checkpoints if cp.state_fips == initial_cp.state_fips
            )
            assert final_cp.row_count == initial_cp.row_count

    def test_new_file_processed_existing_skipped(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """New files are processed while completed files are skipped."""
        # Create initial file (used by loader via directory discovery)
        create_commodity_csv(materials_csv_dir, "lithium", [2020])

        config = LoaderConfig(materials_years=[2020])
        loader = MaterialsLoader(config)

        # First load - process file1
        _stats1 = loader.load(
            integration_session,
            reset=True,
            verbose=False,
            data_path=materials_csv_dir,
        )

        initial_checkpoints = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .count()
        )
        assert initial_checkpoints == 1

        # Add a new file (used by loader via directory discovery)
        create_commodity_csv(materials_csv_dir, "cobalt", [2020])

        # Second load with reset=False
        _stats2 = loader.load(
            integration_session,
            reset=False,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # Should now have 2 checkpoints (file1 skipped, file2 processed)
        final_checkpoints = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .count()
        )
        assert final_checkpoints == 2


# =============================================================================
# CHECKPOINT ISOLATION TESTS
# =============================================================================


@pytest.mark.integration
class TestCheckpointSourceIsolation:
    """Tests verifying checkpoint isolation between different data sources."""

    def test_different_sources_isolated(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """Checkpoints for different sources don't interfere."""
        # Create a materials checkpoint
        file1 = create_commodity_csv(materials_csv_dir, "lithium", [2020])
        file_hash = get_file_hash(file1)

        config = LoaderConfig(materials_years=[2020])
        loader = MaterialsLoader(config)

        # Create checkpoint for materials
        loader._mark_completed(integration_session, "materials", 0, file_hash, "file", "T", 100)
        # Create checkpoint for a different source with same key values
        loader._mark_completed(integration_session, "qcew", 0, file_hash, "file", "T", 200)
        integration_session.flush()

        # Check that materials checkpoint exists
        assert loader._is_completed(integration_session, "materials", 0, file_hash, "file", "T")
        assert loader._is_completed(integration_session, "qcew", 0, file_hash, "file", "T")

        # Clear only materials checkpoints
        loader._clear_checkpoints(integration_session, "materials")
        integration_session.flush()

        # Materials checkpoint should be gone, qcew should remain
        assert not loader._is_completed(integration_session, "materials", 0, file_hash, "file", "T")
        assert loader._is_completed(integration_session, "qcew", 0, file_hash, "file", "T")


# =============================================================================
# CHECKPOINT ROW COUNT TRACKING TESTS
# =============================================================================


@pytest.mark.integration
class TestCheckpointRowCountTracking:
    """Tests verifying checkpoint row_count tracking."""

    def test_row_count_reflects_processed_records(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """Checkpoint row_count reflects actual records processed."""
        # Create file with known number of records (3 years x 3 metrics = 9 records)
        # File path used by loader via directory discovery
        create_commodity_csv(materials_csv_dir, "lithium", [2020, 2021, 2022])

        config = LoaderConfig(materials_years=[2020, 2021, 2022])
        loader = MaterialsLoader(config)

        # Load the file
        _stats = loader.load(
            integration_session,
            reset=True,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # Check checkpoint row count
        checkpoint = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .first()
        )

        # Should have 9 records (3 years x 3 metrics per year)
        assert checkpoint is not None
        assert checkpoint.row_count == 9

    def test_checkpoint_preserves_row_count_on_skip(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """Checkpoint row_count is preserved when file is skipped."""
        file1 = create_commodity_csv(materials_csv_dir, "lithium", [2020])
        file_hash = get_file_hash(file1)

        config = LoaderConfig(materials_years=[2020])
        loader = MaterialsLoader(config)

        # Pre-populate checkpoint with specific row count
        loader._mark_completed(integration_session, "materials", 0, file_hash, "file", "T", 999)
        integration_session.flush()

        # Load with reset=False (file will be skipped)
        _stats = loader.load(
            integration_session,
            reset=False,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # Row count should be unchanged
        checkpoint = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .first()
        )
        assert checkpoint is not None
        assert checkpoint.row_count == 999


# =============================================================================
# EMPTY CASES AND EDGE CONDITIONS
# =============================================================================


@pytest.mark.integration
class TestCheckpointEdgeCases:
    """Tests for checkpoint edge cases."""

    def test_empty_directory_no_checkpoints(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """Empty directory creates no checkpoints."""
        config = LoaderConfig(materials_years=[2020])
        loader = MaterialsLoader(config)

        # Load from empty directory
        stats = loader.load(
            integration_session,
            reset=True,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # Should have error but no checkpoints
        assert len(stats.errors) > 0  # "No commodity CSV files found"

        checkpoint_count = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .count()
        )
        assert checkpoint_count == 0

    def test_all_files_already_completed(
        self, integration_session: Session, materials_csv_dir: Path
    ) -> None:
        """When all files are completed, nothing is processed."""
        # Create 2 CSV files
        file1 = create_commodity_csv(materials_csv_dir, "lithium", [2020])
        file2 = create_commodity_csv(materials_csv_dir, "cobalt", [2020])

        config = LoaderConfig(materials_years=[2020])
        loader = MaterialsLoader(config)

        # Pre-populate checkpoints for both files
        for f in [file1, file2]:
            loader._mark_completed(
                integration_session, "materials", 0, get_file_hash(f), "file", "T", 3
            )
        integration_session.flush()

        # Load with reset=False
        _stats = loader.load(
            integration_session,
            reset=False,
            verbose=False,
            data_path=materials_csv_dir,
        )

        # No facts should be loaded (everything skipped)
        fact_count = integration_session.query(FactCommodityObservation).count()
        assert fact_count == 0  # No new data loaded

        # Checkpoints should be unchanged
        checkpoint_count = (
            integration_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "materials")
            .count()
        )
        assert checkpoint_count == 2
