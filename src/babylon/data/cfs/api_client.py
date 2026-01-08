"""Census Commodity Flow Survey (CFS) API client.

Provides access to Census Bureau CFS data at state-level geography.
The API provides commodity flow data for origin-destination pairs by
SCTG (Standard Classification of Transported Goods) commodity codes.

API Documentation: https://api.census.gov/data/2022/cfsarea
Variables: COMM (SCTG code), VAL (value $M), TON (tons k), dms_orig, dms_dest

Environment:
    CENSUS_API_KEY: API key for higher rate limits (optional but recommended)
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from babylon.data.exceptions import CFSAPIError

logger = logging.getLogger(__name__)

# CFS API configuration
CFS_BASE_URL = "https://api.census.gov/data"
DEFAULT_CFS_YEAR = 2022

# Rate limiting
REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0


@dataclass
class CFSFlowRecord:
    """Single commodity flow record from CFS API.

    Attributes:
        origin_state_fips: 2-digit origin state FIPS code.
        dest_state_fips: 2-digit destination state FIPS code.
        sctg_code: SCTG commodity code (2-digit).
        value_millions: Value in millions of dollars.
        tons_thousands: Weight in thousands of tons.
        ton_miles_millions: Ton-miles in millions (optional).
        mode_code: Transportation mode code (optional).
    """

    origin_state_fips: str
    dest_state_fips: str
    sctg_code: str
    value_millions: float | None = None
    tons_thousands: float | None = None
    ton_miles_millions: float | None = None
    mode_code: str | None = None


class CFSAPIClient:
    """Client for Census Commodity Flow Survey REST API.

    Fetches state-level commodity flow data with rate limiting
    and error handling. CFS provides origin-destination flows
    by commodity type (SCTG codes).

    Note: CFS API provides state-level and CFS-area level data only,
    NOT county-level. County disaggregation requires DimGeographicHierarchy.

    Attributes:
        api_key: Optional API key for higher rate limits.
        year: CFS survey year (default 2022).
    """

    def __init__(
        self,
        api_key: str | None = None,
        year: int = DEFAULT_CFS_YEAR,
        timeout: float = 30.0,
    ) -> None:
        """Initialize CFS API client.

        Args:
            api_key: Census API key. If None, reads from CENSUS_API_KEY env var.
            year: CFS data year (default 2022).
            timeout: HTTP request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("CENSUS_API_KEY")
        self.year = year
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)
        self.last_error: CFSAPIError | None = None

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "CFSAPIClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _build_url(self) -> str:
        """Build API URL for CFS area query."""
        return f"{CFS_BASE_URL}/{self.year}/cfsarea"

    def _request(self, params: dict[str, str]) -> list[list[str]]:
        """Make rate-limited API request with retries.

        Args:
            params: Query parameters.

        Returns:
            API response as list of lists (header row + data rows).

        Raises:
            CFSAPIError: On API error or after max retries.
        """
        url = self._build_url()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data
                    raise CFSAPIError(
                        status_code=200,
                        message="Empty or invalid response",
                        url=str(response.url),
                    )

                if response.status_code == 429:
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue

                raise CFSAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=str(response.url),
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise CFSAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=url,
        )

    def get_state_flows(
        self,
        origin_state: str | None = None,
        sctg_code: str | None = None,
    ) -> list[CFSFlowRecord]:
        """Get commodity flows at state level.

        Args:
            origin_state: Filter by origin state FIPS (optional).
            sctg_code: Filter by SCTG commodity code (optional).

        Returns:
            List of CFSFlowRecord objects.
        """
        # Build query parameters
        # Variables: NAME, dms_orig, dms_dest, COMM (SCTG), VAL, TON, TMILES
        params: dict[str, str] = {
            "get": "NAME,dms_orig,dms_dest,COMM,VAL,TON,TMILES",
            "for": "state:*",  # All states
        }

        if self.api_key:
            params["key"] = self.api_key

        # Add filters if specified
        predicates = []
        if origin_state:
            predicates.append(f"dms_orig={origin_state}")
        if sctg_code:
            predicates.append(f"COMM={sctg_code}")

        # CFS uses different filter syntax than ACS
        # We'll fetch all and filter in Python for simplicity
        # (CFS API has limited predicate support)

        try:
            data = self._request(params)
        except CFSAPIError as e:
            self.last_error = e
            logger.error(f"CFS API error: {e.message}")
            return []

        # Parse response: first row is headers
        if len(data) < 2:
            return []

        headers = data[0]
        records: list[CFSFlowRecord] = []

        # Find column indices
        col_map = {h: i for i, h in enumerate(headers)}

        for row in data[1:]:
            try:
                origin = str(row[col_map.get("dms_orig", 1)]).zfill(2)
                dest = str(row[col_map.get("dms_dest", 2)]).zfill(2)
                sctg = str(row[col_map.get("COMM", 3)])

                # Skip if filtering and doesn't match
                if origin_state and origin != origin_state:
                    continue
                if sctg_code and sctg != sctg_code:
                    continue

                # Parse numeric values
                val_str = row[col_map.get("VAL", 4)]
                ton_str = row[col_map.get("TON", 5)]
                tmiles_str = row[col_map.get("TMILES", 6)] if "TMILES" in col_map else None

                value = float(val_str) if val_str and val_str != "N" else None
                tons = float(ton_str) if ton_str and ton_str != "N" else None
                tmiles = float(tmiles_str) if tmiles_str and tmiles_str != "N" else None

                records.append(
                    CFSFlowRecord(
                        origin_state_fips=origin,
                        dest_state_fips=dest,
                        sctg_code=sctg,
                        value_millions=value,
                        tons_thousands=tons,
                        ton_miles_millions=tmiles,
                    )
                )
            except (IndexError, ValueError) as e:
                logger.debug(f"Skipping row due to parse error: {e}")
                continue

        return records

    def get_sctg_codes(self) -> list[tuple[str, str]]:
        """Get list of SCTG commodity codes and names.

        Returns:
            List of (code, name) tuples for SCTG commodities.
        """
        # SCTG codes are standardized - return hardcoded list
        # Full list at: https://www.census.gov/library/reference/code-lists/sctg.html
        return [
            ("01", "Live animals and fish"),
            ("02", "Cereal grains"),
            ("03", "Other agricultural products"),
            ("04", "Animal feed"),
            ("05", "Meat, poultry, fish, seafood"),
            ("06", "Milled grain products"),
            ("07", "Other prepared foodstuffs"),
            ("08", "Alcoholic beverages"),
            ("09", "Tobacco products"),
            ("10", "Building stone"),
            ("11", "Natural sands"),
            ("12", "Gravel and crushed stone"),
            ("13", "Nonmetallic minerals"),
            ("14", "Metallic ores"),
            ("15", "Coal"),
            ("16", "Crude petroleum"),
            ("17", "Gasoline and aviation fuel"),
            ("18", "Fuel oils"),
            ("19", "Natural gas and other fossil fuels"),
            ("20", "Basic chemicals"),
            ("21", "Pharmaceutical products"),
            ("22", "Fertilizers"),
            ("23", "Chemical products"),
            ("24", "Plastics and rubber"),
            ("25", "Logs"),
            ("26", "Wood products"),
            ("27", "Pulp and paper"),
            ("28", "Paper articles"),
            ("29", "Printed products"),
            ("30", "Textiles and leather"),
            ("31", "Nonmetallic mineral products"),
            ("32", "Base metal in primary or semifinished forms"),
            ("33", "Articles of base metal"),
            ("34", "Machinery"),
            ("35", "Electronic and electrical equipment"),
            ("36", "Motorized vehicles"),
            ("37", "Transportation equipment"),
            ("38", "Precision instruments"),
            ("39", "Furniture"),
            ("40", "Miscellaneous manufactured products"),
            ("41", "Waste and scrap"),
            ("43", "Mixed freight"),
        ]


__all__ = ["CFSAPIClient", "CFSFlowRecord", "CFSAPIError"]
