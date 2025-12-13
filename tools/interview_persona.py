#!/usr/bin/env python
"""Interview Persona - Tuning Fork for Persephone Raskova's voice.

This script tests the AI persona under pressure by running 3 "Hard Case"
scenarios through the real LLM. Use this to verify that Persephone's
narrative voice is consistent and compelling.

The Hard Cases:
    1. The Squeeze: Massive debt servicing extraction from Global South
    2. The Crash: Economic crisis with austerity decision
    3. The Reaction: Phase transition from liquid to solid (organization)

Outputs:
    - Console: Real-time output with logging
    - logs/interview_persona.log: Full debug log
    - results/interview_persona.md: Markdown transcript

Usage:
    poetry run python tools/interview_persona.py
    mise run interview-persona

Environment:
    Requires DEEPSEEK_API_KEY in .env or environment
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

from dotenv import load_dotenv

from babylon.ai.director import NarrativeDirector
from babylon.ai.llm_provider import DeepSeekClient
from babylon.ai.persona_loader import PersonaLoadError, load_default_persona
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models.events import CrisisEvent, ExtractionEvent, PhaseTransitionEvent
from babylon.models.world_state import WorldState

# Output paths
LOGS_DIR = Path(__file__).parent.parent / "logs"
RESULTS_DIR = Path(__file__).parent.parent / "results"
LOG_FILE = LOGS_DIR / "interview_persona.log"
MARKDOWN_FILE = RESULTS_DIR / "interview_persona.md"


def setup_logging() -> None:
    """Configure logging for console and file output."""
    LOGS_DIR.mkdir(exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "[%(levelname)s] %(name)s: %(message)s",
    )
    console_handler.setFormatter(console_format)

    # File handler (DEBUG level)
    file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


class MarkdownTranscript:
    """Builds a markdown transcript of the interview."""

    def __init__(self, persona_name: str, persona_role: str) -> None:
        """Initialize the transcript with persona info."""
        self.lines: list[str] = []
        self.persona_name = persona_name
        self.persona_role = persona_role
        self._write_header()

    def _write_header(self) -> None:
        """Write the markdown header."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lines.extend(
            [
                "# Interview Persona: Hard Cases",
                "",
                f"**Persona:** {self.persona_name}",
                f"**Role:** {self.persona_role}",
                f"**Generated:** {timestamp}",
                "",
                "---",
                "",
                "## Overview",
                "",
                "Testing the AI persona's narrative voice under pressure through 3 Hard Case scenarios.",
                "",
            ]
        )

    def add_tick(
        self,
        tick_num: int,
        title: str,
        event_type: str,
        event_details: dict[str, str | float],
        narrative: str | None,
    ) -> None:
        """Add a tick section to the transcript."""
        self.lines.extend(
            [
                f"## Tick {tick_num}: {title}",
                "",
                f"**Event Type:** `{event_type}`",
                "",
                "### Event Parameters",
                "",
            ]
        )

        for key, value in event_details.items():
            self.lines.append(f"- **{key}:** {value}")

        self.lines.extend(["", "### Narrative Response", ""])

        if narrative:
            self.lines.extend(
                [
                    "> *Persephone speaks:*",
                    "",
                    narrative,
                    "",
                ]
            )
        else:
            self.lines.append("*(No narrative generated)*\n")

        self.lines.append("---\n")

    def add_summary(self, narratives_count: int, events_count: int) -> None:
        """Add summary section."""
        self.lines.extend(
            [
                "## Summary",
                "",
                f"- **Narratives generated:** {narratives_count}",
                f"- **Events accumulated:** {events_count}",
                "",
            ]
        )

    def save(self, path: Path) -> None:
        """Save transcript to file."""
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.lines), encoding="utf-8")


def create_hard_case_events() -> tuple[ExtractionEvent, CrisisEvent, PhaseTransitionEvent]:
    """Create the 3 Hard Case events for testing persona voice.

    Returns:
        Tuple of (extraction_event, crisis_event, phase_event).
    """
    extraction_event = ExtractionEvent(
        tick=1,
        source_id="GlobalSouth",
        target_id="Empire_Core",
        amount=1000.0,
        mechanism="Debt Servicing",
    )

    crisis_event = CrisisEvent(
        tick=2,
        pool_ratio=0.12,
        aggregate_tension=0.95,
        decision="AUSTERITY",
        wage_delta=-0.25,
    )

    phase_event = PhaseTransitionEvent(
        tick=3,
        previous_state="liquid",
        new_state="solid",
        percolation_ratio=0.88,
        num_components=1,
        largest_component_size=150,
        cadre_density=0.75,
    )

    return extraction_event, crisis_event, phase_event


def create_minimal_state() -> WorldState:
    """Create minimal WorldState for testing.

    Returns:
        WorldState with 2 entities (worker + owner) and no events.
    """
    worker = create_proletariat()
    owner = create_bourgeoisie()

    return WorldState(
        tick=0,
        entities={worker.id: worker, owner.id: owner},
        relationships=[],
        event_log=[],
        events=[],
    )


def print_separator(title: str, out: TextIO = sys.stdout) -> None:
    """Print a visual separator with title."""
    width = 70
    print("\n" + "=" * width, file=out)
    print(title.center(width), file=out)
    print("=" * width + "\n", file=out)


def main() -> int:
    """Run the Interview Persona tuning fork.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Setup logging (console + file)
    setup_logging()
    logger = logging.getLogger(__name__)

    # Load environment variables
    load_dotenv()

    logger.info("Starting Interview Persona tuning fork")
    logger.debug("Log file: %s", LOG_FILE)
    logger.debug("Markdown output: %s", MARKDOWN_FILE)

    # Load persona
    try:
        persona = load_default_persona()
        print(f"Loaded persona: {persona.name}")
        print(f"Role: {persona.role}")
        print(f"Addresses user as: {persona.voice.address_user_as}")
        logger.info("Loaded persona: %s", persona.name)
    except PersonaLoadError as e:
        logger.exception("Failed to load persona")
        print(f"ERROR: Failed to load persona: {e}", file=sys.stderr)
        return 1

    # Initialize markdown transcript
    transcript = MarkdownTranscript(persona.name, persona.role)

    # Initialize real LLM
    try:
        llm = DeepSeekClient()
        print(f"Initialized LLM: {llm.name}")
        logger.info("Initialized LLM: %s", llm.name)
    except Exception as e:
        logger.exception("Failed to initialize LLM")
        print(f"ERROR: Failed to initialize LLM: {e}", file=sys.stderr)
        print("Ensure DEEPSEEK_API_KEY is set in .env or environment", file=sys.stderr)
        return 1

    # Initialize NarrativeDirector with persona
    director = NarrativeDirector(
        use_llm=True,
        llm=llm,
        persona=persona,
    )
    print(f"Initialized: {director.name}")
    logger.info("Initialized NarrativeDirector")

    # Create events and initial state
    extraction_event, crisis_event, phase_event = create_hard_case_events()
    initial_state = create_minimal_state()

    print_separator("INTERVIEW PERSONA: HARD CASES")
    print("Testing Persephone Raskova's narrative voice under pressure...")
    print("Each tick presents a dramatic scenario that demands her analysis.\n")

    # =========================================================================
    # TICK 1: THE SQUEEZE
    # =========================================================================
    print_separator("TICK 1: THE SQUEEZE")
    print("Event: ExtractionEvent")
    print(f"  Source: {extraction_event.source_id}")
    print(f"  Target: {extraction_event.target_id}")
    print(f"  Amount: {extraction_event.amount}")
    print(f"  Mechanism: {extraction_event.mechanism}")
    print()

    logger.info("Processing Tick 1: The Squeeze")

    state_1 = WorldState(
        tick=1,
        entities=initial_state.entities,
        territories=initial_state.territories,
        relationships=initial_state.relationships,
        event_log=[],
        events=[extraction_event],
    )

    director.on_tick(initial_state, state_1)

    narrative_1 = director.narrative_log[-1] if director.narrative_log else None
    if narrative_1:
        print("PERSEPHONE SPEAKS:")
        print("-" * 40)
        print(narrative_1)
        logger.debug(
            "Narrative 1: %s", narrative_1[:200] + "..." if len(narrative_1) > 200 else narrative_1
        )
    else:
        print("(No narrative generated)")

    transcript.add_tick(
        tick_num=1,
        title="The Squeeze",
        event_type="ExtractionEvent",
        event_details={
            "Source": extraction_event.source_id,
            "Target": extraction_event.target_id,
            "Amount": extraction_event.amount,
            "Mechanism": extraction_event.mechanism,
        },
        narrative=narrative_1,
    )

    # =========================================================================
    # TICK 2: THE CRASH
    # =========================================================================
    print_separator("TICK 2: THE CRASH")
    print("Event: CrisisEvent")
    print(f"  Pool Ratio: {crisis_event.pool_ratio}")
    print(f"  Aggregate Tension: {crisis_event.aggregate_tension}")
    print(f"  Decision: {crisis_event.decision}")
    print(f"  Wage Delta: {crisis_event.wage_delta}")
    print()

    logger.info("Processing Tick 2: The Crash")

    state_2 = WorldState(
        tick=2,
        entities=initial_state.entities,
        territories=initial_state.territories,
        relationships=initial_state.relationships,
        event_log=[],
        events=list(state_1.events) + [crisis_event],
    )

    director.on_tick(state_1, state_2)

    narrative_2 = director.narrative_log[-1] if len(director.narrative_log) > 1 else None
    if narrative_2:
        print("PERSEPHONE SPEAKS:")
        print("-" * 40)
        print(narrative_2)
        logger.debug(
            "Narrative 2: %s", narrative_2[:200] + "..." if len(narrative_2) > 200 else narrative_2
        )
    else:
        print("(No narrative generated)")

    transcript.add_tick(
        tick_num=2,
        title="The Crash",
        event_type="CrisisEvent",
        event_details={
            "Pool Ratio": crisis_event.pool_ratio,
            "Aggregate Tension": crisis_event.aggregate_tension,
            "Decision": crisis_event.decision,
            "Wage Delta": crisis_event.wage_delta,
        },
        narrative=narrative_2,
    )

    # =========================================================================
    # TICK 3: THE REACTION
    # =========================================================================
    print_separator("TICK 3: THE REACTION")
    print("Event: PhaseTransitionEvent")
    print(f"  Previous State: {phase_event.previous_state}")
    print(f"  New State: {phase_event.new_state}")
    print(f"  Percolation Ratio: {phase_event.percolation_ratio}")
    print(f"  Cadre Density: {phase_event.cadre_density}")
    print(f"  Largest Component: {phase_event.largest_component_size}")
    print()

    logger.info("Processing Tick 3: The Reaction")

    state_3 = WorldState(
        tick=3,
        entities=initial_state.entities,
        territories=initial_state.territories,
        relationships=initial_state.relationships,
        event_log=[],
        events=list(state_2.events) + [phase_event],
    )

    director.on_tick(state_2, state_3)

    narrative_3 = director.narrative_log[-1] if len(director.narrative_log) > 2 else None
    if narrative_3:
        print("PERSEPHONE SPEAKS:")
        print("-" * 40)
        print(narrative_3)
        logger.debug(
            "Narrative 3: %s", narrative_3[:200] + "..." if len(narrative_3) > 200 else narrative_3
        )
    else:
        print("(No narrative generated)")

    transcript.add_tick(
        tick_num=3,
        title="The Reaction",
        event_type="PhaseTransitionEvent",
        event_details={
            "Previous State": phase_event.previous_state,
            "New State": phase_event.new_state,
            "Percolation Ratio": phase_event.percolation_ratio,
            "Cadre Density": phase_event.cadre_density,
            "Largest Component": phase_event.largest_component_size,
        },
        narrative=narrative_3,
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_separator("INTERVIEW COMPLETE")
    print(f"Total narratives generated: {len(director.narrative_log)}")
    print(f"Events accumulated: {len(state_3.events)}")

    transcript.add_summary(len(director.narrative_log), len(state_3.events))

    # Save outputs
    transcript.save(MARKDOWN_FILE)
    print("\nOutputs saved:")
    print(f"  Log file: {LOG_FILE}")
    print(f"  Markdown: {MARKDOWN_FILE}")

    logger.info(
        "Interview complete. Narratives: %d, Events: %d",
        len(director.narrative_log),
        len(state_3.events),
    )
    logger.info("Saved markdown transcript to %s", MARKDOWN_FILE)

    return 0


if __name__ == "__main__":
    sys.exit(main())
