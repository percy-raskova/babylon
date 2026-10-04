//! Projection controls use the same real captured circuit/organizer fixture.
use super::*;
use crate::organizer_aid_fixture as fixture;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::{OrganizerChoice, OrganizerOutcome};

#[test]
fn remote_projection_preserves_admission_dispatch_and_resolution_dates() {
    let mut config = fixture::config();
    config.aid_bindings[0].kind = OrganizerAidKind::Remote;
    config.aid_bindings[0].coordination_hours = 1;
    let mut session = fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        config,
        false,
        true,
    );
    let accepted = fixture::commitment(&session, OrganizerChoice::RemoteAid);
    assert_eq!(accepted.command.expected_period, 0);
    assert_eq!(accepted.resolves_period, 1);
    let first = fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    fixture::commit(&mut session, &mut sink, first);
    let state = session.material().organizer_state().unwrap();
    let projected = pending(&state.pending_aid[0]);
    assert_eq!(projected.admitted_period, 0);
    assert_eq!(projected.dispatch_period, 1);
    assert_eq!(projected.original_commitment_id, accepted.commitment_id);
    assert_eq!(
        projected.material_commitment_id,
        state.pending_aid[0].material_commitment_id
    );
    assert_eq!(projected.mandate_id, state.pending_aid[0].gift.mandate_id);
    let waiting = resolutions(state);
    assert_eq!(waiting.len(), 1);
    assert_eq!(waiting[0].pending, projected);
    assert_eq!(waiting[0].practice.period, 1);
    assert_eq!(
        waiting[0].practice.outcome,
        OrganizerOutcome::AidAwaitingSupport
    );
    let json = serde_json::to_value(&projected).unwrap();
    assert!(json.get("partner_authorization").is_none());
    assert!(json.get("authority_digest").is_none());
    let second = fixture::prepare(&session, None);
    fixture::commit(&mut session, &mut sink, second);
    let state = session.material().organizer_state().unwrap();
    assert!(state.pending_aid.is_empty());
    let returned = resolutions(state);
    assert_eq!(returned.len(), 1);
    assert_eq!(returned[0].pending, projected);
    assert_eq!(returned[0].support.period, 2);
    assert_eq!(returned[0].practice.period, 2);
    assert_eq!(
        returned[0].practice.outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert!(returned.iter().all(|r| r.practice.period == state.period));
}

#[test]
fn opening_time_is_unknown_then_projection_uses_actual_unspent_closed_time() {
    let mut config = fixture::config();
    config.aid_bindings[0].kind = OrganizerAidKind::Remote;
    config.aid_bindings[0].coordination_hours = 1;
    let mut session = fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        config,
        false,
        true,
    );
    let opening = projections(
        session.material().state(),
        session.material().organizer_config().unwrap(),
        0,
    )
    .unwrap();
    assert_eq!(opening.len(), 1);
    assert_eq!(opening[0].period, 0);
    assert_eq!(opening[0].time, None);
    assert!(projections(
        session.material().state(),
        session.material().organizer_config().unwrap(),
        1
    )
    .is_err());
    let accepted = fixture::commitment(&session, OrganizerChoice::RemoteAid);
    let first = fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    fixture::commit(&mut session, &mut sink, first);
    let second = fixture::prepare(&session, None);
    fixture::commit(&mut session, &mut sink, second);
    let register = session.material();
    let preview = projections(register.state(), register.organizer_config().unwrap(), 2).unwrap();
    let CircuitAccounting::Monetary(economy) = &register.state().accounting else {
        panic!("monetary fixture");
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("modeled fixture");
    };
    let principal = fixture::household();
    let row = book
        .receipts
        .iter()
        .find(|r| r.principal_id == principal)
        .unwrap();
    let spent = book
        .contributions
        .iter()
        .filter(|r| r.contribution.principal_id == principal)
        .map(|r| r.contribution.hours)
        .sum::<u64>();
    assert!(spent > 0);
    assert_eq!(
        preview[0].time,
        Some(OrganizerAidTime {
            period: 2,
            labor_unit_id: row.labor_unit_id.as_bytes(),
            remaining_hours: row.contribution_available_hours.checked_sub(spent).unwrap()
        })
    );
    assert_eq!(preview[0].period, 2);
    assert_eq!(register.state().period, 3);
    assert_eq!(
        remaining_time(register.state(), principal, row.labor_unit_id, 1),
        Err(RuntimeSessionErrorCode::OrganizerRefused)
    );
}
