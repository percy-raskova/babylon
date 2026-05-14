-- 0019_trace_emission_view.sql
-- Spec-064 — Headless Postgres-Backed Simulation Runner.
-- Owner subsystem: headless_runner feature (spec-064).
-- Constitution II.11: this view IS the declared cross-subsystem read
-- interface for trace emission. The runner reads ONLY this view; never
-- the underlying subsystem tables.
--
-- Depends on tables created in migration 0011 (dynamic_hex_state).
-- Future subsystem migrations (consciousness, demographics, employment)
-- will add LEFT JOINs to this view's definition without changing the
-- 22-column external contract; columns whose source tables don't yet
-- exist are emitted as NULL.

-- DROP + CREATE (not OR REPLACE) so column rename / reorder is allowed.
-- Idempotent: DROP IF EXISTS lets re-runs succeed.
DROP VIEW IF EXISTS view_runtime_trace_emission;

CREATE VIEW view_runtime_trace_emission AS
SELECT
    h.session_id,
    h.tick,
    h.county_fips                              AS entity_id,
    'county'::TEXT                             AS entity_kind,
    -- Marx primitives (sum over the hexes that make up the county).
    -- Column order matches contracts/trace_csv_schema.yaml (v, c, s, k).
    SUM(h.v)                                   AS v,
    SUM(h.c)                                   AS c,
    SUM(h.s)                                   AS s,
    SUM(h.k)                                   AS k,
    -- Survival calculus (not yet persisted at hex/county granularity)
    NULL::DOUBLE PRECISION                     AS p_acquiescence,
    NULL::DOUBLE PRECISION                     AS p_revolution,
    -- Ternary consciousness simplex (spec-034 / spec-043; not yet persisted)
    NULL::DOUBLE PRECISION                     AS ideology_r,
    NULL::DOUBLE PRECISION                     AS ideology_l,
    NULL::DOUBLE PRECISION                     AS ideology_f,
    -- Territory state (intensive ratios; average over hexes)
    AVG(h.surveillance_coupling)               AS surveillance_coupling,
    AVG(h.internet_access_pct)                 AS internet_access_pct,
    -- Substrate stocks (extensive; sum over hexes)
    SUM(h.biocapacity_stock)                   AS biocapacity_stock,
    SUM(h.energy_stock)                        AS energy_stock,
    SUM(h.raw_material_stock)                  AS raw_material_stock,
    -- Derived rates: s/(c+v) and s/v, NULL on zero/negative denominator
    CASE WHEN SUM(h.c) + SUM(h.v) > 0
         THEN SUM(h.s) / (SUM(h.c) + SUM(h.v))
         ELSE NULL
    END                                        AS profit_rate,
    CASE WHEN SUM(h.v) > 0
         THEN SUM(h.s) / SUM(h.v)
         ELSE NULL
    END                                        AS exploitation_rate,
    -- Demographics (not yet persisted; QCEW employment lives in
    -- immutable_reference_qcew_employment but isn't keyed by session_id +
    -- tick, so it can't be JOINed cleanly here).
    NULL::BIGINT                               AS population,
    NULL::DOUBLE PRECISION                     AS employment_proxy
FROM dynamic_hex_state h
GROUP BY h.session_id, h.tick, h.county_fips;

GRANT SELECT ON view_runtime_trace_emission TO PUBLIC;

COMMENT ON VIEW view_runtime_trace_emission IS
    'spec-064 trace emission contract. Owned by headless_runner feature. '
    'Per Constitution II.11: cross-subsystem read via declared interface. '
    'Subsystem table changes require a coordinated update to this view. '
    'The 22-column external contract is fixed by '
    'specs/064-headless-sim-runner/contracts/trace_csv_schema.yaml; '
    'columns whose source tables do not yet exist are emitted as NULL '
    'and will be backfilled by future subsystem migrations.';
