-- 0017_border_commute_synthesis.sql
-- Spec 063 — Vol II Circulation System with LODES OD Integration, Phase 2 (T005).
-- Owner subsystem: economics (per data-model.md §3).
-- Stores the per-session synthesized Detroit-Windsor cross-border commute flows
-- (BTS Border Crossing Data + StatCan Frontier Counts + Workforce WindsorEssex
-- 2017 commuter-share anchor) for the Option B opt-in path (FR-031..FR-036).
-- Empty for sessions that do not enable enable_border_commute_synthesis.

CREATE TABLE IF NOT EXISTS immutable_reference_border_commute_synthesis (
    session_id        UUID NOT NULL,
    year              INTEGER NOT NULL,
    week_of_year      INTEGER NOT NULL CHECK (week_of_year BETWEEN 1 AND 52),
    direction         TEXT NOT NULL
                      CHECK (direction IN ('us_to_canada', 'canada_to_us')),
    aggregate_origin  TEXT NOT NULL,
    aggregate_dest    TEXT NOT NULL,
    magnitude_workers DOUBLE PRECISION NOT NULL CHECK (magnitude_workers >= 0),
    source_anchor     TEXT NOT NULL,
    PRIMARY KEY (session_id, year, week_of_year, direction)
);

CREATE INDEX IF NOT EXISTS ix_border_synth_session_year
    ON immutable_reference_border_commute_synthesis (session_id, year);

-- Append-only at the role layer.
REVOKE UPDATE, DELETE ON immutable_reference_border_commute_synthesis FROM PUBLIC;
