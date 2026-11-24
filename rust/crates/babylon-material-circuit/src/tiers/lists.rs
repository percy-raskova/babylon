//! What every household has still to buy this period, and what it bought of its wants.
//!
//! A household's list holds its needs (tier 1) and its wants (tiers 2 and 3). The list gives each
//! rung of a bid its reserve: the posted cost of what is ahead of it in the list and still to buy.

use super::records::{self, HouseholdTierReceipt, HouseholdWantReceipt};
use crate::clearing::BidRung;
use crate::recurring::households;
use crate::recurring::households::Intent;
use crate::services::Request;
use crate::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, GoodId, HouseholdCohort, HouseholdNeed,
    HouseholdPurchasePolicy, HouseholdWant, MarketClearingPolicy, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, MonetaryCircuit, OrderId, RecurringEconomy, SiteId,
    TaxBasis, UnitId, WageAccrualReceipt, WantTier,
};
use babylon_kernel::currency::Currency;
use std::collections::{BTreeMap, BTreeSet};

type Product = (FinalDemandPrincipalId, GoodId, UnitId);

/// One need or want of one account.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ListItem {
    pub principal: FinalDemandPrincipalId,
    /// 1 for a need, 2 for a comfort, 3 for a luxury.
    pub tier: u8,
    /// The product's place in the order of paying; `usize::MAX` for a need outside it.
    pub place: usize,
    pub good: GoodId,
    pub unit: UnitId,
    pub seller: SiteId,
    pub order_id: OrderId,
    pub posted: Currency,
    pub wanted: u64,
    pub bought: u64,
    pub still: u64,
    /// The market's price once the item's market has cleared.
    pub cleared: Option<Currency>,
}

impl ListItem {
    /// An item no market has cleared yet: everything wanted is still to buy.
    #[must_use]
    #[allow(
        clippy::too_many_arguments,
        reason = "one flat row of the list; the fields are its columns"
    )]
    pub(crate) fn new(
        product: Product,
        tier: u8,
        place: usize,
        seller: SiteId,
        order_id: OrderId,
        posted: Currency,
        wanted: u64,
    ) -> Self {
        Self {
            principal: product.0,
            tier,
            place,
            good: product.1,
            unit: product.2,
            seller,
            order_id,
            posted,
            wanted,
            bought: 0,
            still: wanted,
            cleared: None,
        }
    }

    fn product(&self) -> Product {
        (self.principal, self.good, self.unit)
    }

    fn cost_still(&self) -> Result<i128, MaterialCircuitError> {
        records::value(self.still, self.posted)
    }
}

/// One rung of a bid with the order it would be bought under.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct ListRung {
    pub tier: u8,
    pub order_id: OrderId,
    pub rung: BidRung,
}

/// What every household has still to buy this period, and what it bought of its wants.
#[derive(Debug, Clone, Default)]
pub(crate) struct HouseholdLists {
    /// Sorted by account, tier, good and unit.
    items: Vec<ListItem>,
    /// Every account of the period, in order.
    principals: Vec<FinalDemandPrincipalId>,
    /// The order a need rung would carry for a product the account wants and does not need.
    bare_needs: BTreeMap<Product, OrderId>,
    /// The order id of every want, so a household moment asks once per order, not once per item.
    want_orders: BTreeSet<OrderId>,
    /// The wage tax each account owes for the period as the lists opened: held back from every want.
    tax_ahead: BTreeMap<FinalDemandPrincipalId, Currency>,
}

impl HouseholdLists {
    /// The list of the period: empty unless the catalog has a market policy with wants.
    ///
    /// `wage_accruals` are the wages the period has booked so far: those paid at its opening, before
    /// any buying (rule R6). They give each account's wage tax, which is ahead of its wants.
    ///
    /// # Errors
    /// The refusals of the household intents and of the service requests; `PurchaseInvariant` for a
    /// bought product with no offer; `FinalDemandInvariant` for a want with no purchase row or cohort;
    /// `Arithmetic`, or `FinancialInvariant` for a tax row the close would refuse too.
    pub(crate) fn open(
        catalog: &MaterialCatalog,
        state: &MaterialCircuitState,
        wage_accruals: &[WageAccrualReceipt],
    ) -> Result<Self, MaterialCircuitError> {
        let Some(policy) = catalog
            .market_clearing
            .as_ref()
            .filter(|policy| !policy.household_wants.is_empty())
        else {
            return Ok(Self::default());
        };
        let CircuitAccounting::Monetary(economy) = &state.accounting else {
            return Ok(Self::default());
        };
        let Some(rows) = &economy.recurring else {
            return Ok(Self::default());
        };
        // The period's own validation first, so a malformed state gets its own refusal, not one of the
        // intents or the requests.
        crate::recurring::validate(catalog, state)?;
        let opening = Opening::new(
            catalog,
            state,
            policy,
            rows,
            households::household_intents(catalog, state, rows)?,
            crate::services::requests(catalog, state)?,
        );
        let mut lists = Self {
            principals: rows.households.iter().map(|r| r.principal_id).collect(),
            tax_ahead: wage_tax_ahead(economy, state.period, wage_accruals)?,
            ..Self::default()
        };
        let mut needed: BTreeSet<Product> = BTreeSet::new();
        for need in &catalog.household_needs {
            let item = opening.need_item(need)?;
            needed.insert(item.product());
            lists.items.push(item);
        }
        for want in &policy.household_wants {
            let key = (want.principal_id, want.good_id, want.unit_id);
            let (item, bare) = opening.want_item(want)?;
            if !needed.contains(&key) {
                lists.bare_needs.insert(key, bare);
            }
            lists.items.push(item);
        }
        lists
            .items
            .sort_by_key(|i| (i.principal, i.tier, i.good, i.unit));
        lists.want_orders = lists
            .items
            .iter()
            .filter(|i| i.tier > 1)
            .map(|i| i.order_id)
            .collect();
        Ok(lists)
    }

    /// Tests only: a list from hand-built items, without a catalog or a state.
    #[cfg(test)]
    pub(crate) fn from_items(mut items: Vec<ListItem>) -> Self {
        items.sort_by_key(|i| (i.principal, i.tier, i.good, i.unit));
        let mut principals: Vec<_> = items.iter().map(|i| i.principal).collect();
        principals.dedup();
        let want_orders = items
            .iter()
            .filter(|i| i.tier > 1)
            .map(|i| i.order_id)
            .collect();
        Self {
            items,
            principals,
            bare_needs: BTreeMap::new(),
            want_orders,
            tax_ahead: BTreeMap::new(),
        }
    }

    /// Tests only: the wage tax an account owes for the period.
    #[cfg(test)]
    pub(crate) fn with_tax_ahead(
        mut self,
        principal: FinalDemandPrincipalId,
        amount: Currency,
    ) -> Self {
        self.tax_ahead.insert(principal, amount);
        self
    }

    /// The wage tax the account owes for the period as the lists opened: what the close will assess
    /// on the wages paid at the opening. 0 for an account with no wage tax row.
    #[must_use]
    pub(crate) fn tax_ahead(&self, principal: FinalDemandPrincipalId) -> Currency {
        self.tax_ahead
            .get(&principal)
            .copied()
            .unwrap_or_else(|| Currency::from_micro_units(0))
    }

    /// Tests only: seed the need rung of a product the account only wants.
    #[cfg(test)]
    pub(crate) fn with_bare_need(mut self, product: Product, order: OrderId) -> Self {
        self.bare_needs.insert(product, order);
        self
    }

    fn account(&self, principal: FinalDemandPrincipalId) -> &[ListItem] {
        let start = self.items.partition_point(|i| i.principal < principal);
        let end = self.items.partition_point(|i| i.principal <= principal);
        &self.items[start..end]
    }

    /// The posted cost of what is ahead of `want` in its account's list and still to buy: needs, and
    /// wants of an earlier tier or, inside its tier, of an earlier place, of every other product.
    fn reserve(account: &[ListItem], want: &ListItem) -> Result<Currency, MaterialCircuitError> {
        let mut total = 0_i128;
        for item in account {
            let ahead =
                item.tier < want.tier || (item.tier == want.tier && item.place < want.place);
            if ahead && item.product() != want.product() {
                total = total
                    .checked_add(item.cost_still()?)
                    .ok_or(MaterialCircuitError::Arithmetic)?;
            }
        }
        Ok(Currency::from_micro_units(total))
    }

    /// The rungs of one account in one market: its need (`need` units, reserve 0), then each want of
    /// the product, each with its reserve.
    ///
    /// # Errors
    /// `MarketClearingInvariant` for a product the account neither needs nor wants; `Arithmetic`.
    pub(crate) fn rungs(
        &self,
        principal: FinalDemandPrincipalId,
        good: GoodId,
        unit: UnitId,
        need: u64,
    ) -> Result<Vec<ListRung>, MaterialCircuitError> {
        let account = self.account(principal);
        let tax = self.tax_ahead(principal).micro_units();
        let key = (principal, good, unit);
        let need_order = account
            .iter()
            .find(|i| i.tier == 1 && i.product() == key)
            .map(|i| i.order_id)
            .or_else(|| self.bare_needs.get(&key).copied())
            .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
        let mut rungs = vec![ListRung {
            tier: 1,
            order_id: need_order,
            rung: BidRung {
                wanted: need,
                reserve: Currency::from_micro_units(0),
            },
        }];
        for want in account.iter().filter(|i| i.tier > 1 && i.product() == key) {
            rungs.push(ListRung {
                tier: want.tier,
                order_id: want.order_id,
                rung: BidRung {
                    wanted: want.wanted,
                    reserve: Currency::from_micro_units(
                        Self::reserve(account, want)?
                            .micro_units()
                            .checked_add(tax)
                            .ok_or(MaterialCircuitError::Arithmetic)?,
                    ),
                },
            });
        }
        Ok(rungs)
    }

    /// Record each rung's (order id, bought), the need's included, and settle the product's items.
    ///
    /// A need is still to buy by the part it did not get; a want is done whatever it got.
    ///
    /// # Errors
    /// `MarketClearingInvariant` for an order that is not an item of the product (the bare need rung
    /// of a product only wanted is one, but may buy only 0), more bought than wanted, a price below
    /// the posted one, or a product settled twice.
    pub(crate) fn settle(
        &mut self,
        principal: FinalDemandPrincipalId,
        good: GoodId,
        unit: UnitId,
        bought: &[(OrderId, u64)],
        price: Currency,
    ) -> Result<(), MaterialCircuitError> {
        let start = self.items.partition_point(|i| i.principal < principal);
        let end = self.items.partition_point(|i| i.principal <= principal);
        let key = (principal, good, unit);
        let bare = self.bare_needs.get(&key).copied();
        let account = &mut self.items[start..end];
        for (order, quantity) in bought {
            if Some(*order) == bare {
                // The need rung of a product the account only wants: it wants 0, so it buys 0.
                if *quantity != 0 {
                    return Err(MaterialCircuitError::MarketClearingInvariant);
                }
            } else if !account
                .iter()
                .any(|i| i.product() == key && i.order_id == *order)
            {
                return Err(MaterialCircuitError::MarketClearingInvariant);
            }
        }
        for item in account.iter_mut().filter(|i| i.product() == key) {
            let got = bought
                .iter()
                .filter(|(order, _)| *order == item.order_id)
                .try_fold(0_u64, |sum, (_, quantity)| sum.checked_add(*quantity))
                .ok_or(MaterialCircuitError::Arithmetic)?;
            if item.cleared.is_some() || got > item.wanted || price < item.posted {
                return Err(MaterialCircuitError::MarketClearingInvariant);
            }
            item.bought = got;
            item.still = if item.tier == 1 { item.wanted - got } else { 0 };
            item.cleared = Some(price);
        }
        Ok(())
    }

    /// Whether the period's lists hold nothing: a catalog without wants.
    pub(crate) fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    pub(crate) fn is_want_order(&self, order: OrderId) -> bool {
        self.want_orders.contains(&order)
    }

    /// One row per want and two per account, at posted prices; empty when no account wants anything.
    ///
    /// # Errors
    /// `MarketClearingInvariant` for a record that does not hold together; `Arithmetic`.
    pub(crate) fn receipts(
        &self,
        period: u64,
    ) -> Result<(Vec<HouseholdWantReceipt>, Vec<HouseholdTierReceipt>), MaterialCircuitError> {
        let mut wants = vec![];
        for item in self.items.iter().filter(|i| i.tier > 1) {
            wants.push(HouseholdWantReceipt {
                period,
                principal_id: item.principal,
                tier: tier_of(item.tier)?,
                seller_site_id: item.seller,
                good_id: item.good,
                unit_id: item.unit,
                order_id: item.order_id,
                wanted_quantity: item.wanted,
                bought_quantity: item.bought,
                posted_price: item.posted,
                unit_price: item.cleared.unwrap_or(item.posted),
            });
        }
        let mut tiers = vec![];
        if !self.items.is_empty() {
            let grouped = records::group_by_tier(&wants);
            for &principal in &self.principals {
                for tier in [WantTier::Comfort, WantTier::Luxury] {
                    let (wanted, bought) = records::tier_sums(grouped.get(&(principal, tier)))?;
                    tiers.push(HouseholdTierReceipt {
                        period,
                        principal_id: principal,
                        tier,
                        wanted_value: Currency::from_micro_units(wanted),
                        bought_value: Currency::from_micro_units(bought),
                    });
                }
            }
        }
        records::validate_records(&wants, &tiers)?;
        Ok((wants, tiers))
    }
}

/// The wage tax each account owes for the period: for every wage tax row of a household payer,
/// the same fraction of the wages booked that `collect_taxes` assesses at the close.
fn wage_tax_ahead(
    economy: &MonetaryCircuit,
    period: u64,
    accruals: &[WageAccrualReceipt],
) -> Result<BTreeMap<FinalDemandPrincipalId, Currency>, MaterialCircuitError> {
    // The period's wages of each payee, summed once: a scan of the accruals for every tax row is a
    // square when both families hold a row for every account.
    let mut booked: BTreeMap<AccountId, i128> = BTreeMap::new();
    for accrual in accruals.iter().filter(|a| a.period == period) {
        let sum = booked.entry(accrual.payee).or_insert(0_i128);
        *sum = sum
            .checked_add(accrual.amount.micro_units())
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    let mut owed = BTreeMap::new();
    for row in &economy.financial.taxes {
        let (AccountId::Household(principal), TaxBasis::WageIncome) = (row.payer, row.basis) else {
            continue;
        };
        let wages = booked.get(&row.payer).copied().unwrap_or(0);
        let due = crate::financial::fraction(
            Currency::from_micro_units(wages),
            u64::from(row.rate_bps),
            10_000,
        )?;
        let total = owed.entry(principal).or_insert(0_i128);
        *total = total
            .checked_add(due.micro_units())
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(owed
        .into_iter()
        .map(|(principal, micro)| (principal, Currency::from_micro_units(micro)))
        .collect())
}

/// What the list of a period is read from, with each family of rows indexed by the key a need or a
/// want looks it up by (the first row of a key, as a scan for it would find): the national world has
/// tens of thousands of accounts, and a scan for every one of them is a square.
struct Opening<'a> {
    catalog: &'a MaterialCatalog,
    state: &'a MaterialCircuitState,
    policy: &'a MarketClearingPolicy,
    intents: Vec<Intent>,
    requests: Vec<Request>,
    /// The posted price of each seller's product.
    offers: BTreeMap<(SiteId, GoodId, UnitId), Currency>,
    /// The purchase row of each account's product.
    purchases: BTreeMap<Product, &'a HouseholdPurchasePolicy>,
    /// The cohort of each account.
    cohorts: BTreeMap<FinalDemandPrincipalId, &'a HouseholdCohort>,
    /// The place in `intents` of each account's product.
    intent_places: BTreeMap<Product, usize>,
    /// The place in `requests` of each household's request of a service as a need (one without a
    /// tier).
    need_requests: BTreeMap<Product, usize>,
}

/// The first value of each key, in the order given.
fn first_by_key<K: Ord, V>(rows: impl Iterator<Item = (K, V)>) -> BTreeMap<K, V> {
    let mut map = BTreeMap::new();
    for (key, value) in rows {
        map.entry(key).or_insert(value);
    }
    map
}

impl<'a> Opening<'a> {
    fn new(
        catalog: &'a MaterialCatalog,
        state: &'a MaterialCircuitState,
        policy: &'a MarketClearingPolicy,
        rows: &'a RecurringEconomy,
        intents: Vec<Intent>,
        requests: Vec<Request>,
    ) -> Self {
        Self {
            offers: first_by_key(
                rows.offers
                    .iter()
                    .map(|r| ((r.site_id, r.good_id, r.unit_id), r.unit_price)),
            ),
            purchases: first_by_key(
                rows.household_purchases
                    .iter()
                    .map(|p| ((p.principal_id, p.good_id, p.unit_id), p)),
            ),
            cohorts: first_by_key(rows.households.iter().map(|c| (c.principal_id, c))),
            intent_places: first_by_key(
                intents
                    .iter()
                    .enumerate()
                    .map(|(at, i)| ((i.principal_id, i.good_id, i.unit_id), at)),
            ),
            need_requests: first_by_key(requests.iter().enumerate().filter_map(|(at, r)| {
                match (r.tier, r.buyer) {
                    (None, AccountId::Household(principal)) => {
                        Some(((principal, r.good, r.unit), at))
                    }
                    _ => None,
                }
            })),
            catalog,
            state,
            policy,
            intents,
            requests,
        }
    }

    fn posted(
        &self,
        seller: SiteId,
        good: GoodId,
        unit: UnitId,
    ) -> Result<Currency, MaterialCircuitError> {
        self.offers
            .get(&(seller, good, unit))
            .copied()
            .ok_or(MaterialCircuitError::PurchaseInvariant)
    }

    /// A need: its seller, order and quantity are today's, from the intent or the service request.
    fn need_item(&self, need: &HouseholdNeed) -> Result<ListItem, MaterialCircuitError> {
        let key = (need.principal_id, need.good_id, need.unit_id);
        let (seller, order_id, wanted) = if crate::services::is_service(self.catalog, key.1, key.2)
        {
            // The requests also hold the want requests of the same key: a need's is the one without
            // a tier, whatever the order of the requests.
            let request = self
                .need_requests
                .get(&key)
                .map(|&at| &self.requests[at])
                .ok_or(MaterialCircuitError::ServiceInvariant)?;
            (request.provider, request.order_id, request.requested)
        } else {
            let intent = self
                .intent_places
                .get(&key)
                .map(|&at| &self.intents[at])
                .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
            (
                intent.retailer_site_id,
                intent.order_id,
                intent.requested_quantity,
            )
        };
        let place = self.policy.place(key.1, key.2).unwrap_or(usize::MAX);
        let posted = self.posted(seller, key.1, key.2)?;
        Ok(ListItem::new(
            key, 1, place, seller, order_id, posted, wanted,
        ))
    }

    /// A want, and the order its product's need rung would carry were the product not needed.
    fn want_item(&self, want: &HouseholdWant) -> Result<(ListItem, OrderId), MaterialCircuitError> {
        let period = self.state.period;
        let key = (want.principal_id, want.good_id, want.unit_id);
        let purchase = self
            .purchases
            .get(&key)
            .copied()
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let cohort = self
            .cohorts
            .get(&key.0)
            .copied()
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let wanted = if purchase.enabled {
            want.quantity(cohort)?
        } else {
            0
        };
        let seller = purchase.retailer_site_id;
        let (order_id, need_order) = if crate::services::is_service(self.catalog, key.1, key.2) {
            let buyer = AccountId::Household(key.0);
            (
                records::recurring_service_want_order_id(
                    period, key.0, seller, key.1, key.2, want.tier,
                ),
                crate::recurring_service_order_id(period, buyer, seller, key.1, key.2),
            )
        } else {
            (
                records::recurring_household_want_order_id(period, key, want.tier),
                households::recurring_household_order_id(period, key),
            )
        };
        let place = self.policy.place(key.1, key.2).unwrap_or(usize::MAX);
        let posted = self.posted(seller, key.1, key.2)?;
        let item = ListItem::new(
            key,
            want.tier as u8,
            place,
            seller,
            order_id,
            posted,
            wanted,
        );
        Ok((item, need_order))
    }
}

fn tier_of(tier: u8) -> Result<WantTier, MaterialCircuitError> {
    match tier {
        2 => Ok(WantTier::Comfort),
        3 => Ok(WantTier::Luxury),
        _ => Err(MaterialCircuitError::MarketClearingInvariant),
    }
}

#[cfg(test)]
mod opening_tests {
    use super::*;
    use crate::clearing::limit_fixture;
    use crate::{
        CapacitySupply, CommodityDefinition, CommodityKind, HouseholdNeedBasis, ServiceStage,
    };

    fn principal() -> FinalDemandPrincipalId {
        FinalDemandPrincipalId::from_bytes([9; 32])
    }

    fn order(n: u8) -> OrderId {
        OrderId::from_bytes([n; 32])
    }

    fn request(order_n: u8, tier: Option<WantTier>, requested: u64) -> Request {
        Request {
            order_id: order(order_n),
            buyer: AccountId::Household(principal()),
            provider: limit_fixture::site(7),
            good: limit_fixture::good(1),
            unit: limit_fixture::units(),
            requested,
            floor: Currency::from_micro_units(0),
            tier,
        }
    }

    /// A service need whose requests hold the want's request ahead of the need's own.
    #[test]
    fn a_service_need_takes_its_own_request_not_a_wants() {
        let need = HouseholdNeed {
            principal_id: principal(),
            good_id: limit_fixture::good(1),
            unit_id: limit_fixture::units(),
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        };
        let policy = MarketClearingPolicy {
            plans_from_spare_money: false,
            adjustments: Vec::new(),
            paying_order: vec![(limit_fixture::good(1), limit_fixture::units())],
            household_wants: vec![],
        };
        let catalog = MaterialCatalog::try_new(crate::MaterialCatalogDefinition {
            company_portfolios: None,
            company_payouts: vec![],
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![],
            process_outputs: vec![],
            input_coefficients: vec![],
            labor_coefficients: vec![],
            commodities: vec![CommodityDefinition {
                good_id: limit_fixture::good(1),
                unit_id: limit_fixture::units(),
                kind: CommodityKind::PeriodService {
                    stage: ServiceStage::UtilityProvision,
                },
            }],
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![],
            handling_coefficients: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs: vec![need.clone()],
            market_clearing: Some(policy.clone()),
        })
        .expect("the fixture catalog is valid");
        let (_, recurring) = limit_fixture::world();
        let state = limit_fixture::state_of(recurring);
        let rows = state
            .recurring_economy()
            .expect("the fixture state is monetary");
        let opening = Opening::new(
            &catalog,
            &state,
            &policy,
            rows,
            vec![],
            vec![
                request(20, Some(WantTier::Comfort), 5),
                request(10, None, 3),
            ],
        );
        let item = opening.need_item(&need).expect("the need has its request");
        assert_eq!((item.order_id, item.wanted), (order(10), 3));
    }
}
