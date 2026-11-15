INSERT INTO babylon_state.labor_movement_block_v1
    (campaign_id,resolve_tick,block_ordinal,slots,source_node,destination_node,receipt_family,receipt_ordinal,quantity,recorded_micro_hours,unknown_opening)
SELECT r.campaign_id,r.resolve_tick,r.ordinal/128,array_agg((r.ordinal%128)::smallint ORDER BY r.ordinal),
       array_agg(r.source_node ORDER BY r.ordinal),
       array_agg(r.destination_node ORDER BY r.ordinal),
       array_agg(r.receipt_family ORDER BY r.ordinal),
       array_agg(r.receipt_ordinal ORDER BY r.ordinal),
       array_agg(r.quantity ORDER BY r.ordinal),
       array_agg(r.recorded_micro_hours ORDER BY r.ordinal),
       array_agg(r.unknown_opening ORDER BY r.ordinal)
FROM jsonb_populate_recordset(NULL::babylon_state.labor_movement_v1,$1::text::jsonb) AS r
GROUP BY 1,2,3 ORDER BY 1,2,3
