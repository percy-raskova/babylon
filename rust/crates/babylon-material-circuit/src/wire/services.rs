use super::{append_rows, decode_rows, Cursor};
use crate::{
    CommodityDefinition, CommodityKind, GoodId, MaterialCircuitError, OrderId, ServiceConnection,
    ServiceOrder, ServiceStage, SiteId, UnitId,
};
pub(super) fn append_commodities(
    out: &mut Vec<u8>,
    rows: &[CommodityDefinition],
) -> Result<(), MaterialCircuitError> {
    append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        match r.kind {
            CommodityKind::Storable { grams_per_unit } => {
                b.push(1);
                b.extend_from_slice(&grams_per_unit.to_be_bytes());
            }
            CommodityKind::PeriodService { stage } => {
                b.push(2);
                b.push(stage as u8);
            }
        }
    })
}
pub(super) fn decode_commodities(
    c: &mut Cursor<'_>,
) -> Result<Vec<CommodityDefinition>, MaterialCircuitError> {
    decode_rows(c, |b| {
        Ok(CommodityDefinition {
            good_id: GoodId::from_bytes(b.array()?),
            unit_id: UnitId::from_bytes(b.array()?),
            kind: match b.u8()? {
                1 => CommodityKind::Storable {
                    grams_per_unit: b.u64()?,
                },
                2 => CommodityKind::PeriodService {
                    stage: match b.u8()? {
                        1 => ServiceStage::UtilityProvision,
                        2 => ServiceStage::LocalServiceProvision,
                        _ => return Err(MaterialCircuitError::WireEnum),
                    },
                },
                _ => return Err(MaterialCircuitError::WireEnum),
            },
        })
    })
}
pub(super) fn append_connections(
    out: &mut Vec<u8>,
    rows: &[ServiceConnection],
) -> Result<(), MaterialCircuitError> {
    append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.provider_site_id.as_bytes());
        super::accounting::append_account(b, r.buyer);
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
    })
}
pub(super) fn decode_connections(
    c: &mut Cursor<'_>,
) -> Result<Vec<ServiceConnection>, MaterialCircuitError> {
    decode_rows(c, |b| {
        Ok(ServiceConnection {
            provider_site_id: SiteId::from_bytes(b.array()?),
            buyer: super::accounting::decode_account(b)?,
            good_id: GoodId::from_bytes(b.array()?),
            unit_id: UnitId::from_bytes(b.array()?),
        })
    })
}
pub(super) fn append_orders(
    out: &mut Vec<u8>,
    rows: &[ServiceOrder],
) -> Result<(), MaterialCircuitError> {
    append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.order_id.as_bytes());
        b.extend_from_slice(&r.performance_period.to_be_bytes());
        b.extend_from_slice(&r.provider_site_id.as_bytes());
        super::accounting::append_account(b, r.buyer);
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.quantity.to_be_bytes());
    })
}
pub(super) fn decode_orders(c: &mut Cursor<'_>) -> Result<Vec<ServiceOrder>, MaterialCircuitError> {
    decode_rows(c, |b| {
        Ok(ServiceOrder {
            order_id: OrderId::from_bytes(b.array()?),
            performance_period: b.u64()?,
            provider_site_id: SiteId::from_bytes(b.array()?),
            buyer: super::accounting::decode_account(b)?,
            good_id: GoodId::from_bytes(b.array()?),
            unit_id: UnitId::from_bytes(b.array()?),
            quantity: b.u64()?,
        })
    })
}
