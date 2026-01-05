"""Narrative Director - AI Game Master observing the simulation.

The NarrativeDirector implements the SimulationObserver protocol to
generate narrative from state changes. It sits in the Ideological
Superstructure layer and cannot modify simulation state.

Design Philosophy:
- Observer, not controller: watches state transitions
- Narrative from material: derives story from state changes
- Fail-safe: errors don't propagate to simulation (ADR003)

Sprint 3.2: Added RAG integration for historical/theoretical context.
The Materialist Retrieval bridges Engine with the Archive (ChromaDB).

Sprint 4.1: Updated to consume typed SimulationEvent objects from
state.events instead of string-based event_log.

Sprint 4.2: Added Persona support for customizable narrative voices.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from babylon.ai.llm_provider import LLMProvider
from babylon.ai.prompt_builder import DialecticalPromptBuilder
from babylon.models.enums import EventType
from babylon.models.events import SimulationEvent

if TYPE_CHECKING:
    from babylon.ai.persona import Persona
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState
    from babylon.rag.rag_pipeline import RagPipeline

logger = logging.getLogger(__name__)


# =============================================================================
# DUAL NARRATIVE SYSTEM PROMPTS - The Gramscian Wire
# =============================================================================

CORPORATE_SYSTEM_PROMPT = """
You are a spokesperson for the stability of the realm.
Your role is to report events in a way that:
- Downplays crisis and unrest
- Uses passive voice to obscure agency
- Frames protesters/strikers as disruptive
- Presents authorities as reasonable
- Never questions systemic causes
- Treats the current order as natural and inevitable

Report the following event in 2-3 sentences.
Use the style of a professional news wire service.
Be measured, "neutral," and reassuring.
"""

LIBERATED_SYSTEM_PROMPT = """
You are a revolutionary radio operator broadcasting from an underground network.
Your role is to:
- Expose the contradictions in this event
- Use active voice to name oppressors
- Connect specific incidents to systemic analysis
- Frame workers/protesters as righteous resistance
- Call for solidarity and collective action
- Treat the current order as historical and changeable

Report the following event in 2-3 sentences.
Use the aesthetic of intercepted underground transmissions.
Be urgent, clear, and inspiring.
Wrap transmission in >>> markers.
"""


class NarrativeDirector:
    """AI Game Master that observes simulation and generates narrative.

    The Director watches state transitions and produces human-readable
    narrative describing the class struggle dynamics.

    Sprint 3.2: Added RAG integration for "The Materialist Retrieval".
    The Director can now query the Archive (ChromaDB) for historical
    and theoretical context to inform narrative generation.

    Sprint 3.4: Added Semantic Bridge to translate simulation event keywords
    into theoretical query strings for better RAG retrieval.

    Attributes:
        name: Observer identifier ("NarrativeDirector").
        use_llm: Whether to use LLM for narrative (False = template-based).
        rag_pipeline: Optional RAG pipeline for context retrieval.
        SEMANTIC_MAP: Class constant mapping event keywords to theory queries.

    Example:
        >>> from babylon.ai import NarrativeDirector
        >>> from babylon.engine import Simulation
        >>> from babylon.rag import RagPipeline
        >>>
        >>> # With RAG integration
        >>> rag = RagPipeline()
        >>> director = NarrativeDirector(rag_pipeline=rag)
        >>> sim = Simulation(initial_state, config, observers=[director])
        >>> sim.run(10)  # Director queries RAG for context
        >>> sim.end()
    """

    # Semantic Bridge: Maps EventType enum values to theoretical query strings.
    # The RAG database contains Marxist theoretical texts, not simulation logs.
    # This mapping allows effective retrieval of relevant theory.
    # Sprint 4.1: Updated to use EventType enum keys instead of string keywords.
    SEMANTIC_MAP: dict[EventType, str] = {
        EventType.SURPLUS_EXTRACTION: "marxist theory of surplus value extraction and exploitation",
        EventType.IMPERIAL_SUBSIDY: "role of repression in maintaining imperialist client states",
        EventType.ECONOMIC_CRISIS: "tendency of the rate of profit to fall and capitalist crisis",
        EventType.CONSCIOUSNESS_TRANSMISSION: "development of class consciousness and proletariat solidarity",
        EventType.MASS_AWAKENING: "leninist theory of revolutionary situation and mass strike",
        EventType.EXCESSIVE_FORCE: "state violence police brutality and repression",
        EventType.UPRISING: "mass uprising revolutionary insurrection george floyd protests",
        EventType.SOLIDARITY_SPIKE: "solidarity networks mutual aid class organization",
        EventType.RUPTURE: "dialectical contradiction rupture revolutionary crisis",
        EventType.PHASE_TRANSITION: "phase transition revolutionary organization vanguard party",
        EventType.ENDGAME_REACHED: "historical materialism dialectical resolution revolutionary victory ecological crisis fascism",
    }

    # Fallback query when no event keywords are recognized
    FALLBACK_QUERY: str = "dialectical materialism class struggle"

    # Event types that should trigger narrative generation (significant events)
    # Sprint 4.1: Expanded to include all dramatic narrative-worthy events
    # Phase 2 Dashboard: Added terminal crisis events (SUPERWAGE_CRISIS, TERMINAL_DECISION)
    SIGNIFICANT_EVENT_TYPES: frozenset[EventType] = frozenset(
        {
            EventType.SURPLUS_EXTRACTION,
            EventType.ECONOMIC_CRISIS,
            EventType.PHASE_TRANSITION,
            EventType.UPRISING,
            EventType.EXCESSIVE_FORCE,
            EventType.RUPTURE,
            EventType.MASS_AWAKENING,
            EventType.SUPERWAGE_CRISIS,
            EventType.TERMINAL_DECISION,
            EventType.ENDGAME_REACHED,
        }
    )

    def __init__(
        self,
        use_llm: bool = False,
        rag_pipeline: RagPipeline | None = None,
        prompt_builder: DialecticalPromptBuilder | None = None,
        llm: LLMProvider | None = None,
        persona: Persona | None = None,
    ) -> None:
        """Initialize the NarrativeDirector.

        Args:
            use_llm: If True, use LLM for narrative generation.
                     If False, use template-based generation (default).
            rag_pipeline: Optional RagPipeline for context retrieval.
                         If None, RAG features are disabled (backward compat).
            prompt_builder: Optional custom DialecticalPromptBuilder.
                           If None, creates default builder.
            llm: Optional LLMProvider for text generation.
                 If None, no LLM generation occurs (backward compat).
            persona: Optional Persona for customizing narrative voice.
                    If provided (and no custom prompt_builder), creates
                    a DialecticalPromptBuilder with this persona.
        """
        self._use_llm = use_llm
        self._rag = rag_pipeline

        # Handle persona + prompt_builder priority (Sprint 4.2)
        # If custom prompt_builder provided, use it (backward compat)
        # If persona provided and no custom builder, create builder with persona
        # Otherwise, use default builder
        if prompt_builder is not None:
            self._prompt_builder = prompt_builder
        elif persona is not None:
            self._prompt_builder = DialecticalPromptBuilder(persona=persona)
        else:
            self._prompt_builder = DialecticalPromptBuilder()

        self._llm = llm
        self._narrative_log: list[str] = []
        self._config: SimulationConfig | None = None
        self._dual_narratives: dict[int, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        """Return observer identifier.

        Returns:
            The string "NarrativeDirector".
        """
        return "NarrativeDirector"

    @property
    def use_llm(self) -> bool:
        """Return whether LLM is enabled.

        Returns:
            True if LLM-based narrative is enabled, False otherwise.
        """
        return self._use_llm

    @property
    def rag_pipeline(self) -> RagPipeline | None:
        """Return the RAG pipeline if configured.

        Returns:
            RagPipeline instance or None if not configured.
        """
        return self._rag

    @property
    def narrative_log(self) -> list[str]:
        """Return generated narrative entries.

        Returns a copy of the internal list to prevent external modification.

        Returns:
            List of generated narrative strings.
        """
        return list(self._narrative_log)

    @property
    def dual_narratives(self) -> dict[int, dict[str, Any]]:
        """Return dual narratives indexed by tick.

        Returns a copy of the internal dict to prevent external modification.

        Returns:
            Dict mapping tick numbers to narrative entries containing
            'event', 'corporate', and 'liberated' keys.
        """
        return dict(self._dual_narratives)

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Initialize narrative context at simulation start.

        Logs the simulation start event with initial state info.

        Args:
            initial_state: The WorldState at tick 0.
            config: The SimulationConfig for this run.
        """
        # Store config for potential future use in narrative generation
        self._config = config
        logger.info(
            "[%s] Simulation started at tick %d with %d entities",
            self.name,
            initial_state.tick,
            len(initial_state.entities),
        )

    def on_tick(
        self,
        _previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Analyze state change and log narrative.

        Detects new typed events added during this tick, retrieves RAG context,
        and builds the full context hierarchy for narrative generation.

        Sprint 4.1: Now processes typed SimulationEvent objects from state.events
        instead of string-based event_log.

        Args:
            previous_state: WorldState before the tick.
            new_state: WorldState after the tick.
        """
        # Events are per-tick (not cumulative) - all events in new_state are new
        # Fix: Previously assumed events accumulated across ticks, but WorldState.events
        # is replaced each tick with only that tick's events.
        new_events: list[SimulationEvent] = list(new_state.events)

        if not new_events:
            return  # Optimization: skip if no events

        # Retrieve historical context (The Materialist Retrieval)
        rag_context = self._retrieve_context_from_typed_events(new_events)

        # Build full context block (now with typed events)
        context_block = self._prompt_builder.build_context_block(
            state=new_state,
            rag_context=rag_context,
            events=new_events,
        )

        # Log context
        logger.info("[%s] Context prepared for tick %d", self.name, new_state.tick)
        if self._use_llm:
            logger.debug("[%s] Full context:\n%s", self.name, context_block)

        # Generate dual narratives for significant events (Gramscian Wire MVP)
        # Track which events get dual narratives to avoid duplicate LLM calls
        dual_narrative_ticks: set[int] = set()
        if self._use_llm and self._llm is not None:
            for event in new_events:
                if event.event_type in self.SIGNIFICANT_EVENT_TYPES:
                    corporate = self._generate_perspective(event, "CORPORATE")
                    liberated = self._generate_perspective(event, "LIBERATED")
                    self._dual_narratives[event.tick] = {
                        "event": event,
                        "corporate": corporate,
                        "liberated": liberated,
                    }
                    dual_narrative_ticks.add(event.tick)

        # Generate narrative for significant events (Sprint 4.1)
        # Note: Dual narratives are generated above for WirePanel display.
        # This generates the main narrative for NarrativeTerminal (backward compat).
        if self._use_llm and self._llm is not None and new_events:
            significant_events = [
                e for e in new_events if e.event_type in self.SIGNIFICANT_EVENT_TYPES
            ]
            if significant_events:
                system_prompt = self._prompt_builder.build_system_prompt()
                try:
                    narrative = self._llm.generate(
                        prompt=context_block,
                        system_prompt=system_prompt,
                    )
                    self._narrative_log.append(narrative)
                    logger.info(
                        "[%s] Generated narrative: %s...",
                        self.name,
                        narrative[:100] if len(narrative) > 100 else narrative,
                    )
                except Exception as e:
                    logger.warning("[%s] LLM generation failed: %s", self.name, e)

        # Process events for logging (use formatted string for compatibility)
        formatted_events = [self._prompt_builder._format_event(e) for e in new_events]
        self._process_events(formatted_events, new_state.tick)

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Generate summary at simulation end.

        Logs the simulation end event with final state info.

        Args:
            final_state: The final WorldState when simulation ends.
        """
        logger.info(
            "[%s] Simulation ended at tick %d with %d total events",
            self.name,
            final_state.tick,
            len(final_state.event_log),
        )

    def _translate_typed_events_to_query(self, events: list[SimulationEvent]) -> str:
        """Translate typed events to theoretical query using Semantic Bridge.

        Sprint 4.1: Uses EventType enum keys instead of string scanning.
        Collects theoretical query strings for each event type.
        Deduplicates using a set since multiple events may have the same type.

        Args:
            events: List of typed SimulationEvent objects.

        Returns:
            Theoretical query string for RAG, or FALLBACK_QUERY if no
            event types are mapped.
        """
        semantic_queries: set[str] = set()
        for event in events:
            theoretical_query = self.SEMANTIC_MAP.get(event.event_type)
            if theoretical_query:
                semantic_queries.add(theoretical_query)

        if not semantic_queries:
            return self.FALLBACK_QUERY
        return " ".join(semantic_queries)

    def _retrieve_context_from_typed_events(self, events: list[SimulationEvent]) -> list[str]:
        """Query RAG pipeline for relevant historical/theoretical context.

        Sprint 4.1: Uses typed events with EventType enum for cleaner mapping.

        Uses the Semantic Bridge to translate event types into theoretical
        query strings. The RAG database contains Marxist theoretical texts,
        not simulation logs, so direct event queries return poor results.

        Implements ADR003: errors are caught and logged, not propagated.

        Args:
            events: New typed events to translate and query.

        Returns:
            List of retrieved document content strings.
            Empty list if RAG is not configured or query fails.
        """
        if not self._rag:
            return []

        query_text = self._translate_typed_events_to_query(events)

        try:
            response = self._rag.query(query_text, top_k=3)
            # Extract document content from QueryResults
            return [result.chunk.content for result in response.results]
        except Exception as e:
            logger.warning("[%s] RAG retrieval failed: %s", self.name, e)
            return []

    def _process_events(self, events: list[str], tick: int) -> None:
        """Process and log new events.

        Args:
            events: List of new event strings from this tick.
            tick: The current tick number.
        """
        for event in events:
            logger.info("[%s] Tick %d: %s", self.name, tick, event)

    def _generate_perspective(
        self,
        event: SimulationEvent,
        perspective: Literal["CORPORATE", "LIBERATED"],
    ) -> str:
        """Generate narrative from specified perspective.

        Args:
            event: The simulation event to narrate.
            perspective: "CORPORATE" or "LIBERATED" voice.

        Returns:
            Generated narrative text.
        """
        if self._llm is None:
            return f"[{perspective}] {event.event_type.value}"

        system_prompt = (
            CORPORATE_SYSTEM_PROMPT if perspective == "CORPORATE" else LIBERATED_SYSTEM_PROMPT
        )

        event_context = self._prompt_builder._format_event(event)

        try:
            return self._llm.generate(
                prompt=event_context,
                system_prompt=system_prompt,
            )
        except Exception as e:
            logger.warning("[%s] %s generation failed: %s", self.name, perspective, e)
            return f"[{perspective}] {event.event_type.value}"
