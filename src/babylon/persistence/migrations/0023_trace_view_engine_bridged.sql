-- 0023_trace_view_engine_bridged.sql
-- Spec-065 engine-bridging T009.
-- Recreates view_runtime_trace_emission (originally migration 0019) to
-- JOIN the three new spec-065 subsystem tables:
--   * dynamic_consciousness_state (migration 0020)
--   * dynamic_demographics_state  (migration 0021)
--   * dynamic_employment_state    (migration 0022)
--
-- Per II.11: this view IS the declared cross-subsystem read interface.
-- The 22-column external contract from
-- specs/064-headless-sim-runner/contracts/trace_csv_schema.yaml is
-- unchanged; previously-NULL columns are now sourced from the new
-- subsystem tables via LEFT JOIN on (session_id, tick, county_fips).
--
-- Migration 0019 emitted NULL for: p_acquiescence, p_revolution,
-- ideology_r, ideology_l, ideology_f, population, employment_proxy.
-- Migration 0023 sources all seven from real per-tick subsystem data
-- when the subsystem has written rows; otherwise LEFT JOIN preserves
-- NULL (which the trace_emitter writes as empty string per FR-008).

DROP VIEW IF EXISTS view_runtime_trace_emission;

CREATE VIEW view_runtime_trace_emission AS
SELECT
    h.session_id,
    h.tick,
    h.county_fips                              AS entity_id,
    'county'::TEXT                             AS entity_kind,
    -- Marx primitives (sum hex → county; spec-064 ordering: v, c, s, k)
    SUM(h.v)                                   AS v,
    SUM(h.c)                                   AS c,
    SUM(h.s)                                   AS s,
    SUM(h.k)                                   AS k,
    -- Consciousness (per-county, from 0020 table)
    cs.p_acquiescence,
    cs.p_revolution,
    cs.ideology_r,
    cs.ideology_l,
    cs.ideology_f,
    -- Territory ratios (intensive — avg hex → county)
    AVG(h.surveillance_coupling)               AS surveillance_coupling,
    AVG(h.internet_access_pct)                 AS internet_access_pct,
    -- Substrate stocks (extensive — sum hex → county)
    SUM(h.biocapacity_stock)                   AS biocapacity_stock,
    SUM(h.energy_stock)                        AS energy_stock,
    SUM(h.raw_material_stock)                  AS raw_material_stock,
    -- Derived rates (computed in-view; NULL on degenerate denominators)
    CASE WHEN SUM(h.c) + SUM(h.v) > 0
         THEN SUM(h.s) / (SUM(h.c) + SUM(h.v))
         ELSE NULL
    END                                        AS profit_rate,
    CASE WHEN SUM(h.v) > 0
         THEN SUM(h.s) / SUM(h.v)
         ELSE NULL
    END                                        AS exploitation_rate,
    -- Demographics + employment (per-county, from 0021/0022 tables)
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
    'spec-065 trace emission contract. Owned by headless_runner feature. '
    'Per Constitution II.11: cross-subsystem read via declared interface. '
    'JOINs hex_state (Marx primitives + substrate + territory ratios), '
    'consciousness_state (ternary simplex + survival calculus), '
    'demographics_state (population), employment_state (employment_proxy). '
    'Every column in the 22-column trace_csv_schema.yaml contract is '
    'sourceable from this view. Previous spec-064 NULL columns now flow '
    'from the new per-tick subsystem tables when the engine bridge has '
    'written rows; otherwise LEFT JOIN preserves NULL (FR-008).';
