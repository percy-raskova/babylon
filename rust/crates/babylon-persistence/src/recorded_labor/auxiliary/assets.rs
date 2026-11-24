//! Installation work in progress, maintenance service and equipment wear.
use super::super::book::{Frame, Result};
use super::super::model::{LaborBasis, LaborNode, ReceiptRef, RecordedLaborError};
use super::super::view::PeriodView;
use crate::recorded_labor::LaborDisposition;
use crate::recorded_labor::LaborReceiptFamily;

use babylon_material_circuit::{
    EquipmentCohortId, EquipmentDefinition, EquipmentWearReceipt, InstallationReceipt,
    MaintenanceReceipt, MaterialCatalog, MaterialCircuitState, ProcessId, ProductiveEquipment,
};

pub(in super::super) fn productive_assets(
    frame: &mut Frame,
    process: ProcessId,
    maintenance: Option<&MaintenanceReceipt>,
    wear: &[(usize, &EquipmentWearReceipt)],
) -> Result<LaborBasis> {
    let target = LaborNode::process(process);
    let mut total = LaborBasis::default();
    if let Some(row) = maintenance.filter(|r| r.binding.consumer_process_id == process) {
        let source = LaborNode::maintenance(process);
        if frame.quantity(source) != row.opening_service_batches {
            return Err(RecordedLaborError::ReceiptMismatch("maintenance opening"));
        }
        let used = row.consumed_service_batches;
        let basis = frame.take(source, used)?;
        frame.edge(
            source,
            target,
            used,
            basis,
            ReceiptRef::new(LaborReceiptFamily::Maintenance, 0),
        );
        total = basis;
    }
    for &(ordinal, row) in wear {
        let source = LaborNode::equipment(row.cohort_id);
        if row.process_id != process
            || row.used_batches == 0
            || row.used_batches.checked_add(row.remaining_service_batches)
                != Some(row.opening_service_batches)
            || frame.quantity(source) != row.opening_service_batches
        {
            return Err(RecordedLaborError::ReceiptMismatch("equipment wear"));
        }
        let basis = frame.take(source, row.used_batches)?;
        frame.edge(
            source,
            target,
            row.used_batches,
            basis,
            ReceiptRef::new(LaborReceiptFamily::EquipmentWear, ordinal),
        );
        total = total.add(basis)?;
    }
    Ok(total)
}

pub(in super::super) fn maintenance_and_installation(
    frame: &mut Frame,
    catalog: &MaterialCatalog,
    view: &PeriodView<'_>,
) -> Result<()> {
    let after = view.after;
    match (
        &catalog.maintenance_binding,
        view.receipts.maintenance,
        after.maintenance_service,
    ) {
        (None, None, None) => {}
        (Some(binding), Some(row), Some(next))
            if *binding == row.binding && next == row.next_service && row.period == view.period =>
        {
            maintenance_close(frame, row)?;
        }
        _ => return Err(RecordedLaborError::ReceiptMismatch("maintenance service")),
    }
    if !view.receipts.installation.is_empty() {
        let content = catalog
            .equipment_content()
            .ok_or(RecordedLaborError::ReceiptMismatch(
                "installation definition",
            ))?;
        for (ordinal, row) in view.receipts.installation.iter().enumerate() {
            installation(
                frame,
                content,
                after,
                row,
                ReceiptRef::new(LaborReceiptFamily::Installation, ordinal),
            )?;
        }
    }
    Ok(())
}

pub(super) fn maintenance_close(frame: &mut Frame, row: &MaintenanceReceipt) -> Result<()> {
    let binding = &row.binding;
    let node = LaborNode::maintenance(binding.consumer_process_id);
    let receipt = ReceiptRef::new(LaborReceiptFamily::Maintenance, 0);
    if row
        .expired_service_batches
        .checked_add(row.consumed_service_batches)
        != Some(row.opening_service_batches)
        || frame.quantity(node) != row.expired_service_batches
        || row.completed_jobs.checked_mul(binding.spare_units_per_job)
            != Some(row.consumed_spare_parts)
        || row.completed_jobs.checked_mul(binding.labor_units_per_job)
            != Some(row.consumed_labor_hours)
        || row
            .completed_jobs
            .checked_mul(binding.enabled_batches_per_job)
            != Some(row.next_service.available_batches)
        || row.period.checked_add(1) != Some(row.next_service.period)
    {
        return Err(RecordedLaborError::ReceiptMismatch("maintenance close"));
    }
    frame.release(
        node,
        LaborNode::sink(LaborDisposition::MaintenanceExpiry),
        row.expired_service_batches,
        receipt,
    )?;
    let parts = LaborNode::site(
        binding.provider_site_id,
        binding.spare_good_id,
        binding.spare_unit_id,
    );
    if frame.quantity(parts) != row.available_spare_parts {
        return Err(RecordedLaborError::ReceiptMismatch("maintenance parts"));
    }
    let basis = frame.take(parts, row.consumed_spare_parts)?;
    frame.edge(parts, node, row.consumed_spare_parts, basis, receipt);
    let work = frame.direct(
        LaborNode::work(binding.provider_site_id, binding.labor_unit_id),
        node,
        row.consumed_labor_hours,
        receipt,
    )?;
    frame.credit(node, row.next_service.available_batches, basis.add(work)?)
}

pub(super) fn installation(
    frame: &mut Frame,
    content: &ProductiveEquipment,
    after: &MaterialCircuitState,
    row: &InstallationReceipt,
    receipt: ReceiptRef,
) -> Result<()> {
    let mismatch = RecordedLaborError::ReceiptMismatch("installation");
    let index = content
        .bindings
        .binary_search_by_key(&row.process_id, |b| b.process_id)
        .map_err(|_| mismatch)?;
    let binding = &content.bindings[index];
    let index = content
        .definitions
        .binary_search_by_key(&binding.definition_id, |d| d.id)
        .map_err(|_| mismatch)?;
    let definition = &content.definitions[index];
    let wip = LaborNode::installation(row.id);
    if binding.site_id != row.site_id
        || row.units == 0
        || row.opening_hours == 0
        || row.period.checked_add(1) != Some(after.period)
        || row.used_hours.checked_add(row.remaining_hours) != Some(row.opening_hours)
        || frame.quantity(wip) != if row.started { 0 } else { row.units }
    {
        return Err(mismatch);
    }
    let materials = if row.started {
        if row.id != babylon_material_circuit::equipment_installation_id(row.period, row.process_id)
            || row
                .units
                .checked_mul(definition.installation_hours_per_unit)
                != Some(row.opening_hours)
        {
            return Err(mismatch);
        }
        installation_inputs(frame, content, definition, row, receipt)?
    } else {
        frame.take(wip, row.units)?
    };
    let work = frame.direct(
        LaborNode::work(row.site_id, definition.installation_labor_unit_id),
        wip,
        row.used_hours,
        receipt,
    )?;
    let basis = materials.add(work)?;
    let assets = &after.capacity_reservations.equipment;
    if row.remaining_hours > 0 {
        let index = assets
            .pending
            .binary_search_by_key(&(row.process_id, row.id), |p| (p.process_id, p.id))
            .map_err(|_| mismatch)?;
        let project = &assets.pending[index];
        if project.units != row.units
            || project.remaining_hours != row.remaining_hours
            || row.usable_from_period != 0
        {
            return Err(mismatch);
        }
        return frame.credit(wip, row.units, basis);
    }
    let id = EquipmentCohortId::from_bytes(row.id.as_bytes());
    let index = assets
        .cohorts
        .binary_search_by_key(&(row.process_id, id), |p| (p.process_id, p.id))
        .map_err(|_| mismatch)?;
    let cohort = &assets.cohorts[index];
    let batches = row
        .units
        .checked_mul(definition.service_batches_per_unit)
        .ok_or(RecordedLaborError::Arithmetic)?;
    if cohort.units != row.units
        || cohort.remaining_service_batches != batches
        || cohort.usable_from_period != after.period
        || row.usable_from_period != after.period
    {
        return Err(mismatch);
    }
    let installed = LaborNode::equipment(id);
    frame.edge(wip, installed, row.units, basis, receipt);
    frame.credit(installed, batches, basis)
}

fn installation_inputs(
    frame: &mut Frame,
    content: &ProductiveEquipment,
    definition: &EquipmentDefinition,
    row: &InstallationReceipt,
    receipt: ReceiptRef,
) -> Result<LaborBasis> {
    let first = content
        .installation_inputs
        .partition_point(|r| r.definition_id < definition.id);
    let complements = content.installation_inputs[first..]
        .iter()
        .take_while(|r| r.definition_id == definition.id)
        .map(|r| (r.good_id, r.unit_id, r.quantity_per_equipment_unit));
    let machine = (
        definition.equipment_good_id,
        definition.equipment_unit_id,
        1,
    );
    let mut total = LaborBasis::default();
    for (good, unit, coefficient) in std::iter::once(machine).chain(complements) {
        let quantity = row
            .units
            .checked_mul(coefficient)
            .ok_or(RecordedLaborError::Arithmetic)?;
        let source = LaborNode::site(row.site_id, good, unit);
        let basis = frame.take(source, quantity)?;
        frame.edge(
            source,
            LaborNode::installation(row.id),
            quantity,
            basis,
            receipt,
        );
        total = total.add(basis)?;
    }
    Ok(total)
}
