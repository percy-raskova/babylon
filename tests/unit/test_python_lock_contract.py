"""Python lockfile contracts for a clean Babylon checkout."""

from __future__ import annotations

import subprocess


def test_pinned_uv_validates_the_lock_without_a_hypergraph_sibling() -> None:
    """A clean checkout resolves the committed Python lock without local sibling setup."""
    result = subprocess.run(  # noqa: S603
        ["mise", "exec", "uv", "--", "uv", "lock", "--check"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
