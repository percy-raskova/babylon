#!/usr/bin/env python3
"""Verification tool for Multiverse Protocol mathematical divergence.

This tool runs all 8 multiverse scenarios through 10 ticks of simulation
and produces a markdown table showing the P(S|R) divergence across scenarios.

Expected Results:
- High Rent + Low Solidarity + High Repression -> Low P(S|R) (Stable for Capital)
- Low Rent + High Solidarity + Low Repression -> High P(S|R) (Revolution likely)

Usage:
    poetry run python tools/verify_math_divergence.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.engine.scenarios import (
    apply_scenario,
    create_two_node_scenario,
    get_multiverse_scenarios,
)
from babylon.engine.simulation_engine import step
from babylon.models.scenario import ScenarioConfig

# Number of simulation ticks to run per scenario
NUM_TICKS: Final[int] = 10

# Entity ID of the worker whose P(S|R) we track
WORKER_ID: Final[str] = "C001"


def run_scenario_simulation(
    scenario: ScenarioConfig,
    num_ticks: int = NUM_TICKS,
) -> tuple[float, float, float]:
    """Run a scenario through simulation and return final metrics.

    Args:
        scenario: ScenarioConfig to apply
        num_ticks: Number of simulation ticks to run

    Returns:
        Tuple of (final_p_revolution, final_p_acquiescence, final_wealth)
    """
    # Create base scenario
    base_state, base_config = create_two_node_scenario()

    # Apply scenario modifiers
    state, config = apply_scenario(base_state, base_config, scenario)

    # Create persistent context for multi-tick simulation
    persistent_context: dict[str, object] = {}

    # Run simulation for num_ticks
    for _ in range(num_ticks):
        state = step(state, config, persistent_context)

    # Extract final metrics from worker
    worker = state.entities.get(WORKER_ID)
    if worker is None:
        raise ValueError(f"Worker entity {WORKER_ID} not found in state")

    return (
        worker.p_revolution,
        worker.p_acquiescence,
        worker.wealth,
    )


def format_markdown_table(
    results: list[tuple[ScenarioConfig, float, float, float]],
) -> str:
    """Format results as a markdown table.

    Args:
        results: List of (scenario, p_revolution, p_acquiescence, wealth) tuples

    Returns:
        Markdown formatted table string
    """
    lines = [
        "| Scenario | Rent | Solidarity | Repression | P(S|R) Final | P(S|A) Final | Wealth |",
        "|----------|------|------------|------------|--------------|--------------|--------|",
    ]

    for scenario, p_rev, p_acq, wealth in results:
        lines.append(
            f"| {scenario.name} | {scenario.rent_level} | "
            f"{scenario.solidarity_index} | {scenario.repression_capacity} | "
            f"{p_rev:.4f} | {p_acq:.4f} | {wealth:.4f} |"
        )

    return "\n".join(lines)


def verify_expected_divergence(
    results: list[tuple[ScenarioConfig, float, float, float]],
) -> bool:
    """Verify that extreme scenarios produce expected divergence.

    Expected:
    - High Rent + Low Solidarity + High Repression -> Low P(S|R)
    - Low Rent + High Solidarity + Low Repression -> High P(S|R)

    Args:
        results: List of (scenario, p_revolution, p_acquiescence, wealth) tuples

    Returns:
        True if divergence is verified, False otherwise
    """
    stable_scenario: tuple[ScenarioConfig, float, float, float] | None = None
    collapse_scenario: tuple[ScenarioConfig, float, float, float] | None = None

    for result in results:
        scenario = result[0]
        if (
            scenario.rent_level == 1.5
            and scenario.solidarity_index == 0.2
            and scenario.repression_capacity == 0.8
        ):
            stable_scenario = result
        elif (
            scenario.rent_level == 0.3
            and scenario.solidarity_index == 0.8
            and scenario.repression_capacity == 0.2
        ):
            collapse_scenario = result

    if stable_scenario is None or collapse_scenario is None:
        print("ERROR: Could not find extreme scenarios in results")
        return False

    stable_p_rev = stable_scenario[1]
    collapse_p_rev = collapse_scenario[1]

    print("\nDivergence Verification:")
    print(f"  Stable scenario P(S|R):   {stable_p_rev:.4f}")
    print(f"  Collapse scenario P(S|R): {collapse_p_rev:.4f}")
    print(f"  Difference:               {collapse_p_rev - stable_p_rev:.4f}")

    # Verify divergence: collapse scenario should have higher P(S|R)
    if collapse_p_rev > stable_p_rev:
        print("  [PASS] Mathematical divergence verified!")
        return True
    else:
        print("  [FAIL] Expected collapse scenario to have higher P(S|R)")
        return False


def main() -> int:
    """Run the verification tool.

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    print("=" * 70)
    print("MULTIVERSE PROTOCOL: Mathematical Divergence Verification")
    print("=" * 70)
    print(f"\nRunning {NUM_TICKS} ticks for each of 8 scenarios...\n")

    # Get all multiverse scenarios
    scenarios = get_multiverse_scenarios()
    print(f"Generated {len(scenarios)} scenarios:\n")

    # Run simulations and collect results
    results: list[tuple[ScenarioConfig, float, float, float]] = []

    for scenario in scenarios:
        p_rev, p_acq, wealth = run_scenario_simulation(scenario)
        results.append((scenario, p_rev, p_acq, wealth))
        print(f"  {scenario.name}: P(S|R)={p_rev:.4f}, P(S|A)={p_acq:.4f}")

    # Sort by P(S|R) for better visualization
    results_sorted = sorted(results, key=lambda x: x[1], reverse=True)

    print("\n" + "=" * 70)
    print("RESULTS TABLE (sorted by P(S|R) descending)")
    print("=" * 70 + "\n")

    # Output markdown table
    table = format_markdown_table(results_sorted)
    print(table)

    print("\n" + "=" * 70)

    # Verify expected divergence
    success = verify_expected_divergence(results)

    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
