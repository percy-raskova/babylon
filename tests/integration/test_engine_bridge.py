"""Integration tests for the engine-bridged headless runner.

Spec: 065-engine-bridging (T005, T026-T029, T075, T076).

Tests in this module require a live Postgres test DB
(``BABYLON_TEST_PG_DSN``) and the SQLite reference DB at
``data/sqlite/marxist-data-3NF.sqlite``. They exercise the full
engine-bridged tick loop (no more no-op carry-forward).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PG_DSN = os.environ.get("BABYLON_TEST_PG_DSN")
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        PG_DSN is None,
        reason="BABYLON_TEST_PG_DSN env var not set; engine-bridge tests require Postgres.",
    ),
    pytest.mark.skipif(
        not SQLITE_REF.exists(),
        reason=f"SQLite reference DB missing at {SQLITE_REF}.",
    ),
]


# Test bodies land in T026 (smoke), T027 (determinism), T028 (tick-over-tick
# evolution), T029 (zero empty cells), T075 (tri-county wallclock smoke),
# T076 (SC-002 canonical wallclock budget).
