"""Unit tests for the shared tenancy-inversion seam (WO-52b, Unit T3/U5).

Covers the three functions hoisted/added to
:mod:`babylon.projection.territory_anchor` — the single non-underscore home
:mod:`babylon.projection.verbs.plate` and
:mod:`babylon.game.chronicle_adapter` both consume, replacing what used to
be two independent private copies (this one, and the legacy
``web/game/engine_bridge.py`` twin, which stays legacy/out of scope).
"""

from __future__ import annotations

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.territory_anchor import (
    TerritoryAnchor,
    class_to_territory,
    resolve_class_territory_anchor,
    tenancy_members_by_territory,
)
from babylon.topology import BabylonGraph


def _graph_with_tenancy() -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node("T001", NodeType.TERRITORY, name="Wayne County")
    graph.add_node("C001", NodeType.SOCIAL_CLASS, name="Periphery Proletariat")
    graph.add_edge("C001", "T001", EdgeType.TENANCY)
    return graph


def test_tenancy_members_by_territory_groups_social_class_occupants() -> None:
    """A TENANCY edge from a social_class node groups under its territory."""
    graph = _graph_with_tenancy()
    members = tenancy_members_by_territory(graph)
    assert members == {"T001": ["C001"]}


def test_tenancy_members_by_territory_ignores_non_tenancy_edges() -> None:
    """A non-TENANCY edge between a class and a territory-shaped node never
    contributes an entry — only the real TENANCY edge type counts."""
    graph = BabylonGraph()
    graph.add_node("T001", NodeType.TERRITORY, name="Wayne County")
    graph.add_node("C001", NodeType.SOCIAL_CLASS, name="Periphery Proletariat")
    graph.add_edge("C001", "T001", EdgeType.SOLIDARITY)
    assert tenancy_members_by_territory(graph) == {}


def test_tenancy_members_by_territory_ignores_non_social_class_sources() -> None:
    """A TENANCY-typed edge from a non-social_class source is not counted —
    the primitive is Occupant(social_class) -> Territory specifically."""
    graph = BabylonGraph()
    graph.add_node("T001", NodeType.TERRITORY, name="Wayne County")
    graph.add_node("org-1", NodeType.ORGANIZATION, name="A Union", territory_ids=["T001"])
    graph.add_edge("org-1", "T001", EdgeType.TENANCY)
    assert tenancy_members_by_territory(graph) == {}


def test_class_to_territory_inverts_one_to_one() -> None:
    """A single tenant class inverts cleanly to its one territory."""
    assert class_to_territory({"T001": ["C001"]}) == {"C001": "T001"}


def test_class_to_territory_deterministic_tie_break_lowest_territory_wins() -> None:
    """A class TENANCY-linked to more than one territory resolves to the
    lexicographically smallest territory id — deterministic, not
    insertion-order-dependent (mirrors the legacy bridge's own convention)."""
    tenancy_members = {"T002": ["C001"], "T001": ["C001"]}
    assert class_to_territory(tenancy_members) == {"C001": "T001"}


def test_class_to_territory_empty_when_no_tenancy() -> None:
    """No TENANCY edges at all inverts to an empty map — honest absence."""
    assert class_to_territory({}) == {}


def test_resolve_class_territory_anchor_resolves_real_name() -> None:
    """A resolvable class id yields a TerritoryAnchor carrying the
    territory's real display name."""
    graph = _graph_with_tenancy()
    mapping = class_to_territory(tenancy_members_by_territory(graph))
    anchor = resolve_class_territory_anchor(graph, mapping, "C001")
    assert anchor == TerritoryAnchor(
        territory_id="T001", territory_name="Wayne County", county_fips=None
    )


def test_resolve_class_territory_anchor_falls_back_to_id_without_a_name() -> None:
    """A territory node with no stamped ``name`` falls back to its own id —
    honest, never a fabricated human name."""
    graph = BabylonGraph()
    graph.add_node("T001", NodeType.TERRITORY, county_fips="26163")
    graph.add_node("C001", NodeType.SOCIAL_CLASS)
    graph.add_edge("C001", "T001", EdgeType.TENANCY)
    mapping = class_to_territory(tenancy_members_by_territory(graph))
    anchor = resolve_class_territory_anchor(graph, mapping, "C001")
    assert anchor == TerritoryAnchor(
        territory_id="T001", territory_name="T001", county_fips="26163"
    )


def test_resolve_class_territory_anchor_none_when_unresolvable() -> None:
    """A class id with no TENANCY edge into any territory yields ``None`` —
    never a fabricated anchor."""
    graph = _graph_with_tenancy()
    mapping = class_to_territory(tenancy_members_by_territory(graph))
    assert resolve_class_territory_anchor(graph, mapping, "C999") is None


class TestCountyFipsCarryThrough:
    """Unit "chronicle-row-nav-salience" (shell-interconnect): the anchor now
    also carries ``county_fips`` — read off the SAME territory node
    :func:`resolve_class_territory_anchor` already reads ``name`` from."""

    def test_a_territory_node_with_a_stamped_county_fips_carries_it_on_the_anchor(self) -> None:
        graph = _graph_with_tenancy()
        graph.update_node("T001", county_fips="26163")
        mapping = class_to_territory(tenancy_members_by_territory(graph))
        anchor = resolve_class_territory_anchor(graph, mapping, "C001")
        assert anchor is not None
        assert anchor.county_fips == "26163"

    def test_a_territory_node_with_no_stamped_county_fips_carries_none_honestly(self) -> None:
        """VERIFIED against a real live ``WayneCountyScenario`` graph
        (this unit's own recon probe): every one of Wayne's 81 H3-hex
        ``NodeType.TERRITORY`` nodes carries ``county_fips=None`` — this
        fixture mirrors that real, current shape, not a hypothetical one."""
        graph = _graph_with_tenancy()  # T001 stamped with no county_fips at all
        mapping = class_to_territory(tenancy_members_by_territory(graph))
        anchor = resolve_class_territory_anchor(graph, mapping, "C001")
        assert anchor is not None
        assert anchor.county_fips is None
