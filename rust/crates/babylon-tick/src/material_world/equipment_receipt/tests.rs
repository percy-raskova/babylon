use super::*;
use babylon_material_circuit::*;
include!("../../../../babylon-material-circuit/tests/support/equipment_fixture.rs");

#[test]
fn actual_equipment_close_receipts_roundtrip_with_wip_installation_wages_and_wear() {
    let mut state = opening();
    for period in 1..=5 {
        let transition = advance_material_circuit(&state).unwrap();
        let bytes = super::super::encode_material_receipts(period, &transition).unwrap();
        let decoded = super::super::decode_material_receipts(&bytes).unwrap();
        assert_eq!(decoded.installation, transition.installation);
        assert_eq!(decoded.equipment_wear, transition.equipment_wear);
        assert_eq!(decoded.member_labor_use, transition.member_labor_use);
        assert_eq!(decoded.income, transition.income);
        assert!(super::super::decode_material_receipts(&bytes[..bytes.len() - 1]).is_err());
        state = transition.state;
    }
    assert!(equipment(&state).cohorts.is_empty());
    assert_eq!(equipment_cost(&state), money(0));
    assert_eq!(stock_cost(&state, good(4)), money(44));
    let mut state = opening();
    configure_investment(&mut state, 100, -10);
    let transition = advance_material_circuit(&state).unwrap();
    let bytes = super::super::encode_material_receipts(1, &transition).unwrap();
    assert_eq!(
        super::super::decode_material_receipts(&bytes)
            .unwrap()
            .investment,
        transition.investment
    );
}

#[test]
fn equipment_receipt_refuses_invalid_work_cost_partitions_duplicates_and_old_version() {
    let mut transition = advance_material_circuit(&opening()).unwrap();
    let original = transition.clone();
    transition.installation[0].used_hours = 1;
    assert!(super::super::encode_material_receipts(1, &transition).is_err());
    transition = original.clone();
    transition
        .installation
        .push(transition.installation[0].clone());
    assert!(super::super::encode_material_receipts(1, &transition).is_err());
    transition = original;
    transition.installation[0].closing_carrying = money(27);
    assert!(super::super::encode_material_receipts(1, &transition).is_err());
    let mut state = opening();
    for _ in 0..3 {
        state = advance_material_circuit(&state).unwrap().state;
    }
    let mut transition = advance_material_circuit(&state).unwrap();
    transition.equipment_wear[0].closing_carrying = money(0);
    assert!(super::super::encode_material_receipts(4, &transition).is_err());
    let old = b"babylon.material-tick-receipts.v11\0";
    assert!(super::super::decode_material_receipts(old).is_err());
}
