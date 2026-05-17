"""Build manifest.json — the artifact-bundle reproducibility fingerprint.

Spec: 064-headless-sim-runner (T027).

The manifest follows ``contracts/manifest_json_schema.yaml`` and exposes:

* ``schema_version`` — locked literal "1.0"
* ``generator`` — tool name, babylon version, git SHA, python version, partial flag
* ``files`` — per-artifact name + schema_ref + sha256 + size + optional row_count
* ``reproducibility`` — deterministic_inputs + non_deterministic_inputs + input_hash
* ``column_dictionaries`` — inlined 22-column dictionary mirroring trace_csv_schema.yaml

``input_hash`` is the SHA-256 of canonical-JSON-serialized
``deterministic_inputs``; two runs with the same hash MUST produce
byte-identical trace.csv and summary.json (modulo declared wallclock /
hostname fields).
"""

from __future__ import annotations

import hashlib
import json
import platform
import socket
import subprocess
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from babylon.engine.headless_runner.models import ExitReason, SimulationRunConfig
from babylon.engine.headless_runner.trace_emitter import TRACE_COLUMNS

#: Inlined column dictionary mirroring trace_csv_schema.yaml. Embedded
#: here so LLM consumers can parse trace.csv without fetching external
#: schema files.
TRACE_COLUMN_DICT: tuple[dict[str, Any], ...] = (
    {
        "name": "tick",
        "type": "int",
        "units": "weekly_tick",
        "semantics": "Zero-indexed tick.",
        "nullable": False,
    },
    {
        "name": "simulated_year",
        "type": "float",
        "units": "calendar_year",
        "semantics": "start_year + tick/52.",
        "nullable": False,
    },
    {
        "name": "entity_id",
        "type": "str",
        "units": "id",
        "semantics": "5-digit FIPS / canonical short name.",
        "nullable": False,
    },
    {
        "name": "entity_kind",
        "type": "str",
        "units": "enum",
        "semantics": "county | external | national | hex_aggregate.",
        "nullable": False,
    },
    {
        "name": "v",
        "type": "float",
        "units": "USD/week",
        "semantics": "Variable capital this tick.",
        "nullable": True,
        "applies_to": ["county", "national", "hex_aggregate"],
    },
    {
        "name": "c",
        "type": "float",
        "units": "USD/week",
        "semantics": "Constant capital consumed.",
        "nullable": True,
        "applies_to": ["county", "national", "hex_aggregate"],
    },
    {
        "name": "s",
        "type": "float",
        "units": "USD/week",
        "semantics": "Surplus value extracted.",
        "nullable": True,
        "applies_to": ["county", "national", "hex_aggregate"],
    },
    {
        "name": "k",
        "type": "float",
        "units": "USD/stock",
        "semantics": "Accumulated capital stock.",
        "nullable": True,
        "applies_to": ["county", "national", "hex_aggregate"],
    },
    {
        "name": "p_acquiescence",
        "type": "float",
        "units": "prob",
        "semantics": "P(S|A).",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "p_revolution",
        "type": "float",
        "units": "prob",
        "semantics": "P(S|R).",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "ideology_r",
        "type": "float",
        "units": "simplex",
        "semantics": "Reactionary weight.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "ideology_l",
        "type": "float",
        "units": "simplex",
        "semantics": "Liberal weight.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "ideology_f",
        "type": "float",
        "units": "simplex",
        "semantics": "Front weight.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "surveillance_coupling",
        "type": "float",
        "units": "ratio",
        "semantics": "State surveillance coupling.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "internet_access_pct",
        "type": "float",
        "units": "ratio",
        "semantics": "Broadband-population fraction.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "biocapacity_stock",
        "type": "float",
        "units": "abstract",
        "semantics": "Remaining biocapacity.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "energy_stock",
        "type": "float",
        "units": "abstract",
        "semantics": "Remaining energy stock.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "raw_material_stock",
        "type": "float",
        "units": "abstract",
        "semantics": "Remaining raw material stock.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "profit_rate",
        "type": "float",
        "units": "ratio",
        "semantics": "s/(c+v).",
        "nullable": True,
        "applies_to": ["county", "national"],
    },
    {
        "name": "exploitation_rate",
        "type": "float",
        "units": "ratio",
        "semantics": "s/v.",
        "nullable": True,
        "applies_to": ["county", "national"],
    },
    {
        "name": "population",
        "type": "int",
        "units": "persons",
        "semantics": "Resident population.",
        "nullable": True,
        "applies_to": ["county"],
    },
    {
        "name": "employment_proxy",
        "type": "float",
        "units": "FTE",
        "semantics": "QCEW-derived employment proxy.",
        "nullable": True,
        "applies_to": ["county"],
    },
)

assert len(TRACE_COLUMN_DICT) == len(TRACE_COLUMNS), (
    "TRACE_COLUMN_DICT and TRACE_COLUMNS must stay in lock-step"
)


def build_manifest(
    *,
    config: SimulationRunConfig,
    session_id: str,
    exit_reason: ExitReason,
    wallclock_start: datetime,
    wallclock_end: datetime,
    artifact_dir: Path,
    artifact_files: list[tuple[str, str, int, int | None]],
    defines_hash: str,
    data_versions: dict[str, Any],
    engine_systems_invoked: list[str] | None = None,
    bridge_db_reads: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Construct the manifest payload as a plain dict.

    Args:
        config: The :class:`SimulationRunConfig` driving the run.
        session_id: UUID string for this run.
        exit_reason: How the run terminated.
        wallclock_start: Run start time (UTC).
        wallclock_end: Run end time (UTC).
        artifact_dir: Where the bundle is being written.
        artifact_files: List of ``(name, schema_ref, size_bytes, row_count)``
            tuples; ``row_count`` is None for non-CSV files.
        defines_hash: SHA-256 over the canonical GameDefines serialization.
        data_versions: Reference-data vintages (TIGER year, LODES max year,
            etc.). Free-form; all entries land in ``deterministic_inputs``.
        engine_systems_invoked: Ordered list of engine system class names
            actually executed during the run (spec-065 T081 / spec-066
            T036). Empty list when the engine is not wired.
        bridge_db_reads: Spec-069 SC-002 instrumentation block. If
            provided, emitted as a top-level ``bridge_db_reads`` key with
            ``{population_db_reads, employment_db_reads, total_db_reads}``.
            Omit when running a non-bridged path.

    Returns:
        Dict ready to be JSON-encoded as manifest.json.
    """
    partial = exit_reason in (ExitReason.USER_INTERRUPTED, ExitReason.ERRORED)

    deterministic_inputs: dict[str, Any] = {
        "seed": config.random_seed,
        "ticks": config.ticks,
        "start_year": config.start_year,
        "scope_fips": sorted(config.scope_fips),
        "external_node_ids": sorted(config.external_node_ids),
        "defines_hash": defines_hash,
        "data_versions": data_versions,
        # Spec-065 T081: engine system class names (ordered) — empty
        # list when the engine is not yet wired (current first cut).
        # Participates in input_hash so add/remove of engine systems
        # between runs surfaces as hash drift.
        "engine_systems_invoked": engine_systems_invoked or [],
    }
    non_deterministic_inputs: dict[str, Any] = {
        "session_id": session_id,
        "wallclock_start": _iso_utc(wallclock_start),
        "wallclock_end": _iso_utc(wallclock_end),
        "hostname": socket.gethostname(),
        "working_dir": str(Path.cwd()),
    }

    file_entries: list[dict[str, Any]] = []
    for name, schema_ref, size_bytes, row_count in artifact_files:
        entry: dict[str, Any] = {
            "name": name,
            "schema_ref": schema_ref,
            "sha256": _sha256_file(artifact_dir / name),
            "size_bytes": size_bytes,
        }
        if row_count is not None:
            entry["row_count"] = row_count
        file_entries.append(entry)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "generator": {
            "tool": "babylon.engine.headless_runner",
            "babylon_version": _babylon_version(),
            "git_sha": _git_sha(),
            "python_version": platform.python_version(),
            "partial": partial,
        },
        "files": file_entries,
        "reproducibility": {
            "deterministic_inputs": deterministic_inputs,
            "non_deterministic_inputs": non_deterministic_inputs,
            "input_hash": input_hash(deterministic_inputs),
        },
        "column_dictionaries": {
            "trace_csv": [dict(c) for c in TRACE_COLUMN_DICT],
        },
    }
    if bridge_db_reads is not None:
        payload["bridge_db_reads"] = dict(bridge_db_reads)
    return payload


def input_hash(deterministic_inputs: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON serialization of ``deterministic_inputs``.

    Two runs with identical input_hash MUST produce byte-identical
    trace.csv and summary.json (modulo wallclock fields in
    non_deterministic_inputs).
    """
    canonical = json.dumps(deterministic_inputs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    """Compute the hex SHA-256 of ``path`` contents."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_utc(dt: datetime) -> str:
    """Format ``dt`` as ISO 8601 with explicit microsecond precision + ``Z``."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _babylon_version() -> str:
    """Best-effort lookup of the project version from package metadata."""
    try:
        return version("babylon")
    except PackageNotFoundError:
        return "unknown"


def _git_sha() -> str:
    """Best-effort HEAD SHA via subprocess; ``"unknown"`` on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"


def python_version() -> str:
    """Public helper, used by tests."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


__all__ = ["TRACE_COLUMN_DICT", "build_manifest", "input_hash", "python_version"]
