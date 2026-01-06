"""BLS QCEW (Quarterly Census of Employment and Wages) API client.

Provides rate-limited access to the BLS QCEW Open Data API for fetching
employment and wage data by area, industry, or establishment size class.

API Documentation: https://www.bls.gov/cew/additional-resources/open-data/
"""

from __future__ import annotations

import csv
import io
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# QCEW API configuration
BASE_URL = "https://data.bls.gov/cew/data/api"

# Rate limiting: BLS has no official limit, but be polite
# Conservative 0.5s delay between requests
REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0
DEFAULT_TIMEOUT = 60.0  # Large CSV files may take time


@dataclass
class QcewAPIError(Exception):
    """Error from QCEW API."""

    status_code: int
    message: str
    url: str


@dataclass
class QcewAreaRecord:
    """Parsed record from QCEW area slice CSV."""

    # Geographic
    area_fips: str
    own_code: str
    industry_code: str
    agglvl_code: int
    size_code: str
    year: int
    qtr: str

    # Core metrics
    disclosure_code: str
    annual_avg_estabs: int | None
    annual_avg_emplvl: int | None
    total_annual_wages: float | None
    taxable_annual_wages: float | None
    annual_contributions: float | None
    annual_avg_wkly_wage: int | None
    avg_annual_pay: int | None

    # Location quotients
    lq_disclosure_code: str
    lq_annual_avg_estabs: float | None
    lq_annual_avg_emplvl: float | None
    lq_total_annual_wages: float | None
    lq_taxable_annual_wages: float | None
    lq_annual_contributions: float | None
    lq_annual_avg_wkly_wage: float | None
    lq_avg_annual_pay: float | None

    # Year-over-year changes
    oty_disclosure_code: str
    oty_annual_avg_estabs_chg: int | None
    oty_annual_avg_estabs_pct_chg: float | None
    oty_annual_avg_emplvl_chg: int | None
    oty_annual_avg_emplvl_pct_chg: float | None
    oty_total_annual_wages_chg: float | None
    oty_total_annual_wages_pct_chg: float | None
    oty_taxable_annual_wages_chg: float | None
    oty_taxable_annual_wages_pct_chg: float | None
    oty_annual_contributions_chg: float | None
    oty_annual_contributions_pct_chg: float | None
    oty_annual_avg_wkly_wage_chg: int | None
    oty_annual_avg_wkly_wage_pct_chg: float | None
    oty_avg_annual_pay_chg: int | None
    oty_avg_annual_pay_pct_chg: float | None


class QcewAPIClient:
    """Client for BLS QCEW Open Data API.

    Fetches employment and wage data with rate limiting and error handling.
    No authentication required.

    Example:
        with QcewAPIClient() as client:
            for record in client.get_area_annual_data(2023, "01001"):
                print(f"{record.industry_code}: {record.annual_avg_emplvl}")
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize QCEW API client."""
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> QcewAPIClient:
        """Enter context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager."""
        self.close()

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _fetch_csv(self, url: str) -> str:
        """Fetch CSV data from URL with retries."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.get(url)

                if response.status_code == 200:
                    return response.text

                if response.status_code == 404:
                    # Area/year combination doesn't exist - log and raise
                    msg = f"Data not available: {url}"
                    logger.info(msg)  # Info level - expected for some areas
                    raise QcewAPIError(
                        status_code=404,
                        message="Data not available for this area/year",
                        url=url,
                    )

                if response.status_code == 429:
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                    msg = f"Rate limited, waiting {wait_time:.1f}s"
                    logger.warning(msg)
                    print(msg)  # Console output for visibility
                    time.sleep(wait_time)
                    continue

                # Unexpected error - log to both console and logger
                msg = f"API error {response.status_code}: {url}"
                logger.error(msg)
                print(f"ERROR: {msg}")  # Console visibility
                raise QcewAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=url,
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise QcewAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=url,
        )

    def get_area_annual_data(
        self,
        year: int,
        area_fips: str,
    ) -> Iterator[QcewAreaRecord]:
        """Fetch annual QCEW data for a specific area.

        Args:
            year: Calendar year (e.g., 2023).
            area_fips: Area FIPS code (e.g., "01001" for Autauga County, AL).

        Yields:
            QcewAreaRecord for each data row.

        Raises:
            QcewAPIError: If request fails.
        """
        url = f"{BASE_URL}/{year}/a/area/{area_fips}.csv"
        csv_text = self._fetch_csv(url)
        yield from self._parse_area_csv(csv_text)

    def get_industry_annual_data(
        self,
        year: int,
        naics_code: str,
    ) -> Iterator[QcewAreaRecord]:
        """Fetch annual QCEW data for a specific industry.

        Args:
            year: Calendar year.
            naics_code: NAICS code (hyphens converted to underscores).

        Yields:
            QcewAreaRecord for each data row.
        """
        # Convert hyphens to underscores for API
        api_code = naics_code.replace("-", "_")
        url = f"{BASE_URL}/{year}/a/industry/{api_code}.csv"
        csv_text = self._fetch_csv(url)
        yield from self._parse_area_csv(csv_text)

    def _parse_area_csv(self, csv_text: str) -> Iterator[QcewAreaRecord]:
        """Parse CSV text into QcewAreaRecord objects."""
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            try:
                yield QcewAreaRecord(
                    area_fips=row["area_fips"].strip(),
                    own_code=row["own_code"].strip(),
                    industry_code=row["industry_code"].strip(),
                    agglvl_code=int(row["agglvl_code"]),
                    size_code=row["size_code"].strip(),
                    year=int(row["year"]),
                    qtr=row["qtr"].strip(),
                    disclosure_code=row.get("disclosure_code", "").strip(),
                    annual_avg_estabs=_safe_int(row.get("annual_avg_estabs", "")),
                    annual_avg_emplvl=_safe_int(row.get("annual_avg_emplvl", "")),
                    total_annual_wages=_safe_float(row.get("total_annual_wages", "")),
                    taxable_annual_wages=_safe_float(row.get("taxable_annual_wages", "")),
                    annual_contributions=_safe_float(row.get("annual_contributions", "")),
                    annual_avg_wkly_wage=_safe_int(row.get("annual_avg_wkly_wage", "")),
                    avg_annual_pay=_safe_int(row.get("avg_annual_pay", "")),
                    lq_disclosure_code=row.get("lq_disclosure_code", "").strip(),
                    lq_annual_avg_estabs=_safe_float(row.get("lq_annual_avg_estabs", "")),
                    lq_annual_avg_emplvl=_safe_float(row.get("lq_annual_avg_emplvl", "")),
                    lq_total_annual_wages=_safe_float(row.get("lq_total_annual_wages", "")),
                    lq_taxable_annual_wages=_safe_float(row.get("lq_taxable_annual_wages", "")),
                    lq_annual_contributions=_safe_float(row.get("lq_annual_contributions", "")),
                    lq_annual_avg_wkly_wage=_safe_float(row.get("lq_annual_avg_wkly_wage", "")),
                    lq_avg_annual_pay=_safe_float(row.get("lq_avg_annual_pay", "")),
                    oty_disclosure_code=row.get("oty_disclosure_code", "").strip(),
                    oty_annual_avg_estabs_chg=_safe_int(row.get("oty_annual_avg_estabs_chg", "")),
                    oty_annual_avg_estabs_pct_chg=_safe_float(
                        row.get("oty_annual_avg_estabs_pct_chg", "")
                    ),
                    oty_annual_avg_emplvl_chg=_safe_int(row.get("oty_annual_avg_emplvl_chg", "")),
                    oty_annual_avg_emplvl_pct_chg=_safe_float(
                        row.get("oty_annual_avg_emplvl_pct_chg", "")
                    ),
                    oty_total_annual_wages_chg=_safe_float(
                        row.get("oty_total_annual_wages_chg", "")
                    ),
                    oty_total_annual_wages_pct_chg=_safe_float(
                        row.get("oty_total_annual_wages_pct_chg", "")
                    ),
                    oty_taxable_annual_wages_chg=_safe_float(
                        row.get("oty_taxable_annual_wages_chg", "")
                    ),
                    oty_taxable_annual_wages_pct_chg=_safe_float(
                        row.get("oty_taxable_annual_wages_pct_chg", "")
                    ),
                    oty_annual_contributions_chg=_safe_float(
                        row.get("oty_annual_contributions_chg", "")
                    ),
                    oty_annual_contributions_pct_chg=_safe_float(
                        row.get("oty_annual_contributions_pct_chg", "")
                    ),
                    oty_annual_avg_wkly_wage_chg=_safe_int(
                        row.get("oty_annual_avg_wkly_wage_chg", "")
                    ),
                    oty_annual_avg_wkly_wage_pct_chg=_safe_float(
                        row.get("oty_annual_avg_wkly_wage_pct_chg", "")
                    ),
                    oty_avg_annual_pay_chg=_safe_int(row.get("oty_avg_annual_pay_chg", "")),
                    oty_avg_annual_pay_pct_chg=_safe_float(
                        row.get("oty_avg_annual_pay_pct_chg", "")
                    ),
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping malformed row: {e}")
                continue


def _safe_int(value: str) -> int | None:
    """Convert string to int, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _safe_float(value: str) -> float | None:
    """Convert string to float, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


# Area code utilities
def get_state_area_code(state_fips: str) -> str:
    """Convert 2-digit state FIPS to QCEW area code.

    State-level area codes are state FIPS + "000".
    Example: "01" (Alabama) -> "01000"
    """
    return f"{state_fips}000"


def get_county_area_codes(state_fips: str) -> list[str]:
    """Get list of county FIPS codes for a state.

    This requires DimCounty to be populated first (by CensusLoader).
    Returns 5-digit county FIPS codes.
    """
    # This will be called from the loader with session access
    raise NotImplementedError("Call from loader with session access")


__all__ = [
    "QcewAPIClient",
    "QcewAPIError",
    "QcewAreaRecord",
    "get_state_area_code",
    "_safe_int",
    "_safe_float",
]
