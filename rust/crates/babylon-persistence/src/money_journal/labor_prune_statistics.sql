-- A fresh national ledger can have tens of thousands of nodes before autovacuum
-- samples it. Without endpoint statistics, each source-node cascade can scan
-- a whole period through the destination index after the bulk child delete.
ANALYZE babylon_state.labor_movement_v1 (campaign_id, resolve_tick, source_node, destination_node);
ANALYZE babylon_state.labor_node_v1 (campaign_id, resolve_tick, node_ordinal, descriptor_key);
ANALYZE babylon_state.labor_node_identity_v1 (campaign_id, descriptor_key, descriptor_sha256);
