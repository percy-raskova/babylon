#!/usr/bin/env python3
"""Vertical Slice Demo - Phase 3 Complete System.

Demonstrates the full Babylon pipeline with VERBOSE logging:
1. Engine runs simulation (ImperialRentSystem extracts surplus)
2. EventBus emits SURPLUS_EXTRACTION events
3. NarrativeDirector observes state changes
4. RAG retrieves Marxist theoretical context
5. LLM generates narrative commentary

Usage:
    poetry run python tools/vertical_slice.py
    poetry run python tools/vertical_slice.py --quiet  # Less verbose

Set DEEPSEEK_API_KEY for real AI, or run in mock mode.

Outputs structured JSON logs to logs/vertical_slice_<timestamp>.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from babylon.ai.director import NarrativeDirector
from babylon.ai.llm_provider import DeepSeekClient, MockLLM
from babylon.ai.prompt_builder import DialecticalPromptBuilder
from babylon.config.chromadb_config import ChromaDBConfig
from babylon.config.llm_config import LLMConfig
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation import Simulation
from babylon.rag.rag_pipeline import RagConfig, RagPipeline

if TYPE_CHECKING:
    from babylon.ai.llm_provider import LLMProvider
    from babylon.models.world_state import WorldState

# Constants
MAX_TICKS: int = 10
TICK_DELAY_SECONDS: float = 1.5
LOG_DIR = Path(__file__).parent.parent / "logs"


class StructuredLogger:
    """Machine-readable JSON logger for troubleshooting."""

    def __init__(self, log_path: Path) -> None:
        """Initialize structured logger."""
        self.log_path = log_path
        self.session_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.events: list[dict[str, Any]] = []
        self.start_time = time.time()

        # Write header
        self._log_event(
            "session_start",
            {
                "session_id": self.session_id,
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "python_version": sys.version,
            },
        )

    def _log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log a structured event."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "elapsed_ms": int((time.time() - self.start_time) * 1000),
            "data": data,
        }
        self.events.append(event)
        self._write_log()

    def _write_log(self) -> None:
        """Write current events to log file."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w") as f:
            json.dump(
                {
                    "session_id": self.session_id,
                    "events": self.events,
                },
                f,
                indent=2,
                default=str,
            )

    def log_config(self, component: str, config: dict[str, Any]) -> None:
        """Log configuration for a component."""
        self._log_event("config", {"component": component, **config})

    def log_llm_setup(
        self,
        provider: str,
        model: str,
        api_base: str | None,
        is_mock: bool,
    ) -> None:
        """Log LLM setup."""
        self._log_event(
            "llm_setup",
            {
                "provider": provider,
                "model": model,
                "api_base": api_base,
                "is_mock": is_mock,
            },
        )

    def log_rag_setup(
        self,
        collection_name: str,
        chunk_count: int,
        embedding_model: str,
        embedding_dimension: int,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Log RAG setup with embedding configuration."""
        self._log_event(
            "rag_setup",
            {
                "collection_name": collection_name,
                "chunk_count": chunk_count,
                "embedding_model": embedding_model,
                "embedding_dimension": embedding_dimension,
                "success": success,
                "error": error,
            },
        )

    def log_rag_query(
        self,
        query_text: str,
        top_k: int,
        results_count: int,
        results: list[dict[str, Any]],
        query_embedding_dim: int | None,
        collection_embedding_dim: int | None,
        duration_ms: float,
        success: bool,
        error: str | None = None,
        error_traceback: str | None = None,
    ) -> None:
        """Log RAG query with full context for debugging dimension mismatches."""
        self._log_event(
            "rag_query",
            {
                "query_text": query_text[:500],  # Truncate for readability
                "query_text_length": len(query_text),
                "top_k": top_k,
                "results_count": results_count,
                "results": results,
                "query_embedding_dim": query_embedding_dim,
                "collection_embedding_dim": collection_embedding_dim,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
                "error_traceback": error_traceback,
            },
        )

    def log_embedding_request(
        self,
        content_preview: str,
        content_length: int,
        expected_dimension: int,
        actual_dimension: int | None,
        duration_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Log embedding API request."""
        self._log_event(
            "embedding_request",
            {
                "content_preview": content_preview[:200],
                "content_length": content_length,
                "expected_dimension": expected_dimension,
                "actual_dimension": actual_dimension,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
            },
        )

    def log_llm_request(
        self,
        prompt_preview: str,
        system_prompt_preview: str,
        response_preview: str | None,
        duration_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Log LLM API request."""
        self._log_event(
            "llm_request",
            {
                "prompt_preview": prompt_preview[:500],
                "system_prompt_preview": system_prompt_preview[:300],
                "response_preview": response_preview[:500] if response_preview else None,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
            },
        )

    def log_tick(
        self,
        tick: int,
        # 4-entity wealth tracking
        p_w_wealth: float,  # C001 - Periphery Worker
        p_c_wealth: float,  # C002 - Comprador
        c_b_wealth: float,  # C003 - Core Bourgeoisie
        c_w_wealth: float,  # C004 - Labor Aristocracy
        # Global economy metrics
        imperial_rent_pool: float,
        super_wage_rate: float,
        # Dialectical metrics
        tension: float,
        value_flow: float,
        events: list[str],
    ) -> None:
        """Log simulation tick state for Imperial Circuit."""
        self._log_event(
            "simulation_tick",
            {
                "tick": tick,
                "entities": {
                    "C001_periphery_worker": p_w_wealth,
                    "C002_comprador": p_c_wealth,
                    "C003_core_bourgeoisie": c_b_wealth,
                    "C004_labor_aristocracy": c_w_wealth,
                },
                "economy": {
                    "imperial_rent_pool": imperial_rent_pool,
                    "super_wage_rate": super_wage_rate,
                },
                "tension": tension,
                "value_flow": value_flow,
                "events": events,
            },
        )

    def log_error(self, component: str, error: str, traceback_str: str | None = None) -> None:
        """Log an error."""
        self._log_event(
            "error",
            {
                "component": component,
                "error": error,
                "traceback": traceback_str,
            },
        )

    def log_session_end(self, narratives_generated: int, success: bool) -> None:
        """Log session end."""
        self._log_event(
            "session_end",
            {
                "total_duration_ms": int((time.time() - self.start_time) * 1000),
                "narratives_generated": narratives_generated,
                "success": success,
                "total_events": len(self.events),
            },
        )


class VerboseNarrativeDirector(NarrativeDirector):
    """NarrativeDirector with verbose logging of all LLM interactions."""

    def __init__(
        self,
        console: Console,
        logger: StructuredLogger,
        use_llm: bool = False,
        rag_pipeline: RagPipeline | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        """Initialize with console for verbose output."""
        super().__init__(
            use_llm=use_llm,
            rag_pipeline=rag_pipeline,
            llm=llm,
        )
        self._console = console
        self._logger = logger
        self._prompt_builder = DialecticalPromptBuilder()

    def on_tick(self, previous_state: WorldState, new_state: WorldState) -> None:
        """Override on_tick to show verbose LLM interactions."""
        # Detect new events
        num_prev = len(previous_state.event_log)
        num_new = len(new_state.event_log)
        new_events = new_state.event_log[num_prev:num_new] if num_new > num_prev else []

        if not new_events:
            return

        # Check for SURPLUS_EXTRACTION events
        surplus_events = [
            e for e in new_events if "SURPLUS_EXTRACTION" in e or "surplus_extraction" in e
        ]

        if not surplus_events or not self._use_llm or self._llm is None:
            return

        # === SHOW RAG QUERY ===
        self._console.print("\n[bold magenta]═══ RAG CONTEXT RETRIEVAL ═══[/bold magenta]")

        rag_context: list[str] = []
        if self._rag is not None:
            query_text = " ".join(new_events)
            self._console.print(f"[dim]Query:[/dim] {query_text[:100]}...")

            start_time = time.time()
            try:
                response = self._rag.query(query_text, top_k=3)
                duration_ms = (time.time() - start_time) * 1000

                results_data = []
                for i, result in enumerate(response.results):
                    doc_preview = result.chunk.content[:300]
                    metadata = result.chunk.metadata or {}
                    title = metadata.get("title", "Unknown")
                    author = metadata.get("author", "Unknown")

                    results_data.append(
                        {
                            "index": i,
                            "title": title,
                            "author": author,
                            "content_preview": doc_preview,
                            "distance": getattr(result, "distance", None),
                        }
                    )

                    self._console.print(
                        Panel(
                            f"[dim]{doc_preview}...[/dim]",
                            title=f"[cyan]RAG Result {i + 1}: {title} ({author})[/cyan]",
                            border_style="cyan",
                        )
                    )
                    rag_context.append(result.chunk.content)

                # Log successful RAG query
                self._logger.log_rag_query(
                    query_text=query_text,
                    top_k=3,
                    results_count=len(response.results),
                    results=results_data,
                    query_embedding_dim=LLMConfig.get_model_dimensions(),
                    collection_embedding_dim=None,  # Would need to query ChromaDB metadata
                    duration_ms=duration_ms,
                    success=True,
                )

                if not response.results:
                    self._console.print("[yellow]No RAG results found[/yellow]")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_tb = traceback.format_exc()
                self._console.print(f"[red]RAG query failed: {e}[/red]")

                # Log failed RAG query with full traceback
                self._logger.log_rag_query(
                    query_text=query_text,
                    top_k=3,
                    results_count=0,
                    results=[],
                    query_embedding_dim=LLMConfig.get_model_dimensions(),
                    collection_embedding_dim=None,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                    error_traceback=error_tb,
                )
        else:
            self._console.print("[yellow]RAG not available[/yellow]")

        # === BUILD PROMPT ===
        self._console.print("\n[bold magenta]═══ PROMPT CONSTRUCTION ═══[/bold magenta]")

        system_prompt = self._prompt_builder.build_system_prompt()
        context_block = self._prompt_builder.build_context_block(
            state=new_state,
            rag_context=rag_context,
            events=new_events,
        )

        self._console.print(
            Panel(
                system_prompt,
                title="[yellow]SYSTEM PROMPT[/yellow]",
                border_style="yellow",
            )
        )

        self._console.print(
            Panel(
                context_block,
                title="[yellow]USER PROMPT (Context Block)[/yellow]",
                border_style="yellow",
            )
        )

        # === CALL LLM ===
        self._console.print("\n[bold magenta]═══ LLM GENERATION ═══[/bold magenta]")
        self._console.print(f"[dim]Calling {self._llm.name}...[/dim]")

        start_time = time.time()
        try:
            narrative = self._llm.generate(
                prompt=context_block,
                system_prompt=system_prompt,
            )
            duration_ms = (time.time() - start_time) * 1000

            self._narrative_log.append(narrative)

            # Log successful LLM request
            self._logger.log_llm_request(
                prompt_preview=context_block,
                system_prompt_preview=system_prompt,
                response_preview=narrative,
                duration_ms=duration_ms,
                success=True,
            )

            self._console.print(f"[dim]Response time: {duration_ms / 1000:.2f}s[/dim]")
            self._console.print(
                Panel(
                    Text(narrative, style="bold green"),
                    title="[bold green]LLM RESPONSE[/bold green]",
                    border_style="green",
                )
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._console.print(f"[bold red]LLM Generation Failed: {e}[/bold red]")

            # Log failed LLM request
            self._logger.log_llm_request(
                prompt_preview=context_block,
                system_prompt_preview=system_prompt,
                response_preview=None,
                duration_ms=duration_ms,
                success=False,
                error=str(e),
            )


def setup_logging(verbose: bool, logger: StructuredLogger) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )

    # Enable specific loggers for verbose mode
    if verbose:
        logging.getLogger("babylon.ai").setLevel(logging.DEBUG)
        logging.getLogger("babylon.rag").setLevel(logging.DEBUG)
        logging.getLogger("babylon.engine").setLevel(logging.DEBUG)

    logger.log_config("logging", {"level": level, "verbose": verbose})


def setup_llm(console: Console, logger: StructuredLogger) -> LLMProvider:
    """Set up LLM provider, falling back to mock if no API key."""
    if LLMConfig.is_configured():
        console.print("[green]✓[/green] DeepSeek API key found")
        console.print(f"[dim]  API Base: {LLMConfig.API_BASE}[/dim]")
        console.print(f"[dim]  Model: {LLMConfig.CHAT_MODEL}[/dim]")

        logger.log_llm_setup(
            provider="deepseek",
            model=LLMConfig.CHAT_MODEL,
            api_base=LLMConfig.API_BASE,
            is_mock=False,
        )
        return DeepSeekClient()

    console.print("[yellow]⚠[/yellow] No API key - RUNNING IN MOCK MODE")
    logger.log_llm_setup(
        provider="mock",
        model="MockLLM",
        api_base=None,
        is_mock=True,
    )
    return MockLLM(
        default_response="[Mock] The extraction of surplus value continues unabated. "
        "The worker's wealth diminishes as the owner accumulates capital. "
        "This is the fundamental contradiction of capitalism - the bourgeoisie "
        "enriches itself at the expense of the proletariat."
    )


def setup_rag(console: Console, logger: StructuredLogger) -> RagPipeline | None:
    """Set up RAG pipeline, returning None if unavailable."""
    try:
        # Use the same collection as the ingest script (marxist_theory)
        config = RagConfig(collection_name=ChromaDBConfig.THEORY_COLLECTION)
        console.print(f"[dim]  Collection: {ChromaDBConfig.THEORY_COLLECTION}[/dim]")

        # Get embedding configuration for logging
        embedding_model = LLMConfig.EMBEDDING_MODEL
        embedding_dim = LLMConfig.get_model_dimensions()
        console.print(f"[dim]  Embedding Model: {embedding_model}[/dim]")
        console.print(f"[dim]  Embedding Dimension: {embedding_dim}[/dim]")

        rag = RagPipeline(config=config)
        stats = rag.get_stats()
        chunk_count = stats.get("total_chunks", 0)

        if chunk_count > 0:
            console.print(f"[green]✓[/green] RAG loaded ({chunk_count} chunks)")
        else:
            console.print(f"[yellow]⚠[/yellow] RAG loaded but EMPTY ({chunk_count} chunks)")
            console.print(
                "[dim]  Run: poetry run python tools/ingest_corpus.py --import-from /media/user/marxists.org/www.marxists.org/[/dim]"
            )

        logger.log_rag_setup(
            collection_name=ChromaDBConfig.THEORY_COLLECTION,
            chunk_count=chunk_count,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dim,
            success=True,
        )

        return rag

    except Exception as e:
        error_tb = traceback.format_exc()
        console.print(f"[red]✗[/red] RAG unavailable: {e}")

        logger.log_rag_setup(
            collection_name=ChromaDBConfig.THEORY_COLLECTION,
            chunk_count=0,
            embedding_model=LLMConfig.EMBEDDING_MODEL,
            embedding_dimension=LLMConfig.get_model_dimensions(),
            success=False,
            error=f"{e}\n{error_tb}",
        )
        return None


def display_banner(console: Console) -> None:
    """Display the demo banner."""
    console.print(
        Panel.fit(
            "[bold red]BABYLON[/bold red] - [italic]The Fall of America[/italic]\n"
            "[dim]Phase 3: Vertical Slice Demo (VERBOSE MODE)[/dim]",
            border_style="red",
        )
    )


def display_tick_state(
    console: Console,
    tick: int,
    # 4 entities
    p_w_wealth: float,  # C001
    p_c_wealth: float,  # C002
    c_b_wealth: float,  # C003
    c_w_wealth: float,  # C004
    # Survival probabilities (for P_w only - others are protected)
    p_w_p_acquiescence: float,
    p_w_p_revolution: float,
    # Global economy
    imperial_rent_pool: float,
    super_wage_rate: float,
    # Dialectical
    tension: float,
    value_flow: float,
) -> None:
    """Display the state at a given tick (Imperial Circuit)."""
    console.rule(f"[bold cyan]══════════ TICK {tick} ══════════[/bold cyan]")

    # Entity Table (4 rows)
    table = Table(show_header=True, header_style="bold", title="Imperial Circuit State")
    table.add_column("Entity", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Wealth", justify="right")
    table.add_column("P(S|A)", justify="right")
    table.add_column("P(S|R)", justify="right")

    table.add_row(
        "Periphery Worker",
        "C001",
        f"{p_w_wealth:.4f}",
        f"{p_w_p_acquiescence:.4f}",
        f"{p_w_p_revolution:.4f}",
    )
    table.add_row("Comprador", "C002", f"{p_c_wealth:.4f}", "-", "-")
    table.add_row("Core Bourgeoisie", "C003", f"{c_b_wealth:.4f}", "-", "-")
    table.add_row("Labor Aristocracy", "C004", f"{c_w_wealth:.4f}", "-", "-")
    console.print(table)

    # Global Economy Panel (NEW)
    console.print(
        Panel(
            f"Imperial Rent Pool: [bold]{imperial_rent_pool:.2f}[/bold]\n"
            f"Super-Wage Rate: [bold]{super_wage_rate:.4f}[/bold]",
            title="[yellow]Global Economy[/yellow]",
            border_style="yellow",
        )
    )

    # Dialectical metrics
    console.print(
        f"\n[bold]Dialectical Metrics:[/bold]\n"
        f"  Tension (τ): {tension:.4f}\n"
        f"  Value Flow (Φ): {value_flow:.4f}"
    )


def display_events(console: Console, events: list[str]) -> None:
    """Display new events from this tick."""
    for event in events:
        if "SURPLUS_EXTRACTION" in event or "surplus_extraction" in event:
            console.print(f"\n[bold red]⚡ EVENT:[/bold red] {event}")


def display_final_summary(
    console: Console,
    # Initial values
    initial_p_w: float,
    initial_p_c: float,
    initial_c_b: float,
    initial_c_w: float,
    initial_rent_pool: float,
    # Final values
    final_p_w: float,
    final_p_c: float,
    final_c_b: float,
    final_c_w: float,
    final_rent_pool: float,
    narrative_count: int,
) -> None:
    """Display final summary for Imperial Circuit."""
    console.print("\n")
    console.rule("[bold red]═══════════ SIMULATION COMPLETE ═══════════[/bold red]")

    # Calculate changes
    p_w_delta = final_p_w - initial_p_w
    p_c_delta = final_p_c - initial_p_c
    c_b_delta = final_c_b - initial_c_b
    c_w_delta = final_c_w - initial_c_w
    pool_delta = final_rent_pool - initial_rent_pool

    table = Table(title="Imperial Circuit - Wealth Transfer", show_header=True, header_style="bold")
    table.add_column("Entity", style="cyan")
    table.add_column("Initial", justify="right")
    table.add_column("Final", justify="right")
    table.add_column("Change", justify="right")

    def style(delta: float) -> str:
        if delta < 0:
            return "red"
        if delta > 0:
            return "green"
        return "dim"

    table.add_row(
        "P_w (Periphery Worker)",
        f"{initial_p_w:.4f}",
        f"{final_p_w:.4f}",
        f"[{style(p_w_delta)}]{p_w_delta:+.4f}[/{style(p_w_delta)}]",
    )
    table.add_row(
        "P_c (Comprador)",
        f"{initial_p_c:.4f}",
        f"{final_p_c:.4f}",
        f"[{style(p_c_delta)}]{p_c_delta:+.4f}[/{style(p_c_delta)}]",
    )
    table.add_row(
        "C_b (Core Bourgeoisie)",
        f"{initial_c_b:.4f}",
        f"{final_c_b:.4f}",
        f"[{style(c_b_delta)}]{c_b_delta:+.4f}[/{style(c_b_delta)}]",
    )
    table.add_row(
        "C_w (Labor Aristocracy)",
        f"{initial_c_w:.4f}",
        f"{final_c_w:.4f}",
        f"[{style(c_w_delta)}]{c_w_delta:+.4f}[/{style(c_w_delta)}]",
    )
    table.add_row("-" * 22, "-" * 8, "-" * 8, "-" * 10)
    table.add_row(
        "Imperial Rent Pool",
        f"{initial_rent_pool:.2f}",
        f"{final_rent_pool:.2f}",
        f"[{style(pool_delta)}]{pool_delta:+.2f}[/{style(pool_delta)}]",
    )

    console.print(table)
    console.print(f"\n[bold]Total Narratives Generated:[/bold] {narrative_count}")

    # Analysis message
    if p_w_delta < 0 and c_w_delta > 0:
        console.print(
            f"\n[dim]Imperial Circuit confirmed: Periphery Worker lost {abs(p_w_delta):.4f} "
            f"while Labor Aristocracy gained {c_w_delta:.4f} via super-wages.[/dim]"
        )


def main() -> int:
    """Run the vertical slice demo."""
    parser = argparse.ArgumentParser(description="Babylon Vertical Slice Demo")
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Less verbose output",
    )
    parser.add_argument(
        "--ticks",
        "-t",
        type=int,
        default=MAX_TICKS,
        help=f"Number of ticks to run (default: {MAX_TICKS})",
    )
    args = parser.parse_args()

    # Create structured logger
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"vertical_slice_{timestamp}.json"
    logger = StructuredLogger(log_path)

    verbose = not args.quiet
    setup_logging(verbose, logger)

    console = Console()

    # === BANNER ===
    display_banner(console)
    console.print()
    console.print(f"[dim]Log file: {log_path}[/dim]")
    console.print()

    success = False
    try:
        # === SETUP LLM ===
        console.print("[bold]Setting up LLM...[/bold]")
        llm = setup_llm(console, logger)
        console.print()

        # === SETUP RAG ===
        console.print("[bold]Setting up RAG...[/bold]")
        rag = setup_rag(console, logger)
        console.print()

        # === SETUP SCENARIO ===
        console.print("[bold]Setting up Scenario...[/bold]")
        initial_state, config = create_imperial_circuit_scenario(
            periphery_wealth=0.1,
            core_wealth=0.9,
            extraction_efficiency=0.8,
        )
        console.print("[green]✓[/green] Imperial Circuit scenario loaded")
        console.print("[dim]  P_w (C001): Periphery Worker (wealth=0.1)[/dim]")
        console.print("[dim]  P_c (C002): Comprador (wealth=0.2)[/dim]")
        console.print("[dim]  C_b (C003): Core Bourgeoisie (wealth=0.9)[/dim]")
        console.print("[dim]  C_w (C004): Labor Aristocracy (wealth=0.18)[/dim]")
        console.print("[dim]  Extraction efficiency (α): 0.8[/dim]")
        console.print()

        logger.log_config(
            "scenario",
            {
                "type": "imperial_circuit",
                "periphery_wealth": 0.1,
                "core_wealth": 0.9,
                "extraction_efficiency": 0.8,
                "imperial_rent_pool": float(initial_state.economy.imperial_rent_pool),
            },
        )

        # Store initial values for summary (4 entities + rent pool)
        initial_p_w_wealth = float(initial_state.entities["C001"].wealth)
        initial_p_c_wealth = float(initial_state.entities["C002"].wealth)
        initial_c_b_wealth = float(initial_state.entities["C003"].wealth)
        initial_c_w_wealth = float(initial_state.entities["C004"].wealth)
        initial_rent_pool = float(initial_state.economy.imperial_rent_pool)

        # === SETUP DIRECTOR (VERBOSE VERSION) ===
        console.print("[bold]Setting up Narrative Director...[/bold]")
        director = VerboseNarrativeDirector(
            console=console,
            logger=logger,
            use_llm=True,
            rag_pipeline=rag,
            llm=llm,
        )
        console.print("[green]✓[/green] Verbose Narrative Director initialized")
        console.print()

        # === SETUP SIMULATION ===
        console.print("[bold]Setting up Simulation...[/bold]")
        sim = Simulation(
            initial_state=initial_state,
            config=config,
            observers=[director],
        )
        console.print("[green]✓[/green] Simulation ready")
        console.print()

        console.print(
            Panel(
                f"Running {args.ticks} ticks with {TICK_DELAY_SECONDS}s delay between each.\n"
                "Watch the LLM prompts, RAG context, and generated narratives!",
                title="[bold]Starting Simulation[/bold]",
                border_style="blue",
            )
        )
        time.sleep(2)

        # === SIMULATION LOOP ===
        for _ in range(args.ticks):
            # Track event count before step
            pre_step_event_count = len(sim.current_state.event_log)

            # Step simulation
            state = sim.step()

            # Get all 4 entities
            p_w = state.entities["C001"]  # Periphery Worker
            p_c = state.entities["C002"]  # Comprador
            c_b = state.entities["C003"]  # Core Bourgeoisie
            c_w = state.entities["C004"]  # Labor Aristocracy

            # Get economy metrics
            economy = state.economy

            # Get relationship (first EXPLOITATION edge)
            rel = state.relationships[0] if state.relationships else None

            # Get NEW events from this tick only (not historical accumulator)
            post_step_event_count = len(state.event_log)
            tick_events = state.event_log[pre_step_event_count:post_step_event_count]

            # Log tick state (updated signature)
            logger.log_tick(
                tick=state.tick,
                p_w_wealth=float(p_w.wealth),
                p_c_wealth=float(p_c.wealth),
                c_b_wealth=float(c_b.wealth),
                c_w_wealth=float(c_w.wealth),
                imperial_rent_pool=float(economy.imperial_rent_pool),
                super_wage_rate=float(economy.current_super_wage_rate),
                tension=float(rel.tension) if rel else 0.0,
                value_flow=float(rel.value_flow) if rel else 0.0,
                events=tick_events,
            )

            # === DISPLAY STATE ===
            display_tick_state(
                console=console,
                tick=state.tick,
                p_w_wealth=float(p_w.wealth),
                p_c_wealth=float(p_c.wealth),
                c_b_wealth=float(c_b.wealth),
                c_w_wealth=float(c_w.wealth),
                p_w_p_acquiescence=float(p_w.p_acquiescence),
                p_w_p_revolution=float(p_w.p_revolution),
                imperial_rent_pool=float(economy.imperial_rent_pool),
                super_wage_rate=float(economy.current_super_wage_rate),
                tension=float(rel.tension) if rel else 0.0,
                value_flow=float(rel.value_flow) if rel else 0.0,
            )

            # === EVENTS (show NEW events from this tick only) ===
            if tick_events:
                display_events(console, tick_events)
            else:
                console.print("[dim]No new events this tick[/dim]")

            # Director's on_tick already ran and displayed everything

            console.print()
            time.sleep(TICK_DELAY_SECONDS)

        # === END SIMULATION ===
        sim.end()

        # === FINAL SUMMARY ===
        final_state = sim.current_state
        final_p_w = final_state.entities["C001"]
        final_p_c = final_state.entities["C002"]
        final_c_b = final_state.entities["C003"]
        final_c_w = final_state.entities["C004"]
        final_rent_pool = float(final_state.economy.imperial_rent_pool)

        display_final_summary(
            console=console,
            initial_p_w=initial_p_w_wealth,
            initial_p_c=initial_p_c_wealth,
            initial_c_b=initial_c_b_wealth,
            initial_c_w=initial_c_w_wealth,
            initial_rent_pool=initial_rent_pool,
            final_p_w=float(final_p_w.wealth),
            final_p_c=float(final_p_c.wealth),
            final_c_b=float(final_c_b.wealth),
            final_c_w=float(final_c_w.wealth),
            final_rent_pool=final_rent_pool,
            narrative_count=len(director.narrative_log),
        )

        success = True

        # === CLEANUP ===
        if rag:
            rag.close()

    except Exception as e:
        error_tb = traceback.format_exc()
        console.print(f"[bold red]FATAL ERROR: {e}[/bold red]")
        console.print(f"[red]{error_tb}[/red]")
        logger.log_error("main", str(e), error_tb)

    finally:
        logger.log_session_end(
            narratives_generated=len(director.narrative_log) if "director" in dir() else 0,
            success=success,
        )
        console.print(f"\n[dim]Log written to: {log_path}[/dim]")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
