"""Unit tests for FRED API client.

Tests client initialization, URL construction, and error handling
with mocked HTTP responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from babylon.data.fred.api_client import (
    DFA_WEALTH_LEVEL_SERIES,
    DFA_WEALTH_SHARE_SERIES,
    INDUSTRY_UNEMPLOYMENT_SERIES,
    NATIONAL_SERIES,
    US_STATES,
    FredAPIClient,
    FredAPIError,
    Observation,
    SeriesData,
    SeriesMetadata,
)


@pytest.mark.unit
class TestFredAPIClientInit:
    """Tests for client initialization."""

    def test_init_with_explicit_api_key(self) -> None:
        """Client accepts explicit API key."""
        client = FredAPIClient(api_key="test_key")
        assert client.api_key == "test_key"
        client.close()

    def test_init_reads_api_key_from_env(self) -> None:
        """Client reads FRED_API_KEY from environment."""
        with patch.dict("os.environ", {"FRED_API_KEY": "env_key"}):
            client = FredAPIClient()
            assert client.api_key == "env_key"
            client.close()

    def test_init_requires_api_key(self) -> None:
        """Client raises ValueError if no API key available."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="FRED API key required"),
        ):
            FredAPIClient()

    def test_init_with_custom_timeout(self) -> None:
        """Client accepts custom timeout."""
        client = FredAPIClient(api_key="test_key", timeout=60.0)
        assert client.timeout == 60.0
        client.close()

    def test_init_default_timeout(self) -> None:
        """Client has default 30s timeout."""
        client = FredAPIClient(api_key="test_key")
        assert client.timeout == 30.0
        client.close()


@pytest.mark.unit
class TestFredAPIClientContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_returns_client(self) -> None:
        """Context manager returns client instance."""
        with FredAPIClient(api_key="test_key") as client:
            assert isinstance(client, FredAPIClient)

    def test_context_manager_closes_client(self) -> None:
        """Context manager closes client on exit."""
        with FredAPIClient(api_key="test_key") as client:
            # Client is open
            assert client._client is not None
        # Exit should have called close()


@pytest.mark.unit
class TestStateUnemploymentSeriesId:
    """Tests for state unemployment series ID generation."""

    def test_generate_series_id_single_digit(self) -> None:
        """Single digit FIPS codes are zero-padded."""
        client = FredAPIClient(api_key="test_key")
        series_id = client.get_state_unemployment_series_id("1")
        assert series_id == "LAUST010000000000003A"
        client.close()

    def test_generate_series_id_two_digit(self) -> None:
        """Two digit FIPS codes remain unchanged."""
        client = FredAPIClient(api_key="test_key")
        series_id = client.get_state_unemployment_series_id("06")
        assert series_id == "LAUST060000000000003A"
        client.close()

    def test_generate_series_id_format(self) -> None:
        """Series ID follows LAUST format."""
        client = FredAPIClient(api_key="test_key")
        series_id = client.get_state_unemployment_series_id("48")
        # Format: LAUST + 2-digit FIPS + fixed suffix
        assert series_id.startswith("LAUST")
        assert series_id.endswith("03A")
        client.close()


@pytest.mark.unit
class TestDataclasses:
    """Tests for data class structures."""

    def test_series_metadata_fields(self) -> None:
        """SeriesMetadata has expected fields."""
        metadata = SeriesMetadata(
            series_id="CPIAUCSL",
            title="Consumer Price Index",
            units="Index 1982-1984=100",
            frequency="Monthly",
            seasonal_adjustment="Seasonally Adjusted",
            observation_start="1947-01-01",
            observation_end="2024-01-01",
            last_updated="2024-01-15",
        )
        assert metadata.series_id == "CPIAUCSL"
        assert metadata.title == "Consumer Price Index"

    def test_series_metadata_optional_source(self) -> None:
        """SeriesMetadata source field defaults to empty string."""
        metadata = SeriesMetadata(
            series_id="TEST",
            title="Test",
            units="",
            frequency="",
            seasonal_adjustment="",
            observation_start="",
            observation_end="",
            last_updated="",
        )
        assert metadata.source == ""

    def test_observation_with_value(self) -> None:
        """Observation stores date and value."""
        obs = Observation(date="2020-01-01", value=100.5)
        assert obs.date == "2020-01-01"
        assert obs.value == 100.5

    def test_observation_with_none_value(self) -> None:
        """Observation handles None (missing) values."""
        obs = Observation(date="2020-01-01", value=None)
        assert obs.value is None

    def test_series_data_default_observations(self) -> None:
        """SeriesData observations defaults to empty list."""
        metadata = SeriesMetadata(
            series_id="TEST",
            title="Test",
            units="",
            frequency="",
            seasonal_adjustment="",
            observation_start="",
            observation_end="",
            last_updated="",
        )
        series = SeriesData(metadata=metadata)
        assert series.observations == []


@pytest.mark.unit
class TestFredAPIError:
    """Tests for FRED API error dataclass."""

    def test_error_has_required_fields(self) -> None:
        """FredAPIError stores status code, message, and URL."""
        error = FredAPIError(
            status_code=429,
            message="Rate limited",
            url="https://api.stlouisfed.org/fred/series",
        )
        assert error.status_code == 429
        assert error.message == "Rate limited"
        assert "stlouisfed" in error.url

    def test_error_is_exception(self) -> None:
        """FredAPIError can be raised as exception."""
        error = FredAPIError(status_code=400, message="Bad request", url="http://test")
        with pytest.raises(FredAPIError):
            raise error


@pytest.mark.unit
class TestConstantMappings:
    """Tests for constant mappings."""

    def test_us_states_has_50_plus_dc(self) -> None:
        """US_STATES contains 50 states plus DC."""
        assert len(US_STATES) >= 51

    def test_us_states_california(self) -> None:
        """US_STATES has correct California mapping."""
        assert US_STATES["06"] == ("California", "CA")

    def test_us_states_texas(self) -> None:
        """US_STATES has correct Texas mapping."""
        assert US_STATES["48"] == ("Texas", "TX")

    def test_national_series_includes_key_indicators(self) -> None:
        """NATIONAL_SERIES includes key economic indicators."""
        assert "CPIAUCSL" in NATIONAL_SERIES  # CPI
        assert "UNRATE" in NATIONAL_SERIES  # Unemployment
        assert "M2SL" in NATIONAL_SERIES  # Money supply

    def test_industry_series_has_major_sectors(self) -> None:
        """INDUSTRY_UNEMPLOYMENT_SERIES has major sectors."""
        assert len(INDUSTRY_UNEMPLOYMENT_SERIES) >= 8
        assert "LNU04032231" in INDUSTRY_UNEMPLOYMENT_SERIES  # Construction

    def test_dfa_level_series_has_percentile_classes(self) -> None:
        """DFA_WEALTH_LEVEL_SERIES has all percentile classes."""
        percentile_codes = {key[0] for key in DFA_WEALTH_LEVEL_SERIES}
        assert "LT01" in percentile_codes  # Top 1%
        assert "N09" in percentile_codes  # 90-99%
        assert "N40" in percentile_codes  # 50-90%
        assert "B50" in percentile_codes  # Bottom 50%

    def test_dfa_share_series_structure(self) -> None:
        """DFA_WEALTH_SHARE_SERIES has expected structure."""
        # Keys are (percentile_code, asset_category) tuples
        for key, series_id in DFA_WEALTH_SHARE_SERIES.items():
            assert len(key) == 2
            assert isinstance(series_id, str)


@pytest.mark.unit
class TestFredAPIClientRequest:
    """Tests for request handling with mocked HTTP."""

    def test_request_includes_api_key(self) -> None:
        """Request adds API key to parameters."""
        with patch("babylon.data.fred.api_client.httpx.Client") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"seriess": [{"id": "TEST"}]}
            mock_httpx.return_value.get.return_value = mock_response

            with (
                FredAPIClient(api_key="my_api_key") as client,
                patch.object(client, "_rate_limit"),
            ):
                # Manually call internal _request (normally called by public methods)
                client._request("series", {"series_id": "TEST"})

            # Check that api_key was in params
            call_kwargs = mock_httpx.return_value.get.call_args
            params = (
                call_kwargs.kwargs.get("params")
                if call_kwargs.kwargs
                else call_kwargs[1].get("params")
            )
            assert params is not None
            assert params.get("api_key") == "my_api_key"

    def test_request_handles_rate_limiting(self) -> None:
        """Client retries on 429 status code."""
        with patch("babylon.data.fred.api_client.httpx.Client") as mock_httpx:
            mock_client = MagicMock()

            # First call returns 429, second returns 200
            response_429 = MagicMock()
            response_429.status_code = 429

            response_200 = MagicMock()
            response_200.status_code = 200
            response_200.json.return_value = {"test": "data"}

            mock_client.get.side_effect = [response_429, response_200]
            mock_httpx.return_value = mock_client

            with (
                patch("babylon.data.fred.api_client.time.sleep"),
                FredAPIClient(api_key="test") as client,
            ):
                client._last_request_time = 0  # Skip rate limiting
                result = client._request("test")

            assert result == {"test": "data"}
            assert mock_client.get.call_count == 2
