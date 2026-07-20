"""Runtime builder for the QCEW-sourced :class:`Business` seed artifact (ADR086).

The canonical playable scenarios (``us_nationwide`` / ``wayne_county``) seed
representative :class:`~babylon.models.entities.organization.Business`
organizations sized from REAL BLS QCEW private-sector employment. The scenario
builders take no reference-DB session at build time, so the aggregates are
precomputed by ``tools/generate_business_seeds.py`` into the committed,
hash-stamped ``src/babylon/data/game/business_seeds.json`` (deterministic-data
-artifacts doctrine: CI never touches the data drive). This module reads that
artifact and constructs the frozen :class:`Business` models — the single shared
helper both scenario builders call (DRY).

Only fields the real data supports are set: ``sector`` (real 2-digit label),
``naics_2digit``, and ``employment_count`` (the real aggregate). Every other
Business field (revenue, surplus rates, constant/variable capital) keeps its
model default — economic *behaviour* for seeded businesses is deliberately
future work (ADR086; layer0 currently emits an inert EMPLOY ActionResult).
``class_character`` is :class:`ClassCharacter.BOURGEOIS` — a Business is
privately-owned capital employing wage labour, a domain judgment, not data.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from babylon.models.entities.organization import Business
from babylon.models.enums import ClassCharacter

#: Committed seed artifact (mirrors the doctrine-tree loader's data-dir pattern:
#: ``<pkg>/data/game/<file>.json``).
ARTIFACT_PATH = Path(__file__).resolve().parents[2] / "data" / "game" / "business_seeds.json"


@lru_cache(maxsize=1)
def load_seed_data() -> dict[str, Any]:
    """Load and cache the committed business-seed artifact.

    Returns:
        The parsed artifact payload (``schema_version``, ``source``,
        ``content_hash``, ``scopes``).

    Raises:
        FileNotFoundError: If the artifact is missing (regenerate with
            ``tools/generate_business_seeds.py``).
        json.JSONDecodeError: If the artifact is not valid JSON.
    """
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def build_seeded_businesses(scope: str, territory_ids: list[str]) -> dict[str, Business]:
    """Build the seeded Business orgs for one scenario scope.

    Args:
        scope: Artifact scope key — ``"US"`` (national) or a county FIPS such
            as ``"26163"`` (Wayne County).
        territory_ids: Territories the businesses operate in (a mechanical
            anchor so they are MOBILIZE-eligible and fog-reachable for a player
            org present in the same territories). Typically the player org's
            starting territories.

    Returns:
        Mapping of deterministic business id -> frozen :class:`Business`, in
        employment-rank order.

    Raises:
        KeyError: If ``scope`` is not a scope defined in the artifact — a loud
            failure (Constitution III.11), never a silent empty seeding.
    """
    scope_entry = load_seed_data()["scopes"][scope]
    display_name: str = scope_entry["display_name"]
    id_prefix: str = scope_entry["id_prefix"]

    businesses: dict[str, Business] = {}
    for sector in scope_entry["sectors"]:
        biz_id = f"{id_prefix}{sector['rank']:02d}"
        businesses[biz_id] = Business(
            id=biz_id,
            name=f"{display_name} {sector['sector_title']}",
            class_character=ClassCharacter.BOURGEOIS,
            sector=sector["sector_title"],
            naics_2digit=sector["naics_2digit"],
            employment_count=sector["employment_count"],
            territory_ids=list(territory_ids),
        )
    return businesses


__all__ = ["ARTIFACT_PATH", "build_seeded_businesses", "load_seed_data"]
