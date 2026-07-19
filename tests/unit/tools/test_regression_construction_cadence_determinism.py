"""Empirical proof that the per-tick ServiceContainer.create(**overrides)
cadence (simulation_engine.py:527) is deterministic across independent OS
processes, now that tools/regression_test.py threads Vol III financial
calculator_overrides through it (U1, D4's committed FRED fixture).

Design spec 2026-07-18-vol3-money-scissors-design.md section 5, hazard 2:
"Same-inputs -> same-outputs across every construction site must be
verified EMPIRICALLY before U7, not inferred from reading code. ADR056's
precedent applies: the planned determinism proof was wrong and only an
empirical run caught it." ADR056 (spec-102) found that a determinism check
performed by re-running the SAME interpreter in-process, or by comparing a
hash that turned out to embed run-scoped state, both gave false confidence.
This test follows that precedent literally: it spawns two genuinely
separate ``python`` processes (never two in-process calls, which would
share one PYTHONHASHSEED and could hide a hash-randomization-dependent
set/dict iteration-order bug) and byte-compares their output. Per
.mise.toml and tests/conftest.py, BLAS thread counts are pinned to 1 for
determinism but PYTHONHASHSEED is deliberately left unpinned -- each
subprocess below gets Python's normal fresh random hash seed, so a
byte-identical result here is real cross-process evidence, not an artifact
of test isolation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION_TOOL = REPO_ROOT / "tools" / "regression_test.py"

# imperial_circuit is the 4-node default scenario -- the first key in
# tools/regression_test.py's SCENARIOS dict and the scenario every other
# behavioral-contract test in this suite treats as the canonical case.
DETERMINISM_SCENARIO = "imperial_circuit"


def _run_generate(output_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run ``regression_test.py generate`` for one scenario in its own process.

    Args:
        output_dir: Directory the subprocess writes
            ``<scenario>.json`` and ``dense/<scenario>.csv`` into.

    Returns:
        The completed subprocess result (stdout/stderr captured as text).
    """
    return subprocess.run(
        [
            sys.executable,
            str(REGRESSION_TOOL),
            "generate",
            "--scenario",
            DETERMINISM_SCENARIO,
            "--dense",
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        timeout=120,
    )


def test_two_independent_processes_produce_byte_identical_dense_trace(
    tmp_path: Path,
) -> None:
    """Two separate `generate` subprocesses for the same scenario must agree byte-for-byte."""
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"

    result_a = _run_generate(dir_a)
    result_b = _run_generate(dir_b)

    assert result_a.returncode == 0, f"run A failed: {result_a.stderr}"
    assert result_b.returncode == 0, f"run B failed: {result_b.stderr}"

    data_a = json.loads((dir_a / f"{DETERMINISM_SCENARIO}.json").read_text())
    data_b = json.loads((dir_b / f"{DETERMINISM_SCENARIO}.json").read_text())
    # generated_at is a wall-clock ISO timestamp -- the only field two
    # independent runs are allowed to disagree on. Strip before comparing.
    data_a.pop("generated_at", None)
    data_b.pop("generated_at", None)
    assert data_a == data_b, (
        "sampled-checkpoint JSON diverged between two independent processes "
        "running the identical scenario -- the per-tick ServiceContainer "
        "construction cadence is NOT deterministic"
    )

    csv_a = (dir_a / "dense" / f"{DETERMINISM_SCENARIO}.csv").read_bytes()
    csv_b = (dir_b / "dense" / f"{DETERMINISM_SCENARIO}.csv").read_bytes()
    assert csv_a == csv_b, (
        "dense per-tick trace CSV diverged between two independent processes "
        "running the identical scenario -- the per-tick ServiceContainer "
        "construction cadence is NOT deterministic"
    )
