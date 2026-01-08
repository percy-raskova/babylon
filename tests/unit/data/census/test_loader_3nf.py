"""Unit tests for Census 3NF loader resilience."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from babylon.data.census.api_client import VariableMetadata
from babylon.data.census.loader_3nf import CensusLoader, FactTableSpec
from babylon.data.exceptions import CensusAPIError
from babylon.data.loader_base import LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimFredSeries,
    DimTime,
    FactFredNational,
    NormalizedBase,
)


@pytest.mark.unit
class TestCensusLoaderResilience:
    """Tests for Census loader error handling."""

    def test_load_fact_table_skips_state_errors(self, mocker: MockerFixture) -> None:
        """Fact table loader should skip states that fail to fetch."""
        loader = CensusLoader(LoaderConfig(api_error_policy="skip_state"))
        loader._client = MagicMock()
        loader._source_id = 1

        # Mock checkpoint helpers to allow processing (not skip any states)
        mocker.patch.object(loader, "_is_completed", return_value=False)
        mocker.patch.object(loader, "_mark_completed")

        spec = FactTableSpec(
            table_id="B19001",
            fact_class=object,
            label="Test",
            value_field="value",
        )

        fetch_mock = MagicMock(
            side_effect=[
                CensusAPIError(
                    status_code=503,
                    message="Service unavailable",
                    url="https://api.census.gov/data",
                ),
                [],
            ]
        )
        mocker.patch.object(loader, "_fetch_table_data", fetch_mock)
        session = MagicMock()
        stats = LoadStats(source="census")

        count = loader._load_fact_table(
            spec,
            session,
            ["01", "02"],
            verbose=False,
            time_id=1,
            race_id=1,
            stats=stats,
        )

        assert count == 0
        assert fetch_mock.call_count == 2

    def test_load_fact_hours_skips_state_errors(self, mocker: MockerFixture) -> None:
        """Hours loader should skip states that fail to fetch."""
        loader = CensusLoader(LoaderConfig(api_error_policy="skip_state"))
        loader._client = MagicMock()
        loader._source_id = 1

        # Mock checkpoint helpers to allow processing
        mocker.patch.object(loader, "_is_completed", return_value=False)
        mocker.patch.object(loader, "_mark_completed")
        mocker.patch.object(loader, "_fetch_variables", return_value={})

        fetch_mock = MagicMock(
            side_effect=[
                CensusAPIError(
                    status_code=503,
                    message="Service unavailable",
                    url="https://api.census.gov/data",
                ),
                [],
            ]
        )
        mocker.patch.object(loader, "_fetch_table_data", fetch_mock)
        session = MagicMock()
        stats = LoadStats(source="census")

        count = loader._load_fact_hours(
            session,
            ["01", "02"],
            verbose=False,
            time_id=1,
            race_id=1,
            stats=stats,
        )

        assert count == 0
        assert fetch_mock.call_count == 2

    def test_load_fact_income_sources_skips_state_errors(self, mocker: MockerFixture) -> None:
        """Income sources loader should skip states that fail to fetch."""
        loader = CensusLoader(LoaderConfig(api_error_policy="skip_state"))
        loader._client = MagicMock()
        loader._source_id = 1
        calls: list[tuple[str, str]] = []

        # Mock checkpoint helpers to allow processing
        mocker.patch.object(loader, "_is_completed", return_value=False)
        mocker.patch.object(loader, "_mark_completed")

        def fetch(table_id: str, state_fips: str) -> list[object]:
            calls.append((table_id, state_fips))
            if state_fips == "01" and table_id == "B19052":
                raise CensusAPIError(
                    status_code=503,
                    message="Service unavailable",
                    url="https://api.census.gov/data",
                )
            return []

        mocker.patch.object(loader, "_fetch_table_data", fetch)
        session = MagicMock()
        stats = LoadStats(source="census")

        count = loader._load_fact_income_sources(
            session,
            ["01", "02"],
            verbose=False,
            time_id=1,
            race_id=1,
            stats=stats,
        )

        assert count == 0
        assert ("B19052", "02") in calls
        assert ("B19053", "02") in calls
        assert ("B19054", "02") in calls

    def test_load_fact_table_aborts_when_policy_abort(self, mocker: MockerFixture) -> None:
        """Fact table loader should raise when policy is abort."""
        loader = CensusLoader(LoaderConfig(api_error_policy="abort"))
        loader._client = MagicMock()
        loader._source_id = 1

        # Mock checkpoint helpers to allow processing
        mocker.patch.object(loader, "_is_completed", return_value=False)
        mocker.patch.object(loader, "_mark_completed")

        spec = FactTableSpec(
            table_id="B19001",
            fact_class=object,
            label="Test",
            value_field="value",
        )

        fetch_mock = MagicMock(
            side_effect=CensusAPIError(
                status_code=503,
                message="Service unavailable",
                url="https://api.census.gov/data",
            )
        )
        mocker.patch.object(loader, "_fetch_table_data", fetch_mock)
        session = MagicMock()
        stats = LoadStats(source="census")

        with pytest.raises(CensusAPIError):
            loader._load_fact_table(
                spec,
                session,
                ["01"],
                verbose=False,
                time_id=1,
                race_id=1,
                stats=stats,
            )

    def test_race_tables_skip_when_base_table_missing(
        self,
        mocker: MockerFixture,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Race-iterated tables should skip states where base table is missing."""
        loader = CensusLoader(LoaderConfig(api_error_policy="skip_state"))
        loader._client = MagicMock()
        loader._client.year = 2010
        loader._source_id = 1
        session = MagicMock()
        stats = LoadStats(source="census")

        # Mock checkpoint helpers to allow processing
        mocker.patch.object(loader, "_is_completed", return_value=False)
        mocker.patch.object(loader, "_mark_completed")

        base_spec = FactTableSpec(
            table_id="B23025",
            fact_class=object,
            label="Test",
            value_field="value",
        )
        mocker.patch.object(loader, "_fetch_table_data", return_value=[])

        loader._load_fact_table(
            base_spec,
            session,
            ["01"],
            verbose=False,
            time_id=1,
            race_id=1,
            stats=stats,
        )

        race_spec = FactTableSpec(
            table_id="B23025A",
            fact_class=object,
            label="Test",
            value_field="value",
        )
        fetch_mock = MagicMock(return_value=[])
        mocker.patch.object(loader, "_fetch_table_data", fetch_mock)

        loader._load_fact_table(
            race_spec,
            session,
            ["01"],
            verbose=False,
            time_id=1,
            race_id=2,
            stats=stats,
        )

        assert fetch_mock.call_count == 0
        assert loader._race_table_skips_by_year[2010]["B23025"] == {"01"}

        with caplog.at_level(logging.WARNING):
            loader._log_race_table_skip_summary(2010, stats)

        assert any(
            "Skipping race-iterated tables for base table B23025" in record.message
            for record in caplog.records
        )

    def test_clear_tables_does_not_delete_shared_dims(self) -> None:
        """Census clear_tables should not delete shared dimensions."""
        engine = create_engine("duckdb:///:memory:")
        NormalizedBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        time = DimTime(year=2022, month=None, quarter=None, is_annual=True)
        series = DimFredSeries(
            series_code="TEST",
            title="Test",
            units=None,
            frequency=None,
            seasonal_adjustment=None,
            source=None,
        )
        session.add_all([time, series])
        session.flush()
        session.add(FactFredNational(series_id=series.series_id, time_id=time.time_id, value=None))
        session.commit()

        loader = CensusLoader()
        loader.clear_tables(session)
        session.commit()

        assert session.query(DimTime).count() == 1
        assert session.query(FactFredNational).count() == 1
        session.close()

    def test_load_states_skips_existing(self) -> None:
        """State loading should reuse existing dimension records."""
        loader = CensusLoader()
        loader._client = MagicMock()
        loader._client.get_all_states.return_value = [("01", "Alabama")]

        existing_state = SimpleNamespace(
            state_id=9,
            state_fips="01",
            state_name="Alabama",
            state_abbrev="AL",
        )
        query_mock = MagicMock()
        query_mock.all.return_value = [existing_state]
        session = MagicMock()
        session.query.return_value = query_mock

        count = loader._load_states(session, ["01"], verbose=False)

        assert count == 0
        assert loader._state_fips_to_id["01"] == 9
        session.add.assert_not_called()

    def test_load_counties_skips_existing(self) -> None:
        """County loading should reuse existing dimension records."""
        loader = CensusLoader()
        loader._client = MagicMock()
        loader._state_fips_to_id = {"01": 9}
        loader._client.get_county_data.return_value = [
            SimpleNamespace(
                fips="01001",
                county_fips="001",
                name="Autauga County, AL",
                values={},
            )
        ]

        existing_county = SimpleNamespace(
            county_id=12,
            fips="01001",
            county_fips="001",
            county_name="Autauga County",
            state_id=9,
        )
        query_mock = MagicMock()
        query_mock.all.return_value = [existing_county]
        session = MagicMock()
        session.query.return_value = query_mock

        count = loader._load_counties(session, ["01"], verbose=False)

        assert count == 0
        assert loader._fips_to_county["01001"] == 12
        session.add.assert_not_called()

    def test_missing_table_skips_race_table_for_year(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Missing race tables should short-circuit the load for a year."""
        loader = CensusLoader()
        loader._client = MagicMock()
        loader._client.year = 2011
        loader._source_id = 1

        race_spec = FactTableSpec(
            table_id="B24080E",
            fact_class=object,
            label="Test",
            value_field="value",
            extract_gender=True,
        )
        loader._fetch_variables = MagicMock(return_value={})  # type: ignore[assignment]
        fetch_mock = MagicMock(return_value=[])
        loader._fetch_table_data = fetch_mock  # type: ignore[assignment]

        session = MagicMock()
        stats = LoadStats(source="census")

        with caplog.at_level(logging.WARNING):
            count = loader._load_fact_table(
                race_spec,
                session,
                ["01", "02"],
                verbose=False,
                time_id=1,
                race_id=2,
                stats=stats,
            )

        assert count == 0
        assert fetch_mock.call_count == 0
        assert "B24080E" in loader._missing_tables_by_year[2011]

    def test_race_table_skips_when_metadata_missing(self) -> None:
        """Race tables should skip when group metadata is missing."""
        loader = CensusLoader()
        loader._client = MagicMock()
        loader._client.year = 2021
        loader._source_id = 1

        base_vars = {
            "B19013_001E": VariableMetadata(
                code="B19013_001E",
                label="Median income",
                concept=None,
                predicate_type=None,
            )
        }

        def fetch_variables(table_id: str) -> dict[str, VariableMetadata]:
            if table_id == "B19013A":
                return {}
            if table_id == "B19013":
                return base_vars
            return {}

        loader._fetch_variables = MagicMock(side_effect=fetch_variables)  # type: ignore[assignment]
        loader._fetch_table_data = MagicMock(return_value=[])  # type: ignore[assignment]
        loader._client.get_county_data = MagicMock(return_value=[])
        loader._build_dimension_map = MagicMock(return_value={})  # type: ignore[assignment]
        loader._write_rows = MagicMock(return_value=0)  # type: ignore[assignment]

        spec = FactTableSpec(
            table_id="B19013A",
            fact_class=object,
            label="Test",
            value_field="median_income",
            scalar_var="B19013A_001E",
        )

        stats = LoadStats(source="census")
        count = loader._load_fact_table(
            spec,
            MagicMock(),
            ["01"],
            verbose=False,
            time_id=1,
            race_id=2,
            stats=stats,
        )

        assert count == 0
        assert loader._fetch_table_data.call_count == 0
        assert loader._client.get_county_data.call_count == 0
        assert "B19013" in loader._race_tables_unavailable_by_year[2021]
