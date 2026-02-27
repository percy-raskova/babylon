#!/usr/bin/env python3
"""Download and import LODES Origin-Destination commuter flow data.

Downloads OD files from the LEHD Census server for all 51 states (50 + DC),
then imports county-to-county aggregated flows into the 3NF database.

Data Source:
    https://lehd.ces.census.gov/data/lodes/LODES8/

Usage:
    # Download + import all states, years 2010-2025 (skips missing years)
    poetry run python tools/ingest_lodes_od.py

    # Download only (no import)
    poetry run python tools/ingest_lodes_od.py --download-only

    # Import only (assumes files already downloaded)
    poetry run python tools/ingest_lodes_od.py --import-only

    # Single state
    poetry run python tools/ingest_lodes_od.py --states mi

    # Custom year range
    poetry run python tools/ingest_lodes_od.py --start-year 2015 --end-year 2021

    # Dry run (show what would be downloaded)
    poetry run python tools/ingest_lodes_od.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEHD_BASE_URL = "https://lehd.ces.census.gov/data/lodes/LODES8"
DEFAULT_OD_DIR = Path("data/lodes/od")
DEFAULT_START_YEAR = 2010
DEFAULT_END_YEAR = 2025
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 300  # 5 min for large files

# State FIPS -> abbreviation (50 states + DC)
STATE_ABBREVS: dict[str, str] = {
    "01": "al",
    "02": "ak",
    "04": "az",
    "05": "ar",
    "06": "ca",
    "08": "co",
    "09": "ct",
    "10": "de",
    "11": "dc",
    "12": "fl",
    "13": "ga",
    "15": "hi",
    "16": "id",
    "17": "il",
    "18": "in",
    "19": "ia",
    "20": "ks",
    "21": "ky",
    "22": "la",
    "23": "me",
    "24": "md",
    "25": "ma",
    "26": "mi",
    "27": "mn",
    "28": "ms",
    "29": "mo",
    "30": "mt",
    "31": "ne",
    "32": "nv",
    "33": "nh",
    "34": "nj",
    "35": "nm",
    "36": "ny",
    "37": "nc",
    "38": "nd",
    "39": "oh",
    "40": "ok",
    "41": "or",
    "42": "pa",
    "44": "ri",
    "45": "sc",
    "46": "sd",
    "47": "tn",
    "48": "tx",
    "49": "ut",
    "50": "vt",
    "51": "va",
    "53": "wa",
    "54": "wv",
    "55": "wi",
    "56": "wy",
}


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _build_url(state_abbrev: str, year: int) -> str:
    """Build LEHD download URL for a state/year OD file."""
    filename = f"{state_abbrev}_od_main_JT00_{year}.csv.gz"
    return f"{LEHD_BASE_URL}/{state_abbrev}/od/{filename}"


def _download_file(
    client: httpx.Client,
    url: str,
    dest: Path,
) -> bool:
    """Download a single file with retries. Returns True on success."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with client.stream("GET", url) as response:
                if response.status_code == 404:
                    return False  # File doesn't exist on server
                response.raise_for_status()

                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".tmp")
                total_bytes = 0
                with tmp.open("wb") as f:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        total_bytes += len(chunk)

                tmp.rename(dest)
                size_mb = total_bytes / (1024 * 1024)
                print(f"    downloaded {size_mb:.1f} MB")
                return True

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return False
            print(f"    HTTP {exc.response.status_code} (attempt {attempt}/{MAX_RETRIES})")
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            print(f"    {type(exc).__name__} (attempt {attempt}/{MAX_RETRIES})")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SECONDS * attempt)

    return False


def download_all(
    od_dir: Path,
    states: list[str],
    years: list[int],
    dry_run: bool = False,
) -> dict[str, list[int]]:
    """Download OD files for all requested states and years.

    Returns:
        Dict mapping state_abbrev -> list of years successfully downloaded.
    """
    od_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, list[int]] = {}

    total_combos = len(states) * len(years)
    completed = 0
    downloaded = 0
    skipped_existing = 0
    not_available = 0

    print(f"\n{'=' * 60}")
    print(f"LODES OD Download: {len(states)} states x {len(years)} years = {total_combos} files")
    print(f"Target directory: {od_dir}")
    print(f"{'=' * 60}\n")

    with httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
    ) as client:
        for state_fips in states:
            state_abbrev = STATE_ABBREVS[state_fips]
            state_years: list[int] = []
            print(f"[{state_abbrev.upper()}] ({state_fips})")

            for year in years:
                completed += 1
                filename = f"{state_abbrev}_od_main_JT00_{year}.csv.gz"
                dest = od_dir / filename
                url = _build_url(state_abbrev, year)

                progress = f"  ({completed}/{total_combos})"

                # Skip if already downloaded
                if dest.exists() and dest.stat().st_size > 0:
                    print(
                        f"  {year}: exists ({dest.stat().st_size / 1024 / 1024:.1f} MB) {progress}"
                    )
                    state_years.append(year)
                    skipped_existing += 1
                    continue

                if dry_run:
                    print(f"  {year}: would download {url} {progress}")
                    continue

                print(f"  {year}: downloading... {progress}", end="", flush=True)
                if _download_file(client, url, dest):
                    state_years.append(year)
                    downloaded += 1
                else:
                    print("    not available on server")
                    not_available += 1

                # Brief pause between downloads to be polite to the server
                time.sleep(0.3)

            results[state_abbrev] = state_years
            print()

    print(f"\n{'=' * 60}")
    print("Download Summary:")
    print(f"  New downloads:    {downloaded}")
    print(f"  Already existed:  {skipped_existing}")
    print(f"  Not on server:    {not_available}")
    total_files = sum(len(yrs) for yrs in results.values())
    print(f"  Total files ready: {total_files}")
    print(f"{'=' * 60}\n")

    return results


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def import_to_database(
    od_dir: Path,
    years: list[int],
    states: list[str],
) -> None:
    """Import downloaded OD files into the 3NF database."""
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.lodes.loader_od import LODESODLoader
    from babylon.data.reference.database import get_normalized_session, init_normalized_db

    # Ensure all tables exist (creates missing tables like fact_lodes_commuter_flow)
    init_normalized_db()

    print(f"\n{'=' * 60}")
    print("LODES OD Import to marxist-data-3NF.sqlite")
    print(f"{'=' * 60}\n")

    config = LoaderConfig(
        state_fips_list=states,
        batch_size=10_000,
    )
    loader = LODESODLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(
            session,
            reset=True,
            verbose=True,
            data_dir=od_dir,
            years=years,
            states=states,
        )

    print(f"\n{stats}")
    print()

    if stats.has_errors:
        print("ERRORS:")
        for error in stats.errors:
            print(f"  - {error}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download and import LODES OD commuter flow data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download files but do not import to database",
    )
    parser.add_argument(
        "--import-only",
        action="store_true",
        help="Import already-downloaded files (skip download)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )
    parser.add_argument(
        "--states",
        nargs="+",
        default=None,
        help="State abbreviations to download (e.g., mi oh in). Default: all 51",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=f"First year to download (default: {DEFAULT_START_YEAR})",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=DEFAULT_END_YEAR,
        help=f"Last year to download (default: {DEFAULT_END_YEAR})",
    )
    parser.add_argument(
        "--od-dir",
        type=Path,
        default=DEFAULT_OD_DIR,
        help=f"Directory to store OD files (default: {DEFAULT_OD_DIR})",
    )
    return parser.parse_args(argv)


def _resolve_state_fips(state_inputs: list[str] | None) -> list[str]:
    """Convert state abbreviations or FIPS codes to FIPS codes."""
    if state_inputs is None:
        return sorted(STATE_ABBREVS.keys())

    # Build reverse lookup
    abbrev_to_fips = {v: k for k, v in STATE_ABBREVS.items()}

    fips_list: list[str] = []
    for s in state_inputs:
        s_lower = s.lower().strip()
        if s_lower in abbrev_to_fips:
            fips_list.append(abbrev_to_fips[s_lower])
        elif s_lower in STATE_ABBREVS:
            fips_list.append(s_lower)
        else:
            print(f"WARNING: Unknown state '{s}', skipping")
    return sorted(fips_list)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    args = parse_args(argv)

    years = list(range(args.start_year, args.end_year + 1))
    states = _resolve_state_fips(args.states)

    if not states:
        print("ERROR: No valid states specified")
        return 1

    state_names = [STATE_ABBREVS[f].upper() for f in states]
    print(f"States: {', '.join(state_names)} ({len(states)} total)")
    print(f"Years:  {years[0]}-{years[-1]} ({len(years)} years)")

    # Download phase
    if not args.import_only:
        download_all(
            od_dir=args.od_dir,
            states=states,
            years=years,
            dry_run=args.dry_run,
        )

    if args.dry_run:
        print("Dry run complete. No files downloaded or imported.")
        return 0

    # Import phase
    if not args.download_only:
        import_to_database(
            od_dir=args.od_dir,
            years=years,
            states=states,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
