"""Player-disk safety and archive-location periphery.

Rust runtime authority will own live-session retention after the one-way
persistence cutover. This module retains only host disk preflight/warning
behavior and the player-tier archive location; it does not inspect or mutate
game-managed database state.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path

from babylon.config.paths import player_data_dir

__all__ = [
    "DiskPreflightError",
    "check_disk_preflight",
    "default_archive_root",
    "disk_warning_message",
]


def _gib(n_bytes: int) -> str:
    return f"{n_bytes / 1024**3:.1f} GiB"


class DiskPreflightError(RuntimeError):
    """Raised at boot when the data filesystem is below the required budget."""


def check_disk_preflight(path: Path, required_bytes: int) -> None:
    """Abort the boot loudly when ``path``'s filesystem is below budget.

    The other half of ruling 32: on a 30-80 hour campaign on a shared
    consumer disk, ENOSPC is a scheduled event, and it used to surface as
    a Postgres PANIC with no player-actionable message. ``required_bytes``
    comes from ``GameDefines.persistence.disk_preflight_required_bytes``
    (0 disables — the modding escape hatch; never probes at all).

    :raises DiskPreflightError: free space below ``required_bytes``, with
        the numbers and the path the player must act on.
    """
    if required_bytes <= 0:
        return
    path.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(path).free
    if free < required_bytes:
        raise DiskPreflightError(
            f"Not enough disk space to start a campaign: {path} has "
            f"{_gib(free)} free but Babylon needs {_gib(required_bytes)} "
            f"(campaign history + WAL + reference data). Free up space or "
            f"lower persistence.disk_preflight_required_bytes in "
            f"defines.yaml if this install is deliberately small."
        )


def disk_warning_message(path: Path, floor_bytes: int) -> str | None:
    """The mid-run soft warning, checked at checkpoint cadence.

    Non-blocking by design: the session keeps running; the message is for
    the log and the client surface. Disk state NEVER enters an event or
    the tick hash — machine circumstance, not material history. ``0``
    disables (never probes).
    """
    if floor_bytes <= 0:
        return None
    path.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(path).free
    if free >= floor_bytes:
        return None
    return (
        f"Disk space is running low: {_gib(free)} free at {path} "
        f"(soft floor {_gib(floor_bytes)}). Free some space soon — "
        f"Postgres stopping mid-campaign is the failure this warning exists "
        f"to prevent."
    )


def default_archive_root(env: Mapping[str, str] | None = None) -> Path:
    """The player-tier archive location, beside the logging estate.

    ``$XDG_DATA_HOME/babylon/archives/`` else ``~/.local/share/babylon/
    archives/`` — the same XDG-honoring root the client logs already use
    (``player_data_dir()``, ADR181 Train G: logs + archives honor XDG
    together, never half-and-half).

    :param env: environment mapping forwarded to
        :func:`babylon.config.paths.player_data_dir`; defaults to the real
        process environment.
    """
    return player_data_dir(env) / "archives"
