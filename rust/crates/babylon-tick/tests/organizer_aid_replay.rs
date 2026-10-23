//! Real BSL/tick gift, scarce time and independent partner controls.
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;
#[path = "support/organizer_aid_fixture.rs"]
mod organizer_aid_fixture;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::state_hash::CanonicalState;
use babylon_material_circuit::{
    AidOutcome, CircuitAccounting, CommodityKind, HouseholdTimeAccounting,
};
use babylon_practice_contract::{
    admit_organizer, OrganizerAidKind, OrganizerChoice, OrganizerOutcome, OrganizerPartnerPolicy,
    OrganizerTimeBindingMode,
};
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;
use organizer_aid_fixture::*;

#[test]
fn fulfilled_gift_uses_real_time_before_later_coordination() {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap();
    let parts = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation_fixture_parts();
    let mut remaining = foundation.canonical_bytes();
    for part in parts {
        let (prefix, tail) = remaining.split_at(part.len());
        assert_eq!(prefix, part);
        remaining = tail;
    }
    assert!(remaining.is_empty());
    let mut session = authored_session(foundation, config(), false, false);
    let accepted = commitment(&session, OrganizerChoice::LocalAid);
    let candidate = prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    commit(&mut session, &mut sink, candidate);
    let receipt = session
        .material()
        .organizer_state()
        .unwrap()
        .aid_receipts
        .last()
        .map(|row| &row.practice)
        .unwrap();
    assert_actual_aid_postings(
        &session
            .material()
            .organizer_state()
            .unwrap()
            .aid_receipts
            .last()
            .unwrap()
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
            .filter(|r| r.contribution.principal_id == household())
            .map(|r| r.contribution.hours)
            .sum::<u64>(),
        4
    );
    assert_eq!(
        economy
            .recurring
            .as_ref()
            .unwrap()
            .household_stocks
            .iter()
            .find(|r| r.principal_id == recipient())
            .unwrap()
            .quantity,
        1
    );
}
#[test]
fn captured_promises_cannot_replace_zero_actual_household_time() {
    let mut session = authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        config(),
        true,
        false,
    );
    let accepted = commitment(&session, OrganizerChoice::LocalAid);
    let candidate = prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    commit(&mut session, &mut sink, candidate);
    assert_eq!(
        session
            .material()
            .organizer_state()
            .unwrap()
            .aid_receipts
            .last()
            .unwrap()
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
            .organizer_state()
            .unwrap()
            .aid_receipts
            .last()
            .unwrap()
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
            .unwrap()
            .household_stocks
            .iter()
            .find(|r| r.principal_id == recipient())
            .unwrap()
            .quantity,
        0
    );
}
#[test]
fn recipient_practice_refusal_does_not_revoke_granted_food() {
    let mut cfg = config();
    cfg.aid_bindings[0].coordination_hours = 1;
    cfg.aid_bindings[0].partner.policy = OrganizerPartnerPolicy::Refuse;
    let mut session = authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        cfg,
        false,
        false,
    );
    let accepted = commitment(&session, OrganizerChoice::LocalAid);
    let candidate = prepare(&session, Some(&accepted));
    let mut sink = CollectingSink::default();
    commit(&mut session, &mut sink, candidate);
    let receipt = session
        .material()
        .organizer_state()
        .unwrap()
        .aid_receipts
        .last()
        .map(|row| &row.practice)
        .unwrap();
    assert_actual_aid_postings(
        &session
            .material()
            .organizer_state()
            .unwrap()
            .aid_receipts
            .last()
            .unwrap()
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
            .unwrap()
            .household_stocks
            .iter()
            .find(|r| r.principal_id == recipient())
            .unwrap()
            .quantity,
        1
    );
}

#[test]
fn delivered_consumed_support_funds_only_actual_independent_coordination() {
    let mut cfg = config();
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        cfg,
        false,
        false,
    );
    let opening = session.material().organizer_state().unwrap().clone();
    let accepted = commitment(&session, OrganizerChoice::LocalAid);
    let candidate = prepare(&session, Some(&accepted));
    let material = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .unwrap();
    assert!(material
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity == 2));
    let consumed = material
        .household_consumption
        .iter()
        .find(|r| r.principal_id == recipient())
        .unwrap();
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
    commit(&mut session, &mut sink, candidate);
    let next = session.material().organizer_state().unwrap();
    assert_actual_aid_postings(&next.aid_receipts.last().unwrap().support, 2, 4, 6, 6, 0);
    assert_eq!(
        next.receipts.last().unwrap().outcome,
        OrganizerOutcome::AidScheduled
    );
    assert!(next.receipts.last().unwrap().time_use.is_empty());
    assert_eq!(
        next.aid_receipts.last().unwrap().practice.outcome,
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
    for (principal, gross, used) in [(household(), 6, 5), (recipient(), 3, 2)] {
        assert_eq!(
            time.receipts
                .iter()
                .find(|r| r.principal_id == principal)
                .unwrap()
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
    let recovered = MaterialWorldRegister::decode(session.material().canonical_bytes()).unwrap();
    assert_eq!(recovered, *session.material());
}

#[test]
fn failed_gift_tick_publishes_nothing_and_exact_retry_preserves_receipt_identity() {
    let mut cfg = config();
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        cfg,
        false,
        false,
    );
    let accepted = commitment(&session, OrganizerChoice::LocalAid);
    let before = session.material().canonical_bytes().to_vec();
    let graph_before = session
        .graph_session()
        .graph()
        .encode_state()
        .unwrap()
        .as_bytes()
        .to_vec();
    let hash_before = session.current_world_hash().unwrap();
    let candidate = prepare(&session, Some(&accepted));
    let expected = *candidate.identity();
    let mut sink = CollectingSink::default();
    let result = session.commit_prepared_and_publish(&mut sink, candidate, |_| {
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
            .unwrap()
            .as_bytes(),
        graph_before
    );
    assert_eq!(session.current_world_hash().unwrap(), hash_before);
    assert_eq!(session.completed_tick(), 0);
    assert!(sink.events.is_empty());
    let retry = prepare(&session, Some(&accepted));
    assert_eq!(*retry.identity(), expected);
    commit(&mut session, &mut sink, retry);
    assert_eq!(session.completed_tick(), 1);
    assert_eq!(
        session.material().organizer_state().unwrap().receipts.len(),
        1
    );
}

#[test]
fn remote_support_keeps_original_authorization_until_arrival_without_another_command() {
    let mut cfg = config();
    cfg.aid_bindings[0].kind = OrganizerAidKind::Remote;
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        cfg,
        false,
        true,
    );
    let accepted = commitment(&session, OrganizerChoice::RemoteAid);
    let first = prepare(&session, Some(&accepted));
    let first_receipts =
        babylon_tick::material_world::decode_material_receipts(first.material().receipt_bytes())
            .unwrap();
    assert!(first_receipts
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Dispatched && r.quantity == 2));
    assert!(!first_receipts
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted));
    let mut sink = CollectingSink::default();
    commit(&mut session, &mut sink, first);
    let saved = MaterialWorldRegister::decode(session.material().canonical_bytes()).unwrap();
    assert_eq!(saved, *session.material());
    let waiting = saved.organizer_state().unwrap();
    assert_actual_aid_postings(&waiting.aid_receipts[0].support, 2, 4, 6, 0, 0);
    assert_eq!(waiting.pending_aid.len(), 1);
    assert_eq!(waiting.pending_aid[0].gift.commitment, accepted);
    assert_eq!(
        waiting.aid_receipts[0].practice.outcome,
        OrganizerOutcome::AidAwaitingSupport
    );
    assert!(waiting.aid_receipts[0].practice.time_use.is_empty());
    let second = prepare(&session, None);
    let second_receipts =
        babylon_tick::material_world::decode_material_receipts(second.material().receipt_bytes())
            .unwrap();
    assert!(second_receipts
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity == 2));
    assert!(second_receipts
        .household_consumption
        .iter()
        .any(|r| r.principal_id == recipient() && r.consumed_quantity == 1));
    commit(&mut session, &mut sink, second);
    let completed = session.material().organizer_state().unwrap();
    assert!(completed.pending_aid.is_empty());
    let resolution = completed.aid_receipts.last().unwrap();
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
        session.material().organizer_config().unwrap(),
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
            .unwrap()
            .contribution_available_hours;
        let used = time
            .contributions
            .iter()
            .filter(|r| r.contribution.principal_id == policy.principal_id)
            .map(|r| r.contribution.hours)
            .sum::<u64>();
        assert!(used <= available);
    }
    let recovered = MaterialWorldRegister::decode(session.material().canonical_bytes()).unwrap();
    assert_eq!(recovered, *session.material());
}

#[test]
fn workplace_report_converts_declared_mass_exactly_without_requiring_one_kg_units() {
    let mut cfg = config();
    cfg.time_binding = OrganizerTimeBindingMode::FixedTimeControl;
    cfg.aid_bindings.clear();
    cfg.participants.retain(|row| row.contributor_id != 204);
    let mut material = opening();
    material
        .commodities
        .iter_mut()
        .find(|r| r.good_id == good(1))
        .unwrap()
        .kind = CommodityKind::Storable {
        grams_per_unit: 14_000,
    };
    let session = try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        material,
        cfg,
    )
    .unwrap();
    let result = prepare(&session, None);
    let report = result
        .material()
        .register()
        .organizer_state()
        .unwrap()
        .last_workplace_facts
        .as_ref()
        .unwrap();
    assert_eq!(report.output_kg, 56);
    assert_eq!(report.performed_labor_hours, 4);
}

#[test]
fn workplace_report_refuses_nonintegral_kg_instead_of_rounding() {
    let mut cfg = config();
    cfg.time_binding = OrganizerTimeBindingMode::FixedTimeControl;
    cfg.aid_bindings.clear();
    cfg.participants.retain(|row| row.contributor_id != 204);
    let mut material = opening();
    material
        .commodities
        .iter_mut()
        .find(|row| row.good_id == good(1))
        .unwrap()
        .kind = CommodityKind::Storable {
        grams_per_unit: 1001,
    };
    let session = try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        material,
        cfg,
    )
    .unwrap();
    let actions = babylon_practice_contract::organizer_action_batch(
        session.material().organizer_config().unwrap(),
        session.material().organizer_state().unwrap(),
        None,
        session.graph_session().session_identity().clone(),
    )
    .unwrap();
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
    support: &babylon_practice_contract::OrganizerAidSupport,
    dispatched: u64,
    hours: u64,
    reserved: i128,
    granted: i128,
    refunded: i128,
) {
    let wire = serde_json::to_value(support).unwrap();
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
fn collection_config_for_control() -> babylon_practice_contract::OrganizerConfig {
    let base = authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        config(),
        false,
        false,
    );
    let CircuitAccounting::Monetary(e) = &base.material().state().accounting else {
        unreachable!()
    };
    let mut value = serde_json::to_value(config()).unwrap();
    value["collection"] = serde_json::json!({
        "mandate_id": ([93_u8;32].to_vec()), "source_hash": ([94_u8;32].to_vec()),
        "actor_id":101,"contributor_id":201,
        "household_principal_id": household().as_bytes().to_vec(),
        "organization_account_id":([96_u8;32].to_vec()),"social_class_target":([98_u8;32].to_vec()),
        "labor_unit_id": e.aid.mandates[0].labor_unit_id.as_bytes().to_vec(),
        "cash_consent":"accept","maximum_cash_micros":"2","protected_cash_floor_micros":"0","collection_hours":2
    });
    serde_json::from_value(value).unwrap()
}

fn collection_control_session(protected_target: u64, no_time: bool) -> Session {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap();
    let base = authored_session(foundation, config(), no_time, false);
    let mut opening = base.material().state().clone();
    let CircuitAccounting::Monetary(e) = &mut opening.accounting else {
        unreachable!()
    };
    // Authored fixture target: actual closing pantry remains protected and is
    // asserted independently after close. No altered consumption or cash facts.
    e.recurring.as_mut().unwrap().household_purchases[0].target_closing_stock = protected_target;
    try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        opening,
        collection_config_for_control(),
    )
    .unwrap()
}
#[test]
fn actual_collection_retains_original_cash_posting_and_material_time_once() {
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, MoneyLocation, MoneyTransferPurpose, OrganizationAccountId,
    };
    let mut session = collection_control_session(4, false);
    let collect: OrganizerChoice = serde_json::from_str("\"collect\"").unwrap();
    let accepted = commitment(&session, collect);
    let candidate = prepare(&session, Some(&accepted));
    let actual =
        serde_json::to_value(candidate.material().register().organizer_state().unwrap()).unwrap();
    let fact = &actual["collection_receipts"][0]["fact"];
    assert_eq!(fact["collected_cash_micros"], "2");
    assert_eq!(fact["performed_hours"], 2);
    assert_eq!(fact["outcome"], "collected");
    assert_eq!(
        actual["collection_receipts"][0]["commitment"]["command"]["nonce"],
        serde_json::to_value(accepted.command.nonce.to_vec()).unwrap()
    );
    let decoded = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .unwrap();
    let ordinal = usize::try_from(fact["transfer_ordinal"].as_u64().unwrap()).unwrap();
    let movement = &decoded.money_transfers[ordinal];
    assert_eq!(
        movement.purpose,
        MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
    );
    assert_eq!(
        movement.debit.location,
        MoneyLocation::Cash(AccountId::Household(household()))
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
            .filter(|row| row.contribution.principal_id == household())
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
            .unwrap()
            .household_stocks
            .iter()
            .find(|row| row.principal_id == household())
            .unwrap()
            .quantity,
        4
    );
    let old = session.material().organizer_state().unwrap();
    let new = candidate.material().register().organizer_state().unwrap();
    assert_eq!(new.agreements, old.agreements);
    assert_eq!(new.contact_products, old.contact_products);
    let mut sink = CollectingSink::default();
    commit(&mut session, &mut sink, candidate);
    let before = session.material().canonical_bytes().to_vec();
    let actions = babylon_practice_contract::organizer_action_batch(
        session.material().organizer_config().unwrap(),
        session.material().organizer_state().unwrap(),
        Some(&accepted),
        session.graph_session().session_identity().clone(),
    );
    assert!(actions.is_err());
    assert_eq!(session.material().canonical_bytes(), before);
}
#[test]
fn protected_closing_pantry_refuses_collection_despite_actual_cash() {
    let session = collection_control_session(8, false);
    let collect: OrganizerChoice = serde_json::from_str("\"collect\"").unwrap();
    let accepted = commitment(&session, collect);
    let candidate = prepare(&session, Some(&accepted));
    let actual =
        serde_json::to_value(candidate.material().register().organizer_state().unwrap()).unwrap();
    let fact = &actual["collection_receipts"][0]["fact"];
    assert_eq!(fact["outcome"], "protected_closing_stock_unmet");
    assert_eq!(fact["collected_cash_micros"], "0");
    assert_eq!(fact["performed_hours"], 0);
    assert_eq!(fact["transfer_ordinal"], serde_json::Value::Null);
    let mut omitted = actual.clone();
    omitted["collection_receipts"][0]["fact"]
        .as_object_mut()
        .unwrap()
        .remove("transfer_ordinal");
    assert!(serde_json::from_value::<babylon_practice_contract::OrganizerState>(omitted).is_err());
    let CircuitAccounting::Monetary(e) = &candidate.material().register().state().accounting else {
        unreachable!()
    };
    assert!(
        e.book
            .cash(babylon_material_circuit::AccountId::Household(household()))
            .unwrap()
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
    let collect: OrganizerChoice = serde_json::from_str("\"collect\"").unwrap();
    let accepted = commitment(&session, collect);
    let candidate = prepare(&session, Some(&accepted));
    let bytes = candidate.material().receipt_bytes();
    let decoded = babylon_tick::material_world::decode_material_receipts(bytes).unwrap();
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
    let domain = b"babylon.material-tick-receipts.v17\0".len();
    old[domain - 2] = b'6';
    old[domain..domain + 4].copy_from_slice(&16_u32.to_be_bytes());
    assert!(babylon_tick::material_world::decode_material_receipts(&old).is_err());
    for removed in [1_usize, 32, 317, 326] {
        assert!(babylon_tick::material_world::decode_material_receipts(
            &bytes[..bytes.len() - removed]
        )
        .is_err());
    }
    assert_eq!(session.material().organizer_state().unwrap().period, 0);
}
fn collection_savings_control(no_attendance: bool) -> Session {
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, HistoricalCostBook, OrganizationAccountId,
    };
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap();
    let base = authored_session(foundation, config(), false, false);
    let mut state = base.material().state().clone();
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let payer = AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]));
    let total = e.book.total_cash_and_reserves().unwrap();
    // Exact conserved Designed opening allocation: the future aid payer starts
    // zero, with its six captured micros held as donor savings instead.
    e.book
        .transfer_cash(
            payer,
            AccountId::Household(household()),
            money(6),
            CashTransferPurpose::PublicTransfer,
        )
        .unwrap();
    assert_eq!(e.book.cash(payer).unwrap().micro_units(), 0);
    assert_eq!(e.book.total_cash_and_reserves().unwrap(), total);
    let costs = e.costs.snapshot();
    e.costs = HistoricalCostBook::open(
        &e.book,
        costs.stocks,
        costs.freight,
        costs.equity,
        costs.equipment,
    )
    .unwrap();
    let recurring = e.recurring.as_mut().unwrap();
    recurring.household_purchases[0].target_closing_stock = if no_attendance { 4 } else { 8 };
    recurring.household_purchases[0].enabled = !no_attendance;
    if no_attendance {
        for row in &mut recurring.attendance {
            row.planned_hours = 0;
        }
    }
    let mut cfg = serde_json::to_value(collection_config_for_control()).unwrap();
    cfg["collection"]["maximum_cash_micros"] =
        serde_json::Value::String(if no_attendance { "2" } else { "6" }.into());
    try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        state,
        serde_json::from_value(cfg).unwrap(),
    )
    .unwrap()
}
#[test]
fn savings_can_collect_with_zero_current_funded_attendance() {
    use babylon_material_circuit::AccountId;
    let session = collection_savings_control(true);
    let collect: OrganizerChoice = serde_json::from_str("\"collect\"").unwrap();
    let accepted = commitment(&session, collect);
    let candidate = prepare(&session, Some(&accepted));
    let decoded = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .unwrap();
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
            .find(|row| row.account == AccountId::Household(household()))
            .unwrap()
            .statement
            .wage_income
            .micro_units(),
        0
    );
    let value =
        serde_json::to_value(candidate.material().register().organizer_state().unwrap()).unwrap();
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
            .cash(AccountId::Household(household()))
            .unwrap()
            .micro_units(),
        4
    );
}
#[test]
fn original_collection_funds_only_separately_authorized_later_aid() {
    let mut paid = collection_savings_control(false);
    let mut severed = collection_savings_control(false);
    let collect: OrganizerChoice = serde_json::from_str("\"collect\"").unwrap();
    let accepted = commitment(&paid, collect);
    let paid_candidate = prepare(&paid, Some(&accepted));
    let paid_rows = babylon_tick::material_world::decode_material_receipts(
        paid_candidate.material().receipt_bytes(),
    )
    .unwrap();
    assert!(paid_rows.aid.is_empty());
    let value = serde_json::to_value(
        paid_candidate
            .material()
            .register()
            .organizer_state()
            .unwrap(),
    )
    .unwrap();
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
            .unwrap()
            .statement
            .gift_income
            .micro_units(),
        6
    );
    let held = commitment(&severed, OrganizerChoice::Hold);
    let severed_candidate = prepare(&severed, Some(&held));
    let mut sink = CollectingSink::default();
    commit(&mut paid, &mut sink, paid_candidate);
    commit(&mut severed, &mut sink, severed_candidate);
    let aid = commitment(&paid, OrganizerChoice::LocalAid);
    let absent = commitment(&severed, OrganizerChoice::LocalAid);
    let paid_next = prepare(&paid, Some(&aid));
    let severed_next = prepare(&severed, Some(&absent));
    let actual = babylon_tick::material_world::decode_material_receipts(
        paid_next.material().receipt_bytes(),
    )
    .unwrap();
    let counterfactual = babylon_tick::material_world::decode_material_receipts(
        severed_next.material().receipt_bytes(),
    )
    .unwrap();
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
        .any(|row| row.principal_id == recipient() && row.consumed_quantity == 1));
    assert_eq!(paid.material().organizer_state().unwrap().period, 1);
}

#[test]
fn opening_collection_projection_requires_exact_existing_payer_and_labor_unit() {
    use babylon_practice_contract::{initial_organizer_state, validate_organizer_config};
    let base = authored_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        config(),
        false,
        false,
    );
    let material = base.material().state().clone();
    let good = collection_config_for_control();
    assert!(MaterialWorldRegister::try_new(0, material.clone())
        .unwrap()
        .with_organizer(good.clone(), initial_organizer_state(&good).unwrap())
        .is_ok());
    for field in ["organization_account_id", "labor_unit_id"] {
        let mut value = serde_json::to_value(&good).unwrap();
        value["collection"][field] = serde_json::to_value([97_u8; 32].to_vec()).unwrap();
        let changed: babylon_practice_contract::OrganizerConfig =
            serde_json::from_value(value).unwrap();
        validate_organizer_config(&changed).unwrap();
        assert!(
            MaterialWorldRegister::try_new(0, material.clone())
                .unwrap()
                .with_organizer(changed.clone(), initial_organizer_state(&changed).unwrap())
                .is_err(),
            "{field}"
        );
    }
}
#[test]
fn historical_actual_collection_preserves_original_consent_and_donor_pledge_admission() {
    use babylon_practice_contract::{validate_organizer_collection_fact, OrganizerGiftConsent};
    let session = collection_control_session(4, false);
    let collect: OrganizerChoice = serde_json::from_str("\"collect\"").unwrap();
    let accepted = commitment(&session, collect);
    let candidate = prepare(&session, Some(&accepted));
    let actual = &candidate
        .material()
        .register()
        .organizer_state()
        .unwrap()
        .collection_receipts[0];
    let cfg = session.material().organizer_config().unwrap();
    validate_organizer_collection_fact(cfg, &actual.commitment, &actual.fact).unwrap();
    let mut refused = cfg.clone();
    refused.collection.as_mut().unwrap().cash_consent = OrganizerGiftConsent::Refuse;
    assert!(
        validate_organizer_collection_fact(&refused, &actual.commitment, &actual.fact).is_err()
    );
    let mut insufficient = cfg.clone();
    let donor = insufficient
        .participants
        .iter_mut()
        .find(|p| p.contributor_id == 201)
        .unwrap();
    for pledge in &mut donor.commitments {
        if pledge.actor_id == 101 {
            pledge.hours = 1;
        }
    }
    assert!(
        validate_organizer_collection_fact(&insufficient, &actual.commitment, &actual.fact)
            .is_err()
    );
}

#[test]
fn partial_collection_preserves_protected_floor_and_matches_actual_transfer_and_time() {
    use babylon_material_circuit::{AccountId, OrganizationAccountId};
    let base = collection_savings_control(true);
    let mut cfg = base.material().organizer_config().unwrap().clone();
    let terms = cfg.collection.as_mut().unwrap();
    terms.maximum_cash_micros = 8;
    terms.protected_cash_floor_micros = 2;
    let session = try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        base.material().state().clone(),
        cfg,
    )
    .unwrap();
    let accepted = commitment(&session, OrganizerChoice::Collect);
    let before = session.material().canonical_bytes().to_vec();
    let candidate = prepare(&session, Some(&accepted));
    assert_eq!(session.material().canonical_bytes(), before);
    let organizer = candidate.material().register().organizer_state().unwrap();
    let actual = serde_json::to_value(organizer).unwrap();
    let fact = &actual["collection_receipts"][0]["fact"];
    assert_eq!(fact["requested_cash_micros"], "8");
    assert_eq!(fact["collected_cash_micros"], "4");
    assert_eq!(fact["outcome"], "partially_collected");
    assert_eq!(fact["performed_hours"], 2);
    assert_eq!(
        organizer.receipts.last().unwrap().outcome,
        OrganizerOutcome::CollectionCompleted
    );
    assert_eq!(
        organizer.agreements,
        session.material().organizer_state().unwrap().agreements
    );
    assert_eq!(
        organizer.contact_products,
        session
            .material()
            .organizer_state()
            .unwrap()
            .contact_products
    );
    let decoded = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .unwrap();
    let donor = AccountId::Household(household());
    let recipient = AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]));
    let ordinal = usize::try_from(fact["transfer_ordinal"].as_u64().unwrap()).unwrap();
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
            .unwrap()
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
            .unwrap()
            .statement
            .gift_income
            .micro_units(),
        4
    );
    let CircuitAccounting::Monetary(e) = &candidate.material().register().state().accounting else {
        unreachable!()
    };
    assert_eq!(e.book.cash(donor).unwrap().micro_units(), 2);
    assert_eq!(e.book.cash(recipient).unwrap().micro_units(), 4);
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
    let mut config = base.material().organizer_config().unwrap().clone();
    let terms = config.collection.as_mut().unwrap();
    terms.maximum_cash_micros = cap;
    terms.protected_cash_floor_micros = floor;
    try_session(
        michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        base.material().state().clone(),
        config,
    )
    .unwrap()
}

fn material_collection_input(
    session: &Session,
) -> babylon_material_circuit::CollectionResolveInput {
    let accepted = commitment(session, OrganizerChoice::Collect);
    let terms = session
        .material()
        .organizer_config()
        .unwrap()
        .collection
        .as_ref()
        .unwrap();
    babylon_material_circuit::CollectionResolveInput {
        original_commitment_id: accepted.commitment_id,
        command_nonce: accepted.command.nonce,
        admitted_period: accepted.command.expected_period,
        resolve_period: accepted.resolves_period,
        mandate_id: terms.mandate_id,
        source_hash: terms.source_hash,
        actor_id: terms.actor_id,
        contributor_id: terms.contributor_id,
        donor: babylon_material_circuit::FinalDemandPrincipalId::from_bytes(
            terms.household_principal_id,
        ),
        recipient: babylon_material_circuit::OrganizationAccountId::from_bytes(
            terms.organization_account_id,
        ),
        labor_unit_id: babylon_material_circuit::UnitId::from_bytes(terms.labor_unit_id),
        cash_consent: true,
        requested: money(terms.maximum_cash_micros),
        protected_cash_floor: money(terms.protected_cash_floor_micros),
        collection_hours: terms.collection_hours,
        pledged_hours: session
            .material()
            .organizer_config()
            .unwrap()
            .participants
            .iter()
            .find(|row| row.contributor_id == terms.contributor_id)
            .unwrap()
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
    let accepted = commitment(&session, OrganizerChoice::Collect);
    let config = session.material().organizer_config().unwrap();
    let state = session.material().organizer_state().unwrap();
    for consent in [true, false] {
        let mut refused = config.clone();
        if consent {
            refused.collection.as_mut().unwrap().cash_consent = OrganizerGiftConsent::Refuse;
        } else {
            refused
                .participants
                .iter_mut()
                .find(|row| row.contributor_id == 201)
                .unwrap()
                .commitments
                .iter_mut()
                .find(|row| row.actor_id == 101)
                .unwrap()
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
        let closed = close_collection_control(session.material().state(), &[], &[input]).unwrap();
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
            babylon_practice_contract::OrganizerCollectionOutcome::InsufficientCash,
        ),
        (
            collection_control_session(4, true),
            babylon_practice_contract::OrganizerCollectionOutcome::InsufficientContributionTime,
        ),
    ] {
        let accepted = commitment(&session, OrganizerChoice::Collect);
        let candidate = prepare(&session, Some(&accepted));
        let actual = candidate.material().register().organizer_state().unwrap();
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
fn partial_collection_failure_exact_retry_and_reopen_publish_one_original_receipt() {
    let mut session = capped_collection_session(8, 2);
    let accepted = commitment(&session, OrganizerChoice::Collect);
    let before = session.material().canonical_bytes().to_vec();
    let graph_before = session
        .graph_session()
        .graph()
        .encode_state()
        .unwrap()
        .as_bytes()
        .to_vec();
    let hash_before = session.current_world_hash().unwrap();
    let candidate = prepare(&session, Some(&accepted));
    let expected = *candidate.identity();
    let expected_bytes = candidate.material().receipt_bytes().to_vec();
    let mut sink = CollectingSink::default();
    assert!(matches!(
        session.commit_prepared_and_publish(&mut sink, candidate, |_| {
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
            .unwrap()
            .as_bytes(),
        graph_before
    );
    assert_eq!(session.current_world_hash().unwrap(), hash_before);
    assert_eq!(session.completed_tick(), 0);
    assert!(sink.events.is_empty());
    let retry = prepare(&session, Some(&accepted));
    assert_eq!(*retry.identity(), expected);
    assert_eq!(retry.material().receipt_bytes(), expected_bytes);
    commit(&mut session, &mut sink, retry);
    let reopened = MaterialWorldRegister::decode(session.material().canonical_bytes()).unwrap();
    assert_eq!(reopened, *session.material());
    let organizer = reopened.organizer_state().unwrap();
    assert_eq!(organizer.collection_receipts.len(), 1);
    assert_eq!(organizer.collection_receipts[0].commitment, accepted);
    assert_eq!(
        organizer.collection_receipts[0].fact.collected_cash_micros,
        4
    );
    assert!(admit_organizer(
        reopened.organizer_config().unwrap(),
        organizer,
        &accepted.command
    )
    .is_err());
    let mut conflicting = accepted.command.clone();
    conflicting.choice = OrganizerChoice::LocalAid;
    assert!(admit_organizer(
        reopened.organizer_config().unwrap(),
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
    let accepted = commitment(&session, OrganizerChoice::Collect);
    let candidate = prepare(&session, Some(&accepted));
    let bytes = candidate.material().receipt_bytes();
    let decoded = babylon_tick::material_world::decode_material_receipts(bytes).unwrap();
    assert_eq!(decoded.collections.len(), 1);
    assert_eq!(decoded.collections[0].outcome as u8, 9);
    let row = bytes.len() - 317;
    assert_eq!(bytes[row + 280], 9);
    let original_fact = &candidate
        .material()
        .register()
        .organizer_state()
        .unwrap()
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
                session.material().organizer_config().unwrap(),
                &accepted,
                &fact,
            )
            .is_err()
        );
    }
    let mut changed =
        serde_json::to_value(candidate.material().register().organizer_state().unwrap()).unwrap();
    changed["collection_receipts"][0]["fact"]["outcome"] = serde_json::json!("collected");
    let changed: babylon_practice_contract::OrganizerState =
        serde_json::from_value(changed).unwrap();
    assert!(babylon_practice_contract::validate_organizer_state(&changed).is_err());
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
            close_collection_control(opening, &[], &[input.clone(), second],),
            Err(MaterialCircuitError::RowLimit)
        ));
        assert_eq!(*opening, before);
    }
    let mut due = opening.clone();
    let CircuitAccounting::Monetary(e) = &mut due.accounting else {
        unreachable!()
    };
    let donor = AccountId::Household(household());
    e.financial.ownership.push(OwnershipClaim {
        issuer_site_id: site(1),
        beneficiary: donor,
        shares: 1,
    });
    let mut costs = e.costs.snapshot();
    costs.equity.push(EquityCarryingValue {
        owner: donor,
        issuer_site_id: site(1),
        amount: money(0),
    });
    e.costs = HistoricalCostBook::open(
        &e.book,
        costs.stocks,
        costs.freight,
        costs.equity,
        costs.equipment,
    )
    .unwrap();
    e.financial.contributions.push(CapitalContributionOrder {
        id: ContributionId::from_bytes([80; 32]),
        due_period: 1,
        contributor: AccountId::Household(household()),
        issuer_site_id: site(1),
        amount: money(8),
    });
    let closed = close_collection_control(&due, &[], &[input]).unwrap();
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
    opening: &babylon_material_circuit::MaterialCircuitState,
    aid: &[babylon_material_circuit::AidResolveInput],
    collection: &[babylon_material_circuit::CollectionResolveInput],
) -> Result<
    babylon_material_circuit::MaterialCircuitTransition,
    babylon_material_circuit::MaterialCircuitError,
> {
    let closed =
        babylon_material_circuit::close_material_period_with_support(opening, aid, collection)?;
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
    closed.finish_with_workforce(next_labor, next_member_labor)
}
