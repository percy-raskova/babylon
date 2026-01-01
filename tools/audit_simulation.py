#!/usr/bin/env python3
"""Generate simulation health audit report for AI analysis.

Runs three diagnostic scenarios to validate simulation behavior:
- Baseline: Default parameters, expect stable survival
- Starvation: Very low extraction, expect Comprador collapse
- Glut: High extraction with zero subsistence, expect metabolic overshoot

Usage:
    poetry run python tools/audit_simulation.py
    poetry run python tools/audit_simulation.py --output reports/audit_latest.md
    poetry run python tools/audit_simulation.py --max-ticks 100

Output:
    Markdown report with scenario results and health status.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Import from centralized shared module (ADR036)
from shared import COMPRADOR_ID, PERIPHERY_WORKER_ID, inject_parameter, is_dead

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step
from babylon.models.world_state import WorldState

# Constants (COMPRADOR_ID imported from shared)
DEFAULT_OUTPUT: Final[str] = "reports/audit_latest.md"
DEFAULT_MAX_TICKS: Final[int] = 52

# Scenario parameters
STARVATION_EXTRACTION: Final[float] = 0.05  # Very low - starves Comprador
GLUT_EXTRACTION: Final[float] = 0.99  # Very high - causes metabolic overshoot
GLUT_SUBSISTENCE: Final[float] = 0.0  # Zero consumption

# Expected outcomes
BASELINE_MIN_TICKS: Final[int] = 50  # Baseline should survive at least 50 ticks
STARVATION_DEATH_THRESHOLD: Final[int] = 40  # Comprador should die before tick 40 (~10 months)


def run_full_simulation(
    defines: GameDefines,
    max_ticks: int,
    track_comprador: bool = False,
) -> dict[str, Any]:
    """Run simulation and return detailed metrics.

    Args:
        defines: GameDefines configuration
        max_ticks: Maximum ticks to run
        track_comprador: If True, track Comprador death instead of Worker

    Returns:
        Dict with keys: final_state, ticks_survived, outcome, comprador_death_tick,
        worker_death_tick, max_overshoot_ratio
    """
    state, config, _ = create_imperial_circuit_scenario()
    persistent_context: dict[str, Any] = {}

    result: dict[str, Any] = {
        "final_state": None,
        "ticks_survived": max_ticks,
        "outcome": "SURVIVED",
        "comprador_death_tick": None,
        "worker_death_tick": None,
        "max_overshoot_ratio": 0.0,
    }

    for tick in range(max_ticks):
        state = step(state, config, persistent_context, defines)

        # Track Comprador health (uses VitalitySystem's active field)
        comprador = state.entities.get(COMPRADOR_ID)
        if comprador and is_dead(comprador) and result["comprador_death_tick"] is None:
            result["comprador_death_tick"] = tick + 1

        # Track Worker health (uses VitalitySystem's active field)
        worker = state.entities.get(PERIPHERY_WORKER_ID)
        if worker and is_dead(worker) and result["worker_death_tick"] is None:
            result["worker_death_tick"] = tick + 1

        # Track metabolic overshoot
        overshoot = calculate_overshoot_ratio(state)
        if overshoot > result["max_overshoot_ratio"]:
            result["max_overshoot_ratio"] = overshoot

        # Determine death for early exit
        if track_comprador:
            if result["comprador_death_tick"] is not None:
                result["ticks_survived"] = tick + 1
                result["outcome"] = "COMPRADOR_DIED"
                result["final_state"] = state
                return result
        else:
            if result["worker_death_tick"] is not None:
                result["ticks_survived"] = tick + 1
                result["outcome"] = "WORKER_DIED"
                result["final_state"] = state
                return result

    result["final_state"] = state
    return result


def calculate_overshoot_ratio(state: WorldState) -> float:
    """Calculate metabolic overshoot ratio from entity consumption.

    For Glut scenario detection - uses consumption_needs / total_wealth
    as a proxy for overshoot when territories unavailable.

    Args:
        state: Current WorldState

    Returns:
        Overshoot ratio (>1.0 = overshoot condition)
    """
    # Try territory-based calculation first
    if state.territories:
        try:
            total_bio = sum(t.biocapacity for t in state.territories.values())
            total_consumption = sum(e.consumption_needs for e in state.entities.values())
            if total_bio > 0:
                return total_consumption / total_bio
        except AttributeError:
            pass  # biocapacity not available

    # Fallback: consumption vs wealth proxy
    total_consumption = sum(
        float(getattr(e, "consumption_needs", 0.0)) for e in state.entities.values()
    )
    total_wealth = sum(float(e.wealth) for e in state.entities.values())

    if total_wealth > 0:
        return total_consumption / total_wealth

    return 0.0


def format_overshoot(ratio: float) -> str:
    """Format overshoot ratio for display.

    Args:
        ratio: Overshoot ratio

    Returns:
        Formatted string or "N/A"
    """
    if ratio > 0:
        return f"{ratio:.2f}"
    return "N/A"


def generate_report(
    baseline_result: dict[str, Any],
    starvation_result: dict[str, Any],
    glut_result: dict[str, Any],
) -> str:
    """Generate markdown health report.

    Args:
        baseline_result: Result dict from baseline scenario
        starvation_result: Result dict from starvation scenario
        glut_result: Result dict from glut scenario

    Returns:
        Formatted markdown report
    """
    # Extract baseline metrics
    baseline_state = baseline_result["final_state"]
    comprador = baseline_state.entities.get(COMPRADOR_ID)
    p_c_wealth = float(comprador.wealth) if comprador else 0.0

    worker = baseline_state.entities.get(PERIPHERY_WORKER_ID)
    p_w_wealth = float(worker.wealth) if worker else 0.0

    rent_pool = float(baseline_state.economy.imperial_rent_pool)
    wage_rate = float(baseline_state.economy.current_super_wage_rate)

    # Evaluate scenario expectations
    baseline_pass = baseline_result["ticks_survived"] >= BASELINE_MIN_TICKS
    starvation_pass = (
        starvation_result["comprador_death_tick"] is not None
        and starvation_result["comprador_death_tick"] < STARVATION_DEATH_THRESHOLD
    )

    # Glut requires territories with biocapacity to test ecological limits
    # Skip if scenario has no territories (imperial circuit is 4-node economic model)
    glut_state = glut_result["final_state"]
    has_territories = bool(glut_state and glut_state.territories)
    glut_pass = glut_result["max_overshoot_ratio"] > 1.0 if has_territories else None
    glut_skipped = not has_territories

    # Determine overall health status (skip glut if no territories)
    core_tests_pass = baseline_pass and starvation_pass
    all_pass = core_tests_pass and (glut_skipped or glut_pass)
    status = "HEALTHY" if all_pass else "UNHEALTHY"

    # Format timestamp
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")

    return f"""# Simulation Health Report

**Generated**: {timestamp}
**Status**: {status}

## Scenario Results

| Scenario | Expected | Actual | Status |
|----------|----------|--------|--------|
| A: Baseline | Survives ≥{BASELINE_MIN_TICKS} ticks | {baseline_result["ticks_survived"]} ticks | {"✓ PASS" if baseline_pass else "✗ FAIL"} |
| B: Starvation | Comprador dies <{STARVATION_DEATH_THRESHOLD} ticks | {"Tick " + str(starvation_result["comprador_death_tick"]) if starvation_result["comprador_death_tick"] else "Survived"} | {"✓ PASS" if starvation_pass else "✗ FAIL"} |
| C: Glut | Overshoot >1.0 | {format_overshoot(glut_result["max_overshoot_ratio"])} | {"⊘ SKIP (no territories)" if glut_skipped else ("✓ PASS" if glut_pass else "✗ FAIL")} |

## Baseline Metrics (Tick {baseline_result["ticks_survived"]})

| Metric | Value |
|--------|-------|
| P_c Wealth (Comprador) | {p_c_wealth:.2f} |
| P_w Wealth (Periphery Worker) | {p_w_wealth:.4f} |
| Rent Pool | {rent_pool:.2f} |
| Super Wage Rate | {wage_rate:.2f} |
| Metabolic Overshoot | {format_overshoot(baseline_result["max_overshoot_ratio"])} |

## Scenario Parameters

| Scenario | Parameters |
|----------|------------|
| Baseline | Default GameDefines |
| Starvation | extraction_efficiency={STARVATION_EXTRACTION} |
| Glut | extraction_efficiency={GLUT_EXTRACTION}, default_subsistence={GLUT_SUBSISTENCE} |

## Interpretation

- **Baseline**: Tests that default parameters produce a stable simulation
- **Starvation**: Tests that low extraction causes Comprador collapse (validates economic circuit)
- **Glut**: Tests that unsustainable extraction causes metabolic overshoot (validates ecological limits)
"""


def main() -> int:
    """Generate simulation health audit report."""
    parser = argparse.ArgumentParser(
        description="Generate simulation health audit report for AI analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate default report
    %(prog)s

    # Custom output path
    %(prog)s --output reports/my_audit.md

    # Extended simulation length
    %(prog)s --max-ticks 100
        """,
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output markdown path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=f"Maximum simulation ticks (default: {DEFAULT_MAX_TICKS})",
    )
    args = parser.parse_args()

    base_defines = GameDefines()

    print("Running simulation audit...")
    print()

    # Scenario A: Baseline
    print(f"[A] Baseline test ({args.max_ticks} ticks)...", end=" ", flush=True)
    baseline_result = run_full_simulation(base_defines, args.max_ticks)
    baseline_pass = baseline_result["ticks_survived"] >= BASELINE_MIN_TICKS
    print(f"{baseline_result['outcome']} ({baseline_result['ticks_survived']} ticks)")

    # Scenario B: Starvation
    print(
        f"[B] Starvation test (extraction={STARVATION_EXTRACTION})...",
        end=" ",
        flush=True,
    )
    starvation_defines = inject_parameter(
        base_defines, "economy.extraction_efficiency", STARVATION_EXTRACTION
    )
    starvation_result = run_full_simulation(
        starvation_defines, args.max_ticks, track_comprador=True
    )
    if starvation_result["comprador_death_tick"]:
        print(f"Comprador died at tick {starvation_result['comprador_death_tick']}")
    else:
        print("Comprador SURVIVED (unexpected)")

    # Scenario C: Glut
    print(
        f"[C] Glut test (extraction={GLUT_EXTRACTION}, subsistence={GLUT_SUBSISTENCE})...",
        end=" ",
        flush=True,
    )
    glut_defines = inject_parameter(base_defines, "economy.extraction_efficiency", GLUT_EXTRACTION)
    glut_defines = inject_parameter(glut_defines, "survival.default_subsistence", GLUT_SUBSISTENCE)
    glut_result = run_full_simulation(glut_defines, args.max_ticks)
    print(f"Max overshoot: {format_overshoot(glut_result['max_overshoot_ratio'])}")

    print()

    # Generate report
    report = generate_report(
        baseline_result,
        starvation_result,
        glut_result,
    )

    # Write report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    # Summary
    baseline_pass = baseline_result["ticks_survived"] >= BASELINE_MIN_TICKS
    starvation_pass = (
        starvation_result["comprador_death_tick"] is not None
        and starvation_result["comprador_death_tick"] < STARVATION_DEATH_THRESHOLD
    )

    # Glut requires territories - skip if none present
    glut_state = glut_result["final_state"]
    has_territories = bool(glut_state and glut_state.territories)
    glut_pass = glut_result["max_overshoot_ratio"] > 1.0 if has_territories else None
    glut_skipped = not has_territories

    print(f"Audit report saved to {output_path}")
    print()
    print("Summary:")
    print(f"  Baseline:   {'PASS' if baseline_pass else 'FAIL'}")
    print(f"  Starvation: {'PASS' if starvation_pass else 'FAIL'}")
    print(
        f"  Glut:       {'SKIP (no territories)' if glut_skipped else ('PASS' if glut_pass else 'FAIL')}"
    )

    # Core tests must pass; glut is skipped if no territories
    core_pass = baseline_pass and starvation_pass
    return 0 if (core_pass and (glut_skipped or glut_pass)) else 1


if __name__ == "__main__":
    sys.exit(main())
