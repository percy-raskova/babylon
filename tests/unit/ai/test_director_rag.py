"""Tests for NarrativeDirector RAG integration.

TDD Red Phase: These tests define the contract for RAG pipeline injection
into NarrativeDirector. The Director uses RAG to retrieve historical and
theoretical context to inform narrative generation.

Design decisions (from plan):
- Async Handling: Use sync wrappers (pipeline.query() not aquery())
- RAG Injection: Optional constructor param for backward compatibility
- Error Handling: Catch RAG errors, log, continue (ADR003)
- Context Format: Follow AI_COMMS.md hierarchy
- Query Strategy: Join new events as query text, top_k=3
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    pass

from babylon.models import (
    EdgeType,
    Relationship,
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
def owner() -> SocialClass:
    """Create a core owner social class."""
    return SocialClass(
        id="C002",
        name="Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10.0,
        ideology=0.5,
        organization=0.7,
        repression_faced=0.1,
        subsistence_threshold=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=5.0,
        tension=0.5,
    )


@pytest.fixture
def initial_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create initial WorldState."""
    return WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


@pytest.fixture
def mock_rag_pipeline() -> MagicMock:
    """Create mock RagPipeline with query response.

    Note: We mock the RagPipeline without importing it to avoid
    triggering the full RAG import chain (which requires lifecycle module).
    """
    mock = MagicMock()

    # Create mock QueryResponse with results
    mock_result1 = MagicMock()
    mock_result1.chunk = MagicMock()
    mock_result1.chunk.content = "The revolutionary spirit spreads through the workers."

    mock_result2 = MagicMock()
    mock_result2.chunk = MagicMock()
    mock_result2.chunk.content = "Class consciousness emerges from material conditions."

    mock_result3 = MagicMock()
    mock_result3.chunk = MagicMock()
    mock_result3.chunk.content = "Dialectical tensions accumulate until rupture."

    mock_response = MagicMock()
    mock_response.results = [mock_result1, mock_result2, mock_result3]
    mock_response.total_results = 3

    mock.query.return_value = mock_response
    return mock


@pytest.fixture
def mock_prompt_builder() -> MagicMock:
    """Create mock DialecticalPromptBuilder."""
    from babylon.ai.prompt_builder import DialecticalPromptBuilder

    mock = MagicMock(spec=DialecticalPromptBuilder)
    mock.build_system_prompt.return_value = "System prompt"
    mock.build_context_block.return_value = "Context block"
    return mock


# =============================================================================
# TEST CONSTRUCTOR
# =============================================================================


@pytest.mark.unit
class TestDirectorRAGConstructor:
    """Tests for NarrativeDirector RAG injection constructor."""

    def test_director_accepts_optional_rag_pipeline(
        self,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """NarrativeDirector accepts optional RAG pipeline."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        assert director.rag_pipeline is mock_rag_pipeline

    def test_director_works_without_rag_pipeline(self) -> None:
        """NarrativeDirector works without RAG pipeline (backward compat)."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        assert director.rag_pipeline is None

    def test_director_accepts_prompt_builder(
        self,
        mock_prompt_builder: MagicMock,
    ) -> None:
        """NarrativeDirector accepts custom prompt builder."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(prompt_builder=mock_prompt_builder)

        # The director should use the provided builder
        # We test this indirectly through the builder being called
        assert director._prompt_builder is mock_prompt_builder

    def test_director_creates_default_prompt_builder(self) -> None:
        """NarrativeDirector creates default prompt builder if not provided."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        director = NarrativeDirector()

        assert isinstance(director._prompt_builder, DialecticalPromptBuilder)


# =============================================================================
# TEST RAG QUERY BEHAVIOR
# =============================================================================


@pytest.mark.unit
class TestDirectorRAGQueryBehavior:
    """Tests for RAG query behavior during tick processing."""

    def test_on_tick_queries_rag_when_events_occur(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """on_tick queries RAG when new events occur."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Strike broke out in factory district"],
            }
        )

        director.on_tick(previous_state, new_state)

        # RAG should be queried
        mock_rag_pipeline.query.assert_called_once()

    def test_on_tick_skips_rag_when_no_events(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """on_tick skips RAG query when no new events."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        # Both states have same event log (no new events)
        previous_state = initial_state.model_copy(update={"event_log": ["Old event"]})
        new_state = initial_state.model_copy(update={"tick": 1, "event_log": ["Old event"]})

        director.on_tick(previous_state, new_state)

        # RAG should NOT be queried (optimization)
        mock_rag_pipeline.query.assert_not_called()

    def test_rag_query_uses_semantic_bridge(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """RAG query uses semantic bridge to translate events to theory queries.

        Sprint 3.4: The semantic bridge translates simulation keywords like
        SURPLUS_EXTRACTION into theoretical queries like 'surplus value'.
        Unrecognized events use the fallback 'dialectical materialism' query.
        """
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["SURPLUS_EXTRACTION from Worker to Owner"],
            }
        )

        director.on_tick(previous_state, new_state)

        # Check the query text contains semantic translation, not raw event
        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should contain theoretical query, not raw event text
        assert "surplus value" in query_text.lower()
        # Should NOT contain raw event format
        assert "Tick" not in query_text

    def test_rag_query_uses_top_k_3(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """RAG query uses top_k=3 for result limit."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Revolution brewing"],
            }
        )

        director.on_tick(previous_state, new_state)

        # Check top_k parameter
        call_args = mock_rag_pipeline.query.call_args
        # Could be positional or keyword
        top_k = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("top_k")

        assert top_k == 3

    def test_rag_results_passed_to_prompt_builder(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
        mock_prompt_builder: MagicMock,
    ) -> None:
        """RAG results are passed to prompt builder."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(
            rag_pipeline=mock_rag_pipeline,
            prompt_builder=mock_prompt_builder,
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Workers unite"],
            }
        )

        director.on_tick(previous_state, new_state)

        # Prompt builder should be called with RAG context
        mock_prompt_builder.build_context_block.assert_called_once()
        call_args = mock_prompt_builder.build_context_block.call_args

        # Extract rag_context argument
        rag_context = call_args[1].get("rag_context") if call_args[1] else call_args[0][1]

        # Should contain extracted document content
        assert len(rag_context) == 3
        assert "revolutionary spirit" in rag_context[0].lower()


# =============================================================================
# TEST ERROR HANDLING
# =============================================================================


@pytest.mark.unit
class TestDirectorRAGErrorHandling:
    """Tests for RAG error handling (ADR003: AI failures don't break game)."""

    def test_rag_error_does_not_halt_observer(
        self,
        initial_state: WorldState,
    ) -> None:
        """RAG error does not halt observer processing."""
        from babylon.ai.director import NarrativeDirector

        mock_rag = MagicMock()
        mock_rag.query.side_effect = Exception("RAG service unavailable")

        director = NarrativeDirector(rag_pipeline=mock_rag)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Critical event occurred"],
            }
        )

        # Should not raise - errors are caught internally
        director.on_tick(previous_state, new_state)

    def test_rag_error_is_logged(
        self,
        initial_state: WorldState,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """RAG errors are logged for visibility."""
        from babylon.ai.director import NarrativeDirector

        mock_rag = MagicMock()
        mock_rag.query.side_effect = Exception("Connection timeout")

        director = NarrativeDirector(rag_pipeline=mock_rag)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Event with failing RAG"],
            }
        )

        with caplog.at_level(logging.WARNING):
            director.on_tick(previous_state, new_state)

        # Should log the error
        assert "rag" in caplog.text.lower() or "retrieval" in caplog.text.lower()

    def test_rag_timeout_handled_gracefully(
        self,
        initial_state: WorldState,
    ) -> None:
        """RAG timeout is handled gracefully (returns empty context)."""
        from babylon.ai.director import NarrativeDirector

        mock_rag = MagicMock()
        mock_rag.query.side_effect = TimeoutError("Query timed out")

        director = NarrativeDirector(rag_pipeline=mock_rag)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Timeout test event"],
            }
        )

        # Should not raise
        director.on_tick(previous_state, new_state)


# =============================================================================
# TEST FULL CONTEXT ASSEMBLY
# =============================================================================


@pytest.mark.unit
class TestDirectorFullContext:
    """Tests for full context assembly."""

    def test_full_context_assembled_correctly(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Full context is assembled with all components."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        # Use real prompt builder to test full assembly
        real_builder = DialecticalPromptBuilder()
        director = NarrativeDirector(
            rag_pipeline=mock_rag_pipeline,
            prompt_builder=real_builder,
        )

        previous_state = initial_state
        events = ["Strike in factory", "Troops deployed"]
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": events,
            }
        )

        # We'll capture what the builder produces by checking it works
        director.on_tick(previous_state, new_state)

        # If we got here without error, context assembly worked
        # RAG was queried with correct params
        mock_rag_pipeline.query.assert_called_once()

    def test_context_includes_rag_when_available(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Context includes RAG results when available."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(
            rag_pipeline=mock_rag_pipeline,
            use_llm=True,  # Enable debug logging
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Test event"],
            }
        )

        with caplog.at_level(logging.DEBUG):
            director.on_tick(previous_state, new_state)

        # With use_llm=True and DEBUG level, context should be logged
        # This tests that context assembly includes RAG data
        # (We verify this by checking RAG was called)
        assert mock_rag_pipeline.query.called

    def test_context_works_without_rag(
        self,
        initial_state: WorldState,
    ) -> None:
        """Context assembly works without RAG pipeline."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()  # No RAG

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Event without RAG"],
            }
        )

        # Should not raise - works without RAG
        director.on_tick(previous_state, new_state)
