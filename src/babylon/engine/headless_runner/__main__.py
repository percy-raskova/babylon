"""``python -m babylon.engine.headless_runner`` entry point.

Parses CLI flags, builds a :class:`SimulationRunConfig`, dispatches to
``runner.run()``, and maps :class:`ExitReason` to the exit codes declared
in ``contracts/cli_contract.yaml``.

On non-zero exit, emits a single stderr line in the canonical format:
``ERROR <exit_code_name>: <message> | partial_artifacts=<path-or-NONE>``.
"""

from __future__ import annotations

import sys

from babylon.engine.headless_runner.argparse_cli import build_parser
from babylon.engine.headless_runner.runner import main_from_argv


def main() -> int:
    """Entry point for `python -m babylon.engine.headless_runner`."""
    parser = build_parser()
    args = parser.parse_args()
    return main_from_argv(args)


if __name__ == "__main__":  # pragma: no cover - module-execution wrapper
    sys.exit(main())
