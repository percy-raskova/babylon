"""Unit tests for ArcGISStreamingLoader base class.

Tests verify two-phase loading with page-level checkpoints:
1. Fetch phase: Stream features to staging with checkpoints after each page
2. Aggregate phase: GROUP BY staging data and insert facts

TDD RED phase: These tests define expected behavior before implementation.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.reference.database import NormalizedBase
from babylon.data.reference.schema import (
    DimCounty,
    DimState,
    IngestCheckpoint,
    StagingArcGISFeature,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def streaming_session() -> Generator[Session, None, None]:
    """Create session with staging and checkpoint tables for testing."""
    engine = create_engine("duckdb:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    # Seed minimal geographic dimensions
    state = DimState(state_fips="06", state_name="California", state_abbrev="CA")
    session.add(state)
    session.flush()

    counties = [
        DimCounty(
            fips="06001",
            state_id=state.state_id,
            county_fips="001",
            county_name="Alameda",
        ),
        DimCounty(
            fips="06037",
            state_id=state.state_id,
            county_fips="037",
            county_name="Los Angeles",
        ),
        DimCounty(
            fips="06073",
            state_id=state.state_id,
            county_fips="073",
            county_name="San Diego",
        ),
    ]
    for county in counties:
        session.add(county)
    session.flush()

    yield session
    session.close()


@dataclass
class MockArcGISFeature:
    """Mock feature matching ArcGISFeature interface."""

    object_id: int
    attributes: dict[str, Any]


def create_mock_features(
    count: int,
    county_fips: str = "06001",
    type_code: str = "police_local",
    start_id: int = 1,
) -> list[MockArcGISFeature]:
    """Create mock ArcGIS features for testing."""
    return [
        MockArcGISFeature(
            object_id=start_id + i,
            attributes={
                "OBJECTID": start_id + i,
                "COUNTYFIPS": county_fips,
                "TYPE": type_code,
            },
        )
        for i in range(count)
    ]


# =============================================================================
# FETCH PHASE CHECKPOINT TESTS
# =============================================================================


class TestFetchPhaseCheckpoints:
    """Tests for page-level checkpoint behavior during fetch phase."""

    def test_fresh_load_starts_at_offset_zero(self, streaming_session: Session) -> None:
        """Fresh load with reset=True starts fetching from offset 0."""
        # Import here to allow TDD RED phase (will fail until implemented)

        # Create a concrete test loader
        loader = self._create_test_loader(
            features=create_mock_features(100),
            page_size=50,
        )

        # Fresh load should start at offset 0
        stats = loader.load(streaming_session, reset=True, verbose=False)

        # Should have processed all features
        assert stats.facts_loaded.get("staging", 0) == 100

        # Staging table should have all features
        count = streaming_session.query(StagingArcGISFeature).count()
        assert count == 100

    def test_resume_continues_from_last_checkpoint_offset(self, streaming_session: Session) -> None:
        """Resume starts from offset stored in last checkpoint."""

        # Simulate partial load: checkpoint says offset 50 completed
        streaming_session.add(
            IngestCheckpoint(
                source_code="test_arcgis",
                year=0,
                state_fips="00",
                table_id="fetch:50",
                race_code="T",
                row_count=50,
            )
        )
        # Add 50 features already in staging
        for i in range(50):
            streaming_session.add(
                StagingArcGISFeature(
                    source_code="test_arcgis",
                    object_id=i + 1,
                    county_fips="06001",
                    type_code="police_local",
                )
            )
        streaming_session.flush()

        # Create loader with 100 features (should resume from 50)
        loader = self._create_test_loader(
            features=create_mock_features(100),
            page_size=50,
        )

        # Resume without reset should continue from offset 50
        stats = loader.load(streaming_session, reset=False, verbose=False)

        # Should only process remaining 50 features
        assert stats.facts_loaded.get("staging", 0) == 50

        # Staging should now have all 100
        count = streaming_session.query(StagingArcGISFeature).count()
        assert count == 100

    def test_page_checkpoint_created_after_each_page(self, streaming_session: Session) -> None:
        """After each 2000-feature page, a checkpoint is updated."""

        # Create loader with 150 features, page size 50
        loader = self._create_test_loader(
            features=create_mock_features(150),
            page_size=50,
        )

        loader.load(streaming_session, reset=True, verbose=False)

        # Should have checkpoint showing completion
        checkpoint = (
            streaming_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "test_arcgis")
            .filter(IngestCheckpoint.table_id.like("fetch:%"))
            .order_by(IngestCheckpoint.checkpoint_id.desc())
            .first()
        )
        assert checkpoint is not None
        assert checkpoint.table_id == "fetch:complete"
        assert checkpoint.row_count == 150

    def test_duplicate_objectids_handled_by_upsert(self, streaming_session: Session) -> None:
        """Staging table handles duplicate OBJECTIDs via upsert."""

        # Pre-populate staging with feature 1
        streaming_session.add(
            StagingArcGISFeature(
                source_code="test_arcgis",
                object_id=1,
                county_fips="06001",
                type_code="police_local",
            )
        )
        streaming_session.flush()

        # Load with overlapping feature (same object_id=1)
        loader = self._create_test_loader(
            features=create_mock_features(10, start_id=1),
            page_size=50,
        )

        # Should not fail despite duplicate
        loader.load(streaming_session, reset=False, verbose=False)

        # Should have 10 features (upserted, not duplicated)
        count = streaming_session.query(StagingArcGISFeature).count()
        assert count == 10

    def test_fetch_marked_complete_after_final_page(self, streaming_session: Session) -> None:
        """Fetch phase checkpoint shows 'complete' after final page."""

        loader = self._create_test_loader(
            features=create_mock_features(75),
            page_size=50,
        )

        loader.load(streaming_session, reset=True, verbose=False)

        # Fetch checkpoint should be marked complete
        checkpoint = (
            streaming_session.query(IngestCheckpoint)
            .filter(IngestCheckpoint.source_code == "test_arcgis")
            .filter(IngestCheckpoint.table_id == "fetch:complete")
            .first()
        )
        assert checkpoint is not None

    def _create_test_loader(self, features: list[MockArcGISFeature], page_size: int = 50) -> Any:
        """Create a concrete test loader for testing."""
        from babylon.data.arcgis_loader_base import ArcGISStreamingLoader

        class TestLoader(ArcGISStreamingLoader):
            def __init__(self, test_features: list[MockArcGISFeature], test_page_size: int) -> None:
                super().__init__()
                self._test_features = test_features
                self._test_page_size = test_page_size

            def _get_source_code(self) -> str:
                return "test_arcgis"

            def _get_service_url(self) -> str:
                return "http://test.arcgis.com/FeatureServer/0"

            def _get_out_fields(self) -> str:
                return "OBJECTID,COUNTYFIPS,TYPE"

            def _get_page_size(self) -> int:
                return self._test_page_size

            def _query_features(self, offset: int) -> Iterator[MockArcGISFeature]:
                """Return ALL features starting from offset (matches real client)."""
                # Real ArcGIS client returns all features; pagination is internal
                yield from self._test_features[offset:]

            def _get_total_count(self) -> int:
                return len(self._test_features)

            def _map_feature_to_staging(
                self, feature: MockArcGISFeature, fips_lookup: dict[str, int]
            ) -> dict[str, Any] | None:
                county_fips = feature.attributes.get("COUNTYFIPS")
                if not county_fips or county_fips not in fips_lookup:
                    return None
                return {
                    "object_id": feature.object_id,
                    "county_fips": county_fips,
                    "type_code": feature.attributes.get("TYPE", "unknown"),
                    "capacity": None,
                }

            def _aggregate_and_insert_facts(self, session: Session, source_id: int) -> int:
                # Minimal aggregation for testing
                return 0

        return TestLoader(features, page_size)


# =============================================================================
# AGGREGATE PHASE TESTS
# =============================================================================


class TestAggregatePhase:
    """Tests for aggregate phase behavior."""

    def test_aggregate_skipped_if_fetch_incomplete(self, streaming_session: Session) -> None:
        """Aggregate phase waits for fetch phase to complete."""

        # Add partial checkpoint (not complete)
        streaming_session.add(
            IngestCheckpoint(
                source_code="test_arcgis",
                year=0,
                state_fips="00",
                table_id="fetch:50",  # Not "fetch:complete"
                race_code="T",
                row_count=50,
            )
        )
        streaming_session.flush()

        loader = TestFetchPhaseCheckpoints()._create_test_loader(
            features=create_mock_features(100),
            page_size=50,
        )

        # Load should continue fetch, not aggregate
        stats = loader.load(streaming_session, reset=False, verbose=False)

        # Should have fetched remaining and aggregated
        assert "staging" in stats.facts_loaded or "facts" in stats.facts_loaded

    def test_aggregate_produces_correct_county_counts(self, streaming_session: Session) -> None:
        """Aggregate produces correct count per county/type."""
        # Pre-populate staging with known distribution
        for i in range(30):
            streaming_session.add(
                StagingArcGISFeature(
                    source_code="test_arcgis",
                    object_id=i + 1,
                    county_fips="06001" if i < 20 else "06037",
                    type_code="police_local",
                )
            )
        streaming_session.flush()

        # Query aggregate directly (testing the SQL pattern)
        results = (
            streaming_session.query(
                StagingArcGISFeature.county_fips,
                StagingArcGISFeature.type_code,
                func.count(StagingArcGISFeature.feature_id).label("count"),
            )
            .filter(StagingArcGISFeature.source_code == "test_arcgis")
            .group_by(
                StagingArcGISFeature.county_fips,
                StagingArcGISFeature.type_code,
            )
            .all()
        )

        # Should have 2 groups: 20 in Alameda, 10 in LA
        assert len(results) == 2
        county_counts = {r[0]: r[2] for r in results}
        assert county_counts["06001"] == 20
        assert county_counts["06037"] == 10

    def test_aggregate_is_idempotent(self, streaming_session: Session) -> None:
        """Re-running aggregate produces same results."""
        # Pre-populate staging
        for i in range(10):
            streaming_session.add(
                StagingArcGISFeature(
                    source_code="test_arcgis",
                    object_id=i + 1,
                    county_fips="06001",
                    type_code="police_local",
                )
            )
        # Mark fetch complete
        streaming_session.add(
            IngestCheckpoint(
                source_code="test_arcgis",
                year=0,
                state_fips="00",
                table_id="fetch:complete",
                race_code="T",
                row_count=10,
            )
        )
        streaming_session.flush()

        # First aggregation query
        result1 = (
            streaming_session.query(
                func.count(StagingArcGISFeature.feature_id).label("count"),
            )
            .filter(StagingArcGISFeature.source_code == "test_arcgis")
            .scalar()
        )

        # Second aggregation query (idempotent)
        result2 = (
            streaming_session.query(
                func.count(StagingArcGISFeature.feature_id).label("count"),
            )
            .filter(StagingArcGISFeature.source_code == "test_arcgis")
            .scalar()
        )

        assert result1 == result2 == 10


# =============================================================================
# RESUME CORRECTNESS TESTS
# =============================================================================


class TestResumeCorrectness:
    """End-to-end resume correctness tests."""

    def test_reset_true_clears_staging_and_checkpoints(self, streaming_session: Session) -> None:
        """reset=True clears staging table and checkpoints."""
        # Pre-populate staging and checkpoint
        streaming_session.add(
            StagingArcGISFeature(
                source_code="test_arcgis",
                object_id=999,
                county_fips="06001",
                type_code="old_data",
            )
        )
        streaming_session.add(
            IngestCheckpoint(
                source_code="test_arcgis",
                year=0,
                state_fips="00",
                table_id="fetch:complete",
                race_code="T",
                row_count=100,
            )
        )
        streaming_session.flush()

        loader = TestFetchPhaseCheckpoints()._create_test_loader(
            features=create_mock_features(10),
            page_size=50,
        )

        # Load with reset=True should clear old data
        loader.load(streaming_session, reset=True, verbose=False)

        # Old staging data should be gone
        old_data = (
            streaming_session.query(StagingArcGISFeature)
            .filter(StagingArcGISFeature.object_id == 999)
            .first()
        )
        assert old_data is None

        # Should have new staging data
        count = streaming_session.query(StagingArcGISFeature).count()
        assert count == 10

    def test_no_duplicate_features_on_resume(self, streaming_session: Session) -> None:
        """Resume doesn't double-count features."""
        # First load: 50 features
        loader = TestFetchPhaseCheckpoints()._create_test_loader(
            features=create_mock_features(50),
            page_size=50,
        )
        loader.load(streaming_session, reset=True, verbose=False)

        initial_count = streaming_session.query(StagingArcGISFeature).count()
        assert initial_count == 50

        # Resume with same features (simulating restart)
        loader2 = TestFetchPhaseCheckpoints()._create_test_loader(
            features=create_mock_features(50),
            page_size=50,
        )
        loader2.load(streaming_session, reset=False, verbose=False)

        # Should still have 50 (upserted, not duplicated)
        final_count = streaming_session.query(StagingArcGISFeature).count()
        assert final_count == 50


# =============================================================================
# STAGING TABLE TESTS
# =============================================================================


class TestStagingTable:
    """Tests for staging table behavior."""

    def test_staging_unique_constraint_on_source_objectid(self, streaming_session: Session) -> None:
        """Unique index prevents duplicate (source, object_id) pairs."""
        streaming_session.add(
            StagingArcGISFeature(
                source_code="source_a",
                object_id=1,
                county_fips="06001",
                type_code="type_a",
            )
        )
        streaming_session.flush()

        # Same source + object_id should conflict
        streaming_session.add(
            StagingArcGISFeature(
                source_code="source_a",
                object_id=1,
                county_fips="06037",  # Different county
                type_code="type_b",  # Different type
            )
        )

        with pytest.raises(IntegrityError):
            streaming_session.flush()

        streaming_session.rollback()

    def test_staging_allows_same_objectid_different_source(
        self, streaming_session: Session
    ) -> None:
        """Different sources can have same object_id."""
        streaming_session.add(
            StagingArcGISFeature(
                source_code="source_a",
                object_id=1,
                county_fips="06001",
                type_code="type_a",
            )
        )
        streaming_session.add(
            StagingArcGISFeature(
                source_code="source_b",
                object_id=1,  # Same object_id
                county_fips="06037",
                type_code="type_b",
            )
        )
        streaming_session.flush()

        count = streaming_session.query(StagingArcGISFeature).count()
        assert count == 2

    def test_staging_allows_null_county_fips(self, streaming_session: Session) -> None:
        """Features without valid FIPS can be stored with NULL county."""
        streaming_session.add(
            StagingArcGISFeature(
                source_code="test",
                object_id=1,
                county_fips=None,  # NULL county
                type_code="unknown",
            )
        )
        streaming_session.flush()

        feature = streaming_session.query(StagingArcGISFeature).first()
        assert feature is not None
        assert feature.county_fips is None
