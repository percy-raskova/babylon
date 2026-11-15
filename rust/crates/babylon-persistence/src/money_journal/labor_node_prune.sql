-- Data-modifying CTEs share a snapshot. References outside the removed range keep
-- their descriptor, including when one historical period is rebuilt out of order.
WITH removed AS (
    DELETE FROM babylon_state.labor_node_v1
    WHERE campaign_id=$1 AND resolve_tick BETWEEN $2 AND $3
    RETURNING descriptor_sha256
)
DELETE FROM babylon_state.labor_node_identity_v1 d
WHERE d.campaign_id=$1 AND d.descriptor_sha256 IN (SELECT descriptor_sha256 FROM removed)
  AND NOT EXISTS (
      SELECT FROM babylon_state.labor_node_v1 n
      WHERE n.campaign_id=d.campaign_id AND n.descriptor_sha256=d.descriptor_sha256
        AND n.resolve_tick NOT BETWEEN $2 AND $3
  )
