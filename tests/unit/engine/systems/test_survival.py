"""Tests for SurvivalSystem - The Calculus of Living.

Phase 4 Mass Line: P(Acquiescence) now uses per-capita wealth, not aggregate.

Before Phase 4: A block of 50k workers with $1000 total looked "wealthy"
After Phase 4: P(S|A) correctly sees $0.02 per capita (impoverished)

This completes the normalization pattern:
    VitalitySystem   → per-capita (mortality)
    ProductionSystem → aggregate × population (output)
    MetabolismSystem → aggregate × population (consumption)
    SurvivalSystem   → per-capita (P(S|A))  ← Phase 4
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.survival import SurvivalSystem
from babylon.models.enums import SocialRole

if TYPE_CHECKING:
    pass


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_entity_node(
    graph: nx.DiGraph,
    node_id: str,
    role: SocialRole = SocialRole.PERIPHERY_PROLETARIAT,
    wealth: float = 10.0,
    population: int = 1,
    active: bool = True,
    organization: float = 0.1,
    repression_faced: float = 0.5,
    subsistence_threshold: float | None = None,
) -> None:
    """Add an entity node to the graph with survival-relevant attributes.

    Args:
        graph: The graph to add the node to.
        node_id: Unique identifier for the node.
        role: Social role of the entity.
        wealth: Total aggregate wealth of the block.
        population: Number of individuals in the block.
        active: Whether the entity is alive/active.
        organization: Base organization level for P(S|R).
        repression_faced: Repression level faced by the entity.
        subsistence_threshold: Override for subsistence threshold (uses default if None).
    """
    node_data: dict = {
        "role": role,
        "wealth": wealth,
        "population": population,
        "active": active,
        "organization": organization,
        "repression_faced": repression_faced,
        "_node_type": "social_class",
    }
    if subsistence_threshold is not None:
        node_data["subsistence_threshold"] = subsistence_threshold
    graph.add_node(node_id, **node_data)


@pytest.mark.unit
class TestPopulationNormalization:
    """Phase 4: P(Acquiescence) uses per-capita wealth, not aggregate.

    Key insight: A demographic block of 50,000 starving workers with $1000 total
    should NOT look like a millionaire to the survival formula. Each worker has
    only $0.02 - deeply impoverished.

    Formula: wealth_per_capita = wealth / population
    """

    def test_higher_pop_lower_p_acquiescence(self, services: ServiceContainer) -> None:
        """50k workers with $1000 have lower P(S|A) than 1 worker with $1000.

        Single worker: wealth_per_capita = 1000/1 = 1000 → P(S|A) ≈ 1.0
        50k workers: wealth_per_capita = 1000/50000 = 0.02 → P(S|A) ≈ 0.0

        The sigmoid formula: P(S|A) = 1 / (1 + e^(-k(x - threshold)))
        At wealth >> threshold, P approaches 1.0
        At wealth << threshold, P approaches 0.0
        """
        graph: nx.DiGraph = nx.DiGraph()

        # Single worker with $1000 - should have high P(S|A)
        _create_entity_node(
            graph,
            "single_worker",
            wealth=1000.0,
            population=1,
        )

        # 50,000 workers with $1000 total - should have low P(S|A)
        _create_entity_node(
            graph,
            "block_workers",
            wealth=1000.0,
            population=50000,
        )

        system = SurvivalSystem()
        system.step(graph, services, {"tick": 1})

        p_acq_single = graph.nodes["single_worker"]["p_acquiescence"]
        p_acq_block = graph.nodes["block_workers"]["p_acquiescence"]

        # Single worker with $1000 per capita should have high P(S|A)
        assert p_acq_single > 0.9, f"Single worker P(S|A)={p_acq_single} should be > 0.9"

        # Block with $0.02 per capita should have low P(S|A)
        assert p_acq_block < 0.1, f"Block P(S|A)={p_acq_block} should be < 0.1"

        # Single worker MUST have higher P(S|A) than impoverished block
        assert p_acq_single > p_acq_block, (
            f"Single worker P(S|A)={p_acq_single} should exceed block P(S|A)={p_acq_block}"
        )

    def test_backward_compat_pop_1(self, services: ServiceContainer) -> None:
        """Population=1 with wealth=X has same P(S|A) as before (no regression).

        With population=1, wealth_per_capita == wealth (aggregate).
        This ensures backward compatibility with existing single-entity scenarios.
        """
        graph: nx.DiGraph = nx.DiGraph()

        # Wealthy single entity
        _create_entity_node(
            graph,
            "wealthy",
            wealth=100.0,
            population=1,
        )

        # Poor single entity
        _create_entity_node(
            graph,
            "poor",
            wealth=0.1,
            population=1,
        )

        system = SurvivalSystem()
        system.step(graph, services, {"tick": 1})

        p_acq_wealthy = graph.nodes["wealthy"]["p_acquiescence"]
        p_acq_poor = graph.nodes["poor"]["p_acquiescence"]

        # Wealthy should have higher P(S|A) than poor
        assert p_acq_wealthy > p_acq_poor, (
            f"Wealthy P(S|A)={p_acq_wealthy} should exceed poor P(S|A)={p_acq_poor}"
        )

        # Wealthy single entity should approach 1.0
        assert p_acq_wealthy > 0.9, f"Wealthy P(S|A)={p_acq_wealthy} should be > 0.9"

    def test_inactive_entity_skipped(self, services: ServiceContainer) -> None:
        """Dead blocks (active=False) don't calculate survival probabilities.

        Inactive entities should retain their previous P(S|A) value (or None).
        """
        graph: nx.DiGraph = nx.DiGraph()

        # Dead entity - should be skipped
        _create_entity_node(
            graph,
            "dead_block",
            wealth=1000.0,
            population=0,
            active=False,
        )

        # Pre-set a P(S|A) value that should NOT be updated
        graph.nodes["dead_block"]["p_acquiescence"] = 0.999

        system = SurvivalSystem()
        system.step(graph, services, {"tick": 1})

        # P(S|A) should remain unchanged (not recalculated)
        assert graph.nodes["dead_block"]["p_acquiescence"] == 0.999

    def test_zero_population_handled_safely(self, services: ServiceContainer) -> None:
        """Population=0 with active=True should not cause division by zero.

        Edge case: A technically "active" entity with no population should
        return P(S|A)=0 (no one to survive) rather than crash.
        """
        graph: nx.DiGraph = nx.DiGraph()

        # Active entity with zero population (edge case)
        _create_entity_node(
            graph,
            "empty_block",
            wealth=1000.0,
            population=0,
            active=True,  # Still marked active, but no population
        )

        system = SurvivalSystem()
        # Should not raise ZeroDivisionError
        system.step(graph, services, {"tick": 1})

        # With zero population, P(S|A) should be 0 or very low
        p_acq = graph.nodes["empty_block"]["p_acquiescence"]
        assert p_acq <= 0.5, f"Empty block P(S|A)={p_acq} should be <= 0.5"

    def test_equal_per_capita_equal_p_acquiescence(self, services: ServiceContainer) -> None:
        """Entities with equal per-capita wealth should have equal P(S|A).

        Block A: wealth=100, pop=100 → per_capita=1.0
        Block B: wealth=1000, pop=1000 → per_capita=1.0
        Both should have the same P(S|A).
        """
        graph: nx.DiGraph = nx.DiGraph()

        _create_entity_node(
            graph,
            "small_block",
            wealth=100.0,
            population=100,
        )

        _create_entity_node(
            graph,
            "large_block",
            wealth=1000.0,
            population=1000,
        )

        system = SurvivalSystem()
        system.step(graph, services, {"tick": 1})

        p_acq_small = graph.nodes["small_block"]["p_acquiescence"]
        p_acq_large = graph.nodes["large_block"]["p_acquiescence"]

        # Equal per-capita wealth → equal P(S|A)
        assert p_acq_small == pytest.approx(p_acq_large, abs=0.001), (
            f"Small block P(S|A)={p_acq_small} should equal large block P(S|A)={p_acq_large}"
        )
