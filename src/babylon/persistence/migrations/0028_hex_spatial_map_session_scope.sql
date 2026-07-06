-- 0028_hex_spatial_map_session_scope.sql
-- Session-scope hex_spatial_map so concurrent sessions can't wipe each other.
-- Percy approved schema change (owner-queue decision A, 2026-07-06).
--
-- Before: hex_spatial_map had h3_index as the sole PK — a GLOBAL table.
-- Any process that TRUNCATEd it (or re-ran hydration for a new session
-- with ON CONFLICT DO NOTHING) would silently zero out spatial keys for
-- ALL concurrent sessions. The runner's STEP-0 guard caught the symptom
-- (silent-zero spatial keys) but not the cause.
--
-- After: session_id is part of the PK. Each session has its own row set.
-- The hex hydrator writes (session_id, h3_index) pairs. Views JOIN on
-- both columns. Legacy rows (pre-0028) are backfilled with a sentinel
-- UUID and continue to work via the COALESCE fallback to inline values.

-- 1. Add session_id column (nullable for backward compat with existing rows).
ALTER TABLE hex_spatial_map ADD COLUMN IF NOT EXISTS session_id UUID;

-- 2. Backfill: assign existing rows to the sentinel "legacy" session.
--    Idempotent — only updates rows where session_id IS NULL.
UPDATE hex_spatial_map
SET session_id = '00000000-0000-0000-0000-000000000000'::UUID
WHERE session_id IS NULL;

-- 3. Make NOT NULL (safe after backfill).
ALTER TABLE hex_spatial_map ALTER COLUMN session_id SET NOT NULL;

-- 4. Drop old PK (h3_index only) and add new composite PK (session_id, h3_index).
--    Idempotent: only drops/recreates if the PK is on (h3_index) alone.
DO $pk_swap$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        WHERE t.relname = 'hex_spatial_map'
          AND i.indisprimary
          AND array_length(i.indkey::smallint[], 1) = 1
    ) THEN
        ALTER TABLE hex_spatial_map DROP CONSTRAINT hex_spatial_map_pkey;
        ALTER TABLE hex_spatial_map ADD PRIMARY KEY (session_id, h3_index);
    END IF;
END
$pk_swap$;

-- 5. Index for per-session lookups (the PK covers this, but an explicit
--    session_id-first index helps the query planner for count-by-session).
CREATE INDEX IF NOT EXISTS idx_hex_spatial_map_session
    ON hex_spatial_map (session_id);
