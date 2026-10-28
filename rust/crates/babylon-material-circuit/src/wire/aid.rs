//! One current canonical gift authority, transport and cash-reserve state.
use super::accounting;
use super::Cursor;
use crate::{
    AidBook, AidCashReserve, AidFreightLot, FinalDemandPrincipalId, FreightLotId, GoodId,
    MaterialCircuitError, OrderId, RouteId, UnitId,
};
use std::result::Result as StdResult;

type Result<T> = StdResult<T, MaterialCircuitError>;

pub(super) fn append(out: &mut Vec<u8>, book: &AidBook, reserves: &[AidCashReserve]) -> Result<()> {
    accounting::ordered_rows(&book.freight, |r| r.lot_id)?;
    accounting::ordered_rows(reserves, |r| r.id)?;
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
    super::append_bounded_rows(
        out,
        reserves,
        crate::MAX_MATERIAL_ORDER_PRINCIPALS,
        |b, r| {
            b.extend_from_slice(&r.id.as_bytes());
            accounting::append_account(b, r.payer);
            b.extend_from_slice(&r.donor.as_bytes());
            b.extend_from_slice(&r.recipient.as_bytes());
            b.extend_from_slice(&r.quantity.to_be_bytes());
            b.extend_from_slice(&r.cash_per_unit.micro_units().to_be_bytes());
            b.extend_from_slice(&r.granted.to_be_bytes());
            b.extend_from_slice(&r.refunded.to_be_bytes());
        },
    )
}

pub(super) fn decode(cursor: &mut Cursor<'_>) -> Result<(AidBook, Vec<AidCashReserve>)> {
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
    let reserves = super::decode_bounded_rows(cursor, crate::MAX_MATERIAL_ORDER_PRINCIPALS, |b| {
        Ok(AidCashReserve {
            id: OrderId::from_bytes(b.array()?),
            payer: accounting::decode_account(b)?,
            donor: FinalDemandPrincipalId::from_bytes(b.array()?),
            recipient: FinalDemandPrincipalId::from_bytes(b.array()?),
            quantity: b.u64()?,
            cash_per_unit: accounting::decode_currency(b)?,
            granted: b.u64()?,
            refunded: b.u64()?,
        })
    })?;
    accounting::ordered_rows(&freight, |r| r.lot_id)?;
    accounting::ordered_rows(&reserves, |r| r.id)?;
    Ok((AidBook { freight }, reserves))
}
