"""Integration tests for the narrative generation pipeline.

TDD Red Phase: These tests define the contract for wiring NarrativeDirector
to LLMProvider for generating AI commentary from simulation events.

The NarrativeDirector should:
1. Accept an optional LLMProvider via the `llm` constructor parameter
2. Track generated narratives in a `narrative_log` property
3. Call the LLM when significant events occur (Sprint 4.1: typed events)
4. Include RAG context in the prompt sent to the LLM

Design Philosophy:
- Observer, not controller: watches state transitions
- Fail-safe: LLM errors don't propagate to simulation (ADR003)
- Event-driven: only generates narrative for specific event types

Sprint 4.1: Updated to use typed SimulationEvent objects from state.events
instead of string-based event_log.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    pass

from babylon.ai.director import NarrativeDirector
from babylon.ai.llm_provider import MockLLM
from babylon.models import (
    SimulationConfig,
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.events import ExtractionEvent, TransmissionEvent

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return SocialClass(
        id="C001",
        name="Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


@pytest.fixture
def initial_state(worker: SocialClass) -> WorldState:
    """Create initial WorldState with one worker entity."""
    return WorldState(
        tick=0,
        entities={"C001": worker},
        event_log=[],
    )


# =============================================================================
# TEST NARRATIVE PIPELINE INTEGRATION
# =============================================================================


class TestNarrativePipeline:
    """Integration tests for NarrativeDirector with LLM."""

    @pytest.mark.integration
    def test_surplus_extraction_triggers_narrative_generation(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """LLM generates narrative when SURPLUS_EXTRACTION event occurs.

        This test verifies the complete pipeline:
        1. NarrativeDirector receives tick with SURPLUS_EXTRACTION event
        2. Director calls LLM with context built from state and events
        3. LLM response is stored in narrative_log

        Sprint 4.1: Updated to use typed ExtractionEvent instead of string.
        """
        # Arrange
        mock_llm = MockLLM(responses=["The capitalist class is extracting value."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,  # No RAG for this test
        )

        # Create typed extraction event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        # Create states: t0 (no events) -> t1 (with SURPLUS_EXTRACTION)
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        # Initialize director (simulating simulation start)
        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 1, (
            "Expected one narrative entry after SURPLUS_EXTRACTION event"
        )
        assert director.narrative_log[0] == "The capitalist class is extracting value."
        assert mock_llm.call_count == 1, (
            "MockLLM should be called exactly once for SURPLUS_EXTRACTION"
        )

    @pytest.mark.integration
    def test_no_narrative_without_significant_event(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """LLM not called when no significant events occur.

        This test ensures the Director filters events appropriately.
        Only significant events (SURPLUS_EXTRACTION, CRISIS, etc.) trigger LLM.

        Sprint 4.1: Updated to use typed TransmissionEvent (non-significant).
        """
        # Arrange
        mock_llm = MockLLM(responses=["Should not see this."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        # Create a non-significant typed event (Sprint 4.1)
        transmission_event = TransmissionEvent(
            tick=1,
            target_id="C001",
            source_id="C002",
            delta=0.05,
            solidarity_strength=0.5,
        )

        # Create states: t0 (no events) -> t1 (with non-significant event)
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [transmission_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 0, (
            "No narrative should be generated for non-significant events"
        )
        assert mock_llm.call_count == 0, "MockLLM should not be called for non-significant events"

    @pytest.mark.integration
    def test_narrative_with_rag_context(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Narrative generation includes RAG context when available.

        This test verifies that:
        1. RAG pipeline is queried for context
        2. RAG context is included in the prompt sent to LLM

        Sprint 4.1: Updated to use typed ExtractionEvent.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Analysis with historical context."])

        # Create mock RAG pipeline
        mock_rag = MagicMock()
        mock_result = MagicMock()
        mock_result.chunk = MagicMock()
        mock_result.chunk.content = "Marx wrote about surplus value extraction..."
        mock_rag.query.return_value = MagicMock(results=[mock_result])

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=mock_rag,
        )

        # Create typed extraction event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        # Create states with SURPLUS_EXTRACTION event
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 1, "Narrative should be generated with RAG context"
        mock_rag.query.assert_called_once()

        # Verify the prompt includes RAG context
        call_args = mock_llm.call_history[0]
        assert "Marx wrote about surplus value" in call_args["prompt"], (
            "RAG context should be included in the prompt sent to LLM"
        )

    @pytest.mark.integration
    def test_llm_error_does_not_crash_observer(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """LLM errors are caught and logged, not propagated (ADR003).

        The simulation must never crash due to AI layer failures.

        Sprint 4.1: Updated to use typed ExtractionEvent.
        """
        # Arrange
        mock_llm = MagicMock()
        mock_llm.name = "FailingLLM"
        mock_llm.generate.side_effect = Exception("LLM service unavailable")

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        # Create typed extraction event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act - should not raise
        director.on_tick(state_t0, state_t1)

        # Assert - no narrative generated but no crash
        assert len(director.narrative_log) == 0

    @pytest.mark.integration
    def test_extraction_event_type_triggers_narrative(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """ExtractionEvent with SURPLUS_EXTRACTION type triggers narrative.

        Sprint 4.1: Typed events use EventType enum instead of string matching.
        This test verifies the typed event system works correctly.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Extraction narrative."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        # Create typed extraction event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=15.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 1, (
            "ExtractionEvent should trigger narrative generation"
        )
        assert mock_llm.call_count == 1

    @pytest.mark.integration
    def test_multiple_extraction_events_in_single_tick(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Multiple ExtractionEvents in one tick generate one narrative.

        The Director should call LLM once per tick, not once per event.

        Sprint 4.1: Updated to use typed ExtractionEvents and TransmissionEvent.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Combined analysis of multiple extractions."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        # Create multiple typed events (Sprint 4.1)
        extraction_event_a = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        extraction_event_b = ExtractionEvent(
            tick=1,
            source_id="C003",
            target_id="C002",
            amount=12.0,
        )
        transmission_event = TransmissionEvent(
            tick=1,
            target_id="C001",
            source_id="C002",
            delta=0.05,
            solidarity_strength=0.5,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event_a, extraction_event_b, transmission_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 1, (
            "Only one narrative per tick, regardless of event count"
        )
        assert mock_llm.call_count == 1

    @pytest.mark.integration
    def test_narrative_log_returns_copy(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """narrative_log returns a copy to prevent external modification.

        Sprint 4.1: Updated to use typed ExtractionEvent.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Test narrative"])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        # Create typed extraction event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)
        director.on_tick(state_t0, state_t1)

        # Act - modify the returned list
        log_copy = director.narrative_log
        log_copy.clear()

        # Assert - internal state unchanged
        assert len(director.narrative_log) == 1, (
            "narrative_log should return a copy, not the internal list"
        )

    @pytest.mark.integration
    def test_no_llm_generation_when_use_llm_false(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """No LLM generation when use_llm=False even with LLM provided.

        Sprint 4.1: Updated to use typed ExtractionEvent.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Should not be called"])
        director = NarrativeDirector(
            use_llm=False,  # Explicitly disabled
            llm=mock_llm,
        )

        # Create typed extraction event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 0, "No narrative when use_llm=False"
        assert mock_llm.call_count == 0, "LLM should not be called when use_llm=False"

    @pytest.mark.integration
    def test_no_llm_generation_when_llm_none(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """No LLM generation when llm=None (backward compatibility).

        Sprint 4.1: Updated to use typed ExtractionEvent.
        """
        # Arrange
        director = NarrativeDirector(
            use_llm=True,  # Even with this enabled
            llm=None,  # But no LLM provided
        )

        # Create typed extraction event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act - should not crash
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 0, "No narrative when llm=None"


# =============================================================================
# TEST TYPED EVENT CONSUMPTION (Sprint 4.1)
# =============================================================================


class TestTypedEventConsumption:
    """Tests for consuming typed SimulationEvent objects instead of strings.

    Sprint 4.1: The Narrative Bridge

    The NarrativeDirector should consume typed events from state.events
    instead of string-based event_log. This enables richer narrative
    generation with access to structured event data.
    """

    @pytest.mark.integration
    def test_phase_transition_event_formats_with_cadre_density(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """PhaseTransitionEvent prompt contains phase and cadre_density info.

        When a PhaseTransitionEvent occurs, the prompt sent to the LLM
        should include human-readable information about:
        - The phase transition (e.g., "gaseous" -> "solid")
        - The cadre density metric
        """
        from babylon.models.events import PhaseTransitionEvent

        # Arrange
        mock_llm = MockLLM(responses=["The movement has solidified."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        phase_event = PhaseTransitionEvent(
            tick=5,
            previous_state="liquid",
            new_state="solid",
            percolation_ratio=0.72,
            num_components=2,
            largest_component_size=18,
            cadre_density=0.72,
        )

        # Create state with typed event
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 5,
                "events": [phase_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - LLM should be called for PHASE_TRANSITION
        assert mock_llm.call_count == 1, "PhaseTransitionEvent should trigger LLM generation"
        prompt = mock_llm.call_history[0]["prompt"]
        # Prompt should contain phase information
        assert "solid" in prompt.lower() or "phase" in prompt.lower(), (
            f"Prompt should contain phase info, got: {prompt[:200]}"
        )

    @pytest.mark.integration
    def test_crisis_event_triggers_narrative(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """CrisisEvent triggers narrative generation.

        Economic crises are significant events that should trigger
        narrative generation when pool_ratio falls below threshold.
        """
        from babylon.models.events import CrisisEvent

        # Arrange
        mock_llm = MockLLM(responses=["The crisis deepens."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        crisis_event = CrisisEvent(
            tick=10,
            pool_ratio=0.35,
            aggregate_tension=0.7,
            decision="AUSTERITY",
            wage_delta=-0.05,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 10,
                "events": [crisis_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - LLM should be called for ECONOMIC_CRISIS
        assert mock_llm.call_count == 1, "CrisisEvent should trigger LLM generation"

    @pytest.mark.integration
    def test_director_uses_typed_events_not_event_log(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Director processes typed events even when event_log is empty.

        This test verifies the transition from string-based event_log
        to typed events. The director should process state.events
        independently of event_log.
        """
        from babylon.models.events import ExtractionEvent

        # Arrange
        mock_llm = MockLLM(responses=["Extraction narrative."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        extraction_event = ExtractionEvent(
            tick=3,
            source_id="C001",
            target_id="C002",
            amount=15.5,
        )

        # State with typed event but EMPTY event_log
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 3,
                "event_log": [],  # Deliberately empty
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - Should process typed events
        assert mock_llm.call_count == 1, (
            "Director should process typed events even with empty event_log"
        )

    @pytest.mark.integration
    def test_uprising_event_triggers_narrative(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """UprisingEvent triggers narrative generation.

        Uprisings are dramatic events from the George Floyd Dynamic
        that should definitely trigger narrative generation.
        """
        from babylon.models.events import UprisingEvent

        # Arrange
        mock_llm = MockLLM(responses=["The streets erupt in protest."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        uprising_event = UprisingEvent(
            tick=8,
            node_id="C001",
            trigger="spark",
            agitation=0.9,
            repression=0.7,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 8,
                "events": [uprising_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - LLM should be called for UPRISING
        assert mock_llm.call_count == 1, "UprisingEvent should trigger LLM generation"

    @pytest.mark.integration
    def test_spark_event_triggers_narrative(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """SparkEvent (EXCESSIVE_FORCE) triggers narrative generation.

        State violence events are the spark that can ignite uprisings.
        These should trigger narrative generation.
        """
        from babylon.models.events import SparkEvent

        # Arrange
        mock_llm = MockLLM(responses=["Police violence sparks outrage."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        spark_event = SparkEvent(
            tick=5,
            node_id="C001",
            repression=0.8,
            spark_probability=0.4,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 5,
                "events": [spark_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - LLM should be called for EXCESSIVE_FORCE
        assert mock_llm.call_count == 1, "SparkEvent should trigger LLM generation"

    @pytest.mark.integration
    def test_rupture_event_triggers_narrative(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """RuptureEvent triggers narrative generation.

        Rupture represents the dialectical moment when contradictions
        become irreconcilable - a significant narrative moment.
        """
        from babylon.models.events import RuptureEvent

        # Arrange
        mock_llm = MockLLM(responses=["The contradictions explode."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        rupture_event = RuptureEvent(
            tick=15,
            edge="C001->C002",
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 15,
                "events": [rupture_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - LLM should be called for RUPTURE
        assert mock_llm.call_count == 1, "RuptureEvent should trigger LLM generation"

    @pytest.mark.integration
    def test_typed_event_format_includes_structured_data(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Typed event formatting includes structured data in prompt.

        The PromptBuilder should format typed events with their
        specific fields, not just a generic string representation.
        """
        from babylon.models.events import CrisisEvent

        # Arrange
        mock_llm = MockLLM(responses=["Economic analysis."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        crisis_event = CrisisEvent(
            tick=10,
            pool_ratio=0.15,
            aggregate_tension=0.85,
            decision="IRON_FIST",
            wage_delta=-0.10,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 10,
                "events": [crisis_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - Prompt should contain crisis-specific data
        prompt = mock_llm.call_history[0]["prompt"]
        # Should contain pool ratio or tension info
        assert "0.15" in prompt or "15%" in prompt or "pool" in prompt.lower(), (
            f"Prompt should include crisis metrics, got: {prompt[:300]}"
        )

    @pytest.mark.integration
    def test_multiple_typed_events_all_formatted(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Multiple typed events in one tick are all formatted in prompt.

        When multiple events occur in a single tick, all should be
        included in the context sent to the LLM.
        """
        from babylon.models.events import ExtractionEvent, SparkEvent

        # Arrange
        mock_llm = MockLLM(responses=["Multiple events narrative."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        extraction_event = ExtractionEvent(
            tick=5,
            source_id="C001",
            target_id="C002",
            amount=20.0,
        )
        spark_event = SparkEvent(
            tick=5,
            node_id="C001",
            repression=0.8,
            spark_probability=0.3,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 5,
                "events": [extraction_event, spark_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - Both events should be in the prompt
        assert mock_llm.call_count == 1
        prompt = mock_llm.call_history[0]["prompt"]
        # Should contain references to both event types
        assert "extraction" in prompt.lower() or "surplus" in prompt.lower(), (
            f"Prompt should include extraction event, got: {prompt[:300]}"
        )
        assert (
            "force" in prompt.lower() or "spark" in prompt.lower() or "repression" in prompt.lower()
        ), f"Prompt should include spark event, got: {prompt[:300]}"

    @pytest.mark.integration
    def test_non_significant_event_does_not_trigger_llm(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """TransmissionEvent (non-significant) does not trigger LLM.

        Not all events should trigger narrative generation. Only
        significant events like CRISIS, UPRISING, etc. should.
        """
        from babylon.models.events import TransmissionEvent

        # Arrange
        mock_llm = MockLLM(responses=["Should not be called."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,
        )

        transmission_event = TransmissionEvent(
            tick=3,
            target_id="C001",
            source_id="C002",
            delta=0.05,
            solidarity_strength=0.8,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 3,
                "events": [transmission_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - LLM should NOT be called for routine events
        assert mock_llm.call_count == 0, "TransmissionEvent should NOT trigger LLM generation"


# =============================================================================
# TEST PERSONA INTEGRATION (Sprint 4.2)
# =============================================================================


class TestPersonaIntegration:
    """Integration tests for Persona system with NarrativeDirector.

    Sprint 4.2: The Voice (JSON Edition)

    These tests verify the complete persona pipeline:
    1. Load persona from JSON file
    2. Create NarrativeDirector with persona
    3. Run simulation ticks with events
    4. Verify persona voice is used in LLM prompts
    """

    @pytest.mark.integration
    def test_persona_system_prompt_used_in_llm_call(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Persona's system prompt is passed to LLM during narrative generation.

        When a persona is provided, the NarrativeDirector should use
        the persona's render_system_prompt() output as the LLM system prompt.
        """
        from babylon.ai import load_default_persona

        # Arrange - load Percy Raskova persona
        percy = load_default_persona()
        mock_llm = MockLLM(responses=["The contradictions intensify, Architect."])

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=percy,  # Sprint 4.2: persona injection
        )

        # Create extraction event to trigger narrative
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=15.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - LLM was called with persona's system prompt
        assert mock_llm.call_count == 1
        call_args = mock_llm.call_history[0]
        system_prompt = call_args.get("system_prompt", "")

        # Persona-specific content should be in system prompt
        assert "Persephone" in system_prompt or "Percy" in system_prompt, (
            f"System prompt should contain persona name, got: {system_prompt[:200]}"
        )
        assert "Architect" in system_prompt, (
            "System prompt should contain persona's address term 'Architect'"
        )
        # Check that voice content is present (tone or style keywords)
        assert "Sardonic" in system_prompt or "Visceral" in system_prompt, (
            "System prompt should contain persona's voice style"
        )

    @pytest.mark.integration
    def test_persona_directives_in_system_prompt(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Persona directives are included in LLM system prompt.

        The persona's behavioral directives should be part of the
        system prompt to guide LLM output style.
        """
        from babylon.ai import load_default_persona

        # Arrange
        percy = load_default_persona()
        mock_llm = MockLLM(responses=["Extraction proceeds."])

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=percy,
        )

        # Create extraction event
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - Directives should be in system prompt
        assert mock_llm.call_count == 1
        system_prompt = mock_llm.call_history[0].get("system_prompt", "")

        # Check for directive keywords from Percy's character
        assert "moralize" in system_prompt.lower() or "directive" in system_prompt.lower(), (
            f"System prompt should contain directives, got: {system_prompt[:300]}"
        )

    @pytest.mark.integration
    def test_persona_obsessions_in_system_prompt(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Persona obsessions are included in LLM system prompt.

        The persona's thematic obsessions should guide the narrative focus.
        """
        from babylon.ai import load_default_persona

        # Arrange
        percy = load_default_persona()
        mock_llm = MockLLM(responses=["The hegemony collapses."])

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=percy,
        )

        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - Obsessions should be in system prompt
        system_prompt = mock_llm.call_history[0].get("system_prompt", "")

        # Percy's obsessions include hegemony, material basis, historical parallels
        assert (
            "hegemonic" in system_prompt.lower()
            or "collapse" in system_prompt.lower()
            or "material" in system_prompt.lower()
        ), f"System prompt should contain obsessions, got: {system_prompt[:300]}"

    @pytest.mark.integration
    def test_no_persona_uses_default_system_prompt(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Without persona, NarrativeDirector uses default system prompt.

        This ensures backward compatibility with existing code.
        """
        # Arrange - NO persona
        mock_llm = MockLLM(responses=["Default narrative."])

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=None,  # Explicitly no persona
        )

        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - Should use default (game master style)
        system_prompt = mock_llm.call_history[0].get("system_prompt", "")

        # Default prompt should mention game master or simulation
        assert "game master" in system_prompt.lower() or "simulation" in system_prompt.lower(), (
            f"Default system prompt expected, got: {system_prompt[:200]}"
        )
        # Should NOT contain Percy-specific content
        assert "Persephone" not in system_prompt
        assert "Architect" not in system_prompt

    @pytest.mark.integration
    def test_persona_with_crisis_event(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Persona voice is maintained during crisis events.

        Economic crisis events should still use the persona's voice
        and analytical style.
        """
        from babylon.ai import load_default_persona
        from babylon.models.events import CrisisEvent

        # Arrange
        percy = load_default_persona()
        mock_llm = MockLLM(responses=["The mathematical inevitability unfolds."])

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=percy,
        )

        crisis_event = CrisisEvent(
            tick=5,
            pool_ratio=0.25,
            aggregate_tension=0.75,
            decision="AUSTERITY",
            wage_delta=-0.08,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 5,
                "events": [crisis_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert - Persona system prompt used for crisis narration
        assert mock_llm.call_count == 1
        system_prompt = mock_llm.call_history[0].get("system_prompt", "")
        prompt = mock_llm.call_history[0]["prompt"]

        # Persona should be in system prompt
        assert "Persephone" in system_prompt or "Architect" in system_prompt
        # Crisis data should be in user prompt
        assert "crisis" in prompt.lower() or "austerity" in prompt.lower()

    @pytest.mark.integration
    def test_persona_with_phase_transition_event(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Persona voice narrates phase transitions appropriately.

        Phase transitions (gaseous -> liquid -> solid) are core to Percy's
        analytical framework and should be narrated in her voice.
        """
        from babylon.ai import load_default_persona
        from babylon.models.events import PhaseTransitionEvent

        # Arrange
        percy = load_default_persona()
        mock_llm = MockLLM(responses=["The movement crystallizes into vanguard form."])

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=percy,
        )

        phase_event = PhaseTransitionEvent(
            tick=10,
            previous_state="liquid",
            new_state="solid",
            percolation_ratio=0.65,
            num_components=2,
            largest_component_size=15,
            cadre_density=0.58,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 10,
                "events": [phase_event],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert mock_llm.call_count == 1
        system_prompt = mock_llm.call_history[0].get("system_prompt", "")
        prompt = mock_llm.call_history[0]["prompt"]

        # Percy's obsessions should be in system prompt
        assert "rotting" in system_prompt or "chaos" in system_prompt, (
            "Percy's obsessions should be in system prompt"
        )
        # Event data should be in prompt
        assert "solid" in prompt.lower() or "phase" in prompt.lower()

    @pytest.mark.integration
    def test_full_simulation_loop_with_persona(
        self,
        config: SimulationConfig,
    ) -> None:
        """Complete simulation loop with Persona-driven narrative.

        This end-to-end test runs multiple ticks with different events
        and verifies the persona voice is consistent throughout.
        """
        from babylon.ai import load_default_persona
        from babylon.models.events import CrisisEvent, UprisingEvent

        # Arrange - Full simulation scenario
        percy = load_default_persona()

        mock_responses = [
            "The extraction proceeds with imperial efficiency.",
            "The masses rise in uprising.",
            "The contradictions accumulate toward rupture.",
        ]
        mock_llm = MockLLM(responses=mock_responses)

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=percy,
        )

        worker = SocialClass(
            id="C001",
            name="PeripheryWorker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.3,
            ideology=-0.5,
            organization=0.2,
            repression_faced=0.6,
            subsistence_threshold=0.25,
        )

        state = WorldState(tick=0, entities={"C001": worker})

        # Events for each tick - all are SIGNIFICANT_EVENT_TYPES
        # (SURPLUS_EXTRACTION, ECONOMIC_CRISIS, PHASE_TRANSITION, UPRISING)
        events_per_tick = [
            [ExtractionEvent(tick=1, source_id="C001", target_id="C002", amount=12.0)],
            [
                UprisingEvent(
                    tick=2, node_id="C001", trigger="spark", agitation=0.85, repression=0.7
                )
            ],
            [
                CrisisEvent(
                    tick=3,
                    pool_ratio=0.3,
                    aggregate_tension=0.65,
                    decision="IRON_FIST",
                    wage_delta=-0.05,
                )
            ],
        ]

        director.on_simulation_start(state, config)

        # Act - Run 3 ticks (events accumulate like in real simulation)
        accumulated_events: list = []
        for tick_num, new_events in enumerate(events_per_tick, start=1):
            prev_state = state
            accumulated_events = accumulated_events + new_events  # Events accumulate
            state = state.model_copy(update={"tick": tick_num, "events": accumulated_events})
            director.on_tick(prev_state, state)

        # Assert - 3 narratives generated with consistent persona
        assert len(director.narrative_log) == 3, "One narrative per tick with significant events"
        assert mock_llm.call_count == 3

        # All calls should use Percy's system prompt
        for call in mock_llm.call_history:
            system_prompt = call.get("system_prompt", "")
            assert "Persephone" in system_prompt or "Architect" in system_prompt, (
                "All LLM calls should use Percy's persona"
            )
