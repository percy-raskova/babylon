#!/usr/bin/env python3
"""Tombstone: QCEW loading moved to the babylon-data package (spec-086).

The suppression-imputing loader (spec-086) lives in the babylon-data repo
and is importable here through the ``src/babylon_data`` symlink. Use:

    mise run data:qcew -- --dry-run           # full pipeline, no writes
    mise run data:qcew -- --apply             # staged build + validated swap
    poetry run python -m babylon_data.qcew --help

See specs/086-qcew-loader-imputation/quickstart.md for the operator guide.
"""

import sys


def main() -> int:
    """Entry point."""
    print(
        "ERROR: QCEW loading moved to the babylon-data package (spec-086).\n"
        "Use: mise run data:qcew -- --dry-run|--apply\n"
        "  or: poetry run python -m babylon_data.qcew --help\n"
        "Operator guide: specs/086-qcew-loader-imputation/quickstart.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
