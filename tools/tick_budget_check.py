"""Tick-compute budget gate (spec-104).

Runs a short national-scope simulation and checks the per-system wallclock
against a ratified budget. Exits 0 (pass) or 1 (fail).

The budget file (``specs/104-national-tick-compute/budget.json``) maps
system class names to their ratified cumulative-ms ceiling for the
configured tick count. The budget is ratified AFTER the first measurement
(per master plan §6: "number set AFTER first measurement").

Usage:
    poetry run python tools/tick_budget_check.py [--ticks N] [--budget FILE]

Examples:
    poetry run python tools/tick_budget_check.py
    poetry run python tools/tick_budget_check.py --ticks 5
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from babylon.config.defines import GameDefines  # noqa: E402

DEFAULT_BUDGET_PATH = (
    Path(__file__).parent.parent / "specs" / "104-national-tick-compute" / "budget.json"
)
DEFAULT_TICKS = 5
DEFAULT_SCOPE = "national"


def check_budget(ticks: int, budget_path: Path, scope: str = DEFAULT_SCOPE) -> int:
    """Run a national simulation and check per-system ms against budget."""
    defines = GameDefines.load_default()
    print(f"Running {ticks}-tick {scope} simulation for budget check...")

    with tempfile.TemporaryDirectory(prefix="tick-budget-") as tmpdir:
        from babylon.engine.headless_runner import run as headless_run
        from babylon.engine.headless_runner.models import SimulationRunConfig
        from babylon.engine.headless_runner.scopes import resolve_scope

        scope_obj = resolve_scope(scope)
        config = SimulationRunConfig(
            ticks=ticks,
            random_seed=getattr(defines, "rng_seed", 2010),
            scope_name=scope,
            scope_fips=scope_obj.scope_fips,
            external_node_ids=scope_obj.external_node_ids,
            output_dir=Path(tmpdir),
        )
        result = headless_run(config)

    perf = result.performance
    per_system = perf.per_system_ms
    ticks_completed = max(result.ticks_completed, 1)

    print(f"\nCompleted {result.ticks_completed} ticks in {perf.tick_loop_sec:.1f}s")
    print(f"Per-tick median: {perf.per_tick_median_ms:.1f}ms, p99: {perf.per_tick_p99_ms:.1f}ms")
    print(f"\n{'System':<40} {'Total ms':>10} {'ms/tick':>10} {'Budget ms':>10} {'Status':>8}")
    print("-" * 82)

    if not budget_path.exists():
        print(f"\nWARNING: budget file not found at {budget_path}")
        print("Printing measured values only (no budget enforcement).\n")
        budget = {}
    else:
        budget = json.loads(budget_path.read_text())

    all_pass = True
    for sys_name in sorted(per_system, key=lambda k: per_system[k], reverse=True):
        total_ms = per_system[sys_name]
        ms_per_tick = total_ms / ticks_completed
        budget_ms = budget.get(sys_name)
        if budget_ms is not None:
            status = "PASS" if total_ms <= budget_ms else "FAIL"
            if total_ms > budget_ms:
                all_pass = False
            budget_str = f"{budget_ms:.1f}"
        else:
            status = "N/A"
            budget_str = "-"
        print(f"{sys_name:<40} {total_ms:>10.1f} {ms_per_tick:>10.1f} {budget_str:>10} {status:>8}")

    if all_pass:
        print("\nAll systems within budget.")
        return 0
    else:
        print("\nBUDGET EXCEEDED — see FAIL rows above.")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tick-compute budget gate (spec-104)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ticks", type=int, default=DEFAULT_TICKS, help=f"Ticks to run (default: {DEFAULT_TICKS})"
    )
    parser.add_argument(
        "--scope", type=str, default=DEFAULT_SCOPE, help=f"Scope name (default: {DEFAULT_SCOPE})"
    )
    parser.add_argument(
        "--budget", type=Path, default=DEFAULT_BUDGET_PATH, help="Budget JSON file path"
    )
    args = parser.parse_args()

    sys.exit(check_budget(args.ticks, args.budget, args.scope))


if __name__ == "__main__":
    main()
