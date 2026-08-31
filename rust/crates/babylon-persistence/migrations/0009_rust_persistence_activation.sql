-- Epoch 9 is deliberately destructive and forward-only. Every frozen
-- Python-owned relation must be empty before it can be classified as
-- unreachable and removed. A non-empty predecessor is a hard refusal: this
-- migration never guesses how to translate historical game state.
DO $rust_persistence_activation_preflight$
DECLARE
    relation_name pg_catalog.text;
    relation_oid pg_catalog.regclass;
    relation_kind "char";
    row_count pg_catalog.int8;
BEGIN
    FOR relation_name IN
        SELECT expected.relation_name
        FROM pg_catalog.unnest(ARRAY[
            'babylon_meta.breadcrumb',
            'babylon_meta.campaign',
            'babylon_meta.jumplist',
            'babylon_meta.watchlist',
            'public.action_result',
            'public.balkanization_claims_audit',
            'public.balkanization_influences_audit',
            'public.boundary_flow_register',
            'public.class_snapshot',
            'public.community_membership',
            'public.community_snapshot',
            'public.community_state',
            'public.conservation_audit_log',
            'public.contradiction_field',
            'public.dynamic_consciousness_state',
            'public.dynamic_demographics_state',
            'public.dynamic_employment_state',
            'public.dynamic_external_node_state',
            'public.dynamic_hex_state',
            'public.dynamic_relationship_state',
            'public.economic_summary',
            'public.edge_curvature',
            'public.edge_snapshot',
            'public.edge_state',
            'public.game_defines_snapshot',
            'public.game_session',
            'public.game_turn',
            'public.graph_metadata',
            'public.hex_activity',
            'public.hex_cell',
            'public.hex_latest',
            'public.hex_map',
            'public.hex_r8_linear_features_reference',
            'public.hex_r8_reference',
            'public.hex_spatial_map',
            'public.hex_state',
            'public.hex_substrate',
            'public.hex_terrain_state',
            'public.immutable_reference_basket_gamma',
            'public.immutable_reference_bea_io',
            'public.immutable_reference_bea_reis_rent',
            'public.immutable_reference_border_commute_synthesis',
            'public.immutable_reference_erdi',
            'public.immutable_reference_faf_freight',
            'public.immutable_reference_fred_rates',
            'public.immutable_reference_hickel_drain',
            'public.immutable_reference_lodes_od_matrix',
            'public.immutable_reference_melt_tau',
            'public.immutable_reference_qcew_employment',
            'public.immutable_reference_ricci_unequal',
            'public.immutable_reference_tiger_county',
            'public.infrastructure_link_state',
            'public.node_state',
            'public.org_snapshot',
            'public.runtime_administers_edges',
            'public.runtime_claims_edges',
            'public.runtime_influences_edges',
            'public.runtime_political_factions',
            'public.runtime_sovereigns',
            'public.simulation_event',
            'public.territory_snapshot',
            'public.tick_commit',
            'public.tick_event',
            'public.tick_log',
            'public.tick_summary'
        ]::pg_catalog.text[]) AS expected(relation_name)
        ORDER BY expected.relation_name
    LOOP
        relation_oid := pg_catalog.to_regclass(relation_name);
        IF relation_oid IS NULL THEN
            CONTINUE;
        END IF;
        SELECT relation.relkind
          INTO relation_kind
          FROM pg_catalog.pg_class AS relation
         WHERE relation.oid = relation_oid;
        IF relation_kind NOT IN ('r', 'p') THEN
            RAISE EXCEPTION
                'epoch 9 expected % to be a base or partitioned table, found relkind %',
                relation_name,
                relation_kind;
        END IF;
        EXECUTE pg_catalog.format(
            'SELECT pg_catalog.count(*) FROM %s', relation_oid
        ) INTO row_count;
        IF row_count <> 0 THEN
            RAISE EXCEPTION
                'epoch 9 refuses non-empty Python relation % (% rows)',
                relation_name,
                row_count;
        END IF;
        INSERT INTO babylon_meta.python_relation_disposition_v1 (
            relation_name,
            observed_row_count,
            ordered_semantic_sha256,
            disposition_tag
        ) VALUES (
            relation_name,
            0,
            pg_catalog.sha256(''::pg_catalog.bytea),
            1
        );
    END LOOP;
END
$rust_persistence_activation_preflight$;

DROP VIEW IF EXISTS public.v_national_trend;
DROP VIEW IF EXISTS public.v_global_phi_balance;
DROP VIEW IF EXISTS public.v_county_value_aggregate;
DROP VIEW IF EXISTS public.v_hex_aid;
DROP VIEW IF EXISTS public.v_hex_economic;
DROP VIEW IF EXISTS public.v_hex_heat;
DROP VIEW IF EXISTS public.v_hex_intel;
DROP VIEW IF EXISTS public.v_hex_mobilize;
DROP VIEW IF EXISTS public.v_hex_state_asof;
DROP VIEW IF EXISTS public.v_national_value_aggregate;
DROP VIEW IF EXISTS public.v_state_value_aggregate;
DROP VIEW IF EXISTS public.view_runtime_trace_emission;

DROP TABLE IF EXISTS
    babylon_meta.breadcrumb,
    babylon_meta.jumplist,
    babylon_meta.watchlist,
    babylon_meta.campaign,
    public.action_result,
    public.balkanization_claims_audit,
    public.balkanization_influences_audit,
    public.boundary_flow_register,
    public.class_snapshot,
    public.community_membership,
    public.community_snapshot,
    public.community_state,
    public.conservation_audit_log,
    public.contradiction_field,
    public.dynamic_consciousness_state,
    public.dynamic_demographics_state,
    public.dynamic_employment_state,
    public.dynamic_external_node_state,
    public.dynamic_hex_state,
    public.dynamic_relationship_state,
    public.economic_summary,
    public.edge_curvature,
    public.edge_snapshot,
    public.edge_state,
    public.game_defines_snapshot,
    public.game_turn,
    public.graph_metadata,
    public.hex_activity,
    public.hex_latest,
    public.hex_map,
    public.hex_r8_linear_features_reference,
    public.hex_r8_reference,
    public.hex_spatial_map,
    public.hex_state,
    public.hex_substrate,
    public.hex_terrain_state,
    public.immutable_reference_basket_gamma,
    public.immutable_reference_bea_io,
    public.immutable_reference_bea_reis_rent,
    public.immutable_reference_border_commute_synthesis,
    public.immutable_reference_erdi,
    public.immutable_reference_faf_freight,
    public.immutable_reference_fred_rates,
    public.immutable_reference_hickel_drain,
    public.immutable_reference_lodes_od_matrix,
    public.immutable_reference_melt_tau,
    public.immutable_reference_qcew_employment,
    public.immutable_reference_ricci_unequal,
    public.immutable_reference_tiger_county,
    public.infrastructure_link_state,
    public.node_state,
    public.org_snapshot,
    public.runtime_administers_edges,
    public.runtime_claims_edges,
    public.runtime_influences_edges,
    public.runtime_political_factions,
    public.runtime_sovereigns,
    public.simulation_event,
    public.territory_snapshot,
    public.tick_commit,
    public.tick_event,
    public.tick_log,
    public.tick_summary,
    public.hex_cell,
    public.game_session;

DROP TABLE IF EXISTS public._babylon_schema_stamp;

DO $rust_persistence_opaque_preflight$
DECLARE
    nonempty_count pg_catalog.int8;
BEGIN
    SELECT
        (SELECT pg_catalog.count(*) FROM babylon_state.tick_graph_row)
      + (SELECT pg_catalog.count(*) FROM babylon_state.tick_state_row)
      + (SELECT pg_catalog.count(*) FROM babylon_state.tick_event_row)
      + (SELECT pg_catalog.count(*) FROM babylon_state.tick_subsystem_row)
      + (SELECT pg_catalog.count(*) FROM babylon_state.tick_conservation_row)
      + (SELECT pg_catalog.count(*) FROM babylon_state.tick_boundary_flow_row)
      + (SELECT pg_catalog.count(*) FROM babylon_state.tick_checkpoint_row)
      + (SELECT pg_catalog.count(*) FROM babylon_state.tick_archive_dirty_receipt_row)
      INTO nonempty_count;
    IF nonempty_count <> 0 THEN
        RAISE EXCEPTION
            'epoch 9 refuses unproved opaque Rust rows (% rows)', nonempty_count;
    END IF;
END
$rust_persistence_opaque_preflight$;

DROP TABLE babylon_state.tick_archive_dirty_receipt_row;
DROP TABLE babylon_state.tick_checkpoint_row;
DROP TABLE babylon_state.tick_boundary_flow_row;
DROP TABLE babylon_state.tick_conservation_row;
DROP TABLE babylon_state.tick_subsystem_row;
DROP TABLE babylon_state.tick_event_row;
DROP TABLE babylon_state.tick_state_row;
DROP TABLE babylon_state.tick_graph_row;

ALTER TABLE babylon_state.tick_commit
    DROP CONSTRAINT tick_commit_resolve_tick_sql_range;
ALTER TABLE babylon_state.tick_commit
    ADD CONSTRAINT tick_commit_resolve_tick_sql_range CHECK (resolve_tick >= 1);
