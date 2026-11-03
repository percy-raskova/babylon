//! Real host controls for budget, household time and venue disclosure.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::{AgencyAttendanceOutcome, MaterialCatalog, MaterialCircuitState};
use babylon_practice_contract::{
    CityPdOutcome, OrderedPracticeActionBatch, OrganizerChoice, OrganizerCommand,
    OrganizerCommitment, PublicVenueHistory, PublicVenuePolicy,
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
