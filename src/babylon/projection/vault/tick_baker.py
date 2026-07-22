"""The county tick-baker — the vault's tick-commit adapter.

Satisfies the engine's ``TickCommitObserver`` seam *structurally* (duck
typing): the engine's tick loop calls ``on_tick_committed`` on whatever it
was handed, so this module composes :func:`babylon.projection.county.
project_county` with :class:`~babylon.projection.vault.materializer.
VaultMaterializer` without importing the engine — the projection layer's
import contract stays intact, and the composition root (an integration
test today, the client boot later) is the only place both sides meet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums.topology import NodeType
from babylon.projection.community import project_community
from babylon.projection.county import project_county
from babylon.projection.economy import project_economy
from babylon.projection.faction import project_faction
from babylon.projection.field_state import project_field_state
from babylon.projection.industry import project_industry
from babylon.projection.institution import project_institution
from babylon.projection.national import project_national
from babylon.projection.organization import project_organization
from babylon.projection.social_class import project_social_class
from babylon.projection.sovereign import project_sovereign
from babylon.projection.state import project_state
from babylon.projection.vault.render import render_county, render_sovereign
from babylon.projection.vault.render_community import render_community
from babylon.projection.vault.render_economy import render_economy
from babylon.projection.vault.render_faction import render_faction
from babylon.projection.vault.render_field_state import render_field_state
from babylon.projection.vault.render_industry import render_industry
from babylon.projection.vault.render_institution import render_institution
from babylon.projection.vault.render_national import render_national
from babylon.projection.vault.render_organization import render_organization
from babylon.projection.vault.render_social_class import render_social_class
from babylon.projection.vault.render_state import render_state

if TYPE_CHECKING:
    from babylon.projection.vault.materializer import VaultMaterializer

__all__ = ["ArchiveTickBaker", "CountyTickBaker"]

#: The one national dossier id (NATIONWIDE canonical scale, Amendment R/S).
_NATIONAL_ID = "USA"

#: The one economy dossier id (T3 spine-C singleton, mirrors _NATIONAL_ID).
_ECONOMY_ID = "USA"

#: The one field-state dossier id (T3 U3 singleton, mirrors _ECONOMY_ID).
_FIELD_STATE_ID = "USA"


def _node_ids(graph: Any, node_type: NodeType) -> list[str]:
    """Sorted node ids of one type — deterministic enumeration order."""
    return sorted(node.id for node in graph.query_nodes(node_type=node_type.value))


def _community_ids(world: Any) -> list[str]:
    """Sorted distinct community ids across active entities' memberships.

    Communities are never graph nodes (Amendment U — the lattice is a
    projection); their id universe is exactly the ``CommunityType`` values
    present in ``community_memberships``.
    """
    seen: set[str] = set()
    for entity in world.entities.values():
        if not getattr(entity, "active", True):
            continue
        for membership in getattr(entity, "community_memberships", ()) or ():
            community_type = (
                membership.get("community_type")
                if isinstance(membership, dict)
                else getattr(membership, "community_type", None)
            )
            if community_type is not None:
                seen.add(
                    community_type.value
                    if hasattr(community_type, "value")
                    else str(community_type)
                )
    return sorted(seen)


class CountyTickBaker:
    """Bake a fixed set of county dossiers at every committed tick.

    :param materializer: The vault materializer to bake through.
    :param county_fips: The county FIPS codes to project and bake each
        tick, processed in sorted order for deterministic vault history.
    """

    def __init__(self, materializer: VaultMaterializer, county_fips: tuple[str, ...]) -> None:
        self._materializer = materializer
        self._county_fips = tuple(sorted(county_fips))

    def on_tick_committed(self, *, tick: int, world: Any, graph: Any) -> None:
        """Project and bake every configured county for a committed tick.

        Read-only over ``world``/``graph`` per the observer contract; all
        writes go to the vault repository — as ONE commit for the whole
        tick, with byte-identical pages skipped
        (:meth:`~babylon.projection.vault.materializer.VaultMaterializer.
        bake_tick`, the WO-44 vault-at-scale contract).

        :param tick: The committed tick number.
        :param world: The post-tick world state.
        :param graph: The post-tick engine graph.
        """
        pages: dict[str, str] = {}
        for fips in self._county_fips:
            view = project_county(fips, graph=graph, world=world, tick=tick)
            pages[f"county/{view.county_fips}.md"] = render_county(view, verified_tick=tick)
        self._materializer.bake_tick(pages, tick=tick)


class ArchiveTickBaker:
    """Bake EVERY enumerable kind's dossiers at every committed tick (WO-44 §4).

    The per-kind composition over the Lane P estate: counties from the
    configured scope, states from the scope's FIPS prefixes, the national
    dossier, graph-enumerated organizations / institutions / sovereigns /
    factions / industries / social classes, and membership-enumerated
    communities — all rendered into ONE pages dict and landed as ONE
    content-hash-skipped commit per tick (:meth:`~babylon.projection.vault.
    materializer.VaultMaterializer.bake_tick`). Key figures bake nothing: the
    kind has no producer, so there are no ids to enumerate (honest absence).
    Factions bake nothing in every current scenario for a related but
    distinct reason: the node type has a real producer
    (``WorldState.to_graph()``), but no ``babylon.engine.scenarios`` builder
    populates ``WorldState.factions`` — only the legacy web bridge's
    ``_seed_balkanization_layer`` does (Bridge-layer only) — so
    ``_node_ids(graph, NodeType.FACTION)`` is honestly empty for a headless
    campaign today; that is a scenario-coverage gap, not a bug (see
    :mod:`babylon.projection.faction`'s module docstring).

    Read-only over ``world``/``graph`` per the observer contract; page
    ordering inside the commit is sorted-path (the materializer's own
    determinism rule), and every id enumeration here is sorted.

    :param materializer: The vault materializer to bake through.
    :param county_fips: The county FIPS codes in scope.
    """

    def __init__(self, materializer: VaultMaterializer, county_fips: tuple[str, ...]) -> None:
        self._materializer = materializer
        self._county_fips = tuple(sorted(county_fips))

    def on_tick_committed(self, *, tick: int, world: Any, graph: Any) -> None:
        """Project and bake every enumerable kind for one committed tick.

        :param tick: The committed tick number.
        :param world: The post-tick world state.
        :param graph: The post-tick engine graph.
        """
        pages: dict[str, str] = {}
        for fips in self._county_fips:
            county = project_county(fips, graph=graph, world=world, tick=tick)
            pages[f"county/{fips}.md"] = render_county(county, verified_tick=tick)
        for state_fips in sorted({fips[:2] for fips in self._county_fips}):
            state = project_state(state_fips, graph=graph, world=world, tick=tick)
            pages[f"state/{state_fips}.md"] = render_state(state, verified_tick=tick)
        national = project_national(_NATIONAL_ID, graph=graph, world=world, tick=tick)
        pages[f"national/{_NATIONAL_ID}.md"] = render_national(national, verified_tick=tick)
        economy = project_economy(_ECONOMY_ID, graph=graph, world=world, tick=tick)
        pages[f"economy/{_ECONOMY_ID}.md"] = render_economy(economy, verified_tick=tick)
        field_state = project_field_state(_FIELD_STATE_ID, graph=graph, tick=tick)
        pages[f"field_state/{_FIELD_STATE_ID}.md"] = render_field_state(
            field_state, verified_tick=tick
        )
        for org_id in _node_ids(graph, NodeType.ORGANIZATION):
            org = project_organization(org_id, graph=graph, world=world, tick=tick)
            pages[f"organization/{org_id}.md"] = render_organization(org, verified_tick=tick)
        for institution_id in _node_ids(graph, NodeType.INSTITUTION):
            institution = project_institution(institution_id, graph=graph, tick=tick)
            pages[f"institution/{institution_id}.md"] = render_institution(
                institution, verified_tick=tick
            )
        for sovereign_id in _node_ids(graph, NodeType.SOVEREIGN):
            sovereign = project_sovereign(sovereign_id, graph=graph, world=world, tick=tick)
            pages[f"sovereign/{sovereign_id}.md"] = render_sovereign(sovereign, verified_tick=tick)
        for faction_id in _node_ids(graph, NodeType.FACTION):
            faction = project_faction(faction_id, graph=graph, world=world, tick=tick)
            pages[f"faction/{faction_id}.md"] = render_faction(faction, verified_tick=tick)
        for industry_id in _node_ids(graph, NodeType.INDUSTRY):
            industry = project_industry(industry_id, graph=graph, world=world, tick=tick)
            pages[f"industry/{industry_id}.md"] = render_industry(industry, verified_tick=tick)
        for class_id in _node_ids(graph, NodeType.SOCIAL_CLASS):
            social_class = project_social_class(class_id, graph=graph, world=world, tick=tick)
            pages[f"social_class/{class_id}.md"] = render_social_class(
                social_class, verified_tick=tick
            )
        for community_id in _community_ids(world):
            community = project_community(community_id, world=world, tick=tick)
            pages[f"community/{community_id}.md"] = render_community(community, verified_tick=tick)
        self._materializer.bake_tick(pages, tick=tick)
