-- 0016_lodes_od_matrix.sql
-- Spec 063 — Vol II Circulation System with LODES OD Integration, Phase 2 (T004).
-- Owner subsystem: economics (per data-model.md §3, sibling of immutable_reference_qcew_employment).
-- Stores the year-scoped LEHD LODES Origin-Destination commute matrix in the
-- canonical immutable-reference pattern (read at session-init from the on-disk
-- gzipped CSV files, never mutated at runtime — Constitution II.6 + spec 062 GATE-2).

CREATE TABLE IF NOT EXISTS immutable_reference_lodes_od_matrix (
    session_id           UUID NOT NULL,
    year                 INTEGER NOT NULL,
    home_hex             TEXT NOT NULL,                       -- H3 res-7 origin cell ID
    workplace_dest       TEXT NOT NULL,                       -- H3 cell, "canada", or "rest_of_usa"
    workplace_dest_kind  TEXT NOT NULL
                         CHECK (workplace_dest_kind IN ('hex', 'external')),
    s000_workers         BIGINT NOT NULL CHECK (s000_workers >= 0),
    PRIMARY KEY (session_id, year, home_hex, workplace_dest)
);

CREATE INDEX IF NOT EXISTS ix_lodes_od_session_year
    ON immutable_reference_lodes_od_matrix (session_id, year);

CREATE INDEX IF NOT EXISTS ix_lodes_od_year_home
    ON immutable_reference_lodes_od_matrix (year, home_hex);

-- Append-only at the role layer (Constitution II.6 / spec 062 inheritance).
REVOKE UPDATE, DELETE ON immutable_reference_lodes_od_matrix FROM PUBLIC;
