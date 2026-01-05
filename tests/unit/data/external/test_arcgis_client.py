"""Unit tests for ArcGIS REST API client.

Tests the ArcGISClient class that provides paginated access to HIFLD and
MIRTA Feature Services. Uses mocked HTTP responses for deterministic testing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from babylon.data.external.arcgis import ArcGISAPIError, ArcGISClient, ArcGISFeature

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_client() -> ArcGISClient:
    """Create ArcGIS client for testing."""
    return ArcGISClient("https://test.arcgis.com/rest/services/Test/FeatureServer/0")


@pytest.fixture
def sample_feature_response() -> dict[str, Any]:
    """Sample ArcGIS query response with features."""
    return {
        "features": [
            {
                "attributes": {
                    "OBJECTID": 1,
                    "NAME": "Test Facility 1",
                    "COUNTYFIPS": "06001",
                    "TYPE": "FEDERAL",
                    "CAPACITY": 500,
                },
            },
            {
                "attributes": {
                    "OBJECTID": 2,
                    "NAME": "Test Facility 2",
                    "COUNTYFIPS": "06037",
                    "TYPE": "STATE",
                    "CAPACITY": 1000,
                },
            },
        ]
    }


@pytest.fixture
def sample_count_response() -> dict[str, Any]:
    """Sample ArcGIS count query response."""
    return {"count": 7234}


# =============================================================================
# ARCGIS CLIENT INITIALIZATION TESTS
# =============================================================================


class TestArcGISClientInit:
    """Tests for ArcGIS client initialization."""

    def test_base_url_stored(self) -> None:
        """Base URL should be stored without trailing slash."""
        client = ArcGISClient("https://test.arcgis.com/services/")
        assert client.base_url == "https://test.arcgis.com/services"

    def test_default_timeout(self) -> None:
        """Default timeout should be 30 seconds."""
        client = ArcGISClient("https://test.arcgis.com")
        assert client.timeout == 30.0

    def test_custom_timeout(self) -> None:
        """Custom timeout should be applied."""
        client = ArcGISClient("https://test.arcgis.com", timeout=60.0)
        assert client.timeout == 60.0

    def test_context_manager_support(self) -> None:
        """Client should support context manager protocol."""
        with ArcGISClient("https://test.arcgis.com") as client:
            assert isinstance(client, ArcGISClient)


# =============================================================================
# ARCGIS FEATURE TESTS
# =============================================================================


class TestArcGISFeature:
    """Tests for ArcGISFeature dataclass."""

    def test_feature_creation(self) -> None:
        """Feature should store object_id and attributes."""
        feature = ArcGISFeature(
            object_id=123,
            attributes={"NAME": "Test", "TYPE": "FEDERAL"},
        )
        assert feature.object_id == 123
        assert feature.attributes["NAME"] == "Test"
        assert feature.attributes["TYPE"] == "FEDERAL"

    def test_feature_with_geometry(self) -> None:
        """Feature should optionally store geometry."""
        feature = ArcGISFeature(
            object_id=456,
            attributes={"NAME": "Test"},
            geometry={"x": -122.4, "y": 37.8},
        )
        assert feature.geometry is not None
        assert feature.geometry["x"] == -122.4

    def test_feature_without_geometry(self) -> None:
        """Feature geometry should default to None."""
        feature = ArcGISFeature(
            object_id=789,
            attributes={"NAME": "Test"},
        )
        assert feature.geometry is None


# =============================================================================
# ARCGIS API ERROR TESTS
# =============================================================================


class TestArcGISAPIError:
    """Tests for ArcGIS API error handling."""

    def test_error_creation(self) -> None:
        """Error should store status code, message, and URL."""
        error = ArcGISAPIError(
            status_code=400,
            message="Invalid query",
            url="https://test.arcgis.com/query",
        )
        assert error.status_code == 400
        assert error.message == "Invalid query"
        assert "test.arcgis.com" in error.url

    def test_error_string_representation(self) -> None:
        """Error should have informative string representation."""
        error = ArcGISAPIError(
            status_code=404,
            message="Service not found",
            url="https://test.arcgis.com/query",
        )
        error_str = str(error)
        assert "404" in error_str
        assert "Service not found" in error_str


# =============================================================================
# QUERY ALL TESTS (MOCKED HTTP)
# =============================================================================


class TestArcGISClientQueryAll:
    """Tests for query_all pagination method."""

    def test_query_all_returns_features(
        self, mock_client: ArcGISClient, sample_feature_response: dict[str, Any]
    ) -> None:
        """query_all should yield ArcGISFeature objects."""
        with patch.object(mock_client, "_request", return_value=sample_feature_response):
            features = list(mock_client.query_all())

        assert len(features) == 2
        assert all(isinstance(f, ArcGISFeature) for f in features)
        assert features[0].object_id == 1
        assert features[1].object_id == 2

    def test_query_all_extracts_attributes(
        self, mock_client: ArcGISClient, sample_feature_response: dict[str, Any]
    ) -> None:
        """query_all should extract attributes correctly."""
        with patch.object(mock_client, "_request", return_value=sample_feature_response):
            features = list(mock_client.query_all())

        assert features[0].attributes["NAME"] == "Test Facility 1"
        assert features[0].attributes["COUNTYFIPS"] == "06001"
        assert features[1].attributes["TYPE"] == "STATE"

    def test_query_all_with_where_clause(
        self, mock_client: ArcGISClient, sample_feature_response: dict[str, Any]
    ) -> None:
        """query_all should pass where clause to API."""
        mock_request = MagicMock(return_value=sample_feature_response)
        with patch.object(mock_client, "_request", mock_request):
            list(mock_client.query_all(where="TYPE='FEDERAL'"))

        call_args = mock_request.call_args
        assert call_args[0][1]["where"] == "TYPE='FEDERAL'"

    def test_query_all_with_out_fields(
        self, mock_client: ArcGISClient, sample_feature_response: dict[str, Any]
    ) -> None:
        """query_all should pass outFields to API."""
        mock_request = MagicMock(return_value=sample_feature_response)
        with patch.object(mock_client, "_request", mock_request):
            list(mock_client.query_all(out_fields="NAME,TYPE"))

        call_args = mock_request.call_args
        assert call_args[0][1]["outFields"] == "NAME,TYPE"

    def test_query_all_pagination_stops_on_empty(self, mock_client: ArcGISClient) -> None:
        """query_all should stop when no features returned."""
        empty_response: dict[str, Any] = {"features": []}
        with patch.object(mock_client, "_request", return_value=empty_response):
            features = list(mock_client.query_all())

        assert len(features) == 0

    def test_query_all_pagination_continues(self, mock_client: ArcGISClient) -> None:
        """query_all should paginate when max records returned."""
        # First call returns 2000 records (max), second returns fewer
        page1 = {"features": [{"attributes": {"OBJECTID": i}} for i in range(2000)]}
        page2 = {"features": [{"attributes": {"OBJECTID": i}} for i in range(500)]}

        mock_request = MagicMock(side_effect=[page1, page2])
        with patch.object(mock_client, "_request", mock_request):
            features = list(mock_client.query_all())

        assert len(features) == 2500
        assert mock_request.call_count == 2


# =============================================================================
# GET RECORD COUNT TESTS
# =============================================================================


class TestArcGISClientGetRecordCount:
    """Tests for get_record_count method."""

    def test_returns_count(
        self, mock_client: ArcGISClient, sample_count_response: dict[str, Any]
    ) -> None:
        """get_record_count should return count from API."""
        with patch.object(mock_client, "_request", return_value=sample_count_response):
            count = mock_client.get_record_count()

        assert count == 7234

    def test_with_where_clause(
        self, mock_client: ArcGISClient, sample_count_response: dict[str, Any]
    ) -> None:
        """get_record_count should pass where clause."""
        mock_request = MagicMock(return_value=sample_count_response)
        with patch.object(mock_client, "_request", mock_request):
            mock_client.get_record_count(where="STATE='CA'")

        call_args = mock_request.call_args
        assert call_args[0][1]["where"] == "STATE='CA'"

    def test_returns_zero_if_missing(self, mock_client: ArcGISClient) -> None:
        """get_record_count should return 0 if count not in response."""
        with patch.object(mock_client, "_request", return_value={}):
            count = mock_client.get_record_count()

        assert count == 0


# =============================================================================
# RATE LIMITING TESTS
# =============================================================================


class TestArcGISClientRateLimiting:
    """Tests for rate limiting behavior."""

    def test_rate_limit_enforced(self, mock_client: ArcGISClient) -> None:
        """Rate limiting should delay between requests."""
        # This is a behavioral test - just ensure the method exists and runs
        mock_client._rate_limit()
        # Second call should have minimal delay since we just called it
        mock_client._rate_limit()


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestArcGISClientErrorHandling:
    """Tests for API error handling."""

    def test_arcgis_error_in_response_body(self, mock_client: ArcGISClient) -> None:
        """Should raise ArcGISAPIError when error in response body."""
        error_response = MagicMock()
        error_response.status_code = 200
        error_response.json.return_value = {
            "error": {"code": 400, "message": "Invalid query parameters"}
        }
        error_response.url = "https://test.arcgis.com/query"

        with (
            patch.object(mock_client._client, "get", return_value=error_response),
            pytest.raises(ArcGISAPIError) as exc_info,
        ):
            mock_client._request("https://test.arcgis.com/query", {})

        assert exc_info.value.status_code == 400
        assert "Invalid query" in exc_info.value.message

    def test_http_error_status(self, mock_client: ArcGISClient) -> None:
        """Should raise ArcGISAPIError on HTTP error status."""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        error_response.url = "https://test.arcgis.com/query"

        with (
            patch.object(mock_client._client, "get", return_value=error_response),
            pytest.raises(ArcGISAPIError) as exc_info,
        ):
            mock_client._request("https://test.arcgis.com/query", {})

        assert exc_info.value.status_code == 500

    def test_retry_on_rate_limit(self, mock_client: ArcGISClient) -> None:
        """Should retry on 429 rate limit response."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.url = "https://test.arcgis.com/query"

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"count": 100}
        success_response.url = "https://test.arcgis.com/query"

        mock_get = MagicMock(side_effect=[rate_limit_response, success_response])
        with (
            patch.object(mock_client._client, "get", mock_get),
            patch("time.sleep"),  # Skip actual sleep in tests
        ):
            result = mock_client._request("https://test.arcgis.com/query", {})

        assert result == {"count": 100}
        assert mock_get.call_count == 2

    def test_max_retries_exceeded(self, mock_client: ArcGISClient) -> None:
        """Should raise after max retries exceeded."""
        mock_get = MagicMock(side_effect=httpx.RequestError("Connection failed"))
        with (
            patch.object(mock_client._client, "get", mock_get),
            patch("time.sleep"),  # Skip actual sleep
            pytest.raises(ArcGISAPIError) as exc_info,
        ):
            mock_client._request("https://test.arcgis.com/query", {})

        assert "Max retries exceeded" in exc_info.value.message
        assert mock_get.call_count == 3  # MAX_RETRIES


# =============================================================================
# SERVICE INFO TESTS
# =============================================================================


class TestArcGISClientServiceInfo:
    """Tests for get_service_info method."""

    def test_returns_service_metadata(self, mock_client: ArcGISClient) -> None:
        """get_service_info should return service metadata."""
        service_info = {
            "name": "Prison_Boundaries",
            "type": "Feature Layer",
            "geometryType": "esriGeometryPolygon",
            "fields": [{"name": "OBJECTID"}, {"name": "NAME"}],
        }
        with patch.object(mock_client, "_request", return_value=service_info):
            result = mock_client.get_service_info()

        assert result["name"] == "Prison_Boundaries"
        assert result["type"] == "Feature Layer"
