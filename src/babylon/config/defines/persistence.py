"""Persistence/disk-awareness thresholds (ADR176 ruling 32).

The Director's binding intent for the database tier (ruling 33, verbatim):
*the database functions so perfectly it is 100% in the background*. On a
30-80 hour campaign on a shared consumer disk, ``ENOSPC`` is a scheduled
event, and before this category it surfaced as a Postgres PANIC with no
player-actionable message (the postgres brief: ``rg disk_free|
shutil.disk_usage|ENOSPC src/babylon`` returned nothing). These thresholds
drive the boot preflight and the mid-run soft warning — infrastructure
honesty budgets, not gameplay coefficients, but player-moddable because a
machine with a small dedicated partition is a legitimate install target.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PersistenceDefines(BaseModel):
    """Disk preflight/soft-warning budgets for the campaign estate."""

    model_config = ConfigDict(frozen=True)

    disk_preflight_required_bytes: int = Field(
        default=10 * 1024**3,
        ge=0,
        description=(
            "Player machine: free bytes required on the Babylon data "
            "filesystem before a campaign boots. The 10 GiB default is the "
            "postgres brief's budget: campaign ~2.35 GB + WAL ceiling 2 GB "
            "+ reference-in-PG ~0.6 GB + the 4.2 GB SQLite source, with "
            "headroom. Boot ABORTS below this with a player-actionable "
            "message (Constitution III.11 — a Postgres ENOSPC PANIC "
            "mid-campaign is the failure mode this preflight exists to "
            "prevent). 0 disables the preflight (modding escape hatch for "
            "deliberately tiny installs)."
        ),
    )
    disk_soft_warning_bytes: int = Field(
        default=2 * 1024**3,
        ge=0,
        description=(
            "Player machine: free-bytes floor checked at checkpoint "
            "cadence DURING a campaign; below it the session raises a "
            "soft, non-blocking warning (log + client surface) telling "
            "the player to free space before the disk actually fills. "
            "Never enters the tick hash — disk state is machine "
            "circumstance, not material history. 0 disables the warning."
        ),
    )
