"""TDD tests for linear subsistence burn with class-specific multipliers.

Tests for the "Cost of Living" mechanics that ensure entities cannot survive
indefinitely with zero income. Implements class-specific burn rates to model
differential social reproduction costs.

This is the RED phase - tests are written BEFORE implementation.
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest
from tests.constants import TestConstants

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import SocialRole

TC = TestConstants


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_entity_node(
    graph: nx.DiGraph,
    node_id: str,
    role: SocialRole,
    wealth: float,
    subsistence_multiplier: float = 1.0,
    active: bool = True,
) -> None:
    """Add an entity node to the graph for testing."""
    graph.add_node(
        node_id,
        _node_type="social_class",
        role=role,
        wealth=wealth,
        subsistence_multiplier=subsistence_multiplier,
        active=active,
    )


@pytest.mark.unit
class TestLinearSubsistenceBurn:
    """Tests for LINEAR (not percentage) subsistence burn mechanics."""

    def test_wealth_decreases_by_fixed_amount_not_percentage(
        self, services: ServiceContainer
    ) -> None:
        """Wealth decreases by FIXED cost, not percentage of current wealth.

        With base_subsistence=0.005 and multiplier=1.0:
        - After 1 tick: 0.2 - 0.005 = 0.195 (LINEAR)
        - NOT: 0.2 * 0.995 = 0.199 (exponential)
        """
        graph: nx.DiGraph = nx.DiGraph()
        initial_wealth = 0.2
        _create_entity_node(
            graph,
            "C001",
            SocialRole.PERIPHERY_PROLETARIAT,
            wealth=initial_wealth,
            subsistence_multiplier=1.0,
        )

        system = ImperialRentSystem()
        # Only run subsistence phase
        system._process_subsistence_phase(graph, services)

        base_subsistence = services.defines.economy.base_subsistence
        expected_linear = initial_wealth - (base_subsistence * 1.0)
        actual_wealth = graph.nodes["C001"]["wealth"]

        # Should be linear, not exponential
        assert actual_wealth == pytest.approx(expected_linear, rel=1e-6)

    def test_worker_burns_at_base_multiplier(self, services: ServiceContainer) -> None:
        """Periphery worker (mult=1.5) burns 1.5x base subsistence per tick."""
        graph: nx.DiGraph = nx.DiGraph()
        initial_wealth = 0.2
        worker_multiplier = 1.5
        _create_entity_node(
            graph,
            "C001",
            SocialRole.PERIPHERY_PROLETARIAT,
            wealth=initial_wealth,
            subsistence_multiplier=worker_multiplier,
        )

        system = ImperialRentSystem()
        system._process_subsistence_phase(graph, services)

        base_subsistence = services.defines.economy.base_subsistence
        expected_burn = base_subsistence * worker_multiplier
        expected_wealth = initial_wealth - expected_burn

        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_wealth, rel=1e-6)

    def test_bourgeoisie_burns_faster_than_worker(self, services: ServiceContainer) -> None:
        """Core bourgeoisie (mult=20) burns much faster than worker (mult=1.5)."""
        graph: nx.DiGraph = nx.DiGraph()
        initial_wealth = 0.2

        # Worker with 1.5x multiplier
        _create_entity_node(
            graph,
            "C001",
            SocialRole.PERIPHERY_PROLETARIAT,
            wealth=initial_wealth,
            subsistence_multiplier=1.5,
        )
        # Bourgeoisie with 20x multiplier
        _create_entity_node(
            graph,
            "C002",
            SocialRole.CORE_BOURGEOISIE,
            wealth=initial_wealth,
            subsistence_multiplier=20.0,
        )

        system = ImperialRentSystem()
        system._process_subsistence_phase(graph, services)

        worker_wealth = graph.nodes["C001"]["wealth"]
        bourgeois_wealth = graph.nodes["C002"]["wealth"]

        # Bourgeoisie should have lost more wealth
        worker_loss = initial_wealth - worker_wealth
        bourgeois_loss = initial_wealth - bourgeois_wealth

        # Bourgeoisie loss should be ~13.3x worker loss (20/1.5)
        assert bourgeois_loss > worker_loss
        assert bourgeois_loss / worker_loss == pytest.approx(20.0 / 1.5, rel=0.01)

    def test_comprador_dies_fast_with_zero_income(self, services: ServiceContainer) -> None:
        """Comprador (mult=10) with 0.2 wealth should reach 0 in ~4 ticks.

        With base_subsistence=0.005 and multiplier=10:
        - Burn per tick: 0.005 * 10 = 0.05
        - TTD: 0.2 / 0.05 = 4 ticks
        """
        graph: nx.DiGraph = nx.DiGraph()
        initial_wealth = 0.2
        comprador_multiplier = 10.0
        _create_entity_node(
            graph,
            "C001",
            SocialRole.COMPRADOR_BOURGEOISIE,
            wealth=initial_wealth,
            subsistence_multiplier=comprador_multiplier,
        )

        system = ImperialRentSystem()
        base_subsistence = services.defines.economy.base_subsistence
        burn_per_tick = base_subsistence * comprador_multiplier
        expected_ttd = int(initial_wealth / burn_per_tick)

        # Simulate expected_ttd ticks
        for _ in range(expected_ttd):
            system._process_subsistence_phase(graph, services)

        # After expected_ttd ticks, wealth should be at or near 0
        final_wealth = graph.nodes["C001"]["wealth"]
        assert final_wealth < burn_per_tick, (
            f"Comprador should be nearly dead after {expected_ttd} ticks, "
            f"but has {final_wealth} wealth"
        )

    def test_inactive_entities_skip_burn(self, services: ServiceContainer) -> None:
        """Dead entities (active=False) should not have wealth deducted."""
        graph: nx.DiGraph = nx.DiGraph()
        initial_wealth = 0.2
        _create_entity_node(
            graph,
            "C001",
            SocialRole.PERIPHERY_PROLETARIAT,
            wealth=initial_wealth,
            subsistence_multiplier=1.0,
            active=False,  # Dead
        )

        system = ImperialRentSystem()
        system._process_subsistence_phase(graph, services)

        # Wealth should be unchanged
        assert graph.nodes["C001"]["wealth"] == initial_wealth

    def test_zero_wealth_entities_skip_burn(self, services: ServiceContainer) -> None:
        """Entities with zero wealth should not go negative."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.0,
            subsistence_multiplier=1.0,
        )

        system = ImperialRentSystem()
        system._process_subsistence_phase(graph, services)

        # Wealth should remain 0, not go negative
        assert graph.nodes["C001"]["wealth"] == 0.0


@pytest.mark.unit
class TestClassSpecificMultipliers:
    """Tests for automatic multiplier assignment based on SocialRole."""

    def test_periphery_proletariat_default_multiplier(self) -> None:
        """Periphery proletariat should have multiplier of 1.5."""
        from babylon.models.entities.social_class import SocialClass

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.subsistence_multiplier == 1.5

    def test_labor_aristocracy_default_multiplier(self) -> None:
        """Labor aristocracy should have multiplier of 5.0."""
        from babylon.models.entities.social_class import SocialClass

        la = SocialClass(
            id="C001",
            name="Labor Aristocrat",
            role=SocialRole.LABOR_ARISTOCRACY,
        )
        assert la.subsistence_multiplier == 5.0

    def test_comprador_bourgeoisie_default_multiplier(self) -> None:
        """Comprador bourgeoisie should have multiplier of 10.0."""
        from babylon.models.entities.social_class import SocialClass

        comprador = SocialClass(
            id="C001",
            name="Comprador",
            role=SocialRole.COMPRADOR_BOURGEOISIE,
        )
        assert comprador.subsistence_multiplier == 10.0

    def test_core_bourgeoisie_default_multiplier(self) -> None:
        """Core bourgeoisie should have multiplier of 20.0."""
        from babylon.models.entities.social_class import SocialClass

        bourgeois = SocialClass(
            id="C001",
            name="Bourgeois",
            role=SocialRole.CORE_BOURGEOISIE,
        )
        assert bourgeois.subsistence_multiplier == 20.0

    def test_explicit_multiplier_overrides_default(self) -> None:
        """Explicitly set multiplier should not be overwritten by default."""
        from babylon.models.entities.social_class import SocialClass

        # Worker with explicit multiplier different from default
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            subsistence_multiplier=3.0,  # Override default 1.5
        )
        assert worker.subsistence_multiplier == 3.0
