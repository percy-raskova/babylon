//! Current capacity reservations; the authored policy lives in the catalog.
use super::Cursor;
use crate::CorridorId;
use crate::{CapacityReservations, FutureCapacityReservation, MaterialCircuitError};

pub(super) fn append(
    bytes: &mut Vec<u8>,
    reservations: &CapacityReservations,
) -> Result<(), MaterialCircuitError> {
    super::equipment::append_position(bytes, &reservations.equipment)?;
    super::append_rows(bytes, &reservations.future, |b, row| {
        b.extend_from_slice(&row.departure_period.to_be_bytes());
        b.extend_from_slice(&row.corridor_id.as_bytes());
        b.extend_from_slice(&row.reserved_grams.to_be_bytes());
    })
}

pub(super) fn decode(
    cursor: &mut Cursor<'_>,
) -> Result<CapacityReservations, MaterialCircuitError> {
    Ok(CapacityReservations {
        equipment: super::equipment::decode_position(cursor)?,
        future: super::decode_rows(cursor, |row| {
            Ok(FutureCapacityReservation {
                departure_period: row.u64()?,
                corridor_id: CorridorId::from_bytes(row.array()?),
                reserved_grams: row.u64()?,
            })
        })?,
    })
}
