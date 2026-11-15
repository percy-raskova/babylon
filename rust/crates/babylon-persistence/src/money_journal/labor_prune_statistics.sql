-- A fresh national ledger can have tens of thousands of nodes before autovacuum
-- samples it. Without endpoint statistics, each source-node cascade can scan
-- a whole period through the destination index after the bulk child delete.
ANALYZE babylon_state.labor_movement_block_v1 (campaign_id, resolve_tick, block_ordinal);
ANALYZE babylon_state.labor_node_block_v1 (campaign_id, resolve_tick, block_ordinal, descriptor_keys);
ANALYZE babylon_state.labor_node_identity_v1 (campaign_id, descriptor_key, descriptor_sha256);
