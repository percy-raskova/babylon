//! Ephemeral per-good evidence over existing carrying and actual-work postings.
use super::{add, zero, Result};
use crate::{
    GoodId, GoodsPriceCostBasis, GoodsPriceCostEvidence, MaterialCircuitError, SiteId, UnitId,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

type Key = (SiteId, GoodId, UnitId);
#[derive(Default)]
pub(super) struct GoodsCostLedger {
    produced: BTreeMap<Key, (u64, Currency)>,
    released: BTreeMap<Key, (u64, Currency)>,
    handling: BTreeMap<Key, (u64, Currency)>,
}
fn record(
    rows: &mut BTreeMap<Key, (u64, Currency)>,
    key: Key,
    quantity: u64,
    cost: Currency,
) -> Result<()> {
    if quantity == 0 {
        return if cost == zero() {
            Ok(())
        } else {
            Err(MaterialCircuitError::ValuationInvariant)
        };
    }
    let value = rows.entry(key).or_insert((0, zero()));
    value.0 = value
        .0
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    value.1 = add(value.1, cost)?;
    Ok(())
}
impl GoodsCostLedger {
    pub(super) fn produced(&mut self, key: Key, quantity: u64, cost: Currency) -> Result<()> {
        record(&mut self.produced, key, quantity, cost)
    }
    pub(super) fn released(&mut self, key: Key, quantity: u64, cost: Currency) -> Result<()> {
        record(&mut self.released, key, quantity, cost)
    }
    pub(super) fn handled(&mut self, key: Key, quantity: u64, cost: Currency) -> Result<()> {
        record(&mut self.handling, key, quantity, cost)
    }
    pub(super) fn evidence(&self, key: Key) -> Result<GoodsPriceCostEvidence> {
        let (basis, quantity, carrying, wages) =
            if let Some(&(quantity, wages)) = self.handling.get(&key) {
                let &(released, carrying) = self
                    .released
                    .get(&key)
                    .ok_or(MaterialCircuitError::ValuationInvariant)?;
                if released != quantity {
                    return Err(MaterialCircuitError::ValuationInvariant);
                }
                (GoodsPriceCostBasis::Released, quantity, carrying, wages)
            } else if let Some(&(quantity, carrying)) = self.produced.get(&key) {
                (GoodsPriceCostBasis::Produced, quantity, carrying, zero())
            } else if let Some(&(quantity, carrying)) = self.released.get(&key) {
                (GoodsPriceCostBasis::Released, quantity, carrying, zero())
            } else {
                return Ok(GoodsPriceCostEvidence::unavailable());
            };
        let evidence = GoodsPriceCostEvidence {
            basis,
            quantity,
            carrying_cost: carrying,
            handling_wages: wages,
        };
        evidence.unit_cost()?;
        Ok(evidence)
    }
}

impl super::CostClose {
    pub(crate) fn goods_price_cost(&self, key: Key) -> Result<GoodsPriceCostEvidence> {
        self.goods.evidence(key)
    }
}
