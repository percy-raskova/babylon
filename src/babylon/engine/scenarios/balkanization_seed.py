"""Headless balkanization seeding — the spec-070 political layer for
``engine.scenarios`` (P25 U6, ADR132; closes wiring-doctrine W-C row
"balkanization FACTION-node seeding").

Ports the disabled legacy web bridge's ``_seed_balkanization_layer`` into the
engine so ``NodeType.FACTION`` / ``NodeType.SOVEREIGN`` nodes and their
INFLUENCES / CLAIMS edges exist WITHOUT the web runtime: the projection layer
(``babylon.projection.faction``), ``FactionInfluenceSystem``'s
RED_SETTLER_TRAP / secession arms, ``ReactionarySystem``'s
FASCIST_RECRUITMENT capture arm, and the EndgameDetector's stance gates
(RED_OGV / REVOLUTIONARY_VICTORY / FASCIST_CONSOLIDATION-via-UPHOLD) all read
these shapes and were structurally inert in every headless scenario.

The seed data is county-FIPS-keyed (``seed_influences.json`` v2.0.0 and
``seed_sovereigns.json`` domestic claims — the U6 re-key). Resolution runs
through the ``county_fips`` ATTRIBUTE, never the node id (``Territory.id`` is
pattern-barred from ever being a FIPS; ``resolve_county_identity`` is the
engine-wide read path). Hex-grain territories without a stamped
``county_fips`` resolve via an explicit ``hex_to_county`` map (DI — this
module never queries the reference DB; the web bridge stamps wayne's FIPS
before seeding, so no current caller needs a map at all).

FR-040b fallback (ADR080): every territory the literal claims pass leaves
unclaimed falls to ``SOV_USA_FED`` (domestic federal, UPHOLD-aligned ruling
faction) — never ``SOV_EXTERIOR_NULL``, which stays reserved for genuinely
external nodes that are never scenario territories. This keeps SC-017 total
coverage while making every territory's sovereign stance-attributable from
tick 0.

Byte-safety: NOT applied by any of the six qa:regression scenario factories —
FACTION/SOVEREIGN nodes land only in the electoral/balkanization scenarios
(charter §U6(d)).
"""

from __future__ import annotations

from babylon.data.game.balkanization import (
    load_seed_factions,
    load_seed_influences,
    load_seed_sovereigns,
    load_seed_sovereigns_raw,
)
from babylon.models.entities.relationship import Relationship
from babylon.models.enums import EdgeType
from babylon.models.world_state import WorldState


def _fips_to_territories(
    state: WorldState,
    hex_to_county: dict[str, str],
) -> dict[str, list[str]]:
    """Map county FIPS -> sorted territory node ids that carry it.

    A territory resolves through its ``county_fips`` attribute when set,
    else through ``hex_to_county`` keyed by its ``h3_index``. Territories
    that resolve to neither (abstract fixture terrain like the two_node
    ``T001``) are simply absent — they still receive the FR-040b fallback
    claim, just no INFLUENCES.
    """
    mapping: dict[str, list[str]] = {}
    for territory_id, territory in sorted(state.territories.items()):
        fips = territory.county_fips or hex_to_county.get(territory.h3_index or "")
        if fips:
            mapping.setdefault(fips, []).append(territory_id)
    return mapping


def apply_balkanization_seed(
    state: WorldState,
    hex_to_county: dict[str, str] | None = None,
) -> WorldState:
    """Merge the spec-070 political layer into a scenario-built tick-0 state.

    Seeds the 4 canonical :class:`~babylon.models.entities.
    balkanization_faction.BalkanizationFaction` records and the 3 canonical
    :class:`~babylon.models.entities.sovereign.Sovereign` records, then
    builds edges from the county-FIPS-keyed seed data:

    - **INFLUENCES** (faction -> territory): each seed edge's county FIPS
      resolves to every territory carrying it; ``influence_level`` is an
      intensive [0, 1] quantity, so multiple hex territories in one county
      each receive the county's value verbatim (constant broadcast — the
      inverse of the retired hex->county mean aggregation, exact for an
      intensive).
    - **CLAIMS** (sovereign -> territory): a claim's ``territory_id``
      resolves by literal territory-key match (legacy contract, preserved)
      or by county FIPS. External-node claims (``canada`` /
      ``rest_of_usa``) match neither by design (ADR080) and skip. Every
      territory left unclaimed falls to ``SOV_USA_FED`` (FR-040b), so each
      territory carries exactly one seed CLAIMS edge.

    Args:
        state: The scenario-built tick-0 ``WorldState``.
        hex_to_county: Optional ``{h3_index: county_fips}`` map for
            hex-grain territories without a stamped ``county_fips``.
            ``None`` skips hex resolution; county-grain scenarios need no
            map at all.

    Returns:
        The state with factions/sovereigns/relationships merged in
        (``model_copy`` — the input is untouched).
    """
    factions = {f.id: f for f in load_seed_factions()}
    sovereigns = {s.id: s for s in load_seed_sovereigns()}
    by_fips = _fips_to_territories(state, hex_to_county or {})

    new_relationships: list[Relationship] = []
    for edge in load_seed_influences():
        for territory_id in by_fips.get(str(edge["territory_id"]), []):
            new_relationships.append(
                Relationship(
                    source_id=str(edge["faction_id"]),
                    target_id=territory_id,
                    edge_type=EdgeType.INFLUENCES,
                    influence_level=round(float(edge["influence_level"]), 6),
                    support_type=str(edge["support_type"]),
                )
            )

    claimed: set[str] = set()
    for record in load_seed_sovereigns_raw():
        for claim in record.get("initial_claims", []):
            claim_key = str(claim.get("territory_id", ""))
            targets = [claim_key] if claim_key in state.territories else by_fips.get(claim_key, [])
            for territory_id in targets:
                if territory_id in claimed:
                    continue
                new_relationships.append(
                    Relationship(
                        source_id=str(record["id"]),
                        target_id=territory_id,
                        edge_type=EdgeType.CLAIMS,
                        control_level=float(claim.get("control_level", 0.0)),
                        legal_status=str(claim.get("legal_status", "de_jure")),
                    )
                )
                claimed.add(territory_id)

    # FR-040b fallback (ADR080): unclaimed interior territories default to
    # the domestic federal sovereign. Deterministic iteration per III.7.
    for territory_id in sorted(state.territories):
        if territory_id in claimed:
            continue
        new_relationships.append(
            Relationship(
                source_id="SOV_USA_FED",
                target_id=territory_id,
                edge_type=EdgeType.CLAIMS,
                control_level=1.0,
                legal_status="de_jure",
            )
        )

    return state.model_copy(
        update={
            "factions": {**state.factions, **factions},
            "sovereigns": {**state.sovereigns, **sovereigns},
            "relationships": [*state.relationships, *new_relationships],
        }
    )


__all__ = ["apply_balkanization_seed"]
