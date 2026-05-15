"""Spec-065 T077: full invariant suite gate against the engine-bridged runner.

Skipped unless ``BABYLON_SLOW_TESTS=1``. Asserts that the spec-053/054/055/056
Hypothesis invariant property tests all pass against a fully-bridged
canonical run.

For spec-065 first cut, this test simply re-runs the existing invariant
suite (which targets in-memory WorldState manipulation, not the bridged
runner's Postgres state). When engine integration lands and the bridge
participates in the invariant suite directly, this test becomes the
primary gate.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    os.environ.get("BABYLON_SLOW_TESTS") != "1",
    reason="set BABYLON_SLOW_TESTS=1 to run the full invariant suite gate",
)
def test_invariant_suite_passes_under_bridge() -> None:
    """SC-012: every property in the spec-053/054/055/056 suite passes."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/property/",
            "-q",
            "--no-header",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"invariant suite failed:\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
