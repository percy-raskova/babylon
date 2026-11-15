//! Equipment service is a native quantity independent of the instrument's price.
use super::assets;
use crate::recorded_labor::book::{Book, Frame};
use crate::recorded_labor::model::{LaborBasis, LaborNode, ReceiptRef, RecordedLaborError};
use crate::recorded_labor::LaborReceiptFamily;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    EquipmentCohortId, EquipmentWearReceipt, ProcessId, ProductiveEquipment, SiteId,
};

#[test]
fn zero_price_wear_carries_floor_shares_and_the_final_residual_to_output() {
    let process = ProcessId::from_bytes([1; 32]);
    let cohort = EquipmentCohortId::from_bytes([2; 32]);
    let source = LaborNode::equipment(cohort);
    let mut frame = Frame::new(Book::new());
    let seed = LaborBasis {
        recorded_micro_hours: 5,
        unknown_opening: true,
    };
    frame
        .credit(source, 3, seed)
        .expect("three remaining service batches");
    let free = Currency::from_micro_units(0);
    let mut receipt = EquipmentWearReceipt {
        period: 1,
        cohort_id: cohort,
        process_id: process,
        site_id: SiteId::from_bytes([3; 32]),
        opening_service_batches: 3,
        used_batches: 1,
        remaining_service_batches: 2,
        opening_carrying: free,
        carried_to_output: free,
        closing_carrying: free,
    };
    let first = assets::productive_assets(&mut frame, process, None, &[(8, &receipt)])
        .expect("first batch");
    assert_eq!(
        first,
        LaborBasis {
            recorded_micro_hours: 1,
            unknown_opening: true
        }
    );
    assert_eq!(
        frame.edges[0].receipt,
        ReceiptRef::new(LaborReceiptFamily::EquipmentWear, 8)
    );
    assert_eq!(frame.edges[0].destination, LaborNode::process(process));
    assert_eq!(
        assets::productive_assets(&mut frame, process, None, &[(8, &receipt)]),
        Err(RecordedLaborError::ReceiptMismatch("equipment wear"))
    );
    receipt.period = 2;
    receipt.opening_service_batches = 2;
    receipt.used_batches = 2;
    receipt.remaining_service_batches = 0;
    let last = assets::productive_assets(&mut frame, process, None, &[(0, &receipt)])
        .expect("last two batches");
    assert_eq!(last.recorded_micro_hours, 4);
    assert!(last.unknown_opening);
    assert_eq!(frame.quantity(source), 0);
    assert_eq!(frame.direct_micro_hours, 0);
}

fn equipment_case(process: ProcessId, site: SiteId) -> ProductiveEquipment {
    use babylon_material_circuit::{
        EquipmentBinding, EquipmentDefinition, EquipmentDefinitionId, GoodId, InstallationInput,
        UnitId,
    };
    let id = EquipmentDefinitionId::from_bytes([5; 32]);
    ProductiveEquipment {
        definitions: vec![EquipmentDefinition {
            id,
            equipment_good_id: GoodId::from_bytes([6; 32]),
            equipment_unit_id: UnitId::from_bytes([7; 32]),
            batches_per_unit_per_period: 1,
            service_batches_per_unit: 7,
            installation_labor_unit_id: UnitId::from_bytes([8; 32]),
            installation_hours_per_unit: 3,
        }],
        bindings: vec![EquipmentBinding {
            process_id: process,
            site_id: site,
            definition_id: id,
        }],
        installation_inputs: vec![InstallationInput {
            definition_id: id,
            good_id: GoodId::from_bytes([9; 32]),
            unit_id: UnitId::from_bytes([10; 32]),
            quantity_per_equipment_unit: 1,
        }],
        installation_policies: vec![],
        investment_policies: vec![],
    }
}

fn installation_frame(content: &ProductiveEquipment, site: SiteId) -> Frame {
    let body = &content.definitions[0];
    let spare = &content.installation_inputs[0];
    let mut frame = Frame::new(Book::new());
    frame
        .credit(
            LaborNode::site(site, body.equipment_good_id, body.equipment_unit_id),
            2,
            LaborBasis {
                recorded_micro_hours: 13,
                unknown_opening: true,
            },
        )
        .expect("unmounted equipment");
    frame
        .credit(
            LaborNode::site(site, spare.good_id, spare.unit_id),
            2,
            LaborBasis {
                recorded_micro_hours: 7,
                unknown_opening: false,
            },
        )
        .expect("installation inputs");
    frame
}

#[test]
fn installation_keeps_materials_and_actual_work_in_wip_until_the_cohort_exists() {
    use crate::production_projection::recurring_fixture;
    use babylon_material_circuit::{
        InstallationReceipt, InstalledEquipmentCohort, PendingInstallation,
    };
    let (_, mut after) = recurring_fixture::materials();
    let site = SiteId::from_bytes([3; 32]);
    let process = ProcessId::from_bytes([4; 32]);
    let content = equipment_case(process, site);
    let id = babylon_material_circuit::equipment_installation_id(1, process);
    let wip = LaborNode::installation(id);
    let mut frame = installation_frame(&content, site);
    let free = Currency::from_micro_units(0);
    let mut row = InstallationReceipt {
        period: 1,
        id,
        process_id: process,
        site_id: site,
        units: 2,
        started: true,
        opening_hours: 6,
        used_hours: 2,
        remaining_hours: 4,
        usable_from_period: 0,
        opening_carrying: free,
        materials_capitalized: free,
        wages_capitalized: free,
        closing_carrying: free,
    };
    after.period = 2;
    after.capacity_reservations.equipment.pending = vec![PendingInstallation {
        id,
        process_id: process,
        units: 2,
        started_period: 1,
        remaining_hours: 4,
    }];
    assets::installation(
        &mut frame,
        &content,
        &after,
        &row,
        ReceiptRef::new(LaborReceiptFamily::Installation, 0),
    )
    .expect("unfinished work");
    assert_eq!(frame.book[&wip].quantity, 2);
    assert_eq!(frame.book[&wip].basis.recorded_micro_hours, 2_000_020);
    assert!(frame.book[&wip].basis.unknown_opening);
    let cohort = EquipmentCohortId::from_bytes(id.as_bytes());
    row.period = 2;
    row.started = false;
    row.opening_hours = 4;
    row.used_hours = 4;
    row.remaining_hours = 0;
    row.usable_from_period = 3;
    after.period = 3;
    after.capacity_reservations.equipment.pending.clear();
    after.capacity_reservations.equipment.cohorts = vec![InstalledEquipmentCohort {
        id: cohort,
        process_id: process,
        units: 2,
        remaining_service_batches: 14,
        usable_from_period: 3,
    }];
    assets::installation(
        &mut frame,
        &content,
        &after,
        &row,
        ReceiptRef::new(LaborReceiptFamily::Installation, 1),
    )
    .expect("commissioned cohort");
    assert_eq!(frame.quantity(wip), 0);
    let installed = frame.book[&LaborNode::equipment(cohort)];
    assert_eq!(installed.quantity, 14);
    assert_eq!(
        installed.basis,
        LaborBasis {
            recorded_micro_hours: 6_000_020,
            unknown_opening: true
        }
    );
    assert_eq!(frame.direct_micro_hours, 6_000_000);
    assert_eq!(frame.released_micro_hours, 0);
}

#[test]
fn maintenance_keeps_next_service_and_releases_only_expired_opening_batches() {
    use babylon_material_circuit::{
        GoodId, MaintenanceBinding, MaintenanceReceipt, MaintenanceService, UnitId,
    };
    let process = ProcessId::from_bytes([4; 32]);
    let site = SiteId::from_bytes([5; 32]);
    let good = GoodId::from_bytes([6; 32]);
    let unit = UnitId::from_bytes([7; 32]);
    let node = LaborNode::maintenance(process);
    let parts = LaborNode::site(site, good, unit);
    let mut frame = Frame::new(Book::new());
    frame
        .credit(
            node,
            3,
            LaborBasis {
                recorded_micro_hours: 5,
                unknown_opening: false,
            },
        )
        .expect("previous service");
    frame
        .credit(
            parts,
            2,
            LaborBasis {
                recorded_micro_hours: 11,
                unknown_opening: true,
            },
        )
        .expect("spare parts");
    let row = MaintenanceReceipt {
        binding: MaintenanceBinding {
            provider_site_id: site,
            consumer_process_id: process,
            spare_good_id: good,
            spare_unit_id: unit,
            labor_unit_id: UnitId::from_bytes([8; 32]),
            spare_units_per_job: 1,
            labor_units_per_job: 2,
            enabled_batches_per_job: 2,
            maximum_jobs_per_period: 2,
        },
        period: 1,
        opening_service_batches: 3,
        consumed_service_batches: 1,
        expired_service_batches: 2,
        prospective_batches: 2,
        requested_jobs: 1,
        opening_spare_parts: 2,
        arrived_spare_parts: 0,
        available_spare_parts: 2,
        available_labor_hours: 2,
        completed_jobs: 1,
        consumed_spare_parts: 1,
        consumed_labor_hours: 2,
        next_service: MaintenanceService {
            period: 2,
            available_batches: 2,
        },
    };
    let produced = assets::productive_assets(&mut frame, process, Some(&row), &[])
        .expect("one service batch consumed");
    assert_eq!(produced.recorded_micro_hours, 1);
    assets::maintenance_close(&mut frame, &row)
        .expect("unused service expires and next period is enabled");
    assert_eq!(frame.released_micro_hours, 4);
    assert_eq!(frame.direct_micro_hours, 2_000_000);
    assert_eq!(frame.quantity(node), 2);
    assert_eq!(
        frame.book[&node].basis,
        LaborBasis {
            recorded_micro_hours: 2_000_005,
            unknown_opening: true
        }
    );
    assert_eq!(frame.book[&parts].basis.recorded_micro_hours, 6);
}
