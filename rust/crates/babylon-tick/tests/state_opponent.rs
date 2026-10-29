use babylon_graph::{dossier::Dossier, substrate::NodeId};
use babylon_kernel::currency::Currency;
use babylon_practice_contract::*;
use babylon_tick::state_opponent::{decide_city_pd, CityPdState};
fn config() -> CityPdConfig {
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
fn case(subject_id: u64, source: u8) -> CityPdCase {
    let mut c = CityPdCase {
        case_id: [0; 32],
        actor_id: 9,
        subject_id,
        county: *b"26163",
        public_venue_id: [1; 32],
        source_id: [source; 32],
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
#[test]
fn decision_distinguishes_no_cases_funds_and_selection() {
    let mut state = CityPdState {
        dossier: Dossier::new(NodeId(9)),
        cases: vec![],
        last_decision: None,
    };
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(0), 0)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::NoCases
    );
    state.dossier.resolve_node(NodeId(20));
    state.cases.push(case(20, 2));
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(0), 0)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::NoFunds {
            available_micros: 0,
            required_micros: 6
        }
    );
    let decision = decide_city_pd(&config(), &state, Currency::from_micro_units(6), 1)
        .expect("valid City PD test fixture");
    let CityPdDecision::Selected(intent) = decision.decision else {
        panic!("selected")
    };
    assert_eq!(intent.resolve_period, 2);
}

#[test]
fn choices_are_order_independent_and_choose_one() {
    let mut a = Dossier::new(NodeId(9));
    a.resolve_node(NodeId(30));
    a.resolve_node(NodeId(20));
    let mut b = Dossier::new(NodeId(9));
    b.resolve_node(NodeId(20));
    b.resolve_node(NodeId(30));
    let first = case(20, 2);
    let second = case(20, 3);
    let other = case(30, 4);
    let left = CityPdState {
        dossier: a,
        cases: vec![other.clone(), first.clone(), second.clone()],
        last_decision: None,
    };
    let right = CityPdState {
        dossier: b,
        cases: vec![second.clone(), first.clone(), other],
        last_decision: None,
    };
    let d = decide_city_pd(&config(), &left, Currency::from_micro_units(100), 0)
        .expect("valid City PD test fixture");
    assert_eq!(
        d,
        decide_city_pd(&config(), &right, Currency::from_micro_units(100), 0)
            .expect("valid City PD test fixture")
    );
    let CityPdDecision::Selected(intent) = &d.decision else {
        panic!("selected")
    };
    assert_eq!(intent.subject_id, 20);
    assert_eq!(intent.case_id, first.case_id.min(second.case_id));
    assert_ne!(
        d.decision_basis_digest,
        decide_city_pd(&config(), &left, Currency::from_micro_units(99), 0)
            .expect("valid City PD test fixture")
            .decision_basis_digest
    );
    let mut different = right;
    different.dossier.forget_node(NodeId(20));
    different.cases.retain(|c| c.subject_id == 30);
    let CityPdDecision::Selected(intent) =
        decide_city_pd(&config(), &different, Currency::from_micro_units(6), 0)
            .expect("valid City PD test fixture")
            .decision
    else {
        panic!("selected")
    };
    assert_eq!(intent.subject_id, 30);
}
#[test]
fn rejects_foreign_unknown_duplicate_and_bad_time() {
    let mut dossier = Dossier::new(NodeId(9));
    dossier.resolve_node(NodeId(20));
    let mut state = CityPdState {
        dossier,
        cases: vec![case(20, 2)],
        last_decision: None,
    };
    let run = |s: &CityPdState| decide_city_pd(&config(), s, Currency::from_micro_units(6), 0);
    state.cases.push(state.cases[0].clone());
    assert_eq!(run(&state), Err(CityPdError::DuplicateCase));
    state.cases.pop();
    state.dossier.forget_node(NodeId(20));
    assert_eq!(run(&state), Err(CityPdError::UnknownSubject));
    state.dossier.resolve_node(NodeId(20));
    state.cases[0].actor_id = 10;
    state.cases[0].case_id = city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(run(&state), Err(CityPdError::WrongOwner));
    state.cases[0].actor_id = 9;
    state.cases[0].county = *b"26161";
    state.cases[0].case_id = city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(run(&state), Err(CityPdError::CountyMismatch));
    state.cases[0].county = *b"26163";
    state.cases[0].acquired_period = 1;
    state.cases[0].case_id = city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(run(&state), Err(CityPdError::InvalidTiming));
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(-1), 0),
        Err(CityPdError::NegativeBalance)
    );
    state.cases[0].acquired_period = 0;
    state.cases[0].case_id = city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(6), u64::MAX),
        Err(CityPdError::Arithmetic)
    );
}

#[test]
fn basis_is_independently_pinned_and_price_bound_is_inclusive() {
    let mut dossier = Dossier::new(NodeId(9));
    dossier.resolve_node(NodeId(20));
    let state = CityPdState {
        dossier,
        cases: vec![case(20, 2)],
        last_decision: None,
    };
    let d = decide_city_pd(&config(), &state, Currency::from_micro_units(6), 1)
        .expect("valid City PD test fixture");
    assert_eq!(
        d.decision_basis_digest,
        [
            85, 52, 234, 77, 234, 10, 235, 197, 174, 187, 182, 188, 179, 121, 27, 174, 187, 84, 63,
            146, 16, 230, 87, 183, 224, 247, 68, 111, 248, 78, 209, 76
        ]
    );
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(5), 1)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::NoFunds {
            available_micros: 5,
            required_micros: 6
        }
    );
    let mut c = config();
    c.visit_hours = 1;
    c.hourly_wage_micros = CITY_PD_MAX_COST;
    c.visit_cost_micros = CITY_PD_MAX_COST;
    assert!(matches!(
        decide_city_pd(&c, &state, Currency::from_micro_units(CITY_PD_MAX_COST), 1)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::Selected(_)
    ));
    c.hourly_wage_micros += 1;
    c.visit_cost_micros += 1;
    assert_eq!(
        decide_city_pd(
            &c,
            &state,
            Currency::from_micro_units(CITY_PD_MAX_COST + 1),
            1
        ),
        Err(CityPdError::InvalidPrice)
    );
    c.hourly_wage_micros = i128::MAX;
    c.visit_hours = 2;
    c.visit_cost_micros = 6;
    assert_eq!(
        decide_city_pd(&c, &state, Currency::from_micro_units(6), 1),
        Err(CityPdError::Arithmetic)
    );
}

#[test]
fn validates_owner_provenance_closed_cases_and_case_limit() {
    let mut dossier = Dossier::new(NodeId(9));
    dossier.resolve_node(NodeId(20));
    let mut state = CityPdState {
        dossier,
        cases: vec![case(20, 2)],
        last_decision: None,
    };
    state.dossier = Dossier::new(NodeId(10));
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(0), 0),
        Err(CityPdError::WrongOwner)
    );
    state.dossier = Dossier::new(NodeId(9));
    state.dossier.resolve_node(NodeId(20));
    state.cases[0].source_kind = CityPdCaseSource::ObservedOrganizerReceipt;
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(6), 0),
        Err(CityPdError::InvalidProvenance)
    );
    state.cases[0] = case(20, 2);
    state.cases[0].status = CityPdCaseStatus::Closed;
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(0), 0)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::NoCases
    );
    state.cases = vec![case(20, 2); CITY_PD_MAX_ROWS + 1];
    assert_eq!(
        decide_city_pd(&config(), &state, Currency::from_micro_units(0), 0),
        Err(CityPdError::SizeLimit)
    );
}

#[test]
fn decision_basis_literal_bytes_and_each_input_are_bound() {
    use babylon_kernel::content_digest::sha256_of;
    // Independent preimage: domain, config digest, actor, T, signed balance,
    // one scope ID, and one case ID followed by its open status byte.
    let bytes: &[u8] = &[
        b'b', b'a', b'b', b'y', b'l', b'o', b'n', b'.', b'c', b'i', b't', b'y', b'-', b'p', b'd',
        b'-', b'd', b'e', b'c', b'i', b's', b'i', b'o', b'n', b'-', b'b', b'a', b's', b'i', b's',
        b'.', b'v', b'1', 0, 0xe9, 0x88, 0xe4, 0x8b, 0xc0, 0x25, 0x9e, 0x0c, 0x17, 0x1d, 0xf6,
        0x5a, 0x78, 0xaf, 0xe1, 0x67, 0xc1, 0x79, 0x0c, 0x70, 0x23, 0xdb, 0xc2, 0xa7, 0x5d, 0x0d,
        0x02, 0x34, 0x12, 0x55, 0x9f, 0x08, 0, 0, 0, 0, 0, 0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 20, 0, 0, 0, 1,
        65, 12, 237, 234, 57, 45, 215, 71, 133, 2, 77, 224, 113, 171, 128, 148, 108, 206, 247, 15,
        32, 231, 86, 168, 100, 113, 107, 222, 27, 18, 34, 44, 1,
    ];
    let mut dossier = Dossier::new(NodeId(9));
    dossier.resolve_node(NodeId(20));
    let state = CityPdState {
        dossier,
        cases: vec![case(20, 2)],
        last_decision: None,
    };
    let original = decide_city_pd(&config(), &state, Currency::from_micro_units(6), 1)
        .expect("decision")
        .decision_basis_digest;
    assert_eq!(
        sha256_of(bytes),
        [
            85, 52, 234, 77, 234, 10, 235, 197, 174, 187, 182, 188, 179, 121, 27, 174, 187, 84, 63,
            146, 16, 230, 87, 183, 224, 247, 68, 111, 248, 78, 209, 76
        ]
    );
    assert_eq!(original, sha256_of(bytes));
    let basis = |c: &CityPdConfig, s: &CityPdState, balance, period| {
        decide_city_pd(c, s, Currency::from_micro_units(balance), period)
            .expect("changed decision")
            .decision_basis_digest
    };
    let mut changed_config = config();
    changed_config.content_digest = [10; 32];
    assert_ne!(basis(&changed_config, &state, 6, 1), original);
    assert_ne!(basis(&config(), &state, 7, 1), original);
    assert_ne!(basis(&config(), &state, 6, 2), original);
    let mut changed_scope = state.clone();
    changed_scope.dossier.resolve_node(NodeId(30));
    assert_ne!(basis(&config(), &changed_scope, 6, 1), original);
    let mut changed_case = state.clone();
    changed_case.cases[0] = case(20, 3);
    assert_ne!(basis(&config(), &changed_case, 6, 1), original);
    let mut added_case = state.clone();
    added_case.cases.push(case(20, 3));
    assert_ne!(basis(&config(), &added_case, 6, 1), original);
    let mut closed = state.clone();
    closed.cases[0].status = CityPdCaseStatus::Closed;
    assert_eq!(closed.cases[0].case_id, state.cases[0].case_id);
    assert_ne!(basis(&config(), &closed, 6, 1), original);
    let mut actor_config = config();
    actor_config.actor_id = 10;
    let mut actor_state = state.clone();
    actor_state.dossier = Dossier::new(NodeId(10));
    actor_state.dossier.resolve_node(NodeId(20));
    actor_state.cases[0].actor_id = 10;
    actor_state.cases[0].case_id = city_pd_case_id(&actor_state.cases[0]).expect("changed case");
    assert_ne!(basis(&actor_config, &actor_state, 6, 1), original);
}
