"""SC-006: epsilon-determinism check across two baseline-regen runs.

Two consecutive `mise run sim:e2e-michigan` invocations with the same
seed produce trace.csv files whose numeric cells agree within
float64 machine precision (max relative error ≤ 10^-12).

The test is SKIPPED unless two recent regen artifacts under
`reports/sim-runs/*/trace.csv` are present. Operators producing
both via T051 + T054b can then run this test to assert the
determinism invariant.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNS_DIR = _REPO_ROOT / "reports" / "sim-runs"

# Empirically established machine-precision tolerance (2026-05-17,
# 7.47e-14 observed) plus headroom for future kernel / BLAS upgrades.
_EPSILON_RELATIVE = 1e-12


_MIN_CANONICAL_ROWS = 1000  # smoke-test runs (tri-county / 5-tick) have ~15-50 rows


def _is_canonical_michigan(trace_csv: Path) -> bool:
    """Heuristic: canonical 520-tick michigan-canada runs have ≥ 1000 rows.

    Smoke / qa:e2e-regression runs (detroit-tri-county, 5 ticks) have
    ~15-50 rows and should be excluded from the SC-006 epsilon check.
    """

    with trace_csv.open() as f:
        # Count lines without slurping the file
        return sum(1 for _ in f) > _MIN_CANONICAL_ROWS


def _input_hash(trace_csv: Path) -> str | None:
    """The run's manifest ``reproducibility.input_hash``, or None if absent."""
    import json

    manifest = trace_csv.parent / "manifest.json"
    if not manifest.exists():
        return None
    try:
        payload = json.loads(manifest.read_text())
    except json.JSONDecodeError:
        return None
    repro = payload.get("reproducibility", {})
    value = repro.get("input_hash")
    return str(value) if value else None


def _recent_michigan_runs() -> tuple[Path, Path] | None:
    """Return (older, newer) trace.csv paths from the two most-recent
    *canonical* (520-tick) michigan-canada runs, or None if fewer than two."""

    if not _RUNS_DIR.exists():
        return None
    canonical_traces: list[Path] = []
    for run in sorted(_RUNS_DIR.iterdir()):
        trace = run / "trace.csv"
        if run.is_dir() and trace.exists() and _is_canonical_michigan(trace):
            canonical_traces.append(trace)
    if len(canonical_traces) < 2:
        return None
    return (canonical_traces[-2], canonical_traces[-1])


def test_sc006_recent_regens_epsilon_deterministic() -> None:
    """Two most-recent michigan-e2e regens agree within 10^-12 relative.

    Only a SAME-INPUT pair is a determinism claim: runs whose manifest
    ``input_hash`` differ (different seed, defines, data version, or code
    era) legitimately diverge — comparing them measured code drift, not
    non-determinism (observed 2026-07-16: 33% "error" across two runs from
    different code eras). Such pairs SKIP with instructions to regenerate.
    """

    pair = _recent_michigan_runs()
    if pair is None:
        pytest.skip(
            f"need 2+ trace.csv files under {_RUNS_DIR} — run "
            "`mise run sim:e2e-michigan` twice with the same seed first"
        )
    older_path, newer_path = pair

    older_hash = _input_hash(older_path)
    newer_hash = _input_hash(newer_path)
    if older_hash is None or newer_hash is None or older_hash != newer_hash:
        pytest.skip(
            f"most-recent canonical regens are not a same-input pair "
            f"(input_hash {older_hash!r} vs {newer_hash!r}) — run "
            "`mise run sim:e2e-michigan` twice consecutively on the same "
            "code + seed to produce a determinism pair"
        )

    with older_path.open() as f1, newer_path.open() as f2:
        older = list(csv.DictReader(f1))
        newer = list(csv.DictReader(f2))

    assert len(older) == len(newer), (
        f"row count mismatch: {len(older)} vs {len(newer)} "
        f"({older_path.name} vs {newer_path.name}) — determinism violated"
    )

    max_rel = 0.0
    max_field = ""
    diff_cells = 0
    for i, (row_a, row_b) in enumerate(zip(older, newer, strict=True)):
        for key, va in row_a.items():
            vb = row_b[key]
            if va == vb:
                continue
            try:
                fa, fb = float(va), float(vb)
            except ValueError:
                pytest.fail(f"non-numeric divergence at row {i} field {key!r}: {va!r} vs {vb!r}")
            diff_cells += 1
            denom = max(abs(fa), abs(fb), 1e-300)
            rel = abs(fa - fb) / denom
            if rel > max_rel:
                max_rel = rel
                max_field = f"row {i} {key}={va} vs {vb}"

    assert max_rel <= _EPSILON_RELATIVE, (
        f"SC-006 epsilon-determinism FAILED: max relative error "
        f"{max_rel:.4e} > {_EPSILON_RELATIVE:.0e}. "
        f"Diff cells: {diff_cells}. Worst: {max_field}"
    )
