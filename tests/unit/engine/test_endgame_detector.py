"""Tests for EndgameDetector observer and GameOutcome enum (Slice 1.6).

TDD Red Phase: These tests define the contract for endgame detection.
The tests WILL FAIL initially because the implementations do not exist yet.
This is the correct Red phase outcome.

Slice 1.6: Endgame Detection

The simulation engine must detect three possible game endings and terminate:

1. REVOLUTIONARY_VICTORY: percolation >= 0.7 AND class_consciousness > 0.8
   - The masses have achieved critical organization AND ideological clarity
   - This represents successful proletarian revolution

2. ECOLOGICAL_COLLAPSE: overshoot_ratio > 2.0 for 5 consecutive ticks
   - Sustained ecological overshoot leads to irreversible collapse
   - Capital's metabolic rift has become fatal

3. FASCIST_CONSOLIDATION: national_identity > class_consciousness for 3+ nodes
   - Fascist ideology has captured the majority of the population
   - False consciousness prevents class-based organization

The EndgameDetector is a SimulationObserver that:
- Monitors WorldState for endgame conditions
- Tracks multi-tick conditions (overshoot duration, fascist nodes)
- Emits ENDGAME_REACHED event when game ends
- Exposes current GameOutcome via property

NOTE: Tests marked with @pytest.mark.red_phase are excluded from pre-commit.
Remove the marker when implementing GREEN phase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

# These imports will fail until implementation exists - that's the RED phase
from babylon.engine.observer import SimulationObserver
from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.models.enums import EventType, GameOutcome

# TDD RED phase marker - these tests intentionally fail until GREEN phase
# Remove this line when implementing the GREEN phase
pytestmark = pytest.mark.red_phase

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    from babylon.models import SimulationConfig

    return SimulationConfig()


def create_minimal_state(tick: int = 0) -> WorldState:
    """Create minimal WorldState for testing.

    Args:
        tick: The simulation tick number.

    Returns:
        A minimal WorldState suitable for testing.
    """
    from babylon.models import WorldState

    return WorldState(tick=tick)


# =============================================================================
# TEST GAME OUTCOME ENUM
# =============================================================================


@pytest.mark.unit
class TestGameOutcomeEnum:
    """Test GameOutcome enum definition and values."""

    def test_game_outcome_enum_has_in_progress(self) -> None:
        """GameOutcome must have IN_PROGRESS value.

        The game starts in IN_PROGRESS state and remains there until
        one of the endgame conditions is met.
        """
        assert hasattr(GameOutcome, "IN_PROGRESS")
        assert GameOutcome.IN_PROGRESS.value == "in_progress"

    def test_game_outcome_enum_has_revolutionary_victory(self) -> None:
        """GameOutcome must have REVOLUTIONARY_VICTORY value.

        Represents successful proletarian revolution when:
        - percolation >= 0.7 (mass organization)
        - class_consciousness > 0.8 (ideological clarity)
        """
        assert hasattr(GameOutcome, "REVOLUTIONARY_VICTORY")
        assert GameOutcome.REVOLUTIONARY_VICTORY.value == "revolutionary_victory"

    def test_game_outcome_enum_has_ecological_collapse(self) -> None:
        """GameOutcome must have ECOLOGICAL_COLLAPSE value.

        Represents irreversible ecological collapse when:
        - overshoot_ratio > 2.0 for 5 consecutive ticks
        """
        assert hasattr(GameOutcome, "ECOLOGICAL_COLLAPSE")
        assert GameOutcome.ECOLOGICAL_COLLAPSE.value == "ecological_collapse"

    def test_game_outcome_enum_has_fascist_consolidation(self) -> None:
        """GameOutcome must have FASCIST_CONSOLIDATION value.

        Represents fascist victory when:
        - national_identity > class_consciousness for 3+ nodes
        """
        assert hasattr(GameOutcome, "FASCIST_CONSOLIDATION")
        assert GameOutcome.FASCIST_CONSOLIDATION.value == "fascist_consolidation"


# =============================================================================
# TEST ENDGAME DETECTOR PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestEndgameDetectorProtocol:
    """Test EndgameDetector protocol compliance."""

    def test_endgame_detector_implements_simulation_observer(self) -> None:
        """EndgameDetector must implement SimulationObserver protocol.

        As an observer, it receives state change notifications and
        monitors for endgame conditions without modifying simulation state.
        """
        detector = EndgameDetector()
        assert isinstance(detector, SimulationObserver)

    def test_endgame_detector_has_name_property(self) -> None:
        """EndgameDetector.name returns 'EndgameDetector'."""
        detector = EndgameDetector()
        assert detector.name == "EndgameDetector"


# =============================================================================
# TEST ENDGAME DETECTOR INITIAL STATE
# =============================================================================


@pytest.mark.unit
class TestEndgameDetectorInitialState:
    """Test EndgameDetector initial state."""

    def test_endgame_detector_starts_in_progress(self) -> None:
        """EndgameDetector starts with outcome = IN_PROGRESS.

        Before any state is analyzed, the game is assumed to be ongoing.
        """
        detector = EndgameDetector()
        assert detector.outcome == GameOutcome.IN_PROGRESS

    def test_endgame_detector_is_game_over_false_initially(self) -> None:
        """EndgameDetector.is_game_over is False initially.

        Convenience property to check if game has ended.
        """
        detector = EndgameDetector()
        assert detector.is_game_over is False


# =============================================================================
# TEST REVOLUTIONARY VICTORY DETECTION
# =============================================================================


@pytest.mark.unit
class TestRevolutionaryVictoryDetection:
    """Test detection of revolutionary victory condition."""

    def test_endgame_detector_detects_revolutionary_victory(
        self,
        config: SimulationConfig,
    ) -> None:
        """Detect REVOLUTIONARY_VICTORY when percolation >= 0.7 AND consciousness > 0.8.

        The revolutionary victory condition requires BOTH:
        1. Mass organization: percolation_ratio >= 0.7
        2. Ideological clarity: average class_consciousness > 0.8
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import EdgeType, SocialRole
        from babylon.models.relationship import Relationship

        # Create entities with high class consciousness (> 0.8)
        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Worker {i}",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                class_consciousness=0.9,  # Above 0.8 threshold
            )
            for i in range(10)
        }

        # Create SOLIDARITY edges connecting most entities (for high percolation)
        # Need >= 70% connected in giant component
        relationships = []
        entity_ids = list(entities.keys())
        for i in range(len(entity_ids) - 1):
            relationships.append(
                Relationship(
                    source_id=entity_ids[i],
                    target_id=entity_ids[i + 1],
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.9,
                )
            )

        prev_state = WorldState(tick=0, entities=entities, relationships=relationships)
        new_state = WorldState(tick=1, entities=entities, relationships=relationships)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        assert detector.outcome == GameOutcome.REVOLUTIONARY_VICTORY
        assert detector.is_game_over is True

    def test_no_victory_when_percolation_low(
        self,
        config: SimulationConfig,
    ) -> None:
        """No REVOLUTIONARY_VICTORY when percolation < 0.7 even with high consciousness.

        Both conditions must be met simultaneously.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # High consciousness but isolated entities (no SOLIDARITY edges)
        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Worker {i}",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                class_consciousness=0.9,  # Above threshold
            )
            for i in range(10)
        }

        prev_state = WorldState(tick=0, entities=entities)
        new_state = WorldState(tick=1, entities=entities)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        assert detector.outcome == GameOutcome.IN_PROGRESS

    def test_no_victory_when_consciousness_low(
        self,
        config: SimulationConfig,
    ) -> None:
        """No REVOLUTIONARY_VICTORY when consciousness <= 0.8 even with high percolation.

        Both conditions must be met simultaneously.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import EdgeType, SocialRole
        from babylon.models.relationship import Relationship

        # Low consciousness entities but well connected
        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Worker {i}",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                class_consciousness=0.5,  # Below 0.8 threshold
            )
            for i in range(10)
        }

        relationships = []
        entity_ids = list(entities.keys())
        for i in range(len(entity_ids) - 1):
            relationships.append(
                Relationship(
                    source_id=entity_ids[i],
                    target_id=entity_ids[i + 1],
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.9,
                )
            )

        prev_state = WorldState(tick=0, entities=entities, relationships=relationships)
        new_state = WorldState(tick=1, entities=entities, relationships=relationships)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        assert detector.outcome == GameOutcome.IN_PROGRESS


# =============================================================================
# TEST ECOLOGICAL COLLAPSE DETECTION
# =============================================================================


@pytest.mark.unit
class TestEcologicalCollapseDetection:
    """Test detection of ecological collapse condition."""

    def test_endgame_detector_detects_ecological_collapse(
        self,
        config: SimulationConfig,
    ) -> None:
        """Detect ECOLOGICAL_COLLAPSE when overshoot > 2.0 for 5 consecutive ticks.

        Sustained ecological overshoot represents irreversible collapse.
        The system must track consecutive ticks of overshoot.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType, SocialRole

        # Create high overshoot conditions
        # overshoot_ratio = consumption / biocapacity
        # Need ratio > 2.0

        territory = Territory(
            id="T001",
            name="Depleted Zone",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=10.0,  # Very low biocapacity
            max_biocapacity=100.0,
        )

        # High consumption class
        entity = SocialClass(
            id="C001",
            name="High Consumers",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=100.0,
            s_bio=15.0,
            s_class=10.0,
            # Total consumption = 25.0, ratio = 25/10 = 2.5 > 2.0
        )

        detector = EndgameDetector()

        # Initial state
        initial_state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": entity},
        )
        detector.on_simulation_start(initial_state, config)

        # Run 5 consecutive ticks with overshoot > 2.0
        for tick in range(1, 6):
            prev_state = WorldState(
                tick=tick - 1,
                territories={"T001": territory},
                entities={"C001": entity},
            )
            new_state = WorldState(
                tick=tick,
                territories={"T001": territory},
                entities={"C001": entity},
            )
            detector.on_tick(prev_state, new_state)

        assert detector.outcome == GameOutcome.ECOLOGICAL_COLLAPSE
        assert detector.is_game_over is True

    def test_no_collapse_when_overshoot_interrupted(
        self,
        config: SimulationConfig,
    ) -> None:
        """No ECOLOGICAL_COLLAPSE if overshoot drops below 2.0 before 5 ticks.

        The counter must reset when overshoot ratio becomes sustainable.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType, SocialRole

        detector = EndgameDetector()

        # Start with overshoot territory
        overshoot_territory = Territory(
            id="T001",
            name="Depleted",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=10.0,
        )

        # Sustainable territory
        sustainable_territory = Territory(
            id="T001",
            name="Recovered",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
        )

        entity = SocialClass(
            id="C001",
            name="Consumer",
            role=SocialRole.CORE_BOURGEOISIE,
            s_bio=15.0,
            s_class=10.0,
        )

        initial_state = WorldState(
            tick=0,
            territories={"T001": overshoot_territory},
            entities={"C001": entity},
        )
        detector.on_simulation_start(initial_state, config)

        # Run 3 ticks with overshoot
        for tick in range(1, 4):
            prev = WorldState(
                tick=tick - 1,
                territories={"T001": overshoot_territory},
                entities={"C001": entity},
            )
            new = WorldState(
                tick=tick,
                territories={"T001": overshoot_territory},
                entities={"C001": entity},
            )
            detector.on_tick(prev, new)

        assert detector.outcome == GameOutcome.IN_PROGRESS

        # Tick 4: biocapacity recovers, overshoot < 2.0
        prev = WorldState(
            tick=3,
            territories={"T001": overshoot_territory},
            entities={"C001": entity},
        )
        new = WorldState(
            tick=4,
            territories={"T001": sustainable_territory},
            entities={"C001": entity},
        )
        detector.on_tick(prev, new)

        # Still in progress (counter reset)
        assert detector.outcome == GameOutcome.IN_PROGRESS

        # Run 2 more ticks with overshoot - should NOT trigger (not 5 consecutive)
        for tick in range(5, 7):
            prev = WorldState(
                tick=tick - 1,
                territories={"T001": overshoot_territory},
                entities={"C001": entity},
            )
            new = WorldState(
                tick=tick,
                territories={"T001": overshoot_territory},
                entities={"C001": entity},
            )
            detector.on_tick(prev, new)

        assert detector.outcome == GameOutcome.IN_PROGRESS

    def test_no_collapse_with_moderate_overshoot(
        self,
        config: SimulationConfig,
    ) -> None:
        """No ECOLOGICAL_COLLAPSE if overshoot is between 1.0 and 2.0.

        Overshoot must exceed 2.0 (double the sustainable level) to trigger.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import SectorType, SocialRole

        # Moderate overshoot: ratio = 30/20 = 1.5 (< 2.0)
        territory = Territory(
            id="T001",
            name="Stressed",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=20.0,
        )

        entity = SocialClass(
            id="C001",
            name="Consumer",
            role=SocialRole.CORE_BOURGEOISIE,
            s_bio=15.0,
            s_class=15.0,  # Total = 30
        )

        detector = EndgameDetector()
        initial_state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": entity},
        )
        detector.on_simulation_start(initial_state, config)

        # Run 10 ticks
        for tick in range(1, 11):
            prev = WorldState(
                tick=tick - 1,
                territories={"T001": territory},
                entities={"C001": entity},
            )
            new = WorldState(
                tick=tick,
                territories={"T001": territory},
                entities={"C001": entity},
            )
            detector.on_tick(prev, new)

        assert detector.outcome == GameOutcome.IN_PROGRESS


# =============================================================================
# TEST FASCIST CONSOLIDATION DETECTION
# =============================================================================


@pytest.mark.unit
class TestFascistConsolidationDetection:
    """Test detection of fascist consolidation condition."""

    def test_endgame_detector_detects_fascist_consolidation(
        self,
        config: SimulationConfig,
    ) -> None:
        """Detect FASCIST_CONSOLIDATION when national_identity > class_consciousness for 3+ nodes.

        Fascist victory occurs when false consciousness (national_identity)
        dominates over class consciousness in a majority of social classes.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # Create 5 entities: 4 with fascist consciousness
        entities = {}
        for i in range(5):
            if i < 4:  # 4 fascist nodes (national_identity > class_consciousness)
                entities[f"C{i:03d}"] = SocialClass(
                    id=f"C{i:03d}",
                    name=f"Fascist {i}",
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

        prev_state = WorldState(tick=0, entities=entities)
        new_state = WorldState(tick=1, entities=entities)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        assert detector.outcome == GameOutcome.FASCIST_CONSOLIDATION
        assert detector.is_game_over is True

    def test_no_fascism_when_below_threshold(
        self,
        config: SimulationConfig,
    ) -> None:
        """No FASCIST_CONSOLIDATION when fewer than 3 nodes are fascist.

        The threshold of 3 nodes represents a tipping point.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # Only 2 fascist nodes (below threshold of 3)
        entities = {}
        for i in range(5):
            if i < 2:  # Only 2 fascist
                entities[f"C{i:03d}"] = SocialClass(
                    id=f"C{i:03d}",
                    name=f"Fascist {i}",
                    role=SocialRole.LABOR_ARISTOCRACY,
                    national_identity=0.8,
                    class_consciousness=0.2,
                )
            else:  # 3 class-conscious
                entities[f"C{i:03d}"] = SocialClass(
                    id=f"C{i:03d}",
                    name=f"Worker {i}",
                    role=SocialRole.PERIPHERY_PROLETARIAT,
                    national_identity=0.2,
                    class_consciousness=0.8,
                )

        prev_state = WorldState(tick=0, entities=entities)
        new_state = WorldState(tick=1, entities=entities)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        assert detector.outcome == GameOutcome.IN_PROGRESS

    def test_fascism_exactly_at_threshold(
        self,
        config: SimulationConfig,
    ) -> None:
        """FASCIST_CONSOLIDATION triggers when exactly 3 nodes are fascist.

        The boundary condition: >= 3 nodes.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # Exactly 3 fascist nodes
        entities = {}
        for i in range(5):
            if i < 3:  # Exactly 3 fascist
                entities[f"C{i:03d}"] = SocialClass(
                    id=f"C{i:03d}",
                    name=f"Fascist {i}",
                    role=SocialRole.LABOR_ARISTOCRACY,
                    national_identity=0.8,
                    class_consciousness=0.2,
                )
            else:  # 2 class-conscious
                entities[f"C{i:03d}"] = SocialClass(
                    id=f"C{i:03d}",
                    name=f"Worker {i}",
                    role=SocialRole.PERIPHERY_PROLETARIAT,
                    national_identity=0.2,
                    class_consciousness=0.8,
                )

        prev_state = WorldState(tick=0, entities=entities)
        new_state = WorldState(tick=1, entities=entities)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        assert detector.outcome == GameOutcome.FASCIST_CONSOLIDATION


# =============================================================================
# TEST EVENT EMISSION
# =============================================================================


@pytest.mark.unit
class TestEndgameEventEmission:
    """Test that EndgameDetector emits ENDGAME_REACHED event."""

    def test_endgame_detector_emits_endgame_reached_event(
        self,
        config: SimulationConfig,
    ) -> None:
        """EndgameDetector emits ENDGAME_REACHED event when game ends.

        The event should be retrievable via get_pending_events() similar
        to TopologyMonitor's PHASE_TRANSITION events.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # Trigger fascist consolidation (quickest to set up)
        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Fascist {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                national_identity=0.9,
                class_consciousness=0.1,
            )
            for i in range(5)
        }

        prev_state = WorldState(tick=0, entities=entities)
        new_state = WorldState(tick=1, entities=entities)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        # Get pending events
        events = detector.get_pending_events()

        # Should have exactly one ENDGAME_REACHED event
        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.ENDGAME_REACHED
        assert event.payload["outcome"] == GameOutcome.FASCIST_CONSOLIDATION.value

    def test_no_event_when_game_continues(
        self,
        config: SimulationConfig,
    ) -> None:
        """No ENDGAME_REACHED event when game is still IN_PROGRESS."""
        from babylon.models import WorldState

        prev_state = WorldState(tick=0)
        new_state = WorldState(tick=1)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        events = detector.get_pending_events()
        assert len(events) == 0

    def test_event_only_emitted_once(
        self,
        config: SimulationConfig,
    ) -> None:
        """ENDGAME_REACHED event is emitted only once when game ends.

        Subsequent ticks should not emit additional events.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Fascist {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                national_identity=0.9,
                class_consciousness=0.1,
            )
            for i in range(5)
        }

        detector = EndgameDetector()
        initial_state = WorldState(tick=0, entities=entities)
        detector.on_simulation_start(initial_state, config)

        # First tick - should emit event
        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )
        events1 = detector.get_pending_events()
        assert len(events1) == 1

        # Second tick - should NOT emit again
        detector.on_tick(
            WorldState(tick=1, entities=entities),
            WorldState(tick=2, entities=entities),
        )
        events2 = detector.get_pending_events()
        assert len(events2) == 0


# =============================================================================
# TEST LIFECYCLE HOOKS
# =============================================================================


@pytest.mark.unit
class TestEndgameDetectorLifecycle:
    """Test EndgameDetector lifecycle hooks."""

    def test_on_simulation_start_resets_state(
        self,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_start resets detector to initial state.

        Allows reuse of detector across multiple simulation runs.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Fascist {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                national_identity=0.9,
                class_consciousness=0.1,
            )
            for i in range(5)
        }

        detector = EndgameDetector()

        # First run - ends in fascism
        detector.on_simulation_start(WorldState(tick=0, entities=entities), config)
        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )
        assert detector.outcome == GameOutcome.FASCIST_CONSOLIDATION

        # Reset with new simulation start
        detector.on_simulation_start(WorldState(tick=0), config)

        # Should be back to IN_PROGRESS
        assert detector.outcome == GameOutcome.IN_PROGRESS
        assert detector.is_game_over is False

    def test_on_simulation_end_no_crash(
        self,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_end does not crash."""
        detector = EndgameDetector()
        final_state = create_minimal_state(tick=100)

        # Should not raise
        detector.on_simulation_end(final_state)


# =============================================================================
# TEST PRIORITY / PRECEDENCE
# =============================================================================


@pytest.mark.unit
class TestEndgamePriority:
    """Test precedence when multiple endgame conditions are met."""

    def test_revolutionary_victory_takes_precedence(
        self,
        config: SimulationConfig,
    ) -> None:
        """Revolutionary victory should be checked first.

        If revolution succeeds, that's the preferred ending - the people won.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.entities.territory import Territory
        from babylon.models.enums import EdgeType, SectorType, SocialRole
        from babylon.models.relationship import Relationship

        # Conditions for both revolutionary victory AND fascist consolidation
        # (unlikely in reality, but tests precedence logic)
        entities = {}
        relationships = []

        for i in range(10):
            entities[f"C{i:03d}"] = SocialClass(
                id=f"C{i:03d}",
                name=f"Worker {i}",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                class_consciousness=0.9,  # High (for revolution)
                national_identity=0.95,  # Even higher (for fascism check)
            )

        entity_ids = list(entities.keys())
        for i in range(len(entity_ids) - 1):
            relationships.append(
                Relationship(
                    source_id=entity_ids[i],
                    target_id=entity_ids[i + 1],
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.9,
                )
            )

        # Also add ecological collapse conditions
        territory = Territory(
            id="T001",
            name="Depleted",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=5.0,
        )

        for eid in entities:
            entities[eid] = entities[eid].model_copy(update={"s_bio": 5.0, "s_class": 10.0})

        detector = EndgameDetector()

        initial_state = WorldState(
            tick=0,
            entities=entities,
            relationships=relationships,
            territories={"T001": territory},
        )
        detector.on_simulation_start(initial_state, config)

        # Run enough ticks for ecological collapse
        for tick in range(1, 6):
            prev = WorldState(
                tick=tick - 1,
                entities=entities,
                relationships=relationships,
                territories={"T001": territory},
            )
            new = WorldState(
                tick=tick,
                entities=entities,
                relationships=relationships,
                territories={"T001": territory},
            )
            detector.on_tick(prev, new)

            # Revolutionary victory should trigger first
            if detector.is_game_over:
                break

        # Revolutionary victory takes precedence
        assert detector.outcome == GameOutcome.REVOLUTIONARY_VICTORY
