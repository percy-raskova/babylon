"""Spec-070 initial-state coverage invariant test (T114, SC-017).

After seeding completes, for every in-scope Territory ``t``, the
following MUST hold:

    exists((f, t) in INFLUENCES with influence_level > 0)
    OR
    exists((SOV_EXTERIOR_NULL, t) in CLAIMS)

No in-scope Territory may be both un-influenced AND un-claimed at the
start of tick 1.

Since the proxy-data INFLUENCES seeding pipeline (T111-T113) is a
follow-up not yet committed in this branch, this test exercises the
invariant against an in-memory NetworkXAdapter seeded with the
canonical SOV_EXTERIOR_NULL Sovereign that catches the "un-influenced"
edge case per FR-040b.
"""

from __future__ import annotations

import pytest

from babylon.data.game.balkanization import (
    load_seed_factions,
    load_seed_sovereigns_raw,
)
from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

pytestmark = pytest.mark.integration


def _seed_state_with_exterior_null_fallback(
    territory_ids: list[str],
) -> NetworkXAdapter:
    """Build a NetworkXAdapter where SOV_EXTERIOR_NULL claims every
    in-scope Territory. Models the documented FR-040b behavior."""

    adapter = NetworkXAdapter()
    for faction in load_seed_factions():
        adapter.add_node(
            faction.id,
            "balkanization_faction",
            colonial_stance=faction.colonial_stance.value,
            class_reduction=faction.class_reduction,
            is_settler_formation=faction.is_settler_formation,
        )
    for record in load_seed_sovereigns_raw():
        adapter.add_node(
            record["id"],
            "sovereign",
            name=record["name"],
            sovereignty_type=record["sovereignty_type"],
            legitimacy=record["legitimacy"],
            color_hex=record["color_hex"],
            ruling_faction_id=record.get("ruling_faction_id"),
            extraction_policy=record["extraction_policy"],
            founded_tick=record["founded_tick"],
        )
    for territory_id in territory_ids:
        adapter.add_node(territory_id, "territory", habitability=0.8)
        # FR-040b fallback: SOV_EXTERIOR_NULL claims every otherwise-
        # unclaimed Territory at DE_JURE / control_level=1.0.
        adapter.add_edge(
            "SOV_EXTERIOR_NULL",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
            fiscal_status="taxed",
            recognition_level=1.0,
            claimed_since_tick=0,
        )
    return adapter


def _is_covered(adapter: NetworkXAdapter, territory_id: str) -> bool:
    influences = adapter.query_faction_influence_by_territory(territory_id)
    if any(row[1] > 0.0 for row in influences):
        return True
    claims = adapter.query_territory_claims(territory_id)
    return any(row[0] == "SOV_EXTERIOR_NULL" for row in claims)


def test_every_territory_is_influenced_or_exterior_null_claimed() -> None:
    """SC-017: post-seed coverage invariant."""

    territory_ids = [f"HEX_{i:05d}" for i in range(20)]
    adapter = _seed_state_with_exterior_null_fallback(territory_ids)

    uncovered = [tid for tid in territory_ids if not _is_covered(adapter, tid)]
    assert uncovered == [], (
        f"SC-017 violation: territories with neither INFLUENCES nor "
        f"SOV_EXTERIOR_NULL coverage: {uncovered}"
    )


def test_coverage_holds_when_partial_influences_seeded() -> None:
    """Adding a partial INFLUENCES seed must not break the invariant —
    territories with non-zero INFLUENCES are covered via that path,
    others via SOV_EXTERIOR_NULL."""

    territory_ids = [f"HEX_{i:05d}" for i in range(10)]
    adapter = _seed_state_with_exterior_null_fallback(territory_ids)
    # Add INFLUENCES to half the territories.
    for i in range(5):
        adapter.add_edge(
            "FAC_DECOLONIAL",
            territory_ids[i],
            "influences",
            influence_level=0.4,
            support_type="ideological",
        )
    uncovered = [tid for tid in territory_ids if not _is_covered(adapter, tid)]
    assert uncovered == []


def test_coverage_fails_loud_when_invariant_broken() -> None:
    """Sanity: if SOV_EXTERIOR_NULL is missing AND no INFLUENCES are
    seeded, the invariant correctly reports the violation."""

    adapter = NetworkXAdapter()
    adapter.add_node("HEX_ORPHAN", "territory")
    # No CLAIMS, no INFLUENCES — should be uncovered.
    assert not _is_covered(adapter, "HEX_ORPHAN")
