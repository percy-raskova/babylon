"""ArcGIS REST API client with pagination and rate limiting.

Provides a reusable client for accessing ArcGIS Feature Services, used by
HIFLD (prisons, police, electric grid) and MIRTA (military installations).

The client handles:
- Automatic pagination (ArcGIS limits to 2000 records per request)
- Rate limiting with exponential backoff
- Error handling for ArcGIS-specific error responses
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from babylon.data.exceptions import ArcGISAPIError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ArcGIS Feature Service limits
MAX_RECORD_COUNT = 2000  # Default server limit per request
REQUEST_DELAY_SECONDS = 0.2  # Conservative rate limit
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0
DEFAULT_TIMEOUT = 30.0


@dataclass
class ArcGISFeature:
    """Single feature from ArcGIS Feature Service.

    Attributes:
        object_id: ArcGIS OBJECTID for the feature.
        attributes: Dictionary of attribute values.
        geometry: Optional geometry dictionary (point, polygon, etc.).
    """

    object_id: int
    attributes: dict[str, Any]
    geometry: dict[str, Any] | None = None


class ArcGISClient:
    """Client for ArcGIS REST API Feature Services.

    Handles pagination for large datasets and rate limiting. Follows the
    same patterns as CensusAPIClient for consistency.

    Attributes:
        base_url: Base URL for the Feature Service (e.g., services1.arcgis.com/...).
        timeout: HTTP request timeout in seconds.

    Example:
        >>> with ArcGISClient(PRISONS_SERVICE_URL) as client:
        ...     for feature in client.query_all(out_fields="NAME,CAPACITY"):
        ...         print(feature.attributes["NAME"])
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize ArcGIS client.

        Args:
            base_url: Base URL for Feature Service (without /query suffix).
            timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> ArcGISClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - close client."""
        self.close()

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _request(
        self,
        endpoint: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        """Make rate-limited API request with retries.

        Args:
            endpoint: Full URL endpoint for the request.
            params: Query parameters.

        Returns:
            Parsed JSON response dictionary.

        Raises:
            ArcGISAPIError: If request fails after retries or API returns error.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.get(endpoint, params=params)

                if response.status_code == 200:
                    data: dict[str, Any] = response.json()
                    # Check for ArcGIS error in response body
                    if "error" in data:
                        raise ArcGISAPIError(
                            status_code=data["error"].get("code", 0),
                            message=data["error"].get("message", "Unknown error"),
                            url=str(response.url),
                        )
                    return data

                if response.status_code == 429:
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue

                raise ArcGISAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=str(response.url),
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise ArcGISAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=endpoint,
        )

    def query_all(
        self,
        where: str = "1=1",
        out_fields: str = "*",
        return_geometry: bool = False,
    ) -> Iterator[ArcGISFeature]:
        """Query all features with automatic pagination.

        Iterates through all matching features, handling the 2000-record
        pagination limit automatically.

        Args:
            where: SQL WHERE clause for filtering (default: all records).
            out_fields: Comma-separated field names or "*" for all.
            return_geometry: Whether to include geometry in results.

        Yields:
            ArcGISFeature objects for each record.
        """
        endpoint = f"{self.base_url}/query"
        offset = 0

        while True:
            params = {
                "where": where,
                "outFields": out_fields,
                "returnGeometry": str(return_geometry).lower(),
                "f": "json",
                "resultOffset": str(offset),
                "resultRecordCount": str(MAX_RECORD_COUNT),
            }

            data = self._request(endpoint, params)
            features = data.get("features", [])

            if not features:
                break

            for feature in features:
                yield ArcGISFeature(
                    object_id=feature.get("attributes", {}).get("OBJECTID", 0),
                    attributes=feature.get("attributes", {}),
                    geometry=feature.get("geometry") if return_geometry else None,
                )

            # Check if more results available
            if len(features) < MAX_RECORD_COUNT:
                break

            offset += len(features)
            logger.debug(f"Fetched {offset} features, continuing...")

    def get_record_count(self, where: str = "1=1") -> int:
        """Get total record count for a query.

        Useful for progress bars and validation before fetching all records.

        Args:
            where: SQL WHERE clause for filtering (default: all records).

        Returns:
            Total number of matching records.
        """
        endpoint = f"{self.base_url}/query"
        params = {
            "where": where,
            "returnCountOnly": "true",
            "f": "json",
        }
        data = self._request(endpoint, params)
        count: int = data.get("count", 0)
        return count

    def get_service_info(self) -> dict[str, Any]:
        """Get Feature Service metadata.

        Returns service information including fields, geometry type,
        and capabilities.

        Returns:
            Service metadata dictionary.
        """
        params = {"f": "json"}
        return self._request(self.base_url, params)


__all__ = ["ArcGISClient", "ArcGISFeature", "ArcGISAPIError"]
