//! Closing evidence, funded alternatives and next-period limits for captured companies.
mod evidence;
mod execution;
mod model;
mod strategy;
#[cfg(test)]
mod tests;
mod wire;
pub(crate) use execution::CompanyInvestment;
pub use model::{
    CompanyCondition, CompanyConditionOrder, CompanyPortfolio, CompanyPortfolioEvidence,
    CompanyPortfolioPolicy, CompanyPortfolioRegister, CompanyPortfolioSelection,
    CompanyProcessEvidence, CompanyProcessPlan,
};
pub use wire::COMPANY_PORTFOLIO_DOMAIN;
