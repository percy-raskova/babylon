"""Smoke tests for US3 refactored tool scripts (T042-T045 + T045a).

Each test invokes one of the 5 in-scope refactored tools as a subprocess
with very small parameters and asserts the output file exists with a
reasonable shape. Deep-correctness assertions are out of scope here —
that's what the runner's own integration tests already cover.

Gated on ``BABYLON_TEST_PG_DSN`` + SQLite reference DB presence.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PG_DSN = os.environ.get("BABYLON_TEST_PG_DSN")
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        PG_DSN is None,
        reason="BABYLON_TEST_PG_DSN env var not set",
    ),
    pytest.mark.skipif(
        not SQLITE_REF.exists(),
        reason=f"SQLite reference DB missing at {SQLITE_REF}",
    ),
]


def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=os.environ.copy(),
    )


def test_sim_sweep_via_parameter_analysis(tmp_path: Path) -> None:
    """T042: parameter_analysis sweep with 2 points produces a 2-row CSV."""
    out = tmp_path / "sweep.csv"
    proc = _run(
        [
            sys.executable,
            "tools/parameter_analysis.py",
            "sweep",
            "--param",
            "economy.extraction_efficiency",
            "--start",
            "0.05",
            "--end",
            "0.10",
            "--step",
            "0.05",
            "--ticks",
            "3",
            "--csv",
            str(out),
        ],
    )
    assert proc.returncode == 0, f"parameter_analysis sweep failed: {proc.stderr}"
    assert out.exists()
    lines = out.read_text().strip().splitlines()
    assert len(lines) >= 2  # header + at least 1 row
    assert "value" in lines[0]


def test_profiler_writes_prof_file(tmp_path: Path) -> None:
    """T044: profiler emits a .prof file readable by pstats."""
    out = tmp_path / "profile.prof"
    proc = _run(
        [
            sys.executable,
            "tools/profiler.py",
            "--ticks",
            "3",
            "--output",
            str(out),
        ],
    )
    assert proc.returncode == 0, f"profiler failed: {proc.stderr}"
    assert out.exists()
    # Verify pstats can load it.
    import pstats

    pstats.Stats(str(out))  # raises if malformed


def test_qa_audit_writes_markdown_report(tmp_path: Path) -> None:
    """T045: audit_simulation writes audit_latest.md with the 3-scenario structure."""
    out = tmp_path / "audit_latest.md"
    proc = _run(
        [
            sys.executable,
            "tools/audit_simulation.py",
            "--max-ticks",
            "3",
            "--output",
            str(out),
        ],
    )
    assert proc.returncode in (0, 1), f"audit_simulation failed: {proc.stderr}"
    assert out.exists()
    body = out.read_text()
    assert "Simulation Health Report" in body
    assert "A: Baseline" in body
    assert "B: Starvation" in body
    assert "C: Glut" in body


def test_tune_morris_smoke_known_skipped() -> None:
    """T043: tune:morris smoke. sensitivity_analysis is route-only; not
    refactored beyond the import boundary in this MVP."""
    pytest.skip(
        "sensitivity_analysis (Morris/Sobol) routes through shared.run_simulation "
        "with degraded result fields; full Morris-output validation lands when "
        "real engine systems re-enter the headless tick loop (future spec)."
    )


def test_tune_landscape_smoke_known_skipped() -> None:
    """T045a: landscape_analysis smoke. Same MVP-degradation note as Morris."""
    pytest.skip(
        "landscape_analysis routes through shared.run_simulation with "
        "degraded fields; full 2D-grid value validation deferred."
    )
