-- 0030_views_current.sql
-- THE canonical view file (spec-088 FR-003; spec-089 S1c rewrite).
--
-- Always executed at the end of every migration pass; later specs edit
-- THIS file, never 0015/0019/0023 (whose definitions remain valid for the
-- fresh-DB passes that execute before 0026).
--
-- Spec-089 delta persistence: dynamic_hex_state is now SPARSE — a hex row
-- appears only when its value tuple changed, plus a full checkpoint frame
-- every 52 ticks (and tick 0). Every hex-sourced view therefore
-- reconstructs on read (Constitution FR-019: aggregation without stored
-- duplicates; hex remains the only persisted source of truth):
--
--   intervals      each hex row is valid [tick, next_tick)
--   change_ticks   ticks where any hex row was written
--   county_events  county aggregates AT change ticks (as-of interval join
--                  — cheap: |change_ticks| × |hexes|, not ticks × hexes)
--   spine          all committed ticks (tick_commit ∪ hex-row ticks, so
--                  pre-tick_commit sessions keep working)
--   fill-forward   county value at tick t = latest event ≤ t
--
-- For pre-delta (dense) sessions every tick is a change tick and the
-- as-of join degenerates to exactly the old per-tick GROUP BY.
-- Spatial keys resolve via hex_spatial_map (spec-088 S3) with COALESCE
-- fallback to inline legacy values.

DROP VIEW IF EXISTS view_runtime_trace_emission;
DROP VIEW IF EXISTS v_global_phi_balance;
DROP VIEW IF EXISTS v_national_value_aggregate;
DROP VIEW IF EXISTS v_state_value_aggregate;
DROP VIEW IF EXISTS v_county_value_aggregate;
DROP VIEW IF EXISTS v_hex_state_asof;

-- ───────── v_hex_state_asof (spec-089 FR-009) ─────────
-- Full-resolution reconstruction: the hex frame at every committed tick.
-- The declared hex-level history read interface.
CREATE VIEW v_hex_state_asof AS
WITH spine AS (
    SELECT session_id, tick FROM tick_commit
    UNION
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
),
intervals AS (
    SELECT h.session_id, h.h3_index, h.tick,
           COALESCE(m.county_fips, h.county_fips) AS county_fips,
           COALESCE(m.state_fips, h.state_fips)   AS state_fips,
           COALESCE(m.region_id, h.region_id)     AS region_id,
           h.c, h.v, h.s, h.k,
           h.biocapacity_stock, h.energy_stock, h.raw_material_stock,
           h.internet_access_pct, h.surveillance_coupling,
           LEAD(h.tick) OVER (
               PARTITION BY h.session_id, h.h3_index ORDER BY h.tick
           ) AS next_tick
    FROM dynamic_hex_state h
    LEFT JOIN hex_spatial_map m USING (h3_index)
)
SELECT sp.session_id, sp.tick,
       hi.h3_index, hi.county_fips, hi.state_fips, hi.region_id,
       hi.c, hi.v, hi.s, hi.k,
       hi.biocapacity_stock, hi.energy_stock, hi.raw_material_stock,
       hi.internet_access_pct, hi.surveillance_coupling,
       hi.tick AS written_at_tick
FROM spine sp
JOIN intervals hi
  ON hi.session_id = sp.session_id
 AND hi.tick <= sp.tick
 AND (hi.next_tick IS NULL OR sp.tick < hi.next_tick);

-- ───────── v_county_value_aggregate (0015 contract; as-of filled) ─────────
CREATE VIEW v_county_value_aggregate AS
WITH change_ticks AS (
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
),
intervals AS (
    SELECT h.session_id, h.h3_index, h.tick,
           COALESCE(m.county_fips, h.county_fips) AS county_fips,
           h.c, h.v, h.s, h.k, h.biocapacity_stock,
           LEAD(h.tick) OVER (
               PARTITION BY h.session_id, h.h3_index ORDER BY h.tick
           ) AS next_tick
    FROM dynamic_hex_state h
    LEFT JOIN hex_spatial_map m USING (h3_index)
),
county_events AS (
    SELECT ct.session_id, ct.tick, hi.county_fips,
           SUM(hi.c) AS c_sum,
           SUM(hi.v) AS v_sum,
           SUM(hi.s) AS s_sum,
           SUM(hi.k) AS k_sum,
           SUM(hi.biocapacity_stock) AS biocapacity_sum,
           COUNT(*) AS hex_count
    FROM change_ticks ct
    JOIN intervals hi
      ON hi.session_id = ct.session_id
     AND hi.tick <= ct.tick
     AND (hi.next_tick IS NULL OR ct.tick < hi.next_tick)
    GROUP BY ct.session_id, ct.tick, hi.county_fips
),
county_intervals AS (
    SELECT ce.*,
           LEAD(ce.tick) OVER (
               PARTITION BY ce.session_id, ce.county_fips ORDER BY ce.tick
           ) AS next_tick
    FROM county_events ce
),
spine AS (
    SELECT session_id, tick FROM tick_commit
    UNION
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
)
SELECT sp.session_id, sp.tick, ci.county_fips,
       ci.c_sum, ci.v_sum, ci.s_sum, ci.k_sum, ci.biocapacity_sum,
       ci.hex_count
FROM spine sp
JOIN county_intervals ci
  ON ci.session_id = sp.session_id
 AND ci.tick <= sp.tick
 AND (ci.next_tick IS NULL OR sp.tick < ci.next_tick);

-- ───────── v_state_value_aggregate (0015 contract; as-of filled) ─────────
CREATE VIEW v_state_value_aggregate AS
WITH change_ticks AS (
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
),
intervals AS (
    SELECT h.session_id, h.h3_index, h.tick,
           COALESCE(m.state_fips, h.state_fips) AS state_fips,
           h.c, h.v, h.s, h.k, h.biocapacity_stock,
           LEAD(h.tick) OVER (
               PARTITION BY h.session_id, h.h3_index ORDER BY h.tick
           ) AS next_tick
    FROM dynamic_hex_state h
    LEFT JOIN hex_spatial_map m USING (h3_index)
),
state_events AS (
    SELECT ct.session_id, ct.tick, hi.state_fips,
           SUM(hi.c) AS c_sum,
           SUM(hi.v) AS v_sum,
           SUM(hi.s) AS s_sum,
           SUM(hi.k) AS k_sum,
           SUM(hi.biocapacity_stock) AS biocapacity_sum,
           COUNT(*) AS hex_count
    FROM change_ticks ct
    JOIN intervals hi
      ON hi.session_id = ct.session_id
     AND hi.tick <= ct.tick
     AND (hi.next_tick IS NULL OR ct.tick < hi.next_tick)
    GROUP BY ct.session_id, ct.tick, hi.state_fips
),
state_intervals AS (
    SELECT se.*,
           LEAD(se.tick) OVER (
               PARTITION BY se.session_id, se.state_fips ORDER BY se.tick
           ) AS next_tick
    FROM state_events se
),
spine AS (
    SELECT session_id, tick FROM tick_commit
    UNION
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
)
SELECT sp.session_id, sp.tick, si.state_fips,
       si.c_sum, si.v_sum, si.s_sum, si.k_sum, si.biocapacity_sum,
       si.hex_count
FROM spine sp
JOIN state_intervals si
  ON si.session_id = sp.session_id
 AND si.tick <= sp.tick
 AND (si.next_tick IS NULL OR sp.tick < si.next_tick);

-- ───────── v_national_value_aggregate (0015 contract; as-of filled) ─────────
CREATE VIEW v_national_value_aggregate AS
WITH change_ticks AS (
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
),
intervals AS (
    SELECT h.session_id, h.h3_index, h.tick,
           h.c, h.v, h.s, h.k, h.biocapacity_stock,
           LEAD(h.tick) OVER (
               PARTITION BY h.session_id, h.h3_index ORDER BY h.tick
           ) AS next_tick
    FROM dynamic_hex_state h
),
national_events AS (
    SELECT ct.session_id, ct.tick,
           SUM(hi.c) AS c_sum,
           SUM(hi.v) AS v_sum,
           SUM(hi.s) AS s_sum,
           SUM(hi.k) AS k_sum,
           SUM(hi.biocapacity_stock) AS biocapacity_sum,
           COUNT(*) AS hex_count
    FROM change_ticks ct
    JOIN intervals hi
      ON hi.session_id = ct.session_id
     AND hi.tick <= ct.tick
     AND (hi.next_tick IS NULL OR ct.tick < hi.next_tick)
    GROUP BY ct.session_id, ct.tick
),
national_intervals AS (
    SELECT ne.*,
           LEAD(ne.tick) OVER (
               PARTITION BY ne.session_id ORDER BY ne.tick
           ) AS next_tick
    FROM national_events ne
),
spine AS (
    SELECT session_id, tick FROM tick_commit
    UNION
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
)
SELECT sp.session_id, sp.tick,
       'USA'::TEXT AS national_id,
       ni.c_sum, ni.v_sum, ni.s_sum, ni.k_sum, ni.biocapacity_sum,
       ni.hex_count
FROM spine sp
JOIN national_intervals ni
  ON ni.session_id = sp.session_id
 AND ni.tick <= sp.tick
 AND (ni.next_tick IS NULL OR sp.tick < ni.next_tick);

-- ───────── v_global_phi_balance (0015; dense sources, unchanged) ─────────
-- external-node + boundary rows stay dense per tick (spec-089 FR-007).
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

-- ───────── view_runtime_trace_emission (0023 contract; as-of filled) ─────────
CREATE VIEW view_runtime_trace_emission AS
WITH change_ticks AS (
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
),
intervals AS (
    SELECT h.session_id, h.h3_index, h.tick,
           COALESCE(m.county_fips, h.county_fips) AS county_fips,
           h.c, h.v, h.s, h.k,
           h.biocapacity_stock, h.energy_stock, h.raw_material_stock,
           h.internet_access_pct, h.surveillance_coupling,
           LEAD(h.tick) OVER (
               PARTITION BY h.session_id, h.h3_index ORDER BY h.tick
           ) AS next_tick
    FROM dynamic_hex_state h
    LEFT JOIN hex_spatial_map m USING (h3_index)
),
county_events AS (
    SELECT ct.session_id, ct.tick, hi.county_fips,
           SUM(hi.v) AS v,
           SUM(hi.c) AS c,
           SUM(hi.s) AS s,
           SUM(hi.k) AS k,
           AVG(hi.surveillance_coupling) AS surveillance_coupling,
           AVG(hi.internet_access_pct)   AS internet_access_pct,
           SUM(hi.biocapacity_stock)     AS biocapacity_stock,
           SUM(hi.energy_stock)          AS energy_stock,
           SUM(hi.raw_material_stock)    AS raw_material_stock,
           CASE WHEN SUM(hi.c) + SUM(hi.v) > 0
                THEN SUM(hi.s) / (SUM(hi.c) + SUM(hi.v))
                ELSE NULL
           END AS profit_rate,
           CASE WHEN SUM(hi.v) > 0
                THEN SUM(hi.s) / SUM(hi.v)
                ELSE NULL
           END AS exploitation_rate
    FROM change_ticks ct
    JOIN intervals hi
      ON hi.session_id = ct.session_id
     AND hi.tick <= ct.tick
     AND (hi.next_tick IS NULL OR ct.tick < hi.next_tick)
    GROUP BY ct.session_id, ct.tick, hi.county_fips
),
county_intervals AS (
    SELECT ce.*,
           LEAD(ce.tick) OVER (
               PARTITION BY ce.session_id, ce.county_fips ORDER BY ce.tick
           ) AS next_tick
    FROM county_events ce
),
spine AS (
    SELECT session_id, tick FROM tick_commit
    UNION
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
)
SELECT
    sp.session_id,
    sp.tick,
    ci.county_fips                             AS entity_id,
    'county'::TEXT                             AS entity_kind,
    ci.v,
    ci.c,
    ci.s,
    ci.k,
    cs.p_acquiescence,
    cs.p_revolution,
    cs.ideology_r,
    cs.ideology_l,
    cs.ideology_f,
    ci.surveillance_coupling,
    ci.internet_access_pct,
    ci.biocapacity_stock,
    ci.energy_stock,
    ci.raw_material_stock,
    ci.profit_rate,
    ci.exploitation_rate,
    dem.population,
    emp.employment_proxy
FROM spine sp
JOIN county_intervals ci
  ON ci.session_id = sp.session_id
 AND ci.tick <= sp.tick
 AND (ci.next_tick IS NULL OR sp.tick < ci.next_tick)
LEFT JOIN dynamic_consciousness_state cs
       ON cs.session_id = sp.session_id
      AND cs.tick = sp.tick
      AND cs.county_fips = ci.county_fips
LEFT JOIN dynamic_demographics_state dem
       ON dem.session_id = sp.session_id
      AND dem.tick = sp.tick
      AND dem.county_fips = ci.county_fips
LEFT JOIN dynamic_employment_state emp
       ON emp.session_id = sp.session_id
      AND emp.tick = sp.tick
      AND emp.county_fips = ci.county_fips;

GRANT SELECT ON v_hex_state_asof TO PUBLIC;
GRANT SELECT ON view_runtime_trace_emission TO PUBLIC;

COMMENT ON VIEW view_runtime_trace_emission IS
    'spec-065 trace emission contract; canonical definition lives in '
    '0030_views_current.sql (spec-088 FR-003). As-of fill-forward over '
    'delta-persisted hex rows (spec-089 S1c): every committed tick yields '
    'a row per county. 22-column trace_csv_schema.yaml contract unchanged.';

COMMENT ON VIEW v_hex_state_asof IS
    'spec-089 FR-009: full-resolution hex frame reconstructed at every '
    'committed tick (checkpoint + deltas, fill-forward). The declared '
    'hex-level history read interface; hex res-7 remains the only '
    'persisted source of truth (FR-019).';
