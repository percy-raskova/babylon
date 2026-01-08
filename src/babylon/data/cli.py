"""CLI entry point for unified data loading.

Provides command-line interface to load data from all sources into the
normalized 3NF database (marxist-data-3NF.duckdb).

Usage:
    # Load all data with default config
    mise run data:load

    # Load specific loaders
    mise run data:census -- --year 2021
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

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
import yaml
from sqlalchemy import text

from babylon.data.exceptions import SchemaCheckError
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats

if TYPE_CHECKING:
    from collections.abc import Sequence

    from babylon.data.normalize.schema_check import SchemaRepairAction, SchemaRepairReport
    from babylon.data.preflight import PreflightResult

app = typer.Typer(
    name="data",
    help="Unified data loading for Babylon's 3NF database.",
    no_args_is_help=True,
)

logger = logging.getLogger(__name__)
_LOGGING_CONFIGURED = False


def _configure_cli_logging() -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    from babylon.config.logging_config import setup_logging

    config_path = Path("logging.yaml")
    setup_logging(
        config_path=config_path if config_path.exists() else None,
    )
    _LOGGING_CONFIGURED = True


@app.callback()
def _init_logging() -> None:
    _configure_cli_logging()


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
        census_year = data.get("census_year", 2021)
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
    if stats.api_errors:
        typer.secho(f"\nAPI Errors ({len(stats.api_errors)}):", fg=typer.colors.RED)
        for api_error in stats.api_errors[:10]:
            parts: list[str] = []
            if api_error.error_code:
                parts.append(api_error.error_code)
            if api_error.status_code is not None:
                parts.append(f"status={api_error.status_code}")
            if api_error.context:
                parts.append(f"context={api_error.context}")
            if api_error.url:
                parts.append(f"url={api_error.url}")
            detail_msg = " | ".join(parts)
            if detail_msg:
                detail_msg = f" ({detail_msg})"
            typer.echo(f"  - {api_error.message}{detail_msg}")
            if api_error.details and api_error.details.get("params"):
                typer.echo(f"    params={api_error.details['params']}")
    if stats.has_errors:
        typer.secho(f"\nErrors ({len(stats.errors)}):", fg=typer.colors.RED)
        for error in stats.errors[:10]:  # Show first 10 errors
            typer.echo(f"  - {error}")
        if len(stats.errors) > 10:
            typer.echo(f"  ... and {len(stats.errors) - 10} more")


def _print_preflight(result: object) -> None:
    """Print preflight results."""
    from babylon.data.preflight import PreflightResult

    if not isinstance(result, PreflightResult):
        typer.echo("Invalid preflight result.")
        return

    status_colors = {
        "ok": typer.colors.GREEN,
        "warn": typer.colors.YELLOW,
        "fail": typer.colors.RED,
    }

    typer.echo("\nPreflight checks:")
    for check in result.checks:
        color = status_colors.get(check.status, typer.colors.WHITE)
        typer.secho(f"[{check.status.upper()}] {check.message}", fg=color)
        if check.hint:
            typer.echo(f"  Hint: {check.hint}")

    typer.echo(
        f"\nSummary: {len(result.checks)} checks, "
        f"{len(result.warnings)} warnings, {len(result.failures)} failures"
    )


@dataclass
class IngestReadinessResult:
    """Aggregated readiness results for ingestion."""

    preflight: PreflightResult
    schema_report: SchemaRepairReport | None = None
    schema_error: SchemaCheckError | None = None
    prereq_errors: dict[str, list[str]] = field(default_factory=dict)
    strict: bool = False

    @property
    def ok(self) -> bool:
        if self.preflight.failures:
            return False
        if self.strict and self.preflight.warnings:
            return False
        if self.schema_error is not None:
            return False
        if self.schema_report:
            if self.schema_report.failed:
                return False
            if self.schema_report.remaining_diffs:
                return False
        return not self.prereq_errors


def _run_schema_readiness(repair: bool) -> SchemaRepairReport:
    """Return schema readiness report with optional repairs."""
    try:
        from babylon.data.normalize import schema_check
    except ModuleNotFoundError as exc:
        if exc.name != "alembic":
            raise
        raise SchemaCheckError(
            "Alembic is required for schema drift checks.",
            hint="Install dev dependencies or add alembic to the main group.",
        ) from exc

    try:
        return schema_check.get_schema_repair_report(repair=repair)
    except SchemaCheckError:
        raise
    except ModuleNotFoundError as exc:
        if exc.name in {"duckdb", "duckdb_engine"}:
            raise SchemaCheckError(
                "DuckDB engine not available. Install `duckdb` and `duckdb-engine` "
                "(e.g., `poetry install`) before running schema checks.",
            ) from exc
        raise
    except Exception as exc:
        _no_such_module_exc: type[Exception] | None = None
        try:
            from sqlalchemy.exc import NoSuchModuleError

            _no_such_module_exc = NoSuchModuleError
        except ModuleNotFoundError:
            pass
        if (
            _no_such_module_exc is not None
            and isinstance(exc, _no_such_module_exc)
            and "duckdb" in str(exc)
        ):
            raise SchemaCheckError(
                "DuckDB SQLAlchemy dialect not found. Install `duckdb-engine` "
                "(e.g., `poetry install`) before running schema checks.",
            ) from exc
        raise SchemaCheckError(
            f"Schema check failed: {exc}",
            hint="Review the stack trace and verify database connectivity.",
        ) from exc


def _run_ingest_readiness(
    config: LoaderConfig,
    selected: list[str],
    online: bool,
    strict: bool,
    repair: bool,
) -> IngestReadinessResult:
    """Run preflight + schema readiness + prerequisite checks."""
    from babylon.data.preflight import run_preflight

    preflight = run_preflight(config, selected, online=online)
    schema_report: SchemaRepairReport | None = None
    schema_error: SchemaCheckError | None = None
    try:
        schema_report = _run_schema_readiness(repair=repair)
    except SchemaCheckError as exc:
        schema_error = exc
        schema_error.log(logger, level=logging.ERROR, exc_info=True)

    if schema_report and (schema_report.has_changes or schema_report.remaining_diffs):
        level = logging.WARNING
        if schema_report.failed or schema_report.remaining_diffs:
            level = logging.ERROR
        logger.log(
            level, "Schema readiness report", extra={"schema_repairs": schema_report.to_dict()}
        )

    prereq_errors: dict[str, list[str]] = {}
    if schema_error is None and schema_report and not schema_report.remaining_diffs:
        prereq_errors = _collect_prereq_errors(selected, config)

    return IngestReadinessResult(
        preflight=preflight,
        schema_report=schema_report,
        schema_error=schema_error,
        prereq_errors=prereq_errors,
        strict=strict,
    )


def _print_schema_action_summary(
    label: str,
    actions: Sequence[SchemaRepairAction],
    color: str,
) -> None:
    """Print a summarized list of schema repair actions."""
    if not actions:
        return
    typer.secho(label, fg=color)
    for action in actions[:10]:
        typer.echo(f"  - {action.short_label()}")
    if len(actions) > 10:
        typer.echo(f"  ... and {len(actions) - 10} more")


def _print_schema_readiness(result: IngestReadinessResult) -> None:
    """Print schema readiness and repair results."""
    if result.schema_error:
        typer.secho(str(result.schema_error), fg=typer.colors.RED)
        if result.schema_error.hint:
            typer.echo(f"Hint: {result.schema_error.hint}")
        diffs = result.schema_error.details.get("diffs")
        if diffs:
            typer.echo(f"Diffs:\n{diffs}")
        return

    report = result.schema_report
    if report is None:
        typer.secho("Schema readiness unavailable.", fg=typer.colors.RED)
        return

    if not report.has_changes and not report.remaining_diffs:
        typer.secho("[OK] Schema matches SQLAlchemy models.", fg=typer.colors.GREEN)
        return

    _print_schema_action_summary(
        f"[WARN] Applied {len(report.applied)} schema repair(s).",
        report.applied,
        typer.colors.YELLOW,
    )
    _print_schema_action_summary(
        f"[FAIL] {len(report.failed)} schema repair(s) failed.",
        report.failed,
        typer.colors.RED,
    )
    _print_schema_action_summary(
        f"[WARN] {len(report.skipped)} non-additive diff(s) skipped.",
        report.skipped,
        typer.colors.YELLOW,
    )

    if report.remaining_diffs:
        from babylon.data.normalize.schema_check import format_schema_diffs

        typer.secho("[FAIL] Schema drift remains after repairs.", fg=typer.colors.RED)
        typer.echo(f"Diffs:\n{format_schema_diffs(report.remaining_diffs)}")


def _collect_prereq_errors(
    selected: list[str],
    config: LoaderConfig,
) -> dict[str, list[str]]:
    """Collect prerequisite errors for loaders missing dependencies."""
    from babylon.data.normalize.database import get_normalized_session

    errors: dict[str, list[str]] = {}
    selected_set = set(selected)
    needs_session = any(
        dep not in selected_set for name in selected for dep in LOADER_DEPENDENCIES.get(name, [])
    )
    if not needs_session:
        return errors

    with get_normalized_session() as session:
        for name in selected:
            missing_deps = [
                dep for dep in LOADER_DEPENDENCIES.get(name, []) if dep not in selected_set
            ]
            if not missing_deps:
                continue
            prereq_errors = _check_loader_prereqs(name, session, config)
            if prereq_errors:
                errors[name] = prereq_errors
    return errors


def _print_prereq_summary(errors: dict[str, list[str]]) -> None:
    if not errors:
        return
    for name, loader_errors in errors.items():
        _print_prereq_errors(name, loader_errors)


def _run_schema_check(quiet: bool) -> None:
    """Validate normalized schema against SQLAlchemy models."""
    try:
        from babylon.data.exceptions import SchemaCheckError
        from babylon.data.normalize.schema_check import check_normalized_schema
    except ModuleNotFoundError as exc:
        if exc.name != "alembic":
            raise
        typer.secho(
            "Alembic is required for schema drift checks. "
            "Install dev dependencies or add alembic to the main group.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1) from exc

    try:
        message = check_normalized_schema()
    except SchemaCheckError as exc:
        exc.log(logger, level=logging.ERROR, exc_info=True)
        typer.secho(str(exc), fg=typer.colors.RED)
        if exc.hint:
            typer.echo(f"Hint: {exc.hint}")
        if exc.details.get("diffs"):
            typer.echo(f"Diffs:\n{exc.details['diffs']}")
        raise typer.Exit(1) from exc
    except ModuleNotFoundError as exc:
        if exc.name in {"duckdb", "duckdb_engine"}:
            typer.secho(
                "DuckDB engine not available. Install `duckdb` and `duckdb-engine` "
                "(e.g., `poetry install`) before running schema checks.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1) from exc
        raise
    except Exception as exc:
        _no_such_module_exc: type[Exception] | None = None
        try:
            from sqlalchemy.exc import NoSuchModuleError

            _no_such_module_exc = NoSuchModuleError
        except ModuleNotFoundError:
            pass
        if (
            _no_such_module_exc is not None
            and isinstance(exc, _no_such_module_exc)
            and "duckdb" in str(exc)
        ):
            typer.secho(
                "DuckDB SQLAlchemy dialect not found. Install `duckdb-engine` "
                "(e.g., `poetry install`) before running schema checks.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1) from exc
        logger.exception("Schema check failed unexpectedly.")
        typer.secho(f"Schema check failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    if not quiet:
        typer.echo(message)


def _execute_readiness(
    config: LoaderConfig,
    selected: list[str],
    online: bool,
    strict: bool,
    repair: bool,
    quiet: bool,
) -> None:
    result = _run_ingest_readiness(config, selected, online, strict, repair)
    if not quiet:
        _print_preflight(result.preflight)
        typer.echo("\nSchema readiness:")
        _print_schema_readiness(result)
        _print_prereq_summary(result.prereq_errors)
    if not result.ok:
        raise typer.Exit(1)


ALL_LOADERS = [
    "census",
    "fred",
    "energy",
    "qcew",
    "trade",
    "materials",
    "employment_industry",
    "dot_hpms",
    "lodes",
    "hifld_prisons",
    "hifld_police",
    "hifld_electric",
    "mirta",
    "fcc",
    "geography",
    "cfs",
]

LOADER_DEPENDENCIES: dict[str, list[str]] = {
    "qcew": ["census"],
    "employment_industry": ["census"],
    "dot_hpms": ["census"],
    "lodes": ["census"],
    "fcc": ["census"],
    "hifld_prisons": ["census"],
    "hifld_police": ["census"],
    "hifld_electric": ["census"],
    "mirta": ["census"],
    "geography": ["census", "qcew"],
    "cfs": ["geography"],
}


def _resolve_loader_order(selected: list[str]) -> list[str]:
    """Return selected loaders ordered by declared dependencies."""
    selected_set = set(selected)
    deps: dict[str, list[str]] = {
        name: [dep for dep in LOADER_DEPENDENCIES.get(name, []) if dep in selected_set]
        for name in selected
    }
    in_degree = dict.fromkeys(selected, 0)
    forward: dict[str, list[str]] = {name: [] for name in selected}

    for name, requirements in deps.items():
        for requirement in requirements:
            in_degree[name] += 1
            forward[requirement].append(name)

    ordered: list[str] = []
    queue = [name for name in ALL_LOADERS if name in selected_set and in_degree[name] == 0]

    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for dependent in forward.get(current, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(ordered) != len(selected):
        # Fallback to original order if cycles or missing nodes appear.
        return selected

    return ordered


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


def _has_rows(session: Any, model: Any) -> bool:
    """Return True if the table has at least one row."""
    from sqlalchemy import select

    return session.execute(select(model).limit(1)).first() is not None


def _has_rows_for_year(session: Any, model: Any, year: int, field_name: str) -> bool:
    """Return True if the table has at least one row for a given year."""
    from sqlalchemy import select

    field = getattr(model, field_name)
    return session.execute(select(model).where(field == year).limit(1)).first() is not None


def _get_cfs_year(config: LoaderConfig) -> int:
    """Return the survey year used by the CFS loader."""
    if config.census_years:
        valid_years = [y for y in config.census_years if y in {2012, 2017, 2022}]
        if valid_years:
            return max(valid_years)
    return 2022


def _missing_dimension_rows(session: Any, required: dict[str, Any]) -> list[str]:
    """Return missing dimension names for the requested models."""
    missing: list[str] = []
    for label, model in required.items():
        if not _has_rows(session, model):
            missing.append(label)
    return missing


def _check_prereqs_census_dims(
    session: object,
    name: str,
    _config: LoaderConfig,
) -> list[str]:
    """Return census dimension prerequisite errors."""
    from babylon.data.normalize.schema import (
        DimCounty,
        DimState,
    )

    missing = _missing_dimension_rows(session, {"DimState": DimState, "DimCounty": DimCounty})
    if not missing:
        return []

    return [
        (
            f"{name} requires Census dimensions ({', '.join(missing)}). "
            f"Run `mise run data:census` or include `--loaders=census,{name}`."
        )
    ]


def _check_prereqs_county_only(
    session: object,
    name: str,
    _config: LoaderConfig,
) -> list[str]:
    """Return county-only prerequisite errors."""
    from babylon.data.normalize.schema import DimCounty

    if _has_rows(session, DimCounty):
        return []
    return [
        (
            f"{name} requires county FIPS in DimCounty. "
            f"Run `mise run data:census` or include `--loaders=census,{name}`."
        )
    ]


def _check_prereqs_geography(
    session: object,
    _name: str,
    _config: LoaderConfig,
) -> list[str]:
    """Return prerequisite errors for geography loader."""
    from babylon.data.normalize.schema import DimCounty, FactCensusEmployment, FactQcewAnnual

    missing_parts = []
    if not _has_rows(session, DimCounty):
        missing_parts.append("DimCounty")
    if not _has_rows(session, FactCensusEmployment):
        missing_parts.append("FactCensusEmployment")
    if not _has_rows(session, FactQcewAnnual):
        missing_parts.append("FactQcewAnnual")
    if not missing_parts:
        return []
    return [
        (
            "geography requires Census employment and QCEW annual employment. "
            "Run `mise run data:census` and `mise run data:qcew` first. "
            f"Missing: {', '.join(missing_parts)}."
        )
    ]


def _check_prereqs_cfs(
    session: object,
    _name: str,
    config: LoaderConfig,
) -> list[str]:
    """Return prerequisite errors for cfs loader."""
    from babylon.data.normalize.schema import DimGeographicHierarchy

    year = _get_cfs_year(config)
    if _has_rows_for_year(session, DimGeographicHierarchy, year, "source_year"):
        return []
    return [
        (
            "cfs requires geographic hierarchy weights. "
            f"Run `mise run data:geography` for year {year} or include `--loaders=geography,cfs`."
        )
    ]


_PREREQ_CHECKS: dict[str, Callable[[object, str, LoaderConfig], list[str]]] = {
    "qcew": _check_prereqs_census_dims,
    "employment_industry": _check_prereqs_census_dims,
    "dot_hpms": _check_prereqs_census_dims,
    "lodes": _check_prereqs_census_dims,
    "fcc": _check_prereqs_county_only,
    "hifld_prisons": _check_prereqs_county_only,
    "hifld_police": _check_prereqs_county_only,
    "hifld_electric": _check_prereqs_county_only,
    "mirta": _check_prereqs_county_only,
    "geography": _check_prereqs_geography,
    "cfs": _check_prereqs_cfs,
}


def _check_loader_prereqs(name: str, session: object, config: LoaderConfig) -> list[str]:
    """Return actionable prerequisite errors for a loader."""
    handler = _PREREQ_CHECKS.get(name)
    if handler is None:
        return []
    return handler(session, name, config)


def _print_prereq_errors(name: str, errors: list[str]) -> None:
    typer.secho(f"Prerequisite checks failed for {name}:", fg=typer.colors.RED)
    for error in errors:
        typer.echo(f"  - {error}")


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
        typer.Option(
            "--loaders",
            help=(
                "Loader names (e.g., census,fred,energy,qcew,trade,materials,"
                "employment_industry,dot_hpms,lodes)"
            ),
        ),
    ] = None,
    schema_check: Annotated[
        bool,
        typer.Option(
            "--schema-check/--no-schema-check",
            help="Validate normalized schema before loading",
        ),
    ] = True,
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
    selected = _resolve_loader_order(_validate_loaders(loaders))

    if not quiet:
        typer.echo("Initializing 3NF database...")
    init_normalized_db()
    if schema_check:
        if not quiet:
            typer.echo("Checking normalized schema for drift...")
        _run_schema_check(quiet)

    total_stats, has_errors = _run_all_loaders(selected, config, reset, quiet)

    if not quiet:
        typer.echo("\nCreating analytical views...")
    view_count = create_views(get_normalized_engine())
    if not quiet:
        _print_summary(total_stats, view_count)
        _print_empty_tables(get_normalized_engine())

    if has_errors:
        raise typer.Exit(1)


@app.command("readiness")
def readiness(
    config_file: Annotated[
        Path | None,
        typer.Option("--config-file", "-c", help="Path to YAML config file"),
    ] = None,
    loaders: Annotated[
        str | None,
        typer.Option(
            "--loaders",
            help=(
                "Loader names (e.g., census,fred,energy,qcew,trade,materials,"
                "employment_industry,dot_hpms,lodes)"
            ),
        ),
    ] = None,
    online: Annotated[
        bool,
        typer.Option("--online/--offline", help="Validate API endpoints over the network"),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict/--no-strict", help="Treat warnings as failures"),
    ] = False,
    repair: Annotated[
        bool,
        typer.Option("--repair/--no-repair", help="Apply additive schema repairs"),
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
) -> None:
    """Run ingest readiness checks (preflight + schema + prerequisites)."""
    config = load_config_from_yaml(config_file) if config_file else LoaderConfig()
    selected = _resolve_loader_order(_validate_loaders(loaders))
    _execute_readiness(config, selected, online, strict, repair, quiet)


@app.command("schema-check")
def schema_check(
    config_file: Annotated[
        Path | None,
        typer.Option("--config-file", "-c", help="Path to YAML config file"),
    ] = None,
    loaders: Annotated[
        str | None,
        typer.Option(
            "--loaders",
            help=(
                "Loader names (e.g., census,fred,energy,qcew,trade,materials,"
                "employment_industry,dot_hpms,lodes)"
            ),
        ),
    ] = None,
    online: Annotated[
        bool,
        typer.Option("--online/--offline", help="Validate API endpoints over the network"),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict/--no-strict", help="Treat warnings as failures"),
    ] = False,
    repair: Annotated[
        bool,
        typer.Option("--repair/--no-repair", help="Apply additive schema repairs"),
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
) -> None:
    """Alias for ingest readiness checks."""
    config = load_config_from_yaml(config_file) if config_file else LoaderConfig()
    selected = _resolve_loader_order(_validate_loaders(loaders))
    _execute_readiness(config, selected, online, strict, repair, quiet)


@app.command("schema-init")
def schema_init(
    views: Annotated[
        bool,
        typer.Option("--views/--no-views", help="Create analytical views after tables"),
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
) -> None:
    """Create normalized schema tables (and optional views)."""
    from babylon.data.normalize.database import get_normalized_engine, init_normalized_db
    from babylon.data.normalize.views import create_views

    init_normalized_db()
    view_count = 0
    if views:
        view_count = create_views(get_normalized_engine())
    if not quiet:
        typer.echo("Normalized schema tables created.")
        if views:
            typer.echo(f"Views created: {view_count}")


@app.command("preflight")
def preflight(
    config_file: Annotated[
        Path | None,
        typer.Option("--config-file", "-c", help="Path to YAML config file"),
    ] = None,
    loaders: Annotated[
        str | None,
        typer.Option(
            "--loaders",
            help=(
                "Loader names (e.g., census,fred,energy,qcew,trade,materials,"
                "employment_industry,dot_hpms,lodes)"
            ),
        ),
    ] = None,
    online: Annotated[
        bool,
        typer.Option("--online/--offline", help="Validate API endpoints over the network"),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict/--no-strict", help="Treat warnings as failures"),
    ] = False,
    repair: Annotated[
        bool,
        typer.Option("--repair/--no-repair", help="Apply additive schema repairs"),
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
) -> None:
    """Alias for ingest readiness checks."""
    config = load_config_from_yaml(config_file) if config_file else LoaderConfig()
    selected = _resolve_loader_order(_validate_loaders(loaders))
    _execute_readiness(config, selected, online, strict, repair, quiet)


def _run_all_loaders(
    selected: list[str], config: LoaderConfig, reset: bool, quiet: bool
) -> tuple[list[LoadStats], bool]:
    """Run all selected loaders and return stats."""
    from babylon.data.normalize.database import get_normalized_session
    from babylon.utils.exceptions import BabylonError
    from babylon.utils.log import log_context_scope

    total_stats: list[LoadStats] = []
    has_errors = False

    with get_normalized_session() as session:
        for name in selected:
            if not quiet:
                typer.echo(f"\n{'=' * 60}")
                typer.secho(f"Loading: {name.upper()}", fg=typer.colors.CYAN, bold=True)
                typer.echo("=" * 60)

            try:
                prereq_errors = _check_loader_prereqs(name, session, config)
                if prereq_errors:
                    _print_prereq_errors(name, prereq_errors)
                    has_errors = True
                    raise typer.Exit(1)
                with log_context_scope(loader=name):
                    stats = _run_loader(name, session, config, reset, not quiet)
                    total_stats.append(stats)
                    if stats.has_errors:
                        has_errors = True
                    if not quiet:
                        print_stats(stats)
            except Exception as e:
                if isinstance(e, BabylonError):
                    e.log(logger, level=logging.ERROR, exc_info=True)
                else:
                    logger.exception("Loader %s failed", name)
                typer.secho(f"Error loading {name}: {e}", fg=typer.colors.RED)
                if isinstance(e, BabylonError) and not quiet:
                    if e.details:
                        typer.echo(f"Details: {e.details}")
                    hint = getattr(e, "hint", None)
                    if hint:
                        typer.echo(f"Hint: {hint}")
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


def _quote_identifier(engine: Any, name: str) -> str:
    preparer = engine.dialect.identifier_preparer
    return ".".join(preparer.quote(part) for part in name.split("."))


def _collect_empty_tables(engine: Any) -> list[str]:
    """Return base tables with zero rows."""
    excluded = {"alembic_version"}
    with engine.connect() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
            ).fetchall()
        ]

        empty_tables: list[str] = []
        for table in tables:
            if table in excluded:
                continue
            quoted = _quote_identifier(engine, table)
            has_row = conn.execute(text(f"SELECT 1 FROM {quoted} LIMIT 1")).first()
            if has_row is None:
                empty_tables.append(table)

    return empty_tables


def _print_empty_tables(engine: object) -> None:
    empty_tables = _collect_empty_tables(engine)
    if not empty_tables:
        typer.secho("Empty tables: none", fg=typer.colors.GREEN)
        return
    typer.secho(f"Empty tables: {len(empty_tables)}", fg=typer.colors.YELLOW)
    for table in empty_tables[:50]:
        typer.echo(f"  - {table}")
    if len(empty_tables) > 50:
        typer.echo(f"  ... and {len(empty_tables) - 50} more")


def _make_census_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.census import CensusLoader

    return CensusLoader(config)


def _make_fred_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.fred import FredLoader

    return FredLoader(config)


def _make_energy_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.energy import EnergyLoader

    return EnergyLoader(config)


def _make_qcew_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.qcew import QcewLoader

    return QcewLoader(config)


def _make_trade_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.trade import TradeLoader

    return TradeLoader(config)


def _make_materials_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.materials import MaterialsLoader

    return MaterialsLoader(config)


def _make_employment_industry_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.employment_industry import EmploymentIndustryLoader

    return EmploymentIndustryLoader(config)


def _make_dot_hpms_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.dot import DotHpmsLoader

    return DotHpmsLoader(config)


def _make_lodes_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.lodes import LodesCrosswalkLoader

    return LodesCrosswalkLoader(config)


def _make_hifld_prisons_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.hifld import HIFLDPrisonsLoader

    return HIFLDPrisonsLoader(config)


def _make_hifld_police_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.hifld import HIFLDPoliceLoader

    return HIFLDPoliceLoader(config)


def _make_hifld_electric_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.hifld import HIFLDElectricLoader

    return HIFLDElectricLoader(config)


def _make_mirta_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.mirta import MIRTAMilitaryLoader

    return MIRTAMilitaryLoader(config)


def _make_geography_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.geography import GeographicHierarchyLoader

    return GeographicHierarchyLoader(config)


def _make_cfs_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.cfs import CFSLoader

    return CFSLoader(config)


def _make_fcc_loader(config: LoaderConfig) -> DataLoader:
    from babylon.data.fcc import FCCBroadbandLoader

    return FCCBroadbandLoader(config)


_LOADER_FACTORIES: dict[str, Callable[[LoaderConfig], DataLoader]] = {
    "census": _make_census_loader,
    "fred": _make_fred_loader,
    "energy": _make_energy_loader,
    "qcew": _make_qcew_loader,
    "trade": _make_trade_loader,
    "materials": _make_materials_loader,
    "employment_industry": _make_employment_industry_loader,
    "dot_hpms": _make_dot_hpms_loader,
    "lodes": _make_lodes_loader,
    "hifld_prisons": _make_hifld_prisons_loader,
    "hifld_police": _make_hifld_police_loader,
    "hifld_electric": _make_hifld_electric_loader,
    "mirta": _make_mirta_loader,
    "geography": _make_geography_loader,
    "cfs": _make_cfs_loader,
    "fcc": _make_fcc_loader,
}


def _run_loader(
    name: str,
    session: object,
    config: LoaderConfig,
    reset: bool,
    verbose: bool,
) -> LoadStats:
    """Run a specific loader by name."""
    factory = _LOADER_FACTORIES.get(name)
    if factory is None:
        raise ValueError(f"Unknown loader: {name}")

    loader = factory(config)
    return loader.load(session, reset=reset, verbose=verbose)  # type: ignore[arg-type]


@app.command()
def census(
    year: Annotated[
        int,
        typer.Option("--year", "-y", help="Census ACS 5-year vintage"),
    ] = 2021,
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
def employment_industry(
    data_path: Annotated[
        Path | None,
        typer.Option("--data-path", help="Path to employment industry data directory"),
    ] = None,
    states: Annotated[
        str | None,
        typer.Option("--states", help="State FIPS codes (e.g., 06,36)"),
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
    """Load employment industry data into 3NF database."""
    from babylon.data.employment_industry import EmploymentIndustryLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(state_fips_list=parse_states(states), verbose=not quiet)

    if not quiet:
        typer.echo("Loading employment industry data...")

    init_normalized_db()
    loader = EmploymentIndustryLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet, data_path=data_path)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def dot_hpms(
    data_path: Annotated[
        Path | None,
        typer.Option("--data-path", help="Path to HPMS CSV or directory"),
    ] = None,
    states: Annotated[
        str | None,
        typer.Option("--states", help="State FIPS codes (e.g., 06,36)"),
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
    """Load DOT HPMS road segments into 3NF database."""
    from babylon.data.dot import DotHpmsLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(state_fips_list=parse_states(states), verbose=not quiet)

    if not quiet:
        typer.echo("Loading DOT HPMS road segments...")

    init_normalized_db()
    loader = DotHpmsLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet, data_path=data_path)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command()
def lodes(
    data_path: Annotated[
        Path | None,
        typer.Option("--data-path", help="Path to LODES crosswalk file or directory"),
    ] = None,
    states: Annotated[
        str | None,
        typer.Option("--states", help="State FIPS codes (e.g., 06,36)"),
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
    """Load LODES crosswalk data into 3NF database."""
    from babylon.data.lodes import LodesCrosswalkLoader
    from babylon.data.normalize.database import get_normalized_session, init_normalized_db

    config = LoaderConfig(state_fips_list=parse_states(states), verbose=not quiet)

    if not quiet:
        typer.echo("Loading LODES crosswalk data...")

    init_normalized_db()
    loader = LodesCrosswalkLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=reset, verbose=not quiet, data_path=data_path)

    print_stats(stats)
    if stats.has_errors:
        raise typer.Exit(1)


@app.command("export-sqlite")
def export_sqlite(
    duckdb_path: Annotated[
        Path | None,
        typer.Option("--duckdb-path", help="Path to DuckDB file to export"),
    ] = None,
    sqlite_path: Annotated[
        Path | None,
        typer.Option("--sqlite-path", help="Target SQLite output path"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Overwrite existing SQLite file"),
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
) -> None:
    """Export DuckDB tables into a SQLite database file."""
    from babylon.data.export_sqlite import export_duckdb_to_sqlite

    count = export_duckdb_to_sqlite(
        duckdb_path=duckdb_path,
        sqlite_path=sqlite_path,
        overwrite=overwrite,
    )

    if not quiet:
        target = sqlite_path or Path("data/sqlite/marxist-data-3NF.sqlite")
        typer.echo(f"Exported {count} tables to {target}")


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
