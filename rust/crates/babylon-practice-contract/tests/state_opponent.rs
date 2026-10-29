use babylon_practice_contract::{decode_city_pd_config, encode_city_pd_config, CityPdConfig};

#[test]
fn config_round_trips_and_rejects_a_bad_county() {
    let mut config = CityPdConfig {
        schema_version: 1,
        campaign_id: [1; 16],
        actor_id: 9,
        authority_id: [2; 16],
        county: *b"26163",
        public_account_id: [3; 32],
        agency_account_id: [4; 32],
        investigator_household_account_id: [5; 32],
        investigator_entitlement_id: [6; 32],
        labor_unit_id: [7; 32],
        visit_hours: 2,
        hourly_wage_micros: 3,
        visit_cost_micros: 6,
        appropriation_micros: 10,
        appropriation_priority: 0,
        content_digest: [8; 32],
        policy_source_digest: [9; 32],
    };
    let bytes = encode_city_pd_config(&config).expect("valid config");
    let repeated = |n: u8, count: usize| format!("[{}]", vec![n.to_string(); count].join(","));
    let expected = format!("babylon.city-pd-config.v1\0{{\"schema_version\":1,\"campaign_id\":{},\"actor_id\":9,\"authority_id\":{},\"county\":[50,54,49,54,51],\"public_account_id\":{},\"agency_account_id\":{},\"investigator_household_account_id\":{},\"investigator_entitlement_id\":{},\"labor_unit_id\":{},\"visit_hours\":2,\"hourly_wage_micros\":\"3\",\"visit_cost_micros\":\"6\",\"appropriation_micros\":\"10\",\"appropriation_priority\":0,\"content_digest\":{},\"policy_source_digest\":{}}}", repeated(1,16), repeated(2,16), repeated(3,32), repeated(4,32), repeated(5,32), repeated(6,32), repeated(7,32), repeated(8,32), repeated(9,32));
    assert_eq!(bytes, expected.as_bytes());
    assert_eq!(
        city_pd_config_digest(&config).expect("valid City PD test fixture"),
        [
            0xe9, 0x88, 0xe4, 0x8b, 0xc0, 0x25, 0x9e, 0x0c, 0x17, 0x1d, 0xf6, 0x5a, 0x78, 0xaf,
            0xe1, 0x67, 0xc1, 0x79, 0x0c, 0x70, 0x23, 0xdb, 0xc2, 0xa7, 0x5d, 0x0d, 0x02, 0x34,
            0x12, 0x55, 0x9f, 0x08
        ]
    );
    assert_eq!(decode_city_pd_config(&bytes).expect("decode"), config);
    config.county = *b"26x63";
    assert!(encode_city_pd_config(&config).is_err());
}

use babylon_practice_contract::*;
fn case() -> CityPdCase {
    let mut c = CityPdCase {
        case_id: [0; 32],
        actor_id: 9,
        subject_id: 20,
        county: *b"26163",
        public_venue_id: [1; 32],
        source_id: [2; 32],
        source_kind: CityPdCaseSource::CapturedPublicRecord,
        source_receipt_id: None,
        case_source_witness_id: None,
        observed_period: 0,
        acquired_period: 0,
        status: CityPdCaseStatus::Open,
    };
    c.case_id = city_pd_case_id(&c).expect("valid City PD test fixture");
    c
}
fn intent() -> CityPdIntent {
    let mut i = CityPdIntent {
        intent_id: [0; 32],
        schema_version: 1,
        campaign_id: [1; 16],
        actor_id: 9,
        authority_id: [2; 16],
        config_digest: [3; 32],
        decision_basis_digest: [4; 32],
        case_id: case().case_id,
        subject_id: 20,
        source_period: 1,
        resolve_period: 2,
        cost_micros: 6,
    };
    i.intent_id = city_pd_intent_id(&i).expect("valid City PD test fixture");
    i
}
fn decision() -> CityPdDecisionReceipt {
    let mut d = CityPdDecisionReceipt {
        decision_id: [0; 32],
        campaign_id: [1; 16],
        actor_id: 9,
        period: 1,
        decision_basis_digest: [4; 32],
        decision: CityPdDecision::Selected(intent()),
    };
    d.decision_id = city_pd_decision_id(&d).expect("valid City PD test fixture");
    d
}
fn receipt() -> CityPdReceipt {
    let mut r = CityPdReceipt {
        receipt_id: [0; 32],
        campaign_id: [1; 16],
        actor_id: 9,
        case_id: case().case_id,
        intent_id: intent().intent_id,
        resolve_period: 2,
        outcome: CityPdOutcome::Completed,
        attendance_hours: 2,
        wage_micros: 6,
        shift_receipt_id: Some([5; 32]),
        payment_receipt_id: Some([6; 32]),
        acquired_public_fact_ids: vec![],
        case_source_evidence_id: None,
        player_witness_evidence_id: None,
    };
    r.receipt_id = city_pd_receipt_id(&r).expect("valid City PD test fixture");
    r
}
#[test]
fn all_wire_contracts_round_trip_and_bind_content() {
    let c = case();
    let i = intent();
    let d = decision();
    let r = receipt();
    assert_eq!(
        decode_city_pd_case(&encode_city_pd_case(&c).expect("valid City PD test fixture"))
            .expect("valid City PD test fixture"),
        c
    );
    assert_eq!(
        decode_city_pd_intent(&encode_city_pd_intent(&i).expect("valid City PD test fixture"))
            .expect("valid City PD test fixture"),
        i
    );
    assert_eq!(
        decode_city_pd_decision(&encode_city_pd_decision(&d).expect("valid City PD test fixture"))
            .expect("valid City PD test fixture"),
        d
    );
    assert_eq!(
        decode_city_pd_receipt(&encode_city_pd_receipt(&r).expect("valid City PD test fixture"))
            .expect("valid City PD test fixture"),
        r
    );
    let mut closed = c.clone();
    closed.status = CityPdCaseStatus::Closed;
    assert_eq!(
        city_pd_case_id(&closed).expect("valid City PD test fixture"),
        c.case_id
    );
    closed.subject_id += 1;
    assert_ne!(
        city_pd_case_id(&closed).expect("valid City PD test fixture"),
        c.case_id
    );
    let mut changed = i.clone();
    changed.cost_micros += 1;
    assert_ne!(
        city_pd_intent_id(&changed).expect("valid City PD test fixture"),
        i.intent_id
    );
    let mut changed = d.clone();
    changed.period += 1;
    assert_ne!(
        city_pd_decision_id(&changed).expect("valid City PD test fixture"),
        d.decision_id
    );
    let mut changed = r.clone();
    changed.wage_micros += 1;
    assert_ne!(
        city_pd_receipt_id(&changed).expect("valid City PD test fixture"),
        r.receipt_id
    );
}
#[test]
fn provenance_and_wire_corruption_refuse() {
    let mut c = case();
    c.source_kind = CityPdCaseSource::ObservedOrganizerReceipt;
    assert_eq!(
        validate_city_pd_case(&c),
        Err(CityPdError::InvalidProvenance)
    );
    c.source_receipt_id = Some([1; 32]);
    c.case_source_witness_id = Some([2; 32]);
    c.case_id = city_pd_case_id(&c).expect("valid City PD test fixture");
    assert!(validate_city_pd_case(&c).is_ok());
    c.observed_period = 2;
    c.acquired_period = 1;
    assert_eq!(validate_city_pd_case(&c), Err(CityPdError::InvalidTiming));
    let bytes = encode_city_pd_intent(&intent()).expect("valid City PD test fixture");
    let mut trailing = bytes.clone();
    trailing.push(b' ');
    assert!(decode_city_pd_intent(&trailing).is_err());
    let raw = String::from_utf8(bytes).expect("valid City PD test fixture");
    assert!(decode_city_pd_intent(
        raw.replace("\"cost_micros\":\"6\"", "\"cost_micros\":\"06\"")
            .as_bytes()
    )
    .is_err());
    assert!(decode_city_pd_intent(
        raw.replace("\"schema_version\":1", "\"schema_version\":2")
            .as_bytes()
    )
    .is_err());
    assert!(decode_city_pd_intent(
        raw.replace("\"subject_id\":20", "\"unknown\":0,\"subject_id\":20")
            .as_bytes()
    )
    .is_err());
    assert_eq!(
        decode_city_pd_intent(&vec![0; 1024 * 1024 + 1]),
        Err(CityPdError::SizeLimit)
    );
}
#[test]
fn receipt_rejects_unpaid_fabrication_and_unsorted_facts() {
    let mut r = receipt();
    assert!(validate_city_pd_receipt(&r).is_ok());
    r.outcome = CityPdOutcome::InsufficientTime;
    r.receipt_id = city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert_eq!(
        validate_city_pd_receipt(&r),
        Err(CityPdError::InvalidReceipt)
    );
    r.attendance_hours = 0;
    r.wage_micros = 0;
    r.payment_receipt_id = None;
    r.player_witness_evidence_id = Some([7; 32]);
    r.receipt_id = city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert_eq!(
        validate_city_pd_receipt(&r),
        Err(CityPdError::InvalidReceipt)
    );
    r.player_witness_evidence_id = None;
    r.acquired_public_fact_ids = vec![[2; 32], [1; 32]];
    r.receipt_id = city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert_eq!(
        validate_city_pd_receipt(&r),
        Err(CityPdError::InvalidReceipt)
    );
}

#[test]
fn independently_pinned_identity_hashes() {
    // Computed independently from domain + NUL + compact ordered JSON bodies.
    assert_eq!(
        case().case_id,
        [
            65, 12, 237, 234, 57, 45, 215, 71, 133, 2, 77, 224, 113, 171, 128, 148, 108, 206, 247,
            15, 32, 231, 86, 168, 100, 113, 107, 222, 27, 18, 34, 44
        ]
    );
    assert_eq!(
        intent().intent_id,
        [
            4, 223, 203, 183, 28, 59, 114, 113, 230, 54, 111, 242, 105, 251, 78, 63, 99, 207, 1,
            103, 229, 55, 18, 250, 28, 79, 32, 36, 46, 144, 67, 153
        ]
    );
    assert_eq!(
        decision().decision_id,
        [
            180, 182, 149, 206, 162, 60, 49, 112, 9, 202, 42, 179, 253, 87, 116, 122, 240, 243, 99,
            235, 148, 160, 235, 83, 93, 36, 46, 236, 193, 49, 140, 36
        ]
    );
    assert_eq!(
        receipt().receipt_id,
        [
            29, 71, 33, 249, 133, 250, 214, 206, 247, 184, 117, 30, 50, 13, 43, 1, 108, 109, 183,
            150, 150, 169, 135, 211, 54, 206, 48, 48, 170, 180, 239, 26
        ]
    );
}

#[test]
fn receipt_shapes_and_limits_are_enforced() {
    let mut r = receipt();
    r.player_witness_evidence_id = Some([7; 32]);
    r.receipt_id = city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert!(validate_city_pd_receipt(&r).is_ok());
    assert_eq!(r.case_source_evidence_id, None);
    for outcome in [
        CityPdOutcome::InsufficientFunds,
        CityPdOutcome::InsufficientTime,
    ] {
        r.outcome = outcome;
        r.attendance_hours = 0;
        r.wage_micros = 0;
        r.payment_receipt_id = None;
        r.player_witness_evidence_id = None;
        r.receipt_id = city_pd_receipt_id(&r).expect("valid City PD test fixture");
        assert!(validate_city_pd_receipt(&r).is_ok());
        r.acquired_public_fact_ids = vec![[1; 32]];
        assert_eq!(
            validate_city_pd_receipt(&r),
            Err(CityPdError::InvalidReceipt)
        );
        r.acquired_public_fact_ids.clear();
        r.payment_receipt_id = Some([1; 32]);
        assert_eq!(
            validate_city_pd_receipt(&r),
            Err(CityPdError::InvalidReceipt)
        );
        r.payment_receipt_id = None;
    }
    r.acquired_public_fact_ids = vec![[1; 32], [1; 32]];
    assert_eq!(
        validate_city_pd_receipt(&r),
        Err(CityPdError::InvalidReceipt)
    );
    r.acquired_public_fact_ids = vec![[1; 32]; CITY_PD_MAX_ROWS + 1];
    assert_eq!(validate_city_pd_receipt(&r), Err(CityPdError::SizeLimit));
}

#[test]
fn wire_rejects_wrong_domain_unknown_tag_bad_money_and_ids() {
    let case_bytes =
        String::from_utf8(encode_city_pd_case(&case()).expect("valid City PD test fixture"))
            .expect("valid City PD test fixture");
    assert!(decode_city_pd_case(
        case_bytes
            .replace("captured_public_record", "unknown")
            .as_bytes()
    )
    .is_err());
    assert!(decode_city_pd_case(
        case_bytes
            .replacen("city-pd-case", "city-pd-other", 1)
            .as_bytes()
    )
    .is_err());
    let raw =
        String::from_utf8(encode_city_pd_intent(&intent()).expect("valid City PD test fixture"))
            .expect("valid City PD test fixture");
    for amount in ["-1", "+6", "06", "170141183460469231731687303715884105728"] {
        assert!(decode_city_pd_intent(
            raw.replace(
                "\"cost_micros\":\"6\"",
                &format!("\"cost_micros\":\"{amount}\"")
            )
            .as_bytes()
        )
        .is_err());
    }
    let mut c = case();
    c.source_id = [0; 32];
    assert_eq!(validate_city_pd_case(&c), Err(CityPdError::InvalidId));
    let mut i = intent();
    i.resolve_period = 3;
    assert_eq!(validate_city_pd_intent(&i), Err(CityPdError::InvalidTiming));
    i.source_period = u64::MAX;
    assert_eq!(validate_city_pd_intent(&i), Err(CityPdError::Arithmetic));
}

#[test]
fn finalizing_receipts_sorts_and_deduplicates_facts() {
    let mut draft = receipt();
    draft.acquired_public_fact_ids = vec![[2; 32], [1; 32], [2; 32]];
    let finalized = finalize_city_pd_receipt(draft).expect("valid City PD test fixture");
    assert_eq!(finalized.acquired_public_fact_ids, vec![[1; 32], [2; 32]]);
    assert_eq!(
        decode_city_pd_receipt(
            &encode_city_pd_receipt(&finalized).expect("valid City PD test fixture")
        )
        .expect("valid City PD test fixture"),
        finalized
    );
}
