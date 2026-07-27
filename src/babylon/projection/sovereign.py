"""The sovereign read-model — ``project_sovereign``, Program 24 P2 WO-20.

Assembles a :class:`~babylon.projection.view_models.SovereignView` dossier
from the post-tick graph's ``sovereign`` node (spec-070). Sovereign is the
CLAIMS-edge claimant :func:`babylon.projection.county._single_claimant`
already resolves for a county's ``sovereign_id`` field; this module is what
makes a county page's ``[[sovereign/<id>]]`` wikilink resolve to a real page,
plus the reverse direction — every county a sovereign claims, listed as
``[[county/<fips>]]`` backlinks.

Transport-neutral by construction, exactly like ``county.py``: no Django, no
engine imports, no database connection — the caller hands in the graph and
world it already holds.

**One producer per field:**

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``name``, ``sovereignty_type``, ``legitimacy``, ``ruling_faction_id``,
       ``extraction_policy``, ``capital_territory_id``, ``founded_tick``,
       ``dissolved_tick``
     - The ``sovereign`` graph node's own attributes — ``Sovereign.model_dump()``
       written by ``WorldState.to_graph()`` (spec-070). ``legitimacy`` is the
       same attribute ``CollapseTransitionSystem`` reads for the FR-023
       ``SOVEREIGN_COLLAPSE`` trigger, so this projection and that system
       never disagree about what "legitimacy" means.
   * - ``capital_county_fips``
     - Derived: the ``county_fips`` attribute of the territory node named by
       ``capital_territory_id``, resolved the same way a county page is
       addressed (``county/<fips>``) — never the raw territory node id.
   * - ``claimed_county_fips``
     - Derived: the ``county_fips`` of every territory reached by an
       outgoing CLAIMS edge from this sovereign — the *reverse* of
       ``project_county._single_claimant``, which walks CLAIMS edges from a
       territory to find its (single) claimant.

Absence discipline (Constitution III.11): a sovereign id with no matching
graph node projects every field as ``None`` — including ``claimed_county_fips``,
which is otherwise a *present* (possibly empty) tuple the instant the
sovereign node exists. An empty tuple ("claims nothing right now") and
``None`` ("this sovereign doesn't exist in this run") are deliberately
distinct: the former is real data, the latter is honest absence.

**Fixture-harvest finding (documented, not silently worked around):** the
keel's canonical Wave-1 harvest scenario, ``single_county``
(``babylon.engine.scenarios.create_single_county_scenario``), seeds **no**
``sovereign`` node and **no** CLAIMS edges — confirmed by
``tools/record_projection_fixtures.py``'s own docstring ("the scenario seeds
no CLAIMS edge, so sovereign_id is always None here"). (The stronger 2026-07-21
claim that NO scenario anywhere populates ``WorldState.sovereigns`` went stale
the next day: P25 U6's ``apply_balkanization_seed`` — called by the electoral
fixture — populates sovereigns + CLAIMS, and U9 adds ``SOV_MI_STATE`` + the
ADMINISTERS edge; ``single_county`` itself remains sovereign-free, so this
fixture's honest-absence reading still holds.) ``tools/record_sovereign_fixture.py`` therefore
ships the honest-absence fixture: it drives ``single_county`` for the same
5 ticks and projects the canonical seed sovereign id ``SOV_USA_FED``
(``babylon.data.game.balkanization.seed_sovereigns.json``), which this
scenario's graph genuinely does not contain. This is not a dead node type —
``NodeType.SOVEREIGN`` has real production writers (``WorldState.to_graph()``,
read by ``CollapseTransitionSystem``/``FactionInfluenceSystem``) — it is a
scenario-coverage gap, recorded here rather than papered over with an
invented seed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.vault.render import sovereign_statblock_rows
from babylon.projection.view_models import SovereignView

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode
    from babylon.models.world_state import WorldState

__all__ = ["project_sovereign", "sovereign_statblocks"]


def _resolve_sovereign(graph: GraphProtocol, sovereign_id: str) -> GraphNode | None:
    """Look up the sovereign node by its stable id.

    Unlike ``county.py``'s ``_resolve_territory`` (which matches on the
    ``county_fips`` *attribute* because "county" isn't a node id), a
    sovereign's node id already *is* its stable identity — a direct lookup.

    :param graph: The post-tick graph.
    :param sovereign_id: The sovereign's node id (``SOV_*``, spec-070).
    :returns: The matching node, or ``None`` when no such node exists — the
        sovereign hasn't been instantiated in this run, or the caller passed
        an id nobody has minted (e.g. a stale wikilink).
    """
    node = graph.get_node(sovereign_id)
    if node is None or node.node_type != NodeType.SOVEREIGN.value:
        return None
    return node


def _county_fips_of(graph: GraphProtocol, territory_id: str | None) -> str | None:
    """Resolve a territory node id to its ``county_fips`` attribute.

    Shared by both :func:`project_sovereign`'s ``capital_county_fips``
    derivation and :func:`_claimed_county_fips` — one lookup, two callers.

    :param graph: The post-tick graph.
    :param territory_id: A territory node id, or ``None``.
    :returns: The territory's ``county_fips``, or ``None`` when
        ``territory_id`` is ``None``, names no existing node, or the node
        carries no ``county_fips`` attribute — every case is honest
        absence, never a fabricated code.
    """
    if territory_id is None:
        return None
    territory = graph.get_node(territory_id)
    if territory is None:
        return None
    county_fips = territory.attributes.get("county_fips")
    return county_fips if isinstance(county_fips, str) else None


def _claimed_county_fips(graph: GraphProtocol, sovereign_id: str) -> tuple[str, ...]:
    """The county FIPS of every territory this sovereign CLAIMS.

    The reverse of ``project_county._single_claimant``: that function walks
    CLAIMS edges *from* a territory to find its (single) claimant; this one
    walks CLAIMS edges *from* a sovereign to find every territory it claims,
    resolved to the stable ``county_fips`` identity a county page is
    addressed by, never the raw territory node id.

    :param graph: The post-tick graph.
    :param sovereign_id: The claiming sovereign's node id.
    :returns: Sorted, de-duplicated county FIPS codes claimed by this
        sovereign — empty when the sovereign claims nothing (a real,
        present value; the caller substitutes ``None`` instead when the
        sovereign node itself does not exist).
    """
    claimed: set[str] = set()
    for edge in graph.query_edges(edge_type=EdgeType.CLAIMS):
        if edge.source_id != sovereign_id:
            continue
        county_fips = _county_fips_of(graph, edge.target_id)
        if county_fips is not None:
            claimed.add(county_fips)
    return tuple(sorted(claimed))


def project_sovereign(
    sovereign_id: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> SovereignView:
    """Project one sovereign's post-tick state into a :class:`SovereignView`.

    Read strictly *post-tick*, for the same reason ``project_county`` is:
    systems mutate the shared graph in-place in strict order, so a mid-tick
    read would see a partially-applied world.

    :param sovereign_id: The sovereign's node id (e.g. ``"SOV_USA_FED"``).
    :param graph: The committed post-tick graph.
    :param world: Unused — every ``SovereignView`` field is graph-node
        sourced (spec-070's ``Sovereign`` carries no world-entity
        aggregation the way county population/survival/consciousness do).
        Accepted anyway for signature parity with the Lane P
        ``project_<kind>(id, *, graph, world, tick)`` recipe every sibling
        projector (``project_county`` et al.) shares.
    :param tick: The committed tick this dossier is projected from —
        becomes the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated sovereign dossier. Every unattributed
        or nonexistent quantity is ``None``.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type — a wrong value fails loud, only a *missing*
        one is absence.
    """
    del world  # unused: see docstring above.
    node = _resolve_sovereign(graph, sovereign_id)
    attrs: dict[str, Any] = dict(node.attributes) if node else {}
    capital_territory_id = attrs.get("capital_territory_id")

    return SovereignView(
        sovereign_id=sovereign_id,
        verified_tick=tick,
        name=attrs.get("name"),
        sovereignty_type=attrs.get("sovereignty_type"),
        legitimacy=attrs.get("legitimacy"),
        ruling_faction_id=attrs.get("ruling_faction_id"),
        extraction_policy=attrs.get("extraction_policy"),
        capital_territory_id=capital_territory_id,
        capital_county_fips=_county_fips_of(graph, capital_territory_id),
        founded_tick=attrs.get("founded_tick"),
        dissolved_tick=attrs.get("dissolved_tick"),
        claimed_county_fips=_claimed_county_fips(graph, sovereign_id) if node else None,
    )


def sovereign_statblocks(
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> Callable[[str], list[tuple[str, str]] | None]:
    """Build a live ``{statblock}`` provider for ``sovereign/<id>`` subjects.

    The per-kind statblock provider the shared-file-discipline design rule
    requires (``specs/24-archive/work-orders-p2-p4.md``): this module
    registers nothing in ``babylon.tui.app`` itself — the single serial
    WO-45 composes every Lane P kind's provider into the app's kind-dispatch
    ``StatblockProvider`` registry. Live, not baked (design canon S3): a
    page whose ``{statblock}`` fence carries no baked body defers to
    exactly this kind of provider, by subject id
    (``tui.directives.BabylonFence._directive_statblock``).

    Deliberately does not import :mod:`babylon.tui` — the projection layer
    must not depend on its own client — so the returned callable matches
    ``tui.directives.StatblockProvider``'s shape *structurally*
    (``Callable[[str], Sequence[tuple[str, str]] | None]``) rather than by
    importing that type alias.

    :param graph: The live post-tick graph the caller already holds.
    :param world: Unused; see :func:`project_sovereign`. Accepted for
        signature parity with the other Lane P statblock-provider factories.
    :param tick: The tick this provider's projections are verified as of.
    :returns: A provider callable: for a ``"sovereign/<id>"`` subject whose
        id names a real sovereign node, the flattened statblock rows of its
        live projection; ``None`` for any other subject or an unknown id
        (the honest-absence path the ``{statblock}`` directive itself
        renders).
    """

    def provider(subject: str) -> list[tuple[str, str]] | None:
        prefix = "sovereign/"
        if not subject.startswith(prefix):
            return None
        sovereign_id = subject[len(prefix) :]
        if _resolve_sovereign(graph, sovereign_id) is None:
            return None
        view = project_sovereign(sovereign_id, graph=graph, world=world, tick=tick)
        return list(sovereign_statblock_rows(view))

    return provider
