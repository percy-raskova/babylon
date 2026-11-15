-- The writer holds the journal transaction lock. Reuse requires equality of the complete
-- typed descriptor, including NULLs. An occupied digest with other contents rejects the insert.
WITH batch AS MATERIALIZED (
    SELECT (row_data->>'resolve_tick')::bigint AS resolve_tick,
           (row_data->>'node_ordinal')::bigint AS node_ordinal,
           jsonb_populate_record(NULL::babylon_state.labor_node_identity_v1,row_data) AS body
    FROM jsonb_array_elements($1::text::jsonb) row_data
), expected AS MATERIALIZED (
    SELECT resolve_tick,node_ordinal,jsonb_populate_record(body,
        jsonb_build_object('descriptor_sha256',babylon_state.labor_node_fingerprint_v1(body))) AS body
    FROM batch
), new_definitions AS (
    INSERT INTO babylon_state.labor_node_identity_v1
    SELECT DISTINCT (e.body).* FROM expected e WHERE NOT EXISTS (
        SELECT FROM babylon_state.labor_node_identity_v1 d
        WHERE d.campaign_id=(e.body).campaign_id AND d.descriptor_sha256=(e.body).descriptor_sha256
          AND d IS NOT DISTINCT FROM e.body
    )
)
INSERT INTO babylon_state.labor_node_v1(campaign_id,resolve_tick,node_ordinal,descriptor_sha256)
SELECT (body).campaign_id,resolve_tick,node_ordinal,(body).descriptor_sha256 FROM expected
