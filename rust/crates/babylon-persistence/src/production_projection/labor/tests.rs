use babylon_material_circuit::{
    CapacityRow, CommodityDefinition, CommodityKind, GoodId, LaborCapacityRow, LaborCoefficient,
    LogisticsNodeId, ProcessOutput, ProductionCommitment, SiteLogisticsNode,
};
use babylon_tick::material_world::MaterialWorldRegister;

use super::super::ProductionProjectionError;
use super::projection;
use super::projection::{budgets, completed_totals};
use crate::michigan_economy;
use crate::production_observation::CompletedProductionLabor;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::{MaterialCatalog, MaterialCircuitState, ProcessId, SiteId, UnitId};
use babylon_tick::material_world;
use babylon_tick::material_world::MaterialTickReceipts;

type Parts = (MaterialCatalog, MaterialCircuitState);
type Pair = (
    MaterialCircuitState,
    MaterialCircuitState,
    MaterialTickReceipts,
    MaterialCatalog,
);

fn shared_opening() -> Parts {
    let site = SiteId::from_bytes([1; 32]);
    let labor_unit = UnitId::from_bytes([2; 32]);
    let mut catalog = babylon_material_circuit::MaterialCatalogDefinition {
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: vec![SiteLogisticsNode {
            site_id: site,
            node_id: LogisticsNodeId::from_bytes([3; 32]),
        }],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        commodities: [4, 5]
            .into_iter()
            .map(|id| CommodityDefinition {
                good_id: GoodId::from_bytes([id; 32]),
                unit_id: UnitId::from_bytes([6; 32]),
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
    };
    let mut state = MaterialCircuitState {
        accounting: CircuitAccounting::PhysicalControl,
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
        period: 1,
        route_stage_capacities: vec![],
        service_connections: vec![],
        service_orders: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        inventory: vec![],
        orders: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: vec![],
        production_commitments: vec![],
    };
    for (id, quantity) in [(4, 2), (5, 3)] {
        let process = ProcessId::from_bytes([id; 32]);
        catalog.process_outputs.push(ProcessOutput {
            process_id: process,
            site_id: site,
            good_id: GoodId::from_bytes([id; 32]),
            unit_id: UnitId::from_bytes([6; 32]),
            quantity_per_batch: 1,
        });
        catalog.labor_coefficients.push(LaborCoefficient {
            process_id: process,
            unit_id: labor_unit,
            quantity_per_batch: quantity,
        });
        state.capacities.push(CapacityRow {
            process_id: process,
            site_id: site,
            period: 1,
            available_batches: quantity,
        });
        state.production_commitments.push(ProductionCommitment {
            process_id: process,
            site_id: site,
            period: 1,
            planned_batches: quantity,
        });
    }
    for (period, available) in [(1, 12), (2, 30)] {
        state.labor.push(LaborCapacityRow {
            site_id: site,
            unit_id: labor_unit,
            period,
            available,
        });
    }
    (
        MaterialCatalog::try_new(catalog).expect("the fixture catalog canonicalizes"),
        state,
    )
}

fn committed_pair(parts: Parts) -> Pair {
    let (catalog, state) = parts;
    let opening = MaterialWorldRegister::try_new(&catalog, 0, state)
        .expect("the authored fixture satisfies the constructor invariants");
    let next = opening
        .prepare_next(&catalog)
        .expect("the fixture prepares the authored state");
    (
        opening.state().clone(),
        next.register().state().clone(),
        material_world::decode_material_receipts(next.receipt_bytes())
            .expect("the canonical bytes decode into the declared type"),
        catalog,
    )
}

#[test]
fn shared_principal_is_counted_once_and_time_closes_from_actual_receipts() {
    let (opening, next, receipt, catalog) = committed_pair(shared_opening());
    let rows = projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&receipt))
        .expect("the fixture projection accepts the authored input");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].next_opening_period, 2);
    assert_eq!(rows[0].next_opening_available, 30);
    assert_eq!(
        rows[0].completed,
        Some(CompletedProductionLabor {
            maintenance_needed: 0,
            maintenance_used: 0,
            installation_needed: 0,
            installation_used: 0,
            period: 1,
            opening: 12,
            planned: 13,
            used: 8,
            unused: 4,
            handling_needed: 0,
            handling_used: 0,
        })
    );
    let mut reversed = receipt.clone();
    reversed.production.reverse();
    assert_eq!(
        rows,
        projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&reversed))
            .expect("the fixture projection accepts the authored input")
    );
    assert_eq!(
        opening.labor[0].available, 12,
        "projection never debits authoritative time"
    );
}

#[test]
fn exact_unit_principals_remain_separate_at_the_same_site() {
    let (catalog, mut state) = shared_opening();
    let mut catalog = catalog.into_definition();
    let other_unit = UnitId::from_bytes([7; 32]);
    catalog.labor_coefficients[1].unit_id = other_unit;
    let mut budget = state.labor[0].clone();
    budget.unit_id = other_unit;
    budget.available = 6;
    state.labor.push(budget);
    let catalog = MaterialCatalog::try_new(catalog).expect("valid definitions");
    let (opening, next, receipt, catalog) = committed_pair((catalog, state));
    let rows = projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&receipt))
        .expect("the fixture projection accepts the authored input");
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0].site_id, rows[1].site_id);
    assert_ne!(rows[0].unit_id, rows[1].unit_id);
    let accounts: Vec<_> = rows
        .iter()
        .map(|row| {
            row.completed
                .as_ref()
                .expect("the fixture set the optional field before this read")
        })
        .collect();
    assert_eq!(
        (accounts[0].opening, accounts[0].used, accounts[0].unused),
        (12, 4, 8)
    );
    assert_eq!(
        (accounts[1].opening, accounts[1].used, accounts[1].unused),
        (6, 6, 0)
    );
    assert_eq!(
        rows[1].next_opening_available, 0,
        "no carried unused time or fabricated future budget"
    );
}

#[test]
fn multiplication_and_shared_sum_overflow_refuse_without_mutating_inputs() {
    let (mut opening, _, mut receipt, catalog) = committed_pair(shared_opening());
    let mut definition = catalog.into_definition();
    definition.labor_coefficients[0].quantity_per_batch = u64::MAX;
    let catalog = MaterialCatalog::try_new(definition).expect("valid definitions");
    let before = opening.clone();
    assert!(matches!(
        completed_totals(
            &catalog,
            &opening,
            &receipt,
            None,
            &budgets(&catalog, &opening)
                .expect("the fixture call `budgets` succeeds for the authored inputs"),
            &super::super::equipment::EquipmentFacts::default()
        ),
        Err(ProductionProjectionError::Arithmetic)
    ));
    assert_eq!(opening, before);
    let mut definition = catalog.into_definition();
    for coefficient in &mut definition.labor_coefficients {
        coefficient.quantity_per_batch = u64::MAX;
    }
    let catalog = MaterialCatalog::try_new(definition).expect("valid definitions");
    for plan in &mut opening.production_commitments {
        plan.planned_batches = 1;
    }
    for row in &mut receipt.production {
        row.planned_batches = 1;
        row.produced_batches = 0;
    }
    assert!(matches!(
        completed_totals(
            &catalog,
            &opening,
            &receipt,
            None,
            &budgets(&catalog, &opening)
                .expect("the fixture call `budgets` succeeds for the authored inputs"),
            &super::super::equipment::EquipmentFacts::default()
        ),
        Err(ProductionProjectionError::Arithmetic)
    ));
}

#[test]
fn inconsistent_accounts_refuse_instead_of_publishing_negative_or_unattributed_time() {
    let (opening, next, receipt, catalog) = committed_pair(shared_opening());
    let mut insufficient = opening.clone();
    insufficient.labor[0].available = 7;
    assert_eq!(
        projection::project_labor_accounts(&catalog, &next, Some(&insufficient), Some(&receipt)),
        Err(ProductionProjectionError::State)
    );
    let mut duplicate = receipt.clone();
    duplicate.production.push(receipt.production[0].clone());
    assert_eq!(
        projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&duplicate)),
        Err(ProductionProjectionError::State)
    );
    let mut missing = receipt.clone();
    missing.production.pop();
    assert_eq!(
        projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&missing)),
        Err(ProductionProjectionError::State)
    );
    assert_eq!(
        projection::project_labor_accounts(&catalog, &next, None, Some(&receipt)),
        Err(ProductionProjectionError::History)
    );
    let mut duplicate_budget = opening.clone();
    duplicate_budget.labor.push(opening.labor[0].clone());
    assert_eq!(
        budgets(&catalog, &duplicate_budget),
        Err(ProductionProjectionError::State)
    );
}

#[test]
fn maintenance_labor_is_debited_once_and_stays_separate_from_production_and_handling() {
    let (catalog, mut opening) = shared_opening();
    let mut catalog = catalog.into_definition();
    let consumer = ProcessId::from_bytes([4; 32]);
    catalog
        .process_outputs
        .retain(|row| row.process_id == consumer);
    catalog
        .labor_coefficients
        .retain(|row| row.process_id == consumer);
    opening.capacities.retain(|row| row.process_id == consumer);
    opening
        .production_commitments
        .retain(|row| row.process_id == consumer);
    catalog
        .input_coefficients
        .push(babylon_material_circuit::InputOutputCoefficient {
            process_id: consumer,
            good_id: GoodId::from_bytes([21; 32]),
            unit_id: UnitId::from_bytes([6; 32]),
            quantity_per_batch: 1,
        });
    opening
        .inventory
        .push(babylon_material_circuit::InventoryRow {
            site_id: SiteId::from_bytes([1; 32]),
            good_id: GoodId::from_bytes([21; 32]),
            unit_id: UnitId::from_bytes([6; 32]),
            quantity: 10,
        });
    catalog.commodities.push(CommodityDefinition {
        good_id: GoodId::from_bytes([21; 32]),
        unit_id: UnitId::from_bytes([6; 32]),
        kind: CommodityKind::Storable { grams_per_unit: 1 },
    });
    let provider = SiteId::from_bytes([20; 32]);
    let binding = babylon_material_circuit::MaintenanceBinding {
        provider_site_id: provider,
        consumer_process_id: ProcessId::from_bytes([4; 32]),
        spare_good_id: GoodId::from_bytes([4; 32]),
        spare_unit_id: UnitId::from_bytes([6; 32]),
        labor_unit_id: UnitId::from_bytes([2; 32]),
        spare_units_per_job: 1,
        labor_units_per_job: 2,
        enabled_batches_per_job: 1,
        maximum_jobs_per_period: 2,
    };
    catalog.site_logistics_nodes.push(SiteLogisticsNode {
        site_id: provider,
        node_id: LogisticsNodeId::from_bytes([22; 32]),
    });
    opening
        .inventory
        .push(babylon_material_circuit::InventoryRow {
            site_id: provider,
            good_id: binding.spare_good_id,
            unit_id: binding.spare_unit_id,
            quantity: 3,
        });
    opening.labor.push(LaborCapacityRow {
        site_id: provider,
        unit_id: binding.labor_unit_id,
        period: 1,
        available: 6,
    });
    opening.maintenance_service = Some(babylon_material_circuit::MaintenanceService {
        period: 1,
        available_batches: 2,
    });
    catalog.maintenance_binding = Some(binding);
    let mut future = opening.capacities.clone();
    for capacity in &mut future {
        capacity.period = 2;
    }
    opening.capacities.extend(future);
    let catalog = MaterialCatalog::try_new(catalog).expect("valid definitions");
    let (opening, next, receipt, catalog) = committed_pair((catalog, opening));
    let rows = projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&receipt))
        .expect("the fixture projection accepts the authored input");
    let provider = rows
        .iter()
        .find(|row| row.site_id == michigan_economy::digest_hex(&provider.as_bytes()))
        .expect("the fixture holds the searched element");
    let completed = serde_json::to_value(
        provider
            .completed
            .as_ref()
            .expect("the fixture set the optional field before this read"),
    )
    .expect("the value serializes to JSON");
    assert_eq!(completed["maintenance_needed"], 4);
    assert_eq!(completed["maintenance_used"], 4);
    assert_eq!(completed["used"], 4);
    assert_eq!(completed["unused"], 2);
    assert_eq!(completed["planned"], 0);
    assert_eq!(completed["handling_used"], 0);
    let mut missing = receipt.clone();
    missing.maintenance = None;
    assert!(
        projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&missing))
            .is_err()
    );
}

#[test]
fn monetary_attendance_cannot_relabel_actual_production_as_idle_or_handling() {
    let (opening, next, receipt, catalog) =
        committed_pair(crate::production_projection::recurring_fixture::materials());
    projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&receipt))
        .expect("the fixture projection accepts the authored input");
    for as_idle in [true, false] {
        let mut changed = receipt.clone();
        let member = changed
            .member_labor_use
            .iter_mut()
            .find(|row| row.production_hours > 0)
            .expect("the fixture holds the searched element");
        let key = (member.site_id, member.unit_id);
        let rate = member.compensation.wage_rate();
        member.production_hours -= 1;
        member.production_wages = member
            .production_wages
            .checked_sub(rate)
            .expect("the fixture arithmetic stays in range");
        if as_idle {
            member.idle_hours += 1;
            member.idle_wages = member
                .idle_wages
                .checked_add(rate)
                .expect("the fixture arithmetic stays in range");
            let aggregate = changed
                .labor_use
                .iter_mut()
                .find(|row| (row.site_id, row.unit_id) == key)
                .expect("the fixture holds the searched element");
            aggregate.used_hours -= 1;
            aggregate.paid_idle_hours += 1;
        } else {
            member.handling_hours += 1;
            member.handling_wages = member
                .handling_wages
                .checked_add(rate)
                .expect("the fixture arithmetic stays in range");
        }
        member
            .validate()
            .expect("the authored fixture passes validation");
        assert_eq!(
            projection::project_labor_accounts(&catalog, &next, Some(&opening), Some(&changed)),
            Err(ProductionProjectionError::History)
        );
    }
}
