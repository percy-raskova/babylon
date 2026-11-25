//! A market of thousands of sellers of one good closes in one period.
//!
//! The fixture is built here, with ids made from a `u32`: the other fixtures of this file take `u8`.

use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, AdjustmentRule, AidBook, AttendancePlan, CapacityReservations, CapacitySupply,
    CashAccount, CircuitAccounting, CommodityDefinition, CommodityKind, CorridorCapacity,
    CorridorId, EmploymentTerms, FinalDemandPrincipal, FinalDemandPrincipalId,
    FinancialInstitutions, GoodId, HistoricalCostBook, HouseholdTimeAccounting, LaborCapacityRow,
    LaborCompensation, LogisticsNodeId, MarketClearingPolicy, MaterialCatalog,
    MaterialCatalogDefinition, MaterialCircuitState, MemberLaborCapacityRow, MerchantHandling,
    MerchantHandlingCoefficient, MerchantRole, MonetaryBook, MonetaryCircuit, PriceDecision,
    PricePolicy, RecurringEconomy, ReplenishmentPolicy, RouteId, RouteStage, RouteStageCapacity,
    SellerOffer, SiteId, SiteLogisticsNode, StaffingMemberId, SupplierRoute, SupplierTransport,
    UnitId,
};

const SELLERS: u32 = 20_000;
const PERIODS: u64 = 2;

/// A seller's site, its id made from a `u32`.
fn seller(number: u32) -> SiteId {
    let mut bytes = [7_u8; 32];
    bytes[..4].copy_from_slice(&number.to_be_bytes());
    SiteId::from_bytes(bytes)
}

/// The corridor of the route that brings a seller's good to the seller before it, not the seller's own.
fn road(site: SiteId) -> CorridorId {
    let mut bytes = site.as_bytes();
    bytes[31] ^= 0xff;
    CorridorId::from_bytes(bytes)
}

fn good() -> GoodId {
    GoodId::from_bytes([2; 32])
}

fn unit() -> UnitId {
    UnitId::from_bytes([1; 32])
}

fn hours() -> UnitId {
    UnitId::from_bytes([3; 32])
}

fn dollars(whole: i128) -> Currency {
    Currency::from_micro_units(whole * 1_000_000)
}

fn location() -> EconomicLocation {
    "county:26163"
        .parse()
        .expect("the authored literal parses as the declared type")
}

/// The catalog: every seller is a merchant of the good, under a market policy that rests prices and steps
/// them down.
fn catalog(sites: &[SiteId]) -> MaterialCatalog {
    MaterialCatalog::try_new(MaterialCatalogDefinition {
        company_portfolios: None,
        company_payouts: vec![],
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: sites
            .iter()
            .map(|site| SiteLogisticsNode {
                site_id: *site,
                node_id: LogisticsNodeId::from_bytes(site.as_bytes()),
            })
            .collect(),
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        commodities: vec![CommodityDefinition {
            good_id: good(),
            unit_id: unit(),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        }],
        supplier_routes: sites
            .iter()
            .enumerate()
            .map(|(at, site)| SupplierRoute {
                buyer_site_id: *site,
                supplier_site_id: sites[(at + 1) % sites.len()],
                good_id: good(),
                unit_id: unit(),
                route_id: RouteId::from_bytes(site.as_bytes()),
                transport_kind: SupplierTransport::Staged,
            })
            .collect(),
        route_stages: sites
            .iter()
            .enumerate()
            .map(|(at, site)| RouteStage {
                route_id: RouteId::from_bytes(site.as_bytes()),
                stage_index: 0,
                from_node_id: LogisticsNodeId::from_bytes(sites[(at + 1) % sites.len()].as_bytes()),
                to_node_id: LogisticsNodeId::from_bytes(site.as_bytes()),
                travel_periods: 1,
                loss_ppm: 0,
            })
            .collect(),
        merchants: sites
            .iter()
            .map(|site| MerchantHandling {
                site_id: *site,
                location: location(),
                role: MerchantRole::Retail,
                capacity_id: CorridorId::from_bytes(site.as_bytes()),
                labor_unit_id: hours(),
            })
            .collect(),
        handling_coefficients: sites
            .iter()
            .map(|site| MerchantHandlingCoefficient {
                site_id: *site,
                good_id: good(),
                unit_id: unit(),
                hours_per_unit: 1,
            })
            .collect(),
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
        market_clearing: Some(MarketClearingPolicy {
            paying_order: vec![(good(), unit())],
            household_wants: vec![],
            plans_from_spare_money: false,
            adjustments: vec![AdjustmentRule::RestingPrice, AdjustmentRule::GoodsStepDown],
        }),
    })
    .expect("the fixture catalog is valid")
}

/// The recurring rows: each seller posts a price that may move, restocks from the next seller and plans no
/// hours.
fn recurring(sites: &[SiteId]) -> RecurringEconomy {
    RecurringEconomy {
        households: vec![],
        household_stocks: vec![],
        household_purchases: vec![],
        offers: sites
            .iter()
            .map(|site| SellerOffer {
                site_id: *site,
                good_id: good(),
                unit_id: unit(),
                unit_price: dollars(3),
                pricing: PricePolicy::Responsive {
                    minimum: dollars(1),
                    maximum: dollars(9),
                    step: dollars(1),
                    target_stock: 0,
                },
            })
            .collect(),
        replenishment: sites
            .iter()
            .enumerate()
            .map(|(at, site)| ReplenishmentPolicy {
                buyer_site_id: *site,
                supplier_site_id: sites[(at + 1) % sites.len()],
                good_id: good(),
                unit_id: unit(),
                target_stock: 0,
                maximum_purchase: 0,
                cash_floor: Currency::from_micro_units(0),
            })
            .collect(),
        production: vec![],
        attendance: sites
            .iter()
            .map(|site| AttendancePlan {
                site_id: *site,
                unit_id: hours(),
                period: 1,
                planned_hours: 0,
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }
}

/// The opening state: each seller employs one member who offers no hours, posts a price that may move, and
/// buys the good from the next seller; one household is the payee of every wage.
fn state(sites: &[SiteId]) -> MaterialCircuitState {
    let owner = FinalDemandPrincipalId::from_bytes([9; 32]);
    let mut accounts = vec![CashAccount {
        id: AccountId::Household(owner),
        cash: dollars(1_000_000),
    }];
    accounts.extend(sites.iter().map(|site| CashAccount {
        id: AccountId::Site(*site),
        cash: dollars(5),
    }));
    let book = MonetaryBook::open(accounts).expect("the fixture opens");
    let costs =
        HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![]).expect("the fixture opens");
    let financial = FinancialInstitutions::empty();
    let recurring = recurring(sites);
    MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
            aid: AidBook::default(),
            household_time: HouseholdTimeAccounting::NotModeled,
            financial,
            member_labor: sites
                .iter()
                .flat_map(|site| {
                    (1..=PERIODS).map(move |period| MemberLaborCapacityRow {
                        member_id: StaffingMemberId::from_bytes(site.as_bytes()),
                        period,
                        available_hours: 0,
                    })
                })
                .collect(),
            costs,
            book,
            recurring: Some(Box::new(recurring)),
            employment: sites
                .iter()
                .map(|site| EmploymentTerms {
                    member_id: StaffingMemberId::from_bytes(site.as_bytes()),
                    site_id: *site,
                    unit_id: hours(),
                    payee: owner,
                    compensation: LaborCompensation::Wage(dollars(1)),
                })
                .collect(),
        })),
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: sites
            .iter()
            .map(|site| RouteStageCapacity {
                route_id: RouteId::from_bytes(site.as_bytes()),
                stage_index: 0,
                corridor_id: road(*site),
            })
            .collect(),
        inventory: vec![],
        orders: vec![],
        freight: vec![],
        corridor_capacities: sites
            .iter()
            .flat_map(|site| {
                [1_u64].into_iter().flat_map(move |period| {
                    [CorridorId::from_bytes(site.as_bytes()), road(*site)].map(|corridor_id| {
                        CorridorCapacity {
                            corridor_id,
                            period,
                            available_grams: 1_000_000,
                        }
                    })
                })
            })
            .collect(),
        capacities: vec![],
        labor: sites
            .iter()
            .flat_map(|site| {
                (1..=PERIODS).map(move |period| LaborCapacityRow {
                    site_id: *site,
                    unit_id: hours(),
                    period,
                    available: 0,
                })
            })
            .collect(),
        production_commitments: vec![],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: owner,
            location: location(),
        }],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    }
}

/// A guard against a square coming back: 20,000 sellers of one good close one period under the resting price
/// and the step down. It times nothing; it sees that the period closes, that each seller has a price receipt
/// and that the money is the same.
#[test]
fn a_market_of_many_sellers_closes_with_the_step_down_and_the_rest() {
    let sites: Vec<SiteId> = (0..SELLERS).map(seller).collect();
    let catalog = catalog(&sites);
    let opening = state(&sites);
    let money = |state: &MaterialCircuitState| {
        let CircuitAccounting::Monetary(economy) = &state.accounting else {
            panic!("the fixture is monetary")
        };
        economy
            .book
            .total_cash_and_reserves()
            .expect("the book totals")
    };
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the period closes");
    assert_eq!(
        closed.prices.len(),
        usize::try_from(SELLERS).expect("a small count"),
        "a price receipt for each seller"
    );
    assert!(
        closed
            .prices
            .iter()
            .all(|row| row.reason == PriceDecision::Hold),
        "an idle seller rests"
    );
    assert_eq!(
        money(&closed.state),
        money(&opening),
        "the money is the same"
    );
}
