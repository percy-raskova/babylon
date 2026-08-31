"""Rust-runtime parameter trace entrypoint.

Player parameter actions are a Gate 5 concern. Gate 3 can therefore run only
the governed empty-action batch and refuses Python-side parameter injection.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run_trace(max_ticks: int = 5) -> Path:
    """Run a bounded Rust trace and return its declared stdout path."""
    result = subprocess.run(
        ["babylon-runtime", "run", "--ticks", str(max_ticks)],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=5)
    args = parser.parse_args()
    print(run_trace(args.ticks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
