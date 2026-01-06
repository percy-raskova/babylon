"""CLI entry point for unified data loading.

Provides command-line interface to load data from all sources into the
normalized 3NF database (marxist-data-3NF.sqlite).

Usage:
    # Load all data with default config
    mise run data:load

    # Load specific loaders
    mise run data:census -- --year 2022
    mise run data:fred -- --start-year 1990 --end-year 2024
    mise run data:energy -- --start-year 2000 --end-year 2023

    # Use config file
    mise run data:load -- --config-file config/data-load.yaml

    # Custom year ranges
    mise run data:load -- --census-year 2021 --fred-start 2000 --fred-end 2023

    # Single state for testing
    mise run data:load -- --states 06,36  # CA and NY only
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
import yaml

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats

app = typer.Typer(
    name="data",
    help="Unified data loading for Babylon's 3NF database.",
    no_args_is_help=True,
)


def parse_states(states: str | None) -> list[str] | None:
    """Parse comma-separated state FIPS codes."""
    if states is None:
        return None
    return [s.strip() for s in states.split(",")]


def parse_years(years: str | None) -> list[int] | None:
    """Parse comma-separated years or year ranges."""
    if years is None:
        return None
    result: list[int] = []
    for part in years.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            result.extend(range(int(start), int(end) + 1))
        else:
            result.append(int(part))
    return result


def load_config_from_yaml(config_file: Path) -> LoaderConfig:
    """Load LoaderConfig from a YAML file."""
    with open(config_file) as f:
        data = yaml.safe_load(f)

    # Convert keys to match LoaderConfig field names
    # Support both old (census_year: int) and new (census_years: list) config formats
    census_years = data.get("census_years")
    if census_years is None:
        # Backwards compat: convert old census_year to census_years list
        census_year = data.get("census_year", 2022)
        census_years = [census_year]
    return LoaderConfig(
        census_years=census_years,
        fred_start_year=data.get("fred_start_year", 1990),
        fred_end_year=data.get("fred_end_year", 2024),
        energy_start_year=data.get("energy_start_year", 1990),
        energy_end_year=data.get("energy_end_year", 2024),
        trade_years=data.get("trade_years", list(range(2010, 2025))),
        qcew_years=data.get("qcew_years", list(range(2015, 2024))),
        materials_years=data.get("materials_years", list(range(2015, 2024))),
        state_fips_list=data.get("state_fips_list"),
        include_territories=data.get("include_territories", False),
        batch_size=data.get("batch_size", 10_000),
        request_delay_seconds=data.get("request_delay_seconds", 0.5),
        max_retries=data.get("max_retries", 3),
        verbose=data.get("verbose", True),
    )


def print_stats(stats: LoadStats) -> None:
    """Print load statistics in a formatted way."""
    typer.echo(str(stats))
    if stats.has_errors:
        typer.secho(f"\nErrors ({len(stats.errors)}):", fg=typer.colors.RED)
        for error in stats.errors[:10]:  # Show first 10 errors
            typer.echo(f"  - {error}")
        if len(stats.errors) > 10:
            typer.echo(f"  ... and {len(stats.errors) - 10} more")


ALL_LOADERS = [
    "census",
    "fred",
    "energy",
    "qcew",
    "trade",
    "materials",
    "hifld_prisons",
    "hifld_police",
    "hifld_electric",
    "mirta",
    "fcc",
    "geography",
    "cfs",
]


def _build_config(
    config_file: Path | None,
    census_year: int | None,
    fred_start: int | None,
    fred_end: int | None,
    energy_start: int | None,
    energy_end: int | None,
    states: str | None,
    quiet: bool,
) -> LoaderConfig:
    """Build LoaderConfig from file and CLI overrides."""
    config = load_config_from_yaml(config_file) if config_file else LoaderConfig()

    if census_year is not None:
        config.census_years = [census_year]
    if fred_start is not None:
        config.fred_start_year = fred_start
    if fred_end is not None:
        config.fred_end_year = fred_end
    if energy_start is not None:
        config.energy_start_year = energy_start
    if energy_end is not None:
        config.energy_end_year = energy_end
    if states is not None:
        config.state_fips_list = parse_states(states)
    config.verbose = not quiet
    return config


def _validate_loaders(loaders: str | None) -> list[str]:
    """Validate and return list of loaders to run."""
    if not loaders:
        return ALL_LOADERS

    selected = [s.strip().lower() for s in loaders.split(",")]
    for name in selected:
        if name not in ALL_LOADERS:
            typer.secho(f"Unknown loader: {name}", fg=typer.colors.RED)
            typer.echo(f"Available: {', '.join(ALL_LOADERS)}")
            raise typer.Exit(1)
    return selected


@app.command()
def load(
    config_file: Annotated[
        Path | None,
        typer.Option("--config-file", "-c", help="Path to YAML config file"),
    ] = None,
    census_year: Annotated[
        int | None, typer.Option("--census-year", help="Census ACS 5-year vintage")
    ] = None,
    fred_start: Annotated[int | None, typer.Option("--fred-start", help="FRED start year")] = None,
    fred_end: Annotated[int | None, typer.Option("--fred-end", help="FRED end year")] = None,
    energy_start: Annotated[
        int | None, typer.Option("--energy-start", help="Energy start year")
    ] = None,
    energy_end: Annotated[int | None, typer.Option("--energy-end", help="Energy end year")] = None,
    states: Annotated[
        str | None, typer.Option("--states", help="State FIPS codes (e.g., 06,36)")
    ] = None,
    reset: Annotated[
        bool, typer.Option("--reset/--no-reset", help="Clear tables before loading")
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    loaders: Annotated[
        str | None,
        typer.Option("--loaders", help="Loader names (census,fred,energy,qcew,trade,materials)"),
    ] = None,
) -> None:
    """Load all data sources into the 3NF database."""
    from babylon.data.normalize.database import (
        get_normalized_engine,
        init_normalized_db,
    )
    from babylon.data.normalize.views import create_views

    config = _build_config(
        config_file, census_year, fred_start, fred_end, energy_start, energy_end, states, quiet
    )
    selected = _validate_loaders(loaders)

    if not quiet:
        typer.echo("Initializing 3NF database...")
    init_normalized_db()

    total_stats, has_errors = _run_all_loaders(selected, config, reset, quiet)

    if not quiet:
        typer.echo("\nCreating analytical views...")
    view_count = create_views(get_normalized_engine())
    if not quiet:
        _print_summary(total_stats, view_count)

    if has_errors:
        raise typer.Exit(1)


def _run_all_loaders(
    selected: list[str], config: LoaderConfig, reset: bool, quiet: bool
) -> tuple[list[LoadStats], bool]:
    """Run all selected loaders and return stats."""
    from babylon.data.normalize.database import get_normalized_session

    total_stats: list[LoadStats] = []
    has_errors = False

    with get_normalized_session() as session:
        for name in selected:
            if not quiet:
                typer.echo(f"\n{'=' * 60}")
                typer.secho(f"Loading: {name.upper()}", fg=typer.colors.CYAN, bold=True)
                typer.echo("=" * 60)

            try:
                stats = _run_loader(name, session, config, reset, not quiet)
                total_stats.append(stats)
                if stats.has_errors:
                    has_errors = True
                if not quiet:
                    print_stats(stats)
            except Exception as e:
                typer.secho(f"Error loading {name}: {e}", fg=typer.colors.RED)
                has_errors = True

    return total_stats, has_errors


def _print_summary(total_stats: list[LoadStats], view_count: int) -> None:
    """Print final summary."""
    typer.echo("\n" + "=" * 60)
    typer.secho("SUMMARY", fg=typer.colors.GREEN, bold=True)
    typer.echo("=" * 60)
    total_dims = sum(s.total_dimensions for s in total_stats)
    total_facts = sum(s.total_facts for s in total_stats)
    typer.echo(f"Total dimensions: {total_dims:,}")
    typer.echo(f"Total facts: {total_facts:,}")
    typer.echo(f"Views created: {view_count}")


def _run_loader(
    name: str,
    session: object,
    config: LoaderConfig,
    reset: bool,
    verbose: bool,
) -> LoadStats:
    """Run a specific loader by name."""
    # Import loaders lazily to avoid circular imports
    loader: DataLoader
    if name == "census":
        from babylon.data.census import CensusLoader

        loader = CensusLoader(config)
    elif name == "fred":
        from babylon.data.fred import FredLoader

        loader = FredLoader(config)
    elif name == "energy":
        from babylon.data.energy import EnergyLoader

        loader = EnergyLoader(config)
    elif name == "qcew":
        from babylon.data.qcew import QcewLoader

        loader = QcewLoader(config)
    elif name == "trade":
        from babylon.data.trade import TradeLoader

        loader = TradeLoader(config)
    elif name == "materials":
        from babylon.data.materials import MaterialsLoader

        loader = MaterialsLoader(config)
    elif name == "hifld_prisons":
        from babylon.data.hifld import HIFLDPrisonsLoader

        loader = HIFLDPrisonsLoader(config)
    elif name == "hifld_police":
        from babylon.data.hifld import HIFLDPoliceLoader

        loader = HIFLDPoliceLoader(config)
    elif name == "hifld_electric":
        from babylon.data.hifld import HIFLDElectricLoader

        loader = HIFLDElectricLoader(config)
    elif name == "mirta":
        from babylon.data.mirta import MIRTAMilitaryLoader

        loader = MIRTAMilitaryLoader(config)
    elif name == "geography":
        from babylon.data.geography import GeographicHierarchyLoader

        loader = GeographicHierarchyLoader(config)
    elif name == "cfs":
        from babylon.data.cfs import CFSLoader

        loader = CFSLoader(config)
    elif name == "fcc":
        from babylon.data.fcc import FCCBroadbandLoader

        loader = FCCBroadbandLoader(config)
    else:
        raise ValueError(f"Unknown loader: {name}")

    return loader.load(session, reset=reset, verbose=verbose)  # type: ignore[arg-type]


@app.command()
def census(
    year: Annotated[
        int,
        typer.Option("--year", "-y", help="Census ACS 5-year vintage"),
    ] = 2022,
    states: Annotated[
        str | None,
        typer.Option("--states", help="Comma-separated state FIPS codes"),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load Census ACS data into 3NF database."""
    from babylon.data.census import CensusLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(
        census_years=[year],
        state_fips_list=parse_states(states),
        verbose=not quiet,
    )

    if not quiet:
        typer.echo(f"Loading Census ACS {year} 5-year estimates...")
        if states:
            typer.echo(f"States: {states}")

    init_normalized_db()
    loader = CensusLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def fred(
    start_year: Annotated[
        int,
        typer.Option("--start-year", help="Start year for time series"),
    ] = 1990,
    end_year: Annotated[
        int,
        typer.Option("--end-year", help="End year for time series"),
    ] = 2024,
    states: Annotated[
        str | None,
        typer.Option("--states", help="Comma-separated state FIPS codes"),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load FRED macroeconomic data into 3NF database."""
    from babylon.data.fred import FredLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(
        fred_start_year=start_year,
        fred_end_year=end_year,
        state_fips_list=parse_states(states),
        verbose=not quiet,
    )

    if not quiet:
        typer.echo(f"Loading FRED data {start_year}-{end_year}...")

    init_normalized_db()
    loader = FredLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def energy(
    start_year: Annotated[
        int,
        typer.Option("--start-year", help="Start year for energy data"),
    ] = 1990,
    end_year: Annotated[
        int,
        typer.Option("--end-year", help="End year for energy data"),
    ] = 2024,
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load EIA energy data into 3NF database."""
    from babylon.data.energy import EnergyLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(
        energy_start_year=start_year,
        energy_end_year=end_year,
        verbose=not quiet,
    )

    if not quiet:
        typer.echo(f"Loading EIA energy data {start_year}-{end_year}...")

    init_normalized_db()
    loader = EnergyLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def qcew(
    years: Annotated[
        str | None,
        typer.Option("--years", help="Years to load (e.g., 2020,2021,2022 or 2013-2025)"),
    ] = None,
    force_api: Annotated[
        bool,
        typer.Option("--force-api", help="Use API for all years (may fail for old years)"),
    ] = False,
    force_files: Annotated[
        bool,
        typer.Option("--force-files", help="Use files for all years (requires CSV downloads)"),
    ] = False,
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load BLS QCEW employment data into 3NF database.

    Uses hybrid loading strategy:
    - API for recent years (2021+): Fetches from BLS QCEW Open Data API
    - Files for historical years (2013-2020): Reads from data/qcew/ CSV files

    Supports three geographic levels:
    - County (fact_qcew_annual)
    - State (fact_qcew_state_annual)
    - Metro/Micropolitan/CSA (fact_qcew_metro_annual)

    Examples:
        mise run data:qcew                           # Default years with hybrid loading
        mise run data:qcew -- --years 2021-2025      # Recent years via API
        mise run data:qcew -- --years 2015-2020 --force-files  # Historical via files
        mise run data:qcew -- --force-api            # Force API for all years
    """
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db
    from babylon.data.qcew import QcewLoader

    # Default years: 2013-2025 (hybrid: 2013-2020 files, 2021-2025 API)
    config = LoaderConfig(
        qcew_years=parse_years(years) or list(range(2013, 2026)),
        verbose=not quiet,
    )

    if not quiet:
        typer.echo(f"Loading QCEW data for years: {config.qcew_years}")
        if force_api:
            typer.echo("Mode: Force API for all years")
        elif force_files:
            typer.echo("Mode: Force files for all years")
        else:
            typer.echo("Mode: Hybrid (API for 2021+, files for 2013-2020)")

    init_normalized_db()
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(
            session,
            reset=reset,
            verbose=not quiet,
            force_api=force_api,
            force_files=force_files,
        )

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def trade(
    years: Annotated[
        str | None,
        typer.Option("--years", help="Years to load (e.g., 2020,2021,2022 or 2020-2023)"),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load UN trade data into 3NF database."""
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db
    from babylon.data.trade import TradeLoader

    config = LoaderConfig(
        trade_years=parse_years(years) or list(range(2010, 2025)),
        verbose=not quiet,
    )

    if not quiet:
        typer.echo(f"Loading trade data for years: {config.trade_years}")

    init_normalized_db()
    loader = TradeLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def materials(
    years: Annotated[
        str | None,
        typer.Option("--years", help="Years to load (e.g., 2020,2021,2022 or 2020-2023)"),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load USGS materials data into 3NF database."""
    from babylon.data.materials import MaterialsLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(
        materials_years=parse_years(years) or list(range(2015, 2024)),
        verbose=not quiet,
    )

    if not quiet:
        typer.echo(f"Loading materials data for years: {config.materials_years}")

    init_normalized_db()
    loader = MaterialsLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def hifld_prisons(
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load HIFLD Prison Boundaries into 3NF database.

    Loads ~7,000 prison/correctional facilities from HIFLD ArcGIS Feature Service
    and aggregates to county-level coercive infrastructure metrics.
    """
    from babylon.data.hifld import HIFLDPrisonsLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(verbose=not quiet)

    if not quiet:
        typer.echo("Loading HIFLD Prison Boundaries from ArcGIS...")

    init_normalized_db()
    loader = HIFLDPrisonsLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def hifld_police(
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load HIFLD Local Law Enforcement Locations into 3NF database.

    Loads ~18,000 police stations/law enforcement facilities from HIFLD ArcGIS
    Feature Service and aggregates to county-level coercive infrastructure metrics.
    """
    from babylon.data.hifld import HIFLDPoliceLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(verbose=not quiet)

    if not quiet:
        typer.echo("Loading HIFLD Local Law Enforcement Locations from ArcGIS...")

    init_normalized_db()
    loader = HIFLDPoliceLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def hifld_electric(
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load HIFLD Electric Substations into 3NF database.

    Loads electric substation data from HIFLD ArcGIS Feature Service
    and aggregates to county-level electric grid metrics.
    """
    from babylon.data.hifld import HIFLDElectricLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(verbose=not quiet)

    if not quiet:
        typer.echo("Loading HIFLD Electric Substations from ArcGIS...")

    init_normalized_db()
    loader = HIFLDElectricLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def mirta(
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Load MIRTA Military Installations into 3NF database.

    Loads military installation data from DoD MIRTA ArcGIS Feature Service
    and aggregates to county-level coercive infrastructure metrics.
    """
    from babylon.data.mirta import MIRTAMilitaryLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(verbose=not quiet)

    if not quiet:
        typer.echo("Loading MIRTA Military Installations from ArcGIS...")

    init_normalized_db()
    loader = MIRTAMilitaryLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def fcc(
    reset: Annotated[
        bool,
        typer.Option("--reset/--no-reset", help="Clear tables before loading"),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
    as_of_date: Annotated[
        str | None,
        typer.Option("--as-of-date", "-d", help="FCC data date (e.g., 2025-06-30)"),
    ] = None,
) -> None:
    """Load FCC Broadband Coverage data into 3NF database.

    Loads FCC BDC (Broadband Data Collection) county-level broadband
    coverage metrics from pre-downloaded CSV files.

    Requires data to be downloaded first via fcc-download command:
        mise run data:fcc-download --national
    """
    from babylon.data.fcc import FCCBroadbandLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(verbose=not quiet)

    if not quiet:
        typer.echo("Loading FCC Broadband Coverage from downloaded CSVs...")

    init_normalized_db()
    loader = FCCBroadbandLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet, as_of_date=as_of_date)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


def _parse_state_fips_list(state_fips: str) -> list[str]:
    """Parse state FIPS input into list of 2-digit codes.

    Supports:
    - Single state: "06"
    - Comma-separated: "06,36,48"
    - Range: "01-10"
    - Mixed: "01-05,06,10-15"

    Returns:
        List of 2-digit zero-padded FIPS codes.
    """
    states: list[str] = []
    for part in state_fips.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            for i in range(int(start), int(end) + 1):
                states.append(f"{i:02d}")
        else:
            states.append(part.zfill(2))
    return sorted(set(states))


def _fcc_download_files(
    national: bool,
    hexagon: bool,
    state_fips: str,
    output_dir: Path,
    as_of_date: str | None,
    technology_type: str,
) -> list[Path]:
    """Execute FCC download based on mode."""
    from babylon.data.fcc import (
        download_national_summaries,
        download_state_hexagons,
        download_state_summaries,
    )

    if national:
        return download_national_summaries(output_dir=output_dir, as_of_date=as_of_date)
    if hexagon:
        return download_state_hexagons(
            state_fips=state_fips,
            output_dir=output_dir,
            as_of_date=as_of_date,
            technology_type=technology_type,
        )
    return download_state_summaries(
        state_fips=state_fips,
        output_dir=output_dir,
        as_of_date=as_of_date,
    )


@app.command()
def fcc_download(
    state_fips: Annotated[
        str | None,
        typer.Option(
            "--state-fips",
            "-s",
            help="State FIPS: single (06), comma-separated (06,36), or range (01-56)",
        ),
    ] = None,
    as_of_date: Annotated[
        str | None,
        typer.Option(
            "--as-of-date",
            "-d",
            help="Data vintage date (YYYY-MM-DD). Uses latest if not specified.",
        ),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Output directory for downloaded files"),
    ] = Path("data/fcc/downloads"),
    hexagon: Annotated[
        bool,
        typer.Option(
            "--hexagon", help="Download H3 hexagon coverage data (GIS) instead of summary (CSV)"
        ),
    ] = False,
    national: Annotated[
        bool,
        typer.Option(
            "--national", "-n", help="Download national summary (includes county-level data)"
        ),
    ] = False,
    technology: Annotated[
        str,
        typer.Option(
            "--technology", "-t", help="Technology type: 'fixed' or 'mobile' (for hexagon mode)"
        ),
    ] = "fixed",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress verbose output"),
    ] = False,
) -> None:
    """Download FCC BDC broadband availability data.

    Downloads broadband data from the FCC BDC API.
    - Default: State summary by Census Place (CSV)
    - --national: National summary with county-level data (CSV)
    - --hexagon: State H3 hexagon coverage data (GIS)

    Requires FCC_USERNAME and FCC_API_KEY environment variables.

    Examples:
        mise run data:fcc-download -- --national                   # County-level national data
        mise run data:fcc-download -- --state-fips 06              # CA Census Place summary
        mise run data:fcc-download -- -s 01-56                     # All 50 states + DC + territories
        mise run data:fcc-download -- -s 06,36,48 --hexagon        # CA, NY, TX hexagon data
    """
    if national and hexagon:
        typer.secho("Cannot use --national with --hexagon", fg=typer.colors.RED)
        raise typer.Exit(1)

    tech_map = {"fixed": "Fixed Broadband", "mobile": "Mobile Broadband"}
    technology_type = tech_map.get(technology.lower(), technology)

    # Handle national mode (no state iteration)
    if national:
        if not quiet:
            typer.echo("Downloading FCC BDC national summary data...")
            typer.echo(f"As-of date: {as_of_date or 'latest'}")
            typer.echo(f"Output directory: {output_dir}")
        try:
            extracted = _fcc_download_files(
                national, hexagon, "", output_dir, as_of_date, technology_type
            )
            if not quiet:
                _print_extracted_files(extracted)
        except ValueError as e:
            typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
            raise typer.Exit(1) from e
        return

    # Parse state list (supports ranges like 01-56)
    state_input = state_fips if state_fips else "06"
    states = _parse_state_fips_list(state_input)

    if not quiet:
        data_type = "hexagon (H3)" if hexagon else "summary (Census Place)"
        typer.echo(f"Downloading FCC BDC {data_type} data for {len(states)} state(s)...")
        if hexagon:
            typer.echo(f"Technology: {technology_type}")
        typer.echo(f"As-of date: {as_of_date or 'latest'}")
        typer.echo(f"Output directory: {output_dir}")

    all_extracted: list[Path] = []
    for state in states:
        if not quiet:
            typer.echo(f"\n[{state}] Downloading...")
        try:
            extracted = _fcc_download_files(
                national, hexagon, state, output_dir, as_of_date, technology_type
            )
            all_extracted.extend(extracted)
            if not quiet:
                typer.echo(f"[{state}] Downloaded {len(extracted)} files")
        except ValueError as e:
            typer.secho(f"[{state}] Error: {e}", fg=typer.colors.RED)

    if not quiet:
        typer.secho(f"\nTotal: {len(all_extracted)} files downloaded", fg=typer.colors.GREEN)


def _print_fcc_download_info(
    national: bool, hexagon: bool, state: str, tech: str, date: str | None, output: Path
) -> None:
    """Print FCC download information."""
    data_type = (
        "national summary"
        if national
        else ("hexagon (H3)" if hexagon else "summary (Census Place)")
    )
    scope = "" if national else f" for state {state}"
    typer.echo(f"Downloading FCC BDC {data_type} data{scope}...")
    if hexagon:
        typer.echo(f"Technology: {tech}")
    typer.echo(f"As-of date: {date or 'latest'}")
    typer.echo(f"Output directory: {output}")


def _print_extracted_files(files: list[Path]) -> None:
    """Print extracted files summary."""
    typer.secho(f"\nDownloaded and extracted {len(files)} files:", fg=typer.colors.GREEN)
    for f in files[:10]:
        typer.echo(f"  - {f}")
    if len(files) > 10:
        typer.echo(f"  ... and {len(files) - 10} more")


def main() -> int:
    """Main entry point for CLI."""
    try:
        app()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
