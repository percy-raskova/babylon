//! Real organizer output and closed household debits gate public contact.
#[allow(dead_code, reason = "reuse the existing typed material fixture")]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;
#[allow(dead_code, reason = "reuse the existing typed material fixture")]
#[path = "support/organizer_aid_fixture.rs"]
mod organizer_aid_fixture;

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::{
    AccountId, AgencyAttendanceInput, AgencyAttendanceOutcome, AgencyObservationFundingReceipt,
    MaterialCircuitState, OrganizationAccountId,
};
use babylon_practice_contract::{
    CityPdCase, CityPdCaseSource, CityPdCaseStatus, CityPdConfig, CityPdIntent, OrganizerChoice,
    OrganizerCommitment, OrganizerConfig, OrganizerPartnerResponse, OrganizerPeriodJournalEntries,
    OrganizerState, PublicVenueHistory, PublicVenuePolicy, PublicVenueRecord,
};
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::public_venue;
use babylon_tick::public_venue::{PaidVisitPublication, PublicVenueSourceProof};
use organizer_aid_fixture::Session;

#[derive(Clone, Copy)]
struct ContactContext<'a> {
    config: &'a OrganizerConfig,
    policy: &'a PublicVenuePolicy,
    accepted: &'a OrganizerCommitment,
    state: &'a OrganizerState,
    entries: &'a OrganizerPeriodJournalEntries,
    register: &'a MaterialWorldRegister,
    publication: &'a PublicVenueRecord,
}

#[test]
fn contact_requires_actual_completed_receipt_and_closed_debits() {
    let mut config = organizer_aid_fixture::config();
    config.contact_hours = 1;
    config.partner_response_hours = 1;
    let policy = PublicVenuePolicy::new(
        config.campaign_id,
        config.workplace_id,
        config.controlled_actor_id,
        config.workplace_partner.actor_id,
        config.workplace_partner.authority_id,
        900,
        config.controlled_actor_id,
        config.content_digest,
        [9; 32],
    )
    .expect("public venue fixture supplies valid evidence");
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("public venue fixture supplies valid evidence");
    let mut session =
        organizer_aid_fixture::authored_session(foundation, config.clone(), false, false);
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::Reinforce);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut session, &mut sink, candidate);
    let register = session.material();
    let state = register
        .organizer_state()
        .expect("public venue fixture supplies valid evidence");
    let entries = register
        .organizer_journal()
        .expect("public venue fixture supplies valid evidence")
        .latest()
        .expect("public venue fixture supplies valid evidence");
    let publication = public_venue::publish_public_contact(
        &policy,
        &config,
        &accepted,
        state,
        entries,
        register.state(),
    )
    .expect("public venue fixture supplies valid evidence");
    assert_eq!(publication.period, entries.period);
    let committee_reader = PublicVenuePolicy::new(
        config.campaign_id,
        config.workplace_id,
        config.controlled_actor_id,
        config.workplace_partner.actor_id,
        config.workplace_partner.authority_id,
        900,
        config.workplace_partner.actor_id,
        config.content_digest,
        [9; 32],
    )
    .expect("alternate captured log reader");
    let alternate = public_venue::publish_public_contact(
        &committee_reader,
        &config,
        &accepted,
        state,
        entries,
        register.state(),
    )
    .expect("contact publication is independent of who reads the visitor log");
    assert_eq!(alternate.period, publication.period);
    let context = ContactContext {
        config: &config,
        policy: &policy,
        accepted: &accepted,
        state,
        entries,
        register,
        publication: &publication,
    };
    assert_shared_household_debits(context);
    let history = assert_contact_source_admission(context);
    assert_cold_contact_refusals(context, &history);
    assert_live_contact_refusals(context, &history);
    assert_live_scope_and_usage_refusals(context);
    assert_missing_contact_evidence(context, &history);
    assert_no_command_standing_refuses(
        &mut session,
        &mut sink,
        &policy,
        &config,
        &accepted,
        &history,
        &publication,
    );
}

fn assert_shared_household_debits(context: ContactContext<'_>) {
    let ContactContext {
        register, entries, ..
    } = context;
    // Both role-specific actual debits draw on one household principal.
    let babylon_material_circuit::CircuitAccounting::Monetary(economy) =
        &register.state().accounting
    else {
        panic!("monetary accounting required")
    };
    let babylon_material_circuit::HouseholdTimeAccounting::Modeled(book) = &economy.household_time
    else {
        panic!("modeled household time required")
    };
    let receipt = &entries.receipts[0];
    let actual: Vec<_> = receipt
        .time_use
        .iter()
        .map(|usage| {
            let use_id = babylon_practice_contract::household_contribution_use_id(
                &receipt.receipt_id,
                usage.actor_id,
                usage.contributor_id,
            );
            book.contributions
                .iter()
                .find(|row| row.contribution.use_id == use_id)
                .expect("public venue fixture supplies valid evidence")
        })
        .collect();
    assert_eq!(actual.len(), 2);
    assert_ne!(
        actual[0].contribution.actor_id,
        actual[1].contribution.actor_id
    );
    assert_eq!(
        actual[0].contribution.principal_id,
        actual[1].contribution.principal_id
    );
    assert_eq!(
        actual[0].contribution.principal_id,
        organizer_aid_fixture::household()
    );
}

fn assert_contact_source_admission(context: ContactContext<'_>) -> PublicVenueHistory {
    let ContactContext {
        policy,
        config,
        accepted,
        state,
        entries,
        register,
        publication,
    } = context;
    let notice = babylon_practice_contract::initial_public_venue_notice(policy)
        .expect("public venue fixture supplies valid evidence");
    let mut history = PublicVenueHistory {
        policy: (*policy).clone(),
        records: vec![notice],
    };
    let proof = || PublicVenueSourceProof::Contact {
        config,
        commitment: accepted,
        organizer: state,
        entries,
        closed: register.state(),
    };
    assert_eq!(
        public_venue::admit_public_venue_source(&history, proof())
            .expect_err("the unproven publication must be refused"),
        babylon_tick::public_venue::PublicVenueEvidenceError::InvalidPublicationAccess
    );
    assert!(public_venue::admit_public_venue_source(
        &history,
        PublicVenueSourceProof::CommittedContact {
            config,
            organizer: state,
            entries,
            closed: register.state(),
            record: publication,
        }
    )
    .is_err());
    history.records.push((*publication).clone());
    let source = public_venue::admit_public_venue_source(&history, proof())
        .expect("public venue fixture supplies valid evidence");
    let mut forged_record = (*publication).clone();
    forged_record.source_id = [83; 32];
    assert!(public_venue::admit_public_venue_source(
        &history,
        PublicVenueSourceProof::CommittedContact {
            config,
            organizer: state,
            entries,
            closed: register.state(),
            record: &forged_record,
        }
    )
    .is_err());
    assert_eq!(source.record(), publication);
    let cold = |organizer: &OrganizerState,
                original_entries: &OrganizerPeriodJournalEntries,
                closed: &MaterialCircuitState| {
        public_venue::admit_public_venue_source(
            &history,
            PublicVenueSourceProof::CommittedContact {
                config,
                organizer,
                entries: original_entries,
                closed,
                record: publication,
            },
        )
    };
    assert_eq!(
        cold(state, entries, register.state())
            .expect("public venue fixture supplies valid evidence"),
        source
    );
    history
}

fn assert_cold_contact_refusals(context: ContactContext<'_>, history: &PublicVenueHistory) {
    let ContactContext {
        config,
        state,
        entries,
        register,
        publication,
        ..
    } = context;
    let cold = |organizer: &OrganizerState,
                original_entries: &OrganizerPeriodJournalEntries,
                closed: &MaterialCircuitState| {
        public_venue::admit_public_venue_source(
            history,
            PublicVenueSourceProof::CommittedContact {
                config,
                organizer,
                entries: original_entries,
                closed,
                record: publication,
            },
        )
    };
    let mut no_product = (*state).clone();
    no_product.contact_products.clear();
    assert!(cold(&no_product, entries, register.state()).is_err());
    let mut no_witness = (*state).clone();
    no_witness.last_period_time_witness = None;
    assert!(cold(&no_witness, entries, register.state()).is_err());
    let mut false_standing = (*entries).clone();
    false_standing.receipts[0].standing_work = true;
    assert!(cold(state, &false_standing, register.state()).is_err());
    let mut no_commitment = (*entries).clone();
    no_commitment.receipts[0].commitment_id = None;
    assert!(cold(state, &no_commitment, register.state()).is_err());
    let mut zero_commitment = (*entries).clone();
    zero_commitment.receipts[0].commitment_id = Some([0; 32]);
    assert!(cold(state, &zero_commitment, register.state()).is_err());
    let mut wrong_commitment = (*entries).clone();
    wrong_commitment.receipts[0].commitment_id = Some([77; 32]);
    assert!(cold(state, &wrong_commitment, register.state()).is_err());
    let mut wrong_receipt_actor = (*entries).clone();
    wrong_receipt_actor.receipts[0].actor_id = 999;
    assert!(cold(state, &wrong_receipt_actor, register.state()).is_err());
}

fn assert_live_contact_refusals(context: ContactContext<'_>, history: &PublicVenueHistory) {
    let ContactContext {
        policy,
        config,
        accepted,
        state,
        entries,
        register,
        publication,
    } = context;
    let cold = |organizer: &OrganizerState,
                original_entries: &OrganizerPeriodJournalEntries,
                closed: &MaterialCircuitState| {
        public_venue::admit_public_venue_source(
            history,
            PublicVenueSourceProof::CommittedContact {
                config,
                organizer,
                entries: original_entries,
                closed,
                record: publication,
            },
        )
    };
    let mut no_participation = (*entries).clone();
    no_participation.receipts[0].partner_response = OrganizerPartnerResponse::Refused;
    assert!(public_venue::publish_public_contact(
        policy,
        config,
        accepted,
        state,
        &no_participation,
        register.state()
    )
    .is_err());
    let mut wrong_period = (*entries).clone();
    wrong_period.receipts[0].period += 1;
    assert!(cold(state, &wrong_period, register.state()).is_err());
    assert!(public_venue::publish_public_contact(
        policy,
        config,
        accepted,
        state,
        &wrong_period,
        register.state()
    )
    .is_err());
}

fn assert_live_scope_and_usage_refusals(context: ContactContext<'_>) {
    let ContactContext {
        policy,
        config,
        accepted,
        state,
        entries,
        register,
        ..
    } = context;
    let wrong_scope = PublicVenuePolicy::new(
        config.campaign_id,
        config.workplace_id,
        config.controlled_actor_id,
        999,
        config.workplace_partner.authority_id,
        900,
        config.controlled_actor_id,
        config.content_digest,
        [9; 32],
    )
    .expect("public venue fixture supplies valid evidence");
    assert!(public_venue::publish_public_contact(
        &wrong_scope,
        config,
        accepted,
        state,
        entries,
        register.state()
    )
    .is_err());
    let mut wrong_actor = (*entries).clone();
    wrong_actor.receipts[0].time_use[0].actor_id = 999;
    assert!(public_venue::publish_public_contact(
        policy,
        config,
        accepted,
        state,
        &wrong_actor,
        register.state()
    )
    .is_err());
    let mut wrong_hours = (*entries).clone();
    wrong_hours.receipts[0].time_use[0].hours += 1;
    assert!(public_venue::publish_public_contact(
        policy,
        config,
        accepted,
        state,
        &wrong_hours,
        register.state()
    )
    .is_err());
    let mut wrong_digest = (*accepted).clone();
    wrong_digest.command.content_digest = [88; 32];
    assert!(public_venue::publish_public_contact(
        policy,
        config,
        &wrong_digest,
        state,
        entries,
        register.state()
    )
    .is_err());
}

fn assert_missing_contact_evidence(context: ContactContext<'_>, history: &PublicVenueHistory) {
    let ContactContext {
        policy,
        config,
        accepted,
        state,
        entries,
        register,
        publication,
    } = context;
    let cold = |organizer: &OrganizerState,
                original_entries: &OrganizerPeriodJournalEntries,
                closed: &MaterialCircuitState| {
        public_venue::admit_public_venue_source(
            history,
            PublicVenueSourceProof::CommittedContact {
                config,
                organizer,
                entries: original_entries,
                closed,
                record: publication,
            },
        )
    };
    let mut forged = (*entries).clone();
    forged.receipts.clear();
    assert!(cold(state, &forged, register.state()).is_err());
    assert!(public_venue::publish_public_contact(
        policy,
        config,
        accepted,
        state,
        &forged,
        register.state()
    )
    .is_err());
    let mut no_debits = register.state().clone();
    if let babylon_material_circuit::CircuitAccounting::Monetary(economy) =
        &mut no_debits.accounting
    {
        if let babylon_material_circuit::HouseholdTimeAccounting::Modeled(book) =
            &mut economy.household_time
        {
            book.contributions.clear();
        }
    }
    assert!(public_venue::publish_public_contact(
        policy, config, accepted, state, entries, &no_debits
    )
    .is_err());
    assert!(cold(state, entries, &no_debits).is_err());
}

fn assert_no_command_standing_refuses(
    session: &mut Session,
    sink: &mut CollectingSink,
    policy: &PublicVenuePolicy,
    config: &OrganizerConfig,
    accepted: &OrganizerCommitment,
    history: &PublicVenueHistory,
    publication: &PublicVenueRecord,
) {
    // Perform the next period with no accepted command: the real standing
    // receipt and actual debits cannot renew the old explicit commitment.
    let routine = organizer_aid_fixture::prepare(session, None);
    organizer_aid_fixture::commit(session, sink, routine);
    let routine_register = session.material();
    let routine_state = routine_register
        .organizer_state()
        .expect("public venue fixture supplies valid evidence");
    let routine_entries = routine_register
        .organizer_journal()
        .expect("public venue fixture supplies valid evidence")
        .latest()
        .expect("public venue fixture supplies valid evidence");
    assert_eq!(routine_entries.period, accepted.resolves_period + 1);
    assert!(routine_entries
        .receipts
        .iter()
        .any(|receipt| receipt.standing_work && receipt.commitment_id.is_none()));
    assert!(public_venue::admit_public_venue_source(
        history,
        PublicVenueSourceProof::CommittedContact {
            config,
            organizer: routine_state,
            entries: routine_entries,
            closed: routine_register.state(),
            record: publication,
        }
    )
    .is_err());
    assert!(public_venue::publish_public_contact(
        policy,
        config,
        accepted,
        routine_state,
        routine_entries,
        routine_register.state()
    )
    .is_err());
}

#[allow(dead_code, reason = "reuse real material agency attendance fixture")]
#[path = "../../babylon-material-circuit/tests/support/organizer_funding_control.rs"]
mod funding_control;

struct PaidFixture {
    config: CityPdConfig,
    policy: PublicVenuePolicy,
    notice: PublicVenueRecord,
    case: CityPdCase,
    intent: CityPdIntent,
    funding: AgencyObservationFundingReceipt,
    bytes: Vec<u8>,
    result: PaidVisitPublication,
}

fn agency_account() -> OrganizationAccountId {
    match funding_control::organization() {
        AccountId::Organization(id) => id,
        _ => unreachable!(),
    }
}

fn paid_terms() -> (CityPdConfig, PublicVenuePolicy) {
    let agency = agency_account();
    let principal = funding_control::recipient();
    let config = CityPdConfig {
        schema_version: 1,
        campaign_id: [1; 16],
        actor_id: 900,
        authority_id: [2; 16],
        county: *b"26163",
        public_account_id: [3; 32],
        agency_account_id: agency.as_bytes(),
        investigator_household_account_id: principal.as_bytes(),
        investigator_entitlement_id: [6; 32],
        labor_unit_id: funding_control::unit(90).as_bytes(),
        visit_hours: 1,
        hourly_wage_micros: 100_000,
        visit_cost_micros: 100_000,
        appropriation_micros: 200_000,
        appropriation_priority: 0,
        content_digest: [8; 32],
        policy_source_digest: [9; 32],
    };
    let policy = PublicVenuePolicy::new(
        config.campaign_id,
        104,
        101,
        102,
        [3; 16],
        config.actor_id,
        101,
        [5; 32],
        config.policy_source_digest,
    )
    .expect("public venue fixture supplies valid evidence");
    (config, policy)
}

fn authored_case_and_intent(
    config: &CityPdConfig,
    policy: &PublicVenuePolicy,
) -> (PublicVenueRecord, CityPdCase, CityPdIntent) {
    let notice = babylon_practice_contract::initial_public_venue_notice(policy)
        .expect("public venue fixture supplies valid evidence");
    let mut case = CityPdCase {
        case_id: [0; 32],
        actor_id: config.actor_id,
        subject_id: policy.workplace_id,
        county: config.county,
        public_venue_id: policy.venue_id,
        source_id: notice.source_id,
        source_kind: CityPdCaseSource::CapturedPublicRecord,
        source_receipt_id: None,
        case_source_witness_id: None,
        observed_period: 0,
        acquired_period: 0,
        status: CityPdCaseStatus::Open,
    };
    case.case_id = babylon_practice_contract::city_pd_case_id(&case)
        .expect("public venue fixture supplies valid evidence");
    let mut intent = CityPdIntent {
        intent_id: [0; 32],
        schema_version: 1,
        campaign_id: config.campaign_id,
        actor_id: config.actor_id,
        authority_id: config.authority_id,
        config_digest: babylon_practice_contract::city_pd_config_digest(config)
            .expect("public venue fixture supplies valid evidence"),
        decision_basis_digest: [11; 32],
        case_id: case.case_id,
        subject_id: case.subject_id,
        source_period: 1,
        resolve_period: 2,
        cost_micros: config.visit_cost_micros,
    };
    intent.intent_id = babylon_practice_contract::city_pd_intent_id(&intent)
        .expect("public venue fixture supplies valid evidence");
    (notice, case, intent)
}

fn paid_material_evidence(intent: &CityPdIntent) -> (AgencyObservationFundingReceipt, Vec<u8>) {
    let (catalog, opening) = funding_control::opening();
    let first = funding_control::close(&catalog, &opening, &[], &[funding_control::collection(1)])
        .expect("public venue fixture supplies valid evidence");
    let (catalog, state) = funding_control::controlled_opening(catalog, first.state);
    let agency = agency_account();
    let principal = funding_control::recipient();
    let input = AgencyAttendanceInput {
        intent_id: intent.intent_id,
        shift_id: babylon_material_circuit::agency_shift_id(2, intent.intent_id),
        agency,
        principal_id: principal,
        residence: state
            .final_demand_principals
            .iter()
            .find(|p| p.id == principal)
            .expect("public venue fixture supplies valid evidence")
            .location,
        labor_unit_id: funding_control::unit(90),
        due_period: 2,
        hours: 1,
        hourly_rate: funding_control::money(100_000),
    };
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &state,
        &[],
        &[],
        &[input],
    )
    .expect("public venue fixture supplies valid evidence")
    .finish_with_workforce(
        &catalog,
        funding_control::labor(3),
        funding_control::members(3),
    )
    .expect("public venue fixture supplies valid evidence");
    let bytes = babylon_tick::material_world::encode_material_receipts(&catalog, 2, &completed)
        .expect("public venue fixture supplies valid evidence");
    (completed.agency_attendance[0].clone(), bytes)
}

fn paid_fixture() -> PaidFixture {
    let (config, policy) = paid_terms();
    let (notice, case, intent) = authored_case_and_intent(&config, &policy);
    let (funding, bytes) = paid_material_evidence(&intent);
    let result =
        public_venue::publish_paid_visit(&policy, &config, &intent, &case, &funding, &bytes)
            .expect("public venue fixture supplies valid evidence");
    PaidFixture {
        config,
        policy,
        notice,
        case,
        intent,
        funding,
        bytes,
        result,
    }
}

#[test]
fn paid_visit_requires_real_funding_and_material_receipt_family() {
    let fixture = paid_fixture();
    let history = assert_paid_public_access(&fixture);
    assert_original_period_sources(&fixture, &history);
    assert_paid_evidence_refusals(&fixture);
}

fn assert_paid_public_access(fixture: &PaidFixture) -> PublicVenueHistory {
    let PaidFixture {
        policy,
        config,
        notice,
        result,
        ..
    } = fixture;
    let history = PublicVenueHistory {
        policy: (*policy).clone(),
        records: vec![(*notice).clone()],
    };
    assert!(
        public_venue::read_public_visit(&history, policy.player_reader_actor_id, result)
            .expect("public venue fixture supplies valid evidence")
            .is_none()
    );
    let mut published_history = history.clone();
    published_history.records.push(result.record().clone());
    assert!(public_venue::read_public_visit(
        &published_history,
        policy.player_reader_actor_id,
        result
    )
    .expect("public venue fixture supplies valid evidence")
    .is_some());
    assert!(
        public_venue::read_public_visit(&published_history, 999, result)
            .expect("public venue fixture supplies valid evidence")
            .is_none()
    );
    let token =
        public_venue::admit_public_venue_source(&history, PublicVenueSourceProof::InitialNotice)
            .expect("public venue fixture supplies valid evidence");
    let sources = public_venue::read_public_venue_sources(
        &history,
        config.actor_id,
        result,
        std::slice::from_ref(&token),
    )
    .expect("public venue fixture supplies valid evidence");
    assert_eq!(sources.len(), 1);
    assert_eq!(sources[0].record.source_id, notice.source_id);
    assert!(public_venue::read_public_venue_sources(
        &history,
        901,
        result,
        std::slice::from_ref(&token)
    )
    .is_err());
    assert!(public_venue::read_public_venue_sources(
        &history,
        config.actor_id,
        result,
        &[token.clone(), token]
    )
    .is_err());
    assert_eq!(
        public_venue::read_public_venue_sources(&history, config.actor_id, result, &[])
            .expect("public venue fixture supplies valid evidence"),
        Vec::new()
    );
    assert_ne!(result.visit_core_id(), [0; 32]);
    assert_ne!(result.shift_evidence_id(), result.payment_evidence_id());
    history
}

struct ContactPeriod {
    commitment: OrganizerCommitment,
    organizer: OrganizerState,
    entries: OrganizerPeriodJournalEntries,
    closed: MaterialCircuitState,
    publication: PublicVenueRecord,
}

fn resolve_contact_period(
    session: &mut Session,
    sink: &mut CollectingSink,
    config: &OrganizerConfig,
    policy: &PublicVenuePolicy,
) -> ContactPeriod {
    let commitment = organizer_aid_fixture::commitment(session, OrganizerChoice::Reinforce);
    let candidate = organizer_aid_fixture::prepare(session, Some(&commitment));
    organizer_aid_fixture::commit(session, sink, candidate);
    let organizer = session
        .material()
        .organizer_state()
        .expect("public venue fixture supplies valid evidence")
        .clone();
    let entries = session
        .material()
        .organizer_journal()
        .expect("public venue fixture supplies valid evidence")
        .latest()
        .expect("public venue fixture supplies valid evidence")
        .clone();
    let closed = session.material().state().clone();
    let publication = public_venue::publish_public_contact(
        policy,
        config,
        &commitment,
        &organizer,
        &entries,
        &closed,
    )
    .expect("public venue fixture supplies valid evidence");
    ContactPeriod {
        commitment,
        organizer,
        entries,
        closed,
        publication,
    }
}

fn assert_original_period_sources(fixture: &PaidFixture, history: &PublicVenueHistory) {
    let PaidFixture {
        policy,
        config,
        result,
        ..
    } = fixture;
    // Original period proof remains required after the live household book rolls forward.
    let mut organizer_config = organizer_aid_fixture::config();
    organizer_config.contact_hours = 1;
    organizer_config.partner_response_hours = 1;
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("public venue fixture supplies valid evidence");
    let mut session =
        organizer_aid_fixture::authored_session(foundation, organizer_config.clone(), false, false);
    let mut sink = CollectingSink::default();
    let first = resolve_contact_period(&mut session, &mut sink, &organizer_config, policy);
    let second = resolve_contact_period(&mut session, &mut sink, &organizer_config, policy);
    let mut contact_history = (*history).clone();
    contact_history
        .records
        .extend([first.publication.clone(), second.publication.clone()]);
    contact_history
        .records
        .sort_by_key(|row| (row.period, row.source_id));
    let first_proof = || PublicVenueSourceProof::Contact {
        config: &organizer_config,
        commitment: &first.commitment,
        organizer: &first.organizer,
        entries: &first.entries,
        closed: &first.closed,
    };
    let first_token = public_venue::admit_public_venue_source(&contact_history, first_proof())
        .expect("public venue fixture supplies valid evidence");
    assert!(public_venue::admit_public_venue_source(
        &contact_history,
        PublicVenueSourceProof::Contact {
            config: &organizer_config,
            commitment: &first.commitment,
            organizer: &first.organizer,
            entries: &first.entries,
            closed: &second.closed
        }
    )
    .is_err());
    let second_token = public_venue::admit_public_venue_source(
        &contact_history,
        PublicVenueSourceProof::Contact {
            config: &organizer_config,
            commitment: &second.commitment,
            organizer: &second.organizer,
            entries: &second.entries,
            closed: &second.closed,
        },
    )
    .expect("public venue fixture supplies valid evidence");
    let forward = public_venue::read_public_venue_sources(
        &contact_history,
        config.actor_id,
        result,
        &[first_token.clone(), second_token.clone()],
    )
    .expect("public venue fixture supplies valid evidence");
    let reverse = public_venue::read_public_venue_sources(
        &contact_history,
        config.actor_id,
        result,
        &[second_token, first_token],
    )
    .expect("public venue fixture supplies valid evidence");
    assert_eq!(forward, reverse);
    assert_eq!(forward.len(), 1);
    assert_eq!(forward[0].record.source_id, first.publication.source_id);
}

fn assert_paid_evidence_refusals(fixture: &PaidFixture) {
    let PaidFixture {
        policy,
        config,
        intent,
        case,
        funding,
        bytes,
        result,
        ..
    } = fixture;
    let mut unpaid = (*funding).clone();
    unpaid.outcome = AgencyAttendanceOutcome::NoFunds;
    assert_eq!(
        public_venue::publish_paid_visit(policy, config, intent, case, &unpaid, bytes)
            .expect_err("invalid paid evidence must be refused"),
        babylon_tick::public_venue::PublicVenueEvidenceError::InvalidPaidEvidence
    );
    unpaid.outcome = AgencyAttendanceOutcome::InsufficientTime;
    assert_eq!(
        public_venue::publish_paid_visit(policy, config, intent, case, &unpaid, bytes)
            .expect_err("invalid paid evidence must be refused"),
        babylon_tick::public_venue::PublicVenueEvidenceError::InvalidPaidEvidence
    );
    assert_eq!(
        public_venue::publish_paid_visit(policy, config, intent, case, funding, bytes)
            .expect("public venue fixture supplies valid evidence"),
        *result
    );
    let mut foreign_case = (*case).clone();
    foreign_case.source_id = [99; 32];
    assert!(public_venue::publish_paid_visit(
        policy,
        config,
        intent,
        &foreign_case,
        funding,
        bytes
    )
    .is_err());
    let mut truncated = (*bytes).clone();
    truncated.pop();
    assert!(
        public_venue::publish_paid_visit(policy, config, intent, case, funding, &truncated)
            .is_err()
    );
}
