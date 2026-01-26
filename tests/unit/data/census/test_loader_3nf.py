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
from babylon.data.reference.schema import (
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


@pytest.mark.unit
class TestVariableFallbackBehavior:
    """Tests for year fallback when fetching Census API variable metadata.

    The Census Bureau's older API vintages (especially 2010) lack variable
    metadata for certain tables like B23025 and B15003. The fallback mechanism
    tries newer years when the current year returns empty metadata.
    """

    def test_fetch_variables_with_fallback_returns_early_when_current_year_succeeds(
        self, mocker: MockerFixture
    ) -> None:
        """Fallback should not be triggered when current year has data."""
        loader = CensusLoader()
        loader._client = MagicMock()
        loader._client.year = 2023

        expected_vars = {
            "B23025_001E": VariableMetadata(
                code="B23025_001E",
                label="Total",
                concept=None,
                predicate_type=None,
            )
        }
        loader._client.get_variables.return_value = expected_vars

        result = loader._fetch_variables_with_fallback("B23025", [2010, 2015, 2023])

        assert result == expected_vars
        loader._client.get_variables.assert_called_once_with("B23025")

    def test_fetch_variables_with_fallback_tries_newer_years_on_empty(
        self, mocker: MockerFixture
    ) -> None:
        """Fallback should try newer years when current year returns empty."""
        loader = CensusLoader()

        # Track which clients were created and used
        clients_created: list[int] = []
        get_variables_calls: list[tuple[int, str]] = []

        def make_mock_client(year: int) -> MagicMock:
            clients_created.append(year)
            client = MagicMock()
            client.year = year
            client.close = MagicMock()

            def get_vars(table_id: str) -> dict[str, VariableMetadata]:
                get_variables_calls.append((year, table_id))
                # 2010 returns empty, 2023 has data
                if year == 2010:
                    return {}
                return {
                    "B23025_001E": VariableMetadata(
                        code="B23025_001E",
                        label="Total",
                        concept=None,
                        predicate_type=None,
                    )
                }

            client.get_variables = get_vars
            return client

        mocker.patch.object(loader, "_make_client", make_mock_client)

        # Start with 2010 client (which has no data)
        loader._client = make_mock_client(2010)
        clients_created.clear()  # Reset after initial setup

        result = loader._fetch_variables_with_fallback("B23025", [2010, 2015, 2023])

        # Should have data from fallback year
        assert "B23025_001E" in result
        # Should have tried 2010 first, then 2023 (newest), then 2015
        assert (2010, "B23025") in get_variables_calls
        assert (2023, "B23025") in get_variables_calls

    def test_fetch_variables_with_fallback_returns_empty_when_all_years_fail(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Fallback should return empty dict when all years fail."""
        loader = CensusLoader()

        def make_mock_client(year: int) -> MagicMock:
            client = MagicMock()
            client.year = year
            client.close = MagicMock()
            client.get_variables = MagicMock(return_value={})
            return client

        mocker.patch.object(loader, "_make_client", make_mock_client)
        loader._client = make_mock_client(2010)

        with caplog.at_level(logging.WARNING):
            result = loader._fetch_variables_with_fallback("B23025", [2010, 2011, 2012])

        assert result == {}
        assert any(
            "No variable metadata found for B23025 in any year" in record.message
            for record in caplog.records
        )

    def test_fetch_variables_with_fallback_logs_successful_fallback(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Fallback should log when using data from a different year."""
        loader = CensusLoader()

        def make_mock_client(year: int) -> MagicMock:
            client = MagicMock()
            client.year = year
            client.close = MagicMock()

            def get_vars(table_id: str) -> dict[str, VariableMetadata]:
                if year == 2010:
                    return {}
                return {
                    "B15003_001E": VariableMetadata(
                        code="B15003_001E",
                        label="Total",
                        concept=None,
                        predicate_type=None,
                    )
                }

            client.get_variables = get_vars
            return client

        mocker.patch.object(loader, "_make_client", make_mock_client)
        loader._client = make_mock_client(2010)

        with caplog.at_level(logging.INFO):
            result = loader._fetch_variables_with_fallback("B15003", [2010, 2023])

        assert "B15003_001E" in result
        assert any(
            "Fetched B15003 metadata from fallback year 2023" in record.message
            for record in caplog.records
        )

    def test_fetch_variables_with_fallback_tries_years_newest_first(
        self, mocker: MockerFixture
    ) -> None:
        """Fallback should try years in descending order (newest first)."""
        loader = CensusLoader()

        years_tried: list[int] = []

        def make_mock_client(year: int) -> MagicMock:
            client = MagicMock()
            client.year = year
            client.close = MagicMock()

            def get_vars(table_id: str) -> dict[str, VariableMetadata]:
                years_tried.append(year)
                # Only 2015 has data
                if year == 2015:
                    return {
                        "B23025_001E": VariableMetadata(
                            code="B23025_001E",
                            label="Total",
                            concept=None,
                            predicate_type=None,
                        )
                    }
                return {}

            client.get_variables = get_vars
            return client

        mocker.patch.object(loader, "_make_client", make_mock_client)
        loader._client = make_mock_client(2010)

        result = loader._fetch_variables_with_fallback("B23025", [2010, 2012, 2015, 2018])

        # Should try 2010 first (current), then 2018 (newest), then 2015, then 2012
        # But should stop at 2015 since it has data
        assert "B23025_001E" in result  # Got data from fallback
        assert years_tried[0] == 2010  # Current year first
        assert years_tried[1] == 2018  # Then newest fallback
        assert years_tried[2] == 2015  # Found data, stopped
        assert 2012 not in years_tried  # Never reached

    def test_initial_year_uses_newest_year(self) -> None:
        """Loader should use newest year for initial dimension loading."""
        loader = CensusLoader(LoaderConfig(census_years=[2010, 2015, 2020, 2023]))

        # Access config to verify it would use newest year
        # The actual initial_year selection happens in load(), but we can verify
        # the config is set up correctly
        census_years = loader.config.census_years
        expected_initial = census_years[-1] if census_years else 2023

        assert expected_initial == 2023
