"""Contract tests for :func:`babylon.projection.field_state.project_field_state`.

The field-state dossier's behavioral contract (T3 U3, the Weather Layer):
port of ``web/game/engine_bridge.py::EngineBridge.get_field_state`` into a
pure projection read-model — Systems #19/#20's per-social_class
``contradiction_fields``/``field_derivatives`` (laplacian/df_dt only,
d2f_dt2 excluded), FascistFactionSystem's ``fascist_alignment``,
FieldDerivativeSystem's per-edge ``field_gradients`` (TENANCY-anchored to a
territory), and the graph-level ``principal_field``/``dialectical_regime``
attrs. Fixture-fed — no engine tick, no database — per the keel's
fixture-first discipline. Test class name mirrors the retired
``TestGetFieldState`` GAP row (``specs/24-archive/test-port-ledger.md`` row
193).
"""

from __future__ import annotations

import pytest

from babylon.models.enums import EdgeType
from babylon.models.enums.topology import NodeType
from babylon.projection.field_state import project_field_state
from babylon.topology import BabylonGraph


class TestGetFieldStateNodes:
    """Per-social_class node readings: honest omission, id-sorted."""

    def test_no_node_carries_any_attr_is_honest_absence(self) -> None:
        view = project_field_state("USA", graph=BabylonGraph(), tick=1)

        assert view.nodes is None

    def test_node_carrying_only_fascist_alignment_is_included(self) -> None:
        graph = BabylonGraph()
        graph.add_node("C001", NodeType.SOCIAL_CLASS, fascist_alignment=0.3)
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.nodes is not None
        assert len(view.nodes) == 1
        node = view.nodes[0]
        assert node.node_id == "C001"
        assert node.fascist_alignment == pytest.approx(0.3)
        assert node.fields is None
        assert node.laplacian is None
        assert node.df_dt is None

    def test_nodes_are_sorted_by_id_independent_of_insertion_order(self) -> None:
        graph = BabylonGraph()
        graph.add_node("C002", NodeType.SOCIAL_CLASS, fascist_alignment=0.1)
        graph.add_node("C001", NodeType.SOCIAL_CLASS, fascist_alignment=0.2)
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.nodes is not None
        assert [n.node_id for n in view.nodes] == ["C001", "C002"]

    def test_node_name_falls_back_to_id_when_unattributed(self) -> None:
        graph = BabylonGraph()
        graph.add_node("C001", NodeType.SOCIAL_CLASS, fascist_alignment=0.0)
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.nodes is not None
        assert view.nodes[0].name == "C001"

    def test_node_name_reads_the_attributed_name(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "C001", NodeType.SOCIAL_CLASS, name="Periphery Proletariat", fascist_alignment=0.0
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.nodes is not None
        assert view.nodes[0].name == "Periphery Proletariat"

    def test_fields_hydrate_from_contradiction_fields(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            NodeType.SOCIAL_CLASS,
            contradiction_fields={"exploitation": 0.523, "atomization": 0.1},
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.nodes is not None
        assert view.nodes[0].fields == {"exploitation": 0.523, "atomization": 0.1}

    def test_laplacian_and_df_dt_only_include_present_sub_keys(self) -> None:
        """d2f_dt2 is deliberately excluded — out of this dossier's contract."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            NodeType.SOCIAL_CLASS,
            field_derivatives={
                "exploitation": {"laplacian": 0.4, "df_dt": None, "d2f_dt2": None},
                "atomization": {"laplacian": 0.0, "df_dt": 0.05, "d2f_dt2": 0.01},
            },
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.nodes is not None
        node = view.nodes[0]
        assert node.laplacian == {"exploitation": 0.4, "atomization": 0.0}
        assert node.df_dt == {"atomization": 0.05}

    def test_empty_field_derivatives_dict_yields_no_laplacian_or_df_dt(self) -> None:
        graph = BabylonGraph()
        graph.add_node("C001", NodeType.SOCIAL_CLASS, field_derivatives={})
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.nodes is None


class TestGetFieldStateEdges:
    """Per-(edge, field) gradient entries, TENANCY-territory-anchored, sorted."""

    def test_no_edge_carries_a_gradient_is_honest_absence(self) -> None:
        graph = BabylonGraph()
        graph.add_edge("C001", "C002", edge_type=EdgeType.SOLIDARITY, strength=0.5)
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.edges is None

    def test_one_entry_per_field_name_sorted(self) -> None:
        graph = BabylonGraph()
        graph.add_edge(
            "C001",
            "C002",
            edge_type=EdgeType.SOLIDARITY,
            field_gradients={"exploitation": 0.2, "atomization": -0.1},
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.edges is not None
        assert len(view.edges) == 2
        assert [e.field for e in view.edges] == ["atomization", "exploitation"]
        atomization_entry = next(e for e in view.edges if e.field == "atomization")
        assert atomization_entry.gradient == pytest.approx(-0.1)

    def test_edges_sorted_by_source_target_field(self) -> None:
        graph = BabylonGraph()
        graph.add_edge(
            "C002", "C003", edge_type=EdgeType.SOLIDARITY, field_gradients={"exploitation": 0.1}
        )
        graph.add_edge(
            "C001", "C002", edge_type=EdgeType.SOLIDARITY, field_gradients={"exploitation": 0.2}
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.edges is not None
        assert [(e.source, e.target) for e in view.edges] == [("C001", "C002"), ("C002", "C003")]

    def test_territory_anchored_via_tenancy_edges(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY)
        graph.add_edge("C001", "T001", edge_type=EdgeType.TENANCY)
        graph.add_edge("C002", "T001", edge_type=EdgeType.TENANCY)
        graph.add_edge(
            "C001", "C002", edge_type=EdgeType.SOLIDARITY, field_gradients={"exploitation": 0.2}
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.edges is not None
        entry = view.edges[0]
        assert entry.source_territory == "T001"
        assert entry.target_territory == "T001"

    def test_unresolved_territory_is_none_not_omitted(self) -> None:
        graph = BabylonGraph()
        graph.add_edge(
            "C001", "C002", edge_type=EdgeType.SOLIDARITY, field_gradients={"exploitation": 0.2}
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.edges is not None
        entry = view.edges[0]
        assert entry.source_territory is None
        assert entry.target_territory is None

    def test_tenancy_tiebreak_prefers_lexicographically_smallest_territory(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T002", NodeType.TERRITORY)
        graph.add_node("T001", NodeType.TERRITORY)
        graph.add_edge("C001", "T002", edge_type=EdgeType.TENANCY)
        graph.add_edge("C001", "T001", edge_type=EdgeType.TENANCY)
        graph.add_edge(
            "C001", "C002", edge_type=EdgeType.SOLIDARITY, field_gradients={"exploitation": 0.2}
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.edges is not None
        assert view.edges[0].source_territory == "T001"


class TestGetFieldStatePrincipalFieldAndRegime:
    """Graph-level principal_field/dialectical_regime, hydrated verbatim."""

    def test_principal_field_absent_when_graph_attr_unset(self) -> None:
        view = project_field_state("USA", graph=BabylonGraph(), tick=1)

        assert view.principal_field is None

    def test_principal_field_hydrates_verbatim(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            "principal_field",
            {"field_name": "exploitation", "max_abs_df_dt": 0.42, "changed": True},
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.principal_field is not None
        assert view.principal_field.field_name == "exploitation"
        assert view.principal_field.max_abs_df_dt == pytest.approx(0.42)
        assert view.principal_field.changed is True

    def test_principal_field_present_with_null_field_name_is_legitimate(self) -> None:
        """< 2 ticks of history: the attr is written but no principal chosen yet."""
        graph = BabylonGraph()
        graph.set_graph_attr(
            "principal_field", {"field_name": None, "max_abs_df_dt": 0.0, "changed": False}
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.principal_field is not None
        assert view.principal_field.field_name is None

    def test_dialectical_regime_absent_when_graph_attr_unset(self) -> None:
        view = project_field_state("USA", graph=BabylonGraph(), tick=1)

        assert view.dialectical_regime is None

    def test_dialectical_regime_hydrates_verbatim(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            "dialectical_regime",
            {"regime": "crisis", "opposition": "capital_labor", "rate": 0.07},
        )
        view = project_field_state("USA", graph=graph, tick=1)

        assert view.dialectical_regime is not None
        assert view.dialectical_regime.regime == "crisis"
        assert view.dialectical_regime.opposition == "capital_labor"
        assert view.dialectical_regime.rate == pytest.approx(0.07)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            NodeType.SOCIAL_CLASS,
            contradiction_fields={"exploitation": 0.5},
            fascist_alignment=0.2,
        )
        graph.add_edge(
            "C001", "C002", edge_type=EdgeType.SOLIDARITY, field_gradients={"exploitation": 0.1}
        )
        graph.set_graph_attr(
            "principal_field",
            {"field_name": "exploitation", "max_abs_df_dt": 0.1, "changed": False},
        )

        first = project_field_state("USA", graph=graph, tick=847)
        second = project_field_state("USA", graph=graph, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()
