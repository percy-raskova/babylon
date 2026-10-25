//! Real BSL/tick gift, scarce time and independent partner controls.

#[path = "support/dual_aid_schedule.rs"]
mod dual_aid_schedule;
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;
#[path = "support/organizer_aid_fixture.rs"]
mod organizer_aid_fixture;
use crate::organizer_aid_fixture::Session;
use crate::organizer_aid_fixture::MATERIAL;
use crate::organizer_aid_fixture::PRACTICE;
use crate::organizer_aid_fixture::PRODUCTS;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::state_hash::CanonicalState;
use babylon_material_circuit::AidResolveInput;
use babylon_material_circuit::CollectionResolveInput;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::UnitId;
use babylon_material_circuit::{
    AidOutcome, CircuitAccounting, CommodityKind, HouseholdTimeAccounting,
};
use babylon_practice_contract::OrganizerAidResolutionReceipt;
use babylon_practice_contract::OrganizerAidSupport;
use babylon_practice_contract::OrganizerCollectionOutcome;
use babylon_practice_contract::OrganizerConfig;
use babylon_practice_contract::OrganizerPeriodJournalEntries;
use babylon_practice_contract::OrganizerState;
use babylon_practice_contract::{
    admit_organizer, OrganizerAidKind, OrganizerChoice, OrganizerOutcome, OrganizerPartnerPolicy,
    OrganizerTimeBindingMode,
};
use babylon_tick::material_world;
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;
use serde_json::Value;
use std::collections::BTreeSet;

trait OrganizerHistory {
    fn history(&self) -> &OrganizerPeriodJournalEntries;
}

impl OrganizerHistory for MaterialWorldRegister {
    fn history(&self) -> &OrganizerPeriodJournalEntries {
        self.organizer_journal()
            .and_then(|journal| journal.latest())
            .expect("the fixture register carries organizer journal entries")
    }
}

#[test]
fn fulfilled_gift_uses_real_time_before_later_coordination() {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let parts = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation_fixture_parts();
    let mut remaining = foundation.canonical_bytes();
    for part in parts {
        let (prefix, tail) = remaining.split_at(part.len());
        assert_eq!(prefix, part);
        remaining = tail;
    }
    assert!(remaining.is_empty());
    let mut session = organizer_aid_fixture::authored_session(
        foundation,
        organizer_aid_fixture::config(),
        false,
        false,
    );
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::LocalAid);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut session, &mut sink, candidate);
    let receipt = session
        .material()
        .history()
        .aid_receipts
        .last()
        .map(|row| &row.practice)
        .expect("the fixture call `map` succeeds for the authored inputs");
    assert_actual_aid_postings(
        &session
            .material()
            .history()
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .support,
        2,
        4,
        6,
        6,
        0,
    );
    assert_eq!(receipt.outcome, OrganizerOutcome::InsufficientTime);
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        unreachable!()
    };
    assert_eq!(
        book.contributions
            .iter()
            .filter(|r| r.contribution.principal_id == organizer_aid_fixture::household())
            .map(|r| r.contribution.hours)
            .sum::<u64>(),
        4
    );
    assert_eq!(
        economy
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .household_stocks
            .iter()
            .find(|r| r.principal_id == organizer_aid_fixture::recipient())
            .expect("the fixture holds the searched element")
            .quantity,
        1
    );
}
#[test]
fn captured_promises_cannot_replace_zero_actual_household_time() {
    let mut session = organizer_aid_fixture::authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        organizer_aid_fixture::config(),
        true,
        false,
    );
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::LocalAid);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut session, &mut sink, candidate);
    assert_eq!(
        session
            .material()
            .history()
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .outcome,
        OrganizerOutcome::AidNotProvisioned
    );
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        unreachable!()
    };
    assert_actual_aid_postings(
        &session
            .material()
            .history()
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .support,
        0,
        0,
        6,
        0,
        6,
    );
    assert!(book.contributions.is_empty());
    assert_eq!(
        economy
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .household_stocks
            .iter()
            .find(|r| r.principal_id == organizer_aid_fixture::recipient())
            .expect("the fixture holds the searched element")
            .quantity,
        0
    );
}
#[test]
fn recipient_practice_refusal_does_not_revoke_granted_food() {
    let mut cfg = organizer_aid_fixture::config();
    cfg.aid_bindings[0].coordination_hours = 1;
    cfg.aid_bindings[0].partner.policy = OrganizerPartnerPolicy::Refuse;
    let mut session = organizer_aid_fixture::authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        cfg,
        false,
        false,
    );
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::LocalAid);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut session, &mut sink, candidate);
    let receipt = session
        .material()
        .history()
        .aid_receipts
        .last()
        .map(|row| &row.practice)
        .expect("the fixture call `map` succeeds for the authored inputs");
    assert_actual_aid_postings(
        &session
            .material()
            .history()
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .support,
        2,
        4,
        6,
        6,
        0,
    );
    assert_eq!(receipt.outcome, OrganizerOutcome::AidPracticeUncompleted);
    assert!(!receipt.time_use.iter().any(|r| r.actor_id == 120));
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        unreachable!()
    };
    assert_eq!(
        economy
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .household_stocks
            .iter()
            .find(|r| r.principal_id == organizer_aid_fixture::recipient())
            .expect("the fixture holds the searched element")
            .quantity,
        1
    );
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`delivered_consumed_support_funds_only_actual_independent_coordination` keeps one authored boundary's fixture and assertions together"
)]
fn delivered_consumed_support_funds_only_actual_independent_coordination() {
    let mut cfg = organizer_aid_fixture::config();
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = organizer_aid_fixture::authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        cfg,
        false,
        false,
    );
    let opening = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state")
        .clone();
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::LocalAid);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let material = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .expect("the canonical bytes decode into the declared type");
    assert!(material
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity == 2));
    let consumed = material
        .household_consumption
        .iter()
        .find(|r| r.principal_id == organizer_aid_fixture::recipient())
        .expect("the fixture holds the searched element");
    assert_eq!(
        (consumed.consumed_quantity, consumed.unmet_quantity),
        (1, 0)
    );
    assert_eq!(
        material
            .member_labor_use
            .iter()
            .map(|r| r.attended_hours)
            .sum::<u64>(),
        16
    );
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut session, &mut sink, candidate);
    let next = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let next_entries = session.material().history();
    assert_actual_aid_postings(
        &next_entries
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .support,
        2,
        4,
        6,
        6,
        0,
    );
    assert_eq!(
        next_entries
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .outcome,
        OrganizerOutcome::AidScheduled
    );
    assert!(next_entries
        .receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .time_use
        .is_empty());
    assert_eq!(
        next_entries
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert_eq!(next.agreements, opening.agreements);
    assert_eq!(next.contact_products, opening.contact_products);
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(time) = &economy.household_time else {
        unreachable!()
    };
    for (principal, gross, used) in [
        (organizer_aid_fixture::household(), 6, 5),
        (organizer_aid_fixture::recipient(), 3, 2),
    ] {
        assert_eq!(
            time.receipts
                .iter()
                .find(|r| r.principal_id == principal)
                .expect("the fixture holds the searched element")
                .contribution_available_hours,
            gross
        );
        assert_eq!(
            time.contributions
                .iter()
                .filter(|r| r.contribution.principal_id == principal)
                .map(|r| r.contribution.hours)
                .sum::<u64>(),
            used
        );
    }
    let recovered = MaterialWorldRegister::decode_external(
        session.catalog(),
        session.material().canonical_bytes().to_vec(),
    )
    .expect("the committed canonical bytes decode");
    assert_eq!(recovered, *session.material());
}

#[test]
fn failed_gift_tick_publishes_nothing_and_exact_retry_preserves_receipt_identity() {
    let mut cfg = organizer_aid_fixture::config();
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = organizer_aid_fixture::authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        cfg,
        false,
        false,
    );
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::LocalAid);
    let before = session.material().canonical_bytes().to_vec();
    let graph_before = session
        .graph_session()
        .graph()
        .encode_state()
        .expect("the graph encodes its canonical state")
        .as_bytes()
        .to_vec();
    let hash_before = session
        .current_world_hash()
        .expect("the committed session publishes a world hash");
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let expected = *candidate.identity();
    let mut sink = CollectingSink::default();
    let result = session.commit_prepared_and_publish(&mut sink, candidate, |_, _| {
        Err::<ReplayCommitDisposition, _>("injected durable failure")
    });
    assert!(matches!(
        result,
        Err(babylon_tick::material_replay::MaterialCommitError::Commit(
            "injected durable failure"
        ))
    ));
    assert_eq!(session.material().canonical_bytes(), before);
    assert_eq!(
        session
            .graph_session()
            .graph()
            .encode_state()
            .expect("the graph encodes its canonical state")
            .as_bytes(),
        graph_before
    );
    assert_eq!(
        session
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        hash_before
    );
    assert_eq!(session.completed_tick(), 0);
    assert!(sink.events.is_empty());
    let retry = organizer_aid_fixture::prepare(&session, Some(&accepted));
    assert_eq!(*retry.identity(), expected);
    organizer_aid_fixture::commit(&mut session, &mut sink, retry);
    assert_eq!(session.completed_tick(), 1);
    assert_eq!(session.material().history().receipts.len(), 1);
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`remote_support_keeps_original_authorization_until_arrival_without_another_command` keeps one authored boundary's fixture and assertions together"
)]
fn remote_support_keeps_original_authorization_until_arrival_without_another_command() {
    let mut cfg = organizer_aid_fixture::config();
    cfg.aid_bindings[0].kind = OrganizerAidKind::Remote;
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = organizer_aid_fixture::authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        cfg,
        false,
        true,
    );
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::RemoteAid);
    let first = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let first_receipts =
        babylon_tick::material_world::decode_material_receipts(first.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type");
    assert!(first_receipts
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Dispatched && r.quantity == 2));
    assert!(!first_receipts
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted));
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut session, &mut sink, first);
    let saved = MaterialWorldRegister::decode_external(
        session.catalog(),
        session.material().canonical_bytes().to_vec(),
    )
    .expect("the committed canonical bytes decode");
    assert_eq!(saved, *session.material());
    let waiting = saved
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let waiting_entries = saved.history();
    assert_actual_aid_postings(&waiting_entries.aid_receipts[0].support, 2, 4, 6, 0, 0);
    assert_eq!(waiting.pending_aid.len(), 1);
    assert_eq!(waiting.pending_aid[0].gift.commitment, accepted);
    assert_eq!(
        waiting_entries.aid_receipts[0].practice.outcome,
        OrganizerOutcome::AidAwaitingSupport
    );
    assert!(waiting_entries.aid_receipts[0].practice.time_use.is_empty());
    let second = organizer_aid_fixture::prepare(&session, None);
    let second_receipts =
        babylon_tick::material_world::decode_material_receipts(second.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type");
    assert!(second_receipts
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity == 2));
    assert!(second_receipts
        .household_consumption
        .iter()
        .any(|r| r.principal_id == organizer_aid_fixture::recipient() && r.consumed_quantity == 1));
    organizer_aid_fixture::commit(&mut session, &mut sink, second);
    let completed = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    assert!(completed.pending_aid.is_empty());
    let resolution = session
        .material()
        .history()
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_actual_aid_postings(&resolution.support, 0, 0, 0, 6, 0);
    assert_eq!(resolution.authorization.gift.commitment, accepted);
    assert_eq!(resolution.authorization.dispatch_period, 1);
    assert_eq!(resolution.practice.period, 2);
    assert_eq!(
        resolution.practice.outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert_eq!(completed.contact_products.len(), 1); // Ordinary standing contact only.
    assert!(admit_organizer(
        session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        completed,
        &accepted.command
    )
    .is_err());
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(time) = &economy.household_time else {
        unreachable!()
    };
    for policy in &time.policies {
        let available = time
            .receipts
            .iter()
            .find(|r| r.principal_id == policy.principal_id)
            .expect("the fixture holds the searched element")
            .contribution_available_hours;
        let used = time
            .contributions
            .iter()
            .filter(|r| r.contribution.principal_id == policy.principal_id)
            .map(|r| r.contribution.hours)
            .sum::<u64>();
        assert!(used <= available);
    }
    let recovered = MaterialWorldRegister::decode_external(
        session.catalog(),
        session.material().canonical_bytes().to_vec(),
    )
    .expect("the committed canonical bytes decode");
    assert_eq!(recovered, *session.material());
}

#[test]
fn workplace_report_converts_declared_mass_exactly_without_requiring_one_kg_units() {
    let mut cfg = organizer_aid_fixture::config();
    cfg.time_binding = OrganizerTimeBindingMode::FixedTimeControl;
    cfg.aid_bindings.clear();
    cfg.participants.retain(|row| row.contributor_id != 204);
    let mut material = organizer_aid_fixture::opening();
    material
        .catalog
        .commodities
        .iter_mut()
        .find(|r| r.good_id == organizer_aid_fixture::good(1))
        .expect("the fixture holds the searched element")
        .kind = CommodityKind::Storable {
        grams_per_unit: 14_000,
    };
    let session = organizer_aid_fixture::try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        material,
        cfg,
    )
    .expect("the fixture opens a session");
    let result = organizer_aid_fixture::prepare(&session, None);
    let report = result
        .material()
        .register()
        .organizer_state()
        .expect("the fixture register carries organizer state")
        .last_workplace_facts
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(report.output_kg, 56);
    assert_eq!(report.performed_labor_hours, 4);
}

#[test]
fn workplace_report_refuses_nonintegral_kg_instead_of_rounding() {
    let mut cfg = organizer_aid_fixture::config();
    cfg.time_binding = OrganizerTimeBindingMode::FixedTimeControl;
    cfg.aid_bindings.clear();
    cfg.participants.retain(|row| row.contributor_id != 204);
    let mut material = organizer_aid_fixture::opening();
    material
        .catalog
        .commodities
        .iter_mut()
        .find(|row| row.good_id == organizer_aid_fixture::good(1))
        .expect("the fixture holds the searched element")
        .kind = CommodityKind::Storable {
        grams_per_unit: 1001,
    };
    let session = organizer_aid_fixture::try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        material,
        cfg,
    )
    .expect("the fixture opens a session");
    let actions = babylon_practice_contract::organizer_action_batch(
        session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        session
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state"),
        None,
        session.graph_session().session_identity().clone(),
    )
    .expect("the authored action batch builds");
    assert!(matches!(
        session.prepare_advance_with_organizer(&actions, None),
        Err(babylon_tick::material_replay::MaterialReplayError::Graph(
            babylon_tick::replay_session::ReplayTickError::MaterialBase(
                babylon_tick::material_replay::MaterialBaseError::World(
                    babylon_tick::material_world::MaterialWorldError::Wire
                )
            )
        ))
    ));
}

fn assert_actual_aid_postings(
    support: &OrganizerAidSupport,
    dispatched: u64,
    hours: u64,
    reserved: i128,
    granted: i128,
    refunded: i128,
) {
    let wire = serde_json::to_value(support).expect("the value serializes to JSON");
    assert_eq!(
        wire["material_postings"],
        serde_json::json!({
            "dispatched_quantity": dispatched,
            "fulfillment_hours": hours,
            "payer_cash_reserved_micros": reserved.to_string(),
            "payer_cash_granted_micros": granted.to_string(),
            "payer_cash_refunded_micros": refunded.to_string()
        })
    );
}
// Existing real BSL/material/organizer fixture; source-only RED/GREEN controls.
fn collection_config_for_control() -> OrganizerConfig {
    let base = organizer_aid_fixture::authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        organizer_aid_fixture::config(),
        false,
        false,
    );
    let CircuitAccounting::Monetary(e) = &base.material().state().accounting else {
        unreachable!()
    };
    let mut value = serde_json::to_value(organizer_aid_fixture::config())
        .expect("the value serializes to JSON");
    value["collection"] = serde_json::json!({
        "mandate_id": ([93_u8;32].to_vec()), "source_hash": ([94_u8;32].to_vec()),
        "actor_id":101,"contributor_id":201,
        "household_principal_id": organizer_aid_fixture::household().as_bytes().to_vec(),
        "organization_account_id":([96_u8;32].to_vec()),"social_class_target":([98_u8;32].to_vec()),
        "labor_unit_id": e.aid.mandates[0].labor_unit_id.as_bytes().to_vec(),
        "cash_consent":"accept","maximum_cash_micros":"2","protected_cash_floor_micros":"0","collection_hours":2
    });
    serde_json::from_value(value).expect("the JSON value matches the declared type")
}

fn collection_control_session(protected_target: u64, no_time: bool) -> Session {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let base = organizer_aid_fixture::authored_session(
        foundation,
        organizer_aid_fixture::config(),
        no_time,
        false,
    );
    let catalog = base.catalog().clone();
    let mut opening = base.material().state().clone();
    let CircuitAccounting::Monetary(e) = &mut opening.accounting else {
        unreachable!()
    };
    // Authored fixture target: actual closing pantry remains protected and is
    // asserted independently after close. No altered consumption or cash facts.
    e.recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .household_purchases[0]
        .target_closing_stock = protected_target;
    organizer_aid_fixture::try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        organizer_aid_fixture::Materials {
            catalog,
            state: opening,
        },
        collection_config_for_control(),
    )
    .expect("the fixture opens a session")
}
#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`actual_collection_retains_original_cash_posting_and_material_time_once` keeps one authored boundary's fixture and assertions together"
)]
fn actual_collection_retains_original_cash_posting_and_material_time_once() {
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, MoneyLocation, MoneyTransferPurpose, OrganizationAccountId,
    };
    let mut session = collection_control_session(4, false);
    let collect: OrganizerChoice =
        serde_json::from_str("\"collect\"").expect("the authored JSON matches the declared schema");
    let accepted = organizer_aid_fixture::commitment(&session, collect);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let actual = serde_json::to_value(candidate.material().register().history())
        .expect("the value serializes to JSON");
    let fact = &actual["collection_receipts"][0]["fact"];
    assert_eq!(fact["collected_cash_micros"], "2");
    assert_eq!(fact["performed_hours"], 2);
    assert_eq!(fact["outcome"], "collected");
    assert_eq!(
        actual["collection_receipts"][0]["commitment"]["command"]["nonce"],
        serde_json::to_value(accepted.command.nonce.to_vec())
            .expect("the value serializes to JSON")
    );
    let decoded = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .expect("the canonical bytes decode into the declared type");
    let ordinal = usize::try_from(
        fact["transfer_ordinal"]
            .as_u64()
            .expect("the JSON fixture field is an unsigned integer"),
    )
    .expect("the fixture value fits the target range");
    let movement = &decoded.money_transfers[ordinal];
    assert_eq!(
        movement.purpose,
        MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
    );
    assert_eq!(
        movement.debit.location,
        MoneyLocation::Cash(AccountId::Household(organizer_aid_fixture::household()))
    );
    assert_eq!(
        movement.credit.location,
        MoneyLocation::Cash(AccountId::Organization(OrganizationAccountId::from_bytes(
            [96; 32]
        )))
    );
    assert_eq!(movement.debit.delta.micro_units(), -2);
    assert_eq!(movement.credit.delta.micro_units(), 2);
    let CircuitAccounting::Monetary(e) = &candidate.material().register().state().accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(time) = &e.household_time else {
        unreachable!()
    };
    assert_eq!(
        time.contributions
            .iter()
            .filter(|row| row.contribution.principal_id == organizer_aid_fixture::household())
            .map(|row| row.contribution.hours)
            .sum::<u64>(),
        2
    );
    assert_eq!(
        time.contributions
            .iter()
            .filter(|row| row.contribution.contributor_id == 201)
            .count(),
        1
    );
    assert_eq!(
        e.recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .household_stocks
            .iter()
            .find(|row| row.principal_id == organizer_aid_fixture::household())
            .expect("the fixture holds the searched element")
            .quantity,
        4
    );
    let old = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let new = candidate
        .material()
        .register()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    assert_eq!(new.agreements, old.agreements);
    assert_eq!(new.contact_products, old.contact_products);
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut session, &mut sink, candidate);
    let before = session.material().canonical_bytes().to_vec();
    let actions = babylon_practice_contract::organizer_action_batch(
        session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        session
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state"),
        Some(&accepted),
        session.graph_session().session_identity().clone(),
    );
    assert!(actions.is_err());
    assert_eq!(session.material().canonical_bytes(), before);
}
#[test]
fn protected_closing_pantry_refuses_collection_despite_actual_cash() {
    let session = collection_control_session(8, false);
    let collect: OrganizerChoice =
        serde_json::from_str("\"collect\"").expect("the authored JSON matches the declared schema");
    let accepted = organizer_aid_fixture::commitment(&session, collect);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let actual = serde_json::to_value(candidate.material().register().history())
        .expect("the value serializes to JSON");
    let fact = &actual["collection_receipts"][0]["fact"];
    assert_eq!(fact["outcome"], "protected_closing_stock_unmet");
    assert_eq!(fact["collected_cash_micros"], "0");
    assert_eq!(fact["performed_hours"], 0);
    assert_eq!(fact["transfer_ordinal"], Value::Null);
    let mut omitted = actual.clone();
    omitted["collection_receipts"][0]["fact"]
        .as_object_mut()
        .expect("the JSON fixture field is an object")
        .remove("transfer_ordinal");
    assert!(serde_json::from_value::<OrganizerState>(omitted).is_err());
    let CircuitAccounting::Monetary(e) = &candidate.material().register().state().accounting else {
        unreachable!()
    };
    assert!(
        e.book
            .cash(babylon_material_circuit::AccountId::Household(
                organizer_aid_fixture::household()
            ))
            .expect("the fixture book holds the payer account")
            .micro_units()
            >= 2
    );
    let HouseholdTimeAccounting::Modeled(book) = &e.household_time else {
        unreachable!()
    };
    assert!(book.contributions.is_empty());
}
#[test]
fn actual_collection_wire_refuses_changed_posting_hours_use_and_previous_schema() {
    let session = collection_control_session(4, false);
    let collect: OrganizerChoice =
        serde_json::from_str("\"collect\"").expect("the authored JSON matches the declared schema");
    let accepted = organizer_aid_fixture::commitment(&session, collect);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let bytes = candidate.material().receipt_bytes();
    let decoded = babylon_tick::material_world::decode_material_receipts(bytes)
        .expect("the canonical bytes decode into the declared type");
    assert!(decoded.money_transfers.len() > 1);
    let row = bytes.len() - 317;
    for offset in [240_usize, 256, 272, 280, 281, 285] {
        let mut changed = bytes.to_vec();
        changed[row + offset] ^= 1;
        assert!(
            babylon_tick::material_world::decode_material_receipts(&changed).is_err(),
            "offset {offset}"
        );
    }
    let mut old = bytes.to_vec();
    let domain = b"babylon.material-tick-receipts.v18\0".len();
    old[domain - 2] = b'6';
    old[domain..domain + 4].copy_from_slice(&16_u32.to_be_bytes());
    assert!(babylon_tick::material_world::decode_material_receipts(&old).is_err());
    for removed in [1_usize, 32, 317, 326] {
        assert!(babylon_tick::material_world::decode_material_receipts(
            &bytes[..bytes.len() - removed]
        )
        .is_err());
    }
    assert_eq!(
        session
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state")
            .period,
        0
    );
}
fn collection_savings_control(no_attendance: bool) -> Session {
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, HistoricalCostBook, OrganizationAccountId,
    };
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let base = organizer_aid_fixture::authored_session(
        foundation,
        organizer_aid_fixture::config(),
        false,
        false,
    );
    let catalog = base.catalog().clone();
    let mut state = base.material().state().clone();
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let payer = AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]));
    let total = e
        .book
        .total_cash_and_reserves()
        .expect("the fixture book totals without overflow");
    // Exact conserved Designed opening allocation: the future aid payer starts
    // zero, with its six captured micros held as donor savings instead.
    e.book
        .transfer_cash(
            payer,
            AccountId::Household(organizer_aid_fixture::household()),
            organizer_aid_fixture::money(6),
            CashTransferPurpose::PublicTransfer,
        )
        .expect("the fixture transfer stays funded");
    assert_eq!(
        e.book
            .cash(payer)
            .expect("the fixture book holds the payer account")
            .micro_units(),
        0
    );
    assert_eq!(
        e.book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        total
    );
    let costs = e.costs.snapshot();
    e.costs = HistoricalCostBook::open(
        &e.book,
        costs.stocks,
        costs.freight,
        costs.equity,
        costs.equipment,
    )
    .expect("the fixture opens the authored source");
    let recurring = e
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    recurring.household_purchases[0].target_closing_stock = if no_attendance { 4 } else { 8 };
    recurring.household_purchases[0].enabled = !no_attendance;
    if no_attendance {
        for row in &mut recurring.attendance {
            row.planned_hours = 0;
        }
    }
    let mut cfg = serde_json::to_value(collection_config_for_control())
        .expect("the value serializes to JSON");
    cfg["collection"]["maximum_cash_micros"] =
        Value::String(if no_attendance { "2" } else { "6" }.into());
    organizer_aid_fixture::try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        organizer_aid_fixture::Materials { catalog, state },
        serde_json::from_value(cfg).expect("the JSON value matches the declared type"),
    )
    .expect("the fixture opens a session")
}
#[test]
fn savings_can_collect_with_zero_current_funded_attendance() {
    use babylon_material_circuit::AccountId;
    let session = collection_savings_control(true);
    let collect: OrganizerChoice =
        serde_json::from_str("\"collect\"").expect("the authored JSON matches the declared schema");
    let accepted = organizer_aid_fixture::commitment(&session, collect);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let decoded = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .expect("the canonical bytes decode into the declared type");
    assert_eq!(
        decoded
            .member_labor_use
            .iter()
            .map(|row| row.attended_hours)
            .sum::<u64>(),
        0
    );
    assert_eq!(
        decoded
            .income
            .iter()
            .find(|row| row.account == AccountId::Household(organizer_aid_fixture::household()))
            .expect("the fixture holds the searched element")
            .statement
            .wage_income
            .micro_units(),
        0
    );
    let value = serde_json::to_value(candidate.material().register().history())
        .expect("the value serializes to JSON");
    assert_eq!(
        value["collection_receipts"][0]["fact"]["collected_cash_micros"],
        "2"
    );
    assert_eq!(
        value["collection_receipts"][0]["fact"]["performed_hours"],
        2
    );
    let CircuitAccounting::Monetary(e) = &candidate.material().register().state().accounting else {
        unreachable!()
    };
    assert_eq!(
        e.book
            .cash(AccountId::Household(organizer_aid_fixture::household()))
            .expect("the fixture book holds the payer account")
            .micro_units(),
        4
    );
}
#[test]
fn original_collection_funds_only_separately_authorized_later_aid() {
    let mut paid = collection_savings_control(false);
    let mut severed = collection_savings_control(false);
    let collect: OrganizerChoice =
        serde_json::from_str("\"collect\"").expect("the authored JSON matches the declared schema");
    let accepted = organizer_aid_fixture::commitment(&paid, collect);
    let paid_candidate = organizer_aid_fixture::prepare(&paid, Some(&accepted));
    let paid_rows = babylon_tick::material_world::decode_material_receipts(
        paid_candidate.material().receipt_bytes(),
    )
    .expect("the canonical bytes decode into the declared type");
    assert!(paid_rows.aid.is_empty());
    let value = serde_json::to_value(paid_candidate.material().register().history())
        .expect("the value serializes to JSON");
    assert_eq!(
        value["collection_receipts"][0]["fact"]["collected_cash_micros"],
        "6"
    );
    assert_eq!(
        paid_rows
            .income
            .iter()
            .find(|row| row.account
                == babylon_material_circuit::AccountId::Organization(
                    babylon_material_circuit::OrganizationAccountId::from_bytes([96; 32])
                ))
            .expect("the fixture holds the searched element")
            .statement
            .gift_income
            .micro_units(),
        6
    );
    let held = organizer_aid_fixture::commitment(&severed, OrganizerChoice::Hold);
    let severed_candidate = organizer_aid_fixture::prepare(&severed, Some(&held));
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(&mut paid, &mut sink, paid_candidate);
    organizer_aid_fixture::commit(&mut severed, &mut sink, severed_candidate);
    let aid = organizer_aid_fixture::commitment(&paid, OrganizerChoice::LocalAid);
    let absent = organizer_aid_fixture::commitment(&severed, OrganizerChoice::LocalAid);
    let paid_next = organizer_aid_fixture::prepare(&paid, Some(&aid));
    let severed_next = organizer_aid_fixture::prepare(&severed, Some(&absent));
    let actual = babylon_tick::material_world::decode_material_receipts(
        paid_next.material().receipt_bytes(),
    )
    .expect("the canonical bytes decode into the declared type");
    let counterfactual = babylon_tick::material_world::decode_material_receipts(
        severed_next.material().receipt_bytes(),
    )
    .expect("the canonical bytes decode into the declared type");
    assert!(actual
        .aid
        .iter()
        .any(|row| row.outcome == AidOutcome::Granted
            && row.cash_amount.micro_units() == 6
            && row.quantity == 2));
    assert!(!counterfactual
        .aid
        .iter()
        .any(|row| row.outcome == AidOutcome::Granted));
    assert!(actual
        .household_consumption
        .iter()
        .any(|row| row.principal_id == organizer_aid_fixture::recipient()
            && row.consumed_quantity == 1));
    assert_eq!(
        paid.material()
            .organizer_state()
            .expect("the fixture register carries organizer state")
            .period,
        1
    );
}

#[test]
fn opening_collection_projection_requires_exact_existing_payer_and_labor_unit() {
    use babylon_practice_contract::initial_organizer_state;
    let base = organizer_aid_fixture::authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        organizer_aid_fixture::config(),
        false,
        false,
    );
    let catalog = base.catalog().clone();
    let material = base.material().state().clone();
    let good = collection_config_for_control();
    assert!(
        MaterialWorldRegister::try_new(&catalog, 0, material.clone())
            .expect("the authored fixture satisfies the constructor invariants")
            .with_organizer(
                &catalog,
                good.clone(),
                initial_organizer_state(&good)
                    .expect("the authored config admits an opening organizer state"),
                babylon_practice_contract::OrganizerPeriodJournal::empty(),
            )
            .is_ok()
    );
    for field in ["organization_account_id", "labor_unit_id"] {
        let mut value = serde_json::to_value(&good).expect("the value serializes to JSON");
        value["collection"][field] =
            serde_json::to_value([97_u8; 32].to_vec()).expect("the value serializes to JSON");
        let changed: OrganizerConfig =
            serde_json::from_value(value).expect("the JSON value matches the declared type");
        babylon_practice_contract::validate_organizer_config(&changed)
            .expect("the authored organizer config passes validation");
        assert!(
            MaterialWorldRegister::try_new(&catalog, 0, material.clone())
                .expect("the authored fixture satisfies the constructor invariants")
                .with_organizer(
                    &catalog,
                    changed.clone(),
                    initial_organizer_state(&changed)
                        .expect("the authored config admits an opening organizer state"),
                    babylon_practice_contract::OrganizerPeriodJournal::empty(),
                )
                .is_err(),
            "{field}"
        );
    }
}
#[test]
fn historical_actual_collection_preserves_original_consent_and_donor_pledge_admission() {
    use babylon_practice_contract::OrganizerGiftConsent;
    let session = collection_control_session(4, false);
    let collect: OrganizerChoice =
        serde_json::from_str("\"collect\"").expect("the authored JSON matches the declared schema");
    let accepted = organizer_aid_fixture::commitment(&session, collect);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let actual = &candidate
        .material()
        .register()
        .history()
        .collection_receipts[0];
    let cfg = session
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config");
    babylon_practice_contract::validate_organizer_collection_fact(
        cfg,
        &actual.commitment,
        &actual.fact,
    )
    .expect("the authored fixture satisfies the rule");
    let mut refused = cfg.clone();
    refused
        .collection
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .cash_consent = OrganizerGiftConsent::Refuse;
    assert!(
        babylon_practice_contract::validate_organizer_collection_fact(
            &refused,
            &actual.commitment,
            &actual.fact
        )
        .is_err()
    );
    let mut insufficient = cfg.clone();
    let donor = insufficient
        .participants
        .iter_mut()
        .find(|p| p.contributor_id == 201)
        .expect("the fixture holds the searched element");
    for pledge in &mut donor.commitments {
        if pledge.actor_id == 101 {
            pledge.hours = 1;
        }
    }
    assert!(
        babylon_practice_contract::validate_organizer_collection_fact(
            &insufficient,
            &actual.commitment,
            &actual.fact
        )
        .is_err()
    );
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`partial_collection_preserves_protected_floor_and_matches_actual_transfer_and_time` keeps one authored boundary's fixture and assertions together"
)]
fn partial_collection_preserves_protected_floor_and_matches_actual_transfer_and_time() {
    use babylon_material_circuit::{AccountId, OrganizationAccountId};
    let base = collection_savings_control(true);
    let mut cfg = base
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config")
        .clone();
    let terms = cfg
        .collection
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    terms.maximum_cash_micros = 8;
    terms.protected_cash_floor_micros = 2;
    let session = organizer_aid_fixture::try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        organizer_aid_fixture::Materials {
            catalog: base.catalog().clone(),
            state: base.material().state().clone(),
        },
        cfg,
    )
    .expect("the fixture opens a session");
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::Collect);
    let before = session.material().canonical_bytes().to_vec();
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    assert_eq!(session.material().canonical_bytes(), before);
    let organizer = candidate
        .material()
        .register()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let actual = serde_json::to_value(candidate.material().register().history())
        .expect("the value serializes to JSON");
    let fact = &actual["collection_receipts"][0]["fact"];
    assert_eq!(fact["requested_cash_micros"], "8");
    assert_eq!(fact["collected_cash_micros"], "4");
    assert_eq!(fact["outcome"], "partially_collected");
    assert_eq!(fact["performed_hours"], 2);
    assert_eq!(
        candidate
            .material()
            .register()
            .history()
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .outcome,
        OrganizerOutcome::CollectionCompleted
    );
    assert_eq!(
        organizer.agreements,
        session
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state")
            .agreements
    );
    assert_eq!(
        organizer.contact_products,
        session
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state")
            .contact_products
    );
    let decoded = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .expect("the canonical bytes decode into the declared type");
    let donor = AccountId::Household(organizer_aid_fixture::household());
    let recipient = AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]));
    let ordinal = usize::try_from(
        fact["transfer_ordinal"]
            .as_u64()
            .expect("the JSON fixture field is an unsigned integer"),
    )
    .expect("the fixture value fits the target range");
    assert_eq!(
        decoded.money_transfers[ordinal].debit.delta.micro_units(),
        -4
    );
    assert_eq!(
        decoded.money_transfers[ordinal].credit.delta.micro_units(),
        4
    );
    assert_eq!(
        decoded
            .income
            .iter()
            .find(|row| row.account == donor)
            .expect("the fixture holds the searched element")
            .statement
            .gift_expense
            .micro_units(),
        4
    );
    assert_eq!(
        decoded
            .income
            .iter()
            .find(|row| row.account == recipient)
            .expect("the fixture holds the searched element")
            .statement
            .gift_income
            .micro_units(),
        4
    );
    let CircuitAccounting::Monetary(e) = &candidate.material().register().state().accounting else {
        unreachable!()
    };
    assert_eq!(
        e.book
            .cash(donor)
            .expect("the fixture book holds the payer account")
            .micro_units(),
        2
    );
    assert_eq!(
        e.book
            .cash(recipient)
            .expect("the fixture book holds the payer account")
            .micro_units(),
        4
    );
    let HouseholdTimeAccounting::Modeled(time) = &e.household_time else {
        unreachable!()
    };
    assert_eq!(
        time.contributions
            .iter()
            .filter(|row| row.contribution.contributor_id == 201)
            .count(),
        1
    );
    assert_eq!(
        time.contributions
            .iter()
            .filter(|row| row.contribution.contributor_id == 201)
            .map(|row| row.contribution.hours)
            .sum::<u64>(),
        2
    );
}

fn capped_collection_session(cap: i128, floor: i128) -> Session {
    let base = collection_savings_control(true);
    let mut config = base
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config")
        .clone();
    let terms = config
        .collection
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    terms.maximum_cash_micros = cap;
    terms.protected_cash_floor_micros = floor;
    organizer_aid_fixture::try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        organizer_aid_fixture::Materials {
            catalog: base.catalog().clone(),
            state: base.material().state().clone(),
        },
        config,
    )
    .expect("the fixture opens a session")
}

fn material_collection_input(session: &Session) -> CollectionResolveInput {
    let accepted = organizer_aid_fixture::commitment(session, OrganizerChoice::Collect);
    let terms = session
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config")
        .collection
        .as_ref()
        .expect("the fixture set the optional field before this read");
    CollectionResolveInput {
        original_commitment_id: accepted.commitment_id,
        command_nonce: accepted.command.nonce,
        admitted_period: accepted.command.expected_period,
        resolve_period: accepted.resolves_period,
        mandate_id: terms.mandate_id,
        source_hash: terms.source_hash,
        actor_id: terms.actor_id,
        contributor_id: terms.contributor_id,
        donor: FinalDemandPrincipalId::from_bytes(terms.household_principal_id),
        recipient: babylon_material_circuit::OrganizationAccountId::from_bytes(
            terms.organization_account_id,
        ),
        labor_unit_id: UnitId::from_bytes(terms.labor_unit_id),
        cash_consent: true,
        requested: organizer_aid_fixture::money(terms.maximum_cash_micros),
        protected_cash_floor: organizer_aid_fixture::money(terms.protected_cash_floor_micros),
        collection_hours: terms.collection_hours,
        pledged_hours: session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config")
            .participants
            .iter()
            .find(|row| row.contributor_id == terms.contributor_id)
            .expect("the fixture holds the searched element")
            .commitments
            .iter()
            .filter(|row| row.actor_id == terms.actor_id)
            .map(|row| row.hours)
            .sum(),
    }
}

#[test]
fn collection_independent_consent_and_fixed_pledge_gate_admission_and_material_close() {
    use babylon_practice_contract::{OrganizerError, OrganizerGiftConsent, OrganizerRefusal};
    let session = capped_collection_session(8, 2);
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::Collect);
    let config = session
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config");
    let state = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    for consent in [true, false] {
        let mut refused = config.clone();
        if consent {
            refused
                .collection
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .cash_consent = OrganizerGiftConsent::Refuse;
        } else {
            refused
                .participants
                .iter_mut()
                .find(|row| row.contributor_id == 201)
                .expect("the fixture holds the searched element")
                .commitments
                .iter_mut()
                .find(|row| row.actor_id == 101)
                .expect("the fixture holds the searched element")
                .hours = 1;
        }
        assert_eq!(
            admit_organizer(&refused, state, &accepted.command),
            Err(OrganizerError::Refused(if consent {
                OrganizerRefusal::CollectionCashRefused
            } else {
                OrganizerRefusal::InsufficientCommittedTime
            }))
        );
        let mut input = material_collection_input(&session);
        if consent {
            input.cash_consent = false;
        } else {
            input.pledged_hours = 1;
        }
        let closed =
            close_collection_control(session.catalog(), session.material().state(), &[], &[input])
                .expect(
                    "the fixture call `close_collection_control` succeeds for the authored inputs",
                );
        let row = &closed.collections[0];
        assert_eq!(row.collected.micro_units(), 0);
        assert_eq!(row.performed_hours, 0);
        assert_eq!(row.transfer_ordinal, None);
        assert_eq!(
            row.outcome,
            if consent {
                babylon_material_circuit::CollectionOutcome::CashConsentRefused
            } else {
                babylon_material_circuit::CollectionOutcome::InsufficientContributionTime
            }
        );
    }
}

#[test]
fn collection_zero_eligible_cash_and_missing_actual_time_refuse_without_spending() {
    for (session, expected) in [
        (
            capped_collection_session(8, 8),
            OrganizerCollectionOutcome::InsufficientCash,
        ),
        (
            collection_control_session(4, true),
            OrganizerCollectionOutcome::InsufficientContributionTime,
        ),
    ] {
        let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::Collect);
        let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
        let actual = candidate.material().register().history();
        let fact = &actual.collection_receipts[0].fact;
        assert_eq!(fact.outcome, expected);
        assert_eq!(fact.collected_cash_micros, 0);
        assert_eq!(fact.performed_hours, 0);
        assert_eq!(fact.transfer_ordinal, None);
        let CircuitAccounting::Monetary(e) = &candidate.material().register().state().accounting
        else {
            unreachable!()
        };
        let HouseholdTimeAccounting::Modeled(time) = &e.household_time else {
            unreachable!()
        };
        assert!(time.contributions.is_empty());
    }
}

#[test]
fn external_register_reopen_adopts_authenticated_bytes_and_rejects_wire_changes() {
    let mut session = capped_collection_session(8, 2);
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::Collect);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    organizer_aid_fixture::commit(&mut session, &mut CollectingSink::default(), candidate);
    let canonical = session.material().canonical_bytes();
    let input = canonical.to_vec();
    let allocation = input.as_ptr();
    let catalog = session.catalog().clone();
    let owned = MaterialWorldRegister::decode_external(&catalog, input)
        .expect("the canonical bytes decode");
    let borrowed = MaterialWorldRegister::decode_external(&catalog, canonical.to_vec())
        .expect("the committed canonical bytes decode");
    assert_eq!(owned, borrowed);
    assert_eq!(owned, *session.material());
    assert_eq!(owned.digest(), session.material().digest());
    assert_eq!(owned.history().collection_receipts.len(), 1);
    assert!(
        std::ptr::eq(owned.canonical_bytes().as_ptr(), allocation),
        "owned admission must retain the exact authenticated input allocation"
    );
    let domain = b"babylon.material-world-register.v4\0".len();
    for offset in [0, domain, domain + 11, domain + 19, canonical.len() - 1] {
        let mut invalid = canonical.to_vec();
        invalid[offset] ^= 1;
        MaterialWorldRegister::decode_external(&catalog, invalid)
            .expect_err("the malformed bytes are refused");
    }
    for length in [0, domain + 19, canonical.len() - 1] {
        let invalid = canonical[..length].to_vec();
        MaterialWorldRegister::decode_external(&catalog, invalid)
            .expect_err("the malformed bytes are refused");
    }
    let mut trailing = canonical.to_vec();
    trailing.push(0);
    MaterialWorldRegister::decode_external(&catalog, trailing)
        .expect_err("the malformed bytes are refused");
}

#[test]
fn partial_collection_failure_exact_retry_and_reopen_publish_one_original_receipt() {
    let mut session = capped_collection_session(8, 2);
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::Collect);
    let before = session.material().canonical_bytes().to_vec();
    let graph_before = session
        .graph_session()
        .graph()
        .encode_state()
        .expect("the graph encodes its canonical state")
        .as_bytes()
        .to_vec();
    let hash_before = session
        .current_world_hash()
        .expect("the committed session publishes a world hash");
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let expected = *candidate.identity();
    let expected_bytes = candidate.material().receipt_bytes().to_vec();
    let mut sink = CollectingSink::default();
    assert!(matches!(
        session.commit_prepared_and_publish(&mut sink, candidate, |_, _| {
            Err::<ReplayCommitDisposition, _>("injected collection durable failure")
        }),
        Err(babylon_tick::material_replay::MaterialCommitError::Commit(
            "injected collection durable failure"
        ))
    ));
    assert_eq!(session.material().canonical_bytes(), before);
    assert_eq!(
        session
            .graph_session()
            .graph()
            .encode_state()
            .expect("the graph encodes its canonical state")
            .as_bytes(),
        graph_before
    );
    assert_eq!(
        session
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        hash_before
    );
    assert_eq!(session.completed_tick(), 0);
    assert!(sink.events.is_empty());
    let retry = organizer_aid_fixture::prepare(&session, Some(&accepted));
    assert_eq!(*retry.identity(), expected);
    assert_eq!(retry.material().receipt_bytes(), expected_bytes);
    organizer_aid_fixture::commit(&mut session, &mut sink, retry);
    let reopened = MaterialWorldRegister::decode_external(
        session.catalog(),
        session.material().canonical_bytes().to_vec(),
    )
    .expect("the committed canonical bytes decode");
    assert_eq!(reopened, *session.material());
    let organizer = reopened
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let organizer_entries = reopened.history();
    assert_eq!(organizer_entries.collection_receipts.len(), 1);
    assert_eq!(
        organizer_entries.collection_receipts[0].commitment,
        accepted
    );
    assert_eq!(
        organizer_entries.collection_receipts[0]
            .fact
            .collected_cash_micros,
        4
    );
    assert!(admit_organizer(
        reopened
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        organizer,
        &accepted.command
    )
    .is_err());
    let mut conflicting = accepted.command.clone();
    conflicting.choice = OrganizerChoice::LocalAid;
    assert!(admit_organizer(
        reopened
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        organizer,
        &conflicting
    )
    .is_err());
    assert_eq!(
        reopened.canonical_bytes(),
        session.material().canonical_bytes()
    );
}

#[test]
fn partial_collection_canonical_row_rejects_fabricated_amount_tag_time_and_join() {
    let session = capped_collection_session(8, 2);
    let accepted = organizer_aid_fixture::commitment(&session, OrganizerChoice::Collect);
    let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
    let bytes = candidate.material().receipt_bytes();
    let decoded = babylon_tick::material_world::decode_material_receipts(bytes)
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(decoded.collections.len(), 1);
    assert_eq!(decoded.collections[0].outcome as u8, 9);
    let row = bytes.len() - 317;
    assert_eq!(bytes[row + 280], 9);
    let original_fact = &candidate
        .material()
        .register()
        .history()
        .collection_receipts[0]
        .fact;
    for (amount, outcome) in [(0_i128, 9_u8), (8, 9), (9, 9), (4, 1), (4, 10)] {
        let mut changed = bytes.to_vec();
        changed[row + 256..row + 272].copy_from_slice(&amount.to_be_bytes());
        changed[row + 280] = outcome;
        assert!(babylon_tick::material_world::decode_material_receipts(&changed).is_err());
    }
    for offset in [256_usize, 272, 281, 285] {
        let mut changed = bytes.to_vec();
        changed[row + offset] ^= 1;
        assert!(
            babylon_tick::material_world::decode_material_receipts(&changed).is_err(),
            "offset {offset}"
        );
    }
    for kind in 0..6 {
        let mut fact = original_fact.clone();
        match kind {
            0 => fact.collected_cash_micros = 8,
            1 => fact.collected_cash_micros = 0,
            2 => fact.performed_hours = 1,
            3 => fact.transfer_ordinal = None,
            4 => fact.contribution_use_id = [0; 32],
            _ => fact.requested_cash_micros = 9,
        }
        assert!(
            babylon_practice_contract::validate_organizer_collection_fact(
                session
                    .material()
                    .organizer_config()
                    .expect("the fixture register carries organizer config"),
                &accepted,
                &fact,
            )
            .is_err()
        );
    }
    let mut changed = serde_json::to_value(candidate.material().register().history())
        .expect("the value serializes to JSON");
    changed["collection_receipts"][0]["fact"]["outcome"] = serde_json::json!("collected");
    let changed: babylon_practice_contract::OrganizerPeriodJournalEntries =
        serde_json::from_value(changed).expect("the JSON value matches the declared type");
    assert!(
        babylon_practice_contract::validate_organizer_period_entries(
            session
                .material()
                .organizer_config()
                .expect("the fixture register carries organizer config"),
            &changed,
        )
        .is_err()
    );
}

#[test]
fn collection_duplicate_and_unfunded_due_commitment_never_mint_a_second_transfer() {
    use babylon_material_circuit::{
        AccountId, CapitalContributionOrder, CollectionOutcome, ContributionId,
        EquityCarryingValue, HistoricalCostBook, MaterialCircuitError, OwnershipClaim,
    };
    let session = capped_collection_session(8, 2);
    let input = material_collection_input(&session);
    let opening = session.material().state();
    let before = opening.clone();
    let mut conflicting = input.clone();
    conflicting.command_nonce = [8; 16];
    for second in [input.clone(), conflicting] {
        assert!(matches!(
            close_collection_control(session.catalog(), opening, &[], &[input.clone(), second],),
            Err(MaterialCircuitError::RowLimit)
        ));
        assert_eq!(*opening, before);
    }
    let mut due = opening.clone();
    let CircuitAccounting::Monetary(e) = &mut due.accounting else {
        unreachable!()
    };
    let donor = AccountId::Household(organizer_aid_fixture::household());
    e.financial.ownership.push(OwnershipClaim {
        issuer_site_id: organizer_aid_fixture::site(1),
        beneficiary: donor,
        shares: 1,
    });
    let mut costs = e.costs.snapshot();
    costs.equity.push(EquityCarryingValue {
        owner: donor,
        issuer_site_id: organizer_aid_fixture::site(1),
        amount: organizer_aid_fixture::money(0),
    });
    e.costs = HistoricalCostBook::open(
        &e.book,
        costs.stocks,
        costs.freight,
        costs.equity,
        costs.equipment,
    )
    .expect("the fixture opens the authored source");
    e.financial.contributions.push(CapitalContributionOrder {
        id: ContributionId::from_bytes([80; 32]),
        due_period: 1,
        contributor: AccountId::Household(organizer_aid_fixture::household()),
        issuer_site_id: organizer_aid_fixture::site(1),
        amount: organizer_aid_fixture::money(8),
    });
    let closed = close_collection_control(session.catalog(), &due, &[], &[input])
        .expect("the fixture call `close_collection_control` succeeds for the authored inputs");
    assert_eq!(
        closed.collections[0].outcome,
        CollectionOutcome::DuePaymentUnmet
    );
    assert_eq!(closed.collections[0].collected.micro_units(), 0);
    assert_eq!(closed.collections[0].performed_hours, 0);
    assert!(closed
        .contributions
        .iter()
        .any(|row| row.unfunded.micro_units() == 2));
}

fn close_collection_control(
    catalog: &MaterialCatalog,
    opening: &MaterialCircuitState,
    aid: &[AidResolveInput],
    collection: &[CollectionResolveInput],
) -> Result<MaterialCircuitTransition, babylon_material_circuit::MaterialCircuitError> {
    let closed = babylon_material_circuit::close_material_period_with_support(
        catalog, opening, aid, collection,
    )?;
    let next_labor = opening
        .labor
        .iter()
        .filter(|row| row.period == closed.next_period())
        .cloned()
        .collect();
    let CircuitAccounting::Monetary(economy) = &opening.accounting else {
        unreachable!()
    };
    let next_member_labor = economy
        .member_labor
        .iter()
        .filter(|row| row.period == closed.next_period())
        .cloned()
        .collect();
    closed.finish_with_workforce(catalog, next_labor, next_member_labor)
}

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn run_dual_aid_schedule(separated: bool, refuses_remote: bool) {
    use babylon_practice_contract::OrganizerAidSupportStatus;
    let mut session = dual_aid_schedule::session(refuses_remote);
    let mut sink = CollectingSink::default();
    let schedule: &[OrganizerChoice] = if separated {
        &[
            OrganizerChoice::RemoteAid,
            OrganizerChoice::PauseStanding,
            OrganizerChoice::LocalAid,
        ]
    } else {
        &[OrganizerChoice::RemoteAid, OrganizerChoice::LocalAid]
    };
    let mut original = Vec::new();
    let mut actual_grants = BTreeSet::new();
    for &choice in schedule {
        let accepted = organizer_aid_fixture::commitment(&session, choice);
        if matches!(
            choice,
            OrganizerChoice::RemoteAid | OrganizerChoice::LocalAid
        ) {
            original.push(accepted.commitment_id);
        }
        let candidate = organizer_aid_fixture::prepare(&session, Some(&accepted));
        let rows = material_world::decode_material_receipts(candidate.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type");
        for grant in rows.aid.iter().filter(|r| r.outcome == AidOutcome::Granted) {
            assert_eq!(
                (grant.quantity, grant.cash_amount),
                (1, organizer_aid_fixture::money(3))
            );
            let consumed = rows
                .household_consumption
                .iter()
                .find(|r| r.principal_id == grant.recipient)
                .expect("the fixture holds the searched element");
            assert_eq!(
                (
                    consumed.good_id,
                    consumed.unit_id,
                    consumed.consumed_quantity
                ),
                (grant.good_id, grant.unit_id, 1)
            );
            let posted = rows
                .money_transfers
                .iter()
                .filter(|r| {
                    r.purpose
                        == babylon_material_circuit::MoneyTransferPurpose::AidGrant(
                            grant.commitment_id,
                        )
                })
                .map(|r| {
                    assert_eq!(
                        r.debit.location,
                        babylon_material_circuit::MoneyLocation::AidReserve(grant.commitment_id)
                    );
                    assert_eq!(
                        r.credit.location,
                        babylon_material_circuit::MoneyLocation::Cash(
                            babylon_material_circuit::AccountId::Household(grant.recipient)
                        )
                    );
                    assert_eq!(
                        r.debit.delta.micro_units().checked_neg(),
                        Some(r.credit.delta.micro_units())
                    );
                    r.credit.delta.micro_units()
                })
                .try_fold(0_i128, i128::checked_add)
                .expect("the fixture input satisfies the fallible conversion");
            assert_eq!(posted, 3);
            actual_grants.insert(grant.commitment_id.as_bytes());
        }
        organizer_aid_fixture::commit(&mut session, &mut sink, candidate);
    }
    let journal = session
        .material()
        .organizer_journal()
        .expect("the fixture register carries organizer journal");
    let rows = journal
        .periods
        .iter()
        .flat_map(|entries| &entries.aid_receipts)
        .collect::<Vec<_>>();
    let remote = rows
        .iter()
        .rev()
        .find(|r| r.authorization.gift.kind == OrganizerAidKind::Remote)
        .expect("the fixture holds the searched element");
    let local = rows
        .iter()
        .rev()
        .find(|r| r.authorization.gift.kind == OrganizerAidKind::Local)
        .expect("the fixture holds the searched element");
    for (row, id) in [(remote, original[0]), (local, original[1])] {
        assert_eq!(row.authorization.gift.commitment.commitment_id, id);
        assert!(matches!(
            row.support.status,
            OrganizerAidSupportStatus::Granted {
                granted_quantity: 1,
                consumed_quantity: 1
            }
        ));
        assert!(actual_grants.contains(&row.support.material_commitment_id));
        // Remote terminal support describes arrival: dispatch/time/reservation were
        // charged in the preceding period, never again on delivery.
        if row.authorization.gift.kind == OrganizerAidKind::Remote {
            assert_actual_aid_postings(&row.support, 0, 0, 0, 3, 0);
        } else {
            assert_actual_aid_postings(&row.support, 1, 2, 3, 3, 0);
        }
        assert_dual_aid_practice_time(row);
    }
    assert_eq!(
        local.practice.outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert_eq!(
        remote.practice.outcome,
        if refuses_remote {
            OrganizerOutcome::AidPracticeUncompleted
        } else if separated {
            OrganizerOutcome::AidPracticeCompleted
        } else {
            OrganizerOutcome::InsufficientTime
        }
    );
    // Every actual period remains bounded by the same2h controlled-actor commitment.
    for period in 1..=schedule.len() as u64 {
        let state = session.material().history();
        let ordinary = state
            .receipts
            .iter()
            .filter(|r| r.period == period)
            .flat_map(|r| &r.time_use);
        let aid = state
            .aid_receipts
            .iter()
            .filter(|r| r.practice.period == period)
            .flat_map(|r| &r.practice.time_use);
        let debit = ordinary
            .chain(aid)
            .filter(|r| r.actor_id == 101)
            .try_fold(0_u64, |a, r| a.checked_add(r.hours))
            .expect("the fixture input satisfies the fallible conversion");
        assert!(debit <= 2);
    }
    let CircuitAccounting::Monetary(e) = &session.material().state().accounting else {
        unreachable!()
    };
    assert_eq!(
        e.book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        organizer_aid_fixture::money(100)
    );
    assert_eq!(
        MaterialWorldRegister::decode_external(
            session.catalog(),
            session.material().canonical_bytes().to_vec(),
        )
        .expect("the committed canonical bytes decode"),
        *session.material()
    );
}
fn assert_dual_aid_practice_time(row: &OrganizerAidResolutionReceipt) {
    use babylon_practice_contract::OrganizerPartnerResponse;
    let controlled = row
        .practice
        .time_use
        .iter()
        .filter(|r| r.actor_id == 101)
        .try_fold(0_u64, |a, r| a.checked_add(r.hours))
        .expect("the fixture input satisfies the fallible conversion");
    let completed = row.practice.outcome == OrganizerOutcome::AidPracticeCompleted;
    assert_eq!(controlled, row.practice.hours_spent);
    assert_eq!(
        controlled,
        if row.practice.outcome == OrganizerOutcome::InsufficientTime {
            0
        } else {
            2
        }
    );
    if completed {
        assert_eq!(
            row.practice.partner_response,
            OrganizerPartnerResponse::Participated
        );
    }
}

#[test]
fn colliding_aid_practices_refuse_fictitious_second_time_debit() {
    run_dual_aid_schedule(false, false);
}
#[test]
fn separated_aid_schedule_completes_both_original_independent_practices() {
    run_dual_aid_schedule(true, false);
}
#[test]
fn consumed_remote_gift_does_not_force_independent_participation() {
    run_dual_aid_schedule(true, true);
}
