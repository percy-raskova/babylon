//! Captured claims and budgets; identity does not infer class or jurisdiction.
use crate::{
    AccountId, CompanyId, FinalDemandPrincipalId, MaterialCircuitError, PublicAccountId, SiteId,
    StaffingMemberId,
};
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use std::collections::BTreeSet;

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
/// One row for each basis and public recipient of a payer in this bounded policy.
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
    /// Named programs of the public accounts that spend in proportion, in key order.
    pub programs: Vec<PublicProgram>,
    /// The people laid off in play and still looking, one record for each staffing member that has
    /// any, in member order.
    pub layoffs: Vec<LayoffRecord>,
}
/// The most half periods an after-layoff program may pay for.
pub const MAX_LAYOFF_HALF_PERIODS: u16 = 26;
/// The most cohorts of one record: the periods of the longest term, rounded up.
pub const MAX_LAYOFF_PERIODS: usize = 13;
/// One staffing member's people laid off in play and still looking, newest first: `cohorts[k]`
/// were laid off at the staffing of the period `k + 1` before this opening. Never empty; the last
/// entry is not 0.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LayoffRecord {
    pub member_id: StaffingMemberId,
    /// The schedule of the job lost, set when the record is made and never refreshed.
    pub hours_per_person: u64,
    pub cohorts: Vec<u64>,
}
impl FinancialInstitutions {
    /// Whether the state needs the tail of the financial rows (version 25 or 26): a budget in
    /// proportion, or a payer with more than one tax row.
    #[must_use]
    pub(crate) fn has_public_program_extension(&self) -> bool {
        let mut payers = BTreeSet::new();
        !self.programs.is_empty()
            || self
                .public_budgets
                .iter()
                .any(|b| b.rule != PublicSpendingRule::CappedInOrder)
            || !self.layoffs.is_empty()
            || !self.taxes.iter().all(|r| payers.insert(r.payer))
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
            programs: vec![],
            layoffs: vec![],
        }
    }
}
/// A short name that politics refers to: 1 to 32 bytes of `a-z`, `0-9` and `_`, a letter first.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PublicProgramKey(String);
impl PublicProgramKey {
    /// # Errors
    /// `PublicProgramInvariant` for an empty, long or ill-formed key.
    pub fn new(text: &str) -> Result<Self, MaterialCircuitError> {
        let mut bytes = text.bytes();
        let well_formed = bytes.next().is_some_and(|b| b.is_ascii_lowercase())
            && bytes.all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_');
        if !well_formed || text.len() > 32 {
            return Err(MaterialCircuitError::PublicProgramInvariant);
        }
        Ok(Self(text.to_owned()))
    }
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
/// What a program pays; its kind is fixed and its figures may change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PublicProgramTerms {
    /// For each person of the recipient account's cohort (tag 1).
    PerPerson { amount_per_person: Currency },
    /// A share of the pay lost, for a worker laid off in play (tag 2).
    AfterLayoff {
        wage_share_bps: u16,
        half_periods: u16,
    },
}
/// A named rule of one public account that pays each of its recipients every period.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicProgram {
    /// Fixed.
    pub key: PublicProgramKey,
    /// Fixed.
    pub payer: PublicAccountId,
    /// May change.
    pub rank: u32,
    /// Its kind is fixed; its figures may change.
    pub terms: PublicProgramTerms,
    /// May change. Each is the principal of a household account.
    pub recipients: Vec<FinalDemandPrincipalId>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicProgramReceipt {
    pub period: u64,
    pub public_account: PublicAccountId,
    pub program: PublicProgramKey,
    pub recipient: FinalDemandPrincipalId,
    pub rank: u32,
    /// Per person: the account's persons. After a layoff: the persons covered this period.
    pub covered_persons: u64,
    pub due: Currency,
    pub paid: Currency,
    pub unfunded: Currency,
}
impl PublicProgramReceipt {
    /// # Errors
    /// `PublicProgramInvariant` unless `period > 0` and `0 <= paid <= due = paid + unfunded`.
    pub fn validate(&self) -> Result<(), MaterialCircuitError> {
        let sum = self.paid.checked_add(self.unfunded);
        let zero = Currency::from_micro_units(0);
        if self.period == 0 || self.paid < zero || self.unfunded < zero || sum != Ok(self.due) {
            return Err(MaterialCircuitError::PublicProgramInvariant);
        }
        Ok(())
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
