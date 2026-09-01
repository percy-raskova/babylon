#!/usr/bin/env python3
"""Run the Rust simulation and retain a bounded, validated report bundle."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Final, cast
from uuid import uuid4

TICK_REPORT_SCHEMA: Final = "babylon.simulation.tick-report.v1"
SUMMARY_SCHEMA: Final = "babylon.simulation.run-summary.v1"
VALIDATION_EXIT_CODE: Final = 2
MAX_TICKS: Final = 10_000
MAX_JSONL_BYTES: Final = 256 * 1024 * 1024
MAX_JSONL_ROW_BYTES: Final = 4 * 1024 * 1024
MAX_STDOUT_BYTES: Final = 2 * 1024 * 1024
MAX_STDERR_BYTES: Final = 2 * 1024 * 1024
RUNTIME_TIMEOUT_SECONDS: Final = 15 * 60.0
CAPTURE_CHUNK_BYTES: Final = 64 * 1024
PROCESS_POLL_SECONDS: Final = 0.02
PROCESS_JOIN_SECONDS: Final = 2.0

COMMIT_DISPOSITIONS: Final = frozenset({"committed", "reconciled_after_ambiguous_commit"})
TOP_LEVEL_FIELDS: Final = frozenset(
    {
        "schema",
        "resolve_tick",
        "commit_disposition",
        "graph",
        "world",
        "rules",
        "events",
        "audit_receipts",
        "material_rows",
        "tick_content_hash",
    }
)
HASH_PAIR_FIELDS: Final = frozenset({"before_sha256", "after_sha256"})
RULES_FIELDS: Final = frozenset({"considered", "fired", "per_rule"})
PER_RULE_FIELDS: Final = frozenset({"rule_id", "considered", "fired"})
EVENT_FIELDS: Final = frozenset({"count", "digest_sha256"})
AUDIT_RECEIPT_FIELDS: Final = frozenset({"count"})
MATERIAL_ROW_FIELDS: Final = frozenset({"count", "digest_sha256"})
LOWER_HEX_DIGEST: Final = re.compile(r"[0-9a-f]{64}")

CSV_COLUMNS: Final = (
    "resolve_tick",
    "commit_disposition",
    "graph_before_sha256",
    "graph_after_sha256",
    "world_before_sha256",
    "world_after_sha256",
    "rules_considered",
    "rules_fired",
    "event_count",
    "event_digest_sha256",
    "audit_receipt_count",
    "material_row_count",
    "material_row_digest_sha256",
    "tick_content_hash",
)


class ReportError(RuntimeError):
    """Raised when a report run cannot safely start."""


class JsonlValidationError(ReportError):
    """Raised when the runtime report is missing or violates its wire contract."""


class _DuplicateJsonField(ValueError):
    """Raised by the JSON object hook for a duplicate member name."""

    def __init__(self, field_name: str) -> None:
        super().__init__(field_name)
        self.field_name = field_name


@dataclass(frozen=True)
class RunResult:
    """Completed wrapper result, including its durable artifact location."""

    artifact_dir: Path
    summary: dict[str, object]
    exit_code: int
    error: str | None = None


@dataclass
class _StreamCapture:
    label: str
    limit: int
    content: bytearray = field(default_factory=bytearray)
    exceeded: bool = False
    error: OSError | None = None


@dataclass(frozen=True)
class _ProcessOutcome:
    returncode: int
    stdout: bytes
    stderr: bytes
    wrapper_status: str | None = None
    wrapper_error: str | None = None


def _positive_ticks(value: str) -> int:
    try:
        ticks = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("ticks must be an integer") from error
    if ticks < 1 or ticks > MAX_TICKS:
        raise argparse.ArgumentTypeError(f"ticks must be between 1 and {MAX_TICKS}")
    return ticks


def _positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout must be a number") from error
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive finite number")
    return timeout


def _validate_runtime(runtime: Path) -> Path:
    try:
        resolved = runtime.resolve(strict=True)
    except OSError as error:
        raise ReportError(f"runtime does not exist: {runtime}") from error
    if not resolved.is_file():
        raise ReportError(f"runtime is not a file: {runtime}")
    if not os.access(resolved, os.X_OK):
        raise ReportError(f"runtime is not executable: {runtime}")
    return resolved


def _create_artifact_dir(output_root: Path) -> Path:
    try:
        root = output_root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise ReportError(f"output root is not a directory: {output_root}")
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ-")
        return Path(tempfile.mkdtemp(prefix=timestamp, dir=root))
    except ReportError:
        raise
    except OSError as error:
        raise ReportError(f"cannot create output root: {output_root}") from error


def _child_environment() -> tuple[dict[str, str], str]:
    environment = dict(os.environ)
    campaign_id = str(uuid4())
    environment["BABYLON_CAMPAIGN_ID"] = campaign_id
    return environment, campaign_id


def _redacted_environment_values(environment: Mapping[str, str]) -> tuple[bytes, ...]:
    secrets: set[bytes] = set()
    for key, value in environment.items():
        upper_key = key.upper()
        is_connection_secret = (
            "DSN" in upper_key
            or "DATABASE_URL" in upper_key
            or "PASSWORD" in upper_key
            or "PASSWD" in upper_key
        )
        if not is_connection_secret or not value:
            continue
        secrets.add(value.encode(errors="surrogateescape"))
    return tuple(sorted(secrets, key=len, reverse=True))


def _redact_secrets(content: bytes, secrets: Sequence[bytes]) -> bytes:
    redacted = content
    for secret in secrets:
        redacted = redacted.replace(secret, b"[REDACTED]")
    return redacted


def _write_process_logs(
    artifact_dir: Path,
    *,
    stdout: bytes,
    stderr: bytes,
    secrets: Sequence[bytes],
) -> None:
    safe_stdout = _redact_secrets(stdout, secrets)[:MAX_STDOUT_BYTES]
    safe_stderr = _redact_secrets(stderr, secrets)[:MAX_STDERR_BYTES]
    (artifact_dir / "stdout.txt").write_bytes(safe_stdout)
    (artifact_dir / "stderr.txt").write_bytes(safe_stderr)


def _capture_pipe(
    pipe: BinaryIO,
    state: _StreamCapture,
    attention: threading.Event,
) -> None:
    try:
        while True:
            chunk = os.read(pipe.fileno(), CAPTURE_CHUNK_BYTES)
            if not chunk:
                break
            remaining = state.limit - len(state.content)
            if remaining > 0:
                state.content.extend(chunk[:remaining])
            if len(chunk) > remaining:
                state.exceeded = True
                attention.set()
    except OSError as error:
        state.error = error
        attention.set()
    finally:
        pipe.close()


def _kill_and_reap(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=PROCESS_JOIN_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _bounded_process_run(
    argv: Sequence[str],
    *,
    environment: Mapping[str, str],
    timeout_seconds: float,
) -> _ProcessOutcome:
    process = subprocess.Popen(
        list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(environment),
    )
    if process.stdout is None or process.stderr is None:
        _kill_and_reap(process)
        raise ReportError("runtime capture pipes were not created")

    stdout = _StreamCapture("stdout", MAX_STDOUT_BYTES)
    stderr = _StreamCapture("stderr", MAX_STDERR_BYTES)
    attention = threading.Event()
    threads = [
        threading.Thread(
            target=_capture_pipe,
            args=(process.stdout, stdout, attention),
            daemon=True,
        ),
        threading.Thread(
            target=_capture_pipe,
            args=(process.stderr, stderr, attention),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    deadline = time.monotonic() + timeout_seconds
    wrapper_status: str | None = None
    wrapper_error: str | None = None
    while process.poll() is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            wrapper_status = "runtime_timed_out"
            rendered_timeout = f"{timeout_seconds:g}"
            wrapper_error = f"runtime exceeded the {rendered_timeout}-second timeout"
            _kill_and_reap(process)
            break
        if attention.wait(timeout=min(PROCESS_POLL_SECONDS, remaining)):
            if stdout.exceeded:
                wrapper_status = "runtime_output_limit_exceeded"
                wrapper_error = f"runtime stdout exceeded the {stdout.limit}-byte capture bound"
            elif stderr.exceeded:
                wrapper_status = "runtime_output_limit_exceeded"
                wrapper_error = f"runtime stderr exceeded the {stderr.limit}-byte capture bound"
            elif stdout.error is not None:
                wrapper_status = "runtime_capture_failed"
                wrapper_error = "runtime stdout capture failed"
            elif stderr.error is not None:
                wrapper_status = "runtime_capture_failed"
                wrapper_error = "runtime stderr capture failed"
            if wrapper_status is not None:
                _kill_and_reap(process)
                break
            attention.clear()

    if process.poll() is None:
        _kill_and_reap(process)
    for thread in threads:
        thread.join(timeout=PROCESS_JOIN_SECONDS)

    if wrapper_status is None:
        if stdout.exceeded:
            wrapper_status = "runtime_output_limit_exceeded"
            wrapper_error = f"runtime stdout exceeded the {stdout.limit}-byte capture bound"
        elif stderr.exceeded:
            wrapper_status = "runtime_output_limit_exceeded"
            wrapper_error = f"runtime stderr exceeded the {stderr.limit}-byte capture bound"
        elif stdout.error is not None:
            wrapper_status = "runtime_capture_failed"
            wrapper_error = "runtime stdout capture failed"
        elif stderr.error is not None:
            wrapper_status = "runtime_capture_failed"
            wrapper_error = "runtime stderr capture failed"
        elif any(thread.is_alive() for thread in threads):
            wrapper_status = "runtime_capture_failed"
            wrapper_error = "runtime capture did not close after process exit"

    returncode = process.returncode
    if returncode is None:
        _kill_and_reap(process)
        returncode = process.returncode
    if returncode is None:
        raise ReportError("runtime process could not be reaped")
    return _ProcessOutcome(
        returncode=returncode,
        stdout=bytes(stdout.content),
        stderr=bytes(stderr.content),
        wrapper_status=wrapper_status,
        wrapper_error=wrapper_error,
    )


def _duplicate_rejecting_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonField(key)
        result[key] = value
    return result


def _require_fields(
    value: object,
    expected: frozenset[str],
    *,
    line_number: int,
    location: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise JsonlValidationError(f"line {line_number} {location} must be a JSON object")
    actual = set(value)
    if actual != expected:
        details: list[str] = []
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected {', '.join(unexpected)}")
        raise JsonlValidationError(
            f"line {line_number} {location} fields differ ({'; '.join(details)})"
        )
    return value


def _require_nonnegative_integer(
    value: object,
    *,
    line_number: int,
    location: str,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise JsonlValidationError(f"line {line_number} {location} must be a nonnegative integer")
    return value


def _require_digest(
    value: object,
    *,
    line_number: int,
    location: str,
) -> str:
    if not isinstance(value, str) or LOWER_HEX_DIGEST.fullmatch(value) is None:
        raise JsonlValidationError(
            f"line {line_number} {location} must be a lowercase 64-hex digest"
        )
    return value


def _validate_hash_pair(
    value: object,
    *,
    line_number: int,
    location: str,
) -> None:
    pair = _require_fields(
        value,
        HASH_PAIR_FIELDS,
        line_number=line_number,
        location=location,
    )
    _require_digest(
        pair["before_sha256"],
        line_number=line_number,
        location=f"{location}.before_sha256",
    )
    _require_digest(
        pair["after_sha256"],
        line_number=line_number,
        location=f"{location}.after_sha256",
    )


def _validate_rules(value: object, *, line_number: int) -> None:
    rules = _require_fields(
        value,
        RULES_FIELDS,
        line_number=line_number,
        location="rules",
    )
    considered = _require_nonnegative_integer(
        rules["considered"],
        line_number=line_number,
        location="rules.considered",
    )
    fired = _require_nonnegative_integer(
        rules["fired"],
        line_number=line_number,
        location="rules.fired",
    )
    if considered < fired:
        raise JsonlValidationError(f"line {line_number} rules.considered must be >= rules.fired")

    per_rule = rules["per_rule"]
    if not isinstance(per_rule, list):
        raise JsonlValidationError(f"line {line_number} rules.per_rule must be a list")
    considered_sum = 0
    fired_sum = 0
    seen_rule_ids: set[str] = set()
    for index, candidate in enumerate(per_rule):
        location = f"rules.per_rule[{index}]"
        rule = _require_fields(
            candidate,
            PER_RULE_FIELDS,
            line_number=line_number,
            location=location,
        )
        rule_id = rule["rule_id"]
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise JsonlValidationError(
                f"line {line_number} {location} must have a nonempty rule_id"
            )
        if rule_id in seen_rule_ids:
            raise JsonlValidationError(
                f"line {line_number} {location} duplicates rule_id {rule_id!r}"
            )
        seen_rule_ids.add(rule_id)
        rule_considered = _require_nonnegative_integer(
            rule["considered"],
            line_number=line_number,
            location=f"{location}.considered",
        )
        rule_fired = _require_nonnegative_integer(
            rule["fired"],
            line_number=line_number,
            location=f"{location}.fired",
        )
        if rule_considered < rule_fired:
            raise JsonlValidationError(f"line {line_number} {location} considered must be >= fired")
        considered_sum += rule_considered
        fired_sum += rule_fired
    if considered_sum != considered:
        raise JsonlValidationError(
            f"line {line_number} per-rule considered sum {considered_sum} "
            f"does not equal rules.considered {considered}"
        )
    if fired_sum != fired:
        raise JsonlValidationError(
            f"line {line_number} per-rule fired sum {fired_sum} does not equal rules.fired {fired}"
        )


def _validate_tick_row(
    candidate: object,
    *,
    line_number: int,
    previous_tick: int | None,
) -> dict[str, object]:
    row = _require_fields(
        candidate,
        TOP_LEVEL_FIELDS,
        line_number=line_number,
        location="top-level",
    )
    if row["schema"] != TICK_REPORT_SCHEMA:
        raise JsonlValidationError(
            f"line {line_number} has schema {row['schema']!r}; expected {TICK_REPORT_SCHEMA!r}"
        )
    resolve_tick = row["resolve_tick"]
    if not isinstance(resolve_tick, int) or isinstance(resolve_tick, bool) or resolve_tick < 1:
        raise JsonlValidationError(f"line {line_number} must have a positive resolve_tick")
    if previous_tick is not None and resolve_tick != previous_tick + 1:
        raise JsonlValidationError(
            f"line {line_number} expected contiguous resolve_tick "
            f"{previous_tick + 1}, got {resolve_tick}"
        )
    disposition = row["commit_disposition"]
    if not isinstance(disposition, str) or disposition not in COMMIT_DISPOSITIONS:
        raise JsonlValidationError(
            f"line {line_number} has invalid commit_disposition {disposition!r}"
        )

    _validate_hash_pair(row["graph"], line_number=line_number, location="graph")
    _validate_hash_pair(row["world"], line_number=line_number, location="world")
    _validate_rules(row["rules"], line_number=line_number)

    events = _require_fields(
        row["events"],
        EVENT_FIELDS,
        line_number=line_number,
        location="events",
    )
    _require_nonnegative_integer(events["count"], line_number=line_number, location="events.count")
    _require_digest(
        events["digest_sha256"],
        line_number=line_number,
        location="events.digest_sha256",
    )

    receipts = _require_fields(
        row["audit_receipts"],
        AUDIT_RECEIPT_FIELDS,
        line_number=line_number,
        location="audit_receipts",
    )
    _require_nonnegative_integer(
        receipts["count"],
        line_number=line_number,
        location="audit_receipts.count",
    )

    material_rows = _require_fields(
        row["material_rows"],
        MATERIAL_ROW_FIELDS,
        line_number=line_number,
        location="material_rows",
    )
    _require_nonnegative_integer(
        material_rows["count"],
        line_number=line_number,
        location="material_rows.count",
    )
    _require_digest(
        material_rows["digest_sha256"],
        line_number=line_number,
        location="material_rows.digest_sha256",
    )
    _require_digest(
        row["tick_content_hash"],
        line_number=line_number,
        location="tick_content_hash",
    )
    return row


def _validate_durable_hash_continuity(
    previous_row: Mapping[str, object],
    row: Mapping[str, object],
    *,
    line_number: int,
) -> None:
    previous_disposition = previous_row["commit_disposition"]
    disposition = row["commit_disposition"]
    if previous_disposition not in COMMIT_DISPOSITIONS or disposition not in COMMIT_DISPOSITIONS:
        return

    for state_name in ("graph", "world"):
        previous_state = cast("Mapping[str, object]", previous_row[state_name])
        state = cast("Mapping[str, object]", row[state_name])
        if state["before_sha256"] != previous_state["after_sha256"]:
            raise JsonlValidationError(
                f"line {line_number} {state_name}.before_sha256 does not equal "
                f"the previous durable row's {state_name}.after_sha256"
            )


def _validate_jsonl(
    path: Path,
    *,
    expected_rows: int | None = None,
    maximum_rows: int | None = None,
    first_resolve_tick: int | None = None,
) -> list[dict[str, object]]:
    try:
        size = path.stat().st_size
    except FileNotFoundError as error:
        raise JsonlValidationError("runtime did not create ticks.jsonl") from error
    except OSError as error:
        raise JsonlValidationError("cannot inspect ticks.jsonl") from error
    if not path.is_file():
        raise JsonlValidationError("ticks.jsonl is not a regular file")
    if size > MAX_JSONL_BYTES:
        raise JsonlValidationError(
            f"ticks.jsonl exceeds the {MAX_JSONL_BYTES}-byte validation bound"
        )

    rows: list[dict[str, object]] = []
    previous_tick: int | None = None
    previous_row: dict[str, object] | None = None
    try:
        with path.open("rb") as report_file:
            line_number = 0
            while raw_line := report_file.readline(MAX_JSONL_ROW_BYTES + 1):
                line_number += 1
                if len(raw_line) > MAX_JSONL_ROW_BYTES:
                    raise JsonlValidationError(
                        f"line {line_number} exceeds the {MAX_JSONL_ROW_BYTES}-byte bound"
                    )
                next_row_count = len(rows) + 1
                if expected_rows is not None and next_row_count > expected_rows:
                    raise JsonlValidationError(
                        f"ticks.jsonl exceeds expected row count {expected_rows}"
                    )
                if maximum_rows is not None and next_row_count > maximum_rows:
                    raise JsonlValidationError(
                        f"ticks.jsonl exceeds maximum row count {maximum_rows}"
                    )
                if not raw_line.strip():
                    raise JsonlValidationError(f"line {line_number} is blank")
                try:
                    decoded = raw_line.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise JsonlValidationError(f"line {line_number} is not UTF-8") from error
                try:
                    candidate = json.loads(
                        decoded,
                        object_pairs_hook=_duplicate_rejecting_object,
                    )
                except _DuplicateJsonField as error:
                    raise JsonlValidationError(
                        f"line {line_number} contains duplicate JSON field {error.field_name!r}"
                    ) from error
                except json.JSONDecodeError as error:
                    raise JsonlValidationError(
                        f"line {line_number} is not valid JSON: {error.msg}"
                    ) from error
                row = _validate_tick_row(
                    candidate,
                    line_number=line_number,
                    previous_tick=previous_tick,
                )
                current_tick = cast("int", row["resolve_tick"])
                if (
                    previous_tick is None
                    and first_resolve_tick is not None
                    and current_tick != first_resolve_tick
                ):
                    raise JsonlValidationError(
                        "ticks.jsonl must start at resolve_tick "
                        f"{first_resolve_tick}, got {current_tick}"
                    )
                if previous_row is not None:
                    _validate_durable_hash_continuity(
                        previous_row,
                        row,
                        line_number=line_number,
                    )
                previous_tick = current_tick
                previous_row = row
                rows.append(row)
    except JsonlValidationError:
        raise
    except OSError as error:
        raise JsonlValidationError("cannot read ticks.jsonl") from error

    if not rows:
        raise JsonlValidationError("ticks.jsonl contains no tick reports")
    if expected_rows is not None and len(rows) != expected_rows:
        raise JsonlValidationError(
            f"ticks.jsonl reports {len(rows)} rows; expected exactly {expected_rows}"
        )
    return rows


def _nested_mapping(row: Mapping[str, object], key: str) -> Mapping[str, object]:
    return cast("Mapping[str, object]", row[key])


def _evidence_summary(
    rows: Sequence[Mapping[str, object]],
    *,
    campaign_id: str,
    ticks_requested: int,
    status: str,
    runtime_exit_code: int,
    error: str | None = None,
) -> dict[str, object]:
    final = rows[-1]
    final_graph = _nested_mapping(final, "graph")
    final_world = _nested_mapping(final, "world")
    totals = {
        "rules_considered": sum(
            cast("int", _nested_mapping(row, "rules")["considered"]) for row in rows
        ),
        "rules_fired": sum(cast("int", _nested_mapping(row, "rules")["fired"]) for row in rows),
        "events": sum(cast("int", _nested_mapping(row, "events")["count"]) for row in rows),
        "audit_receipts": sum(
            cast("int", _nested_mapping(row, "audit_receipts")["count"]) for row in rows
        ),
        "material_rows": sum(
            cast("int", _nested_mapping(row, "material_rows")["count"]) for row in rows
        ),
    }
    summary: dict[str, object] = {
        "schema": SUMMARY_SCHEMA,
        "status": status,
        "campaign_id": campaign_id,
        "runtime_exit_code": runtime_exit_code,
        "ticks_requested": ticks_requested,
        "ticks_reported": len(rows),
        "first_resolve_tick": rows[0]["resolve_tick"],
        "last_resolve_tick": final["resolve_tick"],
        "totals": totals,
        "final": {
            "graph_sha256": final_graph["after_sha256"],
            "world_sha256": final_world["after_sha256"],
            "tick_content_hash": final["tick_content_hash"],
        },
    }
    if error is not None:
        summary["error"] = error
    return summary


def _failure_summary(
    *,
    status: str,
    campaign_id: str,
    ticks_requested: int,
    runtime_exit_code: int | None,
    error: str,
    report_validation_error: str | None = None,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "schema": SUMMARY_SCHEMA,
        "status": status,
        "campaign_id": campaign_id,
        "runtime_exit_code": runtime_exit_code,
        "ticks_requested": ticks_requested,
        "ticks_reported": 0,
        "error": error,
    }
    if report_validation_error is not None:
        summary["report_validation_error"] = report_validation_error
    return summary


def render_summary(summary: Mapping[str, object]) -> str:
    lines = [
        f"status: {summary['status']}",
        f"campaign: {summary['campaign_id']}",
        f"ticks: {summary['ticks_reported']} reported / {summary['ticks_requested']} requested",
    ]
    if cast("int", summary["ticks_reported"]) > 0:
        lines.append(
            f"resolve ticks: {summary['first_resolve_tick']}..{summary['last_resolve_tick']}"
        )
        totals = cast("Mapping[str, object]", summary["totals"])
        final = cast("Mapping[str, object]", summary["final"])
        lines.extend(
            [
                f"rules: {totals['rules_fired']} fired / {totals['rules_considered']} considered",
                (
                    f"events: {totals['events']}; "
                    f"audit receipts: {totals['audit_receipts']}; "
                    f"material rows: {totals['material_rows']}"
                ),
                f"final graph: {final['graph_sha256']}",
                f"final world: {final['world_sha256']}",
                f"tick content hash: {final['tick_content_hash']}",
            ]
        )
    if "error" in summary:
        lines.append(f"error: {summary['error']}")
    if "report_validation_error" in summary:
        lines.append(f"report validation: {summary['report_validation_error']}")
    return "\n".join(lines) + "\n"


def _write_summary(artifact_dir: Path, summary: Mapping[str, object]) -> None:
    json_text = json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (artifact_dir / "summary.json").write_text(json_text, encoding="utf-8")
    (artifact_dir / "summary.txt").write_text(render_summary(summary), encoding="utf-8")


def _csv_row(row: Mapping[str, object]) -> dict[str, object]:
    graph = _nested_mapping(row, "graph")
    world = _nested_mapping(row, "world")
    rules = _nested_mapping(row, "rules")
    events = _nested_mapping(row, "events")
    receipts = _nested_mapping(row, "audit_receipts")
    material_rows = _nested_mapping(row, "material_rows")
    return {
        "resolve_tick": row["resolve_tick"],
        "commit_disposition": row["commit_disposition"],
        "graph_before_sha256": graph["before_sha256"],
        "graph_after_sha256": graph["after_sha256"],
        "world_before_sha256": world["before_sha256"],
        "world_after_sha256": world["after_sha256"],
        "rules_considered": rules["considered"],
        "rules_fired": rules["fired"],
        "event_count": events["count"],
        "event_digest_sha256": events["digest_sha256"],
        "audit_receipt_count": receipts["count"],
        "material_row_count": material_rows["count"],
        "material_row_digest_sha256": material_rows["digest_sha256"],
        "tick_content_hash": row["tick_content_hash"],
    }


def _write_csv(
    artifact_dir: Path,
    rows: Sequence[Mapping[str, object]],
) -> None:
    with (artifact_dir / "ticks.csv").open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_csv_row(row))


def _finalize_wrapper_failure(
    *,
    artifact_dir: Path,
    report_path: Path,
    campaign_id: str,
    ticks: int,
    outcome: _ProcessOutcome,
) -> RunResult:
    message = outcome.wrapper_error or "runtime wrapper failed"
    if report_path.exists():
        try:
            rows = _validate_jsonl(
                report_path,
                maximum_rows=ticks,
                first_resolve_tick=1,
            )
        except JsonlValidationError as error:
            validation_message = f"report validation failed: {error}"
            combined = f"{message}; {validation_message}"
            summary = _failure_summary(
                status=outcome.wrapper_status or "runtime_wrapper_failed",
                campaign_id=campaign_id,
                ticks_requested=ticks,
                runtime_exit_code=outcome.returncode,
                error=message,
                report_validation_error=validation_message,
            )
            _write_summary(artifact_dir, summary)
            return RunResult(
                artifact_dir,
                summary,
                VALIDATION_EXIT_CODE,
                combined,
            )

        summary = _evidence_summary(
            rows,
            campaign_id=campaign_id,
            ticks_requested=ticks,
            status=outcome.wrapper_status or "runtime_wrapper_failed",
            runtime_exit_code=outcome.returncode,
            error=message,
        )
        _write_csv(artifact_dir, rows)
        _write_summary(artifact_dir, summary)
        return RunResult(
            artifact_dir,
            summary,
            VALIDATION_EXIT_CODE,
            message,
        )

    summary = _failure_summary(
        status=outcome.wrapper_status or "runtime_wrapper_failed",
        campaign_id=campaign_id,
        ticks_requested=ticks,
        runtime_exit_code=outcome.returncode,
        error=message,
    )
    _write_summary(artifact_dir, summary)
    return RunResult(
        artifact_dir,
        summary,
        VALIDATION_EXIT_CODE,
        message,
    )


def _finalize_runtime_failure(
    *,
    artifact_dir: Path,
    report_path: Path,
    campaign_id: str,
    ticks: int,
    runtime_exit_code: int,
) -> RunResult:
    message = f"runtime exited with status {runtime_exit_code}"
    if not report_path.exists():
        summary = _failure_summary(
            status="runtime_failed",
            campaign_id=campaign_id,
            ticks_requested=ticks,
            runtime_exit_code=runtime_exit_code,
            error=message,
        )
        _write_summary(artifact_dir, summary)
        return RunResult(artifact_dir, summary, runtime_exit_code, message)

    try:
        rows = _validate_jsonl(
            report_path,
            maximum_rows=ticks,
            first_resolve_tick=1,
        )
    except JsonlValidationError as error:
        validation_message = f"report validation failed: {error}"
        combined = f"{message}; {validation_message}"
        summary = _failure_summary(
            status="runtime_failed",
            campaign_id=campaign_id,
            ticks_requested=ticks,
            runtime_exit_code=runtime_exit_code,
            error=message,
            report_validation_error=validation_message,
        )
        _write_summary(artifact_dir, summary)
        return RunResult(artifact_dir, summary, runtime_exit_code, combined)

    summary = _evidence_summary(
        rows,
        campaign_id=campaign_id,
        ticks_requested=ticks,
        status="runtime_failed",
        runtime_exit_code=runtime_exit_code,
        error=message,
    )
    _write_csv(artifact_dir, rows)
    _write_summary(artifact_dir, summary)
    return RunResult(artifact_dir, summary, runtime_exit_code, message)


def run_report(
    *,
    runtime: Path,
    ticks: int,
    output_root: Path,
    timeout_seconds: float | None = None,
) -> RunResult:
    """Run one fresh-campaign simulation and return its durable wrapper result."""
    if ticks < 1 or ticks > MAX_TICKS:
        raise ReportError(f"ticks must be between 1 and {MAX_TICKS}")
    effective_timeout = RUNTIME_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    if not math.isfinite(effective_timeout) or effective_timeout <= 0:
        raise ReportError("runtime timeout must be a positive finite number")

    runtime_path = _validate_runtime(runtime)
    child_environment, campaign_id = _child_environment()
    artifact_dir = _create_artifact_dir(output_root)
    report_path = artifact_dir / "ticks.jsonl"
    argv = [
        str(runtime_path),
        "run",
        "--ticks",
        str(ticks),
        "--report-jsonl",
        str(report_path),
    ]
    secrets = _redacted_environment_values(child_environment)
    try:
        outcome = _bounded_process_run(
            argv,
            environment=child_environment,
            timeout_seconds=effective_timeout,
        )
    except OSError as error:
        message = f"could not launch runtime: {error.strerror or type(error).__name__}"
        _write_process_logs(
            artifact_dir,
            stdout=b"",
            stderr=b"",
            secrets=secrets,
        )
        summary = _failure_summary(
            status="launch_failed",
            campaign_id=campaign_id,
            ticks_requested=ticks,
            runtime_exit_code=None,
            error=message,
        )
        _write_summary(artifact_dir, summary)
        return RunResult(
            artifact_dir,
            summary,
            VALIDATION_EXIT_CODE,
            message,
        )

    _write_process_logs(
        artifact_dir,
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        secrets=secrets,
    )
    if outcome.wrapper_status is not None:
        return _finalize_wrapper_failure(
            artifact_dir=artifact_dir,
            report_path=report_path,
            campaign_id=campaign_id,
            ticks=ticks,
            outcome=outcome,
        )
    if outcome.returncode != 0:
        return _finalize_runtime_failure(
            artifact_dir=artifact_dir,
            report_path=report_path,
            campaign_id=campaign_id,
            ticks=ticks,
            runtime_exit_code=outcome.returncode,
        )

    try:
        rows = _validate_jsonl(
            report_path,
            expected_rows=ticks,
            first_resolve_tick=1,
        )
    except JsonlValidationError as error:
        message = f"report validation failed: {error}"
        summary = _failure_summary(
            status="validation_failed",
            campaign_id=campaign_id,
            ticks_requested=ticks,
            runtime_exit_code=0,
            error=message,
        )
        _write_summary(artifact_dir, summary)
        return RunResult(
            artifact_dir,
            summary,
            VALIDATION_EXIT_CODE,
            message,
        )

    summary = _evidence_summary(
        rows,
        campaign_id=campaign_id,
        ticks_requested=ticks,
        status="ok",
        runtime_exit_code=0,
    )
    _write_csv(artifact_dir, rows)
    _write_summary(artifact_dir, summary)
    return RunResult(artifact_dir, summary, 0)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run babylon-runtime and retain a bounded, validated simulation report bundle."
        ),
        epilog=(
            "The wrapper always supplies a fresh child-only BABYLON_CAMPAIGN_ID; "
            "an inherited value is ignored so report runs cannot resume an old campaign."
        ),
    )
    parser.add_argument(
        "--runtime",
        required=True,
        type=Path,
        help="babylon-runtime executable",
    )
    parser.add_argument(
        "--ticks",
        required=True,
        type=_positive_ticks,
        help=(f"count of ticks to execute for the fresh campaign (maximum {MAX_TICKS})"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "reports" / "sim-runs",
        help="parent directory for collision-safe run artifacts",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=_positive_timeout,
        default=RUNTIME_TIMEOUT_SECONDS,
        help="wall-clock runtime timeout in seconds",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = run_report(
            runtime=arguments.runtime,
            ticks=arguments.ticks,
            output_root=arguments.output_root,
            timeout_seconds=arguments.timeout_seconds,
        )
    except ReportError as error:
        print(f"sim-report: {error}", file=sys.stderr)
        return VALIDATION_EXIT_CODE

    print(result.artifact_dir)
    print(render_summary(result.summary), end="")
    if result.error is not None:
        print(f"sim-report: {result.error}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
