//! Opening data copied from the engine's eight-period control; transitions use the real engine.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::*;

fn site(id: u8) -> SiteId {
    SiteId::from_bytes([id; 32])
}
fn node(id: u8) -> LogisticsNodeId {
    LogisticsNodeId::from_bytes([id; 32])
}
fn good(id: u8) -> GoodId {
    GoodId::from_bytes([id; 32])
}
fn process(id: u8) -> ProcessId {
    ProcessId::from_bytes([id; 32])
}
fn corridor(id: u8) -> CorridorId {
    CorridorId::from_bytes([id; 32])
}
fn route(id: u8) -> RouteId {
    RouteId::from_bytes([id; 32])
}
fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([1; 32])
}
fn units() -> UnitId {
    UnitId::from_bytes([1; 32])
}
fn hours() -> UnitId {
    UnitId::from_bytes([2; 32])
}
fn money(value: i128) -> Currency {
    Currency::from_micro_units(value)
}
fn inventory(owner: u8, commodity: u8, quantity: u64) -> InventoryRow {
    InventoryRow {
        site_id: site(owner),
        good_id: good(commodity),
        unit_id: units(),
        quantity,
    }
}

pub(super) fn opening() -> MaterialCircuitState {
    let offers = [(1, 1, 1), (2, 2, 3), (3, 2, 4)]
        .into_iter()
        .map(|(owner, commodity, price)| SellerOffer {
            site_id: site(owner),
            good_id: good(commodity),
            unit_id: units(),
            unit_price: money(price),
            pricing: PricePolicy::Fixed,
        })
        .collect();
    let recurring = RecurringEconomy {
        households: vec![HouseholdCohort {
            principal_id: household(),
            households: 2,
            persons: 4,
        }],
        household_stocks: vec![HouseholdStock {
            principal_id: household(),
            good_id: good(2),
            unit_id: units(),
            quantity: 8,
        }],
        household_needs: vec![HouseholdNeed {
            principal_id: household(),
            good_id: good(2),
            unit_id: units(),
            units_per_person: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household(),
            retailer_site_id: site(3),
            good_id: good(2),
            unit_id: units(),
            target_closing_stock: 8,
            maximum_purchase: 4,
            enabled: true,
        }],
        offers,
        replenishment: [(2, 1, 1), (3, 2, 2)]
            .into_iter()
            .map(|(buyer, supplier, commodity)| ReplenishmentPolicy {
                buyer_site_id: site(buyer),
                supplier_site_id: site(supplier),
                good_id: good(commodity),
                unit_id: units(),
                target_stock: 4,
                maximum_purchase: 4,
                cash_floor: money(0),
            })
            .collect(),
        production: [1, 2]
            .into_iter()
            .map(|owner| ProductionDemandPolicy {
                process_id: process(owner),
                site_id: site(owner),
                output_buffer: 0,
                planned_batches: 4,
            })
            .collect(),
        attendance: [(1, 4), (2, 8), (3, 4)]
            .into_iter()
            .map(|(owner, planned_hours)| AttendancePlan {
                site_id: site(owner),
                unit_id: hours(),
                period: 1,
                planned_hours,
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    };
    MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(MonetaryCircuit {
            recurring: Some(Box::new(recurring)),
            book: MonetaryBook::open(vec![
                CashAccount {
                    id: AccountId::Site(site(1)),
                    cash: money(4),
                },
                CashAccount {
                    id: AccountId::Site(site(2)),
                    cash: money(12),
                },
                CashAccount {
                    id: AccountId::Site(site(3)),
                    cash: money(8),
                },
                CashAccount {
                    id: AccountId::Household(household()),
                    cash: money(0),
                },
            ])
            .unwrap(),
            employment: [1, 2, 3]
                .into_iter()
                .map(|owner| EmploymentTerms {
                    site_id: site(owner),
                    unit_id: hours(),
                    payee: household(),
                    hourly_rate: money(1),
                })
                .collect(),
        }),
        site_logistics_nodes: [1, 2, 3]
            .into_iter()
            .map(|owner| SiteLogisticsNode {
                site_id: site(owner),
                node_id: node(owner),
            })
            .collect(),
        process_outputs: [1, 2]
            .into_iter()
            .map(|owner| ProcessOutput {
                process_id: process(owner),
                site_id: site(owner),
                good_id: good(owner),
                unit_id: units(),
                quantity_per_batch: 1,
            })
            .collect(),
        input_coefficients: [1, 2]
            .into_iter()
            .map(|owner| InputOutputCoefficient {
                process_id: process(owner),
                good_id: good(owner - 1),
                unit_id: units(),
                quantity_per_batch: 1,
            })
            .collect(),
        labor_coefficients: [(1, 1), (2, 2)]
            .into_iter()
            .map(|(owner, quantity_per_batch)| LaborCoefficient {
                process_id: process(owner),
                unit_id: hours(),
                quantity_per_batch,
            })
            .collect(),
        freight_mass_coefficients: [0, 1, 2]
            .into_iter()
            .map(|commodity| FreightMassCoefficient {
                good_id: good(commodity),
                unit_id: units(),
                grams_per_unit: 1,
            })
            .collect(),
        supplier_routes: [(1, 2, 1), (2, 3, 2)]
            .into_iter()
            .map(|(supplier, buyer, commodity)| SupplierRoute {
                buyer_site_id: site(buyer),
                supplier_site_id: site(supplier),
                good_id: good(commodity),
                unit_id: units(),
                route_id: route(supplier),
                transport_kind: SupplierTransport::Staged,
            })
            .collect(),
        route_stages: [(1, 2), (2, 3)]
            .into_iter()
            .map(|(source, destination)| RouteStage {
                route_id: route(source),
                stage_index: 0,
                from_node_id: node(source),
                to_node_id: node(destination),
                travel_periods: 1,
                loss_ppm: 0,
            })
            .collect(),
        route_stage_capacities: [1, 2]
            .into_iter()
            .map(|id| RouteStageCapacity {
                route_id: route(id),
                stage_index: 0,
                corridor_id: corridor(id),
            })
            .collect(),
        inventory: vec![inventory(1, 0, 40), inventory(2, 1, 4), inventory(3, 2, 4)],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: (1..=9)
            .flat_map(|period| {
                [1, 2, 3].into_iter().map(move |id| CorridorCapacity {
                    corridor_id: corridor(id),
                    period,
                    available_grams: 4,
                })
            })
            .collect(),
        capacities: (1..=9)
            .flat_map(|period| {
                [1, 2].into_iter().map(move |owner| CapacityRow {
                    process_id: process(owner),
                    site_id: site(owner),
                    period,
                    available_batches: 4,
                })
            })
            .collect(),
        labor: (1..=9)
            .flat_map(|period| {
                [(1, 4), (2, 8), (3, 4)]
                    .into_iter()
                    .map(move |(owner, available)| LaborCapacityRow {
                        site_id: site(owner),
                        unit_id: hours(),
                        period,
                        available,
                    })
            })
            .collect(),
        production_commitments: [1, 2]
            .into_iter()
            .map(|owner| ProductionCommitment {
                process_id: process(owner),
                site_id: site(owner),
                period: 1,
                planned_batches: 4,
            })
            .collect(),
        merchants: vec![MerchantHandling {
            site_id: site(3),
            county_geoid: *b"26163",
            role: MerchantRole::Retail,
            capacity_id: corridor(3),
            labor_unit_id: hours(),
        }],
        handling_coefficients: vec![MerchantHandlingCoefficient {
            site_id: site(3),
            good_id: good(2),
            unit_id: units(),
            hours_per_unit: 1,
        }],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            county_geoid: *b"26163",
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}
