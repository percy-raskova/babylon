//! One current canonical gift authority, transport and cash-reserve state.
use super::accounting::{append_account, decode_account, decode_currency, ordered_rows};
use super::{append_rows, decode_rows, Cursor};
use crate::{
    AidBook, AidCashReserve, AidFreightLot, AidMandate, AidTransport, FinalDemandPrincipalId,
    FreightLotId, GoodId, LogisticsNodeId, MaterialCircuitError, OrderId, RouteId, UnitId,
};

type Result<T> = std::result::Result<T, MaterialCircuitError>;

pub(super) fn append(out: &mut Vec<u8>, book: &AidBook, reserves: &[AidCashReserve]) -> Result<()> {
    ordered_rows(&book.mandates, |r| r.id)?;
    ordered_rows(&book.freight, |r| r.lot_id)?;
    ordered_rows(reserves, |r| r.id)?;
    append_rows(out, &book.mandates, |b, r| {
        b.extend_from_slice(&r.id);
        b.extend_from_slice(&r.source_hash);
        for actor in [r.donor_actor, r.donor_contributor_id, r.recipient_actor] {
            b.extend_from_slice(&actor.to_be_bytes());
        }
        append_account(b, r.payer);
        b.extend_from_slice(&r.donor.as_bytes());
        b.extend_from_slice(&r.recipient.as_bytes());
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.labor_unit_id.as_bytes());
        b.extend_from_slice(&r.hours_per_unit.to_be_bytes());
        b.extend_from_slice(&r.maximum_quantity.to_be_bytes());
        b.extend_from_slice(&r.cash_per_unit.micro_units().to_be_bytes());
        match r.transport {
            AidTransport::Local => b.push(1),
            AidTransport::Routed {
                route_id,
                from_node_id,
                to_node_id,
            } => {
                b.push(2);
                b.extend_from_slice(&route_id.as_bytes());
                b.extend_from_slice(&from_node_id.as_bytes());
                b.extend_from_slice(&to_node_id.as_bytes());
            }
        }
    })?;
    append_rows(out, &book.freight, |b, r| {
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
            append_account(b, r.payer);
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
    let mandates = decode_rows(cursor, |b| {
        let id = b.array()?;
        let source_hash = b.array()?;
        let donor_actor = b.u64()?;
        let donor_contributor_id = b.u64()?;
        let recipient_actor = b.u64()?;
        let payer = decode_account(b)?;
        let donor = FinalDemandPrincipalId::from_bytes(b.array()?);
        let recipient = FinalDemandPrincipalId::from_bytes(b.array()?);
        let good_id = GoodId::from_bytes(b.array()?);
        let unit_id = UnitId::from_bytes(b.array()?);
        let labor_unit_id = UnitId::from_bytes(b.array()?);
        let hours_per_unit = b.u64()?;
        let maximum_quantity = b.u64()?;
        let cash_per_unit = decode_currency(b)?;
        let transport = match b.u8()? {
            1 => AidTransport::Local,
            2 => AidTransport::Routed {
                route_id: RouteId::from_bytes(b.array()?),
                from_node_id: LogisticsNodeId::from_bytes(b.array()?),
                to_node_id: LogisticsNodeId::from_bytes(b.array()?),
            },
            _ => return Err(MaterialCircuitError::WireEnum),
        };
        let row = AidMandate {
            id,
            source_hash,
            donor_actor,
            donor_contributor_id,
            recipient_actor,
            payer,
            donor,
            recipient,
            good_id,
            unit_id,
            labor_unit_id,
            hours_per_unit,
            maximum_quantity,
            cash_per_unit,
            transport,
        };
        row.validate()?;
        Ok(row)
    })?;
    let freight = decode_rows(cursor, |b| {
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
            payer: decode_account(b)?,
            donor: FinalDemandPrincipalId::from_bytes(b.array()?),
            recipient: FinalDemandPrincipalId::from_bytes(b.array()?),
            quantity: b.u64()?,
            cash_per_unit: decode_currency(b)?,
            granted: b.u64()?,
            refunded: b.u64()?,
        })
    })?;
    ordered_rows(&mandates, |r| r.id)?;
    ordered_rows(&freight, |r| r.lot_id)?;
    ordered_rows(&reserves, |r| r.id)?;
    Ok((AidBook { mandates, freight }, reserves))
}
