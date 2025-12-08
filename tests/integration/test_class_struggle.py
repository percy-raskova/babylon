"""Integration tests for the History of Class Struggle simulation.

TDD Red Phase: These tests prove the engine works end-to-end by running
a 100-tick simulation and verifying wealth transfer dynamics.

This is the capstone integration test that proves:
1. Factory functions create valid entities
2. Simulation facade manages state correctly
3. Wealth transfers from Worker (exploited) to Owner (exploiter)
4. History is preserved for narrative generation
"""

import pytest

# =============================================================================
# TEST 100-TICK WEALTH TRANSFER
# =============================================================================


@pytest.mark.integration
class TestHistoryOfClassStruggle:
    """Integration tests proving the class struggle dynamics."""

    def test_100_tick_wealth_transfer_worker_to_owner(self) -> None:
        """100-tick simulation shows wealth transfer from Worker to Owner.

        This is the fundamental theorem of imperial rent in action:
        value flows from the exploited (Proletariat) to the exploiter (Bourgeoisie).
        """
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        # Create entities using factory functions
        worker = create_proletariat(id="C001", wealth=0.5)
        owner = create_bourgeoisie(id="C002", wealth=0.5)

        # Create exploitation relationship
        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        # Create initial state
        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        # Create config with default parameters
        config = SimulationConfig()

        # Run simulation
        sim = Simulation(initial_state, config)
        final_state = sim.run(100)

        # ASSERT: Worker lost wealth, Owner gained wealth
        initial_worker_wealth = worker.wealth
        initial_owner_wealth = owner.wealth

        final_worker_wealth = final_state.entities["C001"].wealth
        final_owner_wealth = final_state.entities["C002"].wealth

        # Worker should have lost wealth (extracted by owner)
        assert (
            final_worker_wealth < initial_worker_wealth
        ), f"Worker wealth should decrease: {initial_worker_wealth} -> {final_worker_wealth}"

        # Owner should have gained wealth (from extraction)
        assert (
            final_owner_wealth > initial_owner_wealth
        ), f"Owner wealth should increase: {initial_owner_wealth} -> {final_owner_wealth}"

        # Total wealth should be conserved (zero-sum extraction)
        initial_total = initial_worker_wealth + initial_owner_wealth
        final_total = final_worker_wealth + final_owner_wealth
        assert final_total == pytest.approx(
            initial_total, rel=0.01
        ), f"Total wealth not conserved: {initial_total} -> {final_total}"

    def test_component_values_stay_in_valid_ranges(self) -> None:
        """All component values stay within their valid ranges over 100 ticks.

        This tests numerical stability:
        - Wealth: [0, inf)
        - Ideology: [-1, 1]
        - Probability: [0, 1]
        - Tension: [0, 1]
        """
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        worker = create_proletariat(id="C001", wealth=0.5)
        owner = create_bourgeoisie(id="C002", wealth=0.5)

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
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
                assert (
                    entity.wealth >= 0.0
                ), f"Tick {state.tick}: {entity_id} wealth < 0: {entity.wealth}"

                # Ideology must be in [-1, 1]
                assert (
                    -1.0 <= entity.ideology <= 1.0
                ), f"Tick {state.tick}: {entity_id} ideology out of range: {entity.ideology}"

                # Organization must be in [0, 1]
                assert (
                    0.0 <= entity.organization <= 1.0
                ), f"Tick {state.tick}: {entity_id} organization out of range: {entity.organization}"

                # Probabilities must be in [0, 1]
                assert (
                    0.0 <= entity.p_acquiescence <= 1.0
                ), f"Tick {state.tick}: {entity_id} p_acquiescence out of range: {entity.p_acquiescence}"
                assert (
                    0.0 <= entity.p_revolution <= 1.0
                ), f"Tick {state.tick}: {entity_id} p_revolution out of range: {entity.p_revolution}"

            # Check all relationships
            for rel in state.relationships:
                # Value flow must be non-negative
                assert rel.value_flow >= 0.0, f"Tick {state.tick}: value_flow < 0: {rel.value_flow}"

                # Tension must be in [0, 1]
                assert (
                    0.0 <= rel.tension <= 1.0
                ), f"Tick {state.tick}: tension out of range: {rel.tension}"

    def test_worker_ideology_drifts_revolutionary(self) -> None:
        """Worker ideology drifts toward -1 (revolutionary) over 100 ticks.

        As the worker is exploited, consciousness increases (ideology decreases).
        This is the consciousness drift formula in action.
        """
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        worker = create_proletariat(id="C001", wealth=0.5, ideology=0.0)
        owner = create_bourgeoisie(id="C002", wealth=0.5)

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        final_state = sim.run(100)

        # Worker should have drifted revolutionary
        assert final_state.entities["C001"].ideology < 0.0, (
            f"Worker ideology should be negative (revolutionary): "
            f"{final_state.entities['C001'].ideology}"
        )

    def test_tension_accumulates_on_exploitation_edge(self) -> None:
        """Tension accumulates on the exploitation edge over 100 ticks.

        As wealth is extracted, contradiction tension builds on the edge.
        """
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        worker = create_proletariat(id="C001", wealth=0.5)
        owner = create_bourgeoisie(id="C002", wealth=0.5)

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,  # Start with no tension
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        final_state = sim.run(100)

        # Tension should have accumulated
        assert (
            final_state.relationships[0].tension > 0.0
        ), f"Tension should be positive: {final_state.relationships[0].tension}"

    def test_simulation_is_deterministic(self) -> None:
        """Same initial state and config produces identical results."""
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        def run_simulation() -> WorldState:
            worker = create_proletariat(id="C001", wealth=0.5)
            owner = create_bourgeoisie(id="C002", wealth=0.5)

            exploitation = Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.EXPLOITATION,
                value_flow=0.0,
                tension=0.0,
            )

            initial_state = WorldState(
                tick=0,
                entities={"C001": worker, "C002": owner},
                relationships=[exploitation],
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
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.history_formatter import format_class_struggle_history
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        worker = create_proletariat(id="C001", name="Worker", wealth=0.5)
        owner = create_bourgeoisie(id="C002", name="Owner", wealth=0.5)

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
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
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.history_formatter import format_class_struggle_history
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        worker = create_proletariat(id="C001", wealth=0.5)
        owner = create_bourgeoisie(id="C002", wealth=0.5)

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
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
        from babylon.engine.factories import create_bourgeoisie, create_proletariat
        from babylon.engine.history_formatter import format_class_struggle_history
        from babylon.engine.simulation import Simulation
        from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

        worker = create_proletariat(id="C001", wealth=0.5)
        owner = create_bourgeoisie(id="C002", wealth=0.5)

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        initial_state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        config = SimulationConfig()
        sim = Simulation(initial_state, config)
        sim.run(10)

        narrative = format_class_struggle_history(sim)

        # Should mention ticks or turns
        lower_narrative = narrative.lower()
        assert any(
            term in lower_narrative for term in ["tick", "turn", "year", "period"]
        ), f"Narrative should mention time progression: {narrative}"
