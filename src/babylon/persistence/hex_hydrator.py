"""Hex graph hydration at session-init time.

Spec 063 closure + Spec 065 engine-bridging real-data rewrite
(T030-T035).

The hex hydrator runs once per session, writes tick-0 ``dynamic_hex_state``
rows for each county in the study area, and assembles per-hex Marx
primitives + substrate stocks + territory ratios from real reference
data in the SQLite knowledge base (``marxist-data-3NF.sqlite``).

Per spec-065 ``contracts/hex_hydrator_input.yaml`` (R7 in research.md),
the per-column source matrix is:

  - v: SUM(fact_qcew_annual.total_wages_usd) over industries / 52
  - c: GDP_county × intermediate_inputs_fraction / 52 (fraction = 0.5
       constant nationally; fact_bea_national_industry is empty in the
       current SQLite snapshot, so we use a defensible default).
  - s: max(0, GDP_county/52 - v - c); negative residual flagged via
       audit log (severity='warn').
  - k: capital_output_ratio × GDP_county_USD, with capital_output_ratio
       = 3.0 (BEA national fixed-asset accounts 2010).
  - surveillance_coupling: clip(0.3 + 0.4 × pct_100_20 +
       0.3 × facility_count_normalized, 0, 1)
  - internet_access_pct: pct_25_3 / 100
  - biocapacity_stock, energy_stock, raw_material_stock: defines
       defaults for now — fact_state_minerals is empty and dim_county
       has no land_area_sqmi column; per-county apportionment is
       deferred to a future spec that ingests those data sources.

Per-hex allocation: uniform within county (one county's per-county
values divided across its H3 res-7 cells). LODES-workplace-density
weighting is deferred to a future spec.

Units note: v + c + s + k now flow in **USD per week** (post spec-065),
not worker-equivalents like spec-063 first-cut. Downstream consumers
that compared c/v ratios remain unit-invariant; downstream consumers
that summed across regions get USD-consistent totals.

See Also:
    ``specs/065-engine-bridging/spec.md`` (FR-002a hex hydrator scope)
    ``specs/065-engine-bridging/contracts/hex_hydrator_input.yaml``
    ``specs/065-engine-bridging/research.md`` §R7
    :class:`babylon.persistence.hex_state.DynamicHexState`
    :func:`babylon.economics.substrate.h3_utils.generate_h3_cells`
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from babylon.economics.substrate.h3_utils import generate_h3_cells
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.state_fips_to_region import region_for_state_fips

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.persistence.protocols import RuntimePersistence
    from babylon.reference.bea.share_lookup_service import BEAShareLookupService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CalibrationAlarm:
    """Structured hydration-time alarm (spec-066 T020).

    Carried out-of-band from ``_fetch_per_county_data`` to allow the
    runner / bridge to convert into a full ``ConservationAuditRow`` once
    a session_id + determinism_hash are available at tick 0. The
    invariant_name + per-county details are stable identifiers.
    """

    invariant_name: str
    county_fips: str
    year: int
    gdp_per_week: float
    v_per_week: float
    residual: float  # = gdp_per_week - v_per_week (signed, negative)


# Default TIGER county shapefile shipped under data/tiger/county/.
_DEFAULT_TIGER_PATH = Path("data/tiger/county/tl_2024_us_county.shp")

# Default path to the SQLite reference DB.
_DEFAULT_SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")

# Weeks per year — canonical weekly tick cadence (spec-062 / 063).
_WEEKS_PER_YEAR = 52

# Intermediate-inputs fraction (constant capital share of GDP).
# Source: BEA national fixed-asset accounts 2010 baseline (c.f.
# fact_bea_national_industry which is empty in the current snapshot).
# A 0.5 fraction matches the BEA economy-wide average for total
# intermediate inputs / gross output.
#
# Spec-066 (Phase 0 R7 + T021): explicitly kept at the Shaikh-tractable
# economy-wide constant. Per-industry I-O refinement (BEA national
# table 5) is deferred to spec-068. The 0.5 share yields an organic
# composition c/v ≈ 1.0 at the BEA-broad v (QCEW total compensation),
# which is consistent with Shaikh's modern US empirical magnitudes
# (broad-measure c/v in [0.8, 1.2] for the 2000-2020 window).
_INTERMEDIATE_INPUTS_FRACTION = 0.5

# Capital-output ratio (k = ratio × annual GDP).
# Source: BEA national fixed-asset accounts 2010; private + government
# fixed assets / GDP ≈ 3.0.
_CAPITAL_OUTPUT_RATIO = 3.0

# Max coercive facility count across US counties (normalization
# denominator for surveillance_coupling).
# Source: max SUM(facility_count) over all counties in
# fact_coercive_infrastructure (verified 2026-05-15 = 66).
_MAX_COERCIVE_FACILITY_COUNT = 66

# BEA industry id for "All industries" total (bea_level = 1).
_BEA_ALL_INDUSTRIES_ID = 1


def hydrate_hex_state(
    *,
    runtime: RuntimePersistence,
    session_id: UUID,
    counties: frozenset[str],
    start_year: int,
    defines: GameDefines,
    tiger_county_shapefile: Path | None = None,
    sqlite_path: Path | None = None,
    bea_share_service: BEAShareLookupService | None = None,
) -> int:
    """Hydrate ``dynamic_hex_state`` for the study area at tick 0.

    Args:
        runtime: PostgresRuntime instance (provides ``_pool`` + ``persist_tick_atomic``).
        session_id: Active session UUID.
        counties: 5-digit FIPS codes for the study area
            (e.g., ``frozenset({"26163", "26125", "26099"})`` for Detroit tri-county).
        start_year: Year used to look up QCEW employment + BEA GDP totals.
        defines: ``GameDefines`` instance providing per-hex defaults for the
            substrate stocks (biocapacity/energy/raw_material) which lack
            per-county apportionment data in the current SQLite snapshot.
        tiger_county_shapefile: Optional override for the TIGER shapefile path.
        sqlite_path: Optional override for the SQLite reference DB path.
        bea_share_service: Optional ``BEAShareLookupService`` (spec-068 II.11
            contract). When provided, the per-county intermediate-inputs
            share is looked up from ``fact_bea_national_industry`` via the
            QCEW-employment-weighted concordance. When ``None``, falls back
            to the economy-wide 0.5 constant (FR-010 backward-compat with
            the spec-066/067 baseline).

    Returns:
        Total number of ``dynamic_hex_state`` rows persisted at tick 0.
    """
    if not counties:
        logger.info("hydrate_hex_state: empty county set; nothing to do")
        return 0

    sqlite_path_resolved = sqlite_path or _DEFAULT_SQLITE_PATH
    if not sqlite_path_resolved.exists():
        raise FileNotFoundError(
            f"SQLite reference DB not found at {sqlite_path_resolved}; "
            "hex hydrator requires real-data lookups (spec-065)."
        )

    # 1. Load county polygons (Postgres-resident or shapefile fallback).
    polygons = _load_county_polygons(
        counties=counties,
        runtime=runtime,
        shapefile_fallback=tiger_county_shapefile or _DEFAULT_TIGER_PATH,
    )

    # 2. Batch-fetch per-county economic + infrastructure data from SQLite.
    with sqlite3.connect(sqlite_path_resolved) as sql_conn:
        county_data = _fetch_per_county_data(
            conn=sql_conn,
            counties=counties,
            year=start_year,
            bea_share_service=bea_share_service,
        )
        # Spec-066 T065/T066/T067: per-county apportionment factors for
        # energy (population-weighted) and raw_material (area-weighted).
        # Returns dict[fips, (pop_factor, area_factor)] mean-normalized to 1.0.
        substrate_apportionment = _fetch_per_county_substrate_apportionment(
            conn=sql_conn,
            counties=counties,
            year=start_year,
        )

    # 3. Build per-hex DynamicHexState rows.
    hex_rows: list[DynamicHexState] = []
    for county_fips, polygon in polygons.items():
        cells = _polygons_to_hexes(polygon)
        if not cells:
            logger.warning(
                "hydrate_hex_state: county %s polyfill produced 0 cells",
                county_fips,
            )
            continue
        county_row = county_data.get(county_fips)
        if county_row is None:
            logger.warning(
                "hydrate_hex_state: county %s has no SQLite reference data "
                "for year=%d; emitting all-zero hex rows",
                county_fips,
                start_year,
            )
            county_row = _CountyRow.zero()

        hex_count = len(cells)
        # Per-hex per-week values (uniform allocation).
        v_per_hex = county_row.v_per_week / hex_count
        c_per_hex = county_row.c_per_week / hex_count
        s_per_hex = county_row.s_per_week / hex_count
        k_per_hex = county_row.k_total / hex_count
        # Spec-066 T066: substrate apportionment.
        # energy_stock follows POPULATION (where consumption + storage happens);
        # raw_material_stock follows AREA (where mining + extraction happens).
        pop_factor, area_factor = substrate_apportionment.get(county_fips, (1.0, 1.0))
        energy_per_hex = defines.territory.initial_energy_per_hex * pop_factor
        raw_material_per_hex = defines.territory.initial_raw_material_per_hex * area_factor
        state_fips = county_fips[:2]
        region_id = region_for_state_fips(state_fips)
        for h3_index in cells:
            hex_rows.append(
                DynamicHexState(
                    session_id=session_id,
                    tick=0,
                    h3_index=h3_index,
                    county_fips=county_fips,
                    state_fips=state_fips,
                    region_id=region_id,
                    c=c_per_hex,
                    v=v_per_hex,
                    s=s_per_hex,
                    k=k_per_hex,
                    biocapacity_stock=defines.territory.initial_biocapacity_per_hex,
                    energy_stock=energy_per_hex,
                    raw_material_stock=raw_material_per_hex,
                    internet_access_pct=county_row.internet_access_pct,
                    surveillance_coupling=county_row.surveillance_coupling,
                )
            )

    if not hex_rows:
        return 0

    # 4. Spec-088 S3 (FR-006): hex_spatial_map is the single stored copy
    # of the immutable hex → (county, state, region) mapping; per-tick hex
    # rows write NULL spatial keys (see _hex_row_dict). Populate the map
    # first so a hydrated session always resolves through it.
    _persist_hex_spatial_map(runtime, hex_rows)

    # 5. Persist atomically at tick 0. No commit marker (spec-089 FR-003):
    # the placeholder hash below is not part of the III.7 chain — the
    # bridge's tick-0 re-delivery writes the real tick_commit row.
    envelope = PerTickTransactionEnvelope(
        session_id=session_id,
        tick=0,
        hex_state_rows=hex_rows,
        determinism_hash="0" * 64,
    )
    runtime.persist_tick_atomic(envelope, write_commit_marker=False)  # type: ignore[attr-defined]
    logger.info(
        "hydrate_hex_state: persisted %d hex rows across %d counties for session %s",
        len(hex_rows),
        len(polygons),
        session_id,
    )
    return len(hex_rows)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


_HEX_SPATIAL_MAP_INSERT = """
INSERT INTO hex_spatial_map (session_id, h3_index, county_fips, state_fips, region_id)
VALUES (%(session_id)s, %(h3_index)s, %(county_fips)s, %(state_fips)s, %(region_id)s)
ON CONFLICT (session_id, h3_index) DO NOTHING
"""


def _persist_hex_spatial_map(runtime: Any, hex_rows: list[DynamicHexState]) -> None:
    """Idempotently record each hex's immutable spatial mapping (spec-088 FR-006).

    Session-scoped per migration 0028: each session has its own row set,
    so concurrent sessions can't wipe each other's spatial map.
    """
    pool = runtime._pool  # noqa: SLF001
    with pool.connection() as conn:
        conn.cursor().executemany(
            _HEX_SPATIAL_MAP_INSERT,
            [
                {
                    "session_id": row.session_id,
                    "h3_index": row.h3_index,
                    "county_fips": row.county_fips,
                    "state_fips": row.state_fips,
                    "region_id": row.region_id,
                }
                for row in hex_rows
            ],
        )


class _CountyRow:
    """Resolved per-county values for one tick-0 hydration pass.

    All Marx primitives are in USD per WEEK (post spec-065 unit switch);
    ``k_total`` is in USD as a stock (not a flow). Territory ratios are
    in [0, 1].
    """

    __slots__ = (
        "v_per_week",
        "c_per_week",
        "s_per_week",
        "k_total",
        "surveillance_coupling",
        "internet_access_pct",
    )

    def __init__(
        self,
        v_per_week: float,
        c_per_week: float,
        s_per_week: float,
        k_total: float,
        surveillance_coupling: float,
        internet_access_pct: float,
    ) -> None:
        self.v_per_week = v_per_week
        self.c_per_week = c_per_week
        self.s_per_week = s_per_week
        self.k_total = k_total
        self.surveillance_coupling = surveillance_coupling
        self.internet_access_pct = internet_access_pct

    @classmethod
    def zero(cls) -> _CountyRow:
        """All-zero fallback for counties with no reference data."""
        return cls(
            v_per_week=0.0,
            c_per_week=0.0,
            s_per_week=0.0,
            k_total=0.0,
            surveillance_coupling=defines_fallback_surveillance(),
            internet_access_pct=defines_fallback_internet(),
        )


def defines_fallback_surveillance() -> float:
    """Default surveillance_coupling for counties missing FCC data."""
    return 0.3


def defines_fallback_internet() -> float:
    """Default internet_access_pct for counties missing FCC data."""
    return 0.7


def _fetch_per_county_substrate_apportionment(
    *,
    conn: sqlite3.Connection,
    counties: frozenset[str],
    year: int,
    audit_alarms: list[_CalibrationAlarm] | None = None,
) -> dict[str, tuple[float, float]]:
    """Spec-066 T065/T066/T067: per-county (pop_factor, area_factor) apportionment.

    Returns a dict keyed by county FIPS with ``(pop_factor, area_factor)``
    where each factor is dimensionless and normalized so that
    ``mean(factor) == 1.0`` across the scope counties. Multiplying a
    per-hex substrate default by these factors yields the spec-066
    apportioned per-hex value (energy_stock uses pop_factor;
    raw_material_stock uses area_factor).

    Data sources (SQLite reference DB):
      - ``fact_census_income.population`` (preferred) → per-county population
      - ``dim_county_geometry.area_sq_km`` → per-county land area

    Fallbacks (graceful per T067):
      - If population is missing: pop_factor = 1.0 (uniform).
      - If area_sq_km is missing or zero: area_factor = pop_factor
        (degraded mode — area follows population), and a
        ``severity='warning'`` calibration alarm is appended.

    Args:
        conn:        Open SQLite connection.
        counties:    Set of 5-digit FIPS codes in scope.
        year:        Calendar year for population lookup.
        audit_alarms: Optional sink for warning alarms about missing area data.

    Returns:
        ``{fips: (pop_factor, area_factor)}`` keyed by FIPS.
    """
    if audit_alarms is None:
        audit_alarms = []
    fips_list = sorted(counties)
    placeholders = _placeholders(fips_list)

    # 1. Population per county (proxied by SUM(fact_census_income.household_count)
    #    summed across income brackets and races for the target year — mirrors
    #    babylon.persistence.county_aggregation.fetch_population_for_county_at_tick).
    pop_rows = conn.execute(
        f"""
        SELECT dc.fips, COALESCE(SUM(fci.household_count), 0)
        FROM fact_census_income fci
        JOIN dim_county dc ON dc.county_id = fci.county_id
        JOIN dim_time t ON t.time_id = fci.time_id
        WHERE dc.fips IN ({placeholders}) AND t.year = ?
        GROUP BY dc.fips
        """,
        (*fips_list, year),
    ).fetchall()
    population_by_fips = {fips: float(total or 0) for fips, total in pop_rows}

    # 2. Area per county (from dim_county_geometry; no time dimension).
    area_rows = conn.execute(
        f"""
        SELECT dc.fips, dcg.area_sq_km
        FROM dim_county_geometry dcg
        JOIN dim_county dc ON dc.county_id = dcg.county_id
        WHERE dc.fips IN ({placeholders})
        """,
        tuple(fips_list),
    ).fetchall()
    area_by_fips = {fips: float(area or 0) for fips, area in area_rows}

    # 3. Compute totals + apportionment factors (mean-normalized to 1.0).
    n_counties = len(counties) or 1
    total_pop = sum(population_by_fips.values()) or float(n_counties)
    total_area = sum(area_by_fips.values()) or float(n_counties)
    mean_pop = total_pop / n_counties
    mean_area = total_area / n_counties

    apportionment: dict[str, tuple[float, float]] = {}
    for fips in counties:
        pop = population_by_fips.get(fips, mean_pop)
        area = area_by_fips.get(fips, 0.0)
        pop_factor = (pop / mean_pop) if mean_pop > 0 else 1.0
        if area <= 0:
            # Graceful fallback per T067: area_factor follows pop_factor.
            area_factor = pop_factor
            audit_alarms.append(
                _CalibrationAlarm(
                    invariant_name="county_area_missing_falls_back_to_population",
                    county_fips=fips,
                    year=year,
                    gdp_per_week=0.0,
                    v_per_week=0.0,
                    residual=0.0,
                )
            )
        else:
            area_factor = (area / mean_area) if mean_area > 0 else 1.0
        apportionment[fips] = (pop_factor, area_factor)

    return apportionment


def _fetch_per_county_data(
    *,
    conn: sqlite3.Connection,
    counties: frozenset[str],
    year: int,
    audit_alarms: list[_CalibrationAlarm] | None = None,
    bea_share_service: BEAShareLookupService | None = None,
) -> dict[str, _CountyRow]:
    """Read per-county economic + infrastructure values for tick-0 seeding.

    Five SQLite tables consulted (per `contracts/hex_hydrator_input.yaml`):

      - fact_qcew_annual: SUM(total_wages_usd) over canonical leaves → v_per_week (/52)
        (post-spec-067: no filter needed; the table contains only naics_level=6
        × own_code in {'1','2','3','5'} rows by data-layer migration)
      - fact_bea_county_gdp + dim_bea_industry: GDP_county for the year
        (bea_industry_id = 1 = "All industries") → c_per_week + s_per_week + k_total
      - fact_broadband_coverage: pct_25_3, pct_100_20 → internet/surveillance
      - fact_coercive_infrastructure: SUM(facility_count) → surveillance

    Spec-068 T056: when ``bea_share_service`` is provided, the per-county
    intermediate-inputs share is looked up via the II.11 Protocol
    (QCEW-employment-weighted concordance → fact_bea_national_industry).
    When ``None``, the economy-wide 0.5 constant is used (FR-010
    backward-compat with the spec-066/067 baseline). The service's
    ``GLOBAL_FALLBACK_SHARE = 0.5`` ensures counties with no BEA data
    still get 0.5 — the pre-068 behavior is preserved end-to-end.

    Spec-066 T020: callers may pass an ``audit_alarms`` list to receive
    structured ``_CalibrationAlarm`` records for any county where the
    raw value-added residual ``GDP/52 - v`` is negative (commuter-wage
    boundary effect). The function still clamps ``s`` to 0 and logs a
    warning; the alarm list is the structured channel for downstream
    auditor / observability tooling.

    Returns:
        ``{county_fips: _CountyRow}`` for every county that has at
        least one of (QCEW, BEA, FCC) data. Counties with no data at
        all are absent from the returned dict; the caller emits a
        warning and uses _CountyRow.zero().
    """
    if audit_alarms is None:
        audit_alarms = []
    fips_list = sorted(counties)

    # 1. QCEW total_wages_usd per (county, year) — primary v source.
    #
    # Post-spec-067 contract (see contracts/post_067_query_contract.md):
    # fact_qcew_annual now contains only canonical-leaf rows
    # (naics_level=6 × own_code in {'1','2','3','5'}). The natural SUM over
    # those leaves recovers the BLS-publication Total Covered value for the
    # (county, year). No defensive filter is needed — the predicate is
    # enforced at the data layer by spec-067's DELETE migration.
    qcew_rows = conn.execute(
        f"""
        SELECT dc.fips, COALESCE(SUM(fq.total_wages_usd), 0) AS total_wages
        FROM fact_qcew_annual fq
        JOIN dim_county dc ON dc.county_id = fq.county_id
        JOIN dim_time t ON t.time_id = fq.time_id
        WHERE dc.fips IN ({_placeholders(fips_list)})
          AND t.year = ?
        GROUP BY dc.fips
        """,
        (*fips_list, year),
    ).fetchall()
    qcew_wages_by_fips = {fips: float(total or 0) for fips, total in qcew_rows}

    # 2. BEA GDP (All industries) per (county, year).
    bea_rows = conn.execute(
        f"""
        SELECT dc.fips, fbg.gdp_millions
        FROM fact_bea_county_gdp fbg
        JOIN dim_county dc ON dc.county_id = fbg.county_id
        JOIN dim_time t ON t.time_id = fbg.time_id
        WHERE dc.fips IN ({_placeholders(fips_list)})
          AND t.year = ? AND fbg.bea_industry_id = ?
        """,
        (*fips_list, year, _BEA_ALL_INDUSTRIES_ID),
    ).fetchall()
    bea_gdp_by_fips = {fips: float(gdp_millions or 0) * 1e6 for fips, gdp_millions in bea_rows}

    # 3. FCC broadband (cross-section — no time dimension).
    broadband_rows = conn.execute(
        f"""
        SELECT dc.fips, fbc.pct_25_3, fbc.pct_100_20
        FROM fact_broadband_coverage fbc
        JOIN dim_county dc ON dc.county_id = fbc.county_id
        WHERE dc.fips IN ({_placeholders(fips_list)})
        """,
        tuple(fips_list),
    ).fetchall()
    broadband_by_fips = {
        fips: (float(p25 or 0), float(p100 or 0)) for fips, p25, p100 in broadband_rows
    }

    # 4. Coercive infrastructure facility counts (cross-section).
    coercive_rows = conn.execute(
        f"""
        SELECT dc.fips, COALESCE(SUM(fci.facility_count), 0) AS facility_total
        FROM fact_coercive_infrastructure fci
        JOIN dim_county dc ON dc.county_id = fci.county_id
        WHERE dc.fips IN ({_placeholders(fips_list)})
        GROUP BY dc.fips
        """,
        tuple(fips_list),
    ).fetchall()
    coercive_by_fips = {fips: int(total or 0) for fips, total in coercive_rows}

    # Assemble per-county rows.
    result: dict[str, _CountyRow] = {}
    for fips in counties:
        v_per_week = qcew_wages_by_fips.get(fips, 0.0) / _WEEKS_PER_YEAR
        gdp_usd = bea_gdp_by_fips.get(fips, 0.0)
        # c = GDP × intermediate-inputs-share (weekly). Spec-068 T056:
        # when a BEAShareLookupService is provided, the per-county share
        # comes from the QCEW-employment-weighted BEA national I-O
        # concordance (II.11 Protocol). When None, the economy-wide 0.5
        # constant is used (FR-010 backward-compat).
        if bea_share_service is not None:
            share_result = bea_share_service.lookup_county_share(county_fips=fips, year=year)
            ii_share = share_result.intermediate_inputs_share
        else:
            ii_share = _INTERMEDIATE_INPUTS_FRACTION
        c_per_week = gdp_usd * ii_share / _WEEKS_PER_YEAR
        # s = max(0, GDP/52 - v). Spec-066 T018: the value-added identity
        # is GDP = v + s (Marx Vol I Ch 9 + BEA accounting). Earlier code
        # subtracted c as well, which double-counts the constant-capital
        # pass-through (c is intermediate inputs that flow THROUGH the
        # production process; they are NOT subtracted from value-added).
        gdp_per_week = gdp_usd / _WEEKS_PER_YEAR
        s_raw = gdp_per_week - v_per_week
        if s_raw < 0:
            # Spec-066 T020: emit a structured calibration alarm in
            # addition to the human-readable log line. The runner / bridge
            # picks these up from `_fetch_per_county_data`'s return tuple
            # and forwards them to the ConservationAuditor at tick 0.
            audit_alarms.append(
                _CalibrationAlarm(
                    invariant_name="s_residual_negative",
                    county_fips=fips,
                    year=year,
                    gdp_per_week=gdp_per_week,
                    v_per_week=v_per_week,
                    residual=s_raw,
                )
            )
            logger.warning(
                "hex_hydrator: negative s for county=%s year=%d "
                "(GDP/52=%.0f, v=%.0f, s=%.0f); clamping to 0. "
                "Calibration alarm emitted as s_residual_negative.",
                fips,
                year,
                gdp_per_week,
                v_per_week,
                s_raw,
            )
        s_per_week = max(0.0, s_raw)
        # k = capital_output_ratio × annual GDP.
        k_total = _CAPITAL_OUTPUT_RATIO * gdp_usd

        # Territory ratios from FCC + coercive (or fallback defaults).
        pct_25_3, pct_100_20 = broadband_by_fips.get(fips, (None, None))
        if pct_25_3 is None or pct_100_20 is None:
            internet_pct = defines_fallback_internet()
            broadband_norm = 0.0
        else:
            internet_pct = pct_25_3 / 100.0
            broadband_norm = pct_100_20 / 100.0
        facility_count = coercive_by_fips.get(fips, 0)
        facility_norm = min(1.0, facility_count / _MAX_COERCIVE_FACILITY_COUNT)
        surveillance = min(
            1.0,
            max(0.0, 0.3 + 0.4 * broadband_norm + 0.3 * facility_norm),
        )

        result[fips] = _CountyRow(
            v_per_week=v_per_week,
            c_per_week=c_per_week,
            s_per_week=s_per_week,
            k_total=k_total,
            surveillance_coupling=surveillance,
            internet_access_pct=internet_pct,
        )
    return result


def _placeholders(items: list[str]) -> str:
    """Build a comma-separated ``?`` placeholder list for SQLite IN."""
    return ", ".join("?" for _ in items)


def _load_county_polygons(
    *,
    counties: frozenset[str],
    runtime: RuntimePersistence,
    shapefile_fallback: Path,
) -> dict[str, object]:
    """Return ``{fips: shapely_geometry}`` for the requested counties.

    Preferred path: query ``immutable_reference_tiger_county`` for the
    Postgres-resident WKT representation populated by
    :func:`babylon.persistence.tiger_ingestion.ingest_tiger_counties`.
    Reproducible across deployments because the source of truth is the
    Postgres row, not a transient shapefile read.

    Fallback path: if the Postgres table is empty or missing entries
    for the requested counties, read directly from the TIGER shapefile.
    A warning is emitted so the operator can run the ingestion CLI.
    """
    import shapely.wkt  # type: ignore[import-untyped]

    from babylon.persistence.tiger_ingestion import fetch_county_geometries_wkt

    pool = runtime._pool  # type: ignore[attr-defined]  # noqa: SLF001
    wkt_by_geoid = fetch_county_geometries_wkt(pool, counties)
    polygons: dict[str, object] = {
        geoid: shapely.wkt.loads(wkt) for geoid, wkt in wkt_by_geoid.items()
    }
    missing = counties - polygons.keys()
    if not missing:
        return polygons

    logger.warning(
        "hex_hydrator: %d counties missing from immutable_reference_tiger_county "
        "(%s); falling back to shapefile read at %s. "
        "Run `python -m babylon.persistence.tiger_ingestion` to make this "
        "lookup fully Postgres-resident.",
        len(missing),
        sorted(missing),
        shapefile_fallback,
    )
    if not shapefile_fallback.exists():
        raise FileNotFoundError(
            f"TIGER county shapefile not found at {shapefile_fallback}; "
            f"missing counties: {sorted(missing)}"
        )

    import geopandas as gpd  # type: ignore[import-untyped]

    gdf = gpd.read_file(shapefile_fallback, columns=["GEOID", "geometry"])
    gdf = gdf[gdf["GEOID"].isin(missing)]
    for _, row in gdf.iterrows():
        polygons[row["GEOID"]] = row["geometry"]
    return polygons


def _polygons_to_hexes(polygon: object) -> set[str]:
    """Convert a Shapely (Multi)Polygon to a set of H3 res-7 cells."""
    return generate_h3_cells(polygon, resolution=7)


__all__ = ["hydrate_hex_state"]
