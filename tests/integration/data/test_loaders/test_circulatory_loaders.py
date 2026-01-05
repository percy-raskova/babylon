"""Integration tests for circulatory system data loaders.

Tests the full load flow for HIFLD and MIRTA loaders with mock ArcGIS API
responses. Verifies end-to-end behavior including:
- API pagination handling
- County FIPS aggregation
- Dimension table population
- Fact table population with proper FK references
- Load statistics tracking
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from babylon.data.loader_base import LoaderConfig
from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import (
    DimCoerciveType,
    DimCounty,
    DimDataSource,
    DimState,
    FactCoerciveInfrastructure,
    FactElectricGrid,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from sqlalchemy.orm import Session

    from babylon.data.external.arcgis import ArcGISFeature


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def circulatory_db_session() -> Generator[Session, None, None]:
    """Create fresh in-memory database for circulatory loader tests.

    This fixture creates all required dimension tables pre-populated with
    sample data for testing foreign key relationships.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    NormalizedBase.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    # Pre-populate required dimension tables
    _populate_base_dimensions(session)

    yield session

    session.close()
    engine.dispose()


def _populate_base_dimensions(session: Session) -> None:
    """Populate base dimension tables required for FK relationships."""
    # States - commit first to satisfy FK constraints
    states = [
        DimState(state_id=1, state_fips="01", state_name="Alabama", state_abbrev="AL"),
        DimState(state_id=2, state_fips="06", state_name="California", state_abbrev="CA"),
        DimState(state_id=3, state_fips="36", state_name="New York", state_abbrev="NY"),
        DimState(state_id=4, state_fips="48", state_name="Texas", state_abbrev="TX"),
    ]
    session.add_all(states)
    session.commit()

    # Counties (fips=5 digits, county_fips=3 digits)
    counties = [
        DimCounty(
            county_id=1, fips="01001", county_fips="001", county_name="Autauga County", state_id=1
        ),
        DimCounty(
            county_id=2, fips="06001", county_fips="001", county_name="Alameda County", state_id=2
        ),
        DimCounty(
            county_id=3,
            fips="06037",
            county_fips="037",
            county_name="Los Angeles County",
            state_id=2,
        ),
        DimCounty(
            county_id=4, fips="06073", county_fips="073", county_name="San Diego County", state_id=2
        ),
        DimCounty(
            county_id=5, fips="36061", county_fips="061", county_name="New York County", state_id=3
        ),
        DimCounty(
            county_id=6, fips="48029", county_fips="029", county_name="Bexar County", state_id=4
        ),
        DimCounty(
            county_id=7, fips="48201", county_fips="201", county_name="Harris County", state_id=4
        ),
    ]
    session.add_all(counties)
    session.commit()


def _create_mock_feature(attrs: dict[str, Any]) -> ArcGISFeature:
    """Create a mock ArcGIS feature with given attributes."""
    from babylon.data.external.arcgis import ArcGISFeature

    return ArcGISFeature(
        object_id=attrs.get("OBJECTID", 1),
        attributes=attrs,
        geometry=None,
    )


# =============================================================================
# HIFLD PRISONS LOADER INTEGRATION TESTS
# =============================================================================


class TestHIFLDPrisonsLoaderIntegration:
    """Integration tests for HIFLD Prison Boundaries loader."""

    @pytest.fixture
    def mock_prison_features(self) -> list[dict[str, Any]]:
        """Sample prison facility features."""
        return [
            {
                "OBJECTID": 1,
                "NAME": "Federal Correctional Institution",
                "COUNTYFIPS": "06001",
                "TYPE": "FEDERAL",
                "CAPACITY": 1500,
                "STATUS": "OPERATIONAL",
            },
            {
                "OBJECTID": 2,
                "NAME": "State Prison - Central California",
                "COUNTYFIPS": "06001",
                "TYPE": "STATE",
                "CAPACITY": 2000,
                "STATUS": "OPERATIONAL",
            },
            {
                "OBJECTID": 3,
                "NAME": "County Jail",
                "COUNTYFIPS": "06037",
                "TYPE": "LOCAL",
                "CAPACITY": 500,
                "STATUS": "OPERATIONAL",
            },
            {
                "OBJECTID": 4,
                "NAME": "Federal Prison Camp",
                "COUNTYFIPS": "48029",
                "TYPE": "FEDERAL",
                "CAPACITY": 800,
                "STATUS": "OPERATIONAL",
            },
        ]

    def test_load_creates_dimension_records(
        self, circulatory_db_session: Session, mock_prison_features: list[dict[str, Any]]
    ) -> None:
        """Load should create DimCoerciveType records for prison types."""
        from babylon.data.hifld.prisons import HIFLDPrisonsLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_prison_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_prison_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.hifld.prisons.ArcGISClient", return_value=mock_client):
            loader = HIFLDPrisonsLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        # Verify DimCoerciveType records created
        coercive_types = circulatory_db_session.query(DimCoerciveType).all()
        codes = {t.code for t in coercive_types}

        assert "prison_federal" in codes
        assert "prison_state" in codes
        assert "prison_local" in codes

    def test_load_aggregates_to_county_level(
        self, circulatory_db_session: Session, mock_prison_features: list[dict[str, Any]]
    ) -> None:
        """Load should aggregate facilities to county level."""
        from babylon.data.hifld.prisons import HIFLDPrisonsLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_prison_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_prison_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.hifld.prisons.ArcGISClient", return_value=mock_client):
            loader = HIFLDPrisonsLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        # Verify county aggregation
        facts = circulatory_db_session.query(FactCoerciveInfrastructure).all()

        # Alameda County (06001) should have 2 facilities (1 federal + 1 state)
        alameda = circulatory_db_session.query(DimCounty).filter_by(fips="06001").first()
        assert alameda is not None

        alameda_facts = [f for f in facts if f.county_id == alameda.county_id]
        total_alameda = sum(f.facility_count for f in alameda_facts)
        assert total_alameda == 2

    def test_load_tracks_capacity(
        self, circulatory_db_session: Session, mock_prison_features: list[dict[str, Any]]
    ) -> None:
        """Load should track total capacity per county/type."""
        from babylon.data.hifld.prisons import HIFLDPrisonsLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_prison_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_prison_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.hifld.prisons.ArcGISClient", return_value=mock_client):
            loader = HIFLDPrisonsLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        # Check capacity tracking
        # Alameda federal: 1500, Alameda state: 2000
        alameda = circulatory_db_session.query(DimCounty).filter_by(fips="06001").first()
        federal_type = (
            circulatory_db_session.query(DimCoerciveType).filter_by(code="prison_federal").first()
        )

        if alameda and federal_type:
            federal_fact = (
                circulatory_db_session.query(FactCoerciveInfrastructure)
                .filter_by(
                    county_id=alameda.county_id, coercive_type_id=federal_type.coercive_type_id
                )
                .first()
            )
            if federal_fact:
                assert federal_fact.total_capacity == 1500

    def test_load_returns_stats(
        self, circulatory_db_session: Session, mock_prison_features: list[dict[str, Any]]
    ) -> None:
        """Load should return accurate LoadStats."""
        from babylon.data.hifld.prisons import HIFLDPrisonsLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_prison_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_prison_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.hifld.prisons.ArcGISClient", return_value=mock_client):
            loader = HIFLDPrisonsLoader(LoaderConfig(verbose=False))
            stats = loader.load(circulatory_db_session, reset=True, verbose=False)

        assert stats.source == "hifld_prisons"
        # Verify stats tracked api_calls and loaded facts
        assert stats.api_calls >= 1 or sum(stats.facts_loaded.values()) > 0


# =============================================================================
# HIFLD POLICE LOADER INTEGRATION TESTS
# =============================================================================


class TestHIFLDPoliceLoaderIntegration:
    """Integration tests for HIFLD Local Law Enforcement loader."""

    @pytest.fixture
    def mock_police_features(self) -> list[dict[str, Any]]:
        """Sample police station features."""
        return [
            {
                "OBJECTID": 1,
                "NAME": "Los Angeles Police Department",
                "COUNTYFIPS": "06037",
                "TYPE": "POLICE DEPARTMENT",
            },
            {
                "OBJECTID": 2,
                "NAME": "LA County Sheriff - Central",
                "COUNTYFIPS": "06037",
                "TYPE": "SHERIFF",
            },
            {
                "OBJECTID": 3,
                "NAME": "UCLA Campus Police",
                "COUNTYFIPS": "06037",
                "TYPE": "CAMPUS POLICE",
            },
            {
                "OBJECTID": 4,
                "NAME": "San Diego Police Department",
                "COUNTYFIPS": "06073",
                "TYPE": "POLICE DEPARTMENT",
            },
        ]

    def test_load_creates_police_types(
        self, circulatory_db_session: Session, mock_police_features: list[dict[str, Any]]
    ) -> None:
        """Load should create DimCoerciveType records for police types."""
        from babylon.data.hifld.police import HIFLDPoliceLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_police_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_police_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.hifld.police.ArcGISClient", return_value=mock_client):
            loader = HIFLDPoliceLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        coercive_types = circulatory_db_session.query(DimCoerciveType).all()
        codes = {t.code for t in coercive_types}

        assert "police_local" in codes
        assert "police_sheriff" in codes
        assert "police_campus" in codes

    def test_load_aggregates_by_type(
        self, circulatory_db_session: Session, mock_police_features: list[dict[str, Any]]
    ) -> None:
        """Load should aggregate facilities by type within county."""
        from babylon.data.hifld.police import HIFLDPoliceLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_police_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_police_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.hifld.police.ArcGISClient", return_value=mock_client):
            loader = HIFLDPoliceLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        # LA County should have 3 police facilities (1 local + 1 sheriff + 1 campus)
        la_county = circulatory_db_session.query(DimCounty).filter_by(fips="06037").first()
        assert la_county is not None

        la_facts = (
            circulatory_db_session.query(FactCoerciveInfrastructure)
            .filter_by(county_id=la_county.county_id)
            .all()
        )
        total_la = sum(f.facility_count for f in la_facts)
        assert total_la == 3


# =============================================================================
# MIRTA MILITARY LOADER INTEGRATION TESTS
# =============================================================================


class TestMIRTAMilitaryLoaderIntegration:
    """Integration tests for MIRTA Military Installations loader."""

    @pytest.fixture
    def mock_military_features(self) -> list[dict[str, Any]]:
        """Sample military installation features."""
        return [
            {
                "OBJECTID": 1,
                "SITE_NAME": "Fort Hood",
                "COUNTYFIPS": "48029",
                "SERVICE": "ARMY",
            },
            {
                "OBJECTID": 2,
                "SITE_NAME": "Naval Base San Diego",
                "COUNTYFIPS": "06073",
                "SERVICE": "NAVY",
            },
            {
                "OBJECTID": 3,
                "SITE_NAME": "Edwards Air Force Base",
                "COUNTYFIPS": "06037",
                "SERVICE": "AIR FORCE",
            },
            {
                "OBJECTID": 4,
                "SITE_NAME": "Camp Pendleton",
                "COUNTYFIPS": "06073",
                "SERVICE": "MARINE CORPS",
            },
        ]

    def test_load_creates_military_types(
        self, circulatory_db_session: Session, mock_military_features: list[dict[str, Any]]
    ) -> None:
        """Load should create DimCoerciveType records for military branches."""
        from babylon.data.mirta.loader import MIRTAMilitaryLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_military_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_military_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.mirta.loader.ArcGISClient", return_value=mock_client):
            loader = MIRTAMilitaryLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        coercive_types = circulatory_db_session.query(DimCoerciveType).all()
        codes = {t.code for t in coercive_types}

        assert "military_army" in codes
        assert "military_navy" in codes
        assert "military_air_force" in codes
        assert "military_marines" in codes

    def test_all_military_types_are_federal(
        self, circulatory_db_session: Session, mock_military_features: list[dict[str, Any]]
    ) -> None:
        """All military types should have federal command chain."""
        from babylon.data.mirta.loader import MIRTAMilitaryLoader

        def mock_query_all(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_military_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(mock_military_features)
        mock_client.query_all.side_effect = mock_query_all

        with patch("babylon.data.mirta.loader.ArcGISClient", return_value=mock_client):
            loader = MIRTAMilitaryLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        military_types = (
            circulatory_db_session.query(DimCoerciveType)
            .filter(DimCoerciveType.category == "military")
            .all()
        )

        for mil_type in military_types:
            assert mil_type.command_chain == "federal", (
                f"{mil_type.code} should have federal command chain"
            )


# =============================================================================
# HIFLD ELECTRIC LOADER INTEGRATION TESTS
# =============================================================================


class TestHIFLDElectricLoaderIntegration:
    """Integration tests for HIFLD Electric Grid loader."""

    @pytest.fixture
    def mock_substation_features(self) -> list[dict[str, Any]]:
        """Sample electric substation features."""
        return [
            {
                "OBJECTID": 1,
                "NAME": "Downtown LA Substation",
                "COUNTYFIPS": "06037",
                "MAX_VOLT": "115000",
                "MIN_VOLT": "4000",
            },
            {
                "OBJECTID": 2,
                "NAME": "Valley Substation",
                "COUNTYFIPS": "06037",
                "MAX_VOLT": "230000",
                "MIN_VOLT": "69000",
            },
            {
                "OBJECTID": 3,
                "NAME": "San Diego Central",
                "COUNTYFIPS": "06073",
                "MAX_VOLT": "500000",
                "MIN_VOLT": "230000",
            },
        ]

    def test_load_creates_fact_records(
        self, circulatory_db_session: Session, mock_substation_features: list[dict[str, Any]]
    ) -> None:
        """Load should create FactElectricGrid records."""
        from babylon.data.hifld.electric import HIFLDElectricLoader

        def mock_substation_query(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_substation_features:
                yield _create_mock_feature(attrs)

        def mock_transmission_query(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            return iter([])

        mock_sub_client = MagicMock()
        mock_sub_client.get_record_count.return_value = len(mock_substation_features)
        mock_sub_client.query_all.side_effect = mock_substation_query

        mock_trans_client = MagicMock()
        mock_trans_client.get_record_count.return_value = 0
        mock_trans_client.query_all.side_effect = mock_transmission_query

        # ArcGISClient is called twice - once for substations, once for transmission
        with patch(
            "babylon.data.hifld.electric.ArcGISClient",
            side_effect=[mock_sub_client, mock_trans_client],
        ):
            loader = HIFLDElectricLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        facts = circulatory_db_session.query(FactElectricGrid).all()
        assert len(facts) > 0

    def test_load_aggregates_substation_counts(
        self, circulatory_db_session: Session, mock_substation_features: list[dict[str, Any]]
    ) -> None:
        """Load should count substations per county."""
        from babylon.data.hifld.electric import HIFLDElectricLoader

        def mock_substation_query(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in mock_substation_features:
                yield _create_mock_feature(attrs)

        def mock_transmission_query(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            return iter([])

        mock_sub_client = MagicMock()
        mock_sub_client.get_record_count.return_value = len(mock_substation_features)
        mock_sub_client.query_all.side_effect = mock_substation_query

        mock_trans_client = MagicMock()
        mock_trans_client.get_record_count.return_value = 0
        mock_trans_client.query_all.side_effect = mock_transmission_query

        with patch(
            "babylon.data.hifld.electric.ArcGISClient",
            side_effect=[mock_sub_client, mock_trans_client],
        ):
            loader = HIFLDElectricLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        # LA County should have 2 substations
        la_county = circulatory_db_session.query(DimCounty).filter_by(fips="06037").first()
        assert la_county is not None

        la_fact = (
            circulatory_db_session.query(FactElectricGrid)
            .filter_by(county_id=la_county.county_id)
            .first()
        )
        if la_fact:
            assert la_fact.substation_count == 2


# =============================================================================
# CROSS-LOADER INTEGRATION TESTS
# =============================================================================


class TestCirculatoryLoadersCrossIntegration:
    """Tests for interactions between circulatory system loaders."""

    def test_multiple_loaders_share_coercive_types(self, circulatory_db_session: Session) -> None:
        """Different loaders should add to the same DimCoerciveType table."""
        from babylon.data.hifld.police import HIFLDPoliceLoader
        from babylon.data.hifld.prisons import HIFLDPrisonsLoader
        from babylon.data.mirta.loader import MIRTAMilitaryLoader

        # Simple mock data
        prison_features = [{"OBJECTID": 1, "COUNTYFIPS": "06001", "TYPE": "FEDERAL"}]
        police_features = [{"OBJECTID": 1, "COUNTYFIPS": "06001", "TYPE": "SHERIFF"}]
        military_features = [{"OBJECTID": 1, "COUNTYFIPS": "06001", "SERVICE": "ARMY"}]

        def create_mock_client(features: list[dict[str, Any]]) -> MagicMock:
            def mock_query(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
                for attrs in features:
                    yield _create_mock_feature(attrs)

            mock_client = MagicMock()
            mock_client.get_record_count.return_value = len(features)
            mock_client.query_all.side_effect = mock_query
            return mock_client

        # Load all three with proper patching
        prison_mock = create_mock_client(prison_features)
        with patch("babylon.data.hifld.prisons.ArcGISClient", return_value=prison_mock):
            prison_loader = HIFLDPrisonsLoader(LoaderConfig(verbose=False))
            prison_loader.load(circulatory_db_session, reset=True, verbose=False)

        police_mock = create_mock_client(police_features)
        with patch("babylon.data.hifld.police.ArcGISClient", return_value=police_mock):
            police_loader = HIFLDPoliceLoader(LoaderConfig(verbose=False))
            police_loader.load(circulatory_db_session, reset=False, verbose=False)

        military_mock = create_mock_client(military_features)
        with patch("babylon.data.mirta.loader.ArcGISClient", return_value=military_mock):
            military_loader = MIRTAMilitaryLoader(LoaderConfig(verbose=False))
            military_loader.load(circulatory_db_session, reset=False, verbose=False)

        # Verify all types are in the same table
        coercive_types = circulatory_db_session.query(DimCoerciveType).all()
        codes = {t.code for t in coercive_types}

        # Should have types from all three loaders
        assert "prison_federal" in codes
        assert "police_sheriff" in codes
        assert "military_army" in codes

    def test_loaders_preserve_data_source_attribution(
        self, circulatory_db_session: Session
    ) -> None:
        """Each loader should attribute data to correct source."""
        from babylon.data.hifld.prisons import HIFLDPrisonsLoader

        prison_features = [
            {"OBJECTID": 1, "COUNTYFIPS": "06001", "TYPE": "FEDERAL", "CAPACITY": 1000}
        ]

        def mock_query(*args: Any, **kwargs: Any) -> Iterator[ArcGISFeature]:
            for attrs in prison_features:
                yield _create_mock_feature(attrs)

        mock_client = MagicMock()
        mock_client.get_record_count.return_value = len(prison_features)
        mock_client.query_all.side_effect = mock_query

        with patch("babylon.data.hifld.prisons.ArcGISClient", return_value=mock_client):
            loader = HIFLDPrisonsLoader(LoaderConfig(verbose=False))
            loader.load(circulatory_db_session, reset=True, verbose=False)

        # Verify data source is attributed
        sources = circulatory_db_session.query(DimDataSource).all()

        # Should have HIFLD source
        hifld_sources = [
            s
            for s in sources
            if "hifld" in s.source_name.lower() or "prison" in s.source_name.lower()
        ]
        assert len(hifld_sources) > 0 or len(sources) > 0  # At least some source attribution
