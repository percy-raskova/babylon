//! Projection controls use the same real captured circuit/organizer fixture.
use super::{remaining_time, OrganizerAidTime};
use crate::organizer_aid_fixture as fixture;
use crate::organizer_aid_fixture::Session;
use crate::runtime_session::OrganizerSnapshot;
use crate::runtime_session::RuntimeSessionErrorCode;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::{CircuitAccounting, HouseholdTimeAccounting};
use babylon_practice_contract::OrganizerAidKind;
use babylon_practice_contract::OrganizerAllocation;
use babylon_practice_contract::OrganizerCommitment;
use babylon_practice_contract::{OrganizerChoice, OrganizerOutcome};
use serde_json::Value;

#[test]
fn remote_projection_preserves_admission_dispatch_and_resolution_dates() {
    let mut config = fixture::config();
    config.aid_bindings[0].kind = OrganizerAidKind::Remote;
    config.aid_bindings[0].coordination_hours = 1;
    let mut session = fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().expect("the Michigan hex foundation builds"),
        config,
        false,
        true,
    );
    let accepted = fixture::commitment_with_allocation(
        &session,
        OrganizerChoice::RemoteAid,
        OrganizerAllocation::Aid {
            food_quantity: 2,
            cash_micros: 0,
        },
    );
    assert_eq!(accepted.command.expected_period, 0);
    assert_eq!(accepted.resolves_period, 1);
    let first = fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    fixture::commit(&mut session, &mut sink, first);
    let state = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let entries = session
        .material()
        .organizer_journal()
        .and_then(|journal| journal.latest())
        .expect("the fixture register carries organizer journal entries");
    let projected = super::pending(&state.pending_aid[0]);
    assert_eq!(projected.admitted_period, 0);
    assert_eq!(projected.dispatch_period, 1);
    assert_eq!(projected.original_commitment_id, accepted.commitment_id);
    assert_eq!(
        projected.material_commitment_id,
        state.pending_aid[0].material_commitment_id
    );
    assert_eq!(projected.mandate_id, state.pending_aid[0].gift.mandate_id);
    let waiting = super::resolutions(entries);
    assert_eq!(waiting.len(), 1);
    assert_eq!(waiting[0].pending, projected);
    assert_eq!(waiting[0].practice.period, 1);
    assert_eq!(
        waiting[0].practice.outcome,
        OrganizerOutcome::AidAwaitingSupport
    );
    let json = serde_json::to_value(&projected).expect("the value serializes to JSON");
    assert!(json.get("partner_authorization").is_none());
    assert!(json.get("authority_digest").is_none());
    let second = fixture::prepare(&session, None);
    fixture::commit(&mut session, &mut sink, second);
    let state = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    assert_eq!(state.pending_aid.len(), 0);
    let entries = session
        .material()
        .organizer_journal()
        .and_then(|journal| journal.latest())
        .expect("the fixture register carries organizer journal entries");
    let returned = super::resolutions(entries);
    assert_eq!(returned.len(), 1);
    assert_eq!(projected.response, None);
    let mut completed = projected;
    completed.response = Some(returned[0].practice.clone());
    assert_eq!(returned[0].pending, completed);
    assert_eq!(returned[0].support.period, 2);
    assert_eq!(returned[0].practice.period, 2);
    assert_eq!(
        returned[0].practice.outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert!(returned.iter().all(|r| r.practice.period == state.period));
    let practice = &entries.aid_receipts[0].practice;
    assert!(practice
        .time_use
        .iter()
        .any(|usage| usage.actor_id != practice.actor_id));
    assert!(returned[0]
        .practice
        .time_use
        .iter()
        .all(|usage| usage.actor_id == practice.actor_id));
    assert_eq!(
        returned[0].practice.partner_response,
        practice.partner_response
    );
    assert_eq!(returned[0].practice.hours_spent, practice.hours_spent);
    let mut withheld = entries.clone();
    let babylon_practice_contract::OrganizerAidSupportStatus::Granted {
        household_consumed_quantity,
        ..
    } = &mut withheld.aid_receipts[0].support.status
    else {
        panic!("the arrived fixture must contain an actual grant");
    };
    *household_consumed_quantity += 1;
    assert_eq!(
        super::resolutions(&withheld),
        returned,
        "a sender's practice receipt cannot disclose the recipient's private consumption"
    );
}

#[test]
fn opening_time_is_unknown_then_projection_uses_actual_unspent_closed_time() {
    let mut config = fixture::config();
    config.aid_bindings[0].kind = OrganizerAidKind::Remote;
    config.aid_bindings[0].coordination_hours = 1;
    let mut session = fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().expect("the Michigan hex foundation builds"),
        config,
        false,
        true,
    );
    let opening = super::projections(
        session.catalog(),
        session.material().state(),
        session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        0,
    )
    .expect("the fixture call `projections` succeeds for the authored inputs");
    assert_eq!(opening.len(), 1);
    assert_eq!(opening[0].period, 0);
    assert_eq!(opening[0].food.as_ref().expect("food offer").time, None);
    assert!(super::projections(
        session.catalog(),
        session.material().state(),
        session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        1
    )
    .is_err());
    let accepted = fixture::commitment_with_allocation(
        &session,
        OrganizerChoice::RemoteAid,
        OrganizerAllocation::Aid {
            food_quantity: 2,
            cash_micros: 0,
        },
    );
    let first = fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    fixture::commit(&mut session, &mut sink, first);
    let second = fixture::prepare(&session, None);
    fixture::commit(&mut session, &mut sink, second);
    let register = session.material();
    let preview = super::projections(
        session.catalog(),
        register.state(),
        register
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        2,
    )
    .expect("the fixture call `projections` succeeds for the authored inputs");
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
        .expect("the fixture holds the searched element");
    let spent = book
        .contributions
        .iter()
        .filter(|r| r.contribution.principal_id == principal)
        .map(|r| r.contribution.hours)
        .sum::<u64>();
    assert!(spent > 0);
    assert_eq!(
        preview[0].food.as_ref().expect("food offer").time,
        Some(OrganizerAidTime {
            period: 2,
            labor_unit_id: row.labor_unit_id.as_bytes(),
            remaining_hours: row
                .contribution_available_hours
                .checked_sub(spent)
                .expect("the fixture arithmetic stays in range")
        })
    );
    assert_eq!(preview[0].period, 2);
    assert_eq!(register.state().period, 3);
    assert_eq!(
        remaining_time(register.state(), principal, row.labor_unit_id, 1),
        Err(RuntimeSessionErrorCode::OrganizerRefused)
    );
}

fn independent_leg_session(cash_only: bool) -> Session {
    use babylon_material_circuit::{
        AccountId, AidTransport, LogisticsNodeId, OrganizationAccountId, RouteId,
    };
    let mut materials = fixture::aid_opening(false);
    let mut config = fixture::config();
    config.collection = None;
    let mandate = &mut materials.catalog.aid_mandates[0];
    if cash_only {
        config.aid_bindings[0].kind = OrganizerAidKind::Remote;
        mandate.good_id = fixture::good(99);
        mandate.transport = AidTransport::Routed {
            route_id: RouteId::from_bytes([99; 32]),
            from_node_id: LogisticsNodeId::from_bytes([98; 32]),
            to_node_id: LogisticsNodeId::from_bytes([99; 32]),
        };
        mandate.initial_quantity = 0;
        mandate.initial_cash = fixture::money(3);
        config.aid_bindings[0].initial_food_quantity = 0;
        config.aid_bindings[0].initial_cash_micros = 3;
    } else {
        mandate.payer = AccountId::Organization(OrganizationAccountId::from_bytes([99; 32]));
        mandate.initial_cash = fixture::money(0);
        config.aid_bindings[0].initial_cash_micros = 0;
    }
    fixture::try_session(
        crate::michigan_dynamic_hex_foundation().expect("foundation"),
        &format!(
            "{}\n{}\n{}",
            fixture::MATERIAL,
            fixture::PRODUCTS,
            fixture::PRACTICE
        ),
        materials,
        config,
    )
    .expect("valid selected-leg capture")
}

#[test]
fn stock_only_status_admits_food_without_unselected_payer() {
    let session = independent_leg_session(false);
    let snapshot = crate::organizer_runtime::captured_organizer_snapshot(
        session.catalog(),
        session.material(),
        None,
        session.duration(),
    )
    .expect("ordinary status permits food with unavailable unrelated cash");
    assert_eq!(snapshot.aid[0].initial_food_quantity, 1);
    let accepted = fixture::commitment_with_allocation(
        &session,
        OrganizerChoice::LocalAid,
        OrganizerAllocation::Aid {
            food_quantity: 1,
            cash_micros: 0,
        },
    );
    verify_independent_selected_terms(&session, &snapshot, &accepted);
    let candidate = fixture::prepare(&session, Some(&accepted));
    let facts = super::resolutions(
        candidate
            .material()
            .register()
            .organizer_journal()
            .expect("journal")
            .latest()
            .expect("close"),
    );
    assert!(matches!(
        facts[0].support.status,
        super::OrganizerFoodDelivery::Granted {
            granted_quantity: 1,
            ..
        }
    ));
    assert_eq!(
        facts[0].support.material_postings.payer_cash_granted_micros,
        0
    );
}

#[test]
fn cash_only_status_admits_cash_without_unselected_food_metadata() {
    let session = independent_leg_session(true);
    let snapshot = crate::organizer_runtime::captured_organizer_snapshot(
        session.catalog(),
        session.material(),
        None,
        session.duration(),
    )
    .expect("ordinary status permits cash with unavailable unrelated food");
    assert_eq!(snapshot.aid[0].initial_cash_micros, 3);
    let accepted = fixture::commitment_with_allocation(
        &session,
        OrganizerChoice::RemoteAid,
        OrganizerAllocation::Aid {
            food_quantity: 0,
            cash_micros: 3,
        },
    );
    verify_independent_selected_terms(&session, &snapshot, &accepted);
    let candidate = fixture::prepare(&session, Some(&accepted));
    let facts = super::resolutions(
        candidate
            .material()
            .register()
            .organizer_journal()
            .expect("journal")
            .latest()
            .expect("close"),
    );
    assert_eq!(
        facts[0].support.status,
        super::OrganizerFoodDelivery::NotRequested
    );
    assert_eq!(
        facts[0].support.material_postings.payer_cash_granted_micros,
        3
    );
}

fn verify_independent_selected_terms(
    session: &Session,
    snapshot: &OrganizerSnapshot,
    accepted: &OrganizerCommitment,
) {
    let cash_only = accepted.command.choice == OrganizerChoice::RemoteAid;
    let expected: Value = serde_json::from_str(if cash_only {
        include_str!("../../tests/fixtures/cash_only_no_food_v17.json")
    } else {
        include_str!("../../tests/fixtures/food_only_no_payer_v17.json")
    })
    .expect("actual producer fixture");
    assert_eq!(
        serde_json::to_value(snapshot).expect("status JSON"),
        expected["snapshot"]
    );
    let config = session.material().organizer_config().expect("config");
    let state = session.material().organizer_state().expect("state");
    assert_eq!(
        serde_json::to_value(config).expect("config JSON"),
        expected["config"]
    );
    assert_eq!(
        serde_json::to_value(state).expect("state JSON"),
        expected["state"]
    );
    assert_eq!(
        serde_json::to_value(accepted).expect("command JSON"),
        expected["accepted"]
    );
    let before = session.material().canonical_bytes().to_vec();
    super::validate_selected(
        session.catalog(),
        session.material().state(),
        config,
        0,
        &accepted.command,
    )
    .expect("selected leg has its actual material wiring");
    let preview = babylon_practice_contract::preview_organizer(config, state, &accepted.command)
        .expect("authenticated preview");
    assert_eq!(
        serde_json::to_value(preview).expect("preview JSON"),
        expected["preview"]
    );
    assert_eq!(snapshot.aid[0].food.is_none(), cash_only);
    assert_eq!(snapshot.aid[0].payer_cash.is_none(), !cash_only);
    let mut missing_selected = accepted.command.clone();
    missing_selected.allocation = OrganizerAllocation::Aid {
        food_quantity: 1,
        cash_micros: 3,
    };
    assert_eq!(
        super::validate_selected(
            session.catalog(),
            session.material().state(),
            config,
            0,
            &missing_selected
        ),
        Err(RuntimeSessionErrorCode::OrganizerRefused)
    );
    let mut changed_source = config.clone();
    changed_source.aid_bindings[0].source_hash = [99; 32];
    assert_eq!(
        super::projections(
            session.catalog(),
            session.material().state(),
            &changed_source,
            0
        ),
        Err(RuntimeSessionErrorCode::OrganizerRefused)
    );
    assert_eq!(
        session.material().canonical_bytes(),
        before,
        "all previews leave authoritative state unchanged"
    );
}
