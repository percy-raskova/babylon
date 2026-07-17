"""US4 CI gate: a fresh run matches the committed baseline (T052, spec-064).

Runs the headless runner once, then exercises ``tools/regression_test.py
compare-bundle`` against ``tests/baselines/detroit-tri-county-5t.json``. The
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
# Like-for-like: the test runs a 5-tick detroit-tri-county bundle, so it
# compares against the 5-tick tri-county baseline (same one qa:e2e-regression
# gates on). It USED to point at michigan-e2e.json — valid until f528e7d3
# regenerated that file as an 83-county/520-tick run under the same name,
# which turned this test into a guaranteed counties_alive 3-vs-83 mismatch.
BASELINE = Path("tests/baselines/detroit-tri-county-5t.json")

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
    pytest.mark.skipif(
        BASELINE.exists() and BASELINE.stat().st_size < 1024,
        reason=(
            f"baseline at {BASELINE} looks like a git-LFS pointer, not the real "
            "JSON — run `git lfs pull` (an un-smudged pointer fed JSONDecodeError "
            "to compare-bundle, 2026-07-16)"
        ),
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
        # 5-tick runs take 160-300s under 4-way xdist contention (2026-07-16).
        timeout=600,
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
