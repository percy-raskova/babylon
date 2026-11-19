//! Captured monetary opening for national company controllers.
mod claims;
mod model;
mod opening;
#[cfg(test)]
mod tests;
pub use model::{
    BeneficiaryClaim, CompanyFinances, CompanyTreasury, MemberFunding, OriginalClaim, TreasuryError,
};
pub(in crate::national_economy) use opening::fund;
