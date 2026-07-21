"""Per-county derivation/aggregation helpers for the spec-065 bridge.

Spec: 065-engine-bridging (T037, T037a, T038, T039).

The :class:`WorldStateBridge` calls four pure functions in this module
to assemble per-tick per-county subsystem state rows. Two are
engine-state aggregators (consciousness + survival), two are
reference-data fetchers (population + employment). See
``specs/065-engine-bridging/research.md §R10`` for the design
rationale: the bridge is a derivation adapter, not a flat
WorldState-to-table serializer.

Module is import-cycle-safe: depends on :mod:`babylon.models` (for
``WorldState`` + ``TernaryConsciousness``) and the stdlib ``sqlite3``.
Does NOT import from :mod:`babylon.engine.headless_runner` — the
bridge imports this module, not the other way around.

See Also:
    ``specs/065-engine-bridging/data-model.md §1.6``
    ``specs/065-engine-bridging/research.md §R10``
    ``specs/065-engine-bridging/contracts/subsystem_state_tables.yaml``
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Pure aggregation math RELOCATED to ``babylon.projection.aggregation``
# (Program 24 P2 WO-45 layering fix) — re-exported here unchanged so every
# existing bridge/persistence caller keeps its import path. New projection
# code imports from the new home directly.
from babylon.projection.aggregation import (
    _SIMPLEX_ASSERT_TOL as _SIMPLEX_ASSERT_TOL,  # noqa: PLC0414 — re-export
)
from babylon.projection.aggregation import (
    BridgeMappingError as BridgeMappingError,  # noqa: PLC0414 — re-export
)
from babylon.projection.aggregation import (
    _ideology_to_ternary as _ideology_to_ternary,  # noqa: PLC0414 — re-export
)
from babylon.projection.aggregation import (
    aggregate_consciousness_for_county as aggregate_consciousness_for_county,  # noqa: PLC0414 — re-export
)
from babylon.projection.aggregation import (
    aggregate_survival_for_county as aggregate_survival_for_county,  # noqa: PLC0414 — re-export
)

__all__ = [
    "BridgeMappingError",
    "ReferenceDataMissingError",
    "aggregate_consciousness_for_county",
    "aggregate_survival_for_county",
    "fetch_employment_proxy_for_county_at_tick",
    "fetch_population_for_county_at_tick",
]


class ReferenceDataMissingError(LookupError):
    """Raised when a (county_fips, year) tuple has no row in the relevant
    SQLite reference table. The FR-022 preflight at session init
    normally catches missing windows before the tick loop starts;
    this is a defensive last-line check for completeness."""


# ---------------------------------------------------------------------------
# SQLite reference-data fetchers
# ---------------------------------------------------------------------------


def _tick_to_year(tick: int, start_year: int) -> int:
    """Convert a (tick, start_year) pair to a calendar year.

    Weekly tick cadence: ``year = start_year + tick // 52``.
    """
    return start_year + tick // 52


def fetch_population_for_county_at_tick(
    sqlite_path: Path,
    county_fips: str,
    tick: int,
    start_year: int,
) -> int:
    """Per-county population for the calendar year at the given tick.

    Primary source: ``SUM(fact_census_income.household_count)`` for
    ``(county_id, year)``. The Census income table's per-bracket
    counts roll up to Census ACS county-population totals when summed
    across all (race, source, bracket) buckets — verified for Wayne
    County 2010 (1.77M vs ACS 1.82M actual).

    Fallback: if Census has no row for the (county, year), uses
    ``SUM(fact_qcew_annual.employment)`` × 0.33 (Wayne-calibrated
    employment-to-population ratio for industrialized US counties).

    Args:
        sqlite_path:  Path to ``marxist-data-3NF.sqlite``.
        county_fips:  5-digit FIPS code.
        tick:         Tick number; converted to year via weekly cadence.
        start_year:   Calendar year for tick 0.

    Returns:
        Non-negative integer population.

    Raises:
        ReferenceDataMissingError: If neither Census nor QCEW has data
            for the resolved (county, year).
        FileNotFoundError: If ``sqlite_path`` does not exist.
    """
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite reference DB not found: {sqlite_path}")

    year = _tick_to_year(tick, start_year)

    with sqlite3.connect(sqlite_path) as conn:
        # Primary: Census income aggregate.
        cur = conn.execute(
            """
            SELECT COALESCE(SUM(fci.household_count), 0)
            FROM fact_census_income fci
            JOIN dim_county dc ON dc.county_id = fci.county_id
            JOIN dim_time t ON t.time_id = fci.time_id
            WHERE dc.fips = ? AND t.year = ?
            """,
            (county_fips, year),
        )
        census_total = int(cur.fetchone()[0])
        if census_total > 0:
            return census_total

        # Fallback: QCEW employment × 0.33 (Wayne-calibrated ratio).
        cur = conn.execute(
            """
            SELECT COALESCE(SUM(fq.employment), 0)
            FROM fact_qcew_annual fq
            JOIN dim_county dc ON dc.county_id = fq.county_id
            JOIN dim_time t ON t.time_id = fq.time_id
            WHERE dc.fips = ? AND t.year = ?
            """,
            (county_fips, year),
        )
        qcew_emp = int(cur.fetchone()[0])
        if qcew_emp > 0:
            return int(qcew_emp * 0.33)

    raise ReferenceDataMissingError(
        f"No population data for county_fips={county_fips!r} year={year} "
        f"(checked fact_census_income then fact_qcew_annual fallback)"
    )


def fetch_employment_proxy_for_county_at_tick(
    sqlite_path: Path,
    county_fips: str,
    tick: int,
    start_year: int,
) -> float:
    """Annual-average per-county employment from QCEW.

    Formula: ``SUM(fact_qcew_annual.employment)`` over the canonical leaves
    for ``(county_id, year)``. Same data source as hex ``v`` (QCEW table;
    ``total_wages_usd → v``, ``employment → employment_proxy``).

    Spec-066 T058 / discovery: the QCEW `employment` column IS the BLS
    'annual average employment' (already aggregated across the 12 monthly
    snapshots). No divisor is needed — the legacy /52 and the spec's
    proposed /12 are both incorrect re-divisions of an already-averaged
    value.

    Post-spec-067 contract (see contracts/post_067_query_contract.md):
    ``fact_qcew_annual`` contains only canonical-leaf rows
    (``naics_level = 6`` × ``own_code ∈ {'1','2','3','5'}``) after the
    spec-067 DELETE migration. The natural SUM over those leaves recovers
    the BLS Total-Covered Total-Industries figure for the (county, year);
    no defensive filter is needed because the predicate is enforced at the
    data layer.

    Args:
        sqlite_path:  Path to ``marxist-data-3NF.sqlite``.
        county_fips:  5-digit FIPS code.
        tick:         Tick number; converted to year via weekly cadence.
        start_year:   Calendar year for tick 0.

    Returns:
        Non-negative float annual average employment (FTE-equivalent,
        BLS-publication granularity, no further division applied).

    Raises:
        ReferenceDataMissingError: If QCEW has no data for the
            resolved (county, year).
        FileNotFoundError: If ``sqlite_path`` does not exist.
    """
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite reference DB not found: {sqlite_path}")

    year = _tick_to_year(tick, start_year)

    with sqlite3.connect(sqlite_path) as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(SUM(fq.employment), 0)
            FROM fact_qcew_annual fq
            JOIN dim_county dc ON dc.county_id = fq.county_id
            JOIN dim_time t ON t.time_id = fq.time_id
            WHERE dc.fips = ? AND t.year = ?
            """,
            (county_fips, year),
        )
        qcew_emp = int(cur.fetchone()[0])

    if qcew_emp <= 0:
        raise ReferenceDataMissingError(
            f"No QCEW employment data for county_fips={county_fips!r} year={year}"
        )

    # Spec-066 T058: return as-is. The QCEW `employment` column already IS
    # the BLS annual-average. Earlier code's /52 and the spec's proposed
    # /12 are both incorrect re-divisions; the column is already averaged.
    return float(qcew_emp)
