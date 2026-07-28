"""Corridor mesh: territory-indexed view over the infrastructure inventory.

Spec-108 (Transport Substrate, Constitution II.13/Amendment O), slice 1
engine-step (Program 26 U5e). Per D1 this reuses --
never duplicates -- :class:`~babylon.domain.geography.types.InfrastructureLinkState`
and :class:`~babylon.domain.geography.inventory.DefaultInfrastructureInventory`.

**Scope note (deviation from FR-108-2's full description, recorded per this
worktree's escalation discipline):** FR-108-2 describes a SPARSE res-8 mesh
assembled from Natural Earth/HPMS/NTAD linear-feature ingestion. Those
loaders are a separate, later data-pipeline unit (spec-108's own Data
Contract table: "loader still needed" for road condition and freight; loaders
"live in the babylon-data repo per the standing owner ruling"). This module
does NOT ingest that geodata -- it provides the territory-splash
reconciliation (ADR165 Director ruling 4) and connectivity-aggregation
(ADR165 item 5) logic as PURE functions over whatever
:class:`~babylon.domain.geography.inventory.DefaultInfrastructureInventory`
a future loader/composer populates, plus a ``territory_hexes`` mapping a
future session/persistence caller supplies (mirrors the
``read_hex_county_adjunction(runtime, session_id)`` seam FR-108-10 names for
``Vol2CirculationStep``). An inventory with zero links is the honest default
(Constitution III.11) -- every function here degrades gracefully to
``{}``/``0``, never a fabricated nonzero.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from babylon.domain.geography.inventory import DefaultInfrastructureInventory
from babylon.domain.geography.types import InfrastructureLinkState
from babylon.models.enums import FlowCategory


@dataclass
class CorridorMesh:
    """A corridor-edge inventory plus the territory-hex index it needs
    for territory-scoped operations (uniform splash, connectivity
    aggregation).

    Attributes:
        inventory: The (possibly empty) infrastructure link inventory --
            D1's reused DTO, unmodified in shape.
        territory_hexes: Mapping of territory/county id (e.g. a FIPS code)
            to the frozenset of H3 cell ids belonging to it. Supplied by the
            caller (production: a hex/county adjunction read, e.g.
            ``persistence/hex_hydrator.py::read_hex_county_adjunction``;
            tests: a small fixture dict) -- this module never queries a
            database itself.
    """

    inventory: DefaultInfrastructureInventory
    territory_hexes: Mapping[str, frozenset[str]] = field(default_factory=dict)


def _reverse_hex_index(territory_hexes: Mapping[str, frozenset[str]]) -> dict[str, list[str]]:
    """Hex id -> sorted list of territory ids that claim it (deterministic)."""
    reverse: dict[str, list[str]] = {}
    for territory_id in sorted(territory_hexes):
        for hex_id in territory_hexes[territory_id]:
            reverse.setdefault(hex_id, []).append(territory_id)
    return reverse


def _touching_links(mesh: CorridorMesh, territory_id: str) -> list[InfrastructureLinkState]:
    """All links on edges with at least one endpoint hex in ``territory_id``.

    Sorted, deterministic iteration (Constitution III.7): edges sorted by
    canonical key, links within an edge in inventory-insertion order.
    """
    hexes = mesh.territory_hexes.get(territory_id)
    if not hexes:
        return []
    links: list[InfrastructureLinkState] = []
    for source_h3, target_h3 in sorted(mesh.inventory.get_all_edges()):
        if source_h3 in hexes or target_h3 in hexes:
            links.extend(mesh.inventory.get_edge_links(source_h3, target_h3))
    return links


def touching_link_ids(mesh: CorridorMesh, territory_id: str) -> list[str]:
    """Sorted link ids on every corridor edge touching ``territory_id``.

    Empty for a territory with no registered hexes or no touching edges
    (honest absence, never an error -- a territory legitimately outside the
    slice-1 corridor mesh's coverage area).
    """
    return sorted(link.link_id for link in _touching_links(mesh, territory_id))


def apply_uniform_territory_splash(
    mesh: CorridorMesh,
    territory_id: str,
    condition_delta: float,
) -> int:
    """Uniformly adjust condition on every corridor link touching a territory.

    ADR165 Director ruling 4 (spec-108 FR-108-5 "Director ruling required
    item 4"): a BUILD/ATTACK_INFRASTRUCTURE action resolved against a
    Territory degrades or restores ALL corridor edges touching it uniformly
    -- edge-targeted splash is out of scope for slice 1 (it needs an
    ``Action.target_id`` resolving to a corridor edge rather than a
    Territory, an ``Action`` schema change that is amendment-gated per
    spec-108's non-goals).

    Args:
        mesh: The corridor mesh.
        territory_id: Territory whose touching edges are adjusted.
        condition_delta: Signed delta applied to every touching link's
            condition (positive = repair/construction, negative = damage).
            Delegates the clamp-to-[0,1] and per-link mutation to
            :meth:`DefaultInfrastructureInventory.adjust_link_condition`.

    Returns:
        Count of links adjusted (0 for an unknown/uncovered territory).
    """
    link_ids = touching_link_ids(mesh, territory_id)
    for link_id in link_ids:
        mesh.inventory.adjust_link_condition(link_id, condition_delta)
    return len(link_ids)


def decay_all_links(
    mesh: CorridorMesh,
    decay_rate_per_tick: float,
    flux_coefficient: float,
) -> int:
    """Apply base + flux-proportional condition decay to every link (US3).

    ``delta = -(decay_rate_per_tick + flux_coefficient * link.conductivity)``
    -- condition "degrades with use" (the flux term, using ``conductivity``
    as the ``|Q|`` proxy per spec-108 FR-108-3) "and neglect" (the base
    rate), matching FR-108-4's degradation text exactly. Disused corridors
    losing conductivity is the slime-mold decay term itself (a separate EMA
    update, not this function's job) -- FR-108-4 is explicit that this IS
    the disuse mechanic, no separate "abandonment" system.

    Args:
        mesh: The corridor mesh (mutated in place via the inventory).
        decay_rate_per_tick: Base per-tick decay (neglect).
        flux_coefficient: Additional decay scaled by each link's
            ``conductivity`` (use).

    Returns:
        Count of links decayed (0 for an empty mesh).
    """
    count = 0
    for source_h3, target_h3 in sorted(mesh.inventory.get_all_edges()):
        for link in mesh.inventory.get_edge_links(source_h3, target_h3):
            delta = -(decay_rate_per_tick + flux_coefficient * link.conductivity)
            mesh.inventory.adjust_link_condition(link.link_id, delta)
            count += 1
    return count


def aggregate_connectivity_by_county_pair(
    mesh: CorridorMesh,
) -> dict[tuple[str, str], float]:
    """Aggregate per-edge effective FREIGHT capacity into a per-county-pair
    connectivity coefficient.

    FR-108-2's stated aggregation target; ADR165 item 5 rules this
    aggregated indicator (not the underlying res-8 mesh) is what may surface
    in the Archive client's county dossier ("supply lines
    healthy/degraded/cut"). The session-reachable read: this function takes
    only a :class:`CorridorMesh` built from primitives (an inventory + a
    territory-hex mapping) -- no hidden global or session state -- so a
    future ``GameSession``/projection-layer caller can compose it directly
    without this unit touching ``game/session.py``.

    Only INTER-territory edges contribute (an edge whose two endpoint hexes
    belong to the same territory is not "connectivity between" anything);
    pair keys are lexicographically sorted so ``(a, b)`` and ``(b, a)``
    never both appear.

    Args:
        mesh: The corridor mesh.

    Returns:
        Mapping of sorted ``(territory_a, territory_b)`` to the summed
        effective FREIGHT capacity of every corridor edge connecting them.
        ``{}`` for an empty inventory or territory map -- an honest absence
        (Constitution III.11), never a fabricated coefficient.
    """
    reverse = _reverse_hex_index(mesh.territory_hexes)
    totals: dict[tuple[str, str], float] = {}
    for source_h3, target_h3 in sorted(mesh.inventory.get_all_edges()):
        source_territories = reverse.get(source_h3, [])
        target_territories = reverse.get(target_h3, [])
        if not source_territories or not target_territories:
            continue
        edge_capacity = sum(
            link.effective_capacity(FlowCategory.FREIGHT)
            for link in mesh.inventory.get_edge_links(source_h3, target_h3)
        )
        for t_a in source_territories:
            for t_b in target_territories:
                if t_a == t_b:
                    continue
                pair = (t_a, t_b) if t_a < t_b else (t_b, t_a)
                totals[pair] = totals.get(pair, 0.0) + edge_capacity
    return totals


__all__ = [
    "CorridorMesh",
    "aggregate_connectivity_by_county_pair",
    "apply_uniform_territory_splash",
    "decay_all_links",
    "touching_link_ids",
]
