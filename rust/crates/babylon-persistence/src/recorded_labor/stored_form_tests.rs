//! The stored forms of the recorded-labor ledger and the order of its refusals are pinned, so that
//! moving the fold cannot change a checkpoint's bytes, its digest, a period's JSON or a refusal.
use super::{
    RecordedLaborCheckpoint, RecordedLaborError, RecordedLaborLedger, RecordedLaborPeriod,
};
use crate::production_projection::{equipment_fixture, recurring_fixture};
use babylon_kernel::content_digest;
use babylon_tick::material_world::{self, MaterialWorldRegister};
use std::fmt::Write;

fn hex(bytes: &[u8]) -> String {
    bytes.iter().fold(String::new(), |mut out, b| {
        write!(out, "{b:02x}").expect("a string takes any text");
        out
    })
}

/// What one period leaves in storage: the checkpoint's digests, the period's JSON digest, its totals.
#[derive(Debug, PartialEq, Eq)]
struct Stored {
    checkpoint_bytes: String,
    checkpoint_sha256: String,
    period_json: String,
    totals: [u128; 4],
}

fn stored(checkpoint: &RecordedLaborCheckpoint, period: &RecordedLaborPeriod) -> Stored {
    let json = serde_json::to_vec(period).expect("period JSON");
    Stored {
        checkpoint_bytes: hex(&content_digest::sha256_of(&checkpoint.bytes)),
        checkpoint_sha256: hex(&checkpoint.sha256),
        period_json: hex(&content_digest::sha256_of(&json)),
        totals: [
            period.opening_recorded_micro_hours,
            period.closing_recorded_micro_hours,
            period.direct_micro_hours,
            period.released_micro_hours,
        ],
    }
}

fn pinned(checkpoint: &str, json: &str, totals: [u128; 4]) -> Stored {
    Stored {
        checkpoint_bytes: checkpoint.to_owned(),
        checkpoint_sha256: checkpoint.to_owned(),
        period_json: json.to_owned(),
        totals,
    }
}

#[test]
fn the_stored_forms_of_three_periods_are_pinned() {
    let (catalog, state) = recurring_fixture::materials();
    let mut register =
        MaterialWorldRegister::try_new(&catalog, 0, state).expect("admitted foundation");
    let mut ledger =
        RecordedLaborLedger::from_foundation(&catalog, [1; 32], &register).expect("bound ledger");
    let mut seen = Vec::new();
    for _ in 0..3 {
        let next = register.prepare_next(&catalog).expect("close");
        let receipts =
            material_world::decode_material_receipts(next.receipt_bytes()).expect("receipts");
        let period = ledger
            .advance(&catalog, &register, next.register(), &receipts)
            .expect("period");
        let checkpoint = ledger.checkpoint().expect("checkpoint");
        assert_eq!(
            checkpoint.sha256,
            content_digest::sha256_of(&checkpoint.bytes)
        );
        seen.push(stored(&checkpoint, &period));
        register = next.register().clone();
    }
    let expected = [
        pinned(
            "9ccf2acfedbae2d9bae3bb1b68e4888d45aeba6fd943d3fd4c16789b5f4460c2",
            "efd554a861baf99892f4ef2eb18b84602c8abcdf8274bfbd0f6144d23be28d11",
            [0, 14_666_667, 16_000_000, 1_333_333],
        ),
        pinned(
            "f18cc7e8d66ce1f1314f5c9ea9ff799bc69de149c945beec6a35783d6a13a21b",
            "b36bba8e3de0be05029b48bae1fb2e642c9f27bab280c6ad48946343a5a1c4c1",
            [14_666_667, 25_777_778, 16_000_000, 4_888_889],
        ),
        pinned(
            "b0754bd908173fd8c9b1192b655ae0b15af9736d0b2db42dcaff05c3058179ee",
            "6b5173a6d2592e7d567af80d8492622e0e421d17b1a32b890974a7717c8bcb44",
            [25_777_778, 33_185_186, 16_000_000, 8_592_592],
        ),
    ];
    assert_eq!(seen, expected);
}

#[test]
fn the_stored_forms_of_an_equipment_period_are_pinned() {
    let (catalog, mut state) = equipment_fixture::opening();
    let catalog = equipment_fixture::rebuild(&catalog, |c| {
        c.definitions[0].installation_hours_per_unit = 1;
    });
    state.labor[0].available = 1;
    equipment_fixture::economy_mut(&mut state).member_labor[0].available_hours = 1;
    let prior = MaterialWorldRegister::try_new(&catalog, 0, state).expect("opening");
    let mut ledger =
        RecordedLaborLedger::from_foundation(&catalog, [3; 32], &prior).expect("opening ledger");
    let close = prior.prepare_next(&catalog).expect("close");
    let receipts =
        material_world::decode_material_receipts(close.receipt_bytes()).expect("receipts");
    let period = ledger
        .advance(&catalog, &prior, close.register(), &receipts)
        .expect("period");
    let checkpoint = ledger.checkpoint().expect("checkpoint");
    assert_eq!(
        stored(&checkpoint, &period),
        pinned(
            "90e61df8821b7d9ce42517e4dc703cef70f7224eb494cf2190ecfb08edc41490",
            "709bef435f83aa4e2f74f6334ebbb258f888b3a6aaab680f277b6801f114621e",
            [0, 1_000_000, 1_000_000, 0],
        )
    );
}

#[test]
fn the_refusals_keep_their_order() {
    let (catalog, state) = recurring_fixture::materials();
    let opening = MaterialWorldRegister::try_new(&catalog, 0, state).expect("foundation");
    let first = opening.prepare_next(&catalog).expect("first close");
    let second = first
        .register()
        .prepare_next(&catalog)
        .expect("second close");
    let receipts =
        material_world::decode_material_receipts(first.receipt_bytes()).expect("receipts");
    let fresh =
        || RecordedLaborLedger::from_foundation(&catalog, [1; 32], &opening).expect("fresh ledger");
    let mut attendance = receipts.clone();
    attendance.member_labor_use[0].attended_hours += 1;
    let mut consumption = receipts.clone();
    consumption.household_consumption[0].closing_quantity += 1;
    let mut both = attendance.clone();
    both.household_consumption[0].closing_quantity += 1;
    // A successor of the wrong tick, with both other faults present: continuity is checked first.
    assert_eq!(
        fresh().advance(&catalog, &opening, second.register(), &both),
        Err(RecordedLaborError::DiscontinuousPeriod)
    );
    // The attendance fault, with the consumption fault present: attendance is checked first.
    assert_eq!(
        fresh().advance(&catalog, &opening, first.register(), &both),
        Err(RecordedLaborError::InvalidAttendance)
    );
    assert_eq!(
        fresh().advance(&catalog, &opening, first.register(), &attendance),
        Err(RecordedLaborError::InvalidAttendance)
    );
    // The consumption fault alone.
    assert_eq!(
        fresh().advance(&catalog, &opening, first.register(), &consumption),
        Err(RecordedLaborError::ReceiptMismatch("household_consumption"))
    );
    // The same receipts without a fault are accepted.
    fresh()
        .advance(&catalog, &opening, first.register(), &receipts)
        .expect("unfaulted close");
}
