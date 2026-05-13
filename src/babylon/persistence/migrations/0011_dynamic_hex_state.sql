-- 0011_dynamic_hex_state.sql
-- Spec 062 — Cross-Scale Integration, Phase 2 (T006).
-- Owner subsystem: persistence (per data-model.md §1).
-- PRIMARY persistence target for c/v/s/K/biocapacity (FR-018).
-- Hex resolution 7 is the ONLY persisted source-of-truth (FR-019).

CREATE TABLE IF NOT EXISTS dynamic_hex_state (
    session_id      UUID NOT NULL,
    tick            INTEGER NOT NULL CHECK (tick >= 0),
    h3_index        TEXT NOT NULL CHECK (length(h3_index) = 15),

    -- Spatial mapping (immutable per hex; computed once at init)
    county_fips     TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),
    state_fips      TEXT NOT NULL CHECK (state_fips ~ '^\d{2}$'),
    region_id       TEXT NOT NULL,

    -- Value substance (Vol I primitives)
    c               DOUBLE PRECISION NOT NULL CHECK (c >= 0),
    v               DOUBLE PRECISION NOT NULL CHECK (v >= 0),
    s               DOUBLE PRECISION NOT NULL CHECK (s >= 0),

    -- Capital stock (perpetual-inventory; FR-014/FR-015)
    k               DOUBLE PRECISION NOT NULL CHECK (k >= 0),

    -- Substrate stocks (computed by Substrate system at pipeline pos 2.5)
    biocapacity_stock   DOUBLE PRECISION NOT NULL CHECK (biocapacity_stock >= 0),
    energy_stock        DOUBLE PRECISION NOT NULL CHECK (energy_stock >= 0),
    raw_material_stock  DOUBLE PRECISION NOT NULL CHECK (raw_material_stock >= 0),

    -- Surveillance / coupling (FCC broadband-derived)
    internet_access_pct     DOUBLE PRECISION NOT NULL
                            CHECK (internet_access_pct BETWEEN 0 AND 1),
    surveillance_coupling   DOUBLE PRECISION NOT NULL
                            CHECK (surveillance_coupling BETWEEN 0 AND 1),

    PRIMARY KEY (session_id, tick, h3_index)
);

CREATE INDEX IF NOT EXISTS ix_hex_state_session_tick
    ON dynamic_hex_state (session_id, tick);
CREATE INDEX IF NOT EXISTS ix_hex_state_county
    ON dynamic_hex_state (session_id, tick, county_fips);
CREATE INDEX IF NOT EXISTS ix_hex_state_state
    ON dynamic_hex_state (session_id, tick, state_fips);
