#!/usr/bin/env python3
"""Tri-county economic substrate demo.

Runs the full pipeline (spatial mesh -> hydration -> Vol I/II/III -> aggregation)
with both DEFAULT_COUNTY_ECONOMICS and MarxianHydrator to compare profit rates.

Usage:
    poetry run python tools/demo_substrate.py
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
logger = logging.getLogger("demo_substrate")


# ── Substrate CommuterFlowSource adapter (bridges LODES -> substrate protocol) ──


class SQLiteSubstrateCommuterSource:
    """Adapter bridging LODES fact table to substrate CommuterFlowSource protocol."""

    def __init__(self, session_factory: object) -> None:
        self._session_factory = session_factory

    def get_county_od_flows(
        self, county_fips_list: Sequence[str], year: int
    ) -> dict[tuple[str, str], int]:
        """Query FactLodesCommuterFlow for county-to-county OD flows."""
        factory = self._session_factory  # type: ignore[assignment]
        session: Session = factory()
        try:
            fips_str = ",".join(f"'{f}'" for f in county_fips_list)
            query = text(f"""
                SELECT
                    home.fips AS home_fips,
                    work.fips AS work_fips,
                    SUM(f.total_jobs) AS total
                FROM fact_lodes_commuter_flow f
                JOIN dim_county home ON f.home_county_id = home.county_id
                JOIN dim_county work ON f.work_county_id = work.county_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE home.fips IN ({fips_str})
                  AND work.fips IN ({fips_str})
                  AND t.year = :year
                GROUP BY home.fips, work.fips
            """)
            rows = session.execute(query, {"year": year}).fetchall()
            return {(r[0], r[1]): int(r[2]) for r in rows}
        finally:
            session.close()


def run_pipeline(
    label: str,
    use_marxian_hydrator: bool = False,
    year: int = 2023,
    lodes_year: int = 2021,
) -> None:
    """Run the substrate pipeline with or without MarxianHydrator."""
    from babylon.domain.economics.substrate import (
        DefaultHexCirculationComputer,
        DefaultHexEqualizationComputer,
        DefaultHexProductionComputer,
        DefaultResolutionAggregator,
        SubstrateConfig,
        generate_tri_county_mesh,
        hydrate_hex_grid,
    )
    from babylon.reference.database import get_normalized_session_factory

    logger.info("=" * 70)
    logger.info("  %s", label)
    logger.info("=" * 70)

    t0 = time.perf_counter()
    session_factory = get_normalized_session_factory()
    config = SubstrateConfig()

    # ── Step 1: Spatial mesh ──
    t1 = time.perf_counter()
    grid = generate_tri_county_mesh(config)
    dt_spatial = time.perf_counter() - t1
    logger.info(
        "Spatial mesh: %d hexes (%s) in %.2fs",
        len(grid.hexes),
        ", ".join(f"{fips}: {len(ids)}" for fips, ids in sorted(grid.county_hex_ids.items())),
        dt_spatial,
    )

    # ── Step 2: Hydration ──
    marxian_hydrator = None
    if use_marxian_hydrator:
        from babylon.domain.economics.adapters import SQLiteQCEWSource
        from babylon.domain.economics.department_mapper import get_default_mapper
        from babylon.domain.economics.hydrator import MarxianHydrator

        class _NoBEASource:
            """InterpolatingBEASource was retired (fork ledger F2); the
            hydrator's YAML-default fallback path handles a None-returning
            source — the same degradation it always used when BEA tables
            were absent."""

            def get_sv_ratio(self, naics: str, year: int) -> float | None:  # noqa: ARG002 - protocol shape
                return None

            def get_cv_ratio(self, naics: str, year: int) -> float | None:  # noqa: ARG002 - protocol shape
                return None

        session = session_factory()
        qcew_source = SQLiteQCEWSource(session)
        dept_mapper = get_default_mapper()
        marxian_hydrator = MarxianHydrator(qcew_source, _NoBEASource(), dept_mapper)

    t2 = time.perf_counter()
    grid = hydrate_hex_grid(grid, year=year, marxian_hydrator=marxian_hydrator)
    dt_hydration = time.perf_counter() - t2

    total_c = sum(h.constant_capital for h in grid.hexes.values())
    total_v = sum(h.variable_capital for h in grid.hexes.values())
    total_s = sum(h.surplus_value for h in grid.hexes.values())
    logger.info(
        "Hydration: c=%.1f, v=%.1f, s=%.1f (total=%.1f) in %.2fs",
        total_c,
        total_v,
        total_s,
        total_c + total_v + total_s,
        dt_hydration,
    )

    # ── Step 3: Volume I Production ──
    prod = DefaultHexProductionComputer()
    grid = prod.compute_production(grid)

    county_rates: dict[str, float] = {}
    for fips, hex_ids in sorted(grid.county_hex_ids.items()):
        c = sum(grid.hexes[h].constant_capital for h in hex_ids)
        v = sum(grid.hexes[h].variable_capital for h in hex_ids)
        s = sum(grid.hexes[h].surplus_value for h in hex_ids)
        pr = s / (c + v) if (c + v) > 0 else 0.0
        county_rates[fips] = pr
        logger.info("  County %s: c=%.1f, v=%.1f, s=%.1f, r=%.1f%%", fips, c, v, s, pr * 100)

    # ── Step 4: Volume II Circulation ──
    t4 = time.perf_counter()
    circ = DefaultHexCirculationComputer()
    commuter_source = SQLiteSubstrateCommuterSource(session_factory)
    od_matrix = circ.build_od_matrix(grid, commuter_source, lodes_year)
    pre_v = sum(h.variable_capital for h in grid.hexes.values())
    grid, boundary = circ.circulate_wages(grid, od_matrix)
    post_v = sum(h.variable_capital for h in grid.hexes.values())
    dt_circulation = time.perf_counter() - t4
    logger.info(
        "Circulation: OD matrix %s, nnz=%d in %.2fs",
        od_matrix.shape,
        od_matrix.nnz,
        dt_circulation,
    )
    logger.info(
        "  Conservation: pre_v=%.6f, post_v=%.6f, diff=%.2e",
        pre_v,
        post_v,
        abs(pre_v - post_v),
    )

    # County-level wage shifts
    for fips, hex_ids in sorted(grid.county_hex_ids.items()):
        v_post = sum(grid.hexes[h].variable_capital for h in hex_ids)
        logger.info("  County %s post-circulation v=%.1f", fips, v_post)

    # ── Step 5: Volume III Equalization ──
    t5 = time.perf_counter()
    eq = DefaultHexEqualizationComputer()
    grid = eq.equalize_capital(grid)
    dt_equalization = time.perf_counter() - t5
    logger.info("Equalization: %.2fs", dt_equalization)

    # ── Step 6: Aggregation ──
    t6 = time.perf_counter()
    agg = DefaultResolutionAggregator()
    r6 = agg.aggregate(grid, target_resolution=6)
    r5 = agg.aggregate(grid, target_resolution=5)
    dt_agg = time.perf_counter() - t6
    logger.info("Aggregation: r6=%d parents, r5=%d parents in %.2fs", len(r6), len(r5), dt_agg)

    # ── Conservation checks ──
    circ_ok = abs(pre_v - post_v) < 1e-8

    # ── Summary ──
    total_c_final = sum(h.constant_capital for h in grid.hexes.values())
    total_v_final = sum(h.variable_capital for h in grid.hexes.values())
    total_s_final = sum(h.surplus_value for h in grid.hexes.values())
    metro_pr = (
        total_s_final / (total_c_final + total_v_final)
        if (total_c_final + total_v_final) > 0
        else 0.0
    )

    dt_total = time.perf_counter() - t0
    logger.info("")
    logger.info("── RESULTS ──")
    logger.info("  Metro-area profit rate: %.1f%%", metro_pr * 100)
    logger.info(
        "  Circulation conservation: %s (diff=%.2e)",
        "PASS" if circ_ok else "FAIL",
        abs(pre_v - post_v),
    )
    logger.info("  Total pipeline time: %.2fs", dt_total)
    logger.info("")


if __name__ == "__main__":
    # Run with defaults first
    run_pipeline("Pipeline with DEFAULT_COUNTY_ECONOMICS (hardcoded)", use_marxian_hydrator=False)

    # Run with MarxianHydrator
    run_pipeline("Pipeline with MarxianHydrator (real QCEW data)", use_marxian_hydrator=True)
