//! Whole-site controllers derived only while admitting a company-enabled national foundation.
mod assign;
mod capture;
mod model;
mod scale;
pub(in crate::national_economy) use scale::partition;
mod treasury;
pub(in crate::national_economy) use capture::from_workplaces;
pub use model::{
    CensusDivision, CompanyBand, CompanyCapture, CompanyCaptureError, CompanyKey, CompanyMember,
    CompanyPolicy, CompanyPopulation, DivisionPopulation, EmploymentTargets,
    ExperimentalPopulation,
};
pub(in crate::national_economy) use treasury::fund;
pub use treasury::{
    BeneficiaryClaim, CompanyFinances, CompanyTreasury, MemberFunding, OriginalClaim, TreasuryError,
};
#[cfg(test)]
mod tests;
