"""Builder for Dialectical Prompts and Context Hierarchy.

Implements the context structure from docs/AI_COMMS.md:
1. Material Conditions (from WorldState)
2. Historical/Theoretical Context (from RAG)
3. Recent Events (from tick delta)

The builder creates structured prompts that ground AI responses
in material conditions and class analysis, following Marxist
dialectical materialism principles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.models.world_state import WorldState


class DialecticalPromptBuilder:
    """Builds prompts following Marxist dialectical materialism.

    The builder creates structured prompts that ground AI responses
    in material conditions and class analysis. It follows the context
    hierarchy defined in AI_COMMS.md.

    Example:
        >>> builder = DialecticalPromptBuilder()
        >>> system_prompt = builder.build_system_prompt()
        >>> context = builder.build_context_block(state, rag_docs, events)
    """

    def build_system_prompt(self) -> str:
        """Return the immutable core identity of the Director.

        The system prompt establishes the AI as a Marxist game master
        that analyzes through dialectical materialism.

        Returns:
            System prompt establishing Marxist game master role.
        """
        return """You are the game master for a Marxist political simulation. Your role is to:
- Analyze player actions through dialectical materialism
- Generate realistic consequences based on material conditions
- Maintain internal consistency with previous events
- Escalate or de-escalate contradictions appropriately
- Consider class interests and power relations in all outcomes"""

    def build_context_block(
        self,
        state: WorldState,
        rag_context: list[str],
        events: list[str],
    ) -> str:
        """Assemble the Context Hierarchy.

        Builds context following AI_COMMS.md hierarchy:
        1. Material Conditions (from WorldState)
        2. Historical/Theoretical Context (from RAG)
        3. Recent Events (from tick delta)

        Args:
            state: Current WorldState for material conditions.
            rag_context: Retrieved documents from RAG pipeline.
            events: New events from this tick.

        Returns:
            Formatted context block string.
        """
        sections = [
            self._build_material_section(state),
            self._build_rag_section(rag_context),
            self._build_events_section(events),
        ]
        return "\n\n".join(sections)

    def _build_material_section(self, state: WorldState) -> str:
        """Build material conditions section.

        Args:
            state: Current WorldState.

        Returns:
            Formatted material conditions section.
        """
        tension = self._calculate_tension(state)
        return (
            f"--- MATERIAL CONDITIONS (Tick {state.tick}) ---\n"
            f"Entities: {len(state.entities)}\n"
            f"Global Tension: {tension}"
        )

    def _build_rag_section(self, rag_context: list[str]) -> str:
        """Build historical/theoretical context section.

        Args:
            rag_context: Retrieved documents from RAG.

        Returns:
            Formatted historical context section.
        """
        header = "--- HISTORICAL & THEORETICAL CONTEXT ---"
        if not rag_context:
            return f"{header}\nNo relevant context retrieved."
        lines = [f"{i}. {doc}" for i, doc in enumerate(rag_context, 1)]
        return f"{header}\n" + "\n".join(lines)

    def _build_events_section(self, events: list[str]) -> str:
        """Build recent events section.

        Args:
            events: List of new event strings.

        Returns:
            Formatted events section.
        """
        header = "--- RECENT EVENTS ---"
        if not events:
            return f"{header}\nNo new events this tick."
        lines = [f"- {event}" for event in events]
        return f"{header}\n" + "\n".join(lines)

    def _calculate_tension(self, state: WorldState) -> str:
        """Calculate aggregate tension from relationships.

        Computes average tension across all relationships and
        categorizes it as High, Medium, Low, or None.

        Args:
            state: WorldState containing relationships.

        Returns:
            Tension level string: 'High', 'Medium', 'Low', or 'None'.
        """
        if not state.relationships:
            return "None"
        tensions = [r.tension for r in state.relationships]
        avg = sum(tensions) / len(tensions)
        if avg >= 0.7:
            return "High"
        if avg >= 0.4:
            return "Medium"
        return "Low"
