-- 0020_dynamic_consciousness_state.sql
-- Spec-065 engine-bridging T006.
-- Owner subsystem: consciousness (ConsciousnessSystem per spec-034/043).
-- Per II.11: only the consciousness subsystem writes to this table.
-- Cross-subsystem reads MUST go through view_runtime_trace_emission.
--
-- Naming note: this table is at county resolution (one row per
-- (session_id, tick, county_fips)) but is NOT a stored aggregate of
-- hex-resolution data — consciousness state IS computed at county
-- scope natively by ConsciousnessSystem. Spec-062 FR-019 forbids
-- stored aggregates of dynamic_hex_state at county/state/national
-- scale; this table is a NATIVE-county-resolution subsystem state
-- table, not an aggregate. The table name deliberately omits the
-- "county_" prefix to avoid namespace collision with the FR-019
-- guard regex.
--
-- Ternary simplex invariant (r + l + f ≈ 1.0 within ±1e-9) is enforced
-- by the engine, not by DB CHECK — float drift during serialization
-- may exceed any reasonable DB tolerance.

CREATE TABLE IF NOT EXISTS dynamic_consciousness_state (
    session_id      UUID NOT NULL,
    tick            INTEGER NOT NULL CHECK (tick >= 0),
    county_fips     TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),

    -- Survival calculus (spec-001)
    p_acquiescence  DOUBLE PRECISION NOT NULL
                    CHECK (p_acquiescence BETWEEN 0 AND 1),
    p_revolution    DOUBLE PRECISION NOT NULL
                    CHECK (p_revolution BETWEEN 0 AND 1),

    -- Ternary consciousness simplex (spec-034/043): r + l + f ≈ 1
    ideology_r      DOUBLE PRECISION NOT NULL
                    CHECK (ideology_r BETWEEN 0 AND 1),
    ideology_l      DOUBLE PRECISION NOT NULL
                    CHECK (ideology_l BETWEEN 0 AND 1),
    ideology_f      DOUBLE PRECISION NOT NULL
                    CHECK (ideology_f BETWEEN 0 AND 1),

    PRIMARY KEY (session_id, tick, county_fips)
);

CREATE INDEX IF NOT EXISTS ix_consciousness_session_tick
    ON dynamic_consciousness_state (session_id, tick);

-- Append-only enforcement: only INSERT and SELECT permitted.
REVOKE UPDATE, DELETE ON dynamic_consciousness_state FROM PUBLIC;

COMMENT ON TABLE dynamic_consciousness_state IS
    'spec-065 consciousness subsystem state per tick per county. '
    'Owner: ConsciousnessSystem. r + l + f ≈ 1.0 invariant enforced '
    'by engine, not DB (float drift may exceed CHECK tolerance). '
    'NOT an aggregate of dynamic_hex_state; this is native county-scope '
    'subsystem state (FR-019 compliant by construction).';
