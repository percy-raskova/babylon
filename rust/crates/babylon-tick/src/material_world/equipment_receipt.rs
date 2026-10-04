//! Exact bounded equipment receipt families; no absent-state assumptions.
use super::{MaterialWorldError, ReceiptCursor};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    EquipmentCohortId, EquipmentWearReceipt, InstallationId, InstallationReceipt,
    InvestmentReceipt, OrderId, ProcessId, SiteId,
};
use std::collections::BTreeSet;
pub(super) const INSTALLATION_BYTES: usize = 209;
pub(super) fn encode_installation(
    rows: &[InstallationReceipt],
    period: u64,
    b: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for r in rows {
        r.validate().map_err(|_| MaterialWorldError::Wire)?;
        if r.period != period {
            return Err(MaterialWorldError::Wire);
        }
        b.extend_from_slice(&r.period.to_be_bytes());
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.site_id.as_bytes());
        b.extend_from_slice(&r.units.to_be_bytes());
        b.push(u8::from(r.started));
        b.extend_from_slice(&r.opening_hours.to_be_bytes());
        b.extend_from_slice(&r.used_hours.to_be_bytes());
        b.extend_from_slice(&r.remaining_hours.to_be_bytes());
        b.extend_from_slice(&r.usable_from_period.to_be_bytes());
        b.extend_from_slice(&r.opening_carrying.micro_units().to_be_bytes());
        b.extend_from_slice(&r.materials_capitalized.micro_units().to_be_bytes());
        b.extend_from_slice(&r.wages_capitalized.micro_units().to_be_bytes());
        b.extend_from_slice(&r.closing_carrying.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_installation(
    c: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<InstallationReceipt, MaterialWorldError> {
    let r = InstallationReceipt {
        period: c.u64()?,
        id: InstallationId::from_bytes(c.take()?),
        process_id: ProcessId::from_bytes(c.take()?),
        site_id: SiteId::from_bytes(c.take()?),
        units: c.u64()?,
        started: match c.take::<1>()?[0] {
            0 => false,
            1 => true,
            _ => return Err(MaterialWorldError::Wire),
        },
        opening_hours: c.u64()?,
        used_hours: c.u64()?,
        remaining_hours: c.u64()?,
        usable_from_period: c.u64()?,
        opening_carrying: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        materials_capitalized: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        wages_capitalized: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        closing_carrying: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
    };
    r.validate().map_err(|_| MaterialWorldError::Wire)?;
    if r.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(r)
}
pub(super) const WEAR_BYTES: usize = 176;
pub(super) fn encode_wear(
    rows: &[EquipmentWearReceipt],
    period: u64,
    b: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for r in rows {
        r.validate().map_err(|_| MaterialWorldError::Wire)?;
        if r.period != period {
            return Err(MaterialWorldError::Wire);
        }
        b.extend_from_slice(&r.period.to_be_bytes());
        b.extend_from_slice(&r.cohort_id.as_bytes());
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.site_id.as_bytes());
        b.extend_from_slice(&r.opening_service_batches.to_be_bytes());
        b.extend_from_slice(&r.used_batches.to_be_bytes());
        b.extend_from_slice(&r.remaining_service_batches.to_be_bytes());
        b.extend_from_slice(&r.opening_carrying.micro_units().to_be_bytes());
        b.extend_from_slice(&r.carried_to_output.micro_units().to_be_bytes());
        b.extend_from_slice(&r.closing_carrying.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_wear(
    c: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<EquipmentWearReceipt, MaterialWorldError> {
    let r = EquipmentWearReceipt {
        period: c.u64()?,
        cohort_id: EquipmentCohortId::from_bytes(c.take()?),
        process_id: ProcessId::from_bytes(c.take()?),
        site_id: SiteId::from_bytes(c.take()?),
        opening_service_batches: c.u64()?,
        used_batches: c.u64()?,
        remaining_service_batches: c.u64()?,
        opening_carrying: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        carried_to_output: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        closing_carrying: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
    };
    r.validate().map_err(|_| MaterialWorldError::Wire)?;
    if r.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(r)
}
pub(super) const INVESTMENT_BYTES: usize = 272;
pub(super) fn encode_investment(
    rows: &[InvestmentReceipt],
    period: u64,
    b: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for r in rows {
        r.validate().map_err(|_| MaterialWorldError::Wire)?;
        if r.period != period {
            return Err(MaterialWorldError::Wire);
        }
        b.extend_from_slice(&r.period.to_be_bytes());
        b.extend_from_slice(&r.order_id.as_bytes());
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.site_id.as_bytes());
        b.extend_from_slice(&r.supplier_site_id.as_bytes());
        b.extend_from_slice(&r.installed_units.to_be_bytes());
        b.extend_from_slice(&r.pending_units.to_be_bytes());
        b.extend_from_slice(&r.on_hand_units.to_be_bytes());
        b.extend_from_slice(&r.outstanding_inbound_units.to_be_bytes());
        b.extend_from_slice(&r.captured_plan_batches.to_be_bytes());
        b.extend_from_slice(&r.accepted_output_orders.to_be_bytes());
        b.extend_from_slice(&r.output_stock.to_be_bytes());
        b.extend_from_slice(&r.output_buffer.to_be_bytes());
        b.extend_from_slice(&r.replacement_requested_units.to_be_bytes());
        b.extend_from_slice(&r.expansion_requested_units.to_be_bytes());
        b.extend_from_slice(&r.admitted_units.to_be_bytes());
        b.extend_from_slice(&r.unit_price.micro_units().to_be_bytes());
        b.extend_from_slice(&r.free_cash.micro_units().to_be_bytes());
        b.extend_from_slice(&r.earnings_budget.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_investment(
    c: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<InvestmentReceipt, MaterialWorldError> {
    let r = InvestmentReceipt {
        period: c.u64()?,
        order_id: OrderId::from_bytes(c.take()?),
        process_id: ProcessId::from_bytes(c.take()?),
        site_id: SiteId::from_bytes(c.take()?),
        supplier_site_id: SiteId::from_bytes(c.take()?),
        installed_units: c.u64()?,
        pending_units: c.u64()?,
        on_hand_units: c.u64()?,
        outstanding_inbound_units: c.u64()?,
        captured_plan_batches: c.u64()?,
        accepted_output_orders: c.u64()?,
        output_stock: c.u64()?,
        output_buffer: c.u64()?,
        replacement_requested_units: c.u64()?,
        expansion_requested_units: c.u64()?,
        admitted_units: c.u64()?,
        unit_price: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        free_cash: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        earnings_budget: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
    };
    r.validate().map_err(|_| MaterialWorldError::Wire)?;
    if r.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(r)
}
pub(super) fn validate_order(
    installation: &[InstallationReceipt],
    wear: &[EquipmentWearReceipt],
    investment: &[InvestmentReceipt],
) -> Result<(), MaterialWorldError> {
    if installation.windows(2).any(|p| {
        let key = |r: &InstallationReceipt| (r.process_id, r.id);
        key(&p[0]) >= key(&p[1])
    }) {
        return Err(MaterialWorldError::Wire);
    }
    if wear.windows(2).any(|p| {
        let key = |r: &EquipmentWearReceipt| (r.process_id, r.cohort_id);
        key(&p[0]) >= key(&p[1])
    }) {
        return Err(MaterialWorldError::Wire);
    }
    if investment.windows(2).any(|p| {
        let key = |r: &InvestmentReceipt| r.process_id;
        key(&p[0]) >= key(&p[1])
    }) {
        return Err(MaterialWorldError::Wire);
    }
    if installation
        .iter()
        .map(|r| r.id)
        .collect::<BTreeSet<_>>()
        .len()
        != installation.len()
        || wear
            .iter()
            .map(|r| r.cohort_id)
            .collect::<BTreeSet<_>>()
            .len()
            != wear.len()
        || investment
            .iter()
            .map(|r| r.order_id)
            .collect::<BTreeSet<_>>()
            .len()
            != investment.len()
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

#[cfg(test)]
mod tests;

mod join;
pub(super) use join::{validate_installation, validate_investment, validate_wear};
