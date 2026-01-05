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
    return LoaderConfig(
        census_year=data.get("census_year", 2022),
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


ALL_LOADERS = ["census", "fred", "energy", "qcew", "trade", "materials"]


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
        config.census_year = census_year
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
        census_year=year,
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
    """Load BLS QCEW employment data into 3NF database."""
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db
    from babylon.data.qcew import QcewLoader

    config = LoaderConfig(
        qcew_years=parse_years(years) or list(range(2015, 2024)),
        verbose=not quiet,
    )

    if not quiet:
        typer.echo(f"Loading QCEW data for years: {config.qcew_years}")

    init_normalized_db()
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet)

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
