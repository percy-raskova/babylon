//! Leaf implementation for the parent module; public paths stay on the parent.

use babylon_material_circuit::{
    decode_material_circuit_state, AccountId, AidBook, CapacityReservations, CapacityRow,
    CapacitySupply, CashAccount, CircuitAccounting, CommodityDefinition, CommodityKind,
    EmploymentTerms, FinalDemandPrincipal, FinalDemandPrincipalId, GoodId, HistoricalCostBook,
    InputOutputCoefficient, InventoryRow, LaborCapacityRow, LaborCoefficient, LogisticsNodeId,
    MaterialCatalog, MaterialCircuitError, MaterialCircuitState, MaterialPurchase, MonetaryBook,
    MonetaryCircuit, OrderId, ProcessId, ProcessOutput, ProductionCommitment, ServiceConnection,
    ServiceOrder, ServiceStage, SiteId, SiteLogisticsNode, StockCarryingValue, UnitId,
};

use babylon_kernel::currency::Currency;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::StaffingMemberId;

pub(crate) fn site(n: u8) -> SiteId {
    SiteId::from_bytes([n; 32])
}

pub(crate) fn good(n: u8) -> GoodId {
    GoodId::from_bytes([n; 32])
}

pub(crate) fn unit(n: u8) -> UnitId {
    UnitId::from_bytes([n; 32])
}

pub(crate) fn process(n: u8) -> ProcessId {
    ProcessId::from_bytes([n; 32])
}

pub(crate) fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([9; 32])
}

pub(crate) fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
pub(crate) fn opening() -> (MaterialCatalog, MaterialCircuitState) {
    let inventory = vec![
        InventoryRow {
            site_id: site(1),
            good_id: good(4),
            unit_id: unit(4),
            quantity: 1,
        },
        InventoryRow {
            site_id: site(3),
            good_id: good(3),
            unit_id: unit(3),
            quantity: 0,
        },
    ];
    let book = MonetaryBook::open(
        (1..=3)
            .map(|n| CashAccount {
                id: AccountId::Site(site(n)),
                cash: money(10),
            })
            .chain([CashAccount {
                id: AccountId::Household(household()),
                cash: money(0),
            }])
            .collect(),
    )
    .expect("the fixture opens the authored source");
    let costs = HistoricalCostBook::open(
        &book,
        inventory
            .iter()
            .map(|r| StockCarryingValue {
                owner: AccountId::Site(r.site_id),
                good_id: r.good_id,
                unit_id: r.unit_id,
                amount: money(0),
            })
            .collect(),
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    let catalog = MaterialCatalog {
        capacity_policy: CapacitySupply::FiniteSchedule,
        commodities: vec![
            CommodityDefinition {
                good_id: good(1),
                unit_id: unit(1),
                kind: CommodityKind::PeriodService {
                    stage: ServiceStage::UtilityProvision,
                },
            },
            CommodityDefinition {
                good_id: good(2),
                unit_id: unit(2),
                kind: CommodityKind::PeriodService {
                    stage: ServiceStage::LocalServiceProvision,
                },
            },
            CommodityDefinition {
                good_id: good(3),
                unit_id: unit(3),
                kind: CommodityKind::Storable {
                    grams_per_unit: 100,
                },
            },
            CommodityDefinition {
                good_id: good(4),
                unit_id: unit(4),
                kind: CommodityKind::Storable {
                    grams_per_unit: 100,
                },
            },
        ],
        site_logistics_nodes: (1..=3)
            .map(|n| SiteLogisticsNode {
                site_id: site(n),
                node_id: LogisticsNodeId::from_bytes([n; 32]),
            })
            .collect(),
        process_outputs: (1..=3)
            .map(|n| ProcessOutput {
                process_id: process(n),
                site_id: site(n),
                good_id: good(n),
                unit_id: unit(n),
                quantity_per_batch: 1,
            })
            .collect(),
        input_coefficients: vec![
            InputOutputCoefficient {
                process_id: process(1),
                good_id: good(4),
                unit_id: unit(4),
                quantity_per_batch: 1,
            },
            InputOutputCoefficient {
                process_id: process(2),
                good_id: good(1),
                unit_id: unit(1),
                quantity_per_batch: 1,
            },
            InputOutputCoefficient {
                process_id: process(3),
                good_id: good(1),
                unit_id: unit(1),
                quantity_per_batch: 1,
            },
            InputOutputCoefficient {
                process_id: process(3),
                good_id: good(2),
                unit_id: unit(2),
                quantity_per_batch: 1,
            },
        ],
        labor_coefficients: (1..=3)
            .map(|n| LaborCoefficient {
                process_id: process(n),
                unit_id: unit(9),
                quantity_per_batch: 1,
            })
            .collect(),
        supplier_routes: vec![],
        route_stages: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
        catalog_digest: [0; 32],
    };
    let state = MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
            aid: AidBook::default(),

            household_time: HouseholdTimeAccounting::NotModeled,
            financial: FinancialInstitutions::empty(),
            member_labor: (1..=3)
                .map(|n| babylon_material_circuit::MemberLaborCapacityRow {
                    member_id: StaffingMemberId::from_bytes(site(n).as_bytes()),
                    period: 1,
                    available_hours: if n == 1 { 2 } else { 1 },
                })
                .collect(),
            costs,
            book,
            recurring: None,
            employment: (1..=3)
                .map(|n| EmploymentTerms {
                    member_id: StaffingMemberId::from_bytes((site(n)).as_bytes()),
                    site_id: site(n),
                    unit_id: unit(9),
                    payee: household(),
                    compensation: LaborCompensation::Wage(money(1)),
                })
                .collect(),
        })),
        service_connections: vec![
            ServiceConnection {
                provider_site_id: site(1),
                buyer: AccountId::Site(site(2)),
                good_id: good(1),
                unit_id: unit(1),
            },
            ServiceConnection {
                provider_site_id: site(1),
                buyer: AccountId::Site(site(3)),
                good_id: good(1),
                unit_id: unit(1),
            },
            ServiceConnection {
                provider_site_id: site(2),
                buyer: AccountId::Site(site(3)),
                good_id: good(2),
                unit_id: unit(2),
            },
        ],
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory,
        orders: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: (1..=3)
            .map(|n| CapacityRow {
                process_id: process(n),
                site_id: site(n),
                period: 1,
                available_batches: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        labor: (1..=3)
            .map(|n| LaborCapacityRow {
                site_id: site(n),
                unit_id: unit(9),
                period: 1,
                available: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        production_commitments: (1..=3)
            .map(|n| ProductionCommitment {
                process_id: process(n),
                site_id: site(n),
                period: 1,
                planned_batches: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
        }],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    (
        MaterialCatalog::try_new(catalog).expect("the authored fixture catalog is valid"),
        state,
    )
}

pub(crate) fn funded(
    catalog: &MaterialCatalog,
    mut state: MaterialCircuitState,
) -> MaterialCircuitState {
    for (id, provider, buyer, commodity, price) in
        [(1, 1, 2, 1, 2), (2, 1, 3, 1, 2), (3, 2, 3, 2, 3)]
    {
        state = babylon_material_circuit::admit_material_purchase(
            catalog,
            &state,
            MaterialPurchase::Service(ServiceOrder {
                order_id: OrderId::from_bytes([id; 32]),
                performance_period: 1,
                provider_site_id: site(provider),
                buyer: AccountId::Site(site(buyer)),
                good_id: good(commodity),
                unit_id: unit(commodity),
                quantity: 1,
            }),
            money(price),
        )
        .expect("the fixture admits the authored purchase")
        .0;
    }
    state
}

fn reseal(catalog: MaterialCatalog, mutate: impl FnOnce(&mut MaterialCatalog)) -> MaterialCatalog {
    let mut catalog = catalog;
    mutate(&mut catalog);
    catalog.catalog_digest = [0; 32];
    MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid")
}

#[test]
pub(crate) fn native_services_feed_later_stages_without_freight_or_stored_service() {
    let (catalog, mut state) = opening();
    state.inventory[0].quantity = 2;
    let state = funded(&catalog, state);
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        closed
            .production
            .iter()
            .map(|r| r.produced_batches)
            .collect::<Vec<_>>(),
        vec![2, 1, 1]
    );
    assert_eq!(closed.dispatches.len(), 0);
    assert_eq!(closed.handling.len(), 0);
    assert_eq!(closed.state.freight.len(), 0);
    assert_eq!(
        closed
            .state
            .inventory
            .iter()
            .filter(|r| r.good_id == good(3))
            .map(|r| r.quantity)
            .sum::<u64>(),
        1
    );
    assert!(closed
        .state
        .inventory
        .iter()
        .all(|r| r.good_id != good(1) && r.good_id != good(2)));
    assert!(closed
        .service_performance
        .iter()
        .all(|r| r.performed_quantity == 1 && r.used_quantity == 1 && r.unused_quantity == 0));
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        panic!()
    };
    assert_eq!(
        economy
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(30)
    );
    assert_eq!(
        economy
            .costs
            .snapshot()
            .stocks
            .iter()
            .find(|r| r.good_id == good(3))
            .expect("the fixture holds the searched element")
            .amount,
        money(6)
    );
    assert_eq!(closed.state.service_orders.len(), 0);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &closed.state)
        .expect("the canonical material state encodes");
    assert_eq!(
        decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode"),
        closed.state
    );
}

#[test]
pub(crate) fn absent_utility_constrains_services_and_goods_without_spending_work_twice() {
    let (catalog, mut state) = opening();
    state.inventory[0].quantity = 0;
    let funded = funded(&catalog, state);
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &funded)
        .expect("the authored material state advances one period");
    assert!(closed.production.iter().all(|r| r.produced_batches == 0));
    assert!(closed
        .service_performance
        .iter()
        .all(|r| r.expired_quantity == 1 && r.performed_quantity == 0));
    assert!(closed.labor_use.iter().all(|r| r.used_hours == 0));
}

#[test]
pub(crate) fn a_service_dependency_cycle_and_durable_service_stock_are_refused_atomically() {
    let (catalog, state) = opening();
    let catalog = reseal(catalog, |catalog| {
        catalog.input_coefficients.push(InputOutputCoefficient {
            process_id: process(1),
            good_id: good(2),
            unit_id: unit(2),
            quantity_per_batch: 1,
        });
    });
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::ServiceInvariant)
    );
    let (catalog, mut state) = opening();
    state.inventory.push(InventoryRow {
        site_id: site(1),
        good_id: good(1),
        unit_id: unit(1),
        quantity: 0,
    });
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::ServiceInvariant)
    );
}
