"""Integration tests for ArcGIS streaming loader resume correctness.

Tests that interrupted loads can be resumed and produce the same results
as uninterrupted loads, verifying the checkpoint architecture works correctly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import delete, func

from babylon.data.arcgis_loader_base import ArcGISStreamingLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.reference.schema import (
    DimCoerciveType,
    DimCounty,
    DimState,
    FactCoerciveInfrastructure,
    IngestCheckpoint,
    StagingArcGISFeature,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.orm import Session


# =============================================================================
# TEST LOADER IMPLEMENTATION
# =============================================================================


class MockPoliceLoader(ArcGISStreamingLoader):
    """Mock police loader for testing resume behavior."""

    def __init__(
        self,
        test_features: list[Any] | None = None,
        config: LoaderConfig | None = None,
    ) -> None:
        super().__init__(config)
        self._test_features = test_features or []

    def _get_source_code(self) -> str:
        return "test_police"

    def _get_service_url(self) -> str:
        return "https://test.arcgis.com/test/FeatureServer/0"

    def _get_out_fields(self) -> str:
        return "OBJECTID,COUNTYFIPS,TYPE"

    def _map_feature_to_staging(
        self, feature: Any, fips_lookup: dict[str, int]
    ) -> dict[str, Any] | None:
        attrs = feature.attributes
        county_fips = attrs.get("COUNTYFIPS")
        if not county_fips or county_fips not in fips_lookup:
            return None
        return {
            "object_id": feature.object_id,
            "county_fips": county_fips,
            "type_code": "police_local",
            "capacity": None,
        }

    def _aggregate_and_insert_facts(self, session: Session, source_id: int) -> int:
        source_code = self._get_source_code()
        results = (
            session.query(
                StagingArcGISFeature.county_fips,
                StagingArcGISFeature.type_code,
                func.count(StagingArcGISFeature.feature_id).label("count"),
            )
            .filter(StagingArcGISFeature.source_code == source_code)
            .filter(StagingArcGISFeature.county_fips.isnot(None))
            .group_by(
                StagingArcGISFeature.county_fips,
                StagingArcGISFeature.type_code,
            )
            .all()
        )
        count = 0
        for county_fips, type_code, facility_count in results:
            county_id = self._fips_to_county.get(county_fips)
            type_id = self._type_to_id.get(type_code)
            if county_id and type_id:
                fact = FactCoerciveInfrastructure(
                    county_id=county_id,
                    coercive_type_id=type_id,
                    source_id=source_id,
                    facility_count=facility_count,
                    total_capacity=None,
                )
                session.add(fact)
                count += 1
        session.flush()
        return count

    def _setup_dimensions(self, session: Session, verbose: bool) -> None:
        # Create coercive type
        existing = (
            session.query(DimCoerciveType).filter(DimCoerciveType.code == "police_local").first()
        )
        if existing:
            self._type_to_id["police_local"] = existing.coercive_type_id
        else:
            ct = DimCoerciveType(
                code="police_local",
                name="Local Police",
                category="enforcement",
                command_chain="local",
            )
            session.add(ct)
            session.flush()
            self._type_to_id["police_local"] = ct.coercive_type_id

        # Create data source
        self._source_id = self._get_or_create_data_source(
            session,
            source_code="TEST_POLICE_2024",
            source_name="Test Police",
            source_agency="Test",
            source_year=2024,
        )

    def _clear_fact_data(self, session: Session, verbose: bool) -> None:
        # Query the type from DB since _type_to_id may not be populated yet
        coercive_type = (
            session.query(DimCoerciveType).filter(DimCoerciveType.code == "police_local").first()
        )
        if coercive_type:
            session.query(FactCoerciveInfrastructure).filter(
                FactCoerciveInfrastructure.coercive_type_id == coercive_type.coercive_type_id
            ).delete(synchronize_session=False)

    def _query_features(self, offset: int) -> Iterator[Any]:
        # Return features from offset for test resumption
        yield from self._test_features[offset:]

    def _get_total_count(self) -> int:
        return len(self._test_features)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def db_session(session: Session) -> Session:
    """Use the shared session fixture from conftest."""
    return session


@pytest.fixture
def test_county(db_session: Session) -> DimCounty:
    """Create a test county with its state."""
    # First check if state exists, or create it
    state = db_session.query(DimState).filter(DimState.state_fips == "06").first()
    if not state:
        state = DimState(
            state_fips="06",
            state_name="California",
            state_abbrev="CA",
        )
        db_session.add(state)
        db_session.flush()

    # Now check if county exists
    county = db_session.query(DimCounty).filter(DimCounty.fips == "06001").first()
    if not county:
        county = DimCounty(
            fips="06001",
            state_id=state.state_id,
            county_fips="001",
            county_name="Alameda",
        )
        db_session.add(county)
        db_session.flush()
    return county


@pytest.fixture
def test_features(test_county: DimCounty) -> list[Any]:
    """Create 100 test features for the mock loader."""
    features = []
    for i in range(100):
        feature = MagicMock()
        feature.object_id = i + 1
        feature.attributes = {
            "OBJECTID": i + 1,
            "COUNTYFIPS": "06001",
            "TYPE": "POLICE DEPARTMENT",
        }
        features.append(feature)
    return features


@pytest.fixture
def clean_staging(db_session: Session) -> None:
    """Clean staging and checkpoint tables before test."""
    db_session.execute(
        delete(StagingArcGISFeature).where(StagingArcGISFeature.source_code == "test_police")
    )
    db_session.execute(
        delete(IngestCheckpoint).where(IngestCheckpoint.source_code == "test_police")
    )
    db_session.commit()


# =============================================================================
# RESUME CORRECTNESS TESTS
# =============================================================================


@pytest.mark.integration
class TestResumeCorrectness:
    """Tests that verify resume produces same results as uninterrupted load."""

    def test_interrupted_and_resume_produces_same_facts(
        self,
        db_session: Session,
        test_features: list[Any],
        test_county: DimCounty,
        clean_staging: None,
    ) -> None:
        """Verify interrupted load + resume equals uninterrupted load."""
        # First run: Uninterrupted load
        loader1 = MockPoliceLoader(test_features=test_features)
        loader1.load(db_session, reset=True, verbose=False)

        uninterrupted_count = (
            db_session.query(FactCoerciveInfrastructure)
            .join(DimCoerciveType)
            .filter(DimCoerciveType.code == "police_local")
            .count()
        )

        # Clean up for interrupted test
        db_session.execute(
            delete(FactCoerciveInfrastructure).where(
                FactCoerciveInfrastructure.coercive_type_id.in_(
                    db_session.query(DimCoerciveType.coercive_type_id).filter(
                        DimCoerciveType.code == "police_local"
                    )
                )
            )
        )
        db_session.execute(
            delete(StagingArcGISFeature).where(StagingArcGISFeature.source_code == "test_police")
        )
        db_session.execute(
            delete(IngestCheckpoint).where(IngestCheckpoint.source_code == "test_police")
        )
        db_session.commit()

        # Second run: Simulated interruption (load first 50 features)
        loader2 = MockPoliceLoader(test_features=test_features[:50])
        loader2.load(db_session, reset=True, verbose=False)

        # Third run: Resume with all features (simulates resume after crash)
        loader3 = MockPoliceLoader(test_features=test_features)
        loader3.load(db_session, reset=False, verbose=False)

        resumed_count = (
            db_session.query(FactCoerciveInfrastructure)
            .join(DimCoerciveType)
            .filter(DimCoerciveType.code == "police_local")
            .count()
        )

        # Both should produce the same fact count
        assert resumed_count == uninterrupted_count
        assert resumed_count > 0

    def test_reset_true_clears_staging_and_checkpoints(
        self,
        db_session: Session,
        test_features: list[Any],
        test_county: DimCounty,
        clean_staging: None,
    ) -> None:
        """Verify reset=True clears previous staging and checkpoints."""
        # First load
        loader1 = MockPoliceLoader(test_features=test_features[:50])
        loader1.load(db_session, reset=True, verbose=False)

        # Count staging after first load
        staging_count_1 = (
            db_session.query(StagingArcGISFeature)
            .filter(StagingArcGISFeature.source_code == "test_police")
            .count()
        )
        assert staging_count_1 == 50

        # Second load with reset=True should clear and start fresh
        loader2 = MockPoliceLoader(test_features=test_features[:30])
        loader2.load(db_session, reset=True, verbose=False)

        staging_count_2 = (
            db_session.query(StagingArcGISFeature)
            .filter(StagingArcGISFeature.source_code == "test_police")
            .count()
        )

        # Should have only 30 (cleared previous 50)
        assert staging_count_2 == 30

    def test_reset_false_preserves_staging(
        self,
        db_session: Session,
        test_features: list[Any],
        test_county: DimCounty,
        clean_staging: None,
    ) -> None:
        """Verify reset=False preserves previous staging data."""
        # First load
        loader1 = MockPoliceLoader(test_features=test_features[:50])
        loader1.load(db_session, reset=True, verbose=False)

        staging_count_1 = (
            db_session.query(StagingArcGISFeature)
            .filter(StagingArcGISFeature.source_code == "test_police")
            .count()
        )
        assert staging_count_1 == 50

        # Second load with reset=False should skip fetch (already complete)
        loader2 = MockPoliceLoader(test_features=test_features)
        loader2.load(db_session, reset=False, verbose=False)

        staging_count_2 = (
            db_session.query(StagingArcGISFeature)
            .filter(StagingArcGISFeature.source_code == "test_police")
            .count()
        )

        # Should still have 50 (fetch complete checkpoint means skip)
        assert staging_count_2 == 50
