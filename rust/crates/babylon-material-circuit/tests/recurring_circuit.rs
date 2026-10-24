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

use support::{
    corridor, economy, good, hours, household, inventory, money, node, opening, output, process,
    producer_retail_opening, recurring_mut, route, site, units,
};

use babylon_kernel::currency::Currency;
