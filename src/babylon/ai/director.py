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
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.ai.prompt_builder import DialecticalPromptBuilder

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState
    from babylon.rag.rag_pipeline import RagPipeline

logger = logging.getLogger(__name__)


class NarrativeDirector:
    """AI Game Master that observes simulation and generates narrative.

    The Director watches state transitions and produces human-readable
    narrative describing the class struggle dynamics.

    Sprint 3.2: Added RAG integration for "The Materialist Retrieval".
    The Director can now query the Archive (ChromaDB) for historical
    and theoretical context to inform narrative generation.

    Attributes:
        name: Observer identifier ("NarrativeDirector").
        use_llm: Whether to use LLM for narrative (False = template-based).
        rag_pipeline: Optional RAG pipeline for context retrieval.

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

    def __init__(
        self,
        use_llm: bool = False,
        rag_pipeline: RagPipeline | None = None,
        prompt_builder: DialecticalPromptBuilder | None = None,
    ) -> None:
        """Initialize the NarrativeDirector.

        Args:
            use_llm: If True, use LLM for narrative generation.
                     If False, use template-based generation (default).
            rag_pipeline: Optional RagPipeline for context retrieval.
                         If None, RAG features are disabled (backward compat).
            prompt_builder: Optional custom DialecticalPromptBuilder.
                           If None, creates default builder.
        """
        self._use_llm = use_llm
        self._rag = rag_pipeline
        self._prompt_builder = prompt_builder or DialecticalPromptBuilder()
        self._config: SimulationConfig | None = None

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
        previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Analyze state change and log narrative.

        Detects new events added during this tick, retrieves RAG context,
        and builds the full context hierarchy for narrative generation.

        Args:
            previous_state: WorldState before the tick.
            new_state: WorldState after the tick.
        """
        # Detect new events added this tick
        num_new_events = len(new_state.event_log) - len(previous_state.event_log)

        if num_new_events == 0:
            return  # Optimization: skip if no events

        new_events = new_state.event_log[-num_new_events:]

        # Retrieve historical context (The Materialist Retrieval)
        rag_context = self._retrieve_context(new_events)

        # Build full context block
        context_block = self._prompt_builder.build_context_block(
            state=new_state,
            rag_context=rag_context,
            events=new_events,
        )

        # Log context (future: pass to LLM in Sprint 3.3)
        logger.info("[%s] Context prepared for tick %d", self.name, new_state.tick)
        if self._use_llm:
            logger.debug("[%s] Full context:\n%s", self.name, context_block)

        # Process events for logging
        self._process_events(new_events, new_state.tick)

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

    def _retrieve_context(self, events: list[str]) -> list[str]:
        """Query RAG pipeline for relevant historical/theoretical context.

        Uses event text as semantic query to retrieve relevant documents
        from the Archive (ChromaDB). Implements ADR003: errors are caught
        and logged, not propagated to simulation.

        Args:
            events: New events to use as query text.

        Returns:
            List of retrieved document content strings.
            Empty list if RAG is not configured or query fails.
        """
        if not self._rag:
            return []

        query_text = " ".join(events)
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
