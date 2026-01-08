"""Census Bureau API client for ACS data retrieval.

Provides direct access to Census Bureau REST API for county-level ACS data,
replacing CSV-based ingestion with API-first approach for granular labor analysis.

API Documentation: https://api.census.gov/data.html
ACS 5-Year Estimates: https://api.census.gov/data/2022/acs/acs5

Environment:
    CENSUS_API_KEY: API key for higher rate limits (optional but recommended)
"""

import logging
import os
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from babylon.data.exceptions import CensusAPIError

logger = logging.getLogger(__name__)

# Census Bureau API configuration
BASE_URL = "https://api.census.gov/data"
DEFAULT_YEAR = 2022
DEFAULT_DATASET = "acs/acs5"

# Rate limiting: 500 requests/day without key, higher with key
REQUEST_DELAY_SECONDS = 0.5  # Conservative delay between requests
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0


class VariableMetadata(BaseModel):
    """Metadata for a Census variable."""

    code: str
    label: str
    concept: str | None = None
    predicate_type: str | None = None


class CountyData(BaseModel):
    """Census data for a single county."""

    state_fips: str
    county_fips: str
    fips: str  # Combined 5-digit FIPS
    name: str
    values: dict[str, int | float | None] = Field(default_factory=dict)


class ACSDataResponse(BaseModel):
    """Validates Census API data response (2D array with headers).

    Census API returns data as a 2D array where the first row is headers
    and subsequent rows are data. This model validates that structure.
    """

    headers: list[str]
    rows: list[list[str | int | float | None]]

    @classmethod
    def from_raw(cls, data: list[list[Any]]) -> "ACSDataResponse":
        """Parse raw Census API response into validated model.

        Args:
            data: Raw 2D array from Census API JSON response.

        Returns:
            Validated ACSDataResponse with headers and data rows separated.
        """
        if not data or len(data) < 1:
            return cls(headers=[], rows=[])
        # First row is headers, rest are data rows
        headers = [str(h) for h in data[0]]
        rows = data[1:] if len(data) > 1 else []
        return cls(headers=headers, rows=rows)


class CensusAPIClient:
    """Client for Census Bureau REST API.

    Fetches ACS 5-Year Estimates at county level with rate limiting
    and error handling. Uses `group(TABLE)` syntax to fetch all
    variables in a table, bypassing the 50-variable limit.

    Attributes:
        api_key: Optional API key for higher rate limits.
        year: ACS year (default 2022 for latest 5-year estimates).
        dataset: API dataset path (default acs/acs5).
    """

    def __init__(
        self,
        api_key: str | None = None,
        year: int = DEFAULT_YEAR,
        dataset: str = DEFAULT_DATASET,
        timeout: float = 30.0,
    ) -> None:
        """Initialize Census API client.

        Args:
            api_key: Census API key. If None, reads from CENSUS_API_KEY env var.
            year: ACS data year (default 2022).
            dataset: API dataset path (default acs/acs5).
            timeout: HTTP request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("CENSUS_API_KEY")
        self.year = year
        self.dataset = dataset
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "CensusAPIClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @property
    def base_endpoint(self) -> str:
        """Base API endpoint for configured year and dataset."""
        return f"{BASE_URL}/{self.year}/{self.dataset}"

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _request(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Make rate-limited API request with retries.

        Args:
            endpoint: API endpoint URL.
            params: Query parameters.

        Returns:
            JSON response data.

        Raises:
            CensusAPIError: If request fails after retries.
        """
        if params is None:
            params = {}

        # Add API key if available
        if self.api_key:
            params["key"] = self.api_key

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.get(endpoint, params=params)

                if response.status_code == 200:
                    return response.json()

                # Handle specific error codes
                if response.status_code == 204:
                    # No content - empty result
                    return []

                if response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue

                raise CensusAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=str(response.url),
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise CensusAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=endpoint,
        )

    def get_variables(self, table: str) -> dict[str, VariableMetadata]:
        """Fetch variable metadata for a table.

        Args:
            table: Census table code (e.g., "B19001").

        Returns:
            Dict mapping variable codes to metadata. Returns empty dict if
            the table doesn't exist for this year (404 response).
        """
        endpoint = f"{self.base_endpoint}/groups/{table}.json"

        try:
            data = self._request(endpoint)
        except CensusAPIError as e:
            # Handle both 404 (not found) and 400 (group does not exist)
            # Census API returns 400 with "Group 'X' does not exist" for missing tables
            if e.status_code == 404 or (e.status_code == 400 and "does not exist" in e.message):
                logger.info(f"Table {table} not available for year {self.year}")
                return {}
            raise

        variables: dict[str, VariableMetadata] = {}
        for code, info in data.get("variables", {}).items():
            # Skip annotation columns (ending in EA, MA, etc.)
            if not code.endswith("E"):
                continue

            variables[code] = VariableMetadata(
                code=code,
                label=info.get("label", ""),
                concept=info.get("concept"),
                predicate_type=info.get("predicateType"),
            )

        return variables

    def get_county_data(
        self,
        variables: list[str],
        state_fips: str | None = None,
    ) -> list[CountyData]:
        """Fetch county-level data for specified variables.

        Args:
            variables: List of variable codes (e.g., ["B19001_001E", "B19001_002E"]).
            state_fips: Optional 2-digit state FIPS to limit query.

        Returns:
            List of CountyData objects with values for each county.
            Returns empty list if data is unavailable (404 response).
        """
        # Build variable list (NAME is always included)
        var_string = ",".join(["NAME"] + variables)

        params: dict[str, str] = {"get": var_string}

        # Geography specification
        if state_fips:
            params["for"] = "county:*"
            params["in"] = f"state:{state_fips}"
        else:
            params["for"] = "county:*"
            params["in"] = "state:*"

        try:
            data = self._request(self.base_endpoint, params)
        except CensusAPIError as e:
            if e.status_code == 404:
                # Data not available for this year/geography - return empty list
                logger.info(f"County data not available for state {state_fips}, year {self.year}")
                return []
            raise

        if not data or len(data) < 2:
            return []

        # First row is headers
        headers = data[0]
        results: list[CountyData] = []

        for row in data[1:]:
            row_dict = dict(zip(headers, row, strict=False))

            state = row_dict.get("state", "")
            county = row_dict.get("county", "")

            # Extract values for requested variables
            values: dict[str, Any] = {}
            for var in variables:
                raw_value = row_dict.get(var)
                values[var] = self._parse_value(raw_value)

            results.append(
                CountyData(
                    state_fips=state,
                    county_fips=county,
                    fips=f"{state}{county}",
                    name=row_dict.get("NAME", ""),
                    values=values,
                )
            )

        return results

    def get_table_data(
        self,
        table: str,
        state_fips: str | None = None,
    ) -> list[CountyData]:
        """Fetch all data for a table using group() syntax.

        This uses the `group(TABLE)` function to fetch all variables
        in a table at once, bypassing the 50-variable limit.

        Args:
            table: Census table code (e.g., "B19001").
            state_fips: Optional 2-digit state FIPS to limit query.

        Returns:
            List of CountyData objects with all table values.
            Returns empty list if the table is unavailable (404 response).
        """
        params: dict[str, str] = {"get": f"NAME,group({table})"}

        if state_fips:
            params["for"] = "county:*"
            params["in"] = f"state:{state_fips}"
        else:
            params["for"] = "county:*"
            params["in"] = "state:*"

        try:
            data = self._request(self.base_endpoint, params)
        except CensusAPIError as e:
            # Handle both 404 (not found) and 400 (group does not exist)
            # Census API returns 400 with "Group 'X' does not exist" for missing tables
            if e.status_code == 404 or (e.status_code == 400 and "does not exist" in e.message):
                logger.info(f"Table {table} not available for state {state_fips}, year {self.year}")
                return []
            raise

        # Validate response structure with Pydantic
        response = ACSDataResponse.from_raw(data)
        if not response.rows:
            return []

        results: list[CountyData] = []

        for row in response.rows:
            row_dict = dict(zip(response.headers, row, strict=False))

            state = str(row_dict.get("state", ""))
            county = str(row_dict.get("county", ""))

            # Extract all estimate columns (ending in E)
            values: dict[str, int | float | None] = {}
            for key, val in row_dict.items():
                if isinstance(key, str) and key.startswith(table) and key.endswith("E"):
                    values[key] = self._parse_value(val)

            results.append(
                CountyData(
                    state_fips=state,
                    county_fips=county,
                    fips=f"{state}{county}",
                    name=str(row_dict.get("NAME", "")),
                    values=values,
                )
            )

        return results

    def get_all_states(self) -> list[tuple[str, str]]:
        """Get list of all state FIPS codes and names.

        Returns:
            List of (fips, name) tuples for all states.
        """
        params = {"get": "NAME", "for": "state:*"}
        data = self._request(self.base_endpoint, params)

        if not data or len(data) < 2:
            return []

        results: list[tuple[str, str]] = []
        for row in data[1:]:
            if len(row) >= 2:
                results.append((row[1], row[0]))  # (fips, name)

        return sorted(results)

    @staticmethod
    def _parse_value(value: Any) -> int | float | None:
        """Parse Census API value to numeric type.

        Args:
            value: Raw value from API response.

        Returns:
            Parsed numeric value or None for missing/suppressed data.
        """
        if value is None:
            return None

        # String representations of missing data
        if isinstance(value, str):
            if value in {"", "-", "N", "(X)", "**", "***", "null", "-666666666"}:
                return None
            try:
                # Try integer first
                if "." not in value:
                    return int(value)
                return float(value)
            except ValueError:
                return None

        # Already numeric
        if isinstance(value, int | float):
            return value

        return None


# Convenience function for quick queries
def fetch_county_table(
    table: str,
    year: int = DEFAULT_YEAR,
    api_key: str | None = None,
) -> list[CountyData]:
    """Fetch all county data for a Census table.

    Args:
        table: Census table code (e.g., "B19001").
        year: ACS data year.
        api_key: Optional API key.

    Returns:
        List of CountyData objects.
    """
    with CensusAPIClient(api_key=api_key, year=year) as client:
        return client.get_table_data(table)
