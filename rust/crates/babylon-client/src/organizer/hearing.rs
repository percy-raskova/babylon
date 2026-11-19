//! Player-facing hearing notice, committed minutes, and county review.
use super::ui::{self, DetailControls, OrganizerAction};
use super::{OrganizerClient, OrganizerInspector};
use crate::observer::ObserverSession;
use babylon_persistence::runtime_session::{
    OrganizerAidKind, OrganizerChoice, OrganizerHearingDelegation, OrganizerHearingMandate,
    OrganizerHearingNotice, OrganizerHearingOffer, OrganizerHearingOutcome,
    OrganizerHearingReceipt, OrganizerHearingResponse, OrganizerHearingReview,
    OrganizerHearingSeat, OrganizerKnownAidPartner, OrganizerView,
};
use bevy::prelude::*;
use std::fmt::Write as _;

pub(super) fn invitee(view: &OrganizerView) -> Option<&OrganizerKnownAidPartner> {
    view.aid_partners
        .iter()
        .find(|partner| partner.kind == OrganizerAidKind::Local)
}

pub(super) fn invitation(view: &OrganizerView) -> Option<&OrganizerHearingNotice> {
    view.hearing
        .as_ref()
        .filter(|hearing| Some(hearing.period) == view.period.checked_add(1))
        .filter(|_| invitee(view).is_some())
}

fn minutes(view: &OrganizerView, period: u64) -> Option<&OrganizerHearingReceipt> {
    view.hearing_receipt
        .as_ref()
        .filter(|receipt| receipt.period <= period)
}

pub(super) fn committed_review(
    view: &OrganizerView,
    period: u64,
) -> Option<&OrganizerHearingReview> {
    let hearing = minutes(view, period)?;
    view.hearing_review.as_ref().filter(|review| {
        review.period <= period
            && review.period == hearing.review_period
            && review.hearing_receipt_id == hearing.receipt_id
            && review.county_geoid == hearing.county_geoid
    })
}

pub(super) fn map_entry<'a>(
    client: &'a OrganizerClient,
    session: &ObserverSession,
) -> Option<(&'a str, u64, &'static str)> {
    if client.campaign != Some(*session.campaign.as_uuid()) {
        return None;
    }
    let view = client.view.as_ref()?;
    let period = session.viewed_tick;
    if let Some(review) = committed_review(view, period) {
        return Some((&review.county_geoid, review.period, "County review"));
    }
    if let Some(receipt) = minutes(view, period) {
        return Some((&receipt.county_geoid, receipt.period, "Hearing minutes"));
    }
    if view.period != period || session.durable_tick != period {
        return None;
    }
    let hearing = view.hearing.as_ref()?;
    invitee(view)?;
    Some((&hearing.county_geoid, hearing.period, "Hearing notice"))
}

pub(super) fn has_entry(client: &OrganizerClient, session: &ObserverSession) -> bool {
    map_entry(client, session).is_some()
}

pub(super) const fn label(offer: OrganizerHearingOffer) -> &'static str {
    match offer {
        OrganizerHearingOffer::ClaimantOnly => "Invite with claimant-only terms",
        OrganizerHearingOffer::JointMinutes => "Invite with joint minutes",
    }
}

pub(super) const fn terms(offer: OrganizerHearingOffer) -> &'static str {
    match offer {
        OrganizerHearingOffer::ClaimantOnly => {
            "The claimants keep the opening and reply. Only their delegate has to attend and agree."
        }
        OrganizerHearingOffer::JointMinutes => {
            "The claimants open and the invited group gets the reply. Both delegates have to attend and agree."
        }
    }
}

pub(super) fn spawn_choices(body: &mut ChildSpawnerCommands) {
    body.spawn((ui::column(), DetailControls(OrganizerInspector::Hearing)))
        .with_children(|panel| {
            for offer in [
                OrganizerHearingOffer::JointMinutes,
                OrganizerHearingOffer::ClaimantOnly,
            ] {
                ui::button(
                    panel,
                    label(offer),
                    OrganizerAction::Choose(OrganizerChoice::InviteToHearing(offer)),
                );
            }
        });
}

pub(super) fn notice(view: &OrganizerView, period: u64, live: bool) -> String {
    if let Some(receipt) = minutes(view, period) {
        return report(receipt, committed_review(view, period));
    }
    if let (Some(hearing), Some(partner)) = (&view.hearing, invitee(view)) {
        if live && view.period == period {
            let decision = if invitation(view).is_some() {
                format!(
                    "\n\nJoint minutes · {}\n\nClaimant-only · {}\n\nWith either invitation, a delegate who attends can enter a demand in the minutes. Members set the limits of any agreement. New terms go back to them. If you keep the current routine, the claimants can still testify. The next review reserves no turns.",
                    terms(OrganizerHearingOffer::JointMinutes),
                    terms(OrganizerHearingOffer::ClaimantOnly),
                )
            } else {
                "\n\nInvitations open in the period before the hearing.".into()
            };
            return format!(
                "Hearing in period {} · Wayne hearing notice at period {}\n\nStanding seat · {}\n{}\n{}\n\nInvitation seat · {}\n{}\n{}\n\nIssuing an invitation uses {} organizer-hours. Each attending group needs {} hours of its own time. The next review is scheduled for period {}. Aid decisions remain with the ordinary accounts.{decision}",
                hearing.period,
                view.period,
                hearing.claimant_label,
                delegation(&hearing.claimant_delegation),
                hearing.claimant_claim,
                partner.label,
                delegation(&hearing.partner_delegation),
                hearing.partner_claim,
                hearing.attendance_hours,
                hearing.attendance_hours,
                hearing.review_period,
            );
        }
    }
    "No hearing record is available for this period.".into()
}

fn report(receipt: &OrganizerHearingReceipt, review: Option<&OrganizerHearingReview>) -> String {
    let outcome = match receipt.outcome {
        OrganizerHearingOutcome::NoOffer => {
            "No invitation was issued. The claimant’s standing seat still applied."
        }
        OrganizerHearingOutcome::NoQuorum => {
            "One or more required delegates did not attend. No agreement was reached."
        }
        OrganizerHearingOutcome::ReferredToMembers => {
            "The proposal went back to members because it exceeded a delegate’s authority."
        }
        OrganizerHearingOutcome::Settled if receipt.offer == Some(OrganizerHearingOffer::ClaimantOnly) => {
            "The claimants’ delegate accepted on behalf of the households that authorized them. The agreement covers the claimants alone."
        }
        OrganizerHearingOutcome::Settled => {
            "Both delegates accepted the joint terms on behalf of the households that authorized them."
        }
    };
    let mut text = format!(
        "Period {} · Wayne hearing minutes\n\n{outcome}",
        receipt.period
    );
    if let Some(offer) = receipt.offer {
        let _ = write!(text, "\nTerms on the table · {}", terms(offer));
    }
    for testimony in &receipt.testimony {
        let _ = write!(
            text,
            "\n\nDemand entered in the period {} minutes · {}\n{}",
            testimony.period, testimony.delegate_label, testimony.claim
        );
    }
    append_seat(&mut text, "Standing seat", &receipt.claimant);
    append_seat(&mut text, "Invitation seat", &receipt.partner);
    if review.is_none() && receipt.outcome == OrganizerHearingOutcome::Settled {
        let _ = write!(
            text,
            "\n\nAgreed speaking turns for the period {} review",
            receipt.review_period
        );
        append_turns(&mut text, receipt, &receipt.review_access_actor_ids);
    }
    text.push_str("\nAid decisions remain with the ordinary accounts.");
    if let Some(review) = review {
        let mut report_back = format!("Period {} · County review report back", review.period);
        if review.speaker_actor_ids.is_empty() {
            report_back.push_str("\nThe review recorded no agreed speaking turns.");
        } else {
            report_back.push_str("\nThe county docket recorded these turns.");
            append_turns(&mut report_back, receipt, &review.speaker_actor_ids);
        }
        report_back.push_str("\n\n");
        report_back.push_str(&text);
        return report_back;
    }
    text
}

fn append_turns(text: &mut String, hearing: &OrganizerHearingReceipt, speakers: &[u64]) {
    for (turn, actor) in ["Opening", "Reply"].into_iter().zip(speakers) {
        if let Some(seat) = [&hearing.claimant, &hearing.partner]
            .into_iter()
            .find(|seat| seat.actor_id == *actor)
        {
            let _ = write!(text, "\n{turn} · {}", seat.label);
        }
    }
}

fn delegation(value: &OrganizerHearingDelegation) -> String {
    let unit = if value.authorizing_households == 1 {
        "household"
    } else {
        "households"
    };
    format!(
        "{} · authorized by {} {unit}",
        value.delegate_label, value.authorizing_households
    )
}

fn append_seat(text: &mut String, role: &str, seat: &OrganizerHearingSeat) {
    let detail = match seat.response {
        OrganizerHearingResponse::NotInvited => "No invitation was issued.",
        OrganizerHearingResponse::Withheld => "Members did not authorize attendance.",
        OrganizerHearingResponse::NoTime => "The group lacked the committed time to attend.",
        OrganizerHearingResponse::Attended => match seat.mandate {
            Some(OrganizerHearingMandate::Withhold) | None => "Attendance was recorded.",
            Some(OrganizerHearingMandate::EitherProceduralOffer) => {
                "The delegate could settle either proposal as written."
            }
            Some(OrganizerHearingMandate::SpeakOnly) => {
                "The delegate could speak and had to take any settlement back to members."
            }
            Some(OrganizerHearingMandate::Settle(OrganizerHearingOffer::ClaimantOnly)) => {
                "The delegate could settle on claimant-only terms."
            }
            Some(OrganizerHearingMandate::Settle(OrganizerHearingOffer::JointMinutes)) => {
                "The delegate could settle on joint minutes and shared access to the next review."
            }
        },
    };
    let _ = write!(text, "\n\n{role} · {}\n{detail}", seat.label);
    if seat.response == OrganizerHearingResponse::Attended {
        let _ = write!(text, "\n{}", delegation(&seat.delegation));
    }
}
