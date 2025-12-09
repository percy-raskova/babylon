"""Integration tests for the narrative generation pipeline.

TDD Red Phase: These tests define the contract for wiring NarrativeDirector
to LLMProvider for generating AI commentary from simulation events.

The NarrativeDirector should:
1. Accept an optional LLMProvider via the `llm` constructor parameter
2. Track generated narratives in a `narrative_log` property
3. Call the LLM when SURPLUS_EXTRACTION events occur
4. Include RAG context in the prompt sent to the LLM

Design Philosophy:
- Observer, not controller: watches state transitions
- Fail-safe: LLM errors don't propagate to simulation (ADR003)
- Event-driven: only generates narrative for specific event types
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
        """
        # Arrange
        mock_llm = MockLLM(responses=["The capitalist class is extracting value."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            rag_pipeline=None,  # No RAG for this test
        )

        # Create states: t0 (no events) -> t1 (with SURPLUS_EXTRACTION)
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: SURPLUS_EXTRACTION - Worker exploited"],
            }
        )

        # Initialize director (simulating simulation start)
        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert (
            len(director.narrative_log) == 1
        ), "Expected one narrative entry after SURPLUS_EXTRACTION event"
        assert director.narrative_log[0] == "The capitalist class is extracting value."
        assert (
            mock_llm.call_count == 1
        ), "MockLLM should be called exactly once for SURPLUS_EXTRACTION"

    @pytest.mark.integration
    def test_no_narrative_without_surplus_extraction_event(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """LLM not called when no SURPLUS_EXTRACTION events.

        This test ensures the Director filters events appropriately.
        Only SURPLUS_EXTRACTION events should trigger LLM generation.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Should not see this."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        # Create states: t0 (no events) -> t1 (with different event type)
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: CONSCIOUSNESS_DRIFT - Worker awakens"],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert (
            len(director.narrative_log) == 0
        ), "No narrative should be generated for non-SURPLUS_EXTRACTION events"
        assert (
            mock_llm.call_count == 0
        ), "MockLLM should not be called for non-SURPLUS_EXTRACTION events"

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

        # Create states with SURPLUS_EXTRACTION event
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: SURPLUS_EXTRACTION occurred"],
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
        assert (
            "Marx wrote about surplus value" in call_args["prompt"]
        ), "RAG context should be included in the prompt sent to LLM"

    @pytest.mark.integration
    def test_llm_error_does_not_crash_observer(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """LLM errors are caught and logged, not propagated (ADR003).

        The simulation must never crash due to AI layer failures.
        """
        # Arrange
        mock_llm = MagicMock()
        mock_llm.name = "FailingLLM"
        mock_llm.generate.side_effect = Exception("LLM service unavailable")

        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: SURPLUS_EXTRACTION - Error test"],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act - should not raise
        director.on_tick(state_t0, state_t1)

        # Assert - no narrative generated but no crash
        assert len(director.narrative_log) == 0

    @pytest.mark.integration
    def test_case_insensitive_surplus_extraction_matching(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """SURPLUS_EXTRACTION matching is case-insensitive.

        Both 'SURPLUS_EXTRACTION' and 'surplus_extraction' should trigger.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Response 1", "Response 2"])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        # Test lowercase variant
        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: surplus_extraction - lowercase test"],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert (
            len(director.narrative_log) == 1
        ), "lowercase surplus_extraction should trigger narrative generation"
        assert mock_llm.call_count == 1

    @pytest.mark.integration
    def test_multiple_surplus_extraction_events_in_single_tick(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Multiple SURPLUS_EXTRACTION events in one tick generate one narrative.

        The Director should call LLM once per tick, not once per event.
        """
        # Arrange
        mock_llm = MockLLM(responses=["Combined analysis of multiple extractions."])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": [
                    "Tick 1: SURPLUS_EXTRACTION - Worker A exploited",
                    "Tick 1: SURPLUS_EXTRACTION - Worker B exploited",
                    "Tick 1: CONSCIOUSNESS_DRIFT - Unrelated event",
                ],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act
        director.on_tick(state_t0, state_t1)

        # Assert
        assert (
            len(director.narrative_log) == 1
        ), "Only one narrative per tick, regardless of event count"
        assert mock_llm.call_count == 1

    @pytest.mark.integration
    def test_narrative_log_returns_copy(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """narrative_log returns a copy to prevent external modification."""
        # Arrange
        mock_llm = MockLLM(responses=["Test narrative"])
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: SURPLUS_EXTRACTION"],
            }
        )

        director.on_simulation_start(state_t0, config)
        director.on_tick(state_t0, state_t1)

        # Act - modify the returned list
        log_copy = director.narrative_log
        log_copy.clear()

        # Assert - internal state unchanged
        assert (
            len(director.narrative_log) == 1
        ), "narrative_log should return a copy, not the internal list"

    @pytest.mark.integration
    def test_no_llm_generation_when_use_llm_false(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """No LLM generation when use_llm=False even with LLM provided."""
        # Arrange
        mock_llm = MockLLM(responses=["Should not be called"])
        director = NarrativeDirector(
            use_llm=False,  # Explicitly disabled
            llm=mock_llm,
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: SURPLUS_EXTRACTION"],
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
        """No LLM generation when llm=None (backward compatibility)."""
        # Arrange
        director = NarrativeDirector(
            use_llm=True,  # Even with this enabled
            llm=None,  # But no LLM provided
        )

        state_t0 = initial_state
        state_t1 = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: SURPLUS_EXTRACTION"],
            }
        )

        director.on_simulation_start(state_t0, config)

        # Act - should not crash
        director.on_tick(state_t0, state_t1)

        # Assert
        assert len(director.narrative_log) == 0, "No narrative when llm=None"
