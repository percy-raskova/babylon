"""Integration tests for RUPTURE events - Revolutionary Moments.

This module tests the ContradictionSystem's RUPTURE event emission:
- RUPTURE occurs when accumulated tension reaches 1.0 on an edge
- Tension accumulates based on wealth gap: delta = wealth_gap * accumulation_rate
- RUPTURE represents qualitative shift in class struggle

Key insight: Revolution emerges from accumulated contradictions, not random chance.
When the tension between exploiter and exploited reaches critical mass, the
relationship ruptures - a qualitative leap from quantity to quality.

Test Scenarios:
1. RUPTURE triggers when tension reaches 1.0 (edge-level event)
2. High wealth gap + high accumulation rate speeds RUPTURE
3. Low wealth gap may never trigger RUPTURE within test timeframe
"""

import random

import pytest

from babylon.config.defines import GameDefines, TensionDefines
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

pytestmark = [pytest.mark.integration, pytest.mark.theory_solidarity]


class TestRuptureEvents:
    """Tests for RUPTURE event emission."""

    def test_rupture_triggers_at_tension_threshold(self) -> None:
        """Test that RUPTURE event fires when tension reaches 1.0.

        ContradictionSystem triggers RUPTURE when edge tension goes from <1.0 to >=1.0.
        High wealth gap + high accumulation rate should trigger within reasonable ticks.
        """
        random.seed(42)

        # Create extreme wealth gap for fast tension accumulation
        worker = create_proletariat(
            id="C001",
            name="Oppressed Worker",
            wealth=10.0,  # Very low wealth
        )

        owner = create_bourgeoisie(
            id="C002",
            name="Oppressor",
            wealth=1000.0,  # Very high wealth
        )

        # EXPLOITATION edge - tension will accumulate here
        # Wealth gap = 990, tension_delta per tick = 990 * accumulation_rate
        exploitation = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.0,  # Start at zero
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        # Use high accumulation rate for faster RUPTURE
        # With gap=990, rate=0.1, delta=99 per tick -> instant rupture
        # But wealth changes during simulation, so use more reasonable rate
        defines = GameDefines(
            tension=TensionDefines(
                accumulation_rate=0.1,  # 10% of wealth gap per tick
            )
        )
        config = SimulationConfig()

        # Run simulation
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(30)

        # Check for RUPTURE event
        rupture_events = [log for log in final_state.event_log if "RUPTURE" in log]

        # With high wealth gap and 10% rate, RUPTURE should trigger
        assert len(rupture_events) >= 1, (
            f"RUPTURE should trigger with extreme wealth gap. Events: {final_state.event_log[-10:]}"
        )

    def test_no_rupture_with_low_accumulation_rate(self) -> None:
        """Test that very low accumulation rate prevents RUPTURE within test timeframe.

        Even with a wealth gap, a sufficiently low accumulation rate should prevent
        RUPTURE from triggering within a reasonable number of ticks.
        """
        random.seed(42)

        # Some wealth gap exists, but very low accumulation rate
        worker = create_proletariat(
            id="C001",
            name="Worker",
            wealth=50.0,
        )

        owner = create_bourgeoisie(
            id="C002",
            name="Owner",
            wealth=200.0,  # Modest gap
        )

        exploitation = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.0,  # Start at zero
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        # Very low accumulation rate - with gap of ~150, rate=0.001
        # delta = 150 * 0.001 = 0.15 per tick, need ~7 ticks to reach 1.0
        # But this is still quite fast. Use even lower rate.
        defines = GameDefines(
            tension=TensionDefines(
                accumulation_rate=0.0001,  # 0.01% of wealth gap per tick
            )
        )
        config = SimulationConfig()

        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(30)

        # With 0.0001 rate and ~150 gap, delta = 0.015 per tick
        # After 30 ticks: max tension ~ 0.45 (below 1.0 threshold)
        rupture_events = [log for log in final_state.event_log if "RUPTURE" in log]

        assert len(rupture_events) == 0, (
            f"No RUPTURE expected with very low accumulation rate. "
            f"Got {len(rupture_events)} events: {rupture_events}"
        )

    def test_tension_accumulation_rate_affects_rupture_timing(self) -> None:
        """Test that higher accumulation rate leads to faster RUPTURE.

        Compare two simulations:
        1. High accumulation rate -> fast RUPTURE
        2. Low accumulation rate -> slower (or no) RUPTURE
        """
        random.seed(42)

        def create_scenario() -> WorldState:
            worker = create_proletariat(id="C001", name="Worker", wealth=50.0)
            owner = create_bourgeoisie(id="C002", name="Owner", wealth=500.0)

            exploitation = Relationship(
                source_id="C002",
                target_id="C001",
                edge_type=EdgeType.EXPLOITATION,
                tension=0.5,  # Start halfway to rupture
            )

            return WorldState(
                tick=0,
                entities={"C001": worker, "C002": owner},
                relationships=[exploitation],
            )

        config = SimulationConfig()

        # High rate simulation
        random.seed(42)
        high_rate_defines = GameDefines(tension=TensionDefines(accumulation_rate=0.2))
        sim_high = Simulation(create_scenario(), config, defines=high_rate_defines)
        final_high = sim_high.run(20)
        rupture_high = [log for log in final_high.event_log if "RUPTURE" in log]

        # Low rate simulation
        random.seed(42)
        low_rate_defines = GameDefines(tension=TensionDefines(accumulation_rate=0.01))
        sim_low = Simulation(create_scenario(), config, defines=low_rate_defines)
        final_low = sim_low.run(20)
        rupture_low = [log for log in final_low.event_log if "RUPTURE" in log]

        # High rate should produce at least as many (likely more) ruptures
        assert len(rupture_high) >= len(rupture_low), (
            f"Higher accumulation rate should lead to more ruptures. "
            f"High rate: {len(rupture_high)}, Low rate: {len(rupture_low)}"
        )

    def test_rupture_is_per_edge_event(self) -> None:
        """Test that RUPTURE is emitted per edge when tension threshold is crossed.

        Multiple edges can rupture independently based on their tension levels.
        """
        random.seed(42)

        # Create three workers with different wealth (different tension deltas)
        worker1 = create_proletariat(id="C001", name="Poorest Worker", wealth=10.0)
        worker2 = create_proletariat(id="C002", name="Poor Worker", wealth=50.0)
        owner = create_bourgeoisie(id="C003", name="Owner", wealth=1000.0)

        # Two exploitation edges with different starting tension
        exploitation1 = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.9,  # Very close to rupture
        )

        exploitation2 = Relationship(
            source_id="C003",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.1,  # Far from rupture
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker1, "C002": worker2, "C003": owner},
            relationships=[exploitation1, exploitation2],
        )

        defines = GameDefines(tension=TensionDefines(accumulation_rate=0.1))
        config = SimulationConfig()

        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(15)

        # Check for RUPTURE events
        rupture_events = [log for log in final_state.event_log if "RUPTURE" in log]

        # The edge starting at 0.9 tension should rupture first
        # (and maybe the other one too if enough ticks pass)
        assert len(rupture_events) >= 1, (
            f"At least one edge should rupture (starting at 0.9 tension). "
            f"Events: {final_state.event_log[-10:]}"
        )

    def test_rupture_only_fires_once_per_edge(self) -> None:
        """Test that RUPTURE is only emitted once when crossing threshold.

        The condition is: new_tension >= 1.0 AND current_tension < 1.0
        Once ruptured, the edge stays at 1.0 and shouldn't re-fire.
        """
        random.seed(42)

        worker = create_proletariat(id="C001", name="Worker", wealth=10.0)
        owner = create_bourgeoisie(id="C002", name="Owner", wealth=1000.0)

        exploitation = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.95,  # Very close to rupture
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        defines = GameDefines(tension=TensionDefines(accumulation_rate=0.2))
        config = SimulationConfig()

        # Run many ticks
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(50)

        # Count RUPTURE events for this specific edge
        rupture_events = [log for log in final_state.event_log if "RUPTURE" in log]

        # Should only see one RUPTURE per edge
        assert len(rupture_events) == 1, (
            f"RUPTURE should only fire once per edge. Got {len(rupture_events)} events"
        )
