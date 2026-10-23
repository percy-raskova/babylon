#[path = "support/household_service_time_cases.rs"]
mod household_service_time_cases;

#[path = "support/period_service_cases.rs"]
mod service_cases;

#[path = "period_services/order_limits.rs"]
mod order_limits;

#[path = "period_services/inventory_limits.rs"]
mod inventory_limits;

#[path = "period_services/support.rs"]
mod support;

#[allow(unused_imports)]
use support::{
    a_service_dependency_cycle_and_durable_service_stock_are_refused_atomically,
    absent_utility_constrains_services_and_goods_without_spending_work_twice, funded, good,
    household, money, native_services_feed_later_stages_without_freight_or_stored_service, opening,
    process, site, unit,
};

#[allow(unused_imports)]
use babylon_kernel::currency::Currency;

#[allow(unused_imports)]
use babylon_material_circuit::*;
