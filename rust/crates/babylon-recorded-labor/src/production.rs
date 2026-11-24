//! Reconstruct actual recipe debits before any outputs of the same phase become available.
use crate::auxiliary;
use crate::book::{Frame, Result};
use crate::model::{LaborBasis, LaborNode, LaborReceiptFamily, ReceiptRef, RecordedLaborError};
use crate::services;
use crate::view::PeriodView;
use babylon_material_circuit::{
    CommodityKind, EquipmentWearReceipt, GoodId, MaintenanceReceipt, MaterialCatalog,
    ProcessOutput, ProductionReceipt, ServiceStage, UnitId,
};
use std::collections::BTreeMap;

pub(crate) fn stage(
    catalog: &MaterialCatalog,
    good: GoodId,
    unit: UnitId,
) -> Result<Option<ServiceStage>> {
    let index = catalog
        .commodities
        .binary_search_by_key(&(good, unit), |r| (r.good_id, r.unit_id))
        .map_err(|_| RecordedLaborError::ReceiptMismatch("commodity definition"))?;
    Ok(match catalog.commodities[index].kind {
        CommodityKind::Storable { .. } => None,
        CommodityKind::PeriodService { stage } => Some(stage),
    })
}

struct Batch<'a> {
    row: &'a ProductionReceipt,
    output: &'a ProcessOutput,
    receipt: ReceiptRef,
}

fn inputs(frame: &mut Frame, catalog: &MaterialCatalog, batch: &Batch<'_>) -> Result<LaborBasis> {
    let process = batch.row.process_id;
    let coefficients = &catalog.input_coefficients;
    let start = coefficients.partition_point(|r| r.process_id < process);
    let end = coefficients.partition_point(|r| r.process_id <= process);
    let mut total = LaborBasis::default();
    for row in &coefficients[start..end] {
        let source = LaborNode::site(batch.row.site_id, row.good_id, row.unit_id);
        let qty = batch
            .row
            .produced_batches
            .checked_mul(row.quantity_per_batch)
            .ok_or(RecordedLaborError::Arithmetic)?;
        let basis = frame.take(source, qty)?;
        frame.edge(
            source,
            LaborNode::process(process),
            qty,
            basis,
            batch.receipt,
        );
        total = total.add(basis)?;
    }
    Ok(total)
}

fn output(
    frame: &mut Frame,
    catalog: &MaterialCatalog,
    batch: &Batch<'_>,
    inputs: LaborBasis,
    maintenance: Option<&MaintenanceReceipt>,
    wear: &[(usize, &EquipmentWearReceipt)],
) -> Result<()> {
    let process = batch.row.process_id;
    let labor = catalog
        .labor_coefficients
        .binary_search_by_key(&process, |r| r.process_id)
        .map(|i| &catalog.labor_coefficients[i])
        .map_err(|_| RecordedLaborError::UnknownProcess)?;
    let hours = labor
        .quantity_per_batch
        .checked_mul(batch.row.produced_batches)
        .ok_or(RecordedLaborError::Arithmetic)?;
    let quantity = batch
        .output
        .quantity_per_batch
        .checked_mul(batch.row.produced_batches)
        .ok_or(RecordedLaborError::Arithmetic)?;
    let assets = auxiliary::productive_assets(frame, process, maintenance, wear)?;
    let node = LaborNode::process(process);
    let direct = frame.direct(
        LaborNode::work(batch.row.site_id, labor.unit_id),
        node,
        hours,
        batch.receipt,
    )?;
    let basis = inputs.add(assets)?.add(direct)?;
    let target = LaborNode::site(
        batch.row.site_id,
        batch.output.good_id,
        batch.output.unit_id,
    );
    frame.credit(target, quantity, basis)?;
    frame.edge(node, target, quantity, basis, batch.receipt);
    Ok(())
}

/// Production: inputs, work and outputs, stage by stage, with the services handed over after each.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn execute(frame: &mut Frame, catalog: &MaterialCatalog, view: &PeriodView<'_>) -> Result<()> {
    let mut phases = BTreeMap::new();
    for (ordinal, row) in view.receipts.production.iter().enumerate() {
        let output = catalog
            .process_outputs
            .binary_search_by_key(&row.process_id, |o| o.process_id)
            .map(|i| &catalog.process_outputs[i])
            .map_err(|_| RecordedLaborError::UnknownProcess)?;
        if output.site_id != row.site_id || row.produced_batches > row.planned_batches {
            return Err(RecordedLaborError::ReceiptMismatch("production"));
        }
        let phase = stage(catalog, output.good_id, output.unit_id)?;
        phases.entry(phase).or_insert_with(Vec::new).push(Batch {
            row,
            output,
            receipt: ReceiptRef::new(LaborReceiptFamily::Production, ordinal),
        });
    }
    let mut wear = BTreeMap::new();
    for (ordinal, row) in view.receipts.equipment_wear.iter().enumerate() {
        wear.entry(row.process_id)
            .or_insert_with(Vec::new)
            .push((ordinal, row));
    }
    for phase in [
        Some(ServiceStage::UtilityProvision),
        Some(ServiceStage::LocalServiceProvision),
        None,
    ] {
        if let Some(batches) = phases.remove(&phase) {
            let debits = batches
                .iter()
                .map(|b| inputs(frame, catalog, b))
                .collect::<Result<Vec<_>>>()?;
            for (batch, debit) in batches.iter().zip(debits) {
                let cohorts = wear.remove(&batch.row.process_id).unwrap_or_default();
                output(
                    frame,
                    catalog,
                    batch,
                    debit,
                    view.receipts.maintenance,
                    &cohorts,
                )?;
            }
        }
        if let Some(phase) = phase {
            services::handoff(frame, catalog, phase, view)?;
        }
    }
    if !wear.is_empty() {
        return Err(RecordedLaborError::ReceiptMismatch("equipment_wear"));
    }
    services::finish(frame, view)
}
