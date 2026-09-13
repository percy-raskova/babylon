use babylon_kernel::replay::ReplaySessionId;
use babylon_practice_contract::*;

fn config() -> OrganizerConfig {
    OrganizerConfig {
        schema_version: ORGANIZER_SCHEMA_VERSION,
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

fn facts(period: u64, labor: u64) -> OrganizerWorkplaceFacts {
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

fn command(
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
        resource_digest: organizer_resource_digest().unwrap(),
        nonce: [7; 16],
        choice,
    }
}

fn act(
    config: &OrganizerConfig,
    state: &OrganizerState,
    choice: OrganizerChoice,
    labor: u64,
) -> OrganizerState {
    let accepted = admit_organizer(config, state, &command(config, state, choice)).unwrap();
    resolve_organizer_period(
        config,
        state,
        &facts(state.period + 1, labor),
        Some(&accepted),
    )
    .unwrap()
}

#[test]
fn inquiry_uses_typed_practice_and_earns_a_finite_committed_report() {
    let config = config();
    let opening = initial_organizer_state(&config).unwrap();
    let first = act(&config, &opening, OrganizerChoice::Hold, 160);
    let second = act(&config, &first, OrganizerChoice::Hold, 0);
    let command = command(
        &config,
        &second,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
    );
    let commitment = admit_organizer(&config, &second, &command).unwrap();
    let intent = organizer_practice_intent(&config, &second, &commitment).unwrap();
    assert_eq!(intent.practice_id, PracticeId::Investigate);
    assert_eq!(
        decode_practice_intent(&encode_practice_intent(&intent).unwrap()).unwrap(),
        intent
    );
    let third =
        resolve_organizer_period(&config, &second, &facts(3, 160), Some(&commitment)).unwrap();
    let receipt = third.receipts.last().unwrap();
    assert_eq!(receipt.hours_spent, 12);
    assert_eq!(receipt.outcome, OrganizerOutcome::EvidenceObtained);
    let observed = third.observations.last().unwrap();
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
    assert_eq!(fourth.observations.last(), Some(observed));
    assert_eq!(fourth.receipts.last().unwrap().hours_spent, 8);
    assert!(fourth.standing.authorized);
}

#[test]
fn choices_create_different_real_work_without_altering_factory_facts() {
    let config = config();
    let initial = initial_organizer_state(&config).unwrap();
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
        .map(|state| state.receipts.last().unwrap())
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
            organizer_state_digest(&pair[0]).unwrap(),
            organizer_state_digest(&pair[1]).unwrap()
        );
    }
}

#[test]
fn contact_receipt_is_consumed_later_and_expired_relationship_can_recover() {
    let config = config();
    let mut state = initial_organizer_state(&config).unwrap();
    for _ in 0..3 {
        state = act(&config, &state, OrganizerChoice::Hold, 160);
    }
    state = act(&config, &state, OrganizerChoice::PauseStanding, 0);
    assert_eq!(
        state.observations.len(),
        0,
        "workplace report agreement expired after period 3"
    );
    state = act(&config, &state, OrganizerChoice::Reinforce, 160);
    let product = state.contact_products.last().unwrap().clone();
    let receipt = state.receipts.last().unwrap().clone();
    assert_eq!(receipt.outcome, OrganizerOutcome::ContactCompleted);
    assert!(!state.consumed_product_ids.contains(&product.product_id));
    assert_eq!(
        state
            .agreements
            .iter()
            .find(|row| row.partner_actor_id == 102)
            .unwrap()
            .valid_through_period,
        3
    );
    let next = act(&config, &state, OrganizerChoice::Hold, 0);
    assert!(next.consumed_product_ids.contains(&product.product_id));
    let agreement = next
        .agreements
        .iter()
        .find(|row| row.partner_actor_id == 102)
        .unwrap();
    assert_eq!(
        (agreement.valid_from_period, agreement.valid_through_period),
        (6, 7)
    );
    assert_eq!(next.observations.last().unwrap().observed_period, 6);
    assert!(
        !next.standing.authorized,
        "specific commitment does not undo explicit pause"
    );
}

#[test]
fn partner_refusal_and_capacity_do_not_override_ruling_or_create_contact_products() {
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
        let state = initial_organizer_state(&config).unwrap();
        let result = act(&config, &state, OrganizerChoice::Reinforce, 160);
        let receipt = result.receipts.last().unwrap();
        assert_eq!(receipt.choice, OrganizerChoice::Reinforce);
        assert_eq!(receipt.hours_spent, 8);
        assert_eq!(receipt.outcome, OrganizerOutcome::ContactUncompleted);
        assert_eq!(result.contact_products.len(), 0);
    }
}

#[test]
fn explicit_pause_persists_hold_does_not_resume_and_resume_performs_routine() {
    let config = config();
    let initial = initial_organizer_state(&config).unwrap();
    let paused = act(&config, &initial, OrganizerChoice::PauseStanding, 160);
    let held = act(&config, &paused, OrganizerChoice::Hold, 0);
    assert_eq!(held.receipts.last().unwrap().hours_spent, 0);
    assert!(!held.standing.authorized);
    let resumed = act(&config, &held, OrganizerChoice::ResumeStanding, 160);
    assert!(resumed.standing.authorized);
    assert_eq!(resumed.receipts.last().unwrap().hours_spent, 8);
    assert_eq!(resumed.receipts.last().unwrap().partner_actor_id, Some(103));
}

#[test]
fn missing_routine_time_pauses_and_failed_admission_preserves_authorization() {
    let mut config = config();
    config.participants[0].commitments[0].hours = 7;
    let state = initial_organizer_state(&config).unwrap();
    assert_eq!(
        admit_organizer(
            &config,
            &state,
            &command(&config, &state, OrganizerChoice::Reinforce)
        ),
        Err(OrganizerError::Refused(
            OrganizerRefusal::InsufficientCommittedTime
        ))
    );
    assert!(state.standing.authorized);
    let next = resolve_organizer_period(&config, &state, &facts(1, 160), None).unwrap();
    assert_eq!(
        next.standing.paused_reason,
        Some(OrganizerPauseReason::InsufficientCommittedTime)
    );
    assert_eq!(next.receipts.last().unwrap().hours_spent, 0);
}

#[test]
fn private_partner_policy_capacity_and_factory_facts_do_not_change_lawful_preview() {
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
    let initial = initial_organizer_state(&config).unwrap();
    let state = act(&config, &initial, OrganizerChoice::PauseStanding, 160);
    assert!(
        !state.observations.is_empty(),
        "the authorization test must have actual knowledge to withhold"
    );
    let command = command(
        &config,
        &state,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
    );
    let preview = preview_organizer(&config, &state, &command).unwrap();
    let view = organizer_view(&config, &state, config.controlled_actor_id).unwrap();
    let mut hidden = config.clone();
    hidden.workplace_partner.policy = OrganizerPartnerPolicy::Refuse;
    hidden.workplace_partner.permits_work_report = false;
    hidden.participants[1].available_hours = 999;
    hidden.participants[1].commitments[0].hours = 999;
    let mut hidden_state = state.clone();
    hidden_state
        .last_workplace_facts
        .as_mut()
        .unwrap()
        .output_kg = 12_345;
    assert_eq!(
        preview_organizer(&hidden, &hidden_state, &command).unwrap(),
        preview
    );
    assert_eq!(
        organizer_view(&hidden, &hidden_state, hidden.controlled_actor_id).unwrap(),
        view
    );
    let serialized = serde_json::to_string(&view).unwrap();
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
        let lawful = preview_organizer(&lawful_config, &state, &request).unwrap();
        let concealed = preview_organizer(&concealed_config, &hidden_state, &request).unwrap();
        assert_eq!(lawful.refusal, Some(refusal));
        assert_eq!(
            lawful, concealed,
            "safe refusal must not distinguish hidden state"
        );
        if refusal == OrganizerRefusal::WrongAuthority {
            assert_eq!((lawful.available_hours, lawful.required_hours), (0, 0));
            assert!(!lawful.replaces_standing_work);
            assert!(lawful.observations.is_empty());
        } else {
            assert_eq!(
                lawful.observations, state.observations,
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
fn command_authority_tick_and_contracts_are_bound_and_retry_is_identical() {
    let config = config();
    let state = initial_organizer_state(&config).unwrap();
    let valid = command(&config, &state, OrganizerChoice::Reinforce);
    let accepted = admit_organizer(&config, &state, &valid).unwrap();
    assert_eq!(admit_organizer(&config, &state, &valid).unwrap(), accepted);
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
            admit_organizer(&config, &state, &command),
            Err(OrganizerError::Refused(refusal))
        );
    }
    let mut forged = accepted.clone();
    forged.resolves_period = 3;
    assert_eq!(
        resolve_organizer_period(&config, &state, &facts(1, 160), Some(&forged)),
        Err(OrganizerError::InvalidCommitment)
    );
    assert_eq!(state.period, 0);
}

#[test]
fn shared_contributors_cannot_promise_or_spend_the_same_hours_twice() {
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
    let state = initial_organizer_state(&config).unwrap();
    let next = act(&config, &state, OrganizerChoice::Reinforce, 160);
    let usage = &next.receipts.last().unwrap().time_use;
    assert_eq!(usage.iter().map(|row| row.hours).sum::<u64>(), 10);
    assert!(usage.iter().all(|row| row.contributor_id == 201));
    config.participants[0].available_hours = 31;
    assert_eq!(
        validate_organizer_config(&config),
        Err(OrganizerError::InvalidConfig)
    );
}

#[test]
fn restart_canonical_roundtrip_and_action_batch_are_deterministic() {
    let config = config();
    let initial = initial_organizer_state(&config).unwrap();
    let config = decode_organizer_config(&encode_organizer_config(&config).unwrap()).unwrap();
    let accepted = admit_organizer(
        &config,
        &initial,
        &command(&config, &initial, OrganizerChoice::Reinforce),
    )
    .unwrap();
    let batch = organizer_action_batch(
        &config,
        &initial,
        Some(&accepted),
        ReplaySessionId::try_from("organizer-replay").unwrap(),
    )
    .unwrap();
    assert_eq!(
        batch.items().len(),
        2,
        "player and independent participating response share canonical input rail"
    );
    let first =
        resolve_organizer_period(&config, &initial, &facts(1, 160), Some(&accepted)).unwrap();
    let restarted = decode_organizer_state(&encode_organizer_state(&first).unwrap()).unwrap();
    let second = resolve_organizer_period(&config, &first, &facts(2, 0), None).unwrap();
    assert_eq!(
        resolve_organizer_period(&config, &restarted, &facts(2, 0), None).unwrap(),
        second
    );
    assert_eq!(
        resolve_organizer_period(&config, &initial, &facts(1, 160), Some(&accepted)).unwrap(),
        first
    );
    let mut bytes = encode_organizer_state(&first).unwrap();
    bytes.push(b' ');
    assert_eq!(
        decode_organizer_state(&bytes),
        Err(OrganizerError::NonCanonical)
    );
    let mut invalid = first.clone();
    invalid.schema_version = 0;
    assert_eq!(
        encode_organizer_state(&invalid),
        Err(OrganizerError::UnsupportedSchema)
    );
}

#[test]
fn changing_actor_labels_and_authority_identifiers_creates_no_capacity_or_success_privilege() {
    let original = config();
    let mut renamed = original.clone();
    renamed.organization_label = "CPU organization".into();
    renamed.input_authority_id = [20; 16];
    let left = act(
        &original,
        &initial_organizer_state(&original).unwrap(),
        OrganizerChoice::Reinforce,
        160,
    );
    let right = act(
        &renamed,
        &initial_organizer_state(&renamed).unwrap(),
        OrganizerChoice::Reinforce,
        160,
    );
    let left = left.receipts.last().unwrap();
    let right = right.receipts.last().unwrap();
    assert_eq!(left.outcome, right.outcome);
    assert_eq!(left.hours_spent, right.hours_spent);
    assert_eq!(left.time_use, right.time_use);
    assert_eq!(left.partner_response, right.partner_response);
}

#[test]
fn severing_the_contact_consumer_removes_later_report_access_but_preserves_completed_work() {
    let config = config();
    let mut opening = initial_organizer_state(&config).unwrap();
    for _ in 0..2 {
        opening = act(&config, &opening, OrganizerChoice::Hold, 160);
    }
    opening = act(&config, &opening, OrganizerChoice::Reinforce, 160);
    let contact_receipt = opening.receipts.last().unwrap().clone();
    let completed = facts(4, 0);
    let connected = reduce_organizer_products(&config, &opening, &completed).unwrap();
    let disconnected = report_organizer_workplace(&config, &opening, &opening, &completed).unwrap();
    assert_eq!(connected.receipts.last(), Some(&contact_receipt));
    assert_eq!(disconnected.receipts.last(), Some(&contact_receipt));
    assert_eq!(connected.contact_products, disconnected.contact_products);
    assert!(connected
        .agreements
        .iter()
        .any(|row| row.partner_actor_id == 102 && row.valid_through_period >= 4));
    assert!(!disconnected
        .agreements
        .iter()
        .any(|row| row.partner_actor_id == 102 && row.valid_through_period >= 4));
    assert_eq!(connected.observations.len(), 1);
    assert_eq!(disconnected.observations.len(), 0);
}

#[test]
fn receipt_codec_rejects_noncanonical_unknown_and_false_conservation_claims() {
    let config = config();
    let state = act(
        &config,
        &initial_organizer_state(&config).unwrap(),
        OrganizerChoice::Reinforce,
        160,
    );
    let receipt = state.receipts.last().unwrap();
    let bytes = encode_organizer_receipt(receipt).unwrap();
    assert_eq!(decode_organizer_receipt(&bytes).unwrap(), *receipt);
    let mut bad = receipt.clone();
    bad.hours_spent += 1;
    assert_eq!(
        encode_organizer_receipt(&bad),
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
fn inquiry_question_bytes_change_intent_identity_and_other_parameters_remain_closed() {
    let config = config();
    let state = initial_organizer_state(&config).unwrap();
    let intent = |question| {
        let accepted = admit_organizer(
            &config,
            &state,
            &command(&config, &state, OrganizerChoice::Inquiry(question)),
        )
        .unwrap();
        organizer_practice_intent(&config, &state, &accepted).unwrap()
    };
    let work = intent(OrganizerInquiry::WorkLost);
    let maintenance = intent(OrganizerInquiry::MaintenanceReceived);
    assert_ne!(
        practice_intent_digest(&work).unwrap(),
        practice_intent_digest(&maintenance).unwrap()
    );
    assert_ne!(
        practice_parameter_bytes_digest(&work).unwrap(),
        practice_parameter_bytes_digest(&maintenance).unwrap()
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
fn every_accepted_control_and_nonce_binds_distinct_canonical_input() {
    let config = config();
    let paused = act(
        &config,
        &initial_organizer_state(&config).unwrap(),
        OrganizerChoice::PauseStanding,
        160,
    );
    let session = ReplaySessionId::try_from("organizer-controls").unwrap();
    let make = |choice, nonce| {
        let mut command = command(&config, &paused, choice);
        command.nonce = nonce;
        let accepted = admit_organizer(&config, &paused, &command).unwrap();
        let batch =
            organizer_action_batch(&config, &paused, Some(&accepted), session.clone()).unwrap();
        let outcome =
            resolve_organizer_period(&config, &paused, &facts(2, 0), Some(&accepted)).unwrap();
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
        assert_eq!(state.receipts.last().unwrap().hours_spent, 0);
        assert_eq!(
            state.receipts.last().unwrap().partner_response,
            OrganizerPartnerResponse::NotRequested
        );
    }
}

#[test]
fn completed_contact_product_cannot_be_retargeted_to_a_different_partner() {
    let config = config();
    let mut state = act(
        &config,
        &initial_organizer_state(&config).unwrap(),
        OrganizerChoice::Hold,
        160,
    );
    assert_eq!(
        state.contact_products[0].partner_actor_id,
        config.neighborhood_partner.actor_id
    );
    state.contact_products[0].partner_actor_id = config.workplace_partner.actor_id;
    assert!(matches!(
        encode_organizer_state(&state),
        Err(OrganizerError::InvalidState)
    ));
}

#[test]
fn commitment_identity_remains_valid_after_resolution_but_rejects_forgery() {
    let config = config();
    let state = initial_organizer_state(&config).unwrap();
    let accepted = admit_organizer(
        &config,
        &state,
        &command(&config, &state, OrganizerChoice::Reinforce),
    )
    .unwrap();
    let next = resolve_organizer_period(&config, &state, &facts(1, 160), Some(&accepted)).unwrap();
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
fn paired_checkpoint_validation_rejects_foreign_workplace_binding() {
    let config = config();
    let state = act(
        &config,
        &initial_organizer_state(&config).unwrap(),
        OrganizerChoice::Hold,
        160,
    );
    let mut foreign_config = config.clone();
    foreign_config.workplace_id = 1004;
    assert_eq!(validate_organizer_config(&foreign_config), Ok(()));
    assert_eq!(validate_organizer_state(&state), Ok(()));
    assert_eq!(
        validate_organizer_pair(&foreign_config, &state),
        Err(OrganizerError::InvalidState)
    );
}

#[test]
fn explicit_hold_cannot_alias_standing_work_even_with_the_same_nonce() {
    let config = config();
    let state = initial_organizer_state(&config).unwrap();
    let session = ReplaySessionId::try_from("organizer-origin").unwrap();
    let routine = organizer_action_batch(&config, &state, None, session.clone()).unwrap();
    let routine_own = routine
        .items()
        .iter()
        .find(|row| {
            row.intent().actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes()
        })
        .unwrap();
    let mut command = command(&config, &state, OrganizerChoice::Hold);
    command.nonce = routine_own.intent().proposal_nonce.as_bytes();
    let accepted = admit_organizer(&config, &state, &command).unwrap();
    let explicit = organizer_action_batch(&config, &state, Some(&accepted), session).unwrap();
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
            .unwrap()
            .intent()
            .proposal_nonce
            .as_bytes()
    };
    assert_ne!(
        partner(&routine),
        partner(&explicit),
        "partner response identity is bound to originating practice"
    );
    let routine_result = resolve_organizer_period(&config, &state, &facts(1, 160), None).unwrap();
    let explicit_result =
        resolve_organizer_period(&config, &state, &facts(1, 160), Some(&accepted)).unwrap();
    assert_eq!(
        routine_result.receipts.last().unwrap().hours_spent,
        explicit_result.receipts.last().unwrap().hours_spent
    );
    assert_eq!(
        routine_result.receipts.last().unwrap().outcome,
        explicit_result.receipts.last().unwrap().outcome
    );
}

#[test]
fn player_and_policy_authority_bindings_grant_no_shared_contact_time_privilege() {
    let mut config = config();
    let mut shared = config.participants.remove(0);
    for participant in config.participants.drain(..) {
        shared.available_hours += participant.available_hours;
        shared.commitments.extend(participant.commitments);
    }
    config.participants.push(shared);
    let state = initial_organizer_state(&config).unwrap();
    let accepted = admit_organizer(
        &config,
        &state,
        &command(&config, &state, OrganizerChoice::Reinforce),
    )
    .unwrap();
    let batch = organizer_resolved_action_batch(&config, &state, Some(&accepted)).unwrap();
    let ledger = organizer_input_authority_ledger(&config).unwrap();
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
        input_authority_ledger_digest(&exchanged_ledger).unwrap();
    for item in &mut exchanged_batch.items {
        item.authority = exchanged_ledger
            .rows
            .iter()
            .find(|row| row.input_authority_id == item.intent.input_authority_id)
            .unwrap()
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
    let actual =
        resolve_organizer_period(&config, &state, &facts(1, 160), Some(&accepted)).unwrap();
    let receipt = actual.receipts.last().unwrap();
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

fn shared_contact_allocation(
    config: &OrganizerConfig,
    ledger: &PracticeInputAuthorityLedger,
    batch: &ResolvedPracticeBatch,
    available: u64,
) -> PracticeResourceAllocationOutcome {
    validate_resolved_practice_batch(batch, ledger).unwrap();
    let projected = OrderedPracticeActionBatch::project(
        ReplaySessionId::try_from("organizer-controller-neutrality").unwrap(),
        batch,
        ledger,
    )
    .unwrap();
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
            derive_practice_resource_request(
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
            .unwrap()
        })
        .collect::<Vec<_>>();
    allocate_practice_resources(
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
    .unwrap()
}
