"""Social-class -> territory resolution — the shared tenancy-inversion seam.

The engine gives a social-class node no direct spatial field (``SocialClass``
carries no ``territory_ids`` — see the CLAUDE.md gotcha on stamped attribute
shape); its one live spatial link is the Occupant -> Territory ``TENANCY``
edge. Two independent call sites already needed the inversion of that edge
into a lookup table: the legacy web bridge's own
``web/game/engine_bridge.py::_tenancy_members_by_territory`` /
``_class_to_territory`` (event-anchoring for the map layer), and
:mod:`babylon.projection.verbs.plate`'s ``_tenancy_members_by_territory``
(verb-plate target-existence eligibility). This module is the ONE shared,
non-underscore home for that primitive (DRY) — :mod:`babylon.projection.
verbs.plate` and :mod:`babylon.game.chronicle_adapter` both consume it
rather than each carrying their own copy.

:func:`tenancy_members_by_territory` is the ported twin of ``plate.py``'s
own private implementation (byte-identical logic, hoisted here); the
inversion, :func:`class_to_territory`, follows the deterministic
sorted-first tie-break the legacy bridge's own ``_class_to_territory``
docstring establishes: territories and their members are walked in sorted
order, so the lexicographically smallest territory wins for the (currently
unseeded) case of a class carrying TENANCY edges into more than one
territory.

**County-FIPS carry-through (unit "chronicle-row-nav-salience",
shell-interconnect).** :class:`TerritoryAnchor` now also carries
``county_fips`` — read straight off the SAME territory node
:func:`resolve_class_territory_anchor` already reads ``name`` from, no
second lookup. This is what lets a consumer build a real, dispatchable
``"county/<fips>"`` subject id (:meth:`~babylon.game.session.GameSession.
subject_view`'s own ``kind == "county"`` branch) from an anchor, rather
than the bare, non-dispatchable territory node id alone.

**VERIFIED HONEST GAP**, not assumed: probed against a real, live
``WayneCountyScenario`` graph (``uv run python`` composition-root probe,
this unit's own recon) — every one of Wayne's 81 ``NodeType.TERRITORY``
nodes is an H3 hex (``territory_id`` values like
``"86274d35fffffff"``, never the legacy ``^T[0-9]{3}$`` id shape this
module's own tests still fixture), and EVERY one of them carries
``county_fips=None`` on the live graph — the hex↔county crosswalk lives in
the reference-data pipeline (``v_hex_state_asof``'s own ``county_fips``
column, ``projection/topology/hex_habitability.py``), never stamped onto
the runtime graph node itself. So on Wayne's own live data, a
:class:`TerritoryAnchor` resolved through this module always carries
``county_fips=None`` today — real, correct, and forward-compatible for any
territory node shape that DOES stamp it (this module's own fixtures, and
any future scenario/migration that does), but not yet a live win for
Wayne. A future unit that closes the hex→county crosswalk gap on the
runtime graph is this field's own natural completion, not fabricated here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.topology import BabylonGraph

__all__ = [
    "TerritoryAnchor",
    "tenancy_members_by_territory",
    "class_to_territory",
    "resolve_class_territory_anchor",
]


class TerritoryAnchor(BaseModel):
    """One resolved social-class -> territory anchor.

    :param territory_id: the resolved territory node id.
    :param territory_name: the territory's human-readable display name
        (``Territory.name``, or the raw ``territory_id`` itself when a
        fixture graph never stamped a name — an honest fallback, never a
        fabricated one).
    :param county_fips: the territory node's own ``county_fips`` attribute,
        or ``None`` when the node carries none (module docstring's
        "VERIFIED HONEST GAP" — true of every live Wayne territory node
        today). Never fabricated from ``territory_id`` — an absent value
        here means "no dispatchable county subject id is derivable from
        this anchor," not "assume the obvious one."
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    territory_id: str = Field(min_length=1)
    territory_name: str = Field(min_length=1)
    county_fips: str | None = None


def tenancy_members_by_territory(graph: BabylonGraph) -> dict[str, list[str]]:
    """Map territory id -> social-class occupants via TENANCY edges.

    Social classes carry no ``territory_ids`` field — their spatial link is
    the Occupant -> Territory TENANCY edge (Track 1 / Task 8b). Ported
    verbatim from :mod:`babylon.projection.verbs.plate`'s own prior
    implementation (now hoisted here so both callers share one copy).

    :param graph: World graph (read-only).
    :returns: Territory id to occupant social-class ids, insertion-ordered.
    """
    members: dict[str, list[str]] = {}
    for source, target, data in graph.edges(data=True):
        if data.get("_edge_type") == EdgeType.TENANCY:
            source_type = graph.nodes[source].get("_node_type")
            if source_type == NodeType.SOCIAL_CLASS:
                members.setdefault(str(target), []).append(str(source))
    return members


def class_to_territory(tenancy_members: dict[str, list[str]]) -> dict[str, str]:
    """Invert :func:`tenancy_members_by_territory` to social_class -> territory.

    Deterministic tie-break: territories and their members are walked in
    sorted order, so the lexicographically smallest territory wins if a
    class somehow carries TENANCY edges into more than one territory (not
    seeded by any current scenario, but not structurally forbidden either)
    — the same convention ``web/game/engine_bridge.py::_class_to_territory``
    already established for the legacy map layer.

    :param tenancy_members: Output of :func:`tenancy_members_by_territory`
        (territory node id -> list of tenant social_class node ids).
    :returns: Map of social_class node id -> territory node id. A class with
        no TENANCY edge into any territory is simply absent — callers must
        treat a missing entry as unresolved, never a fabricated territory.
    """
    mapping: dict[str, str] = {}
    for territory_id in sorted(tenancy_members):
        for class_id in sorted(tenancy_members[territory_id]):
            mapping.setdefault(class_id, territory_id)
    return mapping


def resolve_class_territory_anchor(
    graph: BabylonGraph,
    class_to_territory_map: dict[str, str],
    class_id: str,
) -> TerritoryAnchor | None:
    """Resolve one social_class node id to its :class:`TerritoryAnchor`.

    :param graph: World graph (read-only) — read for the territory's
        display name only; membership itself comes from
        ``class_to_territory_map``.
    :param class_to_territory_map: Output of :func:`class_to_territory`,
        computed once per caller (never recomputed per-event).
    :param class_id: the social_class node id to resolve.
    :returns: the resolved anchor, or ``None`` when ``class_id`` carries no
        TENANCY edge into any territory (honest absence — never a
        fabricated territory).
    """
    territory_id = class_to_territory_map.get(class_id)
    if territory_id is None:
        return None
    node = graph.nodes.get(territory_id, {})
    territory_name = node.get("name")
    county_fips = node.get("county_fips")
    return TerritoryAnchor(
        territory_id=territory_id,
        territory_name=str(territory_name) if territory_name else territory_id,
        county_fips=str(county_fips) if county_fips else None,
    )
