-- 0015_aggregation_views.sql
-- Spec 062 — Cross-Scale Integration, Phase 2 (T010).
-- Constitution II.11: these four read-only views ARE the declared
-- cross-subsystem read interface (per data-model.md §1).
-- Depends on tables created in migrations 0011, 0012, 0013.

-- ───────── v_county_value_aggregate ─────────
CREATE OR REPLACE VIEW v_county_value_aggregate AS
SELECT
    session_id,
    tick,
    county_fips,
    SUM(c) AS c_sum,
    SUM(v) AS v_sum,
    SUM(s) AS s_sum,
    SUM(k) AS k_sum,
    SUM(biocapacity_stock) AS biocapacity_sum,
    COUNT(*) AS hex_count
FROM dynamic_hex_state
GROUP BY session_id, tick, county_fips;

-- ───────── v_state_value_aggregate ─────────
-- Direct hex→state aggregation. This bypasses the per-county view but
-- guarantees identical results to a hierarchical SUM(c_sum) via county.
-- The data-model.md §3.6 hierarchical form is preserved in spirit by the
-- aggregation chain in the auditor (county → state → national); both
-- forms compute the same SUM(c) over the same hexes.
CREATE OR REPLACE VIEW v_state_value_aggregate AS
SELECT
    session_id,
    tick,
    state_fips,
    SUM(c) AS c_sum,
    SUM(v) AS v_sum,
    SUM(s) AS s_sum,
    SUM(k) AS k_sum,
    SUM(biocapacity_stock) AS biocapacity_sum,
    COUNT(*) AS hex_count
FROM dynamic_hex_state
GROUP BY session_id, tick, state_fips;

-- ───────── v_national_value_aggregate ─────────
CREATE OR REPLACE VIEW v_national_value_aggregate AS
SELECT
    session_id,
    tick,
    'USA'::TEXT AS national_id,
    SUM(c) AS c_sum,
    SUM(v) AS v_sum,
    SUM(s) AS s_sum,
    SUM(k) AS k_sum,
    SUM(biocapacity_stock) AS biocapacity_sum,
    COUNT(*) AS hex_count
FROM dynamic_hex_state
GROUP BY session_id, tick;

-- ───────── v_global_phi_balance ─────────
CREATE OR REPLACE VIEW v_global_phi_balance AS
WITH periphery_outflow AS (
    SELECT session_id, tick,
           SUM(phi_year_inflow) / 52.0 AS phi_week_outflow_total
    FROM dynamic_external_node_state
    WHERE kind = 'international'
    GROUP BY session_id, tick
),
core_inflow AS (
    SELECT session_id, tick,
           SUM(magnitude) AS phi_week_inflow_total
    FROM boundary_flow_register
    WHERE flow_type = 'drain_edge' AND dest_kind = 'county'
    GROUP BY session_id, tick
)
SELECT
    p.session_id,
    p.tick,
    p.phi_week_outflow_total,
    COALESCE(c.phi_week_inflow_total, 0) AS phi_week_inflow_total,
    p.phi_week_outflow_total - COALESCE(c.phi_week_inflow_total, 0) AS residual
FROM periphery_outflow p
LEFT JOIN core_inflow c USING (session_id, tick);
