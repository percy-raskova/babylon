use super::cursor;
use super::cursor::reconstruct;
use crate::organizer_aid_fixture as fixture;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::content_digest;
use babylon_kernel::replay::ReplaySessionId;
use babylon_practice_contract::{
    InputAuthorityId, OrganizerAidKind, OrganizerChoice, OrganizerInquiry, ProposalNonce,
};
use babylon_practice_contract::{
    OrganizerConfig, OrganizerPeriodJournal, OrganizerPeriodJournalEntries, OrganizerState,
    PracticeIntent, ORDERED_PRACTICE_ACTION_BATCH_DOMAIN_BYTES,
};
use fixture::Session;

fn authored(routed: bool) -> Session {
    let mut config = fixture::config();
    if routed {
        config.aid_bindings[0].kind = OrganizerAidKind::Remote;
        config.aid_bindings[0].coordination_hours = 1;
    }
    fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().expect("the Michigan hex foundation builds"),
        config,
        false,
        routed,
    )
}

fn verify_advance(session: &mut Session, choice: Option<OrganizerChoice>) {
    let config = session
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config")
        .clone();
    let prior = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state")
        .clone();
    let identity = session.graph_session().session_identity().clone();
    let accepted = choice.map(|choice| {
        let mut command = fixture::commitment(session, choice).command;
        command.nonce =
            [u8::try_from(prior.period + 7).expect("the fixture value fits the target range"); 16];
        babylon_practice_contract::admit_organizer(&config, &prior, &command)
            .expect("the fixture admits the organizer actor")
    });
    let batch = babylon_practice_contract::organizer_action_batch(
        &config,
        &prior,
        accepted.as_ref(),
        identity.clone(),
    )
    .expect("the authored action batch builds");
    let candidate = fixture::prepare(session, accepted.as_ref());
    fixture::commit(session, &mut CollectingSink::default(), candidate);
    let current = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let journal = session
        .material()
        .organizer_journal()
        .expect("the fixture register carries organizer journal");
    let entries = journal.latest().expect("the fixture resolved one period");
    let tick = current.period;
    let bytes = batch.canonical_bytes();
    if prior.period == 1 && choice == Some(OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost)) {
        assert_mixed_batch(&config, &prior, current, journal, &identity, tick, bytes);
    }
    assert_eq!(
        reconstruct(&config, &prior, current, journal, &identity, tick, bytes)
            .expect("the fixture call `reconstruct` succeeds for the authored inputs"),
        batch
    );
    assert!(reconstruct(&config, current, current, journal, &identity, tick, bytes).is_err());
    let mut changed = entries.clone();
    let receipt = changed
        .receipts
        .iter_mut()
        .find(|row| row.period == tick && row.actor_id == config.controlled_actor_id)
        .expect("the fixture holds the searched element");
    receipt.choice = OrganizerChoice::PauseStanding;
    let changed = window(changed);
    assert!(reconstruct(&config, &prior, current, &changed, &identity, tick, bytes).is_err());
    let mut changed = entries.clone();
    changed
        .receipts
        .retain(|row| row.period != tick || row.actor_id != config.controlled_actor_id);
    let changed = window(changed);
    assert!(reconstruct(&config, &prior, current, &changed, &identity, tick, bytes).is_err());
    let mut changed = entries.clone();
    let receipt = changed
        .receipts
        .iter()
        .find(|row| row.period == tick && row.actor_id == config.controlled_actor_id)
        .expect("the fixture holds the searched element")
        .clone();
    changed.receipts.push(receipt);
    let changed = window(changed);
    assert!(reconstruct(&config, &prior, current, &changed, &identity, tick, bytes).is_err());
    assert!(reconstruct(
        &config,
        &prior,
        current,
        journal,
        &identity,
        tick,
        &bytes[..bytes.len() - 1]
    )
    .is_err());
    let mut trailing = bytes.to_vec();
    trailing.push(0);
    assert!(reconstruct(&config, &prior, current, journal, &identity, tick, &trailing).is_err());
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
    let config = session
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config");
    let prior = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let identity = session.graph_session().session_identity();
    let commitment = fixture::commitment(&session, OrganizerChoice::LocalAid);
    let batch = babylon_practice_contract::organizer_action_batch(
        config,
        prior,
        Some(&commitment),
        identity.clone(),
    )
    .expect("the authored action batch builds");
    let intents = cursor::parse(identity, batch.resolve_tick(), batch.canonical_bytes())
        .expect("the authored literal parses as the declared type");
    for field in 0..3 {
        let mut changed = intents.clone();
        let intent = changed
            .iter_mut()
            .find(|row| row.actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes())
            .expect("the fixture holds the searched element");
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
            actual
                .material()
                .organizer_state()
                .expect("the fixture register carries organizer state"),
            actual
                .material()
                .organizer_journal()
                .expect("the fixture register carries organizer journal"),
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
        actual
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state"),
        actual
            .material()
            .organizer_journal()
            .expect("the fixture register carries organizer journal"),
        identity,
        batch.resolve_tick(),
        &bytes
    )
    .is_err());
    assert!(reconstruct(
        config,
        prior,
        actual
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state"),
        actual
            .material()
            .organizer_journal()
            .expect("the fixture register carries organizer journal"),
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
    bytes.extend(
        session
            .canonical_bytes()
            .expect("the graph value exposes canonical bytes"),
    );
    bytes.extend(tick.to_be_bytes());
    bytes.extend(
        u16::try_from(intents.len())
            .expect("the fixture value fits the target range")
            .to_be_bytes(),
    );
    for (ordinal, intent) in intents.iter().enumerate() {
        bytes.extend(
            u16::try_from(ordinal)
                .expect("the fixture value fits the target range")
                .to_be_bytes(),
        );
        bytes.extend(content_digest::sha256_of(
            &babylon_practice_contract::encode_practice_action_id_preimage(session, intent)
                .expect("the fixture value encodes to its canonical bytes"),
        ));
        let value = babylon_practice_contract::encode_practice_intent(intent)
            .expect("the practice intent encodes canonically");
        bytes.extend(
            u16::try_from(value.len())
                .expect("the fixture value fits the target range")
                .to_be_bytes(),
        );
        bytes.extend(value);
    }
    bytes
}

fn window(entries: OrganizerPeriodJournalEntries) -> OrganizerPeriodJournal {
    OrganizerPeriodJournal {
        periods: vec![entries],
    }
}

fn assert_mixed_batch(
    config: &OrganizerConfig,
    prior: &OrganizerState,
    current: &OrganizerState,
    journal: &OrganizerPeriodJournal,
    identity: &ReplaySessionId,
    tick: u64,
    bytes: &[u8],
) {
    let intents = cursor::parse(identity, tick, bytes)
        .expect("the authored literal parses as the declared type");
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
        journal,
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
        .expect("the fixture sequence holds the addressed position");
    without_delayed.remove(delayed);
    assert!(reconstruct(
        config,
        prior,
        current,
        journal,
        identity,
        tick,
        &encoded(identity, tick, &without_delayed)
    )
    .is_err());
}
