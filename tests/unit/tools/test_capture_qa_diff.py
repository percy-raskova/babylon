"""Unit tests for tools/capture_qa_diff.py (U8.2's evidence-capture tool).

Mocks subprocess.run so this test is fast and independent of the engine's
actual current pass/fail state -- the REAL capture (this repo's real
qa:regression output, expected RED per design D3) happens in Step 4/5 of
this task by running the tool for real, not by this test.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from capture_qa_diff import (  # type: ignore[import-not-found]  # noqa: E402
    capture_qa_regression_diff,
)


def test_capture_qa_regression_diff_writes_file_and_returns_exit_code(
    tmp_path: Path,
) -> None:
    """Writes captured stdout/stderr to the given path and propagates the exit code."""
    fake_result = MagicMock(
        returncode=1,
        stdout="  Comparing imperial_circuit... FAIL\n    tick 38: p_w_wealth: 0.601234 != 0.598877\n",
        stderr="",
    )
    output_path = tmp_path / "diff.txt"

    with patch("capture_qa_diff.subprocess.run", return_value=fake_result) as mock_run:
        exit_code = capture_qa_regression_diff(output_path=output_path)

    assert exit_code == 1
    invoked_argv = mock_run.call_args.args[0]
    assert invoked_argv[1].endswith("regression_test.py")
    assert invoked_argv[2] == "compare"
    content = output_path.read_text()
    assert "FAIL" in content
    assert "exit code: 1" in content


def test_capture_qa_regression_diff_propagates_zero_exit_on_pass(tmp_path: Path) -> None:
    """A green qa:regression is captured and reported as exit code 0."""
    fake_result = MagicMock(returncode=0, stdout="Results: 5 passed, 0 failed\n", stderr="")
    output_path = tmp_path / "diff.txt"

    with patch("capture_qa_diff.subprocess.run", return_value=fake_result):
        exit_code = capture_qa_regression_diff(output_path=output_path)

    assert exit_code == 0
    assert "exit code: 0" in output_path.read_text()
