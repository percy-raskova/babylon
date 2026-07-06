"""Spec-070 Balkanization seed data and loaders.

Loaders return frozen Pydantic models validated against the JSON
Schemas in ``specs/070-balkanization/contracts/``. Concrete files:

- ``seed_factions.json``: 4 canonical
  :class:`~babylon.models.entities.balkanization_faction.BalkanizationFaction`
  records (FAC_RESTORATIONIST, FAC_WORKERS_CONGRESS, FAC_DECOLONIAL,
  FAC_LIBERAL_IMPERIAL).
- ``seed_sovereigns.json``: 3 canonical
  :class:`~babylon.models.entities.sovereign.Sovereign` records
  (SOV_USA_FED, SOV_CAN_FED, SOV_EXTERIOR_NULL per FR-040 / FR-040a /
  FR-040b).
- ``seed_influences.json``: computed by the proxy-data pipeline in
  :mod:`compute_seed_influences` (T112) and checked into the repository
  per Percy's ruling on spec-070 item #8. The loader reads the
  ``edges`` array of the schema-conformant payload; it gracefully
  returns an empty list when the file is absent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from babylon.models.entities.balkanization_faction import BalkanizationFaction
from babylon.models.entities.sovereign import Sovereign

_DATA_DIR = Path(__file__).resolve().parent
_SEED_FACTIONS_PATH = _DATA_DIR / "seed_factions.json"
_SEED_SOVEREIGNS_PATH = _DATA_DIR / "seed_sovereigns.json"
_SEED_INFLUENCES_PATH = _DATA_DIR / "seed_influences.json"


def load_seed_factions(
    path: Path | None = None,
) -> list[BalkanizationFaction]:
    """Load and validate the canonical seed factions.

    Args:
        path: Optional override for the JSON file path; defaults to the
            in-package ``seed_factions.json``.

    Returns:
        Frozen :class:`BalkanizationFaction` instances in file order.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        pydantic.ValidationError: If any faction record violates the
            entity schema.
    """

    if path is None:
        path = _SEED_FACTIONS_PATH
    payload = json.loads(path.read_text())
    return [BalkanizationFaction.model_validate(record) for record in payload["factions"]]


def load_seed_sovereigns(
    path: Path | None = None,
) -> list[Sovereign]:
    """Load and validate the canonical seed Sovereigns.

    Args:
        path: Optional override for the JSON file path; defaults to the
            in-package ``seed_sovereigns.json``.

    Returns:
        Frozen :class:`Sovereign` instances in file order. The initial
        CLAIMS list is preserved as a side-channel under
        ``Sovereign.__pydantic_extra__`` is NOT used; consumers must
        read the raw JSON via :func:`load_seed_sovereigns_raw` to get
        the ``initial_claims`` array. The Pydantic Sovereign model
        intentionally does not carry edge state.
    """

    if path is None:
        path = _SEED_SOVEREIGNS_PATH
    payload = json.loads(path.read_text())
    sovereigns: list[Sovereign] = []
    for record in payload["sovereigns"]:
        # Drop edge-state fields before constructing the entity.
        entity_record = {
            key: value for key, value in record.items() if key not in {"initial_claims"}
        }
        sovereigns.append(Sovereign.model_validate(entity_record))
    return sovereigns


def load_seed_sovereigns_raw(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return the raw seed-sovereigns records (including
    ``initial_claims`` edge arrays) for consumption by the
    db-init pipeline.

    Args:
        path: Optional override for the JSON file path.

    Returns:
        List of raw record dicts straight from the JSON file.
    """

    if path is None:
        path = _SEED_SOVEREIGNS_PATH
    payload = json.loads(path.read_text())
    return list(payload["sovereigns"])


def load_seed_influences(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Load the proxy-data-derived INFLUENCES edge seeds (FR-039).

    Gracefully returns an empty list when ``seed_influences.json`` is
    absent. The file is produced by the
    :mod:`compute_seed_influences` pipeline (T112); per Percy's ruling
    on item #8 the computed artifact IS checked into the repository so
    the runtime loader finds a concrete edge set rather than the empty
    fallback.

    Args:
        path: Optional override for the JSON file path.

    Returns:
        List of raw seed edge records (the ``edges`` array from the
        schema-conformant payload). Each record has
        ``{faction_id, territory_id, influence_level, support_type,
        cadre_count, sympathizer_count, established_tick}``.
    """

    if path is None:
        path = _SEED_INFLUENCES_PATH
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    return list(payload["edges"])


__all__ = [
    "load_seed_factions",
    "load_seed_influences",
    "load_seed_sovereigns",
    "load_seed_sovereigns_raw",
]
