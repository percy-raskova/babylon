"""E4 attribution must survive script-mode, not just pytest's import context.

``tests/unit/tools/test_divergence_attribution.py`` unit-tests
``attribute_divergence()`` directly via ``from tools.regression_test import
...`` — that import only resolves because pytest adds the repo root to
``sys.path`` (rootdir insertion), which silently masked a script-mode-only
bug: inside ``attribute_divergence``, the lazy
``from tools.regression_scenarios import CHANNEL_WRITERS`` required ``tools``
to resolve as a subpackage of something already on ``sys.path``, but
script-mode's auto-added ``sys.path[0]`` is the invoked script's own
directory (``tools/``), never the repo root — the rest of
``tools/regression_test.py`` already avoids this by importing its sibling
``regression_scenarios`` module bare (``from regression_scenarios import
SCENARIOS, create_scenario`` at the top of the file, which resolves because
the module inserts ``tools/`` itself onto ``sys.path`` at import time). The
one package-qualified import inside ``attribute_divergence`` was the odd one
out. Net effect: ``mise run qa:regression`` / stock
``poetry run python tools/regression_test.py compare`` crashed with
``ModuleNotFoundError: No module named 'tools.regression_scenarios'`` on any
run that actually had a divergence to attribute — never on a clean run,
which is why it went unnoticed (discovered task 7, qa-modernization program,
2026-07-20). Fixed by switching that one import to the bare sibling idiom
(``from regression_scenarios import CHANNEL_WRITERS``), matching the rest of
the file — resolves under both script-mode and pytest.

This test spawns a genuine subprocess (never in-process — pytest's own
sys.path would hide the bug again) invoked exactly the way
``mise run qa:regression`` invokes it (relative script path, repo root as
cwd), against a synthetic baseline directory holding the real committed
``two_node`` checkpoint baseline (byte-untouched) plus a copy of the real
committed dense golden CSV with exactly ONE cell flipped — guaranteed to
reach ``compare_dense_trace``'s ``attribute_divergence()`` call, the only
code path that ever exercised the buggy import. All synthetic files live
under ``tmp_path``; the only real-repo file this test touches is the
gitignored machine-readable divergence report
(``reports/qa-first-divergence.json`` — its path is computed from the tool's
own ``__file__``, so it always lands under the repo root regardless of
``--baseline-dir``), which is deleted in a ``finally`` block either way.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_JSON = REPO_ROOT / "tests" / "baselines" / "two_node.json"
BASELINE_DENSE_CSV = REPO_ROOT / "tests" / "baselines" / "dense" / "two_node.csv"
FIRST_DIVERGENCE_REPORT = REPO_ROOT / "reports" / "qa-first-divergence.json"


def _flip_one_cell(csv_text: str) -> str:
    """Flip exactly one numeric data cell (tick-1 row, ``C001_wealth`` column).

    Guarantees a real, attributable divergence without hand-constructing the
    dense CSV's column contract from scratch.
    """
    lines = csv_text.splitlines(keepends=True)
    header = lines[0].rstrip("\n").split(",")
    column_index = header.index("C001_wealth")
    tick1_line_index = 2  # lines[0]=header, lines[1]=tick 0, lines[2]=tick 1
    cells = lines[tick1_line_index].rstrip("\n").split(",")
    cells[column_index] = f"{float(cells[column_index]) + 1.0}"
    lines[tick1_line_index] = ",".join(cells) + "\n"
    return "".join(lines)


def test_script_mode_compare_reports_first_divergence(tmp_path: Path) -> None:
    """``python tools/regression_test.py compare`` must not crash on a real divergence.

    Proves the whole failure path — exit 1, ``FIRST DIVERGENCE`` printed to
    stdout, and the machine-readable JSON report written — survives under
    the stock script-mode invocation.
    """
    baseline_dir = tmp_path / "baselines"
    (baseline_dir / "dense").mkdir(parents=True)
    shutil.copyfile(BASELINE_JSON, baseline_dir / "two_node.json")

    doctored_csv = _flip_one_cell(BASELINE_DENSE_CSV.read_text())
    (baseline_dir / "dense" / "two_node.csv").write_text(doctored_csv)

    if FIRST_DIVERGENCE_REPORT.exists():
        FIRST_DIVERGENCE_REPORT.unlink()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "tools/regression_test.py",
                "compare",
                "--baseline-dir",
                str(baseline_dir),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )

        assert "ModuleNotFoundError" not in result.stderr, (
            f"script-mode import regressed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert result.returncode == 1, (
            f"expected exit 1 on a real divergence, got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "FIRST DIVERGENCE" in result.stdout, (
            f"attribution never printed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert FIRST_DIVERGENCE_REPORT.exists(), (
            "compare_all_baselines did not write the machine-readable divergence "
            f"report to {FIRST_DIVERGENCE_REPORT}\nstdout:\n{result.stdout}"
        )
    finally:
        if FIRST_DIVERGENCE_REPORT.exists():
            FIRST_DIVERGENCE_REPORT.unlink()
