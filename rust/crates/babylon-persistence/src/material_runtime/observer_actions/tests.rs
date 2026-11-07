use super::cursor;
use super::cursor::reconstruct;
use crate::organizer_aid_fixture as fixture;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::content_digest;
use babylon_kernel::replay::ReplaySessionId;
use babylon_practice_contract::OrganizerAllocation;
use babylon_practice_contract::PracticeId;
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

fn collection_session() -> Session {
    use babylon_material_circuit::AccountId;
    use babylon_practice_contract::{OrganizerCollectionMandate, OrganizerGiftConsent};
    let base = authored(false);
    let mut config = fixture::config();
    let mandate = &base.catalog().aid_mandates[0];
    let AccountId::Organization(account) = mandate.payer else {
        panic!("organization payer")
    };
    config.collection = Some(OrganizerCollectionMandate {
        mandate_id: [93; 32],
        source_hash: [94; 32],
        actor_id: config.controlled_actor_id,
        contributor_id: mandate.donor_contributor_id,
        household_principal_id: mandate.donor.as_bytes(),
        organization_account_id: account.as_bytes(),
        social_class_target: config.aid_bindings[0].social_class_target,
        labor_unit_id: mandate.labor_unit_id.as_bytes(),
        cash_consent: OrganizerGiftConsent::Accept,
        initial_cash_micros: 2,
        maximum_cash_micros: 8,
        protected_cash_floor_micros: 0,
        collection_hours: 2,
    });
    fixture::try_session(
        crate::michigan_dynamic_hex_foundation().expect("foundation"),
        &format!(
            "{}\n{}\n{}",
            fixture::MATERIAL,
            fixture::PRODUCTS,
            fixture::PRACTICE
        ),
        fixture::Materials {
            catalog: base.catalog().clone().into_definition(),
            state: base.material().state().clone(),
        },
        config,
    )
    .expect("collection session")
}

#[test]
fn collection_restart_reconstructs_selected_target_only_from_the_original_resolution() {
    use babylon_practice_contract::OrganizerAllocation;
    let mut session = collection_session();
    let config = session
        .material()
        .organizer_config()
        .expect("config")
        .clone();
    let prior = session
        .material()
        .organizer_state()
        .expect("organizer")
        .clone();
    let mut command = fixture::commitment(&session, OrganizerChoice::Collect).command;
    command.allocation = OrganizerAllocation::Collection {
        target_cash_micros: 2,
    };
    let accepted = babylon_practice_contract::admit_organizer(&config, &prior, &command)
        .expect("selected target");
    let identity = session.graph_session().session_identity().clone();
    let batch = babylon_practice_contract::organizer_action_batch(
        &config,
        &prior,
        Some(&accepted),
        identity.clone(),
    )
    .expect("selected action");
    let candidate = fixture::prepare(&session, Some(&accepted));
    fixture::commit(&mut session, &mut CollectingSink::default(), candidate);
    let current = session.material().organizer_state().expect("organizer");
    let journal = session.material().organizer_journal().expect("journal");
    assert_eq!(
        reconstruct(
            &config,
            &prior,
            current,
            journal,
            &identity,
            1,
            batch.canonical_bytes()
        )
        .expect("exact reconstruction"),
        batch
    );
    let mut missing = journal.clone();
    missing.periods[0].collection_receipts.clear();
    assert!(reconstruct(
        &config,
        &prior,
        current,
        &missing,
        &identity,
        1,
        batch.canonical_bytes()
    )
    .is_err());
    let mut changed = journal.clone();
    changed.periods[0].collection_receipts[0]
        .commitment
        .command
        .allocation = OrganizerAllocation::Collection {
        target_cash_micros: 8,
    };
    assert!(reconstruct(
        &config,
        &prior,
        current,
        &changed,
        &identity,
        1,
        batch.canonical_bytes()
    )
    .is_err());
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
    let commitment = fixture::commitment_with_allocation(
        &session,
        OrganizerChoice::LocalAid,
        OrganizerAllocation::Aid {
            food_quantity: 0,
            cash_micros: 5,
        },
    );
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
    assert_eq!(
        intents.len(),
        2,
        "only the fresh inquiry and its independent partner response are consumed"
    );
    let controlled = intents
        .iter()
        .find(|row| row.actor_org_id.to_bytes() == config.controlled_actor_id.to_be_bytes())
        .expect("fresh controlled inquiry");
    assert_eq!(controlled.proposal_nonce.as_bytes(), [8; 16]);
    assert!(
        intents
            .iter()
            .all(|row| row.practice_id != PracticeId::MutualAid),
        "later food creates no retimed Aid input"
    );
    let partner = intents
        .iter()
        .find(|row| row.actor_org_id != controlled.actor_org_id)
        .expect("fresh inquiry response");
    assert_eq!(
        partner.actor_org_id.to_bytes(),
        config.workplace_partner.actor_id.to_be_bytes()
    );
    assert_eq!(
        partner.input_authority_id.as_bytes(),
        config.workplace_partner.authority_id
    );
    assert_ne!(partner.proposal_nonce, controlled.proposal_nonce);
    let mut injected = intents.clone();
    let mut replayed = controlled.clone();
    replayed.proposal_nonce = ProposalNonce::from_bytes([7; 16]);
    injected.push(replayed);
    assert!(
        reconstruct(
            config,
            prior,
            current,
            journal,
            identity,
            tick,
            &encoded(identity, tick, &injected)
        )
        .is_err(),
        "an extra retimed input is refused"
    );
    assert!(
        reconstruct(
            config,
            prior,
            current,
            journal,
            identity,
            tick,
            &encoded(identity, tick, &[])
        )
        .is_err(),
        "the fresh inquiry remains required"
    );
}
