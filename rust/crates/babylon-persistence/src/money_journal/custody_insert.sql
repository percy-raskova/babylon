INSERT INTO babylon_state.money_movement_block_v1
    (campaign_id,resolve_tick,block_ordinal,slots,purpose,reference_kind,reference_id,payer_key,recipient_key,amount_micros)
SELECT $1::uuid,$2::bigint,r.ordinal/128,array_agg((r.ordinal%128)::smallint ORDER BY r.ordinal),
       array_agg(r.purpose ORDER BY r.ordinal),
       array_agg(r.reference_kind ORDER BY r.ordinal),
       array_agg(r.reference_id ORDER BY r.ordinal),
       array_agg(r.payer_key ORDER BY r.ordinal),
       array_agg(r.recipient_key ORDER BY r.ordinal),
       array_agg(r.amount_micros::numeric ORDER BY r.ordinal)
FROM unnest($3::bigint[],$4::text[],$5::text[],$6::bytea[],$7::integer[],$8::integer[],$9::text[])
    AS r(ordinal,purpose,reference_kind,reference_id,payer_key,recipient_key,amount_micros)
GROUP BY 1,2,3 ORDER BY 1,2,3
