//! A small economy of service providers: a utility, a local service, a public service, any number of
//! household accounts and one business that takes the utility as an input.

use super::support;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, AidBook, AttendancePlan, CapacityReservations, CapacityRow, CapacitySupply,
    CashAccount, CircuitAccounting, CommodityDefinition, CommodityKind, EmploymentTerms,
    FinalDemandPrincipal, FinalDemandPrincipalId, FinancialInstitutions, GoodId,
    HistoricalCostBook, HouseholdCohort, HouseholdKind, HouseholdNeed, HouseholdNeedBasis,
    HouseholdPurchasePolicy, HouseholdTimeAccounting, HouseholdWant, InputOutputCoefficient,
    LaborCapacityRow, LaborCoefficient, LaborCompensation, LogisticsNodeId, MarketClearingPolicy,
    MaterialCatalog, MaterialCatalogDefinition, MaterialCircuitState, MemberLaborCapacityRow,
    MonetaryBook, MonetaryCircuit, OrderId, OutboundOrderId, PricePolicy, ProcessId, ProcessOutput,
    ProductionCommitment, ProductionDemandPolicy, PurchaseEscrow, RecurringEconomy, SellerOffer,
    ServiceConnection, ServiceInputPolicy, ServiceOrder, ServiceStage, SiteLogisticsNode,
    StaffingMemberId, WantTier,
};

/// The utility, a service of the first stage.
pub(crate) const UTILITY: u8 = 1;
/// The local service, a service of the second stage.
pub(crate) const LOCAL: u8 = 2;
/// A public provision, a service of the second stage that is left out of the order of paying.
pub(crate) const PUBLIC: u8 = 3;
/// The good the business makes with the utility.
const PRODUCT: u8 = 5;
/// The business that takes the utility as an input.
pub(crate) const BUSINESS: u8 = 4;
/// The provider of the public service.
const PUBLIC_PROVIDER: u8 = 6;
/// The payee of every wage.
const PAYEE: u8 = 99;

pub(crate) fn account(index: u8) -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([10 + index; 32])
}

/// The posted price of a service.
pub(crate) fn posted(service: u8) -> Currency {
    match service {
        UTILITY => support::dollars(4),
        _ => support::dollars(3),
    }
}

/// The provider of a service. Services are numbered after their providers' sites.
fn provider(service: u8) -> u8 {
    match service {
        PUBLIC => PUBLIC_PROVIDER,
        other => other,
    }
}

/// An order for a service already funded for the period, by one household account.
#[derive(Clone)]
pub(crate) struct Funded {
    pub buyer: u8,
    pub service: u8,
    pub quantity: u64,
    pub price: Currency,
    pub order: u8,
}

#[derive(Clone)]
pub(crate) struct ServiceFixture {
    pub utility_capacity: u64,
    pub local_capacity: u64,
    pub public_capacity: u64,
    pub purses: Vec<Currency>,
    /// What each household account needs, by service.
    pub wants: Vec<Vec<(u8, u64)>>,
    /// The cash of the business that asks for 100 units of utility, if there is one.
    pub business: Option<Currency>,
    /// The services in the order of paying, or `None` for a catalog without a policy.
    pub paying_order: Option<Vec<u8>>,
    pub funded: Vec<Funded>,
    /// The posted-price policy of the utility.
    pub utility_pricing: PricePolicy,
    /// The hours the utility's workers can give, if fewer than its nameplate batches.
    pub utility_hours: Option<u64>,
    /// Keep every provider's fixed price even where its service is in the order (to see it refused).
    pub keep_fixed: bool,
    /// What each account wants after its needs: account, tier, service, quantity. Each account is
    /// one household. A want of a service the account does not need adds its purchase row and
    /// connection.
    pub household_wants: Vec<(u8, WantTier, u8, u64)>,
}

impl ServiceFixture {
    pub(crate) fn new(purses: &[Currency], wants: &[Vec<(u8, u64)>]) -> Self {
        Self {
            utility_capacity: 1_000,
            local_capacity: 1_000,
            public_capacity: 1_000,
            purses: purses.to_vec(),
            wants: wants.to_vec(),
            business: None,
            paying_order: Some(vec![UTILITY, LOCAL]),
            funded: vec![],
            utility_pricing: PricePolicy::Fixed,
            utility_hours: None,
            keep_fixed: false,
            household_wants: vec![],
        }
    }

    /// The accounts' purchase rows: what each needs and what it only wants, once each.
    fn bought(&self) -> Vec<(u8, u8, u64)> {
        let mut rows: Vec<(u8, u8, u64)> = vec![];
        for (index, needs) in self.wants.iter().enumerate() {
            let index = u8::try_from(index).expect("few accounts");
            rows.extend(
                needs
                    .iter()
                    .map(|&(service, quantity)| (index, service, quantity)),
            );
        }
        for &(index, _, service, quantity) in &self.household_wants {
            if !rows.iter().any(|&(i, s, _)| (i, s) == (index, service)) {
                rows.push((index, service, quantity));
            }
        }
        rows.sort_unstable();
        rows
    }

    pub(crate) fn build(&self) -> (MaterialCatalog, MaterialCircuitState) {
        (
            MaterialCatalog::try_new(self.definition()).expect("the fixture catalog is valid"),
            self.state(),
        )
    }

    fn capacity(&self, service: u8) -> u64 {
        match service {
            UTILITY => self.utility_capacity,
            LOCAL => self.local_capacity,
            _ => self.public_capacity,
        }
    }

    /// The hours a producer can give: its nameplate batches, but for a utility with fewer hands.
    fn hands(&self, id: u8, planned: u64) -> u64 {
        match self.utility_hours {
            Some(hours) if id == UTILITY => hours,
            _ => planned,
        }
    }

    /// The business's process: a hundred batches that each take one unit of utility.
    const BUSINESS_BATCHES: u64 = 100;

    fn process(service: u8) -> ProcessId {
        ProcessId::from_bytes([provider(service) + 40; 32])
    }

    fn business_process() -> ProcessId {
        ProcessId::from_bytes([BUSINESS + 40; 32])
    }

    /// Every producing site with the process it runs and its hours in the period.
    fn producers(&self) -> Vec<(u8, ProcessId, u64)> {
        let mut rows: Vec<_> = [UTILITY, LOCAL, PUBLIC]
            .into_iter()
            .map(|service| {
                (
                    provider(service),
                    Self::process(service),
                    self.capacity(service),
                )
            })
            .collect();
        if self.business.is_some() {
            rows.push((BUSINESS, Self::business_process(), Self::BUSINESS_BATCHES));
        }
        rows
    }

    #[allow(clippy::too_many_lines, reason = "a fixture builds its whole catalog")]
    fn definition(&self) -> MaterialCatalogDefinition {
        let stage = |service: u8| match service {
            UTILITY => ServiceStage::UtilityProvision,
            _ => ServiceStage::LocalServiceProvision,
        };
        let mut commodities: Vec<_> = [UTILITY, LOCAL, PUBLIC]
            .into_iter()
            .map(|service| CommodityDefinition {
                good_id: support::good(service),
                unit_id: support::units(),
                kind: CommodityKind::PeriodService {
                    stage: stage(service),
                },
            })
            .collect();
        let mut process_outputs: Vec<_> = [UTILITY, LOCAL, PUBLIC]
            .into_iter()
            .map(|service| ProcessOutput {
                process_id: Self::process(service),
                site_id: support::site(provider(service)),
                good_id: support::good(service),
                unit_id: support::units(),
                quantity_per_batch: 1,
            })
            .collect();
        let mut input_coefficients = vec![];
        let mut service_inputs = vec![];
        if self.business.is_some() {
            commodities.push(CommodityDefinition {
                good_id: support::good(PRODUCT),
                unit_id: support::units(),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
            });
            process_outputs.push(ProcessOutput {
                process_id: Self::business_process(),
                site_id: support::site(BUSINESS),
                good_id: support::good(PRODUCT),
                unit_id: support::units(),
                quantity_per_batch: 1,
            });
            input_coefficients.push(InputOutputCoefficient {
                process_id: Self::business_process(),
                good_id: support::good(UTILITY),
                unit_id: support::units(),
                quantity_per_batch: 1,
            });
            service_inputs.push(ServiceInputPolicy {
                buyer_site_id: support::site(BUSINESS),
                provider_site_id: support::site(UTILITY),
                good_id: support::good(UTILITY),
                unit_id: support::units(),
                quantity_per_period: 100,
                maximum_purchase: 100,
                cash_floor: support::money(0),
            });
        }
        let mut household_needs = vec![];
        for (index, wants) in self.wants.iter().enumerate() {
            for &(service, quantity) in wants {
                household_needs.push(HouseholdNeed {
                    principal_id: account(u8::try_from(index).expect("few accounts")),
                    good_id: support::good(service),
                    unit_id: support::units(),
                    basis: HouseholdNeedBasis::Persons,
                    units_per_basis: quantity,
                });
            }
        }
        commodities.sort_by_key(|row| (row.good_id, row.unit_id));
        MaterialCatalogDefinition {
            market_clearing: self
                .paying_order
                .as_ref()
                .map(|order| MarketClearingPolicy {
                    paying_order: order
                        .iter()
                        .map(|&g| (support::good(g), support::units()))
                        .collect(),
                    household_wants: self
                        .household_wants
                        .iter()
                        .map(|&(index, tier, service, quantity)| HouseholdWant {
                            principal_id: account(index),
                            tier,
                            good_id: support::good(service),
                            unit_id: support::units(),
                            basis: HouseholdNeedBasis::Households,
                            units_per_basis: quantity,
                        })
                        .collect(),
                }),
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: self
                .producers()
                .iter()
                .map(|&(id, _, _)| SiteLogisticsNode {
                    site_id: support::site(id),
                    node_id: LogisticsNodeId::from_bytes([id; 32]),
                })
                .collect(),
            process_outputs,
            input_coefficients,
            labor_coefficients: self
                .producers()
                .iter()
                .map(|&(_, process, _)| LaborCoefficient {
                    process_id: process,
                    unit_id: support::hours(),
                    quantity_per_batch: 1,
                })
                .collect(),
            commodities,
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![],
            handling_coefficients: vec![],
            company_portfolios: None,
            company_payouts: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs,
            household_needs,
        }
    }

    fn recurring(&self) -> RecurringEconomy {
        let mut households = vec![];
        let mut purchases = vec![];
        for index in 0..self.wants.len() {
            let principal = account(u8::try_from(index).expect("few accounts"));
            households.push(HouseholdCohort {
                kind: HouseholdKind::Ordinary,
                principal_id: principal,
                households: 1,
                persons: 1,
            });
        }
        for (index, service, quantity) in self.bought() {
            purchases.push(HouseholdPurchasePolicy {
                principal_id: account(index),
                retailer_site_id: support::site(provider(service)),
                good_id: support::good(service),
                unit_id: support::units(),
                target_closing_stock: 0,
                maximum_purchase: quantity,
                enabled: true,
            });
        }
        let mut offers: Vec<_> = [UTILITY, LOCAL, PUBLIC]
            .into_iter()
            .map(|service| SellerOffer {
                site_id: support::site(provider(service)),
                good_id: support::good(service),
                unit_id: support::units(),
                unit_price: posted(service),
                pricing: support::held(
                    &if service == UTILITY {
                        self.utility_pricing.clone()
                    } else {
                        PricePolicy::Fixed
                    },
                    self.paying_order.as_deref(),
                    self.keep_fixed,
                    service,
                    posted(service),
                    true,
                ),
            })
            .collect();
        if self.business.is_some() {
            // The business sells what it makes at a price that covers the utility many times over,
            // so its limit (P5) never binds in these tests.
            offers.push(SellerOffer {
                site_id: support::site(BUSINESS),
                good_id: support::good(PRODUCT),
                unit_id: support::units(),
                unit_price: support::dollars(100),
                pricing: support::held(
                    &PricePolicy::Fixed,
                    self.paying_order.as_deref(),
                    self.keep_fixed,
                    PRODUCT,
                    support::dollars(100),
                    false,
                ),
            });
            offers.sort_by_key(|o| (o.site_id, o.good_id, o.unit_id));
        }
        RecurringEconomy {
            households,
            household_stocks: vec![],
            household_purchases: purchases,
            offers,
            replenishment: vec![],
            production: self
                .producers()
                .iter()
                .map(|&(id, process, hours)| ProductionDemandPolicy {
                    process_id: process,
                    site_id: support::site(id),
                    output_buffer: 0,
                    planned_batches: hours,
                })
                .collect(),
            attendance: self
                .producers()
                .iter()
                .map(|&(id, _, planned)| AttendancePlan {
                    site_id: support::site(id),
                    unit_id: support::hours(),
                    period: 1,
                    planned_hours: self.hands(id, planned),
                })
                .collect(),
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        }
    }

    fn connections(&self) -> Vec<ServiceConnection> {
        let mut rows = vec![];
        for (index, service, _) in self.bought() {
            rows.push(ServiceConnection {
                provider_site_id: support::site(provider(service)),
                buyer: AccountId::Household(account(index)),
                good_id: support::good(service),
                unit_id: support::units(),
            });
        }
        if self.business.is_some() {
            rows.push(ServiceConnection {
                provider_site_id: support::site(UTILITY),
                buyer: AccountId::Site(support::site(BUSINESS)),
                good_id: support::good(UTILITY),
                unit_id: support::units(),
            });
        }
        rows.sort();
        rows
    }

    #[allow(clippy::too_many_lines, reason = "a fixture builds its whole state")]
    fn state(&self) -> MaterialCircuitState {
        let payee = FinalDemandPrincipalId::from_bytes([PAYEE; 32]);
        let mut accounts: Vec<_> = self
            .producers()
            .iter()
            .map(|&(id, _, _)| CashAccount {
                id: AccountId::Site(support::site(id)),
                cash: if id == BUSINESS {
                    self.business.unwrap_or_else(|| support::money(0))
                } else {
                    support::dollars(1_000)
                },
            })
            .collect();
        for (index, purse) in self.purses.iter().enumerate() {
            accounts.push(CashAccount {
                id: AccountId::Household(account(u8::try_from(index).expect("few accounts"))),
                cash: *purse,
            });
        }
        accounts.push(CashAccount {
            id: AccountId::Household(payee),
            cash: support::dollars(1_000_000),
        });
        let mut book = MonetaryBook::open(accounts).expect("the fixture opens the authored source");
        let mut service_orders = vec![];
        for row in &self.funded {
            let order = ServiceOrder {
                order_id: OrderId::from_bytes([row.order; 32]),
                performance_period: 1,
                provider_site_id: support::site(provider(row.service)),
                buyer: AccountId::Household(account(row.buyer)),
                good_id: support::good(row.service),
                unit_id: support::units(),
                quantity: row.quantity,
            };
            book.reserve_purchase(
                PurchaseEscrow::new(
                    OutboundOrderId::Service(order.order_id),
                    order.buyer,
                    AccountId::Site(order.provider_site_id),
                    row.quantity,
                    row.price,
                )
                .expect("the fixture escrow is valid"),
            )
            .expect("the buyer can fund its order");
            service_orders.push(order);
        }
        service_orders.sort_by_key(|row| row.order_id);
        let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
            .expect("the fixture opens the authored source");
        let mut principals: Vec<_> = (0..self.purses.len())
            .map(|index| account(u8::try_from(index).expect("few accounts")))
            .collect();
        principals.push(payee);
        let location: EconomicLocation = "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type");
        let producers = self.producers();
        let member = |id: u8| StaffingMemberId::from_bytes(support::site(id).as_bytes());
        MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                aid: AidBook::default(),
                household_time: HouseholdTimeAccounting::NotModeled,
                financial: FinancialInstitutions::empty(),
                member_labor: producers
                    .iter()
                    .flat_map(|&(id, _, planned)| {
                        let hours = self.hands(id, planned);
                        (1..=9).map(move |period| MemberLaborCapacityRow {
                            member_id: member(id),
                            period,
                            available_hours: hours,
                        })
                    })
                    .collect(),
                costs,
                book,
                recurring: Some(Box::new(self.recurring())),
                employment: producers
                    .iter()
                    .map(|&(id, _, _)| EmploymentTerms {
                        member_id: member(id),
                        site_id: support::site(id),
                        unit_id: support::hours(),
                        payee,
                        compensation: LaborCompensation::Wage(support::money(1)),
                    })
                    .collect(),
            })),
            service_connections: self.connections(),
            service_orders,
            route_stage_capacities: vec![],
            inventory: vec![],
            orders: vec![],
            freight: vec![],
            corridor_capacities: vec![],
            capacities: producers
                .iter()
                .flat_map(|&(id, process, planned)| {
                    (1..=9).map(move |period| CapacityRow {
                        process_id: process,
                        site_id: support::site(id),
                        period,
                        available_batches: planned,
                    })
                })
                .collect(),
            labor: producers
                .iter()
                .flat_map(|&(id, _, planned)| {
                    let hours = self.hands(id, planned);
                    (1..=9).map(move |period| LaborCapacityRow {
                        site_id: support::site(id),
                        unit_id: support::hours(),
                        period,
                        available: hours,
                    })
                })
                .collect(),
            production_commitments: producers
                .iter()
                .map(|&(id, process, planned)| ProductionCommitment {
                    process_id: process,
                    site_id: support::site(id),
                    period: 1,
                    planned_batches: planned,
                })
                .collect(),
            final_demand_principals: principals
                .into_iter()
                .map(|id| FinalDemandPrincipal { id, location })
                .collect(),
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        }
    }
}

/// The good of a service.
pub(crate) fn service_good(service: u8) -> GoodId {
    support::good(service)
}
