"""BLS Unemployment Decomposition loader (Feature 021, FR-014).

Loads county-level unemployment decomposition from BLS LAUS API into
FactBLSUnemploymentDecomposition. Uses annual averages (period M13).

BLS LAUS series ID format: LAUCN{FIPS5}00000000{measure2}
  Measures: 03=unemp_rate, 04=unemp_count, 05=emp_count, 06=labor_force

Environment:
    BLS_API_KEY: Registration key for v2 API (500 req/day, 50 series/req).
    Without key, uses v1 (25 req/day, 25 series/req).

Note: U-6, PTER, discouraged, marginally_attached are CPS state-level
only — not available at county level. These are set to 0.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from babylon.data.loader_base import DataLoader, LoadStats

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from babylon.data.preflight import PreflightCheck

logger = logging.getLogger(__name__)

# BLS API v2 (with key): 500 req/day, 50 series/req, 20-year span
# BLS API v1 (no key): 25 req/day, 25 series/req, 10-year span
BLS_API_V2_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_API_V1_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
MAX_YEAR_SPAN = 20
COUNTIES_PER_BATCH = 12
REQUEST_DELAY = 0.55


def _build_series_id(fips: str, measure: str) -> str:
    """Build LAUS series ID: LAUCN{FIPS5}00000000{measure2}."""
    return f"LAUCN{fips}00000000{measure}"


def _get_bls_api_key() -> str | None:
    """Read BLS API key from environment."""
    return os.environ.get("BLS_API_KEY")


def _fetch_bls_batch(
    series_ids: list[str],
    start_year: int,
    end_year: int,
) -> dict[str, dict[int, str]]:
    """Fetch a batch of series from BLS API.

    Uses v2 endpoint if BLS_API_KEY is set, falls back to v1.

    Returns:
        Dict mapping series_id -> {year: value} for annual averages (M13).
    """
    api_key = _get_bls_api_key()
    url = BLS_API_V2_URL if api_key else BLS_API_V1_URL

    body: dict[str, object] = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
        "annualaverage": True,
    }
    if api_key:
        body["registrationkey"] = api_key

    payload = json.dumps(body)
    req = urllib.request.Request(
        url, data=payload.encode(), headers={"Content-Type": "application/json"}
    )

    data: dict[str, Any] = {}
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == max_retries - 1:
                logger.warning("BLS API failed after %d retries: %s", max_retries, exc)
                return {}
            time.sleep(2.0 * (attempt + 1))

    if data.get("status") != "REQUEST_SUCCEEDED":
        logger.warning("BLS API error: %s", data.get("message", []))
        return {}

    result: dict[str, dict[int, str]] = {}
    for series in data.get("Results", {}).get("series", []):
        sid = series["seriesID"]
        year_vals: dict[int, str] = {}
        for point in series.get("data", []):
            if point.get("period") == "M13":
                year_vals[int(point["year"])] = point["value"]
        result[sid] = year_vals

    return result


def _parse_bls_int(value: str) -> int:
    """Parse BLS comma-formatted integer string."""
    return int(value.replace(",", "") or "0")


class BLSUnemploymentLoader(DataLoader):
    """Loads BLS unemployment decomposition into 3NF schema via API.

    Feature 021: Capital Volume I Production Dynamics (FR-014).
    """

    SOURCE_CODE = "BLS_LAUS"

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,  # noqa: ARG002
    ) -> LoadStats:
        """Load BLS unemployment data from API for all counties."""
        from babylon.data.reference.schema import FactBLSUnemploymentDecomposition

        stats = LoadStats(source=self.SOURCE_CODE)

        if reset:
            self._clear_checkpoints(session, self.SOURCE_CODE)
            session.query(FactBLSUnemploymentDecomposition).delete()
            session.flush()

        source_id = self._get_or_create_data_source(
            session,
            source_code=self.SOURCE_CODE,
            source_name="BLS Local Area Unemployment Statistics",
            source_agency="Bureau of Labor Statistics",
            coverage_start_year=self.config.bls_unemployment_years[0],
            coverage_end_year=self.config.bls_unemployment_years[-1],
        )

        years = self.config.bls_unemployment_years
        county_lookup = self._build_county_lookup(session)
        fips_list = list(county_lookup.keys())
        year_ranges = _compute_year_ranges(min(years), max(years))

        time_ids: dict[int, int] = {}
        for year in years:
            time_ids[year] = self._get_or_create_time(session, year)

        row_count = 0
        total_batches = ((len(fips_list) + COUNTIES_PER_BATCH - 1) // COUNTIES_PER_BATCH) * len(
            year_ranges
        )
        batch_num = 0

        for span_start, span_end in year_ranges:
            for i in range(0, len(fips_list), COUNTIES_PER_BATCH):
                batch_fips = fips_list[i : i + COUNTIES_PER_BATCH]
                batch_num += 1

                if self._batch_completed(session, span_start, batch_fips):
                    continue

                rows = self._fetch_and_parse_batch(
                    batch_fips,
                    span_start,
                    span_end,
                    years,
                    county_lookup,
                    time_ids,
                    source_id,
                    stats,
                )
                for record in rows:
                    session.add(record)
                    row_count += 1

                for fips in batch_fips:
                    self._mark_completed(
                        session,
                        self.SOURCE_CODE,
                        span_start,
                        fips,
                        "laus",
                        row_count=row_count,
                    )

                if batch_num % 20 == 0:
                    session.flush()
                if verbose and batch_num % 50 == 0:
                    pct = batch_num / total_batches * 100
                    print(f"  BLS LAUS: batch {batch_num}/{total_batches} ({pct:.0f}%)")

                time.sleep(REQUEST_DELAY)

        session.flush()
        stats.facts_loaded["fact_bls_unemployment_decomposition"] = row_count
        if verbose:
            print(f"  BLS LAUS: loaded {row_count} rows from {stats.api_calls} API calls")
        return stats

    def _batch_completed(self, session: Session, span_start: int, batch_fips: list[str]) -> bool:
        """Check if all counties in a batch are already checkpointed."""
        return all(
            self._is_completed(session, self.SOURCE_CODE, span_start, fips, "laus")
            for fips in batch_fips
        )

    def _fetch_and_parse_batch(
        self,
        batch_fips: list[str],
        span_start: int,
        span_end: int,
        years: list[int],
        county_lookup: dict[str, int],
        time_ids: dict[int, int],
        source_id: int,
        stats: LoadStats,
    ) -> list[object]:
        """Fetch one API batch and return ORM records."""
        from babylon.data.reference.schema import FactBLSUnemploymentDecomposition

        series_ids: list[str] = []
        for fips in batch_fips:
            for measure in ["04", "05", "06"]:
                series_ids.append(_build_series_id(fips, measure))

        api_data = _fetch_bls_batch(series_ids, span_start, span_end)
        stats.api_calls += 1

        if not api_data:
            return []

        records: list[object] = []
        for fips in batch_fips:
            unemp_key = _build_series_id(fips, "04")
            emp_key = _build_series_id(fips, "05")
            lf_key = _build_series_id(fips, "06")
            county_id = county_lookup[fips]

            for year in range(span_start, span_end + 1):
                if year not in years:
                    continue

                labor_force = _parse_bls_int(api_data.get(lf_key, {}).get(year, "0"))
                employed = _parse_bls_int(api_data.get(emp_key, {}).get(year, "0"))
                unemployed_u3 = _parse_bls_int(api_data.get(unemp_key, {}).get(year, "0"))

                if labor_force <= 0:
                    continue

                records.append(
                    FactBLSUnemploymentDecomposition(
                        county_id=county_id,
                        time_id=time_ids[year],
                        source_id=source_id,
                        labor_force=labor_force,
                        employed=employed,
                        unemployed_u3=unemployed_u3,
                        unemployed_u6=0,
                        part_time_economic=0,
                        discouraged=0,
                        marginally_attached=0,
                    )
                )
        return records

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (none specific to this loader)."""
        return []

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        from babylon.data.reference.schema import FactBLSUnemploymentDecomposition

        return [FactBLSUnemploymentDecomposition]

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,  # noqa: ARG002
    ) -> list[PreflightCheck]:
        """Verify BLS API availability."""
        from babylon.data.preflight import PreflightCheck as PC

        checks: list[PC] = []
        bls_dir = data_dir / "bls" / "laus"
        if not bls_dir.exists():
            checks.append(
                PC(
                    check_id="bls_unemployment:data_dir",
                    status="warn",
                    message=f"BLS LAUS cache directory not found: {bls_dir}",
                    hint="Will fetch from BLS API. Create directory for caching.",
                )
            )
        return checks


def _compute_year_ranges(min_year: int, max_year: int) -> list[tuple[int, int]]:
    """Split a year range into MAX_YEAR_SPAN-sized chunks."""
    ranges: list[tuple[int, int]] = []
    start = min_year
    while start <= max_year:
        end = min(start + MAX_YEAR_SPAN - 1, max_year)
        ranges.append((start, end))
        start = end + 1
    return ranges
