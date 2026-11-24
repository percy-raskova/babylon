//! Only committed household contributions count as collection work.
use super::view;
use super::{
    LaborDisposition, LaborEdge, LaborNode, LaborReceiptFamily, ReceiptRef, RecordedLaborError,
};
use crate::production_projection::recurring_fixture;
use crate::test_support;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    CircuitAccounting, CollectionOutcome, CollectionReceipt, FinalDemandPrincipalId,
    HouseholdContributionReceipt, HouseholdTimeAccounting, HouseholdTimeBook, MaterialCircuitState,
    OrganizationAccountId, UnitId,
};
use babylon_recorded_labor::phases as household_work;
use babylon_recorded_labor::{Book, Frame, PeriodView};
use babylon_tick::material_world::MaterialTickReceipts;

fn period_view<'a>(
    state: &'a MaterialCircuitState,
    receipts: &'a MaterialTickReceipts,
) -> PeriodView<'a> {
    PeriodView {
        period: receipts.resolve_tick,
        before: state,
        after: state,
        receipts: view::receipt_view(receipts, &[]),
    }
}

fn funded_state() -> MaterialCircuitState {
    let (_, mut state) = recurring_fixture::materials();
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("funded household");
    };
    e.household_time = HouseholdTimeAccounting::Modeled(HouseholdTimeBook::default());
    state
}

fn partial() -> CollectionReceipt {
    let donor = FinalDemandPrincipalId::from_bytes([5; 32]);
    let unit = UnitId::from_bytes([7; 32]);
    CollectionReceipt {
        period: 1,
        admitted_period: 0,
        original_commitment_id: [1; 32],
        command_nonce: [2; 16],
        mandate_id: [3; 32],
        source_hash: [4; 32],
        actor_id: 101,
        contributor_id: 201,
        donor,
        recipient: OrganizationAccountId::from_bytes([6; 32]),
        labor_unit_id: unit,
        requested: Currency::from_micro_units(8),
        collected: Currency::from_micro_units(4),
        performed_hours: 2,
        outcome: CollectionOutcome::PartiallyCollected,
        transfer_ordinal: Some(3),
        contribution_use_id: babylon_material_circuit::collection_contribution_id(
            [1; 32], [3; 32], 1, 101, 201, donor, unit,
        ),
    }
}

#[test]
fn collection_work_is_released_once_for_the_actual_contribution() {
    let mut closing = funded_state();
    let mut frame = Frame::new(Book::new());
    let mut receipts = test_support::material_receipts(1);
    let row = partial();
    let source = LaborNode::household_work(row.donor, row.labor_unit_id);
    let contribution = row.contribution_use().expect("partial gift consumes time");
    receipts.collections.push(row);
    let mismatch = RecordedLaborError::ReceiptMismatch("collections");
    assert_eq!(
        household_work::collections(&mut frame, &period_view(&closing, &receipts)),
        Err(mismatch)
    );
    let CircuitAccounting::Monetary(e) = &mut closing.accounting else {
        panic!("funded household");
    };
    let HouseholdTimeAccounting::Modeled(book) = &mut e.household_time else {
        panic!("household time modeled");
    };
    book.contributions.push(HouseholdContributionReceipt {
        period: 1,
        contribution,
    });
    household_work::collections(&mut frame, &period_view(&closing, &receipts))
        .expect("performed partial collection");
    let [edge] = frame.edges.as_slice() else {
        panic!("exactly one edge for performed work");
    };
    assert_eq!(edge.source, source);
    assert_eq!(
        edge.destination,
        LaborNode::sink(LaborDisposition::OrganizerCashCollection)
    );
    assert_eq!(
        edge.receipt,
        ReceiptRef::new(LaborReceiptFamily::Collections, 0)
    );
    assert_eq!(edge.quantity, 2);
    assert_eq!(edge.basis.recorded_micro_hours, 2_000_000);
    assert_eq!(frame.direct_micro_hours, 2_000_000);
    assert_eq!(frame.released_micro_hours, frame.direct_micro_hours);
    assert!(frame.book.is_empty());
}

#[test]
fn refused_collection_records_no_work_and_rejects_fabricated_hours() {
    let closing = funded_state();
    let mut frame = Frame::new(Book::new());
    let mut receipts = test_support::material_receipts(1);
    let mut row = partial();
    row.outcome = CollectionOutcome::InsufficientCash;
    row.collected = Currency::from_micro_units(0);
    row.performed_hours = 0;
    row.transfer_ordinal = None;
    row.contribution_use_id = [0; 32];
    receipts.collections.push(row);
    household_work::collections(&mut frame, &period_view(&closing, &receipts))
        .expect("refused gift");
    receipts.collections[0].performed_hours = 2;
    let mismatch = RecordedLaborError::ReceiptMismatch("collections");
    assert_eq!(
        household_work::collections(&mut frame, &period_view(&closing, &receipts)),
        Err(mismatch)
    );
    assert_eq!(frame.edges, [] as [LaborEdge; 0]);
    assert_eq!(
        (frame.direct_micro_hours, frame.released_micro_hours),
        (0, 0)
    );
}
