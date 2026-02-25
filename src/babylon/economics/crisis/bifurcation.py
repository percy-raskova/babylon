"""Bifurcation risk calculator for crisis dynamics.

Feature: 018-crisis-devaluation-mechanics (FR-011 through FR-014)

Computes a George Jackson bifurcation risk metric during active crisis
that synthesizes solidarity topology, legitimation, and class burden
distribution into a directional score [-1, +1].

Score semantics:
    -1.0 = fully revolutionary trajectory
    +1.0 = fully fascist trajectory
     0.0 = neutral / non-crisis

Formula (FR-011):
    raw = -w_s * solidarity_density + w_b * class_burden_ratio
    dampened = raw * (1 - legitimation)
    score = clamp(dampened, -1, +1)

See Also:
    :mod:`babylon.economics.tick.types`: BifurcationRiskMetric, CrisisState
    :mod:`babylon.config.defines`: CrisisDefines (weights, epsilon)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from babylon.economics.tick.types import (
    BifurcationRiskMetric,
    CrisisPhase,
    CrisisState,
)
from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    from babylon.economics.dynamics.types import ClassDistribution
    from babylon.engine.graph_protocol import GraphProtocol


class BifurcationRiskCalculator:
    """Compute bifurcation risk during active crisis periods.

    Implements FR-011: Synthesizes cross-class solidarity density,
    legitimation index, and class burden ratio into a directional
    score [-1, +1].

    Args:
        solidarity_weight: Weight for solidarity in formula (w_s).
        burden_weight: Weight for class burden in formula (w_b).
        epsilon: Division-by-zero guard for burden ratio.

    Example:
        >>> calc = BifurcationRiskCalculator()
        >>> result = calc.compute(graph, "26163", crisis, prev, curr)
        >>> result.score  # -1 to +1
    """

    def __init__(
        self,
        solidarity_weight: float = 1.0,
        burden_weight: float = 1.0,
        epsilon: float = 0.001,
    ) -> None:
        self._w_s = solidarity_weight
        self._w_b = burden_weight
        self._epsilon = epsilon

    def compute(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        fips: str,
        crisis_state: CrisisState,
        previous_distribution: ClassDistribution,
        current_distribution: ClassDistribution,
    ) -> BifurcationRiskMetric:
        """Compute bifurcation risk metric for a county.

        Args:
            graph: Simulation graph with social class nodes and edges.
            fips: County FIPS code.
            crisis_state: Current crisis state.
            previous_distribution: Class distribution before transitions.
            current_distribution: Class distribution after transitions.

        Returns:
            BifurcationRiskMetric with score, components.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        # FR-011: Non-crisis returns neutral
        if crisis_state.phase == CrisisPhase.NORMAL:
            return BifurcationRiskMetric.neutral()

        # Compute components
        solidarity = self._compute_solidarity_density(graph, fips)
        legitimation = self._compute_legitimation(graph, fips)
        burden = self._compute_class_burden_ratio(
            previous_distribution,
            current_distribution,
        )

        # FR-011: Combination formula
        raw = -self._w_s * solidarity + self._w_b * burden
        dampened = raw * (1.0 - legitimation)
        score = max(-1.0, min(1.0, dampened))

        return BifurcationRiskMetric(
            score=score,
            solidarity_density=solidarity,
            legitimation=legitimation,
            class_burden_ratio=burden,
        )

    def _compute_solidarity_density(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        fips: str,
    ) -> float:
        """Compute cross-class solidarity density (FR-012).

        Fraction of possible cross-class SOLIDARITY edges that exist.
        Requires >= 2 distinct class categories; returns 0 otherwise.

        Args:
            graph: Simulation graph.
            fips: County FIPS code.

        Returns:
            Solidarity density [0, 1].
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        # Find social class nodes in this county
        county_nodes: list[tuple[str, str]] = []  # (node_id, role)
        for node in graph.query_nodes():
            if node.node_type != "social_class":
                continue
            attrs = node.attributes
            if attrs.get("territory") != fips:
                continue
            role = attrs.get("role", "")
            county_nodes.append((node.id, str(role)))

        # Need >= 2 distinct classes
        distinct_roles = {role for _, role in county_nodes}
        if len(distinct_roles) < 2:
            return 0.0

        # Count possible cross-class directed edges
        possible = 0
        for nid_a, role_a in county_nodes:
            for nid_b, role_b in county_nodes:
                if nid_a != nid_b and role_a != role_b:
                    possible += 1

        if possible == 0:
            return 0.0

        # Count actual cross-class SOLIDARITY edges
        actual = 0
        for nid_a, role_a in county_nodes:
            for nid_b, role_b in county_nodes:
                if nid_a == nid_b or role_a == role_b:
                    continue
                edge = graph.get_edge(nid_a, nid_b, EdgeType.SOLIDARITY)
                if edge is not None:
                    actual += 1

        return actual / possible

    def _compute_legitimation(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        fips: str,
    ) -> float:
        """Compute legitimation index (FR-013).

        legitimation = 1 - mean(agitation) across county social class nodes.

        Args:
            graph: Simulation graph.
            fips: County FIPS code.

        Returns:
            Legitimation index [0, 1].
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        agitations: list[float] = []
        for node in graph.query_nodes():
            if node.node_type != "social_class":
                continue
            attrs = node.attributes
            if attrs.get("territory") != fips:
                continue
            ideology = attrs.get("ideology", {})
            if isinstance(ideology, dict):
                agitation = ideology.get("agitation", 0.0)
            else:
                agitation = getattr(ideology, "agitation", 0.0)
            agitations.append(float(agitation))

        if not agitations:
            return 1.0  # No nodes = full legitimation (no agitation)

        mean_agitation = sum(agitations) / len(agitations)
        return max(0.0, min(1.0, 1.0 - mean_agitation))

    def _compute_class_burden_ratio(
        self,
        previous: ClassDistribution,
        current: ClassDistribution,
    ) -> float:
        """Compute class burden ratio (FR-014).

        |delta_LA| / max(|delta_Prol|, epsilon), clamped to [0, 1].

        Args:
            previous: Distribution before transitions.
            current: Distribution after transitions.

        Returns:
            Class burden ratio [0, 1].
        """
        delta_la = abs(previous.labor_aristocracy_share - current.labor_aristocracy_share)
        delta_prol = abs(previous.proletariat_share - current.proletariat_share)

        if delta_la == 0.0:
            return 0.0

        ratio = delta_la / max(delta_prol, self._epsilon)
        return min(ratio, 1.0)


__all__ = ["BifurcationRiskCalculator"]
