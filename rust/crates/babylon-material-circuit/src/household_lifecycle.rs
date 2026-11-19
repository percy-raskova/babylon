//! Resident ages and dated demographic transitions in four-week material periods.
mod advance;
mod close;
mod model;
#[cfg(test)]
mod tests;
mod workforce;
pub(crate) use close::close;
pub(crate) use model::MAX_BIRTHDAY_PERIODS;
pub use model::{
    HouseholdLifecycleBook, HouseholdLifecyclePosition, HouseholdLifecycleRates,
    HouseholdLifecycleReceipt, ResidentAges,
};
pub use workforce::{reconcile_resident_workforce, ResidentWorkforceAttrition};
