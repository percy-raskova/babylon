#!/usr/bin/env python3
"""Generate ``0039_domain_contracts.sql`` from models/types.py + the registry.

The PostgreSQL ``CREATE DOMAIN`` types that lift the range/format contracts of
:mod:`babylon.models.types` are a BUILD PRODUCT, never hand-written — exactly
as ``tools/generate_defines_config.py`` renders ``defines.yaml`` from the
``GameDefines`` schema. The numeric domains' bounds come from the
``annotated_types`` metadata on the constrained types; the fips/h3 format
literals come from :mod:`babylon.sentinels.domain_sync.registry`. Rendering
lives in :mod:`babylon.sentinels.domain_sync.ddl` so this tool and the
``domain_sync`` sentinel share one renderer.

Regenerate after changing a ``types.py`` bound or a registry pattern::

    uv run python tools/generate_domain_ddl.py           # write
    uv run python tools/generate_domain_ddl.py --check    # CI: verify in sync

The ``domain_sync`` sentinel is the independent guard (it re-derives the
expected CHECK from ``types.py``/registry and compares against the committed
file), so a drift is caught even if this generator is bypassed.

See Also:
    :mod:`babylon.sentinels.domain_sync.registry` — the domain declarations.
    ``src/babylon/models/types.py`` — the numeric source of truth.
    ``ai/decisions/ADR138_domain_contracts.yaml`` — the design record.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.sentinels.domain_sync.ddl import build_migration_sql  # noqa: E402
from babylon.sentinels.domain_sync.registry import (  # noqa: E402
    MIGRATION_FILENAME,
    MIGRATION_PATH,
)

_REPO_ROOT = Path(__file__).parent.parent


def main() -> int:
    """Generate the domain-contracts migration, or verify it is in sync.

    With ``--check``, render in memory and compare against the on-disk file
    WITHOUT writing; exit non-zero if it is stale (a ``types.py`` bound or
    registry pattern changed but the migration was not regenerated).

    :returns: Process exit code — 0 clean/written, 1 stale (``--check``).
    """
    parser = argparse.ArgumentParser(description="Generate 0039_domain_contracts.sql")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the on-disk migration is up to date without writing (exit 1 if stale).",
    )
    args = parser.parse_args()

    rendered = build_migration_sql(MIGRATION_FILENAME)

    if args.check:
        if not MIGRATION_PATH.exists() or MIGRATION_PATH.read_text(encoding="utf-8") != rendered:
            print(
                f"STALE: {MIGRATION_PATH.relative_to(_REPO_ROOT)} is out of date. "
                "Regenerate with:\n  uv run python tools/generate_domain_ddl.py",
                file=sys.stderr,
            )
            return 1
        print(f"{MIGRATION_FILENAME} is up to date.")
        return 0

    MIGRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    MIGRATION_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote {MIGRATION_PATH.relative_to(_REPO_ROOT)} ({len(rendered.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
