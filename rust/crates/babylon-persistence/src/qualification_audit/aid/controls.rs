//! Actual replay receipts exercise the observer fold, including non-Wayne terms.
use super::audit;
use super::audit::{Accepted, Audit, Refusal};
use crate::identity::CampaignId;
use crate::observer_reader::CommittedMaterialReceipts;
use crate::organizer_aid_fixture as fixture;
use crate::runtime_session::OrganizerSnapshot;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HouseholdTimeAccounting;
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
    let commitment = fixture::commitment(&session, choice);
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
            OrganizerOutcome::AidNotProvisioned,
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
    assert_eq!(
        after.aid_resolutions[0].practice.outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert!(second
        .receipts
        .aid
        .iter()
        .all(|r| r.contribution_hours == 0));
    assert_eq!(after.aid_resolutions[0].practice.hours_spent, 5);
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
            0 => row.payer_cash += 1,
            1 => row.donor_stock += 1,
            2 => {
                row.ordinary_offer
                    .as_mut()
                    .expect("the fixture set the optional field before this borrow")
                    .unit_price += 1;
            }
            _ => {
                if let crate::runtime_session::OrganizerAidTransportPreview::Routed {
                    stages, ..
                } = &mut row.transport
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
