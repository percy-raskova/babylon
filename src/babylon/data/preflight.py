"""Preflight checks for data ingestion prerequisites."""

from __future__ import annotations

import importlib.util
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from babylon.config.base import BaseConfig
from babylon.data.qcew.loader_3nf import API_CUTOFF_YEAR

if TYPE_CHECKING:
    from babylon.data.loader_base import LoaderConfig

PreflightStatus = Literal["ok", "warn", "fail"]


@dataclass(frozen=True)
class PreflightCheck:
    """Single preflight check result."""

    check_id: str
    status: PreflightStatus
    message: str
    hint: str | None = None
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize check for structured output."""
        return {
            "check_id": self.check_id,
            "status": self.status,
            "message": self.message,
            "hint": self.hint,
            "details": self.details,
        }


@dataclass
class PreflightResult:
    """Aggregated preflight results."""

    checks: list[PreflightCheck] = field(default_factory=list)

    @property
    def failures(self) -> list[PreflightCheck]:
        return [check for check in self.checks if check.status == "fail"]

    @property
    def warnings(self) -> list[PreflightCheck]:
        return [check for check in self.checks if check.status == "warn"]

    @property
    def ok(self) -> bool:
        return len(self.failures) == 0

    def to_dict(self) -> dict[str, object]:
        """Serialize results for structured output."""
        return {
            "ok": self.ok,
            "failures": len(self.failures),
            "warnings": len(self.warnings),
            "checks": [check.to_dict() for check in self.checks],
        }


# Type alias for check accumulator function
AddCheckFn = Callable[[str, PreflightStatus, str, str | None, dict[str, object] | None], None]


def _check_env_var(
    add_check: AddCheckFn,
    name: str,
    required: bool,
    hint: str | None = None,
) -> None:
    """Check if an environment variable is set."""
    value = os.getenv(name)
    if value:
        add_check(f"env:{name}", "ok", f"{name} is set", None, None)
    elif required:
        add_check(f"env:{name}", "fail", f"{name} is not set", hint, None)
    else:
        add_check(f"env:{name}", "warn", f"{name} is not set", hint, None)


def _check_module(
    add_check: AddCheckFn,
    module: str,
    required: bool,
    hint: str | None = None,
) -> None:
    """Check if a Python module is available."""
    if importlib.util.find_spec(module):
        add_check(f"module:{module}", "ok", f"Module available: {module}", None, None)
    elif required:
        add_check(f"module:{module}", "fail", f"Missing Python module: {module}", hint, None)
    else:
        add_check(f"module:{module}", "warn", f"Missing Python module: {module}", hint, None)


def _check_file(
    add_check: AddCheckFn,
    path: Path,
    check_id: str,
    hint: str | None = None,
) -> None:
    """Check if a file exists."""
    if path.exists():
        add_check(check_id, "ok", f"Found {path}", None, None)
    else:
        add_check(check_id, "fail", f"Missing {path}", hint, None)


def _check_dir_with_glob(
    add_check: AddCheckFn,
    path: Path,
    pattern: str,
    check_id: str,
    hint: str | None = None,
) -> None:
    """Check if a directory contains files matching a pattern."""
    if not path.exists():
        add_check(check_id, "fail", f"Missing {path}", hint, None)
        return
    matches = list(path.glob(pattern))
    if matches:
        add_check(check_id, "ok", f"Found {len(matches)} files in {path}", None, None)
    else:
        add_check(check_id, "fail", f"No files matching {pattern} in {path}", hint, None)


def _check_dir_with_globs(
    add_check: AddCheckFn,
    path: Path,
    patterns: list[str],
    check_id: str,
    hint: str | None = None,
) -> None:
    """Check if a directory contains files matching any of several patterns."""
    if not path.exists():
        add_check(check_id, "fail", f"Missing {path}", hint, None)
        return
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(path.glob(pattern))
    if matches:
        add_check(check_id, "ok", f"Found {len(matches)} files in {path}", None, None)
    else:
        joined = ", ".join(patterns)
        add_check(check_id, "fail", f"No files matching {joined} in {path}", hint, None)


def _check_core_dependencies(add_check: AddCheckFn) -> None:
    """Check core runtime dependencies for DuckDB ingestion."""
    _check_module(add_check, "duckdb", required=True, hint="Install `duckdb` (poetry install).")
    _check_module(
        add_check, "duckdb_engine", required=True, hint="Install `duckdb-engine` (poetry install)."
    )
    _check_module(
        add_check, "sqlalchemy", required=True, hint="Install `sqlalchemy` (poetry install)."
    )


def _check_census(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check census loader prerequisites."""
    census_dir = data_dir / "census"
    cbsa_path = census_dir / "cbsa_delineation_2023.xlsx"

    if not cbsa_path.exists():
        add_check(
            "census:cbsa_file",
            "fail",
            f"Missing CBSA delineation file: {cbsa_path}",
            "Download from Census Bureau delineation page.",
            None,
        )
    else:
        from babylon.data.census import cbsa_parser

        if cbsa_parser._is_lfs_pointer(cbsa_path):  # noqa: SLF001
            add_check(
                "census:cbsa_file",
                "fail",
                f"CBSA delineation file is a Git LFS pointer: {cbsa_path}",
                'Run `git lfs pull --include "data/census/cbsa_delineation_2023.xlsx"`.',
                None,
            )
        else:
            add_check("census:cbsa_file", "ok", f"Found {cbsa_path}", None, None)

    _check_env_var(
        add_check,
        "CENSUS_API_KEY",
        required=False,
        hint="Optional but recommended for higher rate limits.",
    )
    _check_module(
        add_check,
        "census",
        required=False,
        hint="Optional census library for higher-level API access.",
    )
    _check_module(add_check, "pandas", required=True, hint="Install `pandas` (poetry install).")
    _check_module(add_check, "openpyxl", required=True, hint="Install `openpyxl` (poetry install).")


def _check_fred(add_check: AddCheckFn) -> None:
    """Check FRED loader prerequisites."""
    _check_env_var(
        add_check,
        "FRED_API_KEY",
        required=True,
        hint="Set FRED_API_KEY from https://fredaccount.stlouisfed.org/apikeys",
    )
    _check_module(
        add_check,
        "fredapi",
        required=False,
        hint="Optional fredapi library for higher-level FRED access.",
    )


def _check_energy(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check energy loader prerequisites."""
    energy_key = os.getenv("ENERGY_API_KEY")
    if energy_key:
        add_check("env:ENERGY_API_KEY", "ok", "ENERGY_API_KEY is set", None, None)
    else:
        add_check(
            "env:ENERGY_API_KEY",
            "warn",
            "ENERGY_API_KEY is not set",
            "Set ENERGY_API_KEY or provide MER Excel files in data/energy.",
            None,
        )

    energy_dir = data_dir / "energy"
    mer_files = list(energy_dir.glob("Table *.xlsx")) if energy_dir.exists() else []
    if mer_files:
        add_check(
            "energy:mer_files",
            "ok",
            f"Found {len(mer_files)} MER tables in {energy_dir}",
            None,
            None,
        )
        _check_module(
            add_check, "pandas", required=True, hint="Install `pandas` for MER ingestion."
        )
        _check_module(
            add_check, "openpyxl", required=True, hint="Install `openpyxl` for MER ingestion."
        )
    elif not energy_key:
        add_check(
            "energy:mer_files",
            "fail",
            f"No MER tables found in {energy_dir}",
            "Provide MER Excel files (Table *.xlsx) in data/energy or set ENERGY_API_KEY.",
            None,
        )


def _check_qcew(add_check: AddCheckFn, data_dir: Path, config: LoaderConfig) -> None:
    """Check QCEW loader prerequisites."""
    needs_files = any(year < API_CUTOFF_YEAR for year in config.qcew_years)
    if needs_files:
        _check_dir_with_globs(
            add_check,
            data_dir / "qcew",
            ["*.csv", "*.xlsx"],
            "qcew:files",
            hint="Provide historical QCEW files (.csv or .xlsx) under data/qcew.",
        )
    else:
        add_check(
            "qcew:files", "ok", "QCEW API-only years selected; CSV files optional", None, None
        )


def _check_trade(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check trade loader prerequisites."""
    _check_file(
        add_check,
        data_dir / "imperial_rent" / "country.xlsx",
        "trade:file",
        hint="Provide data/imperial_rent/country.xlsx before running trade loader.",
    )


def _check_materials(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check materials loader prerequisites."""
    _check_dir_with_globs(
        add_check,
        data_dir / "raw_mats",
        ["commodities/mcs2025-*_salient.csv", "minerals/mcs2025-*_salient.csv"],
        "materials:files",
        hint="Provide USGS MCS salient CSVs under data/raw_mats/commodities or data/raw_mats/minerals.",
    )


def _check_employment_industry(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check employment industry loader prerequisites."""
    _check_dir_with_glob(
        add_check,
        data_dir / "employment_industry",
        "*.annual.by_area/*.csv",
        "employment:files",
        hint="Provide BLS employment industry CSVs under data/employment_industry/*.",
    )


def _check_dot_hpms(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check DOT HPMS loader prerequisites."""
    _check_dir_with_glob(
        add_check,
        data_dir / "dot",
        "HPMS_Spatial*Sections*.csv",
        "dot:hpms",
        hint="Provide HPMS spatial CSVs under data/dot.",
    )


def _check_lodes(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check LODES loader prerequisites."""
    _check_dir_with_glob(
        add_check,
        data_dir / "lodes",
        "us_xwalk.csv*",
        "lodes:files",
        hint="Provide LODES crosswalk file (us_xwalk.csv) under data/lodes.",
    )


def _check_fcc(add_check: AddCheckFn, data_dir: Path) -> None:
    """Check FCC loader prerequisites."""
    download_dir = data_dir / "fcc" / "downloads"
    _check_dir_with_glob(
        add_check,
        download_dir,
        "*/national/*.csv",
        "fcc:downloads",
        hint="Run `mise run data:fcc-download` to populate data/fcc/downloads.",
    )
    _check_env_var(
        add_check,
        "FCC_USERNAME",
        required=False,
        hint="Required only for data:fcc-download (not for loading downloaded files).",
    )
    _check_env_var(
        add_check,
        "FCC_API_KEY",
        required=False,
        hint="Required only for data:fcc-download (not for loading downloaded files).",
    )


def _check_arcgis_loaders(
    add_check: AddCheckFn,
    selected: set[str],
    online: bool,
) -> None:
    """Check ArcGIS-based loader prerequisites."""
    arcgis_loaders = {
        "hifld_prisons": "HIFLD prisons",
        "hifld_police": "HIFLD police",
        "hifld_electric": "HIFLD electric",
        "mirta": "MIRTA",
    }
    arcgis_selected = arcgis_loaders.keys() & selected
    if not arcgis_selected:
        return

    from babylon.data.data_sources import get_arcgis_service_url
    from babylon.data.external.arcgis import ArcGISClient

    endpoints = {
        "hifld_prisons": [get_arcgis_service_url("hifld_prisons")],
        "hifld_police": [get_arcgis_service_url("hifld_police")],
        "hifld_electric": [
            get_arcgis_service_url("hifld_electric", "substations"),
            get_arcgis_service_url("hifld_electric", "transmission"),
        ],
        "mirta": [get_arcgis_service_url("mirta")],
    }

    for loader_name in arcgis_selected:
        urls = endpoints.get(loader_name, [])
        for url in urls:
            check_id = f"{loader_name}:endpoint"
            if online:
                try:
                    with ArcGISClient(url) as client:
                        client.get_service_info()
                    add_check(check_id, "ok", f"ArcGIS endpoint reachable: {url}", None, None)
                except Exception as exc:  # pragma: no cover - network
                    add_check(
                        check_id,
                        "fail",
                        f"ArcGIS endpoint failed: {url}",
                        str(exc),
                        None,
                    )
            else:
                add_check(
                    check_id,
                    "warn",
                    f"ArcGIS endpoint not validated (offline): {url}",
                    "Run preflight with --online to validate endpoints.",
                    None,
                )


def run_preflight(
    config: LoaderConfig,
    loaders: list[str],
    base_dir: Path | None = None,
    online: bool = False,
) -> PreflightResult:
    """Run ingestion prerequisite checks for selected loaders.

    Args:
        config: LoaderConfig with temporal/geographic settings.
        loaders: List of loader names to check (e.g., ["census", "fred"]).
        base_dir: Base directory for data files (default: BaseConfig.BASE_DIR).
        online: If True, validate network endpoints (slower).

    Returns:
        PreflightResult with all check outcomes.
    """
    resolved_base = base_dir or BaseConfig.BASE_DIR
    data_dir = resolved_base / "data"
    selected = {name.lower() for name in loaders}

    checks: list[PreflightCheck] = []

    def add_check(
        check_id: str,
        status: PreflightStatus,
        message: str,
        hint: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        checks.append(
            PreflightCheck(
                check_id=check_id,
                status=status,
                message=message,
                hint=hint,
                details=details or {},
            )
        )

    # Core dependencies (always checked)
    _check_core_dependencies(add_check)

    # Loader-specific checks (dispatched by name)
    if "census" in selected:
        _check_census(add_check, data_dir)
    if "fred" in selected:
        _check_fred(add_check)
    if "energy" in selected:
        _check_energy(add_check, data_dir)
    if "qcew" in selected:
        _check_qcew(add_check, data_dir, config)
    if "trade" in selected:
        _check_trade(add_check, data_dir)
    if "materials" in selected:
        _check_materials(add_check, data_dir)
    if "employment_industry" in selected:
        _check_employment_industry(add_check, data_dir)
    if "dot_hpms" in selected:
        _check_dot_hpms(add_check, data_dir)
    if "lodes" in selected:
        _check_lodes(add_check, data_dir)
    if "fcc" in selected:
        _check_fcc(add_check, data_dir)

    # ArcGIS loaders (handled together)
    _check_arcgis_loaders(add_check, selected, online)

    return PreflightResult(checks=checks)


__all__ = ["PreflightCheck", "PreflightResult", "run_preflight"]
