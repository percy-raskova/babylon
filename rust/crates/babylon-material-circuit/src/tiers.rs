//! Households buy in tiers: a period's lists of what each account has still to buy, and the records
//! of what each wanted and bought in each tier, and so its standard.

mod lists;
mod records;

pub(crate) use lists::HouseholdLists;
pub use records::{
    household_standard, recurring_household_want_order_id, recurring_service_want_order_id,
    HouseholdStandard, HouseholdTierReceipt, HouseholdWantReceipt,
};

#[cfg(test)]
mod tests;
