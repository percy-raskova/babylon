-- A link carries a local physical key. Only the complete typed descriptor and its
-- SHA-256 identify the source fact. The journal lock serializes key allocation.
WITH batch AS MATERIALIZED (
    SELECT jsonb_populate_record(NULL::babylon_state.labor_node_v1,row_data) AS link,
           jsonb_populate_record(NULL::babylon_state.labor_node_descriptor_v1,row_data) AS body
    FROM jsonb_array_elements($1::text::jsonb) row_data
), expected AS MATERIALIZED (
    SELECT link,jsonb_populate_record(body,
        jsonb_build_object('descriptor_sha256',babylon_state.labor_node_fingerprint_v1(body))) AS body
    FROM batch
), matched AS MATERIALIZED (
    SELECT e.body,d.descriptor_key
    FROM (SELECT DISTINCT body FROM expected) e
    LEFT JOIN babylon_state.labor_node_descriptor_v1 d
      ON d.campaign_id=(e.body).campaign_id AND d.descriptor_sha256=(e.body).descriptor_sha256
     AND d IS NOT DISTINCT FROM jsonb_populate_record(e.body,jsonb_build_object('descriptor_key',d.descriptor_key))
), prior AS MATERIALIZED (
    SELECT c.campaign_id, coalesce((SELECT max(d.descriptor_key)
        FROM babylon_state.labor_node_identity_v1 d WHERE d.campaign_id=c.campaign_id),0) AS last_key
    FROM (SELECT DISTINCT (body).campaign_id FROM matched WHERE descriptor_key IS NULL) c
), allocated AS (
    SELECT m.body,p.last_key+row_number() OVER (PARTITION BY p.campaign_id ORDER BY (m.body).descriptor_sha256) AS descriptor_key
    FROM matched m JOIN prior p ON p.campaign_id=(m.body).campaign_id
    WHERE m.descriptor_key IS NULL
), new_definitions AS (
    INSERT INTO babylon_state.labor_node_identity_v1
        (campaign_id,descriptor_key,descriptor_sha256,kind,entity_id,product_key,purpose,
         scope_key,scope_revision,location_key,point_revision,physical_scope,process_id,route_id,origin_id,destination_id)
    SELECT (t.body).campaign_id,t.descriptor_key,(t.body).descriptor_sha256,(t.body).kind,
           CASE WHEN (t.body).kind IN ('commercial_freight','aid_freight','equipment','installation')
                THEN (t.body).entity_id END,g.product_key,(t.body).purpose,
           a.account_key,a.labor_scope_revision,(t.body).location_key,l.labor_point_revision,
           CASE WHEN a.account_key IS NULL AND (t.body).scope_kind IS NOT NULL THEN
               ROW((t.body).scope_kind,(t.body).scope_id,(t.body).location_key,(t.body).catchment_key,
                   (t.body).industry_key,(t.body).industry_label,(t.body).longitude,(t.body).latitude)::babylon_state.labor_physical_scope_v1 END,
           (t.body).process_id,(t.body).route_id,(t.body).origin_id,(t.body).destination_id
    FROM allocated t
    LEFT JOIN babylon_state.economic_flow_account_v1 a
      ON (a.campaign_id,a.account_kind,a.account_id)=((t.body).campaign_id,(t.body).scope_kind,(t.body).scope_id)
    LEFT JOIN babylon_state.economic_flow_location_v1 l
      ON (l.campaign_id,l.location_key)=(a.campaign_id,a.location_key) AND (t.body).longitude IS NOT NULL
    LEFT JOIN babylon_state.labor_product_v1 g
      ON (g.campaign_id,g.unit_id)=((t.body).campaign_id,(t.body).unit_id) AND g.good_id IS NOT DISTINCT FROM (t.body).good_id
    RETURNING campaign_id,descriptor_sha256,descriptor_key
), resolved AS (
    SELECT (body).campaign_id,(body).descriptor_sha256,descriptor_key FROM matched WHERE descriptor_key IS NOT NULL
    UNION ALL SELECT campaign_id,descriptor_sha256,descriptor_key FROM new_definitions
)
INSERT INTO babylon_state.labor_node_block_v1(campaign_id,resolve_tick,block_ordinal,descriptor_keys,
    opening_quantity,opening_recorded_micro_hours,opening_unknown_opening,
    closing_quantity,closing_recorded_micro_hours,closing_unknown_opening)
SELECT r.campaign_id,(e.link).resolve_tick,(e.link).node_ordinal/256,
       array_agg(r.descriptor_key ORDER BY (e.link).node_ordinal),
       array_agg((e.link).opening_quantity ORDER BY (e.link).node_ordinal),
       array_agg((e.link).opening_recorded_micro_hours ORDER BY (e.link).node_ordinal),
       array_agg((e.link).opening_unknown_opening ORDER BY (e.link).node_ordinal),
       array_agg((e.link).closing_quantity ORDER BY (e.link).node_ordinal),
       array_agg((e.link).closing_recorded_micro_hours ORDER BY (e.link).node_ordinal),
       array_agg((e.link).closing_unknown_opening ORDER BY (e.link).node_ordinal)
FROM expected e JOIN resolved r
  ON (r.campaign_id,r.descriptor_sha256)=((e.body).campaign_id,(e.body).descriptor_sha256)
GROUP BY r.campaign_id,(e.link).resolve_tick,(e.link).node_ordinal/256
