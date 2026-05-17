-- 0021_dynamic_demographics_state.sql
-- Spec-065 engine-bridging T007.
-- Owner subsystem: demographics (Census ACS interpolated to weekly).
-- Per II.11: only the demographics subsystem writes to this table.
--
-- Naming note: this table is at county resolution. NOT an aggregate
-- of dynamic_hex_state — population is reported by Census at block
-- group → ACS county totals, which is what we store here directly.
-- Hex-level population would be an apportionment, not source data.
-- Spec-062 FR-019 compliant by construction.

CREATE TABLE IF NOT EXISTS dynamic_demographics_state (
    session_id    UUID NOT NULL,
    tick          INTEGER NOT NULL CHECK (tick >= 0),
    county_fips   TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),

    population    BIGINT NOT NULL CHECK (population >= 0),

    PRIMARY KEY (session_id, tick, county_fips)
);

CREATE INDEX IF NOT EXISTS ix_demographics_session_tick
    ON dynamic_demographics_state (session_id, tick);

REVOKE UPDATE, DELETE ON dynamic_demographics_state FROM PUBLIC;

COMMENT ON TABLE dynamic_demographics_state IS
    'spec-065 demographic state per tick per county. Owner: demographics. '
    'Population values derived from Census ACS interpolated to weekly '
    'cadence per spec-062 year-scoped lookup policy. NOT an aggregate '
    'of hex data; native county-scope (FR-019 compliant).';
