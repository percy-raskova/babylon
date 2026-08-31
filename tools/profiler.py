"""Profile the sole Rust runtime process instead of a Python engine."""

from __future__ import annotations

import argparse
import subprocess


def profile_simulation(
    ticks: int = 100,
    output: str | None = None,
    *,
    scope_name: str = "michigan",
) -> None:
    del output, scope_name
    subprocess.run(
        ["babylon-runtime", "run", "--ticks", str(ticks)],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=100)
    parser.add_argument("--scope", default="michigan")
    parser.add_argument("--output")
    args = parser.parse_args()
    profile_simulation(args.ticks, args.output, scope_name=args.scope)


if __name__ == "__main__":
    main()
