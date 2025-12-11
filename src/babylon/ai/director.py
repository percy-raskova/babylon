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

from babylon.ai.llm_provider import LLMProvider
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

    # Semantic Bridge: Maps simulation event keywords to theoretical query strings.
    # The RAG database contains Marxist theoretical texts, not simulation logs.
    # This mapping allows effective retrieval of relevant theory.
    SEMANTIC_MAP: dict[str, str] = {
        "SURPLUS_EXTRACTION": "marxist theory of surplus value extraction and exploitation",
        "IMPERIAL_SUBSIDY": "role of repression in maintaining imperialist client states",
        "ECONOMIC_CRISIS": "tendency of the rate of profit to fall and capitalist crisis",
        "SOLIDARITY_AWAKENING": "development of class consciousness and proletariat solidarity",
        "MASS_AWAKENING": "leninist theory of revolutionary situation and mass strike",
        "BRIBERY": "labor aristocracy and imperialist super-wages",
        "WAGES": "labor aristocracy and imperialist super-wages",
    }

    # Fallback query when no event keywords are recognized
    FALLBACK_QUERY: str = "dialectical materialism class struggle"

    def __init__(
        self,
        use_llm: bool = False,
        rag_pipeline: RagPipeline | None = None,
        prompt_builder: DialecticalPromptBuilder | None = None,
        llm: LLMProvider | None = None,
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
        """
        self._use_llm = use_llm
        self._rag = rag_pipeline
        self._prompt_builder = prompt_builder or DialecticalPromptBuilder()
        self._llm = llm
        self._narrative_log: list[str] = []
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

    @property
    def narrative_log(self) -> list[str]:
        """Return generated narrative entries.

        Returns a copy of the internal list to prevent external modification.

        Returns:
            List of generated narrative strings.
        """
        return list(self._narrative_log)

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

        # Log context
        logger.info("[%s] Context prepared for tick %d", self.name, new_state.tick)
        if self._use_llm:
            logger.debug("[%s] Full context:\n%s", self.name, context_block)

        # Generate narrative for SURPLUS_EXTRACTION events (Sprint 3.3)
        if self._use_llm and self._llm is not None and new_events:
            surplus_events = [
                e for e in new_events if "SURPLUS_EXTRACTION" in e or "surplus_extraction" in e
            ]
            if surplus_events:
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

    def _translate_events_to_query(self, events: list[str]) -> str:
        """Translate simulation events to theoretical query using Semantic Bridge.

        Scans each event for keywords from SEMANTIC_MAP and collects the
        corresponding theoretical query strings. Deduplicates using a set
        since multiple events may contain the same keyword.

        Args:
            events: List of simulation event strings.

        Returns:
            Theoretical query string for RAG, or FALLBACK_QUERY if no
            keywords were recognized.
        """
        semantic_queries: set[str] = set()
        for event in events:
            for keyword, theoretical_query in self.SEMANTIC_MAP.items():
                if keyword in event:
                    semantic_queries.add(theoretical_query)

        if not semantic_queries:
            return self.FALLBACK_QUERY
        return " ".join(semantic_queries)

    def _retrieve_context(self, events: list[str]) -> list[str]:
        """Query RAG pipeline for relevant historical/theoretical context.

        Uses the Semantic Bridge to translate event keywords into theoretical
        query strings. The RAG database contains Marxist theoretical texts,
        not simulation logs, so direct event queries return poor results.

        Implements ADR003: errors are caught and logged, not propagated.

        Args:
            events: New events to translate and query.

        Returns:
            List of retrieved document content strings.
            Empty list if RAG is not configured or query fails.
        """
        if not self._rag:
            return []

        query_text = self._translate_events_to_query(events)

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
