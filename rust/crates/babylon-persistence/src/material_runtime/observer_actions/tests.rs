use super::*;
use crate::organizer_aid_fixture as fixture;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::{
    InputAuthorityId, OrganizerAidKind, OrganizerChoice, OrganizerInquiry, ProposalNonce,
};

fn authored(routed: bool) -> fixture::Session {
    let mut config = fixture::config();
    if routed {
        config.aid_bindings[0].kind = OrganizerAidKind::Remote;
        config.aid_bindings[0].coordination_hours = 1;
    }
    fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        config,
        false,
        routed,
    )
}

fn verify_advance(session: &mut fixture::Session, choice: Option<OrganizerChoice>) {
    let config = session.material().organizer_config().unwrap().clone();
    let prior = session.material().organizer_state().unwrap().clone();
    let identity = session.graph_session().session_identity().clone();
    let accepted = choice.map(|choice| {
        let mut command = fixture::commitment(session, choice).command;
        command.nonce = [u8::try_from(prior.period + 7).unwrap(); 16];
        admit_organizer(&config, &prior, &command).unwrap()
    });
    let batch =
        organizer_action_batch(&config, &prior, accepted.as_ref(), identity.clone()).unwrap();
    let candidate = fixture::prepare(session, accepted.as_ref());
    fixture::commit(session, &mut CollectingSink::default(), candidate);
    let current = session.material().organizer_state().unwrap();
    let tick = current.period;
    let bytes = batch.canonical_bytes();
    if prior.period == 1 && choice == Some(OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost)) {
        assert_mixed_batch(&config, &prior, current, &identity, tick, bytes);
    }
    assert_eq!(
        reconstruct(&config, &prior, current, &identity, tick, bytes).unwrap(),
        batch
    );
    assert!(reconstruct(&config, current, current, &identity, tick, bytes).is_err());
    let mut changed = current.clone();
    let receipt = changed
        .receipts
        .iter_mut()
        .find(|row| row.period == tick && row.actor_id == config.controlled_actor_id)
        .unwrap();
    receipt.choice = OrganizerChoice::PauseStanding;
    assert!(reconstruct(&config, &prior, &changed, &identity, tick, bytes).is_err());
    let mut changed = current.clone();
    changed
        .receipts
        .retain(|row| row.period != tick || row.actor_id != config.controlled_actor_id);
    assert!(reconstruct(&config, &prior, &changed, &identity, tick, bytes).is_err());
    let mut changed = current.clone();
    let receipt = changed
        .receipts
        .iter()
        .find(|row| row.period == tick && row.actor_id == config.controlled_actor_id)
        .unwrap()
        .clone();
    changed.receipts.push(receipt);
    assert!(reconstruct(&config, &prior, &changed, &identity, tick, bytes).is_err());
    assert!(reconstruct(
        &config,
        &prior,
        current,
        &identity,
        tick,
        &bytes[..bytes.len() - 1]
    )
    .is_err());
    let mut trailing = bytes.to_vec();
    trailing.push(0);
    assert!(reconstruct(&config, &prior, current, &identity, tick, &trailing).is_err());
}

#[test]
fn observer_local_accepted_and_standing_batches_are_exact() {
    let mut session = authored(false);
    verify_advance(&mut session, Some(OrganizerChoice::LocalAid));
    verify_advance(&mut session, None);
}

#[test]
fn observer_routed_delayed_and_fresh_batches_are_exact() {
    let mut session = authored(true);
    verify_advance(&mut session, Some(OrganizerChoice::RemoteAid));
    verify_advance(
        &mut session,
        Some(OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost)),
    );
    verify_advance(&mut session, None);
}

#[test]
fn observer_checked_action_identity_nonce_and_authority_refuse() {
    let session = authored(false);
    let config = session.material().organizer_config().unwrap();
    let prior = session.material().organizer_state().unwrap();
    let identity = session.graph_session().session_identity();
    let commitment = fixture::commitment(&session, OrganizerChoice::LocalAid);
    let batch = organizer_action_batch(config, prior, Some(&commitment), identity.clone()).unwrap();
    let intents = parse(identity, batch.resolve_tick(), batch.canonical_bytes()).unwrap();
    for field in 0..3 {
        let mut changed = intents.clone();
        let intent = changed
            .iter_mut()
            .find(|row| row.actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes())
            .unwrap();
        match field {
            0 => intent.proposal_nonce = ProposalNonce::from_bytes([99; 16]),
            1 => intent.input_authority_id = InputAuthorityId::from_bytes([99; 16]),
            _ => intent.quoted_content_digest = [99; 32],
        }
        let bytes = encoded(identity, batch.resolve_tick(), &changed);
        let candidate = fixture::prepare(&session, Some(&commitment));
        // Real close creates the current commitment witness; modified public intents must not match it.
        let mut actual = authored(false);
        fixture::commit(&mut actual, &mut CollectingSink::default(), candidate);
        assert!(reconstruct(
            config,
            prior,
            actual.material().organizer_state().unwrap(),
            identity,
            batch.resolve_tick(),
            &bytes
        )
        .is_err());
    }
    let mut duplicate = intents.clone();
    duplicate.extend(intents);
    let bytes = encoded(identity, batch.resolve_tick(), &duplicate);
    let candidate = fixture::prepare(&session, Some(&commitment));
    let mut actual = authored(false);
    fixture::commit(&mut actual, &mut CollectingSink::default(), candidate);
    assert!(reconstruct(
        config,
        prior,
        actual.material().organizer_state().unwrap(),
        identity,
        batch.resolve_tick(),
        &bytes
    )
    .is_err());
    assert!(reconstruct(
        config,
        prior,
        actual.material().organizer_state().unwrap(),
        identity,
        batch.resolve_tick(),
        &encoded(identity, batch.resolve_tick(), &[])
    )
    .is_err());
}

fn encoded(session: &ReplaySessionId, tick: u64, intents: &[PracticeIntent]) -> Vec<u8> {
    let mut bytes = ORDERED_PRACTICE_ACTION_BATCH_DOMAIN_BYTES.to_vec();
    bytes.push(0);
    bytes.extend(1_u16.to_be_bytes());
    bytes.extend(session.canonical_bytes().unwrap());
    bytes.extend(tick.to_be_bytes());
    bytes.extend(u16::try_from(intents.len()).unwrap().to_be_bytes());
    for (ordinal, intent) in intents.iter().enumerate() {
        bytes.extend(u16::try_from(ordinal).unwrap().to_be_bytes());
        bytes.extend(sha256_of(
            &encode_practice_action_id_preimage(session, intent).unwrap(),
        ));
        let value = encode_practice_intent(intent).unwrap();
        bytes.extend(u16::try_from(value.len()).unwrap().to_be_bytes());
        bytes.extend(value);
    }
    bytes
}

fn assert_mixed_batch(
    config: &OrganizerConfig,
    prior: &OrganizerState,
    current: &OrganizerState,
    identity: &ReplaySessionId,
    tick: u64,
    bytes: &[u8],
) {
    let intents = parse(identity, tick, bytes).unwrap();
    let controlled = |intent: &PracticeIntent| {
        intent.actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes()
    };
    assert!(intents.iter().filter(|row| controlled(row)).count() >= 2);
    assert!(intents.iter().any(|row| !controlled(row)));
    let without_partner: Vec<_> = intents
        .iter()
        .filter(|row| controlled(row))
        .cloned()
        .collect();
    assert!(reconstruct(
        config,
        prior,
        current,
        identity,
        tick,
        &encoded(identity, tick, &without_partner)
    )
    .is_err());
    // Keep fresh intent but omit the controlled delayed intent. No date-only match.
    let mut without_delayed = intents;
    let delayed = without_delayed
        .iter()
        .position(|row| controlled(row) && row.proposal_nonce.as_bytes() != [8; 16])
        .unwrap();
    without_delayed.remove(delayed);
    assert!(reconstruct(
        config,
        prior,
        current,
        identity,
        tick,
        &encoded(identity, tick, &without_delayed)
    )
    .is_err());
}
