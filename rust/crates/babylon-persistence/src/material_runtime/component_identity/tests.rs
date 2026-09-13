use super::*;

fn identity() -> MaterialComponentIdentity {
    MaterialComponentIdentity::from_parts(
        b"resolver",
        b"environment",
        &ReplaySessionId::try_from("fixture/component-identity").unwrap(),
        ReplaySeed::new(7),
        &ContentDigest {
            defines_hash: [3; 32],
            rules_hash: [4; 32],
        },
        RefDigest::from_bytes([5; 32]),
    )
}

#[test]
fn every_immutable_checkpoint_section_is_exact_and_mandatory() {
    let expected = identity();
    let mut sections = vec![Vec::new(); 9];
    sections[2..8].clone_from_slice(&expected.sections);
    expected.validate_sections(&sections).unwrap();
    for tag in 2..8 {
        let mut altered = sections.clone();
        altered[tag][0] ^= 1;
        assert!(matches!(
            expected.validate_sections(&altered),
            Err(MaterialRuntimeError::InvalidCheckpoint)
        ));
    }
    sections.pop();
    assert!(matches!(
        expected.validate_sections(&sections),
        Err(MaterialRuntimeError::InvalidCheckpoint)
    ));
}

#[test]
fn empty_actions_bind_exact_session_tick_layout_digest_and_bytes() {
    let expected = identity();
    let actions = OrderedPracticeActionBatch::empty(expected.session_id.clone(), 3).unwrap();
    expected
        .validate_actions(
            3,
            1,
            actions.digest().as_bytes(),
            actions.canonical_bytes(),
            None,
        )
        .unwrap();
    let foreign = OrderedPracticeActionBatch::empty(
        ReplaySessionId::try_from("fixture/foreign-session").unwrap(),
        3,
    )
    .unwrap();
    for (tick, layout, digest, bytes) in [
        (
            4,
            1,
            actions.digest().as_bytes().as_slice(),
            actions.canonical_bytes(),
        ),
        (
            3,
            2,
            actions.digest().as_bytes().as_slice(),
            actions.canonical_bytes(),
        ),
        (
            3,
            1,
            foreign.digest().as_bytes().as_slice(),
            foreign.canonical_bytes(),
        ),
        (
            3,
            1,
            foreign.digest().as_bytes().as_slice(),
            actions.canonical_bytes(),
        ),
        (
            3,
            1,
            actions.digest().as_bytes().as_slice(),
            foreign.canonical_bytes(),
        ),
    ] {
        assert!(matches!(
            expected.validate_actions(tick, layout, digest, bytes, None),
            Err(MaterialRuntimeError::InvalidCheckpoint)
        ));
    }
}

#[test]
fn captured_foundation_and_live_session_have_identical_component_admission() {
    let foundation = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let retained = MaterialComponentIdentity::from_foundation(foundation.graph_foundation());
    let session = foundation.into_session().unwrap();
    assert_eq!(
        retained,
        MaterialComponentIdentity::from_session(session.graph_session())
    );
}

#[test]
fn organizer_actions_require_the_exact_authorized_batch_on_restart() {
    let expected = identity();
    let defines = crate::michigan_defines::MichiganDefines::parse(include_str!(
        "../../../../../../content/scenarios/michigan/defines.toml"
    ))
    .unwrap();
    let config = crate::organizer_content::config(
        crate::identity::CampaignId::from_uuid(uuid::Uuid::from_u128(26163)),
        &defines.organizer,
        [7; 32],
    )
    .unwrap();
    let state = babylon_practice_contract::initial_organizer_state(&config).unwrap();
    let actions = babylon_practice_contract::organizer_action_batch(
        &config,
        &state,
        None,
        expected.session_id.clone(),
    )
    .unwrap();
    assert!(!actions.is_empty());
    assert!(expected
        .validate_actions(
            1,
            1,
            actions.digest().as_bytes(),
            actions.canonical_bytes(),
            None
        )
        .is_err());
    expected
        .validate_actions(
            1,
            1,
            actions.digest().as_bytes(),
            actions.canonical_bytes(),
            Some(&actions),
        )
        .unwrap();
    let mut altered = actions.canonical_bytes().to_vec();
    *altered.last_mut().unwrap() ^= 1;
    assert!(expected
        .validate_actions(1, 1, actions.digest().as_bytes(), &altered, Some(&actions))
        .is_err());
}
