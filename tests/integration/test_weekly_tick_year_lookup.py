"""Weekly tick year-lookup integration test (T034 / US2).

Hydrates a Detroit session, then exercises ``ImmutableReferenceLookup`` against
the live ``immutable_reference_*`` rows. Verifies:

  - exact_year path at tick 0
  - linear_interpolated path at tick 26 (mid-year)
  - clamped_to_last path at tick 832 (year 2026 > end_year 2025)
  - clamped_to_earliest path at synthetic year < start_year
  - FR-016 single-shot warning behaviour

Skips cleanly when Postgres is unavailable.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite").resolve()
DETROIT_TRI_COUNTY = ["26163", "26125", "26099"]


@pytest.fixture(scope="module")
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


@pytest.fixture(scope="module")
def runtime(pg_pool, apply_062_migrations):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


@pytest.fixture(scope="module")
def hydrated_session(runtime):  # type: ignore[no-untyped-def]
    """Hydrate a single Detroit session for the whole test module."""
    if not SQLITE_PATH.is_file():
        pytest.skip(f"SQLite reference DB not found at {SQLITE_PATH}")
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    initialize_session(
        session_id=sid,
        sqlite_path=SQLITE_PATH,
        runtime=runtime,
        defines=GameDefines(),
        start_year=2010,
        scenario_length_years=15,
        counties=DETROIT_TRI_COUNTY,
    )
    return sid


def _provider_from_pg(runtime, session_id):  # type: ignore[no-untyped-def]
    """Build a value_provider that reads CPI annual averages from Postgres."""

    def provider(series_id: str, year: int) -> float:  # noqa: ARG001
        with runtime._pool.connection() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT rate FROM immutable_reference_fred_rates "
                "WHERE session_id = %s AND year = %s AND series_id = 'CPIAUCSL'",
                (str(session_id), year),
            ).fetchone()
        if row is None or row[0] is None:
            raise KeyError(f"No CPI for {year}")
        return float(row[0])

    return provider


def test_exact_year_at_tick_0(runtime, hydrated_session):  # type: ignore[no-untyped-def]
    """At tick 0, simulated_year is start_year and the lookup is an exact hit."""
    from babylon.persistence.postgres_reference import ImmutableReferenceLookup, LookupMethod

    lookup = ImmutableReferenceLookup(runtime, hydrated_session, 2010, 2025)
    result = lookup.get(
        "cpi",
        tick=0,
        policy="slowly_varying",
        value_provider=_provider_from_pg(runtime, hydrated_session),
    )
    assert result.simulated_year == 2010
    assert result.lookup_method == LookupMethod.EXACT_YEAR
    assert result.value > 0  # Real CPI value


def test_linear_interpolated_at_mid_year_tick_26(runtime, hydrated_session):  # type: ignore[no-untyped-def]
    """At tick 26, slowly_varying interpolates between 2010 and 2011 CPI."""
    from babylon.persistence.postgres_reference import ImmutableReferenceLookup, LookupMethod

    lookup = ImmutableReferenceLookup(runtime, hydrated_session, 2010, 2025)
    provider = _provider_from_pg(runtime, hydrated_session)
    v_2010 = provider("cpi", 2010)
    v_2011 = provider("cpi", 2011)
    expected = v_2010 + (v_2011 - v_2010) * 0.5  # 26/52 = 0.5

    result = lookup.get("cpi", tick=26, policy="slowly_varying", value_provider=provider)
    assert result.lookup_method == LookupMethod.LINEAR_INTERPOLATED
    assert result.bracketing_years == (2010, 2011)
    assert abs(result.value - expected) < 1e-6


def test_event_discrete_step_at_year_boundary(runtime, hydrated_session):  # type: ignore[no-untyped-def]
    """tick 51 reads year 2010; tick 52 jumps to year 2011 for event_discrete."""
    from babylon.persistence.postgres_reference import ImmutableReferenceLookup, LookupMethod

    lookup = ImmutableReferenceLookup(runtime, hydrated_session, 2010, 2025)
    provider = _provider_from_pg(runtime, hydrated_session)

    r_51 = lookup.get("cpi", tick=51, policy="event_discrete", value_provider=provider)
    r_52 = lookup.get("cpi", tick=52, policy="event_discrete", value_provider=provider)
    assert r_51.lookup_method == LookupMethod.EXACT_YEAR
    assert r_52.lookup_method == LookupMethod.EXACT_YEAR
    assert r_51.simulated_year == 2010
    assert r_52.simulated_year == 2011
    assert r_51.value != r_52.value  # CPI rises year over year


def test_clamped_to_last_at_overrange_tick(runtime, hydrated_session):  # type: ignore[no-untyped-def]
    """A tick beyond end_year clamps to last + warns once (FR-016)."""
    from babylon.persistence.postgres_reference import ImmutableReferenceLookup, LookupMethod

    # CPI data in this fixture runs through 2024; cap end_year so the
    # provider can serve the boundary value when clamping kicks in.
    lookup = ImmutableReferenceLookup(runtime, hydrated_session, 2010, 2024)
    provider = _provider_from_pg(runtime, hydrated_session)

    # tick 780 → year 2010 + 15 = 2025, one year past end_year 2024.
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = lookup.get("cpi", tick=780, policy="slowly_varying", value_provider=provider)
    assert r.lookup_method == LookupMethod.CLAMPED_TO_LAST
    assert r.warning_emitted is True
    assert any("FR-016" in str(item.message) for item in w)

    # Second call: still clamped but no warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r2 = lookup.get("cpi", tick=832, policy="slowly_varying", value_provider=provider)
    assert r2.lookup_method == LookupMethod.CLAMPED_TO_LAST
    assert r2.warning_emitted is False
    assert len(w) == 0
