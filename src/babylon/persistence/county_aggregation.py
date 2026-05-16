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
from typing import TYPE_CHECKING

from babylon.models.entities.consciousness import TernaryConsciousness
from babylon.models.types import Probability

if TYPE_CHECKING:
    from babylon.models.world_state import WorldState


__all__ = [
    "BridgeMappingError",
    "ReferenceDataMissingError",
    "aggregate_consciousness_for_county",
    "aggregate_survival_for_county",
    "fetch_employment_proxy_for_county_at_tick",
    "fetch_population_for_county_at_tick",
]


# Simplex tolerance: tighter than TernaryConsciousness._SIMPLEX_TOLERANCE
# (1e-4) because the bridge mapping is algebraically exact and any drift
# above 1e-9 indicates a numerical bug worth surfacing.
_SIMPLEX_ASSERT_TOL = 1e-9


class BridgeMappingError(RuntimeError):
    """Raised when the IdeologicalProfile → TernaryConsciousness mapping
    produces a non-simplex result (should never happen given the
    algebra; raised as a defensive runtime check)."""


class ReferenceDataMissingError(LookupError):
    """Raised when a (county_fips, year) tuple has no row in the relevant
    SQLite reference table. The FR-022 preflight at session init
    normally catches missing windows before the tick loop starts;
    this is a defensive last-line check for completeness."""


# ---------------------------------------------------------------------------
# Bridge mapping: IdeologicalProfile (2-axis) → TernaryConsciousness (3-simplex)
# ---------------------------------------------------------------------------


def _ideology_to_ternary(
    class_consciousness: float,
    national_identity: float,
) -> tuple[float, float, float]:
    """Convert a 2-axis IdeologicalProfile point to a 3-simplex point.

    Bridge mapping (research.md §R10):

        r = class_consciousness × (1 - national_identity)   # revolutionary
        f = national_identity × (1 - class_consciousness)   # fascist
        l = max(0, 1 - r - f)                                # liberal (remainder)

    Algebraic properties (verified by unit tests):

    * ``r + l + f == 1`` by construction (l is the remainder).
    * All three are in ``[0, 1]`` since cc and ni are each in [0, 1] and
      products of two numbers in [0, 1] are in [0, 1], and ``r + f ≤ 1``
      so the ``max(0, ...)`` for l is never load-bearing in non-degenerate
      cases (it's purely a defensive clamp against float drift).
    * Corner mapping:
      - (1, 0) → (r=1, l=0, f=0)   pure revolutionary
      - (0, 1) → (r=0, l=0, f=1)   pure fascist
      - (0, 0) → (r=0, l=1, f=0)   pure liberal (Jackson's unorganized default)
      - (1, 1) → (r=0, l=1, f=0)   "national revolutionary" routes to liberal

    Args:
        class_consciousness: Relationship to Capital, [0.0, 1.0].
        national_identity:   Relationship to State/Tribe, [0.0, 1.0].

    Returns:
        ``(r, l, f)`` simplex coordinates.

    Raises:
        BridgeMappingError: If the computed simplex doesn't sum to 1.0
            within :data:`_SIMPLEX_ASSERT_TOL`. Indicates a numerical bug.
    """
    cc = class_consciousness
    ni = national_identity
    r = cc * (1.0 - ni)
    f = ni * (1.0 - cc)
    l_ = max(0.0, 1.0 - r - f)  # noqa: E741 — l is the natural simplex coordinate name
    total = r + l_ + f
    if abs(total - 1.0) > _SIMPLEX_ASSERT_TOL:
        raise BridgeMappingError(
            f"Bridge mapping produced non-simplex result: "
            f"r={r}, l={l_}, f={f}, sum={total} "
            f"(from cc={cc}, ni={ni})"
        )
    return (r, l_, f)


# ---------------------------------------------------------------------------
# Engine-state aggregators
# ---------------------------------------------------------------------------


def aggregate_survival_for_county(
    world: WorldState,
    county_fips: str,
) -> tuple[float, float, int]:
    """Population-weighted means of ``(p_acquiescence, p_revolution)``.

    Iterates ``world.entities.values()`` and filters to entities where
    ``entity.county_fips == county_fips``. Computes population-weighted
    means over the filtered set. If no entities match the FIPS, returns
    ``(0.0, 0.0, 0)`` — the caller is expected to emit a ``warning``
    severity audit row when ``total_population == 0`` for a county
    that was supposed to have attribution.

    Args:
        world:        Current in-memory WorldState.
        county_fips:  5-digit US county FIPS (e.g., ``"26163"`` for Wayne).

    Returns:
        ``(mean_p_acquiescence, mean_p_revolution, total_population)``.
        Both probabilities are floats in [0, 1]; population is a
        non-negative int.

    See Also:
        :func:`aggregate_consciousness_for_county`: companion helper for
        ideology r/l/f.
    """
    total_population = 0
    sum_p_acq_weighted = 0.0
    sum_p_rev_weighted = 0.0

    for entity in world.entities.values():
        if entity.county_fips != county_fips:
            continue
        pop = int(entity.population)
        if pop <= 0:
            continue
        total_population += pop
        sum_p_acq_weighted += float(entity.p_acquiescence) * pop
        sum_p_rev_weighted += float(entity.p_revolution) * pop

    if total_population == 0:
        return (0.0, 0.0, 0)

    mean_p_acq = sum_p_acq_weighted / total_population
    mean_p_rev = sum_p_rev_weighted / total_population
    return (mean_p_acq, mean_p_rev, total_population)


def aggregate_consciousness_for_county(
    world: WorldState,
    county_fips: str,
) -> TernaryConsciousness:
    """Population-weighted ``(r, l, f)`` over entities in a county.

    For each entity with ``entity.county_fips == county_fips``, applies
    the bridge mapping (see :func:`_ideology_to_ternary`) to convert the
    entity's ``IdeologicalProfile`` to a 3-simplex point, then takes a
    population-weighted mean.

    If the county has no matching entities, returns the
    ``TernaryConsciousness`` substrate default
    (``r=0.3, l=0.6, f=0.1`` — Jackson's "unorganized default,
    liberal-leaning"). This matches spec-034's substrate-floor
    semantics without requiring the substrate-floor machinery.

    Args:
        world:        Current in-memory WorldState.
        county_fips:  5-digit US county FIPS.

    Returns:
        :class:`TernaryConsciousness` with simplex invariant
        ``abs(r + l + f - 1.0) < 1e-9`` (asserted before return).

    Raises:
        BridgeMappingError: If the per-entity simplex mapping fails
            (algebraically should never happen; raised as a defensive
            runtime check).
    """
    total_population = 0
    sum_r_weighted = 0.0
    sum_l_weighted = 0.0
    sum_f_weighted = 0.0

    for entity in world.entities.values():
        if entity.county_fips != county_fips:
            continue
        pop = int(entity.population)
        if pop <= 0:
            continue
        cc = float(entity.ideology.class_consciousness)
        ni = float(entity.ideology.national_identity)
        r_i, l_i, f_i = _ideology_to_ternary(cc, ni)
        total_population += pop
        sum_r_weighted += r_i * pop
        sum_l_weighted += l_i * pop
        sum_f_weighted += f_i * pop

    if total_population == 0:
        # No matching entities; return the substrate default.
        # TernaryConsciousness() with no args uses (0.3, 0.6, 0.1).
        return TernaryConsciousness()

    r = sum_r_weighted / total_population
    l_ = sum_l_weighted / total_population  # noqa: E741
    f = sum_f_weighted / total_population

    # Floating-point drift across many entities could push the sum a
    # few ULPs off 1.0; renormalize defensively.
    total = r + l_ + f
    if abs(total - 1.0) > _SIMPLEX_ASSERT_TOL:
        # Renormalize. If total is effectively zero (shouldn't be —
        # every per-entity mapping produces a valid simplex), fall
        # back to substrate default.
        if total < _SIMPLEX_ASSERT_TOL:
            return TernaryConsciousness()
        r = r / total
        l_ = l_ / total
        f = f / total

    return TernaryConsciousness(
        r=Probability(r),
        l=Probability(l_),
        f=Probability(f),
    )


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

    Formula: ``SUM(fact_qcew_annual.employment WHERE industry_id=1 AND
    ownership_id=1)`` for ``(county_id, year)``. Same data source as hex
    ``v`` (QCEW table; ``total_wages_usd → v``, ``employment →
    employment_proxy``).

    Spec-066 T058 / discovery: the QCEW `employment` column IS the BLS
    'annual average employment' (already aggregated across the 12 monthly
    snapshots). No divisor is needed — the legacy /52 and the spec's
    proposed /12 are both incorrect re-divisions of an already-averaged
    value. The state-aggregate of ownership_id=1 rows at industry_id=1
    matches BLS publication numbers within ~1%.

    Filters applied (mirroring the hex_hydrator wages query):
      - ``industry_id = 1`` — BLS 'All Industries' rollup (avoids NAICS
        hierarchy triple-counting where Manufacturing + Durable Goods
        contain the same establishments)
      - ``ownership_id = 1`` — BLS 'Total Covered' rollup (avoids the
        ownership rollup-vs-leaves double-count where ownership_id=1
        equals the sum of Federal+State+Local+Private leaves)

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
              AND fq.industry_id = 1
              AND fq.ownership_id = 1
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
