"""Integration tests for the Carceral Geography Layer - TerritorySystem.

This module tests the TerritorySystem which implements:
- Heat Dynamics: HIGH_PROFILE gains heat, LOW_PROFILE decays
- Eviction Pipeline: heat >= 0.8 triggers eviction, rent spike, displacement
- Heat Spillover: Adjacent territories receive heat transmission
- Necropolitics: CONCENTRATION_CAMP decay, PENAL_COLONY organization suppression

Key insight: TerritorySystem emits NO events. All tests verify graph mutations
directly via final_state.territories and entity organization values.

Test Scenarios:
1. HIGH_PROFILE territory accumulates heat over ticks until eviction threshold
2. Eviction triggers rent spike and population displacement to sinks
3. Heat spills from hot territory to adjacent LOW_PROFILE territories
4. CONCENTRATION_CAMP populations decay each tick (genocide modeling)
5. PENAL_COLONY suppresses organization of tenants (atomization)
"""

import random

import pytest

from babylon.config.defines import GameDefines, TerritoryDefines
from babylon.engine.factories import create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    WorldState,
)
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    OperationalProfile,
    SectorType,
    TerritoryType,
)

pytestmark = [pytest.mark.integration, pytest.mark.theory_rent]


class TestHeatDynamics:
    """Tests for heat accumulation and decay based on OperationalProfile."""

    def test_high_profile_territory_accumulates_heat(self) -> None:
        """Test that HIGH_PROFILE territories gain heat each tick."""
        random.seed(42)

        # Create HIGH_PROFILE territory
        territory = Territory(
            id="T001",
            name="Revolutionary Cell HQ",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.0,  # Start cold
            population=100,
        )

        # Create worker tenant (needed for simulation to have entities)
        worker = create_proletariat(
            id="C001",
            name="Cell Members",
            wealth=50.0,
        )

        tenancy = Relationship(
            source_id="C001",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[tenancy],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Heat should have accumulated
        initial_heat = 0.0
        final_heat = final_state.territories["T001"].heat

        # Default high_profile_heat_gain = 0.15 per tick
        # After 10 ticks: ~1.5 (capped at 1.0)
        assert final_heat > initial_heat, (
            f"HIGH_PROFILE territory should accumulate heat. "
            f"Initial: {initial_heat}, Final: {final_heat}"
        )
        assert final_heat <= 1.0, f"Heat should be capped at 1.0, got {final_heat}"

    def test_low_profile_territory_decays_heat(self) -> None:
        """Test that LOW_PROFILE territories lose heat each tick."""
        random.seed(42)

        # Create LOW_PROFILE territory with existing heat
        territory = Territory(
            id="T001",
            name="Community Center",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.8,  # Start hot
            population=100,
        )

        worker = create_proletariat(id="C001", name="Members", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Heat should have decayed
        initial_heat = 0.8
        final_heat = final_state.territories["T001"].heat

        # Default heat_decay_rate = 0.1, formula: heat * (1 - rate)
        # After 10 ticks: 0.8 * (0.9)^10 ≈ 0.279
        assert final_heat < initial_heat, (
            f"LOW_PROFILE territory should decay heat. Initial: {initial_heat}, Final: {final_heat}"
        )
        assert final_heat >= 0.0, f"Heat should not go negative, got {final_heat}"


class TestEvictionPipeline:
    """Tests for eviction triggering, rent spikes, and population displacement."""

    def test_eviction_triggers_at_heat_threshold(self) -> None:
        """Test that eviction triggers when heat >= 0.8."""
        random.seed(42)

        # Create territory just below eviction threshold with HIGH_PROFILE
        territory = Territory(
            id="T001",
            name="Hot Zone",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.75,  # Just below 0.8 threshold
            population=1000,
            rent_level=1.0,
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=100.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Run enough ticks to cross threshold (1 tick adds 0.15 heat)
        sim = Simulation(state, config)
        final_state = sim.run(5)

        # Assert: Territory should be under eviction
        final_territory = final_state.territories["T001"]
        assert final_territory.under_eviction is True, (
            f"Territory should be under eviction when heat >= 0.8. "
            f"Final heat: {final_territory.heat}"
        )

    def test_rent_spike_during_eviction(self) -> None:
        """Test that rent increases during eviction."""
        random.seed(42)

        # Create territory already at eviction threshold
        territory = Territory(
            id="T001",
            name="Evicting Zone",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.85,  # Above threshold
            population=1000,
            rent_level=1.0,
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=100.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Run 5 ticks
        sim = Simulation(state, config)
        final_state = sim.run(5)

        # Assert: Rent should have spiked
        initial_rent = 1.0
        final_rent = final_state.territories["T001"].rent_level

        # Default rent_spike_multiplier = 1.5 per eviction tick
        # After 5 ticks: 1.0 * 1.5^5 ≈ 7.59
        assert final_rent > initial_rent, (
            f"Rent should spike during eviction. Initial: {initial_rent}, Final: {final_rent}"
        )

    def test_population_displaced_to_sink_node(self) -> None:
        """Test that displaced population flows to PENAL_COLONY sink."""
        random.seed(42)

        # Create evicting territory and penal colony sink
        source = Territory(
            id="T001",
            name="Evicting Neighborhood",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,  # Above threshold
            population=1000,
            rent_level=1.0,
        )

        sink = Territory(
            id="T002",
            name="State Prison",
            sector_type=SectorType.GOVERNMENT,  # Prisons are state facilities
            territory_type=TerritoryType.PENAL_COLONY,
            heat=0.0,
            population=100,  # Start with some prisoners
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=50.0)

        # Adjacency edge from source to sink
        adjacency = Relationship(
            source_id="T001",
            target_id="T002",
            edge_type=EdgeType.ADJACENCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": source, "T002": sink},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY),
                adjacency,
            ],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Population transferred to sink
        initial_source_pop = 1000
        initial_sink_pop = 100

        final_source_pop = final_state.territories["T001"].population
        final_sink_pop = final_state.territories["T002"].population

        assert final_source_pop < initial_source_pop, (
            f"Source population should decrease. "
            f"Initial: {initial_source_pop}, Final: {final_source_pop}"
        )
        assert final_sink_pop > initial_sink_pop, (
            f"Sink population should increase. Initial: {initial_sink_pop}, Final: {final_sink_pop}"
        )


class TestHeatSpillover:
    """Tests for heat transmission via ADJACENCY edges."""

    def test_heat_spills_to_adjacent_territory(self) -> None:
        """Test that heat from hot territory spills to adjacent cold territory."""
        random.seed(42)

        # Create hot source and cold target
        hot_territory = Territory(
            id="T001",
            name="Hot Zone",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            population=100,
        )

        cold_territory = Territory(
            id="T002",
            name="Cold Zone",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.0,
            population=100,
        )

        worker = create_proletariat(id="C001", name="Workers", wealth=50.0)

        # Adjacency edge enables spillover
        adjacency = Relationship(
            source_id="T001",
            target_id="T002",
            edge_type=EdgeType.ADJACENCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": hot_territory, "T002": cold_territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY),
                adjacency,
            ],
        )
        config = SimulationConfig()

        # Run 5 ticks
        sim = Simulation(state, config)
        final_state = sim.run(5)

        # Assert: Cold territory gained heat from spillover
        initial_cold_heat = 0.0
        final_cold_heat = final_state.territories["T002"].heat

        # Spillover occurs each tick: spillover = source_heat * spillover_rate
        # Default spillover_rate = 0.05
        assert final_cold_heat > initial_cold_heat, (
            f"Cold territory should receive heat spillover. "
            f"Initial: {initial_cold_heat}, Final: {final_cold_heat}"
        )


class TestNecropolitics:
    """Tests for sink node effects: concentration camp decay, penal colony suppression."""

    def test_concentration_camp_population_decays(self) -> None:
        """Test that CONCENTRATION_CAMP populations decay each tick (genocide)."""
        random.seed(42)

        # Create concentration camp with population
        camp = Territory(
            id="T001",
            name="Death Camp",
            sector_type=SectorType.GOVERNMENT,
            territory_type=TerritoryType.CONCENTRATION_CAMP,
            heat=0.0,
            population=1000,
        )

        # Need at least one entity for simulation to run
        worker = create_proletariat(id="C001", name="Guard", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": camp},
            relationships=[],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Population decayed
        initial_pop = 1000
        final_pop = final_state.territories["T001"].population

        # Default concentration_camp_decay_rate = 0.2
        # After 10 ticks: 1000 * (0.8)^10 ≈ 107
        assert final_pop < initial_pop, (
            f"Concentration camp population should decay. "
            f"Initial: {initial_pop}, Final: {final_pop}"
        )

    def test_penal_colony_suppresses_organization(self) -> None:
        """Test that PENAL_COLONY tenants have organization set to 0."""
        random.seed(42)

        # Create penal colony
        prison = Territory(
            id="T001",
            name="State Prison",
            sector_type=SectorType.GOVERNMENT,
            territory_type=TerritoryType.PENAL_COLONY,
            heat=0.0,
            population=500,
        )

        # Create prisoner with high organization
        prisoner = create_proletariat(
            id="C001",
            name="Political Prisoner",
            wealth=10.0,
            organization=0.8,  # High organization
        )

        # TENANCY edge connects prisoner to prison
        tenancy = Relationship(
            source_id="C001",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": prisoner},
            territories={"T001": prison},
            relationships=[tenancy],
        )
        config = SimulationConfig()

        # Run 1 tick
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Assert: Organization suppressed to 0
        initial_org = 0.8
        final_org = final_state.entities["C001"].organization

        assert final_org == 0.0, (
            f"Penal colony should suppress organization to 0. "
            f"Initial: {initial_org}, Final: {final_org}"
        )


class TestDisplacementModes:
    """Tests for displacement priority modes (EXTRACTION prioritizes PENAL_COLONY)."""

    def test_extraction_mode_prioritizes_penal_colony(self) -> None:
        """Test that EXTRACTION mode routes displaced population to PENAL_COLONY first."""
        random.seed(42)

        # Create evicting territory with multiple sink options
        source = Territory(
            id="T001",
            name="Evicting Zone",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            population=1000,
        )

        prison = Territory(
            id="T002",
            name="Prison",
            sector_type=SectorType.GOVERNMENT,
            territory_type=TerritoryType.PENAL_COLONY,
            population=0,
        )

        reservation = Territory(
            id="T003",
            name="Reservation",
            sector_type=SectorType.GOVERNMENT,
            territory_type=TerritoryType.RESERVATION,
            population=0,
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": source, "T002": prison, "T003": reservation},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY),
                Relationship(source_id="T001", target_id="T002", edge_type=EdgeType.ADJACENCY),
                Relationship(source_id="T001", target_id="T003", edge_type=EdgeType.ADJACENCY),
            ],
        )
        config = SimulationConfig()

        # Run with EXTRACTION mode (default)
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Prison received more population than reservation
        prison_pop = final_state.territories["T002"].population
        reservation_pop = final_state.territories["T003"].population

        # With EXTRACTION mode, PENAL_COLONY has priority
        # All displaced population should go to prison, not reservation
        assert prison_pop >= reservation_pop, (
            f"EXTRACTION mode should prioritize penal colony. "
            f"Prison: {prison_pop}, Reservation: {reservation_pop}"
        )


class TestCustomDefines:
    """Tests for configurable parameters in TerritorySystem."""

    def test_custom_heat_gain_rate(self) -> None:
        """Test that custom high_profile_heat_gain affects heat accumulation."""
        random.seed(42)

        territory = Territory(
            id="T001",
            name="Test Zone",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.0,
            population=100,
        )

        worker = create_proletariat(id="C001", name="Worker", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Test with HIGH heat gain
        high_gain_defines = GameDefines(
            territory=TerritoryDefines(high_profile_heat_gain=0.3)  # 2x default
        )

        sim_high = Simulation(state, config, defines=high_gain_defines)
        final_high = sim_high.run(5)

        # Reset and test with LOW heat gain
        random.seed(42)
        low_gain_defines = GameDefines(
            territory=TerritoryDefines(high_profile_heat_gain=0.05)  # 1/3 default
        )

        sim_low = Simulation(state, config, defines=low_gain_defines)
        final_low = sim_low.run(5)

        high_heat = final_high.territories["T001"].heat
        low_heat = final_low.territories["T001"].heat

        # High gain should produce more heat
        assert high_heat >= low_heat, (
            f"Higher heat gain should produce more heat. High: {high_heat}, Low: {low_heat}"
        )

    def test_custom_eviction_threshold(self) -> None:
        """Test that custom eviction_heat_threshold affects eviction trigger."""
        random.seed(42)

        # Territory with heat at 0.6 (below default 0.8, above custom 0.5)
        territory = Territory(
            id="T001",
            name="Test Zone",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.LOW_PROFILE,  # Keep heat stable
            heat=0.6,
            population=1000,
        )

        worker = create_proletariat(id="C001", name="Worker", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Lower threshold to 0.5 (below current heat of 0.6)
        low_threshold_defines = GameDefines(territory=TerritoryDefines(eviction_heat_threshold=0.5))

        sim = Simulation(state, config, defines=low_threshold_defines)
        final_state = sim.run(1)

        # Should trigger eviction since heat (0.6) > threshold (0.5)
        assert final_state.territories["T001"].under_eviction is True, (
            "Eviction should trigger when heat (0.6) >= threshold (0.5)"
        )
