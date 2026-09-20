//! Reconcile installed supply and dated booking changes against actual receipts.
//! This reads committed accounts; it neither allocates nor creates capacity.
use super::{
    budgets, reservation_receipts, Budgets, CapacityKey, MaterialCircuitState,
    ProductionFreightReservation, ProductionProjectionError, Reservations, Result,
};
use babylon_material_circuit::{CorridorId, FutureCapacityReservation, RollingCapacitySupply};
use std::collections::{BTreeMap, BTreeSet};

pub(super) fn reconcile(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    before: &RollingCapacitySupply,
    after: &RollingCapacitySupply,
    reservations: Reservations,
) -> Result<BTreeMap<CapacityKey, ProductionFreightReservation>> {
    if supply_identity(before) != supply_identity(after) {
        return Err(ProductionProjectionError::State);
    }
    let supply: BTreeMap<_, _> = before
        .shared
        .iter()
        .map(|row| (row.corridor_id, row.grams_per_period))
        .collect();
    if supply.len() != before.shared.len() {
        return Err(ProductionProjectionError::State);
    }
    let previous_book = reservation_book(&before.future_reservations, prior.period)?;
    let mut dates: BTreeSet<_> = previous_book.keys().copied().collect();
    dates.extend(reservations.keys().copied());
    dates.extend(supply.keys().map(|id| (*id, current.period)));
    let mut opening = budgets(prior)?;
    for key in dates {
        if key.1 > prior.period {
            let amount = gross(&supply, key.0)?
                .checked_sub(previous_book.get(&key).copied().unwrap_or(0))
                .ok_or(ProductionProjectionError::State)?;
            if opening.insert(key, amount).is_some() {
                return Err(ProductionProjectionError::State);
            }
        }
    }
    let (remaining, result) = reservation_receipts(&opening, reservations)?;
    let next: Budgets = remaining
        .iter()
        .filter(|(key, _)| key.1 == current.period)
        .map(|(key, value)| (*key, *value))
        .collect();
    if next != budgets(current)? {
        return Err(ProductionProjectionError::State);
    }
    let mut expected_book = BTreeMap::new();
    for (key, remaining) in remaining.iter().filter(|(key, _)| key.1 > current.period) {
        let booked = gross(&supply, key.0)?
            .checked_sub(*remaining)
            .ok_or(ProductionProjectionError::State)?;
        if booked > 0 {
            expected_book.insert(*key, booked);
        }
    }
    if expected_book != reservation_book(&after.future_reservations, current.period)? {
        return Err(ProductionProjectionError::State);
    }
    Ok(result)
}

fn gross(supply: &BTreeMap<CorridorId, u64>, id: CorridorId) -> Result<u64> {
    supply
        .get(&id)
        .copied()
        .ok_or(ProductionProjectionError::State)
}

fn reservation_book(rows: &[FutureCapacityReservation], period: u64) -> Result<Budgets> {
    let mut result = BTreeMap::new();
    for row in rows {
        if row.departure_period <= period
            || row.reserved_grams == 0
            || result
                .insert((row.corridor_id, row.departure_period), row.reserved_grams)
                .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(result)
}

type InstalledIdentity = (
    babylon_material_circuit::ProcessId,
    babylon_material_circuit::SiteId,
    u64,
);
type SupplyIdentity = (Vec<InstalledIdentity>, Vec<(CorridorId, u64)>);

fn supply_identity(value: &RollingCapacitySupply) -> SupplyIdentity {
    let mut processes: Vec<_> = value
        .installed_processes
        .iter()
        .map(|row| (row.process_id, row.site_id, row.batches_per_period))
        .collect();
    let mut shared: Vec<_> = value
        .shared
        .iter()
        .map(|row| (row.corridor_id, row.grams_per_period))
        .collect();
    processes.sort_unstable();
    shared.sort_unstable();
    (processes, shared)
}
