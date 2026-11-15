//! Company material policy, observed period evidence and the four feasible action bundles.
use crate::{CompanyId, MaterialCircuitError, ProcessId, SiteId};
use babylon_kernel::currency::Currency;
use std::result::Result as StdResult;
pub(super) type Result<T> = StdResult<T, MaterialCircuitError>;

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub struct CompanyPortfolioPolicy {
    pub rows: [[u16; 4]; 4],
    pub high_utilization_bps: u16,
    pub history_periods: u8,
    pub modest_expansion_bps: u16,
}
impl CompanyPortfolioPolicy {
    /// # Errors
    /// Refuses an empty defer branch or terms outside the bounded portfolio contract.
    pub fn validate(self) -> Result<()> {
        if !(1..=3).contains(&self.history_periods)
            || !(1..=10_000).contains(&self.high_utilization_bps)
            || self.modest_expansion_bps > 5_000
            || self.rows.iter().any(|r| r[0] == 0)
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        Ok(())
    }
}
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum CompanyPortfolio {
    Defer,
    ReplacementOnly,
    ModestExpansion,
    LargerExpansion,
}
impl CompanyPortfolio {
    #[must_use]
    pub const fn from_index(i: u8) -> Option<Self> {
        match i {
            0 => Some(Self::Defer),
            1 => Some(Self::ReplacementOnly),
            2 => Some(Self::ModestExpansion),
            3 => Some(Self::LargerExpansion),
            _ => None,
        }
    }
}
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub struct CompanyPortfolioSelection {
    pub company: CompanyId,
    pub evidence_period: u64,
    pub portfolio: CompanyPortfolio,
}
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum CompanyCondition {
    Loss,
    Replacement,
    Spare,
    UnmetDemand,
    NoMatchingRow,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompanyProcessEvidence {
    pub site: SiteId,
    pub process: ProcessId,
    pub produced_batches: u64,
    pub capacity_batches: u64,
    pub unmet_accepted_units: u64,
    pub used_service_batches: u64,
    pub replacement: u64,
    pub expansion: u64,
    pub unit_price: Currency,
    pub free_cash: Currency,
    pub earnings_budget: Currency,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompanyProcessPlan {
    pub site: SiteId,
    pub process: ProcessId,
    pub replacement: u64,
    pub expansion: u64,
    pub funding: Currency,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompanyPortfolioEvidence {
    pub company: CompanyId,
    pub period: u64,
    /// Consecutive actual operating incomes, oldest first and ending at period.
    pub history: Vec<Currency>,
    pub treasury_available: Currency,
    pub processes: Vec<CompanyProcessEvidence>,
    pub original_weights: [u16; 4],
    pub weights: [u16; 4],
    pub feasible: [bool; 4],
    pub condition: CompanyCondition,
    pub plans: [Vec<CompanyProcessPlan>; 4],
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompanyPortfolioRegister {
    pub companies: Vec<CompanyPortfolioEvidence>,
}
pub(super) fn add(a: Currency, b: Currency) -> Result<Currency> {
    a.checked_add(b)
        .map_err(|_| MaterialCircuitError::Arithmetic)
}
pub(super) fn zero() -> Currency {
    Currency::from_micro_units(0)
}
