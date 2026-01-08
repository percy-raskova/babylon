"""FRED (Federal Reserve Economic Data) API client.

Provides rate-limited access to the FRED REST API for fetching
macroeconomic time series data.

API Documentation: https://fred.stlouisfed.org/docs/api/fred/

Environment:
    FRED_API_KEY: API key for FRED access (required).
        Register at: https://fredaccount.stlouisfed.org/apikeys
"""

import contextlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from babylon.data.exceptions import FredAPIError

logger = logging.getLogger(__name__)

# FRED API configuration
BASE_URL = "https://api.stlouisfed.org/fred"
DEFAULT_FILE_TYPE = "json"

# Rate limiting: FRED allows ~120 requests/minute
# We use conservative 0.5s delay to stay well under limits
REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0


@dataclass
class SeriesMetadata:
    """Metadata for a FRED series."""

    series_id: str
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    observation_start: str
    observation_end: str
    last_updated: str
    source: str = ""


@dataclass
class Observation:
    """Single observation from a FRED series."""

    date: str
    value: float | None


@dataclass
class SeriesData:
    """Complete series data with metadata and observations."""

    metadata: SeriesMetadata
    observations: list[Observation] = field(default_factory=list)


class FredAPIClient:
    """Client for FRED REST API.

    Fetches macroeconomic time series with rate limiting and error handling.
    Supports national indicators, state-level unemployment, and industry
    unemployment series.

    Attributes:
        api_key: FRED API key.
        timeout: HTTP request timeout in seconds.

    Example:
        >>> with FredAPIClient() as client:
        ...     data = client.get_series_observations("CPIAUCSL", "2022-01-01", "2022-12-31")
        ...     print(f"Got {len(data.observations)} observations")
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize FRED API client.

        Args:
            api_key: FRED API key. If None, reads from FRED_API_KEY env var.
            timeout: HTTP request timeout in seconds.

        Raises:
            ValueError: If no API key provided and FRED_API_KEY not set.
        """
        self.api_key = api_key or os.environ.get("FRED_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FRED API key required. Set FRED_API_KEY environment variable "
                "or pass api_key parameter. Register at: "
                "https://fredaccount.stlouisfed.org/apikeys"
            )
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "FredAPIClient":
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
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make rate-limited API request with retries.

        Args:
            endpoint: API endpoint path (e.g., "series").
            params: Query parameters.

        Returns:
            JSON response data.

        Raises:
            FredAPIError: If request fails after retries.
        """
        if params is None:
            params = {}

        # Add required parameters
        params["api_key"] = self.api_key  # type: ignore[assignment]
        params["file_type"] = DEFAULT_FILE_TYPE

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
                    # Bad request - likely invalid series ID
                    error_msg = response.text[:500]
                    raise FredAPIError(
                        status_code=response.status_code,
                        message=f"Bad request: {error_msg}",
                        url=str(response.url),
                    )

                raise FredAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=str(response.url),
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise FredAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=url,
        )

    def get_series_info(self, series_id: str) -> SeriesMetadata:
        """Fetch metadata for a series.

        Args:
            series_id: FRED series identifier (e.g., "CPIAUCSL").

        Returns:
            SeriesMetadata with title, units, frequency, etc.
        """
        data = self._request("series", {"series_id": series_id})

        if "seriess" not in data or not data["seriess"]:
            raise FredAPIError(
                status_code=404,
                message=f"Series not found: {series_id}",
                url=f"{BASE_URL}/series?series_id={series_id}",
            )

        series = data["seriess"][0]
        return SeriesMetadata(
            series_id=series.get("id", series_id),
            title=series.get("title", ""),
            units=series.get("units", ""),
            frequency=series.get("frequency", ""),
            seasonal_adjustment=series.get("seasonal_adjustment", ""),
            observation_start=series.get("observation_start", ""),
            observation_end=series.get("observation_end", ""),
            last_updated=series.get("last_updated", ""),
            source=series.get("source_title", ""),
        )

    def get_series_observations(
        self,
        series_id: str,
        observation_start: str | None = None,
        observation_end: str | None = None,
        frequency: str | None = None,
    ) -> SeriesData:
        """Fetch observations for a series.

        Args:
            series_id: FRED series identifier.
            observation_start: Start date (YYYY-MM-DD).
            observation_end: End date (YYYY-MM-DD).
            frequency: Aggregation frequency (a=annual, q=quarterly, m=monthly).

        Returns:
            SeriesData with metadata and observations.
        """
        # First get metadata
        metadata = self.get_series_info(series_id)

        # Build parameters
        params: dict[str, str] = {"series_id": series_id}
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        if frequency:
            params["frequency"] = frequency

        # Fetch observations
        data = self._request("series/observations", params)

        observations: list[Observation] = []
        for obs in data.get("observations", []):
            value_str = obs.get("value", "")
            value: float | None = None
            if value_str and value_str != ".":
                with contextlib.suppress(ValueError):
                    value = float(value_str)

            observations.append(
                Observation(
                    date=obs.get("date", ""),
                    value=value,
                )
            )

        return SeriesData(
            metadata=metadata,
            observations=observations,
        )

    def get_state_unemployment_series_id(self, fips_code: str) -> str:
        """Generate LAUST series ID for state unemployment.

        Args:
            fips_code: 2-digit state FIPS code (e.g., "12" for Florida).

        Returns:
            LAUST series ID (e.g., "LAUST120000000000003A").
        """
        # LAUST format: LAUST + FIPS (padded to 2 digits) + 0000000000003A
        # The suffix 03A indicates unemployment rate (annual, not seasonally adjusted)
        return f"LAUST{fips_code.zfill(2)}0000000000003A"

    def get_state_unemployment(
        self,
        fips_code: str,
        observation_start: str | None = None,
        observation_end: str | None = None,
    ) -> SeriesData:
        """Fetch state unemployment rate.

        Args:
            fips_code: 2-digit state FIPS code.
            observation_start: Start date (YYYY-MM-DD).
            observation_end: End date (YYYY-MM-DD).

        Returns:
            SeriesData with unemployment observations.
        """
        series_id = self.get_state_unemployment_series_id(fips_code)
        return self.get_series_observations(
            series_id,
            observation_start=observation_start,
            observation_end=observation_end,
        )


# Mapping of US states to FIPS codes
US_STATES = {
    "01": ("Alabama", "AL"),
    "02": ("Alaska", "AK"),
    "04": ("Arizona", "AZ"),
    "05": ("Arkansas", "AR"),
    "06": ("California", "CA"),
    "08": ("Colorado", "CO"),
    "09": ("Connecticut", "CT"),
    "10": ("Delaware", "DE"),
    "11": ("District of Columbia", "DC"),
    "12": ("Florida", "FL"),
    "13": ("Georgia", "GA"),
    "15": ("Hawaii", "HI"),
    "16": ("Idaho", "ID"),
    "17": ("Illinois", "IL"),
    "18": ("Indiana", "IN"),
    "19": ("Iowa", "IA"),
    "20": ("Kansas", "KS"),
    "21": ("Kentucky", "KY"),
    "22": ("Louisiana", "LA"),
    "23": ("Maine", "ME"),
    "24": ("Maryland", "MD"),
    "25": ("Massachusetts", "MA"),
    "26": ("Michigan", "MI"),
    "27": ("Minnesota", "MN"),
    "28": ("Mississippi", "MS"),
    "29": ("Missouri", "MO"),
    "30": ("Montana", "MT"),
    "31": ("Nebraska", "NE"),
    "32": ("Nevada", "NV"),
    "33": ("New Hampshire", "NH"),
    "34": ("New Jersey", "NJ"),
    "35": ("New Mexico", "NM"),
    "36": ("New York", "NY"),
    "37": ("North Carolina", "NC"),
    "38": ("North Dakota", "ND"),
    "39": ("Ohio", "OH"),
    "40": ("Oklahoma", "OK"),
    "41": ("Oregon", "OR"),
    "42": ("Pennsylvania", "PA"),
    "44": ("Rhode Island", "RI"),
    "45": ("South Carolina", "SC"),
    "46": ("South Dakota", "SD"),
    "47": ("Tennessee", "TN"),
    "48": ("Texas", "TX"),
    "49": ("Utah", "UT"),
    "50": ("Vermont", "VT"),
    "51": ("Virginia", "VA"),
    "53": ("Washington", "WA"),
    "54": ("West Virginia", "WV"),
    "55": ("Wisconsin", "WI"),
    "56": ("Wyoming", "WY"),
}

# Industry unemployment series mapping
# LNU04 prefix = unemployment rate
INDUSTRY_UNEMPLOYMENT_SERIES = {
    "LNU04032231": ("Construction", "23"),  # NAICS 23
    "LNU04032232": ("Manufacturing", "31-33"),  # NAICS 31-33
    "LNU04032236": ("Transportation and Utilities", "48-49"),  # NAICS 48-49
    "LNU04032237": ("Information", "51"),  # NAICS 51
    "LNU04032238": ("Financial Activities", "52-53"),  # NAICS 52-53
    "LNU04032239": ("Professional and Business Services", "54-56"),  # NAICS 54-56
    "LNU04032240": ("Education and Health Services", "61-62"),  # NAICS 61-62
    "LNU04032241": ("Leisure and Hospitality", "71-72"),  # NAICS 71-72
}

# National series for core economic indicators
NATIONAL_SERIES = {
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
    "AHETPI": "Average Hourly Earnings of All Employees, Total Private",
    "UNRATE": "Unemployment Rate",
    "GFDEBTN": "Federal Debt: Total Public Debt",
    "GINIALLRF": "GINI Index for the United States",
    "M2SL": "M2 Money Stock",
    "PPPTTLUSA618NUPN": "Purchasing Power Parity over GDP",
    "RGDPCHUSA625NUPN": "Real GDP per Capita (PPP)",
}


# =============================================================================
# DFA (Distributional Financial Accounts) Wealth Distribution Series
# =============================================================================
# Federal Reserve quarterly data on household wealth distribution since 1989.
# Source: https://www.federalreserve.gov/releases/z1/dataviz/dfa/
#
# These series map directly to Babylon's MLM-TW class categories for modeling
# wealth concentration and "stake in empire" dynamics.

# Percentile class mapping to Babylon social classes
DFA_WEALTH_CLASSES: dict[str, dict[str, str | float]] = {
    "LT01": {
        "label": "Top 1%",
        "percentile_min": 99.0,
        "percentile_max": 100.0,
        "babylon_class": "core_bourgeoisie",
        "description": (
            "Global Capital Accumulation - Transnational capitalist class "
            "controlling finance capital. Stakes in empire depend on continued "
            "imperial extraction from the periphery."
        ),
    },
    "N09": {
        "label": "90-99%",
        "percentile_min": 90.0,
        "percentile_max": 99.0,
        "babylon_class": "petty_bourgeoisie",
        "description": (
            "Enforcers & High-Level Functionaries - Professional-managerial class "
            "(executives, doctors, lawyers). Buffer stratum enforcing capitalist "
            "relations in exchange for above-median wealth accumulation."
        ),
    },
    "N40": {
        "label": "50-90%",
        "percentile_min": 50.0,
        "percentile_max": 90.0,
        "babylon_class": "labor_aristocracy",
        "description": (
            "The Junior Partner - Core workers receiving super-wages from imperial "
            "rent. Real estate holdings are the 'material basis of fascism' - "
            "property values tie them to the settler-colonial project."
        ),
    },
    "B50": {
        "label": "Bottom 50%",
        "percentile_min": 0.0,
        "percentile_max": 50.0,
        "babylon_class": "internal_proletariat",
        "description": (
            "The Excluded - Those with 'nothing to lose but their chains.' "
            "Net worth often negative (debt exceeds assets). Includes internal "
            "colonies: Black, Indigenous, imprisoned populations."
        ),
    },
}

# Asset category metadata with Marxian interpretations
DFA_ASSET_CATEGORIES: dict[str, dict[str, str]] = {
    "TOTAL_ASSETS": {
        "label": "Total Assets",
        "interpretation": (
            "Stake in Empire - what this class has to lose by revolution. "
            "Total assets (not net worth) measure entrenchment in the system."
        ),
    },
    "REAL_ESTATE": {
        "label": "Real Estate",
        "interpretation": (
            "Material Basis of Fascism (after Sakai) - land value ties settlers "
            "to the colonial project. Real estate wealth is WHY the 'middle class' "
            "defends the state."
        ),
    },
    "NET_WORTH": {
        "label": "Net Worth",
        "interpretation": (
            "Overall class position - assets minus liabilities. Often negative "
            "for bottom 50%. Shows who is truly 'wageless' - living on credit."
        ),
    },
}

# DFA Series IDs - Wealth Levels ($ Millions, Quarterly)
# Format: WFRBL{percentile}{sequence} for absolute dollar values
DFA_WEALTH_LEVEL_SERIES: dict[tuple[str, str], str] = {
    # Total Assets by percentile class
    ("LT01", "TOTAL_ASSETS"): "WFRBLT01000",
    ("N09", "TOTAL_ASSETS"): "WFRBLN09027",
    ("N40", "TOTAL_ASSETS"): "WFRBLN40054",
    ("B50", "TOTAL_ASSETS"): "WFRBLB50081",
    # Real Estate by percentile class
    ("LT01", "REAL_ESTATE"): "WFRBLT01002",
    ("N09", "REAL_ESTATE"): "WFRBLN09029",
    ("N40", "REAL_ESTATE"): "WFRBLN40056",
    ("B50", "REAL_ESTATE"): "WFRBLB50083",
    # Net Worth by percentile class
    ("LT01", "NET_WORTH"): "WFRBLT01026",
    ("N09", "NET_WORTH"): "WFRBLN09053",
    ("N40", "NET_WORTH"): "WFRBLN40080",
    ("B50", "NET_WORTH"): "WFRBLB50107",
}

# DFA Series IDs - Wealth Shares (%, Quarterly)
# Format: WFRBS{percentile}{sequence} for percentage shares
DFA_WEALTH_SHARE_SERIES: dict[tuple[str, str], str] = {
    # Share of Net Worth by percentile class
    ("LT01", "NET_WORTH"): "WFRBST01134",
    ("N09", "NET_WORTH"): "WFRBSN09161",
    ("N40", "NET_WORTH"): "WFRBSN40188",
    ("B50", "NET_WORTH"): "WFRBSB50215",
    # Share of Total Assets by percentile class
    ("LT01", "TOTAL_ASSETS"): "WFRBST01108",
    ("N09", "TOTAL_ASSETS"): "WFRBSN09135",
    ("N40", "TOTAL_ASSETS"): "WFRBSN40162",
    ("B50", "TOTAL_ASSETS"): "WFRBSB50189",
}
