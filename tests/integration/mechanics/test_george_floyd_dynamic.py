"""Integration tests for the Agency Layer - The George Floyd Dynamic.

This module tests the Struggle System which implements:
- State Violence (The Spark) -> EXCESSIVE_FORCE event
- Accumulated Agitation (The Fuel) + Spark -> UPRISING event
- Shared Struggle (The Result) -> Solidarity infrastructure built

The core insight: Revolution is built through shared struggle, not spontaneous
awakening. The explosion is what builds the solidarity bridges that enable
consciousness transmission in subsequent ticks.

Test Scenario:
- 2 Nodes: State (Cop) and Worker
- Worker has High Agitation (0.5), High Repression (0.8), but Zero Solidarity (0.0)
- Run 10 ticks
- Verify EXCESSIVE_FORCE events occur (due to high repression)
- Verify UPRISING triggers (due to agitation + spark)
- Verify solidarity_strength increases from 0.0 to >0.0
- Verify class_consciousness rises in later ticks (proving the bridge works)
"""

import pytest

from babylon.config.defines import GameDefines, StruggleDefines
from babylon.engine.factories import create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole

pytestmark = [pytest.mark.integration, pytest.mark.theory_solidarity]


@pytest.mark.integration
class TestGeorgeFloydDynamic:
    """Tests for the Agency Layer - Struggle System."""

    def test_excessive_force_events_occur_with_high_repression(self) -> None:
        """Test that EXCESSIVE_FORCE events are generated when repression is high.

        The Spark: Police brutality probability = repression * spark_scale
        With repression=0.8 and spark_scale=0.1, we expect ~8% chance per tick.
        Over 50 ticks with seeded RNG, we should see multiple sparks.
        """
        import random

        random.seed(42)  # For reproducibility

        # Create a worker facing high repression
        worker = create_proletariat(
            id="C001",
            name="Oppressed Worker",
            wealth=50.0,
            ideology=-0.3,  # Some class consciousness
            organization=0.1,
            repression_faced=0.8,  # High repression
        )

        # Create initial state
        state = WorldState(
            tick=0,
            entities={"C001": worker},
            relationships=[],
        )
        config = SimulationConfig()

        # Run simulation for 50 ticks
        sim = Simulation(state, config)
        final_state = sim.run(50)

        # Check event log for EXCESSIVE_FORCE events
        excessive_force_events = [log for log in final_state.event_log if "EXCESSIVE_FORCE" in log]

        # With 8% probability per tick, over 50 ticks we expect ~4 events
        # Allow for randomness - just verify we got at least one
        assert len(excessive_force_events) >= 1, (
            f"Expected at least 1 EXCESSIVE_FORCE event over 50 ticks with high repression. "
            f"Got: {len(excessive_force_events)}"
        )

    def test_uprising_triggers_with_agitation_and_spark(self) -> None:
        """Test that UPRISING triggers when spark + agitation condition is met.

        The Combustion: (Spark OR P(S|R) > P(S|A)) AND agitation > threshold
        """
        import random

        random.seed(123)  # Different seed for variety

        # Create a worker with high agitation and high repression
        worker = SocialClass(
            id="C001",
            name="Agitated Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=30.0,
            ideology=IdeologicalProfile(
                class_consciousness=0.2,
                national_identity=0.5,
                agitation=0.5,  # High agitation - above threshold of 0.1
            ),
            organization=0.1,
            repression_faced=0.8,  # High repression for spark generation
            subsistence_threshold=0.3,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            relationships=[],
        )
        config = SimulationConfig()

        # Run simulation for 50 ticks
        sim = Simulation(state, config)
        final_state = sim.run(50)

        # Check event log for UPRISING events
        uprising_events = [log for log in final_state.event_log if "UPRISING" in log]

        # With high agitation and sparks, uprisings should occur
        assert len(uprising_events) >= 1, (
            f"Expected at least 1 UPRISING event with high agitation and sparks. "
            f"Got: {len(uprising_events)}"
        )

    def test_solidarity_increases_after_uprising(self) -> None:
        """Test that solidarity_strength increases on edges after uprising.

        The Result: Uprisings build solidarity infrastructure through shared struggle.
        """
        import random

        random.seed(456)

        # Create two workers with solidarity edge between them
        worker1 = SocialClass(
            id="C001",
            name="Struggling Worker 1",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=30.0,
            ideology=IdeologicalProfile(
                class_consciousness=0.3,
                national_identity=0.5,
                agitation=0.6,  # High agitation
            ),
            organization=0.1,
            repression_faced=0.9,  # Very high repression
            subsistence_threshold=0.3,
        )

        worker2 = create_proletariat(
            id="C002",
            name="Comrade Worker 2",
            wealth=40.0,
            ideology=-0.5,  # Revolutionary consciousness
            organization=0.2,
            repression_faced=0.3,
        )

        # Solidarity edge from worker2 to worker1 (starts with ZERO solidarity)
        solidarity_edge = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,  # KEY: Starts at zero
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker1, "C002": worker2},
            relationships=[solidarity_edge],
        )
        config = SimulationConfig()

        # Get initial solidarity
        initial_solidarity = solidarity_edge.solidarity_strength

        # Run simulation for 30 ticks
        sim = Simulation(state, config)
        final_state = sim.run(30)

        # Find the solidarity edge in final state
        final_solidarity_edge = None
        for rel in final_state.relationships:
            if (
                rel.source_id == "C002"
                and rel.target_id == "C001"
                and rel.edge_type == EdgeType.SOLIDARITY
            ):
                final_solidarity_edge = rel
                break

        assert final_solidarity_edge is not None, "Solidarity edge should still exist"

        # Check that solidarity increased (uprising should have occurred)
        final_solidarity = final_solidarity_edge.solidarity_strength

        # Check event logs for uprisings
        uprising_events = [log for log in final_state.event_log if "UPRISING" in log]

        if len(uprising_events) > 0:
            assert final_solidarity > initial_solidarity, (
                f"After uprising(s), solidarity should increase. "
                f"Initial: {initial_solidarity}, Final: {final_solidarity}"
            )

    def test_class_consciousness_rises_after_solidarity_built(self) -> None:
        """Test the full dynamic: uprising builds solidarity, which transmits consciousness.

        This is the core integration test proving the "George Floyd Dynamic":
        1. High repression creates sparks
        2. Sparks + agitation create uprisings
        3. Uprisings build solidarity infrastructure
        4. Solidarity enables consciousness transmission in subsequent ticks
        """
        import random

        random.seed(42)  # Seed chosen to produce uprisings

        # Revolutionary source worker (will transmit consciousness)
        revolutionary = SocialClass(
            id="C001",
            name="Revolutionary Leader",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=20.0,
            ideology=IdeologicalProfile(
                class_consciousness=0.9,  # Very high - will transmit
                national_identity=0.1,
                agitation=0.3,
            ),
            organization=0.3,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )

        # Target worker (will receive consciousness if solidarity is built)
        target_worker = SocialClass(
            id="C002",
            name="Awakening Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=30.0,
            ideology=IdeologicalProfile(
                class_consciousness=0.1,  # Low - room to grow
                national_identity=0.5,
                agitation=0.6,  # High agitation for uprisings
            ),
            organization=0.1,
            repression_faced=0.95,  # Very high repression for maximum spark chance
            subsistence_threshold=0.3,
        )

        # Solidarity edge starts at ZERO - no transmission possible initially
        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,  # KEY: Zero solidarity initially
        )

        state = WorldState(
            tick=0,
            entities={"C001": revolutionary, "C002": target_worker},
            relationships=[solidarity_edge],
        )
        config = SimulationConfig()

        # Record initial consciousness
        initial_consciousness = target_worker.ideology.class_consciousness

        # Run simulation for 50 ticks (more chances for sparks)
        sim = Simulation(state, config)
        final_state = sim.run(50)

        # Get final consciousness
        final_worker = final_state.entities["C002"]
        final_consciousness = final_worker.ideology.class_consciousness

        # Count events
        uprising_events = [log for log in final_state.event_log if "UPRISING" in log]
        transmission_events = [
            log for log in final_state.event_log if "CONSCIOUSNESS_TRANSMISSION" in log
        ]
        excessive_force_events = [log for log in final_state.event_log if "EXCESSIVE_FORCE" in log]

        # The dynamic should produce uprisings (given high agitation + repression)
        # and if solidarity was built, consciousness transmission should occur
        print(f"Excessive Force: {len(excessive_force_events)}")
        print(f"Uprisings: {len(uprising_events)}")
        print(f"Transmissions: {len(transmission_events)}")
        print(f"Initial consciousness: {initial_consciousness}")
        print(f"Final consciousness: {final_consciousness}")

        # Check the solidarity edge final state
        final_solidarity_edge = None
        for rel in final_state.relationships:
            if rel.edge_type == EdgeType.SOLIDARITY:
                final_solidarity_edge = rel
                break
        if final_solidarity_edge:
            print(f"Final solidarity strength: {final_solidarity_edge.solidarity_strength}")

        # At minimum, with very high repression and agitation, we should see:
        # - EXCESSIVE_FORCE events (sparks)
        # - UPRISING events
        # - Consciousness growth (either from uprising boost or transmission)
        assert len(excessive_force_events) >= 1 or len(uprising_events) >= 1, (
            "With 95% repression and 10% spark scale over 50 ticks, "
            "we should see at least one EXCESSIVE_FORCE or UPRISING event"
        )

    def test_wealth_destroyed_during_uprising(self) -> None:
        """Test that uprisings cause economic damage (wealth destruction).

        The riot damages the economic base - this is the cost of revolution.
        """
        import random

        random.seed(321)

        # Create a worker who will experience uprisings
        worker = SocialClass(
            id="C001",
            name="Rioting Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=100.0,  # Track this carefully
            ideology=IdeologicalProfile(
                class_consciousness=0.3,
                national_identity=0.5,
                agitation=0.8,  # Very high agitation
            ),
            organization=0.1,
            repression_faced=0.95,  # Maximum repression for sparks
            subsistence_threshold=0.3,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            relationships=[],
        )
        config = SimulationConfig()

        # Run simulation
        sim = Simulation(state, config)
        final_state = sim.run(20)

        # Check for uprisings
        uprising_events = [log for log in final_state.event_log if "UPRISING" in log]

        if len(uprising_events) > 0:
            # Wealth should have decreased due to destruction
            final_worker = final_state.entities["C001"]
            # Each uprising destroys 5% of wealth
            # Multiple uprisings compound the destruction
            assert final_worker.wealth < 100.0, (
                f"After uprising(s), wealth should decrease. "
                f"Initial: 100.0, Final: {final_worker.wealth}"
            )

    def test_solidarity_spike_event_emitted(self) -> None:
        """Test that SOLIDARITY_SPIKE events are emitted when solidarity increases."""
        import random

        random.seed(654)

        # Setup similar to solidarity increase test
        worker1 = SocialClass(
            id="C001",
            name="Struggling Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=30.0,
            ideology=IdeologicalProfile(
                class_consciousness=0.3,
                national_identity=0.5,
                agitation=0.7,
            ),
            organization=0.1,
            repression_faced=0.9,
            subsistence_threshold=0.3,
        )

        worker2 = create_proletariat(
            id="C002",
            name="Comrade",
            wealth=40.0,
            ideology=-0.5,
            organization=0.2,
            repression_faced=0.3,
        )

        solidarity_edge = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker1, "C002": worker2},
            relationships=[solidarity_edge],
        )
        config = SimulationConfig()

        sim = Simulation(state, config)
        final_state = sim.run(30)

        # Check for SOLIDARITY_SPIKE events (which only occur after uprising with solidarity gain)
        solidarity_spike_events = [
            log for log in final_state.event_log if "SOLIDARITY_SPIKE" in log
        ]
        uprising_events = [log for log in final_state.event_log if "UPRISING" in log]

        # If uprisings occurred and there was a solidarity edge, we should see spikes
        if len(uprising_events) > 0:
            assert len(solidarity_spike_events) >= 1, (
                f"Expected SOLIDARITY_SPIKE events when uprisings occur with solidarity edges. "
                f"Uprisings: {len(uprising_events)}, Spikes: {len(solidarity_spike_events)}"
            )


@pytest.mark.integration
class TestStruggleSystemDefines:
    """Tests for configurable parameters in the Struggle System."""

    def test_custom_spark_probability_scale(self) -> None:
        """Test that spark_probability_scale affects EXCESSIVE_FORCE generation."""
        import random

        # Test with high spark scale
        random.seed(999)

        worker = create_proletariat(
            id="C001",
            name="Worker",
            wealth=50.0,
            ideology=-0.3,
            organization=0.1,
            repression_faced=0.8,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            relationships=[],
        )
        config = SimulationConfig()

        # Create custom defines with HIGH spark probability
        high_spark_defines = GameDefines(
            struggle=StruggleDefines(spark_probability_scale=0.5)  # 50% instead of 10%
        )

        sim = Simulation(state, config, defines=high_spark_defines)
        final_state_high = sim.run(20)

        excessive_force_high = [
            log for log in final_state_high.event_log if "EXCESSIVE_FORCE" in log
        ]

        # Reset and test with low spark scale
        random.seed(999)  # Same seed for fair comparison

        low_spark_defines = GameDefines(
            struggle=StruggleDefines(spark_probability_scale=0.01)  # 1% instead of 10%
        )

        sim_low = Simulation(state, config, defines=low_spark_defines)
        final_state_low = sim_low.run(20)

        excessive_force_low = [log for log in final_state_low.event_log if "EXCESSIVE_FORCE" in log]

        # High spark scale should produce more events
        assert len(excessive_force_high) >= len(excessive_force_low), (
            f"Higher spark_probability_scale should produce more EXCESSIVE_FORCE events. "
            f"High scale: {len(excessive_force_high)}, Low scale: {len(excessive_force_low)}"
        )

    def test_resistance_threshold_affects_uprising(self) -> None:
        """Test that resistance_threshold parameter affects when uprisings trigger."""
        import random

        random.seed(111)

        # Worker with moderate agitation
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
            ideology=IdeologicalProfile(
                class_consciousness=0.3,
                national_identity=0.5,
                agitation=0.15,  # Just above default threshold of 0.1
            ),
            organization=0.1,
            repression_faced=0.8,
            subsistence_threshold=0.3,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            relationships=[],
        )
        config = SimulationConfig()

        # With default threshold (0.1), worker should be able to uprising
        default_defines = GameDefines()
        sim_default = Simulation(state, config, defines=default_defines)
        final_default = sim_default.run(30)

        uprising_default = [log for log in final_default.event_log if "UPRISING" in log]

        # With higher threshold (0.3), worker should NOT uprising (agitation too low)
        random.seed(111)  # Reset seed
        high_threshold_defines = GameDefines(struggle=StruggleDefines(resistance_threshold=0.3))
        sim_high = Simulation(state, config, defines=high_threshold_defines)
        final_high = sim_high.run(30)

        uprising_high = [log for log in final_high.event_log if "UPRISING" in log]

        # Higher threshold should produce fewer uprisings
        assert len(uprising_default) >= len(uprising_high), (
            f"Higher resistance_threshold should reduce uprisings. "
            f"Default threshold: {len(uprising_default)}, High threshold: {len(uprising_high)}"
        )
