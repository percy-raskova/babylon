"""Integration tests for Monte Carlo via the headless runner (T036-T038).

These tests invoke ``tools/monte_carlo.py`` as a subprocess and verify
the output CSV shape. Each Monte Carlo sample triggers a full headless
runner cycle (Postgres pool + initialize_session + tick loop +
artifact emission), so we keep ``--samples`` and ``--max-ticks`` small
to fit within reasonable test budgets.

Gated on ``BABYLON_TEST_PG_DSN`` + SQLite reference DB presence.
"""

from __future__ import annotations

import csv
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


def _run_monte_carlo(samples: int, csv_path: Path, seed: int | None = None) -> int:
    """Invoke tools/monte_carlo.py as a subprocess; return its exit code."""
    cmd = [
        sys.executable,
        "tools/monte_carlo.py",
        "--samples",
        str(samples),
        "--csv",
        str(csv_path),
        "--max-ticks",
        "3",
    ]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=os.environ.copy())
    if proc.returncode != 0:
        print("STDOUT:", proc.stdout, file=sys.stderr)
        print("STDERR:", proc.stderr, file=sys.stderr)
    return proc.returncode


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def test_n_samples_yields_n_rows(tmp_path: Path) -> None:
    """T036: 3 samples → 3 sample rows in the per-sample CSV."""
    out = tmp_path / "monte_carlo.csv"
    rc = _run_monte_carlo(samples=3, csv_path=out)
    assert rc == 0, f"monte_carlo.py exited non-zero: {rc}"
    assert out.exists()
    rows = _csv_rows(out)
    # monte_carlo.py emits one header + N sample rows + an aggregate stats block.
    # Extract just the sample-id rows (those with a numeric sample_id column).
    sample_rows = [r for r in rows if r.get("sample_id", "").isdigit()]
    assert len(sample_rows) == 3, f"expected 3 sample rows, got {len(sample_rows)}: {sample_rows}"


def test_top_level_seed_reproducible(tmp_path: Path) -> None:
    """T037: same top-level seed → identical sample output across runs."""
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    rc_a = _run_monte_carlo(samples=2, csv_path=a, seed=2010)
    rc_b = _run_monte_carlo(samples=2, csv_path=b, seed=2010)
    assert rc_a == 0 and rc_b == 0
    sample_rows_a = [r for r in _csv_rows(a) if r.get("sample_id", "").isdigit()]
    sample_rows_b = [r for r in _csv_rows(b) if r.get("sample_id", "").isdigit()]
    assert sample_rows_a == sample_rows_b, "seed-2010 reruns produced divergent samples"


def test_per_sample_variance_nonzero_known_degraded(tmp_path: Path) -> None:
    """T038: per-sample variance.

    The MVP headless runner is fully deterministic — a no-op carry-forward
    means every per-sample seed produces the same output. Genuine
    cross-sample variance returns when real engine systems land in a
    future spec. For now we assert the test runs and produces sample
    rows; nonzero-variance is a documented spec-064 MVP gap.
    """
    out = tmp_path / "variance.csv"
    rc = _run_monte_carlo(samples=2, csv_path=out)
    assert rc == 0
    sample_rows = [r for r in _csv_rows(out) if r.get("sample_id", "").isdigit()]
    assert len(sample_rows) == 2
    # Future-spec assertion (intentionally skipped while MVP is deterministic):
    pytest.skip(
        "MVP runner is deterministic; cross-sample variance lands when real "
        "engine systems are wired into the headless tick loop (future spec)."
    )
