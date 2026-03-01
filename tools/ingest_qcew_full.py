#!/usr/bin/env python3
"""Load raw QCEW 2022 employment/wage data into SQLite research database.

NOTE: This tool has been moved to the babylon-data package.
The data loading infrastructure was extracted from babylon into
a separate repository. Use the babylon-data CLI instead:

    cd /path/to/babylon-data
    poetry run python -m babylon_data.cli qcew ...

For more information, see the babylon-data repository.
"""

import sys


def main() -> int:
    """Entry point."""
    print(
        "ERROR: ingest_qcew_full.py has been moved to the babylon-data package.\n"
        "The data loading infrastructure was extracted from babylon.\n"
        "Use the babylon-data CLI instead.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
