//! Independent current-format receipt vectors for the bounded maintenance close.
//! These bytes exercise the decoder without constructing a circuit implementation.

use babylon_tick::material_world::decode_material_receipts;

const DOMAIN: &[u8] = b"babylon.material-tick-receipts.v5\0";
const ROW_START: usize = DOMAIN.len() + 12 + 10 * 9;
const QUANTITIES: usize = ROW_START + 5 * 32 + 4 * 8;

fn receipt(values: [u64; 15]) -> Vec<u8> {
    receipt_with_coefficients([1, 10, 1, 16], values)
}

fn receipt_with_coefficients(coefficients: [u64; 4], values: [u64; 15]) -> Vec<u8> {
    let mut bytes = DOMAIN.to_vec();
    bytes.extend_from_slice(&5_u32.to_be_bytes());
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for tag in 1..=10_u8 {
        bytes.push(tag);
        bytes.extend_from_slice(&u64::from(tag == 10).to_be_bytes());
    }
    for id in 1..=5_u8 {
        bytes.extend_from_slice(&[id; 32]);
    }
    for coefficient in coefficients {
        bytes.extend_from_slice(&coefficient.to_be_bytes());
    }
    for value in values {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes
}

fn baseline() -> Vec<u8> {
    receipt([1, 16, 16, 0, 16, 16, 256, 0, 256, 160, 16, 16, 160, 2, 16])
}

fn replace_u64(bytes: &mut [u8], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_be_bytes());
}

#[test]
fn current_maintenance_receipts_admit_completed_and_zero_job_closes() {
    let values = [
        [1, 16, 16, 0, 16, 16, 256, 0, 256, 160, 16, 16, 160, 2, 16],
        [1, 16, 16, 0, 16, 16, 256, 0, 256, 0, 0, 0, 0, 2, 0],
        [1, 16, 16, 0, 16, 16, 0, 0, 0, 160, 0, 0, 0, 2, 0],
        [1, 16, 16, 0, 16, 16, 0, 0, 0, 0, 0, 0, 0, 2, 0],
        // A due arrival can fund jobs; unconsumed service expires, not accumulates.
        [1, 16, 8, 8, 16, 16, 0, 60, 60, 160, 16, 16, 160, 2, 16],
    ];
    for quantities in values {
        let decoded = decode_material_receipts(&receipt(quantities)).unwrap();
        assert_eq!(decoded.resolve_tick, 1);
        let row = decoded.maintenance.unwrap();
        assert_eq!(row.binding.provider_site_id.as_bytes(), [1; 32]);
        assert_eq!(row.binding.consumer_process_id.as_bytes(), [2; 32]);
        assert_eq!(row.binding.spare_good_id.as_bytes(), [3; 32]);
        assert_eq!(row.binding.spare_unit_id.as_bytes(), [4; 32]);
        assert_eq!(row.binding.labor_unit_id.as_bytes(), [5; 32]);
        assert_eq!(row.completed_jobs, quantities[10]);
        assert_eq!(row.next_service.available_batches, quantities[14]);
    }
}

#[test]
fn old_receipt_format_is_refused_without_a_compatibility_reader() {
    let mut bytes = b"babylon.material-tick-receipts.v4\0".to_vec();
    bytes.extend_from_slice(&4_u32.to_be_bytes());
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for tag in 1..=9_u8 {
        bytes.push(tag);
        bytes.extend_from_slice(&0_u64.to_be_bytes());
    }
    assert!(decode_material_receipts(&bytes).is_err());
}

#[test]
fn maintenance_receipts_refuse_corrupt_identity_period_conservation_and_grants() {
    // Each mutation breaks a separate causal accounting relation.
    for (index, value) in [
        (0, 2),
        (1, 17),
        (2, 17),
        (3, 1),
        (4, 17),
        (5, 15),
        (6, 255),
        (7, 1),
        (8, 255),
        (9, 159),
        (10, 15),
        (11, 15),
        (12, 159),
        (13, 3),
        (14, 15),
    ] {
        let mut bytes = baseline();
        replace_u64(&mut bytes, QUANTITIES + index * 8, value);
        assert!(
            decode_material_receipts(&bytes).is_err(),
            "quantity {index}"
        );
    }
    for index in 0..4 {
        let mut bytes = baseline();
        replace_u64(&mut bytes, ROW_START + 5 * 32 + index * 8, 0);
        assert!(
            decode_material_receipts(&bytes).is_err(),
            "coefficient {index}"
        );
    }
    let mut bytes = baseline();
    let spare_unit = bytes[ROW_START + 3 * 32..ROW_START + 4 * 32].to_vec();
    bytes[ROW_START + 4 * 32..ROW_START + 5 * 32].copy_from_slice(&spare_unit);
    assert!(
        decode_material_receipts(&bytes).is_err(),
        "labor is not a spare unit"
    );
}

#[test]
fn maintenance_receipts_refuse_duplicate_truncated_trailing_and_overflow_rows() {
    let original = baseline();
    let mut bytes = original.clone();
    replace_u64(&mut bytes, ROW_START - 8, 2);
    bytes.extend_from_slice(&original[ROW_START..]);
    assert!(decode_material_receipts(&bytes).is_err());
    for end in [ROW_START, original.len() - 1] {
        assert!(decode_material_receipts(&original[..end]).is_err());
    }
    let mut bytes = original.clone();
    bytes.push(0);
    assert!(decode_material_receipts(&bytes).is_err());
    let mut bytes = original;
    replace_u64(&mut bytes, QUANTITIES + 6 * 8, u64::MAX);
    replace_u64(&mut bytes, QUANTITIES + 7 * 8, 1);
    replace_u64(&mut bytes, QUANTITIES + 8 * 8, 0);
    assert!(decode_material_receipts(&bytes).is_err());
}

#[test]
fn maintenance_receipts_distinguish_unrestricted_request_from_capacity_and_ceil_jobs() {
    let capped = receipt([1, 16, 16, 0, 20, 20, 256, 0, 256, 160, 16, 16, 160, 2, 16]);
    let row = decode_material_receipts(&capped)
        .unwrap()
        .maintenance
        .unwrap();
    assert_eq!((row.requested_jobs, row.completed_jobs), (20, 16));
    let rounded = receipt_with_coefficients(
        [1, 10, 2, 8],
        [1, 16, 16, 0, 17, 9, 256, 0, 256, 160, 8, 8, 80, 2, 16],
    );
    let row = decode_material_receipts(&rounded)
        .unwrap()
        .maintenance
        .unwrap();
    assert_eq!(
        (
            row.requested_jobs,
            row.completed_jobs,
            row.next_service.available_batches
        ),
        (9, 8, 16)
    );
}

#[test]
fn absent_maintenance_is_distinct_from_a_bound_completed_zero_close() {
    let mut absent = baseline();
    absent.truncate(ROW_START);
    replace_u64(&mut absent, ROW_START - 8, 0);
    assert!(decode_material_receipts(&absent)
        .unwrap()
        .maintenance
        .is_none());
    let zero = receipt([1, 16, 16, 0, 16, 16, 0, 0, 0, 0, 0, 0, 0, 2, 0]);
    let row = decode_material_receipts(&zero)
        .unwrap()
        .maintenance
        .unwrap();
    assert_eq!((row.requested_jobs, row.completed_jobs), (16, 0));
}
