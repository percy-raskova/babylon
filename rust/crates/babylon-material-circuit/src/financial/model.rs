//! Captured claims and budgets; identity does not infer class or jurisdiction.
use crate::{AccountId, CompanyId, PublicAccountId, SiteId};
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;

crate::model::identity_type!(ContributionId);
/// Source-derived, immutable shareholder capital weights and captured payout rate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompanyPayoutPolicy {
    pub company: CompanyId,
    pub earnings_bps: u16,
    pub claims: Vec<(AccountId, u128)>,
}
/// One ultimate owner allocation from a single frozen company payout basis.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompanyDistributionReceipt {
    pub period: u64,
    pub company: CompanyId,
    pub beneficiary: AccountId,
    pub weight: u128,
    pub total_weight: u128,
    pub eligible_earnings: Currency,
    pub protected_contributions: Currency,
    pub declared: Currency,
    pub paid: Currency,
}

/// Only non-workplace institutions use this table. Site and household locations
/// retain their existing physical/residence authority.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstitutionLocation {
    pub account: AccountId,
    pub location: EconomicLocation,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OwnershipClaim {
    pub issuer_site_id: SiteId,
    pub beneficiary: AccountId,
    pub shares: u64,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DistributionPolicy {
    pub issuer_site_id: SiteId,
    pub earnings_fraction_bps: u16,
    pub period_cap: Currency,
    pub cash_floor: Currency,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum TaxBasis {
    WageIncome = 1,
    PositiveOperatingIncome = 2,
}
/// One explicitly captured public jurisdiction per payer in this bounded policy.
/// Uncollected assessment is disclosed, not an implied debt or receivable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaxPolicy {
    pub payer: AccountId,
    pub public_recipient: PublicAccountId,
    pub basis: TaxBasis,
    pub rate_bps: u16,
    pub cash_floor: Currency,
}
/// How one public account's budget is spent.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum PublicSpendingRule {
    /// Today: `min(period_cap, cash less floor)`; in a rank, the first by identifier first.
    CappedInOrder = 1,
    /// Cash less floor, no cap; ranks lowest first; the first rank not covered is cut in proportion.
    CashInProportion = 2,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicBudget {
    pub public_account: PublicAccountId,
    pub period_cap: Currency,
    pub cash_floor: Currency,
    pub rule: PublicSpendingRule,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum PublicTransferTreatment {
    HouseholdIncomeSupport = 1,
    ProviderOperatingGrant = 2,
    AgencyAppropriation = 3,
}
/// Lower captured priority numbers are funded first. Identity breaks ties.
/// Capital support instead uses a finite `CapitalContributionOrder`; spending a
/// grant is not itself evidence of consumption or service performance.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicAllocation {
    pub public_account: PublicAccountId,
    pub recipient: AccountId,
    pub treatment: PublicTransferTreatment,
    pub priority: u32,
    pub amount_per_period: Currency,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CapitalContributionOrder {
    pub id: ContributionId,
    pub due_period: u64,
    pub contributor: AccountId,
    pub issuer_site_id: SiteId,
    pub amount: Currency,
}
/// Explicit empty tables capture controls without public/ownership actions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FinancialInstitutions {
    pub locations: Vec<InstitutionLocation>,
    pub ownership: Vec<OwnershipClaim>,
    pub distributions: Vec<DistributionPolicy>,
    pub taxes: Vec<TaxPolicy>,
    pub public_budgets: Vec<PublicBudget>,
    pub public_allocations: Vec<PublicAllocation>,
    pub contributions: Vec<CapitalContributionOrder>,
}
impl FinancialInstitutions {
    /// Whether the state needs the tail of the financial rows (version 25 or 26).
    #[must_use]
    pub(crate) fn has_public_program_extension(&self) -> bool {
        self.public_budgets
            .iter()
            .any(|b| b.rule != PublicSpendingRule::CappedInOrder)
    }
    #[must_use]
    pub const fn empty() -> Self {
        Self {
            locations: vec![],
            ownership: vec![],
            distributions: vec![],
            taxes: vec![],
            public_budgets: vec![],
            public_allocations: vec![],
            contributions: vec![],
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicBudgetReceipt {
    pub period: u64,
    pub public_account: PublicAccountId,
    pub recipient: AccountId,
    pub treatment: PublicTransferTreatment,
    pub priority: u32,
    pub requested: Currency,
    pub paid: Currency,
    pub unfunded: Currency,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaxReceipt {
    pub period: u64,
    pub payer: AccountId,
    pub public_recipient: PublicAccountId,
    pub basis: TaxBasis,
    pub rate_bps: u16,
    pub taxable_amount: Currency,
    pub assessed: Currency,
    pub collected: Currency,
    pub uncollected: Currency,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DistributionReceipt {
    pub period: u64,
    pub issuer_site_id: SiteId,
    pub beneficiary: AccountId,
    pub shares: u64,
    pub total_shares: u64,
    pub eligible_earnings: Currency,
    pub declared_total: Currency,
    pub paid: Currency,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CapitalContributionReceipt {
    pub period: u64,
    pub id: ContributionId,
    pub contributor: AccountId,
    pub issuer_site_id: SiteId,
    pub requested: Currency,
    pub paid: Currency,
    pub unfunded: Currency,
}
