"""The industry read-model — ``project_industry`` (Program 24 P2, WO-22).

Assembles a :class:`~babylon.projection.view_models.IndustryView` dossier
from the post-tick world: the ``INDUSTRY``-typed graph node's attributes.
Transport-neutral by construction — no Django, no engine imports, no
database connection; callers hand in the graph and world they already hold.
Mirrors :mod:`babylon.projection.county` exactly (the keel-api extension
recipe), with one structural simplification: unlike a county dossier, which
composes several independent subsystem-sourced quantities, an industry has
exactly **one** producer for every field — the graph node itself — so
presence/absence collapses to a single binary gate (see
:class:`~babylon.projection.view_models.IndustryView`'s field-producer
table for the full ruling).

The imperial-rent/Leontief-adjacent quantities (``profit_rate``, ``occ``,
``department_weights``) are computed upstream by
``babylon.domain.economics.department_mapper.DepartmentMapper`` at
hydration time (``babylon.engine.hydration.reference.hydrate_industry_hyperedges``)
and stamped onto the graph node by ``WorldState.to_graph()``. This module
reads those already-computed values off the graph only — it never imports
``babylon.domain.economics`` or ``babylon.engine`` (``mise run
lint:imports``' "projection must not import the engine" contract, and the
transport-neutrality this package is chartered to keep).

Absence discipline (Constitution III.11): a graph carrying no ``INDUSTRY``
node for ``industry_id`` projects every non-identity field as ``None`` —
never a defaulted zero. A present-but-malformed value (e.g. a
``department_weights`` dict missing a required department) fails loud via
:class:`~babylon.projection.view_models.DepartmentComposition`'s validation,
never silently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums.topology import NodeType
from babylon.projection.view_models import DepartmentComposition, IndustryView

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.world_state import WorldState

__all__ = ["industry_statblocks", "project_industry"]


def project_industry(
    industry_id: str,
    *,
    graph: GraphProtocol,
    world: WorldState,  # noqa: ARG001 — kept for the uniform Lane-P project_<kind> signature (WO-45 dispatch); industry data lives entirely on the graph node, not in per-entity WorldState aggregation.
    tick: int,
) -> IndustryView:
    """Project one industry's post-tick state into an :class:`IndustryView`.

    Read strictly *post-tick*: systems mutate the shared graph in-place in
    strict order, so a mid-tick read would see a partially-applied world (not
    that any system currently mutates ``INDUSTRY`` nodes — none does — but
    the discipline is uniform across every Lane-P projector).

    :param industry_id: The graph node id, e.g. ``"ind_31-33"``.
    :param graph: The committed post-tick graph.
    :param world: The committed post-tick world state — accepted for
        signature parity with every other ``project_<kind>`` function (the
        future kind-dispatch registry, WO-45, calls them uniformly) but
        unused here: industry data has exactly one producer, the graph node.
    :param tick: The committed tick this dossier is projected from — becomes
        the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated industry dossier. Every field is
        ``None`` when no ``INDUSTRY`` node carries ``industry_id``.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type, or a present ``department_weights`` dict is
        malformed — a wrong value fails loud, only a *missing* node is
        absence.
    """
    node = graph.get_node(industry_id)
    attrs: dict[str, Any] = (
        node.attributes if node is not None and node.node_type == NodeType.INDUSTRY else {}
    )

    weights = attrs.get("department_weights")
    department_weights = DepartmentComposition(**weights) if weights else None

    county_fips_raw = attrs.get("county_fips")
    county_fips = tuple(sorted(county_fips_raw)) if county_fips_raw else None

    business_ids = attrs.get("member_business_ids")
    worker_block_ids = attrs.get("member_worker_block_ids")

    return IndustryView(
        industry_id=industry_id,
        verified_tick=tick,
        naics_2digit=attrs.get("naics_2digit"),
        naics_label=attrs.get("naics_label"),
        total_employment=attrs.get("total_employment"),
        total_wages=attrs.get("total_wages"),
        profit_rate=attrs.get("profit_rate"),
        occ=attrs.get("occ"),
        department_weights=department_weights,
        member_business_count=len(business_ids) if business_ids is not None else None,
        member_worker_block_count=(len(worker_block_ids) if worker_block_ids is not None else None),
        county_fips=county_fips,
    )


def industry_statblocks(subject: str) -> list[tuple[str, str]] | None:
    """The demo page's only industry statblock: ``industry/ind_31-33`` fixture rows.

    Mirrors ``babylon.tui.app._sample_statblocks``'s shape (a literal
    subject-id check, hardcoded rows) rather than importing
    ``babylon.tui.directives.StatblockProvider`` — the projection layer stays
    transport-neutral, so the return type is spelled out structurally
    (``list[tuple[str, str]] | None``, exactly ``StatblockRow``'s shape)
    instead of importing a ``tui``-side alias. Wave 2's WO-45 kind-dispatch
    registry wires this in with no change to either side. Live-graph wiring
    is WO-45's job; nothing here reads from a graph, a database, or a fixture
    file.

    :param subject: the statblock subject id.
    :returns: hardcoded rows for ``"industry/ind_31-33"``, else ``None``.
    """
    if subject != "industry/ind_31-33":
        return None
    return [
        ("naics_2digit", "31-33"),
        ("naics_label", "Manufacturing"),
        ("total_employment", "2,000"),
        ("occ", "2.000000"),
    ]
