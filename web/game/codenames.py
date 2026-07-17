"""Deterministic operation codenames (spec-116 FR-116-3).

A session's codename is a pure function of its UUID primary key — the same
session always renders the same name, with zero schema change to the
``managed=False`` ``game_session`` table (computed on read, per the FR-116-3
recon ruling). Deliberately NOT derived from ``rng_seed``: that column is 0
for every pre-existing session (serializer default; the lobby historically
never sent one), so a seed-derived name would collide across all games.

32 x 32 curated single-word lists give 1,024 distinct codenames; indices come
from the UUID's first four bytes (big-endian, two bytes per list) so the
mapping is byte-stable across processes and platforms.
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

#: Left word — evocative modifier (indexed by UUID bytes 0-1).
_LEFT: Final[tuple[str, ...]] = (
    "CRIMSON",
    "IRON",
    "EMBER",
    "GRANITE",
    "SCARLET",
    "HOLLOW",
    "SILENT",
    "NORTHERN",
    "RUSTED",
    "VELVET",
    "COPPER",
    "MIDNIGHT",
    "BURNING",
    "FALLOW",
    "WINTER",
    "SALT",
    "ASH",
    "LONG",
    "BROKEN",
    "PATIENT",
    "RED",
    "STONE",
    "HUNGRY",
    "DISTANT",
    "EARLY",
    "LAST",
    "SOVEREIGN",
    "UNION",
    "HARBOR",
    "SIGNAL",
    "QUIET",
    "FERAL",
)

#: Right word — concrete noun (indexed by UUID bytes 2-3).
_RIGHT: Final[tuple[str, ...]] = (
    "HARVEST",
    "DAWN",
    "FURNACE",
    "ANVIL",
    "RIVER",
    "LANTERN",
    "THRESHOLD",
    "SPINDLE",
    "GRANARY",
    "PICKET",
    "TELEGRAPH",
    "FOUNDRY",
    "ORCHARD",
    "CROSSING",
    "EMBANKMENT",
    "TURBINE",
    "QUARRY",
    "SICKLE",
    "BALLAST",
    "MERIDIAN",
    "WATCHTOWER",
    "CAUSEWAY",
    "DYNAMO",
    "ARCHIVE",
    "BULWARK",
    "TRELLIS",
    "COMPASS",
    "VIADUCT",
    "SEMAPHORE",
    "TANNERY",
    "MILLSTONE",
    "ACCORD",
)


def operation_codename(session_id: UUID) -> str:
    """Derive a stable two-word operation codename from a session UUID.

    :param session_id: The game session's primary key.
    :returns: ``"LEFT RIGHT"`` in uppercase, e.g. ``"CRIMSON HARVEST"``.
    """
    left_index = int.from_bytes(session_id.bytes[0:2], "big") % len(_LEFT)
    right_index = int.from_bytes(session_id.bytes[2:4], "big") % len(_RIGHT)
    return f"{_LEFT[left_index]} {_RIGHT[right_index]}"
