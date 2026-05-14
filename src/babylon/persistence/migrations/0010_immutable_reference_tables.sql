-- 0010_immutable_reference_tables.sql
-- Spec 062 — Cross-Scale Integration, Phase 2 (T005).
-- Owner subsystem: persistence (per data-model.md §1, Constitution II.11).
-- READ-ONLY after Phase A initialization; FR-005 forbids runtime writes.
--
-- Ten tables, one per immutable federal reference series. All share a
-- (session_id, year, [+ optional kind discriminator]) primary key so a
-- multi-tenant Postgres can host many concurrent sessions without ID
-- collisions. Each table has REVOKE INSERT/UPDATE/DELETE FROM PUBLIC so
-- that the default runtime role cannot mutate them; the init-time role
-- is granted INSERT explicitly inside initialize_session().

-- ───────────────────────── 1. BEA Make-Use-Imports ─────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_bea_io (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    matrix_kind     TEXT NOT NULL
                    CHECK (matrix_kind IN ('intermediate', 'imports', 'make')),
    coefficients    JSONB NOT NULL,
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, matrix_kind)
);
CREATE INDEX IF NOT EXISTS ix_bea_io_session_year
    ON immutable_reference_bea_io (session_id, year);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_bea_io FROM PUBLIC;

-- ───────────────────────── 2. MELT τ (price of labor-time) ─────────────
CREATE TABLE IF NOT EXISTS immutable_reference_melt_tau (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    tau             DOUBLE PRECISION NOT NULL CHECK (tau > 0),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_melt_tau FROM PUBLIC;

-- ───────────────────────── 3. Basket γ (visibility) ────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_basket_gamma (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    gamma           DOUBLE PRECISION NOT NULL
                    CHECK (gamma BETWEEN 0 AND 1),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_basket_gamma FROM PUBLIC;

-- ───────────────────────── 4. ERDI ratio ───────────────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_erdi (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    partner_node_id TEXT NOT NULL,
    erdi_ratio      DOUBLE PRECISION NOT NULL CHECK (erdi_ratio > 0),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, partner_node_id)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_erdi FROM PUBLIC;

-- ───────────────────────── 5. Hickel Φ drain ───────────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_hickel_drain (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    partner_node_id TEXT NOT NULL,
    phi_year        DOUBLE PRECISION NOT NULL CHECK (phi_year >= 0),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, partner_node_id)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_hickel_drain FROM PUBLIC;

-- ───────────────────────── 6. Ricci unequal exchange ───────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_ricci_unequal (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    partner_node_id TEXT NOT NULL,
    bilateral_value DOUBLE PRECISION NOT NULL CHECK (bilateral_value >= 0),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, partner_node_id)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_ricci_unequal FROM PUBLIC;

-- ───────────────────────── 7. FAF freight ──────────────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_faf_freight (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    partner_node_id TEXT NOT NULL,
    tons            DOUBLE PRECISION NOT NULL CHECK (tons >= 0),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, partner_node_id)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_faf_freight FROM PUBLIC;

-- ───────────────────────── 8. QCEW employment ──────────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_qcew_employment (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    county_fips     TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),
    naics_code      TEXT NOT NULL,
    employment      INTEGER NOT NULL CHECK (employment >= 0),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, county_fips, naics_code)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_qcew_employment FROM PUBLIC;

-- ───────────────────────── 9. BEA REIS rent ────────────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_bea_reis_rent (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    county_fips     TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),
    rent            DOUBLE PRECISION NOT NULL CHECK (rent >= 0),
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, county_fips)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_bea_reis_rent FROM PUBLIC;

-- ───────────────────────── 10. FRED rates ──────────────────────────────
CREATE TABLE IF NOT EXISTS immutable_reference_fred_rates (
    session_id      UUID NOT NULL,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    series_id       TEXT NOT NULL,
    rate            DOUBLE PRECISION NOT NULL,
    canonical_source TEXT NOT NULL,
    PRIMARY KEY (session_id, year, series_id)
);
REVOKE INSERT, UPDATE, DELETE ON immutable_reference_fred_rates FROM PUBLIC;
