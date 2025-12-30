#!/usr/bin/env python3
"""Verification tool for Multiverse Protocol mathematical divergence.

This tool runs all 8 multiverse scenarios through 52 ticks (1 Imperial Year)
and produces a markdown table showing the P(S|R) divergence across scenarios.

Expected Results (PPP Model):
- High SW -> High PPP -> High Effective Wealth -> P(S|A) high (Stable for Capital)
- Low SW -> Low PPP -> Low Effective Wealth -> P(S|A) crashes (Revolution likely)

The PPP (Purchasing Power Parity) model implements Unequal Exchange theory:
- Bourgeoisie captures SURPLUS VALUE (Money/Profit)
- Labor Aristocracy captures USE VALUE (Cheap Commodities via PPP)

The "unearned increment" = Effective Wealth - Nominal Wage = material basis
of labor aristocracy loyalty.

Usage:
    poetry run python tools/verify_math_divergence.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import (
    apply_scenario,
    create_two_node_scenario,
    get_multiverse_scenarios,
)
from babylon.engine.simulation_engine import step
from babylon.models.scenario import ScenarioConfig

# Use centralized timescale constant (1 tick = 1 week, 52 ticks = 1 year)
TICKS_PER_YEAR: Final[int] = GameDefines().timescale.ticks_per_year

# Entity IDs
WORKER_ID: Final[str] = "C001"  # Periphery worker (exploited)
OWNER_ID: Final[str] = "C002"  # Core owner (exploiter, receives rent)


def run_scenario_simulation(
    scenario: ScenarioConfig,
    num_ticks: int = TICKS_PER_YEAR,
) -> tuple[float, float, float, float, float, float, float]:
    """Run a scenario through simulation and return final metrics.

    Args:
        scenario: ScenarioConfig to apply
        num_ticks: Number of simulation ticks to run

    Returns:
        Tuple of (worker_p_revolution, worker_p_acquiescence, worker_wealth,
                  owner_wealth, worker_organization, effective_wealth, unearned_increment)
    """
    # Create base scenario
    base_state, base_config, base_defines = create_two_node_scenario()

    # Apply scenario modifiers - now returns (state, config, defines) 3-tuple
    # Mikado Refactor: superwage_multiplier is applied to defines.economy
    state, config, defines = apply_scenario(base_state, base_config, base_defines, scenario)

    # Create persistent context for multi-tick simulation
    persistent_context: dict[str, object] = {}

    # Run simulation for num_ticks - pass modified defines for PPP calculation
    for _ in range(num_ticks):
        state = step(state, config, persistent_context, defines=defines)

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
        worker.effective_wealth,
        worker.unearned_increment,
    )


# Result tuple type: (scenario, p_rev, p_acq, worker_wealth, owner_wealth, org, eff_wealth, unearned)
ResultTuple = tuple[ScenarioConfig, float, float, float, float, float, float, float]


def format_markdown_table(results: list[ResultTuple]) -> str:
    """Format results as a markdown table.

    Args:
        results: List of (scenario, p_rev, p_acq, worker_wealth, owner_wealth, org, eff_wealth, unearned) tuples

    Returns:
        Markdown formatted table string
    """
    lines = [
        "| Scenario | SW | Sol | Rep | P(S|R) | P(S|A) | W.Nom | W.Eff | Unearned | O.Wealth |",
        "|----------|-----|-----|-----|--------|--------|-------|-------|----------|----------|",
    ]

    for scenario, p_rev, p_acq, w_wealth, o_wealth, _org, eff_wealth, unearned in results:
        lines.append(
            f"| {scenario.name} | {scenario.superwage_multiplier} | "
            f"{scenario.solidarity_index} | {scenario.repression_capacity} | "
            f"{p_rev:.4f} | {p_acq:.4f} | {w_wealth:.4f} | {eff_wealth:.4f} | "
            f"{unearned:.4f} | {o_wealth:.4f} |"
        )

    return "\n".join(lines)


def verify_expected_divergence(results: list[ResultTuple]) -> bool:
    """Verify that extreme scenarios produce expected divergence.

    Expected (PPP Model):
    - High SW -> High PPP -> High Effective Wealth -> Higher P(S|A) (stable for capital)
    - Low SW -> Low PPP -> Low Effective Wealth -> Lower P(S|A) (revolution likely)
    - High SW should produce higher unearned_increment (material basis of loyalty)

    Args:
        results: List of (scenario, p_rev, p_acq, worker_wealth, owner_wealth, org, eff_wealth, unearned) tuples

    Returns:
        True if divergence is verified, False otherwise
    """
    stable_scenario: ResultTuple | None = None
    collapse_scenario: ResultTuple | None = None

    for result in results:
        scenario = result[0]
        if (
            scenario.superwage_multiplier == 1.5
            and scenario.solidarity_index == 0.2
            and scenario.repression_capacity == 0.8
        ):
            stable_scenario = result
        elif (
            scenario.superwage_multiplier == 0.3
            and scenario.solidarity_index == 0.8
            and scenario.repression_capacity == 0.2
        ):
            collapse_scenario = result

    if stable_scenario is None or collapse_scenario is None:
        print("ERROR: Could not find extreme scenarios in results")
        return False

    # Extract values: (scenario, p_rev, p_acq, worker_wealth, owner_wealth, org, eff_wealth, unearned)
    stable_p_rev = stable_scenario[1]
    stable_p_acq = stable_scenario[2]
    stable_owner_wealth = stable_scenario[4]
    stable_eff_wealth = stable_scenario[6]
    stable_unearned = stable_scenario[7]

    collapse_p_rev = collapse_scenario[1]
    collapse_p_acq = collapse_scenario[2]
    collapse_owner_wealth = collapse_scenario[4]
    collapse_eff_wealth = collapse_scenario[6]
    collapse_unearned = collapse_scenario[7]

    print("\nDivergence Verification (PPP Model):")
    print("  Stable scenario (HighSW_LowSol_HighRep):")
    print(
        f"    P(S|R)={stable_p_rev:.4f}, P(S|A)={stable_p_acq:.4f}, "
        f"Eff.Wealth={stable_eff_wealth:.4f}, Unearned={stable_unearned:.4f}"
    )
    print("  Collapse scenario (LowSW_HighSol_LowRep):")
    print(
        f"    P(S|R)={collapse_p_rev:.4f}, P(S|A)={collapse_p_acq:.4f}, "
        f"Eff.Wealth={collapse_eff_wealth:.4f}, Unearned={collapse_unearned:.4f}"
    )

    # Check all success criteria
    all_pass = True

    # PPP Model Check 1: High SW -> Higher Effective Wealth
    if stable_eff_wealth > collapse_eff_wealth:
        print(
            f"\n  [PASS] PPP Effective Wealth: {stable_eff_wealth:.4f} > {collapse_eff_wealth:.4f}"
        )
        print("         (High superwage_multiplier -> Higher purchasing power via PPP)")
    else:
        print(
            f"\n  [FAIL] PPP Effective Wealth: expected {stable_eff_wealth:.4f} > {collapse_eff_wealth:.4f}"
        )
        all_pass = False

    # PPP Model Check 2: High SW -> Higher Unearned Increment
    if stable_unearned > collapse_unearned:
        print(f"  [PASS] Unearned Increment: {stable_unearned:.4f} > {collapse_unearned:.4f}")
        print(
            "         (High SW -> Higher PPP bonus -> Material basis of labor aristocracy loyalty)"
        )
    else:
        print(
            f"  [FAIL] Unearned Increment: expected {stable_unearned:.4f} > {collapse_unearned:.4f}"
        )
        all_pass = False

    # Bug 1 Fix: High Solidarity -> Higher P(S|R)
    if collapse_p_rev > stable_p_rev:
        print(f"  [PASS] P(S|R) divergence: {collapse_p_rev:.4f} > {stable_p_rev:.4f}")
        print("         (Solidarity affects P(S|R) through multiplicative organization bonus)")
    else:
        print(f"  [FAIL] P(S|R) divergence: expected {collapse_p_rev:.4f} > {stable_p_rev:.4f}")
        all_pass = False

    # Note: With PPP model, owner wealth may be equal across scenarios
    # since superwage_multiplier no longer affects extraction_efficiency.
    # Owner wealth is determined by extraction (minus wages paid).
    if stable_owner_wealth != collapse_owner_wealth:
        diff = stable_owner_wealth - collapse_owner_wealth
        print(f"  [INFO] Owner wealth difference: {diff:+.4f}")
    else:
        print(f"  [INFO] Owner wealth equal: {stable_owner_wealth:.4f} (expected with PPP model)")
        print("         (superwage_multiplier affects PPP, not extraction)")
    # This is no longer a pass/fail criterion for PPP model

    if all_pass:
        print("\n  [ALL PASS] PPP Model working - mathematical divergence verified!")
    else:
        print("\n  [SOME FAILED] Review the failing criteria above")

    return all_pass


def main() -> int:
    """Run the verification tool.

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    print("=" * 80)
    print("MULTIVERSE PROTOCOL: PPP Model Mathematical Divergence Verification")
    print("=" * 80)
    print(f"\nRunning {TICKS_PER_YEAR} ticks (1 Imperial Year) for each of 8 scenarios...\n")

    # Get all multiverse scenarios
    scenarios = get_multiverse_scenarios()
    print(f"Generated {len(scenarios)} scenarios:\n")

    # Run simulations and collect results
    results: list[ResultTuple] = []

    for scenario in scenarios:
        p_rev, p_acq, w_wealth, o_wealth, org, eff_wealth, unearned = run_scenario_simulation(
            scenario
        )
        results.append((scenario, p_rev, p_acq, w_wealth, o_wealth, org, eff_wealth, unearned))
        print(
            f"  {scenario.name}: P(S|R)={p_rev:.4f}, P(S|A)={p_acq:.4f}, "
            f"EffWealth={eff_wealth:.4f}, Unearned={unearned:.4f}"
        )

    # Sort by effective wealth for better visualization of PPP impact
    results_sorted = sorted(results, key=lambda x: x[6], reverse=True)  # Sort by effective_wealth

    print("\n" + "=" * 80)
    print("RESULTS TABLE (sorted by Effective Wealth descending)")
    print("=" * 80 + "\n")

    # Output markdown table
    table = format_markdown_table(results_sorted)
    print(table)

    print("\n" + "=" * 80)

    # Verify expected divergence
    success = verify_expected_divergence(results)

    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
