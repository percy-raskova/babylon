"""FCC Broadband Data Collection (BDC) API client.

Downloads broadband availability data files from FCC BDC Public Data API.
Files are downloaded as ZIPs and extracted to local directory for ingestion.

API Base URL: https://broadbandmap.fcc.gov
Rate Limit: 10 calls/minute (6 seconds between calls)
Auth: HTTP headers with username and hash_value

Source: https://broadbandmap.fcc.gov/data-download/nationwide-data
"""

from __future__ import annotations

import logging
import os
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from babylon.data.exceptions import FCCAPIError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# FCC BDC API configuration
FCC_BASE_URL = "https://broadbandmap.fcc.gov"
REQUEST_DELAY_SECONDS = 6.0  # 10 calls/minute = 6 seconds between calls
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0
DEFAULT_TIMEOUT = 60.0  # Longer timeout for file downloads

# Environment variable names for credentials
FCC_USERNAME_ENV = "FCC_USERNAME"
FCC_API_KEY_ENV = "FCC_API_KEY"


@dataclass
class FCCFileInfo:
    """Metadata for a downloadable FCC BDC file.

    Attributes:
        file_id: Unique identifier for the file.
        file_name: Original filename from the API.
        data_type: Type of data (e.g., "availability").
        category: Category (e.g., "Summary by Geography Type").
        state_fips: State FIPS code (if applicable).
        as_of_date: Data vintage date (YYYY-MM-DD format).
    """

    file_id: str
    file_name: str
    data_type: str
    category: str
    state_fips: str | None
    as_of_date: str


class FCCBDCClient:
    """Client for FCC Broadband Data Collection API.

    Handles authentication, rate limiting, and file downloads from the
    FCC BDC Public Data API.

    Attributes:
        base_url: FCC BDC API base URL.
        username: FCC account username.
        api_key: FCC API hash_value token.
        timeout: HTTP request timeout in seconds.

    Example:
        >>> with FCCBDCClient.from_env() as client:
        ...     dates = client.list_as_of_dates()
        ...     files = client.list_availability_files(dates[0], "Summary by Geography Type", "06")
        ...     for f in files:
        ...         client.download_and_extract(f, Path("data/fcc/downloads"))
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        base_url: str = FCC_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize FCC BDC client.

        Args:
            username: FCC account username.
            api_key: FCC API hash_value token.
            base_url: API base URL (default: broadbandmap.fcc.gov).
            timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.api_key = api_key
        self.timeout = timeout
        self._last_request_time = 0.0
        self._client = httpx.Client(timeout=timeout)

    @classmethod
    def from_env(cls) -> FCCBDCClient:
        """Create client from environment variables.

        Reads FCC_USERNAME and FCC_API_KEY from environment.

        Returns:
            Configured FCCBDCClient instance.

        Raises:
            ValueError: If required environment variables are not set.
        """
        username = os.environ.get(FCC_USERNAME_ENV, "")
        api_key = os.environ.get(FCC_API_KEY_ENV, "")

        if not username:
            msg = f"Environment variable {FCC_USERNAME_ENV} is not set"
            raise ValueError(msg)
        if not api_key:
            msg = f"Environment variable {FCC_API_KEY_ENV} is not set"
            raise ValueError(msg)

        return cls(username=username, api_key=api_key)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> FCCBDCClient:
        """Context manager entry."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Context manager exit - close client."""
        self.close()

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        return {
            "username": self.username,
            "hash_value": self.api_key,
        }

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests (6 seconds)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            sleep_time = REQUEST_DELAY_SECONDS - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make rate-limited API request with retries.

        Args:
            method: HTTP method (GET, POST).
            endpoint: API endpoint path (appended to base_url).
            params: Optional query parameters.

        Returns:
            HTTP response object.

        Raises:
            FCCAPIError: If request fails after retries.
        """
        url = f"{self.base_url}{endpoint}"
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            self._rate_limit()

            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=self._get_auth_headers(),
                )

                if response.status_code == 200:
                    return response

                if response.status_code == 429:
                    wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue

                raise FCCAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    url=url,
                )

            except httpx.RequestError as e:
                last_error = e
                wait_time = REQUEST_DELAY_SECONDS * (RETRY_BACKOFF_FACTOR**attempt)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                time.sleep(wait_time)

        raise FCCAPIError(
            status_code=0,
            message=f"Max retries exceeded: {last_error}",
            url=url,
        )

    def list_as_of_dates(self, data_type: str = "availability") -> list[str]:
        """Get available data vintage dates.

        Args:
            data_type: Filter by data type ("availability" or "challenge").

        Returns:
            List of as_of_date strings (YYYY-MM-DD format), sorted descending.
        """
        response = self._request("GET", "/api/public/map/listAsOfDates")
        data: dict[str, Any] = response.json()

        # API returns {"data": [{"data_type": "availability", "as_of_date": "2024-06-30"}, ...]}
        raw_data: list[dict[str, str]] = data.get("data", [])

        # Filter by data_type and extract dates
        dates: list[str] = [
            entry["as_of_date"]
            for entry in raw_data
            if entry.get("data_type") == data_type and "as_of_date" in entry
        ]
        return sorted(dates, reverse=True)

    def list_availability_files(
        self,
        as_of_date: str,
        category: str | None = None,
        subcategory: str | None = None,
        state_fips: str | None = None,
        technology_type: str | None = None,
    ) -> list[FCCFileInfo]:
        """List available files for a given date.

        Args:
            as_of_date: Data vintage date (YYYY-MM-DD format).
            category: Filter by category (e.g., "Provider", "State", "Summary").
            subcategory: Filter by subcategory (e.g., "Hexagon Coverage").
            state_fips: Filter by 2-digit state FIPS code.
            technology_type: Filter by technology (e.g., "Fixed Broadband", "Mobile Broadband").

        Returns:
            List of FCCFileInfo objects for matching files.
        """
        endpoint = f"/api/public/map/downloads/listAvailabilityData/{as_of_date}"
        response = self._request("GET", endpoint)
        data: dict[str, Any] = response.json()

        # API returns flat list of file entries
        files: list[FCCFileInfo] = []
        raw_data = data.get("data", [])

        for entry in raw_data:
            entry_category = entry.get("category", "")
            entry_subcategory = entry.get("subcategory", "")
            entry_state = entry.get("state_fips", "")
            entry_tech = entry.get("technology_type", "")

            # Apply filters
            if category and entry_category != category:
                continue
            if subcategory and entry_subcategory != subcategory:
                continue
            if state_fips and entry_state and entry_state != state_fips:
                continue
            if technology_type and entry_tech != technology_type:
                continue

            # Each entry is a file record
            file_info = FCCFileInfo(
                file_id=str(entry.get("file_id", "")),
                file_name=entry.get("file_name", ""),
                data_type="availability",
                category=f"{entry_category}/{entry_subcategory}",
                state_fips=entry_state if entry_state else None,
                as_of_date=as_of_date,
            )
            if file_info.file_id:
                files.append(file_info)

        return files

    def download_file(
        self,
        file_info: FCCFileInfo,
        output_dir: Path,
    ) -> Path:
        """Download a single file (ZIP).

        Args:
            file_info: File metadata from list_availability_files.
            output_dir: Directory to save downloaded file.

        Returns:
            Path to downloaded ZIP file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Construct download URL
        endpoint = (
            f"/api/public/map/downloads/downloadFile/{file_info.data_type}/{file_info.file_id}"
        )

        logger.info(f"Downloading {file_info.file_name}...")
        response = self._request("GET", endpoint)

        # Determine output filename
        output_path = output_dir / f"{file_info.file_id}.zip"
        output_path.write_bytes(response.content)

        logger.info(f"Downloaded {output_path} ({len(response.content):,} bytes)")
        return output_path

    def download_and_extract(
        self,
        file_info: FCCFileInfo,
        output_dir: Path,
    ) -> list[Path]:
        """Download and extract a ZIP file.

        Args:
            file_info: File metadata from list_availability_files.
            output_dir: Directory to extract files to.

        Returns:
            List of paths to extracted files.
        """
        # Download ZIP
        zip_path = self.download_file(file_info, output_dir)

        # Extract contents
        extracted_files: list[Path] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                # Skip directories and hidden files
                if member.endswith("/") or member.startswith("__"):
                    continue

                extracted_path = output_dir / member
                extracted_path.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(member) as src, open(extracted_path, "wb") as dst:
                    dst.write(src.read())

                extracted_files.append(extracted_path)
                logger.debug(f"Extracted: {extracted_path}")

        # Clean up ZIP file
        zip_path.unlink()
        logger.info(f"Extracted {len(extracted_files)} files from {file_info.file_name}")

        return extracted_files


def download_state_summaries(
    state_fips: str,
    output_dir: Path,
    as_of_date: str | None = None,
) -> list[Path]:
    """Download state summary data for broadband coverage.

    Downloads Summary by Geography Type - Census Place files for a state.

    Args:
        state_fips: 2-digit state FIPS code (e.g., "06" for California).
        output_dir: Base directory for downloads.
        as_of_date: Specific date to download. If None, uses latest.

    Returns:
        List of paths to extracted CSV files.
    """
    with FCCBDCClient.from_env() as client:
        # Get latest date if not specified
        if as_of_date is None:
            dates = client.list_as_of_dates()
            if not dates:
                msg = "No data dates available from FCC BDC API"
                raise FCCAPIError(status_code=0, message=msg, url="")
            as_of_date = dates[0]
            logger.info(f"Using latest as_of_date: {as_of_date}")

        # Construct output path: output_dir/{as_of_date}/{state_fips}/summary/
        state_output_dir = output_dir / as_of_date / state_fips / "summary"
        state_output_dir.mkdir(parents=True, exist_ok=True)

        # List Summary files for this state
        files = client.list_availability_files(
            as_of_date=as_of_date,
            category="Summary",
            subcategory="Summary by Geography Type - Census Place",
            state_fips=state_fips,
        )

        if not files:
            logger.warning(
                f"No Summary by Geography Type files found for state {state_fips} on {as_of_date}"
            )
            return []

        logger.info(f"Found {len(files)} summary files to download for state {state_fips}")

        # Download and extract all files
        all_extracted: list[Path] = []
        for file_info in files:
            extracted = client.download_and_extract(file_info, state_output_dir)
            all_extracted.extend(extracted)

        logger.info(
            f"Downloaded {len(files)} files, extracted {len(all_extracted)} files "
            f"to {state_output_dir}"
        )
        return all_extracted


def download_state_hexagons(
    state_fips: str,
    output_dir: Path,
    as_of_date: str | None = None,
    technology_type: str = "Fixed Broadband",
) -> list[Path]:
    """Download H3 hexagon coverage data for a state.

    Downloads Hexagon Coverage GIS files from the State category.
    These contain H3 hexagon-aggregated coverage data suitable for
    Uber H3 spatial analysis.

    Args:
        state_fips: 2-digit state FIPS code (e.g., "06" for California).
        output_dir: Base directory for downloads.
        as_of_date: Specific date to download. If None, uses latest.
        technology_type: "Fixed Broadband" or "Mobile Broadband".

    Returns:
        List of paths to extracted GIS files.
    """
    with FCCBDCClient.from_env() as client:
        # Get latest date if not specified
        if as_of_date is None:
            dates = client.list_as_of_dates()
            if not dates:
                msg = "No data dates available from FCC BDC API"
                raise FCCAPIError(status_code=0, message=msg, url="")
            as_of_date = dates[0]
            logger.info(f"Using latest as_of_date: {as_of_date}")

        # Construct output path: output_dir/{as_of_date}/{state_fips}/hexagon/
        state_output_dir = output_dir / as_of_date / state_fips / "hexagon"
        state_output_dir.mkdir(parents=True, exist_ok=True)

        # List State-level Hexagon Coverage files for this state
        files = client.list_availability_files(
            as_of_date=as_of_date,
            category="State",
            subcategory="Hexagon Coverage",
            state_fips=state_fips,
            technology_type=technology_type,
        )

        if not files:
            logger.warning(
                f"No State Hexagon Coverage files found for state {state_fips} "
                f"({technology_type}) on {as_of_date}"
            )
            return []

        logger.info(
            f"Found {len(files)} hexagon files to download for state {state_fips} "
            f"({technology_type})"
        )

        # Download and extract all files
        all_extracted: list[Path] = []
        for file_info in files:
            extracted = client.download_and_extract(file_info, state_output_dir)
            all_extracted.extend(extracted)

        logger.info(
            f"Downloaded {len(files)} files, extracted {len(all_extracted)} files "
            f"to {state_output_dir}"
        )
        return all_extracted


def download_national_summaries(
    output_dir: Path,
    as_of_date: str | None = None,
) -> list[Path]:
    """Download national summary data including county-level coverage.

    Downloads Summary by Geography Type - Other Geographies files which
    contain county, congressional district, and tribal area coverage data.

    Args:
        output_dir: Base directory for downloads.
        as_of_date: Specific date to download. If None, uses latest.

    Returns:
        List of paths to extracted CSV files.
    """
    with FCCBDCClient.from_env() as client:
        # Get latest date if not specified
        if as_of_date is None:
            dates = client.list_as_of_dates()
            if not dates:
                msg = "No data dates available from FCC BDC API"
                raise FCCAPIError(status_code=0, message=msg, url="")
            as_of_date = dates[0]
            logger.info(f"Using latest as_of_date: {as_of_date}")

        # Construct output path: output_dir/{as_of_date}/national/
        nat_output_dir = output_dir / as_of_date / "national"
        nat_output_dir.mkdir(parents=True, exist_ok=True)

        # List national Summary by Geography Type - Other Geographies files
        files = client.list_availability_files(
            as_of_date=as_of_date,
            category="Summary",
            subcategory="Summary by Geography Type - Other Geographies",
        )

        if not files:
            logger.warning(f"No national summary files found on {as_of_date}")
            return []

        logger.info(f"Found {len(files)} national summary files to download")

        # Download and extract all files
        all_extracted: list[Path] = []
        for file_info in files:
            extracted = client.download_and_extract(file_info, nat_output_dir)
            all_extracted.extend(extracted)

        logger.info(
            f"Downloaded {len(files)} files, extracted {len(all_extracted)} files "
            f"to {nat_output_dir}"
        )
        return all_extracted


__all__ = [
    "FCCBDCClient",
    "FCCFileInfo",
    "FCCAPIError",
    "download_national_summaries",
    "download_state_hexagons",
    "download_state_summaries",
]
