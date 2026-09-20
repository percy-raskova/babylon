//! Exact explicit capacity source and advance-booking state.
use super::{append_rows, decode_rows, Cursor};
use crate::{
    CapacitySupply, CorridorId, FutureCapacityReservation, InstalledProcessCapacity,
    MaterialCircuitError, ProcessId, RollingCapacitySupply, SharedCapacitySupply, SiteId,
};

pub(super) fn append(
    bytes: &mut Vec<u8>,
    supply: &CapacitySupply,
) -> Result<(), MaterialCircuitError> {
    match supply {
        CapacitySupply::FiniteSchedule => bytes.push(0),
        CapacitySupply::Rolling(rows) => {
            bytes.push(1);
            append_rows(bytes, &rows.installed_processes, |bytes, row| {
                bytes.extend_from_slice(&row.process_id.as_bytes());
                bytes.extend_from_slice(&row.site_id.as_bytes());
                bytes.extend_from_slice(&row.batches_per_period.to_be_bytes());
            })?;
            append_rows(bytes, &rows.shared, |bytes, row| {
                bytes.extend_from_slice(&row.corridor_id.as_bytes());
                bytes.extend_from_slice(&row.grams_per_period.to_be_bytes());
            })?;
            append_rows(bytes, &rows.future_reservations, |bytes, row| {
                bytes.extend_from_slice(&row.departure_period.to_be_bytes());
                bytes.extend_from_slice(&row.corridor_id.as_bytes());
                bytes.extend_from_slice(&row.reserved_grams.to_be_bytes());
            })?;
        }
    }
    Ok(())
}

pub(super) fn decode(cursor: &mut Cursor<'_>) -> Result<CapacitySupply, MaterialCircuitError> {
    match cursor.u8()? {
        0 => Ok(CapacitySupply::FiniteSchedule),
        1 => Ok(CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
            installed_processes: decode_rows(cursor, |row| {
                Ok(InstalledProcessCapacity {
                    process_id: ProcessId::from_bytes(row.array()?),
                    site_id: SiteId::from_bytes(row.array()?),
                    batches_per_period: row.u64()?,
                })
            })?,
            shared: decode_rows(cursor, |row| {
                Ok(SharedCapacitySupply {
                    corridor_id: CorridorId::from_bytes(row.array()?),
                    grams_per_period: row.u64()?,
                })
            })?,
            future_reservations: decode_rows(cursor, |row| {
                Ok(FutureCapacityReservation {
                    departure_period: row.u64()?,
                    corridor_id: CorridorId::from_bytes(row.array()?),
                    reserved_grams: row.u64()?,
                })
            })?,
        }))),
        _ => Err(MaterialCircuitError::WireEnum),
    }
}
