#!/usr/bin/env python3
"""Vertical Slice Demo - Phase 3 Complete System.

Demonstrates the full Babylon pipeline:
1. Engine runs simulation (ImperialRentSystem extracts surplus)
2. EventBus emits SURPLUS_EXTRACTION events
3. NarrativeDirector observes state changes
4. RAG retrieves Marxist theoretical context
5. LLM generates narrative commentary

Usage:
    poetry run python tools/vertical_slice.py

Set DEEPSEEK_API_KEY for real AI, or run in mock mode.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from babylon.ai.director import NarrativeDirector
from babylon.ai.llm_provider import DeepSeekClient, MockLLM
from babylon.config.llm_config import LLMConfig
from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation
from babylon.rag.rag_pipeline import RagPipeline

if TYPE_CHECKING:
    from babylon.ai.llm_provider import LLMProvider

# Configure logging to be quiet during demo (INFO level is too chatty)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Constants
MAX_TICKS: int = 10
TICK_DELAY_SECONDS: float = 1.0


def setup_llm(console: Console) -> LLMProvider:
    """Set up LLM provider, falling back to mock if no API key.

    Args:
        console: Rich console for output.

    Returns:
        LLMProvider instance (DeepSeekClient or MockLLM).
    """
    if LLMConfig.is_configured():
        console.print("[green]v[/green] DeepSeek API key found")
        return DeepSeekClient()

    console.print("[yellow]![/yellow] No API key - RUNNING IN MOCK MODE")
    return MockLLM(
        default_response="[Mock] The extraction of surplus value continues unabated. "
        "The worker's wealth diminishes as the owner accumulates capital."
    )


def setup_rag(console: Console) -> RagPipeline | None:
    """Set up RAG pipeline, returning None if unavailable.

    Args:
        console: Rich console for output.

    Returns:
        RagPipeline instance or None if setup fails.
    """
    try:
        rag = RagPipeline()
        stats = rag.get_stats()
        chunk_count = stats.get("total_chunks", 0)
        console.print(f"[green]v[/green] RAG loaded ({chunk_count} chunks)")
        return rag
    except Exception as e:
        console.print(f"[yellow]![/yellow] RAG unavailable: {e}")
        return None


def display_banner(console: Console) -> None:
    """Display the demo banner.

    Args:
        console: Rich console for output.
    """
    console.print(
        Panel.fit(
            "[bold red]BABYLON[/bold red] - [italic]The Fall of America[/italic]\n"
            "[dim]Phase 3: Vertical Slice Demo[/dim]",
            border_style="red",
        )
    )


def display_tick_state(
    console: Console,
    tick: int,
    worker_wealth: float,
    owner_wealth: float,
    worker_p_acquiescence: float,
    worker_p_revolution: float,
    tension: float,
    value_flow: float,
) -> None:
    """Display the state at a given tick.

    Args:
        console: Rich console for output.
        tick: Current tick number.
        worker_wealth: Worker's current wealth.
        owner_wealth: Owner's current wealth.
        worker_p_acquiescence: Worker's P(S|A).
        worker_p_revolution: Worker's P(S|R).
        tension: Current tension level.
        value_flow: Current value flow (Phi).
    """
    console.rule(f"[bold cyan]TICK {tick}[/bold cyan]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Entity", style="cyan")
    table.add_column("Wealth", justify="right")
    table.add_column("P(S|A)", justify="right")
    table.add_column("P(S|R)", justify="right")

    table.add_row(
        "Worker (Periphery)",
        f"{worker_wealth:.3f}",
        f"{worker_p_acquiescence:.3f}",
        f"{worker_p_revolution:.3f}",
    )
    table.add_row(
        "Owner (Core)",
        f"{owner_wealth:.3f}",
        "-",
        "-",
    )
    console.print(table)

    console.print(
        f"[dim]Tension:[/dim] {tension:.3f}  |  " f"[dim]Value Flow (Phi):[/dim] {value_flow:.3f}"
    )


def display_events(console: Console, events: list[str]) -> None:
    """Display new events from this tick.

    Args:
        console: Rich console for output.
        events: List of event strings.
    """
    for event in events:
        if "SURPLUS_EXTRACTION" in event or "surplus_extraction" in event:
            console.print(f"[bold red]! EVENT:[/bold red] {event}")


def display_narrative(console: Console, narrative: str) -> None:
    """Display AI-generated narrative.

    Args:
        console: Rich console for output.
        narrative: The narrative text.
    """
    console.print(
        Panel(
            Text(narrative, style="green italic"),
            title="[bold green]AI Narrative[/bold green]",
            border_style="green",
        )
    )


def display_final_summary(
    console: Console,
    worker_wealth: float,
    owner_wealth: float,
    narrative_count: int,
) -> None:
    """Display final summary after simulation ends.

    Args:
        console: Rich console for output.
        worker_wealth: Final worker wealth.
        owner_wealth: Final owner wealth.
        narrative_count: Total narratives generated.
    """
    console.rule("[bold red]SIMULATION COMPLETE[/bold red]")
    console.print("\n[bold]Final State:[/bold]")
    console.print(f"  Worker Wealth: {worker_wealth:.3f}")
    console.print(f"  Owner Wealth:  {owner_wealth:.3f}")
    console.print(f"  Total Narratives Generated: {narrative_count}")


def main() -> int:
    """Run the vertical slice demo.

    Returns:
        Exit code (0 for success).
    """
    console = Console()

    # === BANNER ===
    display_banner(console)

    # === SETUP LLM ===
    llm = setup_llm(console)

    # === SETUP RAG ===
    rag = setup_rag(console)

    # === SETUP SCENARIO ===
    initial_state, config = create_two_node_scenario(
        worker_wealth=0.5,
        owner_wealth=0.5,
        extraction_efficiency=0.8,
    )
    console.print("[green]v[/green] Two-node scenario loaded (Worker vs Owner)")

    # === SETUP DIRECTOR ===
    director = NarrativeDirector(
        use_llm=True,
        rag_pipeline=rag,
        llm=llm,
    )

    # === SETUP SIMULATION ===
    sim = Simulation(
        initial_state=initial_state,
        config=config,
        observers=[director],
    )
    console.print("[green]v[/green] Simulation initialized\n")

    console.print("[bold]Starting simulation...[/bold]\n")
    time.sleep(TICK_DELAY_SECONDS)

    # === SIMULATION LOOP ===
    prev_narrative_count = 0

    for _ in range(MAX_TICKS):
        # Step simulation
        state = sim.step()

        # Get entities
        worker = state.entities["C001"]
        owner = state.entities["C002"]

        # Get relationship (first one in list)
        rel = state.relationships[0] if state.relationships else None

        # === DISPLAY STATE ===
        display_tick_state(
            console=console,
            tick=state.tick,
            worker_wealth=float(worker.wealth),
            owner_wealth=float(owner.wealth),
            worker_p_acquiescence=float(worker.p_acquiescence),
            worker_p_revolution=float(worker.p_revolution),
            tension=float(rel.tension) if rel else 0.0,
            value_flow=float(rel.value_flow) if rel else 0.0,
        )

        # === EVENTS ===
        # Get events from the current tick by checking difference from previous tick count
        event_log_length = len(state.event_log)
        # Events for this tick would be after position (tick - 1) if tick > 0
        # Since we're iterating and tick increments each step, get most recent events
        if event_log_length > 0:
            # Get only new events (last N where N = events added this tick)
            # Approximate: show last 3 events or fewer
            recent_events = state.event_log[-3:] if event_log_length >= 3 else state.event_log
            display_events(console, recent_events)

        # === NARRATIVE ===
        current_narrative_count = len(director.narrative_log)
        if current_narrative_count > prev_narrative_count:
            new_narrative = director.narrative_log[-1]
            display_narrative(console, new_narrative)
            prev_narrative_count = current_narrative_count

        console.print()
        time.sleep(TICK_DELAY_SECONDS)

    # === END SIMULATION ===
    sim.end()

    # === FINAL SUMMARY ===
    final_state = sim.current_state
    worker_final = final_state.entities["C001"]
    owner_final = final_state.entities["C002"]

    display_final_summary(
        console=console,
        worker_wealth=float(worker_final.wealth),
        owner_wealth=float(owner_final.wealth),
        narrative_count=len(director.narrative_log),
    )

    # === CLEANUP ===
    if rag:
        rag.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
