//! Source-bound treasury amounts and beneficiary provenance.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, CompanyId, SiteId};
use std::result::Result as StdResult;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TreasuryError {
    InvalidRate,
    OpeningBook,
    MissingSite(SiteId),
    MissingFloor(SiteId),
    InvalidBasis(SiteId),
    InvalidClaims(SiteId),
    UnrepresentedCapital(CompanyId),
    Arithmetic,
}
pub(super) type Result<T> = StdResult<T, TreasuryError>;

/// Fixed evidence for an opening transfer. All amounts use the native currency unit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemberFunding {
    pub site: SiteId,
    pub company: CompanyId,
    pub original_cash: Currency,
    pub cash_floor: Currency,
    pub swept: Currency,
    pub remaining_cash: Currency,
    pub original_capital: Currency,
    pub remaining_capital: Currency,
}

/// Source capital is the historical-cost equity of the subsidiary before centralization.
/// An original claim's exact capital entitlement is capital × shares / `site_total_shares`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OriginalClaim {
    pub site: SiteId,
    pub company: CompanyId,
    pub beneficiary: AccountId,
    pub capital: Currency,
    pub original_shares: u64,
    pub site_total_shares: u64,
    pub original_carrying_value: Currency,
}

/// Share of a parent is weight / that parent's `total_weight`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BeneficiaryClaim {
    pub company: CompanyId,
    pub beneficiary: AccountId,
    pub weight: u128,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompanyTreasury {
    pub company: CompanyId,
    pub cash: Currency,
    pub subsidiary_capital: Currency,
    pub original_capital: Currency,
    /// Denominator of the company-wide capital-weight amounts, in micro-currency.
    pub common_denominator: u128,
    pub total_weight: u128,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompanyFinances {
    pub sweep_bps: u16,
    pub members: Vec<MemberFunding>,
    pub sources: Vec<OriginalClaim>,
    pub claims: Vec<BeneficiaryClaim>,
    pub treasuries: Vec<CompanyTreasury>,
}
