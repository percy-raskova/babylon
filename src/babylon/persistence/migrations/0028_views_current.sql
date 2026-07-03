-- 0028_views_current.sql
-- Spec 088 (S2a, FR-003) — THE canonical view file.
--
-- Migration 0026's converting pass drops the 5 views that depend on the
-- per-tick tables (views bind to table OIDs and would otherwise chase the
-- conversion RENAME). This file recreates all of them and runs at the end
-- of every migration pass, so the view definitions here are authoritative:
-- later specs edit THIS file, never 0015/0019/0023 (whose definitions
-- remain valid for the fresh-DB passes that execute before 0026).
-- 0027 is reserved for S3's hex_map normalization.
--
-- Definitions are verbatim 0015 (aggregation views) + 0023 (trace view).

DROP VIEW IF EXISTS view_runtime_trace_emission;
DROP VIEW IF EXISTS v_global_phi_balance;
DROP VIEW IF EXISTS v_national_value_aggregate;
DROP VIEW IF EXISTS v_state_value_aggregate;
DROP VIEW IF EXISTS v_county_value_aggregate;

-- ───────── v_county_value_aggregate (0015) ─────────
CREATE VIEW v_county_value_aggregate AS
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

-- ───────── v_state_value_aggregate (0015) ─────────
CREATE VIEW v_state_value_aggregate AS
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

-- ───────── v_national_value_aggregate (0015) ─────────
CREATE VIEW v_national_value_aggregate AS
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

-- ───────── v_global_phi_balance (0015) ─────────
CREATE VIEW v_global_phi_balance AS
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

-- ───────── view_runtime_trace_emission (0023) ─────────
CREATE VIEW view_runtime_trace_emission AS
SELECT
    h.session_id,
    h.tick,
    h.county_fips                              AS entity_id,
    'county'::TEXT                             AS entity_kind,
    SUM(h.v)                                   AS v,
    SUM(h.c)                                   AS c,
    SUM(h.s)                                   AS s,
    SUM(h.k)                                   AS k,
    cs.p_acquiescence,
    cs.p_revolution,
    cs.ideology_r,
    cs.ideology_l,
    cs.ideology_f,
    AVG(h.surveillance_coupling)               AS surveillance_coupling,
    AVG(h.internet_access_pct)                 AS internet_access_pct,
    SUM(h.biocapacity_stock)                   AS biocapacity_stock,
    SUM(h.energy_stock)                        AS energy_stock,
    SUM(h.raw_material_stock)                  AS raw_material_stock,
    CASE WHEN SUM(h.c) + SUM(h.v) > 0
         THEN SUM(h.s) / (SUM(h.c) + SUM(h.v))
         ELSE NULL
    END                                        AS profit_rate,
    CASE WHEN SUM(h.v) > 0
         THEN SUM(h.s) / SUM(h.v)
         ELSE NULL
    END                                        AS exploitation_rate,
    dem.population,
    emp.employment_proxy
FROM dynamic_hex_state h
LEFT JOIN dynamic_consciousness_state cs
       ON cs.session_id = h.session_id
      AND cs.tick = h.tick
      AND cs.county_fips = h.county_fips
LEFT JOIN dynamic_demographics_state dem
       ON dem.session_id = h.session_id
      AND dem.tick = h.tick
      AND dem.county_fips = h.county_fips
LEFT JOIN dynamic_employment_state emp
       ON emp.session_id = h.session_id
      AND emp.tick = h.tick
      AND emp.county_fips = h.county_fips
GROUP BY h.session_id, h.tick, h.county_fips,
         cs.p_acquiescence, cs.p_revolution,
         cs.ideology_r, cs.ideology_l, cs.ideology_f,
         dem.population, emp.employment_proxy;

GRANT SELECT ON view_runtime_trace_emission TO PUBLIC;

COMMENT ON VIEW view_runtime_trace_emission IS
    'spec-065 trace emission contract; canonical definition lives in '
    '0028_views_current.sql per spec-088 FR-003 (view lifecycle survives '
    'the 0026 partition conversion). 22-column trace_csv_schema.yaml '
    'contract unchanged.';
