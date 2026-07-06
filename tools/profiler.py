"""cProfile wrapper for Babylon simulation profiling.

Runs the simulation for N ticks under cProfile to identify performance
bottlenecks. Output can be viewed with snakeviz or pstats.

Spec-064 migration: this tool now profiles the headless Postgres-backed
runner via :func:`tools.shared.run_simulation` (no in-memory engine
imports remain — SC-007).
Spec-104: ``--scope`` arg added for national-scale profiling.

Usage:
    poetry run python tools/profiler.py [--ticks N] [--scope NAME] [--output FILE]

Examples:
    poetry run python tools/profiler.py --ticks 100
    poetry run python tools/profiler.py --ticks 50 --output results/profile.prof
    poetry run python tools/profiler.py --scope national --ticks 20
    snakeviz results/profile.prof
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
from pathlib import Path

# Add src and tools to path for imports.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from shared import run_simulation  # noqa: E402

from babylon.config.defines import GameDefines  # noqa: E402


def profile_simulation(
    ticks: int = 100,
    output: str | None = None,
    *,
    scope_name: str = "detroit-tri-county",
) -> None:
    """Profile a single headless simulation run for ``ticks`` ticks."""
    defines = GameDefines.load_default()
    print(f"Profiling {ticks} ticks (scope={scope_name}) via headless_runner...")

    profiler = cProfile.Profile()
    profiler.enable()
    run_simulation(defines, max_ticks=ticks, scope_name=scope_name)
    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")

    if output:
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
        "--scope",
        type=str,
        default="detroit-tri-county",
        help="Predefined scope name (default: detroit-tri-county). "
        "Use 'national' for all ~3,156 US counties (spec-104).",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output .prof file (optional, prints to stdout if not specified)",
    )
    args = parser.parse_args()
    profile_simulation(args.ticks, args.output, scope_name=args.scope)


if __name__ == "__main__":
    main()
