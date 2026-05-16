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
from typing import TYPE_CHECKING
from uuid import UUID

from babylon.economics.substrate.h3_utils import generate_h3_cells
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.state_fips_to_region import region_for_state_fips

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.persistence.protocols import RuntimePersistence

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
                    energy_stock=defines.territory.initial_energy_per_hex,
                    raw_material_stock=defines.territory.initial_raw_material_per_hex,
                    internet_access_pct=county_row.internet_access_pct,
                    surveillance_coupling=county_row.surveillance_coupling,
                )
            )

    if not hex_rows:
        return 0

    # 4. Persist atomically at tick 0.
    envelope = PerTickTransactionEnvelope(
        session_id=session_id,
        tick=0,
        hex_state_rows=hex_rows,
        determinism_hash="0" * 64,
    )
    runtime.persist_tick_atomic(envelope)  # type: ignore[attr-defined]
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


def _fetch_per_county_data(
    *,
    conn: sqlite3.Connection,
    counties: frozenset[str],
    year: int,
    audit_alarms: list[_CalibrationAlarm] | None = None,
) -> dict[str, _CountyRow]:
    """Read per-county economic + infrastructure values for tick-0 seeding.

    Five SQLite tables consulted (per `contracts/hex_hydrator_input.yaml`):

      - fact_qcew_annual: SUM(total_wages_usd) WHERE industry_id=1 → v_per_week (/52)
        (spec-066: industry_id=1 filter prevents NAICS-hierarchy triple-counting)
      - fact_bea_county_gdp + dim_bea_industry: GDP_county for the year
        (bea_industry_id = 1 = "All industries") → c_per_week + s_per_week + k_total
      - fact_broadband_coverage: pct_25_3, pct_100_20 → internet/surveillance
      - fact_coercive_infrastructure: SUM(facility_count) → surveillance

    The intermediate-inputs-fraction is a hardcoded national average
    (0.5) since fact_bea_national_industry is empty in the current
    SQLite snapshot. Future ingestion of BEA national I-O tables can
    refine this per-industry (spec-068).

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
    # Spec-066 T019: filter to `industry_id = 1` (the BLS 'All Industries'
    # aggregate). fact_qcew_annual is denormalized across
    # (industry x ownership x establishment) rows; summing across industries
    # triple-counts overlapping NAICS hierarchies (Manufacturing + Durable
    # Goods both contain the same establishments). industry_id=1 is the
    # BLS publication granularity that researchers cite in QCEW totals.
    qcew_rows = conn.execute(
        f"""
        SELECT dc.fips, COALESCE(SUM(fq.total_wages_usd), 0) AS total_wages
        FROM fact_qcew_annual fq
        JOIN dim_county dc ON dc.county_id = fq.county_id
        JOIN dim_time t ON t.time_id = fq.time_id
        WHERE dc.fips IN ({_placeholders(fips_list)})
          AND t.year = ?
          AND fq.industry_id = 1
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
        # c = GDP × intermediate-inputs-fraction (weekly).
        c_per_week = gdp_usd * _INTERMEDIATE_INPUTS_FRACTION / _WEEKS_PER_YEAR
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
