"""Run the Rust authority root for a bounded persistence audit."""

from __future__ import annotations

import argparse
import subprocess


def run_full_simulation(max_ticks: int) -> dict[str, int]:
    result = subprocess.run(
        ["babylon-runtime", "run", "--ticks", str(max_ticks)],
        check=True,
    )
    return {"exit_code": result.returncode, "ticks_requested": max_ticks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-ticks", type=int, default=52)
    args = parser.parse_args()
    run_full_simulation(args.max_ticks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
