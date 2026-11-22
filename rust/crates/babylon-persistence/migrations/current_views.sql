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

CREATE VIEW public.v_observer_graph_hyperedge_member_f64_v1 AS
SELECT component.*
FROM babylon_state.graph_hyperedge_member_f64_v1 AS component
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
    public.v_observer_graph_hyperedge_member_f64_v1,
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
SELECT d.campaign_id, d.resolve_tick, d.ordinal, d.purpose, d.reference_kind, d.reference_id,
    CASE WHEN d.reference_id IS NOT NULL AND d.recipient_key IS NOT NULL
        THEN ref.reserve_kind ELSE payer.account_kind END AS debit_kind,
    CASE WHEN d.reference_id IS NOT NULL AND d.recipient_key IS NOT NULL
        THEN d.reference_id ELSE payer.account_id END AS debit_id,
    CASE WHEN d.recipient_key IS NULL THEN ref.reserve_kind ELSE recipient.account_kind END AS credit_kind,
    CASE WHEN d.recipient_key IS NULL THEN d.reference_id ELSE recipient.account_id END AS credit_id,
    d.amount_micros
FROM babylon_state.money_movement_v1 d
JOIN public.v_observer_money_journal_period_v1 p USING (campaign_id,resolve_tick)
CROSS JOIN LATERAL (VALUES (
    CASE WHEN d.reference_kind='shift' THEN 'payroll_reserve' ELSE d.reference_kind || '_reserve' END
)) AS ref(reserve_kind)
LEFT JOIN babylon_state.economic_flow_account_v1 payer
    ON (payer.campaign_id,payer.account_key)=(d.campaign_id,d.payer_key)
LEFT JOIN babylon_state.economic_flow_account_v1 recipient
    ON (recipient.campaign_id,recipient.account_key)=(d.campaign_id,d.recipient_key)
WHERE p.detail_retained
    AND (d.payer_key IS NULL OR payer.foundation_sha256=p.foundation_sha256)
    AND (d.recipient_key IS NULL OR recipient.foundation_sha256=p.foundation_sha256);
CREATE VIEW public.v_observer_money_movement_total_v1 AS
SELECT d.* FROM babylon_state.money_movement_total_v1 d
JOIN public.v_observer_money_journal_period_v1 p USING (campaign_id, resolve_tick);
REVOKE ALL ON public.v_observer_money_journal_period_v1, public.v_observer_money_movement_v1,
    public.v_observer_money_movement_total_v1 FROM PUBLIC;

CREATE VIEW public.v_observer_economic_flow_location_v1 AS
SELECT l.campaign_id,l.foundation_sha256,l.location_key,l.longitude,l.latitude,l.county_internal_point,
       'tiger_county_internal_point'::text AS point_basis
FROM babylon_state.economic_flow_location_v1 l
JOIN babylon_state.material_campaign_foundation_v3 f ON f.campaign_id=l.campaign_id
    AND f.foundation_sha256=l.foundation_sha256;
REVOKE ALL ON public.v_observer_economic_flow_location_v1 FROM PUBLIC;
CREATE VIEW public.v_observer_economic_flow_account_v1 AS
SELECT a.campaign_id,a.foundation_sha256,a.account_kind,a.account_id,
    a.location_key,a.catchment_key,a.industry_key,a.industry_label
FROM babylon_state.economic_flow_account_v1 a
JOIN babylon_state.material_campaign_foundation_v3 f ON f.campaign_id=a.campaign_id
    AND f.foundation_sha256=a.foundation_sha256;
CREATE VIEW public.v_observer_economic_company_v1 AS
SELECT c.* FROM babylon_state.economic_company_v1 c
JOIN babylon_state.material_campaign_foundation_v3 f USING(campaign_id,foundation_sha256);
REVOKE ALL ON public.v_observer_economic_company_v1 FROM PUBLIC;
CREATE VIEW public.v_observer_economic_company_member_v1 AS
SELECT c.* FROM babylon_state.economic_company_member_v1 c
JOIN babylon_state.material_campaign_foundation_v3 f USING(campaign_id,foundation_sha256);
REVOKE ALL ON public.v_observer_economic_company_member_v1 FROM PUBLIC;
CREATE VIEW public.v_observer_economic_company_claim_v1 AS
SELECT c.* FROM babylon_state.economic_company_claim_v1 c
JOIN babylon_state.material_campaign_foundation_v3 f USING(campaign_id,foundation_sha256);
REVOKE ALL ON public.v_observer_economic_company_claim_v1 FROM PUBLIC;
CREATE VIEW public.v_observer_economic_company_claim_source_v1 AS
SELECT c.* FROM babylon_state.economic_company_claim_source_v1 c
JOIN babylon_state.material_campaign_foundation_v3 f USING(campaign_id,foundation_sha256);
REVOKE ALL ON public.v_observer_economic_company_claim_source_v1 FROM PUBLIC;
CREATE VIEW public.v_observer_economic_flow_account_v2 AS
SELECT a.*,c.company_id,c.label AS company_label
FROM public.v_observer_economic_flow_account_v1 a
LEFT JOIN public.v_observer_economic_company_member_v1 m
    ON a.account_kind='site_cash' AND (m.campaign_id,m.foundation_sha256,m.site_id)=(a.campaign_id,a.foundation_sha256,a.account_id)
LEFT JOIN public.v_observer_economic_company_v1 c
    ON (c.campaign_id,c.foundation_sha256)=(a.campaign_id,a.foundation_sha256)
    AND c.company_id=CASE WHEN a.account_kind='company_cash' THEN a.account_id ELSE m.company_id END;
REVOKE ALL ON public.v_observer_economic_flow_account_v2 FROM PUBLIC;
-- Keep each settlement within its admitted period. Resolve both compact keys
-- against the same campaign and foundation, including a payer behind escrow.
CREATE VIEW public.v_observer_economic_payment_v1 AS
SELECT p.campaign_id, p.resolve_tick, paid.ordinal, paid.purpose, paid.reference_kind, paid.reference_id,
    paid.payer_kind, paid.payer_id, paid.recipient_kind, paid.recipient_id, paid.amount_micros
FROM public.v_observer_money_journal_period_v1 p
CROSS JOIN LATERAL (
    WITH accounts AS (
        SELECT jsonb_object_agg(account_key,jsonb_build_array(account_kind,encode(account_id,'hex'))) AS by_key
        FROM babylon_state.economic_flow_account_v1
        WHERE campaign_id=p.campaign_id AND foundation_sha256=p.foundation_sha256
    )
    SELECT m.ordinal,m.purpose,m.reference_kind,m.reference_id,
        key.payer->>0 AS payer_kind,decode(key.payer->>1,'hex') AS payer_id,
        key.recipient->>0 AS recipient_kind,decode(key.recipient->>1,'hex') AS recipient_id,m.amount_micros
    FROM babylon_state.money_movement_v1 m CROSS JOIN accounts
    CROSS JOIN LATERAL (SELECT accounts.by_key->m.payer_key::text AS payer,
        accounts.by_key->m.recipient_key::text AS recipient) key
    WHERE m.campaign_id=p.campaign_id AND m.resolve_tick=p.resolve_tick
        AND key.payer IS NOT NULL AND key.recipient IS NOT NULL
    OFFSET 0
) AS paid
WHERE p.detail_retained;
REVOKE ALL ON public.v_observer_economic_flow_account_v1, public.v_observer_economic_payment_v1 FROM PUBLIC;

CREATE VIEW public.v_observer_site_statement_v1 AS
SELECT s.campaign_id,s.site_ordinal,s.resolve_tick,k.site_id,
    s.opening_cash_micros, s.opening_purchase_reserves_micros,
    s.opening_payroll_reserves_micros, s.opening_wage_receivables_micros,
    s.opening_inventory_micros, s.opening_freight_micros,
    s.opening_equity_investments_micros, s.opening_equipment_micros,
    s.opening_total_assets_micros, s.opening_wage_payables_micros,
    s.opening_total_liabilities_micros, s.opening_opening_capital_micros,
    s.opening_contributed_capital_micros, s.opening_retained_earnings_micros,
    s.opening_total_equity_micros, s.closing_cash_micros,
    s.closing_purchase_reserves_micros, s.closing_payroll_reserves_micros,
    s.closing_wage_receivables_micros, s.closing_inventory_micros,
    s.closing_freight_micros, s.closing_equity_investments_micros,
    s.closing_equipment_micros, s.closing_total_assets_micros,
    s.closing_wage_payables_micros, s.closing_total_liabilities_micros,
    s.closing_opening_capital_micros, s.closing_contributed_capital_micros,
    s.closing_retained_earnings_micros, s.closing_total_equity_micros,
    s.income_sales_micros, s.income_wage_income_micros,
    s.income_cost_of_goods_sold_micros, s.income_productive_labor_capitalized_micros,
    s.income_installation_labor_capitalized_micros, s.income_equipment_wear_capitalized_micros,
    s.income_idle_labor_expense_micros, s.income_handling_expense_micros,
    s.income_maintenance_labor_expense_micros, s.income_maintenance_material_expense_micros,
    s.income_freight_loss_expense_micros, s.income_consumption_expense_micros,
    s.income_final_demand_outlay_micros, s.income_unused_service_expense_micros,
    s.income_tax_income_micros, s.income_tax_expense_micros,
    s.income_public_transfer_income_micros, s.income_public_transfer_expense_micros,
    s.income_distribution_income_micros, s.income_gift_income_micros,
    s.income_gift_expense_micros, s.income_agency_observation_labor_expense_micros,
    s.cash_flow_operating_micros, s.cash_flow_investing_micros,
    s.cash_flow_financing_micros, s.cash_flow_reserve_reclassification_micros,
    s.net_income_micros, s.contributions_received_micros,
    s.distributions_paid_micros, s.change_in_equity_micros,
    p.site_monetary_books,p.receipt_sha256
FROM babylon_state.site_statement_v1 s
JOIN public.v_observer_money_journal_period_v1 p USING(campaign_id,resolve_tick)
JOIN babylon_state.site_principal_v1 k ON (k.campaign_id,k.site_key,k.foundation_sha256)=(s.campaign_id,s.site_key,p.foundation_sha256);
CREATE VIEW public.v_observer_site_stock_balance_v1 AS
SELECT s.campaign_id,s.resolve_tick,k.site_id,g.good_id,g.unit_id,s.opening_quantity,s.closing_quantity,
    s.opening_carrying_cost_micros,s.closing_carrying_cost_micros,p.site_monetary_books,p.receipt_sha256
FROM babylon_state.site_stock_balance_v1 s
JOIN public.v_observer_money_journal_period_v1 p USING(campaign_id,resolve_tick)
JOIN babylon_state.site_principal_v1 k ON (k.campaign_id,k.site_key,k.foundation_sha256)=(s.campaign_id,s.site_key,p.foundation_sha256)
JOIN babylon_state.site_stock_key_v1 g ON (g.campaign_id,g.resolve_tick,g.commodity_ordinal)=(s.campaign_id,s.resolve_tick,s.commodity_ordinal);
REVOKE ALL ON public.v_observer_site_statement_v1, public.v_observer_site_stock_balance_v1 FROM PUBLIC;

CREATE VIEW public.v_observer_labor_period_v1 AS
-- One guarded release per campaign and period. Keep the source checks together when
-- the view is joined to many facts; both keys remain eligible for predicate pushdown.
SELECT DISTINCT ON (l.campaign_id,l.resolve_tick) l.*,p.detail_retained,p.foundation_sha256,p.tick_content_hash,p.receipt_sha256
FROM babylon_state.labor_period_v1 l JOIN public.v_observer_money_journal_period_v1 p USING(campaign_id,resolve_tick);
CREATE VIEW public.v_observer_labor_checkpoint_v1 AS
SELECT c.*,p.foundation_sha256,p.tick_content_hash,p.receipt_sha256,p.result_world_hash
FROM babylon_state.labor_checkpoint_v1 c JOIN public.v_observer_labor_period_v1 p USING(campaign_id,resolve_tick)
WHERE c.sha256=p.checkpoint_sha256;
CREATE VIEW public.v_observer_labor_node_v1 AS
SELECT n.campaign_id,n.resolve_tick,n.node_ordinal,n.kind,n.entity_id,n.good_id,n.unit_id,n.purpose,
       n.scope_kind,n.scope_id,n.process_id,n.route_id,n.origin_id,n.destination_id,
       n.location_key,n.catchment_key,n.industry_key,n.industry_label,n.longitude,n.latitude
FROM babylon_state.labor_node_fact_v1 n JOIN public.v_observer_labor_period_v1 p USING(campaign_id,resolve_tick)
WHERE p.detail_retained;
CREATE VIEW public.v_observer_labor_movement_v1 AS
SELECT e.* FROM babylon_state.labor_movement_v1 e JOIN public.v_observer_labor_period_v1 p USING(campaign_id,resolve_tick) WHERE p.detail_retained;
CREATE VIEW public.v_observer_labor_position_v1 AS
SELECT b.campaign_id, b.resolve_tick, endpoint.side, b.node_ordinal,
       endpoint.quantity, endpoint.recorded_micro_hours, endpoint.unknown_opening
FROM babylon_state.labor_node_v1 b
JOIN public.v_observer_labor_period_v1 p USING (campaign_id, resolve_tick)
CROSS JOIN LATERAL (VALUES
    ('opening'::text, b.opening_quantity, b.opening_recorded_micro_hours, b.opening_unknown_opening),
    ('closing'::text, b.closing_quantity, b.closing_recorded_micro_hours, b.closing_unknown_opening)
) AS endpoint(side, quantity, recorded_micro_hours, unknown_opening)
WHERE p.detail_retained AND endpoint.quantity IS NOT NULL;
REVOKE ALL ON public.v_observer_labor_period_v1,public.v_observer_labor_checkpoint_v1,public.v_observer_labor_node_v1,
public.v_observer_labor_movement_v1,public.v_observer_labor_position_v1 FROM PUBLIC;

-- Full observer company statements, attached to the same source-validating period marker.
CREATE VIEW public.v_observer_company_accounting_period_v1 AS
SELECT b.*, p.foundation_sha256, p.tick_content_hash, p.receipt_sha256, p.source_identity_bytes
FROM babylon_state.company_accounting_period_v1 b JOIN public.v_observer_money_journal_period_v1 p USING(campaign_id,resolve_tick);
CREATE VIEW public.v_observer_company_accounting_checkpoint_v1 AS
SELECT b.*,p.checkpoint_sha256,p.result_world_hash,p.foundation_sha256,p.tick_content_hash,p.receipt_sha256,p.source_identity_bytes
FROM babylon_state.company_accounting_checkpoint_v1 b JOIN public.v_observer_company_accounting_period_v1 p USING(campaign_id,resolve_tick);
CREATE VIEW public.v_observer_company_statement_balance_v1 AS
SELECT b.*
FROM babylon_state.company_statement_balance_v1 b JOIN public.v_observer_company_accounting_period_v1 p USING(campaign_id,resolve_tick);
CREATE VIEW public.v_observer_company_statement_income_v1 AS
SELECT b.*
FROM babylon_state.company_statement_income_v1 b JOIN public.v_observer_company_accounting_period_v1 p USING(campaign_id,resolve_tick);
CREATE VIEW public.v_observer_company_statement_cash_flow_v1 AS
SELECT b.*
FROM babylon_state.company_statement_cash_flow_v1 b JOIN public.v_observer_company_accounting_period_v1 p USING(campaign_id,resolve_tick);
CREATE VIEW public.v_observer_company_elimination_v1 AS
SELECT b.*
FROM babylon_state.company_elimination_v1 b JOIN public.v_observer_company_accounting_period_v1 p USING(campaign_id,resolve_tick);
CREATE VIEW public.v_observer_company_realization_entry_v1 AS
SELECT b.*
FROM babylon_state.company_realization_entry_v1 b JOIN public.v_observer_company_accounting_period_v1 p USING(campaign_id,resolve_tick);
REVOKE ALL ON public.v_observer_company_accounting_period_v1,
    public.v_observer_company_accounting_checkpoint_v1,
    public.v_observer_company_statement_balance_v1,
    public.v_observer_company_statement_income_v1,
    public.v_observer_company_statement_cash_flow_v1,
    public.v_observer_company_elimination_v1,
    public.v_observer_company_realization_entry_v1 FROM PUBLIC;
