-- 0014_conservation_audit_log.sql
-- Spec 062 — Cross-Scale Integration, Phase 2 (T009).
-- Owner subsystem: persistence (per data-model.md §1).
-- Per-tick forensic record of conservation invariants (FR-043 .. FR-049).
-- Append-only enforced by REVOKE UPDATE, DELETE on the runtime role.

CREATE TABLE IF NOT EXISTS conservation_audit_log (
    session_id          UUID NOT NULL,
    tick                INTEGER NOT NULL CHECK (tick >= 0),
    scale               TEXT NOT NULL
                        CHECK (scale IN ('hex', 'county', 'state',
                                         'national', 'global_phi',
                                         'per_stage')),
    invariant_name      TEXT NOT NULL,
    computed_value      DOUBLE PRECISION NOT NULL,
    expected_value      DOUBLE PRECISION NOT NULL,
    residual            DOUBLE PRECISION NOT NULL,
    severity            TEXT NOT NULL
                        CHECK (severity IN ('ok', 'warn', 'alarm')),
    determinism_hash    TEXT NOT NULL CHECK (length(determinism_hash) = 64),
    created_at_utc      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_id, tick, scale, invariant_name)
);

CREATE INDEX IF NOT EXISTS ix_audit_session_tick
    ON conservation_audit_log (session_id, tick);
CREATE INDEX IF NOT EXISTS ix_audit_severity
    ON conservation_audit_log (session_id, severity)
    WHERE severity != 'ok';

-- Constitution III.7 + FR-049: append-only enforcement.
REVOKE UPDATE, DELETE ON conservation_audit_log FROM PUBLIC;
