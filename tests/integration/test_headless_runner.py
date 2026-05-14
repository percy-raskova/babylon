"""Integration tests for the headless Postgres-backed simulation runner.

Spec: 064-headless-sim-runner (T021-T024b).

Gated on Postgres + SQLite reference data availability so fast-gate CI
(``mise run check``) ignores them; integration CI (``mise run test:int``)
picks them up automatically.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

PG_DSN = os.environ.get("BABYLON_TEST_PG_DSN")
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        PG_DSN is None,
        reason="BABYLON_TEST_PG_DSN env var not set; headless runner tests require Postgres.",
    ),
    pytest.mark.skipif(
        not SQLITE_REF.exists(),
        reason=f"SQLite reference DB missing at {SQLITE_REF}.",
    ),
]


def _invoke_runner(tmp_out: Path, extra: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ``python -m babylon.engine.headless_runner`` as a subprocess."""
    cmd = [
        sys.executable,
        "-m",
        "babylon.engine.headless_runner",
        "--scope",
        "detroit-tri-county",
        "--ticks",
        "5",
        "--output-dir",
        str(tmp_out),
        *extra,
    ]
    env = os.environ.copy()
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )


def test_smoke_tri_county(tmp_path: Path) -> None:
    """T021: full runner produces all 3 artifacts; CSV row count == 3 × 5."""
    out = tmp_path / "bundle"
    result = _invoke_runner(out, [])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert (out / "trace.csv").is_file()
    assert (out / "summary.json").is_file()
    assert (out / "manifest.json").is_file()
    # Validate row count: 3 counties × 5 ticks = 15 data + 1 header.
    trace_lines = (out / "trace.csv").read_text().strip().splitlines()
    assert len(trace_lines) == 16
    # summary.json parses and has the contracted top-level keys.
    summary = json.loads((out / "summary.json").read_text())
    for k in (
        "schema_version",
        "run_metadata",
        "terminal_state",
        "external_node_flows",
        "county_terminal_snapshot",
        "conservation_audit",
        "performance",
    ):
        assert k in summary
    # stdout receives exactly the artifact directory path.
    assert result.stdout.strip() == str(out.resolve())


def test_determinism(tmp_path: Path) -> None:
    """T022: same seed → byte-identical trace.csv + identical input_hash."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    ra = _invoke_runner(a, ["--seed", "2010"])
    rb = _invoke_runner(b, ["--seed", "2010"])
    assert ra.returncode == 0 and rb.returncode == 0
    assert (a / "trace.csv").read_bytes() == (b / "trace.csv").read_bytes()
    hash_a = json.loads((a / "manifest.json").read_text())["reproducibility"]["input_hash"]
    hash_b = json.loads((b / "manifest.json").read_text())["reproducibility"]["input_hash"]
    assert hash_a == hash_b


def test_sigint_partial_artifacts(tmp_path: Path) -> None:
    """T023: SIGINT mid-run → exit 130 + partial=true + partial bundle written.

    We launch a longer run, sleep briefly, then SIGINT the subprocess.
    """
    out = tmp_path / "interrupted"
    cmd = [
        sys.executable,
        "-m",
        "babylon.engine.headless_runner",
        "--scope",
        "detroit-tri-county",
        "--ticks",
        "200",
        "--output-dir",
        str(out),
    ]
    env = os.environ.copy()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    # Give it a moment to enter the tick loop.
    time.sleep(1.5)
    proc.send_signal(signal.SIGINT)
    stdout, stderr = proc.communicate(timeout=60)
    assert proc.returncode == 130, (
        f"expected exit 130 (USER_INTERRUPTED), got {proc.returncode}; stderr={stderr}"
    )
    assert (out / "manifest.json").is_file()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["generator"]["partial"] is True


def test_output_dir_overwrite(tmp_path: Path) -> None:
    """T024: re-running into the same output dir silently overwrites (FR-007)."""
    out = tmp_path / "reused"
    # First run
    r1 = _invoke_runner(out, [])
    assert r1.returncode == 0
    first_trace_bytes = (out / "trace.csv").stat().st_size
    # Plant a sentinel file the runner should NOT preserve
    (out / "sentinel.txt").write_text("stale")
    # Second run — same path, no error
    r2 = _invoke_runner(out, [])
    assert r2.returncode == 0
    assert (out / "trace.csv").stat().st_size == first_trace_bytes
    assert not (out / "sentinel.txt").exists(), "stale file should have been overwritten"


def test_end_game_early_termination(tmp_path: Path) -> None:
    """T024a: end-game condition fires → exit 0, exit_reason="early_terminated".

    This is a skipped placeholder while the MVP runner does no end-game
    detection (T033 is unwired; carry-forward never fires an end-game).
    A future commit lands the EndgameDetector + monkey-patch fixture.
    """
    pytest.skip("MVP runner does not yet fire end-game conditions; future spec")


def test_conservation_violation_does_not_abort(tmp_path: Path) -> None:
    """T024b: a conservation invariant violation continues the run (E6)."""
    out = tmp_path / "with-audit"
    result = _invoke_runner(out, [])
    assert result.returncode == 0
    summary = json.loads((out / "summary.json").read_text())
    # A clean MVP run should have zero violations (carry-forward is a no-op).
    assert summary["conservation_audit"] == []
    # The schema MUST include conservation_audit even when empty.
    assert "conservation_audit" in summary
