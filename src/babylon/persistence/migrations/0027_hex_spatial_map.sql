-- 0027_hex_spatial_map.sql
-- Spec 088 — Storage program sprint 2 (S3, FR-006/FR-007).
--
-- The hex → (county, state, region) mapping is immutable per hex yet was
-- re-written on every dynamic_hex_state row every tick (~15-20 B/row of
-- pure duplication at 48,827 rows/tick statewide). hex_spatial_map becomes
-- the single stored copy: the hex hydrator populates it once per hex
-- (ON CONFLICT DO NOTHING) and the per-tick write layer (_hex_row_dict)
-- writes NULL spatial keys. Views resolve via LEFT JOIN + COALESCE so
-- legacy rows (inline fips) and test-harness rows keep working.
--
-- NOTE: distinct from spec-037's `hex_map` (game-scoped geometry table in
-- postgres_schema.py). Columns here are NOT dropped from dynamic_hex_state
-- (recorded deviation, spec-088 FR-007): the runner re-applies every
-- migration each start, so a column drop would break the earlier 0011/0023
-- DDL passes; NULLed TEXT columns cost ~nothing on disk.

CREATE TABLE IF NOT EXISTS hex_spatial_map (
    h3_index    TEXT PRIMARY KEY CHECK (length(h3_index) = 15),
    county_fips TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),
    state_fips  TEXT NOT NULL CHECK (state_fips ~ '^\d{2}$'),
    region_id   TEXT NOT NULL
);

-- Spatial-key columns become NULLable (idempotent; new rows write NULL).
ALTER TABLE dynamic_hex_state ALTER COLUMN county_fips DROP NOT NULL;
ALTER TABLE dynamic_hex_state ALTER COLUMN state_fips DROP NOT NULL;
ALTER TABLE dynamic_hex_state ALTER COLUMN region_id DROP NOT NULL;

-- Backfill the mapping from any legacy rows already present (pre-S3 data
-- carried the keys inline). Idempotent via ON CONFLICT DO NOTHING.
-- NO conflict target on purpose: 0028 replaces the single-column PK with
-- (session_id, h3_index), and the runner re-applies every migration each
-- start — naming (h3_index) here fails with InvalidColumnReference on any
-- database where 0028 has already run, and the composite key cannot be
-- named either (session_id does not exist until 0028 on a fresh database).
INSERT INTO hex_spatial_map (h3_index, county_fips, state_fips, region_id)
SELECT DISTINCT ON (h3_index) h3_index, county_fips, state_fips, region_id
FROM dynamic_hex_state
WHERE county_fips IS NOT NULL
  AND state_fips IS NOT NULL
  AND region_id IS NOT NULL
ORDER BY h3_index, tick
ON CONFLICT DO NOTHING;

-- Index diet (S3): the three secondary indexes on dynamic_hex_state are
-- dead weight post-normalization — (session_id, tick) is a strict prefix
-- of the PK, and the county/state indexes would index NULLs. Names vary
-- (originals from 0011 on a flat table; LIKE-generated on the partitioned
-- parent), so drop every non-unique index on the parent dynamically.
-- Dropping a partitioned index cascades to its partition children.
DO $index_diet$
DECLARE
    idx RECORD;
BEGIN
    FOR idx IN
        SELECT c.relname AS index_name
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        WHERE t.relname = 'dynamic_hex_state'
          AND NOT i.indisunique
          AND NOT i.indisprimary
    LOOP
        EXECUTE format('DROP INDEX IF EXISTS %I', idx.index_name);
    END LOOP;
END
$index_diet$;
