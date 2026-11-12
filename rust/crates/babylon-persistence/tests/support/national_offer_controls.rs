//! Captured opening terms with Designed pending-status interventions.
use babylon_persistence::runtime_session::{OrganizerAidKind, OrganizerSnapshot};

fn opening() -> OrganizerSnapshot {
    serde_json::from_str(include_str!(
        "../fixtures/national_organizer_opening_v19.json"
    ))
    .expect("the authored JSON matches the declared schema")
}

fn remote_in_transit() -> OrganizerSnapshot {
    serde_json::from_str(include_str!(
        "../fixtures/national_organizer_pending_v19.json"
    ))
    .expect("the actual engine pending snapshot matches the current schema")
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
#[should_panic(expected = "actionable aid kinds must exclude exactly the already pending kinds")]
fn missing_offer_without_pending_is_refused() {
    let mut snapshot = opening();
    snapshot.view.aid_options.pop();
    super::verify_offers(&snapshot);
}

#[test]
#[should_panic(expected = "pending mandate must repeat the captured preview mandate")]
fn changed_pending_identity_is_refused() {
    let mut wrong_identity = remote_in_transit();
    wrong_identity.pending_aid[0].mandate_id = [99; 32];
    super::verify_offers(&wrong_identity);
}

#[test]
#[should_panic(expected = "one original commitment per pending kind")]
fn duplicate_pending_action_is_refused() {
    let mut duplicate = remote_in_transit();
    duplicate.pending_aid.push(duplicate.pending_aid[0].clone());
    super::verify_offers(&duplicate);
}

#[test]
#[should_panic(expected = "actionable aid kinds must exclude exactly the already pending kinds")]
fn second_actionable_offer_is_refused() {
    let mut actionable = remote_in_transit();
    actionable.view.aid_options = opening().view.aid_options;
    super::verify_offers(&actionable);
}

#[test]
fn captured_pending_boundary_retains_both_terms_and_only_the_local_action() {
    let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
        "../fixtures/national_organizer_pending_v19.json"
    ))
    .expect("the authored JSON matches the declared schema");
    assert_eq!(snapshot.view.period, 1);
    assert_eq!(snapshot.pending_aid.len(), 1);
    assert_eq!(snapshot.pending_aid[0].kind, OrganizerAidKind::Remote);
    super::verify_offers(&snapshot);
}
