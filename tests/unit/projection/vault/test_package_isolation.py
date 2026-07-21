"""Package-import hygiene: babylon.projection.vault stays jinja2/dulwich-free
at module-import time (the package __init__ contract — heavy templating and
git dependencies are lazy, function-local imports only, so read-only clients
importing ``babylon.projection`` never pay for them).

Runs in a subprocess for a clean ``sys.modules`` baseline: any other test in
this session may already have imported jinja2/dulwich transitively (e.g. a
test that calls ``render_county``), which would make an in-process
assertion meaningless regardless of collection order.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# tests/unit/projection/vault/test_package_isolation.py -> worktree root is
# four parents up; its src/ directory is what the subprocess must import
# from (the shared venv's babylon.pth points at the *main* checkout, not
# this worktree).
_WORKTREE_SRC = Path(__file__).resolve().parents[4] / "src"

_SCRIPT = (
    "import sys\n"
    "import babylon.projection.vault\n"
    "assert 'jinja2' not in sys.modules, 'jinja2 imported at module scope'\n"
    "assert 'dulwich' not in sys.modules, 'dulwich imported at module scope'\n"
)


def test_importing_vault_package_does_not_pull_in_jinja2_or_dulwich() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_WORKTREE_SRC)
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
