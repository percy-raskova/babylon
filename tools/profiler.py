"""cProfile wrapper for Babylon simulation profiling.

Runs the simulation for N ticks under cProfile to identify performance bottlenecks.
Output can be viewed with snakeviz or pstats.

Usage:
    poetry run python tools/profiler.py [--ticks N] [--output FILE]

Examples:
    # Print top 30 cumulative time functions
    poetry run python tools/profiler.py --ticks 100

    # Save profile for visualization with snakeviz
    poetry run python tools/profiler.py --ticks 500 --output results/profile.prof
    snakeviz results/profile.prof
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation


def profile_simulation(ticks: int = 100, output: str | None = None) -> None:
    """Profile simulation for N ticks with cProfile.

    Args:
        ticks: Number of simulation ticks to profile.
        output: Optional path to save .prof file for external visualization.
    """
    # Create minimal scenario for profiling
    initial_state, config, _defines = create_two_node_scenario()
    sim = Simulation(initial_state=initial_state, config=config)

    print(f"Profiling {ticks} simulation ticks...")

    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(ticks):
        sim.step()

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")

    if output:
        # Ensure output directory exists
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stats.dump_stats(output)
        print(f"Profile saved to {output}")
        print(f"View with: snakeviz {output}")
    else:
        print("\n" + "=" * 80)
        print("Top 30 functions by cumulative time:")
        print("=" * 80)
        stats.print_stats(30)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Profile Babylon simulation with cProfile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=100,
        help="Number of simulation ticks to profile (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output .prof file (optional, prints to stdout if not specified)",
    )

    args = parser.parse_args()
    profile_simulation(args.ticks, args.output)


if __name__ == "__main__":
    main()
