-- Data-modifying CTEs share a snapshot. References outside the removed range keep
-- their descriptor, including when one historical period is rebuilt out of order.
WITH removed AS (
    DELETE FROM babylon_state.labor_node_block_v1
    WHERE campaign_id=$1 AND resolve_tick BETWEEN $2 AND $3
    RETURNING descriptor_keys
)
DELETE FROM babylon_state.labor_node_identity_v1 d
WHERE d.campaign_id=$1 AND d.descriptor_key IN (SELECT unnest(descriptor_keys) FROM removed)
  AND NOT EXISTS (
      SELECT FROM babylon_state.labor_node_block_v1 n
      WHERE n.campaign_id=d.campaign_id AND n.descriptor_keys @> ARRAY[d.descriptor_key]
        AND n.resolve_tick NOT BETWEEN $2 AND $3
  )
