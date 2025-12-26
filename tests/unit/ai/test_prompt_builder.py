"""Tests for DialecticalPromptBuilder implementation.

TDD Red Phase: These tests define the contract for the DialecticalPromptBuilder
that constructs prompts following the AI_COMMS.md context hierarchy:
1. Material Conditions (from WorldState)
2. Historical/Theoretical Context (from RAG)
3. Recent Events (from tick delta)

The builder creates structured prompts grounded in Marxist dialectical materialism.

Sprint 4.1: Updated to use typed SimulationEvent objects from state.events
instead of string-based event_log.
"""

from __future__ import annotations

import pytest

from babylon.models import (
    EdgeType,
    Relationship,
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.events import ExtractionEvent, SparkEvent

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
def high_tension_edge() -> Relationship:
    """Create a high-tension exploitation relationship."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=5.0,
        tension=0.8,
    )


@pytest.fixture
def low_tension_edge() -> Relationship:
    """Create a low-tension exploitation relationship."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=1.0,
        tension=0.2,
    )


@pytest.fixture
def state_with_entities(worker: SocialClass, owner: SocialClass) -> WorldState:
    """Create state with entities but no relationships."""
    return WorldState(
        tick=5,
        entities={"C001": worker, "C002": owner},
        relationships=[],
    )


@pytest.fixture
def state_with_high_tension(
    worker: SocialClass,
    owner: SocialClass,
    high_tension_edge: Relationship,
) -> WorldState:
    """Create state with high-tension relationship."""
    return WorldState(
        tick=10,
        entities={"C001": worker, "C002": owner},
        relationships=[high_tension_edge],
    )


@pytest.fixture
def state_with_low_tension(
    worker: SocialClass,
    owner: SocialClass,
    low_tension_edge: Relationship,
) -> WorldState:
    """Create state with low-tension relationship."""
    return WorldState(
        tick=10,
        entities={"C001": worker, "C002": owner},
        relationships=[low_tension_edge],
    )


# =============================================================================
# TEST SYSTEM PROMPT
# =============================================================================


@pytest.mark.unit
class TestSystemPrompt:
    """Tests for system prompt generation."""

    def test_build_system_prompt_returns_marxist_identity(self) -> None:
        """System prompt establishes Marxist game master identity."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        prompt = builder.build_system_prompt()

        assert "game master" in prompt.lower()
        assert "marxist" in prompt.lower()

    def test_system_prompt_includes_dialectical_materialism(self) -> None:
        """System prompt references dialectical materialism analysis."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        prompt = builder.build_system_prompt()

        assert "dialectical materialism" in prompt.lower()

    def test_system_prompt_includes_class_analysis(self) -> None:
        """System prompt mentions class interests and power relations."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        prompt = builder.build_system_prompt()

        assert "class" in prompt.lower()
        # Should mention power relations or class interests
        assert "power" in prompt.lower() or "interest" in prompt.lower()


# =============================================================================
# TEST CONTEXT BLOCK
# =============================================================================


@pytest.mark.unit
class TestContextBlock:
    """Tests for context block generation.

    Sprint 4.1: Updated to use typed SimulationEvent objects.
    """

    def test_build_context_block_includes_material_conditions(
        self,
        state_with_entities: WorldState,
    ) -> None:
        """Context block includes material conditions section."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()

        # Create typed event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=5,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["Historical context"],
            events=[extraction_event],
        )

        # Should include material conditions header or content
        assert "material conditions" in context.lower()
        # Should include tick number
        assert "5" in context or "tick" in context.lower()

    def test_build_context_block_includes_rag_context(
        self,
        state_with_entities: WorldState,
    ) -> None:
        """Context block includes RAG-retrieved historical context."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        rag_docs = [
            "The revolution of 1917 established...",
            "Class consciousness emerges from...",
        ]

        # Create typed event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=5,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=rag_docs,
            events=[extraction_event],
        )

        # Should include the RAG documents
        assert "revolution of 1917" in context.lower()
        assert "class consciousness" in context.lower()

    def test_build_context_block_includes_recent_events(
        self,
        state_with_entities: WorldState,
    ) -> None:
        """Context block includes recent events section.

        Sprint 4.1: Updated to use typed events - check for event type info.
        """
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()

        # Create typed events (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=5,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        spark_event = SparkEvent(
            tick=5,
            node_id="C001",
            repression=0.8,
            spark_probability=0.4,
        )

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["Historical context"],
            events=[extraction_event, spark_event],
        )

        # Should include formatted event info
        assert "surplus_extraction" in context.lower() or "extraction" in context.lower()
        assert "force" in context.lower() or "repression" in context.lower()

    def test_context_block_handles_empty_rag_context(
        self,
        state_with_entities: WorldState,
    ) -> None:
        """Context block handles empty RAG results gracefully."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()

        # Create typed event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=5,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=[],
            events=[extraction_event],
        )

        # Should not crash, should have some indication of no context
        assert context is not None
        # Should still have material conditions and events
        assert "surplus_extraction" in context.lower() or "extraction" in context.lower()

    def test_context_block_handles_empty_events(
        self,
        state_with_entities: WorldState,
    ) -> None:
        """Context block handles empty events list gracefully."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["Historical context"],
            events=[],
        )

        # Should not crash
        assert context is not None
        # Should still have material conditions and RAG context
        assert "historical context" in context.lower()


# =============================================================================
# TEST TENSION CALCULATION
# =============================================================================


@pytest.mark.unit
class TestTensionCalculation:
    """Tests for tension aggregation from relationships."""

    def test_calculate_tension_aggregates_relationships(
        self,
        state_with_high_tension: WorldState,
    ) -> None:
        """Tension calculation aggregates from all relationships."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        # The state has tension=0.8, which should be "High"
        tension_level = builder._calculate_tension(state_with_high_tension)

        # Should return a tension level indication
        assert tension_level in ["High", "Medium", "Low", "None"]
        # With 0.8 tension, should be "High"
        assert tension_level == "High"

    def test_calculate_tension_handles_no_relationships(
        self,
        state_with_entities: WorldState,
    ) -> None:
        """Tension calculation handles state with no relationships."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        # state_with_entities has empty relationships
        tension_level = builder._calculate_tension(state_with_entities)

        # Should handle gracefully - return None or some default
        assert tension_level == "None"

    def test_calculate_tension_medium_level(
        self,
        worker: SocialClass,
        owner: SocialClass,
    ) -> None:
        """Tension calculation returns Medium for mid-range tension."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        # Create medium tension relationship (0.4-0.7 range)
        medium_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=3.0,
            tension=0.5,
        )
        state = WorldState(
            tick=5,
            entities={"C001": worker, "C002": owner},
            relationships=[medium_edge],
        )

        builder = DialecticalPromptBuilder()
        tension_level = builder._calculate_tension(state)

        assert tension_level == "Medium"

    def test_calculate_tension_low_level(
        self,
        state_with_low_tension: WorldState,
    ) -> None:
        """Tension calculation returns Low for low tension."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        # state_with_low_tension has tension=0.2
        tension_level = builder._calculate_tension(state_with_low_tension)

        assert tension_level == "Low"
