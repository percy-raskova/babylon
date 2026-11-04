//! Real host controls for budget, household time and venue disclosure.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::NodeId;
use babylon_kernel::content_digest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::{AgencyAttendanceOutcome, MaterialCatalog, MaterialCircuitState};
use babylon_practice_contract::{
    CityPdOutcome, OrderedPracticeActionBatch, OrganizerChoice, OrganizerCommand,
    OrganizerCommitment, PublicVenueHistory, PublicVenuePolicy, PublicVenueRecordKind,
};
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::material_world::CityPdAttempt;
use babylon_tick::material_world::{CityPdRegister, MaterialWorldRegister};
use babylon_tick::replay_session::ReplayCommitDisposition;
use uuid::Uuid;

use super::MaterialRuntimeFoundation;
use crate::economic_catalog::{self, CapturedEconomicCatalog};
use crate::identity::CampaignId;

type Session = MaterialReplaySession<HypergraphStore>;

fn national_foundation(name: &str) -> MaterialRuntimeFoundation {
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7031));
    CapturedEconomicCatalog::capture_national_campaign(
        economic_catalog::national_catalog_input(),
        campaign,
    )
    .expect("captured material")
    .create_foundation(
        ReplaySessionId::try_from(name).expect("session"),
        ReplaySeed::new(319),
    )
    .expect("foundation")
}

fn controlled_register(
    foundation: &MaterialRuntimeFoundation,
    catalog: &MaterialCatalog,
    state: MaterialCircuitState,
    venue: PublicVenueHistory,
) -> MaterialWorldRegister {
    MaterialWorldRegister::try_new(catalog, 0, state)
        .expect("controlled material opening")
        .with_organizer(
            catalog,
            foundation
                .register
                .organizer_config()
                .expect("config")
                .clone(),
            foundation
                .register
                .organizer_state()
                .expect("state")
                .clone(),
            foundation
                .register
                .organizer_journal()
                .expect("journal")
                .clone(),
        )
        .expect("organizer opening")
        .with_public_venue(catalog, venue, None)
        .expect("public venue opening")
}

fn controlled_session(
    foundation: MaterialRuntimeFoundation,
    register: MaterialWorldRegister,
    catalog_override: Option<MaterialCatalog>,
) -> Session {
    let fixture_digest = content_digest::sha256_of(register.canonical_bytes());
    let catalog = catalog_override.unwrap_or(foundation.catalog);
    MaterialReplaySession::new(
        foundation.graph,
        register,
        catalog,
        fixture_digest,
        foundation.spec.duration,
        foundation.labor,
    )
    .expect("controlled material host")
}

fn actions(
    session: &Session,
    commitment: Option<&OrganizerCommitment>,
) -> OrderedPracticeActionBatch {
    babylon_practice_contract::organizer_action_batch(
        session.material().organizer_config().expect("organizer"),
        session.material().organizer_state().expect("state"),
        commitment,
        session.graph_session().session_identity().clone(),
    )
    .expect("organizer actions")
}

fn alternate_reader_register(foundation: &MaterialRuntimeFoundation) -> MaterialWorldRegister {
    let organizer = foundation.register.organizer_config().expect("organizer");
    let old_venue = foundation.register.public_venue().expect("venue");
    let old_pd = foundation.register.city_pd().expect("PD");
    assert_ne!(
        organizer.controlled_actor_id,
        organizer.workplace_partner.actor_id
    );
    let terms = &old_venue.policy;
    let policy = PublicVenuePolicy::new(
        terms.campaign_id,
        terms.workplace_id,
        terms.controlled_actor_id,
        terms.committee_actor_id,
        terms.committee_authority_id,
        terms.agency_reader_actor_id,
        organizer.workplace_partner.actor_id,
        terms.organizer_content_digest,
        terms.source_terms_digest,
    )
    .expect("separate actual captured reader");
    let notice = babylon_practice_contract::initial_public_venue_notice(&policy).expect("notice");
    let mut case = old_pd.state.cases[0].clone();
    case.public_venue_id = notice.venue_id;
    case.source_id = notice.source_id;
    case.case_id = babylon_practice_contract::city_pd_case_id(&case).expect("case");
    let register = controlled_register(
        foundation,
        &foundation.catalog,
        foundation.register.state().clone(),
        PublicVenueHistory {
            policy,
            records: vec![notice],
        },
    );
    let pd = CityPdRegister::try_initial(
        old_pd.config.clone(),
        case,
        old_pd.bindings.clone(),
        &foundation.catalog,
        register.state(),
        foundation.graph.stable_resolver(),
    )
    .expect("real zero-cash opening decision");
    register
        .with_city_pd(&foundation.catalog, pd, foundation.graph.stable_resolver())
        .expect("bound PD")
}

#[test]
fn paid_visit_with_no_authorized_player_witness_still_completes() {
    let foundation = national_foundation("national-city-pd-no-witness");
    let register = alternate_reader_register(&foundation);
    let mut session = controlled_session(foundation, register, None);
    let config = session.material().organizer_config().expect("organizer");
    let state = session.material().organizer_state().expect("state");
    let command = OrganizerCommand {
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: 0,
        content_digest: config.content_digest,
        resource_digest: babylon_practice_contract::organizer_resource_digest().expect("resources"),
        nonce: [1; 16],
        choice: OrganizerChoice::Hold,
    };
    let commitment =
        babylon_practice_contract::admit_organizer(config, state, &command).expect("hold");
    let first = session
        .prepare_advance_with_organizer(&actions(&session, Some(&commitment)), Some(&commitment))
        .expect("P1");
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), first, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("commit P1");
    let second = session
        .prepare_advance(&actions(&session, None))
        .expect("P2");
    let [attempt] = second
        .material()
        .register()
        .city_pd()
        .expect("PD")
        .attempts
        .as_slice()
    else {
        panic!("one attempt")
    };
    assert_eq!(attempt.funding.outcome, AgencyAttendanceOutcome::Paid);
    assert_eq!(attempt.receipt.outcome, CityPdOutcome::Completed);
    assert_eq!(
        attempt.receipt.acquired_public_fact_ids,
        [] as [[u8; 32]; 0]
    );
    assert!(attempt.receipt.player_witness_evidence_id.is_none());
    assert_eq!(
        crate::organizer_runtime::encounter::projections(second.material().register())
            .expect("authenticated no-witness projection")
            .len(),
        0
    );
}

fn shortage_opening(foundation: &MaterialRuntimeFoundation) -> MaterialCircuitState {
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, CircuitAccounting, FinalDemandPrincipalId, PublicAccountId,
    };
    let old_pd = foundation.register.city_pd().expect("PD");
    let mut state = foundation.register.state().clone();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("monetary material")
    };
    let public = AccountId::Public(PublicAccountId::from_bytes(old_pd.config.public_account_id));
    let recipient = AccountId::Household(FinalDemandPrincipalId::from_bytes(
        old_pd.config.investigator_household_account_id,
    ));
    let cash = economy.book.cash(public).expect("Wayne public account");
    assert!(cash.micro_units() > 0);
    let before = economy.book.total_cash_and_reserves().expect("total cash");
    economy
        .book
        .transfer_cash(public, recipient, cash, CashTransferPurpose::PublicTransfer)
        .expect("explicit opening control redistributes existing cash");
    assert_eq!(
        economy.book.total_cash_and_reserves().expect("total cash"),
        before
    );
    // This is a distinct captured opening, retaining all physical carrying amounts.
    let carrying = economy.costs.snapshot();
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        carrying.stocks,
        carrying.freight,
        carrying.equity,
        carrying.equipment,
    )
    .expect("capture the control's actual opening capital");
    state
}

#[test]
fn public_budget_shortage_leaves_no_pending_visit() {
    use babylon_material_circuit::PublicTransferTreatment;
    use babylon_practice_contract::CityPdDecision;
    let foundation = national_foundation("national-city-pd-budget-control");
    let old_pd = foundation.register.city_pd().expect("PD").clone();
    let register = controlled_register(
        &foundation,
        &foundation.catalog,
        shortage_opening(&foundation),
        foundation.register.public_venue().expect("venue").clone(),
    )
    .with_city_pd(
        &foundation.catalog,
        old_pd.clone(),
        foundation.graph.stable_resolver(),
    )
    .expect("bound zero-cash PD");
    let session = controlled_session(foundation, register, None);
    let first = session
        .prepare_advance(&actions(&session, None))
        .expect("P1");
    let pd = first.material().register().city_pd().expect("PD");
    assert_eq!(pd.attempts, [] as [CityPdAttempt; 0]);
    assert!(matches!(
        pd.state
            .last_decision
            .as_ref()
            .expect("P1 decision")
            .decision,
        CityPdDecision::NoFunds {
            available_micros: 0,
            ..
        }
    ));
    let receipts =
        babylon_tick::material_world::decode_material_receipts(first.material().receipt_bytes())
            .expect("material receipts");
    let appropriation = receipts
        .public_budgets
        .iter()
        .find(|row| {
            row.treatment == PublicTransferTreatment::AgencyAppropriation
                && row.public_account.as_bytes() == old_pd.config.public_account_id
        })
        .expect("agency appropriation");
    assert_eq!(appropriation.requested.micro_units(), 24_000_000);
    assert_eq!(appropriation.paid.micro_units(), 0);
    assert_eq!(appropriation.unfunded.micro_units(), 24_000_000);
}

fn scarce_time_catalog(foundation: &MaterialRuntimeFoundation) -> MaterialCatalog {
    use babylon_material_circuit::FinalDemandPrincipalId;
    let pd = foundation.register.city_pd().expect("PD");
    let principal = FinalDemandPrincipalId::from_bytes(pd.config.investigator_household_account_id);
    let mut definitions = foundation.catalog.clone().into_definition();
    definitions
        .household_time_policy
        .iter_mut()
        .find(|policy| policy.principal_id == principal)
        .expect("investigator household policy")
        .hours_per_eligible_person = 1;
    MaterialCatalog::try_new(definitions).expect("captured scarce time policy")
}

#[test]
fn genuine_household_time_shortfall_does_not_complete_the_visit() {
    use babylon_practice_contract::{CityPdCaseStatus, PublicVenueRecordKind};
    let foundation = national_foundation("national-city-pd-time-control");
    let catalog = scarce_time_catalog(&foundation);
    let register = controlled_register(
        &foundation,
        &catalog,
        foundation.register.state().clone(),
        foundation.register.public_venue().expect("venue").clone(),
    )
    .with_city_pd(
        &catalog,
        foundation.register.city_pd().expect("PD").clone(),
        foundation.graph.stable_resolver(),
    )
    .expect("bound PD");
    let mut session = controlled_session(foundation, register, Some(catalog));
    for period in 1..=2 {
        let candidate = session
            .prepare_advance(&actions(&session, None))
            .expect("material period");
        if period == 1 {
            session
                .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
                    Ok::<_, ()>(ReplayCommitDisposition::Committed)
                })
                .expect("commit P1");
            continue;
        }
        let register = candidate.material().register();
        let pd = register.city_pd().expect("PD");
        let [attempt] = pd.attempts.as_slice() else {
            panic!("one selected attempt")
        };
        assert_eq!(
            attempt.funding.outcome,
            AgencyAttendanceOutcome::InsufficientTime
        );
        assert_eq!(attempt.receipt.outcome, CityPdOutcome::InsufficientTime);
        assert_eq!(attempt.funding.paid.micro_units(), 0);
        assert_eq!(attempt.funding.attended_hours, 0);
        assert!(attempt.receipt.player_witness_evidence_id.is_none());
        assert_eq!(
            attempt.receipt.acquired_public_fact_ids,
            [] as [[u8; 32]; 0]
        );
        assert!(pd
            .state
            .cases
            .iter()
            .any(|case| case.case_id == attempt.receipt.case_id
                && case.status == CityPdCaseStatus::Open));
        assert!(!register
            .public_venue()
            .expect("venue")
            .records
            .iter()
            .any(|record| matches!(record.kind, PublicVenueRecordKind::PaidVisit { .. })));
    }
}

fn commit_reinforce_first_period(session: &mut Session) {
    let config = session.material().organizer_config().expect("organizer");
    let state = session.material().organizer_state().expect("state");
    let command = OrganizerCommand {
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: 0,
        content_digest: config.content_digest,
        resource_digest: babylon_practice_contract::organizer_resource_digest().expect("resources"),
        nonce: [1; 16],
        choice: OrganizerChoice::Reinforce,
    };
    let commitment =
        babylon_practice_contract::admit_organizer(config, state, &command).expect("reinforce");
    let first = session
        .prepare_advance_with_organizer(&actions(session, Some(&commitment)), Some(&commitment))
        .expect("P1");
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), first, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("commit P1");
}

fn assert_hidden_restore(
    session: &Session,
    p1_register: &MaterialWorldRegister,
    manifest: &[u8],
    before_world: [u8; 32],
    from: NodeId,
    to: NodeId,
    changed_strength: f64,
) {
    use babylon_graph::substrate::GraphSubstrate;
    assert_eq!(
        session
            .graph_session()
            .stable_resolver()
            .manifest()
            .canonical_bytes(),
        manifest
    );
    assert_eq!(session.material().city_pd(), p1_register.city_pd());
    assert_eq!(
        session.material().public_venue(),
        p1_register.public_venue()
    );
    assert_ne!(
        session.current_world_hash().expect("changed P1 world"),
        before_world
    );
    assert_eq!(
        session
            .graph_session()
            .graph()
            .edge_attribute("CONTACT", from, to, "contact/strength")
            .expect("restored contact"),
        changed_strength
    );
}

fn p1_contact_source(register: &MaterialWorldRegister) -> [u8; 32] {
    register
        .public_venue()
        .expect("public venue")
        .records
        .iter()
        .find(|record| {
            record.period == 1
                && matches!(record.kind, PublicVenueRecordKind::ContactCompleted { .. })
        })
        .expect("actual P1 organizer contact")
        .source_id
}

fn assert_next_contact_decision(pd: &CityPdRegister, contact: [u8; 32]) {
    use babylon_practice_contract::{CityPdCaseSource, CityPdCaseStatus, CityPdDecision};

    let [attempt] = pd.attempts.as_slice() else {
        panic!("one actual P2 visit")
    };
    assert_eq!(attempt.funding.outcome, AgencyAttendanceOutcome::Paid);
    assert_eq!(attempt.receipt.outcome, CityPdOutcome::Completed);
    assert_eq!(attempt.receipt.acquired_public_fact_ids, [contact]);
    let case = pd
        .state
        .cases
        .iter()
        .find(|case| {
            case.source_id == contact
                && case.source_kind == CityPdCaseSource::ObservedOrganizerReceipt
                && case.status == CityPdCaseStatus::Open
                && case.observed_period == 1
                && case.acquired_period == 2
                && case.case_source_witness_id.is_some()
        })
        .expect("the acquired public contact is an open evidenced case");
    let CityPdDecision::Selected(intent) = &pd
        .state
        .last_decision
        .as_ref()
        .expect("P2 next decision")
        .decision
    else {
        panic!("the acquired public contact must select a P3 visit")
    };
    assert_eq!(intent.case_id, case.case_id);
    assert_eq!(intent.resolve_period, 3);
}

#[test]
fn unknown_contact_strength_does_not_change_paid_visit_or_disclosure() {
    use babylon_graph::stable_state;
    use babylon_graph::substrate::GraphSubstrate;
    use babylon_practice_contract::CityPdDecision;

    let foundation = national_foundation("national-city-pd-hidden-contact");
    let mut session = foundation.into_session().expect("national host");
    commit_reinforce_first_period(&mut session);

    let p1_register = session.material().clone();
    let contact = p1_contact_source(&p1_register);
    let pd = p1_register.city_pd().expect("PD");
    let decision = &pd
        .state
        .last_decision
        .as_ref()
        .expect("P1 decision")
        .decision;
    assert!(matches!(decision, CityPdDecision::Selected(_)));
    let resolver = session.graph_session().stable_resolver().clone();
    let from = resolver
        .node_handle_by_local_name("wayne-organizing-collective")
        .expect("organizer node");
    let to = resolver
        .node_handle_by_local_name("wayne-neighborhood-contact-group")
        .expect("contact node");
    assert!(!pd.state.dossier.knows_edge("CONTACT", from, to));
    let manifest = resolver.manifest().canonical_bytes().to_vec();
    let rows = session
        .graph_session()
        .current_material_state_rows()
        .expect("P1 material rows");
    let registers = session
        .graph_session()
        .world_registers()
        .expect("P1 registers")
        .canonical_bytes()
        .to_vec();
    let before_world = session.current_world_hash().expect("P1 world");
    let baseline = session
        .prepare_advance(&actions(&session, None))
        .expect("baseline P2");
    let baseline_register = baseline.material().register();
    let baseline_pd = baseline_register.city_pd().expect("baseline PD").clone();
    assert_next_contact_decision(&baseline_pd, contact);
    let baseline_projection = crate::organizer_runtime::encounter::projections(baseline_register)
        .expect("baseline disclosure");
    assert_eq!(baseline_projection.len(), 1);
    let baseline_receipts = content_digest::sha256_of(baseline.material().receipt_bytes());
    let baseline_world = baseline.identity().result_world_hash();
    drop(baseline);

    let mut altered_graph = session.graph_session().graph().clone();
    let original_strength = altered_graph
        .edge_attribute("CONTACT", from, to, "contact/strength")
        .expect("seeded contact");
    let changed_strength = if original_strength.to_bits() == 0.5_f64.to_bits() {
        0.75
    } else {
        0.5
    };
    altered_graph
        .update_edge("CONTACT", from, to, "contact/strength", changed_strength)
        .expect("change hidden contact");
    assert_ne!(
        altered_graph
            .edge_attribute("CONTACT", from, to, "contact/strength")
            .expect("changed contact"),
        original_strength
    );
    let altered =
        stable_state::encode_stable_graph_state(&altered_graph, &resolver).expect("altered graph");
    drop(altered_graph);
    session
        .restore_full_checkpoint(&altered, &rows, &registers, p1_register.clone())
        .expect("restore same topology");
    assert_hidden_restore(
        &session,
        &p1_register,
        &manifest,
        before_world,
        from,
        to,
        changed_strength,
    );
    let changed = session
        .prepare_advance(&actions(&session, None))
        .expect("changed P2");
    let changed_pd = changed.material().register().city_pd().expect("changed PD");
    assert_next_contact_decision(changed_pd, contact);
    assert_eq!(changed_pd, &baseline_pd);
    assert_eq!(
        content_digest::sha256_of(changed.material().receipt_bytes()),
        baseline_receipts
    );
    assert_eq!(
        crate::organizer_runtime::encounter::projections(changed.material().register())
            .expect("changed disclosure"),
        baseline_projection
    );
    assert_ne!(changed.identity().result_world_hash(), baseline_world);
}

#[test]
fn national_input_order_preserves_paid_visit_and_world_identity() {
    use crate::economic_catalog::{EconomicCatalogInput, NationalOpponent};
    use crate::organizer_runtime::encounter::CityPdEncounter;
    use babylon_practice_contract::{CityPdDecision, CityPdDecisionReceipt};

    #[derive(Debug, PartialEq, Eq)]
    struct Output {
        catalog: [u8; 32],
        p1_world: [u8; 32],
        p1_receipts: [u8; 32],
        decision: CityPdDecisionReceipt,
        p2_world: [u8; 32],
        p2_receipts: [u8; 32],
        pd: CityPdRegister,
        encounters: Vec<CityPdEncounter>,
    }
    fn run(input: EconomicCatalogInput) -> Output {
        let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7031));
        let catalog = CapturedEconomicCatalog::capture_national_campaign_with_opponent(
            input,
            campaign,
            NationalOpponent::CityPd,
        )
        .expect("capture");
        let digest = catalog.digest();
        let foundation = catalog
            .create_foundation(
                ReplaySessionId::try_from("national-city-pd-input-order").expect("session"),
                ReplaySeed::new(319),
            )
            .expect("foundation");
        let mut session = foundation.into_session().expect("host");
        let config = session.material().organizer_config().expect("organizer");
        let state = session.material().organizer_state().expect("state");
        let command = OrganizerCommand {
            campaign_id: config.campaign_id,
            actor_id: config.controlled_actor_id,
            authority_id: config.input_authority_id,
            expected_period: 0,
            content_digest: config.content_digest,
            resource_digest: babylon_practice_contract::organizer_resource_digest()
                .expect("resources"),
            nonce: [1; 16],
            choice: OrganizerChoice::Hold,
        };
        let commitment =
            babylon_practice_contract::admit_organizer(config, state, &command).expect("hold");
        let first = session
            .prepare_advance_with_organizer(
                &actions(&session, Some(&commitment)),
                Some(&commitment),
            )
            .expect("P1");
        let p1_world = first.identity().result_world_hash();
        let p1_receipts = content_digest::sha256_of(first.material().receipt_bytes());
        let decision = first
            .material()
            .register()
            .city_pd()
            .expect("PD")
            .state
            .last_decision
            .clone()
            .expect("P1 decision");
        assert!(matches!(decision.decision, CityPdDecision::Selected(_)));
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), first, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("commit P1");
        let second = session
            .prepare_advance(&actions(&session, None))
            .expect("P2");
        let pd = second.material().register().city_pd().expect("PD").clone();
        assert_eq!(pd.attempts.len(), 1);
        assert_eq!(
            pd.attempts[0].funding.outcome,
            AgencyAttendanceOutcome::Paid
        );
        let encounters =
            crate::organizer_runtime::encounter::projections(second.material().register())
                .expect("disclosure");
        assert_eq!(encounters.len(), 1);
        Output {
            catalog: digest,
            p1_world,
            p1_receipts,
            decision,
            p2_world: second.identity().result_world_hash(),
            p2_receipts: content_digest::sha256_of(second.material().receipt_bytes()),
            pd,
            encounters,
        }
    }

    let input = economic_catalog::national_catalog_input();
    let mut permuted = input.clone();
    permuted.sources.reverse();
    assert_ne!(
        input.sources.first().expect("first").kind(),
        permuted.sources.first().expect("reordered first").kind()
    );
    assert_eq!(run(input), run(permuted));
}
