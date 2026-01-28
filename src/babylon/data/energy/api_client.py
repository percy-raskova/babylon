"""EIA (Energy Information Administration) API v2 client.

Provides rate-limited access to the EIA REST API v2 for fetching
energy production, consumption, prices, and emissions data.

API Documentation: https://www.eia.gov/opendata/documentation.php

Environment:
    ENERGY_API_KEY: API key for EIA access (required).
        Register at: https://www.eia.gov/opendata/register.php
"""

from __future__ import annotations

import contextlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from babylon.data.exceptions import EIAAPIError

logger = logging.getLogger(__name__)

# EIA API v2 configuration
BASE_URL = "https://api.eia.gov/v2"

# Rate limiting: EIA has similar limits to FRED
# Use conservative 0.5s delay to stay well under limits
REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0

# Pagination limits
MAX_ROWS_PER_REQUEST = 5000


@dataclass
class EnergySeriesMetadata:
    """Metadata for an EIA energy series."""

    msn: str  # Monthly Series Name (unique identifier)
    description: str
    unit: str
    source: str = "EIA Monthly Energy Review"


@dataclass
class EnergyObservation:
    """Single observation from an EIA series."""

    period: str  # YYYY or YYYY-MM format
    value: float | None


@dataclass
class EnergySeriesData:
    """Complete series data with metadata and observations."""

    metadata: EnergySeriesMetadata
    observations: list[EnergyObservation] = field(default_factory=list)


class EnergyAPIClient:
    """Client for EIA REST API v2.

    Fetches energy data with rate limiting and error handling.
    Supports total-energy data including production, consumption,
    prices, and emissions.

    Attributes:
        api_key: EIA API key.
        timeout: HTTP request timeout in seconds.

    Example:
        >>> with EnergyAPIClient() as client:
        ...     data = client.get_series("PAPRPUS", frequency="annual",
        ...                              start="2010", end="2023")
        ...     print(f"Got {len(data.observations)} observations")
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize EIA API client.

        Args:
            api_key: EIA API key. If None, reads from ENERGY_API_KEY env var.
            timeout: HTTP request timeout in seconds.

        Raises:
            ValueError: If no API key provided and ENERGY_API_KEY not set.
        """
        self.api_key = api_key or os.environ.get("ENERGY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "EIA API key required. Set ENERGY_API_KEY environment variable "
                "or pass api_key parameter. Register at: "
                "https://www.eia.gov/opendata/register.php"
            )
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> EnergyAPIClient:
        return self

    def __exit__(self, *_args: Any) -> None:
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
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make rate-limited API request with retries.

        Args:
            endpoint: API endpoint path (e.g., "total-energy/data").
            params: Query parameters.

        Returns:
            JSON response data.

        Raises:
            EIAAPIError: If request fails after retries.
        """
        if params is None:
            params = {}

        # Add required parameters
        params["api_key"] = self.api_key

        url = f"{BASE_URL}/{endpoint}"
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.get(url, params=params)

                if response.status_code == 200:
                    return response.json()  # type: ignore[no-any-return]

                # Handle specific error codes
                if response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue

                if response.status_code == 400:
                    # Bad request - likely invalid parameters
                    error_msg = response.text[:500]
                    raise EIAAPIError(
                        status_code=response.status_code,
                        message=f"Bad request: {error_msg}",
                        url=str(response.url),
                    )

                raise EIAAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=str(response.url),
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise EIAAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=url,
        )

    def get_series(
        self,
        msn: str,
        frequency: str = "annual",
        start: str | None = None,
        end: str | None = None,
    ) -> EnergySeriesData:
        """Fetch observations for a single series.

        Args:
            msn: Monthly Series Name (e.g., "PAPRPUS" for crude oil production).
            frequency: "annual" or "monthly".
            start: Start period (YYYY for annual, YYYY-MM for monthly).
            end: End period (YYYY for annual, YYYY-MM for monthly).

        Returns:
            EnergySeriesData with metadata and observations.
        """
        params: dict[str, Any] = {
            "frequency": frequency,
            "data[0]": "value",
            "facets[msn][]": msn,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": MAX_ROWS_PER_REQUEST,
        }

        if start:
            params["start"] = start
        if end:
            params["end"] = end

        data = self._request("total-energy/data", params)

        # Extract metadata from response
        response_data = data.get("response", {})
        rows = response_data.get("data", [])

        # Get description and unit from first row (if available)
        description = ""
        unit = ""
        if rows:
            first_row = rows[0]
            description = first_row.get("seriesDescription", "")
            unit = first_row.get("unit", "")

        metadata = EnergySeriesMetadata(
            msn=msn,
            description=description,
            unit=unit,
        )

        # Parse observations
        observations: list[EnergyObservation] = []
        for row in rows:
            value: float | None = None
            value_str = row.get("value")
            if value_str is not None and value_str != "":
                with contextlib.suppress(ValueError, TypeError):
                    value = float(value_str)

            observations.append(
                EnergyObservation(
                    period=row.get("period", ""),
                    value=value,
                )
            )

        return EnergySeriesData(
            metadata=metadata,
            observations=observations,
        )

    def get_multiple_series(
        self,
        msn_list: list[str],
        frequency: str = "annual",
        start: str | None = None,
        end: str | None = None,
    ) -> list[EnergySeriesData]:
        """Fetch observations for multiple series.

        Args:
            msn_list: List of Monthly Series Names.
            frequency: "annual" or "monthly".
            start: Start period.
            end: End period.

        Returns:
            List of EnergySeriesData for each requested series.
        """
        results: list[EnergySeriesData] = []

        for msn in msn_list:
            try:
                data = self.get_series(msn, frequency, start, end)
                results.append(data)
            except EIAAPIError as e:
                logger.warning(f"Failed to fetch series {msn}: {e.message}")
                # Create empty result for failed series
                results.append(
                    EnergySeriesData(
                        metadata=EnergySeriesMetadata(
                            msn=msn,
                            description="",
                            unit="",
                        ),
                        observations=[],
                    )
                )

        return results

    def get_all_annual_data(
        self,
        start_year: int = 1990,
        end_year: int = 2024,
        msn_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all annual energy data with pagination.

        Args:
            start_year: Start year for data range.
            end_year: End year for data range.
            msn_filter: Optional list of MSN codes to filter (None = all).

        Returns:
            List of raw data rows from API.
        """
        all_rows: list[dict[str, Any]] = []
        offset = 0

        while True:
            params: dict[str, Any] = {
                "frequency": "annual",
                "data[0]": "value",
                "start": str(start_year),
                "end": str(end_year),
                "sort[0][column]": "period",
                "sort[0][direction]": "asc",
                "offset": offset,
                "length": MAX_ROWS_PER_REQUEST,
            }

            # Add MSN filter if specified
            if msn_filter:
                for i, msn in enumerate(msn_filter):
                    params[f"facets[msn][{i}]"] = msn

            data = self._request("total-energy/data", params)
            response_data = data.get("response", {})
            rows = response_data.get("data", [])

            if not rows:
                break

            all_rows.extend(rows)
            offset += len(rows)

            # Check if we've fetched all available data
            total = response_data.get("total", 0)
            if offset >= total:
                break

            logger.info(f"Fetched {offset}/{total} rows...")

        return all_rows


# Priority MSN codes for Babylon metabolic analysis
# These map to the conceptual categories in EIA_PRIORITY_TABLES
# Note: MSN codes verified against EIA API v2 total-energy endpoint
PRIORITY_MSN_CODES: dict[str, dict[str, str]] = {
    # Primary Energy Overview (Table 01.01)
    # Note: TETPBUS doesn't exist; TEPRBUS is correct for production
    "TEPRBUS": {
        "table_code": "01.01",
        "description": "Total Primary Energy Production",
        "category": "overview",
        "marxian": "Total metabolic throughput - society's energy extraction rate",
    },
    "TETCBUS": {
        "table_code": "01.01",
        "description": "Total Primary Energy Consumption",
        "category": "overview",
        "marxian": "Social metabolism - total energy consumed by society",
    },
    # Production by Source (Table 01.02)
    "PAPRPUS": {
        "table_code": "01.02",
        "description": "Crude Oil Production",
        "category": "overview",
        "marxian": "Fossil capital - accumulated dead labor from geological time",
    },
    "NGPRBUS": {
        "table_code": "01.02",
        "description": "Natural Gas (Dry) Production",
        "category": "overview",
        "marxian": "Transition fuel - bridge between coal and renewables",
    },
    "CLPRBUS": {
        "table_code": "01.02",
        "description": "Coal Production",
        "category": "overview",
        "marxian": "Historical fossil capital - industrialization's energy base",
    },
    "NUETPUS": {
        "table_code": "01.02",
        "description": "Nuclear Electric Power Production",
        "category": "overview",
        "marxian": "State-subsidized energy - military-industrial complex legacy",
    },
    "REPRBUS": {
        "table_code": "01.02",
        "description": "Total Renewable Energy Production",
        "category": "overview",
        "marxian": "Possible energy transition - breaking fossil dependency",
    },
    # Imports/Exports (Table 01.04)
    "TEIMPUS": {
        "table_code": "01.04a",
        "description": "Total Energy Imports",
        "category": "overview",
        "marxian": "Imperial energy dependency on periphery extraction",
    },
    "TEEXPUS": {
        "table_code": "01.04b",
        "description": "Total Energy Exports",
        "category": "overview",
        "marxian": "Energy exported to periphery (often refined products)",
    },
    # Sector Consumption (Table 02.*)
    "TERCBUS": {
        "table_code": "02.01a",
        "description": "Residential Sector Energy Consumption",
        "category": "sector",
        "marxian": "Labor reproduction energy - household metabolism",
    },
    "TECCBUS": {
        "table_code": "02.01b",
        "description": "Commercial Sector Energy Consumption",
        "category": "sector",
        "marxian": "Circulation sphere energy - commerce and services",
    },
    "TEICBUS": {
        "table_code": "02.02",
        "description": "Industrial Sector Energy Consumption",
        "category": "sector",
        "marxian": "Production sphere energy - value creation metabolism",
    },
    "TEACBUS": {
        "table_code": "02.05",
        "description": "Transportation Sector Energy Consumption",
        "category": "sector",
        "marxian": "Circulation metabolism - commodity and labor mobility",
    },
    # Prices (Table 09.*)
    "RAIMUUS": {
        "table_code": "09.01",
        "description": "Crude Oil Imported Acquisition Cost",
        "category": "prices",
        "marxian": "Ground rent - oil as monopolizable natural resource",
    },
    "MGACDUS": {
        "table_code": "09.04",
        "description": "Motor Gasoline Retail Price",
        "category": "prices",
        "marxian": "Labor reproduction cost - transport to work",
    },
    "NGRCDUS": {
        "table_code": "09.08",
        "description": "Natural Gas Residential Price",
        "category": "prices",
        "marxian": "Heating cost - household energy input",
    },
    "ESRCDUS": {
        "table_code": "09.10",
        "description": "Electricity Residential Price",
        "category": "prices",
        "marxian": "Universal energy carrier price - affects all production",
    },
    # CO2 Emissions (Table 11.*)
    "TETCEUS": {
        "table_code": "11.01",
        "description": "Total Energy CO2 Emissions",
        "category": "emissions",
        "marxian": "Metabolic rift accumulation - waste externality to biosphere",
    },
    "TEACEUS": {
        "table_code": "11.02",
        "description": "Transportation Sector CO2 Emissions",
        "category": "emissions",
        "marxian": "Circulation sphere metabolic rift",
    },
    "TEICEUS": {
        "table_code": "11.02",
        "description": "Industrial Sector CO2 Emissions",
        "category": "emissions",
        "marxian": "Production sphere metabolic rift",
    },
}

# All MSN codes grouped by category for bulk loading
MSN_BY_CATEGORY: dict[str, list[str]] = {
    "overview": [
        "TEPRBUS",  # Total Primary Energy Production (not TETPBUS)
        "TETCBUS",
        "PAPRPUS",
        "NGPRBUS",
        "CLPRBUS",
        "NUETPUS",
        "REPRBUS",
        "TEIMPUS",
        "TEEXPUS",
    ],
    "sector": ["TERCBUS", "TECCBUS", "TEICBUS", "TEACBUS"],
    "prices": ["RAIMUUS", "MGACDUS", "NGRCDUS", "ESRCDUS"],
    "emissions": ["TETCEUS", "TEACEUS", "TEICEUS"],
}
