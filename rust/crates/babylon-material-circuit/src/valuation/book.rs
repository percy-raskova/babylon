//! Bounded carrying amounts and captured equity; no duplicate money balances.
use super::{
    add, portion, sub, zero, CapitalAccount, EquityCarryingValue, FreightCarryingValue,
    HistoricalCostSnapshot, Result, StockCarryingValue, MAX_CARRYING_STOCKS,
};
use crate::{
    AccountId, FreightLotId, GoodId, MaterialCircuitError, MonetaryBook, SiteId, UnitId,
    MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

// A close retains durable stocks until publication, plus one key per possible
// service provider output and per positive admitted service buyer grant.
// Zero-request receipts never credit a grant. ServiceClose::finish removes these
// service keys before final state admission; snapshots retain the durable bound.
const MAX_WORKING_CARRYING_STOCKS: usize =
    MAX_CARRYING_STOCKS + crate::MAX_MATERIAL_CIRCUIT_ROWS + crate::MAX_SERVICE_ORDERS;

pub(super) type StockKey = (AccountId, GoodId, UnitId);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HistoricalCostBook {
    pub(super) accounts: BTreeMap<AccountId, CapitalAccount>,
    pub(super) stocks: BTreeMap<StockKey, Currency>,
    pub(super) freight: BTreeMap<FreightLotId, (SiteId, Currency)>,
    pub(super) equity: BTreeMap<(AccountId, SiteId), Currency>,
    pub(super) equipment: BTreeMap<crate::EquipmentAssetId, (SiteId, Currency)>,
}

impl HistoricalCostBook {
    /// Capture explicit opening carrying amounts and derive initial book capital.
    /// Physical stock/lot identity and zero-quantity validation occurs when the
    /// containing material state is admitted. This is never a period balancing plug.
    /// # Errors
    /// Refuses duplicate/unknown owners, negative costs, row limits and overflow.
    pub fn open(
        money: &MonetaryBook,
        stocks: Vec<StockCarryingValue>,
        freight: Vec<FreightCarryingValue>,
        equity: Vec<EquityCarryingValue>,
        equipment: Vec<crate::EquipmentCarryingValue>,
    ) -> Result<Self> {
        let accounts = money
            .snapshot()
            .accounts
            .into_iter()
            .map(|row| CapitalAccount {
                account: row.id,
                opening_capital: zero(),
                contributed_capital: zero(),
                retained_earnings: zero(),
            })
            .collect();
        let mut book = Self::from_snapshot(HistoricalCostSnapshot {
            accounts,
            stocks,
            freight,
            equity,
            equipment,
        })?;
        let assets = book.net_assets(money)?;
        for (account, value) in assets {
            book.accounts
                .get_mut(&account)
                .ok_or(MaterialCircuitError::ValuationInvariant)?
                .opening_capital = value;
        }
        Ok(book)
    }

    /// Restore only complete explicit captured state, without recapturing capital.
    /// # Errors
    /// Refuses duplicates, negative costs, unknown owners or bounded row excess.
    pub fn from_snapshot(rows: HistoricalCostSnapshot) -> Result<Self> {
        if rows.accounts.len() > crate::MAX_MONETARY_ACCOUNTS
            || rows.stocks.len() > MAX_CARRYING_STOCKS
            || rows.freight.len() > MAX_MATERIAL_CIRCUIT_ROWS
            || rows.equity.len() > crate::MAX_OWNERSHIP_CLAIMS
            || rows.equipment.len() > 2 * MAX_MATERIAL_CIRCUIT_ROWS
        {
            return Err(MaterialCircuitError::RowLimit);
        }
        let mut book = Self {
            accounts: BTreeMap::new(),
            stocks: BTreeMap::new(),
            freight: BTreeMap::new(),
            equity: BTreeMap::new(),
            equipment: BTreeMap::new(),
        };
        for row in rows.accounts {
            if row.opening_capital.micro_units() < 0 || row.contributed_capital.micro_units() < 0 {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            if book.accounts.insert(row.account, row).is_some() {
                return Err(MaterialCircuitError::DuplicateRow);
            }
        }
        for row in rows.stocks {
            if row.amount.micro_units() < 0
                || !book.accounts.contains_key(&row.owner)
                || !matches!(row.owner, AccountId::Site(_) | AccountId::Household(_))
            {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            if book
                .stocks
                .insert((row.owner, row.good_id, row.unit_id), row.amount)
                .is_some()
            {
                return Err(MaterialCircuitError::DuplicateRow);
            }
        }
        for row in rows.freight {
            if row.amount.micro_units() < 0
                || !book.accounts.contains_key(&AccountId::Site(row.owner))
            {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            if book
                .freight
                .insert(row.lot_id, (row.owner, row.amount))
                .is_some()
            {
                return Err(MaterialCircuitError::DuplicateRow);
            }
        }
        for row in rows.equity {
            if row.amount.micro_units() < 0
                || row.owner == AccountId::Site(row.issuer_site_id)
                || !book.accounts.contains_key(&row.owner)
                || !book
                    .accounts
                    .contains_key(&AccountId::Site(row.issuer_site_id))
            {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            if book
                .equity
                .insert((row.owner, row.issuer_site_id), row.amount)
                .is_some()
            {
                return Err(MaterialCircuitError::DuplicateRow);
            }
        }
        for row in rows.equipment {
            if row.amount.micro_units() < 0
                || !book.accounts.contains_key(&AccountId::Site(row.owner))
            {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            if book
                .equipment
                .insert(row.asset, (row.owner, row.amount))
                .is_some()
            {
                return Err(MaterialCircuitError::DuplicateRow);
            }
        }
        Ok(book)
    }

    #[must_use]
    pub fn snapshot(&self) -> HistoricalCostSnapshot {
        HistoricalCostSnapshot {
            equipment: self
                .equipment
                .iter()
                .map(|(&asset, &(owner, amount))| crate::EquipmentCarryingValue {
                    asset,
                    owner,
                    amount,
                })
                .collect(),
            accounts: self.accounts.values().cloned().collect(),
            equity: self
                .equity
                .iter()
                .map(|(&(owner, issuer_site_id), &amount)| EquityCarryingValue {
                    owner,
                    issuer_site_id,
                    amount,
                })
                .collect(),
            stocks: self
                .stocks
                .iter()
                .map(|(&(owner, good_id, unit_id), &amount)| StockCarryingValue {
                    owner,
                    good_id,
                    unit_id,
                    amount,
                })
                .collect(),
            freight: self
                .freight
                .iter()
                .map(|(&lot_id, &(owner, amount))| FreightCarryingValue {
                    lot_id,
                    owner,
                    amount,
                })
                .collect(),
        }
    }

    pub(super) fn take_stock(
        &mut self,
        key: StockKey,
        available: u64,
        quantity: u64,
    ) -> Result<Currency> {
        if quantity == 0 {
            return Ok(zero());
        }
        let cost = self
            .stocks
            .get_mut(&key)
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        let taken = portion(*cost, available, quantity)?;
        *cost = sub(*cost, taken)?;
        Ok(taken)
    }

    pub(super) fn credit_stock(&mut self, key: StockKey, value: Currency) -> Result<()> {
        if !self.stocks.contains_key(&key) && self.stocks.len() >= MAX_WORKING_CARRYING_STOCKS {
            return Err(MaterialCircuitError::RowLimit);
        }
        let cost = self.stocks.entry(key).or_insert_with(zero);
        *cost = add(*cost, value)?;
        Ok(())
    }

    pub(super) fn net_assets(&self, money: &MonetaryBook) -> Result<BTreeMap<AccountId, Currency>> {
        let snapshot = money.snapshot();
        let mut totals: BTreeMap<_, _> = snapshot.accounts.iter().map(|a| (a.id, a.cash)).collect();
        if !totals.keys().eq(self.accounts.keys()) {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        for purchase in snapshot.purchases {
            accumulate(&mut totals, purchase.buyer, purchase.reserved_amount()?)?;
        }
        for shift in snapshot.shifts {
            accumulate(&mut totals, shift.employer, shift.reserved_amount()?)?;
            let owed = shift.outstanding_wages()?;
            accumulate(&mut totals, shift.employer, sub(zero(), owed)?)?;
            accumulate(&mut totals, shift.payee, owed)?;
        }
        for ((owner, _, _), &value) in &self.stocks {
            accumulate(&mut totals, *owner, value)?;
        }
        for &(owner, value) in self.freight.values() {
            accumulate(&mut totals, AccountId::Site(owner), value)?;
        }
        for (&(owner, _), &value) in &self.equity {
            accumulate(&mut totals, owner, value)?;
        }
        for &(owner, value) in self.equipment.values() {
            accumulate(&mut totals, AccountId::Site(owner), value)?;
        }
        Ok(totals)
    }
}

fn accumulate(
    totals: &mut BTreeMap<AccountId, Currency>,
    owner: AccountId,
    value: Currency,
) -> Result<()> {
    let total = totals
        .get_mut(&owner)
        .ok_or(MaterialCircuitError::ValuationInvariant)?;
    *total = add(*total, value)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(index: usize) -> StockKey {
        let mut identity = [0; 32];
        identity[24..].copy_from_slice(&u64::try_from(index).unwrap().to_be_bytes());
        (
            AccountId::Site(SiteId::from_bytes([1; 32])),
            GoodId::from_bytes(identity),
            UnitId::from_bytes([2; 32]),
        )
    }

    fn empty_book() -> HistoricalCostBook {
        let money = MonetaryBook::open(vec![crate::CashAccount {
            id: key(0).0,
            cash: zero(),
        }])
        .unwrap();
        HistoricalCostBook::open(&money, vec![], vec![], vec![], vec![]).unwrap()
    }

    #[test]
    fn transient_carrying_keys_have_an_exact_separate_insertion_bound() {
        let mut book = empty_book();
        book.stocks = (0..MAX_WORKING_CARRYING_STOCKS - 1)
            .map(|i| (key(i), zero()))
            .collect();
        book.credit_stock(
            key(MAX_WORKING_CARRYING_STOCKS - 1),
            Currency::from_micro_units(7),
        )
        .unwrap();
        assert_eq!(book.stocks.len(), 393_216);
        book.credit_stock(
            key(MAX_WORKING_CARRYING_STOCKS - 1),
            Currency::from_micro_units(3),
        )
        .unwrap();
        assert_eq!(
            book.stocks[&key(MAX_WORKING_CARRYING_STOCKS - 1)],
            Currency::from_micro_units(10)
        );
        assert_eq!(
            book.credit_stock(key(MAX_WORKING_CARRYING_STOCKS), zero()),
            Err(MaterialCircuitError::RowLimit)
        );
        assert_eq!(book.stocks.len(), MAX_WORKING_CARRYING_STOCKS);
        assert!(!book.stocks.contains_key(&key(MAX_WORKING_CARRYING_STOCKS)));
        assert_eq!(
            HistoricalCostBook::from_snapshot(book.snapshot()),
            Err(MaterialCircuitError::RowLimit)
        );
    }

    #[test]
    fn durable_carrying_snapshot_still_refuses_the_first_excess_key() {
        let mut book = empty_book();
        book.stocks = (0..MAX_CARRYING_STOCKS).map(|i| (key(i), zero())).collect();
        assert_eq!(
            HistoricalCostBook::from_snapshot(book.snapshot()).unwrap(),
            book
        );
        book.credit_stock(key(MAX_CARRYING_STOCKS), zero()).unwrap();
        assert_eq!(
            HistoricalCostBook::from_snapshot(book.snapshot()),
            Err(MaterialCircuitError::RowLimit)
        );
    }
}
