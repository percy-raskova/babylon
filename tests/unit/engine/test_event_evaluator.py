"""Unit tests for event template evaluation engine.

Tests the pure evaluation functions that check templates against WorldState graphs.

Sprint: Event Template System
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.event_evaluator import (
    aggregate_and_compare,
    calculate_graph_metric,
    compare,
    evaluate_edge_condition,
    evaluate_graph_condition,
    evaluate_node_condition,
    evaluate_preconditions,
    evaluate_template,
    filter_nodes,
    get_matching_nodes_for_resolution,
    get_nested_value,
)
from babylon.models.entities.event_template import (
    EdgeCondition,
    EventTemplate,
    GraphCondition,
    NodeCondition,
    NodeFilter,
    PreconditionSet,
    Resolution,
    TemplateEffect,
)
from babylon.models.enums import EdgeType, SocialRole


@pytest.fixture
def simple_graph() -> nx.DiGraph:
    """Create a simple test graph with two social class nodes."""
    g: nx.DiGraph = nx.DiGraph()

    g.add_node(
        "C001",
        _node_type="social_class",
        role="periphery_proletariat",
        wealth=50.0,
        organization=0.3,
        ideology={"class_consciousness": 0.4, "agitation": 0.7, "national_identity": 0.2},
    )

    g.add_node(
        "C002",
        _node_type="social_class",
        role="core_bourgeoisie",
        wealth=500.0,
        organization=0.1,
        ideology={"class_consciousness": 0.1, "agitation": 0.1, "national_identity": 0.5},
    )

    g.add_edge(
        "C002",
        "C001",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=50.0,
    )

    return g


@pytest.fixture
def solidarity_graph() -> nx.DiGraph:
    """Create a graph with solidarity edges."""
    g: nx.DiGraph = nx.DiGraph()

    g.add_node(
        "C001",
        _node_type="social_class",
        role="periphery_proletariat",
        wealth=50.0,
        ideology={"class_consciousness": 0.6, "agitation": 0.8},
    )

    g.add_node(
        "C002",
        _node_type="social_class",
        role="labor_aristocracy",
        wealth=200.0,
        ideology={"class_consciousness": 0.3, "agitation": 0.4},
    )

    g.add_node(
        "C003",
        _node_type="social_class",
        role="lumpenproletariat",
        wealth=20.0,
        ideology={"class_consciousness": 0.5, "agitation": 0.9},
    )

    # Two solidarity edges
    g.add_edge(
        "C001",
        "C002",
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=0.6,
    )

    g.add_edge(
        "C001",
        "C003",
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=0.8,
    )

    return g


class TestCompare:
    """Tests for the compare function."""

    def test_greater_than_or_equal(self) -> None:
        assert compare(5.0, ">=", 5.0) is True
        assert compare(6.0, ">=", 5.0) is True
        assert compare(4.0, ">=", 5.0) is False

    def test_less_than_or_equal(self) -> None:
        assert compare(5.0, "<=", 5.0) is True
        assert compare(4.0, "<=", 5.0) is True
        assert compare(6.0, "<=", 5.0) is False

    def test_greater_than(self) -> None:
        assert compare(6.0, ">", 5.0) is True
        assert compare(5.0, ">", 5.0) is False

    def test_less_than(self) -> None:
        assert compare(4.0, "<", 5.0) is True
        assert compare(5.0, "<", 5.0) is False

    def test_equal(self) -> None:
        assert compare(5.0, "==", 5.0) is True
        assert compare(5.1, "==", 5.0) is False

    def test_not_equal(self) -> None:
        assert compare(5.1, "!=", 5.0) is True
        assert compare(5.0, "!=", 5.0) is False


class TestGetNestedValue:
    """Tests for get_nested_value function."""

    def test_simple_path(self) -> None:
        data = {"wealth": 100.0}
        assert get_nested_value(data, "wealth") == 100.0

    def test_nested_path(self) -> None:
        data = {"ideology": {"agitation": 0.7}}
        assert get_nested_value(data, "ideology.agitation") == 0.7

    def test_deeply_nested(self) -> None:
        data = {"a": {"b": {"c": 42.0}}}
        assert get_nested_value(data, "a.b.c") == 42.0

    def test_missing_key_returns_none(self) -> None:
        data = {"wealth": 100.0}
        assert get_nested_value(data, "missing") is None

    def test_missing_nested_key_returns_none(self) -> None:
        data = {"ideology": {}}
        assert get_nested_value(data, "ideology.agitation") is None

    def test_integer_value_converted_to_float(self) -> None:
        data = {"count": 5}
        assert get_nested_value(data, "count") == 5.0


class TestAggregateAndCompare:
    """Tests for aggregate_and_compare function."""

    def test_any_aggregation(self) -> None:
        values = [0.3, 0.5, 0.7]
        assert aggregate_and_compare(values, "any", ">=", 0.6) is True
        assert aggregate_and_compare(values, "any", ">=", 0.8) is False

    def test_all_aggregation(self) -> None:
        values = [0.6, 0.7, 0.8]
        assert aggregate_and_compare(values, "all", ">=", 0.5) is True
        assert aggregate_and_compare(values, "all", ">=", 0.7) is False

    def test_count_aggregation(self) -> None:
        values = [0.1, 0.2, 0.3]
        assert aggregate_and_compare(values, "count", "==", 3.0) is True
        assert aggregate_and_compare(values, "count", ">=", 2.0) is True

    def test_sum_aggregation(self) -> None:
        values = [1.0, 2.0, 3.0]
        assert aggregate_and_compare(values, "sum", "==", 6.0) is True

    def test_avg_aggregation(self) -> None:
        values = [1.0, 2.0, 3.0]
        assert aggregate_and_compare(values, "avg", "==", 2.0) is True

    def test_max_aggregation(self) -> None:
        values = [1.0, 5.0, 3.0]
        assert aggregate_and_compare(values, "max", "==", 5.0) is True

    def test_min_aggregation(self) -> None:
        values = [1.0, 5.0, 3.0]
        assert aggregate_and_compare(values, "min", "==", 1.0) is True


class TestFilterNodes:
    """Tests for filter_nodes function."""

    def test_no_filter_returns_all_nodes(self, simple_graph: nx.DiGraph) -> None:
        result = filter_nodes(simple_graph, None)
        assert len(result) == 2
        assert "C001" in result
        assert "C002" in result

    def test_filter_by_node_type(self, simple_graph: nx.DiGraph) -> None:
        node_filter = NodeFilter(node_type="social_class")
        result = filter_nodes(simple_graph, node_filter)
        assert len(result) == 2

    def test_filter_by_role(self, simple_graph: nx.DiGraph) -> None:
        node_filter = NodeFilter(role=[SocialRole.PERIPHERY_PROLETARIAT])
        result = filter_nodes(simple_graph, node_filter)
        assert len(result) == 1
        assert "C001" in result

    def test_filter_by_id_pattern(self, simple_graph: nx.DiGraph) -> None:
        node_filter = NodeFilter(id_pattern=r"^C001$")
        result = filter_nodes(simple_graph, node_filter)
        assert len(result) == 1
        assert "C001" in result


class TestEvaluateNodeCondition:
    """Tests for evaluate_node_condition function."""

    def test_simple_condition_passes(self, simple_graph: nx.DiGraph) -> None:
        condition = NodeCondition(
            path="ideology.agitation",
            operator=">=",
            threshold=0.6,
            aggregation="any",
        )
        assert evaluate_node_condition(condition, simple_graph) is True

    def test_simple_condition_fails(self, simple_graph: nx.DiGraph) -> None:
        condition = NodeCondition(
            path="ideology.agitation",
            operator=">=",
            threshold=0.9,
            aggregation="any",
        )
        assert evaluate_node_condition(condition, simple_graph) is False

    def test_filtered_condition(self, simple_graph: nx.DiGraph) -> None:
        condition = NodeCondition(
            path="wealth",
            operator=">=",
            threshold=100.0,
            node_filter=NodeFilter(role=[SocialRole.CORE_BOURGEOISIE]),
            aggregation="any",
        )
        assert evaluate_node_condition(condition, simple_graph) is True

    def test_all_aggregation_fails_when_one_doesnt_match(self, simple_graph: nx.DiGraph) -> None:
        condition = NodeCondition(
            path="ideology.agitation",
            operator=">=",
            threshold=0.5,
            aggregation="all",
        )
        # C001 has 0.7, C002 has 0.1 - not all >= 0.5
        assert evaluate_node_condition(condition, simple_graph) is False


class TestEvaluateEdgeCondition:
    """Tests for evaluate_edge_condition function."""

    def test_count_exploitation_edges(self, simple_graph: nx.DiGraph) -> None:
        condition = EdgeCondition(
            edge_type=EdgeType.EXPLOITATION,
            metric="count",
            operator=">=",
            threshold=1.0,
        )
        assert evaluate_edge_condition(condition, simple_graph) is True

    def test_count_missing_edge_type(self, simple_graph: nx.DiGraph) -> None:
        condition = EdgeCondition(
            edge_type=EdgeType.SOLIDARITY,
            metric="count",
            operator=">=",
            threshold=1.0,
        )
        assert evaluate_edge_condition(condition, simple_graph) is False

    def test_solidarity_strength_sum(self, solidarity_graph: nx.DiGraph) -> None:
        condition = EdgeCondition(
            edge_type=EdgeType.SOLIDARITY,
            metric="sum_strength",
            operator=">=",
            threshold=1.0,  # 0.6 + 0.8 = 1.4
        )
        assert evaluate_edge_condition(condition, solidarity_graph) is True

    def test_solidarity_strength_avg(self, solidarity_graph: nx.DiGraph) -> None:
        condition = EdgeCondition(
            edge_type=EdgeType.SOLIDARITY,
            metric="avg_strength",
            operator=">=",
            threshold=0.6,  # (0.6 + 0.8) / 2 = 0.7
        )
        assert evaluate_edge_condition(condition, solidarity_graph) is True


class TestEvaluateGraphCondition:
    """Tests for evaluate_graph_condition function."""

    def test_solidarity_density(self, solidarity_graph: nx.DiGraph) -> None:
        condition = GraphCondition(
            metric="solidarity_density",
            operator=">",
            threshold=0.0,
        )
        assert evaluate_graph_condition(condition, solidarity_graph) is True

    def test_total_wealth(self, simple_graph: nx.DiGraph) -> None:
        condition = GraphCondition(
            metric="total_wealth",
            operator=">=",
            threshold=500.0,  # 50 + 500 = 550
        )
        assert evaluate_graph_condition(condition, simple_graph) is True

    def test_average_agitation(self, simple_graph: nx.DiGraph) -> None:
        condition = GraphCondition(
            metric="average_agitation",
            operator=">=",
            threshold=0.3,  # (0.7 + 0.1) / 2 = 0.4
        )
        assert evaluate_graph_condition(condition, simple_graph) is True


class TestCalculateGraphMetric:
    """Tests for calculate_graph_metric function."""

    def test_solidarity_density_zero_for_no_solidarity(self, simple_graph: nx.DiGraph) -> None:
        result = calculate_graph_metric(simple_graph, "solidarity_density")
        assert result == 0.0

    def test_solidarity_density_nonzero(self, solidarity_graph: nx.DiGraph) -> None:
        result = calculate_graph_metric(solidarity_graph, "solidarity_density")
        # 2 solidarity edges, 3 nodes, max_edges = 6
        assert result == pytest.approx(2.0 / 6.0)

    def test_average_consciousness(self, simple_graph: nx.DiGraph) -> None:
        result = calculate_graph_metric(simple_graph, "average_consciousness")
        # (0.4 + 0.1) / 2 = 0.25
        assert result == pytest.approx(0.25)


class TestEvaluatePreconditions:
    """Tests for evaluate_preconditions function."""

    def test_empty_preconditions_pass(self, simple_graph: nx.DiGraph) -> None:
        preconditions = PreconditionSet()
        assert evaluate_preconditions(preconditions, simple_graph) is True

    def test_all_logic_requires_all_conditions(self, simple_graph: nx.DiGraph) -> None:
        preconditions = PreconditionSet(
            node_conditions=[
                NodeCondition(
                    path="ideology.agitation",
                    operator=">=",
                    threshold=0.6,
                    aggregation="any",
                ),
                NodeCondition(
                    path="wealth",
                    operator=">=",
                    threshold=1000.0,  # This will fail
                    aggregation="any",
                ),
            ],
            logic="all",
        )
        assert evaluate_preconditions(preconditions, simple_graph) is False

    def test_any_logic_requires_one_condition(self, simple_graph: nx.DiGraph) -> None:
        preconditions = PreconditionSet(
            node_conditions=[
                NodeCondition(
                    path="ideology.agitation",
                    operator=">=",
                    threshold=0.6,
                    aggregation="any",
                ),
                NodeCondition(
                    path="wealth",
                    operator=">=",
                    threshold=1000.0,  # This will fail
                    aggregation="any",
                ),
            ],
            logic="any",
        )
        assert evaluate_preconditions(preconditions, simple_graph) is True


class TestEvaluateTemplate:
    """Tests for evaluate_template function."""

    def test_template_with_met_preconditions_returns_first_resolution(
        self, simple_graph: nx.DiGraph
    ) -> None:
        template = EventTemplate(
            id="EVT_test_template",
            name="Test Template",
            category="consciousness",
            preconditions=PreconditionSet(
                node_conditions=[
                    NodeCondition(
                        path="ideology.agitation",
                        operator=">=",
                        threshold=0.6,
                        aggregation="any",
                    ),
                ],
            ),
            resolutions=[
                Resolution(
                    id="first_resolution",
                    effects=[
                        TemplateEffect(
                            target_id="${node_id}",
                            attribute="wealth",
                            operation="increase",
                            magnitude=10.0,
                        ),
                    ],
                ),
            ],
        )

        result = evaluate_template(template, simple_graph, current_tick=0)
        assert result is not None
        assert result.id == "first_resolution"

    def test_template_with_unmet_preconditions_returns_none(self, simple_graph: nx.DiGraph) -> None:
        template = EventTemplate(
            id="EVT_test_template",
            name="Test Template",
            category="consciousness",
            preconditions=PreconditionSet(
                node_conditions=[
                    NodeCondition(
                        path="ideology.agitation",
                        operator=">=",
                        threshold=0.99,
                        aggregation="any",
                    ),
                ],
            ),
            resolutions=[
                Resolution(
                    id="first_resolution",
                    effects=[
                        TemplateEffect(
                            target_id="${node_id}",
                            attribute="wealth",
                            operation="increase",
                            magnitude=10.0,
                        ),
                    ],
                ),
            ],
        )

        result = evaluate_template(template, simple_graph, current_tick=0)
        assert result is None

    def test_template_on_cooldown_returns_none(self, simple_graph: nx.DiGraph) -> None:
        template = EventTemplate(
            id="EVT_test_template",
            name="Test Template",
            category="consciousness",
            preconditions=PreconditionSet(),
            resolutions=[
                Resolution(
                    id="first_resolution",
                    effects=[
                        TemplateEffect(
                            target_id="${node_id}",
                            attribute="wealth",
                            operation="increase",
                            magnitude=10.0,
                        ),
                    ],
                ),
            ],
            cooldown_ticks=5,
        )
        template.mark_triggered(tick=3)

        result = evaluate_template(template, simple_graph, current_tick=5)
        assert result is None

        # After cooldown expires
        result = evaluate_template(template, simple_graph, current_tick=8)
        assert result is not None

    def test_resolution_with_condition_selects_matching(self, solidarity_graph: nx.DiGraph) -> None:
        template = EventTemplate(
            id="EVT_bifurcation",
            name="Bifurcation",
            category="consciousness",
            preconditions=PreconditionSet(
                node_conditions=[
                    NodeCondition(
                        path="ideology.agitation",
                        operator=">=",
                        threshold=0.5,
                        aggregation="any",
                    ),
                ],
            ),
            resolutions=[
                Resolution(
                    id="low_solidarity",
                    condition=PreconditionSet(
                        graph_conditions=[
                            GraphCondition(
                                metric="solidarity_density",
                                operator="<",
                                threshold=0.1,
                            ),
                        ],
                    ),
                    effects=[
                        TemplateEffect(
                            target_id="${node_id}",
                            attribute="ideology.national_identity",
                            operation="increase",
                            magnitude=0.15,
                        ),
                    ],
                ),
                Resolution(
                    id="high_solidarity",
                    condition=PreconditionSet(
                        graph_conditions=[
                            GraphCondition(
                                metric="solidarity_density",
                                operator=">=",
                                threshold=0.1,
                            ),
                        ],
                    ),
                    effects=[
                        TemplateEffect(
                            target_id="${node_id}",
                            attribute="ideology.class_consciousness",
                            operation="increase",
                            magnitude=0.15,
                        ),
                    ],
                ),
            ],
        )

        result = evaluate_template(template, solidarity_graph, current_tick=0)
        assert result is not None
        # solidarity_graph has solidarity density > 0.1, so high_solidarity wins
        assert result.id == "high_solidarity"


class TestGetMatchingNodesForResolution:
    """Tests for get_matching_nodes_for_resolution function."""

    def test_returns_nodes_matching_conditions(self, simple_graph: nx.DiGraph) -> None:
        template = EventTemplate(
            id="EVT_test",
            name="Test",
            category="consciousness",
            preconditions=PreconditionSet(
                node_conditions=[
                    NodeCondition(
                        path="ideology.agitation",
                        operator=">=",
                        threshold=0.6,
                        aggregation="any",
                    ),
                ],
            ),
            resolutions=[
                Resolution(
                    id="res",
                    effects=[
                        TemplateEffect(
                            target_id="${node_id}",
                            attribute="wealth",
                            operation="increase",
                            magnitude=10.0,
                        ),
                    ],
                ),
            ],
        )

        matching = get_matching_nodes_for_resolution(template, simple_graph)
        assert "C001" in matching  # Has agitation 0.7 >= 0.6
        assert "C002" not in matching  # Has agitation 0.1 < 0.6
