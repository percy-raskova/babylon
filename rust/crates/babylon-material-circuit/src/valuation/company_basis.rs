//! Immediate legal carrying amounts for consolidation, in native operation order.
use super::book::StockKey;
use super::close::ActiveCosts;
use super::Result;
use crate::{
    AccountId, EquipmentCohortId, FreightLotId, GoodId, InstallationId, MaterialCircuitError,
    OutboundOrderId, ProcessId, SiteId, UnitId,
};
use babylon_kernel::currency::Currency;

/// Each asset belongs to a legal operating site. Process and handoff entries clear within a close.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum CompanyBasisAsset {
    Stock(SiteId, GoodId, UnitId),
    Freight(SiteId, FreightLotId),
    Process(SiteId, ProcessId),
    Installation(SiteId, InstallationId),
    Equipment(SiteId, EquipmentCohortId),
    Handoff(SiteId, OutboundOrderId),
}
impl CompanyBasisAsset {
    #[must_use]
    pub const fn site(self) -> SiteId {
        match self {
            Self::Stock(s, ..)
            | Self::Freight(s, _)
            | Self::Process(s, _)
            | Self::Installation(s, _)
            | Self::Equipment(s, _)
            | Self::Handoff(s, _) => s,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CompanySale {
    pub order: OutboundOrderId,
    pub buyer: AccountId,
    pub proceeds: Currency,
}
/// Withdrawal from the exact opening legal carrying amount and physical denominator.
/// Whole temporary pools transfer in full. A missing destination represents legal expensing
/// or a sale to a principal outside the operating-site stock ledger.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CompanyBasisMovement {
    pub source: CompanyBasisAsset,
    pub destination: Option<CompanyBasisAsset>,
    pub sale: Option<CompanySale>,
    pub opening: Currency,
    pub available: u64,
    pub quantity: u64,
}
impl CompanyBasisMovement {
    /// Checked withdrawal using the same residual rule as the native historical-cost ledger.
    /// # Errors
    /// Refuses negative bases, incompatible ownership and invalid physical withdrawals.
    pub fn released(&self, basis: Currency) -> Result<Currency> {
        if self.quantity == 0 || self.opening.micro_units() < 0 {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        match (self.sale, self.destination) {
            (Some(sale), dest) => {
                if sale.proceeds.micro_units() < 0
                    || dest.map(CompanyBasisAsset::site)
                        != match sale.buyer {
                            AccountId::Site(site) => Some(site),
                            _ => None,
                        }
                {
                    return Err(MaterialCircuitError::ValuationInvariant);
                }
            }
            (None, Some(to)) if to.site() != self.source.site() => {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            _ => {}
        }
        super::portion(basis, self.available, self.quantity)
    }
}
pub const MAX_COMPANY_BASIS_MOVEMENTS: usize = crate::MAX_INPUT_COEFFICIENTS
    + 3 * crate::MAX_SERVICE_RECEIPTS_PER_PERIOD
    + 16 * crate::MAX_MATERIAL_CIRCUIT_ROWS;

impl ActiveCosts {
    pub(super) fn transfer(&mut self, movement: &CompanyBasisMovement) -> Result<()> {
        if movement.quantity != 0 {
            if let Some(rows) = &mut self.company_basis {
                if rows.len() >= MAX_COMPANY_BASIS_MOVEMENTS {
                    return Err(MaterialCircuitError::RowLimit);
                }
                rows.push(*movement);
            }
        }
        Ok(())
    }

    pub(super) fn withdraw(
        &mut self,
        key: StockKey,
        available: u64,
        quantity: u64,
        destination: Option<CompanyBasisAsset>,
        sale: Option<CompanySale>,
    ) -> Result<Currency> {
        if self.company_basis.is_some() && quantity > 0 {
            if let AccountId::Site(site) = key.0 {
                let opening = *self
                    .book
                    .stocks
                    .get(&key)
                    .ok_or(MaterialCircuitError::ValuationInvariant)?;
                self.transfer(&CompanyBasisMovement {
                    source: CompanyBasisAsset::Stock(site, key.1, key.2),
                    destination,
                    sale,
                    available,
                    quantity,
                    opening,
                })?;
            }
        }
        self.book.take_stock(key, available, quantity)
    }

    pub(super) fn entire(
        &mut self,
        source: CompanyBasisAsset,
        destination: CompanyBasisAsset,
        opening: Currency,
    ) -> Result<()> {
        self.transfer(&CompanyBasisMovement {
            source,
            destination: Some(destination),
            sale: None,
            opening,
            available: 1,
            quantity: 1,
        })
    }
}
