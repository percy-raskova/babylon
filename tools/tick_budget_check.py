"""Run the bounded Rust persistence path for a requested tick budget."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

DEFAULT_BUDGET_PATH = Path("specs/104-national-tick-compute/budget.json")
DEFAULT_TICKS = 5
DEFAULT_SCOPE = "michigan"


def check_budget(ticks: int, budget_path: Path, scope: str = DEFAULT_SCOPE) -> int:
    """Run the Rust authority root; storage and timing gates live there."""
    del budget_path, scope
    result = subprocess.run(
        ["babylon-runtime", "run", "--ticks", str(ticks)],
        check=False,
    )
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=DEFAULT_TICKS)
    parser.add_argument("--scope", default=DEFAULT_SCOPE)
    parser.add_argument("--budget", type=Path, default=DEFAULT_BUDGET_PATH)
    args = parser.parse_args()
    raise SystemExit(check_budget(args.ticks, args.budget, args.scope))


if __name__ == "__main__":
    main()
