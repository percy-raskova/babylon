//! The highest price a business pays for an input (P5).
//!
//! A maker pays up to what one batch of its product earns at its own posted price, less its wages
//! and its other inputs. A merchant pays up to its own posted price less the wages of handling.
//! The limit is never under the input's posted price, and a buyer with no selling price of its own
//! never outbids.

use crate::valuation::CostClose;
use crate::{
    CircuitAccounting, GoodId, MaterialCatalog, MaterialCircuitError, MaterialCircuitState,
    ProcessOutput, RecurringEconomy, SiteId, UnitId,
};
use babylon_kernel::currency::Currency;

/// The wages and the hours a site has funded for one kind of labor.
type Funded<'a> = &'a dyn Fn(SiteId, UnitId) -> Result<(Currency, u64), MaterialCircuitError>;

/// The highest price this business pays for this input (P5). Never under the input's posted price.
///
/// # Errors
/// `Arithmetic` on overflow, `MerchantInvariant` for a merchant's product with no handling
/// coefficient.
pub(crate) fn limit_price(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    costs: &CostClose,
    buyer: SiteId,
    good: GoodId,
    unit: UnitId,
    quote: Currency,
) -> Result<Currency, MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(quote);
    };
    let Some(recurring) = &economy.recurring else {
        return Ok(quote);
    };
    limit_in(
        catalog,
        recurring,
        &|site, labor| costs.funded_wage(site, labor),
        (buyer, good, unit),
        quote,
    )
}

fn limit_in(
    catalog: &MaterialCatalog,
    recurring: &RecurringEconomy,
    funded: Funded<'_>,
    product: (SiteId, GoodId, UnitId),
    quote: Currency,
) -> Result<Currency, MaterialCircuitError> {
    let (buyer, good, unit) = product;
    let mut best: Option<i128> = None;
    for output in catalog
        .process_outputs
        .iter()
        .filter(|o| o.site_id == buyer)
    {
        let figure = maker_figure(catalog, recurring, funded, output, (good, unit))?;
        best = best.max(figure);
    }
    best = best.max(merchant_figure(catalog, recurring, funded, product)?);
    Ok(best.map_or(quote, |figure| {
        Currency::from_micro_units(figure.max(quote.micro_units()))
    }))
}

/// The posted price of a seller's product, if it has an offer.
fn posted(
    recurring: &RecurringEconomy,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
) -> Option<Currency> {
    recurring
        .offers
        .binary_search_by_key(&(site, good, unit), |o| (o.site_id, o.good_id, o.unit_id))
        .ok()
        .map(|index| recurring.offers[index].unit_price)
}

/// What `hours` of a site's labor cost at the average of its funded wages.
fn wage_of_hours(
    funded: Funded<'_>,
    site: SiteId,
    unit: UnitId,
    hours: u64,
) -> Result<i128, MaterialCircuitError> {
    let (wages, funded_hours) = funded(site, unit)?;
    if funded_hours == 0 {
        return Ok(0);
    }
    let total = wages
        .micro_units()
        .checked_mul(i128::from(hours))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(total.div_euclid(i128::from(funded_hours)))
}

/// The lowest posted price among the buyer's own suppliers and providers of a product, or 0.
fn cheapest_supplier(
    catalog: &MaterialCatalog,
    recurring: &RecurringEconomy,
    buyer: SiteId,
    good: GoodId,
    unit: UnitId,
) -> i128 {
    let suppliers = recurring
        .replenishment
        .iter()
        .filter(|p| (p.buyer_site_id, p.good_id, p.unit_id) == (buyer, good, unit))
        .map(|p| p.supplier_site_id);
    let providers = catalog
        .service_inputs
        .iter()
        .filter(|p| (p.buyer_site_id, p.good_id, p.unit_id) == (buyer, good, unit))
        .map(|p| p.provider_site_id);
    suppliers
        .chain(providers)
        .filter_map(|seller| posted(recurring, seller, good, unit))
        .map(Currency::micro_units)
        .min()
        .unwrap_or(0)
}

/// What one batch of this process leaves to pay for the input, per unit of the input.
fn maker_figure(
    catalog: &MaterialCatalog,
    recurring: &RecurringEconomy,
    funded: Funded<'_>,
    output: &ProcessOutput,
    input: (GoodId, UnitId),
) -> Result<Option<i128>, MaterialCircuitError> {
    let coefficients = || {
        catalog
            .input_coefficients
            .iter()
            .filter(|c| c.process_id == output.process_id)
    };
    let Some(taken) = coefficients().find(|c| (c.good_id, c.unit_id) == input) else {
        return Ok(None);
    };
    let Some(price) = posted(recurring, output.site_id, output.good_id, output.unit_id) else {
        return Ok(None);
    };
    let receipts = price
        .micro_units()
        .checked_mul(i128::from(output.quantity_per_batch))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let mut costs = 0_i128;
    for labor in catalog
        .labor_coefficients
        .iter()
        .filter(|l| l.process_id == output.process_id)
    {
        let wages = wage_of_hours(
            funded,
            output.site_id,
            labor.unit_id,
            labor.quantity_per_batch,
        )?;
        costs = costs
            .checked_add(wages)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    for other in coefficients().filter(|c| (c.good_id, c.unit_id) != input) {
        let each = cheapest_supplier(
            catalog,
            recurring,
            output.site_id,
            other.good_id,
            other.unit_id,
        );
        let spent = each
            .checked_mul(i128::from(other.quantity_per_batch))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        costs = costs
            .checked_add(spent)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    let left = receipts
        .checked_sub(costs)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let per_batch = i128::from(taken.quantity_per_batch);
    if per_batch == 0 {
        return Err(MaterialCircuitError::Arithmetic);
    }
    Ok(Some(left.div_euclid(per_batch)))
}

/// A site with a price of its own for the same product pays that price less its handling wages.
fn merchant_figure(
    catalog: &MaterialCatalog,
    recurring: &RecurringEconomy,
    funded: Funded<'_>,
    product: (SiteId, GoodId, UnitId),
) -> Result<Option<i128>, MaterialCircuitError> {
    let (site, good, unit) = product;
    let Some(price) = posted(recurring, site, good, unit) else {
        return Ok(None);
    };
    let mut handling = 0;
    if let Some(merchant) = catalog.merchants.iter().find(|m| m.site_id == site) {
        let hours =
            crate::transition::merchant_admission::hours_per_unit(catalog, site, good, unit)?;
        handling = wage_of_hours(funded, site, merchant.labor_unit_id, hours)?;
    }
    price
        .micro_units()
        .checked_sub(handling)
        .map(Some)
        .ok_or(MaterialCircuitError::Arithmetic)
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::{
        CapacitySupply, CommodityDefinition, CommodityKind, CorridorId, FinalDemandPrincipalId,
        InputOutputCoefficient, LaborCoefficient, LaborCompensation, LogisticsNodeId,
        MaterialCatalogDefinition, MemberLaborUseReceipt, MerchantHandling,
        MerchantHandlingCoefficient, MerchantRole, PricePolicy, ProcessId, ReplenishmentPolicy,
        SellerOffer, SiteLogisticsNode, StaffingMemberId,
    };

    pub(crate) fn site(id: u8) -> SiteId {
        SiteId::from_bytes([id; 32])
    }
    pub(crate) fn good(id: u8) -> GoodId {
        GoodId::from_bytes([id; 32])
    }
    pub(crate) fn units() -> UnitId {
        UnitId::from_bytes([1; 32])
    }
    pub(crate) fn hours() -> UnitId {
        UnitId::from_bytes([2; 32])
    }
    pub(crate) fn dollars(value: i128) -> Currency {
        Currency::from_micro_units(value * 1_000_000)
    }
    pub(crate) fn offer(owner: u8, item: u8, price: Currency) -> SellerOffer {
        SellerOffer {
            site_id: site(owner),
            good_id: good(item),
            unit_id: units(),
            unit_price: price,
            pricing: PricePolicy::Fixed,
        }
    }

    /// Site 7 makes good 9 (4 per batch) from 2 of good 1 and 1 of good 2, with 3 hours a batch;
    /// good 2 comes from sites 5 at $30 and 6 at $40. Site 7 also sells good 1 over a counter.
    pub(crate) fn world() -> (MaterialCatalog, RecurringEconomy) {
        let process = ProcessId::from_bytes([9; 32]);
        let definition = MaterialCatalogDefinition {
            company_portfolios: None,
            company_payouts: vec![],
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![SiteLogisticsNode {
                site_id: site(7),
                node_id: LogisticsNodeId::from_bytes([7; 32]),
            }],
            process_outputs: vec![crate::ProcessOutput {
                process_id: process,
                site_id: site(7),
                good_id: good(9),
                unit_id: units(),
                quantity_per_batch: 4,
            }],
            input_coefficients: vec![
                InputOutputCoefficient {
                    process_id: process,
                    good_id: good(1),
                    unit_id: units(),
                    quantity_per_batch: 2,
                },
                InputOutputCoefficient {
                    process_id: process,
                    good_id: good(2),
                    unit_id: units(),
                    quantity_per_batch: 1,
                },
            ],
            labor_coefficients: vec![LaborCoefficient {
                process_id: process,
                unit_id: hours(),
                quantity_per_batch: 3,
            }],
            commodities: [1, 2, 9]
                .into_iter()
                .map(|item| CommodityDefinition {
                    good_id: good(item),
                    unit_id: units(),
                    kind: CommodityKind::Storable { grams_per_unit: 1 },
                })
                .collect(),
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![MerchantHandling {
                site_id: site(7),
                location: "county:26163".parse().expect("the literal parses"),
                role: MerchantRole::Retail,
                capacity_id: CorridorId::from_bytes([7; 32]),
                labor_unit_id: hours(),
            }],
            handling_coefficients: vec![MerchantHandlingCoefficient {
                site_id: site(7),
                good_id: good(1),
                unit_id: units(),
                hours_per_unit: 2,
            }],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs: vec![],
            market_clearing: None,
        };
        let recurring = RecurringEconomy {
            households: vec![],
            household_stocks: vec![],
            household_purchases: vec![],
            offers: vec![
                offer(5, 2, dollars(30)),
                offer(6, 2, dollars(40)),
                offer(7, 1, dollars(60)),
                offer(7, 9, dollars(80)),
            ],
            replenishment: [5, 6]
                .into_iter()
                .map(|supplier| ReplenishmentPolicy {
                    buyer_site_id: site(7),
                    supplier_site_id: site(supplier),
                    good_id: good(2),
                    unit_id: units(),
                    target_stock: 1,
                    maximum_purchase: 1,
                    cash_floor: dollars(0),
                })
                .collect(),
            production: vec![],
            attendance: vec![],
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        };
        (
            MaterialCatalog::try_new(definition).expect("the fixture catalog is valid"),
            recurring,
        )
    }

    /// A monetary state holding the recurring rows and a cash account for site 7.
    pub(crate) fn state_of(recurring: RecurringEconomy) -> MaterialCircuitState {
        use crate::{
            AidBook, CapacityReservations, CashAccount, FinancialInstitutions, HistoricalCostBook,
            HouseholdTimeAccounting, MonetaryBook, MonetaryCircuit,
        };
        let book = MonetaryBook::open(vec![CashAccount {
            id: crate::AccountId::Site(site(7)),
            cash: dollars(1_000),
        }])
        .expect("the fixture book opens");
        let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
            .expect("the fixture costs open");
        MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                aid: AidBook::default(),
                household_time: HouseholdTimeAccounting::NotModeled,
                financial: FinancialInstitutions::empty(),
                member_labor: vec![],
                costs,
                book,
                recurring: Some(Box::new(recurring)),
                employment: vec![],
            })),
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: vec![],
            orders: vec![],
            freight: vec![],
            corridor_capacities: vec![],
            capacities: vec![],
            labor: vec![],
            production_commitments: vec![],
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        }
    }

    /// One member row of site 7's hours: attended hours at a compensation.
    pub(crate) fn member_row(
        member: u8,
        compensation: LaborCompensation,
        hours_worked: u64,
    ) -> MemberLaborUseReceipt {
        let wages = Currency::from_micro_units(
            compensation.wage_rate().micro_units() * i128::from(hours_worked),
        );
        let none = Currency::from_micro_units(0);
        MemberLaborUseReceipt {
            member_id: StaffingMemberId::from_bytes([member; 32]),
            site_id: site(7),
            unit_id: hours(),
            payee: FinalDemandPrincipalId::from_bytes([member; 32]),
            compensation,
            period: 1,
            available_hours: hours_worked,
            planned_hours: hours_worked,
            unplanned_hours: 0,
            attended_hours: hours_worked,
            unattended_hours: 0,
            production_hours: hours_worked,
            handling_hours: 0,
            maintenance_hours: 0,
            installation_hours: 0,
            idle_hours: 0,
            accrued_wages: wages,
            production_wages: wages,
            handling_wages: none,
            maintenance_wages: none,
            installation_wages: none,
            idle_wages: none,
        }
    }

    /// $200 funded over 20 hours: one wage earner and one working owner of 10 hours each.
    fn funded(site_id: SiteId, unit: UnitId) -> (Currency, u64) {
        if site_id == site(7) && unit == hours() {
            (dollars(200), 20)
        } else {
            (dollars(0), 0)
        }
    }

    #[test]
    fn a_makers_limit_is_what_a_batch_leaves_for_one_unit() {
        let (catalog, recurring) = world();
        // receipts 4 x $80 = $320; wages floor(3 x $200 / 20) = $30; the other input 1 x $30;
        // floor(($320 - $30 - $30) / 2) = $130. The handling figure of the same site is
        // $60 - 2 x $10 = $40, so the maker's figure stands.
        let limit = limit_in(
            &catalog,
            &recurring,
            &|s, u| Ok(funded(s, u)),
            (site(7), good(1), units()),
            dollars(50),
        )
        .expect("the limit reads");
        assert_eq!(limit, dollars(130));
    }

    #[test]
    fn a_limit_is_never_under_the_quote() {
        let (catalog, recurring) = world();
        let limit = limit_in(
            &catalog,
            &recurring,
            &|s, u| Ok(funded(s, u)),
            (site(7), good(1), units()),
            dollars(500),
        )
        .expect("the limit reads");
        assert_eq!(limit, dollars(500));
    }

    #[test]
    fn a_buyer_with_no_price_of_its_own_never_outbids() {
        let (catalog, recurring) = world();
        let limit = limit_in(
            &catalog,
            &recurring,
            &|s, u| Ok(funded(s, u)),
            (site(8), good(1), units()),
            dollars(50),
        )
        .expect("the limit reads");
        assert_eq!(limit, dollars(50));
    }

    #[test]
    fn a_merchants_limit_is_its_price_less_handling() {
        let (catalog, recurring) = world();
        let figure = merchant_figure(
            &catalog,
            &recurring,
            &|s, u| Ok(funded(s, u)),
            (site(7), good(1), units()),
        )
        .expect("the figure reads");
        assert_eq!(figure, Some(40_000_000));
    }

    #[test]
    fn unfunded_hours_cost_nothing() {
        let (catalog, recurring) = world();
        let unfunded = |_: SiteId, _: UnitId| Ok((dollars(0), 0));
        let limit = limit_in(
            &catalog,
            &recurring,
            &unfunded,
            (site(7), good(1), units()),
            dollars(50),
        )
        .expect("the limit reads");
        // receipts $320 less the other input $30, over 2 units.
        assert_eq!(limit, dollars(145));
    }

    #[test]
    fn the_limit_reads_the_sites_own_funded_wage() {
        let (catalog, recurring) = world();
        let state = state_of(recurring);
        // One wage earner at $20 and one working owner, 10 hours each: $200 funded over 20 hours.
        let costs = CostClose::with_members(
            &state,
            &catalog,
            vec![
                member_row(1, LaborCompensation::Wage(dollars(20)), 10),
                member_row(2, LaborCompensation::WorkingOwner, 10),
            ],
        );
        let limit = limit_price(
            &catalog,
            &state,
            &costs,
            site(7),
            good(1),
            units(),
            dollars(50),
        )
        .expect("the limit reads");
        // The maker's figure of the example above: floor(($320 - $30 - $30) / 2).
        assert_eq!(limit, dollars(130));
    }
}
