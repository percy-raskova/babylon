//! Independent native service wire witnesses; no Rust layout or encoder-derived fixture.
use babylon_tick::material_world::decode_material_receipts;
const DOMAIN: &[u8] = b"babylon.material-tick-receipts.v17\0";
fn quantities(bytes: &mut Vec<u8>, values: &[u64]) {
    for value in values {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
}
fn amounts(bytes: &mut Vec<u8>, values: &[i128]) {
    for value in values {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
}
fn row(tag: u8, key: u8) -> Vec<u8> {
    let mut bytes = vec![];
    quantities(&mut bytes, &[1]);
    match tag {
        20 => {
            bytes.extend_from_slice(&[key; 32]);
            bytes.extend_from_slice(&[1; 32]);
            bytes.push(1);
            bytes.extend_from_slice(&[2; 32]);
            bytes.extend_from_slice(&[3; 32]);
            bytes.extend_from_slice(&[4; 32]);
            quantities(&mut bytes, &[3, 3, 2, 1, 1, 1]);
            amounts(&mut bytes, &[2]);
            assert_eq!(bytes.len(), 233);
        }
        21 => {
            for id in [key, 3, 4] {
                bytes.extend_from_slice(&[id; 32]);
            }
            quantities(&mut bytes, &[2, 3, 2, 0, 1]);
            assert_eq!(bytes.len(), 144);
        }
        22 => {
            quantities(&mut bytes, &[2]);
            for id in [1, key, 3, 4] {
                bytes.extend_from_slice(&[id; 32]);
            }
            quantities(&mut bytes, &[3, 3, 2, 4]);
            amounts(&mut bytes, &[10, 2, 3]);
            bytes.push(3);
            quantities(&mut bytes, &[3]);
            assert_eq!(bytes.len(), 233);
        }
        23 => {
            for id in [1, key, 3, 4] {
                bytes.extend_from_slice(&[id; 32]);
            }
            quantities(&mut bytes, &[4, 2, 2]);
            amounts(&mut bytes, &[10, 6]);
            assert_eq!(bytes.len(), 192);
        }
        _ => panic!("service family"),
    }
    bytes
}
fn envelope(tag: u8, rows: &[Vec<u8>]) -> Vec<u8> {
    let mut bytes = DOMAIN.to_vec();
    bytes.extend_from_slice(&17_u32.to_be_bytes());
    quantities(&mut bytes, &[1]);
    for family in 1..=36 {
        bytes.push(family);
        quantities(
            &mut bytes,
            &[if family == tag { rows.len() as u64 } else { 0 }],
        );
        if family == tag {
            for row in rows {
                bytes.extend_from_slice(row);
            }
        }
    }
    bytes
}
#[test]
fn service_receipts_keep_performance_satisfaction_market_and_output_distinct() {
    let performance = decode_material_receipts(&envelope(20, &[row(20, 1)])).unwrap();
    assert_eq!(performance.service_performance[0].used_quantity, 1);
    let household = decode_material_receipts(&envelope(21, &[row(21, 1)])).unwrap();
    assert_eq!(household.household_services[0].satisfied_quantity, 2);
    let market = decode_material_receipts(&envelope(22, &[row(22, 1)])).unwrap();
    assert_eq!(market.service_markets[0].direct_cost.micro_units(), 10);
    let output = decode_material_receipts(&envelope(23, &[row(23, 1)])).unwrap();
    assert_eq!(
        (
            output.service_outputs[0].expired_quantity,
            output.service_outputs[0].expired_cost.micro_units()
        ),
        (2, 6)
    );
}
#[test]
fn service_rows_refuse_false_partitions_costs_periods_and_noncanonical_keys() {
    for (tag, offset, value) in [(20, 193, 2_u64), (21, 120, 3), (22, 168, 1), (23, 152, 3)] {
        let mut damaged = row(tag, 1);
        damaged[offset..offset + 8].copy_from_slice(&value.to_be_bytes());
        assert!(
            decode_material_receipts(&envelope(tag, &[damaged])).is_err(),
            "family {tag}"
        );
    }
    for (tag, offset, value) in [
        (20, 217, 0_i128),
        (20, 217, i128::MAX),
        (22, 176, -1),
        (23, 176, 11),
    ] {
        let mut damaged = row(tag, 1);
        damaged[offset..offset + 16].copy_from_slice(&value.to_be_bytes());
        assert!(
            decode_material_receipts(&envelope(tag, &[damaged])).is_err(),
            "family {tag}"
        );
    }
    for tag in 20..=23 {
        let mut damaged = row(tag, 1);
        damaged[..8].copy_from_slice(&2_u64.to_be_bytes());
        assert!(decode_material_receipts(&envelope(tag, &[damaged])).is_err());
        assert!(decode_material_receipts(&envelope(tag, &[row(tag, 1), row(tag, 1)])).is_err());
        assert!(decode_material_receipts(&envelope(tag, &[row(tag, 2), row(tag, 1)])).is_err());
    }
}
#[test]
fn service_wire_refuses_previous_schema_and_every_truncation() {
    let bytes = envelope(23, &[row(23, 1)]);
    for length in 0..bytes.len() {
        assert!(decode_material_receipts(&bytes[..length]).is_err());
    }
    let mut previous = bytes.clone();
    previous[DOMAIN.len()..DOMAIN.len() + 4].copy_from_slice(&8_u32.to_be_bytes());
    assert!(decode_material_receipts(&previous).is_err());
    let mut previous = bytes.clone();
    previous[DOMAIN.len() - 2] = b'8';
    assert!(decode_material_receipts(&previous).is_err());
    let mut trailing = bytes;
    trailing.push(0);
    assert!(decode_material_receipts(&trailing).is_err());
}
