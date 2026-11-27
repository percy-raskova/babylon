//! Independently follow recorded hours through a real paid/unpaid material close.
use super::{RecordedLaborError, RecordedLaborLedger};
use crate::production_projection::recurring_fixture;
use crate::recorded_labor::LaborDisposition;
use crate::recorded_labor::LaborReceiptFamily;
use babylon_material_circuit::PendingInstallation;
use babylon_material_circuit::{CircuitAccounting, LaborCompensation};
use babylon_tick::material_world::{self, MaterialWorldRegister};

#[test]
fn committed_mixed_compensation_keeps_unknown_foundation_and_carries_recorded_labor() {
    let (catalog, mut state) = recurring_fixture::materials();
    let CircuitAccounting::Monetary(book) = &mut state.accounting else {
        panic!("paid fixture")
    };
    book.employment[0].compensation = LaborCompensation::UnpaidFamily;
    let first = MaterialWorldRegister::try_new(&catalog, 0, state)
        .expect("admitted mixed compensation fixture");
    let mut ledger =
        RecordedLaborLedger::from_foundation(&catalog, [9; 32], &first).expect("stock opening");
    let next = first.prepare_next(&catalog).expect("first actual close");
    let receipts =
        material_world::decode_material_receipts(next.receipt_bytes()).expect("first receipts");
    let mut inconsistent = receipts.clone();
    inconsistent.household_consumption[0].closing_quantity += 1;
    assert_eq!(
        ledger.advance(&catalog, &first, next.register(), &inconsistent),
        Err(RecordedLaborError::ReceiptMismatch("household_consumption"))
    );
    let report = ledger
        .advance(&catalog, &first, next.register(), &receipts)
        .expect("trace first close");
    assert_eq!(report.opening_recorded_micro_hours, 0);
    assert!(report.direct_micro_hours > 0);
    assert!(report.attendance.iter().any(|row| row.compensation
        == super::RecordedCompensation::UnpaidFamily
        && row.production_hours > 0));
    assert!(report
        .edges
        .iter()
        .any(|edge| edge.basis.unknown_opening && edge.basis.recorded_micro_hours > 0));
    assert_eq!(
        report.direct_micro_hours,
        report.closing_recorded_micro_hours + report.released_micro_hours
    );
    assert_eq!(
        report
            .attendance
            .iter()
            .map(|row| row.production_hours
                + row.handling_hours
                + row.installation_hours
                + row.maintenance_hours)
            .map(u128::from)
            .sum::<u128>()
            * super::MICROS_PER_HOUR,
        report.direct_micro_hours
    );
    let serialized = serde_json::to_value(&report).expect("wire-safe hours");
    assert_eq!(
        serialized["direct_micro_hours"].as_str(),
        Some(report.direct_micro_hours.to_string().as_str())
    );
    let later = next
        .register()
        .prepare_next(&catalog)
        .expect("second actual close");
    let receipts =
        material_world::decode_material_receipts(later.receipt_bytes()).expect("second receipts");
    let second = ledger
        .advance(&catalog, next.register(), later.register(), &receipts)
        .expect("trace second close");
    assert_eq!(report.closing_positions, second.opening_positions);
    assert_eq!(
        report.closing_recorded_micro_hours,
        second.opening_recorded_micro_hours
    );
    assert_eq!(
        second.opening_recorded_micro_hours + second.direct_micro_hours,
        second.closing_recorded_micro_hours + second.released_micro_hours
    );
}

#[test]
fn mixed_inventory_preserves_the_floor_remainder_through_transfer_and_depletion() {
    use super::{LaborBasis, LaborNode, ReceiptRef};
    use babylon_material_circuit::{GoodId, SiteId, UnitId};
    use babylon_recorded_labor::{Book, Frame};
    let good = GoodId::from_bytes([3; 32]);
    let quantity_unit = UnitId::from_bytes([4; 32]);
    let source = LaborNode::site(SiteId::from_bytes([1; 32]), good, quantity_unit);
    let buyer = LaborNode::site(SiteId::from_bytes([2; 32]), good, quantity_unit);
    let work = LaborNode::work(SiteId::from_bytes([1; 32]), UnitId::from_bytes([5; 32]));
    let customer = LaborNode::sink(LaborDisposition::HouseholdConsumption);
    let receipt = ReceiptRef::new(LaborReceiptFamily::Production, 0);
    let mut frame = Frame::new(Book::new());
    frame
        .credit(
            source,
            2,
            LaborBasis {
                recorded_micro_hours: 0,
                unknown_opening: true,
            },
        )
        .expect("two foundation units");
    let actual = frame
        .direct(work, source, 1, receipt)
        .expect("one hour of new output");
    frame
        .credit(source, 1, actual)
        .expect("mix fresh output with opening");
    frame
        .move_units(
            source,
            buyer,
            1,
            ReceiptRef::new(LaborReceiptFamily::LocalTransfers, 0),
        )
        .expect("one third transferred");
    let first = frame.take(buyer, 1).expect("whole transfer");
    assert_eq!(
        first,
        LaborBasis {
            recorded_micro_hours: 333_333,
            unknown_opening: true
        }
    );
    frame.release_basis(first).expect("released transfer");
    frame
        .release(source, customer, 1, receipt)
        .expect("one more unit");
    frame
        .release(source, customer, 1, receipt)
        .expect("deplete residual");
    assert_eq!(
        frame
            .edges
            .last()
            .expect("last withdrawal")
            .basis
            .recorded_micro_hours,
        333_334
    );
    assert_eq!(frame.direct_micro_hours, frame.released_micro_hours);
    assert!(frame.book.is_empty());
    // This ratio fits even though multiplying the carrying amount by the numerator would overflow.
    let huge = LaborBasis {
        recorded_micro_hours: u128::MAX,
        unknown_opening: false,
    };
    frame
        .credit(source, u64::MAX, huge)
        .expect("large retained basis");
    let partial = frame.take(source, u64::MAX - 1).expect("exact quotient");
    let residual = frame.take(source, 1).expect("all residual");
    assert_eq!(residual.recorded_micro_hours, u128::from(u64::MAX) + 2);
    assert_eq!(partial.add(residual).expect("complete carrying"), huge);
}

#[test]
fn a_project_started_and_finished_in_one_close_has_a_resolvable_installation_identity() {
    use super::{LaborNode, RecordedAssetIdentity};
    use crate::production_projection::equipment_fixture;
    use babylon_material_circuit::EquipmentCohortId;
    let (catalog, mut state) = equipment_fixture::opening();
    let catalog = equipment_fixture::rebuild(&catalog, |c| {
        c.definitions[0].installation_hours_per_unit = 1;
    });
    state.labor[0].available = 1;
    equipment_fixture::economy_mut(&mut state).member_labor[0].available_hours = 1;
    let prior = MaterialWorldRegister::try_new(&catalog, 0, state)
        .expect("opening budget admits one installation hour");
    let mut ledger = RecordedLaborLedger::from_foundation(&catalog, [3; 32], &prior)
        .expect("admitted asset opening");
    let close = prior
        .prepare_next(&catalog)
        .expect("engine closes the funded installation");
    let receipts =
        material_world::decode_material_receipts(close.receipt_bytes()).expect("admitted receipts");
    let [work] = receipts.installation.as_slice() else {
        panic!("one installation expected")
    };
    assert!(work.started);
    assert_eq!(work.used_hours, 1);
    assert_eq!(work.remaining_hours, 0);
    for register in [&prior, close.register()] {
        assert_eq!(
            register
                .state()
                .capacity_reservations
                .equipment
                .pending
                .as_slice(),
            &[] as &[PendingInstallation]
        );
    }
    let report = ledger
        .advance(&catalog, &prior, close.register(), &receipts)
        .expect("complete asset movements");
    let wip = LaborNode::installation(work.id);
    let cohort = LaborNode::equipment(EquipmentCohortId::from_bytes(work.id.as_bytes()));
    let instrument = report
        .assets
        .iter()
        .find(|r| r.node == cohort)
        .expect("installed node identity");
    let project = report
        .assets
        .iter()
        .find(|r| r.node == wip)
        .expect("intra-period WIP is resolvable");
    assert_eq!(project.identity, instrument.identity);
    assert!(matches!(
        project.identity,
        RecordedAssetIdentity::ProductiveEquipment { .. }
    ));
    assert!(report.edges.iter().any(|e| e.source == wip
        && e.destination == cohort
        && e.basis.recorded_micro_hours == 1_000_000));
}
