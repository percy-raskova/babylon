use super::{aid, support};
use babylon_practice_contract::{
    OrganizerChoice, OrganizerConfig, OrganizerContribution, OrganizerHearingConfig,
    OrganizerHearingDelegation, OrganizerHearingMandate, OrganizerHearingOffer,
    OrganizerHearingOutcome, OrganizerHearingResponse, OrganizerHouseholdBinding,
    OrganizerMaterialSupport, OrganizerParticipant, OrganizerPeriodJournal, OrganizerRefusal,
    OrganizerTimeBindingMode, OrganizerTimeUse, ResolvedOrganizerPeriod,
};

use OrganizerHearingMandate::{EitherProceduralOffer, Settle, SpeakOnly, Withhold};
use OrganizerHearingOffer::{ClaimantOnly, JointMinutes};
use OrganizerHearingOutcome::{NoOffer, NoQuorum, ReferredToMembers, Settled};
use OrganizerHearingResponse::{Attended, NoTime, NotInvited, Withheld};

const CLAIMANT: u64 = 107;
const PARTNER: u64 = 105;
const CLAIMANT_CONTRIBUTOR: u64 = 206;
const PARTNER_CONTRIBUTOR: u64 = 204;

fn config(
    claimant_mandate: OrganizerHearingMandate,
    partner_mandate: OrganizerHearingMandate,
) -> OrganizerConfig {
    let mut config = aid::captured();
    config.participants.push(OrganizerParticipant {
        contributor_id: CLAIMANT_CONTRIBUTOR,
        label: "Claimant delegate".into(),
        available_hours: 2,
        commitments: vec![OrganizerContribution {
            actor_id: CLAIMANT,
            hours: 2,
        }],
        concern: String::new(),
        objection: String::new(),
        review_condition: String::new(),
    });
    let OrganizerTimeBindingMode::Household { bindings } = &mut config.time_binding else {
        panic!("captured fixture must use real household time");
    };
    bindings.push(OrganizerHouseholdBinding {
        contributor_id: CLAIMANT_CONTRIBUTOR,
        principal_id: [206; 32],
    });
    config.hearing = Some(OrganizerHearingConfig {
        county_geoid: "26163".into(),
        period: 1,
        review_period: 2,
        claimant_actor_id: CLAIMANT,
        claimant_authority_id: [57; 16],
        claimant_label: "Claimants' assembly".into(),
        claimant_claim: "A dated answer on relief eligibility".into(),
        partner_claim: "A public register of relief referrals".into(),
        claimant_delegation: OrganizerHearingDelegation {
            delegate_label: "Assembly secretary".into(),
            authorizing_households: 2,
        },
        partner_delegation: OrganizerHearingDelegation {
            delegate_label: "Aid case delegate".into(),
            authorizing_households: 4,
        },
        attendance_hours: 2,
        claimant_mandate,
        partner_mandate,
    });
    config
}

fn resolve(
    config: &OrganizerConfig,
    choice: OrganizerChoice,
    limited_contributor: u64,
    available: u64,
) -> ResolvedOrganizerPeriod {
    let opening =
        babylon_practice_contract::initial_organizer_state(config).expect("hearing campaign opens");
    let commitment = babylon_practice_contract::admit_organizer(
        config,
        &opening,
        &support::command(config, &opening, choice),
    )
    .expect("hearing decision admitted");
    babylon_practice_contract::resolve_organizer_period_with_time(
        config,
        &opening,
        &support::facts(1, 160),
        Some(&commitment),
        &aid::time(config, limited_contributor, available),
        OrganizerMaterialSupport {
            aid: &[],
            collection: None,
        },
    )
    .expect("hearing resolves")
}

#[test]
fn review_must_follow_the_hearing_in_the_next_period() {
    let mut config = config(EitherProceduralOffer, Settle(JointMinutes));
    config.hearing.as_mut().expect("hearing").review_period = 3;
    assert_eq!(
        babylon_practice_contract::validate_organizer_config(&config),
        Err(babylon_practice_contract::OrganizerError::InvalidConfig)
    );
}

#[test]
fn hold_still_resolves_the_independent_home_seat_and_no_offer() {
    let config = config(SpeakOnly, Settle(JointMinutes));
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("hearing campaign opens");
    let batch = babylon_practice_contract::organizer_resolved_action_batch(&config, &opening, None)
        .expect("hold batch");
    assert!(batch.items.iter().any(|row| {
        row.intent.actor_org_id.to_bytes() == CLAIMANT.to_be_bytes()
            && row.authority.input_authority_id.as_bytes() == [57; 16]
    }));
    assert!(!batch
        .items
        .iter()
        .any(|row| { row.intent.actor_org_id.to_bytes() == PARTNER.to_be_bytes() }));
    let resolved = resolve(&config, OrganizerChoice::Hold, CLAIMANT_CONTRIBUTOR, 2);
    let receipt = resolved.journal.hearing.expect("scheduled report");
    assert_eq!(receipt.claimant.response, Attended);
    assert_eq!(receipt.partner.response, NotInvited);
    assert_eq!(receipt.outcome, NoOffer);
    assert_eq!(receipt.review_access_actor_ids, [] as [u64; 0]);
    assert_eq!(receipt.time_use.len(), 1);
    assert_eq!(receipt.time_use[0].actor_id, CLAIMANT);
    assert_eq!(receipt.time_use[0].hours, 2);
}

#[test]
fn joint_offer_requires_both_exact_mandates_and_both_actual_debits() {
    let choice = OrganizerChoice::InviteToHearing(JointMinutes);
    let both = config(EitherProceduralOffer, Settle(JointMinutes));
    let full = resolve(&both, choice, PARTNER_CONTRIBUTOR, 2);
    assert_eq!(full, resolve(&both, choice, PARTNER_CONTRIBUTOR, 2));

    let mut journal = OrganizerPeriodJournal::empty();
    journal.append(full.journal).expect("append hearing period");
    let encoded = babylon_practice_contract::encode_organizer_journal(&both, &journal)
        .expect("encode hearing evidence");
    let decoded = babylon_practice_contract::decode_organizer_journal(&both, &encoded)
        .expect("reopen hearing evidence");
    let view = babylon_practice_contract::organizer_view(
        &both,
        &full.state,
        &decoded,
        both.controlled_actor_id,
    )
    .expect("project the hearing report on reopening");
    let report = view.hearing_receipt.expect("hearing report");
    assert_eq!(report.outcome, Settled);
    assert_eq!(report.review_period, 2);
    assert_eq!(report.review_access_actor_ids, [CLAIMANT, PARTNER]);
    assert_eq!(report.time_use, [] as [OrganizerTimeUse; 0]);
    let debits: Vec<_> = decoded.periods[0]
        .hearing
        .as_ref()
        .expect("hearing")
        .time_use
        .iter()
        .map(|usage| (usage.actor_id, usage.contributor_id, usage.hours))
        .collect();
    assert_eq!(
        debits,
        [
            (CLAIMANT, CLAIMANT_CONTRIBUTOR, 2),
            (PARTNER, PARTNER_CONTRIBUTOR, 2)
        ]
    );
    assert_eq!(
        full.state
            .last_period_time_witness
            .as_ref()
            .expect("household witness")
            .contribution_use_ids
            .len(),
        3,
        "both named delegates and the organizer invitation spend actual time"
    );

    let late = babylon_practice_contract::admit_organizer(
        &both,
        &full.state,
        &support::command(&both, &full.state, choice),
    );
    assert_eq!(
        late,
        Err(babylon_practice_contract::OrganizerError::Refused(
            OrganizerRefusal::HearingUnavailable
        ))
    );

    let short = resolve(&both, choice, PARTNER_CONTRIBUTOR, 1)
        .journal
        .hearing
        .expect("scarce hearing");
    assert_eq!(short.claimant.response, Attended);
    assert_eq!(short.partner.response, NoTime);
    assert_eq!(short.outcome, NoQuorum);
    assert_eq!(short.time_use.len(), 1);
    assert_eq!(short.review_access_actor_ids, [] as [u64; 0]);

    for (mandate, response, outcome) in [
        (SpeakOnly, Attended, ReferredToMembers),
        (Withhold, Withheld, NoQuorum),
    ] {
        let limited = config(Settle(JointMinutes), mandate);
        let hearing = resolve(&limited, choice, PARTNER_CONTRIBUTOR, 8)
            .journal
            .hearing
            .expect("limited hearing");
        assert_eq!(hearing.partner.response, response);
        assert_eq!(hearing.outcome, outcome);
        assert_eq!(hearing.review_access_actor_ids, [] as [u64; 0]);
    }

    let mut forged = decoded;
    forged.periods[0]
        .hearing
        .as_mut()
        .expect("hearing")
        .review_access_actor_ids
        .push(both.controlled_actor_id);
    assert!(babylon_practice_contract::encode_organizer_journal(&both, &forged).is_err());
}

#[test]
fn narrow_offer_cannot_settle_for_the_invited_group() {
    let hearing = resolve(
        &config(EitherProceduralOffer, Withhold),
        OrganizerChoice::InviteToHearing(ClaimantOnly),
        PARTNER_CONTRIBUTOR,
        8,
    )
    .journal
    .hearing
    .expect("narrow offer was heard");
    assert_eq!(hearing.partner.response, Withheld);
    assert_eq!(hearing.outcome, Settled);
    assert_eq!(hearing.review_access_actor_ids, [CLAIMANT, CLAIMANT]);
}

#[test]
fn unperformed_invitation_cannot_create_an_offer_or_expose_private_mandate() {
    let config = config(EitherProceduralOffer, SpeakOnly);
    let choice = OrganizerChoice::InviteToHearing(JointMinutes);
    let resolved = resolve(&config, choice, 201, 0);
    let invitation = &resolved.journal.receipts[0];
    assert_eq!(
        invitation.outcome,
        babylon_practice_contract::OrganizerOutcome::InsufficientTime
    );
    assert_eq!(invitation.hours_spent, 0);
    let commitment_id = invitation.commitment_id;
    let mut journal = OrganizerPeriodJournal::empty();
    journal.append(resolved.journal).expect("hearing period");
    let report = babylon_practice_contract::organizer_view(
        &config,
        &resolved.state,
        &journal,
        config.controlled_actor_id,
    )
    .expect("player projection")
    .hearing_receipt
    .expect("claimant kept the home appointment");
    assert_eq!(report.invitation_commitment_id, commitment_id);
    assert_eq!(report.offer, None);
    assert_eq!(report.claimant.response, Attended);
    assert_eq!(report.partner.response, NotInvited);
    assert_eq!(report.partner.mandate, None);
    assert_eq!(report.outcome, NoOffer);
}

#[test]
fn review_period_uses_the_prior_settlement_once_even_across_reopen() {
    for (choice, partner_mandate, expected) in [
        (
            OrganizerChoice::InviteToHearing(JointMinutes),
            Settle(JointMinutes),
            vec![CLAIMANT, PARTNER],
        ),
        (
            OrganizerChoice::InviteToHearing(ClaimantOnly),
            Settle(JointMinutes),
            vec![CLAIMANT, CLAIMANT],
        ),
        (
            OrganizerChoice::InviteToHearing(JointMinutes),
            SpeakOnly,
            vec![],
        ),
        (OrganizerChoice::Hold, SpeakOnly, vec![]),
    ] {
        let config = config(EitherProceduralOffer, partner_mandate);
        let first = resolve(&config, choice, PARTNER_CONTRIBUTOR, 8);
        let hearing = first.journal.hearing.as_ref().expect("hearing happened");
        let source_id = hearing.receipt_id;
        let mut journal = OrganizerPeriodJournal::empty();
        journal.append(first.journal).expect("first period");
        let mut state = first.state;
        for period in 2..=4 {
            let saved =
                babylon_practice_contract::encode_organizer_state(&state).expect("saved organizer");
            state = babylon_practice_contract::decode_organizer_state(&saved)
                .expect("reopened organizer");
            let before = babylon_practice_contract::organizer_view(
                &config,
                &state,
                &journal,
                config.controlled_actor_id,
            )
            .expect("prior organizer view");
            if period == 2 {
                assert!(before.hearing_review.is_none());
            }
            let mut resources = aid::time(&config, PARTNER_CONTRIBUTOR, 8);
            resources.period = period;
            let next = babylon_practice_contract::resolve_organizer_period_with_time(
                &config,
                &state,
                &support::facts(period, 160),
                None,
                &resources,
                OrganizerMaterialSupport {
                    aid: &[],
                    collection: None,
                },
            )
            .expect("later period advances");
            if period == 2 {
                let review = next
                    .journal
                    .hearing_review
                    .as_ref()
                    .expect("review roll issued");
                assert_eq!(review.speaker_actor_ids, expected);
                assert_eq!(review.hearing_receipt_id, source_id);
                assert_eq!(review.period, 2);
                assert!(next.state.pending_hearing_review.is_none());
                assert!(next
                    .journal
                    .receipts
                    .iter()
                    .flat_map(|r| &r.time_use)
                    .all(|row| { row.actor_id != CLAIMANT && row.actor_id != PARTNER }));
            } else {
                assert!(next.journal.hearing_review.is_none());
            }
            journal.append(next.journal).expect("later journal period");
            state = next.state;
        }
        let saved = babylon_practice_contract::encode_organizer_journal(&config, &journal)
            .expect("authenticated agenda saved");
        let journal = babylon_practice_contract::decode_organizer_journal(&config, &saved)
            .expect("authenticated agenda reopened");
        let snapshot = babylon_practice_contract::organizer_view(
            &config,
            &state,
            &journal,
            config.controlled_actor_id,
        )
        .expect("review remains available");
        assert_eq!(
            snapshot
                .hearing_review
                .expect("retained review agenda")
                .speaker_actor_ids,
            expected
        );
        assert_forged_agenda_refused(&config, journal, &expected);
    }
}

/// A saved journal whose dated review agenda was altered must not re-authenticate.
fn assert_forged_agenda_refused(
    config: &OrganizerConfig,
    mut forged: OrganizerPeriodJournal,
    expected: &[u64],
) {
    let agenda = forged.periods[1]
        .hearing_review
        .as_mut()
        .expect("dated agenda");
    agenda.speaker_actor_ids = if expected.is_empty() {
        vec![CLAIMANT, PARTNER]
    } else {
        vec![]
    };
    assert!(babylon_practice_contract::encode_organizer_journal(config, &forged).is_err());
}

#[test]
fn funded_claimant_contributor_can_stand_in_and_testify_after_first_budget_exhausts() {
    let mut config = config(SpeakOnly, Withhold);
    let mut alternate = config
        .participants
        .last()
        .expect("claimant contributor")
        .clone();
    alternate.contributor_id += 1;
    let alternate_id = alternate.contributor_id;
    config.participants.push(alternate);
    let OrganizerTimeBindingMode::Household { bindings } = &mut config.time_binding else {
        panic!("hearing fixture must have actual household time");
    };
    bindings.push(OrganizerHouseholdBinding {
        contributor_id: alternate_id,
        principal_id: [207; 32],
    });
    let first = resolve(&config, OrganizerChoice::Hold, CLAIMANT_CONTRIBUTOR, 0);
    let receipt = first.journal.hearing.expect("hearing happened");
    assert_eq!(receipt.claimant.response, Attended);
    assert_eq!(receipt.time_use[0].contributor_id, alternate_id);
    assert_eq!(receipt.testimony.len(), 1);
    assert_eq!(receipt.testimony[0].actor_id, CLAIMANT);
    assert_eq!(receipt.testimony[0].period, 1);
    assert_eq!(receipt.testimony[0].delegate_label, "Assembly secretary");
    assert_eq!(receipt.testimony[0].claim, receipt.claimant.claim);
    assert_eq!(receipt.review_access_actor_ids, [] as [u64; 0]);
}
