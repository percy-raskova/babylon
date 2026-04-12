"""Tick-0 ETL: seed hex_latest from territory_snapshot + hex_map.

Called once at game init after territory_snapshot and hex_map have
been populated. Constructs the denormalized R7 hex cache by JOINing
county-level economics with hex geography and (optionally) R8
substrate terrain aggregates.

Usage::

    from babylon.persistence.hex_init import seed_hex_latest

    seed_hex_latest(pool, game_id)  # After init writes to territory_snapshot + hex_map
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from psycopg import Connection
    from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

# SQL: seed hex_latest from territory_snapshot(tick=0) + hex_map + hex_substrate
SEED_HEX_LATEST_SQL = """
INSERT INTO hex_latest (
    game_id, h3_index, tick,
    county_fips, county_name, state_fips,
    center_lat, center_lng,
    profit_rate, exploitation_rate, occ, imperial_rent, g33_visibility,
    pop_bourgeoisie, pop_petit_bourgeoisie, pop_labor_aristocracy,
    pop_proletariat, pop_lumpenproletariat, pop_total,
    dominant_class,
    faction_finance_capital, faction_security_state, faction_settler_populist,
    terrain_type, water_coverage, internet_access,
    attributes
)
SELECT
    ts.game_id,
    hm.h3_index,
    0,
    ts.county_fips,
    hm.county_name,
    hm.state_fips,
    hm.center_lat,
    hm.center_lng,
    ts.profit_rate,
    ts.exploitation_rate,
    ts.occ,
    ts.imperial_rent,
    ts.g33_visibility,
    ts.pop_bourgeoisie,
    ts.pop_petit_bourgeoisie,
    ts.pop_labor_aristocracy,
    ts.pop_proletariat,
    ts.pop_lumpenproletariat,
    ts.pop_total,
    CASE
        WHEN ts.pop_proletariat >= GREATEST(
            ts.pop_bourgeoisie, ts.pop_labor_aristocracy
        ) THEN 'proletariat'
        WHEN ts.pop_bourgeoisie >= ts.pop_labor_aristocracy
            THEN 'bourgeoisie'
        ELSE 'labor_aristocracy'
    END,
    ts.faction_finance_capital,
    ts.faction_security_state,
    ts.faction_settler_populist,
    COALESCE(sub.terrain_type, 'LAND'),
    COALESCE(sub.avg_water, 0.0),
    COALESCE(sub.has_internet, FALSE),
    ts.attributes
FROM territory_snapshot ts
JOIN hex_map hm
    ON ts.game_id = hm.game_id AND ts.county_fips = hm.county_fips
LEFT JOIN (
    SELECT
        game_id, r7_parent,
        MODE() WITHIN GROUP (ORDER BY terrain_type) AS terrain_type,
        AVG(water_coverage) AS avg_water,
        BOOL_OR(internet_access) AS has_internet
    FROM hex_substrate
    GROUP BY game_id, r7_parent
) sub ON ts.game_id = sub.game_id AND hm.h3_index = sub.r7_parent
WHERE ts.game_id = %s
  AND ts.tick = 0
"""


def seed_hex_latest(
    pool: ConnectionPool[Connection[Any]],
    game_id: UUID,
) -> int:
    """Seed hex_latest from tick-0 territory_snapshot + hex_map.

    Prerequisite: ``territory_snapshot`` (tick 0) and ``hex_map`` must
    already be populated for this game_id.

    Optionally aggregates R8 terrain from ``hex_substrate`` if present.

    Args:
        pool: psycopg ConnectionPool.
        game_id: Game session UUID.

    Returns:
        Number of hex_latest rows inserted.
    """
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(SEED_HEX_LATEST_SQL, (game_id,))
        inserted = cur.rowcount
        logger.info(
            "Seeded hex_latest: %d rows (game=%s)",
            inserted,
            game_id,
        )
        return inserted
