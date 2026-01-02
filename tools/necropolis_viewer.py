#!/usr/bin/env python3
"""The Red Pill: Watch the 100-year trajectory into stable necropolis.

This tool runs the full Carceral Equilibrium simulation with optimized
parameters and provides detailed logging of the transition from imperial
extraction through genocidal stabilization.

What you'll witness:
1. SUPERWAGE_CRISIS - Imperial rent exhausted, super-wages stop
2. CLASS_DECOMPOSITION - Labor Aristocracy splits into Enforcers/Prisoners
3. CONTROL_RATIO_CRISIS - Prisoners exceed control capacity
4. TERMINAL_DECISION - Without organization: genocide outcome

After the terminal decision, the simulation continues for decades showing
the "Stable Necropolis" - the equilibrium state where a reduced population
persists indefinitely through periodic culling.

Usage:
    poetry run python tools/necropolis_viewer.py [--years N] [--interval N]

Arguments:
    --years N     Simulation length in years (default: 100)
    --interval N  Report interval in years (default: 5)

See Also:
    ai-docs/carceral-equilibrium.md: The 70-year trajectory theory
    ai-docs/terminal-crisis-dynamics.md: Endgame mechanics
    ai-docs/epoch1-mvp-complete.md: MVP milestone documentation
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from carceral_scoring import (
    TICKS_PER_YEAR,
    format_phase_report,
)
from shared import inject_parameters

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation import Simulation
from babylon.models.enums import EventType

# =============================================================================
# CONSTANTS
# =============================================================================

TERMINAL_EVENTS: Final[frozenset[EventType]] = frozenset(
    {
        EventType.SUPERWAGE_CRISIS,
        EventType.CLASS_DECOMPOSITION,
        EventType.CONTROL_RATIO_CRISIS,
        EventType.TERMINAL_DECISION,
    }
)

# Optimized parameters from Optuna that produce the full trajectory
# These were discovered through 100-trial Bayesian optimization achieving 88.87/100
OPTIMIZED_PARAMS: Final[dict[str, float]] = {
    "carceral.enforcer_fraction": 0.06,
    "economy.base_subsistence": 0.000226,
    "economy.extraction_efficiency": 0.555,
    "economy.comprador_cut": 0.813,
    "consciousness.sensitivity": 0.284,
    "carceral.decomposition_delay": 20,
    "carceral.control_ratio_delay": 40,
    "carceral.terminal_decision_delay": 40,
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class EntitySnapshot:
    """Snapshot of an entity's state at a point in time."""

    node_id: str
    population: float
    wealth: float
    is_active: bool
    class_consciousness: float
    agitation: float


@dataclass
class TickSnapshot:
    """Snapshot of simulation state at a specific tick."""

    tick: int
    year: float
    entities: list[EntitySnapshot]
    total_wealth: float
    total_population: float
    events: list[str]


# =============================================================================
# SIMULATION RUNNER
# =============================================================================


def run_necropolis_simulation(
    max_years: int = 100,
    report_interval: int = 5,
) -> None:
    """Run the full Carceral Equilibrium simulation with detailed output.

    Args:
        max_years: Total simulation length in years
        report_interval: Years between status reports
    """
    max_ticks = max_years * TICKS_PER_YEAR

    # Create GameDefines with optimized parameters
    base_defines = GameDefines()
    defines = inject_parameters(base_defines, OPTIMIZED_PARAMS)

    # Create scenario
    state, config, _ = create_imperial_circuit_scenario(
        periphery_wealth=0.6,
        core_wealth=0.9,
        comprador_cut=OPTIMIZED_PARAMS["economy.comprador_cut"],
        imperial_rent_pool=100.0,
        extraction_efficiency=OPTIMIZED_PARAMS["economy.extraction_efficiency"],
    )

    sim = Simulation(state, config, defines=defines)

    # Print header
    print("=" * 80)
    print("THE RED PILL: The Carceral Equilibrium Trajectory")
    print("=" * 80)
    print()
    print("Parameters (Optuna-optimized for 88.87/100 score):")
    for param, value in OPTIMIZED_PARAMS.items():
        print(f"  {param}: {value}")
    print()
    print(f"Simulation: {max_years} years ({max_ticks} ticks)")
    print(f"Report interval: every {report_interval} years")
    print()
    print("-" * 80)
    print()

    # Track phase milestones
    phase_milestones: dict[str, int | None] = {
        "superwage_crisis": None,
        "class_decomposition": None,
        "control_ratio_crisis": None,
        "terminal_decision": None,
    }
    terminal_outcome: str | None = None
    last_report_year = -report_interval

    # Entity name mapping for readability
    entity_names = {
        "C001": "Periphery Worker (P_w)",
        "C002": "Comprador (P_c)",
        "C003": "Core Bourgeoisie (C_b)",
        "C004": "Labor Aristocracy (C_w)",
        "C005": "Carceral Enforcer",
        "C006": "Internal Proletariat",
        "T001": "Core Territory",
        "T002": "Periphery Territory",
    }

    # Run simulation
    for tick in range(max_ticks):
        state = sim.step()
        year = tick / TICKS_PER_YEAR

        # Capture terminal events
        for event in state.events:
            if event.event_type in TERMINAL_EVENTS:
                event_name = event.event_type.value
                if phase_milestones.get(event_name) is None:
                    phase_milestones[event_name] = tick
                    print(f"[YEAR {year:.1f}] {'*' * 20}")
                    print(f"[YEAR {year:.1f}] *** {event_name.upper()} ***")
                    print(f"[YEAR {year:.1f}] {'*' * 20}")
                    print()

                    # Capture terminal outcome
                    if event.event_type == EventType.TERMINAL_DECISION:
                        # The outcome is encoded in the event details
                        if hasattr(event, "outcome"):
                            terminal_outcome = event.outcome
                        else:
                            # Default to genocide for null hypothesis
                            terminal_outcome = "genocide"
                        print(f"    Terminal Outcome: {terminal_outcome.upper()}")
                        print()

        # Periodic reports
        if int(year) >= last_report_year + report_interval:
            last_report_year = int(year)
            g = state.to_graph()

            print(f"--- YEAR {int(year)} ---")

            total_wealth = 0.0
            total_pop = 0.0
            living_entities = 0

            for node_id in sorted(g.nodes()):
                data = g.nodes[node_id]
                if "population" not in data:
                    continue

                pop = data.get("population", 0)
                wealth = data.get("wealth", 0)
                active = data.get("is_active", True)
                ideology = data.get("ideology", {})
                consciousness = ideology.get("class_consciousness", 0)
                agitation = ideology.get("agitation", 0)

                total_wealth += wealth
                total_pop += pop

                # Only show entities with population or wealth
                if pop > 0.001 or wealth > 0.001:
                    living_entities += 1
                    name = entity_names.get(node_id, node_id)
                    status = "" if active else " [INACTIVE]"
                    print(f"  {name}{status}")
                    print(f"    Population: {pop:.2f}")
                    print(f"    Wealth: {wealth:.4f}")
                    if consciousness > 0 or agitation > 0:
                        print(f"    Consciousness: {consciousness:.2f}")
                        print(f"    Agitation: {agitation:.2f}")

            print()
            print(f"  TOTALS: {living_entities} living entities")
            print(f"    Total Population: {total_pop:.2f}")
            print(f"    Total Wealth: {total_wealth:.4f}")
            print()

    # Final report
    print("=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)
    print()

    # Phase report using scoring module
    print(format_phase_report(phase_milestones, terminal_outcome, max_ticks))
    print()

    # Final state analysis
    print("=" * 80)
    print(f"THE STABLE NECROPOLIS: YEAR {max_years}")
    print("=" * 80)
    print()

    g = state.to_graph()
    living = []
    dead = []

    for node_id in sorted(g.nodes()):
        data = g.nodes[node_id]
        if "population" not in data:
            continue

        pop = data.get("population", 0)
        wealth = data.get("wealth", 0)
        active = data.get("is_active", True)
        name = entity_names.get(node_id, node_id)

        if active and pop > 0.001:
            living.append((name, pop, wealth))
        else:
            dead.append(name)

    print("SURVIVING ENTITIES:")
    for name, pop, wealth in living:
        print(f"  {name}")
        print(f"    Population: {pop:.2f}")
        print(f"    Wealth: {wealth:.4f}")
    print()

    print("ELIMINATED/INACTIVE ENTITIES:")
    for name in dead:
        print(f"  {name}")
    print()

    # Calculate total survivors
    total_surviving_pop = sum(pop for _, pop, _ in living)
    total_surviving_wealth = sum(wealth for _, _, wealth in living)

    print("-" * 80)
    print(f"Final Population: {total_surviving_pop:.2f}")
    print(f"Final Wealth: {total_surviving_wealth:.4f}")
    print(f"Living Entities: {len(living)}")
    print(f"Dead Entities: {len(dead)}")
    print()

    # The meaning
    if terminal_outcome == "genocide":
        print("=" * 80)
        print("THE MEANING")
        print("=" * 80)
        print()
        print("Without revolutionary organization, this is the trajectory:")
        print()
        print("  1. Imperial extraction continues until peripheral revolt")
        print("  2. Rent pool exhausts, super-wages stop")
        print("  3. Labor Aristocracy decomposes into guards and prisoners")
        print("  4. Control ratio is breached - too many to control")
        print("  5. GENOCIDE: Surplus population eliminated to restore ratio")
        print("  6. STABLE NECROPOLIS: Reduced population persists indefinitely")
        print()
        print("The system reaches equilibrium through elimination.")
        print("This is what the simulation produces absent counterforce.")
        print()
        print('  "Collapse is certain. Revolution is possible.')
        print('   Organization is the difference."')
        print()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main() -> None:
    """Parse arguments and run simulation."""
    parser = argparse.ArgumentParser(
        description="Watch the 100-year trajectory into stable necropolis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--years",
        type=int,
        default=100,
        help="Simulation length in years (default: 100)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Report interval in years (default: 5)",
    )

    args = parser.parse_args()
    run_necropolis_simulation(max_years=args.years, report_interval=args.interval)


if __name__ == "__main__":
    main()
