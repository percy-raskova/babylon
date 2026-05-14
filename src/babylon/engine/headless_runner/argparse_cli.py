"""CLI parser for the headless simulation runner.

Implements every flag from ``contracts/cli_contract.yaml`` as an
``argparse`` parser. Pure parser construction; no run logic.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the headless runner CLI.

    Returns:
        Fully configured parser mirroring ``contracts/cli_contract.yaml``.
    """
    parser = argparse.ArgumentParser(
        prog="babylon.engine.headless_runner",
        description="Headless Postgres-backed Babylon simulation runner (spec-064).",
    )

    parser.add_argument(
        "--ticks",
        type=int,
        default=1000,
        help="Number of weekly ticks to simulate (1..100000). Default: 1000.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2010,
        help="Calendar year corresponding to tick 0 (1900..2100). Default: 2010.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2010,
        help="Top-level RNG seed. Default 2010 (fixed, NOT time-derived).",
    )

    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        "--scope",
        type=str,
        default="michigan-canada",
        choices=[
            "michigan-canada",
            "michigan-statewide-no-canada",
            "detroit-tri-county",
            "national",
        ],
        help="Predefined scope name. Mutually exclusive with --fips.",
    )
    scope_group.add_argument(
        "--fips",
        type=str,
        default=None,
        help="Comma-separated 5-digit FIPS codes overriding --scope.",
    )

    parser.add_argument(
        "--external",
        type=str,
        default="canada",
        help="Comma-separated external boundary node ids. Default: canada.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override the artifact directory; default is timestamped.",
    )
    parser.add_argument(
        "--defines",
        type=Path,
        default=None,
        help="Optional TOML overlay path applied on top of GameDefines.load_default().",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="stderr logging level. stdout reserved for the artifact path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Bootstrap session + tick 0 only; skip the full tick loop.",
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=Path("data/sqlite/marxist-data-3NF.sqlite"),
        help="Override the SQLite reference DB path.",
    )

    return parser


__all__ = ["build_parser"]
