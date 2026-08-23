"""Guard frozen Rust migration vectors against the Python legacy sources."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_frozen_rust_legacy_postgres_fixtures_match_python_sources() -> None:
    """The committed vectors must exactly match the source DDL sequences."""
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, str(root / "tools/export_legacy_postgres_contract.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
