#!/usr/bin/env python
"""Interview Persona - Tuning Fork for Persephone Raskova's voice.

This script tests the AI persona under pressure by running 3 "Hard Case"
scenarios through the real LLM. Use this to verify that Persephone's
narrative voice is consistent and compelling.

The Hard Cases:
    1. The Squeeze: Massive debt servicing extraction from Global South
    2. The Crash: Economic crisis with austerity decision
    3. The Reaction: Phase transition from liquid to solid (organization)

Usage:
    poetry run python tools/interview_persona.py

Environment:
    Requires DEEPSEEK_API_KEY in .env or environment
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from babylon.ai.director import NarrativeDirector
from babylon.ai.llm_provider import DeepSeekClient
from babylon.ai.persona_loader import PersonaLoadError, load_default_persona
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models.events import CrisisEvent, ExtractionEvent, PhaseTransitionEvent
from babylon.models.world_state import WorldState


def create_hard_case_events() -> tuple[ExtractionEvent, CrisisEvent, PhaseTransitionEvent]:
    """Create the 3 Hard Case events for testing persona voice.

    Returns:
        Tuple of (extraction_event, crisis_event, phase_event).
    """
    # Tick 1: The Squeeze
    extraction_event = ExtractionEvent(
        tick=1,
        source_id="GlobalSouth",
        target_id="Empire_Core",
        amount=1000.0,
        mechanism="Debt Servicing",
    )

    # Tick 2: The Crash
    crisis_event = CrisisEvent(
        tick=2,
        pool_ratio=0.12,
        aggregate_tension=0.95,
        decision="AUSTERITY",
        wage_delta=-0.25,
    )

    # Tick 3: The Reaction
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


def print_separator(title: str) -> None:
    """Print a visual separator with title."""
    width = 70
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width + "\n")


def main() -> int:
    """Run the Interview Persona tuning fork.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Load environment variables
    load_dotenv()

    # Load persona
    try:
        persona = load_default_persona()
        print(f"Loaded persona: {persona.name}")
        print(f"Role: {persona.role}")
        print(f"Addresses user as: {persona.voice.address_user_as}")
    except PersonaLoadError as e:
        print(f"ERROR: Failed to load persona: {e}", file=sys.stderr)
        return 1

    # Initialize real LLM
    try:
        llm = DeepSeekClient()
        print(f"Initialized LLM: {llm.name}")
    except Exception as e:
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

    state_1 = WorldState(
        tick=1,
        entities=initial_state.entities,
        territories=initial_state.territories,
        relationships=initial_state.relationships,
        event_log=[],
        events=[extraction_event],  # First event only
    )

    director.on_tick(initial_state, state_1)

    if director.narrative_log:
        print("PERSEPHONE SPEAKS:")
        print("-" * 40)
        print(director.narrative_log[-1])
    else:
        print("(No narrative generated)")

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

    # Event Accumulation Pattern: include previous events
    state_2 = WorldState(
        tick=2,
        entities=initial_state.entities,
        territories=initial_state.territories,
        relationships=initial_state.relationships,
        event_log=[],
        events=list(state_1.events) + [crisis_event],  # Accumulate
    )

    director.on_tick(state_1, state_2)

    if len(director.narrative_log) > 1:
        print("PERSEPHONE SPEAKS:")
        print("-" * 40)
        print(director.narrative_log[-1])
    else:
        print("(No narrative generated)")

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

    # Event Accumulation Pattern: include all previous events
    state_3 = WorldState(
        tick=3,
        entities=initial_state.entities,
        territories=initial_state.territories,
        relationships=initial_state.relationships,
        event_log=[],
        events=list(state_2.events) + [phase_event],  # Accumulate
    )

    director.on_tick(state_2, state_3)

    if len(director.narrative_log) > 2:
        print("PERSEPHONE SPEAKS:")
        print("-" * 40)
        print(director.narrative_log[-1])
    else:
        print("(No narrative generated)")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_separator("INTERVIEW COMPLETE")
    print(f"Total narratives generated: {len(director.narrative_log)}")
    print(f"Events accumulated: {len(state_3.events)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
