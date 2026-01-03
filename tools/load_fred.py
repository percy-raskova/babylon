#!/usr/bin/env python3
"""Load FRED (Federal Reserve Economic Data) into SQLite research database.

Fetches macroeconomic time series from the FRED API and loads them into
data/sqlite/research.sqlite for use in Babylon's FiscalSystem and PrecaritySystem.

Environment:
    FRED_API_KEY: Required. Register at https://fredaccount.stlouisfed.org/apikeys

National Series (8):
    CPIAUCSL  - Consumer Price Index (real wage calculation)
    AHETPI    - Average Hourly Earnings (nominal wage input)
    UNRATE    - Unemployment Rate (reserve army proxy)
    GFDEBTN   - Federal Debt (fiscal trilemma)
    GINIALLRF - Gini Index (class tension initialization)
    M2SL      - M2 Money Supply (fictitious capital proxy)
    PPPTTLUSD - PPP Conversion Factor (unequal exchange)
    RGDPCHUSA625NUPN - PPP GDP/Capita (imperial bribe)

State Unemployment (51):
    LAUST{FIPS}0000000003A for all 50 states + DC

Industry Unemployment (8):
    LNU04 series for Construction, Manufacturing, Transportation,
    Information, Financial, Professional, Education, Leisure sectors

DFA Wealth Distribution (20 series):
    Federal Reserve Distributional Financial Accounts (quarterly, 2015-present)
    WFRBL* - Wealth levels by percentile class (Top 1%, 90-99%, 50-90%, Bottom 50%)
    WFRBS* - Wealth shares by percentile class

Examples:
    # Load all data for 2022 (default)
    poetry run python tools/load_fred.py

    # Load national series only (no state/industry/wealth)
    poetry run python tools/load_fred.py --national-only

    # Load only DFA wealth distribution data
    poetry run python tools/load_fred.py --wealth-only

    # Load wealth data from 2010 instead of default 2015
    poetry run python tools/load_fred.py --start-year 2010

    # Reset and reload everything
    poetry run python tools/load_fred.py --reset

    # Quiet mode (for CI)
    poetry run python tools/load_fred.py -q
"""

import argparse
import sys
import traceback


def main() -> int:
    """Load FRED data into SQLite database."""
    parser = argparse.ArgumentParser(
        description="Load FRED macroeconomic data into SQLite research database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--year",
        type=int,
        default=2022,
        help="Year to load data for (default: 2022)",
    )
    parser.add_argument(
        "--national-only",
        action="store_true",
        help="Load only national series (skip state/industry unemployment)",
    )
    parser.add_argument(
        "--no-states",
        action="store_true",
        help="Skip state-level unemployment data",
    )
    parser.add_argument(
        "--no-industries",
        action="store_true",
        help="Skip industry-level unemployment data",
    )
    parser.add_argument(
        "--no-wealth",
        action="store_true",
        help="Skip DFA wealth distribution data",
    )
    parser.add_argument(
        "--wealth-only",
        action="store_true",
        help="Load only DFA wealth distribution data (skip national/state/industry)",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2015,
        help="Start year for DFA wealth data (default: 2015)",
    )
    parser.add_argument(
        "--series",
        type=str,
        nargs="+",
        help="Specific series IDs to load (e.g., CPIAUCSL UNRATE)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="FRED API key (default: FRED_API_KEY env var)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate FRED tables before loading",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    try:
        # Import here to defer API key check until after arg parsing
        from babylon.data.fred import load_fred_data

        # Determine what to include
        if args.wealth_only:
            # Wealth-only mode: skip everything except DFA wealth data
            include_states = False
            include_industries = False
            include_wealth = True
            series_ids: list[str] | None = []  # Empty = skip national series
        else:
            include_states = not (args.national_only or args.no_states)
            include_industries = not (args.national_only or args.no_industries)
            include_wealth = not (args.national_only or args.no_wealth)
            series_ids = args.series

        stats = load_fred_data(
            series_ids=series_ids,
            year=args.year,
            include_states=include_states,
            include_industries=include_industries,
            include_wealth=include_wealth,
            start_year=args.start_year,
            reset=args.reset,
            verbose=not args.quiet,
            api_key=args.api_key,
        )

        # Print summary if quiet
        if args.quiet:
            total = (
                stats.national_records
                + stats.state_records
                + stats.industry_records
                + stats.wealth_level_records
                + stats.wealth_share_records
            )
            print(f"Loaded {total} FRED records for {args.year}")

        # Exit with error if there were failures
        if stats.errors:
            return 1

        return 0

    except ValueError as e:
        # API key not set
        print(f"Error: {e}", file=sys.stderr)
        print(
            "\nSet FRED_API_KEY environment variable or use --api-key option.",
            file=sys.stderr,
        )
        print("Register at: https://fredaccount.stlouisfed.org/apikeys", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if not args.quiet:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
