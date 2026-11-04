//! Actual national capture through detached material and opponent execution.

use babylon_bsl::evaluator::Value;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::currency::Currency;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{
    AccountId, AgencyAttendanceOutcome, CircuitAccounting, OrganizationAccountId, PublicAccountId,
};
use babylon_persistence::economic_catalog::{
    CapturedEconomicCatalog, EconomicCatalogInput, NationalOpponent,
};
use babylon_persistence::identity::CampaignId;
use babylon_practice_contract::{
    CityPdCaseSource, CityPdConfig, CityPdDecision, CityPdOutcome, OrganizerChoice,
    OrganizerCommand, PublicVenueRecordKind,
};
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::material_world::CityPdAttempt;
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;
use uuid::Uuid;

#[path = "fixtures/national_capture.rs"]
mod national_capture;

#[path = "fixtures/city_pd_acceptance.rs"]
mod city_pd_acceptance;

#[test]
fn actual_national_opening_and_two_periods_use_committed_pd_cash() {
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7031));
    let input = national_capture::input();
    let foundation = CapturedEconomicCatalog::capture_national_campaign_with_opponent(
        input.clone(),
        campaign,
        NationalOpponent::CityPd,
    )
    .expect("national capture")
    .create_foundation(
        ReplaySessionId::try_from("national-city-pd-live").expect("session"),
        ReplaySeed::new(319),
    )
    .expect("national foundation");
    let mut session = foundation.into_session().expect("scheduled native host");
    let (public, public_opening) = assert_opening(&session);
    let config = session
        .material()
        .organizer_config()
        .expect("organizer")
        .clone();
    let state = session
        .material()
        .organizer_state()
        .expect("organizer state")
        .clone();
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
    let commitment = babylon_practice_contract::admit_organizer(&config, &state, &command)
        .expect("admitted ruling");
    let actions = babylon_practice_contract::organizer_action_batch(
        &config,
        &state,
        Some(&commitment),
        session.graph_session().session_identity().clone(),
    )
    .expect("action batch");
    let candidate = session
        .prepare_advance_with_organizer(&actions, Some(&commitment))
        .expect("detached P1");
    let contact_source = assert_first_period(candidate.material().register());
    let pd_config = candidate
        .material()
        .register()
        .city_pd()
        .expect("PD")
        .config
        .clone();
    let receipts = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .expect("P1 receipts");
    city_pd_acceptance::assert_receipts(&pd_config, &receipts, true);
    let before = session.material().digest();
    let world = session.current_world_hash().expect("opening hash");
    let mut sink = CollectingSink::default();
    assert!(session
        .commit_prepared_and_publish(
            &mut sink,
            candidate,
            |_, _| Err::<ReplayCommitDisposition, _>("injected failure")
        )
        .is_err());
    assert_eq!(session.material().digest(), before);
    assert_eq!(session.current_world_hash().expect("unchanged hash"), world);
    assert_eq!(sink.events, [] as [(String, Vec<(String, Value)>); 0]);
    let retry = session
        .prepare_advance_with_organizer(&actions, Some(&commitment))
        .expect("retry P1");
    session
        .commit_prepared_and_publish(&mut sink, retry, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("commit P1");
    let config = session.material().organizer_config().expect("organizer");
    let state = session.material().organizer_state().expect("state");
    let actions = babylon_practice_contract::organizer_action_batch(
        config,
        state,
        None,
        session.graph_session().session_identity().clone(),
    )
    .expect("P2 actions");
    let second = session.prepare_advance(&actions).expect("detached P2");
    assert_paid_source(second.material().register(), contact_source);
    let receipts =
        babylon_tick::material_world::decode_material_receipts(second.material().receipt_bytes())
            .expect("P2 receipts");
    city_pd_acceptance::assert_receipts(&pd_config, &receipts, true);
    drop(receipts);
    drop(second);
    drop(session);

    assert_no_pd_control(input, campaign, &pd_config, public, public_opening);
}

fn assert_opening(session: &MaterialReplaySession<HypergraphStore>) -> (AccountId, Currency) {
    let opening = session.material().city_pd().expect("captured PD");
    assert!(matches!(
        opening
            .state
            .last_decision
            .as_ref()
            .expect("period-zero decision")
            .decision,
        CityPdDecision::NoFunds {
            available_micros: 0,
            ..
        }
    ));
    let opening_config = &opening.config;
    let CircuitAccounting::Monetary(opening_money) = &session.material().state().accounting else {
        panic!("monetary opening")
    };
    let public = AccountId::Public(PublicAccountId::from_bytes(
        opening_config.public_account_id,
    ));
    let public_opening = opening_money.book.cash(public).expect("public opening");
    let agency = AccountId::Organization(OrganizationAccountId::from_bytes(
        opening_config.agency_account_id,
    ));
    assert_eq!(
        opening_money
            .book
            .cash(agency)
            .expect("agency opening")
            .micro_units(),
        0
    );
    (public, public_opening)
}

fn assert_no_pd_control(
    input: EconomicCatalogInput,
    campaign: CampaignId,
    pd_config: &CityPdConfig,
    public: AccountId,
    public_opening: Currency,
) {
    let foundation = CapturedEconomicCatalog::capture_national_campaign_with_opponent(
        input,
        campaign,
        NationalOpponent::None,
    )
    .expect("matched no-opponent capture")
    .create_foundation(
        ReplaySessionId::try_from("national-city-pd-live").expect("session"),
        ReplaySeed::new(319),
    )
    .expect("matched foundation");
    let mut control = foundation.into_session().expect("no-opponent host");
    assert!(control.material().city_pd().is_none());
    let CircuitAccounting::Monetary(money) = &control.material().state().accounting else {
        panic!("monetary control")
    };
    assert_eq!(
        money.book.cash(public).expect("control public opening"),
        public_opening
    );
    let config = control.material().organizer_config().expect("organizer");
    let state = control
        .material()
        .organizer_state()
        .expect("organizer state");
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
    let commitment = babylon_practice_contract::admit_organizer(config, state, &command)
        .expect("control command");
    let actions = babylon_practice_contract::organizer_action_batch(
        config,
        state,
        Some(&commitment),
        control.graph_session().session_identity().clone(),
    )
    .expect("control actions");
    let first = control
        .prepare_advance_with_organizer(&actions, Some(&commitment))
        .expect("control P1");
    let receipts =
        babylon_tick::material_world::decode_material_receipts(first.material().receipt_bytes())
            .expect("control P1 receipts");
    city_pd_acceptance::assert_receipts(pd_config, &receipts, false);
    assert!(
        first
            .material()
            .register()
            .public_venue()
            .expect("venue")
            .records
            .iter()
            .any(|r| r.period == 1
                && matches!(r.kind, PublicVenueRecordKind::ContactCompleted { .. }))
    );
    control
        .commit_prepared_and_publish(&mut CollectingSink::default(), first, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("commit control P1");
    let actions = babylon_practice_contract::organizer_action_batch(
        control.material().organizer_config().expect("config"),
        control.material().organizer_state().expect("state"),
        None,
        control.graph_session().session_identity().clone(),
    )
    .expect("control P2 actions");
    let second = control.prepare_advance(&actions).expect("control P2");
    let receipts =
        babylon_tick::material_world::decode_material_receipts(second.material().receipt_bytes())
            .expect("control P2 receipts");
    city_pd_acceptance::assert_receipts(pd_config, &receipts, false);
}

fn assert_first_period(after: &MaterialWorldRegister) -> [u8; 32] {
    let pd = after.city_pd().expect("PD retained");
    assert_eq!(
        pd.attempts,
        [] as [CityPdAttempt; 0],
        "no P0 funds means no P1 visit"
    );
    let CircuitAccounting::Monetary(money) = &after.state().accounting else {
        panic!("monetary opening")
    };
    let cash = money
        .book
        .cash(AccountId::Organization(OrganizationAccountId::from_bytes(
            pd.config.agency_account_id,
        )))
        .expect("agency account")
        .micro_units();
    eprintln!(
        "national P1: agency_cash_micros={cash}, venue_records={}",
        after.public_venue().expect("public venue").records.len()
    );
    assert_eq!(cash, 24_000_000);
    let CityPdDecision::Selected(intent) = &pd
        .state
        .last_decision
        .as_ref()
        .expect("P1 decision")
        .decision
    else {
        panic!("the funded initial notice must select a P2 visit")
    };
    assert_eq!(intent.resolve_period, 2);
    after
        .public_venue()
        .expect("venue")
        .records
        .iter()
        .find(|record| {
            record.period == 1
                && matches!(record.kind, PublicVenueRecordKind::ContactCompleted { .. })
        })
        .expect("performed P1 contact publication")
        .source_id
}

fn assert_paid_source(register: &MaterialWorldRegister, contact_source: [u8; 32]) {
    let pd = register.city_pd().expect("PD retained");
    let [attempt] = pd.attempts.as_slice() else {
        panic!("the selected P2 visit must resolve exactly once")
    };
    assert_eq!(attempt.funding.outcome, AgencyAttendanceOutcome::Paid);
    assert_eq!(attempt.funding.paid.micro_units(), 24_000_000);
    assert_eq!(attempt.funding.attended_hours, 1);
    assert_eq!(attempt.receipt.outcome, CityPdOutcome::Completed);
    assert_eq!(attempt.receipt.resolve_period, 2);
    assert_eq!(attempt.funding.input.intent_id, attempt.receipt.intent_id);
    assert!(attempt.receipt.shift_receipt_id.is_some());
    assert!(attempt.receipt.payment_receipt_id.is_some());
    assert!(attempt.receipt.player_witness_evidence_id.is_some());
    assert!(attempt.receipt.case_source_evidence_id.is_some());
    let [source_id] = attempt.receipt.acquired_public_fact_ids.as_slice() else {
        panic!("the P1 contact must be acquired during the paid visit")
    };
    assert_eq!(*source_id, contact_source);
    let source_case = pd
        .state
        .cases
        .iter()
        .find(|case| {
            case.source_id == *source_id
                && case.source_kind == CityPdCaseSource::ObservedOrganizerReceipt
                && case.observed_period == 1
                && case.acquired_period == 2
                && case.case_source_witness_id.is_some()
        })
        .expect("the acquired P1 contact creates an evidenced case");
    let CityPdDecision::Selected(next) = &pd
        .state
        .last_decision
        .as_ref()
        .expect("P3 decision")
        .decision
    else {
        panic!("the funded P1-contact case must select a P3 visit")
    };
    assert_eq!(next.case_id, source_case.case_id);
    assert_eq!(next.resolve_period, 3);
    assert!(register
        .public_venue()
        .expect("venue")
        .records
        .iter()
        .any(|record| record.period == 2
            && matches!(record.kind, PublicVenueRecordKind::PaidVisit { .. })));
}

#[test]
fn withheld_contact_completes_paid_visit_without_a_new_case() {
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7031));
    let foundation =
        CapturedEconomicCatalog::capture_national_campaign(national_capture::input(), campaign)
            .expect("national capture")
            .create_foundation(
                ReplaySessionId::try_from("national-city-pd-live").expect("session"),
                ReplaySeed::new(319),
            )
            .expect("national foundation");
    let mut session = foundation.into_session().expect("scheduled native host");
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
        babylon_practice_contract::admit_organizer(config, state, &command).expect("admit hold");
    let actions = babylon_practice_contract::organizer_action_batch(
        config,
        state,
        Some(&commitment),
        session.graph_session().session_identity().clone(),
    )
    .expect("actions");
    let first = session
        .prepare_advance_with_organizer(&actions, Some(&commitment))
        .expect("P1");
    assert!(!first
        .material()
        .register()
        .public_venue()
        .expect("venue")
        .records
        .iter()
        .any(|record| matches!(record.kind, PublicVenueRecordKind::ContactCompleted { .. })));
    let mut sink = CollectingSink::default();
    session
        .commit_prepared_and_publish(&mut sink, first, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("commit P1");
    let config = session.material().organizer_config().expect("organizer");
    let state = session.material().organizer_state().expect("state");
    let actions = babylon_practice_contract::organizer_action_batch(
        config,
        state,
        None,
        session.graph_session().session_identity().clone(),
    )
    .expect("P2 actions");
    let second = session.prepare_advance(&actions).expect("P2");
    let pd = second.material().register().city_pd().expect("PD");
    let [attempt] = pd.attempts.as_slice() else {
        panic!("one P2 attempt")
    };
    assert_eq!(attempt.funding.outcome, AgencyAttendanceOutcome::Paid);
    assert_eq!(attempt.funding.paid.micro_units(), 24_000_000);
    assert_eq!(attempt.funding.attended_hours, 1);
    assert_eq!(attempt.receipt.outcome, CityPdOutcome::Completed);
    assert_eq!(
        attempt.receipt.acquired_public_fact_ids,
        [] as [[u8; 32]; 0]
    );
    assert!(attempt.receipt.case_source_evidence_id.is_none());
    assert_eq!(
        pd.state.cases.len(),
        1,
        "only the authored opening notice was known"
    );
    assert!(matches!(
        pd.state
            .last_decision
            .as_ref()
            .expect("P3 decision")
            .decision,
        CityPdDecision::NoCases
    ));
}

#[test]
fn national_no_opponent_still_publishes_the_real_contact() {
    use babylon_persistence::economic_catalog::NationalOpponent;

    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7031));
    let foundation = CapturedEconomicCatalog::capture_national_campaign_with_opponent(
        national_capture::input(),
        campaign,
        NationalOpponent::None,
    )
    .expect("national no-opponent capture")
    .create_foundation(
        ReplaySessionId::try_from("national-city-pd-live").expect("session"),
        ReplaySeed::new(319),
    )
    .expect("national no-opponent foundation");
    let session = foundation.into_session().expect("no-opponent host");
    assert!(session.material().city_pd().is_none());
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
        babylon_practice_contract::admit_organizer(config, state, &command).expect("admit contact");
    let actions = babylon_practice_contract::organizer_action_batch(
        config,
        state,
        Some(&commitment),
        session.graph_session().session_identity().clone(),
    )
    .expect("actions");
    let first = session
        .prepare_advance_with_organizer(&actions, Some(&commitment))
        .expect("P1 without a native PD operation");
    assert!(first.material().register().city_pd().is_none());
    assert!(first
        .material()
        .register()
        .public_venue()
        .expect("venue")
        .records
        .iter()
        .any(|record| record.period == 1
            && matches!(record.kind, PublicVenueRecordKind::ContactCompleted { .. })));
}
