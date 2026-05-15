-- 0024_dynamic_relationship_state.sql
-- Spec-065 engine-bridging T080.
-- Owner subsystem: contradiction/solidarity (per spec-001/043).
-- Per II.11: only the contradiction + solidarity systems write to this table.
--
-- Stores per-tick dyadic relationship state — EXPLOITATION + SOLIDARITY
-- edges between SocialClass entities. The summary.json `max_tension`
-- field (T080) is computed as
--   MAX(tension) FILTER (WHERE edge_type = 'EXPLOITATION')
-- across all rows in a session — i.e., across all persisted ticks
-- (spec wording: "across all ticks").
--
-- Naming note: per FR-019, no `dynamic_county_*` aggregate tables. This
-- table is at edge resolution (one row per (session_id, tick, source,
-- target, edge_type)) — it's NOT a stored aggregate of any hex/county
-- subsystem state. It's the native persistence surface for the
-- relationship graph that the engine mutates per tick.
--
-- Spec-065 first cut: the bridge writes 0 rows per tick (no relationships
-- in WorldState yet). Spec-066 will populate them when ContradictionSystem
-- + SolidaritySystem are wired through the bridged engine. The SQL is
-- cross-tick-correct from day one.

CREATE TABLE IF NOT EXISTS dynamic_relationship_state (
    session_id        UUID NOT NULL,
    tick              INTEGER NOT NULL CHECK (tick >= 0),
    source_node_id    TEXT NOT NULL CHECK (length(source_node_id) BETWEEN 1 AND 64),
    target_node_id    TEXT NOT NULL CHECK (length(target_node_id) BETWEEN 1 AND 64),
    edge_type         TEXT NOT NULL CHECK (edge_type IN (
                          'EXPLOITATION', 'SOLIDARITY', 'WAGES',
                          'TRIBUTE', 'TENANCY', 'ADJACENCY', 'OTHER'
                      )),

    -- Tension is the canonical "intensity" measure used by max_tension.
    -- 0.0 means no tension; 1.0 means saturated.
    tension           DOUBLE PRECISION NOT NULL
                      CHECK (tension BETWEEN 0 AND 1),
    -- Solidarity (0..1) is meaningful for SOLIDARITY edges; defaults to
    -- 0.0 for non-solidarity edge types.
    solidarity        DOUBLE PRECISION NOT NULL DEFAULT 0.0
                      CHECK (solidarity BETWEEN 0 AND 1),

    PRIMARY KEY (session_id, tick, source_node_id, target_node_id, edge_type)
);

-- Cross-tick scan index: max_tension queries filter by session_id +
-- edge_type and aggregate across all ticks.
CREATE INDEX IF NOT EXISTS ix_relationship_state_session_edge
    ON dynamic_relationship_state (session_id, edge_type, tension);

-- Append-only enforcement: only INSERT and SELECT permitted.
REVOKE UPDATE, DELETE ON dynamic_relationship_state FROM PUBLIC;

COMMENT ON TABLE dynamic_relationship_state IS
    'spec-065 T080 per-tick dyadic relationship state. Owner: '
    'ContradictionSystem + SolidaritySystem. Cross-tick max_tension '
    'is computed via SQL aggregation here. FR-019 compliant: edge-'
    'resolution table, not a county/state/national aggregate.';
