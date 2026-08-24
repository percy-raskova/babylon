#!/usr/bin/env python3
"""Worktree environment contract (ADR181 R9c — scar class #2, >=5 incidents).

Five asserts, each mapped to a real debugging session this class cost:

1. The venv interpreter matches ``.python-version`` (worktree venvs created
   against the wrong interpreter shadow imports unpredictably).
2. The ``server`` extra is installed (Django import — its absence produced a
   false "the game is broken" 500).
3. Every ``data/`` symlink resolves and the reference DB is present (fresh
   worktrees lack the symlink farm; tests then auto-create empty sqlite).
4. ``.env`` exists.
5. ``uv.lock`` is unmodified vs HEAD (committing an incidental re-lock breaks
   CI; fix: ``git checkout -- uv.lock``; use ``UV_FROZEN=1`` only for ``uv
   sync`` or ``uv run``; ``uv lock --check`` must run with ``UV_FROZEN`` unset).

Stdlib-only and interpreter-agnostic on purpose: it runs as the FIRST
pre-commit hook (fail_fast), before anything trusts the venv it is checking.
Also invocable as ``mise run check:worktree-contract``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REFERENCE_DB = Path("data/sqlite/marxist-data-3NF.sqlite")


def check_interpreter() -> str | None:
    """Venv python must match the ``.python-version`` minor."""
    pin = Path(".python-version").read_text().strip()
    venv_python = Path(".venv/bin/python")
    if not venv_python.exists():
        return ".venv/bin/python missing — run `uv sync --extra server --frozen`"
    proc = subprocess.run(
        [str(venv_python), "--version"], capture_output=True, text=True, check=False
    )
    version = proc.stdout.strip().removeprefix("Python ")
    if not version.startswith(pin):
        return f"venv python {version} does not match .python-version pin {pin}"
    return None


def check_server_extra() -> str | None:
    """The server extra must be installed (django is its marker import)."""
    proc = subprocess.run(
        [".venv/bin/python", "-c", "import django"], capture_output=True, check=False
    )
    if proc.returncode != 0:
        return "server extra not installed (import django failed) — run `uv sync --extra server --frozen`"
    return None


def check_data_symlinks() -> str | None:
    """Every data/ symlink resolves; the reference DB is reachable."""
    data = Path("data")
    if not data.is_dir():
        return "data/ missing — copy the symlink farm from the main checkout"
    dangling = [str(p) for p in sorted(data.iterdir()) if p.is_symlink() and not p.exists()]
    if dangling:
        return f"dangling data/ symlinks: {', '.join(dangling)}"
    if not REFERENCE_DB.exists():
        return f"{REFERENCE_DB} missing — fresh worktrees lack the data/ symlink farm"
    return None


def check_dotenv() -> str | None:
    """.env must exist (runtime DSNs and settings load from it)."""
    if not Path(".env").is_file():
        return ".env missing — copy it from the main checkout"
    return None


def check_lock_unmodified() -> str | None:
    """uv.lock must be byte-identical to HEAD's."""
    proc = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "uv.lock"], check=False)
    if proc.returncode != 0:
        return (
            "uv.lock modified vs HEAD — restore with `git checkout -- uv.lock` "
            "and use `UV_FROZEN=1` only for `uv sync` or `uv run`; "
            "`uv lock --check` must run with `UV_FROZEN` unset"
        )
    return None


def main() -> int:
    checks = (
        check_interpreter,
        check_server_extra,
        check_data_symlinks,
        check_dotenv,
        check_lock_unmodified,
    )
    failures = [message for check in checks if (message := check()) is not None]
    for message in failures:
        print(f"worktree-contract: {message}", file=sys.stderr)
    if not failures:
        print("worktree-contract: clean")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
