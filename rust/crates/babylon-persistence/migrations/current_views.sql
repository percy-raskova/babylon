-- Current read-only projections; privileges are provisioned separately.

CREATE VIEW public.v_committed_tick_status_v1 AS
SELECT
    campaign_id,
    resolve_tick,
    envelope_layout_version,
    tick_content_hash,
    envelope_digest
FROM babylon_state.tick_commit;
REVOKE ALL ON public.v_committed_tick_status_v1 FROM PUBLIC;

CREATE VIEW public.v_observer_economy_foundation_v1 AS
SELECT foundation.campaign_id, foundation.foundation_sha256,
       pg_catalog.sha256(foundation.content_bundle_bytes) AS source_sha256,
       campaign.geography_scope
FROM babylon_state.campaign_foundation AS foundation
JOIN babylon_state.campaign AS campaign USING (campaign_id);

CREATE VIEW public.v_observer_county_economy_v1 AS
SELECT foundation.campaign_id, 0::bigint AS resolve_tick, mapping.county_geoid,
       NULL::bigint AS annual_avg_estabs_count, NULL::bigint AS annual_avg_emplvl,
       NULL::bigint AS total_annual_wages, NULL::bigint AS annual_avg_wkly_wage,
       true AS establishments_granted, true AS employment_granted,
       true AS annual_wages_granted, true AS weekly_wage_granted
FROM babylon_state.campaign_foundation AS foundation
JOIN babylon_meta.territory_county_map_v1 AS mapping USING (campaign_id)
UNION ALL
SELECT membership.campaign_id, membership.resolve_tick,
       pg_catalog.lpad(identity.int_value::text, 5, '0') AS county_geoid,
       max(fields.int_value) FILTER (WHERE fields.field_name = 'qcew-establishments'),
       max(fields.int_value) FILTER (WHERE fields.field_name = 'qcew-employment'),
       max(fields.int_value) FILTER (WHERE fields.field_name = 'qcew-total-annual-wages'),
       max(fields.int_value) FILTER (WHERE fields.field_name = 'qcew-average-weekly-wage'),
       true, true, true, true
FROM babylon_state.territory_tick_membership_v1 AS membership
JOIN babylon_state.territory_definition_v1 AS definition USING (campaign_id, definition_id)
JOIN babylon_state.territory_definition_field_v1 AS fields USING (campaign_id, definition_id)
JOIN babylon_state.territory_definition_field_v1 AS identity USING (campaign_id, definition_id)
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = membership.campaign_id AND marker.resolve_tick = membership.resolve_tick
WHERE identity.field_name = 'county-fips' AND identity.value_tag = 1
  AND fields.value_tag = 1 AND fields.field_name IN
  ('qcew-establishments', 'qcew-employment', 'qcew-total-annual-wages', 'qcew-average-weekly-wage')
GROUP BY membership.campaign_id, membership.resolve_tick, identity.int_value
UNION ALL
-- National counties carry identity in the graph. Their published QCEW values
-- remain immutable captured observations, never synthetic dynamic state fields.
SELECT foundation.campaign_id, marker.resolve_tick, mapping.county_geoid,
       NULL::bigint, NULL::bigint, NULL::bigint, NULL::bigint,
       true, true, true, true
FROM babylon_state.campaign_foundation AS foundation
JOIN babylon_meta.territory_county_map_v1 AS mapping USING (campaign_id)
JOIN babylon_state.tick_commit AS marker USING (campaign_id)
JOIN babylon_state.campaign AS campaign USING (campaign_id)
WHERE campaign.geography_scope = 'national-counties';

CREATE VIEW public.v_known_county_economy_v1 WITH (security_barrier = true) AS
SELECT raw.campaign_id, raw.resolve_tick, raw.county_geoid,
       CASE WHEN permission.establishments THEN raw.annual_avg_estabs_count END AS annual_avg_estabs_count,
       CASE WHEN permission.employment THEN raw.annual_avg_emplvl END AS annual_avg_emplvl,
       CASE WHEN permission.annual_wages THEN raw.total_annual_wages END AS total_annual_wages,
       CASE WHEN permission.weekly_wage THEN raw.annual_avg_wkly_wage END AS annual_avg_wkly_wage,
       permission.establishments AS establishments_granted,
       permission.employment AS employment_granted,
       permission.annual_wages AS annual_wages_granted,
       permission.weekly_wage AS weekly_wage_granted
FROM public.v_observer_county_economy_v1 AS raw
CROSS JOIN LATERAL (
  -- County mappings use C collation; the grant primary key uses the database
  -- default. Match that indexed collation explicitly for these ASCII IDs.
  SELECT
    EXISTS (SELECT 1 FROM babylon_meta.archive_knowledge_grant_v1 AS grant_row
      WHERE grant_row.campaign_id = raw.campaign_id AND grant_row.subject_kind = 'county'
        AND grant_row.subject_id = raw.county_geoid COLLATE pg_catalog."default"
        AND grant_row.granted_tick <= raw.resolve_tick
        AND grant_row.grant_key = 'qcew-establishments') AS establishments,
    EXISTS (SELECT 1 FROM babylon_meta.archive_knowledge_grant_v1 AS grant_row
      WHERE grant_row.campaign_id = raw.campaign_id AND grant_row.subject_kind = 'county'
        AND grant_row.subject_id = raw.county_geoid COLLATE pg_catalog."default"
        AND grant_row.granted_tick <= raw.resolve_tick
        AND grant_row.grant_key = 'qcew-employment') AS employment,
    EXISTS (SELECT 1 FROM babylon_meta.archive_knowledge_grant_v1 AS grant_row
      WHERE grant_row.campaign_id = raw.campaign_id AND grant_row.subject_kind = 'county'
        AND grant_row.subject_id = raw.county_geoid COLLATE pg_catalog."default"
        AND grant_row.granted_tick <= raw.resolve_tick
        AND grant_row.grant_key = 'qcew-total-annual-wages') AS annual_wages,
    EXISTS (SELECT 1 FROM babylon_meta.archive_knowledge_grant_v1 AS grant_row
      WHERE grant_row.campaign_id = raw.campaign_id AND grant_row.subject_kind = 'county'
        AND grant_row.subject_id = raw.county_geoid COLLATE pg_catalog."default"
        AND grant_row.granted_tick <= raw.resolve_tick
        AND grant_row.grant_key = 'qcew-average-weekly-wage') AS weekly_wage
) AS permission;

CREATE VIEW public.v_material_campaign_identity_v2 AS
SELECT campaign_id, preset_id, duration_kind, final_period, content_sha256, foundation_sha256
FROM babylon_state.material_campaign_foundation_v3;

-- Captured sources belong to the full observer capability only.
CREATE VIEW public.v_observer_material_foundation_v1 AS
SELECT f.campaign_id, f.preset_id, f.duration_kind, f.final_period,
       f.content_sha256, f.initial_register_bytes, f.foundation_sha256,
       g.foundation_sha256 AS graph_foundation_sha256,
       g.stable_graph, g.world_registers, g.resolver_manifest, g.prepared_environment,
       g.replay_session_id, g.rng_seed, g.defines_hash, g.rules_hash, g.ref_digest,
       g.content_bundle_bytes
FROM babylon_state.material_campaign_foundation_v3 AS f
JOIN babylon_state.campaign_foundation AS g USING (campaign_id);
REVOKE ALL ON public.v_observer_material_foundation_v1 FROM PUBLIC;

-- Only the observer group receives complete material bytes. Known preview has
-- no grant on this view or the underlying tables; projection cannot undo that.
CREATE VIEW public.v_observer_material_state_v1 AS
SELECT campaign_id, 0::bigint AS resolve_tick, initial_register_bytes AS register_storage_bytes,
       NULL::bytea AS receipt_storage_bytes, NULL::bytea AS identity_bytes,
       NULL::bytea AS tick_content_hash, NULL::bytea AS lookup_delta_bytes
FROM babylon_state.material_campaign_foundation_v3
UNION ALL
SELECT state.campaign_id, state.resolve_tick, state.register_storage_bytes,
       state.receipt_storage_bytes, state.identity_bytes, marker.tick_content_hash,
       state.lookup_delta_bytes
FROM babylon_state.material_tick_v3 AS state
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = state.campaign_id AND marker.resolve_tick = state.resolve_tick
WHERE marker.envelope_layout_version = 3;

REVOKE ALL ON public.v_material_campaign_identity_v2,
              public.v_observer_material_state_v1 FROM PUBLIC;

-- Complete persisted components for authenticated material-tick reconstruction.
-- Only the full observer receives these rows; known and Archive readers do not.

CREATE VIEW public.v_observer_graph_node_v1 AS
SELECT component.*
FROM babylon_state.graph_node_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_graph_node_f64_v1 AS
SELECT component.*
FROM babylon_state.graph_node_f64_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_graph_edge_v1 AS
SELECT component.*
FROM babylon_state.graph_edge_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_graph_hyperedge_v1 AS
SELECT component.*
FROM babylon_state.graph_hyperedge_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_graph_hyperedge_member_v1 AS
SELECT component.*
FROM babylon_state.graph_hyperedge_member_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_graph_edge_f64_v1 AS
SELECT component.*
FROM babylon_state.graph_edge_f64_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_graph_node_currency_v1 AS
SELECT component.*
FROM babylon_state.graph_node_currency_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_graph_hyperedge_f64_v1 AS
SELECT component.*
FROM babylon_state.graph_hyperedge_f64_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_world_register_v1 AS
SELECT component.*
FROM babylon_state.world_register_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_hex_state_delta_v1 AS
SELECT component.*
FROM babylon_state.hex_state_delta_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_territory_state_v1 AS
SELECT component.*
FROM babylon_state.territory_state_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_territory_state_field_v1 AS
SELECT component.*
FROM babylon_state.territory_state_field_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_organization_state_v1 AS
SELECT component.*
FROM babylon_state.organization_state_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_organization_state_field_v1 AS
SELECT component.*
FROM babylon_state.organization_state_field_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_organization_territory_v1 AS
SELECT component.*
FROM babylon_state.organization_territory_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_tick_event_v2 AS
SELECT component.*
FROM babylon_state.tick_event_v2 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_tick_event_field_v2 AS
SELECT component.*
FROM babylon_state.tick_event_field_v2 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_tick_choice_receipt_v1 AS
SELECT component.*
FROM babylon_state.tick_choice_receipt_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_tick_choice_receipt_branch_v1 AS
SELECT component.*
FROM babylon_state.tick_choice_receipt_branch_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_tick_choice_receipt_carrier_element_v1 AS
SELECT component.*
FROM babylon_state.tick_choice_receipt_carrier_element_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_checkpoint_manifest AS
SELECT component.*
FROM babylon_state.checkpoint_manifest AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

-- Current closed checkpoint source references; Rust restores canonical section bytes.
CREATE VIEW public.v_observer_checkpoint_section_v1 AS
SELECT component.*
FROM babylon_state.checkpoint_section_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_archive_dirty_receipt_v1 AS
SELECT component.*
FROM babylon_state.archive_dirty_receipt_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

CREATE VIEW public.v_observer_tick_action_batch_v1 AS
SELECT component.*
FROM babylon_state.tick_action_batch_v1 AS component
JOIN babylon_state.tick_commit AS marker
  ON marker.campaign_id = component.campaign_id
 AND marker.resolve_tick = component.resolve_tick
WHERE marker.envelope_layout_version = 3;

REVOKE ALL ON
    public.v_observer_graph_node_v1,
    public.v_observer_graph_node_f64_v1,
    public.v_observer_graph_edge_v1,
    public.v_observer_graph_hyperedge_v1,
    public.v_observer_graph_hyperedge_member_v1,
    public.v_observer_graph_edge_f64_v1,
    public.v_observer_graph_node_currency_v1,
    public.v_observer_graph_hyperedge_f64_v1,
    public.v_observer_world_register_v1,
    public.v_observer_hex_state_delta_v1,
    public.v_observer_territory_state_v1,
    public.v_observer_territory_state_field_v1,
    public.v_observer_organization_state_v1,
    public.v_observer_organization_state_field_v1,
    public.v_observer_organization_territory_v1,
    public.v_observer_tick_event_v2,
    public.v_observer_tick_event_field_v2,
    public.v_observer_tick_choice_receipt_v1,
    public.v_observer_tick_choice_receipt_branch_v1,
    public.v_observer_tick_choice_receipt_carrier_element_v1,
    public.v_observer_checkpoint_manifest,
    public.v_observer_checkpoint_section_v1,
    public.v_observer_archive_dirty_receipt_v1,
    public.v_observer_tick_action_batch_v1
FROM PUBLIC;

-- Only committed, identity-bound published evidence is exposed to the full observer.
CREATE VIEW public.v_observer_money_journal_period_v1 AS
SELECT p.* FROM babylon_state.money_journal_period_v1 p
JOIN babylon_state.tick_commit t USING (campaign_id, resolve_tick)
JOIN babylon_state.material_tick_v3 m USING (campaign_id, resolve_tick)
JOIN babylon_state.material_campaign_foundation_v3 f USING (campaign_id)
JOIN babylon_meta.current_schema s ON s.singleton AND s.schema_sha256 = p.schema_sha256
WHERE p.source_identity_bytes = m.identity_bytes AND p.tick_content_hash = t.tick_content_hash
    AND p.envelope_digest = t.envelope_digest AND p.foundation_sha256 = f.foundation_sha256
    AND p.content_sha256 = f.content_sha256;
CREATE VIEW public.v_observer_money_movement_v1 AS
SELECT d.* FROM babylon_state.money_movement_v1 d
JOIN public.v_observer_money_journal_period_v1 p USING (campaign_id, resolve_tick)
WHERE p.detail_retained;
CREATE VIEW public.v_observer_money_movement_total_v1 AS
SELECT d.* FROM babylon_state.money_movement_total_v1 d
JOIN public.v_observer_money_journal_period_v1 p USING (campaign_id, resolve_tick);
REVOKE ALL ON public.v_observer_money_journal_period_v1, public.v_observer_money_movement_v1,
    public.v_observer_money_movement_total_v1 FROM PUBLIC;

CREATE VIEW public.v_observer_economic_flow_location_v1 AS
SELECT l.*, 'tiger_county_internal_point'::text AS point_basis
FROM babylon_state.economic_flow_location_v1 l
JOIN babylon_state.material_campaign_foundation_v3 f ON f.campaign_id=l.campaign_id
    AND f.foundation_sha256=l.foundation_sha256;
REVOKE ALL ON public.v_observer_economic_flow_location_v1 FROM PUBLIC;
CREATE VIEW public.v_observer_economic_flow_account_v1 AS
SELECT a.* FROM babylon_state.economic_flow_account_v1 a
JOIN babylon_state.material_campaign_foundation_v3 f ON f.campaign_id=a.campaign_id
    AND f.foundation_sha256=a.foundation_sha256;
CREATE VIEW public.v_observer_economic_payment_v1 AS
SELECT m.campaign_id, m.resolve_tick, m.ordinal, m.purpose, m.reference_kind, m.reference_id,
    p.payer_kind, p.payer_id, m.credit_kind AS recipient_kind, m.credit_id AS recipient_id, m.amount_micros
FROM public.v_observer_money_movement_v1 m
JOIN babylon_state.economic_payment_v1 p USING(campaign_id, resolve_tick, ordinal)
WHERE m.purpose IN ('delivery_settlement','wage_payment','tax','public_transfer','household_transfer',
    'ownership_distribution','capital_contribution','transport_service','mutual_aid');
REVOKE ALL ON public.v_observer_economic_flow_account_v1, public.v_observer_economic_payment_v1 FROM PUBLIC;
