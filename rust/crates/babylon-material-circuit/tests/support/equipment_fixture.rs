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
    .unwrap();
    let stock_values = [20, 6, 6, 0]
        .into_iter()
        .enumerate()
        .map(|(n, amount)| StockCarryingValue {
            owner: AccountId::Site(site()),
            good_id: good(u8::try_from(n + 1).unwrap()),
            unit_id: unit(),
            amount: money(amount),
        })
        .collect();
    let costs = HistoricalCostBook::open(&book, stock_values, vec![], vec![], vec![]).unwrap();
    (book, costs)
}
fn opening_capacity() -> CapacitySupply {
    CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
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
            cohorts: vec![],
            pending: vec![],
            installation_policies: vec![InstallationPolicy {
                process_id: process(),
                target: InstallationTarget::FixedUnits(1),
                maximum_started_units_per_period: 1,
                maximum_hours_per_period: 2,
            }],
            investment_policies: vec![],
        })),
        shared: vec![],
        future_reservations: vec![],
    }))
}
fn opening_accounting(
    book: MonetaryBook,
    costs: HistoricalCostBook,
    schedules: &[LaborCapacityRow],
) -> CircuitAccounting {
    CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
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
fn opening() -> MaterialCircuitState {
    let (book, costs) = opening_assets();
    let schedules: Vec<_> = [0, 2, 1, 2, 1, 0, 0, 0]
        .into_iter()
        .enumerate()
        .map(|(n, available)| LaborCapacityRow {
            site_id: site(),
            unit_id: hours(),
            period: u64::try_from(n + 1).unwrap(),
            available,
        })
        .collect();
    MaterialCircuitState {
        period: 1,
        capacity_supply: opening_capacity(),
        accounting: opening_accounting(book, costs, &schedules),
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
        inventory: [1, 2, 3, 0]
            .into_iter()
            .enumerate()
            .map(|(n, quantity)| InventoryRow {
                site_id: site(),
                good_id: good(u8::try_from(n + 1).unwrap()),
                unit_id: unit(),
                quantity,
            })
            .collect(),
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
            location: "county:26163".parse().unwrap(),
        }],
        service_connections: vec![],
        service_orders: vec![],
        supplier_routes: vec![],
        route_stages: vec![],
        route_stage_capacities: vec![],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
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
fn equipment(state: &MaterialCircuitState) -> &ProductiveEquipment {
    let CapacitySupply::Rolling(s) = &state.capacity_supply else {
        panic!("rolling")
    };
    let RollingProcessSupply::Equipment(e) = &s.processes else {
        panic!("equipment")
    };
    e
}
fn equipment_mut(state: &mut MaterialCircuitState) -> &mut ProductiveEquipment {
    let CapacitySupply::Rolling(s) = &mut state.capacity_supply else {
        panic!("rolling")
    };
    let RollingProcessSupply::Equipment(e) = &mut s.processes else {
        panic!("equipment")
    };
    e
}
fn equipment_cost(state: &MaterialCircuitState) -> Currency {
    economy(state)
        .costs
        .snapshot()
        .equipment
        .iter()
        .fold(money(0), |sum, r| sum.checked_add(r.amount).unwrap())
}
fn stock_cost(state: &MaterialCircuitState, id: GoodId) -> Currency {
    economy(state)
        .costs
        .snapshot()
        .stocks
        .iter()
        .find(|r| r.owner == AccountId::Site(site()) && r.good_id == id)
        .unwrap()
        .amount
}

fn configure_investment(state: &mut MaterialCircuitState, cash: i128, retained: i128) {
    configure_investment_supply(state);
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
    .unwrap();
    let mut stocks = e.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.good_id == good(1))
        .unwrap()
        .amount = money(0);
    stocks.push(StockCarryingValue {
        owner: AccountId::Site(seller),
        good_id: good(1),
        unit_id: unit(),
        amount: money(24),
    });
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![]).unwrap();
    let mut costs = e.costs.snapshot();
    let account = costs
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap();
    account.opening_capital = account
        .opening_capital
        .checked_sub(money(retained))
        .unwrap();
    account.retained_earnings = money(retained);
    e.costs = HistoricalCostBook::from_snapshot(costs).unwrap();
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

fn configure_investment_supply(state: &mut MaterialCircuitState) {
    let seller = SiteId::from_bytes([2; 32]);
    let route = RouteId::from_bytes([2; 32]);
    let corridor = CorridorId::from_bytes([2; 32]);
    state.site_logistics_nodes.push(SiteLogisticsNode {
        site_id: seller,
        node_id: LogisticsNodeId::from_bytes([2; 32]),
    });
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(1))
        .unwrap()
        .quantity = 0;
    state.inventory.push(InventoryRow {
        site_id: seller,
        good_id: good(1),
        unit_id: unit(),
        quantity: 2,
    });
    state.supplier_routes.push(SupplierRoute {
        buyer_site_id: site(),
        supplier_site_id: seller,
        good_id: good(1),
        unit_id: unit(),
        route_id: route,
        transport_kind: SupplierTransport::Staged,
    });
    state.route_stages.push(RouteStage {
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
    let CapacitySupply::Rolling(supply) = &mut state.capacity_supply else {
        panic!("rolling")
    };
    supply.shared.push(SharedCapacitySupply {
        corridor_id: corridor,
        grams_per_period: 10,
    });
    equipment_mut(state).investment_policies = vec![InvestmentPolicy {
        process_id: process(),
        supplier_site_id: seller,
        replacement_target_units: 1,
        maximum_installed_units: 2,
        maximum_purchase_per_period: 1,
        expansion_earnings_fraction_bps: 10000,
        cash_floor: money(0),
    }];
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
