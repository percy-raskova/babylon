-- 0018_tiger_county_geometry.sql
-- Spec-063 closure follow-up (2026-05-14): make TIGER county geometry a
-- reproducible Postgres-resident reference table.
--
-- The geometry is stored as WKT (Well-Known Text) in a TEXT column for
-- portability across Postgres deployments without PostGIS. Downstream
-- callers load WKT into a Shapely geometry via `shapely.wkt.loads()`.
--
-- Cross-session reference table (no session_id column). One row per US
-- county (≈3,234 rows from TIGER 2024). Idempotent via ON CONFLICT DO
-- NOTHING in the ingestion path.
--
-- Owner subsystem: economics (mirrors immutable_reference_* convention).

CREATE TABLE IF NOT EXISTS immutable_reference_tiger_county (
    geoid          TEXT NOT NULL PRIMARY KEY CHECK (geoid ~ '^\d{5}$'),
    state_fips     TEXT NOT NULL CHECK (state_fips ~ '^\d{2}$'),
    county_fips    TEXT NOT NULL CHECK (county_fips ~ '^\d{3}$'),
    name           TEXT NOT NULL,
    namelsad       TEXT NOT NULL,
    geometry_wkt   TEXT NOT NULL,
    tiger_vintage  TEXT NOT NULL DEFAULT '2024',
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tiger_county_state
    ON immutable_reference_tiger_county (state_fips);

-- Append-only: ingestion uses ON CONFLICT DO NOTHING; explicit re-load
-- requires a manual TRUNCATE.
REVOKE UPDATE, DELETE ON immutable_reference_tiger_county FROM PUBLIC;
