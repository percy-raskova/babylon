"""Hex graph hydration at session-init time (Spec 063 closure / 2026-05-14).

Closes the ``InitializationReport.hex_count = 0`` stub that spec-062 T029
shipped. For each county in the study area:

  1. Loads the county polygon from the Postgres-resident
     ``immutable_reference_tiger_county`` table (WKT-in-TEXT; populated
     by :func:`babylon.persistence.tiger_ingestion.ingest_tiger_counties`).
     Falls back to direct shapefile read if the table is empty (caller
     should ensure the ingestion ran).
  2. Polyfills to H3 res-7 cells via ``generate_h3_cells`` (existing helper
     at :mod:`babylon.economics.substrate.h3_utils`).
  3. Reads the county's QCEW employment total from
     ``immutable_reference_qcew_employment`` (hydrated upstream).
  4. Allocates v (variable-capital, in worker-units) uniformly across the
     county's hexes; derives c, k from configurable ratios; sets s = 0.
  5. Sets substrate stocks + internet/surveillance fields from
     ``GameDefines`` defaults (uniform per hex).
  6. Constructs ``DynamicHexState`` rows and persists them atomically via
     ``PerTickTransactionEnvelope`` + ``runtime.persist_tick_atomic`` at
     tick 0 (mirrors the ``_bootstrap_external_nodes`` pattern at
     :func:`postgres_initialization._bootstrap_external_nodes`).

Per the 2026-05-14 clarification, allocation is **uniform within county**;
LODES-workplace-density weighting is deferred to a future spec.

Units note: v is reported in **worker-equivalents** (QCEW employment count)
rather than dollars. Downstream consumers compute ratios (e.g., c/v, s/v)
which are unit-invariant. Translating to a wage-bill numéraire is a
follow-on calibration task.

See Also:
    ``specs/063-vol-ii-circulation/spec.md`` (FR-031 spec-063 hex hydration scope)
    ``specs/062-cross-scale-integration/data-model.md`` §2.4 DynamicHexState
    :class:`babylon.persistence.hex_state.DynamicHexState`
    :func:`babylon.economics.substrate.h3_utils.generate_h3_cells`
"""

from __future__ import annotations

import logging
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

# Default TIGER county shapefile shipped under data/tiger/county/.
_DEFAULT_TIGER_PATH = Path("data/tiger/county/tl_2024_us_county.shp")


def hydrate_hex_state(
    *,
    runtime: RuntimePersistence,
    session_id: UUID,
    counties: frozenset[str],
    start_year: int,
    defines: GameDefines,
    tiger_county_shapefile: Path | None = None,
) -> int:
    """Hydrate ``dynamic_hex_state`` for the study area at tick 0.

    Args:
        runtime: PostgresRuntime instance (provides ``_pool`` + ``persist_tick_atomic``).
        session_id: Active session UUID.
        counties: 5-digit FIPS codes for the study area
            (e.g., ``frozenset({"26163", "26125", "26099"})`` for Detroit tri-county).
        start_year: Year used to look up QCEW employment totals.
        defines: ``GameDefines`` instance providing the per-hex defaults.
        tiger_county_shapefile: Optional override for the TIGER shapefile path.

    Returns:
        Total number of ``dynamic_hex_state`` rows persisted at tick 0.
    """
    if not counties:
        logger.info("hydrate_hex_state: empty county set; nothing to do")
        return 0

    # 1. Load county polygons (prefer Postgres-resident WKT, fall back to shapefile)
    #    + employment totals.
    polygons = _load_county_polygons(
        counties=counties,
        runtime=runtime,
        shapefile_fallback=tiger_county_shapefile or _DEFAULT_TIGER_PATH,
    )
    employment_totals = _fetch_county_employment_totals(
        runtime=runtime,
        session_id=session_id,
        counties=counties,
        year=start_year,
    )

    # 2. Build per-county hex sets + allocate state.
    hex_rows: list[DynamicHexState] = []
    for county_fips, polygon in polygons.items():
        cells = _polygons_to_hexes(polygon)
        if not cells:
            logger.warning("hydrate_hex_state: county %s polyfill produced 0 cells", county_fips)
            continue
        employment_county = employment_totals.get(county_fips, 0)
        # Uniform allocation per hex; fall back to v=0 when QCEW absent (FR-011 semantics).
        v_per_hex = float(employment_county) / len(cells) if employment_county else 0.0
        c_per_hex = v_per_hex * defines.economy.initial_c_to_v_ratio
        k_per_hex = v_per_hex * defines.economy.initial_k_to_v_ratio
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
                    s=0.0,
                    k=k_per_hex,
                    biocapacity_stock=defines.territory.initial_biocapacity_per_hex,
                    energy_stock=defines.territory.initial_energy_per_hex,
                    raw_material_stock=defines.territory.initial_raw_material_per_hex,
                    internet_access_pct=defines.territory.initial_internet_access_pct,
                    surveillance_coupling=defines.territory.initial_surveillance_coupling,
                )
            )

    if not hex_rows:
        return 0

    # 3. Persist atomically at tick 0.
    envelope = PerTickTransactionEnvelope(
        session_id=session_id,
        tick=0,
        hex_state_rows=hex_rows,
        determinism_hash="0" * 64,  # tick-0 hydration uses placeholder hash
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
# Internal helpers — public for testability via module-level access.
# ─────────────────────────────────────────────────────────────────────────────


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


def _fetch_county_employment_totals(
    *,
    runtime: RuntimePersistence,
    session_id: UUID,
    counties: frozenset[str],
    year: int,
) -> dict[str, int]:
    """Sum QCEW employment by county for the given year.

    Returns ``{county_fips: total_employment}``. Counties absent from QCEW
    coverage are omitted; the caller falls back to v=0 per FR-011 semantics.
    """
    fips_list = sorted(counties)
    with (
        runtime._pool.connection() as pg,  # type: ignore[attr-defined]  # noqa: SLF001
        pg.cursor() as cur,
    ):
        cur.execute(
            """
            SELECT county_fips, SUM(employment) AS total_employment
            FROM immutable_reference_qcew_employment
            WHERE session_id = %s
              AND year = %s
              AND county_fips = ANY(%s)
            GROUP BY county_fips
            """,
            (session_id, year, fips_list),
        )
        rows = cur.fetchall()
    return {county: int(total) for county, total in rows}


__all__ = ["hydrate_hex_state"]
