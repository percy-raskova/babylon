"""Absence sentinel: every sqlite connect site carries a cited disposition.

Instance of the Sentinel pattern guarding the "auto-create masks absence"
invariant (task #64, founding incident: 2026-07-20 G1 nightly --
``get_reference_session()`` silently created an empty reference DB on a
runner with none, surfacing as a baffling downstream ``no such table:
dim_county``). Registry = one :class:`~babylon.sentinels.absence.registry.
ConnectionDisposition` row per file containing a sqlite connect call under
``src/babylon``; checks = three static AST rules (growth: every hit is
registered; backslide: a readonly_uri file stays read-only; staleness: a
registered file still has a hit). See :mod:`babylon.reference.database` for
the runtime guard this static sentinel's registry documents (part A of the
same task); see :mod:`babylon.sentinels.absence.checks` for the scan itself.
"""

from babylon.sentinels.absence.registry import (
    CONNECTION_DISPOSITIONS,
    ConnectionDisposition,
    Disposition,
)

__all__ = [
    "CONNECTION_DISPOSITIONS",
    "ConnectionDisposition",
    "Disposition",
]
