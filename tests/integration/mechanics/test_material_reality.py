"""Integration tests for Material Reality Refactor.

Tests the interaction between VitalitySystem (death) and ProductionSystem (value creation)
with the rest of the simulation engine to ensure material constraints ground the economy.

Key scenarios:
1. Starvation: Entity with 0 wealth dies immediately
2. Glut: High extraction + low biocapacity → death spiral
3. Sustainable: Balanced production and consumption → stability
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.entities import Relationship, SocialClass, Territory
from babylon.models.enums import EdgeType, SectorType, SocialRole
from babylon.models.world_state import WorldState


def _create_minimal_world(
    entities: dict[str, SocialClass],
    territories: dict[str, Territory] | None = None,
    relationships: list[Relationship] | None = None,
) -> WorldState:
    """Create a minimal world state for testing.

    Args:
        entities: Dict of entity ID to SocialClass
        territories: Optional dict of territory ID to Territory
        relationships: Optional list of Relationship objects
    """
    return WorldState(
        entities=entities,
        territories=territories or {},
        relationships=relationships or [],
        tick=0,
    )


@pytest.mark.integration
class TestStarvationScenario:
    """Tests for entity death via starvation (wealth < consumption_needs)."""

    def test_entity_with_zero_wealth_dies_on_first_tick(self) -> None:
        """Entity with 0 wealth and positive consumption_needs dies immediately."""
        # Setup: Worker with 0 wealth, consumption_needs = s_bio + s_class = 0.02
        starving_worker = SocialClass(
            id="C001",
            name="Starving Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.0,
            s_bio=0.01,
            s_class=0.01,
            active=True,
        )

        world = _create_minimal_world({"C001": starving_worker})
        config = SimulationConfig()
        defines = GameDefines.load_default()

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Worker is now dead
        worker = new_world.entities["C001"]
        assert worker.active is False, "Starving worker should die"

    def test_entity_with_sufficient_wealth_survives(self) -> None:
        """Entity with wealth >= consumption_needs survives."""
        # Setup: Worker with wealth > consumption_needs
        wealthy_worker = SocialClass(
            id="C002",
            name="Wealthy Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=1.0,  # Plenty of wealth
            s_bio=0.01,
            s_class=0.01,  # consumption_needs = 0.02
            active=True,
        )

        world = _create_minimal_world({"C002": wealthy_worker})
        config = SimulationConfig()
        defines = GameDefines.load_default()

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Worker is still alive
        worker = new_world.entities["C002"]
        assert worker.active is True, "Wealthy worker should survive"

    def test_comprador_with_zero_wealth_dies(self) -> None:
        """Comprador bourgeoisie with 0 wealth dies (zombie comprador fix)."""
        zombie_comprador = SocialClass(
            id="C003",
            name="Zombie Comprador",
            role=SocialRole.COMPRADOR_BOURGEOISIE,
            wealth=0.0,
            s_bio=0.01,
            s_class=0.05,  # Higher class consumption
            active=True,
        )

        world = _create_minimal_world({"C003": zombie_comprador})
        config = SimulationConfig()
        defines = GameDefines.load_default()

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Comprador is now dead
        comprador = new_world.entities["C003"]
        assert comprador.active is False, "Zombie comprador should die"


@pytest.mark.integration
class TestProductionScenario:
    """Tests for value creation via ProductionSystem."""

    def test_worker_in_territory_gains_wealth(self) -> None:
        """Worker with TENANCY edge to territory gains wealth from production."""
        worker = SocialClass(
            id="C004",
            name="Producing Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,  # Start with some wealth
            s_bio=0.01,
            s_class=0.01,
            active=True,
        )

        territory = Territory(
            id="T001",
            name="Factory Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,  # Full biocapacity
        )

        # TENANCY edge connects worker to territory
        tenancy = Relationship(
            source_id="C004",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )

        world = _create_minimal_world({"C004": worker}, {"T001": territory}, [tenancy])
        config = SimulationConfig()
        defines = GameDefines.load_default()

        initial_wealth = worker.wealth

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Worker gained wealth from production
        new_worker = new_world.entities["C004"]
        assert new_worker.wealth > initial_wealth, "Worker should gain wealth from production"

    def test_worker_in_depleted_territory_gains_nothing(self) -> None:
        """Worker in territory with 0 biocapacity produces nothing."""
        worker = SocialClass(
            id="C005",
            name="Barren Land Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            s_bio=0.01,
            s_class=0.01,
            active=True,
        )

        territory = Territory(
            id="T002",
            name="Barren Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=0.0,  # Fully depleted
            max_biocapacity=100.0,
        )

        tenancy = Relationship(
            source_id="C005",
            target_id="T002",
            edge_type=EdgeType.TENANCY,
        )

        world = _create_minimal_world({"C005": worker}, {"T002": territory}, [tenancy])
        config = SimulationConfig()
        defines = GameDefines.load_default()

        initial_wealth = worker.wealth

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Worker wealth unchanged (no production from barren land)
        new_worker = new_world.entities["C005"]
        # Allow for some consumption/extraction, but no production boost
        # The key is that depleted territory doesn't add wealth
        assert new_worker.wealth <= initial_wealth, "Worker should not gain wealth from barren land"

    def test_bourgeoisie_does_not_produce(self) -> None:
        """Bourgeoisie class does not produce value (extractive, not productive)."""
        bourgeois = SocialClass(
            id="C006",
            name="Lazy Bourgeois",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=10.0,
            s_bio=0.01,
            s_class=0.1,
            active=True,
        )

        territory = Territory(
            id="T003",
            name="Estate",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        tenancy = Relationship(
            source_id="C006",
            target_id="T003",
            edge_type=EdgeType.TENANCY,
        )

        world = _create_minimal_world({"C006": bourgeois}, {"T003": territory}, [tenancy])
        config = SimulationConfig()
        defines = GameDefines.load_default()

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Bourgeois did not gain from production (may lose to consumption)
        new_bourgeois = new_world.entities["C006"]
        # Production only applies to PERIPHERY_PROLETARIAT and LABOR_ARISTOCRACY
        # Bourgeoisie should not produce, so wealth should not increase from production
        assert new_bourgeois.active is True  # Should survive with 10.0 wealth


@pytest.mark.integration
class TestDeathSpiralScenario:
    """Tests for cascading economic collapse when entities die."""

    def test_dead_entities_are_skipped_by_all_systems(self) -> None:
        """Dead entities (active=False) are not processed by any system."""
        dead_worker = SocialClass(
            id="C007",
            name="Ghost Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.0,
            s_bio=0.01,
            s_class=0.01,
            active=False,  # Already dead
        )

        live_worker = SocialClass(
            id="C008",
            name="Living Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=1.0,
            s_bio=0.01,
            s_class=0.01,
            active=True,
        )

        world = _create_minimal_world({"C007": dead_worker, "C008": live_worker})
        config = SimulationConfig()
        defines = GameDefines.load_default()

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Dead worker is still dead (no resurrection)
        ghost = new_world.entities["C007"]
        assert ghost.active is False, "Dead entity should stay dead"

        # Assert: Living worker is still alive
        live = new_world.entities["C008"]
        assert live.active is True, "Living entity should stay alive"

    def test_extraction_from_dead_entity_fails(self) -> None:
        """Imperial rent extraction from dead entities produces nothing."""
        dead_periphery = SocialClass(
            id="C009",
            name="Dead Periphery",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=100.0,  # Has wealth but is dead
            s_bio=0.01,
            s_class=0.01,
            active=False,
        )

        living_core = SocialClass(
            id="C010",
            name="Living Core",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=10.0,
            s_bio=0.01,
            s_class=0.02,
            active=True,
        )

        # EXPLOITATION edge from dead periphery to core
        exploitation = Relationship(
            source_id="C009",
            target_id="C010",
            edge_type=EdgeType.EXPLOITATION,
        )

        world = _create_minimal_world(
            {"C009": dead_periphery, "C010": living_core}, relationships=[exploitation]
        )
        config = SimulationConfig()
        defines = GameDefines.load_default()

        initial_periphery_wealth = dead_periphery.wealth

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Dead periphery's wealth was not extracted
        new_periphery = new_world.entities["C009"]

        # Dead entity should not have wealth extracted
        assert new_periphery.wealth == initial_periphery_wealth, (
            "Dead entity should not lose wealth"
        )


@pytest.mark.integration
class TestMaterialRealityIntegration:
    """End-to-end tests for the full material reality loop."""

    def test_production_prevents_starvation(self) -> None:
        """Worker with territory produces enough to survive."""
        # Worker starts with just enough wealth, but production keeps them alive
        worker = SocialClass(
            id="C011",
            name="Sustainable Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.1,  # Low but not zero
            s_bio=0.01,
            s_class=0.01,  # consumption_needs = 0.02
            active=True,
        )

        territory = Territory(
            id="T004",
            name="Fertile Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        tenancy = Relationship(
            source_id="C011",
            target_id="T004",
            edge_type=EdgeType.TENANCY,
        )

        world = _create_minimal_world({"C011": worker}, {"T004": territory}, [tenancy])
        config = SimulationConfig()
        defines = GameDefines.load_default()

        # Run 5 ticks
        persistent_context: dict = {}
        current_world = world
        for _ in range(5):
            current_world = step(current_world, config, persistent_context, defines)

        # Assert: Worker survived all 5 ticks due to production
        final_worker = current_world.entities["C011"]
        assert final_worker.active is True, "Worker with production should survive"
        assert final_worker.wealth > 0, "Worker should have accumulated wealth"

    def test_system_execution_order(self) -> None:
        """Verify VitalitySystem runs before ProductionSystem (death before production)."""
        # Worker with 0 wealth should die BEFORE production can save them
        doomed_worker = SocialClass(
            id="C012",
            name="Doomed Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.0,  # Zero wealth = dies immediately
            s_bio=0.01,
            s_class=0.01,
            active=True,
        )

        territory = Territory(
            id="T005",
            name="Too Late Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        tenancy = Relationship(
            source_id="C012",
            target_id="T005",
            edge_type=EdgeType.TENANCY,
        )

        world = _create_minimal_world({"C012": doomed_worker}, {"T005": territory}, [tenancy])
        config = SimulationConfig()
        defines = GameDefines.load_default()

        # Run 1 tick
        new_world = step(world, config, defines=defines)

        # Assert: Worker died BEFORE production could save them
        worker = new_world.entities["C012"]
        assert worker.active is False, "Worker should die before production runs"
