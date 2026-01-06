"""Unit tests for EIA Energy API client.

Tests client initialization, URL construction, and response parsing
with mocked HTTP responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from babylon.data.energy.api_client import (
    MSN_BY_CATEGORY,
    PRIORITY_MSN_CODES,
    EIAAPIError,
    EnergyAPIClient,
    EnergyObservation,
    EnergySeriesData,
    EnergySeriesMetadata,
)


@pytest.mark.unit
class TestEnergyAPIClientInit:
    """Tests for client initialization."""

    def test_init_with_explicit_api_key(self) -> None:
        """Client accepts explicit API key."""
        client = EnergyAPIClient(api_key="test_key")
        assert client.api_key == "test_key"
        client.close()

    def test_init_reads_api_key_from_env(self) -> None:
        """Client reads ENERGY_API_KEY from environment."""
        with patch.dict("os.environ", {"ENERGY_API_KEY": "env_key"}):
            client = EnergyAPIClient()
            assert client.api_key == "env_key"
            client.close()

    def test_init_requires_api_key(self) -> None:
        """Client raises ValueError if no API key available."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="EIA API key required"),
        ):
            EnergyAPIClient()

    def test_init_with_custom_timeout(self) -> None:
        """Client accepts custom timeout."""
        client = EnergyAPIClient(api_key="test_key", timeout=60.0)
        assert client.timeout == 60.0
        client.close()

    def test_init_default_timeout(self) -> None:
        """Client has default 30s timeout."""
        client = EnergyAPIClient(api_key="test_key")
        assert client.timeout == 30.0
        client.close()


@pytest.mark.unit
class TestEnergyAPIClientContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_returns_client(self) -> None:
        """Context manager returns client instance."""
        with EnergyAPIClient(api_key="test_key") as client:
            assert isinstance(client, EnergyAPIClient)

    def test_context_manager_closes_client(self) -> None:
        """Context manager closes client on exit."""
        with EnergyAPIClient(api_key="test_key") as client:
            assert client._client is not None


@pytest.mark.unit
class TestDataclasses:
    """Tests for data class structures."""

    def test_energy_series_metadata_fields(self) -> None:
        """EnergySeriesMetadata has expected fields."""
        metadata = EnergySeriesMetadata(
            msn="TETPBUS",
            description="Total Primary Energy Production",
            unit="Quadrillion Btu",
        )
        assert metadata.msn == "TETPBUS"
        assert metadata.description == "Total Primary Energy Production"
        assert metadata.unit == "Quadrillion Btu"

    def test_energy_series_metadata_default_source(self) -> None:
        """EnergySeriesMetadata has default source."""
        metadata = EnergySeriesMetadata(msn="TEST", description="", unit="")
        assert metadata.source == "EIA Monthly Energy Review"

    def test_energy_observation_fields(self) -> None:
        """EnergyObservation has expected fields."""
        obs = EnergyObservation(period="2020", value=100.5)
        assert obs.period == "2020"
        assert obs.value == 100.5

    def test_energy_observation_with_none_value(self) -> None:
        """EnergyObservation handles None values."""
        obs = EnergyObservation(period="2020", value=None)
        assert obs.value is None

    def test_energy_series_data_default_observations(self) -> None:
        """EnergySeriesData observations defaults to empty list."""
        metadata = EnergySeriesMetadata(msn="TEST", description="", unit="")
        series = EnergySeriesData(metadata=metadata)
        assert series.observations == []


@pytest.mark.unit
class TestEIAAPIError:
    """Tests for EIA API error dataclass."""

    def test_error_has_required_fields(self) -> None:
        """EIAAPIError stores status code, message, and URL."""
        error = EIAAPIError(
            status_code=400,
            message="Invalid MSN",
            url="https://api.eia.gov/v2",
        )
        assert error.status_code == 400
        assert error.message == "Invalid MSN"
        assert "eia.gov" in error.url

    def test_error_is_exception(self) -> None:
        """EIAAPIError can be raised as exception."""
        error = EIAAPIError(status_code=400, message="Bad request", url="http://test")
        with pytest.raises(EIAAPIError):
            raise error


@pytest.mark.unit
class TestConstantMappings:
    """Tests for constant mappings."""

    def test_priority_msn_codes_not_empty(self) -> None:
        """PRIORITY_MSN_CODES contains entries."""
        assert len(PRIORITY_MSN_CODES) > 0

    def test_priority_msn_codes_structure(self) -> None:
        """PRIORITY_MSN_CODES has expected structure."""
        for msn, info in PRIORITY_MSN_CODES.items():
            assert isinstance(msn, str)
            assert "table_code" in info
            assert "description" in info
            assert "category" in info
            assert "marxian" in info  # Babylon-specific interpretation

    def test_priority_msn_includes_key_series(self) -> None:
        """PRIORITY_MSN_CODES includes key energy series."""
        assert "TEPRBUS" in PRIORITY_MSN_CODES  # Total primary production
        assert "TETCBUS" in PRIORITY_MSN_CODES  # Total consumption
        assert "PAPRPUS" in PRIORITY_MSN_CODES  # Crude oil
        assert "TETCEUS" in PRIORITY_MSN_CODES  # CO2 emissions

    def test_msn_by_category_structure(self) -> None:
        """MSN_BY_CATEGORY has expected categories."""
        assert "overview" in MSN_BY_CATEGORY
        assert "sector" in MSN_BY_CATEGORY
        assert "prices" in MSN_BY_CATEGORY
        assert "emissions" in MSN_BY_CATEGORY

    def test_msn_by_category_lists(self) -> None:
        """Each MSN_BY_CATEGORY entry is a list of codes."""
        for _category, codes in MSN_BY_CATEGORY.items():
            assert isinstance(codes, list)
            assert len(codes) > 0
            for code in codes:
                assert isinstance(code, str)


@pytest.mark.unit
class TestEnergyAPIClientRequest:
    """Tests for request handling with mocked HTTP."""

    def test_request_includes_api_key(self) -> None:
        """Request adds API key to parameters."""
        with patch("babylon.data.energy.api_client.httpx.Client") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": {"data": []}}
            mock_httpx.return_value.get.return_value = mock_response

            with (
                EnergyAPIClient(api_key="my_api_key") as client,
                patch.object(client, "_rate_limit"),
            ):
                client._request("total-energy/data")

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
        with patch("babylon.data.energy.api_client.httpx.Client") as mock_httpx:
            mock_client = MagicMock()

            # First call returns 429, second returns 200
            response_429 = MagicMock()
            response_429.status_code = 429

            response_200 = MagicMock()
            response_200.status_code = 200
            response_200.json.return_value = {"response": {"data": []}}

            mock_client.get.side_effect = [response_429, response_200]
            mock_httpx.return_value = mock_client

            with (
                patch("babylon.data.energy.api_client.time.sleep"),
                EnergyAPIClient(api_key="test") as client,
            ):
                client._last_request_time = 0
                result = client._request("total-energy/data")

            assert result == {"response": {"data": []}}
            assert mock_client.get.call_count == 2


@pytest.mark.unit
class TestGetSeries:
    """Tests for get_series method with mocked responses."""

    def test_get_series_parses_observations(self) -> None:
        """get_series parses API response into observations."""
        mock_response = {
            "response": {
                "data": [
                    {
                        "period": "2020",
                        "value": "100.5",
                        "seriesDescription": "Test",
                        "unit": "Btu",
                    },
                    {
                        "period": "2021",
                        "value": "101.2",
                        "seriesDescription": "Test",
                        "unit": "Btu",
                    },
                ]
            }
        }

        with patch("babylon.data.energy.api_client.httpx.Client") as mock_httpx:
            mock_http_response = MagicMock()
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response
            mock_httpx.return_value.get.return_value = mock_http_response

            with EnergyAPIClient(api_key="test") as client:
                client._last_request_time = 0
                result = client.get_series("TETPBUS")

        assert isinstance(result, EnergySeriesData)
        assert len(result.observations) == 2
        assert result.observations[0].period == "2020"
        assert result.observations[0].value == 100.5

    def test_get_series_handles_empty_values(self) -> None:
        """get_series handles empty/missing values."""
        mock_response = {
            "response": {
                "data": [
                    {"period": "2020", "value": "", "seriesDescription": "", "unit": ""},
                    {"period": "2021", "value": None, "seriesDescription": "", "unit": ""},
                ]
            }
        }

        with patch("babylon.data.energy.api_client.httpx.Client") as mock_httpx:
            mock_http_response = MagicMock()
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response
            mock_httpx.return_value.get.return_value = mock_http_response

            with EnergyAPIClient(api_key="test") as client:
                client._last_request_time = 0
                result = client.get_series("TETPBUS")

        assert result.observations[0].value is None
        assert result.observations[1].value is None
