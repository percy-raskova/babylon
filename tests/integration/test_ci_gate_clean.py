"""US4 CI gate: clean run produces zero critical violations (T051, spec-064).

Long-form integration check intended for the opt-in nightly CI workflow.
Skipped unless ``BABYLON_TEST_PG_DSN`` is set AND ``BABYLON_SLOW_TESTS=1``
(per spec — this is the heavyweight gate, not a per-PR signal).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PG_DSN = os.environ.get("BABYLON_TEST_PG_DSN")
SLOW = os.environ.get("BABYLON_SLOW_TESTS") == "1"
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(PG_DSN is None, reason="BABYLON_TEST_PG_DSN env var not set"),
    pytest.mark.skipif(not SLOW, reason="BABYLON_SLOW_TESTS=1 not set (opt-in gate)"),
    pytest.mark.skipif(
        not SQLITE_REF.exists(),
        reason=f"SQLite reference DB missing at {SQLITE_REF}",
    ),
]


def test_michigan_run_has_zero_critical_violations(tmp_path: Path) -> None:
    """Full headless run → ``summary.conservation_audit`` has no severity=critical entries."""
    out = tmp_path / "ci-gate"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "babylon.engine.headless_runner",
            "--scope",
            "detroit-tri-county",  # MVP: tri-county; full Michigan when budget allows
            "--ticks",
            "10",
            "--output-dir",
            str(out),
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=600,
    )
    assert proc.returncode == 0, f"runner exited non-zero: stderr={proc.stderr}"
    summary = json.loads((out / "summary.json").read_text())
    critical = [a for a in summary.get("conservation_audit", []) if a.get("severity") == "critical"]
    assert critical == [], f"clean run produced critical violations: {critical}"
