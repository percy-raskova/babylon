use babylon_graph::dossier::Dossier;
use babylon_graph::substrate::NodeId;
use babylon_kernel::currency::Currency;
use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    CityPdCase, CityPdCaseSource, CityPdCaseStatus, CityPdConfig, CityPdDecision,
    CityPdDecisionReceipt, CityPdError, CITY_PD_MAX_COST, CITY_PD_MAX_ROWS,
};
use babylon_tick::state_opponent::{self, CityPdState};
fn run_decision(
    config: &CityPdConfig,
    state: &CityPdState,
    available: Currency,
    period: u64,
) -> Result<CityPdDecisionReceipt, CityPdError> {
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::stable_element::StableElementResolver;
    use babylon_graph::substrate::GraphSubstrate;
    use std::collections::HashMap;
    let mut graph = MemoryGraph::new();
    let mut names = HashMap::new();
    for id in 0..=30 {
        let node = graph
            .add_node("actor")
            .expect("valid identity test fixture");
        let name = match id {
            20 => "a20".to_owned(),
            30 => "b30".to_owned(),
            _ => format!("node{id}"),
        };
        names.insert(node, name);
    }
    let resolver = StableElementResolver::seal(&graph, "demo/world", &names, &HashMap::new())
        .expect("valid identity test fixture");
    let bindings = (0..=30)
        .map(|id| {
            (
                id,
                resolver
                    .node_key(NodeId(id))
                    .expect("valid identity test fixture")
                    .clone(),
            )
        })
        .collect::<Vec<_>>();
    state_opponent::decide_city_pd(config, state, &resolver, &bindings, available, period)
}
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
    c.case_id = practice_contract::city_pd_case_id(&c).expect("valid City PD test fixture");
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
        run_decision(&config(), &state, Currency::from_micro_units(0), 0)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::NoCases
    );
    state.dossier.resolve_node(NodeId(20));
    state.cases.push(case(20, 2));
    assert_eq!(
        run_decision(&config(), &state, Currency::from_micro_units(0), 0)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::NoFunds {
            available_micros: 0,
            required_micros: 6
        }
    );
    let decision = run_decision(&config(), &state, Currency::from_micro_units(6), 1)
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
    let d = run_decision(&config(), &left, Currency::from_micro_units(100), 0)
        .expect("valid City PD test fixture");
    assert_eq!(
        d,
        run_decision(&config(), &right, Currency::from_micro_units(100), 0)
            .expect("valid City PD test fixture")
    );
    let mut different_tie_belief = right.clone();
    different_tie_belief
        .dossier
        .resolve_edge("believed-only", NodeId(20), NodeId(30));
    assert_eq!(
        d,
        run_decision(
            &config(),
            &different_tie_belief,
            Currency::from_micro_units(100),
            0,
        )
        .expect("private ties are not a decision input")
    );
    let CityPdDecision::Selected(intent) = &d.decision else {
        panic!("selected")
    };
    assert_eq!(intent.subject_id, 20);
    assert_eq!(intent.case_id, first.case_id.min(second.case_id));
    assert_ne!(
        d.decision_basis_digest,
        run_decision(&config(), &left, Currency::from_micro_units(99), 0)
            .expect("valid City PD test fixture")
            .decision_basis_digest
    );
    let mut different = right;
    different.dossier.forget_node(NodeId(20));
    different.cases.retain(|c| c.subject_id == 30);
    let CityPdDecision::Selected(intent) =
        run_decision(&config(), &different, Currency::from_micro_units(6), 0)
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
    let run = |s: &CityPdState| run_decision(&config(), s, Currency::from_micro_units(6), 0);
    state.cases.push(state.cases[0].clone());
    assert_eq!(run(&state), Err(CityPdError::DuplicateCase));
    state.cases.pop();
    state.dossier.forget_node(NodeId(20));
    assert_eq!(run(&state), Err(CityPdError::UnknownSubject));
    state.dossier.resolve_node(NodeId(20));
    state.cases[0].actor_id = 10;
    state.cases[0].case_id =
        practice_contract::city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(run(&state), Err(CityPdError::WrongOwner));
    state.cases[0].actor_id = 9;
    state.cases[0].county = *b"26161";
    state.cases[0].case_id =
        practice_contract::city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(run(&state), Err(CityPdError::CountyMismatch));
    state.cases[0].county = *b"26163";
    state.cases[0].acquired_period = 1;
    state.cases[0].case_id =
        practice_contract::city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(run(&state), Err(CityPdError::InvalidTiming));
    assert_eq!(
        run_decision(&config(), &state, Currency::from_micro_units(-1), 0),
        Err(CityPdError::NegativeBalance)
    );
    state.cases[0].acquired_period = 0;
    state.cases[0].case_id =
        practice_contract::city_pd_case_id(&state.cases[0]).expect("valid City PD test fixture");
    assert_eq!(
        run_decision(&config(), &state, Currency::from_micro_units(6), u64::MAX),
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
    let d = run_decision(&config(), &state, Currency::from_micro_units(6), 1)
        .expect("valid City PD test fixture");
    // Independently framed v2 preimage: known config and case digests, actor 9,
    // period 1, balance 6, and the stable node key demo/world/a20.
    assert_eq!(
        d.decision_basis_digest,
        [
            0x97, 0x0e, 0xcc, 0xfb, 0xeb, 0x9c, 0x5a, 0x7c, 0x87, 0xe8, 0x55, 0x9b, 0x13, 0x23,
            0x90, 0x55, 0xcd, 0xd6, 0xd1, 0xb4, 0xf9, 0x80, 0xa9, 0x77, 0x5a, 0x6d, 0xf4, 0xdf,
            0x42, 0x4f, 0xae, 0xdc,
        ]
    );
    assert_eq!(
        run_decision(&config(), &state, Currency::from_micro_units(5), 1)
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
        run_decision(&c, &state, Currency::from_micro_units(CITY_PD_MAX_COST), 1)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::Selected(_)
    ));
    c.hourly_wage_micros += 1;
    c.visit_cost_micros += 1;
    assert_eq!(
        run_decision(
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
        run_decision(&c, &state, Currency::from_micro_units(6), 1),
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
        run_decision(&config(), &state, Currency::from_micro_units(0), 0),
        Err(CityPdError::WrongOwner)
    );
    state.dossier = Dossier::new(NodeId(9));
    state.dossier.resolve_node(NodeId(20));
    state.cases[0].source_kind = CityPdCaseSource::ObservedOrganizerReceipt;
    assert_eq!(
        run_decision(&config(), &state, Currency::from_micro_units(6), 0),
        Err(CityPdError::InvalidProvenance)
    );
    state.cases[0] = case(20, 2);
    state.cases[0].status = CityPdCaseStatus::Closed;
    assert_eq!(
        run_decision(&config(), &state, Currency::from_micro_units(0), 0)
            .expect("valid City PD test fixture")
            .decision,
        CityPdDecision::NoCases
    );
    state.cases = vec![case(20, 2); CITY_PD_MAX_ROWS + 1];
    assert_eq!(
        run_decision(&config(), &state, Currency::from_micro_units(0), 0),
        Err(CityPdError::SizeLimit)
    );
}

#[test]
fn decision_basis_literal_bytes_and_each_input_are_bound() {
    let mut dossier = Dossier::new(NodeId(9));
    dossier.resolve_node(NodeId(20));
    let state = CityPdState {
        dossier,
        cases: vec![case(20, 2)],
        last_decision: None,
    };
    let original = run_decision(&config(), &state, Currency::from_micro_units(6), 1)
        .expect("valid identity test fixture")
        .decision_basis_digest;
    let basis = |c: &CityPdConfig, s: &CityPdState, balance, period| {
        run_decision(c, s, Currency::from_micro_units(balance), period)
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
    actor_state.cases[0].case_id =
        practice_contract::city_pd_case_id(&actor_state.cases[0]).expect("changed case");
    assert_ne!(basis(&actor_config, &actor_state, 6, 1), original);
}

#[derive(Clone, Copy)]
enum AllocationOrder {
    Original,
    Reordered,
}

fn reconstructed_fixture(
    order: AllocationOrder,
) -> (
    babylon_graph::stable_element::StableElementResolver,
    CityPdState,
) {
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::stable_element::StableElementResolver;
    use babylon_graph::substrate::GraphSubstrate;
    use std::collections::HashMap;
    let mut graph = MemoryGraph::new();
    let mut names = HashMap::new();
    if matches!(order, AllocationOrder::Reordered) {
        let hidden = graph.add_node("actor").expect("hidden actor");
        names.insert(hidden, "hidden".to_owned());
    }
    let a = graph.add_node("actor").expect("actor");
    let b = graph.add_node("actor").expect("actor");
    let c = graph.add_node("actor").expect("actor");
    let (agency, alpha, beta) = if matches!(order, AllocationOrder::Reordered) {
        (c, b, a)
    } else {
        (a, b, c)
    };
    names.insert(agency, "agency".to_owned());
    names.insert(alpha, "a20".to_owned());
    names.insert(beta, "b30".to_owned());
    let resolver = StableElementResolver::seal(&graph, "demo/world", &names, &HashMap::new())
        .expect("sealed identities");
    let mut dossier = Dossier::new(agency);
    dossier.resolve_edge("false-belief", alpha, beta);
    (
        resolver,
        CityPdState {
            dossier,
            cases: vec![case(30, 3), case(20, 2)],
            last_decision: None,
        },
    )
}

#[test]
fn semantic_cases_and_decisions_survive_graph_reconstruction() {
    use babylon_graph::stable_element::StableElementResolver;

    let (resolver_a, state_a) = reconstructed_fixture(AllocationOrder::Original);
    let (resolver_b, state_b) = reconstructed_fixture(AllocationOrder::Reordered);
    let bindings = |resolver: &StableElementResolver| {
        [(9, "agency"), (20, "a20"), (30, "b30")]
            .into_iter()
            .map(|(id, name)| {
                (
                    id,
                    resolver
                        .node_key(
                            resolver
                                .node_handle_by_local_name(name)
                                .expect("valid identity test fixture"),
                        )
                        .expect("valid identity test fixture")
                        .clone(),
                )
            })
            .collect::<Vec<_>>()
    };
    let a = state_opponent::decide_city_pd(
        &config(),
        &state_a,
        &resolver_a,
        &bindings(&resolver_a),
        Currency::from_micro_units(6),
        1,
    )
    .expect("first semantic decision");
    let b = state_opponent::decide_city_pd(
        &config(),
        &state_b,
        &resolver_b,
        &bindings(&resolver_b),
        Currency::from_micro_units(6),
        1,
    )
    .expect("reconstructed semantic decision");
    assert_eq!(a, b);
    assert_eq!(
        practice_contract::encode_city_pd_decision(&a).expect("first receipt bytes"),
        practice_contract::encode_city_pd_decision(&b).expect("reconstructed receipt bytes")
    );
    for close in [false, true] {
        let mut left = state_a.clone();
        let mut right = state_b.clone();
        if close {
            for case in left.cases.iter_mut().chain(&mut right.cases) {
                case.status = CityPdCaseStatus::Closed;
            }
        }
        let decide = |state: &CityPdState, resolver: &StableElementResolver| {
            state_opponent::decide_city_pd(
                &config(),
                state,
                resolver,
                &bindings(resolver),
                Currency::from_micro_units(0),
                1,
            )
            .expect("reconstructed refusal decision")
        };
        let left_decision = decide(&left, &resolver_a);
        let right_decision = decide(&right, &resolver_b);
        assert_eq!(left_decision, right_decision);
        if close {
            assert_eq!(left_decision.decision, CityPdDecision::NoCases);
        } else {
            assert!(matches!(
                left_decision.decision,
                CityPdDecision::NoFunds { .. }
            ));
        }
    }
    let CityPdDecision::Selected(intent) = a.decision else {
        panic!("selected")
    };
    let CityPdDecision::Selected(intent_b) = b.decision else {
        panic!("selected")
    };
    assert_eq!(
        practice_contract::encode_city_pd_intent(&intent).expect("first intent bytes"),
        practice_contract::encode_city_pd_intent(&intent_b).expect("reconstructed intent bytes")
    );
    assert_eq!(intent.subject_id, 20);
}

#[test]
fn rejects_missing_conflicting_aliased_and_foreign_relevant_bindings() {
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::stable_element::{StableElementKey, StableElementResolver};
    use babylon_graph::substrate::GraphSubstrate;
    use std::collections::HashMap;
    let mut graph = MemoryGraph::new();
    let owner = graph
        .add_node("actor")
        .expect("valid identity test fixture");
    let subject = graph
        .add_node("actor")
        .expect("valid identity test fixture");
    let other = graph
        .add_node("actor")
        .expect("valid identity test fixture");
    let names = HashMap::from([
        (owner, "agency".to_owned()),
        (subject, "a20".to_owned()),
        (other, "other".to_owned()),
    ]);
    let resolver = StableElementResolver::seal(&graph, "demo/world", &names, &HashMap::new())
        .expect("valid identity test fixture");
    let agency = resolver
        .node_key(owner)
        .expect("valid identity test fixture")
        .clone();
    let target = resolver
        .node_key(subject)
        .expect("valid identity test fixture")
        .clone();
    let other_key = resolver
        .node_key(other)
        .expect("valid identity test fixture")
        .clone();
    let mut dossier = Dossier::new(owner);
    dossier.resolve_node(subject);
    let state = CityPdState {
        dossier,
        cases: vec![case(20, 2)],
        last_decision: None,
    };
    let run = |bindings: &[(u64, StableElementKey)]| {
        state_opponent::decide_city_pd(
            &config(),
            &state,
            &resolver,
            bindings,
            Currency::from_micro_units(6),
            0,
        )
    };
    assert_eq!(
        run(&[(9, agency.clone())]),
        Err(CityPdError::InvalidIdentity)
    );
    assert_eq!(
        run(&[(9, agency.clone()), (20, target.clone()), (20, other_key)]),
        Err(CityPdError::InvalidIdentity)
    );
    assert_eq!(
        run(&[(9, agency.clone()), (20, agency.clone())]),
        Err(CityPdError::InvalidIdentity)
    );
    let foreign = StableElementKey::Node {
        scenario: "other/world".to_owned(),
        local_name: "a20".to_owned(),
    };
    assert_eq!(
        run(&[(9, agency.clone()), (20, foreign.clone())]),
        Err(CityPdError::InvalidIdentity)
    );
    let missing = StableElementKey::Node {
        scenario: "demo/world".to_owned(),
        local_name: "missing".to_owned(),
    };
    assert_eq!(
        run(&[(9, agency.clone()), (20, missing)]),
        Err(CityPdError::InvalidIdentity)
    );
    let valid = [(9, agency), (20, target)];
    let expected = run(&valid).expect("valid identity test fixture");
    let mut with_hidden = valid.to_vec();
    with_hidden.push((999, foreign));
    assert_eq!(
        run(&with_hidden).expect("valid identity test fixture"),
        expected
    );
}
