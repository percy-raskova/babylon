//! A real paid close crosses both tick admission and the retained storage codec.
#[allow(
    dead_code,
    reason = "the shared control includes other material scenarios"
)]
#[path = "../../../babylon-material-circuit/tests/support/organizer_funding_control.rs"]
mod control;

use super::storage;
use super::storage::AdmittedReceipts;
use crate::state_storage::TypedLookup;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AgencyAttendanceInput;
use babylon_material_circuit::AgencyAttendanceOutcome;
use babylon_material_circuit::MoneyTransferPurpose;
use babylon_tick::material_world;

#[test]
fn actual_paid_close_survives_persistence_admission_and_roundtrip() {
    let (catalog, opening) = control::opening_with_agency(500_000);
    let AccountId::Organization(agency) = control::organization() else {
        unreachable!()
    };
    let principal_id = control::recipient();
    let residence = opening
        .final_demand_principals
        .iter()
        .find(|r| r.id == principal_id)
        .expect("the fixture contains the household")
        .location;
    let intent_id = [71; 32];
    let input = AgencyAttendanceInput {
        intent_id,
        shift_id: babylon_material_circuit::agency_shift_id(opening.period, intent_id),
        agency,
        principal_id,
        residence,
        labor_unit_id: control::unit(90),
        due_period: opening.period,
        hours: 1,
        hourly_rate: control::money(100_000),
    };
    let result = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        &[input],
    )
    .expect("funded close begins")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("funded close finishes");
    assert_eq!(
        result.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::Paid
    );
    let canonical = material_world::encode_material_receipts(&catalog, 1, &result)
        .expect("the actual paid transition has canonical receipts");
    let admitted = AdmittedReceipts::new(&canonical, None).expect("canonical evidence is admitted");
    let mut lookup = TypedLookup::default();
    let stored = storage::encode(&admitted, &mut lookup).expect("real paid receipt is stored");
    let (restored, decoded) =
        storage::decode_admitted(&stored, &lookup).expect("stored receipt restores");
    assert_eq!(restored, canonical);
    assert_eq!(decoded.agency_paid.len(), 1);
    assert_eq!(decoded.agency_paid[0].wage, control::money(100_000));
    assert_eq!(decoded.wage_accruals, result.wage_accruals);
    assert_eq!(decoded.household_time, result.household_time);
    let before = lookup.entries().to_vec();
    for offset in [0, 32, 64, 96, 128, 160, 168, 176] {
        let mut damaged = canonical.clone();
        let start = damaged.len() - 192;
        damaged[start + offset + if offset >= 160 { 7 } else { 0 }] ^= 1;
        assert!(
            AdmittedReceipts::new(&damaged, None).is_err(),
            "tampered field {offset}"
        );
        assert_eq!(lookup.entries(), before);
    }
    let mut damaged_storage = stored;
    *damaged_storage
        .last_mut()
        .expect("stored receipt is nonempty") ^= 1;
    assert!(storage::decode_admitted(&damaged_storage, &lookup).is_err());
}

fn round2_paid_canonical() -> Vec<u8> {
    let (catalog, opening) = control::opening_with_agency(500_000);
    let AccountId::Organization(agency) = control::organization() else {
        unreachable!()
    };
    let principal_id = control::recipient();
    let residence = opening
        .final_demand_principals
        .iter()
        .find(|r| r.id == principal_id)
        .expect("recipient exists")
        .location;
    let intent_id = [71; 32];
    let input = AgencyAttendanceInput {
        intent_id,
        shift_id: babylon_material_circuit::agency_shift_id(1, intent_id),
        agency,
        principal_id,
        residence,
        labor_unit_id: control::unit(90),
        due_period: 1,
        hours: 1,
        hourly_rate: control::money(100_000),
    };
    let result = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        &[input],
    )
    .expect("close begins")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("close finishes");
    material_world::encode_material_receipts(&catalog, 1, &result).expect("paid receipts encode")
}

fn round2_family(bytes: &[u8], target: usize) -> (usize, usize, usize) {
    let mut position = b"babylon.material-tick-receipts.v20\0".len() + 12;
    for (index, width) in material_world::RECEIPT_ROW_BYTES.iter().enumerate() {
        assert_eq!(usize::from(bytes[position]), index + 1);
        let count = u64::from_be_bytes(
            bytes[position + 1..position + 9]
                .try_into()
                .expect("family count"),
        );
        position += 9;
        if index + 1 == target {
            return (
                position,
                usize::try_from(count).expect("count fits"),
                *width,
            );
        }
        position += usize::try_from(count).expect("count fits") * width;
    }
    unreachable!("expected family")
}

#[test]
fn round2_storage_refuses_coherent_paid_priority_shortfalls() {
    let canonical = round2_paid_canonical();
    let (start, count, width) = round2_family(&canonical, 34);
    let row = (0..count)
        .map(|i| start + i * width)
        .find(|&i| canonical[i..i + 32] == control::recipient().as_bytes())
        .expect("paid household time row");
    for unpaid in [false, true] {
        let mut changed = canonical.clone();
        let attended = u64::from_be_bytes(
            changed[row + 80..row + 88]
                .try_into()
                .expect("attended hours"),
        );
        for (offset, value) in [
            (72, attended),
            (88, 0),
            (96, u64::from(!unpaid)),
            (104, u64::from(unpaid)),
            (112, 0),
            (120, u64::from(unpaid)),
            (128, 0),
        ] {
            changed[row + offset..row + offset + 8].copy_from_slice(&value.to_be_bytes());
        }
        let mut lookup = TypedLookup::default();
        assert!(AdmittedReceipts::new(&changed, None)
            .and_then(|admitted| storage::encode(&admitted, &mut lookup))
            .is_err());
        assert_eq!(lookup.entries().len(), 0);
    }
}

#[test]
fn round2_storage_refuses_payment_before_reservation() {
    let canonical = round2_paid_canonical();
    let decoded =
        material_world::decode_material_receipts(&canonical).expect("paid receipt decodes");
    let shift = decoded.agency_paid[0].shift_id;
    let reservation = decoded
        .money_transfers
        .iter()
        .position(|t| t.purpose == MoneyTransferPurpose::ShiftReservation(shift))
        .expect("reservation");
    let payment = decoded
        .money_transfers
        .iter()
        .position(|t| t.purpose == MoneyTransferPurpose::WagePayment(shift))
        .expect("payment");
    assert!(reservation < payment);
    let (start, _, width) = round2_family(&canonical, 11);
    let mut changed = canonical.clone();
    let first = canonical[start + reservation * width..start + (reservation + 1) * width].to_vec();
    let second = canonical[start + payment * width..start + (payment + 1) * width].to_vec();
    changed[start + reservation * width..start + (reservation + 1) * width]
        .copy_from_slice(&second);
    changed[start + payment * width..start + (payment + 1) * width].copy_from_slice(&first);
    let mut lookup = TypedLookup::default();
    assert!(AdmittedReceipts::new(&changed, None)
        .and_then(|admitted| storage::encode(&admitted, &mut lookup))
        .is_err());
    assert_eq!(lookup.entries().len(), 0);
}
