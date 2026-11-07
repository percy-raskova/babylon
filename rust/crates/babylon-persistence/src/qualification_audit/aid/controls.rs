//! Actual replay receipts exercise the observer fold, including non-Wayne terms.
use super::audit;
use super::audit::{Accepted, Audit, Refusal};
use crate::identity::CampaignId;
use crate::observer_reader::CommittedMaterialReceipts;
use crate::organizer_aid_fixture as fixture;
use crate::runtime_session::OrganizerSnapshot;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::AidOutcome;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_practice_contract::OrganizerAllocation;
use babylon_practice_contract::{
    OrganizerAidKind, OrganizerChoice, OrganizerCommitment, OrganizerPreview,
};
use babylon_practice_contract::{OrganizerOutcome, OrganizerPartnerPolicy};
use babylon_tick::material_world;
use babylon_tick::material_world::MaterialReceiptHandle;
use fixture::Session;
use uuid::Uuid;

fn snapshot(session: &Session) -> OrganizerSnapshot {
    audit::material_disclosure(session.catalog(), session.material(), session.duration())
        .expect("the fixture call `material_disclosure` succeeds for the authored inputs")
}
fn start(
    routed: bool,
    no_time: bool,
    policy: OrganizerPartnerPolicy,
    hours: u64,
) -> (
    Session,
    Audit,
    OrganizerSnapshot,
    OrganizerPreview,
    OrganizerCommitment,
) {
    let mut config = fixture::config();
    config.aid_bindings[0].coordination_hours = hours;
    config.aid_bindings[0].partner.policy = policy;
    config.aid_bindings[0].kind = if routed {
        OrganizerAidKind::Remote
    } else {
        OrganizerAidKind::Local
    };
    let session = fixture::authored_session(
        crate::michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        config,
        no_time,
        routed,
    );
    let before = snapshot(&session);
    let choice = if routed {
        OrganizerChoice::RemoteAid
    } else {
        OrganizerChoice::LocalAid
    };
    let commitment = fixture::commitment_with_allocation(
        &session,
        choice,
        OrganizerAllocation::Aid {
            food_quantity: 2,
            cash_micros: 0,
        },
    );
    let preview = babylon_practice_contract::preview_organizer(
        session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        session
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state"),
        &commitment.command,
    )
    .expect("the organizer preview builds");
    let mut audit = Audit::default();
    audit
        .open(session.catalog(), session.material(), &before)
        .expect("the fixture opens the authored source");
    (session, audit, before, preview, commitment)
}
fn advance(
    session: &mut Session,
    accepted: Option<&OrganizerCommitment>,
) -> (CommittedMaterialReceipts, OrganizerSnapshot) {
    let candidate = fixture::prepare(session, accepted);
    let identity = *candidate.identity();
    let receipts = MaterialReceiptHandle::new(
        material_world::decode_material_receipts(candidate.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type"),
    );
    fixture::commit(session, &mut CollectingSink::default(), candidate);
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        panic!("monetary fixture")
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("household fixture")
    };
    (
        CommittedMaterialReceipts {
            campaign_id: CampaignId::from_uuid(Uuid::from_bytes(
                session
                    .material()
                    .organizer_config()
                    .expect("the fixture register carries organizer config")
                    .campaign_id,
            )),
            identity,
            material_register_bytes: session.material().canonical_bytes().len(),
            receipts,
            household_contributions: book.contributions.clone(),
        },
        snapshot(session),
    )
}

#[test]
fn real_configured_aid_separates_consumption_from_independent_participation() {
    for (no_time, policy, hours, outcome) in [
        (
            false,
            OrganizerPartnerPolicy::Participate,
            1,
            OrganizerOutcome::AidPracticeCompleted,
        ),
        (
            false,
            OrganizerPartnerPolicy::Refuse,
            1,
            OrganizerOutcome::AidPracticeUncompleted,
        ),
        (
            false,
            OrganizerPartnerPolicy::Participate,
            3,
            OrganizerOutcome::InsufficientTime,
        ),
        (
            true,
            OrganizerPartnerPolicy::Participate,
            1,
            OrganizerOutcome::NoQualifyingSupport,
        ),
    ] {
        let (mut session, mut audit, before, preview, commitment) =
            start(false, no_time, policy, hours);
        let accepted = Accepted::capture(&commitment, &preview, &before)
            .expect("the fixture captures the authored state");
        audit
            .accept(accepted.clone())
            .expect("the fixture call `accept` succeeds for the authored inputs");
        audit
            .accept(accepted)
            .expect("the fixture call `accept` succeeds for the authored inputs");
        assert_eq!(audit.report()["accepted_original_commands"], 1);
        let (admitted, after) = advance(&mut session, Some(&commitment));
        let fact = audit
            .read(session.catalog(), &admitted, session.material(), &after)
            .expect("the fixture reader returns its authored facts");
        assert_eq!(after.aid_resolutions[0].practice.outcome, outcome);
        assert!(fact
            .selected_aid
            .iter()
            .all(|r| r["remaining_shared_hours"].is_u64()));
        assert_eq!(
            audit
                .completed_practices
                .contains(&commitment.commitment_id),
            outcome == OrganizerOutcome::AidPracticeCompleted
        );
    }
}

#[test]
fn original_remote_offer_survives_arrival_without_repeated_dispatch_charges() {
    let (mut session, mut audit, before, preview, commitment) =
        start(true, false, OrganizerPartnerPolicy::Participate, 5);
    audit
        .accept(
            Accepted::capture(&commitment, &preview, &before)
                .expect("the fixture captures the authored state"),
        )
        .expect("the fixture call `accept` succeeds for the authored inputs");
    let (first, after) = advance(&mut session, Some(&commitment));
    audit
        .read(session.catalog(), &first, session.material(), &after)
        .expect("the fixture reader returns its authored facts");
    assert_eq!(
        after.aid_resolutions[0].practice.outcome,
        OrganizerOutcome::AidAwaitingSupport
    );
    let (second, after) = advance(&mut session, None);
    let fact = audit
        .read(session.catalog(), &second, session.material(), &after)
        .expect("the fixture reader returns its authored facts");
    let current = after
        .aid_resolutions
        .iter()
        .find(|r| {
            r.practice.period == after.view.period
                && r.pending.original_commitment_id == commitment.commitment_id
        })
        .expect("current arrival for the original commitment");
    assert_eq!(
        current.practice.outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert!(after.aid_resolutions.iter().any(|r| {
        r.practice.period < current.practice.period
            && r.pending.original_commitment_id == commitment.commitment_id
            && r.practice.outcome == OrganizerOutcome::AidAwaitingSupport
    }));
    assert!(second
        .receipts
        .aid
        .iter()
        .all(|r| r.contribution_hours == 0));
    assert_eq!(current.practice.hours_spent, 5);
    assert_eq!(fact.independent_practices[0]["recipient_debited_hours"], 2);
}

#[test]
fn another_campaign_cannot_replace_the_opening_or_advance_an_empty_prefix() {
    let (_, mut audit, before, _, _) = start(false, false, OrganizerPartnerPolicy::Participate, 1);
    let original = audit.report();
    let opening = audit.opening.clone();
    let mut cfg = fixture::config();
    cfg.campaign_id = [99; 16];
    let mut other = fixture::authored_session(
        crate::michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
            .expect("the Michigan hex foundation builds"),
        cfg,
        false,
        false,
    );
    assert_eq!(
        audit.open(other.catalog(), other.material(), &snapshot(&other)),
        Err(Refusal::Identity)
    );
    let (admitted, after) = advance(&mut other, None);
    assert_eq!(admitted.receipts.aid.len(), 0);
    assert_eq!(
        audit
            .read(other.catalog(), &admitted, other.material(), &after)
            .expect_err("the malformed read request is refused"),
        Refusal::Identity
    );
    assert_eq!(audit.report(), original);
    assert_eq!(audit.opening, opening);
    assert_eq!(
        audit
            .opening
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .1,
        before
    );
}

#[test]
fn changed_dynamic_original_offer_is_refused_before_admission() {
    let (_, audit, before, preview, commitment) =
        start(true, false, OrganizerPartnerPolicy::Participate, 5);
    for change in 0..4 {
        let mut changed = before.clone();
        let row = &mut changed.aid[0];
        match change {
            0 => *row.payer_cash.as_mut().expect("cash available") += 1,
            1 => row.food.as_mut().expect("food available").donor_stock += 1,
            2 => {
                row.food
                    .as_mut()
                    .expect("food available")
                    .ordinary_offer
                    .as_mut()
                    .expect("the fixture set the optional field before this borrow")
                    .unit_price += 1;
            }
            _ => {
                if let crate::runtime_session::OrganizerAidTransportPreview::Routed {
                    stages, ..
                } = &mut row.food.as_mut().expect("food available").transport
                {
                    stages[0].travel_periods += 1;
                }
            }
        }
        let mut candidate = audit.clone();
        assert_eq!(
            candidate.accept(
                Accepted::capture(&commitment, &preview, &changed)
                    .expect("the fixture captures the authored state")
            ),
            Err(Refusal::OriginalOffer)
        );
        assert_eq!(candidate.report()["accepted_original_commands"], 0);
    }
}

#[test]
fn late_refusal_does_not_publish_a_partial_aid_fold() {
    let (mut session, mut audit, before, preview, commitment) =
        start(false, false, OrganizerPartnerPolicy::Participate, 1);
    let (admitted, after) = advance(&mut session, Some(&commitment));
    let original = audit.report();
    assert_eq!(
        audit
            .read(session.catalog(), &admitted, session.material(), &after)
            .expect_err("the malformed read request is refused"),
        Refusal::OriginalOffer
    );
    assert_eq!(audit.report(), original);
    audit
        .accept(
            Accepted::capture(&commitment, &preview, &before)
                .expect("the fixture captures the authored state"),
        )
        .expect("the fixture call `accept` succeeds for the authored inputs");
    let original = audit.report();
    let mut crossed = admitted.clone();
    crossed.household_contributions[0]
        .contribution
        .contributor_id += 1;
    assert_eq!(
        audit
            .read(session.catalog(), &crossed, session.material(), &after)
            .expect_err("the malformed read request is refused"),
        Refusal::Time
    );
    assert_eq!(audit.report(), original);
    audit
        .read(session.catalog(), &admitted, session.material(), &after)
        .expect("the fixture reader returns its authored facts");
    let original = audit.report();
    assert_eq!(
        audit
            .read(session.catalog(), &admitted, session.material(), &after)
            .expect_err("the malformed read request is refused"),
        Refusal::Period
    );
    assert_eq!(audit.report(), original);
}

#[allow(
    clippy::too_many_lines,
    reason = "one conserved Designed opening keeps cash, food and carrying-value reallocation assertions together"
)]
fn mixed_collection_session() -> Session {
    use babylon_material_circuit::{AccountId, CashTransferPurpose, HistoricalCostBook};
    use babylon_practice_contract::{OrganizerCollectionMandate, OrganizerGiftConsent};
    let foundation = crate::michigan_dynamic_hex_foundation().expect("fixture foundation");
    let mut config = fixture::config();
    config.aid_bindings[0].kind = OrganizerAidKind::Remote;
    config.aid_bindings[0].coordination_hours = 1;
    let base = fixture::authored_session(foundation, config.clone(), false, true);
    let catalog = base.catalog().clone();
    let mut state = base.material().state().clone();
    let payer = catalog.aid_mandates[0].payer;
    let AccountId::Organization(organization) = payer else {
        panic!("organization payer");
    };
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("money");
    };
    let cash_before = economy.book.total_cash_and_reserves().expect("cash sum");
    // Conserved Designed opening: split existing six micros between donor and
    // organization, and move the retailer's four parcels to donor pantry.
    economy
        .book
        .transfer_cash(
            payer,
            AccountId::Household(fixture::household()),
            fixture::money(3),
            CashTransferPurpose::PublicTransfer,
        )
        .expect("existing funded cash");
    assert_eq!(
        economy.book.total_cash_and_reserves().expect("cash sum"),
        cash_before
    );
    let retail = state
        .inventory
        .iter_mut()
        .find(|row| row.site_id == fixture::site(3) && row.good_id == fixture::good(2))
        .expect("retail stock");
    assert_eq!(retail.quantity, 4);
    retail.quantity = 0;
    let recurring = economy.recurring.as_mut().expect("households");
    let pantry = recurring
        .household_stocks
        .iter_mut()
        .find(|row| row.principal_id == fixture::household())
        .expect("pantry");
    assert_eq!(pantry.quantity, 8);
    pantry.quantity = 12;
    recurring.household_purchases[0].target_closing_stock = 2;
    for row in &mut recurring.attendance {
        row.planned_hours = 0;
    }
    let mut costs = economy.costs.snapshot();
    let retail = costs
        .stocks
        .iter_mut()
        .find(|row| {
            row.owner == AccountId::Site(fixture::site(3)) && row.good_id == fixture::good(2)
        })
        .expect("retail basis");
    assert_eq!(retail.amount, fixture::money(12));
    retail.amount = fixture::money(0);
    let pantry = costs
        .stocks
        .iter_mut()
        .find(|row| {
            row.owner == AccountId::Household(fixture::household())
                && row.good_id == fixture::good(2)
        })
        .expect("pantry basis");
    assert_eq!(pantry.amount, fixture::money(32));
    pantry.amount = fixture::money(44);
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        costs.stocks,
        costs.freight,
        costs.equity,
        costs.equipment,
    )
    .expect("conserved opening basis");
    let binding = &config.aid_bindings[0];
    config.collection = Some(OrganizerCollectionMandate {
        mandate_id: [93; 32],
        source_hash: [94; 32],
        actor_id: config.controlled_actor_id,
        contributor_id: binding.donor_contributor_id,
        household_principal_id: binding.donor_principal_id,
        organization_account_id: organization.as_bytes(),
        social_class_target: binding.social_class_target,
        labor_unit_id: catalog.aid_mandates[0].labor_unit_id.as_bytes(),
        cash_consent: OrganizerGiftConsent::Accept,
        initial_cash_micros: 2,
        maximum_cash_micros: 2,
        protected_cash_floor_micros: 0,
        collection_hours: 2,
    });
    fixture::try_session(
        foundation,
        &format!(
            "{}\n{}\n{}",
            fixture::MATERIAL,
            fixture::PRODUCTS,
            fixture::PRACTICE
        ),
        fixture::Materials {
            catalog: catalog.into_definition(),
            state,
        },
        config,
    )
    .expect("mixed-flow session")
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one mixed-close control retains exact statements and four independent custody corruption checks"
)]
fn delayed_food_and_current_collection_reconcile_without_recounting_prior_cash() {
    use babylon_material_circuit::{AccountId, AidOutcome};
    use babylon_practice_contract::OrganizerAllocation;
    let mut session = mixed_collection_session();
    let before = snapshot(&session);
    let mut audit = Audit::default();
    audit
        .open(session.catalog(), session.material(), &before)
        .expect("audit opening");
    let gift = fixture::commitment_with_allocation(
        &session,
        OrganizerChoice::RemoteAid,
        OrganizerAllocation::Aid {
            food_quantity: 1,
            cash_micros: 3,
        },
    );
    let preview = babylon_practice_contract::preview_organizer(
        session.material().organizer_config().expect("config"),
        session.material().organizer_state().expect("state"),
        &gift.command,
    )
    .expect("exact preview");
    audit
        .accept(Accepted::capture(&gift, &preview, &before).expect("capture"))
        .expect("accepted gift");
    let (dispatch, after) = advance(&mut session, Some(&gift));
    assert_eq!(
        dispatch
            .receipts
            .aid
            .iter()
            .find(|row| row.outcome == AidOutcome::CashGranted)
            .expect("prior cash")
            .cash_amount,
        fixture::money(3)
    );
    audit
        .read(session.catalog(), &dispatch, session.material(), &after)
        .expect("cash-first audit");
    let collect = fixture::commitment(&session, OrganizerChoice::Collect);
    let (arrival, after) = advance(&mut session, Some(&collect));
    assert_eq!(arrival.receipts.collections[0].collected, fixture::money(2));
    assert!(arrival
        .receipts
        .aid
        .iter()
        .any(|row| row.outcome == AidOutcome::Granted && row.quantity == 1));
    assert!(arrival
        .receipts
        .aid
        .iter()
        .all(|row| row.outcome != AidOutcome::CashGranted));
    let payer = session.catalog().aid_mandates[0].payer;
    let income = |account| {
        &arrival
            .receipts
            .income
            .iter()
            .find(|row| row.account == account)
            .expect("income row")
            .statement
    };
    assert_eq!(
        income(AccountId::Household(fixture::household())).gift_expense,
        fixture::money(5)
    );
    assert_eq!(income(payer).gift_income, fixture::money(2));
    assert_eq!(
        income(AccountId::Household(fixture::recipient())).gift_income,
        fixture::money(3)
    );
    for corruption in 0..4 {
        let mut changed = arrival.clone();
        let mut receipts = (*changed.receipts).clone();
        match corruption {
            0 => receipts.collections[0].period = dispatch.receipts.resolve_tick,
            1 => receipts.collections[0].transfer_ordinal = Some(u32::MAX - 1),
            2 => receipts.collections.clear(),
            _ => {
                let index = usize::try_from(
                    receipts.collections[0]
                        .transfer_ordinal
                        .expect("actual ordinal"),
                )
                .expect("ordinal fits");
                receipts.money_transfers[index].credit.delta = fixture::money(3);
            }
        }
        changed.receipts = MaterialReceiptHandle::new(receipts);
        assert_eq!(
            audit
                .read(session.catalog(), &changed, session.material(), &after)
                .err(),
            Some(Refusal::Cash),
            "current-period typed custody refuses corruption {corruption}"
        );
    }
    audit
        .read(session.catalog(), &arrival, session.material(), &after)
        .expect("current collection and food only; prior cash is not repeated");
    assert_eq!(audit.completed_practices.len(), 1);
}

#[test]
fn authorized_zero_transfer_aid_cannot_disappear_from_retained_resolution() {
    let (mut session, mut audit, before, preview, commitment) =
        start(false, true, OrganizerPartnerPolicy::Participate, 1);
    audit
        .accept(Accepted::capture(&commitment, &preview, &before).expect("accepted input"))
        .expect("captured original");
    let (admitted, after) = advance(&mut session, Some(&commitment));
    assert_eq!(
        after.aid_resolutions[0].practice.outcome,
        OrganizerOutcome::NoQualifyingSupport
    );
    assert!(admitted
        .receipts
        .aid
        .iter()
        .any(|row| row.outcome == AidOutcome::Unshipped));
    assert!(admitted
        .receipts
        .aid
        .iter()
        .all(|row| row.cash_amount.micro_units() == 0));
    let mut missing = admitted.clone();
    let mut receipts = (*missing.receipts).clone();
    receipts.aid.clear();
    missing.receipts = MaterialReceiptHandle::new(receipts);
    assert_eq!(
        audit
            .read(session.catalog(), &missing, session.material(), &after)
            .err(),
        Some(Refusal::Support)
    );
    audit
        .read(session.catalog(), &admitted, session.material(), &after)
        .expect("actual zero-transfer refusal remains readable");
}

#[test]
fn cash_only_qualifies_response_without_claiming_food_consumption() {
    let (mut session, mut audit, before, _, _) =
        start(false, false, OrganizerPartnerPolicy::Participate, 1);
    let commitment = fixture::commitment_with_allocation(
        &session,
        OrganizerChoice::LocalAid,
        OrganizerAllocation::Aid {
            food_quantity: 0,
            cash_micros: 3,
        },
    );
    let preview = babylon_practice_contract::preview_organizer(
        session.material().organizer_config().expect("config"),
        session.material().organizer_state().expect("state"),
        &commitment.command,
    )
    .expect("cash preview");
    audit
        .accept(Accepted::capture(&commitment, &preview, &before).expect("capture"))
        .expect("accepted cash original");
    let (admitted, after) = advance(&mut session, Some(&commitment));
    assert_eq!(
        after.aid_resolutions[0]
            .support
            .material_postings
            .payer_cash_granted_micros,
        3
    );
    assert_eq!(
        after.aid_resolutions[0].practice.outcome,
        OrganizerOutcome::InsufficientTime
    );
    assert!(!admitted
        .receipts
        .aid
        .iter()
        .any(|row| row.outcome == AidOutcome::Granted));
    let fact = audit
        .read(session.catalog(), &admitted, session.material(), &after)
        .expect("exact cash audit");
    let response = &fact.independent_practices[0];
    assert!(
        response.get("consumed_support").is_none(),
        "obsolete ambiguous fact is retired"
    );
    assert_eq!(response["food_consumed_quantity"], 0);
    assert_eq!(response["food_consumption_period"], serde_json::Value::Null);
    assert_eq!(response["cash_received_micros"], "3");
    assert_eq!(response["cash_received_period"], 1);
    assert_eq!(response["first_response_period"], 1);
    assert_eq!(response["qualifying_received_support"], true);
    assert_eq!(response["food_consumed"], false);
}
