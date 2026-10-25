use babylon_material_circuit::{LogisticsNodeId, RouteStage, RouteStageCapacity};
use babylon_tick::material_world::MaterialWorldRegister;

use super::super::ProductionProjectionError;
use super::projection;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_economy;
use crate::michigan_material::MichiganDeliveryPreset;
use crate::production_observation::{
    ProductionFreightOrderDefinition, ProductionFreightReservation,
};
use babylon_material_circuit::RollingProcessSupply;
use babylon_material_circuit::{MaterialCatalog, MaterialCircuitState};
use babylon_tick::material_world;
use babylon_tick::material_world::MaterialTickReceipts;
use serde_json::Value;
use std::collections::BTreeMap;
use std::collections::BTreeSet;

type Parts = (MaterialCatalog, MaterialCircuitState);
type Pair = (
    MaterialCircuitState,
    MaterialCircuitState,
    MaterialTickReceipts,
    MaterialCatalog,
);

fn shared_opening(meal_order: u64, capacity: u64) -> Parts {
    let source = crate::test_support::catalog();
    let foundation = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
        .create_foundation(&source)
        .expect("the authored catalog builds the foundation");
    let catalog = foundation.material_catalog().clone();
    let mut state = foundation.initial_register().state().clone();
    let sheet = source
        .routes()
        .iter()
        .find(|route| route.good_key == "sheet")
        .expect("the fixture holds the searched element");
    let meal = source
        .routes()
        .iter()
        .find(|route| route.good_key == "meal")
        .expect("the fixture holds the searched element");
    let shared = state
        .route_stage_capacities
        .iter()
        .find(|leg| leg.route_id == sheet.id())
        .expect("the fixture holds the searched element")
        .corridor_id;
    let obsolete = state
        .route_stage_capacities
        .iter()
        .find(|leg| leg.route_id == meal.id())
        .expect("the fixture holds the searched element")
        .corridor_id;
    for leg in &mut state.route_stage_capacities {
        if leg.route_id == meal.id() {
            leg.corridor_id = shared;
        }
    }
    state
        .corridor_capacities
        .retain(|row| row.corridor_id != obsolete);
    for row in &mut state.corridor_capacities {
        if row.corridor_id == shared {
            row.available_grams = capacity * 1_000;
        }
    }
    state
        .orders
        .iter_mut()
        .find(|order| order.order_id == meal.order_id())
        .expect("the fixture holds the searched element")
        .ordered = meal_order;
    (catalog, state)
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

fn assert_shared_reservation(
    reservation: &ProductionFreightReservation,
    definitions: &[ProductionFreightOrderDefinition],
    receipt: &MaterialTickReceipts,
    capacity: u64,
    expected: (u64, u64, u64),
) {
    assert_eq!(reservation.orders.len(), 2);
    let dispatches: BTreeMap<_, _> = receipt
        .dispatches
        .iter()
        .map(|row| {
            (
                michigan_economy::digest_hex(&row.order_id.as_bytes()),
                row.quantity,
            )
        })
        .collect();
    let projected_orders: Vec<_> = reservation
        .orders
        .iter()
        .map(|reference| {
            &definitions
                .iter()
                .find(|row| &row.id == reference)
                .expect("the fixture holds the searched element")
                .order
        })
        .collect();
    let source = crate::test_support::catalog();
    for (good, quantity) in [("sheet", expected.0), ("meal", expected.1)] {
        let route = source
            .routes()
            .iter()
            .find(|row| row.good_key == good)
            .expect("the fixture holds the searched element");
        let order_id = michigan_economy::digest_hex(&route.order_id().as_bytes());
        let order = projected_orders
            .iter()
            .find(|row| row.order_id == order_id)
            .expect("the fixture holds the searched element");
        assert_eq!(order.dispatched, quantity);
        assert_eq!(order.grams_per_unit, 1_000);
        assert_eq!(dispatches.get(&order_id), Some(&quantity));
        assert_eq!(
            order.requested.checked_sub(order.dispatched),
            Some(order.remaining_unshipped)
        );
    }
    let reserved = projected_orders
        .iter()
        .try_fold(0_u64, |total, row| {
            total.checked_add(row.dispatched.checked_mul(row.grams_per_unit)?)
        })
        .expect("the fixture input satisfies the fallible conversion");
    assert_eq!(reservation.newly_reserved_grams, reserved);
    assert_eq!(
        reservation.opening_available_grams,
        reservation
            .newly_reserved_grams
            .checked_add(reservation.remaining_available_grams)
            .expect("the fixture arithmetic stays in range")
    );
    assert_eq!(
        (
            reservation.reservation_period,
            reservation.opening_available_grams,
            reservation.remaining_available_grams
        ),
        (1, capacity * 1_000, expected.2 * 1_000)
    );
}

#[test]
fn shared_capacity_is_counted_once_with_exact_competing_dispatches_and_residual() {
    for (meal_order, capacity, expected) in [
        (200, 800, (320, 80, 400)),
        (200, 160, (120, 40, 0)),
        (80, 160, (141, 19, 0)),
    ] {
        let (opening, next, receipt, material) =
            committed_pair(shared_opening(meal_order, capacity));
        let (accounts, definitions) = projection::project_freight_capacity_accounts(
            &crate::test_support::catalog(),
            &material,
            &next,
            Some(&opening),
            Some(&receipt),
        )
        .expect("the fixture projection accepts the authored input");
        assert_eq!(
            accounts.len(),
            2,
            "one shared kg principal and the independent panel principal"
        );
        let account = accounts
            .iter()
            .find(|row| row.route_ids.len() == 2)
            .expect("the fixture holds the searched element");
        let completed = account
            .completed
            .as_ref()
            .expect("the fixture set the optional field before this read");
        assert_eq!(completed.period, 1);
        assert_eq!(completed.reservations.len(), 1);
        let reservation = &completed.reservations[0];
        assert_shared_reservation(reservation, &definitions, &receipt, capacity, expected);
        assert!(reservation.reservation_period < next.period);
        assert!(
            !next.corridor_capacities.iter().any(|row| {
                michigan_economy::digest_hex(&row.corridor_id.as_bytes()) == account.corridor_id
                    && row.period == reservation.reservation_period
            }),
            "expired capacity is historical evidence, not next-period supply"
        );
        let mut permuted_opening = opening.clone();
        permuted_opening.orders.reverse();
        permuted_opening.route_stage_capacities.reverse();
        permuted_opening.corridor_capacities.reverse();
        let mut permuted_receipt = receipt.clone();
        permuted_receipt.dispatches.reverse();
        assert_eq!(
            (accounts, definitions),
            projection::project_freight_capacity_accounts(
                &crate::test_support::catalog(),
                &material,
                &next,
                Some(&permuted_opening),
                Some(&permuted_receipt)
            )
            .expect("the fixture projection accepts the authored input")
        );
    }
}

#[test]
fn foundation_sharing_is_known_but_completed_zero_is_not_invented() {
    let (material, state) = shared_opening(200, 160);
    let (accounts, _definitions) = projection::project_freight_capacity_accounts(
        &crate::test_support::catalog(),
        &material,
        &state,
        None,
        None,
    )
    .expect("the fixture projection accepts the authored input");
    assert!(accounts.iter().all(|row| row.completed.is_none()));
    assert_eq!(
        accounts
            .iter()
            .find(|row| row.route_ids.len() == 2)
            .expect("the fixture holds the searched element")
            .next_opening_available_grams,
        160_000
    );
    let (opening, next, receipt, material) = committed_pair(shared_opening(200, 0));
    let (accounts, definitions) = projection::project_freight_capacity_accounts(
        &crate::test_support::catalog(),
        &material,
        &next,
        Some(&opening),
        Some(&receipt),
    )
    .expect("the fixture projection accepts the authored input");
    let completed = accounts
        .iter()
        .find(|row| row.route_ids.len() == 2)
        .expect("the fixture holds the searched element")
        .completed
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(completed.reservations[0].newly_reserved_grams, 0);
    assert!(completed.reservations[0]
        .orders
        .iter()
        .all(|reference| definitions
            .iter()
            .find(|d| &d.id == reference)
            .expect("the fixture holds the searched element")
            .order
            .dispatched
            == 0));
}

#[test]
fn missing_duplicate_and_excess_receipts_or_capacity_refuse() {
    let (opening, next, receipt, material) = committed_pair(shared_opening(200, 160));
    let source = crate::test_support::catalog();
    let mut missing = receipt.clone();
    missing.dispatches.pop();
    assert_eq!(
        projection::project_freight_capacity_accounts(
            &source,
            &material,
            &next,
            Some(&opening),
            Some(&missing)
        ),
        Err(ProductionProjectionError::State)
    );
    let mut duplicate = receipt.clone();
    duplicate.dispatches.push(receipt.dispatches[0].clone());
    assert_eq!(
        projection::project_freight_capacity_accounts(
            &source,
            &material,
            &next,
            Some(&opening),
            Some(&duplicate)
        ),
        Err(ProductionProjectionError::State)
    );
    let mut duplicated_capacity = opening.clone();
    duplicated_capacity
        .corridor_capacities
        .push(opening.corridor_capacities[0].clone());
    assert_eq!(
        projection::project_freight_capacity_accounts(
            &source,
            &material,
            &next,
            Some(&duplicated_capacity),
            Some(&receipt)
        ),
        Err(ProductionProjectionError::State)
    );
    let mut wrong_next = next.clone();
    wrong_next.corridor_capacities[0].available_grams += 1;
    assert_eq!(
        projection::project_freight_capacity_accounts(
            &source,
            &material,
            &wrong_next,
            Some(&opening),
            Some(&receipt)
        ),
        Err(ProductionProjectionError::State)
    );
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`reservations_for_later_legs_debit_the_future_period_without_claiming_arrival` keeps one authored boundary's fixture and assertions together"
)]
fn reservations_for_later_legs_debit_the_future_period_without_claiming_arrival() {
    let (mut catalog, mut state) = shared_opening(200, 160);
    let source = crate::test_support::catalog();
    let sheet = source
        .routes()
        .iter()
        .find(|route| route.good_key == "sheet")
        .expect("the fixture holds the searched element");
    let first = catalog
        .route_stages
        .iter_mut()
        .find(|leg| leg.route_id == sheet.id())
        .expect("the fixture holds the searched element");
    let destination = first.to_node_id;
    let intermediate = LogisticsNodeId::from_bytes([73; 32]);
    first.to_node_id = intermediate;
    let second = RouteStage {
        route_id: first.route_id,
        stage_index: 1,
        from_node_id: intermediate,
        to_node_id: destination,
        travel_periods: 1,
        loss_ppm: 0,
    };
    let shared_id = state
        .route_stage_capacities
        .iter()
        .find(|row| row.route_id == sheet.id())
        .expect("the fixture holds the searched element")
        .corridor_id;
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: sheet.id(),
        stage_index: 1,
        corridor_id: shared_id,
    });
    catalog.route_stages.push(second);
    // The catalog is sealed and ordered; re-seal it after the authored extension.
    let catalog = MaterialCatalog::try_new(catalog).expect("the extended catalog canonicalizes");
    let (opening, next, receipt, material) = committed_pair((catalog, state));
    let (accounts, _definitions) = projection::project_freight_capacity_accounts(
        &source,
        &material,
        &next,
        Some(&opening),
        Some(&receipt),
    )
    .expect("the fixture projection accepts the authored input");
    let shared = accounts
        .iter()
        .find(|row| row.route_ids.len() == 2)
        .expect("the fixture holds the searched element");
    assert_eq!(
        (
            shared.next_opening_period,
            shared.next_opening_available_grams
        ),
        (2, 40_000)
    );
    let completed = shared
        .completed
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(completed.period, 1);
    assert_eq!(
        completed
            .reservations
            .iter()
            .map(|row| (
                row.reservation_period,
                row.newly_reserved_grams,
                row.remaining_available_grams
            ))
            .collect::<Vec<_>>(),
        vec![(1, 160_000, 0), (2, 120_000, 40_000)]
    );
    assert!(receipt.arrivals.is_empty());
    let mut stages = super::super::routes::stage_index(&material, &next)
        .expect("the fixture call `stage_index` succeeds for the authored inputs");
    let legs = stages
        .remove(&sheet.id())
        .expect("the fixture call `remove` succeeds for the authored inputs");
    assert_eq!(
        legs.iter().map(|leg| leg.stage_index).collect::<Vec<_>>(),
        [0, 1]
    );
    assert_eq!(legs[0].capacity_ids, legs[1].capacity_ids);
    let mut mismatched = next.clone();
    let capacity = mismatched
        .corridor_capacities
        .iter_mut()
        .find(|row| {
            row.period == 2
                && michigan_economy::digest_hex(&row.corridor_id.as_bytes()) == shared.corridor_id
        })
        .expect("the fixture holds the searched element");
    capacity.available_grams += 1;
    assert_eq!(
        projection::project_freight_capacity_accounts(
            &source,
            &material,
            &mismatched,
            Some(&opening),
            Some(&receipt)
        ),
        Err(ProductionProjectionError::State)
    );
}

#[test]
fn rolling_capacity_reconciles_future_bookings_and_refuses_unexplained_budget_changes() {
    let source = crate::test_support::catalog();
    let (opening, next, receipt, material) = committed_pair(rolling_two_stage_opening());
    let project = |current: &MaterialCircuitState| {
        projection::project_freight_capacity_accounts(
            &source,
            &material,
            current,
            Some(&opening),
            Some(&receipt),
        )
    };
    let (accounts, _definitions) =
        project(&next).expect("the fixture projection accepts the authored state");
    let shared = accounts
        .iter()
        .find(|row| row.route_ids.len() == 2)
        .expect("the fixture holds the searched element");
    assert_eq!(shared.next_opening_available_grams, 160_000);
    assert_eq!(
        shared
            .completed
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .reservations
            .iter()
            .map(|row| (row.reservation_period, row.newly_reserved_grams))
            .collect::<Vec<_>>(),
        vec![(1, 160_000), (3, 120_000)]
    );
    assert_eq!(next.capacity_reservations.future.len(), 1);
    assert_eq!(next.capacity_reservations.future[0].departure_period, 3);
    assert_eq!(next.capacity_reservations.future[0].reserved_grams, 120_000);
    let mut changed = next.clone();
    changed.capacity_reservations.future[0].reserved_grams -= 1;
    assert_eq!(project(&changed), Err(ProductionProjectionError::State));
    let mut changed = next.clone();
    changed.corridor_capacities[0].available_grams -= 1;
    assert_eq!(project(&changed), Err(ProductionProjectionError::State));
    let mut changed_material = material.clone();
    let babylon_material_circuit::CapacitySupply::Rolling(supply) =
        &mut changed_material.capacity_policy
    else {
        unreachable!()
    };
    supply.shared[0].grams_per_period += 1;
    assert_eq!(
        projection::project_freight_capacity_accounts(
            &source,
            &changed_material,
            &next,
            Some(&opening),
            Some(&receipt),
        ),
        Err(ProductionProjectionError::State)
    );
}

fn rolling_two_stage_opening() -> Parts {
    use babylon_material_circuit::{
        CapacitySupply, InstalledProcessCapacity, RollingCapacitySupply, SharedCapacitySupply,
    };
    let (mut material, mut state) = shared_opening(200, 160);
    let source = crate::test_support::catalog();
    let route = source
        .routes()
        .iter()
        .find(|row| row.good_key == "sheet")
        .expect("the fixture holds the searched element")
        .id();
    let first = material
        .route_stages
        .iter_mut()
        .find(|row| row.route_id == route)
        .expect("the fixture holds the searched element");
    let destination = first.to_node_id;
    first.to_node_id = LogisticsNodeId::from_bytes([73; 32]);
    first.travel_periods = 2;
    let second = RouteStage {
        route_id: route,
        stage_index: 1,
        from_node_id: first.to_node_id,
        to_node_id: destination,
        travel_periods: 1,
        loss_ppm: 0,
    };
    material.route_stages.push(second);
    let shared = state
        .route_stage_capacities
        .iter()
        .find(|row| row.route_id == route)
        .expect("the fixture holds the searched element")
        .corridor_id;
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: route,
        stage_index: 1,
        corridor_id: shared,
    });
    state.capacities.retain(|row| row.period == 1);
    state.corridor_capacities.retain(|row| row.period == 1);
    material.capacity_policy = CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
        processes: RollingProcessSupply::CapturedNameplate(
            state
                .capacities
                .iter()
                .map(|row| InstalledProcessCapacity {
                    process_id: row.process_id,
                    site_id: row.site_id,
                    batches_per_period: row.available_batches,
                })
                .collect(),
        ),
        shared: state
            .corridor_capacities
            .iter()
            .map(|row| SharedCapacitySupply {
                corridor_id: row.corridor_id,
                grams_per_period: row.available_grams,
            })
            .collect(),
    }));
    // The catalog is sealed and ordered; re-seal it after the authored extension.
    let material = MaterialCatalog::try_new(material).expect("the extended catalog canonicalizes");
    (material, state)
}

#[test]
fn multileg_projection_encodes_each_exact_order_fact_once() {
    fn collect(value: &Value, facts: &mut Vec<String>) {
        match value {
            Value::Object(row) => {
                if row.contains_key("order_id") {
                    facts.push(
                        serde_json::to_string(value).expect("the fixture value formats as text"),
                    );
                }
                for child in row.values() {
                    collect(child, facts);
                }
            }
            Value::Array(rows) => {
                for child in rows {
                    collect(child, facts);
                }
            }
            _ => {}
        }
    }
    let (mut catalog, mut state) = shared_opening(200, 160);
    let source = crate::test_support::catalog();
    let sheet = source
        .routes()
        .iter()
        .find(|r| r.good_key == "sheet")
        .expect("the fixture holds the searched element");
    let first = catalog
        .route_stages
        .iter_mut()
        .find(|leg| leg.route_id == sheet.id())
        .expect("the fixture holds the searched element");
    let destination = first.to_node_id;
    let intermediate = LogisticsNodeId::from_bytes([73; 32]);
    first.to_node_id = intermediate;
    let second = RouteStage {
        route_id: first.route_id,
        stage_index: 1,
        from_node_id: intermediate,
        to_node_id: destination,
        travel_periods: 1,
        loss_ppm: 0,
    };
    let shared = state
        .route_stage_capacities
        .iter()
        .find(|r| r.route_id == sheet.id())
        .expect("the fixture holds the searched element")
        .corridor_id;
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: sheet.id(),
        stage_index: 1,
        corridor_id: shared,
    });
    catalog.route_stages.push(second);
    // The catalog is sealed and ordered; re-seal it after the authored extension.
    let catalog = MaterialCatalog::try_new(catalog).expect("the extended catalog canonicalizes");
    let (opening, next, receipt, material) = committed_pair((catalog, state));
    let projection = projection::project_freight_capacity_accounts(
        &source,
        &material,
        &next,
        Some(&opening),
        Some(&receipt),
    )
    .expect("the fixture projection accepts the authored input");
    let disclosure = serde_json::to_value(&projection).expect("the value serializes to JSON");
    let mut facts = Vec::new();
    collect(&disclosure, &mut facts);
    let unique: BTreeSet<_> = facts.iter().collect();
    assert!(
        !unique.is_empty(),
        "actual commercial order facts must remain disclosed"
    );
    assert_eq!(
        facts.len(),
        unique.len(),
        "one exact order tuple must be encoded once despite reservations on multiple legs"
    );
}
