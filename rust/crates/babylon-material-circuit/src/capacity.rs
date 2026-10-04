//! One supply boundary for existing process and shared freight allocators.
use std::collections::{BTreeMap, BTreeSet};

use crate::{
    CapacityRow, CapacitySupply, CorridorCapacity, CorridorId, FutureCapacityReservation,
    MaterialCircuitError, MaterialCircuitState, ProcessId, SiteId, MAX_MATERIAL_CIRCUIT_ROWS,
};

type Result<T> = std::result::Result<T, MaterialCircuitError>;

pub(crate) fn row_limits(state: &MaterialCircuitState) -> Result<()> {
    if let CapacitySupply::Rolling(rows) = &state.capacity_supply {
        if [
            match &rows.processes {
                crate::RollingProcessSupply::CapturedNameplate(r) => r.len(),
                crate::RollingProcessSupply::Equipment(e) => {
                    crate::equipment::row_limits(e)?;
                    e.bindings.len()
                }
            },
            rows.shared.len(),
            rows.future_reservations.len(),
        ]
        .into_iter()
        .any(|n| n > MAX_MATERIAL_CIRCUIT_ROWS)
        {
            return Err(MaterialCircuitError::RowLimit);
        }
    }
    Ok(())
}

pub(crate) fn canonicalize(supply: &mut CapacitySupply) {
    if let CapacitySupply::Rolling(rows) = supply {
        match &mut rows.processes {
            crate::RollingProcessSupply::CapturedNameplate(r) => {
                r.sort_by_key(|r| (r.site_id, r.process_id));
            }
            crate::RollingProcessSupply::Equipment(e) => crate::equipment::canonicalize(e),
        }
        rows.shared.sort_by_key(|r| r.corridor_id);
        rows.future_reservations
            .sort_by_key(|r| (r.departure_period, r.corridor_id));
    }
}

fn unique<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<()> {
    if rows.windows(2).any(|pair| key(&pair[0]) >= key(&pair[1])) {
        Err(MaterialCircuitError::DuplicateRow)
    } else {
        Ok(())
    }
}

pub(crate) fn validate(state: &MaterialCircuitState) -> Result<()> {
    let CapacitySupply::Rolling(rows) = &state.capacity_supply else {
        return Ok(());
    };
    let installed_processes = rows.processes.capacities(state.period)?;
    if let crate::RollingProcessSupply::Equipment(e) = &rows.processes {
        crate::equipment::validate(state, e)?;
    }
    unique(&installed_processes, |r| (r.site_id, r.process_id))?;
    unique(&rows.shared, |r| r.corridor_id)?;
    unique(&rows.future_reservations, |r| {
        (r.departure_period, r.corridor_id)
    })?;
    let processes: BTreeSet<_> = state
        .process_outputs
        .iter()
        .map(|r| (r.site_id, r.process_id))
        .collect();
    let installed: BTreeSet<_> = installed_processes
        .iter()
        .map(|r| (r.site_id, r.process_id))
        .collect();
    let corridors: BTreeSet<_> = state
        .route_stage_capacities
        .iter()
        .map(|r| r.corridor_id)
        .chain(state.merchants.iter().map(|r| r.capacity_id))
        .collect();
    let supply: BTreeMap<_, _> = rows
        .shared
        .iter()
        .map(|r| (r.corridor_id, r.grams_per_period))
        .collect();
    if installed != processes
        || supply.keys().copied().collect::<BTreeSet<_>>() != corridors
        || state.capacities.len() != installed_processes.len()
        || state.corridor_capacities.len() != rows.shared.len()
    {
        return Err(MaterialCircuitError::CapacityInvariant);
    }
    for (budget, installed) in state.capacities.iter().zip(&installed_processes) {
        if budget.period != state.period
            || budget.site_id != installed.site_id
            || budget.process_id != installed.process_id
            || budget.available_batches != installed.batches_per_period
        {
            return Err(MaterialCircuitError::CapacityInvariant);
        }
    }
    for (budget, supply) in state.corridor_capacities.iter().zip(&rows.shared) {
        if budget.period != state.period
            || budget.corridor_id != supply.corridor_id
            || budget.available_grams > supply.grams_per_period
        {
            return Err(MaterialCircuitError::CapacityInvariant);
        }
    }
    let horizons = departure_horizons(state)?;
    for reservation in &rows.future_reservations {
        let offset = reservation
            .departure_period
            .checked_sub(state.period)
            .ok_or(MaterialCircuitError::CapacityInvariant)?;
        if offset == 0
            || horizons
                .get(&reservation.corridor_id)
                .is_none_or(|horizon| offset > *horizon)
            || reservation.reserved_grams == 0
            || supply
                .get(&reservation.corridor_id)
                .is_none_or(|gross| reservation.reserved_grams > *gross)
        {
            return Err(MaterialCircuitError::CapacityInvariant);
        }
    }
    Ok(())
}

fn departure_horizons(state: &MaterialCircuitState) -> Result<BTreeMap<CorridorId, u64>> {
    let mut offsets = BTreeMap::new();
    let mut route = None;
    let mut arrival = 0_u64;
    for stage in &state.route_stages {
        if route != Some(stage.route_id) {
            route = Some(stage.route_id);
            arrival = 0;
        }
        offsets.insert((stage.route_id, stage.stage_index), arrival);
        arrival = arrival
            .checked_add(u64::from(stage.travel_periods))
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    let mut horizons = BTreeMap::<CorridorId, u64>::new();
    for membership in &state.route_stage_capacities {
        let offset = offsets
            .get(&(membership.route_id, membership.stage_index))
            .ok_or(MaterialCircuitError::CapacityInvariant)?;
        let horizon = horizons.entry(membership.corridor_id).or_default();
        *horizon = (*horizon).max(*offset);
    }
    Ok(horizons)
}

pub(crate) fn process_available(
    state: &MaterialCircuitState,
    process: ProcessId,
    site: SiteId,
    period: u64,
) -> Result<u64> {
    if period > state.period {
        if let CapacitySupply::Rolling(rows) = &state.capacity_supply {
            return match &rows.processes {
                crate::RollingProcessSupply::CapturedNameplate(r) => Ok(r
                    .binary_search_by_key(&(site, process), |r| (r.site_id, r.process_id))
                    .ok()
                    .map_or(0, |i| r[i].batches_per_period)),
                crate::RollingProcessSupply::Equipment(e) => {
                    let (b, d) = e.definition(process)?;
                    if b.site_id != site {
                        return Err(MaterialCircuitError::EquipmentInvariant);
                    }
                    e.cohorts[e.cohorts_for(process)]
                        .iter()
                        .filter(|c| c.usable_from_period <= period)
                        .try_fold(0_u64, |n, c| {
                            let v = c
                                .units
                                .checked_mul(d.batches_per_unit_per_period)
                                .ok_or(MaterialCircuitError::Arithmetic)?
                                .min(c.remaining_service_batches);
                            n.checked_add(v).ok_or(MaterialCircuitError::Arithmetic)
                        })
                }
            };
        }
    }
    Ok(state
        .capacities
        .binary_search_by_key(&(period, site, process), |r| {
            (r.period, r.site_id, r.process_id)
        })
        .ok()
        .map_or(0, |i| state.capacities[i].available_batches))
}

pub(crate) fn shared_available(
    state: &MaterialCircuitState,
    period: u64,
    corridor: CorridorId,
) -> Result<u64> {
    if period > state.period {
        if let CapacitySupply::Rolling(rows) = &state.capacity_supply {
            let gross = rows
                .shared
                .binary_search_by_key(&corridor, |r| r.corridor_id)
                .ok()
                .map_or(0, |i| rows.shared[i].grams_per_period);
            let reserved = rows
                .future_reservations
                .binary_search_by_key(&(period, corridor), |r| (r.departure_period, r.corridor_id))
                .ok()
                .map_or(0, |i| rows.future_reservations[i].reserved_grams);
            return gross
                .checked_sub(reserved)
                .ok_or(MaterialCircuitError::CapacityInvariant);
        }
    }
    Ok(state
        .corridor_capacities
        .binary_search_by_key(&(period, corridor), |r| (r.period, r.corridor_id))
        .ok()
        .map_or(0, |i| state.corridor_capacities[i].available_grams))
}

pub(crate) fn reserve(
    state: &mut MaterialCircuitState,
    period: u64,
    corridor: CorridorId,
    grams: u64,
) -> Result<()> {
    if grams == 0 || period < state.period {
        return Err(MaterialCircuitError::CapacityInvariant);
    }
    let remaining = shared_available(state, period, corridor)?
        .checked_sub(grams)
        .ok_or(MaterialCircuitError::CapacityInvariant)?;
    if period > state.period {
        if let CapacitySupply::Rolling(rows) = &mut state.capacity_supply {
            match rows
                .future_reservations
                .binary_search_by_key(&(period, corridor), |r| (r.departure_period, r.corridor_id))
            {
                Ok(i) => {
                    rows.future_reservations[i].reserved_grams = rows.future_reservations[i]
                        .reserved_grams
                        .checked_add(grams)
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                }
                Err(i) => {
                    if rows.future_reservations.len() >= MAX_MATERIAL_CIRCUIT_ROWS {
                        return Err(MaterialCircuitError::RowLimit);
                    }
                    rows.future_reservations.insert(
                        i,
                        FutureCapacityReservation {
                            departure_period: period,
                            corridor_id: corridor,
                            reserved_grams: grams,
                        },
                    );
                }
            }
            return Ok(());
        }
    }
    let i = state
        .corridor_capacities
        .binary_search_by_key(&(period, corridor), |r| (r.period, r.corridor_id))
        .map_err(|_| MaterialCircuitError::CapacityInvariant)?;
    state.corridor_capacities[i].available_grams = remaining;
    Ok(())
}

pub(crate) fn roll_forward(state: &mut MaterialCircuitState, next_period: u64) -> Result<()> {
    if state.period.checked_add(1) != Some(next_period) {
        return Err(MaterialCircuitError::PeriodInvariant);
    }
    let CapacitySupply::Rolling(rows) = &mut state.capacity_supply else {
        state
            .corridor_capacities
            .retain(|r| r.period >= next_period);
        return Ok(());
    };
    let capacities = rows
        .processes
        .capacities(next_period)?
        .iter()
        .map(|r| CapacityRow {
            site_id: r.site_id,
            process_id: r.process_id,
            period: next_period,
            available_batches: r.batches_per_period,
        })
        .collect();
    let corridor_capacities = rows
        .shared
        .iter()
        .map(|r| {
            let reserved = rows
                .future_reservations
                .binary_search_by_key(&(next_period, r.corridor_id), |r| {
                    (r.departure_period, r.corridor_id)
                })
                .ok()
                .map_or(0, |i| rows.future_reservations[i].reserved_grams);
            Ok(CorridorCapacity {
                corridor_id: r.corridor_id,
                period: next_period,
                available_grams: r
                    .grams_per_period
                    .checked_sub(reserved)
                    .ok_or(MaterialCircuitError::CapacityInvariant)?,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    rows.future_reservations
        .retain(|r| r.departure_period > next_period);
    state.capacities = capacities;
    state.corridor_capacities = corridor_capacities;
    Ok(())
}
