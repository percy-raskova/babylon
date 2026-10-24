//! Captured opening terms with Designed pending-status interventions.
use babylon_persistence::runtime_session::OrganizerAidPending;
use babylon_persistence::runtime_session::{OrganizerAidKind, OrganizerSnapshot};

fn opening() -> OrganizerSnapshot {
    serde_json::from_str(include_str!(
        "../fixtures/national_organizer_opening_v11.json"
    ))
    .unwrap()
}

fn remote_in_transit() -> OrganizerSnapshot {
    let mut snapshot = opening();
    snapshot.view.period = 1;
    for preview in &mut snapshot.aid {
        preview.period = 1;
        if let Some(time) = &mut preview.time {
            time.period = 1;
        }
    }
    let remote = snapshot
        .aid
        .iter()
        .find(|row| row.kind == OrganizerAidKind::Remote)
        .unwrap();
    snapshot.pending_aid.push(OrganizerAidPending {
        kind: remote.kind,
        original_commitment_id: [10; 32],
        material_commitment_id: babylon_material_circuit::aid_commitment_id(remote.mandate_id, 1)
            .as_bytes(),
        mandate_id: remote.mandate_id,
        admitted_period: 0,
        dispatch_period: 1,
        good_id: remote.good_id,
        unit_id: remote.unit_id,
    });
    snapshot
        .view
        .aid_options
        .retain(|row| row.kind != OrganizerAidKind::Remote);
    snapshot
}

#[test]
fn opening_requires_both_reviewable_options() {
    super::verify_offers(&opening());
}

#[test]
fn pending_remote_keeps_material_terms_without_a_second_actionable_offer() {
    super::verify_offers(&remote_in_transit());
}

#[test]
fn missing_offer_without_pending_is_refused() {
    let mut snapshot = opening();
    snapshot.view.aid_options.pop();
    assert!(std::panic::catch_unwind(|| super::verify_offers(&snapshot)).is_err());
}

#[test]
fn changed_pending_identity_and_duplicate_action_are_refused() {
    let mut wrong_identity = remote_in_transit();
    wrong_identity.pending_aid[0].mandate_id = [99; 32];
    assert!(std::panic::catch_unwind(|| super::verify_offers(&wrong_identity)).is_err());
    let mut duplicate = remote_in_transit();
    duplicate.pending_aid.push(duplicate.pending_aid[0].clone());
    assert!(std::panic::catch_unwind(|| super::verify_offers(&duplicate)).is_err());
    let mut actionable = remote_in_transit();
    actionable.view.aid_options = opening().view.aid_options;
    assert!(std::panic::catch_unwind(|| super::verify_offers(&actionable)).is_err());
}

#[test]
fn captured_pending_boundary_retains_both_terms_and_only_the_local_action() {
    let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
        "../fixtures/national_organizer_pending_v11.json"
    ))
    .unwrap();
    assert_eq!(snapshot.view.period, 1);
    assert_eq!(snapshot.pending_aid.len(), 1);
    assert_eq!(snapshot.pending_aid[0].kind, OrganizerAidKind::Remote);
    super::verify_offers(&snapshot);
}
