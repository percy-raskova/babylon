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
    babylon_state.economic_company_original_share_v1,
    babylon_state.economic_company_member_key_v1,
    babylon_state.economic_company_v1,
    babylon_state.economic_flow_account_v1,
    babylon_state.economic_flow_location_v1,
    babylon_state.labor_checkpoint_v1,
    babylon_state.labor_movement_block_v1,
    babylon_state.labor_movement_roster_v1,
    babylon_state.labor_node_block_v1,
    babylon_state.economic_reference_guard_v1,
    babylon_state.labor_node_identity_v1,
    babylon_state.labor_product_v1,
    babylon_state.labor_period_v1,
    babylon_state.money_journal_period_v1,
    babylon_state.money_movement_total_v1,
    babylon_state.money_movement_block_v1,
    babylon_state.money_movement_account_v1,
    babylon_state.site_principal_v1,
    babylon_state.site_stock_key_v1,
    babylon_state.site_roster_guard_v1,
    babylon_state.site_roster_block_v1,
    babylon_state.site_statement_block_v1,
    babylon_state.site_stock_block_v1 CASCADE;

DROP FUNCTION babylon_state.touch_site_roster_v1(), babylon_state.verify_site_roster_v1(),
    babylon_state.prevent_site_roster_truncate_v1(), babylon_state.site_ordinals_valid_v1(integer,bit,integer[]),
    babylon_state.site_postings_valid_v1(bit,numeric[]),
    babylon_state.site_stock_slots_valid_v1(bit,numeric[],numeric[],numeric[],numeric[]);

DROP FUNCTION
    babylon_state.movement_slots_v1(smallint[]),
    babylon_state.money_movement_values_v1(text[],text[],bytea[],integer[],integer[],numeric[]),
    babylon_state.labor_movement_values_v1(bigint[],bigint[],text[],bigint[],numeric[],numeric[],boolean[]),
    babylon_state.money_movement_accounts_v1(),
    babylon_state.labor_movement_nodes_v1(),
    babylon_state.money_movement_reference_change_v1(),
    babylon_state.labor_movement_reference_change_v1();

DROP FUNCTION babylon_state.revise_labor_account_scope_v1(),babylon_state.revise_labor_point_v1(),
    babylon_state.retain_labor_identity_v1(),babylon_state.check_labor_descriptors_v1();
DROP TYPE babylon_state.labor_physical_scope_v1;

DROP FUNCTION babylon_state.economic_reference_lock_v1(uuid),babylon_state.labor_node_changed_v1(),babylon_state.labor_node_validate_v1(),
    babylon_state.labor_node_no_truncate_v1(),babylon_state.labor_node_guard_private_v1(),
    babylon_state.labor_holding_block_valid_v1(numeric[],numeric[],boolean[],integer);

ALTER TABLE babylon_state.material_tick_v3
    DROP CONSTRAINT material_tick_v3_receipt_storage_bytes_check,
    ADD CONSTRAINT material_tick_v3_receipt_storage_bytes_check
        CHECK (octet_length(receipt_storage_bytes) <= 925437040);

DROP DOMAIN babylon_state.company_site_shares_v1, babylon_state.company_claim_weight_v1;

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

-- Restore the exact deferred graph marker guard of the admitted predecessor.
CREATE OR REPLACE FUNCTION babylon_state.graph_node_marker_complete_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE m babylon_state.graph_node_manifest_v1%ROWTYPE; bad boolean;
BEGIN
 SELECT * INTO m FROM babylon_state.graph_node_manifest_v1 WHERE campaign_id=NEW.campaign_id AND resolve_tick=NEW.resolve_tick;
 IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_manifest_missing'; END IF;
 -- References are direct, campaign-owned and from this tick or a durable origin.
 IF EXISTS(
  SELECT 1 FROM (
   SELECT campaign_id,vector_id FROM babylon_state.graph_node_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick
   UNION ALL SELECT campaign_id,vector_id FROM babylon_state.graph_node_f64_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick
  ) c LEFT JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id)
  WHERE v.vector_id IS NULL OR v.first_tick>m.resolve_tick OR (v.first_tick<>m.resolve_tick AND NOT EXISTS(SELECT 1 FROM babylon_state.tick_commit p WHERE p.campaign_id=v.campaign_id AND p.resolve_tick=v.first_tick))
 ) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_vector_reference'; END IF;
 IF EXISTS(SELECT 1 FROM babylon_state.graph_node_f64_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick AND cardinality(c.value_bits)<>cardinality(v.node_ids)) THEN
  RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_vector_length';
 END IF;

 SELECT count(*)<>m.node_chunks OR coalesce(sum(cardinality(v.node_ids)),0)<>m.node_count
  OR (count(*)>0 AND (min(ordinal)<>0 OR max(ordinal)<>count(*)-1)) INTO bad
 FROM babylon_state.graph_node_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_chunk_gap_or_count'; END IF;
 SELECT count(*)<>m.f64_chunks OR coalesce(sum(cardinality(v.node_ids)),0)<>m.f64_count INTO bad
 FROM babylon_state.graph_node_f64_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick;
 IF bad OR EXISTS(SELECT 1 FROM babylon_state.graph_node_f64_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick GROUP BY qname_id HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1) THEN
  RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_chunk_gap_or_count';
 END IF;
 -- Validate array refs and one current type per local name in one set operation.
 WITH members AS (SELECT u.node_id FROM babylon_state.graph_node_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) CROSS JOIN LATERAL unnest(v.node_ids) u(node_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick),
 joined AS (SELECT a.node_id,n.name_id,n.first_tick,s.first_tick AS name_tick,t.first_tick AS type_tick FROM members a LEFT JOIN babylon_state.graph_node_lookup_v1 n ON n.campaign_id=m.campaign_id AND n.node_id=a.node_id LEFT JOIN babylon_state.graph_string_lookup_v1 s ON s.campaign_id=m.campaign_id AND s.string_id=n.name_id LEFT JOIN babylon_state.graph_string_lookup_v1 t ON t.campaign_id=m.campaign_id AND t.string_id=n.type_id)
 SELECT count(*)<>count(name_id) OR count(*)<>count(DISTINCT name_id) OR coalesce(bool_or(first_tick>m.resolve_tick OR name_tick>m.resolve_tick OR type_tick>m.resolve_tick),false) INTO bad FROM joined;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_reference_or_duplicate'; END IF;
 WITH members AS (SELECT u.node_id FROM babylon_state.graph_node_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) CROSS JOIN LATERAL unnest(v.node_ids) u(node_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick),
 attrs AS (SELECT c.qname_id,u.node_id FROM babylon_state.graph_node_f64_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) CROSS JOIN LATERAL unnest(v.node_ids) u(node_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick),
 joined AS (SELECT a.node_id,a.qname_id,b.node_id AS member_id,q.first_tick FROM attrs a LEFT JOIN members b USING(node_id) LEFT JOIN babylon_state.graph_string_lookup_v1 q ON q.campaign_id=m.campaign_id AND q.string_id=a.qname_id)
 SELECT count(*)<>count(member_id) OR count(*)<>count(DISTINCT (node_id,qname_id)) OR coalesce(bool_or(first_tick>m.resolve_tick),false) INTO bad FROM joined;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_reference_or_duplicate'; END IF;
 -- Dense append-only IDs make count-based assignment explicit and checked.
 IF EXISTS(SELECT 1 FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(string_id)<>0 OR max(string_id)<>count(*)-1)
 OR EXISTS(SELECT 1 FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(node_id)<>0 OR max(node_id)<>count(*)-1)
 OR EXISTS(SELECT 1 FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=m.campaign_id HAVING min(vector_id)<>0 OR max(vector_id)<>count(*)-1) THEN
  RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_lookup_gap';
 END IF;
 RETURN NEW;
END $$;
