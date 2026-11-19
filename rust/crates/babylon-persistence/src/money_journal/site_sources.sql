-- Validate the typed source before sparse zero encoding. A missing monetary line cannot become zero.
CREATE TEMP TABLE site_statement_source (
    LIKE babylon_state.site_statement_v1,
    PRIMARY KEY(site_key),
    CHECK (site_key BETWEEN 0 AND 16777214 AND site_ordinal BETWEEN 0 AND 16777214),
    CHECK (num_nonnulls(
        opening_cash_micros, opening_purchase_reserves_micros, opening_payroll_reserves_micros,
        opening_wage_receivables_micros, opening_inventory_micros, opening_freight_micros,
        opening_equity_investments_micros, opening_equipment_micros, opening_total_assets_micros,
        opening_wage_payables_micros, opening_total_liabilities_micros, opening_opening_capital_micros,
        opening_contributed_capital_micros, opening_retained_earnings_micros, opening_total_equity_micros,
        closing_cash_micros, closing_purchase_reserves_micros, closing_payroll_reserves_micros,
        closing_wage_receivables_micros, closing_inventory_micros, closing_freight_micros,
        closing_equity_investments_micros, closing_equipment_micros, closing_total_assets_micros,
        closing_wage_payables_micros, closing_total_liabilities_micros, closing_opening_capital_micros,
        closing_contributed_capital_micros, closing_retained_earnings_micros, closing_total_equity_micros,
        income_sales_micros, income_wage_income_micros, income_cost_of_goods_sold_micros,
        income_productive_labor_capitalized_micros, income_installation_labor_capitalized_micros, income_equipment_wear_capitalized_micros,
        income_idle_labor_expense_micros, income_handling_expense_micros, income_maintenance_labor_expense_micros,
        income_maintenance_material_expense_micros, income_freight_loss_expense_micros, income_consumption_expense_micros,
        income_final_demand_outlay_micros, income_unused_service_expense_micros, income_tax_income_micros,
        income_tax_expense_micros, income_public_transfer_income_micros, income_public_transfer_expense_micros,
        income_distribution_income_micros, income_gift_income_micros, income_gift_expense_micros,
        income_agency_observation_labor_expense_micros, cash_flow_operating_micros, cash_flow_investing_micros,
        cash_flow_financing_micros, cash_flow_reserve_reclassification_micros, net_income_micros,
        contributions_received_micros, distributions_paid_micros, change_in_equity_micros) IN (0,60))
) ON COMMIT DROP;
ALTER TABLE pg_temp.site_statement_source
    ALTER campaign_id SET NOT NULL, ALTER resolve_tick SET NOT NULL, ALTER site_ordinal SET NOT NULL;
CREATE TEMP TABLE site_stock_source (
    LIKE babylon_state.site_stock_balance_v1,
    PRIMARY KEY(site_key,commodity_ordinal),
    CHECK (site_key BETWEEN 0 AND 16777214 AND commodity_ordinal>=0)
) ON COMMIT DROP;
ALTER TABLE pg_temp.site_stock_source ALTER campaign_id SET NOT NULL, ALTER resolve_tick SET NOT NULL;
