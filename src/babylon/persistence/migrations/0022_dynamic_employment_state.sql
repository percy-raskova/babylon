-- 0022_dynamic_employment_state.sql
-- Spec-065 engine-bridging T008.
-- Owner subsystem: employment (QCEW interpolated; ImperialRentSystem
-- modulates via wage-extraction feedback).
-- Per II.11: only the employment subsystem writes to this table.
--
-- Naming note: this table is at county resolution. NOT an aggregate
-- of dynamic_hex_state — QCEW employment is reported at the
-- establishment level and rolled up to county by BLS; we store the
-- county-level QCEW totals directly. Spec-062 FR-019 compliant by
-- construction.

CREATE TABLE IF NOT EXISTS dynamic_employment_state (
    session_id        UUID NOT NULL,
    tick              INTEGER NOT NULL CHECK (tick >= 0),
    county_fips       TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),

    employment_proxy  DOUBLE PRECISION NOT NULL
                      CHECK (employment_proxy >= 0),

    PRIMARY KEY (session_id, tick, county_fips)
);

CREATE INDEX IF NOT EXISTS ix_employment_session_tick
    ON dynamic_employment_state (session_id, tick);

REVOKE UPDATE, DELETE ON dynamic_employment_state FROM PUBLIC;

COMMENT ON TABLE dynamic_employment_state IS
    'spec-065 employment state per tick per county. Owner: employment. '
    'Sourced from QCEW annualized employment, interpolated to weekly '
    'cadence; engine systems may modulate via wage-extraction feedback. '
    'NOT an aggregate of hex data; native county-scope (FR-019 compliant).';
