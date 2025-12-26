"""Integration tests for endgame flow (Slice 1.6).

TDD Red Phase: These tests verify end-to-end endgame detection and
simulation termination. The tests WILL FAIL until implementations exist.

Slice 1.6: Endgame Integration

These tests verify that:
1. EndgameDetector integrates with Simulation facade
2. Simulation terminates when endgame is detected
3. run() returns both final state and outcome
4. Simulation continues while IN_PROGRESS

The integration ensures the full pipeline works:
    Simulation.step() -> Observer notification -> EndgameDetector.on_tick()
    -> GameOutcome check -> Simulation termination

NOTE: Tests marked with @pytest.mark.red_phase are excluded from pre-commit.
Remove the marker when implementing GREEN phase.
"""

from __future__ import annotations

import pytest

from babylon.engine.observer import SimulationObserver
from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, GameOutcome, SectorType, SocialRole
from babylon.models.relationship import Relationship

# TDD RED phase marker - these tests intentionally fail until GREEN phase
# Remove this line when implementing the GREEN phase
pytestmark = pytest.mark.red_phase

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation configuration."""
    return SimulationConfig()


@pytest.fixture
def endgame_detector() -> EndgameDetector:
    """Create an EndgameDetector observer."""
    return EndgameDetector()


def create_revolutionary_state() -> WorldState:
    """Create a WorldState that meets revolutionary victory conditions.

    Conditions:
    - percolation >= 0.7 (70%+ of nodes in giant component)
    - class_consciousness > 0.8 (average consciousness above 0.8)

    Returns:
        WorldState configured for revolutionary victory.
    """
    # Create 10 highly conscious, well-connected entities
    entities = {
        f"C{i:03d}": SocialClass(
            id=f"C{i:03d}",
            name=f"Revolutionary Worker {i}",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            class_consciousness=0.9,  # Above 0.8 threshold
            national_identity=0.1,  # Low (not fascist)
            wealth=10.0,
        )
        for i in range(10)
    }

    # Create SOLIDARITY edges forming a connected chain
    entity_ids = list(entities.keys())
    relationships = [
        Relationship(
            source_id=entity_ids[i],
            target_id=entity_ids[i + 1],
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.9,
        )
        for i in range(len(entity_ids) - 1)
    ]

    return WorldState(tick=0, entities=entities, relationships=relationships)


def create_ecological_collapse_state() -> WorldState:
    """Create a WorldState that meets ecological collapse conditions.

    Conditions:
    - overshoot_ratio > 2.0

    Returns:
        WorldState configured for ecological collapse.
    """
    # Low biocapacity territory
    territory = Territory(
        id="T001",
        name="Depleted Zone",
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=10.0,  # Very low
        max_biocapacity=100.0,
        regeneration_rate=0.01,  # Slow recovery
        extraction_intensity=0.0,
    )

    # High consumption entity
    entity = SocialClass(
        id="C001",
        name="High Consumer",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=1000.0,
        s_bio=15.0,
        s_class=10.0,
        # Total consumption = 25, ratio = 25/10 = 2.5 > 2.0
    )

    return WorldState(
        tick=0,
        entities={"C001": entity},
        territories={"T001": territory},
    )


def create_fascist_state() -> WorldState:
    """Create a WorldState that meets fascist consolidation conditions.

    Conditions:
    - national_identity > class_consciousness for 3+ nodes

    Returns:
        WorldState configured for fascist consolidation.
    """
    # Create entities where 4 have fascist consciousness
    entities = {}
    for i in range(5):
        if i < 4:  # 4 fascist nodes
            entities[f"C{i:03d}"] = SocialClass(
                id=f"C{i:03d}",
                name=f"Fascist Worker {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                national_identity=0.8,  # High
                class_consciousness=0.2,  # Low
            )
        else:  # 1 class-conscious node
            entities[f"C{i:03d}"] = SocialClass(
                id=f"C{i:03d}",
                name=f"Revolutionary {i}",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                national_identity=0.2,
                class_consciousness=0.8,
            )

    return WorldState(tick=0, entities=entities)


def create_in_progress_state() -> WorldState:
    """Create a WorldState where game is still in progress.

    No endgame conditions are met.

    Returns:
        WorldState configured for ongoing game.
    """
    # High biocapacity (no ecological collapse)
    territory = Territory(
        id="T001",
        name="Healthy Zone",
        sector_type=SectorType.RESIDENTIAL,
        biocapacity=500.0,
        max_biocapacity=500.0,
    )

    # Balanced entities (no revolutionary victory or fascist consolidation)
    entities = {
        "C001": SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            class_consciousness=0.5,  # Below 0.8
            national_identity=0.3,  # Below class_consciousness
            s_bio=5.0,
            s_class=5.0,
        ),
        "C002": SocialClass(
            id="C002",
            name="Worker 2",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            class_consciousness=0.4,
            national_identity=0.3,
            s_bio=5.0,
            s_class=5.0,
        ),
    }

    return WorldState(
        tick=0,
        entities=entities,
        territories={"T001": territory},
    )


# =============================================================================
# TEST SIMULATION TERMINATION
# =============================================================================


@pytest.mark.integration
class TestSimulationTermination:
    """Test that simulation terminates on endgame conditions."""

    def test_simulation_terminates_on_revolutionary_victory(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """Simulation terminates when revolutionary victory conditions are met.

        The run_until_endgame() method should:
        1. Run simulation ticks
        2. Check EndgameDetector.is_game_over after each tick
        3. Stop when game ends
        4. Return the final state and outcome
        """
        initial_state = create_revolutionary_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        # Simulation should have run_until_endgame method
        assert hasattr(sim, "run_until_endgame"), "Simulation must have run_until_endgame() method"

        # Run until endgame (with reasonable max ticks)
        final_state, outcome = sim.run_until_endgame(max_ticks=100)

        assert outcome == GameOutcome.REVOLUTIONARY_VICTORY
        assert endgame_detector.is_game_over is True

    def test_simulation_terminates_on_ecological_collapse(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """Simulation terminates when ecological collapse conditions are met.

        Ecological collapse requires 5 consecutive ticks of overshoot > 2.0.
        """
        initial_state = create_ecological_collapse_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        # Run until endgame
        final_state, outcome = sim.run_until_endgame(max_ticks=100)

        assert outcome == GameOutcome.ECOLOGICAL_COLLAPSE
        assert endgame_detector.is_game_over is True
        # Should have run at least 5 ticks for consecutive overshoot
        assert final_state.tick >= 5

    def test_simulation_terminates_on_fascist_consolidation(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """Simulation terminates when fascist consolidation conditions are met."""
        initial_state = create_fascist_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        # Run until endgame
        final_state, outcome = sim.run_until_endgame(max_ticks=100)

        assert outcome == GameOutcome.FASCIST_CONSOLIDATION
        assert endgame_detector.is_game_over is True


# =============================================================================
# TEST RUN RETURNS OUTCOME
# =============================================================================


@pytest.mark.integration
class TestRunReturnsOutcome:
    """Test that run methods return final state and outcome."""

    def test_run_returns_final_state_and_outcome(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """run_until_endgame returns tuple of (WorldState, GameOutcome)."""
        initial_state = create_revolutionary_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        result = sim.run_until_endgame(max_ticks=100)

        # Should return a tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

        final_state, outcome = result

        # First element is WorldState
        assert isinstance(final_state, WorldState)

        # Second element is GameOutcome
        assert isinstance(outcome, GameOutcome)
        assert outcome != GameOutcome.IN_PROGRESS  # Game should have ended

    def test_run_until_endgame_respects_max_ticks(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """run_until_endgame stops at max_ticks if no endgame reached.

        This prevents infinite loops for scenarios that never end.
        """
        initial_state = create_in_progress_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        max_ticks = 50
        final_state, outcome = sim.run_until_endgame(max_ticks=max_ticks)

        # Should stop at max_ticks
        assert final_state.tick <= max_ticks

        # Outcome should still be IN_PROGRESS (no endgame reached)
        assert outcome == GameOutcome.IN_PROGRESS


# =============================================================================
# TEST SIMULATION CONTINUES WHILE IN PROGRESS
# =============================================================================


@pytest.mark.integration
class TestSimulationContinues:
    """Test that simulation continues while game is in progress."""

    def test_simulation_continues_while_in_progress(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """Simulation runs multiple ticks while no endgame condition is met."""
        initial_state = create_in_progress_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        # Run 10 ticks
        for _ in range(10):
            sim.step()

        assert sim.current_state.tick == 10
        assert endgame_detector.outcome == GameOutcome.IN_PROGRESS
        assert endgame_detector.is_game_over is False

    def test_get_outcome_method_on_simulation(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """Simulation has get_outcome method that returns current game outcome.

        This provides a convenient way to check game state without
        directly accessing the observer.
        """
        initial_state = create_in_progress_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        # Simulation should have get_outcome method
        assert hasattr(sim, "get_outcome"), "Simulation must have get_outcome() method"

        # Initially should be IN_PROGRESS
        assert sim.get_outcome() == GameOutcome.IN_PROGRESS

        # Run some ticks
        sim.run(5)

        # Still in progress
        assert sim.get_outcome() == GameOutcome.IN_PROGRESS


# =============================================================================
# TEST OBSERVER INTEGRATION
# =============================================================================


@pytest.mark.integration
class TestObserverIntegration:
    """Test EndgameDetector integration with observer pattern."""

    def test_endgame_detector_receives_tick_notifications(
        self,
        config: SimulationConfig,
    ) -> None:
        """EndgameDetector receives on_tick notifications from Simulation."""
        initial_state = create_in_progress_state()
        detector = EndgameDetector()
        sim = Simulation(initial_state, config, observers=[detector])

        # Run a few ticks
        sim.run(3)

        # Detector should have processed ticks
        # We can verify by checking internal state or that no errors occurred
        assert detector.outcome == GameOutcome.IN_PROGRESS

    def test_endgame_detector_receives_start_notification(
        self,
        config: SimulationConfig,
    ) -> None:
        """EndgameDetector receives on_simulation_start notification."""
        initial_state = create_in_progress_state()
        detector = EndgameDetector()
        sim = Simulation(initial_state, config, observers=[detector])

        # First step triggers on_simulation_start
        sim.step()

        # Detector should be initialized (no errors)
        assert detector.outcome == GameOutcome.IN_PROGRESS

    def test_endgame_detector_protocol_compatibility(self) -> None:
        """EndgameDetector satisfies SimulationObserver protocol."""
        detector = EndgameDetector()
        assert isinstance(detector, SimulationObserver)


# =============================================================================
# TEST ENDGAME EVENTS IN WORLDSTATE
# =============================================================================


@pytest.mark.integration
class TestEndgameEvents:
    """Test ENDGAME_REACHED events in simulation."""

    def test_endgame_event_in_final_state(
        self,
        config: SimulationConfig,
        endgame_detector: EndgameDetector,
    ) -> None:
        """ENDGAME_REACHED event appears in event_log when game ends.

        The event should be collected from EndgameDetector and added
        to the WorldState event_log.
        """
        initial_state = create_fascist_state()
        sim = Simulation(initial_state, config, observers=[endgame_detector])

        final_state, outcome = sim.run_until_endgame(max_ticks=100)

        # Check for ENDGAME_REACHED in event_log
        endgame_events = [e for e in final_state.event_log if "ENDGAME" in e.upper()]

        # Should have at least one endgame event
        assert len(endgame_events) >= 1, (
            f"ENDGAME_REACHED event not found in event_log: {final_state.event_log}"
        )


# =============================================================================
# TEST STABILITY
# =============================================================================


@pytest.mark.integration
class TestEndgameStability:
    """Test endgame detection stability over extended runs."""

    def test_repeated_runs_deterministic(
        self,
        config: SimulationConfig,
    ) -> None:
        """Same initial state produces same outcome deterministically."""

        def run_to_endgame() -> tuple[int, GameOutcome]:
            state = create_revolutionary_state()
            detector = EndgameDetector()
            sim = Simulation(state, config, observers=[detector])
            final_state, outcome = sim.run_until_endgame(max_ticks=100)
            return final_state.tick, outcome

        tick1, outcome1 = run_to_endgame()
        tick2, outcome2 = run_to_endgame()

        assert tick1 == tick2
        assert outcome1 == outcome2

    def test_no_crash_on_extended_run(
        self,
        config: SimulationConfig,
    ) -> None:
        """Extended run without endgame does not crash.

        Tests numerical stability and resource management.
        """
        initial_state = create_in_progress_state()
        detector = EndgameDetector()
        sim = Simulation(initial_state, config, observers=[detector])

        # Run 200 ticks (should not crash)
        sim.run(200)

        assert sim.current_state.tick == 200
        # Should still be in progress (no endgame conditions)
        assert detector.outcome == GameOutcome.IN_PROGRESS


# =============================================================================
# TEST MULTIPLE DETECTORS
# =============================================================================


@pytest.mark.integration
class TestMultipleObservers:
    """Test EndgameDetector works alongside other observers."""

    def test_endgame_detector_with_other_observers(
        self,
        config: SimulationConfig,
    ) -> None:
        """EndgameDetector works correctly with other observers registered."""
        from babylon.engine.observers import EconomyMonitor
        from babylon.engine.topology_monitor import TopologyMonitor

        initial_state = create_revolutionary_state()
        endgame = EndgameDetector()
        economy = EconomyMonitor()
        topology = TopologyMonitor()

        sim = Simulation(
            initial_state,
            config,
            observers=[endgame, economy, topology],
        )

        # Run until endgame
        final_state, outcome = sim.run_until_endgame(max_ticks=100)

        # Should still detect endgame correctly
        assert outcome == GameOutcome.REVOLUTIONARY_VICTORY
        assert endgame.is_game_over is True

        # Other observers should have run without error
        # (TopologyMonitor has history we can check)
        assert len(topology.history) > 0
