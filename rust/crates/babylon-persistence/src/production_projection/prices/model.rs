//! Prices are per native unit; monetary fields are exact micro-currency.
use super::{PriceReceipt, Result};
use babylon_material_circuit::{GoodsPriceCostBasis, PriceDecision};
use serde::{Deserialize, Serialize};
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionGoodsPriceAccount {
    pub site_id: String,
    pub good_id: String,
    pub unit_id: String,
    pub good: String,
    pub unit: String,
    pub current_price_micro: i128,
    pub completed: Option<CompletedGoodsPrice>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum GoodsPriceBasis {
    Unavailable,
    Produced,
    Released,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum GoodsPriceReason {
    Fixed,
    Hold,
    UnservedDemand,
    ExcessStock,
    CostPressure,
}
/// Quantity and quote principals join the physical receipts. The per-good carrying
/// is a committed engine posting witness, not an independent reader valuation.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CompletedGoodsPrice {
    pub period: u64,
    pub old_price_micro: i128,
    pub next_price_micro: i128,
    pub unserved_quantity: u64,
    pub closing_stock: u64,
    pub reason: GoodsPriceReason,
    pub cost_basis: GoodsPriceBasis,
    pub basis_quantity: u64,
    pub carrying_cost_micro: i128,
    pub handling_wages_micro: i128,
    pub unit_cost_micro: Option<i128>,
}
pub(super) fn completed(row: &PriceReceipt) -> Result<CompletedGoodsPrice> {
    Ok(CompletedGoodsPrice {
        period: row.period,
        old_price_micro: row.old_price.micro_units(),
        next_price_micro: row.next_price.micro_units(),
        unserved_quantity: row.unserved_quantity,
        closing_stock: row.closing_stock,
        reason: match row.reason {
            PriceDecision::Fixed => GoodsPriceReason::Fixed,
            PriceDecision::Hold => GoodsPriceReason::Hold,
            PriceDecision::UnservedDemand => GoodsPriceReason::UnservedDemand,
            PriceDecision::ExcessStock => GoodsPriceReason::ExcessStock,
            PriceDecision::CostPressure => GoodsPriceReason::CostPressure,
        },
        cost_basis: match row.cost.basis {
            GoodsPriceCostBasis::Unavailable => GoodsPriceBasis::Unavailable,
            GoodsPriceCostBasis::Produced => GoodsPriceBasis::Produced,
            GoodsPriceCostBasis::Released => GoodsPriceBasis::Released,
        },
        basis_quantity: row.cost.quantity,
        carrying_cost_micro: row.cost.carrying_cost.micro_units(),
        handling_wages_micro: row.cost.handling_wages.micro_units(),
        unit_cost_micro: row
            .cost
            .unit_cost()
            .map_err(|_| super::ProductionProjectionError::State)?
            .map(babylon_kernel::currency::Currency::micro_units),
    })
}

impl CompletedGoodsPrice {
    pub(crate) fn valid(&self, period: u64, current: i128) -> bool {
        let evidence = babylon_material_circuit::GoodsPriceCostEvidence {
            basis: match self.cost_basis {
                GoodsPriceBasis::Unavailable => GoodsPriceCostBasis::Unavailable,
                GoodsPriceBasis::Produced => GoodsPriceCostBasis::Produced,
                GoodsPriceBasis::Released => GoodsPriceCostBasis::Released,
            },
            quantity: self.basis_quantity,
            carrying_cost: babylon_kernel::currency::Currency::from_micro_units(
                self.carrying_cost_micro,
            ),
            handling_wages: babylon_kernel::currency::Currency::from_micro_units(
                self.handling_wages_micro,
            ),
        };
        self.period == period
            && self.old_price_micro > 0
            && self.next_price_micro == current
            && evidence.unit_cost().is_ok_and(|cost| {
                cost.map(babylon_kernel::currency::Currency::micro_units) == self.unit_cost_micro
            })
    }
}
