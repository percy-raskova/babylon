//! Installation choice and actual starts share one committed period.
use super::{MaterialWorldError, ReceiptCursor};
use babylon_material_circuit::{
    InstallationDecisionReceipt, InstallationReceipt, ProcessId, SiteId,
};
use std::collections::BTreeMap;

pub(super) const ROW_BYTES: usize = 120;
pub(super) fn encode(
    rows: &[InstallationDecisionReceipt],
    period: u64,
    out: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for row in rows {
        row.validate().map_err(|_| MaterialWorldError::Wire)?;
        if row.period != period {
            return Err(MaterialWorldError::Wire);
        }
        out.extend_from_slice(&row.period.to_be_bytes());
        out.extend_from_slice(&row.process_id.as_bytes());
        out.extend_from_slice(&row.site_id.as_bytes());
        for value in [
            row.captured_plan_batches,
            row.target_units,
            row.installed_units,
            row.pending_units,
            row.requested_units,
            row.started_units,
        ] {
            out.extend_from_slice(&value.to_be_bytes());
        }
    }
    Ok(())
}
pub(super) fn decode(
    c: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<InstallationDecisionReceipt, MaterialWorldError> {
    let row = InstallationDecisionReceipt {
        period: c.u64()?,
        process_id: ProcessId::from_bytes(c.take()?),
        site_id: SiteId::from_bytes(c.take()?),
        captured_plan_batches: c.u64()?,
        target_units: c.u64()?,
        installed_units: c.u64()?,
        pending_units: c.u64()?,
        requested_units: c.u64()?,
        started_units: c.u64()?,
    };
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(row)
}
pub(super) fn validate(
    rows: &[InstallationDecisionReceipt],
    work: &[InstallationReceipt],
) -> Result<(), MaterialWorldError> {
    if rows
        .windows(2)
        .any(|pair| pair[0].process_id >= pair[1].process_id)
    {
        return Err(MaterialWorldError::Wire);
    }
    let mut actual = BTreeMap::<_, (u64, u64)>::new();
    for row in work {
        let entry = actual.entry((row.process_id, row.site_id)).or_default();
        let quantity = if row.started {
            &mut entry.0
        } else {
            &mut entry.1
        };
        *quantity = quantity
            .checked_add(row.units)
            .ok_or(MaterialWorldError::Arithmetic)?;
    }
    for row in rows {
        row.validate().map_err(|_| MaterialWorldError::Wire)?;
        if actual
            .remove(&(row.process_id, row.site_id))
            .unwrap_or_default()
            != (row.started_units, row.pending_units)
        {
            return Err(MaterialWorldError::Wire);
        }
    }
    if !actual.is_empty() {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
