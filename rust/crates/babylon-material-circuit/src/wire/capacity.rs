//! Exact explicit capacity source and advance-booking state.
use super::{append_rows, decode_rows, Cursor};
use crate::{
    CapacitySupply, CorridorId, FutureCapacityReservation, InstalledProcessCapacity,
    MaterialCircuitError, ProcessId, RollingCapacitySupply, RollingProcessSupply,
    SharedCapacitySupply, SiteId,
};

pub(super) fn append(
    bytes: &mut Vec<u8>,
    supply: &CapacitySupply,
) -> Result<(), MaterialCircuitError> {
    match supply {
        CapacitySupply::FiniteSchedule => bytes.push(0),
        CapacitySupply::Rolling(rows) => {
            bytes.push(1);
            match &rows.processes {
                RollingProcessSupply::CapturedNameplate(installed) => {
                    bytes.push(0);
                    append_rows(bytes, installed, |b, r| {
                        b.extend_from_slice(&r.process_id.as_bytes());
                        b.extend_from_slice(&r.site_id.as_bytes());
                        b.extend_from_slice(&r.batches_per_period.to_be_bytes());
                    })?;
                }
                RollingProcessSupply::Equipment(e) => {
                    bytes.push(1);
                    super::equipment::append(bytes, e)?;
                }
            }
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
            processes: match cursor.u8()? {
                0 => RollingProcessSupply::CapturedNameplate(decode_rows(cursor, |r| {
                    Ok(InstalledProcessCapacity {
                        process_id: ProcessId::from_bytes(r.array()?),
                        site_id: SiteId::from_bytes(r.array()?),
                        batches_per_period: r.u64()?,
                    })
                })?),
                1 => RollingProcessSupply::Equipment(Box::new(super::equipment::decode(cursor)?)),
                _ => return Err(MaterialCircuitError::WireEnum),
            },
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
