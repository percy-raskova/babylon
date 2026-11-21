//! The engine's tests of the four moments at which a short market is priced.

#[path = "market_clearing/support.rs"]
mod support;

#[path = "market_clearing/households.rs"]
mod households;

#[path = "market_clearing/service_support.rs"]
mod service_support;

#[path = "market_clearing/services.rs"]
mod services;

#[path = "market_clearing/restock_support.rs"]
mod restock_support;

#[path = "market_clearing/restocking.rs"]
mod restocking;

#[path = "market_clearing/plans.rs"]
mod plans;

#[path = "market_clearing/admission.rs"]
mod admission;

#[path = "market_clearing/wants.rs"]
mod wants;

#[path = "market_clearing/service_wants.rs"]
mod service_wants;

#[path = "market_clearing/unreached_wants.rs"]
mod unreached_wants;
