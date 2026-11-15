-- A link carries a local physical key. Only the complete typed descriptor and its
-- SHA-256 identify the source fact. The journal lock serializes key allocation.
WITH batch AS MATERIALIZED (
    SELECT jsonb_populate_record(NULL::babylon_state.labor_node_v1,row_data) AS link,
           jsonb_populate_record(NULL::babylon_state.labor_node_identity_v1,row_data) AS body
    FROM jsonb_array_elements($1::text::jsonb) row_data
), expected AS MATERIALIZED (
    SELECT link,jsonb_populate_record(body,
        jsonb_build_object('descriptor_sha256',babylon_state.labor_node_fingerprint_v1(body))) AS body
    FROM batch
), matched AS MATERIALIZED (
    SELECT e.body,d.descriptor_key
    FROM (SELECT DISTINCT body FROM expected) e
    LEFT JOIN babylon_state.labor_node_identity_v1 d
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
    SELECT d.* FROM allocated a CROSS JOIN LATERAL
        jsonb_populate_record(a.body,jsonb_build_object('descriptor_key',a.descriptor_key)) d
    RETURNING campaign_id,descriptor_sha256,descriptor_key
), resolved AS (
    SELECT (body).campaign_id,(body).descriptor_sha256,descriptor_key FROM matched WHERE descriptor_key IS NOT NULL
    UNION ALL SELECT campaign_id,descriptor_sha256,descriptor_key FROM new_definitions
)
INSERT INTO babylon_state.labor_node_v1(campaign_id,resolve_tick,node_ordinal,descriptor_key,
    opening_quantity,opening_recorded_micro_hours,opening_unknown_opening,
    closing_quantity,closing_recorded_micro_hours,closing_unknown_opening)
SELECT r.campaign_id,(e.link).resolve_tick,(e.link).node_ordinal,r.descriptor_key,
       (e.link).opening_quantity,(e.link).opening_recorded_micro_hours,(e.link).opening_unknown_opening,
       (e.link).closing_quantity,(e.link).closing_recorded_micro_hours,(e.link).closing_unknown_opening
FROM expected e JOIN resolved r
  ON (r.campaign_id,r.descriptor_sha256)=((e.body).campaign_id,(e.body).descriptor_sha256)
