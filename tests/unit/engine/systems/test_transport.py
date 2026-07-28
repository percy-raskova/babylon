"""Tests for TransportSystem (spec-108 slice 1, Program 26 U5e, position 9.5).

Default-OFF gate (``TransportDefines.enabled``, program-11's own
constraint): every test that wants live behavior must explicitly enable it.
No corridor mesh in ``context.persistent_data`` is an honest absence
(Constitution III.11) — the loader/composer seam is a separate, later unit
(mirrors ``vol2_step``'s own gated-no-op precedent, FR-108-10).
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines, TransportDefines
from babylon.domain.geography.corridor_mesh import CorridorMesh
from babylon.domain.geography.inventory import DefaultInfrastructureInventory
from babylon.domain.geography.types import InfrastructureLinkState
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.transport import TransportSystem, compute_overhang_delta
from babylon.models.enums import FlowCategory, InfrastructureType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _make_link(
    link_id: str, condition: float = 1.0, conductivity: float = 0.0
) -> InfrastructureLinkState:
    return InfrastructureLinkState(
        link_id=link_id,
        infra_type=InfrastructureType.HIGHWAY,
        capacity={FlowCategory.FREIGHT: 1.0},
        condition=condition,
        conductivity=conductivity,
    )


def _services(transport: TransportDefines) -> ServiceContainer:
    defines = GameDefines().model_copy(update={"transport": transport})
    return ServiceContainer.create(defines=defines)


def _graph_with_territory(territory_id: str) -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node(territory_id, _node_type="territory")
    return graph


class TestMasterGate:
    def test_disabled_is_a_full_no_op(self) -> None:
        graph = _graph_with_territory("T001")
        services = _services(TransportDefines(enabled=False))
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = CorridorMesh(
            inventory=DefaultInfrastructureInventory(),
            territory_hexes={"T001": frozenset({"h1"})},
        )

        TransportSystem().step(graph, services, context)

        assert "corridor_connectivity" not in context.persistent_data
        assert "transport_demand_signal" not in graph.nodes["T001"]

    def test_enabled_without_a_corridor_mesh_is_an_honest_no_op(self) -> None:
        """No mesh composed yet for this campaign (loader/composer seam is
        a separate unit) -- never a fabricated signal."""
        graph = _graph_with_territory("T001")
        services = _services(TransportDefines(enabled=True))
        context = TickContext(tick=1)

        TransportSystem().step(graph, services, context)

        assert "corridor_connectivity" not in context.persistent_data
        assert "transport_demand_signal" not in graph.nodes["T001"]


class TestDecayAndConnectivityPublication:
    def test_step_decays_links_and_publishes_connectivity(self) -> None:
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link("h1", "h2", _make_link("cross", condition=1.0))
        mesh = CorridorMesh(
            inventory=inventory,
            territory_hexes={"T001": frozenset({"h1"}), "T002": frozenset({"h2"})},
        )
        graph = _graph_with_territory("T001")
        graph.add_node("T002", _node_type="territory")
        services = _services(
            TransportDefines(
                enabled=True,
                condition_decay_rate_per_tick=0.05,
                condition_decay_flux_coefficient=0.01,
            )
        )
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = mesh

        TransportSystem().step(graph, services, context)

        assert mesh.inventory.get_edge_links("h1", "h2")[0].condition == pytest.approx(0.95)
        assert context.persistent_data["corridor_connectivity"] == {
            ("T001", "T002"): pytest.approx(0.95)
        }
        # The (mutated) mesh stays available for layer3's uniform-splash
        # consumption later this same tick (T6/ADR165 item 4).
        assert context.persistent_data["corridor_mesh"] is mesh


class TestDemandSignalPublication:
    def test_territory_with_touching_links_gets_a_demand_signal(self) -> None:
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link("h1", "h2", _make_link("degraded", condition=0.4, conductivity=0.9))
        mesh = CorridorMesh(inventory=inventory, territory_hexes={"T001": frozenset({"h1"})})
        graph = _graph_with_territory("T001")
        services = _services(TransportDefines(enabled=True, demand_signal_threshold=0.3))
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = mesh

        TransportSystem().step(graph, services, context)

        signal = graph.nodes["T001"]["transport_demand_signal"]
        assert signal > 0.0

    def test_territory_with_no_touching_links_is_untouched(self) -> None:
        mesh = CorridorMesh(
            inventory=DefaultInfrastructureInventory(),
            territory_hexes={"T001": frozenset({"h1"})},
        )
        graph = _graph_with_territory("T001")
        services = _services(TransportDefines(enabled=True))
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = mesh

        TransportSystem().step(graph, services, context)

        assert "transport_demand_signal" not in graph.nodes["T001"]

    def test_territory_not_present_in_the_graph_is_skipped_not_raised(self) -> None:
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link("h1", "h2", _make_link("l1"))
        mesh = CorridorMesh(
            inventory=inventory,
            territory_hexes={"GHOST": frozenset({"h1"})},
        )
        graph = BabylonGraph()  # GHOST is not a node in the graph at all
        services = _services(TransportDefines(enabled=True))
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = mesh

        TransportSystem().step(graph, services, context)  # must not raise


class TestComputeOverhangDelta:
    """T10's pure coupling function (D4) -- NOT yet wired into
    assess_circulation_crisis's call site; see CapitalVolumeIIDefines'
    transport_overhang_damping_coefficient docstring."""

    def test_zero_stranded_ratio_is_zero_delta(self) -> None:
        assert compute_overhang_delta(0.0, damping_coefficient=0.3) == 0.0

    def test_scales_by_the_damping_coefficient(self) -> None:
        assert compute_overhang_delta(0.5, damping_coefficient=0.3) == pytest.approx(0.15)

    def test_ratio_is_clamped_to_zero_one(self) -> None:
        assert compute_overhang_delta(2.0, damping_coefficient=0.5) == pytest.approx(0.5)
        assert compute_overhang_delta(-1.0, damping_coefficient=0.5) == pytest.approx(0.0)

    def test_step_stores_an_aggregate_overhang_delta_in_context(self) -> None:
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link("h1", "h2", _make_link("degraded", condition=0.2))
        mesh = CorridorMesh(inventory=inventory, territory_hexes={"T001": frozenset({"h1"})})
        graph = _graph_with_territory("T001")
        services = _services(TransportDefines(enabled=True))
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = mesh

        TransportSystem().step(graph, services, context)

        assert "transport_overhang_delta" in context.persistent_data
        assert context.persistent_data["transport_overhang_delta"] >= 0.0
