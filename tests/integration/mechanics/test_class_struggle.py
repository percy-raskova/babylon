"""Integration tests for the History of Class Struggle simulation.

TDD Red Phase: These tests prove the engine works end-to-end by running
a 100-tick simulation and verifying wealth transfer dynamics.

This is the capstone integration test that proves:
1. Factory functions create valid entities
2. Simulation facade manages state correctly
3. Wealth transfers from Worker (exploited) to Owner (exploiter)
4. History is preserved for narrative generation

Sprint 1.X: Refactored for Material Reality physics:
- Population=1 for per-capita survival mechanics
- SAFE_WEALTH (5.0) ensures entities survive VitalitySystem
- Territory + TENANCY edges enable production
"""

import pytest

from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType
from tests.constants import TestConstants

TC = TestConstants

pytestmark = [pytest.mark.integration, pytest.mark.theory_solidarity]


@pytest.mark.integration
class TestHistoryOfClassStruggle:
    """Integration tests proving the class struggle dynamics."""

    def test_100_tick_wealth_transfer_worker_to_owner(self) -> None:
        """100-tick simulation shows wealth transfer from Worker to Owner.

        This is the fundamental theorem of imperial rent in action:
        value flows from the exploited (Proletariat) to the exploiter (Bourgeoisie).
        """
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        # Create entities with default population for per-capita survival mechanics
        # Worker has moderate wealth for extraction; Owner has high wealth to survive 100 ticks
        worker = SocialClass(
            id="C001",
            name="Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=100.0,  # High wealth as extraction source
            population=TC.Vitality.DEFAULT_POPULATION,
        )
        owner = SocialClass(
            id="C002",
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=50.0,  # High starting wealth to survive subsistence over 100 ticks
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Create territory for worker production
        # Worker produces via TENANCY; Owner extracts but doesn't produce
        # This models the fundamental MLM-TW dynamic: workers produce, owners extract
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        # Create exploitation relationship
        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        # ONLY worker has TENANCY - Owner is pure extractor (no production)
        # This is the fundamental class relationship: workers produce, owners extract
        tenancy_worker = Relationship(
            source_id="C001",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )

        # Create initial state with territory
        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            territories={"T001": territory},
            relationships=[exploitation, tenancy_worker],  # No owner tenancy
        )

        # Create config with default parameters
        config = SimulationConfig()

        # Run simulation
        sim = Simulation(initial_state, config)
        final_state = sim.run(100)

        # ASSERT: Wealth flows from Worker to Owner (class struggle dynamics)
        initial_worker_wealth = 100.0  # Explicitly set above
        initial_owner_wealth = 50.0  # Explicitly set above

        final_worker_wealth = final_state.entities["C001"].wealth
        final_owner_wealth = final_state.entities["C002"].wealth

        # Worker should have lost wealth to extraction
        # (even with production, high extraction should dominate)
        assert final_worker_wealth < initial_worker_wealth, (
            f"Worker wealth should decrease: {initial_worker_wealth} -> {final_worker_wealth}"
        )

        # Owner accumulates extraction despite no production (pure extraction model)
        # Note: Owner survives on initial wealth + extraction, minus subsistence burn
        # At 100 ticks, owner should still have more than initial if extraction > subsistence
        assert final_owner_wealth > initial_owner_wealth, (
            f"Owner wealth should increase: {initial_owner_wealth} -> {final_owner_wealth}"
        )

        # Wealth redistribution check: verify extraction happened
        worker_loss = initial_worker_wealth - final_worker_wealth
        assert worker_loss > 0, "Worker should have lost wealth to extraction"

    def test_component_values_stay_in_valid_ranges(self) -> None:
        """All component values stay within their valid ranges over 100 ticks.

        This tests numerical stability:
        - Wealth: [0, inf)
        - Ideology: [-1, 1]
        - Probability: [0, 1]
        - Tension: [0, 1]
        """
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        worker = SocialClass(
            id="C001",
            name="Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )
        owner = SocialClass(
            id="C002",
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Create territory for production
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        # TENANCY edges
        tenancy_worker = Relationship(
            source_id="C001",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )
        tenancy_owner = Relationship(
            source_id="C002",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            territories={"T001": territory},
            relationships=[exploitation, tenancy_worker, tenancy_owner],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)

        # Run simulation and check all states
        sim.run(100)
        history = sim.get_history()

        for state in history:
            # Check all entities
            for entity_id, entity in state.entities.items():
                # Wealth must be non-negative
                assert entity.wealth >= 0.0, (
                    f"Tick {state.tick}: {entity_id} wealth < 0: {entity.wealth}"
                )

                # Class consciousness must be in [0, 1]
                assert 0.0 <= entity.ideology.class_consciousness <= 1.0, (
                    f"Tick {state.tick}: {entity_id} class_consciousness out of range: {entity.ideology.class_consciousness}"
                )

                # Organization must be in [0, 1]
                assert 0.0 <= entity.organization <= 1.0, (
                    f"Tick {state.tick}: {entity_id} organization out of range: {entity.organization}"
                )

                # Probabilities must be in [0, 1]
                assert 0.0 <= entity.p_acquiescence <= 1.0, (
                    f"Tick {state.tick}: {entity_id} p_acquiescence out of range: {entity.p_acquiescence}"
                )
                assert 0.0 <= entity.p_revolution <= 1.0, (
                    f"Tick {state.tick}: {entity_id} p_revolution out of range: {entity.p_revolution}"
                )

            # Check all relationships
            for rel in state.relationships:
                # Value flow must be non-negative
                assert rel.value_flow >= 0.0, f"Tick {state.tick}: value_flow < 0: {rel.value_flow}"

                # Tension must be in [0, 1]
                assert 0.0 <= rel.tension <= 1.0, (
                    f"Tick {state.tick}: tension out of range: {rel.tension}"
                )

    def test_worker_ideology_drifts_revolutionary(self) -> None:
        """Worker class_consciousness increases over 100 ticks via solidarity.

        Sprint 3.4.3: Consciousness drift now happens through SOLIDARITY edges.
        A core worker with solidarity connection to a revolutionary periphery worker
        will gain class consciousness over time.
        """
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        # Core worker starts at neutral consciousness (0.5)
        worker = SocialClass(
            id="C001",
            name="Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=TC.Wealth.SAFE_WEALTH,
            ideology=0.0,
            population=TC.Vitality.DEFAULT_POPULATION,
        )
        owner = SocialClass(
            id="C002",
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Add a revolutionary periphery worker to transmit consciousness
        periphery_worker = SocialClass(
            id="C003",
            name="Revolutionary",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=TC.Wealth.SAFE_WEALTH,
            ideology=-0.8,  # consciousness 0.9
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Create territory for production
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        # Solidarity edge from periphery to worker for consciousness transmission
        solidarity = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.3,
        )

        # TENANCY edges for all entities
        tenancy_worker = Relationship(
            source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY
        )
        tenancy_owner = Relationship(source_id="C002", target_id="T001", edge_type=EdgeType.TENANCY)
        tenancy_periphery = Relationship(
            source_id="C003", target_id="T001", edge_type=EdgeType.TENANCY
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner, "C003": periphery_worker},
            territories={"T001": territory},
            relationships=[
                exploitation,
                solidarity,
                tenancy_worker,
                tenancy_owner,
                tenancy_periphery,
            ],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        final_state = sim.run(100)

        # Worker should have gained consciousness via solidarity transmission
        assert final_state.entities["C001"].ideology.class_consciousness > 0.5, (
            f"Worker class_consciousness should be above neutral (revolutionary): "
            f"{final_state.entities['C001'].ideology.class_consciousness}"
        )

    def test_tension_accumulates_on_exploitation_edge(self) -> None:
        """Tension accumulates on the exploitation edge over 100 ticks.

        As wealth is extracted, contradiction tension builds on the edge.
        """
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        worker = SocialClass(
            id="C001",
            name="Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )
        owner = SocialClass(
            id="C002",
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Create territory for production
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,  # Start with no tension
        )

        # TENANCY edges
        tenancy_worker = Relationship(
            source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY
        )
        tenancy_owner = Relationship(source_id="C002", target_id="T001", edge_type=EdgeType.TENANCY)

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            territories={"T001": territory},
            relationships=[exploitation, tenancy_worker, tenancy_owner],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        final_state = sim.run(100)

        # Tension should have accumulated
        assert final_state.relationships[0].tension > 0.0, (
            f"Tension should be positive: {final_state.relationships[0].tension}"
        )

    def test_simulation_is_deterministic(self) -> None:
        """Same initial state and config produces identical results."""
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        def run_simulation() -> WorldState:
            worker = SocialClass(
                id="C001",
                name="Proletariat",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                wealth=TC.Wealth.SAFE_WEALTH,
                population=TC.Vitality.DEFAULT_POPULATION,
            )
            owner = SocialClass(
                id="C002",
                name="Bourgeoisie",
                role=SocialRole.CORE_BOURGEOISIE,
                wealth=TC.Wealth.SAFE_WEALTH,
                population=TC.Vitality.DEFAULT_POPULATION,
            )

            # Create territory for production
            territory = Territory(
                id="T001",
                name="Test Territory",
                sector_type=SectorType.INDUSTRIAL,
                biocapacity=100.0,
                max_biocapacity=100.0,
            )

            exploitation = Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.EXPLOITATION,
                value_flow=0.0,
                tension=0.0,
            )

            # TENANCY edges
            tenancy_worker = Relationship(
                source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY
            )
            tenancy_owner = Relationship(
                source_id="C002", target_id="T001", edge_type=EdgeType.TENANCY
            )

            initial_state = WorldState(
                tick=0,
                entities={"C001": worker, "C002": owner},
                territories={"T001": territory},
                relationships=[exploitation, tenancy_worker, tenancy_owner],
            )

            config = SimulationConfig()
            sim = Simulation(initial_state, config)
            return sim.run(100)

        # Run twice
        result1 = run_simulation()
        result2 = run_simulation()

        # Results should be identical
        assert result1.entities["C001"].wealth == pytest.approx(result2.entities["C001"].wealth)
        assert result1.entities["C002"].wealth == pytest.approx(result2.entities["C002"].wealth)
        assert result1.entities["C001"].ideology == pytest.approx(result2.entities["C001"].ideology)
        assert result1.relationships[0].tension == pytest.approx(result2.relationships[0].tension)


# =============================================================================
# TEST HISTORY FORMATTER
# =============================================================================


@pytest.mark.integration
class TestHistoryFormatter:
    """Tests for the history_formatter module."""

    def test_format_class_struggle_history(self) -> None:
        """format_class_struggle_history() produces readable narrative."""
        from babylon.engine.history_formatter import format_class_struggle_history
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )
        owner = SocialClass(
            id="C002",
            name="Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Create territory for production
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        # TENANCY edges
        tenancy_worker = Relationship(
            source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY
        )
        tenancy_owner = Relationship(source_id="C002", target_id="T001", edge_type=EdgeType.TENANCY)

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            territories={"T001": territory},
            relationships=[exploitation, tenancy_worker, tenancy_owner],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        sim.run(10)

        # Format the history
        narrative = format_class_struggle_history(sim)

        # Should be a non-empty string
        assert isinstance(narrative, str)
        assert len(narrative) > 0

        # Should contain entity names
        assert "Worker" in narrative or "Proletariat" in narrative
        assert "Owner" in narrative or "Bourgeoisie" in narrative

    def test_format_includes_wealth_changes(self) -> None:
        """Formatted history includes wealth change information."""
        from babylon.engine.history_formatter import format_class_struggle_history
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        worker = SocialClass(
            id="C001",
            name="Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )
        owner = SocialClass(
            id="C002",
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Create territory for production
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        # TENANCY edges
        tenancy_worker = Relationship(
            source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY
        )
        tenancy_owner = Relationship(source_id="C002", target_id="T001", edge_type=EdgeType.TENANCY)

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            territories={"T001": territory},
            relationships=[exploitation, tenancy_worker, tenancy_owner],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        sim.run(10)

        narrative = format_class_struggle_history(sim)

        # Should mention wealth or economic concepts
        lower_narrative = narrative.lower()
        assert any(
            term in lower_narrative
            for term in ["wealth", "economic", "extraction", "rent", "value"]
        ), f"Narrative should mention economic terms: {narrative}"

    def test_format_includes_tick_information(self) -> None:
        """Formatted history includes tick/turn information."""
        from babylon.engine.history_formatter import format_class_struggle_history
        from babylon.engine.simulation import Simulation
        from babylon.models import (
            EdgeType,
            Relationship,
            SimulationConfig,
            SocialClass,
            SocialRole,
            WorldState,
        )

        worker = SocialClass(
            id="C001",
            name="Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )
        owner = SocialClass(
            id="C002",
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=TC.Wealth.SAFE_WEALTH,
            population=TC.Vitality.DEFAULT_POPULATION,
        )

        # Create territory for production
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        # TENANCY edges
        tenancy_worker = Relationship(
            source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY
        )
        tenancy_owner = Relationship(source_id="C002", target_id="T001", edge_type=EdgeType.TENANCY)

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            territories={"T001": territory},
            relationships=[exploitation, tenancy_worker, tenancy_owner],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        sim.run(10)

        narrative = format_class_struggle_history(sim)

        # Should mention ticks or turns
        lower_narrative = narrative.lower()
        assert any(term in lower_narrative for term in ["tick", "turn", "year", "period"]), (
            f"Narrative should mention time progression: {narrative}"
        )
