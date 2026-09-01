"""Contracts for the stdlib-only Rust simulation report wrapper."""

from __future__ import annotations

import argparse
import copy
import json
import os
import uuid
from pathlib import Path

import pytest
from tools.devtools import sim_report

pytestmark = pytest.mark.unit

CAMPAIGN_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def _digest(value: int) -> str:
    return f"{value:064x}"


def _valid_row(resolve_tick: int) -> dict[str, object]:
    return {
        "schema": "babylon.simulation.tick-report.v1",
        "resolve_tick": resolve_tick,
        "commit_disposition": "committed",
        "graph": {
            "before_sha256": _digest(resolve_tick),
            "after_sha256": _digest(resolve_tick + 1),
        },
        "world": {
            "before_sha256": _digest(resolve_tick + 100),
            "after_sha256": _digest(resolve_tick + 101),
        },
        "rules": {
            "considered": 3,
            "fired": 1,
            "per_rule": [
                {"rule_id": "phase/example-a", "considered": 2, "fired": 1},
                {"rule_id": "phase/example-b", "considered": 1, "fired": 0},
            ],
        },
        "events": {"count": 2, "digest_sha256": _digest(resolve_tick + 200)},
        "audit_receipts": {"count": 2},
        "material_rows": {
            "count": 3,
            "digest_sha256": _digest(resolve_tick + 300),
        },
        "tick_content_hash": _digest(resolve_tick + 400),
    }


def _write_runtime(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _configured_runtime(
    path: Path,
    *,
    rows: list[dict[str, object]] | None,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    stdout_env: list[str] | None = None,
    stderr_env: list[str] | None = None,
    capture_campaign: bool = False,
    print_campaign: bool = False,
    sleep_seconds: float = 0.0,
    marker_path: Path | None = None,
) -> Path:
    config = {
        "rows": rows,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_env": stdout_env or [],
        "stderr_env": stderr_env or [],
        "capture_campaign": capture_campaign,
        "print_campaign": print_campaign,
        "sleep_seconds": sleep_seconds,
        "marker_path": str(marker_path) if marker_path is not None else None,
    }
    _write_runtime(
        path,
        """\
import json
import os
import pathlib
import sys
import time

assert sys.argv[1] == "run"
assert sys.argv[2] == "--ticks"
assert sys.argv[4] == "--report-jsonl"
report_path = pathlib.Path(sys.argv[5])
config = json.loads(pathlib.Path(sys.argv[0] + ".config.json").read_text(encoding="utf-8"))
if config["rows"] is not None:
    report_path.write_text(
        "".join(json.dumps(row) + "\\n" for row in config["rows"]),
        encoding="utf-8",
    )
campaign_id = os.environ["BABYLON_CAMPAIGN_ID"]
if config["capture_campaign"]:
    capture_path = pathlib.Path(os.environ["CAMPAIGN_CAPTURE_PATH"])
    with capture_path.open("a", encoding="utf-8") as capture:
        capture.write(campaign_id + "\\n")
sys.stdout.write(config["stdout"])
for key in config["stdout_env"]:
    sys.stdout.write(os.environ[key] + "\\n")
if config["print_campaign"]:
    sys.stdout.write(campaign_id + "\\n")
sys.stdout.flush()
sys.stderr.write(config["stderr"])
for key in config["stderr_env"]:
    sys.stderr.write(os.environ[key] + "\\n")
sys.stderr.flush()
time.sleep(config["sleep_seconds"])
if config["marker_path"] is not None:
    pathlib.Path(config["marker_path"]).write_text("survived\\n", encoding="utf-8")
raise SystemExit(config["exit_code"])
""",
    )
    path.with_name(path.name + ".config.json").write_text(json.dumps(config), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _summary(artifact: Path) -> dict[str, object]:
    return json.loads((artifact / "summary.json").read_text(encoding="utf-8"))


class _TrackingReader:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = list(lines)
        self.readline_sizes: list[int] = []
        self.iteration_used = False

    def __enter__(self) -> _TrackingReader:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self) -> _TrackingReader:
        self.iteration_used = True
        return self

    def __next__(self) -> bytes:
        if not self.lines:
            raise StopIteration
        return self.lines.pop(0)

    def readline(self, size: int = -1) -> bytes:
        self.readline_sizes.append(size)
        if not self.lines:
            return b""
        return self.lines.pop(0)[:size]


def test_success_creates_unique_secret_safe_artifacts_summary_and_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = [_valid_row(1), _valid_row(2)]
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=rows,
        stdout="runtime stdout must stay in its artifact\n",
        stderr_env=["VISIBLE_SENTINEL", "DATABASE_URL"],
    )
    output_root = tmp_path / "reports" / "sim-runs"
    monkeypatch.setenv("BABYLON_CAMPAIGN_ID", CAMPAIGN_ID)
    monkeypatch.setenv("VISIBLE_SENTINEL", "inherited-by-runtime")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:top-secret@example.invalid/babylon")

    first_exit = sim_report.main(
        [
            "--runtime",
            str(runtime),
            "--ticks",
            "2",
            "--output-root",
            str(output_root),
        ]
    )
    first_console = capsys.readouterr()
    second_exit = sim_report.main(
        [
            "--runtime",
            str(runtime),
            "--ticks",
            "2",
            "--output-root",
            str(output_root),
        ]
    )
    second_console = capsys.readouterr()

    assert first_exit == second_exit == 0
    first_artifact = Path(first_console.out.splitlines()[0])
    second_artifact = Path(second_console.out.splitlines()[0])
    assert first_artifact.parent == output_root
    assert second_artifact.parent == output_root
    assert first_artifact != second_artifact
    assert first_artifact.is_dir()
    assert second_artifact.is_dir()

    first_summary = _summary(first_artifact)
    second_summary = _summary(second_artifact)
    first_campaign = first_summary.pop("campaign_id")
    second_campaign = second_summary.pop("campaign_id")
    assert isinstance(first_campaign, str)
    assert isinstance(second_campaign, str)
    assert first_campaign != second_campaign
    assert CAMPAIGN_ID not in {first_campaign, second_campaign}
    assert uuid.UUID(first_campaign).version == 4
    assert uuid.UUID(second_campaign).version == 4
    assert first_summary == {
        "final": {
            "graph_sha256": _digest(3),
            "tick_content_hash": _digest(402),
            "world_sha256": _digest(103),
        },
        "first_resolve_tick": 1,
        "last_resolve_tick": 2,
        "runtime_exit_code": 0,
        "schema": "babylon.simulation.run-summary.v1",
        "status": "ok",
        "ticks_reported": 2,
        "ticks_requested": 2,
        "totals": {
            "audit_receipts": 4,
            "events": 4,
            "material_rows": 6,
            "rules_considered": 6,
            "rules_fired": 2,
        },
    }
    assert "runtime stdout must stay" in (first_artifact / "stdout.txt").read_text()
    stderr_log = (first_artifact / "stderr.txt").read_text()
    assert "inherited-by-runtime" in stderr_log
    assert "top-secret" not in stderr_log
    assert "[REDACTED]" in stderr_log
    assert "runtime stdout must stay" not in first_console.out
    assert f"campaign: {first_campaign}" in first_console.out
    assert "ticks: 2 reported / 2 requested" in first_console.out
    assert first_console.err == ""

    csv_lines = (first_artifact / "ticks.csv").read_text(encoding="utf-8").splitlines()
    assert csv_lines[0].split(",") == list(sim_report.CSV_COLUMNS)
    assert len(csv_lines) == 3
    assert csv_lines[1].startswith("1,committed,")
    assert csv_lines[2].endswith("," + _digest(402))

    persisted = "".join(
        file.read_text(encoding="utf-8") for file in first_artifact.iterdir() if file.is_file()
    )
    assert "postgresql://user:top-secret@example.invalid/babylon" not in persisted


def _invalid_row(case: str) -> dict[str, object]:
    row = copy.deepcopy(_valid_row(41))
    if case == "missing_top":
        del row["world"]
    elif case == "extra_top":
        row["unexpected"] = "value"
    elif case == "missing_nested":
        del row["graph"]["after_sha256"]  # type: ignore[index]
    elif case == "zero_tick":
        row["resolve_tick"] = 0
    elif case == "bad_disposition":
        row["commit_disposition"] = "maybe_committed"
    elif case == "nontext_disposition":
        row["commit_disposition"] = []
    elif case == "uppercase_digest":
        row["tick_content_hash"] = "A" * 64
    elif case == "bool_count":
        row["events"]["count"] = True  # type: ignore[index]
    elif case == "top_fired_gt_considered":
        row["rules"]["considered"] = 0  # type: ignore[index]
    elif case == "empty_rule_id":
        row["rules"]["per_rule"][0]["rule_id"] = ""  # type: ignore[index]
    elif case == "per_rule_fired_gt_considered":
        row["rules"]["per_rule"][0]["fired"] = 3  # type: ignore[index]
    elif case == "per_rule_sum_mismatch":
        row["rules"]["considered"] = 4  # type: ignore[index]
    else:
        raise AssertionError(f"unknown case {case}")
    return row


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing_top", "top-level fields"),
        ("extra_top", "top-level fields"),
        ("missing_nested", "graph fields"),
        ("zero_tick", "positive resolve_tick"),
        ("bad_disposition", "commit_disposition"),
        ("nontext_disposition", "commit_disposition"),
        ("uppercase_digest", "lowercase 64-hex"),
        ("bool_count", "events.count"),
        ("top_fired_gt_considered", "rules.considered must be >= rules.fired"),
        ("empty_rule_id", "nonempty rule_id"),
        ("per_rule_fired_gt_considered", "considered must be >= fired"),
        ("per_rule_sum_mismatch", "per-rule considered sum"),
    ],
)
def test_strict_v1_row_validation_rejects_wrong_shapes_and_values(
    tmp_path: Path,
    case: str,
    message: str,
) -> None:
    report = tmp_path / "ticks.jsonl"
    _write_jsonl(report, [_invalid_row(case)])

    with pytest.raises(sim_report.JsonlValidationError, match=message):
        sim_report._validate_jsonl(report, expected_rows=1)


def test_partial_rows_must_be_contiguous_but_may_start_after_one(
    tmp_path: Path,
) -> None:
    report = tmp_path / "ticks.jsonl"
    _write_jsonl(report, [_valid_row(41), _valid_row(43)])

    with pytest.raises(sim_report.JsonlValidationError, match="contiguous resolve_tick 42"):
        sim_report._validate_jsonl(report, expected_rows=2)

    _write_jsonl(report, [_valid_row(41), _valid_row(42)])
    rows = sim_report._validate_jsonl(report, expected_rows=2)
    assert [row["resolve_tick"] for row in rows] == [41, 42]


def test_durable_rows_accept_continuous_graph_and_world_hash_chains(
    tmp_path: Path,
) -> None:
    report = tmp_path / "ticks.jsonl"
    _write_jsonl(report, [_valid_row(1), _valid_row(2), _valid_row(3)])

    rows = sim_report._validate_jsonl(report, expected_rows=3)

    assert [row["resolve_tick"] for row in rows] == [1, 2, 3]


@pytest.mark.parametrize("state_name", ["graph", "world"])
def test_durable_rows_reject_hash_chain_discontinuities(
    tmp_path: Path,
    state_name: str,
) -> None:
    rows = [_valid_row(1), _valid_row(2)]
    state = rows[1][state_name]
    assert isinstance(state, dict)
    state["before_sha256"] = _digest(999)
    report = tmp_path / "ticks.jsonl"
    _write_jsonl(report, rows)

    with pytest.raises(
        sim_report.JsonlValidationError,
        match=(
            rf"line 2 {state_name}\.before_sha256 does not equal "
            rf"the previous durable row's {state_name}\.after_sha256"
        ),
    ):
        sim_report._validate_jsonl(report, expected_rows=2)


@pytest.mark.parametrize(
    ("row_limit", "message"),
    [
        ({"expected_rows": 1}, "exceeds expected row count 1"),
        ({"maximum_rows": 1}, "exceeds maximum row count 1"),
    ],
)
def test_jsonl_aborts_as_soon_as_a_row_count_bound_is_exceeded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    row_limit: dict[str, int],
    message: str,
) -> None:
    report = tmp_path / "ticks.jsonl"
    report.write_bytes(b"placeholder\n")
    lines = [(json.dumps(_valid_row(tick)) + "\n").encode("utf-8") for tick in (1, 2, 3)]
    reader = _TrackingReader(lines)
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: reader)

    with pytest.raises(sim_report.JsonlValidationError, match=message):
        sim_report._validate_jsonl(report, **row_limit)

    assert reader.readline_sizes == [sim_report.MAX_JSONL_ROW_BYTES + 1] * 2
    assert reader.iteration_used is False
    assert len(reader.lines) == 1


def test_jsonl_caps_each_read_before_rejecting_an_oversize_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "ticks.jsonl"
    report.write_bytes(b"placeholder\n")
    monkeypatch.setattr(sim_report, "MAX_JSONL_ROW_BYTES", 32)
    reader = _TrackingReader([b"x" * 33])
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: reader)

    with pytest.raises(
        sim_report.JsonlValidationError,
        match="line 1 exceeds the 32-byte bound",
    ):
        sim_report._validate_jsonl(report)

    assert reader.readline_sizes == [33]
    assert reader.iteration_used is False


def test_successful_runtime_rejects_reused_nonfresh_tick_sequence(tmp_path: Path) -> None:
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=[_valid_row(41), _valid_row(42)],
    )

    result = sim_report.run_report(runtime=runtime, ticks=2, output_root=tmp_path / "out")

    assert result.exit_code == sim_report.VALIDATION_EXIT_CODE
    assert result.summary["status"] == "validation_failed"
    assert "must start at resolve_tick 1" in result.summary["error"]


def test_successful_runtime_must_report_exactly_the_requested_row_count(
    tmp_path: Path,
) -> None:
    runtime = _configured_runtime(tmp_path / "babylon-runtime", rows=[_valid_row(1)])

    result = sim_report.run_report(runtime=runtime, ticks=2, output_root=tmp_path / "out")

    assert result.exit_code == sim_report.VALIDATION_EXIT_CODE
    assert result.summary["status"] == "validation_failed"
    assert "reports 1 rows; expected exactly 2" in result.summary["error"]


def test_nonzero_runtime_preserves_valid_partial_evidence_and_actual_status(
    tmp_path: Path,
) -> None:
    rows = [_valid_row(1), _valid_row(2)]
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=rows,
        exit_code=17,
        stderr="specific runtime failure\n",
    )

    result = sim_report.run_report(runtime=runtime, ticks=5, output_root=tmp_path / "out")

    assert result.exit_code == 17
    assert result.summary["status"] == "runtime_failed"
    assert result.summary["runtime_exit_code"] == 17
    assert result.summary["ticks_reported"] == 2
    assert result.summary["first_resolve_tick"] == 1
    assert result.summary["last_resolve_tick"] == 2
    assert result.summary["totals"] == {
        "audit_receipts": 4,
        "events": 4,
        "material_rows": 6,
        "rules_considered": 6,
        "rules_fired": 2,
    }
    assert (result.artifact_dir / "ticks.csv").is_file()
    assert (result.artifact_dir / "stderr.txt").read_text() == "specific runtime failure\n"


def test_nonzero_runtime_records_invalid_partial_report_without_hiding_status(
    tmp_path: Path,
) -> None:
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=[_valid_row(1), _valid_row(3)],
        exit_code=19,
    )

    result = sim_report.run_report(runtime=runtime, ticks=5, output_root=tmp_path / "out")

    assert result.exit_code == 19
    assert result.summary["status"] == "runtime_failed"
    assert result.summary["runtime_exit_code"] == 19
    assert result.summary["ticks_reported"] == 0
    assert "contiguous resolve_tick 2" in result.summary["report_validation_error"]
    assert "runtime exited with status 19" in result.error
    assert "report validation failed" in result.error
    assert not (result.artifact_dir / "ticks.csv").exists()


def test_nonzero_runtime_rejects_partial_evidence_from_a_reused_campaign(
    tmp_path: Path,
) -> None:
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=[_valid_row(41), _valid_row(42)],
        exit_code=29,
    )

    result = sim_report.run_report(runtime=runtime, ticks=5, output_root=tmp_path / "out")

    assert result.exit_code == 29
    assert result.summary["status"] == "runtime_failed"
    assert result.summary["ticks_reported"] == 0
    assert "must start at resolve_tick 1" in result.summary["report_validation_error"]
    assert not (result.artifact_dir / "ticks.csv").exists()


def test_runtime_failure_without_rows_preserves_logs_and_actual_status(tmp_path: Path) -> None:
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=None,
        exit_code=23,
        stdout="before failure\n",
        stderr="specific runtime failure\n",
    )

    result = sim_report.run_report(runtime=runtime, ticks=1, output_root=tmp_path / "out")

    assert result.exit_code == 23
    assert (result.artifact_dir / "stdout.txt").read_text() == "before failure\n"
    assert (result.artifact_dir / "stderr.txt").read_text() == "specific runtime failure\n"
    assert result.summary["status"] == "runtime_failed"
    assert result.summary["runtime_exit_code"] == 23
    assert result.summary["ticks_reported"] == 0


def test_noisy_runtime_is_killed_at_bounded_capture_without_secret_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "survived.txt"
    secret = "postgresql://user:noisy-secret@example.invalid/babylon"
    monkeypatch.setattr(sim_report, "MAX_STDOUT_BYTES", 128)
    monkeypatch.setenv("DATABASE_URL", secret)
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=[_valid_row(1)],
        stdout=secret + ("x" * 4096),
        sleep_seconds=5.0,
        marker_path=marker,
    )

    result = sim_report.run_report(runtime=runtime, ticks=1, output_root=tmp_path / "out")

    assert result.exit_code == sim_report.VALIDATION_EXIT_CODE
    assert result.summary["status"] == "runtime_output_limit_exceeded"
    assert "stdout exceeded the 128-byte capture bound" in result.summary["error"]
    assert result.summary["ticks_reported"] == 1
    assert result.summary["first_resolve_tick"] == 1
    assert (result.artifact_dir / "ticks.csv").is_file()
    stdout = (result.artifact_dir / "stdout.txt").read_bytes()
    assert len(stdout) <= 128
    assert secret.encode() not in stdout
    assert not marker.exists()


def test_hung_runtime_is_killed_at_explicit_timeout_without_secret_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "survived.txt"
    secret = "host=db.invalid password=timeout-secret"
    monkeypatch.setenv("BABYLON_RUNTIME_DSN", secret)
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=[_valid_row(1)],
        stderr_env=["BABYLON_RUNTIME_DSN"],
        sleep_seconds=5.0,
        marker_path=marker,
    )

    result = sim_report.run_report(
        runtime=runtime,
        ticks=1,
        output_root=tmp_path / "out",
        timeout_seconds=0.1,
    )

    assert result.exit_code == sim_report.VALIDATION_EXIT_CODE
    assert result.summary["status"] == "runtime_timed_out"
    assert "exceeded the 0.1-second timeout" in result.summary["error"]
    assert result.summary["ticks_reported"] == 1
    assert result.summary["first_resolve_tick"] == 1
    assert (result.artifact_dir / "ticks.csv").is_file()
    stderr = (result.artifact_dir / "stderr.txt").read_text(encoding="utf-8")
    assert "timeout-secret" not in stderr
    assert "[REDACTED]" in stderr
    assert not marker.exists()


def test_absent_campaign_id_generates_fresh_child_only_uuid_and_surfaces_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_path = tmp_path / "campaigns.txt"
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=[_valid_row(1)],
        capture_campaign=True,
        print_campaign=True,
    )
    monkeypatch.delenv("BABYLON_CAMPAIGN_ID", raising=False)
    monkeypatch.setenv("CAMPAIGN_CAPTURE_PATH", str(capture_path))

    results = [
        sim_report.run_report(runtime=runtime, ticks=1, output_root=tmp_path / "out")
        for _ in range(2)
    ]

    campaign_ids = capture_path.read_text(encoding="utf-8").splitlines()
    assert len(set(campaign_ids)) == 2
    for result, campaign_id in zip(results, campaign_ids, strict=True):
        parsed = uuid.UUID(campaign_id)
        assert parsed.version == 4
        assert str(parsed) == campaign_id
        assert result.summary["campaign_id"] == campaign_id
        assert (result.artifact_dir / "stdout.txt").read_text() == campaign_id + "\n"
        assert f"campaign: {campaign_id}" in (result.artifact_dir / "summary.txt").read_text()
    assert "BABYLON_CAMPAIGN_ID" not in os.environ


def test_inherited_campaign_id_is_replaced_before_the_runtime_starts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_path = tmp_path / "campaigns.txt"
    runtime = _configured_runtime(
        tmp_path / "babylon-runtime",
        rows=[_valid_row(1)],
        capture_campaign=True,
    )
    monkeypatch.setenv("BABYLON_CAMPAIGN_ID", CAMPAIGN_ID)
    monkeypatch.setenv("CAMPAIGN_CAPTURE_PATH", str(capture_path))

    result = sim_report.run_report(runtime=runtime, ticks=1, output_root=tmp_path / "out")

    assert result.exit_code == 0
    child_campaign_id = capture_path.read_text(encoding="utf-8").strip()
    assert child_campaign_id != CAMPAIGN_ID
    assert uuid.UUID(child_campaign_id).version == 4
    assert result.summary["campaign_id"] == child_campaign_id


def test_help_explains_tick_count_and_fresh_campaign_semantics() -> None:
    help_text = sim_report._parser().format_help()

    assert "count of ticks" in help_text
    assert "BABYLON_CAMPAIGN_ID" in help_text
    assert "fresh campaign" in help_text
    assert "inherited value is ignored" in help_text
    assert "maximum 10000" in help_text


def test_tick_count_bound_accepts_10000_and_rejects_10001() -> None:
    assert sim_report._positive_ticks("10000") == 10_000
    with pytest.raises(argparse.ArgumentTypeError, match="between 1 and 10000"):
        sim_report._positive_ticks("10001")


def test_runtime_path_must_be_an_executable_file(tmp_path: Path) -> None:
    runtime = tmp_path / "babylon-runtime"
    runtime.write_text("not executable\n", encoding="utf-8")

    with pytest.raises(sim_report.ReportError, match="not executable"):
        sim_report.run_report(runtime=runtime, ticks=1, output_root=tmp_path / "out")
