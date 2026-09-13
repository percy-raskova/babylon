//! Text projections over granted organizer records, never material ledger truth.

use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerInquiry, OrganizerObservation, OrganizerOutcome,
    OrganizerPartnerResponse, OrganizerPauseReason, OrganizerRefusal, OrganizerReport,
    OrganizerView,
};
use std::fmt::Write as _;

use super::{evidence::EvidenceMode, OrganizerClient, OrganizerInspector};

pub(super) fn choice(value: OrganizerChoice) -> &'static str {
    match value {
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost) => "Inquiry · work and output",
        OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived) => {
            "Inquiry · maintenance received"
        }
        OrganizerChoice::Reinforce => "Reinforce the workplace relationship",
        OrganizerChoice::Hold => "Hold the current course",
        OrganizerChoice::PauseStanding => "Pause standing work",
        OrganizerChoice::ResumeStanding => "Authorize / resume standing work",
    }
}

pub(super) fn refusal(value: OrganizerRefusal) -> &'static str {
    match value {
        OrganizerRefusal::WrongCampaign => {
            "The campaign changed. Refresh and review this ruling again."
        }
        OrganizerRefusal::WrongAuthority => {
            "This ruling is outside the organization's current authority."
        }
        OrganizerRefusal::StalePeriod => {
            "The period changed. Refresh and review this ruling again."
        }
        OrganizerRefusal::ContentChanged | OrganizerRefusal::ResourceContractChanged => {
            "The campaign's action terms changed. Reopen and review again."
        }
        OrganizerRefusal::InsufficientCommittedTime => {
            "The organization has insufficient committed time for this practice."
        }
        OrganizerRefusal::StandingWorkPaused => "Standing work is already paused.",
        OrganizerRefusal::StandingWorkAlreadyActive => "Standing work is already authorized.",
        OrganizerRefusal::InvalidCommand => {
            "This ruling is unavailable under the current action contract."
        }
    }
}

pub(super) fn partner(view: &OrganizerView, actor: u64) -> &str {
    if actor == view.workplace_partner_id {
        &view.workplace_partner_label
    } else if actor == view.neighborhood_partner_id {
        &view.neighborhood_partner_label
    } else if actor == view.actor_id {
        &view.organization_label
    } else {
        "An attributed participant"
    }
}

fn report(value: &OrganizerReport) -> String {
    match value {
        OrganizerReport::ReducedWork { previous_labor_hours, performed_labor_hours } => format!(
            "Less work was performed: {performed_labor_hours} labor-hours, compared with {previous_labor_hours} in the previous period."
        ),
        OrganizerReport::Work { performed_labor_hours, output_kg, previous_labor_hours, previous_output_kg } => {
            let mut text = format!("Work performed: {performed_labor_hours} labor-hours. Output: {output_kg} kg.");
            if let Some(hours) = previous_labor_hours { let _ = write!(text, " Previous work: {hours} labor-hours."); }
            if let Some(output) = previous_output_kg { let _ = write!(text, " Previous output: {output} kg."); }
            text
        },
        OrganizerReport::Maintenance { enabled_batches, consumed_batches, expired_batches } => format!(
            "Maintenance service received: {enabled_batches} enabled batches; {consumed_batches} used; {expired_batches} expired. These are consumer records, not the provider's private accounts."
        ),
    }
}

pub(super) fn observation(
    view: &OrganizerView,
    item: &OrganizerObservation,
    current_period: u64,
) -> String {
    let age = if item.observed_period < current_period {
        "HISTORICAL REPORT"
    } else {
        "REPORTED"
    };
    let source = item.receipt_id.map_or_else(
        || {
            if item.observed_period == 0 && item.acquired_period == 0 {
                "Captured initial report · period 0".into()
            } else {
                format!(
                    "Automatic report from {} · source actor {}",
                    partner(view, item.source_actor_id),
                    item.source_actor_id
                )
            }
        },
        |receipt| {
            receipt
                .iter()
                .fold(String::from("Committed receipt "), |mut text, byte| {
                    let _ = write!(text, "{byte:02x}");
                    text
                })
        },
    );
    format!(
        "{age} · period {} · {}\n{}\nAcquired period {}. {}",
        item.observed_period,
        partner(view, item.source_actor_id),
        report(&item.report),
        item.acquired_period,
        source
    )
}

pub(super) fn situation(view: &OrganizerView, period: u64) -> String {
    let latest = view
        .observations
        .iter()
        .filter(|item| item.acquired_period <= period)
        .max_by_key(|item| (item.observed_period, item.acquired_period));
    latest.map_or_else(
        || "No workplace report has been obtained for this view. Inquiry can seek a bounded report; an attempt does not guarantee a response.".into(),
        |item| observation(view, item, period),
    )
}

pub(super) fn means(view: &OrganizerView) -> String {
    let standing = if view.standing.authorized {
        "AUTHORIZED"
    } else {
        match view.standing.paused_reason {
            Some(OrganizerPauseReason::Explicit) => "PAUSED BY YOUR RULING",
            Some(OrganizerPauseReason::InsufficientCommittedTime) => {
                "PAUSED · INSUFFICIENT COMMITTED TIME"
            }
            None => "AWAITING AUTHORIZATION",
        }
    };
    format!("CURRENT ORGANIZATION · committed period {}\n{}\n{} organizer-hours committed for practice\n\nSTANDING WORK · {standing}\n{}\nOne scoped contact practice: {} hours. A special commitment replaces it for one period. Hold continues it; Pause is a separate ruling.\n\nPeople, organizational time, and contact terms are Designed scenario content. Organizer-hours are not industrial jobs or wages.",
        view.period, view.organization_label, view.available_hours, partner(view, view.standing.partner_actor_id), view.contact_hours)
}

pub(super) fn review(
    client: &OrganizerClient,
    historical: bool,
    complete: bool,
    resolving: bool,
) -> String {
    if complete {
        return "CAMPAIGN COMPLETE\nNo further period can resolve. Inspect retained reports, practice receipts, and disagreements, or start another campaign from Menu.".into();
    }
    if historical {
        return "HISTORICAL INSPECTION\nReturn Live before reviewing or submitting a ruling. Your selected approach and personal notes remain in the draft.".into();
    }
    if resolving {
        let period = client
            .commitment
            .as_ref()
            .map(|value| value.resolves_period)
            .or_else(|| client.view.as_ref()?.period.checked_add(1));
        let period = period.map_or_else(|| "pending".into(), |value| value.to_string());
        let practice = client.commitment.as_ref().map_or_else(
            || {
                if client
                    .view
                    .as_ref()
                    .is_some_and(|view| view.standing.authorized)
                {
                    "The authorized standing practice is being resolved.".into()
                } else {
                    "No standing routine is authorized for this period.".into()
                }
            },
            |value| {
                format!(
                    "{} · your accepted ruling remains fixed.",
                    choice(value.command.choice)
                )
            },
        );
        return format!("RESOLVING · period {period}\n{practice}\nNo outcome is credited before the period commits. Its receipt will separate performed work, partner response and earned evidence.");
    }
    if let Some(commitment) = &client.commitment {
        let mut text = format!(
            "ACCEPTED · resolves period {}\n{}\n",
            commitment.resolves_period,
            choice(commitment.command.choice)
        );
        if let Some(view) = &client.view {
            let hours = match commitment.command.choice {
                OrganizerChoice::Inquiry(_) => view.inquiry_hours,
                OrganizerChoice::Reinforce | OrganizerChoice::ResumeStanding => view.contact_hours,
                OrganizerChoice::Hold if view.standing.authorized => view.contact_hours,
                OrganizerChoice::Hold | OrganizerChoice::PauseStanding => 0,
            };
            let _ = writeln!(text, "{hours} of {} organizer-hours committed to this ruling; expenditure occurs when the period resolves.", view.available_hours);
        }
        text.push_str("Your ruling is fixed for this period. Advance to receive the engine's actual result. Other organizations control their participation.");
        return text;
    }
    let Some(preview) = &client.preview else {
        return "Select an approach, then review its actual cost and resolving period. Choosing an approach and writing notes execute nothing.".into();
    };
    let mut text = format!(
        "REVIEW · {}\nResolves period {} · {} of {} organizer-hours\n{}\n",
        choice(preview.choice),
        preview.resolves_period,
        preview.required_hours,
        preview.available_hours,
        match preview.choice {
            OrganizerChoice::PauseStanding => "Pauses the saved routine from the resolving period until you explicitly resume it. Its practice and scope remain saved.",
            OrganizerChoice::ResumeStanding => "Authorizes and performs the saved routine in the resolving period. It continues afterward while eligible.",
            OrganizerChoice::Hold => "Continues the saved routine if authorized; Hold does not resume a paused routine.",
            OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce if preview.replaces_standing_work => "Replaces standing work for this period only; eligibility governs its later resumption.",
            OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce => "Performs this specific practice for one period. The saved routine remains paused.",
        }
    );
    if let Some(reason) = preview.refusal {
        let _ = write!(text, "\nUNAVAILABLE · {}", refusal(reason));
    } else {
        text.push_str("\nConfirming sets our organization's ruling. It grants no control over a partner, no guaranteed knowledge, and no factory recovery.");
    }
    text
}

fn outcome(value: OrganizerOutcome) -> &'static str {
    match value {
        OrganizerOutcome::EvidenceObtained => "Evidence obtained",
        OrganizerOutcome::EvidenceWithheld => "Attempt completed; evidence unavailable",
        OrganizerOutcome::ContactCompleted => "Mutual contact completed",
        OrganizerOutcome::ContactUncompleted => "Contact attempt uncompleted",
        OrganizerOutcome::InsufficientTime => "Insufficient committed time",
        OrganizerOutcome::StandingPaused => "Standing work paused",
        OrganizerOutcome::StandingResumed => "Standing work resumed",
        OrganizerOutcome::NoAuthorizedPractice => "No authorized practice",
    }
}

fn response(value: OrganizerPartnerResponse) -> &'static str {
    match value {
        OrganizerPartnerResponse::Participated => "participated",
        OrganizerPartnerResponse::Refused => "declined",
        OrganizerPartnerResponse::NoResponse => "no response; consent is not inferred",
        OrganizerPartnerResponse::UnableToParticipate => "unable to participate",
        OrganizerPartnerResponse::NotRequested => "not requested",
    }
}

fn evidence_inspector(
    client: &OrganizerClient,
    view: &OrganizerView,
    period: u64,
) -> (String, String) {
    let saved = client.evidence.mode == EvidenceMode::Saved;
    let title = format!(
        "{} · {}",
        if saved {
            "Personal draft references"
        } else {
            "Circuit evidence"
        },
        view.workplace_label
    );
    let mut text = String::from("WORKPLACE EVIDENCE\nThese reports describe one observed period. References are personal presentation, not new knowledge or executable instructions. Provider-private accounts remain undisclosed. Wages, shift schedules and household consumption are unmodeled.\n\n");
    let Some(id) = client.selected_evidence_id(period) else {
        text.push_str(if saved {
            "No saved references. Open Workplace evidence and keep a report in the draft."
        } else {
            "No acquired workplace report is available at this period."
        });
        return (title, text);
    };
    let ids = client.evidence_ids(period);
    if let Some(index) = ids.iter().position(|item| *item == id) {
        let _ = writeln!(text, "REPORT {} OF {}\n", index + 1, ids.len());
    }
    let Some(item) = client.lawful_evidence(id, period) else {
        text.push_str("This reference is unavailable in this inspected view. Return Live or select another report. A saved reference grants no additional access.");
        return (title, text);
    };
    text.push_str(if client.evidence_is_saved(id) {
        "IN PERSONAL DRAFT\n\n"
    } else {
        "NOT IN PERSONAL DRAFT\n\n"
    });
    text.push_str(&observation(view, item, period));
    (title, text)
}

pub(super) fn inspector(client: &OrganizerClient, period: u64) -> (String, String) {
    let Some(view) = &client.view else {
        return (
            "Organization".into(),
            "Awaiting the lawful campaign situation.".into(),
        );
    };
    match client.inspector {
        OrganizerInspector::Closed => (String::new(), String::new()),
        OrganizerInspector::Evidence => evidence_inspector(client, view, period),
        OrganizerInspector::Relationships => {
            let mut text = format!("CURRENT COMMUNICATION AGREEMENTS · committed period {}\nAn agreement permits a scoped exchange; it does not grant control over the partner or imply workforce-wide membership.\n\n", view.period);
            if period != view.period {
                let _ = writeln!(text, "Held history is period {period}. These agreement terms describe the current committed period {}; they are not a reconstruction of historical agreements.\n", view.period);
            }
            for agreement in &view.agreements {
                let active = agreement.valid_from_period <= view.period
                    && view.period <= agreement.valid_through_period;
                let _ = writeln!(
                    text,
                    "{}\n{} · periods {}–{}\n{}\n",
                    partner(view, agreement.partner_actor_id),
                    if active {
                        "IN SCOPE AT CURRENT PERIOD"
                    } else {
                        "OUTSIDE CURRENT PERIOD"
                    },
                    agreement.valid_from_period,
                    agreement.valid_through_period,
                    if agreement.source_product_id.is_some() {
                        "Supported by consumed contact evidence."
                    } else {
                        "Captured opening agreement · Designed."
                    }
                );
            }
            ("Relationships and cooperation".into(), text)
        }
        OrganizerInspector::Direction => {
            let mut text = String::from("CURRENT DIRECTION AND DISAGREEMENTS\nThe commitments below describe the current organization; the usage receipt is filtered to the inspected period. You make the organization's final ruling. A recorded objection is neither a veto nor universal agreement. Participants' committed time limits what can be carried out.\n\n");
            for position in &view.positions {
                let used: u64 = view
                    .receipts
                    .iter()
                    .filter(|receipt| receipt.period == period)
                    .flat_map(|receipt| &receipt.time_use)
                    .filter(|time| time.contributor_id == position.contributor_id)
                    .map(|time| time.hours)
                    .sum();
                let _ = writeln!(text, "{} · {} hours committed; {used} used in period {period}\nConcern: {}\nPreserved objection: {}\nReview when: {}\n", position.label, position.promised_hours, position.concern, position.objection, position.review_condition);
            }
            text.push_str("Compare these commitments with the receipts. A production recovery does not settle unanswered income or participation questions. No score certifies political correctness.");
            ("Direction and disagreements".into(), text)
        }
        OrganizerInspector::Receipts => {
            let mut text = String::from("COMMITTED PRACTICE HISTORY\nFactory output and maintenance recovery remain separate from organizational outcomes.\n\n");
            for receipt in view
                .receipts
                .iter()
                .filter(|receipt| receipt.period <= period && receipt.actor_id == view.actor_id)
                .rev()
            {
                let _ = writeln!(text, "PERIOD {} · {}\n{} · {} organizer-hours spent\nPartner: {}\n{} evidence record(s). {}\n", receipt.period,
                    if receipt.standing_work { "Standing work" } else { choice(receipt.choice) }, outcome(receipt.outcome), receipt.hours_spent,
                    response(receipt.partner_response), receipt.observation_ids.len(),
                    if receipt.contact_product_id.is_some() { "Completed contact evidence can support a later report-exchange commitment." } else { "No contact product credited." });
            }
            if !view
                .receipts
                .iter()
                .any(|receipt| receipt.period <= period && receipt.actor_id == view.actor_id)
            {
                text.push_str("No practice has completed at this period.");
            }
            ("Practice receipts and aftermath".into(), text)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::runtime_session::{OrganizerAgreement, OrganizerStandingWork};

    fn view() -> OrganizerView {
        OrganizerView {
            period: 5,
            actor_id: 90,
            authority_id: [1; 16],
            organization_label: "Fixture collective".into(),
            workplace_id: 91,
            workplace_label: "Fixture workplace".into(),
            workplace_partner_id: 92,
            workplace_partner_label: "Fixture workplace contacts".into(),
            neighborhood_partner_id: 93,
            neighborhood_partner_label: "Fixture neighborhood contacts".into(),
            available_hours: 16,
            inquiry_hours: 12,
            contact_hours: 8,
            content_digest: [2; 32],
            resource_digest: [3; 32],
            standing: OrganizerStandingWork {
                partner_actor_id: 93,
                authorized: false,
                paused_reason: Some(OrganizerPauseReason::Explicit),
            },
            agreements: vec![],
            observations: vec![],
            receipts: vec![],
            positions: vec![],
        }
    }

    #[test]
    fn held_history_does_not_reinterpret_current_communication_agreements() {
        let mut view = view();
        view.agreements = vec![OrganizerAgreement {
            actor_id: view.actor_id,
            partner_actor_id: view.workplace_partner_id,
            valid_from_period: 0,
            valid_through_period: 3,
            source_product_id: None,
        }];
        let mut client = OrganizerClient {
            view: Some(view),
            inspector: OrganizerInspector::Relationships,
            ..OrganizerClient::default()
        };
        // It was valid in held period 2, but this DTO describes committed period 5.
        let (_, expired) = inspector(&client, 2);
        assert!(expired.contains("CURRENT COMMUNICATION AGREEMENTS · committed period 5"));
        assert!(expired.contains("Held history is period 2"));
        assert!(expired.contains("OUTSIDE CURRENT PERIOD"));
        assert!(!expired.contains("IN SCOPE"));

        // Renewal replaces the mutable row; do not hide it using the older period.
        let agreement = &mut client.view.as_mut().unwrap().agreements[0];
        agreement.valid_from_period = 4;
        agreement.valid_through_period = 6;
        agreement.source_product_id = Some([7; 32]);
        let (_, renewed) = inspector(&client, 2);
        assert!(renewed.contains("IN SCOPE AT CURRENT PERIOD"));
        assert!(renewed.contains("periods 4–6"));
        assert!(renewed.contains("current committed period"));
        assert!(means(client.view.as_ref().unwrap())
            .contains("CURRENT ORGANIZATION · committed period 5"));
    }

    #[test]
    fn report_provenance_distinguishes_opening_automatic_and_inquiry_sources() {
        let view = view();
        let mut item = OrganizerObservation {
            observation_id: [1; 32],
            actor_id: view.actor_id,
            subject_id: view.workplace_id,
            source_actor_id: view.workplace_partner_id,
            observed_period: 2,
            acquired_period: 2,
            receipt_id: None,
            report: OrganizerReport::ReducedWork {
                previous_labor_hours: 160,
                performed_labor_hours: 0,
            },
        };
        let automatic = observation(&view, &item, 5);
        assert!(automatic.contains("Automatic report from Fixture workplace contacts"));
        assert!(automatic.contains("source actor 92"));
        assert!(!automatic.contains("Captured initial report"));
        item.observed_period = 0;
        item.acquired_period = 0;
        assert!(observation(&view, &item, 5).contains("Captured initial report · period 0"));
        item.receipt_id = Some([7; 32]);
        assert!(observation(&view, &item, 5)
            .contains(&format!("Committed receipt {}", "07".repeat(32))));
    }

    #[test]
    fn standing_controls_explain_their_resolving_effect_before_submission() {
        use babylon_persistence::runtime_session::OrganizerPreview;

        for (choice, hours, explanation) in [
            (
                OrganizerChoice::PauseStanding,
                0,
                "until you explicitly resume",
            ),
            (
                OrganizerChoice::ResumeStanding,
                8,
                "performs the saved routine",
            ),
            (OrganizerChoice::Hold, 0, "does not resume a paused routine"),
        ] {
            let client = OrganizerClient {
                view: Some(view()),
                preview: Some(OrganizerPreview {
                    choice,
                    current_period: 5,
                    resolves_period: 6,
                    available_hours: 16,
                    required_hours: hours,
                    replaces_standing_work: false,
                    refusal: None,
                    observations: vec![],
                }),
                ..OrganizerClient::default()
            };
            let text = review(&client, false, false, false);
            assert!(text.contains(explanation), "{text}");
            assert!(text.contains(&format!("Resolves period 6 · {hours} of 16")));
            assert!(!text.contains("preserves the explicit standing-work authorization"));
        }
    }
}
