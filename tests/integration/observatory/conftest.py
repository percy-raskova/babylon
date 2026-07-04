"""Integration fixtures for the Observatory (spec-096, Postgres-gated).

Seeds a UNIQUE session into the simulation Postgres via the real persistence
path (``select_hex_rows_for_emission`` -> ``persist_tick_atomic``, which writes
``dynamic_hex_state`` deltas + a ``tick_commit`` row per tick), then registers
the Django ``sim`` alias pointing at that same database so the Observatory's
``connections["sim"]`` reads the seeded data. Isolation is per-session (uuid4);
partitions are dropped on teardown. Skips cleanly when Postgres is unavailable
(via the session-scoped ``pg_pool`` fixture from the root conftest).
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.integration

# Two Wayne-County (26163, state 26) hexes; 4 ticks with growing value so the
# aggregates change tick-to-tick (a non-trivial series).
_H3S = ["872a91055ffffff", "872a9105bffffff"]
_COUNTY = "26163"
_STATE = "26"
_TICKS = 4


@dataclass(frozen=True)
class SeededSession:
    """A session seeded into the sim DB for endpoint/read-only tests."""

    session_id: UUID
    county_fips: str
    state_fips: str
    min_tick: int
    max_tick: int
    tick_count: int


@pytest.fixture(scope="session")
def _sim_migrated(pg_pool: Any) -> Any:
    """Apply the runner's idempotent migrations once (views + tick_commit)."""
    from babylon.engine.headless_runner.runner import _apply_migrations

    _apply_migrations(pg_pool)
    return pg_pool


def _hex_row(session: UUID, tick: int, h3: str, scale: float) -> Any:
    from babylon.persistence.hex_state import DynamicHexState

    return DynamicHexState(
        session_id=session,
        tick=tick,
        h3_index=h3,
        county_fips=_COUNTY,
        state_fips=_STATE,
        region_id="east_north_central",
        c=10.0 * scale,
        v=5.0 * scale,
        s=3.0 * scale,
        k=100.0 * scale,
        biocapacity_stock=20.0,
        energy_stock=10.0,
        raw_material_stock=5.0,
        internet_access_pct=0.85,
        surveillance_coupling=0.4,
    )


@pytest.fixture
def seeded_session(_sim_migrated: Any) -> Generator[SeededSession, None, None]:
    """Seed a unique 4-tick session; drop its partitions on teardown."""
    from babylon.persistence.delta import select_hex_rows_for_emission
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.partitioning import drop_session_partitions, ensure_session_partitions
    from babylon.persistence.postgres_runtime import PostgresRuntime

    pool = _sim_migrated
    session = uuid4()
    ensure_session_partitions(pool=pool, session_id=session)
    runtime = PostgresRuntime(pool=pool)

    last_emitted: dict[str, tuple[float, ...]] = {}
    try:
        for tick in range(_TICKS):
            scale = 1.0 + 0.1 * tick  # values grow each tick
            frame = [_hex_row(session, tick, h3, scale) for h3 in _H3S]
            emitted = select_hex_rows_for_emission(
                tick=tick, candidate_rows=frame, last_emitted=last_emitted
            )
            runtime.persist_tick_atomic(
                PerTickTransactionEnvelope(
                    session_id=session,
                    tick=tick,
                    hex_state_rows=emitted,
                    determinism_hash=f"{tick:064d}"[:64],
                )
            )
        yield SeededSession(
            session_id=session,
            county_fips=_COUNTY,
            state_fips=_STATE,
            min_tick=0,
            max_tick=_TICKS - 1,
            tick_count=_TICKS,
        )
    finally:
        with contextlib.suppress(Exception):
            drop_session_partitions(pool=pool, session_id=session)


@pytest.fixture
def sim_alias(pg_dsn: str) -> Generator[str, None, None]:
    """Register the Django ``sim`` alias pointing at the live sim DB, read-only.

    Added AFTER pytest-django's DB setup, so the framework never tries to
    create/destroy it; restored on teardown.
    """
    from django.conf import settings
    from django.db import connections

    from observatory.db import build_sim_database_alias

    had_before = "sim" in settings.DATABASES
    previous = dict(settings.DATABASES["sim"]) if had_before else None

    settings.DATABASES["sim"] = build_sim_database_alias(pg_dsn)
    if "settings" in connections.__dict__:
        del connections.__dict__["settings"]
    connections._settings = settings.DATABASES  # noqa: SLF001

    yield "sim"

    with contextlib.suppress(Exception):
        connections["sim"].close()
    if had_before and previous is not None:
        settings.DATABASES["sim"] = previous
    else:
        settings.DATABASES.pop("sim", None)
    if "settings" in connections.__dict__:
        del connections.__dict__["settings"]
    connections._settings = settings.DATABASES  # noqa: SLF001
