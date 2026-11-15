WITH parts AS (SELECT DISTINCT site_key/32 AS block_key,commodity_ordinal FROM pg_temp.site_stock_source),
padded AS (
    SELECT p.block_key,p.commodity_ordinal,i AS slot,s.site_key,s.opening_quantity,s.closing_quantity,
        s.opening_carrying_cost_micros,s.closing_carrying_cost_micros
    FROM parts p CROSS JOIN generate_series(0,31) AS a(i) LEFT JOIN pg_temp.site_stock_source s
        ON (s.site_key,s.commodity_ordinal)=(p.block_key*32+i,p.commodity_ordinal)
)
SELECT $1::uuid AS campaign_id,$2::bigint AS resolve_tick,p.block_key,p.commodity_ordinal,b.present,
    string_agg(CASE WHEN p.site_key IS NULL THEN '0' ELSE '1' END,'' ORDER BY slot)::bit(32) AS stocks,
    array_agg(opening_quantity ORDER BY slot) AS opening_quantities,array_agg(closing_quantity ORDER BY slot) AS closing_quantities,
    array_agg(opening_carrying_cost_micros ORDER BY slot) AS opening_costs,array_agg(closing_carrying_cost_micros ORDER BY slot) AS closing_costs
FROM padded p LEFT JOIN babylon_state.site_statement_block_v1 b
    ON (b.campaign_id,b.resolve_tick,b.block_key)=($1,$2,p.block_key)
GROUP BY p.block_key,p.commodity_ordinal,b.present
