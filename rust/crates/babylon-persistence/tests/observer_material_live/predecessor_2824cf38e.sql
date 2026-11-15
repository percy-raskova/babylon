-- Restore 2824cf38e in the task-owned disposable source clone only.
-- CASCADE removes the current views, indexes and foreign keys on these derived rows.
DROP TABLE
    babylon_state.company_accounting_checkpoint_v1,
    babylon_state.company_accounting_period_v1,
    babylon_state.company_elimination_v1,
    babylon_state.company_realization_entry_v1,
    babylon_state.company_statement_balance_v1,
    babylon_state.company_statement_cash_flow_v1,
    babylon_state.company_statement_income_v1,
    babylon_state.economic_company_claim_source_v1,
    babylon_state.economic_company_claim_v1,
    babylon_state.economic_company_member_v1,
    babylon_state.economic_company_v1,
    babylon_state.economic_flow_account_v1,
    babylon_state.economic_flow_location_v1,
    babylon_state.labor_checkpoint_v1,
    babylon_state.labor_movement_v1,
    babylon_state.labor_node_v1,
    babylon_state.labor_node_identity_v1,
    babylon_state.labor_period_v1,
    babylon_state.labor_position_v1,
    babylon_state.money_journal_period_v1,
    babylon_state.money_movement_total_v1,
    babylon_state.money_movement_v1,
    babylon_state.site_principal_v1,
    babylon_state.site_stock_key_v1,
    babylon_state.site_statement_v1,
    babylon_state.site_stock_balance_v1 CASCADE;

ALTER TABLE babylon_state.material_tick_v3
    DROP CONSTRAINT material_tick_v3_receipt_storage_bytes_check,
    ADD CONSTRAINT material_tick_v3_receipt_storage_bytes_check
        CHECK (octet_length(receipt_storage_bytes) <= 925437040);

UPDATE babylon_meta.current_schema
SET schema_sha256 = decode('f984e7ee59fa650fc470f884b4663a6fc773c44ed4494254727273e50093d071', 'hex');

-- Reinstall the two predecessor graph readers in place, retaining their owning roles and grants.
CREATE OR REPLACE VIEW babylon_state.graph_node_v1 AS
 SELECT c.campaign_id,c.resolve_tick,s.value AS local_name,t.value AS node_type
 FROM babylon_state.graph_node_chunk_v1 c
 JOIN babylon_state.tick_commit m USING(campaign_id,resolve_tick)
 JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id)
 CROSS JOIN LATERAL unnest(v.node_ids) u(node_id)
 CROSS JOIN LATERAL (
  SELECT n.name_id,n.type_id FROM babylon_state.graph_node_lookup_v1 n
  WHERE n.campaign_id=c.campaign_id AND n.node_id=u.node_id OFFSET 0
 ) n
 CROSS JOIN LATERAL (
  SELECT s.value FROM babylon_state.graph_string_lookup_v1 s
  WHERE s.campaign_id=c.campaign_id AND s.string_id=n.name_id OFFSET 0
 ) s
 CROSS JOIN LATERAL (
  SELECT t.value FROM babylon_state.graph_string_lookup_v1 t
  WHERE t.campaign_id=c.campaign_id AND t.string_id=n.type_id OFFSET 0
 ) t;
CREATE OR REPLACE VIEW babylon_state.graph_node_f64_v1 AS
 SELECT c.campaign_id,c.resolve_tick,s.value AS local_name,q.value AS qname,u.value_bits
 FROM babylon_state.graph_node_f64_chunk_v1 c
 JOIN babylon_state.tick_commit m USING(campaign_id,resolve_tick)
 JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id)
 CROSS JOIN LATERAL unnest(v.node_ids,c.value_bits) u(node_id,value_bits)
 CROSS JOIN LATERAL (
  SELECT n.name_id FROM babylon_state.graph_node_lookup_v1 n
  WHERE n.campaign_id=c.campaign_id AND n.node_id=u.node_id OFFSET 0
 ) n
 CROSS JOIN LATERAL (
  SELECT s.value FROM babylon_state.graph_string_lookup_v1 s
  WHERE s.campaign_id=c.campaign_id AND s.string_id=n.name_id OFFSET 0
 ) s
 CROSS JOIN LATERAL (
  SELECT q.value FROM babylon_state.graph_string_lookup_v1 q
  WHERE q.campaign_id=c.campaign_id AND q.string_id=c.qname_id OFFSET 0
 ) q;
