-- 0012_dynamic_external_node_state.sql
-- Spec 062 — Cross-Scale Integration, Phase 2 (T007).
-- Owner subsystem: persistence (per data-model.md §1).
-- Eight international + one domestic Rest-of-USA external node per session
-- (FR-036/FR-037/FR-038 + R4 Canada amendment).

CREATE TABLE IF NOT EXISTS dynamic_external_node_state (
    session_id              UUID NOT NULL,
    tick                    INTEGER NOT NULL CHECK (tick >= 0),
    node_id                 TEXT NOT NULL,
    kind                    TEXT NOT NULL
                            CHECK (kind IN ('international', 'domestic_rest')),
    phi_year_inflow         DOUBLE PRECISION NOT NULL
                            CHECK (phi_year_inflow >= 0),
    bilateral_trade_value   DOUBLE PRECISION NOT NULL
                            CHECK (bilateral_trade_value >= 0),
    bilateral_trade_tons    DOUBLE PRECISION NOT NULL
                            CHECK (bilateral_trade_tons >= 0),
    erdi_ratio              DOUBLE PRECISION NOT NULL CHECK (erdi_ratio > 0),
    PRIMARY KEY (session_id, tick, node_id)
);

CREATE INDEX IF NOT EXISTS ix_external_node_session_tick
    ON dynamic_external_node_state (session_id, tick);
