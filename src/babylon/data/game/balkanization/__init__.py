"""Spec-070 Balkanization seed data and loaders.

Foundational tasks populate this package with:

- ``seed_factions.json``: 4 canonical :class:`BalkanizationFaction` records.
- ``seed_sovereigns.json``: 3 canonical :class:`Sovereign` records
  (``SOV_USA_FED``, ``SOV_CAN_FED``, ``SOV_EXTERIOR_NULL``).
- ``seed_influences.json``: proxy-data-derived INFLUENCES edge seeds
  produced by :mod:`babylon.data.game.balkanization.compute_seed_influences`.

Loaders return frozen Pydantic models validated against the JSON Schemas
in ``specs/070-balkanization/contracts/``.
"""

from __future__ import annotations

__all__: list[str] = []
