use babylon_kernel::currency::Currency;
use babylon_material_circuit::*;

fn site(n: u8) -> SiteId {
    SiteId::from_bytes([n; 32])
}
fn good(n: u8) -> GoodId {
    GoodId::from_bytes([n; 32])
}
fn unit(n: u8) -> UnitId {
    UnitId::from_bytes([n; 32])
}
fn process(n: u8) -> ProcessId {
    ProcessId::from_bytes([n; 32])
}
fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([9; 32])
}
fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}

fn opening() -> MaterialCircuitState {
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
    .unwrap();
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
    )
    .unwrap();
    MaterialCircuitState {
        capacity_supply: CapacitySupply::FiniteSchedule,
        period: 1,
        accounting: CircuitAccounting::Monetary(MonetaryCircuit {
            costs,
            book,
            recurring: None,
            employment: (1..=3)
                .map(|n| EmploymentTerms {
                    site_id: site(n),
                    unit_id: unit(9),
                    payee: household(),
                    hourly_rate: money(1),
                })
                .collect(),
        }),
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
        route_stage_capacities: vec![],
        inventory,
        orders: vec![],
        backlog: vec![],
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
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            county_geoid: *b"26163",
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}
fn funded(mut state: MaterialCircuitState) -> MaterialCircuitState {
    for (id, provider, buyer, commodity, price) in
        [(1, 1, 2, 1, 2), (2, 1, 3, 1, 2), (3, 2, 3, 2, 3)]
    {
        state = admit_material_purchase(
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
        .unwrap()
        .0;
    }
    state
}
#[test]
fn native_services_feed_later_stages_without_freight_or_stored_service() {
    let mut state = opening();
    state.inventory[0].quantity = 2;
    let state = funded(state);
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(
        closed
            .production
            .iter()
            .map(|r| r.produced_batches)
            .collect::<Vec<_>>(),
        vec![2, 1, 1]
    );
    assert!(closed.dispatches.is_empty());
    assert!(closed.handling.is_empty());
    assert!(closed.state.freight.is_empty());
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
    assert_eq!(economy.book.total_cash_and_reserves().unwrap(), money(30));
    assert_eq!(
        economy
            .costs
            .snapshot()
            .stocks
            .iter()
            .find(|r| r.good_id == good(3))
            .unwrap()
            .amount,
        money(6)
    );
    assert!(closed.state.service_orders.is_empty());
    let bytes = encode_material_circuit_state(&closed.state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), closed.state);
}
#[test]
fn absent_utility_constrains_services_and_goods_without_spending_work_twice() {
    let mut state = opening();
    state.inventory[0].quantity = 0;
    let closed = advance_material_circuit(&funded(state)).unwrap();
    assert!(closed.production.iter().all(|r| r.produced_batches == 0));
    assert!(closed
        .service_performance
        .iter()
        .all(|r| r.expired_quantity == 1 && r.performed_quantity == 0));
    assert!(closed.labor_use.iter().all(|r| r.used_hours == 0));
}
#[test]
fn a_service_dependency_cycle_and_durable_service_stock_are_refused_atomically() {
    let mut state = opening();
    state.input_coefficients.push(InputOutputCoefficient {
        process_id: process(1),
        good_id: good(2),
        unit_id: unit(2),
        quantity_per_batch: 1,
    });
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::ServiceInvariant)
    );
    let mut state = opening();
    state.inventory.push(InventoryRow {
        site_id: site(1),
        good_id: good(1),
        unit_id: unit(1),
        quantity: 0,
    });
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::ServiceInvariant)
    );
}

#[path = "support/period_service_cases.rs"]
mod service_cases;
