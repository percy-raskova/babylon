"""Unit tests for Census API client.

Tests client initialization, URL construction, and response parsing
with mocked HTTP responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from babylon.data.census.api_client import (
    DEFAULT_DATASET,
    DEFAULT_YEAR,
    CensusAPIClient,
    CensusAPIError,
    CountyData,
    VariableMetadata,
)


@pytest.mark.unit
class TestCensusAPIClientInit:
    """Tests for client initialization."""

    def test_init_with_explicit_api_key(self) -> None:
        """Client accepts explicit API key."""
        client = CensusAPIClient(api_key="test_key")
        assert client.api_key == "test_key"
        client.close()

    def test_init_reads_api_key_from_env(self) -> None:
        """Client reads CENSUS_API_KEY from environment."""
        with patch.dict("os.environ", {"CENSUS_API_KEY": "env_key"}):
            client = CensusAPIClient()
            assert client.api_key == "env_key"
            client.close()

    def test_init_without_api_key_allowed(self) -> None:
        """Client can initialize without API key (lower rate limits)."""
        with patch.dict("os.environ", {}, clear=True):
            client = CensusAPIClient()
            assert client.api_key is None
            client.close()

    def test_init_default_year(self) -> None:
        """Client uses DEFAULT_YEAR by default."""
        client = CensusAPIClient()
        assert client.year == DEFAULT_YEAR
        client.close()

    def test_init_custom_year(self) -> None:
        """Client accepts custom year."""
        client = CensusAPIClient(year=2020)
        assert client.year == 2020
        client.close()

    def test_init_default_dataset(self) -> None:
        """Client uses DEFAULT_DATASET by default."""
        client = CensusAPIClient()
        assert client.dataset == DEFAULT_DATASET
        client.close()


@pytest.mark.unit
class TestCensusAPIClientContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_returns_client(self) -> None:
        """Context manager returns client instance."""
        with CensusAPIClient() as client:
            assert isinstance(client, CensusAPIClient)

    def test_context_manager_closes_client(self) -> None:
        """Context manager closes client on exit."""
        with CensusAPIClient() as client:
            assert client._client is not None


@pytest.mark.unit
class TestBaseEndpoint:
    """Tests for endpoint URL construction."""

    def test_base_endpoint_format(self) -> None:
        """Base endpoint includes year and dataset."""
        client = CensusAPIClient(year=2022)
        endpoint = client.base_endpoint
        assert "2022" in endpoint
        assert "acs/acs5" in endpoint
        client.close()

    def test_base_endpoint_custom_dataset(self) -> None:
        """Base endpoint uses custom dataset."""
        client = CensusAPIClient(dataset="acs/acs1")
        endpoint = client.base_endpoint
        assert "acs/acs1" in endpoint
        client.close()


@pytest.mark.unit
class TestDataclasses:
    """Tests for data class structures."""

    def test_variable_metadata_fields(self) -> None:
        """VariableMetadata has expected fields."""
        metadata = VariableMetadata(
            code="B19001_001E",
            label="Estimate!!Total:",
            concept="HOUSEHOLD INCOME",
            predicate_type="int",
        )
        assert metadata.code == "B19001_001E"
        assert metadata.label == "Estimate!!Total:"
        assert metadata.concept == "HOUSEHOLD INCOME"

    def test_variable_metadata_optional_fields(self) -> None:
        """VariableMetadata has optional fields."""
        metadata = VariableMetadata(code="TEST", label="Test")
        assert metadata.concept is None
        assert metadata.predicate_type is None

    def test_county_data_fields(self) -> None:
        """CountyData has expected fields."""
        county = CountyData(
            state_fips="06",
            county_fips="037",
            fips="06037",
            name="Los Angeles County, California",
            values={"B19001_001E": 3000000},
        )
        assert county.state_fips == "06"
        assert county.county_fips == "037"
        assert county.fips == "06037"
        assert county.name == "Los Angeles County, California"
        assert county.values["B19001_001E"] == 3000000

    def test_county_data_default_values(self) -> None:
        """CountyData values defaults to empty dict."""
        county = CountyData(
            state_fips="06",
            county_fips="037",
            fips="06037",
            name="Test County",
        )
        assert county.values == {}


@pytest.mark.unit
class TestCensusAPIError:
    """Tests for Census API error dataclass."""

    def test_error_has_required_fields(self) -> None:
        """CensusAPIError stores status code, message, and URL."""
        error = CensusAPIError(
            status_code=400,
            message="Invalid table",
            url="https://api.census.gov/data",
        )
        assert error.status_code == 400
        assert error.message == "Invalid table"
        assert "census.gov" in error.url

    def test_error_is_exception(self) -> None:
        """CensusAPIError can be raised as exception."""
        error = CensusAPIError(status_code=400, message="Bad request", url="http://test")
        with pytest.raises(CensusAPIError):
            raise error


@pytest.mark.unit
class TestParseValue:
    """Tests for value parsing static method."""

    def test_parse_integer_value(self) -> None:
        """Parses integer string to int."""
        result = CensusAPIClient._parse_value("12345")
        assert result == 12345
        assert isinstance(result, int)

    def test_parse_float_value(self) -> None:
        """Parses float string to float."""
        result = CensusAPIClient._parse_value("123.45")
        assert result == 123.45
        assert isinstance(result, float)

    def test_parse_none(self) -> None:
        """Returns None for None input."""
        assert CensusAPIClient._parse_value(None) is None

    def test_parse_missing_indicators(self) -> None:
        """Returns None for Census missing value indicators."""
        missing_values = ["", "-", "N", "(X)", "**", "***", "null", "-666666666"]
        for val in missing_values:
            assert CensusAPIClient._parse_value(val) is None

    def test_parse_already_numeric(self) -> None:
        """Returns numeric values unchanged."""
        assert CensusAPIClient._parse_value(100) == 100
        assert CensusAPIClient._parse_value(100.5) == 100.5


@pytest.mark.unit
class TestCensusAPIClientRequest:
    """Tests for request handling with mocked HTTP."""

    def test_request_adds_api_key_when_available(self) -> None:
        """Request includes API key in parameters if available."""
        with patch("babylon.data.census.api_client.httpx.Client") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [["header"], ["data"]]
            mock_httpx.return_value.get.return_value = mock_response

            with (
                CensusAPIClient(api_key="my_api_key") as client,
                patch.object(client, "_rate_limit"),
            ):
                client._request(client.base_endpoint, {"get": "NAME"})

            call_kwargs = mock_httpx.return_value.get.call_args
            params = (
                call_kwargs.kwargs.get("params")
                if call_kwargs.kwargs
                else call_kwargs[1].get("params")
            )
            assert params is not None
            assert params.get("key") == "my_api_key"

    def test_request_handles_204_no_content(self) -> None:
        """Client returns empty list for 204 status."""
        with patch("babylon.data.census.api_client.httpx.Client") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_httpx.return_value.get.return_value = mock_response

            with CensusAPIClient() as client, patch.object(client, "_rate_limit"):
                result = client._request(client.base_endpoint)

            assert result == []

    def test_request_handles_rate_limiting(self) -> None:
        """Client retries on 429 status code."""
        with patch("babylon.data.census.api_client.httpx.Client") as mock_httpx:
            mock_client = MagicMock()

            # First call returns 429, second returns 200
            response_429 = MagicMock()
            response_429.status_code = 429

            response_200 = MagicMock()
            response_200.status_code = 200
            response_200.json.return_value = [["header"], ["data"]]

            mock_client.get.side_effect = [response_429, response_200]
            mock_httpx.return_value = mock_client

            with (
                patch("babylon.data.census.api_client.time.sleep"),
                CensusAPIClient() as client,
            ):
                client._last_request_time = 0
                result = client._request(client.base_endpoint)

            assert result == [["header"], ["data"]]
            assert mock_client.get.call_count == 2
