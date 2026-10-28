//! Leaf implementation for the parent module; public paths stay on the parent.

use babylon_practice_contract::OrganizerPeriodJournal;
use babylon_practice_contract::OrganizerPeriodJournalEntries;
use babylon_practice_contract::ResolvedOrganizerPeriod;
use babylon_practice_contract::{
    OrganizerContribution, OrganizerHouseholdBinding, OrganizerObservation, OrganizerParticipant,
    OrganizerPartner, OrganizerTimeUse, PracticeResourceCapacity, PracticeResourceRequirement,
};

use babylon_practice_contract::{
    decode_organizer_receipt, decode_practice_intent, encode_practice_intent,
    organizer_state_digest, organizer_time_unit_id, practice_intent_digest,
    practice_parameter_bytes_digest, resolve_organizer_practice_with_time,
    validate_organizer_commitment, validate_organizer_pair, validate_organizer_state,
    validate_practice_intent, ActorOrganizationId, OrderedPracticeActionBatch, OrganizerChoice,
    OrganizerCommand, OrganizerConfig, OrganizerError, OrganizerInquiry, OrganizerOutcome,
    OrganizerPartnerPolicy, OrganizerPartnerResponse, OrganizerPauseReason,
    OrganizerPeriodTimeResources, OrganizerRefusal, OrganizerReport, OrganizerState,
    OrganizerTimeBindingMode, OrganizerView, OrganizerWorkplaceFacts, PracticeAuthorityKind,
    PracticeId, PracticeInputAuthorityLedger, PracticeIntentError,
    PracticeResourceAllocationContract, PracticeResourceAllocationMode,
    PracticeResourceAllocationOutcome, PracticeResourceId, PracticeResourceLocator,
    PracticeResourceOwner, PracticeUnitId, ResolvedPracticeBatch, ORGANIZER_SCHEMA_VERSION,
};

use babylon_kernel::replay::ReplaySessionId;

pub(crate) fn config() -> OrganizerConfig {
    OrganizerConfig {
        schema_version: ORGANIZER_SCHEMA_VERSION,
        collection: None,
        time_binding: OrganizerTimeBindingMode::FixedTimeControl,
        aid_bindings: vec![],
        campaign_id: [1; 16],
        controlled_actor_id: 101,
        input_authority_id: [2; 16],
        organization_label: "Wayne Organizing Collective".into(),
        workplace_id: 104,
        workplace_process_id: [8; 32],
        workplace_label: "Wayne metal-parts workplace".into(),
        workplace_partner: OrganizerPartner {
            actor_id: 102,
            authority_id: [3; 16],
            label: "Workplace committee".into(),
            policy: OrganizerPartnerPolicy::Participate,
            permits_work_report: true,
            permits_maintenance_report: true,
        },
        neighborhood_partner: OrganizerPartner {
            actor_id: 103,
            authority_id: [4; 16],
            label: "Neighborhood contact group".into(),
            policy: OrganizerPartnerPolicy::Participate,
            permits_work_report: false,
            permits_maintenance_report: false,
        },
        participants: [(201, 101, 16), (202, 102, 8), (203, 103, 8)]
            .into_iter()
            .map(|(contributor_id, actor_id, hours)| OrganizerParticipant {
                contributor_id,
                label: format!("Participant {contributor_id}"),
                available_hours: hours,
                commitments: vec![OrganizerContribution { actor_id, hours }],
                concern: "Understand reduced work".into(),
                objection: "Do not promise hours we do not have".into(),
                review_condition: "Review after resolution".into(),
            })
            .collect(),
        inquiry_hours: 12,
        contact_hours: 8,
        partner_response_hours: 2,
        initial_agreement_through_period: 3,
        contact_renewal_periods: 2,
        content_digest: [5; 32],
        initial_observations: vec![],
    }
}

pub(crate) fn facts(period: u64, labor: u64) -> OrganizerWorkplaceFacts {
    OrganizerWorkplaceFacts {
        period,
        workplace_id: 104,
        performed_labor_hours: labor,
        output_kg: labor * 6,
        maintenance_enabled_batches: labor / 10,
        maintenance_consumed_batches: labor / 10,
        maintenance_expired_batches: 0,
    }
}

pub(crate) fn command(
    config: &OrganizerConfig,
    state: &OrganizerState,
    choice: OrganizerChoice,
) -> OrganizerCommand {
    OrganizerCommand {
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: state.period,
        content_digest: config.content_digest,
        resource_digest: babylon_practice_contract::organizer_resource_digest()
            .expect("the organizer resource set has a digest"),
        nonce: [7; 16],
        choice,
    }
}

pub(crate) fn journal_of(entries: &OrganizerPeriodJournalEntries) -> OrganizerPeriodJournal {
    OrganizerPeriodJournal {
        periods: vec![entries.clone()],
    }
}

pub(crate) fn act(
    config: &OrganizerConfig,
    state: &OrganizerState,
    choice: OrganizerChoice,
    labor: u64,
) -> ResolvedOrganizerPeriod {
    let accepted =
        babylon_practice_contract::admit_organizer(config, state, &command(config, state, choice))
            .expect("the fixture admits the organizer actor");
    babylon_practice_contract::resolve_organizer_period(
        config,
        state,
        &facts(state.period + 1, labor),
        Some(&accepted),
    )
    .expect("the organizer period resolves")
}

#[test]
pub(crate) fn inquiry_uses_typed_practice_and_earns_a_finite_committed_report() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let first = act(&config, &opening, OrganizerChoice::Hold, 160);
    let second = act(&config, &first, OrganizerChoice::Hold, 0);
    let command = command(
        &config,
        &second,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
    );
    let commitment = babylon_practice_contract::admit_organizer(&config, &second, &command)
        .expect("the fixture admits the organizer actor");
    let intent =
        babylon_practice_contract::organizer_practice_intent(&config, &second, &commitment).expect(
            "the fixture call `organizer_practice_intent` succeeds for the authored inputs",
        );
    assert_eq!(intent.practice_id, PracticeId::Investigate);
    assert_eq!(
        decode_practice_intent(
            &encode_practice_intent(&intent).expect("the practice intent encodes canonically")
        )
        .expect("the practice intent bytes decode"),
        intent
    );
    let third = babylon_practice_contract::resolve_organizer_period(
        &config,
        &second,
        &facts(3, 160),
        Some(&commitment),
    )
    .expect("the organizer period resolves");
    let receipt = third
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(receipt.hours_spent, 12);
    assert_eq!(receipt.outcome, OrganizerOutcome::EvidenceObtained);
    let observed = third
        .journal
        .observations
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!((observed.observed_period, observed.acquired_period), (2, 3));
    assert!(matches!(
        observed.report,
        OrganizerReport::Work {
            performed_labor_hours: 0,
            output_kg: 0,
            previous_labor_hours: Some(160),
            ..
        }
    ));
    let fourth = act(&config, &third, OrganizerChoice::Hold, 160);
    assert!(fourth
        .learned_authority_index
        .iter()
        .any(|row| row.observation_id == observed.observation_id));
    assert_eq!(
        fourth
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .hours_spent,
        8
    );
    assert!(fourth.standing.authorized);
}

#[test]
pub(crate) fn choices_create_different_real_work_without_altering_factory_facts() {
    let config = config();
    let initial = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let initial = act(&config, &initial, OrganizerChoice::Hold, 160);
    let choices = [
        OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived),
        OrganizerChoice::Reinforce,
        OrganizerChoice::Hold,
        OrganizerChoice::PauseStanding,
    ];
    let states: Vec<_> = choices
        .into_iter()
        .map(|choice| act(&config, &initial, choice, 0))
        .collect();
    let results: Vec<_> = states
        .iter()
        .map(|state| {
            state
                .journal
                .receipts
                .last()
                .expect("the fixture sequence is non-empty")
        })
        .collect();
    assert_eq!(
        results
            .iter()
            .map(|row| row.hours_spent)
            .collect::<Vec<_>>(),
        [12, 8, 8, 0]
    );
    assert_eq!(results[0].outcome, OrganizerOutcome::EvidenceObtained);
    assert_eq!(results[1].partner_actor_id, Some(102));
    assert_eq!(results[2].partner_actor_id, Some(103));
    assert_eq!(results[3].outcome, OrganizerOutcome::StandingPaused);
    for state in &states {
        assert_eq!(state.last_workplace_facts, Some(facts(2, 0)));
    }
    for pair in states.windows(2) {
        assert_ne!(
            organizer_state_digest(&pair[0]).expect("the organizer state has a digest"),
            organizer_state_digest(&pair[1]).expect("the organizer state has a digest")
        );
    }
}

#[test]
pub(crate) fn contact_receipt_is_consumed_later_and_expired_relationship_can_recover() {
    let config = config();
    let mut state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    for _ in 0..3 {
        state = act(&config, &state, OrganizerChoice::Hold, 160).state;
    }
    let standing = act(&config, &state, OrganizerChoice::PauseStanding, 0);
    let mut state = standing;
    assert_eq!(
        state.journal.observations.len(),
        0,
        "workplace report agreement expired after period 3"
    );
    state = act(&config, &state, OrganizerChoice::Reinforce, 160);
    let product = state
        .contact_products
        .last()
        .expect("the fixture sequence is non-empty")
        .clone();
    let receipt = state
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .clone();
    assert_eq!(receipt.outcome, OrganizerOutcome::ContactCompleted);
    assert!(!state.consumed_product_ids.contains(&product.product_id));
    assert_eq!(
        state
            .agreements
            .iter()
            .find(|row| row.partner_actor_id == 102)
            .expect("the fixture holds the searched element")
            .valid_through_period,
        3
    );
    let next = act(&config, &state, OrganizerChoice::Hold, 0);
    assert!(next.consumed_product_ids.contains(&product.product_id));
    let agreement = next
        .agreements
        .iter()
        .find(|row| row.partner_actor_id == 102)
        .expect("the fixture holds the searched element");
    assert_eq!(
        (agreement.valid_from_period, agreement.valid_through_period),
        (6, 7)
    );
    assert_eq!(
        next.journal
            .observations
            .last()
            .expect("the fixture sequence is non-empty")
            .observed_period,
        6
    );
    assert!(
        !next.standing.authorized,
        "specific commitment does not undo explicit pause"
    );
}

#[test]
pub(crate) fn partner_refusal_and_capacity_do_not_override_ruling_or_create_contact_products() {
    for policy in [
        OrganizerPartnerPolicy::Refuse,
        OrganizerPartnerPolicy::NoResponse,
        OrganizerPartnerPolicy::Participate,
    ] {
        let mut config = config();
        config.workplace_partner.policy = policy;
        if policy == OrganizerPartnerPolicy::Participate {
            config.participants[1].commitments[0].hours = 1;
        }
        let state = babylon_practice_contract::initial_organizer_state(&config)
            .expect("the authored config admits an opening organizer state");
        let result = act(&config, &state, OrganizerChoice::Reinforce, 160);
        let receipt = result
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty");
        assert_eq!(receipt.choice, OrganizerChoice::Reinforce);
        assert_eq!(receipt.hours_spent, 8);
        assert_eq!(receipt.outcome, OrganizerOutcome::ContactUncompleted);
        assert_eq!(result.contact_products.len(), 0);
    }
}

#[test]
pub(crate) fn explicit_pause_persists_hold_does_not_resume_and_resume_performs_routine() {
    let config = config();
    let initial = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let paused = act(&config, &initial, OrganizerChoice::PauseStanding, 160);
    let held = act(&config, &paused, OrganizerChoice::Hold, 0);
    assert_eq!(
        held.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .hours_spent,
        0
    );
    assert!(!held.standing.authorized);
    let resumed = act(&config, &held, OrganizerChoice::ResumeStanding, 160);
    assert!(resumed.standing.authorized);
    assert_eq!(
        resumed
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .hours_spent,
        8
    );
    assert_eq!(
        resumed
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .partner_actor_id,
        Some(103)
    );
}

#[test]
pub(crate) fn missing_routine_time_pauses_and_failed_admission_preserves_authorization() {
    let mut config = config();
    config.participants[0].commitments[0].hours = 7;
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    assert_eq!(
        babylon_practice_contract::admit_organizer(
            &config,
            &state,
            &command(&config, &state, OrganizerChoice::Reinforce)
        ),
        Err(OrganizerError::Refused(
            OrganizerRefusal::InsufficientCommittedTime
        ))
    );
    assert!(state.standing.authorized);
    let next =
        babylon_practice_contract::resolve_organizer_period(&config, &state, &facts(1, 160), None)
            .expect("the organizer period resolves");
    assert_eq!(
        next.standing.paused_reason,
        Some(OrganizerPauseReason::InsufficientCommittedTime)
    );
    assert_eq!(
        next.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .hours_spent,
        0
    );
}

#[test]
// The Google-style module-qualified calls wrap this scenario past the Clippy
// line budget without changing its assertions.
#[allow(
    clippy::too_many_lines,
    reason = "`private_partner_policy_capacity_and_factory_facts_do_not_change_lawful_preview` keeps one authored sequence in a single place"
)]
pub(crate) fn private_partner_policy_capacity_and_factory_facts_do_not_change_lawful_preview() {
    let mut config = config();
    config.initial_observations.push(OrganizerObservation {
        observation_id: [9; 32],
        actor_id: config.controlled_actor_id,
        subject_id: config.workplace_id,
        source_actor_id: config.workplace_partner.actor_id,
        observed_period: 0,
        acquired_period: 0,
        receipt_id: None,
        report: OrganizerReport::Work {
            performed_labor_hours: 160,
            output_kg: 960,
            previous_labor_hours: None,
            previous_output_kg: None,
        },
    });
    let initial = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let state = act(&config, &initial, OrganizerChoice::PauseStanding, 160);
    assert!(
        !state.learned_authority_index.is_empty(),
        "the authorization test must have actual knowledge to withhold"
    );
    let command = command(
        &config,
        &state,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
    );
    let preview = babylon_practice_contract::preview_organizer(&config, &state, &command)
        .expect("the organizer preview builds");
    let view = babylon_practice_contract::organizer_view(
        &config,
        &state,
        &journal_of(&state.journal),
        config.controlled_actor_id,
    )
    .expect("the fixture call `organizer_view` succeeds for the authored inputs");
    let mut hidden = config.clone();
    hidden.workplace_partner.policy = OrganizerPartnerPolicy::Refuse;
    hidden.workplace_partner.permits_work_report = false;
    hidden.participants[1].available_hours = 999;
    hidden.participants[1].commitments[0].hours = 999;
    let mut hidden_state = state.clone();
    hidden_state
        .state
        .last_workplace_facts
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .output_kg = 12_345;
    assert_eq!(
        babylon_practice_contract::preview_organizer(&hidden, &hidden_state, &command)
            .expect("the organizer preview builds"),
        preview
    );
    assert_eq!(
        babylon_practice_contract::organizer_view(
            &hidden,
            &hidden_state,
            &journal_of(&hidden_state.journal),
            hidden.controlled_actor_id
        )
        .expect("the fixture call `organizer_view` succeeds for the authored inputs"),
        view
    );
    let serialized = serde_json::to_string(&view).expect("the fixture value formats as text");
    assert!(!serialized.contains("permits_work_report"));
    assert!(!serialized.contains("last_workplace_facts"));

    for refusal in [
        OrganizerRefusal::WrongAuthority,
        OrganizerRefusal::StalePeriod,
        OrganizerRefusal::InsufficientCommittedTime,
    ] {
        let mut lawful_config = config.clone();
        let mut concealed_config = hidden.clone();
        let mut request = command.clone();
        match refusal {
            OrganizerRefusal::WrongAuthority => request.authority_id = [99; 16],
            OrganizerRefusal::StalePeriod => request.expected_period += 1,
            OrganizerRefusal::InsufficientCommittedTime => {
                lawful_config.participants[0].commitments[0].hours = 11;
                concealed_config.participants[0].commitments[0].hours = 11;
            }
            _ => unreachable!(),
        }
        let lawful = babylon_practice_contract::preview_organizer(&lawful_config, &state, &request)
            .expect("the organizer preview builds");
        let concealed = babylon_practice_contract::preview_organizer(
            &concealed_config,
            &hidden_state,
            &request,
        )
        .expect("the organizer preview builds");
        assert_eq!(lawful.refusal, Some(refusal));
        assert_eq!(
            lawful, concealed,
            "safe refusal must not distinguish hidden state"
        );
        if refusal == OrganizerRefusal::WrongAuthority {
            assert_eq!((lawful.available_hours, lawful.required_hours), (0, 0));
            assert!(!lawful.replaces_standing_work);
            assert_eq!(lawful.observations.len(), 0);
        } else {
            assert_eq!(
                lawful.observations, preview.observations,
                "authorized refusal retains only lawful observations"
            );
            assert_eq!(lawful.required_hours, config.inquiry_hours);
            assert_eq!(
                lawful.available_hours,
                lawful_config.participants[0].commitments[0].hours
            );
        }
    }
}

#[test]
pub(crate) fn command_authority_tick_and_contracts_are_bound_and_retry_is_identical() {
    let config = config();
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let valid = command(&config, &state, OrganizerChoice::Reinforce);
    let accepted = babylon_practice_contract::admit_organizer(&config, &state, &valid)
        .expect("the fixture admits the organizer actor");
    assert_eq!(
        babylon_practice_contract::admit_organizer(&config, &state, &valid)
            .expect("the fixture admits the organizer actor"),
        accepted
    );
    for refusal in [
        OrganizerRefusal::WrongCampaign,
        OrganizerRefusal::WrongAuthority,
        OrganizerRefusal::StalePeriod,
        OrganizerRefusal::ContentChanged,
        OrganizerRefusal::ResourceContractChanged,
    ] {
        let mut command = valid.clone();
        match refusal {
            OrganizerRefusal::WrongCampaign => command.campaign_id = [99; 16],
            OrganizerRefusal::WrongAuthority => command.authority_id = [99; 16],
            OrganizerRefusal::StalePeriod => command.expected_period = 10,
            OrganizerRefusal::ContentChanged => command.content_digest = [99; 32],
            OrganizerRefusal::ResourceContractChanged => command.resource_digest = [99; 32],
            _ => unreachable!(),
        }
        assert_eq!(
            babylon_practice_contract::admit_organizer(&config, &state, &command),
            Err(OrganizerError::Refused(refusal))
        );
    }
    let mut forged = accepted.clone();
    forged.resolves_period = 3;
    assert_eq!(
        babylon_practice_contract::resolve_organizer_period(
            &config,
            &state,
            &facts(1, 160),
            Some(&forged)
        ),
        Err(OrganizerError::InvalidCommitment)
    );
    assert_eq!(state.period, 0);
}

#[test]
pub(crate) fn shared_contributors_cannot_promise_or_spend_the_same_hours_twice() {
    let mut config = config();
    config.participants = vec![OrganizerParticipant {
        contributor_id: 201,
        label: "Shared committed body".into(),
        available_hours: 32,
        commitments: vec![
            OrganizerContribution {
                actor_id: 101,
                hours: 16,
            },
            OrganizerContribution {
                actor_id: 102,
                hours: 8,
            },
            OrganizerContribution {
                actor_id: 103,
                hours: 8,
            },
        ],
        concern: "Available time".into(),
        objection: String::new(),
        review_condition: "Next period".into(),
    }];
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let next = act(&config, &state, OrganizerChoice::Reinforce, 160);
    let usage = &next
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .time_use;
    assert_eq!(usage.iter().map(|row| row.hours).sum::<u64>(), 10);
    assert!(usage.iter().all(|row| row.contributor_id == 201));
    config.participants[0].available_hours = 31;
    assert_eq!(
        babylon_practice_contract::validate_organizer_config(&config),
        Err(OrganizerError::InvalidConfig)
    );
}

#[test]
pub(crate) fn restart_canonical_roundtrip_and_action_batch_are_deterministic() {
    let config = config();
    let initial = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let config = babylon_practice_contract::decode_organizer_config(
        &babylon_practice_contract::encode_organizer_config(&config)
            .expect("the fixture value encodes to its canonical bytes"),
    )
    .expect("the canonical bytes decode into the declared type");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &initial,
        &command(&config, &initial, OrganizerChoice::Reinforce),
    )
    .expect("the fixture admits the organizer actor");
    let batch = babylon_practice_contract::organizer_action_batch(
        &config,
        &initial,
        Some(&accepted),
        ReplaySessionId::try_from("organizer-replay")
            .expect("the fixture value fits the target range"),
    )
    .expect("the authored action batch builds");
    assert_eq!(
        batch.items().len(),
        2,
        "player and independent participating response share canonical input rail"
    );
    let first = babylon_practice_contract::resolve_organizer_period(
        &config,
        &initial,
        &facts(1, 160),
        Some(&accepted),
    )
    .expect("the organizer period resolves");
    let restarted = babylon_practice_contract::decode_organizer_state(
        &babylon_practice_contract::encode_organizer_state(&first)
            .expect("the fixture value encodes to its canonical bytes"),
    )
    .expect("the canonical bytes decode into the declared type");
    let second =
        babylon_practice_contract::resolve_organizer_period(&config, &first, &facts(2, 0), None)
            .expect("the organizer period resolves");
    assert_eq!(
        babylon_practice_contract::resolve_organizer_period(
            &config,
            &restarted,
            &facts(2, 0),
            None
        )
        .expect("the organizer period resolves"),
        second
    );
    assert_eq!(
        babylon_practice_contract::resolve_organizer_period(
            &config,
            &initial,
            &facts(1, 160),
            Some(&accepted)
        )
        .expect("the organizer period resolves"),
        first
    );
    let mut bytes = babylon_practice_contract::encode_organizer_state(&first)
        .expect("the fixture value encodes to its canonical bytes");
    bytes.push(b' ');
    assert_eq!(
        babylon_practice_contract::decode_organizer_state(&bytes),
        Err(OrganizerError::NonCanonical)
    );
    let mut invalid = first.state.clone();
    invalid.schema_version = 0;
    assert_eq!(
        babylon_practice_contract::encode_organizer_state(&invalid),
        Err(OrganizerError::UnsupportedSchema)
    );
}

#[test]
pub(crate) fn changing_actor_labels_and_authority_identifiers_creates_no_capacity_or_success_privilege(
) {
    let original = config();
    let mut renamed = original.clone();
    renamed.organization_label = "CPU organization".into();
    renamed.input_authority_id = [20; 16];
    let left = act(
        &original,
        &babylon_practice_contract::initial_organizer_state(&original)
            .expect("the authored config admits an opening organizer state"),
        OrganizerChoice::Reinforce,
        160,
    );
    let right = act(
        &renamed,
        &babylon_practice_contract::initial_organizer_state(&renamed)
            .expect("the authored config admits an opening organizer state"),
        OrganizerChoice::Reinforce,
        160,
    );
    let left = left
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    let right = right
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(left.outcome, right.outcome);
    assert_eq!(left.hours_spent, right.hours_spent);
    assert_eq!(left.time_use, right.time_use);
    assert_eq!(left.partner_response, right.partner_response);
}

#[test]
pub(crate) fn severing_the_contact_consumer_removes_later_report_access_but_preserves_completed_work(
) {
    let config = config();
    let initial = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut opening = act(&config, &initial, OrganizerChoice::Hold, 160);
    for _ in 0..1 {
        opening = act(&config, &opening, OrganizerChoice::Hold, 160);
    }
    opening = act(&config, &opening, OrganizerChoice::Reinforce, 160);
    let contact_receipt = opening
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .clone();
    let completed = facts(4, 0);
    let connected =
        babylon_practice_contract::reduce_organizer_products(&config, &opening, &completed)
            .expect("the organizer products aggregate");
    let disconnected = babylon_practice_contract::report_organizer_workplace(
        &config, &opening, &opening, &completed,
    )
    .expect("the fixture call `report_organizer_workplace` succeeds for the authored inputs");
    assert_eq!(connected.journal.receipts.len(), 0);
    assert_eq!(disconnected.journal.receipts.len(), 0);
    assert_eq!(
        opening.journal.receipts.last(),
        Some(&contact_receipt),
        "completed work stays in its own period evidence"
    );
    assert!(connected.consumed_product_ids.contains(
        &contact_receipt
            .contact_product_id
            .expect("contact completed")
    ));
    assert!(!disconnected.consumed_product_ids.contains(
        &contact_receipt
            .contact_product_id
            .expect("contact completed")
    ));
    assert!(connected
        .agreements
        .iter()
        .any(|row| row.partner_actor_id == 102 && row.valid_through_period >= 4));
    assert!(!disconnected
        .agreements
        .iter()
        .any(|row| row.partner_actor_id == 102 && row.valid_through_period >= 4));
    assert_eq!(connected.journal.observations.len(), 1);
    assert_eq!(disconnected.journal.observations.len(), 0);
}

#[test]
pub(crate) fn receipt_codec_rejects_noncanonical_unknown_and_false_conservation_claims() {
    let config = config();
    let state = act(
        &config,
        &babylon_practice_contract::initial_organizer_state(&config)
            .expect("the authored config admits an opening organizer state"),
        OrganizerChoice::Reinforce,
        160,
    );
    let receipt = state
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    let bytes = babylon_practice_contract::encode_organizer_receipt(receipt)
        .expect("the fixture value encodes to its canonical bytes");
    assert_eq!(
        decode_organizer_receipt(&bytes)
            .expect("the canonical bytes decode into the declared type"),
        *receipt
    );
    let mut bad = receipt.clone();
    bad.hours_spent += 1;
    assert_eq!(
        babylon_practice_contract::encode_organizer_receipt(&bad),
        Err(OrganizerError::InvalidState)
    );
    let mut bad = bytes.clone();
    bad.push(b'\n');
    assert_eq!(
        decode_organizer_receipt(&bad),
        Err(OrganizerError::NonCanonical)
    );
    let mut bad = bytes;
    bad.pop();
    bad.extend_from_slice(b",\"provider_private_stock\":99}");
    assert_eq!(decode_organizer_receipt(&bad), Err(OrganizerError::Codec));
}

#[test]
pub(crate) fn inquiry_question_bytes_change_intent_identity_and_other_parameters_remain_closed() {
    let config = config();
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let intent = |question| {
        let accepted = babylon_practice_contract::admit_organizer(
            &config,
            &state,
            &command(&config, &state, OrganizerChoice::Inquiry(question)),
        )
        .expect("the fixture admits the organizer actor");
        babylon_practice_contract::organizer_practice_intent(&config, &state, &accepted)
            .expect("the fixture call `organizer_practice_intent` succeeds for the authored inputs")
    };
    let work = intent(OrganizerInquiry::WorkLost);
    let maintenance = intent(OrganizerInquiry::MaintenanceReceived);
    assert_ne!(
        practice_intent_digest(&work).expect("the practice intent has a digest"),
        practice_intent_digest(&maintenance).expect("the practice intent has a digest")
    );
    assert_ne!(
        practice_parameter_bytes_digest(&work).expect("the parameter bytes have a digest"),
        practice_parameter_bytes_digest(&maintenance).expect("the parameter bytes have a digest")
    );
    let mut unknown = work.clone();
    unknown.parameters[0].value_bytes[0] = 3;
    assert_eq!(
        validate_practice_intent(&unknown),
        Err(PracticeIntentError::IntentParameterUnsupported)
    );
    unknown = work;
    unknown.parameters[0].key_u8 = 2;
    assert_eq!(
        validate_practice_intent(&unknown),
        Err(PracticeIntentError::IntentParameterUnsupported)
    );
}

#[test]
pub(crate) fn every_accepted_control_and_nonce_binds_distinct_canonical_input() {
    let config = config();
    let paused = act(
        &config,
        &babylon_practice_contract::initial_organizer_state(&config)
            .expect("the authored config admits an opening organizer state"),
        OrganizerChoice::PauseStanding,
        160,
    );
    let session = ReplaySessionId::try_from("organizer-controls")
        .expect("the fixture value fits the target range");
    let make = |choice, nonce| {
        let mut command = command(&config, &paused, choice);
        command.nonce = nonce;
        let accepted = babylon_practice_contract::admit_organizer(&config, &paused, &command)
            .expect("the fixture admits the organizer actor");
        let batch = babylon_practice_contract::organizer_action_batch(
            &config,
            &paused,
            Some(&accepted),
            session.clone(),
        )
        .expect("the authored action batch builds");
        let outcome = babylon_practice_contract::resolve_organizer_period(
            &config,
            &paused,
            &facts(2, 0),
            Some(&accepted),
        )
        .expect("the organizer period resolves");
        (batch, outcome)
    };
    let commands = [
        make(OrganizerChoice::PauseStanding, [10; 16]),
        make(OrganizerChoice::PauseStanding, [11; 16]),
        make(OrganizerChoice::Hold, [10; 16]),
    ];
    for left in 0..commands.len() {
        for right in left + 1..commands.len() {
            assert_ne!(commands[left].1, commands[right].1);
            assert_ne!(
                commands[left].0.canonical_bytes(),
                commands[right].0.canonical_bytes(),
                "different accepted controls cannot disappear from canonical replay inputs"
            );
        }
    }
    for (batch, state) in commands {
        assert_eq!(
            batch.items().len(),
            1,
            "zero-cost control requests no partner practice"
        );
        assert_eq!(
            state
                .journal
                .receipts
                .last()
                .expect("the fixture sequence is non-empty")
                .hours_spent,
            0
        );
        assert_eq!(
            state
                .journal
                .receipts
                .last()
                .expect("the fixture sequence is non-empty")
                .partner_response,
            OrganizerPartnerResponse::NotRequested
        );
    }
}

#[test]
pub(crate) fn completed_contact_product_cannot_be_retargeted_to_a_different_partner() {
    let config = config();
    let mut state = act(
        &config,
        &babylon_practice_contract::initial_organizer_state(&config)
            .expect("the authored config admits an opening organizer state"),
        OrganizerChoice::Hold,
        160,
    )
    .state;
    assert_eq!(
        state.contact_products[0].partner_actor_id,
        config.neighborhood_partner.actor_id
    );
    state.contact_products[0].partner_actor_id = config.workplace_partner.actor_id;
    assert!(matches!(
        babylon_practice_contract::encode_organizer_state(&state),
        Err(OrganizerError::InvalidState)
    ));
}

#[test]
pub(crate) fn commitment_identity_remains_valid_after_resolution_but_rejects_forgery() {
    let config = config();
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &state,
        &command(&config, &state, OrganizerChoice::Reinforce),
    )
    .expect("the fixture admits the organizer actor");
    let next = babylon_practice_contract::resolve_organizer_period(
        &config,
        &state,
        &facts(1, 160),
        Some(&accepted),
    )
    .expect("the organizer period resolves");
    assert!(next.period > accepted.command.expected_period);
    assert_eq!(validate_organizer_commitment(&accepted), Ok(()));
    let mut wrong_nonce = accepted.clone();
    wrong_nonce.command.nonce = [22; 16];
    assert_eq!(
        validate_organizer_commitment(&wrong_nonce),
        Err(OrganizerError::InvalidCommitment)
    );
    let mut wrong_period = accepted;
    wrong_period.resolves_period += 1;
    assert_eq!(
        validate_organizer_commitment(&wrong_period),
        Err(OrganizerError::InvalidCommitment)
    );
}

#[test]
pub(crate) fn paired_checkpoint_validation_rejects_foreign_workplace_binding() {
    let config = config();
    let state = act(
        &config,
        &babylon_practice_contract::initial_organizer_state(&config)
            .expect("the authored config admits an opening organizer state"),
        OrganizerChoice::Hold,
        160,
    );
    let mut foreign_config = config.clone();
    foreign_config.workplace_id = 1004;
    assert_eq!(
        babylon_practice_contract::validate_organizer_config(&foreign_config),
        Ok(())
    );
    assert_eq!(validate_organizer_state(&state), Ok(()));
    assert_eq!(
        validate_organizer_pair(&foreign_config, &state),
        Err(OrganizerError::InvalidState)
    );
}

#[test]
pub(crate) fn explicit_hold_cannot_alias_standing_work_even_with_the_same_nonce() {
    let config = config();
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let session = ReplaySessionId::try_from("organizer-origin")
        .expect("the fixture value fits the target range");
    let routine =
        babylon_practice_contract::organizer_action_batch(&config, &state, None, session.clone())
            .expect("the authored action batch builds");
    let routine_own = routine
        .items()
        .iter()
        .find(|row| {
            row.intent().actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes()
        })
        .expect("the fixture holds the searched element");
    let mut command = command(&config, &state, OrganizerChoice::Hold);
    command.nonce = routine_own.intent().proposal_nonce.as_bytes();
    let accepted = babylon_practice_contract::admit_organizer(&config, &state, &command)
        .expect("the fixture admits the organizer actor");
    let explicit = babylon_practice_contract::organizer_action_batch(
        &config,
        &state,
        Some(&accepted),
        session,
    )
    .expect("the authored action batch builds");
    assert_ne!(
        routine.canonical_bytes(),
        explicit.canonical_bytes(),
        "standing authority is a canonical input, not hidden receipt metadata"
    );
    let partner = |batch: &OrderedPracticeActionBatch| {
        batch
            .items()
            .iter()
            .find(|row| {
                row.intent().actor_org_id.to_bytes()
                    == config.neighborhood_partner.actor_id.to_be_bytes()
            })
            .expect("the fixture holds the searched element")
            .intent()
            .proposal_nonce
            .as_bytes()
    };
    assert_ne!(
        partner(&routine),
        partner(&explicit),
        "partner response identity is bound to originating practice"
    );
    let routine_result =
        babylon_practice_contract::resolve_organizer_period(&config, &state, &facts(1, 160), None)
            .expect("the organizer period resolves");
    let explicit_result = babylon_practice_contract::resolve_organizer_period(
        &config,
        &state,
        &facts(1, 160),
        Some(&accepted),
    )
    .expect("the organizer period resolves");
    assert_eq!(
        routine_result
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .hours_spent,
        explicit_result
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .hours_spent
    );
    assert_eq!(
        routine_result
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .outcome,
        explicit_result
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .outcome
    );
}

#[test]
pub(crate) fn player_and_policy_authority_bindings_grant_no_shared_contact_time_privilege() {
    let mut config = config();
    let mut shared = config.participants.remove(0);
    for participant in config.participants.drain(..) {
        shared.available_hours += participant.available_hours;
        shared.commitments.extend(participant.commitments);
    }
    config.participants.push(shared);
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &state,
        &command(&config, &state, OrganizerChoice::Reinforce),
    )
    .expect("the fixture admits the organizer actor");
    let batch = babylon_practice_contract::organizer_resolved_action_batch(
        &config,
        &state,
        Some(&accepted),
    )
    .expect("the authored resolved batch builds");
    let ledger = babylon_practice_contract::organizer_input_authority_ledger(&config)
        .expect("the organizer ledger builds");
    assert_eq!(
        batch.items.len(),
        2,
        "our practice and independent response share the input rail"
    );
    let mut exchanged_ledger = ledger.clone();
    for row in &mut exchanged_ledger.rows {
        if row.actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes() {
            assert_eq!(row.authority_kind, PracticeAuthorityKind::PlayerSeat);
            row.authority_kind = PracticeAuthorityKind::DeterministicPolicy;
        } else if row.actor_org_id.to_bytes() == config.workplace_partner.actor_id.to_be_bytes() {
            assert_eq!(
                row.authority_kind,
                PracticeAuthorityKind::DeterministicPolicy
            );
            row.authority_kind = PracticeAuthorityKind::PlayerSeat;
        }
    }
    let mut exchanged_batch = batch.clone();
    exchanged_batch.authority_ledger_digest =
        babylon_practice_contract::input_authority_ledger_digest(&exchanged_ledger).expect(
            "the fixture call `input_authority_ledger_digest` succeeds for the authored inputs",
        );
    for item in &mut exchanged_batch.items {
        item.authority = exchanged_ledger
            .rows
            .iter()
            .find(|row| row.input_authority_id == item.intent.input_authority_id)
            .expect("the fixture holds the searched element")
            .clone();
    }
    let outcomes =
        [(&ledger, &batch), (&exchanged_ledger, &exchanged_batch)].map(|(ledger, batch)| {
            [32, 5].map(|available| shared_contact_allocation(&config, ledger, batch, available))
        });
    assert_eq!(
        outcomes[0], outcomes[1],
        "controller kind cannot alter costs, scarcity shares or conservation"
    );
    for (outcome, (expected, unused)) in outcomes[0].iter().zip([([8, 2], 22), ([4, 1], 0)]) {
        for (allocation, expected) in outcome.allocations().iter().zip(expected) {
            assert_eq!(allocation.allocated(), expected);
        }
        assert_eq!(outcome.balances()[0].unallocated(), unused);
    }
    let actual = babylon_practice_contract::resolve_organizer_period(
        &config,
        &state,
        &facts(1, 160),
        Some(&accepted),
    )
    .expect("the organizer period resolves");
    let receipt = actual
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(receipt.hours_spent, config.contact_hours);
    assert_eq!(
        receipt
            .time_use
            .iter()
            .filter(|row| row.actor_id == config.workplace_partner.actor_id)
            .map(|row| row.hours)
            .sum::<u64>(),
        config.partner_response_hours
    );
}

pub(crate) fn shared_contact_allocation(
    config: &OrganizerConfig,
    ledger: &PracticeInputAuthorityLedger,
    batch: &ResolvedPracticeBatch,
    available: u64,
) -> PracticeResourceAllocationOutcome {
    babylon_practice_contract::validate_resolved_practice_batch(batch, ledger)
        .expect("the authored fixture satisfies the rule");
    let projected = OrderedPracticeActionBatch::project(
        ReplaySessionId::try_from("organizer-controller-neutrality")
            .expect("the fixture value fits the target range"),
        batch,
        ledger,
    )
    .expect("the fixture projection accepts the authored state");
    let contract = PracticeResourceAllocationContract::conservation_first();
    let resource_id = PracticeResourceId::from_bytes([51; 32]);
    let unit_id = PracticeUnitId::from_bytes([52; 32]);
    let requests = projected
        .items()
        .iter()
        .map(|item| {
            let intent = item.intent();
            let quantity =
                if intent.actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes() {
                    config.contact_hours
                } else {
                    assert_eq!(
                        intent.actor_org_id.to_bytes(),
                        config.workplace_partner.actor_id.to_be_bytes()
                    );
                    config.partner_response_hours
                };
            babylon_practice_contract::derive_practice_resource_request(
                &contract,
                intent,
                &PracticeResourceRequirement {
                    practice_id: PracticeId::Organize,
                    locator: PracticeResourceLocator::Shared,
                    resource_id,
                    unit_id,
                    quantity,
                },
            )
            .expect("the authored action derives its request")
        })
        .collect::<Vec<_>>();
    babylon_practice_contract::allocate_practice_resources(
        &contract,
        &requests,
        &[PracticeResourceCapacity {
            owner: PracticeResourceOwner::Shared,
            resource_id,
            unit_id,
            mode: PracticeResourceAllocationMode::DivisibleProRata,
            available,
        }],
    )
    .expect("the fixture practice resources fit the authored budget")
}

pub(crate) fn finite_time(config: &OrganizerConfig, period: u64) -> OrganizerPeriodTimeResources {
    let mut resources = babylon_practice_contract::organizer_fixed_time_resources(config, period)
        .expect(
            "the fixture call `organizer_fixed_time_resources` succeeds for the authored inputs",
        );
    // The real source path accepts the captured material hour unit, not the
    // separate fixed-control identity.
    resources.unit_id = PracticeUnitId::from_bytes([44; 32]);
    for capacity in &mut resources.capacities {
        capacity.unit_id = resources.unit_id;
    }
    resources
}

pub(crate) fn finite_act(
    config: &OrganizerConfig,
    state: &OrganizerState,
    resources: &OrganizerPeriodTimeResources,
) -> Result<babylon_practice_contract::ResolvedOrganizerPeriod, OrganizerError> {
    let accepted = babylon_practice_contract::admit_organizer(
        config,
        state,
        &command(config, state, OrganizerChoice::Reinforce),
    )?;
    babylon_practice_contract::resolve_organizer_period_with_time(
        config,
        state,
        &facts(state.period + 1, 160),
        Some(&accepted),
        resources,
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[],
            collection: None,
        },
    )
}

pub(crate) fn shared_time(
    config: &OrganizerConfig,
    available: u64,
) -> OrganizerPeriodTimeResources {
    let mut resources = finite_time(config, 1);
    let shared = resources.bindings[0].budget_id;
    resources.bindings[1].budget_id = shared;
    resources.capacities.remove(1);
    resources.capacities[0].available = available;
    resources
}

pub(crate) fn assert_no_time_product(state: &babylon_practice_contract::ResolvedOrganizerPeriod) {
    let receipt = state
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(receipt.outcome, OrganizerOutcome::InsufficientTime);
    assert_eq!(receipt.hours_spent, 0);
    assert_eq!(receipt.time_use.len(), 0);
    assert!(receipt.contact_product_id.is_none());
    assert_eq!(receipt.observation_ids.len(), 0);
    assert_eq!(state.contact_products.len(), 0);
}

#[test]
pub(crate) fn finite_shared_alias_supply_is_counted_once_and_shortage_spends_nothing() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    // Eight controlled-actor hours plus two partner hours share nine actual hours.
    let resources = shared_time(&config, 9);
    let before = resources.clone();
    let next = finite_act(&config, &opening, &resources)
        .expect("the fixture call `finite_act` succeeds for the authored inputs");
    assert_no_time_product(&next);
    assert_eq!(next.agreements, opening.agreements);
    assert_eq!(resources, before);
    assert!(!next.standing.authorized);
    assert_eq!(
        next.standing.paused_reason,
        Some(OrganizerPauseReason::InsufficientAvailableTime)
    );
}

#[test]
pub(crate) fn finite_zero_availability_is_a_receipt_not_a_tick_error_or_refill() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut resources = finite_time(&config, 1);
    for capacity in &mut resources.capacities {
        capacity.available = 0;
    }
    assert_no_time_product(
        &finite_act(&config, &opening, &resources)
            .expect("the fixture call `finite_act` succeeds for the authored inputs"),
    );
}

#[test]
pub(crate) fn finite_complete_shared_budget_keeps_exact_alias_and_actor_debits() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let next = finite_act(&config, &opening, &shared_time(&config, 10))
        .expect("the fixture call `finite_act` succeeds for the authored inputs");
    let receipt = next
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(receipt.outcome, OrganizerOutcome::ContactCompleted);
    assert_eq!(receipt.hours_spent, 8);
    assert_eq!(
        receipt.time_use,
        [
            OrganizerTimeUse {
                contributor_id: 201,
                actor_id: 101,
                hours: 8
            },
            OrganizerTimeUse {
                contributor_id: 202,
                actor_id: 102,
                hours: 2
            },
        ]
    );
    assert_eq!(next.contact_products.len(), 1);
    assert_eq!(next.agreements, opening.agreements);
}

#[test]
pub(crate) fn finite_same_actor_aliases_share_one_derived_request_identity() {
    let mut config = config();
    config.participants[0].available_hours = 4;
    config.participants[0].commitments[0].hours = 4;
    let mut extra = config.participants[0].clone();
    extra.contributor_id = 204;
    config.participants.push(extra);
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut resources = finite_time(&config, 1);
    let shared = resources.bindings[0].budget_id;
    resources.bindings[3].budget_id = shared;
    resources.capacities.pop();
    resources.capacities[0].available = 8;
    let next = finite_act(&config, &opening, &resources)
        .expect("the fixture call `finite_act` succeeds for the authored inputs");
    let receipt = next
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(receipt.outcome, OrganizerOutcome::ContactCompleted);
    assert_eq!(
        receipt
            .time_use
            .iter()
            .filter(|row| row.actor_id == 101)
            .map(|row| row.hours)
            .sum::<u64>(),
        8
    );
    assert_eq!(
        receipt
            .time_use
            .iter()
            .filter(|row| row.actor_id == 101)
            .count(),
        2
    );
}

#[test]
pub(crate) fn finite_resource_order_does_not_change_receipt_or_products() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let resources = shared_time(&config, 10);
    let mut reversed = resources.clone();
    reversed.bindings.reverse();
    reversed.capacities.reverse();
    assert_eq!(
        finite_act(&config, &opening, &resources),
        finite_act(&config, &opening, &reversed)
    );
}

#[test]
pub(crate) fn finite_malformed_resources_refuse_with_specific_errors() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let resources = finite_time(&config, 1);
    let mut invalid = resources.clone();
    invalid.capacities.remove(0);
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeCapacityMissing)
    );
    invalid = resources.clone();
    invalid.capacities.push(invalid.capacities[0].clone());
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeCapacityDuplicate)
    );
    invalid = resources.clone();
    invalid.bindings.pop();
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeBindingMismatch)
    );
    invalid = resources.clone();
    invalid.bindings[1].contributor_id = invalid.bindings[0].contributor_id;
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeBindingMismatch)
    );
    invalid = resources.clone();
    invalid.capacities[0].unit_id = PracticeUnitId::from_bytes([45; 32]);
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeUnitMismatch)
    );
    invalid = resources.clone();
    invalid.unit_id = PracticeUnitId::from_bytes([0; 32]);
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeUnitMismatch)
    );
    invalid = resources.clone();
    invalid.period += 1;
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimePeriodMismatch)
    );
    invalid = resources.clone();
    invalid.capacities[0].owner = PracticeResourceOwner::ActorOrganization(
        ActorOrganizationId::from_bytes(101_u64.to_be_bytes()),
    );
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeCapacityScope)
    );
    invalid = resources;
    invalid.capacities[0].mode = PracticeResourceAllocationMode::ExclusiveAllOrNone;
    assert_eq!(
        finite_act(&config, &opening, &invalid),
        Err(OrganizerError::TimeCapacityScope)
    );
}

#[test]
pub(crate) fn finite_time_does_not_supply_partner_consent() {
    for policy in [
        OrganizerPartnerPolicy::Refuse,
        OrganizerPartnerPolicy::NoResponse,
    ] {
        let mut config = config();
        config.workplace_partner.policy = policy;
        let opening = babylon_practice_contract::initial_organizer_state(&config)
            .expect("the authored config admits an opening organizer state");
        let next = finite_act(&config, &opening, &finite_time(&config, 1))
            .expect("the fixture call `finite_act` succeeds for the authored inputs");
        let receipt = next
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty");
        assert_eq!(receipt.outcome, OrganizerOutcome::ContactUncompleted);
        assert_ne!(
            receipt.partner_response,
            OrganizerPartnerResponse::Participated
        );
        assert!(receipt.contact_product_id.is_none());
        assert_eq!(next.contact_products.len(), 0);
        assert_eq!(next.agreements, opening.agreements);
    }
}

#[test]
pub(crate) fn finite_time_rejects_changed_admitted_commitments() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &command(&config, &opening, OrganizerChoice::Reinforce),
    )
    .expect("the fixture admits the organizer actor");
    accepted.resolves_period += 1;
    let reduced =
        babylon_practice_contract::reduce_organizer_products(&config, &opening, &facts(1, 160))
            .expect("the organizer products aggregate");
    assert_eq!(
        resolve_organizer_practice_with_time(
            &config,
            &opening,
            &reduced,
            &facts(1, 160),
            Some(&accepted),
            &finite_time(&config, 1),
            babylon_practice_contract::OrganizerMaterialSupport {
                aid: &[],
                collection: None
            },
        ),
        Err(OrganizerError::InvalidCommitment)
    );
}

#[test]
pub(crate) fn finite_partner_shortage_keeps_all_own_time_and_produces_no_response_work() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut resources = finite_time(&config, 1);
    resources.capacities[1].available = 0;
    let next = finite_act(&config, &opening, &resources)
        .expect("the fixture call `finite_act` succeeds for the authored inputs");
    assert_no_time_product(&next);
    assert_eq!(
        next.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .partner_response,
        OrganizerPartnerResponse::UnableToParticipate
    );
    assert_eq!(next.agreements, opening.agreements);
}

#[test]
pub(crate) fn finite_named_fixed_control_uses_the_same_resolver_without_source_fallback() {
    let config = config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &command(&config, &opening, OrganizerChoice::Reinforce),
    )
    .expect("the fixture admits the organizer actor");
    let resources = babylon_practice_contract::organizer_fixed_time_resources(&config, 1).expect(
        "the fixture call `organizer_fixed_time_resources` succeeds for the authored inputs",
    );
    assert_eq!(resources.unit_id, organizer_time_unit_id());
    assert_eq!(
        babylon_practice_contract::resolve_organizer_period(
            &config,
            &opening,
            &facts(1, 160),
            Some(&accepted)
        ),
        babylon_practice_contract::resolve_organizer_period_with_time(
            &config,
            &opening,
            &facts(1, 160),
            Some(&accepted),
            &resources,
            babylon_practice_contract::OrganizerMaterialSupport {
                aid: &[],
                collection: None,
            }
        )
    );
}

#[test]
pub(crate) fn finite_one_contributor_can_fund_distinct_actor_uses_without_duplicating_supply() {
    let mut config = config();
    config.participants.remove(1);
    config.participants[0].commitments = vec![
        OrganizerContribution {
            actor_id: 101,
            hours: 14,
        },
        OrganizerContribution {
            actor_id: 102,
            hours: 2,
        },
    ];
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut resources = finite_time(&config, 1);
    resources.capacities[0].available = 10;
    let next = finite_act(&config, &opening, &resources)
        .expect("the fixture call `finite_act` succeeds for the authored inputs");
    assert_eq!(
        next.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .time_use,
        [
            OrganizerTimeUse {
                contributor_id: 201,
                actor_id: 101,
                hours: 8
            },
            OrganizerTimeUse {
                contributor_id: 201,
                actor_id: 102,
                hours: 2
            },
        ]
    );
    assert_eq!(
        next.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .outcome,
        OrganizerOutcome::ContactCompleted
    );
}

pub(crate) fn captured_household_config() -> OrganizerConfig {
    let mut captured = config();
    captured.time_binding = OrganizerTimeBindingMode::Household {
        bindings: captured
            .participants
            .iter()
            .map(|participant| OrganizerHouseholdBinding {
                contributor_id: participant.contributor_id,
                principal_id: [51; 32],
            })
            .collect(),
    };
    captured
}

#[test]
pub(crate) fn captured_time_binding_shared_households_roundtrip_and_change_identity() {
    let captured = captured_household_config();
    babylon_practice_contract::validate_organizer_config(&captured)
        .expect("the authored organizer config passes validation");
    let bytes = babylon_practice_contract::encode_organizer_config(&captured)
        .expect("the fixture value encodes to its canonical bytes");
    assert_eq!(
        babylon_practice_contract::decode_organizer_config(&bytes)
            .expect("the canonical bytes decode into the declared type"),
        captured
    );
    assert_ne!(
        bytes,
        babylon_practice_contract::encode_organizer_config(&config())
            .expect("the fixture value encodes to its canonical bytes")
    );
    let mut changed = captured.clone();
    let OrganizerTimeBindingMode::Household { bindings } = &mut changed.time_binding else {
        unreachable!()
    };
    bindings[1].principal_id = [52; 32];
    assert_ne!(
        bytes,
        babylon_practice_contract::encode_organizer_config(&changed)
            .expect("the fixture value encodes to its canonical bytes")
    );
}

#[test]
pub(crate) fn captured_time_binding_rejects_missing_duplicate_zero_and_unrostered_rows() {
    for kind in 0..6 {
        let mut captured = captured_household_config();
        let OrganizerTimeBindingMode::Household { bindings } = &mut captured.time_binding else {
            unreachable!()
        };
        match kind {
            0 => {
                bindings.pop();
            }
            1 => bindings[1].contributor_id = bindings[0].contributor_id,
            2 => bindings[0].principal_id = [0; 32],
            3 => bindings[0].contributor_id = 999,
            4 => bindings.reverse(),
            _ => bindings[0].contributor_id = 0,
        }
        assert_eq!(
            babylon_practice_contract::validate_organizer_config(&captured),
            Err(OrganizerError::TimeBindingMismatch)
        );
    }
}

#[test]
pub(crate) fn captured_time_binding_is_required_and_old_format_is_refused() {
    let captured = captured_household_config();
    let mut old_schema = captured.clone();
    old_schema.schema_version = 1;
    assert_eq!(
        babylon_practice_contract::validate_organizer_config(&old_schema),
        Err(OrganizerError::UnsupportedSchema)
    );
    let mut old_state = babylon_practice_contract::initial_organizer_state(&captured)
        .expect("the authored config admits an opening organizer state");
    old_state.schema_version = 1;
    assert_eq!(
        validate_organizer_state(&old_state),
        Err(OrganizerError::UnsupportedSchema)
    );
    let mut payload = serde_json::to_value(&captured).expect("the value serializes to JSON");
    payload
        .as_object_mut()
        .expect("the JSON fixture field is an object")
        .remove("time_binding");
    assert!(serde_json::from_value::<OrganizerConfig>(payload).is_err());
    let mut old_bytes = b"babylon.organizer-config.v1\0".to_vec();
    old_bytes.extend(
        serde_json::to_vec(&captured).expect("the value serializes to canonical JSON bytes"),
    );
    assert_eq!(
        babylon_practice_contract::decode_organizer_config(&old_bytes),
        Err(OrganizerError::Codec)
    );
}

#[test]
pub(crate) fn captured_time_binding_cannot_select_fixed_allowances() {
    let captured = captured_household_config();
    assert_eq!(
        babylon_practice_contract::organizer_fixed_time_resources(&captured, 1),
        Err(OrganizerError::TimeBindingMismatch)
    );
}

#[test]
pub(crate) fn captured_time_binding_preserves_shared_principal_budget_identity() {
    let mut captured = captured_household_config();
    let mut resources = shared_time(&config(), 10);
    let OrganizerTimeBindingMode::Household { bindings } = &mut captured.time_binding else {
        unreachable!()
    };
    bindings[2].principal_id = [52; 32];
    assert_eq!(
        finite_act(
            &captured,
            &babylon_practice_contract::initial_organizer_state(&captured)
                .expect("the authored config admits an opening organizer state"),
            &resources
        )
        .expect("the fixture call `finite_act` succeeds for the authored inputs")
        .journal
        .receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .outcome,
        OrganizerOutcome::ContactCompleted
    );
    resources = finite_time(&config(), 1);
    assert_eq!(
        finite_act(
            &captured,
            &babylon_practice_contract::initial_organizer_state(&captured)
                .expect("the authored config admits an opening organizer state"),
            &resources
        ),
        Err(OrganizerError::TimeBindingMismatch)
    );
    let mut distinct = captured.clone();
    let OrganizerTimeBindingMode::Household { bindings } = &mut distinct.time_binding else {
        unreachable!()
    };
    bindings[1].principal_id = [53; 32];
    let shared = shared_time(&config(), 10);
    assert_eq!(
        finite_act(
            &distinct,
            &babylon_practice_contract::initial_organizer_state(&distinct)
                .expect("the authored config admits an opening organizer state"),
            &shared
        ),
        Err(OrganizerError::TimeBindingMismatch)
    );
}

#[test]
pub(crate) fn long_horizon_organizer_view_bounds_reply_without_mutating_history_or_authority() {
    let config = config();
    let mut state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut journal = babylon_practice_contract::OrganizerPeriodJournal::empty();
    for period in 1..=325 {
        let resolved = babylon_practice_contract::resolve_organizer_period(
            &config,
            &state,
            &facts(period, 160),
            None,
        )
        .expect("the organizer period resolves");
        journal
            .append(resolved.journal)
            .expect("the resolved period extends the retained window");
        state = resolved.state;
    }
    assert_eq!(journal.periods.len(), 325);
    assert!(state.consumed_product_ids.len() > 8);
    assert!(state.contact_products.len() <= 1);
    let canonical =
        serde_json::to_vec(&state).expect("the value serializes to canonical JSON bytes");
    let command = command(&config, &state, OrganizerChoice::Hold);
    let accepted = babylon_practice_contract::admit_organizer(&config, &state, &command)
        .expect("the fixture admits the organizer actor");
    let view = babylon_practice_contract::organizer_view(
        &config,
        &state,
        &journal,
        config.controlled_actor_id,
    )
    .expect("the fixture call `organizer_view` succeeds for the authored inputs");
    assert_eq!(
        view.receipts.len(),
        8,
        "native snapshot carries a fixed recent window"
    );
    assert_eq!(
        view.receipts
            .first()
            .expect("the fixture sequence is non-empty")
            .period,
        318
    );
    assert_eq!(
        view.receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .period,
        325
    );
    let response = serde_json::json!({"organizer":{"view":view,"pending":null,"aid":[],"pending_aid":[],"aid_resolutions":[]}});
    assert_eq!(response["organizer"]["view"]["total_receipt_count"], 325);
    assert_eq!(
        response["organizer"]["view"]["total_observation_count"],
        journal
            .periods
            .iter()
            .flat_map(|entries| &entries.observations)
            .count()
    );
    assert!(
        serde_json::to_vec(&response)
            .expect("the value serializes to canonical JSON bytes")
            .len()
            < 65_536,
        "leave at least half of the 131072-byte frame for other fixed protocol fields"
    );
    assert_eq!(
        serde_json::to_vec(&state).expect("the value serializes to canonical JSON bytes"),
        canonical,
        "presentation never drops canonical history"
    );
    assert_eq!(
        babylon_practice_contract::admit_organizer(&config, &state, &command)
            .expect("the fixture admits the organizer actor"),
        accepted,
        "bounded presentation does not change command authorization"
    );
}

#[test]
pub(crate) fn recent_observations_preserve_latest_distinct_reports_and_complete_counts() {
    let mut config = config();
    config.initial_agreement_through_period = 1000;
    let initial = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut journal = babylon_practice_contract::OrganizerPeriodJournal::empty();
    let first = act(&config, &initial, OrganizerChoice::Hold, 160);
    journal
        .append(first.journal.clone())
        .expect("the resolved period extends the retained window");
    let mut state = first.state;
    let second = act(
        &config,
        &state,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
        0,
    );
    journal
        .append(second.journal.clone())
        .expect("the resolved period extends the retained window");
    state = second.state;
    let early = journal
        .periods
        .iter()
        .flat_map(|entries| &entries.observations)
        .filter(|row| !matches!(row.report, OrganizerReport::Maintenance { .. }))
        .map(|row| row.observation_id)
        .collect::<Vec<_>>();
    assert_ne!(early.len(), 0);
    for _ in 0..40 {
        let next = act(
            &config,
            &state,
            OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived),
            0,
        );
        journal
            .append(next.journal.clone())
            .expect("the resolved period extends the retained window");
        state = next.state;
    }
    let canonical =
        serde_json::to_vec(&state).expect("the value serializes to canonical JSON bytes");
    let view = babylon_practice_contract::organizer_view(
        &config,
        &state,
        &journal,
        config.controlled_actor_id,
    )
    .expect("the fixture call `organizer_view` succeeds for the authored inputs");
    assert!(
        journal
            .periods
            .iter()
            .flat_map(|entries| &entries.observations)
            .count()
            > 8
    );
    assert!(
        view.observations.len() <= 11,
        "eight recent reports plus at most three report kinds"
    );
    for id in early {
        assert!(
            view.observations.iter().any(|row| row.observation_id == id),
            "latest older report of a distinct kind must remain visible"
        );
    }
    assert!(view
        .observations
        .iter()
        .any(|row| row.acquired_period == state.period));
    assert_eq!(
        serde_json::to_value(&view).expect("the value serializes to JSON")
            ["total_observation_count"],
        journal
            .periods
            .iter()
            .flat_map(|entries| &entries.observations)
            .count()
    );
    assert_eq!(
        serde_json::to_vec(&state).expect("the value serializes to canonical JSON bytes"),
        canonical
    );
}

#[test]
pub(crate) fn organizer_view_refuses_unsupported_history_format_without_counts() {
    let config = config();
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let view = babylon_practice_contract::organizer_view(
        &config,
        &state,
        &babylon_practice_contract::OrganizerPeriodJournal::empty(),
        config.controlled_actor_id,
    )
    .expect("the fixture call `organizer_view` succeeds for the authored inputs");
    for field in ["total_observation_count", "total_receipt_count"] {
        let mut bytes = serde_json::to_value(&view).expect("the value serializes to JSON");
        bytes
            .as_object_mut()
            .expect("the JSON fixture field is an object")
            .remove(field);
        assert!(serde_json::from_value::<OrganizerView>(bytes).is_err());
    }
}

#[test]
pub(crate) fn captured_config_requires_explicit_nullable_collection_terms() {
    let value = serde_json::to_value(config()).expect("the value serializes to JSON");
    assert!(value
        .as_object()
        .expect("the JSON fixture field is an object")
        .contains_key("collection"));
    assert_eq!(value["collection"], serde_json::Value::Null);
}

#[test]
pub(crate) fn omitted_collection_terms_are_refused_not_inferred_from_aid() {
    let mut value = serde_json::to_value(config()).expect("the value serializes to JSON");
    value
        .as_object_mut()
        .expect("the JSON fixture field is an object")
        .remove("collection");
    assert!(serde_json::from_value::<OrganizerConfig>(value).is_err());
}

#[test]
pub(crate) fn partial_collection_epoch_refuses_previous_captures_and_roundtrips_current() {
    let captured = config();
    let opening = babylon_practice_contract::initial_organizer_state(&captured)
        .expect("the authored config admits an opening organizer state");
    assert_eq!(ORGANIZER_SCHEMA_VERSION, 8);
    let config_bytes = babylon_practice_contract::encode_organizer_config(&captured)
        .expect("the fixture value encodes to its canonical bytes");
    let state_bytes = babylon_practice_contract::encode_organizer_state(&opening)
        .expect("the fixture value encodes to its canonical bytes");
    assert!(config_bytes.starts_with(b"babylon.organizer-config.v7\0"));
    assert!(state_bytes.starts_with(b"babylon.organizer-state.v6\0"));
    assert_eq!(
        babylon_practice_contract::decode_organizer_config(&config_bytes)
            .expect("the canonical bytes decode into the declared type"),
        captured
    );
    assert_eq!(
        babylon_practice_contract::decode_organizer_state(&state_bytes)
            .expect("the canonical bytes decode into the declared type"),
        opening
    );
    let mut previous_config = captured.clone();
    previous_config.schema_version = 6;
    let mut previous_state = opening.clone();
    previous_state.schema_version = 6;
    let mut previous_config_bytes = b"babylon.organizer-config.v6\0".to_vec();
    previous_config_bytes.extend(
        serde_json::to_vec(&previous_config).expect("the value serializes to canonical JSON bytes"),
    );
    let mut previous_state_bytes = b"babylon.organizer-state.v4\0".to_vec();
    previous_state_bytes.extend(
        serde_json::to_vec(&previous_state).expect("the value serializes to canonical JSON bytes"),
    );
    assert_eq!(
        babylon_practice_contract::validate_organizer_config(&previous_config),
        Err(OrganizerError::UnsupportedSchema)
    );
    assert_eq!(
        validate_organizer_state(&previous_state),
        Err(OrganizerError::UnsupportedSchema)
    );
    assert_eq!(
        babylon_practice_contract::decode_organizer_config(&previous_config_bytes),
        Err(OrganizerError::Codec)
    );
    assert_eq!(
        babylon_practice_contract::decode_organizer_state(&previous_state_bytes),
        Err(OrganizerError::Codec)
    );
}
