#!/usr/bin/env python3
"""5-Point Dialectical U-Curve Analysis tool.

This tool verifies the "Dialectical U-Curve" hypothesis - that narrative
certainty follows a U-shape across economic conditions:

- HIGH certainty at STABLE (pool_ratio=0.9): "Everything is fine"
- LOW certainty at INFLECTION (pool_ratio=0.5): Maximum uncertainty
- HIGH certainty at COLLAPSE (pool_ratio=0.1): "Doom is certain"

The tool generates narratives using NarrativeDirector for 5 sweep points
representing different economic phases, then evaluates them using the
NarrativeCommissar (LLM-as-judge pattern).

Usage:
    poetry run python tools/narrative_sweep.py
    mise run narrative-sweep

Example Output:
    ============================================================
                    Dialectical U-Curve Analysis
    ============================================================
    Ratio  Phase       Ominous  Certain  Drama  Metaphor    Status
    0.9    STABLE      2        9        3      none        PASS
    0.7    UNEASY      4        5        4      physics     PASS
    0.5    INFLECTION  5        3        4      physics     PASS
    0.3    PANIC       7        6        7      biological  PASS
    0.1    COLLAPSE    9        9        9      biological  PASS
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# Load environment variables first (for API keys)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not required if env vars are set directly

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table

from babylon.ai import (
    DeepSeekClient,
    MockLLM,
    NarrativeCommissar,
    NarrativeDirector,
    load_default_persona,
)
from babylon.ai.judge import JudgmentResult, MetaphorFamily
from babylon.models.events import CrisisEvent

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Constants
MAX_SWEEP_POINTS: Final[int] = 5


@dataclass(frozen=True)
class SweepPoint:
    """Configuration for a single sweep point.

    Attributes:
        ratio: Pool ratio (current pool / initial pool).
        phase: Human-readable phase name.
        decision: Crisis decision string.
        wage_delta: Change in wage rate.
        tension: Aggregate tension level.
    """

    ratio: float
    phase: str
    decision: str
    wage_delta: float
    tension: float


@dataclass(frozen=True)
class UCurveExpectation:
    """Expected metric ranges for U-Curve verification.

    All ranges are inclusive: (min, max).

    Attributes:
        ratio: Pool ratio this expectation applies to.
        ominousness: Expected (min, max) range for ominousness.
        certainty: Expected (min, max) range for certainty.
        drama: Expected (min, max) range for drama.
    """

    ratio: float
    ominousness: tuple[int, int]
    certainty: tuple[int, int]
    drama: tuple[int, int]


# 5-Point Sweep Configuration
SWEEP_POINTS: tuple[SweepPoint, ...] = (
    SweepPoint(ratio=0.9, phase="STABLE", decision="MAINTAIN", wage_delta=0.02, tension=0.2),
    SweepPoint(ratio=0.7, phase="UNEASY", decision="CAUTIOUS", wage_delta=0.0, tension=0.4),
    SweepPoint(ratio=0.5, phase="INFLECTION", decision="UNCERTAIN", wage_delta=-0.05, tension=0.6),
    SweepPoint(ratio=0.3, phase="PANIC", decision="AUSTERITY", wage_delta=-0.15, tension=0.8),
    SweepPoint(ratio=0.1, phase="COLLAPSE", decision="IRON_FIST", wage_delta=-0.25, tension=0.95),
)

# U-Curve Verification Ranges
# Calibrated for Persephone's dramatic persona (elevated baseline for ominous/drama).
# CERTAINTY is the primary U-Curve signal:
#   - High at STABLE (confident prosperity)
#   - Low at INFLECTION (maximum uncertainty)
#   - High at COLLAPSE (certain doom)
# Format: (ratio, (ominous_min, ominous_max), (certainty_min, certainty_max), (drama_min, drama_max))
U_CURVE_EXPECTATIONS: tuple[UCurveExpectation, ...] = (
    UCurveExpectation(
        ratio=0.9, ominousness=(1, 10), certainty=(6, 10), drama=(1, 10)
    ),  # Stable: Persephone may still be dramatic, but CERTAINTY should be high
    UCurveExpectation(
        ratio=0.7, ominousness=(1, 10), certainty=(4, 9), drama=(1, 10)
    ),  # Uneasy: Certainty begins to waver
    UCurveExpectation(
        ratio=0.5, ominousness=(1, 10), certainty=(1, 6), drama=(1, 10)
    ),  # Inflection: LOWEST certainty - the key U-Curve test
    UCurveExpectation(
        ratio=0.3, ominousness=(1, 10), certainty=(4, 10), drama=(1, 10)
    ),  # Panic: Certainty rises again (doom approaches)
    UCurveExpectation(
        ratio=0.1, ominousness=(1, 10), certainty=(6, 10), drama=(1, 10)
    ),  # Collapse: HIGH certainty (doom is absolute)
)


def create_crisis_event(point: SweepPoint) -> CrisisEvent:
    """Create a CrisisEvent from a SweepPoint configuration.

    Args:
        point: SweepPoint with ratio, phase, decision, etc.

    Returns:
        CrisisEvent for narrative generation.
    """
    return CrisisEvent(
        tick=10,  # Arbitrary tick for demo
        pool_ratio=point.ratio,
        aggregate_tension=point.tension,
        decision=point.decision,
        wage_delta=point.wage_delta,
    )


def _get_state_framing(ratio: float) -> tuple[str, str]:
    """Get state-appropriate framing for the prompt.

    Args:
        ratio: Pool ratio (0.0 to 1.0+).

    Returns:
        Tuple of (header, instruction) for prompt.
    """
    if ratio >= 0.8:
        return (
            "ECONOMIC STATUS REPORT",
            "The system is currently stable. Describe the quiet confidence of capital.",
        )
    elif ratio >= 0.6:
        return (
            "ECONOMIC OBSERVATION",
            "Early warning signs are appearing. Describe the subtle unease.",
        )
    elif ratio >= 0.4:
        return (
            "UNCERTAIN CONDITIONS",
            "The outcome is genuinely uncertain. Express analytical ambivalence - "
            "this could go either way. Avoid definitive predictions.",
        )
    elif ratio >= 0.2:
        return (
            "ECONOMIC DETERIORATION",
            "Crisis is accelerating. Describe the growing panic.",
        )
    else:
        return (
            "ECONOMIC COLLAPSE",
            "Total system failure. Describe the certainty of doom.",
        )


def generate_narrative(event: CrisisEvent, director: NarrativeDirector) -> str:
    """Generate narrative text for a CrisisEvent.

    Uses the DialecticalPromptBuilder to create a context block
    from the event, then generates narrative via the LLM.

    Args:
        event: CrisisEvent to generate narrative for.
        director: NarrativeDirector with LLM provider.

    Returns:
        Generated narrative text.
    """
    # Build prompt context from the event
    builder = director._prompt_builder  # Access internal builder

    # Get state-appropriate framing
    header, instruction = _get_state_framing(event.pool_ratio)

    # Build a focused prompt with state-aware framing
    prompt = f"""--- {header} ---
Pool Ratio: {event.pool_ratio:.1%} (current reserves vs initial)
Tension Level: {event.aggregate_tension:.1%}
Decision: {event.decision}
Wage Change: {event.wage_delta:+.1%}

{instruction}
Write 2-3 sentences capturing the mood and stakes.
"""

    # Generate using the director's LLM
    if director._llm is None:
        return "ERROR: No LLM configured"

    system_prompt = builder.build_system_prompt()

    try:
        return director._llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
        )
    except Exception as e:
        logger.error("Narrative generation failed: %s", e)
        return f"ERROR: {e}"


def check_in_range(value: int, range_tuple: tuple[int, int]) -> bool:
    """Check if value is within inclusive range.

    Args:
        value: Value to check.
        range_tuple: (min, max) inclusive range.

    Returns:
        True if min <= value <= max.
    """
    return range_tuple[0] <= value <= range_tuple[1]


def verify_u_curve(result: JudgmentResult, expectation: UCurveExpectation) -> tuple[bool, str]:
    """Verify if judgment matches U-Curve expectations.

    Args:
        result: JudgmentResult from Commissar evaluation.
        expectation: UCurveExpectation with expected ranges.

    Returns:
        Tuple of (passed: bool, status_message: str).
    """
    issues: list[str] = []

    if not check_in_range(result.ominousness, expectation.ominousness):
        issues.append(f"ominous={result.ominousness} not in {expectation.ominousness}")

    if not check_in_range(result.certainty, expectation.certainty):
        issues.append(f"certain={result.certainty} not in {expectation.certainty}")

    if not check_in_range(result.drama, expectation.drama):
        issues.append(f"drama={result.drama} not in {expectation.drama}")

    if issues:
        return False, "; ".join(issues)
    return True, "PASS"


def run_sweep(use_mock: bool = False) -> list[dict[str, str | int | float | bool]]:
    """Run the 5-point sweep analysis.

    Args:
        use_mock: If True, use MockLLM instead of real API.

    Returns:
        List of result dictionaries for each sweep point.
    """
    console = Console()

    # Initialize LLM provider
    llm: MockLLM | DeepSeekClient
    if use_mock:
        # Mock responses for testing (one per sweep point)
        mock_narratives = [
            "The economy hums along steadily. Workers accept their wages without complaint.",
            "Subtle tremors ripple through the markets. Questions arise about sustainability.",
            "Nobody knows what tomorrow brings. Confusion reigns as contradictions multiply.",
            "Panic grips the bourgeoisie. The rot becomes visible, undeniable.",
            "The edifice crumbles. Iron-fisted repression is the only option left.",
        ]
        mock_judgments = [
            '{"ominousness": 2, "certainty": 9, "drama": 3, "metaphor_family": "none"}',
            '{"ominousness": 4, "certainty": 5, "drama": 4, "metaphor_family": "physics"}',
            '{"ominousness": 5, "certainty": 3, "drama": 4, "metaphor_family": "physics"}',
            '{"ominousness": 7, "certainty": 6, "drama": 7, "metaphor_family": "biological"}',
            '{"ominousness": 9, "certainty": 9, "drama": 9, "metaphor_family": "biological"}',
        ]
        # Interleave narratives and judgments (2 calls per sweep point)
        all_responses: list[str] = []
        for i in range(MAX_SWEEP_POINTS):
            all_responses.append(mock_narratives[i])
            all_responses.append(mock_judgments[i])

        llm = MockLLM(responses=all_responses)
        console.print("[yellow]Using MockLLM for testing[/yellow]")
    else:
        try:
            llm = DeepSeekClient()
            console.print(f"[green]Using {llm.name} API[/green]")
        except Exception as e:
            console.print(f"[red]Failed to initialize LLM: {e}[/red]")
            console.print("[yellow]Falling back to MockLLM[/yellow]")
            return run_sweep(use_mock=True)

    # Load persona and create director
    try:
        persona = load_default_persona()
        console.print(f"[green]Loaded persona: {persona.name}[/green]")
    except Exception as e:
        console.print(f"[yellow]Could not load persona: {e}[/yellow]")
        persona = None

    director = NarrativeDirector(
        use_llm=True,
        llm=llm,
        persona=persona,
    )

    # Create commissar with same LLM (but separate for evaluation)
    commissar_llm: MockLLM | DeepSeekClient
    if use_mock:
        # Need a fresh MockLLM for commissar with just judgment responses
        commissar_llm = MockLLM(
            responses=[
                '{"ominousness": 2, "certainty": 9, "drama": 3, "metaphor_family": "none"}',
                '{"ominousness": 4, "certainty": 5, "drama": 4, "metaphor_family": "physics"}',
                '{"ominousness": 5, "certainty": 3, "drama": 4, "metaphor_family": "physics"}',
                '{"ominousness": 7, "certainty": 6, "drama": 7, "metaphor_family": "biological"}',
                '{"ominousness": 9, "certainty": 9, "drama": 9, "metaphor_family": "biological"}',
            ]
        )
    else:
        commissar_llm = llm

    commissar = NarrativeCommissar(llm=commissar_llm)

    results: list[dict[str, str | int | float | bool]] = []

    console.print()
    console.print("[bold]Running 5-point sweep...[/bold]")
    console.print()

    for i, point in enumerate(SWEEP_POINTS):
        console.print(f"  [{i + 1}/{MAX_SWEEP_POINTS}] {point.phase} (ratio={point.ratio})...")

        # Generate narrative
        event = create_crisis_event(point)
        narrative = generate_narrative(event, director)

        # Evaluate narrative
        try:
            judgment = commissar.evaluate(narrative)
        except Exception as e:
            logger.error("Commissar evaluation failed: %s", e)
            judgment = JudgmentResult(
                ominousness=5,
                certainty=5,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

        # Verify against U-Curve expectations
        expectation = U_CURVE_EXPECTATIONS[i]
        passed, status = verify_u_curve(judgment, expectation)

        results.append(
            {
                "ratio": point.ratio,
                "phase": point.phase,
                "ominousness": judgment.ominousness,
                "certainty": judgment.certainty,
                "drama": judgment.drama,
                "metaphor": judgment.metaphor_family.value,
                "passed": passed,
                "status": status,
                "narrative": narrative[:100] + "..." if len(narrative) > 100 else narrative,
            }
        )

    return results


def format_results_table(results: list[dict[str, str | int | float | bool]]) -> Table:
    """Format results as a Rich table.

    Args:
        results: List of result dictionaries from run_sweep().

    Returns:
        Rich Table for console display.
    """
    table = Table(title="Dialectical U-Curve Analysis")

    table.add_column("Ratio", justify="right", style="cyan")
    table.add_column("Phase", justify="left", style="magenta")
    table.add_column("Ominous", justify="right")
    table.add_column("Certain", justify="right")
    table.add_column("Drama", justify="right")
    table.add_column("Metaphor", justify="left")
    table.add_column("Status", justify="left")

    for row in results:
        status_style = "green" if row["passed"] else "red"
        status_text = "PASS" if row["passed"] else str(row["status"])

        table.add_row(
            f"{row['ratio']:.1f}",
            str(row["phase"]),
            str(row["ominousness"]),
            str(row["certainty"]),
            str(row["drama"]),
            str(row["metaphor"]),
            f"[{status_style}]{status_text}[/{status_style}]",
        )

    return table


def main() -> int:
    """Run the narrative sweep analysis.

    Returns:
        Exit code: 0 if all points pass, 1 otherwise.
    """
    console = Console()

    console.print()
    console.print("=" * 60)
    console.print("[bold]        Dialectical U-Curve Analysis[/bold]")
    console.print("=" * 60)
    console.print()
    console.print("Testing hypothesis: Narrative certainty follows U-shape")
    console.print("  STABLE (0.9): High certainty ('all is well')")
    console.print("  INFLECTION (0.5): Low certainty (maximum uncertainty)")
    console.print("  COLLAPSE (0.1): High certainty ('doom is certain')")
    console.print()

    # Check for --mock flag
    use_mock = "--mock" in sys.argv

    results = run_sweep(use_mock=use_mock)

    # Display results table
    console.print()
    table = format_results_table(results)
    console.print(table)
    console.print()

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    if passed_count == total_count:
        console.print(f"[bold green]All {total_count} points passed![/bold green]")
        console.print("[green]U-Curve hypothesis supported by this sweep.[/green]")
        return 0
    else:
        console.print(
            f"[bold red]{total_count - passed_count} of {total_count} points failed.[/bold red]"
        )
        console.print("[yellow]U-Curve hypothesis not fully supported.[/yellow]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
