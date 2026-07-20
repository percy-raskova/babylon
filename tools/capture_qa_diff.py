"""Capture `tools/regression_test.py compare`'s full stdout+stderr to a
fixed evidence file for the Vol III baseline-delta report (U8.2), and
propagate its exit code unchanged.

Usage:
    poetry run python tools/capture_qa_diff.py

Writes: reports/vol3-baseline-delta-raw-diff.txt
Exits: the underlying `compare` invocation's own exit code (0 = every
    scenario matched its committed baseline, 1 = at least one diverged).

See Also:
    :doc:`/reference/determinism-contract` for what qa:regression actually
    compares (checkpoint values + dense goldens).
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

OUTPUT_PATH: Path = Path(__file__).parent.parent / "reports" / "vol3-baseline-delta-raw-diff.txt"


def capture_qa_regression_diff(output_path: Path = OUTPUT_PATH) -> int:
    """Run `regression_test.py compare` and write its combined output to disk.

    Args:
        output_path: File to write the captured stdout+stderr into. Parent
            directories are created if missing.

    Returns:
        The exit code of the underlying `compare` invocation, unchanged.
    """
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "regression_test.py"), "compare"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# qa:regression compare -- captured "
        f"{datetime.now(UTC).isoformat(timespec='seconds')}\n"
        f"# exit code: {result.returncode}\n\n"
    )
    output_path.write_text(header + result.stdout + result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(capture_qa_regression_diff())
