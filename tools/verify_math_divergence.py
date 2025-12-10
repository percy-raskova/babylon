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

# Entity IDs
WORKER_ID: Final[str] = "C001"  # Periphery worker (exploited)
OWNER_ID: Final[str] = "C002"  # Core owner (exploiter, receives rent)


def run_scenario_simulation(
    scenario: ScenarioConfig,
    num_ticks: int = NUM_TICKS,
) -> tuple[float, float, float, float, float]:
    """Run a scenario through simulation and return final metrics.

    Args:
        scenario: ScenarioConfig to apply
        num_ticks: Number of simulation ticks to run

    Returns:
        Tuple of (worker_p_revolution, worker_p_acquiescence, worker_wealth,
                  owner_wealth, worker_organization)
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

    # Extract owner metrics (to verify rent flows correctly)
    owner = state.entities.get(OWNER_ID)
    if owner is None:
        raise ValueError(f"Owner entity {OWNER_ID} not found in state")

    return (
        worker.p_revolution,
        worker.p_acquiescence,
        worker.wealth,
        owner.wealth,
        worker.organization,
    )


# Result tuple type: (scenario, p_rev, p_acq, worker_wealth, owner_wealth, organization)
ResultTuple = tuple[ScenarioConfig, float, float, float, float, float]


def format_markdown_table(results: list[ResultTuple]) -> str:
    """Format results as a markdown table.

    Args:
        results: List of (scenario, p_rev, p_acq, worker_wealth, owner_wealth, org) tuples

    Returns:
        Markdown formatted table string
    """
    lines = [
        "| Scenario | Rent | Sol | Rep | P(S|R) | P(S|A) | W.Wealth | O.Wealth | Org |",
        "|----------|------|-----|-----|--------|--------|----------|----------|-----|",
    ]

    for scenario, p_rev, p_acq, w_wealth, o_wealth, org in results:
        lines.append(
            f"| {scenario.name} | {scenario.rent_level} | "
            f"{scenario.solidarity_index} | {scenario.repression_capacity} | "
            f"{p_rev:.4f} | {p_acq:.4f} | {w_wealth:.4f} | {o_wealth:.4f} | {org:.2f} |"
        )

    return "\n".join(lines)


def verify_expected_divergence(results: list[ResultTuple]) -> bool:
    """Verify that extreme scenarios produce expected divergence.

    Expected:
    - High Rent + Low Solidarity + High Repression -> Low P(S|R), Low Worker Wealth, High Owner Wealth
    - Low Rent + High Solidarity + Low Repression -> High P(S|R), High Worker Wealth, Low Owner Wealth

    Args:
        results: List of (scenario, p_rev, p_acq, worker_wealth, owner_wealth, org) tuples

    Returns:
        True if divergence is verified, False otherwise
    """
    stable_scenario: ResultTuple | None = None
    collapse_scenario: ResultTuple | None = None

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

    # Extract values: (scenario, p_rev, p_acq, worker_wealth, owner_wealth, org)
    stable_p_rev = stable_scenario[1]
    stable_owner_wealth = stable_scenario[4]
    stable_org = stable_scenario[5]

    collapse_p_rev = collapse_scenario[1]
    collapse_owner_wealth = collapse_scenario[4]
    collapse_org = collapse_scenario[5]

    print("\nDivergence Verification:")
    print("  Stable scenario (HighRent_LowSol_HighRep):")
    print(
        f"    P(S|R) = {stable_p_rev:.4f}, Owner Wealth = {stable_owner_wealth:.4f}, Org = {stable_org:.2f}"
    )
    print("  Collapse scenario (LowRent_HighSol_LowRep):")
    print(
        f"    P(S|R) = {collapse_p_rev:.4f}, Owner Wealth = {collapse_owner_wealth:.4f}, Org = {collapse_org:.2f}"
    )

    # Check all success criteria
    all_pass = True

    # Bug 1 Fix: High Solidarity -> Higher P(S|R) (via solidarity multiplier on organization)
    # P(S|R) = effective_org / repression, where effective_org = base_org * solidarity_multiplier
    if collapse_p_rev > stable_p_rev:
        print(f"  [PASS] P(S|R) divergence: {collapse_p_rev:.4f} > {stable_p_rev:.4f}")
        print("         (Solidarity affects P(S|R) through multiplicative organization bonus)")
    else:
        print(f"  [FAIL] P(S|R) divergence: expected {collapse_p_rev:.4f} > {stable_p_rev:.4f}")
        all_pass = False

    # Bug 2 Fix: High Rent -> Higher Owner Wealth (rent accumulates in Core)
    if stable_owner_wealth > collapse_owner_wealth:
        print(
            f"  [PASS] Owner wealth divergence: {stable_owner_wealth:.4f} > {collapse_owner_wealth:.4f}"
        )
        print("         (High rent extraction transfers wealth from Worker to Owner)")
    else:
        print(
            f"  [FAIL] Owner wealth divergence: expected {stable_owner_wealth:.4f} > {collapse_owner_wealth:.4f}"
        )
        all_pass = False

    if all_pass:
        print("\n  [ALL PASS] Both bugs fixed - mathematical model works correctly!")
    else:
        print("\n  [SOME FAILED] Review the failing criteria above")

    return all_pass


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
    results: list[ResultTuple] = []

    for scenario in scenarios:
        p_rev, p_acq, w_wealth, o_wealth, org = run_scenario_simulation(scenario)
        results.append((scenario, p_rev, p_acq, w_wealth, o_wealth, org))
        print(f"  {scenario.name}: P(S|R)={p_rev:.4f}, Org={org:.2f}, OwnerWealth={o_wealth:.4f}")

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
