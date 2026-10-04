//! Gift capacity reservations are separate from commercial supplier orders.
use super::{MaterialCircuitState, ProductionProjectionError, Reservations, Result, RouteIndex};
use crate::{michigan_economy::digest_hex, production_observation::ProductionAidCapacityOrder};
use babylon_material_circuit::{AidOutcome, AidTransport};
use babylon_tick::material_world::MaterialTickReceipts;
pub(super) fn append(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    index: &RouteIndex<'_>,
    reservations: &mut Reservations,
) -> Result<()> {
    super::super::aid::join(prior, current, receipt)?;
    for row in receipt
        .aid
        .iter()
        .filter(|r| r.outcome == AidOutcome::Dispatched)
    {
        let AidTransport::Routed { route_id, .. } = row.transport else {
            return Err(ProductionProjectionError::State);
        };
        let commodity = prior
            .commodities
            .iter()
            .find(|c| c.good_id == row.good_id && c.unit_id == row.unit_id)
            .ok_or(ProductionProjectionError::State)?;
        let grams = commodity
            .grams_per_unit()
            .map_err(|_| ProductionProjectionError::State)?;
        let reserved = row
            .quantity
            .checked_mul(grams)
            .ok_or(ProductionProjectionError::Arithmetic)?;
        let order = ProductionAidCapacityOrder {
            commitment_id: digest_hex(&row.commitment_id.as_bytes()),
            mandate_id: digest_hex(&row.mandate_id),
            donor_principal_id: digest_hex(&row.donor.as_bytes()),
            recipient_principal_id: digest_hex(&row.recipient.as_bytes()),
            route_id: digest_hex(&route_id.as_bytes()),
            good_id: digest_hex(&row.good_id.as_bytes()),
            unit_id: digest_hex(&row.unit_id.as_bytes()),
            dispatched: row.quantity,
            grams_per_unit: grams,
            reserved_grams: reserved,
        };
        let stages = index
            .stages
            .get(&route_id)
            .filter(|rows| !rows.is_empty())
            .ok_or(ProductionProjectionError::State)?;
        let mut departure = prior.period;
        for stage in stages {
            let capacities = index
                .memberships
                .get(&(route_id, stage.stage_index))
                .ok_or(ProductionProjectionError::State)?;
            for capacity in capacities {
                reservations
                    .entry((*capacity, departure))
                    .or_default()
                    .support
                    .push(order.clone());
            }
            departure = departure
                .checked_add(u64::from(stage.travel_periods))
                .ok_or(ProductionProjectionError::Arithmetic)?;
        }
    }
    Ok(())
}
