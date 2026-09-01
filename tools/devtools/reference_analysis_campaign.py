"""Run bounded CI campaigns against the frozen Python simulation reference.

This orchestrator is development tooling. It never reads or writes
authoritative game state, and every manifest labels that boundary explicitly.
The Rust simulation remains authoritative; the Python engine is the frozen
``p27-python-freeze`` transcription and analysis reference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

_CAMPAIGN_SCHEMA: Final[str] = "babylon.sim-analysis.reference-campaign.v1"
_AUTHORITY: Final[str] = "frozen_python_reference"
_FROZEN_REF: Final[str] = "p27-python-freeze"
_SEED: Final[int] = 304
_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports/frozen-reference-analysis")
_MAX_OUTPUT_BYTES: Final[int] = 4 * 1024 * 1024
_CAMPAIGN_TIMEOUT_SECONDS: Final[int] = 55 * 60
_READ_CHUNK_BYTES: Final[int] = 64 * 1024
_SOURCE_FILE_LIMIT: Final[int] = 5_000
_SOURCE_BYTE_LIMIT: Final[int] = 64 * 1024 * 1024
_CURATED_SENSITIVITY_PARAMETERS: Final[tuple[str, ...]] = (
    "economy.base_subsistence",
    "economy.extraction_efficiency",
    "economy.comprador_cut",
    "economy.super_wage_rate",
)

LegStatus = Literal[
    "succeeded",
    "failed",
    "timed_out",
    "output_limit_exceeded",
    "launch_failed",
]


@dataclass(frozen=True)
class ResourceMetrics:
    """Integer resource measurements for one subprocess leg."""

    wall_time_ns: int
    user_cpu_ns: int
    system_cpu_ns: int
    max_rss_bytes: int

    def as_dict(self) -> dict[str, int]:
        """Return the JSON representation with native integers only."""
        return {
            "wall_time_ns": int(self.wall_time_ns),
            "user_cpu_ns": int(self.user_cpu_ns),
            "system_cpu_ns": int(self.system_cpu_ns),
            "max_rss_bytes": int(self.max_rss_bytes),
        }


@dataclass(frozen=True)
class LegSpec:
    """One exact, allowlisted campaign leg."""

    name: str
    argv: list[str]
    output_dir: Path
    timeout_seconds: int
    max_output_bytes: int
    required: bool
    requested_workload: dict[str, Any]
    expected_artifacts: tuple[str, ...]
    expected_schemas: dict[str, str] = field(default_factory=dict)
    working_directory: Path | None = None


@dataclass(frozen=True)
class LegExecution:
    """Bounded process outcome before artifact indexing."""

    status: LegStatus
    return_code: int | None
    failure_reason: str | None
    resources: ResourceMetrics


@dataclass(frozen=True)
class CampaignResult:
    """Completed campaign paths and process exit decision."""

    run_directory: Path
    manifest_path: Path
    exit_code: int


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _sha256_file(path: Path) -> str:
    """Hash one artifact without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_READ_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _source_tree_sha256(repository_root: Path) -> str:
    """Hash the frozen Python simulation, analysis tooling, and lock inputs."""
    root = repository_root.resolve()
    candidates = list((root / "src" / "babylon").rglob("*.py"))
    candidates.extend((root / "tools" / "devtools" / "sim_analysis").rglob("*.py"))
    candidates.extend(
        path
        for path in (
            root / "tools" / "devtools" / "reference_analysis_campaign.py",
            root / "src" / "babylon" / "data" / "defines.yaml",
            root / "pyproject.toml",
            root / "uv.lock",
        )
        if path.is_file()
    )
    files = sorted(set(candidates), key=lambda path: path.relative_to(root).as_posix())
    if not files:
        raise ValueError("reference campaign source fingerprint found no source files")
    if len(files) > _SOURCE_FILE_LIMIT:
        raise ValueError(
            f"reference campaign source fingerprint exceeds {_SOURCE_FILE_LIMIT} files"
        )

    digest = hashlib.sha256()
    total_bytes = 0
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        with path.open("rb") as stream:
            while chunk := stream.read(_READ_CHUNK_BYTES):
                total_bytes += len(chunk)
                if total_bytes > _SOURCE_BYTE_LIMIT:
                    raise ValueError(
                        f"reference campaign source fingerprint exceeds {_SOURCE_BYTE_LIMIT} bytes"
                    )
                digest.update(chunk)
    return digest.hexdigest()


def _git_head(repository_root: Path) -> str:
    """Read and validate the checked-out commit identity."""
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    git_sha = completed.stdout.strip()
    if len(git_sha) not in (40, 64) or any(
        character not in "0123456789abcdef" for character in git_sha
    ):
        raise ValueError("git rev-parse returned an invalid commit identity")
    return git_sha


def _read_process_rss_bytes(process_id: int) -> int:
    """Read a Linux process high-water RSS; return zero when unavailable."""
    try:
        status = Path(f"/proc/{process_id}/status").read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, OSError):
        return 0
    values: dict[str, int] = {}
    for line in status.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {"VmHWM", "VmRSS"}:
            fields = value.split()
            if fields and fields[0].isdigit():
                values[key] = int(fields[0]) * 1024
    return values.get("VmHWM", values.get("VmRSS", 0))


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    """Terminate one exact child, escalating to kill after a short grace."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _run_leg(spec: LegSpec) -> LegExecution:
    """Run one subprocess with wall-clock and combined-output bounds."""
    spec.output_dir.mkdir(parents=True, exist_ok=True)
    started_ns = time.monotonic_ns()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    output_lock = threading.Lock()
    output_limit_exceeded = threading.Event()
    captured_bytes = 0

    def consume(stream: Any, destination: bytearray) -> None:
        nonlocal captured_bytes
        while chunk := stream.read(_READ_CHUNK_BYTES):
            with output_lock:
                remaining = max(0, spec.max_output_bytes - captured_bytes)
                if remaining:
                    retained = chunk[:remaining]
                    destination.extend(retained)
                    captured_bytes += len(retained)
                if len(chunk) > remaining:
                    output_limit_exceeded.set()

    try:
        process = subprocess.Popen(
            spec.argv,
            cwd=spec.working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        elapsed = time.monotonic_ns() - started_ns
        message = f"could not launch leg: {type(exc).__name__}: {exc}"[:1000]
        (spec.output_dir / "stdout.log").write_bytes(b"")
        (spec.output_dir / "stderr.log").write_text(f"{message}\n", encoding="utf-8")
        return LegExecution(
            status="launch_failed",
            return_code=None,
            failure_reason=message,
            resources=ResourceMetrics(elapsed, 0, 0, 0),
        )

    assert process.stdout is not None
    assert process.stderr is not None
    stdout_thread = threading.Thread(
        target=consume, args=(process.stdout, stdout_buffer), daemon=True
    )
    stderr_thread = threading.Thread(
        target=consume, args=(process.stderr, stderr_buffer), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    deadline_ns = started_ns + spec.timeout_seconds * 1_000_000_000
    timed_out = False
    max_rss_bytes = 0
    while process.poll() is None:
        max_rss_bytes = max(max_rss_bytes, _read_process_rss_bytes(process.pid))
        if output_limit_exceeded.is_set():
            _stop_process(process)
            break
        if time.monotonic_ns() >= deadline_ns:
            timed_out = True
            _stop_process(process)
            break
        time.sleep(0.02)

    process.wait()
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    max_rss_bytes = max(max_rss_bytes, _read_process_rss_bytes(process.pid))
    ended_ns = time.monotonic_ns()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    user_cpu_ns = max(0, round((usage_after.ru_utime - usage_before.ru_utime) * 1_000_000_000))
    system_cpu_ns = max(
        0,
        round((usage_after.ru_stime - usage_before.ru_stime) * 1_000_000_000),
    )

    failure_reason: str | None = None
    if timed_out:
        status: LegStatus = "timed_out"
        failure_reason = f"leg exceeded {spec.timeout_seconds}-second timeout"
    elif output_limit_exceeded.is_set():
        status = "output_limit_exceeded"
        failure_reason = f"subprocess output limit exceeded {spec.max_output_bytes} bytes"
    elif process.returncode == 0:
        status = "succeeded"
    else:
        status = "failed"
        failure_reason = f"process exited with status {process.returncode}"

    if failure_reason is not None:
        stderr_buffer.extend(f"\nreference campaign: {failure_reason}\n".encode())
    (spec.output_dir / "stdout.log").write_bytes(bytes(stdout_buffer))
    (spec.output_dir / "stderr.log").write_bytes(bytes(stderr_buffer))
    return LegExecution(
        status=status,
        return_code=process.returncode,
        failure_reason=failure_reason,
        resources=ResourceMetrics(
            wall_time_ns=ended_ns - started_ns,
            user_cpu_ns=user_cpu_ns,
            system_cpu_ns=system_cpu_ns,
            max_rss_bytes=max_rss_bytes,
        ),
    )


def _new_run_directory(output_root: Path, profile: str) -> Path:
    """Create a collision-safe directory without overwriting prior reports."""
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = _utc_now().strftime("%Y%m%dT%H%M%S%fZ")
    prefix = f"{timestamp}-{profile}-{secrets.token_hex(3)}-"
    return Path(tempfile.mkdtemp(prefix=prefix, dir=output_root))


def _monte_carlo_spec(profile: str, output_dir: Path, repository_root: Path) -> LegSpec:
    samples = 16 if profile == "weekly" else 64
    max_ticks = 520
    workload = {
        "samples": samples,
        "max_ticks": max_ticks,
        "maximum_tick_evaluations": samples * max_ticks,
        "seed": _SEED,
        "objective": "carceral",
    }
    return LegSpec(
        name="monte_carlo",
        argv=[
            sys.executable,
            "-m",
            "tools.devtools.sim_analysis",
            "monte-carlo",
            "--n-samples",
            str(samples),
            "--seed",
            str(_SEED),
            "--max-ticks",
            str(max_ticks),
            "--csv-path",
            str(output_dir / "samples.csv"),
            "--manifest-path",
            str(output_dir / "manifest.json"),
            "--report-path",
            str(output_dir / "report.md"),
            "--quiet",
        ],
        output_dir=output_dir,
        timeout_seconds=900,
        max_output_bytes=_MAX_OUTPUT_BYTES,
        required=True,
        requested_workload=workload,
        expected_artifacts=(
            "samples.csv",
            "manifest.json",
            "report.md",
            "stdout.log",
            "stderr.log",
        ),
        expected_schemas={"manifest.json": "babylon.sim-analysis.monte-carlo.v1"},
        working_directory=repository_root,
    )


def _optuna_spec(profile: str, output_dir: Path, repository_root: Path) -> LegSpec:
    trials = 8 if profile == "weekly" else 16
    max_ticks = 5200
    workload = {
        "trials": trials,
        "max_ticks": max_ticks,
        "maximum_trial_tick_evaluations": trials * max_ticks,
        "best_trial_report_rerun_maximum_ticks": max_ticks,
        "seed": _SEED,
        "objective": "carceral",
        "fresh_study": True,
    }
    return LegSpec(
        name="optuna",
        argv=[
            sys.executable,
            "-m",
            "tools.devtools.sim_analysis",
            "bayesian",
            "--study-name",
            f"frozen-python-reference-{profile}",
            "--n-trials",
            str(trials),
            "--max-ticks",
            str(max_ticks),
            "--seed",
            str(_SEED),
            "--output-dir",
            str(output_dir),
        ],
        output_dir=output_dir,
        timeout_seconds=1800,
        max_output_bytes=_MAX_OUTPUT_BYTES,
        required=True,
        requested_workload=workload,
        expected_artifacts=(
            "study.sqlite3",
            "trials.csv",
            "summary.json",
            "report.md",
            "stdout.log",
            "stderr.log",
        ),
        expected_schemas={"summary.json": "babylon.sim-analysis.optuna-summary.v1"},
        working_directory=repository_root,
    )


def _sensitivity_spec(output_dir: Path, repository_root: Path) -> LegSpec:
    max_ticks = 520
    morris_evaluations = 4 * (len(_CURATED_SENSITIVITY_PARAMETERS) + 1)
    sobol_evaluations = 8 * (2 * len(_CURATED_SENSITIVITY_PARAMETERS) + 2)
    workload = {
        "method": "both",
        "parameters": list(_CURATED_SENSITIVITY_PARAMETERS),
        "morris_trajectories": 4,
        "morris_evaluations": morris_evaluations,
        "sobol_base_samples": 8,
        "sobol_evaluations": sobol_evaluations,
        "maximum_tick_evaluations": (morris_evaluations + sobol_evaluations) * max_ticks,
        "max_ticks": max_ticks,
        "seed": _SEED,
        "objective": "final-wealth",
    }
    return LegSpec(
        name="sensitivity",
        argv=[
            sys.executable,
            "-m",
            "tools.devtools.sim_analysis",
            "sensitivity",
            "--method",
            "both",
            "--param-names",
            ",".join(_CURATED_SENSITIVITY_PARAMETERS),
            "--trajectories",
            "4",
            "--samples",
            "8",
            "--max-ticks",
            str(max_ticks),
            "--seed",
            str(_SEED),
            "--objective",
            "final-wealth",
            "--output-dir",
            str(output_dir),
            "--quiet",
        ],
        output_dir=output_dir,
        timeout_seconds=900,
        max_output_bytes=_MAX_OUTPUT_BYTES,
        required=True,
        requested_workload=workload,
        expected_artifacts=("morris.json", "sobol.json", "stdout.log", "stderr.log"),
        expected_schemas={
            "morris.json": "babylon.sim-analysis.morris.v1",
            "sobol.json": "babylon.sim-analysis.sobol.v1",
        },
        working_directory=repository_root,
    )


def _artifact_schema(path: Path) -> str | None:
    if path.suffix != ".json":
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    schema = payload.get("schema") if isinstance(payload, Mapping) else None
    return schema if isinstance(schema, str) else None


def _artifact_record(path: Path, run_directory: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(run_directory).as_posix(),
        "schema": _artifact_schema(path),
        "status": "present",
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _index_artifacts(spec: LegSpec, run_directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    expected_paths = {spec.output_dir / name for name in spec.expected_artifacts}
    for path in sorted(expected_paths):
        if path.is_file():
            record = _artifact_record(path, run_directory)
            record["expected_schema"] = spec.expected_schemas.get(path.name)
            records.append(record)
        else:
            records.append(
                {
                    "path": path.relative_to(run_directory).as_posix(),
                    "schema": spec.expected_schemas.get(path.name),
                    "expected_schema": spec.expected_schemas.get(path.name),
                    "status": "missing",
                    "bytes": 0,
                    "sha256": None,
                }
            )
    for path in sorted(
        candidate for candidate in spec.output_dir.rglob("*") if candidate.is_file()
    ):
        if path not in expected_paths:
            records.append(_artifact_record(path, run_directory))
    return records


def _artifact_contract_errors(artifacts: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for artifact in artifacts:
        if artifact.get("status") != "present":
            errors.append(f"missing required artifact {artifact.get('path')}")
            continue
        expected_schema = artifact.get("expected_schema")
        if expected_schema is not None and artifact.get("schema") != expected_schema:
            errors.append(
                f"artifact {artifact.get('path')} has schema {artifact.get('schema')!r}; "
                f"expected {expected_schema!r}"
            )
    return errors


def _load_json(path: Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _actual_workload(spec: LegSpec) -> dict[str, Any]:
    if spec.name == "monte_carlo":
        manifest = _load_json(spec.output_dir / "manifest.json")
        stats = manifest.get("stats") if manifest is not None else None
        samples = stats.get("n_samples") if isinstance(stats, Mapping) else None
        trial_rows = manifest.get("samples") if manifest is not None else None
        monte_carlo_actual: dict[str, Any] = {}
        if isinstance(samples, int):
            monte_carlo_actual["recorded_samples"] = samples
        if isinstance(trial_rows, Sequence) and not isinstance(trial_rows, (str, bytes)):
            ticks = [
                row.get("ticks_survived")
                for row in trial_rows
                if isinstance(row, Mapping) and isinstance(row.get("ticks_survived"), int)
            ]
            if len(ticks) == len(trial_rows):
                monte_carlo_actual["total_ticks_survived"] = sum(ticks)
            seeds = [
                row.get("seed")
                for row in trial_rows
                if isinstance(row, Mapping) and isinstance(row.get("seed"), int)
            ]
            if len(seeds) == len(trial_rows):
                monte_carlo_actual["recorded_sample_seeds"] = seeds
        return monte_carlo_actual
    if spec.name == "optuna":
        summary = _load_json(spec.output_dir / "summary.json")
        counts = summary.get("trial_counts") if summary is not None else None
        if isinstance(counts, Mapping):
            optuna_actual = {
                "recorded_trials": counts.get("total"),
                "completed_trials": counts.get("complete"),
                "pruned_trials": counts.get("pruned"),
                "failed_trials": counts.get("failed"),
            }
            experiment = summary.get("experiment_manifest") if summary is not None else None
            if isinstance(experiment, Mapping):
                optuna_actual["simulation_seed"] = experiment.get("simulation_seed")
                sampler = experiment.get("sampler")
                if isinstance(sampler, Mapping):
                    optuna_actual["sampler_seed"] = sampler.get("seed")
            return optuna_actual
        return {}
    morris = _load_json(spec.output_dir / "morris.json")
    sobol = _load_json(spec.output_dir / "sobol.json")
    morris_trials = morris.get("trials") if morris is not None else None
    sobol_total = sobol.get("total_samples") if sobol is not None else None
    sensitivity_actual: dict[str, Any] = {}
    if isinstance(morris_trials, Sequence) and not isinstance(morris_trials, (str, bytes)):
        sensitivity_actual["morris_evaluations"] = len(morris_trials)
        morris_ticks = [
            trial.get("repro", {}).get("ticks_survived")
            for trial in morris_trials
            if isinstance(trial, Mapping) and isinstance(trial.get("repro"), Mapping)
        ]
        if len(morris_ticks) == len(morris_trials) and all(
            isinstance(ticks, int) for ticks in morris_ticks
        ):
            sensitivity_actual["morris_ticks_survived"] = sum(morris_ticks)
    if isinstance(sobol_total, int):
        sensitivity_actual["sobol_evaluations"] = sobol_total
    sobol_trials = sobol.get("trials") if sobol is not None else None
    if isinstance(sobol_trials, Sequence) and not isinstance(sobol_trials, (str, bytes)):
        sobol_ticks = [
            trial.get("repro", {}).get("ticks_survived")
            for trial in sobol_trials
            if isinstance(trial, Mapping) and isinstance(trial.get("repro"), Mapping)
        ]
        if len(sobol_ticks) == len(sobol_trials) and all(
            isinstance(ticks, int) for ticks in sobol_ticks
        ):
            sensitivity_actual["sobol_ticks_survived"] = sum(sobol_ticks)
    if sensitivity_actual:
        sensitivity_actual["total_evaluations"] = sum(
            value
            for key, value in sensitivity_actual.items()
            if key.endswith("_evaluations") and isinstance(value, int)
        )
    return sensitivity_actual


def _write_campaign_manifest(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(payload, allow_nan=False, indent=2, sort_keys=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(f"{encoded}\n", encoding="utf-8")
    temporary.replace(path)


def _failed_execution_from_exception(spec: LegSpec, exc: Exception) -> LegExecution:
    spec.output_dir.mkdir(parents=True, exist_ok=True)
    message = f"leg runner raised {type(exc).__name__}: {exc}"[:1000]
    (spec.output_dir / "stderr.log").write_text(f"{message}\n", encoding="utf-8")
    return LegExecution(
        status="failed",
        return_code=None,
        failure_reason=message,
        resources=ResourceMetrics(0, 0, 0, 0),
    )


def run_campaign(
    profile: str,
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
    *,
    repository_root: Path | None = None,
    leg_runner: Callable[[LegSpec], LegExecution] | None = None,
) -> CampaignResult:
    """Run one exact weekly or full frozen-reference campaign."""
    if profile not in {"weekly", "full"}:
        raise ValueError("profile must be weekly or full")
    root = (
        repository_root.resolve()
        if repository_root is not None
        else Path(__file__).resolve().parents[2]
    )
    output_root = output_root.resolve()
    run_directory = _new_run_directory(output_root, profile)
    manifest_path = run_directory / "campaign.json"
    started = _utc_now()
    runner = _run_leg if leg_runner is None else leg_runner

    source: dict[str, Any] = {}
    source_errors: list[str] = []
    metadata_readers: tuple[tuple[str, Callable[[], str]], ...] = (
        ("git_sha", lambda: _git_head(root)),
        ("source_tree_sha256", lambda: _source_tree_sha256(root)),
        ("uv_lock_sha256", lambda: _sha256_file(root / "uv.lock")),
    )
    for metadata_field, reader in metadata_readers:
        try:
            source[metadata_field] = reader()
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            source[metadata_field] = None
            source_errors.append(f"{metadata_field}: {type(exc).__name__}: {exc}"[:1000])

    specs = [
        _monte_carlo_spec(profile, run_directory / "monte-carlo", root),
        _optuna_spec(profile, run_directory / "optuna", root),
    ]
    if profile == "full":
        specs.append(_sensitivity_spec(run_directory / "sensitivity", root))

    requested_workloads = {spec.name: spec.requested_workload for spec in specs}
    if profile == "weekly":
        requested_workloads["sensitivity"] = {
            "status": "skipped",
            "reason": "weekly profile excludes sensitivity analysis",
        }
    manifest: dict[str, Any] = {
        "schema": _CAMPAIGN_SCHEMA,
        "campaign_id": run_directory.name,
        "profile": profile,
        "status": "running",
        "authority": _AUTHORITY,
        "game_state_authoritative": False,
        "frozen_ref": _FROZEN_REF,
        "created_at": started.isoformat(),
        "completed_at": None,
        "source": source,
        "source_errors": source_errors,
        "deterministic_seeds": {
            "monte_carlo_base_seed": _SEED,
            "optuna_simulation_seed": _SEED,
            "sensitivity_sampling_and_simulation_seed": _SEED,
        },
        "requested_workloads": requested_workloads,
        "actual_workloads": {},
        "legs": [],
    }
    _write_campaign_manifest(manifest_path, manifest)

    campaign_deadline = time.monotonic() + _CAMPAIGN_TIMEOUT_SECONDS
    for spec in specs:
        if source_errors:
            execution = LegExecution(
                status="failed",
                return_code=None,
                failure_reason="source identity could not be established",
                resources=ResourceMetrics(0, 0, 0, 0),
            )
        else:
            remaining_seconds = max(0, int(campaign_deadline - time.monotonic()))
            bounded_spec = replace(
                spec,
                timeout_seconds=min(spec.timeout_seconds, remaining_seconds),
            )
            if remaining_seconds < 1:
                execution = LegExecution(
                    status="timed_out",
                    return_code=None,
                    failure_reason="campaign exhausted its 55-minute runtime budget",
                    resources=ResourceMetrics(0, 0, 0, 0),
                )
            else:
                try:
                    execution = runner(bounded_spec)
                except Exception as exc:  # noqa: BLE001 - preserve the required partial manifest
                    execution = _failed_execution_from_exception(bounded_spec, exc)
            spec = bounded_spec

        try:
            artifacts = _index_artifacts(spec, run_directory)
            actual = _actual_workload(spec)
        except (OSError, ValueError) as exc:
            artifacts = []
            actual = {}
            execution = LegExecution(
                status="failed",
                return_code=execution.return_code,
                failure_reason=f"could not index leg artifacts: {type(exc).__name__}: {exc}"[:1000],
                resources=execution.resources,
            )
        artifact_errors = _artifact_contract_errors(artifacts)
        if execution.status == "succeeded" and artifact_errors:
            execution = LegExecution(
                status="failed",
                return_code=execution.return_code,
                failure_reason="; ".join(artifact_errors)[:1000],
                resources=execution.resources,
            )
        manifest["actual_workloads"][spec.name] = actual
        manifest["legs"].append(
            {
                "name": spec.name,
                "argv": spec.argv,
                "required": spec.required,
                "status": execution.status,
                "return_code": execution.return_code,
                "failure_reason": execution.failure_reason,
                "skip_reason": None,
                "timeout_seconds": spec.timeout_seconds,
                "max_output_bytes": spec.max_output_bytes,
                "requested_workload": spec.requested_workload,
                "actual_workload": actual,
                "resources": execution.resources.as_dict(),
                "artifacts": artifacts,
            }
        )
        _write_campaign_manifest(manifest_path, manifest)

    if profile == "weekly":
        skipped_workload = requested_workloads["sensitivity"]
        manifest["actual_workloads"]["sensitivity"] = {}
        manifest["legs"].append(
            {
                "name": "sensitivity",
                "argv": [],
                "required": False,
                "status": "skipped",
                "return_code": None,
                "failure_reason": None,
                "skip_reason": skipped_workload["reason"],
                "timeout_seconds": 0,
                "max_output_bytes": 0,
                "requested_workload": skipped_workload,
                "actual_workload": {},
                "resources": ResourceMetrics(0, 0, 0, 0).as_dict(),
                "artifacts": [],
            }
        )

    required_failed = any(
        leg["required"] and leg["status"] != "succeeded" for leg in manifest["legs"]
    )
    manifest["status"] = "failed" if source_errors or required_failed else "succeeded"
    manifest["completed_at"] = _utc_now().isoformat()
    _write_campaign_manifest(manifest_path, manifest)
    return CampaignResult(
        run_directory=run_directory,
        manifest_path=manifest_path,
        exit_code=1 if manifest["status"] == "failed" else 0,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded, non-authoritative frozen-Python reference analysis."
    )
    parser.add_argument(
        "--profile",
        choices=("weekly", "full"),
        default="weekly",
        help="Exact campaign workload profile. Default: weekly.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=_DEFAULT_OUTPUT_ROOT,
        help="Parent directory for collision-safe campaign reports.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_campaign(args.profile, output_root=args.output_root)
    print(result.manifest_path)
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover - module execution wrapper
    sys.exit(main())


__all__ = [
    "CampaignResult",
    "LegExecution",
    "LegSpec",
    "ResourceMetrics",
    "build_parser",
    "main",
    "run_campaign",
]
