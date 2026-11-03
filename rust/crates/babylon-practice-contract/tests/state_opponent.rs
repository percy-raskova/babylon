use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    CityPdCase, CityPdCaseSource, CityPdCaseStatus, CityPdConfig, CityPdDecision,
    CityPdDecisionReceipt, CityPdError, CityPdIntent, CityPdOutcome, CityPdReceipt,
    CITY_PD_MAX_ROWS,
};

fn config_fixture() -> CityPdConfig {
    CityPdConfig {
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
    }
}

fn config_wire_fixture() -> String {
    let repeated = |n: u8, count: usize| format!("[{}]", vec![n.to_string(); count].join(","));
    format!("babylon.city-pd-config.v1\0{{\"schema_version\":1,\"campaign_id\":{},\"actor_id\":9,\"authority_id\":{},\"county\":[50,54,49,54,51],\"public_account_id\":{},\"agency_account_id\":{},\"investigator_household_account_id\":{},\"investigator_entitlement_id\":{},\"labor_unit_id\":{},\"visit_hours\":2,\"hourly_wage_micros\":\"3\",\"visit_cost_micros\":\"6\",\"appropriation_micros\":\"10\",\"appropriation_priority\":0,\"content_digest\":{},\"policy_source_digest\":{}}}", repeated(1,16), repeated(2,16), repeated(3,32), repeated(4,32), repeated(5,32), repeated(6,32), repeated(7,32), repeated(8,32), repeated(9,32))
}

#[test]
fn config_round_trips_and_rejects_a_bad_county() {
    let mut config = config_fixture();
    let bytes = practice_contract::encode_city_pd_config(&config).expect("valid config");
    let expected = config_wire_fixture();
    assert_eq!(bytes, expected.as_bytes());
    assert_eq!(
        practice_contract::city_pd_config_digest(&config).expect("valid City PD test fixture"),
        [
            0xe9, 0x88, 0xe4, 0x8b, 0xc0, 0x25, 0x9e, 0x0c, 0x17, 0x1d, 0xf6, 0x5a, 0x78, 0xaf,
            0xe1, 0x67, 0xc1, 0x79, 0x0c, 0x70, 0x23, 0xdb, 0xc2, 0xa7, 0x5d, 0x0d, 0x02, 0x34,
            0x12, 0x55, 0x9f, 0x08
        ]
    );
    assert_eq!(
        practice_contract::decode_city_pd_config(&bytes).expect("decode"),
        config
    );
    config.county = *b"26x63";
    assert!(practice_contract::encode_city_pd_config(&config).is_err());
}

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
    c.case_id = practice_contract::city_pd_case_id(&c).expect("valid City PD test fixture");
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
    i.intent_id = practice_contract::city_pd_intent_id(&i).expect("valid City PD test fixture");
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
    d.decision_id = practice_contract::city_pd_decision_id(&d).expect("valid City PD test fixture");
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
    r.receipt_id = practice_contract::city_pd_receipt_id(&r).expect("valid City PD test fixture");
    r
}
#[test]
fn all_wire_contracts_round_trip_and_bind_content() {
    let c = case();
    let i = intent();
    let d = decision();
    let r = receipt();
    assert_eq!(
        practice_contract::decode_city_pd_case(
            &practice_contract::encode_city_pd_case(&c).expect("valid City PD test fixture")
        )
        .expect("valid City PD test fixture"),
        c
    );
    assert_eq!(
        practice_contract::decode_city_pd_intent(
            &practice_contract::encode_city_pd_intent(&i).expect("valid City PD test fixture")
        )
        .expect("valid City PD test fixture"),
        i
    );
    assert_eq!(
        practice_contract::decode_city_pd_decision(
            &practice_contract::encode_city_pd_decision(&d).expect("valid City PD test fixture")
        )
        .expect("valid City PD test fixture"),
        d
    );
    assert_eq!(
        practice_contract::decode_city_pd_receipt(
            &practice_contract::encode_city_pd_receipt(&r).expect("valid City PD test fixture")
        )
        .expect("valid City PD test fixture"),
        r
    );
    let mut closed = c.clone();
    closed.status = CityPdCaseStatus::Closed;
    assert_eq!(
        practice_contract::city_pd_case_id(&closed).expect("valid City PD test fixture"),
        c.case_id
    );
    closed.subject_id += 1;
    assert_ne!(
        practice_contract::city_pd_case_id(&closed).expect("valid City PD test fixture"),
        c.case_id
    );
    let mut changed = i.clone();
    changed.cost_micros += 1;
    assert_ne!(
        practice_contract::city_pd_intent_id(&changed).expect("valid City PD test fixture"),
        i.intent_id
    );
    let mut changed = d.clone();
    changed.period += 1;
    assert_ne!(
        practice_contract::city_pd_decision_id(&changed).expect("valid City PD test fixture"),
        d.decision_id
    );
    let mut changed = r.clone();
    changed.wage_micros += 1;
    assert_ne!(
        practice_contract::city_pd_receipt_id(&changed).expect("valid City PD test fixture"),
        r.receipt_id
    );
}
#[test]
fn provenance_and_wire_corruption_refuse() {
    let mut c = case();
    c.source_kind = CityPdCaseSource::ObservedOrganizerReceipt;
    assert_eq!(
        practice_contract::validate_city_pd_case(&c),
        Err(CityPdError::InvalidProvenance)
    );
    c.source_receipt_id = Some([1; 32]);
    c.case_source_witness_id = Some([2; 32]);
    c.case_id = practice_contract::city_pd_case_id(&c).expect("valid City PD test fixture");
    assert!(practice_contract::validate_city_pd_case(&c).is_ok());
    c.observed_period = 2;
    c.acquired_period = 1;
    assert_eq!(
        practice_contract::validate_city_pd_case(&c),
        Err(CityPdError::InvalidTiming)
    );
    let bytes =
        practice_contract::encode_city_pd_intent(&intent()).expect("valid City PD test fixture");
    let mut trailing = bytes.clone();
    trailing.push(b' ');
    assert!(practice_contract::decode_city_pd_intent(&trailing).is_err());
    let raw = String::from_utf8(bytes).expect("valid City PD test fixture");
    assert!(practice_contract::decode_city_pd_intent(
        raw.replace("\"cost_micros\":\"6\"", "\"cost_micros\":\"06\"")
            .as_bytes()
    )
    .is_err());
    assert!(practice_contract::decode_city_pd_intent(
        raw.replace("\"schema_version\":1", "\"schema_version\":2")
            .as_bytes()
    )
    .is_err());
    assert!(practice_contract::decode_city_pd_intent(
        raw.replace("\"subject_id\":20", "\"unknown\":0,\"subject_id\":20")
            .as_bytes()
    )
    .is_err());
    assert_eq!(
        practice_contract::decode_city_pd_intent(&vec![0; 1024 * 1024 + 1]),
        Err(CityPdError::SizeLimit)
    );
}
#[test]
fn receipt_rejects_unpaid_fabrication_and_unsorted_facts() {
    let mut r = receipt();
    assert!(practice_contract::validate_city_pd_receipt(&r).is_ok());
    r.outcome = CityPdOutcome::InsufficientTime;
    r.receipt_id = practice_contract::city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert_eq!(
        practice_contract::validate_city_pd_receipt(&r),
        Err(CityPdError::InvalidReceipt)
    );
    r.attendance_hours = 0;
    r.wage_micros = 0;
    r.payment_receipt_id = None;
    r.player_witness_evidence_id = Some([7; 32]);
    r.receipt_id = practice_contract::city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert_eq!(
        practice_contract::validate_city_pd_receipt(&r),
        Err(CityPdError::InvalidReceipt)
    );
    r.player_witness_evidence_id = None;
    r.acquired_public_fact_ids = vec![[2; 32], [1; 32]];
    r.receipt_id = practice_contract::city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert_eq!(
        practice_contract::validate_city_pd_receipt(&r),
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
    r.receipt_id = practice_contract::city_pd_receipt_id(&r).expect("valid City PD test fixture");
    assert!(practice_contract::validate_city_pd_receipt(&r).is_ok());
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
        r.receipt_id =
            practice_contract::city_pd_receipt_id(&r).expect("valid City PD test fixture");
        assert!(practice_contract::validate_city_pd_receipt(&r).is_ok());
        r.acquired_public_fact_ids = vec![[1; 32]];
        assert_eq!(
            practice_contract::validate_city_pd_receipt(&r),
            Err(CityPdError::InvalidReceipt)
        );
        r.acquired_public_fact_ids.clear();
        r.payment_receipt_id = Some([1; 32]);
        assert_eq!(
            practice_contract::validate_city_pd_receipt(&r),
            Err(CityPdError::InvalidReceipt)
        );
        r.payment_receipt_id = None;
    }
    r.acquired_public_fact_ids = vec![[1; 32], [1; 32]];
    assert_eq!(
        practice_contract::validate_city_pd_receipt(&r),
        Err(CityPdError::InvalidReceipt)
    );
    r.acquired_public_fact_ids = vec![[1; 32]; CITY_PD_MAX_ROWS + 1];
    assert_eq!(
        practice_contract::validate_city_pd_receipt(&r),
        Err(CityPdError::SizeLimit)
    );
}

#[test]
fn wire_rejects_wrong_domain_unknown_tag_bad_money_and_ids() {
    let case_bytes = String::from_utf8(
        practice_contract::encode_city_pd_case(&case()).expect("valid City PD test fixture"),
    )
    .expect("valid City PD test fixture");
    assert!(practice_contract::decode_city_pd_case(
        case_bytes
            .replace("captured_public_record", "unknown")
            .as_bytes()
    )
    .is_err());
    assert!(practice_contract::decode_city_pd_case(
        case_bytes
            .replacen("city-pd-case", "city-pd-other", 1)
            .as_bytes()
    )
    .is_err());
    let raw = String::from_utf8(
        practice_contract::encode_city_pd_intent(&intent()).expect("valid City PD test fixture"),
    )
    .expect("valid City PD test fixture");
    for amount in ["-1", "+6", "06", "170141183460469231731687303715884105728"] {
        assert!(practice_contract::decode_city_pd_intent(
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
    assert_eq!(
        practice_contract::validate_city_pd_case(&c),
        Err(CityPdError::InvalidId)
    );
    let mut i = intent();
    i.resolve_period = 3;
    assert_eq!(
        practice_contract::validate_city_pd_intent(&i),
        Err(CityPdError::InvalidTiming)
    );
    i.source_period = u64::MAX;
    assert_eq!(
        practice_contract::validate_city_pd_intent(&i),
        Err(CityPdError::Arithmetic)
    );
}

#[test]
fn finalizing_receipts_sorts_and_deduplicates_facts() {
    let mut draft = receipt();
    draft.acquired_public_fact_ids = vec![[2; 32], [1; 32], [2; 32]];
    let finalized =
        practice_contract::finalize_city_pd_receipt(draft).expect("valid City PD test fixture");
    assert_eq!(finalized.acquired_public_fact_ids, vec![[1; 32], [2; 32]]);
    assert_eq!(
        practice_contract::decode_city_pd_receipt(
            &practice_contract::encode_city_pd_receipt(&finalized)
                .expect("valid City PD test fixture")
        )
        .expect("valid City PD test fixture"),
        finalized
    );
}

// These literals specify the wire layout independently of the production encoder.
const CASE_ID: [u8; 32] = [
    65, 12, 237, 234, 57, 45, 215, 71, 133, 2, 77, 224, 113, 171, 128, 148, 108, 206, 247, 15, 32,
    231, 86, 168, 100, 113, 107, 222, 27, 18, 34, 44,
];
const INTENT_ID: [u8; 32] = [
    4, 223, 203, 183, 28, 59, 114, 113, 230, 54, 111, 242, 105, 251, 78, 63, 99, 207, 1, 103, 229,
    55, 18, 250, 28, 79, 32, 36, 46, 144, 67, 153,
];
const DECISION_ID: [u8; 32] = [
    180, 182, 149, 206, 162, 60, 49, 112, 9, 202, 42, 179, 253, 87, 116, 122, 240, 243, 99, 235,
    148, 160, 235, 83, 93, 36, 46, 236, 193, 49, 140, 36,
];
const RECEIPT_ID: [u8; 32] = [
    29, 71, 33, 249, 133, 250, 214, 206, 247, 184, 117, 30, 50, 13, 43, 1, 108, 109, 183, 150, 150,
    169, 135, 211, 54, 206, 48, 48, 170, 180, 239, 26,
];
fn wire_array(bytes: &[u8]) -> String {
    format!(
        "[{}]",
        bytes
            .iter()
            .map(u8::to_string)
            .collect::<Vec<_>>()
            .join(",")
    )
}
fn intent_wire_fields() -> String {
    format!("\"intent_id\":{},\"schema_version\":1,\"campaign_id\":{},\"actor_id\":9,\"authority_id\":{},\"config_digest\":{},\"decision_basis_digest\":{},\"case_id\":{},\"subject_id\":20,\"source_period\":1,\"resolve_period\":2,\"cost_micros\":\"6\"", wire_array(&INTENT_ID), wire_array(&[1; 16]), wire_array(&[2; 16]), wire_array(&[3; 32]), wire_array(&[4; 32]), wire_array(&CASE_ID))
}
#[test]
fn independent_complete_wire_fixtures_include_ids_and_case_status() {
    let case_wire = format!("babylon.city-pd-case.v1\0{{\"case_id\":{},\"actor_id\":9,\"subject_id\":20,\"county\":[50,54,49,54,51],\"public_venue_id\":{},\"source_id\":{},\"source_kind\":\"captured_public_record\",\"source_receipt_id\":null,\"case_source_witness_id\":null,\"observed_period\":0,\"acquired_period\":0,\"status\":\"open\"}}", wire_array(&CASE_ID), wire_array(&[1; 32]), wire_array(&[2; 32]));
    let intent_wire = format!("babylon.city-pd-intent.v1\0{{{}}}", intent_wire_fields());
    let decision_wire = format!("babylon.city-pd-decision.v1\0{{\"decision_id\":{},\"campaign_id\":{},\"actor_id\":9,\"period\":1,\"decision_basis_digest\":{},\"decision\":{{\"kind\":\"selected\",{}}}}}", wire_array(&DECISION_ID), wire_array(&[1;16]), wire_array(&[4;32]), intent_wire_fields());
    let receipt_wire = format!("babylon.city-pd-receipt.v1\0{{\"receipt_id\":{},\"campaign_id\":{},\"actor_id\":9,\"case_id\":{},\"intent_id\":{},\"resolve_period\":2,\"outcome\":\"completed\",\"attendance_hours\":2,\"wage_micros\":\"6\",\"shift_receipt_id\":{},\"payment_receipt_id\":{},\"acquired_public_fact_ids\":[],\"case_source_evidence_id\":null,\"player_witness_evidence_id\":null}}", wire_array(&RECEIPT_ID), wire_array(&[1;16]), wire_array(&CASE_ID), wire_array(&INTENT_ID), wire_array(&[5;32]), wire_array(&[6;32]));
    assert_eq!(
        practice_contract::encode_city_pd_case(&case()).expect("case"),
        case_wire.as_bytes()
    );
    assert_eq!(
        practice_contract::encode_city_pd_intent(&intent()).expect("intent"),
        intent_wire.as_bytes()
    );
    assert_eq!(
        practice_contract::encode_city_pd_decision(&decision()).expect("decision"),
        decision_wire.as_bytes()
    );
    assert_eq!(
        practice_contract::encode_city_pd_receipt(&receipt()).expect("receipt"),
        receipt_wire.as_bytes()
    );
    assert_eq!(
        practice_contract::decode_city_pd_case(case_wire.as_bytes()).expect("case"),
        case()
    );
    assert_eq!(
        practice_contract::decode_city_pd_intent(intent_wire.as_bytes()).expect("intent"),
        intent()
    );
    assert_eq!(
        practice_contract::decode_city_pd_decision(decision_wire.as_bytes()).expect("decision"),
        decision()
    );
    assert_eq!(
        practice_contract::decode_city_pd_receipt(receipt_wire.as_bytes()).expect("receipt"),
        receipt()
    );
    let mut closed = case();
    closed.status = CityPdCaseStatus::Closed;
    assert_eq!(
        practice_contract::city_pd_case_id(&closed).expect("case identity"),
        CASE_ID
    );
    assert_eq!(
        practice_contract::encode_city_pd_case(&closed).expect("closed case"),
        case_wire
            .replace("\"status\":\"open\"", "\"status\":\"closed\"")
            .as_bytes()
    );
    assert_eq!(
        practice_contract::decode_city_pd_case(
            case_wire
                .replacen(&wire_array(&CASE_ID), &wire_array(&[42; 32]), 1)
                .as_bytes()
        ),
        Err(CityPdError::InvalidIdentity)
    );
    assert_eq!(
        practice_contract::decode_city_pd_intent(
            intent_wire
                .replacen(&wire_array(&INTENT_ID), &wire_array(&[42; 32]), 1)
                .as_bytes()
        ),
        Err(CityPdError::InvalidIdentity)
    );
    assert_eq!(
        practice_contract::decode_city_pd_decision(
            decision_wire
                .replacen(&wire_array(&DECISION_ID), &wire_array(&[42; 32]), 1)
                .as_bytes()
        ),
        Err(CityPdError::InvalidIdentity)
    );
    assert_eq!(
        practice_contract::decode_city_pd_receipt(
            receipt_wire
                .replacen(&wire_array(&RECEIPT_ID), &wire_array(&[42; 32]), 1)
                .as_bytes()
        ),
        Err(CityPdError::InvalidIdentity)
    );
}

#[test]
fn config_digest_binds_each_valid_field() {
    let base = config_fixture();
    let original = practice_contract::city_pd_config_digest(&base).expect("config");
    let changes: &[fn(&mut CityPdConfig)] = &[
        |c| c.campaign_id = [11; 16],
        |c| c.actor_id = 10,
        |c| c.authority_id = [12; 16],
        |c| c.county = *b"26161",
        |c| c.public_account_id = [13; 32],
        |c| c.agency_account_id = [14; 32],
        |c| c.investigator_household_account_id = [15; 32],
        |c| c.investigator_entitlement_id = [16; 32],
        |c| c.labor_unit_id = [17; 32],
        |c| {
            c.visit_hours = 3;
            c.visit_cost_micros = 9;
        },
        |c| {
            c.hourly_wage_micros = 4;
            c.visit_cost_micros = 8;
        },
        |c| c.appropriation_micros = 11,
        |c| c.appropriation_priority = 1,
        |c| c.content_digest = [18; 32],
        |c| c.policy_source_digest = [19; 32],
    ];
    for change in changes {
        let mut c = base.clone();
        change(&mut c);
        assert_ne!(
            practice_contract::city_pd_config_digest(&c).expect("valid changed config"),
            original
        );
    }
    // Hours and wage changes necessarily change cost too. Compare complete
    // independently specified wire bytes so the derived cost cannot be omitted.
    let mut c = base.clone();
    c.visit_hours = 3;
    c.visit_cost_micros = 9;
    let expected = config_wire_fixture()
        .replace("\"visit_hours\":2", "\"visit_hours\":3")
        .replace("\"visit_cost_micros\":\"6\"", "\"visit_cost_micros\":\"9\"");
    assert_eq!(
        practice_contract::city_pd_config_digest(&c).expect("changed price"),
        babylon_kernel::content_digest::sha256_of(expected.as_bytes())
    );
    let mut c = base;
    c.schema_version = 2;
    assert_eq!(
        practice_contract::city_pd_config_digest(&c),
        Err(CityPdError::UnsupportedSchema)
    );
}

#[test]
fn case_identity_binds_each_source_and_material_field() {
    let base = case();
    let changes: &[fn(&mut CityPdCase)] = &[
        |c| c.actor_id = 10,
        |c| c.subject_id = 21,
        |c| c.county = *b"26161",
        |c| c.public_venue_id = [3; 32],
        |c| c.source_id = [4; 32],
        |c| {
            c.source_kind = CityPdCaseSource::ObservedOrganizerReceipt;
            c.source_receipt_id = Some([5; 32]);
            c.case_source_witness_id = Some([6; 32]);
        },
        |c| {
            c.observed_period = 1;
            c.acquired_period = 1;
        },
        |c| c.acquired_period = 1,
    ];
    for change in changes {
        let mut c = base.clone();
        change(&mut c);
        c.case_id = practice_contract::city_pd_case_id(&c).expect("case body");
        assert_ne!(c.case_id, base.case_id);
        assert!(practice_contract::validate_city_pd_case(&c).is_ok());
    }
    let mut earlier = base.clone();
    earlier.acquired_period = 1;
    earlier.case_id = practice_contract::city_pd_case_id(&earlier).expect("acquired case");
    let mut later = earlier.clone();
    later.observed_period = 1;
    later.case_id = practice_contract::city_pd_case_id(&later).expect("observed case");
    assert_ne!(later.case_id, earlier.case_id);
    assert!(practice_contract::validate_city_pd_case(&later).is_ok());
    let mut observed = base.clone();
    observed.source_kind = CityPdCaseSource::ObservedOrganizerReceipt;
    observed.source_receipt_id = Some([5; 32]);
    observed.case_source_witness_id = Some([6; 32]);
    observed.case_id = practice_contract::city_pd_case_id(&observed).expect("observed");
    for change in [
        |c: &mut CityPdCase| c.source_receipt_id = Some([7; 32]),
        |c: &mut CityPdCase| c.case_source_witness_id = Some([8; 32]),
    ] {
        let mut c = observed.clone();
        change(&mut c);
        c.case_id = practice_contract::city_pd_case_id(&c).expect("changed source");
        assert_ne!(c.case_id, observed.case_id);
        assert!(practice_contract::validate_city_pd_case(&c).is_ok());
    }
    let mut wrong_id = base.clone();
    wrong_id.case_id = [42; 32];
    assert_eq!(
        practice_contract::city_pd_case_id(&wrong_id).expect("case body"),
        base.case_id
    );
    assert_eq!(
        practice_contract::validate_city_pd_case(&wrong_id),
        Err(CityPdError::InvalidIdentity)
    );
}

#[test]
fn intent_identity_binds_each_field_and_excludes_own_id() {
    let base = intent();
    let changes: &[fn(&mut CityPdIntent)] = &[
        |i| i.campaign_id = [11; 16],
        |i| i.actor_id = 10,
        |i| i.authority_id = [12; 16],
        |i| i.config_digest = [13; 32],
        |i| i.decision_basis_digest = [14; 32],
        |i| i.case_id = [15; 32],
        |i| i.subject_id = 21,
        |i| {
            i.source_period = 2;
            i.resolve_period = 3;
        },
        |i| i.cost_micros = 7,
    ];
    for change in changes {
        let mut i = base.clone();
        change(&mut i);
        i.intent_id = practice_contract::city_pd_intent_id(&i).expect("intent body");
        assert_ne!(i.intent_id, base.intent_id);
        assert!(practice_contract::validate_city_pd_intent(&i).is_ok());
    }
    // Either timing field is bound individually, even though only a matching
    // source/resolve pair can be admitted by the contract.
    for change in [
        |i: &mut CityPdIntent| i.source_period = 2,
        |i: &mut CityPdIntent| i.resolve_period = 3,
    ] {
        let mut i = base.clone();
        change(&mut i);
        assert_ne!(
            practice_contract::city_pd_intent_id(&i).expect("intent body"),
            base.intent_id
        );
        assert_eq!(
            practice_contract::validate_city_pd_intent(&i),
            Err(CityPdError::InvalidTiming)
        );
    }
    let mut wrong_id = base.clone();
    wrong_id.intent_id = [42; 32];
    assert_eq!(
        practice_contract::city_pd_intent_id(&wrong_id).expect("body"),
        base.intent_id
    );
    assert_eq!(
        practice_contract::validate_city_pd_intent(&wrong_id),
        Err(CityPdError::InvalidIdentity)
    );
    let mut unsupported = base.clone();
    unsupported.schema_version = 2;
    assert_ne!(
        practice_contract::city_pd_intent_id(&unsupported).expect("body"),
        base.intent_id
    );
    assert_eq!(
        practice_contract::validate_city_pd_intent(&unsupported),
        Err(CityPdError::UnsupportedSchema)
    );
}

#[test]
fn decision_identity_binds_every_field_and_nested_decision() {
    let mut base = decision();
    base.decision = CityPdDecision::NoCases;
    base.decision_id = practice_contract::city_pd_decision_id(&base).expect("decision body");
    let changes: &[fn(&mut CityPdDecisionReceipt)] = &[
        |d| d.campaign_id = [11; 16],
        |d| d.actor_id = 10,
        |d| d.period = 2,
        |d| d.decision_basis_digest = [12; 32],
        |d| {
            d.decision = CityPdDecision::NoFunds {
                available_micros: 1,
                required_micros: 6,
            }
        },
        |d| d.decision = CityPdDecision::Selected(intent()),
    ];
    for change in changes {
        let mut d = base.clone();
        change(&mut d);
        d.decision_id = practice_contract::city_pd_decision_id(&d).expect("decision body");
        assert_ne!(d.decision_id, base.decision_id);
        assert!(practice_contract::validate_city_pd_decision(&d).is_ok());
    }
    let original = decision();
    let mut nested = original.clone();
    if let CityPdDecision::Selected(i) = &mut nested.decision {
        i.cost_micros = 7;
        i.intent_id = practice_contract::city_pd_intent_id(i).expect("intent body");
    }
    nested.decision_id = practice_contract::city_pd_decision_id(&nested).expect("decision body");
    assert_ne!(nested.decision_id, original.decision_id);
    assert!(practice_contract::validate_city_pd_decision(&nested).is_ok());
    let mut wrong_id = original.clone();
    wrong_id.decision_id = [42; 32];
    assert_eq!(
        practice_contract::city_pd_decision_id(&wrong_id).expect("body"),
        original.decision_id
    );
    assert_eq!(
        practice_contract::validate_city_pd_decision(&wrong_id),
        Err(CityPdError::InvalidIdentity)
    );
}

#[test]
fn receipt_identity_binds_every_field_and_excludes_own_id() {
    let base = receipt();
    let changes: &[fn(&mut CityPdReceipt)] = &[
        |r| r.campaign_id = [11; 16],
        |r| r.actor_id = 10,
        |r| r.case_id = [12; 32],
        |r| r.intent_id = [13; 32],
        |r| r.resolve_period = 3,
        |r| {
            r.outcome = CityPdOutcome::InsufficientFunds;
            r.attendance_hours = 0;
            r.wage_micros = 0;
            r.payment_receipt_id = None;
        },
        |r| r.attendance_hours = 3,
        |r| r.wage_micros = 7,
        |r| r.shift_receipt_id = Some([14; 32]),
        |r| r.payment_receipt_id = Some([15; 32]),
        |r| r.acquired_public_fact_ids = vec![[16; 32]],
        |r| r.case_source_evidence_id = Some([17; 32]),
        |r| r.player_witness_evidence_id = Some([18; 32]),
    ];
    for change in changes {
        let mut r = base.clone();
        change(&mut r);
        r.receipt_id = practice_contract::city_pd_receipt_id(&r).expect("receipt body");
        assert_ne!(r.receipt_id, base.receipt_id);
        assert!(practice_contract::validate_city_pd_receipt(&r).is_ok());
    }
    let mut wrong_id = base.clone();
    wrong_id.receipt_id = [42; 32];
    assert_eq!(
        practice_contract::city_pd_receipt_id(&wrong_id).expect("body"),
        base.receipt_id
    );
    assert_eq!(
        practice_contract::validate_city_pd_receipt(&wrong_id),
        Err(CityPdError::InvalidIdentity)
    );
}
