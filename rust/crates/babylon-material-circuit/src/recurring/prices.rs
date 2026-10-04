//! Current-period direct costs inform bounded quotes without valuing old stock anew.
use std::collections::BTreeMap;

use crate::valuation::CostClose;
use crate::{
    CircuitAccounting, GoodId, HouseholdDemandReceipt, MaterialCircuitError, MaterialCircuitState,
    PricePolicy, SiteId, UnitId,
};
use babylon_kernel::currency::Currency;

type Result<T> = std::result::Result<T, MaterialCircuitError>;
type StockKey = (SiteId, GoodId, UnitId);

/// Mutually exclusive actual native-quantity basis for one quote decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GoodsPriceCostBasis {
    Unavailable,
    Produced,
    /// Historical carrying withdrawn from seller stock, including unsold transit.
    Released,
}

/// A committed direct-cost claim from the same stock and actual-work postings.
/// Production includes inputs, wear and productive wages. A merchant instead uses
/// released carrying and the wages used to handle those same units. Idle work and
/// general maintenance are not allocated speculatively to particular commodities.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GoodsPriceCostEvidence {
    pub basis: GoodsPriceCostBasis,
    pub quantity: u64,
    pub carrying_cost: Currency,
    pub handling_wages: Currency,
}

impl GoodsPriceCostEvidence {
    #[must_use]
    pub fn unavailable() -> Self {
        Self {
            basis: GoodsPriceCostBasis::Unavailable,
            quantity: 0,
            carrying_cost: Currency::from_micro_units(0),
            handling_wages: Currency::from_micro_units(0),
        }
    }

    /// Exact rounded-up micro-currency per native unit, or no current observation.
    /// This validates the standalone claim, not its posting provenance.
    /// # Errors
    /// Refuses negative amounts, invalid basis/quantity partitions and overflow.
    pub fn unit_cost(&self) -> Result<Option<Currency>> {
        let cost = self.carrying_cost.micro_units();
        let handling = self.handling_wages.micro_units();
        if cost < 0 || handling < 0 {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        if self.basis == GoodsPriceCostBasis::Unavailable {
            return if self.quantity == 0 && cost == 0 && handling == 0 {
                Ok(None)
            } else {
                Err(MaterialCircuitError::ValuationInvariant)
            };
        }
        if self.quantity == 0 || (self.basis == GoodsPriceCostBasis::Produced && handling != 0) {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        let total = cost
            .checked_add(handling)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let quantity = i128::from(self.quantity);
        let whole = total / quantity;
        let rounded = whole
            .checked_add(i128::from(total % quantity != 0))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        Ok(Some(Currency::from_micro_units(rounded)))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PriceDecision {
    Fixed,
    Hold,
    UnservedDemand,
    ExcessStock,
    CostPressure,
}

/// Next-period quotes; accepted purchase reserves keep their admitted prices.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PriceReceipt {
    pub period: u64,
    pub site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub old_price: Currency,
    pub next_price: Currency,
    pub unserved_quantity: u64,
    pub closing_stock: u64,
    pub reason: PriceDecision,
    pub cost: GoodsPriceCostEvidence,
}

fn add(rows: &mut BTreeMap<StockKey, u64>, key: StockKey, quantity: u64) -> Result<()> {
    let value = rows.entry(key).or_default();
    *value = value
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

pub(crate) fn update_prices(
    state: &mut MaterialCircuitState,
    demand: &[HouseholdDemandReceipt],
    costs: &CostClose,
) -> Result<Vec<PriceReceipt>> {
    if !matches!(&state.accounting, CircuitAccounting::Monetary(e) if e.recurring.is_some()) {
        return Ok(Vec::new());
    }
    let mut unserved = BTreeMap::new();
    for row in demand {
        add(
            &mut unserved,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.expired_quantity,
        )?;
    }
    for order in &state.orders {
        add(
            &mut unserved,
            (order.supplier_site_id, order.good_id, order.unit_id),
            order.ordered - order.shipped,
        )?;
    }
    for row in &state.final_demand_orders {
        add(
            &mut unserved,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.ordered - row.fulfilled,
        )?;
    }
    let inventory: BTreeMap<_, _> = state
        .inventory
        .iter()
        .map(|row| ((row.site_id, row.good_id, row.unit_id), row.quantity))
        .collect();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(Vec::new());
    };
    let Some(recurring) = &mut economy.recurring else {
        return Ok(Vec::new());
    };
    let mut receipts = Vec::new();
    for offer in &mut recurring.offers {
        if state.commodities.iter().any(|r| {
            (r.good_id, r.unit_id) == (offer.good_id, offer.unit_id)
                && matches!(r.kind, crate::CommodityKind::PeriodService { .. })
        }) {
            continue;
        }
        let key = (offer.site_id, offer.good_id, offer.unit_id);
        let waiting = unserved.get(&key).copied().unwrap_or(0);
        let stock = inventory.get(&key).copied().unwrap_or(0);
        let old = offer.unit_price;
        let cost = costs.goods_price_cost(key)?;
        let cost_pressure = cost.unit_cost()?.is_some_and(|unit| unit > old);
        let reason = quote(offer, waiting, stock, cost_pressure)?;
        receipts.push(PriceReceipt {
            period: state.period,
            site_id: offer.site_id,
            good_id: offer.good_id,
            unit_id: offer.unit_id,
            old_price: old,
            next_price: offer.unit_price,
            unserved_quantity: waiting,
            closing_stock: stock,
            reason,
            cost,
        });
    }
    Ok(receipts)
}

fn quote(
    offer: &mut crate::SellerOffer,
    waiting: u64,
    stock: u64,
    cost_pressure: bool,
) -> Result<PriceDecision> {
    let old = offer.unit_price;
    Ok(match offer.pricing {
        PricePolicy::Fixed => PriceDecision::Fixed,
        PricePolicy::ServiceResponsive { .. } => {
            return Err(MaterialCircuitError::ServiceInvariant)
        }
        PricePolicy::Responsive {
            minimum,
            maximum,
            step,
            target_stock,
        } => {
            if (waiting > 0 && stock <= target_stock) || cost_pressure {
                // Saturation is explicit at the declared quote ceiling.
                offer.unit_price = Currency::from_micro_units(
                    old.micro_units()
                        .saturating_add(step.micro_units())
                        .min(maximum.micro_units()),
                );
                if waiting > 0 && stock <= target_stock {
                    PriceDecision::UnservedDemand
                } else {
                    PriceDecision::CostPressure
                }
            } else if waiting == 0 && stock > target_stock {
                offer.unit_price = Currency::from_micro_units(
                    old.micro_units()
                        .saturating_sub(step.micro_units())
                        .max(minimum.micro_units()),
                );
                PriceDecision::ExcessStock
            } else {
                PriceDecision::Hold
            }
        }
    })
}
