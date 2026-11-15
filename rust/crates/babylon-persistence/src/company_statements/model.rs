//! Distinct legal books and the entries eliminated on consolidation.
use crate::identity::CampaignId;
use crate::national_economy::companies::CompanyKey;
use crate::observer_reader::ObserverEconomyError;
use crate::site_financial_statements::{SiteBalanceSheet, SiteStatementsError};
use babylon_kernel::currency::{Currency, CurrencyOverflow};
use babylon_material_circuit::{CompanyId, SiteId};
use std::fmt::{Display, Formatter, Result as FmtResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompanyStatementsError {
    Read(ObserverEconomyError),
    MembershipNotCaptured,
    TreasuryNotCaptured,
    MonetaryBooksUnavailable,
    SiteBooks(SiteStatementsError),
    MemberMismatch(SiteId),
    TreasuryMismatch(CompanyId),
    BasisMismatch,
    PeriodMismatch,
    ActivityMismatch,
    Arithmetic,
}
impl From<ObserverEconomyError> for CompanyStatementsError {
    fn from(value: ObserverEconomyError) -> Self {
        Self::Read(value)
    }
}
impl From<CurrencyOverflow> for CompanyStatementsError {
    fn from(_: CurrencyOverflow) -> Self {
        Self::Arithmetic
    }
}
impl Display for CompanyStatementsError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "company statements refused: {self:?}")
    }
}
impl std::error::Error for CompanyStatementsError {}

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
pub struct CompanyBalance {
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub cash: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub reserves: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub receivables: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub inventory: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub freight: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub equipment: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub investments: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub assets: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub liabilities: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub equity: Currency,
    #[serde(deserialize_with = "super::statements::from_decimal")]
    pub retained_earnings: Currency,
}
impl Default for CompanyBalance {
    fn default() -> Self {
        let z = Currency::from_micro_units(0);
        Self {
            cash: z,
            reserves: z,
            receivables: z,
            inventory: z,
            freight: z,
            equipment: z,
            investments: z,
            assets: z,
            liabilities: z,
            equity: z,
            retained_earnings: z,
        }
    }
}
impl CompanyBalance {
    pub(super) fn from_sheet(s: &SiteBalanceSheet) -> Result<Self, CurrencyOverflow> {
        Ok(Self {
            cash: s.cash,
            reserves: s.payroll_reserves.checked_add(s.purchase_reserves)?,
            receivables: s.wage_receivables,
            inventory: s.inventory,
            freight: s.freight,
            equipment: s.equipment,
            investments: s.equity_investments,
            assets: s.total_assets,
            liabilities: s.total_liabilities,
            equity: s.total_equity,
            retained_earnings: s.retained_earnings,
        })
    }

    pub(super) fn add(&mut self, other: &Self) -> Result<(), CurrencyOverflow> {
        self.cash = self.cash.checked_add(other.cash)?;
        self.reserves = self.reserves.checked_add(other.reserves)?;
        self.receivables = self.receivables.checked_add(other.receivables)?;
        self.inventory = self.inventory.checked_add(other.inventory)?;
        self.freight = self.freight.checked_add(other.freight)?;
        self.equipment = self.equipment.checked_add(other.equipment)?;
        self.investments = self.investments.checked_add(other.investments)?;
        self.assets = self.assets.checked_add(other.assets)?;
        self.liabilities = self.liabilities.checked_add(other.liabilities)?;
        self.equity = self.equity.checked_add(other.equity)?;
        self.retained_earnings = self
            .retained_earnings
            .checked_add(other.retained_earnings)?;
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EliminatedMember {
    pub site: SiteId,
    pub cash: Currency,
    /// One wholly owned investment, eliminated against this member’s opening equity.
    pub investment: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompanyOpening {
    pub company: CompanyId,
    pub key: CompanyKey,
    pub parent: CompanyBalance,
    pub subsidiaries: CompanyBalance,
    pub eliminated_member_investment: Currency,
    pub consolidated: CompanyBalance,
    pub members: Vec<EliminatedMember>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompanyOpeningReport {
    pub campaign: CampaignId,
    pub foundation: [u8; 32],
    pub companies: Vec<CompanyOpening>,
}
