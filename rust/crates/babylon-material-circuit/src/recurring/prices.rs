//! Current-period direct costs inform bounded quotes without valuing old stock anew.
use std::collections::BTreeMap;

use super::firms::{StockKey, Wanted};
use crate::adjustment::{self, AdjustmentRule, GoodsOfferReceipt, RestingPriceReceipt};
use crate::valuation::CostClose;
use crate::MaterialCatalog;
use crate::SellerOffer;
use crate::{
    CircuitAccounting, GoodId, MaterialCircuitError, MaterialCircuitState, PricePolicy, SiteId,
    UnitId,
};
use babylon_kernel::currency::Currency;
use std::result::Result as StdResult;

type Result<T> = StdResult<T, MaterialCircuitError>;

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

/// What one close's quotes decided: every price receipt, the prices that rested, and, when the catalog asks
/// for the step down, what each goods seller offered and sold.
#[derive(Default)]
pub(crate) struct Quoted {
    pub(crate) prices: Vec<PriceReceipt>,
    pub(crate) rests: Vec<RestingPriceReceipt>,
    pub(crate) offers: Vec<GoodsOfferReceipt>,
}

impl Quoted {
    /// What a seller that stepped its price down plans for: what its buyers could pay for at the new price
    /// beyond the posted one, by product.
    pub(crate) fn gains(&self) -> BTreeMap<StockKey, u64> {
        self.offers
            .iter()
            .filter(|row| row.planned_gain > 0)
            .map(|row| ((row.site_id, row.good_id, row.unit_id), row.planned_gain))
            .collect()
    }
}

/// Whether the catalog asks for the goods step down: goods are then quoted before the plans, and a goods price
/// steps down when goods beyond the buffer went unsold.
pub(crate) fn asks_step_down(catalog: &MaterialCatalog) -> bool {
    catalog
        .market_clearing
        .as_ref()
        .is_some_and(|policy| adjustment::asks(&policy.adjustments, AdjustmentRule::GoodsStepDown))
}

/// What each seller's production policy keeps as a buffer, by product.
fn buffers(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> Result<BTreeMap<StockKey, u64>> {
    let mut kept = BTreeMap::new();
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(kept);
    };
    let Some(recurring) = &economy.recurring else {
        return Ok(kept);
    };
    for policy in &recurring.production {
        let output = catalog
            .process_outputs
            .binary_search_by_key(&policy.process_id, |row| row.process_id)
            .ok()
            .map(|index| &catalog.process_outputs[index])
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        add(
            &mut kept,
            (policy.site_id, output.good_id, output.unit_id),
            policy.output_buffer,
        )?;
    }
    Ok(kept)
}

/// What each seller's buyers wanted of its product and did not get: demand that expired, orders not shipped,
/// final-demand orders not filled, and what bids could pay for in a short market and did not get.
fn unserved_by_product(
    state: &MaterialCircuitState,
    wanted: Wanted<'_>,
) -> Result<BTreeMap<StockKey, u64>> {
    let mut unserved = BTreeMap::new();
    for row in wanted.demand {
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
    // The market's price answers a shortage once; the posted price steps up with it, as it does for
    // demand that went unserved.
    for (key, quantity) in wanted.markets.priced_out_goods() {
        add(&mut unserved, key, quantity)?;
    }
    Ok(unserved)
}

pub(crate) fn update_prices(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    wanted: Wanted<'_>,
    costs: &CostClose,
) -> Result<Quoted> {
    if !matches!(&state.accounting, CircuitAccounting::Monetary(e) if e.recurring.is_some()) {
        return Ok(Quoted::default());
    }
    let unserved = unserved_by_product(state, wanted)?;
    let inventory: BTreeMap<_, _> = state
        .inventory
        .iter()
        .map(|row| ((row.site_id, row.good_id, row.unit_id), row.quantity))
        .collect();
    let stepping = asks_step_down(catalog);
    let kept = if stepping {
        buffers(catalog, state)?
    } else {
        BTreeMap::new()
    };
    // The sellers that rest at this close, read before the offers are borrowed for their quotes.
    let resting = adjustment::resting_among(
        catalog,
        state,
        state_offers(state).map(|key| (key, wanted.markets.offered(key.0, key.1, key.2))),
    );
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(Quoted::default());
    };
    let Some(recurring) = &mut economy.recurring else {
        return Ok(Quoted::default());
    };
    let mut quoted = Quoted::default();
    for offer in &mut recurring.offers {
        if catalog.commodities.iter().any(|r| {
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
        let unsold = stepping
            && wanted
                .markets
                .goods_unsold(key, kept.get(&key).copied().unwrap_or(0))?;
        let reason = if resting.contains(&key) {
            quoted.rests.push(RestingPriceReceipt {
                period: state.period,
                site_id: offer.site_id,
                good_id: offer.good_id,
                unit_id: offer.unit_id,
                price: old,
            });
            PriceDecision::Hold
        } else {
            quote(offer, waiting, stock, cost_pressure, unsold)?
        };
        if stepping {
            if let Some((offered, sold)) = wanted.markets.goods_offered_sold(key) {
                let planned_gain = if offer.unit_price < old {
                    wanted.markets.goods_gain_at(key, offer.unit_price)?
                } else {
                    0
                };
                quoted.offers.push(GoodsOfferReceipt {
                    period: state.period,
                    site_id: offer.site_id,
                    good_id: offer.good_id,
                    unit_id: offer.unit_id,
                    offered,
                    sold,
                    kept: kept.get(&key).copied().unwrap_or(0),
                    planned_gain,
                });
            }
        }
        quoted.prices.push(PriceReceipt {
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
    Ok(quoted)
}

/// The products the state's sellers offer, in the order of the offers.
fn state_offers(state: &MaterialCircuitState) -> impl Iterator<Item = StockKey> + '_ {
    let offers = match &state.accounting {
        CircuitAccounting::Monetary(economy) => economy
            .recurring
            .as_ref()
            .map_or(&[][..], |recurring| &recurring.offers[..]),
        CircuitAccounting::PhysicalControl => &[],
    };
    offers
        .iter()
        .map(|offer| (offer.site_id, offer.good_id, offer.unit_id))
}

fn quote(
    offer: &mut SellerOffer,
    waiting: u64,
    stock: u64,
    cost_pressure: bool,
    unsold: bool,
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
            } else if waiting == 0 && (stock > target_stock || unsold) {
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

#[cfg(test)]
mod tests {
    use super::{quote, PriceDecision};
    use crate::clearing::{MarketMoment, MarketOutcome, MarketTable};
    use crate::MaterialCircuitError;
    use crate::{GoodId, PricePolicy, SellerOffer, SiteId, UnitId};
    use babylon_kernel::currency::Currency;

    fn dollars(micro: i128) -> Currency {
        Currency::from_micro_units(micro * 1_000_000)
    }

    fn offer(price: Currency, minimum: Currency, step: Currency) -> SellerOffer {
        SellerOffer {
            site_id: SiteId::from_bytes([1; 32]),
            good_id: GoodId::from_bytes([2; 32]),
            unit_id: UnitId::from_bytes([3; 32]),
            unit_price: price,
            pricing: PricePolicy::Responsive {
                minimum,
                maximum: dollars(1000),
                step,
                target_stock: 0,
            },
        }
    }

    fn product() -> (SiteId, GoodId, UnitId) {
        (
            SiteId::from_bytes([1; 32]),
            GoodId::from_bytes([2; 32]),
            UnitId::from_bytes([3; 32]),
        )
    }

    /// A market of the product that offered `supply` and sold `sold`.
    fn market(supply: u64, sold: u64) -> MarketTable {
        let mut table = MarketTable::default();
        let outcome = MarketOutcome {
            price: dollars(38),
            quantities: vec![sold],
            demand_at_quote: sold,
        };
        table
            .record(
                1,
                MarketMoment::HouseholdGoods,
                product(),
                dollars(38),
                supply,
                1,
                &outcome,
                Vec::new(),
            )
            .expect("a market is recorded");
        table
    }

    #[test]
    fn a_step_down_goes_under_cost() {
        // The unit cost is $38, the price is $38 and goods went unsold: the price steps down to $37.
        let mut seller = offer(dollars(38), dollars(1), dollars(1));
        let reason = quote(&mut seller, 0, 0, false, true).expect("a quote");
        assert_eq!(reason, PriceDecision::ExcessStock);
        assert_eq!(seller.unit_price, dollars(37));
    }

    #[test]
    fn a_period_service_takes_no_step_down() {
        // A service's price has its own pricing: the goods quote refuses it, so unsold goods never move it.
        let mut seller = offer(dollars(38), dollars(1), dollars(1));
        seller.pricing = PricePolicy::ServiceResponsive {
            minimum: dollars(1),
            maximum: dollars(1000),
            step: dollars(1),
        };
        assert_eq!(
            quote(&mut seller, 0, 0, false, true),
            Err(MaterialCircuitError::ServiceInvariant)
        );
        assert_eq!(seller.unit_price, dollars(38));
    }

    #[test]
    fn a_step_down_stops_at_the_minimum() {
        let mut seller = offer(
            Currency::from_micro_units(1_500_000),
            dollars(1),
            dollars(1),
        );
        quote(&mut seller, 0, 0, false, true).expect("a quote");
        assert_eq!(seller.unit_price, dollars(1));
        quote(&mut seller, 0, 0, false, true).expect("a quote");
        assert_eq!(
            seller.unit_price,
            dollars(1),
            "a price at the minimum holds"
        );
    }

    #[test]
    fn a_buffer_is_not_unsold() {
        let table = market(40, 0);
        assert!(!table.goods_unsold(product(), 40).expect("a sum"));
        assert!(table.goods_unsold(product(), 39).expect("a sum"));
        assert!(!market(40, 40).goods_unsold(product(), 0).expect("a sum"));
        assert_eq!(table.goods_offered_sold(product()), Some((40, 0)));
        assert_eq!(MarketTable::default().goods_offered_sold(product()), None);
    }

    #[test]
    fn a_buyer_who_could_pay_and_waited_bars_the_step() {
        let mut seller = offer(dollars(38), dollars(1), dollars(1));
        let reason = quote(&mut seller, 1, 0, false, true).expect("a quote");
        assert_eq!(reason, PriceDecision::UnservedDemand);
        assert_eq!(
            seller.unit_price,
            dollars(39),
            "the price steps up, not down"
        );
        let mut seller = offer(dollars(38), dollars(1), dollars(1));
        quote(&mut seller, 1, 5, false, true).expect("a quote");
        assert_eq!(
            seller.unit_price,
            dollars(38),
            "waiting with stock above target holds it"
        );
    }

    #[test]
    fn goods_not_unsold_keep_todays_price() {
        let mut seller = offer(dollars(38), dollars(1), dollars(1));
        let reason = quote(&mut seller, 0, 0, false, false).expect("a quote");
        assert_eq!(reason, PriceDecision::Hold);
        assert_eq!(seller.unit_price, dollars(38));
    }
}
