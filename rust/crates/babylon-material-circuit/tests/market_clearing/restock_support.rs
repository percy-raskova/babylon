//! A small economy of businesses that restock an input: suppliers that hold it, and buyers that
//! are makers of something else or merchants of the input itself.

use super::support;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, AidBook, AttendancePlan, CapacityReservations, CapacitySupply, CashAccount,
    CircuitAccounting, CommodityDefinition, CommodityKind, CorridorCapacity, CorridorId,
    EmploymentTerms, FinalDemandPrincipal, FinalDemandPrincipalId, FinancialInstitutions, GoodId,
    HistoricalCostBook, HouseholdTimeAccounting, InputOutputCoefficient, InventoryRow,
    LaborCapacityRow, LaborCoefficient, LaborCompensation, LogisticsNodeId, MarketClearingPolicy,
    MaterialCatalog, MaterialCatalogDefinition, MaterialCircuitState, MemberLaborCapacityRow,
    MerchantHandling, MerchantHandlingCoefficient, MerchantRole, MonetaryBook, MonetaryCircuit,
    OrderAccessMode, OrderId, OrderRow, OutboundOrderId, PricePolicy, ProcessId, ProcessOutput,
    ProductionDemandPolicy, PurchaseEscrow, RecurringEconomy, ReplenishmentPolicy, RouteId,
    RouteStage, RouteStageCapacity, SellerOffer, SiteId, SiteLogisticsNode, StaffingMemberId,
    StockCarryingValue, SupplierRoute, SupplierTransport,
};

/// The input everyone bargains over.
pub(crate) const INPUT: u8 = 1;
/// The payee of every wage.
const PAYEE: u8 = 99;
/// The wage of an hour, in dollars.
pub(crate) const WAGE: i128 = 5;
/// The site of the buyer whose earlier order is blocked on a closed route.
const BLOCKED: u8 = 90;
/// The id of the earlier order.
const EARLIER_ORDER: u8 = 77;

/// A seller of the input.
#[derive(Clone)]
pub(crate) struct Supplier {
    pub stock: u64,
    pub price: Currency,
}

/// What a buyer does with the input.
#[derive(Clone, Copy)]
pub(crate) enum Use {
    /// A maker: one batch takes one unit of the input and yields one unit of its own good, which
    /// it sells at this price.
    Makes(Currency),
    /// A merchant: it sells the input itself at this price and takes one hour to hand over a unit.
    Sells(Currency),
}

/// A business that restocks the input.
#[derive(Clone)]
pub(crate) struct Buyer {
    pub cash: Currency,
    pub uses: Use,
    /// Its target stock and its largest purchase.
    pub wanted: u64,
    /// The funded hours of its one wage earner, or 0 for a buyer without staff.
    pub hours: u64,
    /// What its routes carry in a period, in units.
    pub route_units: u64,
}

impl Buyer {
    pub(crate) fn maker(cash: Currency, price: Currency, wanted: u64) -> Self {
        Self {
            cash,
            uses: Use::Makes(price),
            wanted,
            hours: 10,
            route_units: 1_000_000,
        }
    }
}

#[derive(Clone)]
pub(crate) struct Restock {
    pub suppliers: Vec<Supplier>,
    pub buyers: Vec<Buyer>,
    /// Units of the first supplier's stock owed to an earlier order that its route cannot carry.
    pub owed: u64,
    pub paying_order: Option<Vec<u8>>,
}

pub(crate) fn supplier_site(index: usize) -> SiteId {
    support::site(1 + u8::try_from(index).expect("few suppliers"))
}

pub(crate) fn buyer_site(index: usize) -> SiteId {
    support::site(11 + u8::try_from(index).expect("few buyers"))
}

pub(crate) fn output_good(index: usize) -> GoodId {
    support::good(20 + u8::try_from(index).expect("few buyers"))
}

fn route(supplier: u8, buyer: u8) -> RouteId {
    RouteId::from_bytes(
        [100 + supplier, buyer, 0, 0]
            .repeat(8)
            .try_into()
            .expect("32 bytes"),
    )
}

fn corridor(supplier: u8, buyer: u8) -> CorridorId {
    CorridorId::from_bytes(
        [150 + supplier, buyer, 0, 0]
            .repeat(8)
            .try_into()
            .expect("32 bytes"),
    )
}

fn node(id: u8) -> LogisticsNodeId {
    LogisticsNodeId::from_bytes([id; 32])
}

fn member(id: u8) -> StaffingMemberId {
    StaffingMemberId::from_bytes([id; 32])
}

fn process(index: usize) -> ProcessId {
    ProcessId::from_bytes([50 + u8::try_from(index).expect("few buyers"); 32])
}

fn location() -> EconomicLocation {
    "county:26163"
        .parse()
        .expect("the authored literal parses as the declared type")
}

impl Restock {
    pub(crate) fn new(suppliers: Vec<Supplier>, buyers: Vec<Buyer>) -> Self {
        Self {
            suppliers,
            buyers,
            owed: 0,
            paying_order: Some(vec![INPUT]),
        }
    }

    pub(crate) fn build(&self) -> (MaterialCatalog, MaterialCircuitState) {
        (
            MaterialCatalog::try_new(self.definition()).expect("the fixture catalog is valid"),
            self.state(),
        )
    }

    fn pairs(&self) -> Vec<(u8, u8)> {
        let mut pairs = vec![];
        for s in 0..self.suppliers.len() {
            for b in 0..self.buyers.len() {
                pairs.push((
                    u8::try_from(s).expect("few suppliers"),
                    u8::try_from(b).expect("few buyers"),
                ));
            }
        }
        pairs
    }

    #[allow(clippy::too_many_lines, reason = "a fixture builds its whole catalog")]
    fn definition(&self) -> MaterialCatalogDefinition {
        let mut sites: Vec<SiteId> = (0..self.suppliers.len()).map(supplier_site).collect();
        sites.extend((0..self.buyers.len()).map(buyer_site));
        if self.owed > 0 {
            sites.push(support::site(BLOCKED));
        }
        let mut commodities = vec![CommodityDefinition {
            good_id: support::good(INPUT),
            unit_id: support::units(),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        }];
        let mut process_outputs = vec![];
        let mut input_coefficients = vec![];
        let mut labor_coefficients = vec![];
        let mut merchants = vec![];
        let mut handling = vec![];
        for (index, buyer) in self.buyers.iter().enumerate() {
            match buyer.uses {
                Use::Makes(_) => {
                    commodities.push(CommodityDefinition {
                        good_id: output_good(index),
                        unit_id: support::units(),
                        kind: CommodityKind::Storable { grams_per_unit: 1 },
                    });
                    process_outputs.push(ProcessOutput {
                        process_id: process(index),
                        site_id: buyer_site(index),
                        good_id: output_good(index),
                        unit_id: support::units(),
                        quantity_per_batch: 1,
                    });
                    input_coefficients.push(InputOutputCoefficient {
                        process_id: process(index),
                        good_id: support::good(INPUT),
                        unit_id: support::units(),
                        quantity_per_batch: 1,
                    });
                    labor_coefficients.push(LaborCoefficient {
                        process_id: process(index),
                        unit_id: support::hours(),
                        quantity_per_batch: 1,
                    });
                }
                Use::Sells(_) => {
                    merchants.push(MerchantHandling {
                        site_id: buyer_site(index),
                        location: location(),
                        role: MerchantRole::Retail,
                        capacity_id: CorridorId::from_bytes(
                            [11 + u8::try_from(index).expect("few"); 32],
                        ),
                        labor_unit_id: support::hours(),
                    });
                    handling.push(MerchantHandlingCoefficient {
                        site_id: buyer_site(index),
                        good_id: support::good(INPUT),
                        unit_id: support::units(),
                        hours_per_unit: 1,
                    });
                }
            }
        }
        let mut supplier_routes = vec![];
        let mut route_stages = vec![];
        for (s, b) in self.pairs() {
            supplier_routes.push(SupplierRoute {
                buyer_site_id: buyer_site(usize::from(b)),
                supplier_site_id: supplier_site(usize::from(s)),
                good_id: support::good(INPUT),
                unit_id: support::units(),
                route_id: route(s, b),
                transport_kind: SupplierTransport::Staged,
            });
            route_stages.push(RouteStage {
                route_id: route(s, b),
                stage_index: 0,
                from_node_id: node(1 + s),
                to_node_id: node(11 + b),
                travel_periods: 1,
                loss_ppm: 0,
            });
        }
        if self.owed > 0 {
            supplier_routes.push(SupplierRoute {
                buyer_site_id: support::site(BLOCKED),
                supplier_site_id: supplier_site(0),
                good_id: support::good(INPUT),
                unit_id: support::units(),
                route_id: route(0, BLOCKED),
                transport_kind: SupplierTransport::Staged,
            });
            route_stages.push(RouteStage {
                route_id: route(0, BLOCKED),
                stage_index: 0,
                from_node_id: node(1),
                to_node_id: node(BLOCKED),
                travel_periods: 1,
                loss_ppm: 0,
            });
        }
        MaterialCatalogDefinition {
            market_clearing: self
                .paying_order
                .as_ref()
                .map(|order| MarketClearingPolicy {
                    paying_order: order
                        .iter()
                        .map(|&g| (support::good(g), support::units()))
                        .collect(),
                }),
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: sites
                .iter()
                .map(|&site_id| SiteLogisticsNode {
                    site_id,
                    node_id: node(site_id.as_bytes()[0]),
                })
                .collect(),
            process_outputs,
            input_coefficients,
            labor_coefficients,
            commodities,
            supplier_routes,
            route_stages,
            merchants,
            handling_coefficients: handling,
            company_portfolios: None,
            company_payouts: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs: vec![],
        }
    }

    fn recurring(&self) -> RecurringEconomy {
        let mut offers = vec![];
        for (index, supplier) in self.suppliers.iter().enumerate() {
            offers.push(SellerOffer {
                site_id: supplier_site(index),
                good_id: support::good(INPUT),
                unit_id: support::units(),
                unit_price: supplier.price,
                pricing: support::held(
                    &PricePolicy::Fixed,
                    self.paying_order.as_deref(),
                    false,
                    INPUT,
                    supplier.price,
                    false,
                ),
            });
        }
        let mut replenishment = vec![];
        let mut attendance = vec![];
        let mut production = vec![];
        for (index, buyer) in self.buyers.iter().enumerate() {
            if matches!(buyer.uses, Use::Makes(_)) {
                production.push(ProductionDemandPolicy {
                    process_id: process(index),
                    site_id: buyer_site(index),
                    output_buffer: 0,
                    planned_batches: 0,
                });
            }
            let (good_id, price, good_number) = match buyer.uses {
                Use::Makes(price) => (
                    output_good(index),
                    price,
                    20 + u8::try_from(index).expect("few buyers"),
                ),
                Use::Sells(price) => (support::good(INPUT), price, INPUT),
            };
            offers.push(SellerOffer {
                site_id: buyer_site(index),
                good_id,
                unit_id: support::units(),
                unit_price: price,
                pricing: support::held(
                    &PricePolicy::Fixed,
                    self.paying_order.as_deref(),
                    false,
                    good_number,
                    price,
                    false,
                ),
            });
            for s in 0..self.suppliers.len() {
                replenishment.push(ReplenishmentPolicy {
                    buyer_site_id: buyer_site(index),
                    supplier_site_id: supplier_site(s),
                    good_id: support::good(INPUT),
                    unit_id: support::units(),
                    target_stock: buyer.wanted,
                    maximum_purchase: buyer.wanted,
                    cash_floor: Currency::from_micro_units(0),
                });
            }
            if buyer.hours > 0 {
                attendance.push(AttendancePlan {
                    site_id: buyer_site(index),
                    unit_id: support::hours(),
                    period: 1,
                    planned_hours: buyer.hours,
                });
            }
        }
        offers.sort_by_key(|o| (o.site_id, o.good_id, o.unit_id));
        replenishment.sort_by_key(|p| (p.buyer_site_id, p.supplier_site_id, p.good_id, p.unit_id));
        attendance.sort_by_key(|p| (p.site_id, p.unit_id));
        RecurringEconomy {
            households: vec![],
            household_stocks: vec![],
            household_purchases: vec![],
            offers,
            replenishment,
            production,
            attendance,
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        }
    }

    #[allow(clippy::too_many_lines, reason = "a fixture builds its whole state")]
    pub(crate) fn state(&self) -> MaterialCircuitState {
        let payee = FinalDemandPrincipalId::from_bytes([PAYEE; 32]);
        let mut accounts = vec![CashAccount {
            id: AccountId::Household(payee),
            cash: support::dollars(1_000_000),
        }];
        for index in 0..self.suppliers.len() {
            accounts.push(CashAccount {
                id: AccountId::Site(supplier_site(index)),
                cash: support::dollars(1_000),
            });
        }
        for (index, buyer) in self.buyers.iter().enumerate() {
            accounts.push(CashAccount {
                id: AccountId::Site(buyer_site(index)),
                cash: buyer.cash,
            });
        }
        if self.owed > 0 {
            accounts.push(CashAccount {
                id: AccountId::Site(support::site(BLOCKED)),
                cash: support::dollars(1_000_000),
            });
        }
        let mut book = MonetaryBook::open(accounts).expect("the fixture opens the authored source");
        let mut orders = vec![];
        if self.owed > 0 {
            let id = OrderId::from_bytes([EARLIER_ORDER; 32]);
            book.reserve_purchase(
                PurchaseEscrow::new(
                    OutboundOrderId::Delivery(id),
                    AccountId::Site(support::site(BLOCKED)),
                    AccountId::Site(supplier_site(0)),
                    self.owed,
                    self.suppliers[0].price,
                )
                .expect("the fixture escrow is valid"),
            )
            .expect("the earlier buyer can fund its order");
            orders.push(OrderRow {
                order_id: id,
                access_mode: OrderAccessMode::CommoditySale,
                buyer_site_id: support::site(BLOCKED),
                supplier_site_id: supplier_site(0),
                good_id: support::good(INPUT),
                unit_id: support::units(),
                ordered: self.owed,
                shipped: 0,
                lost: 0,
                delivered: 0,
                realized: 0,
            });
        }
        let mut carrying = vec![];
        for (index, supplier) in self.suppliers.iter().enumerate() {
            carrying.push(StockCarryingValue {
                owner: AccountId::Site(supplier_site(index)),
                good_id: support::good(INPUT),
                unit_id: support::units(),
                amount: Currency::from_micro_units(
                    supplier.price.micro_units() * i128::from(supplier.stock) / 2,
                ),
            });
        }
        let costs = HistoricalCostBook::open(&book, carrying, vec![], vec![], vec![])
            .expect("the fixture opens the authored source");
        let staffed: Vec<_> = self
            .buyers
            .iter()
            .enumerate()
            .filter(|(_, buyer)| buyer.hours > 0)
            .map(|(index, buyer)| (index, buyer.hours))
            .collect();
        let mut corridor_capacities = vec![];
        let mut route_stage_capacities = vec![];
        for (s, b) in self.pairs() {
            route_stage_capacities.push(RouteStageCapacity {
                route_id: route(s, b),
                stage_index: 0,
                corridor_id: corridor(s, b),
            });
            for period in 1..=9 {
                corridor_capacities.push(CorridorCapacity {
                    corridor_id: corridor(s, b),
                    period,
                    available_grams: self.buyers[usize::from(b)].route_units,
                });
            }
        }
        if self.owed > 0 {
            route_stage_capacities.push(RouteStageCapacity {
                route_id: route(0, BLOCKED),
                stage_index: 0,
                corridor_id: corridor(0, BLOCKED),
            });
            for period in 1..=9 {
                corridor_capacities.push(CorridorCapacity {
                    corridor_id: corridor(0, BLOCKED),
                    period,
                    available_grams: 0,
                });
            }
        }
        for (index, buyer) in self.buyers.iter().enumerate() {
            if matches!(buyer.uses, Use::Sells(_)) {
                for period in 1..=9 {
                    corridor_capacities.push(CorridorCapacity {
                        corridor_id: CorridorId::from_bytes(
                            [11 + u8::try_from(index).expect("few"); 32],
                        ),
                        period,
                        available_grams: 1_000_000,
                    });
                }
            }
        }
        corridor_capacities.sort();
        route_stage_capacities.sort();
        let mut principals = vec![FinalDemandPrincipal {
            id: payee,
            location: location(),
        }];
        principals.sort_by_key(|p| p.id);
        let mut inventory: Vec<_> = self
            .suppliers
            .iter()
            .enumerate()
            .map(|(index, supplier)| InventoryRow {
                site_id: supplier_site(index),
                good_id: support::good(INPUT),
                unit_id: support::units(),
                quantity: supplier.stock,
            })
            .collect();
        inventory.sort();
        MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                aid: AidBook::default(),
                household_time: HouseholdTimeAccounting::NotModeled,
                financial: FinancialInstitutions::empty(),
                member_labor: staffed
                    .iter()
                    .flat_map(|&(index, available_hours)| {
                        (1..=9).map(move |period| MemberLaborCapacityRow {
                            member_id: member(11 + u8::try_from(index).expect("few")),
                            period,
                            available_hours,
                        })
                    })
                    .collect(),
                costs,
                book,
                recurring: Some(Box::new(self.recurring())),
                employment: staffed
                    .iter()
                    .map(|&(index, _)| EmploymentTerms {
                        member_id: member(11 + u8::try_from(index).expect("few")),
                        site_id: buyer_site(index),
                        unit_id: support::hours(),
                        payee,
                        compensation: LaborCompensation::Wage(support::money(WAGE * 1_000_000)),
                    })
                    .collect(),
            })),
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities,
            inventory,
            orders,
            freight: vec![],
            corridor_capacities,
            capacities: vec![],
            labor: staffed
                .iter()
                .flat_map(|&(index, available)| {
                    (1..=9).map(move |period| LaborCapacityRow {
                        site_id: buyer_site(index),
                        unit_id: support::hours(),
                        period,
                        available,
                    })
                })
                .collect(),
            production_commitments: vec![],
            final_demand_principals: principals,
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        }
    }
}
