//! Projection controls use the same real captured circuit/organizer fixture.
use super::OrganizerAidResolution;
use super::{remaining_time, OrganizerAidTime};
use crate::organizer_aid_fixture as fixture;
use crate::organizer_aid_fixture::Session;
use crate::runtime_session::OrganizerSnapshot;
use crate::runtime_session::RuntimeSessionErrorCode;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::{CircuitAccounting, HouseholdTimeAccounting};
use babylon_practice_contract::OrganizerAidKind;
use babylon_practice_contract::OrganizerAllocation;
use babylon_practice_contract::OrganizerCommitment;
use babylon_practice_contract::OrganizerPeriodJournalEntries;
use babylon_practice_contract::{OrganizerChoice, OrganizerOutcome};
use babylon_tick::material_world::MaterialWorldRegister;
use serde_json::Value;

#[test]
fn remote_projection_preserves_admission_dispatch_and_resolution_dates() {
    let mut config = fixture::config();
    config.aid_bindings[0].kind = OrganizerAidKind::Remote;
    config.aid_bindings[0].coordination_hours = 1;
    config.aid_bindings[0]
        .report_sharing
        .participation_time
        .push(fixture::mandate(true).labor_unit_id.as_bytes());
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
    let first_snapshot = cold_report_snapshot(&session);
    assert_eq!(first_snapshot.aid_resolutions.len(), 1);
    assert_eq!(first_snapshot.pending_aid.len(), 1);
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
    assert_completed_time_and_history(&session, entries, accepted.commitment_id);
    assert_owned_partner_response(entries, &returned);
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
    verify_independent_selected_terms(&session, &snapshot, &accepted, &facts);
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
    verify_independent_selected_terms(&session, &snapshot, &accepted, &facts);
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
    resolutions: &[OrganizerAidResolution],
) {
    let cash_only = accepted.command.choice == OrganizerChoice::RemoteAid;
    let expected: Value = serde_json::from_str(if cash_only {
        include_str!("../../tests/fixtures/cash_only_no_food_v18.json")
    } else {
        include_str!("../../tests/fixtures/food_only_no_payer_v18.json")
    })
    .expect("actual producer fixture");
    assert_eq!(
        serde_json::to_value(snapshot).expect("status JSON"),
        expected["snapshot"]
    );
    assert_eq!(
        serde_json::to_value(resolutions).expect("complete dated resolution projection"),
        expected["resolutions"]
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

fn cold_report_snapshot(session: &Session) -> OrganizerSnapshot {
    let live = crate::organizer_runtime::captured_organizer_snapshot(
        session.catalog(),
        session.material(),
        None,
        session.duration(),
    )
    .expect("live disclosure");
    let restored = MaterialWorldRegister::decode_external(
        session.catalog(),
        session.material().canonical_bytes().to_vec(),
    )
    .expect("cold register");
    let snapshot = crate::organizer_runtime::captured_organizer_snapshot(
        session.catalog(),
        &restored,
        None,
        session.duration(),
    )
    .expect("reopened evidence");
    assert_eq!(live, snapshot);
    snapshot
}

#[test]
fn captured_cash_delivery_and_subsequent_ordinary_food_purchase_have_distinct_dated_evidence() {
    use babylon_practice_contract::{OrganizerPartnerFacts, OrganizerReport};
    let close = |with_gift: bool, available: i128| {
        let mut session = cash_purchase_session(available, 8);
        let mandate = fixture::mandate(false);
        let gift = fixture::commitment_with_allocation(
            &session,
            OrganizerChoice::LocalAid,
            OrganizerAllocation::Aid {
                food_quantity: 0,
                cash_micros: 4,
            },
        );
        let mut sink = CollectingSink::default();
        let mut evidence = Vec::new();
        let mut demand = Vec::new();
        for period in 1..=2 {
            let candidate = fixture::prepare(&session, (with_gift && period == 1).then_some(&gift));
            let receipts = babylon_tick::material_world::decode_material_receipts(
                candidate.material().receipt_bytes(),
            )
            .expect("actual dated postings");
            demand.extend(
                receipts
                    .household_demand
                    .into_iter()
                    .filter(|r| r.principal_id == fixture::recipient()),
            );
            fixture::commit(&mut session, &mut sink, candidate);
            let snapshot = cold_report_snapshot(&session);
            let row = snapshot
                .view
                .observations
                .iter()
                .find(|r| r.acquired_period == period && r.subject_id == mandate.recipient_actor)
                .expect("actual current food report");
            let OrganizerReport::Partner {
                facts:
                    OrganizerPartnerFacts::FoodProvision {
                        purchased,
                        settled_micros,
                        consumed,
                        ..
                    },
                ..
            } = &row.report
            else {
                panic!("only food authorized")
            };
            evidence.push((*purchased, *settled_micros, *consumed));
            if !with_gift {
                assert_eq!(snapshot.aid_resolutions.len(), 0);
                continue;
            }
            let dispatch = snapshot
                .aid_resolutions
                .iter()
                .find(|r| {
                    r.pending.original_commitment_id == gift.commitment_id && r.practice.period == 1
                })
                .expect("dated original delivery");
            assert!(matches!(
                dispatch.support.cash_status,
                babylon_practice_contract::OrganizerAidCashStatus::Granted
            ));
        }
        (evidence, demand)
    };
    let (aided, orders) = close(true, 4);
    let (ordinary, _) = close(false, 4);
    let (unfilled, expired) = close(true, 0);
    assert_eq!(unfilled, vec![(0, 0, 0), (0, 0, 0)]);
    assert_eq!(
        (expired[1].admitted_quantity, expired[1].expired_quantity),
        (1, 1)
    );
    assert_eq!(ordinary, vec![(1, 4, 1), (0, 0, 0)]);
    assert_eq!(
        aided,
        vec![(1, 4, 1), (1, 4, 1)],
        "actual household orders {orders:?}"
    );
}

fn assert_completed_time_and_history(
    session: &Session,
    entries: &OrganizerPeriodJournalEntries,
    original: [u8; 32],
) {
    let completed_snapshot = cold_report_snapshot(session);
    let dates: Vec<_> = completed_snapshot
        .aid_resolutions
        .iter()
        .map(|r| (r.pending.original_commitment_id, r.practice.period))
        .collect();
    assert_eq!(dates, vec![(original, 1), (original, 2)]);
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        panic!("modeled money")
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("modeled hours")
    };
    let gross = book
        .receipts
        .iter()
        .find(|r| r.principal_id == fixture::recipient())
        .expect("gross closing clock");
    let used = book
        .contributions
        .iter()
        .filter(|r| r.period == 2 && r.contribution.principal_id == fixture::recipient())
        .map(|r| r.contribution.hours)
        .sum::<u64>();
    assert!(
        used > 0,
        "response actually debited the recipient's household clock"
    );
    let time = entries
        .observations
        .iter()
        .find_map(|r| match &r.report {
            babylon_practice_contract::OrganizerReport::Partner {
                facts:
                    babylon_practice_contract::OrganizerPartnerFacts::ParticipationTime {
                        contributed,
                        remaining,
                        ..
                    },
                ..
            } => Some((*contributed, *remaining)),
            _ => None,
        })
        .expect("completed permitted clock");
    assert_eq!(time, (used, gross.contribution_available_hours - used));
}

fn assert_owned_partner_response(
    entries: &OrganizerPeriodJournalEntries,
    returned: &[OrganizerAidResolution],
) {
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

fn cash_purchase_session(available: i128, recipient_hours: u64) -> Session {
    use babylon_practice_contract::OrganizerReportCommodity;
    let mut material = fixture::aid_opening(false);
    material
        .catalog
        .household_time_policy
        .iter_mut()
        .find(|p| p.principal_id == fixture::recipient())
        .expect("captured recipient clock")
        .hours_per_eligible_person = recipient_hours;
    let mut config = fixture::config();
    let mandate = fixture::mandate(false);
    config.aid_bindings[0]
        .report_sharing
        .food
        .push(OrganizerReportCommodity {
            good_id: mandate.good_id.as_bytes(),
            unit_id: mandate.unit_id.as_bytes(),
            label: "Food".into(),
            unit_label: "parcel".into(),
        });
    let CircuitAccounting::Monetary(economy) = &mut material.state.accounting else {
        panic!("fixture economy")
    };
    // Pre-existing spendable cash supports one ordinary purchase in both branches,
    // so the retailer plans real handling hours for the next close.
    let mut opening_cash = economy.book.snapshot();
    for row in &mut opening_cash.accounts {
        if row.id == babylon_material_circuit::AccountId::Site(fixture::site(2)) {
            row.cash = fixture::money(row.cash.micro_units() - available);
        }
        if row.id == babylon_material_circuit::AccountId::Household(fixture::recipient()) {
            row.cash = fixture::money(available);
        }
    }
    economy.book =
        MonetaryBook::from_snapshot(opening_cash).expect("conserved opening cash allocation");
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        economy.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .expect("opening carrying values");
    economy
        .recurring
        .as_mut()
        .expect("ordinary needs")
        .household_purchases
        .iter_mut()
        .find(|p| p.principal_id == fixture::recipient())
        .expect("recipient ordinary buyer")
        .enabled = true;
    fixture::try_session(
        crate::michigan_dynamic_hex_foundation().expect("fixture foundation"),
        &format!(
            "{}\n{}\n{}",
            fixture::MATERIAL,
            fixture::PRODUCTS,
            fixture::PRACTICE
        ),
        material,
        config,
    )
    .expect("ordinary purchasing session")
}

#[test]
fn varying_unshared_household_hours_changes_neither_report_count_nor_disclosed_partners() {
    let close = |hours| {
        let mut session = cash_purchase_session(4, hours);
        let candidate = fixture::prepare(&session, None);
        let actual = babylon_tick::material_world::decode_material_receipts(
            candidate.material().receipt_bytes(),
        )
        .expect("actual gross clock");
        let clock = actual
            .household_time
            .iter()
            .find(|r| r.principal_id == fixture::recipient())
            .expect("actual recipient")
            .endowment_hours;
        fixture::commit(&mut session, &mut CollectingSink::default(), candidate);
        (clock, cold_report_snapshot(&session).view)
    };
    let (first, known) = close(8);
    let (second, same) = close(12);
    assert_ne!(first, second);
    assert_eq!(known, same);
}

#[test]
fn scoped_archive_opening_bound_register_refuses_changed_or_missing_partner_knowledge() {
    use babylon_practice_contract::{OrganizerPartnerFacts, OrganizerPeriodJournal};
    let session = cash_purchase_session(4, 8);
    let mut config = session
        .material()
        .organizer_config()
        .expect("admitted config")
        .clone();
    let binding = &config.aid_bindings[0];
    let actor = binding.partner.actor_id;
    let commodity = binding.report_sharing.food[0].clone();
    let opening = |config: &_, stock| {
        babylon_practice_contract::partner_observation(
            config,
            actor,
            0,
            0,
            OrganizerPartnerFacts::OpeningAssessment {
                commodity: commodity.clone(),
                opening_stock: stock,
                required: 1,
            },
        )
        .expect("valid assessment")
    };
    config.initial_observations = vec![opening(&config, 3)];
    let state =
        babylon_practice_contract::initial_organizer_state(&config).expect("correct authority");
    let bind = |state| {
        session.material().clone().with_organizer(
            session.catalog(),
            config.clone(),
            state,
            OrganizerPeriodJournal::empty(),
        )
    };
    assert!(bind(state.clone()).is_ok());
    let mut missing = state;
    missing.learned_authority_index.clear();
    assert!(bind(missing).is_err());
    let mut changed = config.clone();
    changed.initial_observations = vec![opening(&changed, 4)];
    assert!(bind(
        babylon_practice_contract::initial_organizer_state(&changed)
            .expect("valid alternate capture")
    )
    .is_err());
}
