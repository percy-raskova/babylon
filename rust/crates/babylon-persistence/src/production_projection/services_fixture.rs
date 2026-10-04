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

fn accounting(inventory: &[InventoryRow]) -> CircuitAccounting {
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
        vec![],
        vec![],
    )
    .unwrap();
    CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
        aid: babylon_material_circuit::AidBook::default(),
        household_time: babylon_material_circuit::HouseholdTimeAccounting::NotModeled,
        financial: babylon_material_circuit::FinancialInstitutions::empty(),
        member_labor: (1..=3)
            .map(|n| babylon_material_circuit::MemberLaborCapacityRow {
                member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                    site(n).as_bytes(),
                ),
                period: 1,
                available_hours: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        costs,
        book,
        recurring: None,
        employment: (1..=3)
            .map(|n| EmploymentTerms {
                member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                    (site(n)).as_bytes(),
                ),
                site_id: site(n),
                unit_id: unit(9),
                payee: household(),
                compensation: babylon_material_circuit::LaborCompensation::Wage(money(1)),
            })
            .collect(),
    }))
}
fn commodities() -> Vec<CommodityDefinition> {
    vec![
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
    ]
}
fn service_connections() -> Vec<ServiceConnection> {
    vec![
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
    ]
}
fn input_coefficients() -> Vec<InputOutputCoefficient> {
    vec![
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
    ]
}

pub(super) fn opening() -> MaterialCircuitState {
    let inventory = vec![
        InventoryRow {
            site_id: site(1),
            good_id: good(4),
            unit_id: unit(4),
            quantity: 2,
        },
        InventoryRow {
            site_id: site(3),
            good_id: good(3),
            unit_id: unit(3),
            quantity: 0,
        },
    ];
    MaterialCircuitState {
        capacity_supply: CapacitySupply::FiniteSchedule,
        period: 1,
        accounting: accounting(&inventory),
        commodities: commodities(),
        service_connections: service_connections(),
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
        input_coefficients: input_coefficients(),
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
            location: "county:26163".parse().unwrap(),
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}
pub(super) fn funded(mut state: MaterialCircuitState) -> MaterialCircuitState {
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

pub(super) fn recurring(mut state: MaterialCircuitState) -> MaterialCircuitState {
    state.inventory[0].quantity = 3;
    state.capacities[0].available_batches = 4;
    state.capacities[1].available_batches = 3;
    state.labor[0].available = 3;
    state.labor[1].available = 2;
    state.production_commitments[0].planned_batches = 3;
    state.production_commitments[1].planned_batches = 2;
    state.service_connections.push(ServiceConnection {
        provider_site_id: site(2),
        buyer: AccountId::Household(household()),
        good_id: good(2),
        unit_id: unit(2),
    });
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!()
    };
    e.recurring = Some(Box::new(RecurringEconomy {
        service_inputs: service_inputs(),
        households: vec![HouseholdCohort {
            kind: babylon_material_circuit::HouseholdKind::Ordinary,
            principal_id: household(),
            households: 1,
            persons: 1,
        }],
        household_stocks: vec![],
        household_needs: household_needs(),
        household_purchases: household_purchases(),
        offers: (1..=3)
            .map(|n| SellerOffer {
                site_id: site(n),
                good_id: good(n),
                unit_id: unit(n),
                unit_price: money(if n == 1 { 2 } else { 4 }),
                pricing: if n == 3 {
                    PricePolicy::Fixed
                } else {
                    PricePolicy::ServiceResponsive {
                        minimum: money(1),
                        maximum: money(10),
                        step: money(1),
                    }
                },
            })
            .collect(),
        replenishment: vec![],
        production: (1..=3)
            .map(|n| ProductionDemandPolicy {
                process_id: process(n),
                site_id: site(n),
                output_buffer: 0,
                planned_batches: if n == 1 {
                    3
                } else if n == 2 {
                    2
                } else {
                    1
                },
            })
            .collect(),
        attendance: (1..=3)
            .map(|n| AttendancePlan {
                site_id: site(n),
                unit_id: unit(9),
                period: 1,
                planned_hours: if n == 1 {
                    3
                } else if n == 2 {
                    2
                } else {
                    1
                },
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    for member in &mut e.member_labor {
        member.available_hours = state
            .labor
            .iter()
            .find(|r| r.site_id.as_bytes() == member.member_id.as_bytes())
            .unwrap()
            .available;
    }
    state
}

fn service_inputs() -> Vec<ServiceInputPolicy> {
    vec![
        ServiceInputPolicy {
            buyer_site_id: site(2),
            provider_site_id: site(1),
            good_id: good(1),
            unit_id: unit(1),
            quantity_per_period: 2,
            maximum_purchase: 2,
            cash_floor: money(0),
        },
        ServiceInputPolicy {
            buyer_site_id: site(3),
            provider_site_id: site(1),
            good_id: good(1),
            unit_id: unit(1),
            quantity_per_period: 1,
            maximum_purchase: 1,
            cash_floor: money(0),
        },
        ServiceInputPolicy {
            buyer_site_id: site(3),
            provider_site_id: site(2),
            good_id: good(2),
            unit_id: unit(2),
            quantity_per_period: 1,
            maximum_purchase: 1,
            cash_floor: money(0),
        },
    ]
}

fn household_needs() -> Vec<HouseholdNeed> {
    vec![HouseholdNeed {
        principal_id: household(),
        good_id: good(2),
        unit_id: unit(2),
        basis: babylon_material_circuit::HouseholdNeedBasis::Persons,
        units_per_basis: 1,
    }]
}

fn household_purchases() -> Vec<HouseholdPurchasePolicy> {
    vec![HouseholdPurchasePolicy {
        principal_id: household(),
        retailer_site_id: site(2),
        good_id: good(2),
        unit_id: unit(2),
        target_closing_stock: 0,
        maximum_purchase: 1,
        enabled: true,
    }]
}
