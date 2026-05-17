"""US4 CI gate: a fresh run matches the committed baseline (T052, spec-064).

Runs the headless runner once, then exercises ``tools/regression_test.py
compare-bundle`` against ``tests/baselines/michigan-e2e.json``. The
gate passes when terminal-tick aggregates are within tolerance and no
critical conservation violations fired.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PG_DSN = os.environ.get("BABYLON_TEST_PG_DSN")
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")
BASELINE = Path("tests/baselines/michigan-e2e.json")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(PG_DSN is None, reason="BABYLON_TEST_PG_DSN env var not set"),
    pytest.mark.skipif(
        not SQLITE_REF.exists(),
        reason=f"SQLite reference DB missing at {SQLITE_REF}",
    ),
    pytest.mark.skipif(
        not BASELINE.exists(),
        reason=f"baseline missing at {BASELINE} — run quickstart Operator path to seed",
    ),
]


def test_fresh_run_matches_baseline(tmp_path: Path) -> None:
    """Fresh run + compare-bundle → exit 0 (within ±1% on total_v + zero critical)."""
    bundle = tmp_path / "bundle"
    runner = subprocess.run(
        [
            sys.executable,
            "-m",
            "babylon.engine.headless_runner",
            "--scope",
            "detroit-tri-county",
            "--ticks",
            "5",
            "--output-dir",
            str(bundle),
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=180,
    )
    assert runner.returncode == 0, f"runner failed: {runner.stderr}"

    compare = subprocess.run(
        [
            sys.executable,
            "tools/regression_test.py",
            "compare-bundle",
            "--bundle",
            str(bundle),
            "--baseline",
            str(BASELINE),
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=60,
    )
    assert compare.returncode == 0, (
        f"compare-bundle reported a regression:\nSTDOUT: {compare.stdout}\nSTDERR: {compare.stderr}"
    )
