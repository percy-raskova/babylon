//! Sparse signed differences between subsidiary legal basis and group historical cost.
use super::{CompanyEntry, CompanyEntryKind, CompanyStatementsError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CompanyBasisAsset, CompanyBasisMovement, CompanyId, SiteId,
};
use std::collections::BTreeMap;

#[derive(Default, Debug, Clone)]
pub(super) struct CompanyCarryingLedger {
    pub(super) balances: BTreeMap<CompanyBasisAsset, Currency>,
}
#[derive(Debug)]
pub(super) struct MarginActivity {
    pub entries: Vec<CompanyEntry>,
    pub internal_sales: Currency,
    pub internal_cogs: Currency,
    pub new_internal_margin: Currency,
    pub realized_margin: Currency,
    pub realized_on_sales: Currency,
}
impl Default for MarginActivity {
    fn default() -> Self {
        let zero = Currency::from_micro_units(0);
        Self {
            entries: Vec::new(),
            internal_sales: zero,
            internal_cogs: zero,
            new_internal_margin: zero,
            realized_margin: zero,
            realized_on_sales: zero,
        }
    }
}
impl CompanyCarryingLedger {
    pub(super) fn margin(&self, asset: CompanyBasisAsset) -> Currency {
        self.balances
            .get(&asset)
            .copied()
            .unwrap_or_else(|| Currency::from_micro_units(0))
    }
    fn credit(
        &mut self,
        node: CompanyBasisAsset,
        amount: Currency,
    ) -> Result<(), CompanyStatementsError> {
        if amount.micro_units() != 0 {
            let total = self.margin(node).checked_add(amount)?;
            if total.micro_units() == 0 {
                self.balances.remove(&node);
            } else {
                self.balances.insert(node, total);
            }
        }
        Ok(())
    }
    pub(super) fn close(
        &mut self,
        members: &BTreeMap<SiteId, CompanyId>,
        rows: &[CompanyBasisMovement],
    ) -> Result<BTreeMap<CompanyId, MarginActivity>, CompanyStatementsError> {
        let mut activity = BTreeMap::<CompanyId, MarginActivity>::new();
        for (ordinal, row) in rows.iter().enumerate() {
            let Some(&company) = members.get(&row.source.site()) else {
                continue;
            };
            let legal = row
                .released(row.opening)
                .map_err(|_| CompanyStatementsError::BasisMismatch)?;
            let group = row.opening.checked_sub(self.margin(row.source))?;
            let group_out = row
                .released(group)
                .map_err(|_| CompanyStatementsError::BasisMismatch)?;
            let released = legal.checked_sub(group_out)?;
            self.credit(row.source, group_out.checked_sub(legal)?)?;
            let a = activity.entry(company).or_default();
            let internal = row.sale.filter(
                |s| matches!(s.buyer,AccountId::Site(site) if members.get(&site)==Some(&company)),
            );
            if let Some(sale) = internal {
                let target = row
                    .destination
                    .ok_or(CompanyStatementsError::BasisMismatch)?;
                let gain = sale.proceeds.checked_sub(legal)?;
                let mut e = CompanyEntry::new(
                    39,
                    ordinal,
                    CompanyEntryKind::InternalSale,
                    AccountId::Site(row.source.site()),
                    Some(sale.buyer),
                    sale.proceeds,
                );
                e.legal_cost_micros = legal.micro_units().to_string();
                e.group_cost_micros = group_out.micro_units().to_string();
                e.margin_created_micros = gain.micro_units().to_string();
                a.entries.push(e);
                a.internal_sales = a.internal_sales.checked_add(sale.proceeds)?;
                a.internal_cogs = a.internal_cogs.checked_add(legal)?;
                a.new_internal_margin = a.new_internal_margin.checked_add(gain)?;
                self.credit(target, released.checked_add(gain)?)?;
            } else if let Some(target) = row.destination.filter(|_| row.sale.is_none()) {
                self.credit(target, released)?;
            } else {
                if released.micro_units() != 0 {
                    let (kind, buyer, proceeds) = row.sale.map_or(
                        (
                            CompanyEntryKind::Expense,
                            None,
                            Currency::from_micro_units(0),
                        ),
                        |s| (CompanyEntryKind::ExternalSale, Some(s.buyer), s.proceeds),
                    );
                    let mut e = CompanyEntry::new(
                        39,
                        ordinal,
                        kind,
                        AccountId::Site(row.source.site()),
                        buyer,
                        proceeds,
                    );
                    e.legal_cost_micros = legal.micro_units().to_string();
                    e.group_cost_micros = group_out.micro_units().to_string();
                    e.margin_realized_micros = released.micro_units().to_string();
                    a.entries.push(e);
                }
                a.realized_margin = a.realized_margin.checked_add(released)?;
                if row.sale.is_some() {
                    a.realized_on_sales = a.realized_on_sales.checked_add(released)?;
                }
            }
        }
        if self.balances.keys().any(|k| {
            matches!(
                k,
                CompanyBasisAsset::Process(..) | CompanyBasisAsset::Handoff(..)
            )
        }) {
            return Err(CompanyStatementsError::BasisMismatch);
        }
        Ok(activity)
    }
}
