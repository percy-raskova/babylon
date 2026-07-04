"""Integration fixtures for the Observatory (spec-096, Postgres-gated).

Seeds a UNIQUE session into the simulation Postgres via the real persistence
path (``select_hex_rows_for_emission`` -> ``persist_tick_atomic``, which writes
``dynamic_hex_state`` deltas + a ``tick_commit`` row per tick), then registers
the Django ``sim`` alias pointing at that same database so the Observatory's
``connections["sim"]`` reads the seeded data.

Two properties that matter for the review-hardened tests:

* **Genuinely sparse** — the value schedule leaves at least one hex UNCHANGED
  for a tick, so ``hex_rows_written < total_hexes`` and one tick writes ZERO
  hex rows. Reading that tick exercises the ``v_hex_state_asof`` fill-forward
  carry-forward path (the II.11 / CLAUDE.md sparse-hex gotcha).
* **Spatially resolvable** — spec-088 S3 persists hex spatial keys as NULL in
  ``dynamic_hex_state`` (the single copy lives in ``hex_spatial_map``), so the
  fixture SEEDS ``hex_spatial_map`` for its (session-unique) h3 indices. Without
  this the county/state aggregate views group everything under NULL.

Isolation is per-session (uuid4); partitions and the seeded ``hex_spatial_map``
rows are removed on teardown. Skips cleanly when Postgres is unavailable (via
the session-scoped ``pg_pool`` fixture from the root conftest).
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.integration

_COUNTY = "26163"
_STATE = "26"
_REGION = "east_north_central"
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
    h3_a: str
    h3_b: str
    #: hex rows actually written per tick — sparse: checkpoint frame then
    #: single-hex deltas then a pure carry-forward tick (0 rows).
    expected_rows_written: tuple[int, ...]
    #: reconstructed v per hex at ``max_tick`` (carried forward from deltas).
    carry_v: dict[str, float]


def _hex_row(session: UUID, tick: int, h3: str, v: float) -> Any:
    """One hex row — only ``v`` varies across the schedule; the rest are fixed,
    so a tick that does not change ``v`` re-emits nothing (sparse)."""
    from babylon.persistence.hex_state import DynamicHexState

    return DynamicHexState(
        session_id=session,
        tick=tick,
        h3_index=h3,
        county_fips=_COUNTY,
        state_fips=_STATE,
        region_id=_REGION,
        c=10.0,
        v=v,
        s=3.0,
        k=100.0,
        biocapacity_stock=20.0,
        energy_stock=10.0,
        raw_material_stock=5.0,
        internet_access_pct=0.85,
        surveillance_coupling=0.4,
    )


@pytest.fixture(scope="session")
def _sim_migrated(pg_pool: Any) -> Any:
    """Apply the runner's idempotent migrations once (views + tick_commit)."""
    from babylon.engine.headless_runner.runner import _apply_migrations

    _apply_migrations(pg_pool)
    return pg_pool


@pytest.fixture
def seeded_session(_sim_migrated: Any) -> Generator[SeededSession, None, None]:
    """Seed a unique, genuinely-sparse 4-tick session; clean up on teardown."""
    from babylon.persistence.delta import select_hex_rows_for_emission
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.partitioning import drop_session_partitions, ensure_session_partitions
    from babylon.persistence.postgres_runtime import PostgresRuntime

    pool = _sim_migrated
    session = uuid4()
    # Session-unique h3 indices (never collide with real hex_spatial_map rows).
    h3_a = session.hex[:15]
    h3_b = session.hex[15:30]
    # Sparse value schedule (only v changes; everything else is constant):
    #   tick 0 (checkpoint): both emitted        -> 2 rows
    #   tick 1: A changes 5->6, B unchanged      -> 1 row
    #   tick 2: A unchanged, B changes 5->7      -> 1 row
    #   tick 3: neither changes                  -> 0 rows (pure carry-forward)
    schedule = {h3_a: [5.0, 6.0, 6.0, 6.0], h3_b: [5.0, 5.0, 7.0, 7.0]}

    ensure_session_partitions(pool=pool, session_id=session)
    _seed_spatial_map(pool, [h3_a, h3_b])
    runtime = PostgresRuntime(pool=pool)

    last_emitted: dict[str, tuple[float, ...]] = {}
    try:
        for tick in range(_TICKS):
            frame = [_hex_row(session, tick, h3, schedule[h3][tick]) for h3 in (h3_a, h3_b)]
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
            h3_a=h3_a,
            h3_b=h3_b,
            expected_rows_written=(2, 1, 1, 0),
            carry_v={h3_a: 6.0, h3_b: 7.0},
        )
    finally:
        with contextlib.suppress(Exception):
            drop_session_partitions(pool=pool, session_id=session)
        with contextlib.suppress(Exception):
            _unseed_spatial_map(pool, [h3_a, h3_b])


def _seed_spatial_map(pool: Any, h3s: list[str]) -> None:
    """Insert the fixture's h3 -> county/state mapping (spec-088 source of truth)."""
    with pool.connection() as conn:
        conn.autocommit = True
        for h3 in h3s:
            conn.execute(
                "INSERT INTO hex_spatial_map (h3_index, county_fips, state_fips, region_id) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (h3_index) DO UPDATE SET "
                "county_fips = EXCLUDED.county_fips, state_fips = EXCLUDED.state_fips, "
                "region_id = EXCLUDED.region_id",
                (h3, _COUNTY, _STATE, _REGION),
            )


def _unseed_spatial_map(pool: Any, h3s: list[str]) -> None:
    with pool.connection() as conn:
        conn.autocommit = True
        conn.execute("DELETE FROM hex_spatial_map WHERE h3_index = ANY(%s)", (h3s,))


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
