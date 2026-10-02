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
    receipt: &babylon_tick::material_world::MaterialTickReceipts,
) -> Result<BTreeMap<CapacityKey, ProductionFreightReservation>> {
    // Mutable assets may differ only after the actual installation/wear book join succeeds.
    super::super::equipment::validate(prior, current, receipt)?;
    let same_processes = match (&before.processes, &after.processes) {
        (
            babylon_material_circuit::RollingProcessSupply::Equipment(_),
            babylon_material_circuit::RollingProcessSupply::Equipment(_),
        ) => true,
        (a, b) => a == b,
    };
    if !same_processes || shared_identity(before) != shared_identity(after) {
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

fn shared_identity(supply: &RollingCapacitySupply) -> Vec<(CorridorId, u64)> {
    let mut rows: Vec<_> = supply
        .shared
        .iter()
        .map(|r| (r.corridor_id, r.grams_per_period))
        .collect();
    rows.sort_unstable();
    rows
}
