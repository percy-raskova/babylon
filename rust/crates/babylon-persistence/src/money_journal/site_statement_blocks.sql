-- Bind signed source ordinals to foundation slots independently for sparse periods.
WITH parts AS (SELECT DISTINCT site_key/32 AS block_key FROM pg_temp.site_statement_source),
padded AS MATERIALIZED (
    SELECT p.block_key,i AS slot,s.site_key,s.site_ordinal,s.opening_cash_micros IS NOT NULL AS monetary,
        ARRAY[
            nullif(s.opening_cash_micros,0), nullif(s.opening_purchase_reserves_micros,0),
            nullif(s.opening_payroll_reserves_micros,0), nullif(s.opening_wage_receivables_micros,0),
            nullif(s.opening_inventory_micros,0), nullif(s.opening_freight_micros,0),
            nullif(s.opening_equity_investments_micros,0), nullif(s.opening_equipment_micros,0),
            nullif(s.opening_total_assets_micros,0), nullif(s.opening_wage_payables_micros,0),
            nullif(s.opening_total_liabilities_micros,0), nullif(s.opening_opening_capital_micros,0),
            nullif(s.opening_contributed_capital_micros,0), nullif(s.opening_retained_earnings_micros,0),
            nullif(s.opening_total_equity_micros,0), nullif(s.closing_cash_micros,0),
            nullif(s.closing_purchase_reserves_micros,0), nullif(s.closing_payroll_reserves_micros,0),
            nullif(s.closing_wage_receivables_micros,0), nullif(s.closing_inventory_micros,0),
            nullif(s.closing_freight_micros,0), nullif(s.closing_equity_investments_micros,0),
            nullif(s.closing_equipment_micros,0), nullif(s.closing_total_assets_micros,0),
            nullif(s.closing_wage_payables_micros,0), nullif(s.closing_total_liabilities_micros,0),
            nullif(s.closing_opening_capital_micros,0), nullif(s.closing_contributed_capital_micros,0),
            nullif(s.closing_retained_earnings_micros,0), nullif(s.closing_total_equity_micros,0),
            nullif(s.income_sales_micros,0), nullif(s.income_wage_income_micros,0),
            nullif(s.income_cost_of_goods_sold_micros,0), nullif(s.income_productive_labor_capitalized_micros,0),
            nullif(s.income_installation_labor_capitalized_micros,0), nullif(s.income_equipment_wear_capitalized_micros,0),
            nullif(s.income_idle_labor_expense_micros,0), nullif(s.income_handling_expense_micros,0),
            nullif(s.income_maintenance_labor_expense_micros,0), nullif(s.income_maintenance_material_expense_micros,0),
            nullif(s.income_freight_loss_expense_micros,0), nullif(s.income_consumption_expense_micros,0),
            nullif(s.income_final_demand_outlay_micros,0), nullif(s.income_unused_service_expense_micros,0),
            nullif(s.income_tax_income_micros,0), nullif(s.income_tax_expense_micros,0),
            nullif(s.income_public_transfer_income_micros,0), nullif(s.income_public_transfer_expense_micros,0),
            nullif(s.income_distribution_income_micros,0), nullif(s.income_gift_income_micros,0),
            nullif(s.income_gift_expense_micros,0), nullif(s.income_agency_observation_labor_expense_micros,0),
            nullif(s.cash_flow_operating_micros,0), nullif(s.cash_flow_investing_micros,0),
            nullif(s.cash_flow_financing_micros,0), nullif(s.cash_flow_reserve_reclassification_micros,0),
            nullif(s.net_income_micros,0), nullif(s.contributions_received_micros,0),
            nullif(s.distributions_paid_micros,0), nullif(s.change_in_equity_micros,0)
        ] AS row_data
    FROM parts p CROSS JOIN generate_series(0,31) AS a(i)
    LEFT JOIN pg_temp.site_statement_source s ON s.site_key=p.block_key*32+i
), flags AS (
    SELECT block_key,string_agg(CASE WHEN site_key IS NULL THEN '0' ELSE '1' END,'' ORDER BY slot)::bit(32) AS present,
        string_agg(CASE WHEN monetary THEN '1' ELSE '0' END,'' ORDER BY slot)::bit(32) AS books,
        CASE WHEN bool_or(site_ordinal<>site_key) THEN
            array_agg(CASE WHEN site_ordinal<>site_key THEN site_ordinal END ORDER BY slot) END AS ordinal_exceptions
    FROM padded GROUP BY block_key
), cells AS (
    SELECT block_key,array_agg(amount ORDER BY slot,field) AS lines
    FROM padded CROSS JOIN LATERAL unnest(row_data) WITH ORDINALITY e(amount,field) GROUP BY block_key
)
SELECT $1::uuid AS campaign_id,$2::bigint AS resolve_tick,f.block_key,f.present,f.books,c.lines,
    r.members AS roster_members,r.sha256 AS roster_sha256,f.ordinal_exceptions
FROM flags f JOIN cells c USING(block_key) LEFT JOIN babylon_state.site_roster_block_v1 r
    ON (r.campaign_id,r.block_key)=($1,f.block_key)
