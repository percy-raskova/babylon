//! Real committed aid must remain readable through household accounting.
use super::*;
use crate::organizer_aid_fixture as fixture;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::AidOutcome;
use babylon_practice_contract::{OrganizerAidKind, OrganizerChoice};

#[test]
fn aid_household_projection_accepts_real_local_grant() {
    assert_aid_projection(false);
}
#[test]
fn aid_household_projection_accepts_real_routed_dispatch_and_arrival() {
    assert_aid_projection(true);
}
fn assert_aid_projection(routed: bool) {
    let mut config = fixture::config();
    let choice = if routed {
        config.aid_bindings[0].kind = OrganizerAidKind::Remote;
        config.aid_bindings[0].coordination_hours = 1;
        OrganizerChoice::RemoteAid
    } else {
        OrganizerChoice::LocalAid
    };
    let mut session = fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        config,
        false,
        routed,
    );
    let accepted = fixture::commitment(&session, choice);
    let mut sink = CollectingSink::default();
    for period in 1..=2 {
        let prior = session.material().state().clone();
        let candidate = fixture::prepare(&session, (period == 1).then_some(&accepted));
        let receipts = babylon_tick::material_world::decode_material_receipts(
            candidate.material().receipt_bytes(),
        )
        .unwrap();
        if period == 1 {
            assert!(receipts.aid.iter().any(|row| row.outcome
                == if routed {
                    AidOutcome::Dispatched
                } else {
                    AidOutcome::Granted
                }));
        } else if routed {
            assert!(receipts
                .aid
                .iter()
                .any(|row| row.outcome == AidOutcome::Granted));
        }
        fixture::commit(&mut session, &mut sink, candidate);
        let current = session.material().state();
        let projected =
            households::project_with_labels(current, Some(&prior), Some(&receipts), |_, _| {
                Some(("Food".to_owned(), "units".to_owned()))
            });
        assert!(
            projected.is_ok(),
            "routed={routed} period={period}: {projected:?}"
        );
        assert!(!projected.unwrap().is_empty());
        let (capacity, _definitions) =
            freight::project_with_labels(current, Some(&prior), Some(&receipts), |_| {
                Some("Shared route capacity".to_owned())
            })
            .unwrap();
        if routed && period == 1 {
            assert!(capacity
                .iter()
                .filter_map(|row| row.completed.as_ref())
                .flat_map(|row| &row.reservations)
                .any(|row| !row.support_orders.is_empty() && row.newly_reserved_grams > 0));
        }
        if !receipts.aid.is_empty() {
            let mut missing = receipts.clone();
            missing.aid.clear();
            let mut duplicate = receipts.clone();
            duplicate.aid.push(duplicate.aid[0].clone());
            let mut changed = receipts.clone();
            let movement = changed
                .aid
                .iter_mut()
                .find(|row| row.outcome != AidOutcome::Requested)
                .unwrap();
            movement.quantity = movement.quantity.checked_add(1).unwrap();
            for corrupted in [missing, duplicate, changed] {
                assert_eq!(
                    aid::join(&prior, current, &corrupted).err(),
                    Some(ProductionProjectionError::State)
                );
            }
        }
    }
}
