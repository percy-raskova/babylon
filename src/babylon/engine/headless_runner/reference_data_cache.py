"""Per-bridge reference-data cache for the spec-066 bridged headless runner.

Spec: 069-sqlite-cache-optimization.

The spec-066-bridged headless runner's ``persist_tick`` step opens fresh
``sqlite3.Connection`` instances per ``(county, tick)`` for two
reference-data lookups (population, employment-proxy). The returned
values are invariant within a calendar year, so under the weekly
cadence (``year = start_year + tick // 52``) the same fetch is
re-executed 51 redundant times before the year rolls over.

This module lifts those reads out of the per-tick path into a
hydrate-once, year-keyed cache resident on the bridge instance. At
``WorldStateBridge.hydrate_initial`` time, the cache issues three
batched SQL queries against ``data/sqlite/marxist-data-3NF.sqlite``
under a single connection (Census primary, QCEW fallback for
Census-missing tuples, QCEW employment) — collectively touching
each ``(county_fips, year)`` tuple in scope exactly once. Every
``persist_tick`` thereafter reads from the in-memory dict; no new
SQLite connection is opened on the per-tick path.

See Also:
    ``specs/069-sqlite-cache-optimization/spec.md`` — feature spec.
    ``specs/069-sqlite-cache-optimization/contracts/reference_data_cache_contract.md``
        — cache class contract.
    ``specs/069-sqlite-cache-optimization/contracts/instrumentation_contract.md``
        — bridge read-counter contract.
    ``specs/069-sqlite-cache-optimization/data-model.md`` — entity inventory.
    ``specs/069-sqlite-cache-optimization/research.md`` — design decisions
        (R1-R11).
    :mod:`babylon.persistence.county_aggregation` — the legacy fetchers
        whose values the cache memoizes; unchanged per spec-069 R10
        (II.11 subsystem ownership).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ReferenceCacheEntry",
    "derive_year_set",
]


def derive_year_set(start_year: int, total_ticks: int) -> frozenset[int]:
    """Enumerate the calendar years touched by a ``total_ticks``-tick run.

    Under the weekly cadence (``year = start_year + tick // 52``) the
    in-scope year set is mechanical:

        derive_year_set(start_year, total_ticks) =
            {start_year + i // 52 : i in [0, total_ticks - 1]}
            = {start_year, ..., start_year + (total_ticks - 1) // 52}

    Args:
        start_year:  Calendar year for tick 0.
        total_ticks: Number of ticks in the run.

    Returns:
        Frozen set of distinct calendar years touched. Empty for
        ``total_ticks <= 0`` (degenerate zero-tick run; spec-069
        Edge Cases).

    Example:
        >>> derive_year_set(2010, 520)
        frozenset({2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020})
        >>> derive_year_set(2010, 0)
        frozenset()
        >>> derive_year_set(2010, 53)
        frozenset({2010, 2011})
    """
    if total_ticks <= 0:
        return frozenset()
    last_year = start_year + (total_ticks - 1) // 52
    return frozenset(range(start_year, last_year + 1))


class ReferenceCacheEntry(BaseModel):
    """One ``(county_fips, year)`` tuple's cached reference data.

    ``population`` and ``employment_proxy`` are independently nullable:
    Census and QCEW data coverage is asymmetric (see R2 in
    ``specs/069-sqlite-cache-optimization/research.md``). The four
    combinations ``{(present, present), (present, None), (None, present),
    (None, None)}`` are all legitimate empirical states.

    Frozen: once constructed at hydrate time, never mutated.
    """

    model_config = ConfigDict(frozen=True)

    population: int | None = Field(default=None, ge=0)
    employment_proxy: float | None = Field(default=None, ge=0.0)
