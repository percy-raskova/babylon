WITH expected AS MATERIALIZED (
    SELECT * FROM jsonb_populate_recordset(NULL::babylon_state.labor_movement_v1,$1::text::jsonb)
), keys AS (
    SELECT DISTINCT campaign_id,resolve_tick,ordinal/128 AS block_ordinal FROM expected
), actual AS (
    SELECT b.campaign_id,b.resolve_tick,b.block_ordinal*128+r.slot AS ordinal,
           r.source_node,r.destination_node,r.receipt_family,r.receipt_ordinal,r.quantity,r.recorded_micro_hours,r.unknown_opening
    FROM keys JOIN babylon_state.labor_movement_block_v1 b USING(campaign_id,resolve_tick,block_ordinal)
    CROSS JOIN LATERAL unnest(b.slots,b.source_node,b.destination_node,b.receipt_family,b.receipt_ordinal,
                              b.quantity,b.recorded_micro_hours,b.unknown_opening)
        AS r(slot,source_node,destination_node,receipt_family,receipt_ordinal,quantity,recorded_micro_hours,unknown_opening)
)
SELECT NOT EXISTS (TABLE expected EXCEPT ALL TABLE actual)
