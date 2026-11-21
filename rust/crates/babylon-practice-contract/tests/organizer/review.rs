use super::{aid, support};
use babylon_kernel::content_digest;
use babylon_practice_contract::{
    Band, OrganizerChoice, OrganizerCommand, OrganizerConfig, OrganizerError, OrganizerOutcome,
    OrganizerRefusal, OrganizerReviewConfig, OrganizerState, PositionKey, PracticeId,
    PracticeIntent, PracticeTargetTag, ResolvedOrganizerPeriod,
};

const KEY: PositionKey = PositionKey {
    group: 0,
    band: Band::Next40,
    crew: Some(0),
    at_work: 1,
    seeking: 0,
    units: 0,
};

fn captured_with_review() -> OrganizerConfig {
    let mut config = aid::captured();
    config.review = Some(OrganizerReviewConfig {
        county_geoid: "26163".into(),
        first_session_period: 4,
        county_config_digest: [9; 32],
    });
    config
}

fn at_period(period: u64) -> (OrganizerConfig, OrganizerState) {
    let config = captured_with_review();
    let mut state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the review campaign opens");
    state.period = period;
    (config, state)
}

fn command_for(
    config: &OrganizerConfig,
    state: &OrganizerState,
    choice: OrganizerChoice,
) -> OrganizerCommand {
    support::command(config, state, choice)
}

fn resolve(
    config: &OrganizerConfig,
    state: &OrganizerState,
    choice: OrganizerChoice,
    available: u64,
) -> ResolvedOrganizerPeriod {
    let commitment = babylon_practice_contract::admit_organizer(
        config,
        state,
        &command_for(config, state, choice),
    )
    .expect("the review contact is admitted");
    let mut time = aid::time(config, 201, available);
    time.period = state.period + 1;
    babylon_practice_contract::resolve_organizer_period_with_time(
        config,
        state,
        &support::facts(state.period + 1, 160),
        Some(&commitment),
        &time,
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[],
            collection: None,
        },
    )
    .expect("the review contact resolves")
}

fn intent_for(
    config: &OrganizerConfig,
    state: &OrganizerState,
    key: PositionKey,
) -> PracticeIntent {
    let commitment = babylon_practice_contract::admit_organizer(
        config,
        state,
        &command_for(config, state, OrganizerChoice::ReviewContact(key)),
    )
    .expect("the review contact is admitted");
    babylon_practice_contract::organizer_practice_intent(config, state, &commitment)
        .expect("the review contact has an intent")
}

#[test]
fn a_review_contact_costs_the_contact_hours_and_resolves_one_period_later() {
    let (config, state) = at_period(3);
    let command = command_for(&config, &state, OrganizerChoice::ReviewContact(KEY));
    let preview = babylon_practice_contract::preview_organizer(&config, &state, &command)
        .expect("the contact previews");
    assert_eq!(
        (
            preview.refusal,
            preview.required_hours,
            preview.resolves_period
        ),
        (None, config.contact_hours, 4)
    );
    let resolved = resolve(&config, &state, OrganizerChoice::ReviewContact(KEY), 16);
    let [receipt] = resolved.journal.receipts.as_slice() else {
        panic!("the contact replaces the standing routine, so one receipt is written");
    };
    assert_eq!(
        (receipt.choice, receipt.outcome, receipt.hours_spent),
        (
            OrganizerChoice::ReviewContact(KEY),
            OrganizerOutcome::ReviewContactMade,
            config.contact_hours
        )
    );
    assert_eq!(receipt.time_use.iter().map(|row| row.hours).sum::<u64>(), 8);
}

#[test]
fn a_review_contact_without_free_hours_is_insufficient_time() {
    let (config, state) = at_period(3);
    let resolved = resolve(&config, &state, OrganizerChoice::ReviewContact(KEY), 4);
    let [receipt] = resolved.journal.receipts.as_slice() else {
        panic!("one receipt");
    };
    assert_eq!(
        (receipt.outcome, receipt.hours_spent),
        (OrganizerOutcome::InsufficientTime, 0)
    );
}

#[test]
fn a_contact_that_would_land_before_the_first_session_is_refused() {
    let (config, state) = at_period(2);
    let preview = babylon_practice_contract::preview_organizer(
        &config,
        &state,
        &command_for(&config, &state, OrganizerChoice::ReviewContact(KEY)),
    )
    .expect("the contact previews");
    assert_eq!(preview.refusal, Some(OrganizerRefusal::ReviewUnavailable));
    assert_eq!(
        babylon_practice_contract::admit_organizer(
            &config,
            &state,
            &command_for(&config, &state, OrganizerChoice::ReviewContact(KEY)),
        ),
        Err(OrganizerError::Refused(OrganizerRefusal::ReviewUnavailable))
    );
}

#[test]
fn a_campaign_with_no_review_refuses_the_choice() {
    let config = aid::captured();
    assert!(config.review.is_none());
    let mut state =
        babylon_practice_contract::initial_organizer_state(&config).expect("the campaign opens");
    state.period = 5;
    let preview = babylon_practice_contract::preview_organizer(
        &config,
        &state,
        &command_for(&config, &state, OrganizerChoice::ReviewContact(KEY)),
    )
    .expect("the contact previews");
    assert_eq!(preview.refusal, Some(OrganizerRefusal::ReviewUnavailable));
}

#[test]
fn a_review_contact_intent_carries_control_parameter_nine() {
    let (config, state) = at_period(3);
    let intent = intent_for(&config, &state, KEY);
    assert_eq!(intent.practice_id, PracticeId::Organize);
    assert_eq!(intent.target.tag, PracticeTargetTag::Organization);
    let [parameter] = intent.parameters.as_slice() else {
        panic!("one control parameter");
    };
    assert_eq!(
        (
            parameter.key_u8,
            parameter.value_kind_u8,
            parameter.value_length_u16,
            parameter.value_bytes.as_slice()
        ),
        (2, 1, 1, [9u8].as_slice())
    );
    babylon_practice_contract::validate_practice_intent(&intent)
        .expect("control value nine is admitted");
}

#[test]
fn two_keys_give_two_target_ids() {
    let (config, state) = at_period(3);
    let other = PositionKey { units: 1, ..KEY };
    let first = intent_for(&config, &state, KEY).target.identity;
    assert_eq!(first, intent_for(&config, &state, KEY).target.identity);
    assert_ne!(first, intent_for(&config, &state, other).target.identity);
}

#[test]
fn the_target_id_hashes_the_domain_then_the_keys_sixteen_bytes() {
    let (config, state) = at_period(3);
    let key = PositionKey {
        group: 0x0102_0304,
        band: Band::Top1,
        crew: Some(0x0506_0708),
        at_work: 0x090a,
        seeking: 0x0b0c,
        units: 0x0d0e,
    };
    let mut bytes = b"babylon.organizer-review-position.v1".to_vec();
    bytes.extend_from_slice(&[1, 2, 3, 4, 3, 1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]);
    assert_eq!(
        intent_for(&config, &state, key).target.identity.as_bytes(),
        content_digest::sha256_of(&bytes)
    );
    let none = PositionKey {
        crew: None,
        band: Band::Bottom50,
        ..key
    };
    let mut bytes = b"babylon.organizer-review-position.v1".to_vec();
    bytes.extend_from_slice(&[1, 2, 3, 4, 0, 0, 0, 0, 0, 0, 9, 10, 11, 12, 13, 14]);
    assert_eq!(
        intent_for(&config, &state, none).target.identity.as_bytes(),
        content_digest::sha256_of(&bytes)
    );
}

#[test]
fn a_review_contact_replaces_the_standing_routine() {
    let (config, state) = at_period(3);
    assert!(state.standing.authorized);
    let preview = babylon_practice_contract::preview_organizer(
        &config,
        &state,
        &command_for(&config, &state, OrganizerChoice::ReviewContact(KEY)),
    )
    .expect("the contact previews");
    assert!(preview.replaces_standing_work);
    let resolved = resolve(&config, &state, OrganizerChoice::ReviewContact(KEY), 16);
    assert_eq!(resolved.journal.receipts.len(), 1);
    assert!(resolved.state.standing.authorized);
}

#[test]
fn a_review_contact_made_on_another_choice_is_refused() {
    let (config, state) = at_period(3);
    let resolved = resolve(&config, &state, OrganizerChoice::ReviewContact(KEY), 16);
    let mut receipt = resolved.journal.receipts[0].clone();
    babylon_practice_contract::validate_organizer_receipt(&receipt)
        .expect("the genuine receipt validates");
    receipt.choice = OrganizerChoice::Hold;
    assert_eq!(
        babylon_practice_contract::validate_organizer_receipt(&receipt),
        Err(OrganizerError::InvalidState)
    );
}
