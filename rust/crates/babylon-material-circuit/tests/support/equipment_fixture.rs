use babylon_material_circuit::EquipmentPosition;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::MaterialCatalog;
fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}
fn site() -> SiteId {
    SiteId::from_bytes([1; 32])
}
fn process() -> ProcessId {
    ProcessId::from_bytes([1; 32])
}
fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([9; 32])
}
fn good(n: u8) -> GoodId {
    GoodId::from_bytes([n; 32])
}
fn unit() -> UnitId {
    UnitId::from_bytes([7; 32])
}
fn hours() -> UnitId {
    UnitId::from_bytes([8; 32])
}
fn definition() -> EquipmentDefinitionId {
    EquipmentDefinitionId::from_bytes([1; 32])
}
fn opening_assets() -> (MonetaryBook, HistoricalCostBook) {
    let book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(site()),
            cash: money(100),
        },
        CashAccount {
            id: AccountId::Household(household()),
            cash: money(0),
        },
    ])
    .expect("the fixture opens the authored source");
    let stock_values = [20, 6, 6, 0]
        .into_iter()
        .enumerate()
        .map(|(n, amount)| StockCarryingValue {
            owner: AccountId::Site(site()),
            good_id: good(u8::try_from(n + 1).expect("the fixture value fits the target range")),
            unit_id: unit(),
            amount: money(amount),
        })
        .collect();
    let costs = HistoricalCostBook::open(&book, stock_values, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    (book, costs)
}
fn opening_capacity() -> (CapacitySupply, EquipmentPosition) {
    let policy = CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
        processes: RollingProcessSupply::Equipment(Box::new(ProductiveEquipment {
            definitions: vec![EquipmentDefinition {
                id: definition(),
                equipment_good_id: good(1),
                equipment_unit_id: unit(),
                batches_per_unit_per_period: 2,
                service_batches_per_unit: 3,
                installation_labor_unit_id: hours(),
                installation_hours_per_unit: 3,
            }],
            bindings: vec![EquipmentBinding {
                process_id: process(),
                site_id: site(),
                definition_id: definition(),
            }],
            installation_inputs: vec![InstallationInput {
                definition_id: definition(),
                good_id: good(2),
                unit_id: unit(),
                quantity_per_equipment_unit: 2,
            }],
            installation_policies: vec![InstallationPolicy {
                process_id: process(),
                target: InstallationTarget::FixedUnits(1),
                maximum_started_units_per_period: 1,
                maximum_hours_per_period: 2,
            }],
            investment_policies: vec![],
        })),
        shared: vec![],
    }));
    (policy, EquipmentPosition::default())
}
fn opening_accounting(
    book: MonetaryBook,
    costs: HistoricalCostBook,
    schedules: &[LaborCapacityRow],
) -> CircuitAccounting {
    CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
        aid: AidBook::default(),

        household_time: HouseholdTimeAccounting::NotModeled,
        book,
        costs,
        financial: FinancialInstitutions::empty(),
        recurring: None,
        member_labor: schedules
            .iter()
            .map(|r| MemberLaborCapacityRow {
                member_id: StaffingMemberId::from_bytes([1; 32]),
                period: r.period,
                available_hours: r.available,
            })
            .collect(),
        employment: vec![EmploymentTerms {
            member_id: StaffingMemberId::from_bytes([1; 32]),
            site_id: site(),
            unit_id: hours(),
            payee: household(),
            compensation: LaborCompensation::Wage(money(2)),
        }],
    }))
}
fn opening() -> (MaterialCatalog, MaterialCircuitState) {
    let (book, costs) = opening_assets();
    let (capacity_policy, equipment) = opening_capacity();
    let schedules: Vec<_> = [0, 2, 1, 2, 1, 0, 0, 0]
        .into_iter()
        .enumerate()
        .map(|(n, available)| LaborCapacityRow {
            site_id: site(),
            unit_id: hours(),
            period: u64::try_from(n + 1).expect("the fixture value fits the target range"),
            available,
        })
        .collect();
    let catalog = MaterialCatalog {
        capacity_policy,
        site_logistics_nodes: vec![SiteLogisticsNode {
            site_id: site(),
            node_id: LogisticsNodeId::from_bytes([1; 32]),
        }],
        process_outputs: vec![ProcessOutput {
            site_id: site(),
            process_id: process(),
            good_id: good(4),
            unit_id: unit(),
            quantity_per_batch: 1,
        }],
        input_coefficients: vec![InputOutputCoefficient {
            process_id: process(),
            good_id: good(3),
            unit_id: unit(),
            quantity_per_batch: 1,
        }],
        labor_coefficients: vec![LaborCoefficient {
            process_id: process(),
            unit_id: hours(),
            quantity_per_batch: 1,
        }],
        commodities: (1..=4)
            .map(|n| CommodityDefinition {
                good_id: good(n),
                unit_id: unit(),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
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
        accounting: opening_accounting(book, costs, &schedules),
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: [1, 2, 3, 0]
            .into_iter()
            .enumerate()
            .map(|(n, quantity)| InventoryRow {
                site_id: site(),
                good_id: good(u8::try_from(n + 1).expect("the fixture value fits the target range")),
                unit_id: unit(),
                quantity,
            })
            .collect(),
        orders: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![CapacityRow {
            site_id: site(),
            process_id: process(),
            period: 1,
            available_batches: 0,
        }],
        labor: schedules,
        production_commitments: vec![],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
        }],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: babylon_material_circuit::CapacityReservations {
            equipment,
            future: vec![],
        },
    };
    (
        MaterialCatalog::try_new(catalog).expect("the authored fixture catalog is valid"),
        state,
    )
}
fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        panic!("paid")
    };
    e
}
fn economy_mut(state: &mut MaterialCircuitState) -> &mut MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    e
}
fn equipment(catalog: &MaterialCatalog) -> &ProductiveEquipment {
    let CapacitySupply::Rolling(s) = &catalog.capacity_policy else {
        panic!("rolling")
    };
    let RollingProcessSupply::Equipment(e) = &s.processes else {
        panic!("equipment")
    };
    e
}
fn position(state: &MaterialCircuitState) -> &EquipmentPosition {
    &state.capacity_reservations.equipment
}
fn position_mut(state: &mut MaterialCircuitState) -> &mut EquipmentPosition {
    &mut state.capacity_reservations.equipment
}
/// Rebuild one catalog with a changed equipment definition set.
fn rebuild(
    catalog: &MaterialCatalog,
    mutate: impl FnOnce(&mut ProductiveEquipment),
) -> MaterialCatalog {
    let CapacitySupply::Rolling(supply) = &catalog.capacity_policy else {
        panic!("rolling")
    };
    let RollingProcessSupply::Equipment(existing) = &supply.processes else {
        panic!("equipment")
    };
    let mut content = (**existing).clone();
    mutate(&mut content);
    let mut rebuilt = catalog.clone();
    rebuilt.capacity_policy = CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
        processes: RollingProcessSupply::Equipment(Box::new(content)),
        shared: supply.shared.clone(),
    }));
    rebuilt.catalog_digest = [0; 32];
    MaterialCatalog::try_new(rebuilt).expect("the rebuilt fixture catalog is valid")
}
fn equipment_cost(state: &MaterialCircuitState) -> Currency {
    economy(state)
        .costs
        .snapshot()
        .equipment
        .iter()
        .fold(money(0), |sum, r| {
            sum.checked_add(r.amount)
                .expect("the fixture arithmetic stays in range")
        })
}
fn stock_cost(state: &MaterialCircuitState, id: GoodId) -> Currency {
    economy(state)
        .costs
        .snapshot()
        .stocks
        .iter()
        .find(|r| r.owner == AccountId::Site(site()) && r.good_id == id)
        .expect("the fixture holds the searched element")
        .amount
}
fn configure_investment(
    catalog: &mut MaterialCatalog,
    state: &mut MaterialCircuitState,
    cash: i128,
    retained: i128,
) {
    configure_investment_supply(catalog, state);
    let seller = SiteId::from_bytes([2; 32]);
    let e = economy_mut(state);
    e.book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(site()),
            cash: money(cash),
        },
        CashAccount {
            id: AccountId::Site(seller),
            cash: money(0),
        },
        CashAccount {
            id: AccountId::Household(household()),
            cash: money(0),
        },
    ])
    .expect("the fixture opens the authored source");
    let mut stocks = e.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.good_id == good(1))
        .expect("the fixture holds the searched element")
        .amount = money(0);
    stocks.push(StockCarryingValue {
        owner: AccountId::Site(seller),
        good_id: good(1),
        unit_id: unit(),
        amount: money(24),
    });
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    let mut costs = e.costs.snapshot();
    let account = costs
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .expect("the fixture holds the searched element");
    account.opening_capital = account
        .opening_capital
        .checked_sub(money(retained))
        .expect("the fixture arithmetic stays in range");
    account.retained_earnings = money(retained);
    e.costs =
        HistoricalCostBook::from_snapshot(costs).expect("the snapshot admits the derived value");
    e.recurring = Some(Box::new(RecurringEconomy {
        service_inputs: vec![],
        households: vec![],
        household_stocks: vec![],
        household_needs: vec![],
        household_purchases: vec![],
        offers: vec![SellerOffer {
            site_id: seller,
            good_id: good(1),
            unit_id: unit(),
            unit_price: money(20),
            pricing: PricePolicy::Fixed,
        }],
        replenishment: vec![],
        production: vec![ProductionDemandPolicy {
            process_id: process(),
            site_id: site(),
            output_buffer: 2,
            planned_batches: 2,
        }],
        attendance: vec![AttendancePlan {
            site_id: site(),
            unit_id: hours(),
            period: 1,
            planned_hours: 0,
        }],
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
}
fn configure_investment_supply(catalog: &mut MaterialCatalog, state: &mut MaterialCircuitState) {
    let seller = SiteId::from_bytes([2; 32]);
    let route = RouteId::from_bytes([2; 32]);
    let corridor = CorridorId::from_bytes([2; 32]);
    catalog.site_logistics_nodes.push(SiteLogisticsNode {
        site_id: seller,
        node_id: LogisticsNodeId::from_bytes([2; 32]),
    });
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(1))
        .expect("the fixture holds the searched element")
        .quantity = 0;
    state.inventory.push(InventoryRow {
        site_id: seller,
        good_id: good(1),
        unit_id: unit(),
        quantity: 2,
    });
    catalog.supplier_routes.push(SupplierRoute {
        buyer_site_id: site(),
        supplier_site_id: seller,
        good_id: good(1),
        unit_id: unit(),
        route_id: route,
        transport_kind: SupplierTransport::Staged,
    });
    catalog.route_stages.push(RouteStage {
        route_id: route,
        stage_index: 0,
        from_node_id: LogisticsNodeId::from_bytes([2; 32]),
        to_node_id: LogisticsNodeId::from_bytes([1; 32]),
        travel_periods: 1,
        loss_ppm: 0,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: route,
        stage_index: 0,
        corridor_id: corridor,
    });
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id: corridor,
        period: 1,
        available_grams: 10,
    });
    let CapacitySupply::Rolling(supply) = &mut catalog.capacity_policy else {
        panic!("rolling")
    };
    supply.shared.push(SharedCapacitySupply {
        corridor_id: corridor,
        grams_per_period: 10,
    });
    *catalog = rebuild(catalog, |content| {
        content.investment_policies = vec![InvestmentPolicy {
            process_id: process(),
            supplier_site_id: seller,
            replacement_target_units: 1,
            maximum_installed_units: 2,
            maximum_purchase_per_period: 1,
            expansion_earnings_fraction_bps: 10000,
            cash_floor: money(0),
        }];
    });
}
fn configure_output_quote(state: &mut MaterialCircuitState) {
    let period = state.period;
    economy_mut(state).recurring = Some(Box::new(RecurringEconomy {
        service_inputs: vec![],
        households: vec![],
        household_stocks: vec![],
        household_needs: vec![],
        household_purchases: vec![],
        replenishment: vec![],
        offers: vec![SellerOffer {
            site_id: site(),
            good_id: good(4),
            unit_id: unit(),
            unit_price: money(3),
            pricing: PricePolicy::Responsive {
                minimum: money(1),
                maximum: money(20),
                step: money(1),
                target_stock: 0,
            },
        }],
        production: vec![ProductionDemandPolicy {
            process_id: process(),
            site_id: site(),
            output_buffer: 2,
            planned_batches: 2,
        }],
        attendance: vec![AttendancePlan {
            site_id: site(),
            unit_id: hours(),
            period,
            planned_hours: 2,
        }],
        last_household_admission_period: period - 1,
        last_household_consumption_period: period - 1,
    }));
}
