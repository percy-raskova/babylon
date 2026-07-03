-- 0029_tick_commit.sql
-- Spec 089 — Delta persistence (S1a, FR-001).
--
-- One row per committed tick, written INSIDE the envelope transaction by
-- persist_tick_atomic. Three roles at once:
--   1. Commit marker: with delta emission a tick may write ZERO hex rows,
--      so "MAX(tick) FROM dynamic_hex_state" no longer means "last
--      committed tick" — this table does.
--   2. Queryable Constitution-III.7 hash chain (one determinism_hash per
--      tick; previously only recoverable from conservation_audit_log rows).
--   3. Dense tick spine for the as-of fill-forward views (0028).
--
-- Created partitioned from birth (no 0026-style conversion needed);
-- per-session partitions come from ensure_session_partitions.

CREATE TABLE IF NOT EXISTS tick_commit (
    session_id       UUID NOT NULL,
    tick             INTEGER NOT NULL CHECK (tick >= 0),
    determinism_hash CHAR(64) NOT NULL,
    hex_rows_written INTEGER NOT NULL CHECK (hex_rows_written >= 0),
    is_checkpoint    BOOLEAN NOT NULL,
    created_at_utc   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, tick)
) PARTITION BY LIST (session_id);

CREATE TABLE IF NOT EXISTS tick_commit_default PARTITION OF tick_commit DEFAULT;

REVOKE UPDATE, DELETE ON tick_commit FROM PUBLIC;
