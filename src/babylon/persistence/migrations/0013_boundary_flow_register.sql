-- 0013_boundary_flow_register.sql
-- Spec 062 — Cross-Scale Integration, Phase 2 (T008).
-- Owner subsystem: economics (per data-model.md §1, R5 ownership registry).
-- Append-only record of every cross-boundary flow per tick (FR-040).
-- Composite PRIMARY KEY enables ON CONFLICT DO NOTHING idempotent retry-
-- after-crash semantics. UPDATE and DELETE blocked at the role layer.

CREATE TABLE IF NOT EXISTS boundary_flow_register (
    session_id      UUID NOT NULL,
    tick            INTEGER NOT NULL CHECK (tick >= 0),
    source_node_id  TEXT NOT NULL,
    source_kind     TEXT NOT NULL
                    CHECK (source_kind IN ('hex', 'county', 'state',
                                           'national', 'external')),
    dest_node_id    TEXT NOT NULL,
    dest_kind       TEXT NOT NULL
                    CHECK (dest_kind IN ('hex', 'county', 'state',
                                         'national', 'external')),
    flow_type       TEXT NOT NULL
                    CHECK (flow_type IN ('trade_edge', 'drain_edge',
                                         'commute_out', 'commute_in',
                                         'physical_exchange')),
    magnitude       DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (session_id, tick, source_node_id, dest_node_id, flow_type)
);

CREATE INDEX IF NOT EXISTS ix_boundary_session_tick
    ON boundary_flow_register (session_id, tick);
CREATE INDEX IF NOT EXISTS ix_boundary_source
    ON boundary_flow_register (session_id, source_kind, source_node_id);
CREATE INDEX IF NOT EXISTS ix_boundary_dest
    ON boundary_flow_register (session_id, dest_kind, dest_node_id);

-- Append-only at the role layer (FR-040 / Constitution II.9).
REVOKE UPDATE, DELETE ON boundary_flow_register FROM PUBLIC;
