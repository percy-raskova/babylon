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

#[test]
fn goods_cost_from_real_equipment_close_roundtrips_and_restart_does_not_reuse_it() {
    let mut state = opening();
    for _ in 0..3 {
        state = advance_material_circuit(&state).unwrap().state;
    }
    configure_output_quote(&mut state);
    let transition = advance_material_circuit(&state).unwrap();
    let bytes = super::super::encode_material_receipts(4, &transition).unwrap();
    let decoded = super::super::decode_material_receipts(&bytes).unwrap();
    assert_eq!(decoded.prices, transition.prices);
    assert_eq!(decoded.prices[0].cost.quantity, 2);
    assert_eq!(decoded.prices[0].cost.carrying_cost, money(29));
    assert_eq!(decoded.prices[0].reason, PriceDecision::CostPressure);
    let restored =
        decode_material_circuit_state(&encode_material_circuit_state(&transition.state).unwrap())
            .unwrap();
    let next = advance_material_circuit(&restored).unwrap();
    assert_eq!(next, advance_material_circuit(&transition.state).unwrap());
    assert_eq!(next.prices[0].cost.basis, GoodsPriceCostBasis::Unavailable);
    let next_bytes = super::super::encode_material_receipts(5, &next).unwrap();
    assert_eq!(
        super::super::decode_material_receipts(&next_bytes)
            .unwrap()
            .prices,
        next.prices
    );
}
