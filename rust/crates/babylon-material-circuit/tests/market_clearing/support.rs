//! A small recurring economy with one retailer and any number of household accounts.

use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, AidBook, AttendancePlan, CapacityReservations, CapacityRow, CapacitySupply,
    CashAccount, CircuitAccounting, CommodityDefinition, CommodityKind, CorridorCapacity,
    CorridorId, EmploymentTerms, FinalDemandOrder, FinalDemandPrincipal, FinalDemandPrincipalId,
    FinancialInstitutions, GoodId, HistoricalCostBook, HouseholdCohort, HouseholdKind,
    HouseholdNeed, HouseholdNeedBasis, HouseholdPurchasePolicy, HouseholdStock,
    HouseholdTimeAccounting, InputOutputCoefficient, InventoryRow, LaborCapacityRow,
    LaborCoefficient, LaborCompensation, LogisticsNodeId, MarketClearingPolicy, MaterialCatalog,
    MaterialCatalogDefinition, MaterialCircuitState, MemberLaborCapacityRow, MerchantHandling,
    MerchantHandlingCoefficient, MerchantRole, MonetaryBook, MonetaryCircuit, OrderId,
    OutboundOrderId, PricePolicy, ProcessId, ProcessOutput, ProductionCommitment,
    ProductionDemandPolicy, PurchaseEscrow, RecurringEconomy, SellerOffer, SiteId,
    SiteLogisticsNode, StaffingMemberId, StockCarryingValue, UnitId,
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

pub(crate) fn money(micro: i128) -> Currency {
    Currency::from_micro_units(micro)
}

/// Dollars as money.
pub(crate) fn dollars(value: i128) -> Currency {
    Currency::from_micro_units(value * 1_000_000)
}

/// The retailer's site.
pub(crate) const RETAILER: u8 = 3;
/// The buyer of an order that was accepted in an earlier period.
pub(crate) const EARLIER_BUYER: u8 = 99;

pub(crate) fn account(index: u8) -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([10 + index; 32])
}

/// One good on the shelf.
#[derive(Clone)]
pub(crate) struct Shelf {
    pub good: u8,
    pub price: Currency,
    pub stock: u64,
}

/// What one fixture holds.
#[derive(Clone)]
pub(crate) struct Fixture {
    pub shelves: Vec<Shelf>,
    /// The cash of each household account.
    pub purses: Vec<Currency>,
    /// What each household account asks for of each good.
    pub wanted: u64,
    /// The handling hours of the retailer in the period.
    pub hours: u64,
    /// The goods in the order of paying, or `None` for a catalog without a policy.
    pub paying_order: Option<Vec<u8>>,
    /// Units of the first good owed to an order accepted earlier.
    pub owed: u64,
    /// A process at the retailer that takes the first good as an input and plans this many batches.
    pub process_batches: Option<u64>,
}

impl Fixture {
    pub(crate) fn new(stock: u64, purses: &[Currency]) -> Self {
        Self {
            shelves: vec![Shelf {
                good: 2,
                price: dollars(4),
                stock,
            }],
            purses: purses.to_vec(),
            wanted: 100,
            hours: 100_000,
            paying_order: Some(vec![2]),
            owed: 0,
            process_batches: None,
        }
    }

    pub(crate) fn build(&self) -> (MaterialCatalog, MaterialCircuitState) {
        (
            MaterialCatalog::try_new(self.definition()).expect("the fixture catalog is valid"),
            self.state(),
        )
    }

    fn definition(&self) -> MaterialCatalogDefinition {
        let retailer = site(RETAILER);
        let mut commodities: Vec<_> = self
            .shelves
            .iter()
            .map(|shelf| CommodityDefinition {
                good_id: good(shelf.good),
                unit_id: units(),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
            })
            .collect();
        let mut process_outputs = vec![];
        let mut input_coefficients = vec![];
        let mut labor_coefficients = vec![];
        if self.process_batches.is_some() {
            commodities.push(CommodityDefinition {
                good_id: good(50),
                unit_id: units(),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
            });
            process_outputs.push(ProcessOutput {
                process_id: ProcessId::from_bytes([50; 32]),
                site_id: retailer,
                good_id: good(50),
                unit_id: units(),
                quantity_per_batch: 1,
            });
            input_coefficients.push(InputOutputCoefficient {
                process_id: ProcessId::from_bytes([50; 32]),
                good_id: good(self.shelves[0].good),
                unit_id: units(),
                quantity_per_batch: 1,
            });
            labor_coefficients.push(LaborCoefficient {
                process_id: ProcessId::from_bytes([50; 32]),
                unit_id: hours(),
                quantity_per_batch: 1,
            });
        }
        let mut household_needs = vec![];
        for index in 0..self.purses.len() {
            let index = u8::try_from(index).expect("the fixture has few accounts");
            for shelf in &self.shelves {
                household_needs.push(HouseholdNeed {
                    principal_id: account(index),
                    good_id: good(shelf.good),
                    unit_id: units(),
                    basis: HouseholdNeedBasis::Persons,
                    units_per_basis: 1,
                });
            }
        }
        MaterialCatalogDefinition {
            market_clearing: self
                .paying_order
                .as_ref()
                .map(|order| MarketClearingPolicy {
                    paying_order: order.iter().map(|&g| (good(g), units())).collect(),
                }),
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![SiteLogisticsNode {
                site_id: retailer,
                node_id: LogisticsNodeId::from_bytes([RETAILER; 32]),
            }],
            process_outputs,
            input_coefficients,
            labor_coefficients,
            commodities,
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![MerchantHandling {
                site_id: retailer,
                location: "county:26163"
                    .parse()
                    .expect("the authored literal parses as the declared type"),
                role: MerchantRole::Retail,
                capacity_id: CorridorId::from_bytes([RETAILER; 32]),
                labor_unit_id: hours(),
            }],
            handling_coefficients: self
                .shelves
                .iter()
                .map(|shelf| MerchantHandlingCoefficient {
                    site_id: retailer,
                    good_id: good(shelf.good),
                    unit_id: units(),
                    hours_per_unit: 1,
                })
                .collect(),
            company_portfolios: None,
            company_payouts: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs,
        }
    }

    fn recurring(&self) -> RecurringEconomy {
        let retailer = site(RETAILER);
        let mut households = vec![];
        let mut stocks = vec![];
        let mut purchases = vec![];
        for index in 0..self.purses.len() {
            let index = u8::try_from(index).expect("the fixture has few accounts");
            households.push(HouseholdCohort {
                kind: HouseholdKind::Ordinary,
                principal_id: account(index),
                households: 1,
                persons: self.wanted,
            });
            for shelf in &self.shelves {
                stocks.push(HouseholdStock {
                    principal_id: account(index),
                    good_id: good(shelf.good),
                    unit_id: units(),
                    quantity: 0,
                });
                purchases.push(HouseholdPurchasePolicy {
                    principal_id: account(index),
                    retailer_site_id: retailer,
                    good_id: good(shelf.good),
                    unit_id: units(),
                    target_closing_stock: 0,
                    maximum_purchase: self.wanted,
                    enabled: true,
                });
            }
        }
        RecurringEconomy {
            households,
            household_stocks: stocks,
            household_purchases: purchases,
            offers: self
                .shelves
                .iter()
                .map(|shelf| SellerOffer {
                    site_id: retailer,
                    good_id: good(shelf.good),
                    unit_id: units(),
                    unit_price: shelf.price,
                    pricing: PricePolicy::Fixed,
                })
                .collect(),
            replenishment: vec![],
            production: self
                .process_batches
                .map(|batches| ProductionDemandPolicy {
                    process_id: ProcessId::from_bytes([50; 32]),
                    site_id: retailer,
                    output_buffer: 0,
                    planned_batches: batches,
                })
                .into_iter()
                .collect(),
            attendance: vec![AttendancePlan {
                site_id: retailer,
                unit_id: hours(),
                period: 1,
                planned_hours: self.hours,
            }],
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        }
    }

    #[allow(clippy::too_many_lines, reason = "a fixture builds its whole state")]
    fn state(&self) -> MaterialCircuitState {
        let retailer = site(RETAILER);
        let mut accounts = vec![CashAccount {
            id: AccountId::Site(retailer),
            cash: dollars(1_000),
        }];
        for (index, purse) in self.purses.iter().enumerate() {
            accounts.push(CashAccount {
                id: AccountId::Household(account(
                    u8::try_from(index).expect("the fixture has few accounts"),
                )),
                cash: *purse,
            });
        }
        let earlier = FinalDemandPrincipalId::from_bytes([EARLIER_BUYER; 32]);
        accounts.push(CashAccount {
            id: AccountId::Household(earlier),
            cash: dollars(1_000_000),
        });
        let mut book = MonetaryBook::open(accounts).expect("the fixture opens the authored source");
        let first = &self.shelves[0];
        let earlier_order = OrderId::from_bytes([EARLIER_BUYER; 32]);
        let mut final_demand_orders = vec![];
        if self.owed > 0 {
            book.reserve_purchase(
                PurchaseEscrow::new(
                    OutboundOrderId::LocalFinalDemand(earlier_order),
                    AccountId::Household(earlier),
                    AccountId::Site(retailer),
                    self.owed,
                    first.price,
                )
                .expect("the fixture escrow is valid"),
            )
            .expect("the earlier buyer can fund its order");
            final_demand_orders.push(FinalDemandOrder {
                order_id: earlier_order,
                retailer_site_id: retailer,
                demand_principal_id: earlier,
                good_id: good(first.good),
                unit_id: units(),
                ordered: self.owed,
                fulfilled: 0,
            });
        }
        let mut carrying: Vec<_> = self
            .shelves
            .iter()
            .map(|shelf| StockCarryingValue {
                owner: AccountId::Site(retailer),
                good_id: good(shelf.good),
                unit_id: units(),
                amount: money(shelf.price.micro_units() * i128::from(shelf.stock) / 2),
            })
            .collect();
        for index in 0..self.purses.len() {
            for shelf in &self.shelves {
                carrying.push(StockCarryingValue {
                    owner: AccountId::Household(account(
                        u8::try_from(index).expect("the fixture has few accounts"),
                    )),
                    good_id: good(shelf.good),
                    unit_id: units(),
                    amount: money(0),
                });
            }
        }
        let costs = HistoricalCostBook::open(&book, carrying, vec![], vec![], vec![])
            .expect("the fixture opens the authored source");
        let member = StaffingMemberId::from_bytes(retailer.as_bytes());
        let mut principals: Vec<_> = (0..self.purses.len())
            .map(|index| account(u8::try_from(index).expect("the fixture has few accounts")))
            .collect();
        principals.push(earlier);
        let location: EconomicLocation = "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type");
        let process = ProcessId::from_bytes([50; 32]);
        MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                aid: AidBook::default(),
                household_time: HouseholdTimeAccounting::NotModeled,
                financial: FinancialInstitutions::empty(),
                member_labor: (1..=9)
                    .map(|period| MemberLaborCapacityRow {
                        member_id: member,
                        period,
                        available_hours: self.hours,
                    })
                    .collect(),
                costs,
                book,
                recurring: Some(Box::new(self.recurring())),
                employment: vec![EmploymentTerms {
                    member_id: member,
                    site_id: retailer,
                    unit_id: hours(),
                    payee: FinalDemandPrincipalId::from_bytes([EARLIER_BUYER; 32]),
                    compensation: LaborCompensation::Wage(money(1)),
                }],
            })),
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: self
                .shelves
                .iter()
                .map(|shelf| InventoryRow {
                    site_id: retailer,
                    good_id: good(shelf.good),
                    unit_id: units(),
                    quantity: shelf.stock,
                })
                .collect(),
            orders: vec![],
            freight: vec![],
            corridor_capacities: (1..=9)
                .map(|period| CorridorCapacity {
                    corridor_id: CorridorId::from_bytes([RETAILER; 32]),
                    period,
                    available_grams: 1_000_000,
                })
                .collect(),
            capacities: self
                .process_batches
                .map(|batches| {
                    (1..=9)
                        .map(|period| CapacityRow {
                            process_id: process,
                            site_id: retailer,
                            period,
                            available_batches: batches,
                        })
                        .collect()
                })
                .unwrap_or_default(),
            labor: (1..=9)
                .map(|period| LaborCapacityRow {
                    site_id: retailer,
                    unit_id: hours(),
                    period,
                    available: self.hours,
                })
                .collect(),
            production_commitments: self
                .process_batches
                .map(|batches| ProductionCommitment {
                    process_id: process,
                    site_id: retailer,
                    period: 1,
                    planned_batches: batches,
                })
                .into_iter()
                .collect(),
            final_demand_principals: principals
                .into_iter()
                .map(|id| FinalDemandPrincipal { id, location })
                .collect(),
            final_demand_orders,
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        }
    }
}
