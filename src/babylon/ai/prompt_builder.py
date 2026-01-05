"""Builder for Dialectical Prompts and Context Hierarchy.

Implements the context structure from docs/AI_COMMS.md:
1. Material Conditions (from WorldState)
2. Historical/Theoretical Context (from RAG)
3. Recent Events (from tick delta)

The builder creates structured prompts that ground AI responses
in material conditions and class analysis, following Marxist
dialectical materialism principles.

Sprint 4.1: Updated to consume typed SimulationEvent objects
instead of string-based event_log.

Sprint 4.2: Added Persona support for customizable narrative voices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.models.events import (
    CrisisEvent,
    EndgameEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    PhaseTransitionEvent,
    RuptureEvent,
    SimulationEvent,
    SolidaritySpikeEvent,
    SparkEvent,
    SubsidyEvent,
    TransmissionEvent,
    UprisingEvent,
)

if TYPE_CHECKING:
    from babylon.ai.persona import Persona
    from babylon.models.world_state import WorldState


class DialecticalPromptBuilder:
    """Builds prompts following Marxist dialectical materialism.

    The builder creates structured prompts that ground AI responses
    in material conditions and class analysis. It follows the context
    hierarchy defined in AI_COMMS.md.

    Sprint 4.2: Added persona support for customizable narrative voices.
    When a persona is provided, build_system_prompt() returns the
    persona's rendered prompt instead of the default.

    Attributes:
        persona: Optional Persona to use for system prompt generation.

    Example:
        >>> builder = DialecticalPromptBuilder()
        >>> system_prompt = builder.build_system_prompt()
        >>> context = builder.build_context_block(state, rag_docs, events)
        >>>
        >>> # With persona (Sprint 4.2)
        >>> from babylon.ai.persona_loader import load_default_persona
        >>> percy = load_default_persona()
        >>> builder = DialecticalPromptBuilder(persona=percy)
        >>> system_prompt = builder.build_system_prompt()
    """

    def __init__(self, persona: Persona | None = None) -> None:
        """Initialize the DialecticalPromptBuilder.

        Args:
            persona: Optional Persona to use for system prompt generation.
                    If provided, build_system_prompt() will use the persona's
                    render_system_prompt() method. If None, uses the default
                    Marxist game master prompt.
        """
        self._persona = persona

    @property
    def persona(self) -> Persona | None:
        """Return the persona if configured.

        Returns:
            The Persona instance or None if not configured.
        """
        return self._persona

    def build_system_prompt(self) -> str:
        """Return the immutable core identity of the Director.

        If a persona is configured (Sprint 4.2), returns the persona's
        rendered system prompt. Otherwise, returns the default Marxist
        game master prompt.

        Returns:
            System prompt establishing the AI's identity and role.
        """
        if self._persona is not None:
            return self._persona.render_system_prompt()

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
        events: list[SimulationEvent],
    ) -> str:
        """Assemble the Context Hierarchy.

        Builds context following AI_COMMS.md hierarchy:
        1. Material Conditions (from WorldState)
        2. Historical/Theoretical Context (from RAG)
        3. Recent Events (from tick delta)

        Sprint 4.1: Now accepts typed SimulationEvent objects instead of strings.

        Args:
            state: Current WorldState for material conditions.
            rag_context: Retrieved documents from RAG pipeline.
            events: New typed events from this tick (SimulationEvent objects).

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

    def _build_events_section(self, events: list[SimulationEvent]) -> str:
        """Build recent events section from typed events.

        Sprint 4.1: Now accepts typed SimulationEvent objects and formats
        them with structured data for richer narrative generation.

        Args:
            events: List of typed SimulationEvent objects.

        Returns:
            Formatted events section.
        """
        header = "--- RECENT EVENTS ---"
        if not events:
            return f"{header}\nNo new events this tick."
        lines = [f"- {self._format_event(event)}" for event in events]
        return f"{header}\n" + "\n".join(lines)

    def _format_event(self, event: SimulationEvent) -> str:
        """Format a typed event into a human-readable string.

        Uses match/case to format each event type with its specific fields,
        providing rich context for narrative generation.

        Args:
            event: A SimulationEvent subclass instance.

        Returns:
            Human-readable event description with structured data.
        """
        match event:
            case ExtractionEvent():
                return (
                    f"SURPLUS_EXTRACTION: {event.amount:.2f} units extracted "
                    f"from {event.source_id} to {event.target_id} "
                    f"via {event.mechanism}"
                )
            case SubsidyEvent():
                return (
                    f"IMPERIAL_SUBSIDY: {event.amount:.2f} units from "
                    f"{event.source_id} to {event.target_id}, "
                    f"boosting repression by {event.repression_boost:.2f}"
                )
            case CrisisEvent():
                return (
                    f"ECONOMIC_CRISIS: Pool ratio at {event.pool_ratio:.2f} "
                    f"({event.pool_ratio * 100:.0f}%), tension {event.aggregate_tension:.2f}, "
                    f"decision: {event.decision}, wage delta: {event.wage_delta:+.2f}"
                )
            case TransmissionEvent():
                return (
                    f"CONSCIOUSNESS_TRANSMISSION: {event.source_id} -> {event.target_id}, "
                    f"delta {event.delta:+.3f}, solidarity strength {event.solidarity_strength:.2f}"
                )
            case MassAwakeningEvent():
                return (
                    f"MASS_AWAKENING: {event.target_id} consciousness surged "
                    f"from {event.old_consciousness:.2f} to {event.new_consciousness:.2f}, "
                    f"triggered by {event.triggering_source}"
                )
            case SparkEvent():
                return (
                    f"EXCESSIVE_FORCE: State violence at {event.node_id}, "
                    f"repression level {event.repression:.2f}, "
                    f"spark probability was {event.spark_probability:.2f}"
                )
            case UprisingEvent():
                return (
                    f"UPRISING: Mass insurrection at {event.node_id}, "
                    f"triggered by {event.trigger}, "
                    f"agitation {event.agitation:.2f}, repression {event.repression:.2f}"
                )
            case SolidaritySpikeEvent():
                return (
                    f"SOLIDARITY_SPIKE: {event.node_id} built solidarity infrastructure, "
                    f"gained {event.solidarity_gained:.2f} across {event.edges_affected} edges, "
                    f"triggered by {event.triggered_by}"
                )
            case RuptureEvent():
                return f"RUPTURE: Contradiction at {event.edge} reached breaking point"
            case PhaseTransitionEvent():
                return (
                    f"PHASE_TRANSITION: Network shifted from {event.previous_state} to "
                    f"{event.new_state} phase. Percolation ratio: {event.percolation_ratio:.2f}, "
                    f"Cadre density: {event.cadre_density:.2f}, "
                    f"Largest component: {event.largest_component_size} nodes"
                )
            case EndgameEvent():
                outcome_display = event.outcome.value.replace("_", " ").title()
                return (
                    f"ENDGAME_REACHED: Simulation ended with outcome {outcome_display} "
                    f"at tick {event.tick}"
                )
            case _:
                # Fallback for any unknown event types
                return f"{event.event_type.value.upper()}: Event at tick {event.tick}"

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
