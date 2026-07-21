"""Launcher determinism re-exec (T1.2/K3, spine G, adversarial finding 3).

``PYTHONHASHSEED`` cannot be set once the interpreter has started, and the
shipped ``babylon`` launcher never set it anywhere — so ``babylon.cli``
re-execs itself exactly once, before any heavy import, with
``PYTHONHASHSEED=0`` and the BLAS/OpenMP thread caps pinned to ``1``.

These tests always subprocess-spawn a *fresh* interpreter (never
``CliRunner``/in-process import): ``os.execve`` replaces the calling
process image, so asserting its effect from the calling process is
impossible by construction — only a child process's stdout survives to be
inspected. ``tests/unit/cli/test_app.py`` et al. cover the in-process,
``pytest``-guarded path (see ``babylon.cli._reexec_with_sealed_environment``
docstring): that guard is exactly why importing ``babylon.cli`` in those
files never triggers any of this.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# tests/unit/cli/test_launcher_reexec.py -> worktree root is three parents up;
# its src/ is what the subprocess must import from -- the shared venv's
# babylon.pth points at the *main* checkout, not this worktree (the
# "Worktree gotcha" documented in CLAUDE.md).
_WORKTREE_SRC = Path(__file__).resolve().parents[3] / "src"

_ENV_VARS = (
    "BABYLON_ENV_SEALED",
    "PYTHONHASHSEED",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)

# Appends one line to $REEXEC_MARKER_FILE every time this script body runs,
# then imports babylon.cli (which may or may not re-exec) and prints the
# resulting env. If the re-exec fires exactly once, the marker file ends up
# with exactly 2 lines: one from the original (unsealed) process, one from
# the re-exec'd (sealed) process that then runs to completion.
_SCRIPT = (
    "import os\n"
    "from pathlib import Path\n"
    "with Path(os.environ['REEXEC_MARKER_FILE']).open('a') as fh:\n"
    "    fh.write('run\\n')\n"
    "import babylon.cli\n"
    f"for name in {_ENV_VARS!r}:\n"
    "    print(f'{name}={os.environ.get(name)}')\n"
)


def _run_script(env: dict[str, str], marker_file: Path) -> subprocess.CompletedProcess[str]:
    env = dict(env)
    env["PYTHONPATH"] = str(_WORKTREE_SRC)
    env["REEXEC_MARKER_FILE"] = str(marker_file)
    return subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _parse_env_lines(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in stdout.strip().splitlines():
        key, _, value = line.partition("=")
        parsed[key] = value
    return parsed


def test_unsealed_process_reexecs_exactly_once_and_seals_determinism_env(
    tmp_path: Path,
) -> None:
    marker_file = tmp_path / "marker.txt"
    # Deliberately unsealed and un-pinned starting environment: strip any of
    # our own vars that might already be set in the ambient shell/mise env,
    # so the assertions below can only pass if babylon.cli itself set them.
    env = {k: v for k, v in os.environ.items() if k not in _ENV_VARS}

    result = _run_script(env, marker_file)

    assert result.returncode == 0, result.stdout + result.stderr
    parsed = _parse_env_lines(result.stdout)
    assert parsed["BABYLON_ENV_SEALED"] == "1"
    assert parsed["PYTHONHASHSEED"] == "0"
    assert parsed["OMP_NUM_THREADS"] == "1"
    assert parsed["OPENBLAS_NUM_THREADS"] == "1"
    assert parsed["MKL_NUM_THREADS"] == "1"
    assert parsed["NUMEXPR_NUM_THREADS"] == "1"

    # Exactly one re-exec: the script body ran twice (once unsealed, once
    # sealed) -- never once (no re-exec happened) and never 3+ (a loop).
    marker_lines = marker_file.read_text().splitlines()
    assert len(marker_lines) == 2, marker_lines


def test_already_sealed_process_never_reexecs_again(tmp_path: Path) -> None:
    marker_file = tmp_path / "marker.txt"
    env = {k: v for k, v in os.environ.items() if k not in _ENV_VARS}
    env["BABYLON_ENV_SEALED"] = "1"
    # A value the real re-exec would never produce (which always writes
    # "0"), so any change proves a second re-exec fired despite the guard.
    env["PYTHONHASHSEED"] = "999999"

    result = _run_script(env, marker_file)

    assert result.returncode == 0, result.stdout + result.stderr
    parsed = _parse_env_lines(result.stdout)
    assert parsed["PYTHONHASHSEED"] == "999999"

    marker_lines = marker_file.read_text().splitlines()
    assert len(marker_lines) == 1, marker_lines


def test_import_inside_pytest_process_never_reexecs() -> None:
    """The pytest-detection guard is what keeps ``test_app.py``-style
    in-process imports (``CliRunner``, ``from babylon.cli import app``)
    cheap: if it were ever removed, importing ``babylon.cli`` here would
    replace this pytest worker's own process image mid-session."""
    import babylon.cli  # noqa: F401 -- import-for-side-effect is the point

    assert os.environ.get("BABYLON_ENV_SEALED") != "1"
