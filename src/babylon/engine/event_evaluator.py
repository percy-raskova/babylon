"""Event Template evaluation engine.

Provides pure functions to evaluate EventTemplates against WorldState graphs.
This is NOT a System - it's a utility module used by Systems or the engine.

Sprint: Event Template System
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.entities.event_template import (
        EdgeCondition,
        EventTemplate,
        GraphCondition,
        NodeCondition,
        NodeFilter,
        PreconditionSet,
        Resolution,
    )


def _ensure_protocol(graph: GraphProtocol) -> GraphProtocol:
    """Validate that the graph satisfies GraphProtocol (fail loud)."""
    from babylon.kernel.graph_protocol import GraphProtocol

    if isinstance(graph, GraphProtocol):
        return graph
    raise TypeError(
        "raw networkx graphs are no longer supported; construct "
        f"babylon.topology.graph.BabylonGraph (got {type(graph).__name__})"
    )


def evaluate_template(
    template: EventTemplate,
    graph: GraphProtocol,
    current_tick: int,
) -> Resolution | None:
    """Evaluate an EventTemplate against the current graph state.

    Args:
        template: The EventTemplate to evaluate.
        graph: Graph representing WorldState.
        current_tick: Current simulation tick.

    Returns:
        The matching Resolution if preconditions met and a resolution matches,
        None otherwise.
    """
    graph = _ensure_protocol(graph)

    # Check cooldown
    if template.is_on_cooldown(current_tick):
        return None

    # Check preconditions
    if not evaluate_preconditions(template.preconditions, graph):
        return None

    # Find first matching resolution
    for resolution in template.resolutions:
        if resolution.condition is None or resolution.condition.is_empty():
            return resolution
        if evaluate_preconditions(resolution.condition, graph):
            return resolution

    return None


def evaluate_preconditions(
    preconditions: PreconditionSet,
    graph: GraphProtocol,
) -> bool:
    """Evaluate a PreconditionSet against the graph.

    Args:
        preconditions: Set of conditions to evaluate.
        graph: Graph to evaluate against.

    Returns:
        True if preconditions are satisfied, False otherwise.
    """
    graph = _ensure_protocol(graph)

    results: list[bool] = []

    for node_cond in preconditions.node_conditions:
        results.append(evaluate_node_condition(node_cond, graph))

    for edge_cond in preconditions.edge_conditions:
        results.append(evaluate_edge_condition(edge_cond, graph))

    for graph_cond in preconditions.graph_conditions:
        results.append(evaluate_graph_condition(graph_cond, graph))

    if not results:
        return True  # No conditions = always passes

    if preconditions.logic == "all":
        return all(results)
    else:
        return any(results)


def evaluate_node_condition(
    condition: NodeCondition,
    graph: GraphProtocol,
) -> bool:
    """Evaluate a NodeCondition against matching nodes.

    Args:
        condition: The node condition to evaluate.
        graph: Graph to evaluate against.

    Returns:
        True if condition is satisfied, False otherwise.
    """
    graph = _ensure_protocol(graph)

    matching_nodes = filter_nodes(graph, condition.node_filter)
    values: list[float] = []

    for node_id in matching_nodes:
        node = graph.get_node(node_id)
        node_data = node.attributes if node else {}
        value = get_nested_value(node_data, condition.path)
        if value is not None:
            values.append(value)

    if not values:
        return False

    return aggregate_and_compare(
        values,
        condition.aggregation,
        condition.operator,
        condition.threshold,
    )


def _collect_edge_value(
    edge_data: dict[str, Any],
    target_edge_type: EdgeType,
    metric: str,
) -> float | None:
    """Extract value from an edge if it matches the target type.

    Args:
        edge_data: Edge attributes dictionary.
        target_edge_type: EdgeType to match.
        metric: Metric to extract ("count", "sum_strength", "avg_strength").

    Returns:
        Edge value if matches, None otherwise.
    """
    edge_type = edge_data.get("edge_type")
    if isinstance(edge_type, str):
        try:
            edge_type = EdgeType(edge_type)
        except ValueError:
            return None

    if edge_type != target_edge_type:
        return None

    if metric == "count":
        return 1.0
    elif metric in ("sum_strength", "avg_strength"):
        return float(edge_data.get("solidarity_strength", 0.0))
    return None


def evaluate_edge_condition(
    condition: EdgeCondition,
    graph: GraphProtocol,
) -> bool:
    """Evaluate an EdgeCondition against edges.

    Args:
        condition: The edge condition to evaluate.
        graph: Graph to evaluate against.

    Returns:
        True if condition is satisfied, False otherwise.
    """
    graph = _ensure_protocol(graph)

    matching_nodes = filter_nodes(graph, condition.node_filter)

    edge_values: list[float] = []
    seen_edges: set[tuple[str, str]] = set()

    for node_id in matching_nodes:
        # Collect from both incoming and outgoing edges
        for edge in graph.query_edges():
            if edge.source_id != node_id and edge.target_id != node_id:
                continue

            edge_key = (edge.source_id, edge.target_id)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            # Build edge_data dict for _collect_edge_value compatibility
            edge_data = dict(edge.attributes)
            edge_data["edge_type"] = edge.edge_type

            value = _collect_edge_value(edge_data, condition.edge_type, condition.metric)
            if value is not None:
                edge_values.append(value)

    # Calculate result based on metric
    if condition.metric == "count":
        result = float(len(edge_values))
    elif condition.metric == "sum_strength":
        result = sum(edge_values)
    elif condition.metric == "avg_strength":
        result = sum(edge_values) / len(edge_values) if edge_values else 0.0
    else:
        result = 0.0

    return compare(result, condition.operator, condition.threshold)


def evaluate_graph_condition(
    condition: GraphCondition,
    graph: GraphProtocol,
) -> bool:
    """Evaluate a GraphCondition against graph-level metrics.

    Args:
        condition: The graph condition to evaluate.
        graph: Graph to evaluate against.

    Returns:
        True if condition is satisfied, False otherwise.
    """
    graph = _ensure_protocol(graph)

    value = calculate_graph_metric(graph, condition.metric)
    return compare(value, condition.operator, condition.threshold)


def _calculate_edge_density(graph: GraphProtocol, edge_type: EdgeType) -> float:
    """Calculate edge density for a specific edge type."""
    edge_count = sum(1 for edge in graph.query_edges(edge_type=edge_type))
    num_nodes = graph.count_nodes()
    max_edges = num_nodes * (num_nodes - 1)
    return edge_count / max_edges if max_edges > 0 else 0.0


def _get_social_nodes(graph: GraphProtocol) -> list[dict[str, Any]]:
    """Get all non-territory nodes from graph."""
    return [node.attributes for node in graph.query_nodes() if node.node_type != "territory"]


def _calculate_average_ideology_field(graph: GraphProtocol, field: str) -> float:
    """Calculate average of an ideology field across social nodes."""
    values = []
    for node_data in _get_social_nodes(graph):
        ideology = node_data.get("ideology", {})
        if isinstance(ideology, dict):
            values.append(ideology.get(field, 0.0))
    return sum(values) / len(values) if values else 0.0


def _calculate_gini(graph: GraphProtocol) -> float:
    """Calculate Gini coefficient for wealth distribution."""
    wealth_values = [data.get("wealth", 0.0) for data in _get_social_nodes(graph)]

    if not wealth_values or sum(wealth_values) == 0:
        return 0.0

    sorted_wealth = sorted(wealth_values)
    n = len(sorted_wealth)
    total = sum(sorted_wealth)
    cumulative = sum((2 * (i + 1) - n - 1) * w for i, w in enumerate(sorted_wealth))

    return cumulative / (n * total) if total > 0 else 0.0


def calculate_graph_metric(graph: GraphProtocol, metric: str) -> float:
    """Calculate a graph-level aggregate metric.

    Args:
        graph: Graph to analyze.
        metric: Name of the metric to calculate.

    Returns:
        The calculated metric value.
    """
    graph = _ensure_protocol(graph)

    # Dispatch table for metric calculations
    dispatch: dict[str, Any] = {
        "solidarity_density": lambda: _calculate_edge_density(graph, EdgeType.SOLIDARITY),
        "exploitation_density": lambda: _calculate_edge_density(graph, EdgeType.EXPLOITATION),
        "average_agitation": lambda: _calculate_average_ideology_field(graph, "agitation"),
        "average_consciousness": lambda: _calculate_average_ideology_field(
            graph, "class_consciousness"
        ),
        "total_wealth": lambda: sum(d.get("wealth", 0.0) for d in _get_social_nodes(graph)),
        "gini_coefficient": lambda: _calculate_gini(graph),
    }

    calculator = dispatch.get(metric)
    return calculator() if calculator else 0.0


def filter_nodes(
    graph: GraphProtocol,
    node_filter: NodeFilter | None,
) -> list[str]:
    """Filter nodes based on NodeFilter criteria.

    Args:
        graph: Graph containing nodes.
        node_filter: Filter criteria, or None for all nodes.

    Returns:
        List of node IDs matching the filter.
    """
    graph = _ensure_protocol(graph)

    if node_filter is None:
        return [node.id for node in graph.query_nodes()]

    result: list[str] = []
    for node in graph.query_nodes():
        # NodeFilter.matches() expects _node_type in the data dict
        node_data = dict(node.attributes)
        if node.node_type is not None:
            node_data["_node_type"] = node.node_type
        if node_filter.matches(node.id, node_data):
            result.append(node.id)

    return result


def get_nested_value(data: dict[str, Any], path: str) -> float | None:
    """Get a value from nested dict using dot notation.

    Follows the same pattern as TriggerCondition._get_nested_value.

    Args:
        data: Dictionary to search.
        path: Dot-notation path (e.g., ideology.agitation).

    Returns:
        The value as float, or None if not found.
    """
    keys = path.split(".")
    current: Any = data

    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif hasattr(current, key):
            current = getattr(current, key)
        else:
            return None

        if current is None:
            return None

    if isinstance(current, int | float):
        return float(current)
    if isinstance(current, str):
        try:
            return float(current)
        except ValueError:
            return None
    return None


def compare(value: float, operator: str, threshold: float) -> bool:
    """Apply comparison operator.

    Args:
        value: Value to compare.
        operator: Comparison operator.
        threshold: Threshold to compare against.

    Returns:
        True if comparison succeeds, False otherwise.
    """
    if operator == ">=":  # noqa: SIM116
        return value >= threshold
    elif operator == "<=":
        return value <= threshold
    elif operator == ">":
        return value > threshold
    elif operator == "<":
        return value < threshold
    elif operator == "==":
        return value == threshold
    elif operator == "!=":
        return value != threshold
    return False


def aggregate_and_compare(
    values: list[float],
    aggregation: str,
    operator: str,
    threshold: float,
) -> bool:
    """Aggregate values and compare to threshold.

    Args:
        values: List of values to aggregate.
        aggregation: Aggregation method.
        operator: Comparison operator.
        threshold: Threshold to compare against.

    Returns:
        True if aggregated comparison succeeds, False otherwise.
    """
    if aggregation == "any":
        return any(compare(v, operator, threshold) for v in values)
    elif aggregation == "all":
        return all(compare(v, operator, threshold) for v in values)
    elif aggregation == "count":
        return compare(float(len(values)), operator, threshold)
    elif aggregation == "sum":
        return compare(sum(values), operator, threshold)
    elif aggregation == "avg":
        return compare(sum(values) / len(values), operator, threshold)
    elif aggregation == "max":
        return compare(max(values), operator, threshold)
    elif aggregation == "min":
        return compare(min(values), operator, threshold)
    return False


def get_matching_nodes_for_resolution(
    template: EventTemplate,
    graph: GraphProtocol,
) -> list[str]:
    """Get nodes that match the template's node conditions.

    Used for ${node_id} substitution in resolution effects.

    Args:
        template: The EventTemplate being resolved.
        graph: Graph to search.

    Returns:
        List of node IDs that satisfy the node conditions.
    """
    graph = _ensure_protocol(graph)

    matching: set[str] = set()

    for node_cond in template.preconditions.node_conditions:
        filtered = filter_nodes(graph, node_cond.node_filter)
        for node_id in filtered:
            node = graph.get_node(node_id)
            node_data = node.attributes if node else {}
            value = get_nested_value(node_data, node_cond.path)
            if value is not None and compare(value, node_cond.operator, node_cond.threshold):
                matching.add(node_id)

    return list(matching)
