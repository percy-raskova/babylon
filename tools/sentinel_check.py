#!/usr/bin/env python3
"""CLI dispatcher for the ``babylon.sentinels`` family (VIII.12 / III.11 gates).

Each sentinel is a declared-invariant registry plus a set of loud static checks;
this thin shim just routes ``sentinel_check.py <sensor> --check`` to the chosen
sentinel's ``main``. The check logic lives in the importable package
(``babylon.sentinels.*``) so it is unit-testable and mutation-testable without a
``sys.path`` hack — this file carries no logic of its own.

Run: ``poetry run python tools/sentinel_check.py seam --check``. Exit codes are
the sentinel's own contract: 0 clean, 1 gating violations, 2 infrastructure
failure (source missing/unparseable — never swallowed into a false pass).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from babylon.sentinels.seam.checks import main as seam_main

#: Registered sentinels: name -> its ``main(argv)`` entry point.
_SENSORS: dict[str, Callable[[list[str] | None], int]] = {
    "seam": seam_main,
}


def main(argv: list[str] | None = None) -> int:
    """Route to the chosen sentinel's ``main`` and return its exit code.

    :param argv: CLI args; first positional selects the sensor, ``--check`` is
        the CI-mode alias forwarded to the sentinel (which always gates).
    :returns: The selected sentinel's exit code (0 clean / 1 gating / 2 infra).
    """
    parser = argparse.ArgumentParser(
        description="Babylon Sentinels — run a declared-invariant sensor (VIII.12 / III.11).",
    )
    parser.add_argument("sensor", choices=sorted(_SENSORS), help="which sentinel to run")
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the sentinel always gates (exit 1 on violations).",
    )
    args = parser.parse_args(argv)
    return _SENSORS[args.sensor](["--check"] if args.check else [])


if __name__ == "__main__":
    sys.exit(main())
