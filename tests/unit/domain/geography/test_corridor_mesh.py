"""Tests for the corridor mesh (spec-108 slice 1, FR-108-2/FR-108-9).

``CorridorMesh`` is a territory-indexed VIEW over the existing
``DefaultInfrastructureInventory``/``InfrastructureLinkState`` DTOs (D1: reuse,
not replace) -- NOT the full NE/HPMS/NTAD-ingested SPARSE res-8 mesh FR-108-2
describes (that requires loaders this unit's forbidden-file fence and scope
don't cover; a declared, honestly-disclosed simplification). It provides the
uniform-territory-splash reconciliation (ADR165 Director ruling 4) and the
aggregated per-county-pair connectivity coefficient (ADR165 item 5) as pure,
deterministic functions over primitives a future session/persistence caller
supplies -- mirroring the ``read_hex_county_adjunction(runtime, session_id)``
seam pattern (spec-108 FR-108-10 names it for ``Vol2CirculationStep``).
"""

from __future__ import annotations

import pytest

from babylon.domain.geography.corridor_mesh import (
    CorridorMesh,
    aggregate_connectivity_by_county_pair,
    apply_uniform_territory_splash,
    decay_all_links,
    touching_link_ids,
)
from babylon.domain.geography.inventory import DefaultInfrastructureInventory
from babylon.domain.geography.types import InfrastructureLinkState
from babylon.models.enums import FlowCategory, InfrastructureType

pytestmark = pytest.mark.unit


def _make_link(
    link_id: str,
    condition: float = 1.0,
    conductivity: float = 0.0,
    freight_capacity: float = 1.0,
) -> InfrastructureLinkState:
    return InfrastructureLinkState(
        link_id=link_id,
        infra_type=InfrastructureType.HIGHWAY,
        capacity={FlowCategory.FREIGHT: freight_capacity},
        condition=condition,
        conductivity=conductivity,
    )


def _two_territory_mesh() -> CorridorMesh:
    """hex_a/hex_b belong to county_1; hex_c belongs to county_2.

    One cross-territory edge (hex_b, hex_c) carries a single link; one
    intra-territory edge (hex_a, hex_b) carries a second link.
    """
    inventory = DefaultInfrastructureInventory()
    inventory.add_edge_link("hex_a", "hex_b", _make_link("intra", condition=1.0))
    inventory.add_edge_link("hex_b", "hex_c", _make_link("cross", condition=0.8))
    return CorridorMesh(
        inventory=inventory,
        territory_hexes={
            "county_1": frozenset({"hex_a", "hex_b"}),
            "county_2": frozenset({"hex_c"}),
        },
    )


class TestTouchingLinkIds:
    def test_returns_links_on_edges_touching_the_territory(self) -> None:
        mesh = _two_territory_mesh()
        ids = touching_link_ids(mesh, "county_2")
        assert ids == ["cross"]

    def test_territory_with_two_hexes_sees_both_its_edges(self) -> None:
        mesh = _two_territory_mesh()
        ids = touching_link_ids(mesh, "county_1")
        assert ids == ["cross", "intra"]

    def test_unknown_territory_returns_empty(self) -> None:
        mesh = _two_territory_mesh()
        assert touching_link_ids(mesh, "nonexistent") == []


class TestUniformTerritorySplash:
    """ADR165 Director ruling 4: attacks/repairs on a territory degrade or
    restore ALL corridor edges touching it uniformly -- never edge-targeted
    in slice 1."""

    def test_negative_delta_damages_every_touching_link(self) -> None:
        mesh = _two_territory_mesh()
        count = apply_uniform_territory_splash(mesh, "county_1", -0.3)
        assert count == 2
        assert mesh.inventory.get_edge_links("hex_a", "hex_b")[0].condition == pytest.approx(0.7)
        assert mesh.inventory.get_edge_links("hex_b", "hex_c")[0].condition == pytest.approx(0.5)

    def test_positive_delta_repairs_every_touching_link(self) -> None:
        mesh = _two_territory_mesh()
        apply_uniform_territory_splash(mesh, "county_1", -0.5)
        count = apply_uniform_territory_splash(mesh, "county_1", 0.2)
        assert count == 2
        assert mesh.inventory.get_edge_links("hex_a", "hex_b")[0].condition == pytest.approx(0.7)

    def test_territories_not_touching_an_edge_are_unaffected(self) -> None:
        mesh = _two_territory_mesh()
        apply_uniform_territory_splash(mesh, "county_2", -1.0)
        # county_2 only touches "cross" -- "intra" must be untouched.
        assert mesh.inventory.get_edge_links("hex_a", "hex_b")[0].condition == pytest.approx(1.0)
        assert mesh.inventory.get_edge_links("hex_b", "hex_c")[0].condition == pytest.approx(0.0)

    def test_unknown_territory_is_a_safe_no_op(self) -> None:
        mesh = _two_territory_mesh()
        count = apply_uniform_territory_splash(mesh, "nonexistent", -1.0)
        assert count == 0


class TestDecayAllLinks:
    def test_base_decay_reduces_every_link(self) -> None:
        mesh = _two_territory_mesh()
        count = decay_all_links(mesh, decay_rate_per_tick=0.05, flux_coefficient=0.0)
        assert count == 2
        assert mesh.inventory.get_edge_links("hex_a", "hex_b")[0].condition == pytest.approx(0.95)

    def test_flux_term_scales_with_conductivity(self) -> None:
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link(
            "hex_a", "hex_b", _make_link("busy", condition=1.0, conductivity=0.5)
        )
        mesh = CorridorMesh(inventory=inventory, territory_hexes={})
        decay_all_links(mesh, decay_rate_per_tick=0.0, flux_coefficient=0.1)
        # delta = -(0.0 + 0.1 * 0.5) = -0.05
        assert mesh.inventory.get_edge_links("hex_a", "hex_b")[0].condition == pytest.approx(0.95)

    def test_empty_mesh_is_a_safe_no_op(self) -> None:
        mesh = CorridorMesh(inventory=DefaultInfrastructureInventory(), territory_hexes={})
        assert decay_all_links(mesh, 0.1, 0.1) == 0


class TestAggregateConnectivityByCountyPair:
    """FR-108-2's aggregation target / ADR165 item 5's Archive-client
    indicator -- the session-reachable read."""

    def test_cross_territory_edge_produces_a_sorted_pair_key(self) -> None:
        mesh = _two_territory_mesh()
        result = aggregate_connectivity_by_county_pair(mesh)
        assert result == {("county_1", "county_2"): pytest.approx(0.8)}

    def test_intra_territory_edges_are_excluded(self) -> None:
        """The "intra" edge connects two hexes both owned by county_1 --
        connectivity is inter-territory by definition, so it must not
        appear under any pair key."""
        mesh = _two_territory_mesh()
        result = aggregate_connectivity_by_county_pair(mesh)
        assert all(a != "county_1" or b != "county_1" for a, b in result)

    def test_empty_inventory_returns_empty_not_a_fabricated_zero(self) -> None:
        mesh = CorridorMesh(inventory=DefaultInfrastructureInventory(), territory_hexes={})
        assert aggregate_connectivity_by_county_pair(mesh) == {}

    def test_result_is_session_reachable_from_primitives_only(self) -> None:
        """Pins the access-path shape (spec-108 FR-108-2, ADR165 item 5):
        the function takes ONLY a CorridorMesh built from primitives a
        session/persistence caller already owns (an inventory + a
        territory-hex mapping) -- no hidden global or session state --
        mirroring ``read_hex_county_adjunction(runtime, session_id)``
        (``persistence/hex_hydrator.py``), the pattern FR-108-10 names for
        ``Vol2CirculationStep``. A future ``GameSession``-level read
        composes exactly this shape without this unit touching
        ``game/session.py`` directly.
        """
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link("h1", "h2", _make_link("l1", freight_capacity=2.0))
        mesh = CorridorMesh(
            inventory=inventory,
            territory_hexes={"a": frozenset({"h1"}), "b": frozenset({"h2"})},
        )
        result = aggregate_connectivity_by_county_pair(mesh)
        assert result == {("a", "b"): pytest.approx(2.0)}
