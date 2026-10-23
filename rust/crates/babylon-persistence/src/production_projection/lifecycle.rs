//! Period-local order witnesses, including admissions absent from both snapshots.
//! These joins authenticate receipts; they do not allocate, plan, or replay work.
mod investment;

mod services;

#[path = "lifecycle/period.rs"]
mod period;

#[allow(unused_imports)]
use period::{
    add, add_movements, add_transport_movements, admit_firms, admit_households, advance_purchase,
    check_cash, check_purchases, monetary, offer_index, purchase_amounts, quantities, reconcile,
    OfferKey, Result,
};
#[allow(unused_imports)]
pub(super) use period::{join, recurring};
#[allow(unused_imports)]
pub(crate) use period::{validate_period, PeriodOrders};

#[allow(unused_imports)]
use super::ProductionProjectionError;
#[allow(unused_imports)]
use babylon_kernel::currency::Currency;
#[allow(unused_imports)]
use babylon_material_circuit::{
    recurring_household_order_id, recurring_procurement_order_id, AccountId, CircuitAccounting,
    FinalDemandOrder, MaterialCircuitState, MonetaryCircuit, MoneyLocation, MoneyTransferPurpose,
    OrderAccessMode, OrderId, OrderRow, OutboundOrderId, PurchaseEscrow, RecurringEconomy,
};
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialTickReceipts;
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
