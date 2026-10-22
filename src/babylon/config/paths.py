"""Resolve the persistent player data directory using the platform XDG convention.

Logs and retained operator data share this root without adding a dependency.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def player_data_dir(env: Mapping[str, str] | None = None) -> Path:
    """``$XDG_DATA_HOME/babylon`` else ``~/.local/share/babylon``.

    :param env: environment mapping to read ``XDG_DATA_HOME`` from; defaults
        to the real process environment (``os.environ``) when omitted.
        Injectable so callers and tests get a deterministic result without
        mutating real process environment state.
    :returns: the player data root directory. Not created as a side effect —
        callers ``mkdir(parents=True, exist_ok=True)`` the specific
        subdirectory they need, such as ``logs/``.
    """
    env = os.environ if env is None else env
    xdg = env.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "babylon"


__all__ = ["player_data_dir"]
