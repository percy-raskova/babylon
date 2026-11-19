-- The same statement snapshot includes the deleted blocks. Use the requested
-- bounds to exclude them when finding identities still held by another period.
WITH removed AS (
    DELETE FROM babylon_state.labor_node_block_v1
    WHERE campaign_id=$1 AND resolve_tick BETWEEN $2 AND $3
    RETURNING descriptor_keys
), orphan(descriptor_key) AS MATERIALIZED (
    SELECT unnest(descriptor_keys) FROM removed
    EXCEPT
    SELECT unnest(descriptor_keys) FROM babylon_state.labor_node_block_v1
    WHERE campaign_id=$1 AND resolve_tick NOT BETWEEN $2 AND $3
      AND EXISTS (SELECT FROM removed)
)
DELETE FROM babylon_state.labor_node_identity_v1 d USING orphan
WHERE d.campaign_id=$1 AND d.descriptor_key=orphan.descriptor_key
