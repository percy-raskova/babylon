"""Composition calculators for organizations (Feature 031, T018-T019/T029).

Analyzes membership structure by querying MEMBERSHIP edges in the graph
to determine class, community, and lifecycle composition. Also computes
effective capacity weighted by lifecycle phase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.models.enums import EdgeType, resolve_edge_type
from babylon.organizations.types import CompositionResult

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph


def _membership_targets(org_id: str, G: BabylonGraph) -> list[tuple[str, float]]:
    """Extract (target_id, weight) for all MEMBERSHIP edges from org_id."""
    targets: list[tuple[str, float]] = []
    for _, target, data in G.out_edges(org_id, data=True):
        if resolve_edge_type(data.get("edge_type")) == EdgeType.MEMBERSHIP:
            weight = float(data.get("weight", 1.0))
            targets.append((target, weight))
    return targets


def _composition_by_attribute(
    org_id: str,
    G: BabylonGraph,
    attribute: str,
    axis: str,
) -> CompositionResult:
    """Generic composition calculator by node attribute on MEMBERSHIP targets."""
    targets = _membership_targets(org_id, G)
    if not targets:
        return CompositionResult(distribution={}, total_members=0.0, axis=axis)

    totals: dict[str, float] = {}
    total_weight = 0.0
    for target_id, weight in targets:
        node_data = G.nodes.get(target_id, {})
        attr_val = node_data.get(attribute, "unknown")
        if isinstance(attr_val, str):
            totals[attr_val] = totals.get(attr_val, 0.0) + weight
        total_weight += weight

    if total_weight <= 0:
        return CompositionResult(distribution={}, total_members=0.0, axis=axis)

    distribution = {k: v / total_weight for k, v in totals.items()}
    return CompositionResult(
        distribution=distribution,
        total_members=total_weight,
        axis=axis,
    )


def class_composition(org_id: str, G: BabylonGraph) -> CompositionResult:
    """Analyze class makeup of an organization via MEMBERSHIP edges.

    Args:
        org_id: Organization node ID.
        G: Graph containing organization and social class nodes.

    Returns:
        CompositionResult with class distribution proportions.
    """
    return _composition_by_attribute(org_id, G, "role", "class")


def community_composition(org_id: str, G: BabylonGraph) -> CompositionResult:
    """Analyze community makeup of an organization via MEMBERSHIP edges.

    Args:
        org_id: Organization node ID.
        G: Graph containing organization and social class nodes.

    Returns:
        CompositionResult with community distribution proportions.
    """
    return _composition_by_attribute(org_id, G, "community", "community")


def lifecycle_composition(org_id: str, G: BabylonGraph) -> CompositionResult:
    """Analyze lifecycle phase makeup of an organization via MEMBERSHIP edges.

    Args:
        org_id: Organization node ID.
        G: Graph containing organization and social class nodes.

    Returns:
        CompositionResult with lifecycle phase distribution proportions.
    """
    return _composition_by_attribute(org_id, G, "lifecycle_phase", "lifecycle")


def effective_capacity(
    lifecycle: CompositionResult,
    elder_capacity_factor: float,
) -> float:
    """Compute lifecycle-weighted effective capacity.

    Youth contribute zero capacity, adults contribute full (1.0),
    and elders contribute ``elder_capacity_factor`` (e.g., 0.2).

    Args:
        lifecycle: Result from lifecycle_composition().
        elder_capacity_factor: Capacity scalar for D'-phase members.

    Returns:
        Weighted capacity fraction in [0, 1].
    """
    if not lifecycle.distribution:
        return 0.0

    capacity_weights = {
        "youth": 0.0,
        "adult": 1.0,
        "elder": elder_capacity_factor,
    }

    total = 0.0
    for phase, fraction in lifecycle.distribution.items():
        weight = capacity_weights.get(phase, 0.0)
        total += fraction * weight

    return total
