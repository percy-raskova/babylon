//! Original native witnesses, configured identities and refused evidence.
use babylon_persistence::qualification_audit::aid::{Accepted, Audit, Refusal};
use babylon_persistence::runtime_session::{
    OrganizerAidKind, OrganizerChoice, OrganizerCommitment, OrganizerPreview, OrganizerSnapshot,
};

use babylon_practice_contract::OrganizerRefusal;
use sha2::{Digest, Sha256};

fn witness() -> (OrganizerSnapshot, OrganizerPreview, OrganizerCommitment) {
    let mut before: OrganizerSnapshot =
        serde_json::from_str(include_str!("fixtures/national_organizer_opening_v11.json")).unwrap();
    before.view.actor_id = 42;
    before.view.authority_id = [17; 16];
    before.view.available_hours = 7;
    before.view.resource_digest = babylon_practice_contract::organizer_resource_digest().unwrap();
    let local = before
        .aid
        .iter_mut()
        .find(|r| r.kind == OrganizerAidKind::Local)
        .unwrap();
    local.coordination_hours = 5;
    before
        .view
        .aid_options
        .iter_mut()
        .find(|r| r.kind == OrganizerAidKind::Local)
        .unwrap()
        .coordination_hours = 5;
    let command = babylon_practice_contract::OrganizerCommand {
        campaign_id: [9; 16],
        actor_id: 42,
        authority_id: [17; 16],
        expected_period: 0,
        content_digest: before.view.content_digest,
        resource_digest: before.view.resource_digest,
        nonce: [21; 16],
        choice: OrganizerChoice::LocalAid,
    };
    let mut bytes = b"babylon.organizer-commitment.v1\0".to_vec();
    bytes.extend_from_slice(&serde_json::to_vec(&command).unwrap());
    let commitment = OrganizerCommitment {
        command,
        resolves_period: 1,
        commitment_id: Sha256::digest(bytes).into(),
    };
    babylon_practice_contract::validate_organizer_commitment(&commitment).unwrap();
    let preview = OrganizerPreview {
        choice: OrganizerChoice::LocalAid,
        current_period: 0,
        resolves_period: 1,
        available_hours: 7,
        required_hours: 5,
        replaces_standing_work: true,
        refusal: None,
        observations: vec![],
    };
    (before, preview, commitment)
}

#[test]
fn original_aid_witness_requires_an_authenticated_opening() {
    let (before, preview, commitment) = witness();
    let accepted = Accepted::capture(&commitment, &preview, &before).unwrap();
    let mut audit = Audit::default();
    assert_eq!(audit.accept(accepted), Err(Refusal::OriginalOffer));
    assert_eq!(audit.report()["accepted_original_commands"], 0);
    assert_eq!(audit.practice_report()["status"], "incomplete");
}

#[test]
fn missing_or_changed_original_offer_cannot_be_replaced_by_later_facts() {
    let (mut before, preview, commitment) = witness();
    before.aid.retain(|r| r.kind != OrganizerAidKind::Local);
    assert_eq!(
        Accepted::capture(&commitment, &preview, &before),
        Err(Refusal::OriginalOffer)
    );
    let (mut before, preview, commitment) = witness();
    before.aid[0].coordination_hours += 1;
    assert_eq!(
        Accepted::capture(&commitment, &preview, &before),
        Err(Refusal::OriginalOffer)
    );
    let (before, mut preview, commitment) = witness();
    preview.current_period = 1;
    assert_eq!(
        Accepted::capture(&commitment, &preview, &before),
        Err(Refusal::Admission)
    );
}

#[test]
fn aid_witness_refuses_crossed_authority_refusal_and_conflicting_retry() {
    let (before, mut preview, commitment) = witness();
    preview.refusal = Some(OrganizerRefusal::AidReceivingRefused);
    assert_eq!(
        Accepted::capture(&commitment, &preview, &before),
        Err(Refusal::Admission)
    );
    let (mut before, preview, commitment) = witness();
    before.view.actor_id = 43;
    assert_eq!(
        Accepted::capture(&commitment, &preview, &before),
        Err(Refusal::Admission)
    );
    let (before, preview, commitment) = witness();
    let accepted = Accepted::capture(&commitment, &preview, &before).unwrap();
    let mut audit = Audit::default();
    assert_eq!(audit.accept(accepted), Err(Refusal::OriginalOffer));
    let mut changed = before;
    changed.aid[0].payer_cash += 1;
    assert_eq!(
        audit.accept(Accepted::capture(&commitment, &preview, &changed).unwrap()),
        Err(Refusal::OriginalOffer)
    );
    assert_eq!(audit.report()["accepted_original_commands"], 0);
}
