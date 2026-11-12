//! One current canonical gift authority and physical transport state.
use super::accounting;
use super::Cursor;
use crate::{
    AidBook, AidFreightLot, FinalDemandPrincipalId, FreightLotId, GoodId, MaterialCircuitError,
    OrderId, RouteId, UnitId,
};
use std::result::Result as StdResult;

type Result<T> = StdResult<T, MaterialCircuitError>;

pub(super) fn append(out: &mut Vec<u8>, book: &AidBook) -> Result<()> {
    accounting::ordered_rows(&book.freight, |r| r.lot_id)?;
    super::append_rows(out, &book.freight, |b, r| {
        b.extend_from_slice(&r.lot_id.as_bytes());
        b.extend_from_slice(&r.commitment_id.as_bytes());
        b.extend_from_slice(&r.mandate_id);
        b.extend_from_slice(&r.route_id.as_bytes());
        b.extend_from_slice(&r.dispatch_period.to_be_bytes());
        b.extend_from_slice(&r.current_stage_index.to_be_bytes());
        b.extend_from_slice(&r.stage_arrival_period.to_be_bytes());
        b.extend_from_slice(&r.donor.as_bytes());
        b.extend_from_slice(&r.recipient.as_bytes());
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.quantity.to_be_bytes());
    })?;
    Ok(())
}

pub(super) fn decode(cursor: &mut Cursor<'_>) -> Result<AidBook> {
    let freight = super::decode_rows(cursor, |b| {
        Ok(AidFreightLot {
            lot_id: FreightLotId::from_bytes(b.array()?),
            commitment_id: OrderId::from_bytes(b.array()?),
            mandate_id: b.array()?,
            route_id: RouteId::from_bytes(b.array()?),
            dispatch_period: b.u64()?,
            current_stage_index: b.u16()?,
            stage_arrival_period: b.u64()?,
            donor: FinalDemandPrincipalId::from_bytes(b.array()?),
            recipient: FinalDemandPrincipalId::from_bytes(b.array()?),
            good_id: GoodId::from_bytes(b.array()?),
            unit_id: UnitId::from_bytes(b.array()?),
            quantity: b.u64()?,
        })
    })?;
    accounting::ordered_rows(&freight, |r| r.lot_id)?;
    Ok(AidBook { freight })
}
