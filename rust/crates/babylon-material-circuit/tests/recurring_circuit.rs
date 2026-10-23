//! Executable witness for the independently worked eight-period accounting control.

#[path = "support/economic_location_cases.rs"]
mod economic_location_cases;

#[path = "support/household_need_basis_cases.rs"]
mod household_need_basis_cases;

#[path = "support/empty_workforce_cases.rs"]
mod empty_workforce_cases;

#[path = "support/household_budget_cases.rs"]
mod household_budget_cases;

#[path = "support/household_time_cases.rs"]
mod household_time_cases;

#[path = "support/aid_cases.rs"]
mod aid_cases;

#[path = "support/rolling_capacity.rs"]
mod rolling_capacity;

#[path = "support/cost_income.rs"]
mod cost_income;

#[path = "support/local_cost.rs"]
mod local_cost;

#[path = "support/goods_cost_prices.rs"]
mod goods_cost_prices;

#[path = "recurring_circuit/integrated_controls.rs"]
mod integrated_controls;

#[path = "recurring_circuit/support.rs"]
mod support;

#[allow(unused_imports)]
use support::{
    a_household_purchase_without_a_recipient_stock_is_refused_before_reserving_cash,
    a_shared_production_and_retail_pool_requests_each_kind_of_work_once,
    captured_household_policies_refuse_old_bytes_bad_cursors_and_noncanonical_rows,
    cash_backed_unfilled_retail_demand_can_restart_a_producer_with_no_opening_sales,
    consumption_or_procurement_failure_leaves_all_opening_accounts_unchanged, corridor, economy,
    eight_period_control_reproduces_paid_idle_withdrawal_recovery_and_conservation, good, hours,
    household, inventory, money, node, opening, output,
    prior_funded_transit_suppresses_duplicate_procurement_and_does_not_supply_current_production,
    process, producer_retail_opening, recurring_mut,
    responsive_next_quote_does_not_reprice_existing_reserves,
    retained_finite_purchase_restores_attendance_when_recurring_purchases_are_disabled, route,
    site, units,
};

#[allow(unused_imports)]
use babylon_kernel::currency::Currency;

#[allow(unused_imports)]
use babylon_material_circuit::*;
