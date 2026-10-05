//! Text projections over granted organizer records, never material ledger truth.

use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerCommitment, OrganizerGiftConsent, OrganizerInquiry,
    OrganizerObservation, OrganizerOutcome, OrganizerPartnerResponse, OrganizerPauseReason,
    OrganizerRefusal, OrganizerReport, OrganizerView,
};
use babylon_practice_contract::{OrganizerCollectionOutcome, OrganizerCollectionResolution};
use std::fmt::Write as _;

use super::{evidence::EvidenceMode, OrganizerClient, OrganizerInspector};

pub(super) fn choice(value: OrganizerChoice) -> &'static str {
    match value {
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost) => "Ask about work and output",
        OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived) => "Ask about maintenance",
        OrganizerChoice::Reinforce => "Reinforce workplace contact",
        OrganizerChoice::Collect => "Collect a voluntary contribution",
        OrganizerChoice::LocalAid => "Organize local aid",
        OrganizerChoice::RemoteAid => "Organize remote solidarity",
        OrganizerChoice::Hold => "Keep current routine",
        OrganizerChoice::PauseStanding => "Pause neighborhood work",
        OrganizerChoice::ResumeStanding => "Resume neighborhood work",
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
        OrganizerRefusal::CollectionUnavailable => {
            "No captured collection mandate is offered here."
        }
        OrganizerRefusal::CollectionCashRefused => {
            "The household has declined this cash contribution."
        }
        OrganizerRefusal::AidUnavailable => "No captured aid mandate is offered here.",
        OrganizerRefusal::AidReceivingRefused => {
            "The recipient has not consented to receive this gift."
        }
        OrganizerRefusal::PendingAidConflict => "A different aid commitment is already pending.",
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
    } else if let Some(option) = view
        .aid_options
        .iter()
        .find(|option| option.partner_actor_id == actor)
    {
        &option.partner_label
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
        .filter(|item| {
            item.actor_id == view.actor_id
                && item.subject_id == view.workplace_id
                && item.acquired_period <= period
                && item.observed_period <= period
        })
        .max_by_key(|item| (item.observed_period, item.acquired_period));
    latest.map_or_else(
        || {
            if period == 0 {
                "No completed-period report exists yet. An inquiry now still costs time; it cannot obtain that report.".into()
            } else if view.total_observation_count > 0 {
                "The recent snapshot includes no workplace report for this inspected period. Open Cited workplace Archive to review earned older reports.".into()
            } else {
                "No workplace report obtained at this period. An inquiry requests a report; participation and evidence are not guaranteed.".into()
            }
        },
        |item| {
            let age = if item.observed_period == 0 && item.acquired_period == 0 {
                "opening report"
            } else if item.observed_period < period {
                "historical report"
            } else {
                "latest completed period"
            };
            let source = if item.receipt_id.is_some() {
                "inquiry"
            } else if item.observed_period == 0 && item.acquired_period == 0 {
                "captured opening report"
            } else {
                "automatic report"
            };
            format!(
                "{}\nObserved period {} · {age}\n{} · {source} · acquired period {}",
                report(&item.report),
                item.observed_period,
                partner(view, item.source_actor_id),
                item.acquired_period,
            )
        },
    )
}

pub(super) fn context(view: &OrganizerView) -> String {
    let concern = if view.positions.is_empty() {
        "No current concern recorded.".into()
    } else {
        view.positions
            .iter()
            .map(|position| position.concern.as_str())
            .collect::<Vec<_>>()
            .join(" ")
    };
    let routine = if view.standing.authorized {
        format!("authorized · {} hours", view.contact_hours)
    } else {
        match view.standing.paused_reason {
            Some(OrganizerPauseReason::InsufficientCommittedTime) => {
                "paused · insufficient time".into()
            }
            Some(OrganizerPauseReason::InsufficientAvailableTime) => {
                "paused · household time unavailable".into()
            }
            Some(OrganizerPauseReason::Explicit) => "paused by your ruling".into(),
            None => "awaiting authorization".into(),
        }
    };
    format!("Our concern: {concern}\nCurrent neighborhood routine: {routine}\nPartners choose whether to participate.")
}

fn practice_hours(view: &OrganizerView, choice: OrganizerChoice) -> u64 {
    match choice {
        OrganizerChoice::Inquiry(_) => view.inquiry_hours,
        OrganizerChoice::Reinforce | OrganizerChoice::ResumeStanding => view.contact_hours,
        OrganizerChoice::Hold if view.standing.authorized => view.contact_hours,
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            let kind = if choice == OrganizerChoice::LocalAid {
                babylon_persistence::runtime_session::OrganizerAidKind::Local
            } else {
                babylon_persistence::runtime_session::OrganizerAidKind::Remote
            };
            view.aid_options
                .iter()
                .find(|option| option.kind == kind)
                .map_or(0, |option| option.coordination_hours)
        }
        // Authenticated collection hours are carried by the snapshot.
        OrganizerChoice::Collect | OrganizerChoice::Hold | OrganizerChoice::PauseStanding => 0,
    }
}

pub(super) fn client_approach(
    client: &OrganizerClient,
    view: &OrganizerView,
    choice: OrganizerChoice,
) -> String {
    if choice == OrganizerChoice::Collect {
        return collection_detail(client, view);
    }
    if !matches!(
        choice,
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
    ) {
        return approach(view, choice);
    }
    let Some(preview) = client.aid_preview(choice) else {
        return "No authenticated current material terms. Refresh before choosing aid.".into();
    };
    let mut options = view
        .aid_options
        .iter()
        .filter(|option| option.kind == preview.kind);
    let recipient = options.next().filter(|option| {
        options.next().is_none()
            && view.period == preview.period
            && option.receiving_consent == preview.receiving_consent
            && !option.partner_label.trim().is_empty()
    });
    let mut text = recipient.map_or_else(
        || "UNAVAILABLE · Recipient attribution unavailable. Refresh before choosing aid.\n".into(),
        |option| format!("Recipient: {}\n", option.partner_label),
    );
    let _ = writeln!(text, "Material preview: period {}.", preview.period);
    if let Some(period) = preview.period.checked_add(1) {
        let _ = writeln!(text, "Scheduled material resolution: period {period}.");
    } else {
        text.push_str("Scheduled material resolution unavailable. Refresh before choosing aid.\n");
    }
    let consent = match preview.receiving_consent {
        OrganizerGiftConsent::Accept => "accepted",
        OrganizerGiftConsent::Refuse => "refused; gift unavailable",
    };
    if recipient.is_some() {
        let _ = writeln!(text, "Current recipient receiving consent: {consent}; later practice needs a separate agreement.");
    } else {
        let _ = writeln!(text, "Current receiving consent is unverified; preview recorded {consent}. Refresh before choosing aid.");
    }
    text.push_str(&aid_terms(preview));
    text
}

fn aid_terms(
    preview: &babylon_persistence::runtime_session::OrganizerMaterialAidPreview,
) -> String {
    use babylon_persistence::runtime_session::OrganizerAidTransportPreview;
    let surplus = preview.donor_stock.saturating_sub(preview.own_need);
    let mut text = format!(
        "Current pantry: {} units; own food need: {}; protected surplus: {surplus}.\nOrganization cash: {} micro-currency. Gift transfer: {} micro-currency per food unit, separate from any sale.\nCaptured maximum/request: {} food units ({} grams per unit); actual fulfillment may be lower.\nFulfillment: {} household hours per dispatched unit; later coordination: {} hours. These compete with other work.\n",
        preview.donor_stock, preview.own_need, preview.payer_cash, preview.gift_cash_per_unit,
        preview.maximum_quantity, preview.grams_per_unit, preview.fulfillment_hours_per_unit, preview.coordination_hours
    );
    if let Some(offer) = &preview.ordinary_offer {
        let _ = writeln!(text, "Ordinary quoted food price: {} micro-currency per unit; this gift is not a purchase at that price.", offer.unit_price);
    } else {
        text.push_str("No ordinary food quote is available for comparison.\n");
    }
    match &preview.time {
        Some(time) => {
            let _ = writeln!(text, "Last closed period {}: {} household hours remain. This is observed past supply, not next-period reserved time.", time.period, time.remaining_hours);
        }
        None => text.push_str(
            "No closed household time receipt yet; available future hours are unknown.\n",
        ),
    }
    match &preview.transport {
        OrganizerAidTransportPreview::Local => text.push_str("Local aid can reach the pantry in its dispatch period; own needs, cash and time still constrain fulfillment.\n"),
        OrganizerAidTransportPreview::Routed { stages, .. } => {
            let earliest = stages.last().and_then(|stage| stage.departure_period.checked_add(u64::from(stage.travel_periods)));
            if let Some(period) = earliest { let _ = writeln!(text, "Earliest possible arrival: period {period}; not a delivery guarantee."); }
            else { text.push_str("Earliest arrival is unavailable; no arrival guarantee.\n"); }
            for stage in stages {
                let _ = writeln!(text, "Route stage {}: {} periods; loss {} per million; departure preview period {}.", stage.stage_index, stage.travel_periods, stage.loss_ppm, stage.departure_period);
                for capacity in &stage.capacities {
                    match capacity.remaining_grams {
                        Some(grams) => { let _ = writeln!(text, "Shared corridor remaining capacity: {grams} grams; commercial freight competes for it."); }
                        None => text.push_str("Shared corridor capacity at future departure is unknown.\n"),
                    }
                }
            }
        }
    }
    text.push_str("Preview only: no cash, food, freight or time is reserved. Replaces standing work once when admitted; later ordinary work has first call on time. Delivery and same-period consumption may permit a separate independently authorized practice; no agreement is guaranteed.");
    text
}

fn aid_history(client: &OrganizerClient, period: u64) -> String {
    use babylon_persistence::runtime_session::OrganizerAidSupportStatus;
    let mut text = String::from("\nAID SUPPORT · separate from workplace observations\n");
    for pending in &client.pending_aid {
        if pending.admitted_period <= period {
            let label = match pending.kind {
                babylon_persistence::runtime_session::OrganizerAidKind::Local => "local aid",
                babylon_persistence::runtime_session::OrganizerAidKind::Remote => {
                    "remote solidarity"
                }
            };
            if period < pending.dispatch_period {
                let _ = writeln!(text, "Pending {label}: original admission {}. Scheduled dispatch: period {}; no delivery is credited.", pending.admitted_period, pending.dispatch_period);
            } else {
                let _ = writeln!(text, "Pending {label}: original admission {}; dispatch {}. Surviving delivery awaits actual arrival; no later coordination is credited.", pending.admitted_period, pending.dispatch_period);
            }
        }
    }
    for row in client
        .aid_resolutions
        .iter()
        .filter(|row| row.practice.period <= period)
    {
        let _ = writeln!(
            text,
            "{:?}: original admission {}; dispatch {}; actual resolution {}.",
            row.pending.kind,
            row.pending.admitted_period,
            row.pending.dispatch_period,
            row.practice.period
        );
        match row.support.status {
            OrganizerAidSupportStatus::AwaitingDelivery => {
                text.push_str("Surviving freight remains pending.\n");
            }
            OrganizerAidSupportStatus::TerminalFailure => {
                text.push_str("Terminal support failure; no grant and no surviving delivery.\n");
            }
            OrganizerAidSupportStatus::Granted {
                granted_quantity,
                consumed_quantity,
            } => {
                let _ = writeln!(text, "Granted {granted_quantity} units; total same-period recipient consumption of the same good/unit: {consumed_quantity}. Aggregate consumption is not attribution to donated units or proof of additional time.");
            }
        }
        let postings = &row.support.material_postings;
        let _ = writeln!(
            text,
            "Actual material postings in period {}: dispatched food {} units; donor household fulfillment {} hours.",
            row.support.period, postings.dispatched_quantity, postings.fulfillment_hours
        );
        let _ = writeln!(
            text,
            "Aid payer cash: reserved {}; gift paid {}; refunded {} micro-units. These are distinct movements, not repeated expenses.",
            postings.payer_cash_reserved_micros,
            postings.payer_cash_granted_micros,
            postings.payer_cash_refunded_micros
        );
        let _ = writeln!(text, "Independent outcome: {}; partner {}; coordination {} hours. A declined practice never revokes a delivered gift.", outcome(row.practice.outcome), response(row.practice.partner_response), row.practice.hours_spent);
    }
    text
}

pub(super) fn approach(view: &OrganizerView, choice: OrganizerChoice) -> String {
    let hours = practice_hours(view, choice);
    let resolves = view
        .period
        .checked_add(1)
        .map_or_else(|| "unavailable".into(), |period| period.to_string());
    let displacement = if view.standing.authorized {
        "Replaces neighborhood work once"
    } else {
        "Neighborhood routine stays paused"
    };
    match choice {
        OrganizerChoice::Collect => "Captured collection terms require the current runtime snapshot.".into(),
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid =>
            "Gift delivery and later mutual-aid practice require separate evidence. Review the captured material terms before admission.".into(),
        OrganizerChoice::Inquiry(_) => {
            let report = if view.period == 0 {
                "No completed-period report exists yet".into()
            } else {
                format!("Report requested: period {}", view.period)
            };
            format!("{hours} organizer-hours · workplace committee\n{report}\n{displacement}\nResolves period {resolves} · partner decides")
        }
        OrganizerChoice::Reinforce => format!("{hours} organizer-hours · workplace committee\nSeek contact to renew report sharing\n{displacement}\nResolves period {resolves} · partner decides"),
        OrganizerChoice::Hold => {
            let routine = if view.standing.authorized {
                "Attempt the saved contact practice\nYour routine stays authorized"
            } else {
                "No neighborhood practice will run\nYour routine stays paused"
            };
            format!("{hours} organizer-hours · neighborhood group\n{routine}\nResolves period {resolves}")
        }
        OrganizerChoice::PauseStanding => format!("{hours} organizer-hours\nStop the saved neighborhood routine\nStays paused until explicitly resumed\nResolves period {resolves}"),
        OrganizerChoice::ResumeStanding => format!("{hours} organizer-hours · neighborhood group\nAuthorize and attempt the saved routine\nContinues afterward while eligible\nResolves period {resolves} · partner decides"),
    }
}

pub(super) fn aftermath(client: &OrganizerClient, view: &OrganizerView, period: u64) -> String {
    let Some(receipt) = view
        .receipts
        .iter()
        .filter(|receipt| receipt.actor_id == view.actor_id && receipt.period <= period)
        .max_by_key(|receipt| receipt.period)
    else {
        return if view.total_receipt_count > 0 && period > 0 {
            format!("No receipt from this period is included in the recent window. Open Our practice Archive to review period {period}.")
        } else {
            format!("No practice completed at period {period}.")
        };
    };
    let origin = if receipt.commitment_id.is_some() {
        "accepted ruling"
    } else {
        "saved routine"
    };
    if receipt.choice == OrganizerChoice::Collect {
        let actual = client.collection_resolutions.iter().find(|row| {
            row.practice == *receipt
                && row.fact.actor_id == view.actor_id
                && row.fact.period == receipt.period
                && Some(row.fact.original_commitment_id) == receipt.commitment_id
        });
        return actual.map_or_else(
            || format!("Period {} · {origin}\nCollection ruling resolved. Open Our practice Archive for the actual cash and shared-time result.", receipt.period),
            |row| format!("Period {} · {origin}\n{}\n{}", receipt.period, choice(receipt.choice), collection_result(row)),
        );
    }
    let participant = receipt.partner_actor_id.map_or_else(
        || "Partner participation".into(),
        |actor| partner(view, actor).to_owned(),
    );
    let result = if receipt.contact_product_id.is_some() {
        "Contact recorded; agreement can renew next period".into()
    } else if receipt.observation_ids.is_empty() {
        outcome(receipt.outcome).into()
    } else {
        let count = receipt.observation_ids.len();
        let noun = if count == 1 { "report" } else { "reports" };
        format!("{} · {count} {noun} acquired", outcome(receipt.outcome))
    };
    format!(
        "Period {} · {origin}\n{} · {} organizer-hours spent\n{participant}: {}\n{result}",
        receipt.period,
        choice(receipt.choice),
        receipt.hours_spent,
        response(receipt.partner_response),
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
            Some(OrganizerPauseReason::InsufficientAvailableTime) => {
                "PAUSED · HOUSEHOLD TIME UNAVAILABLE"
            }
            None => "AWAITING AUTHORIZATION",
        }
    };
    format!("CURRENT ORGANIZATION · committed period {}\n{}\n{} organizer-hours committed for practice\n\nSTANDING WORK · {standing}\n{}\nOne scoped contact practice: {} hours. A special commitment replaces it for one period. Hold continues it; Pause is a separate ruling.\n\nPeople, organizational time, and contact terms are Designed scenario content. Organizer-hours are not industrial jobs or wages.",
        view.period, view.organization_label, view.available_hours, partner(view, view.standing.partner_actor_id), view.contact_hours)
}

fn resolving_review(client: &OrganizerClient) -> String {
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
                "The authorized neighborhood routine is being resolved.".into()
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
    format!("RESOLVING · period {period}\n{practice}\nNo outcome is credited until the period commits. Partner response and evidence are reported separately.")
}

fn accepted_aid_review(client: &OrganizerClient, commitment: &OrganizerCommitment) -> String {
    let mut text = format!(
        "ACCEPTED · material resolution period {}\n{}",
        commitment.resolves_period,
        choice(commitment.command.choice)
    );
    if let Some(preview) = client.aid_preview(commitment.command.choice) {
        let _ = write!(
            text,
            " · later coordination: {} hours",
            preview.coordination_hours
        );
    } else {
        text.push_str(" · later coordination requirement unavailable; refresh");
    }
    text.push_str("\nRuling fixed. Advance for material resolution. Later coordination depends on delivery, consumption, finite contributions and independent authorization; no coordination time is reserved.");
    text
}

pub(super) fn review(
    client: &OrganizerClient,
    historical: bool,
    complete: bool,
    resolving: bool,
) -> String {
    if complete {
        return "CAMPAIGN COMPLETE\nInspect the retained reports and practice history, or start another campaign from Menu.".into();
    }
    if historical {
        return "HISTORICAL INSPECTION\nReturn Live to make a ruling. Your approach and notes remain in the draft.".into();
    }
    if resolving {
        return resolving_review(client);
    }
    if let Some(commitment) = &client.commitment {
        if matches!(
            commitment.command.choice,
            OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
        ) {
            return accepted_aid_review(client, commitment);
        }
        if commitment.command.choice == OrganizerChoice::Collect {
            let terms = client.collection_preview().map_or_else(
                || "Captured original collection ruling".into(),
                |m| {
                    format!(
                        "{} · up to {} currency · {} shared material hours",
                        m.contributor_label,
                        currency(m.maximum_cash_micros),
                        m.collection_hours
                    )
                },
            );
            return format!("ACCEPTED · collection resolution period {}\n{terms}. Protected needs and fixed shared time are checked at close.\nReplaces saved routine once; no standing fallback. Actual full, partial or refused payment appears after Advance. Later aid needs its own ruling.", commitment.resolves_period);
        }
        let mut text = format!(
            "ACCEPTED · resolves period {}\n{}",
            commitment.resolves_period,
            choice(commitment.command.choice)
        );
        if let Some(view) = &client.view {
            let hours = practice_hours(view, commitment.command.choice);
            let _ = write!(
                text,
                " · {hours} of {} organizer-hours committed",
                view.available_hours
            );
        }
        text.push_str("\nRuling fixed. Advance to resolve; partners decide their participation.");
        return text;
    }
    let Some(preview) = &client.preview else {
        let advance = client.view.as_ref().map_or_else(
            || "Waiting for the current organization before advancing.".into(),
            |view| if view.standing.authorized {
                format!("Without a confirmed ruling, Advance attempts neighborhood contact for {} organizer-hours.", view.contact_hours)
            } else {
                "The routine is paused. Without a confirmed ruling, Advance runs no organizational practice.".into()
            },
        );
        return format!(
            "DRAFT · {}\nReview the choice, then Confirm. {advance}",
            choice(client.choice())
        );
    };
    let mut text = format!(
        "REVIEW · {}\nResolves period {} · {} of {} organizer-hours\n{}",
        choice(preview.choice),
        preview.resolves_period,
        preview.required_hours,
        preview.available_hours,
        match preview.choice {
            OrganizerChoice::Collect => "Replaces standing work once. Protected consumption, services, closing stock, due payments, independent cash consent and shared material time are checked at close. A gift can fund later aid; no instant membership, agreement or time gain.",
            OrganizerChoice::PauseStanding =>
                "Pauses the saved routine until you explicitly resume it.",
            OrganizerChoice::ResumeStanding =>
                "Authorizes and performs the saved routine; continues afterward while eligible.",
            OrganizerChoice::Hold => "Keeps the saved routine; does not resume a paused routine.",
            OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid =>
                "Gift receiving consent does not guarantee later partner participation.",
            OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce
                if preview.replaces_standing_work =>
                "Replaces neighborhood work once; later work remains subject to eligibility.",
            OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce =>
                "One specific practice; the neighborhood routine remains paused.",
        }
    );
    if matches!(
        preview.choice,
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
    ) {
        text.push_str("\nMaterial terms are shown in the aid card above. This review reserves nothing; the host checks dispatch and independent practice separately.");
    }
    if let Some(reason) = preview.refusal {
        let _ = write!(text, "\nUNAVAILABLE · {}", refusal(reason));
    } else if matches!(preview.choice, OrganizerChoice::Inquiry(_)) {
        if preview.current_period == 0 {
            let _ = write!(text, "\nNo completed-period report exists. An admitted inquiry still spends {} organizer-hours.", preview.required_hours);
        } else {
            let _ = write!(text, "\nReport requested: period {}. Partner participation is independent; no report is guaranteed.", preview.current_period);
        }
    } else if preview.choice == OrganizerChoice::Collect {
        text.push_str("\nThis review reserves nothing. Confirm records the original ruling; Advance reports its actual collection or refusal.");
    } else if preview.choice != OrganizerChoice::PauseStanding {
        text.push_str(
            "\nPartner participation is independent. Confirm sets our ruling; Advance resolves it.",
        );
    }
    text
}

fn outcome(value: OrganizerOutcome) -> &'static str {
    match value {
        OrganizerOutcome::CollectionCompleted => {
            "Voluntary contribution collected; funds available for later aid"
        }
        OrganizerOutcome::CollectionRefused => {
            "Collection refused; original ruling resolved without standing fallback"
        }
        OrganizerOutcome::EvidenceObtained => "Evidence obtained",
        OrganizerOutcome::EvidenceWithheld => "No report obtained",
        OrganizerOutcome::ContactCompleted => "Mutual contact completed",
        OrganizerOutcome::ContactUncompleted => "Contact attempt uncompleted",
        OrganizerOutcome::AidScheduled => "Support committed; awaiting material resolution",
        OrganizerOutcome::AidAwaitingSupport => "Support remains in transit",
        OrganizerOutcome::AidNotProvisioned => "Support did not provide current consumption",
        OrganizerOutcome::AidPracticeCompleted => {
            "Mutual-aid practice completed; delivery has separate evidence"
        }
        OrganizerOutcome::AidPracticeUncompleted => {
            "Mutual-aid practice uncompleted; this does not revoke a delivered gift"
        }
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
    let mut text = String::from("WORKPLACE EVIDENCE\nThese reports describe one observed period. References are personal presentation, not new knowledge or executable instructions. Provider-private accounts remain undisclosed. Workplace reports do not establish aid delivery, household consumption or independent participation.\n\n");
    let _ = writeln!(text, "{} recent and latest report(s) shown; {} acquired through committed period {}. Older reports remain in Cited workplace Archive.\n", view.observations.len(), view.total_observation_count, view.period);
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
        text.push_str("This reference is outside the current report window or unavailable in this inspected view. Open Cited workplace Archive to review earned older reports at the inspected period, or select another recent report. The reference remains in your draft and grants no additional access.");
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
        OrganizerInspector::Notes => ("Personal notes".into(), String::new()),
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
            let mut text = means(view);
            text.push_str("\n\nCURRENT DIRECTION AND DISAGREEMENTS\nThe commitments below describe the current organization; the usage receipt is filtered to the inspected period. You make the organization's final ruling. A recorded objection is neither a veto nor universal agreement. Participants' committed time limits what can be carried out.\n\n");
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
            let visible = view
                .receipts
                .iter()
                .filter(|receipt| receipt.period <= period && receipt.actor_id == view.actor_id)
                .count();
            let mut text = format!("RECENT COMMITTED PRACTICE HISTORY\nShowing {visible} recent receipt(s) of {} committed through period {}. Open Our practice Archive for older receipts at the inspected period.\nFactory output and maintenance recovery remain separate from organizational outcomes.\n\n", view.total_receipt_count, view.period);
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
                text.push_str(if view.total_receipt_count > 0 && period > 0 { "No receipt from this period is included in the recent window. Older receipts remain in Our practice Archive." } else { "No practice has completed at this period." });
            }
            text.push_str(&aid_history(client, period));
            text.push_str(&collection_history(client, view, period));
            ("Practice receipts and aftermath".into(), text)
        }
    }
}

fn currency(micros: i128) -> String {
    let amount = micros.unsigned_abs();
    let whole = amount / 1_000_000;
    let fraction = amount % 1_000_000;
    let sign = if micros < 0 { "-" } else { "" };
    if fraction == 0 {
        format!("{sign}{whole}")
    } else {
        let fraction = format!("{fraction:06}");
        format!("{sign}{whole}.{}", fraction.trim_end_matches('0'))
    }
}

fn collection_detail(client: &OrganizerClient, view: &OrganizerView) -> String {
    let Some(m) = client
        .collection_preview()
        .filter(|m| m.period == view.period && m.actor_id == view.actor_id)
    else {
        return "No authenticated current collection terms. Refresh before choosing collection."
            .into();
    };
    let Some(resolves) = view.period.checked_add(1) else {
        return "Collection period exceeds the campaign bound.".into();
    };
    let consent = match m.cash_consent {
        OrganizerGiftConsent::Accept => "accepted independently",
        OrganizerGiftConsent::Refuse => "refused independently",
    };
    let displacement = if view.standing.authorized {
        format!(
            "Replaces saved neighborhood work this period ({} organizer-hours if eligible).",
            view.contact_hours
        )
    } else {
        "Saved neighborhood work is paused; collection runs once.".into()
    };
    let source: String = m
        .source_hash
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect();
    format!("Contributor: {} (participant {}). Designed terms verified at period {}; source {}.\nVoluntary household gift: up to {} currency; {} shared material hours. Independent cash consent: {}. Protected cash floor: {} currency; mandatory protected needs and due payments are checked at close. Protected consumption, essential services and closing stocks come first. A positive amount below the cap is a partial gift and still uses the fixed hours. Organization cash now: {} currency.\nResolves period {}. {} No cash or time is reserved. Later aid needs its own ruling; no immediate membership, agreement or time gain.", m.contributor_label, m.contributor_id, m.period, source, currency(m.maximum_cash_micros), m.collection_hours, consent, currency(m.protected_cash_floor_micros), currency(m.organization_cash_micros), resolves, displacement)
}

fn collection_outcome(outcome: OrganizerCollectionOutcome) -> &'static str {
    match outcome {
        OrganizerCollectionOutcome::Collected => "Collected in full",
        OrganizerCollectionOutcome::PartiallyCollected => "Partially collected",
        OrganizerCollectionOutcome::CashConsentRefused => "Household cash consent was refused",
        OrganizerCollectionOutcome::ProtectedConsumptionUnmet => "Household consumption is unmet",
        OrganizerCollectionOutcome::ProtectedServiceUnmet => {
            "Essential household services are unmet"
        }
        OrganizerCollectionOutcome::ProtectedClosingStockUnmet => {
            "Protected closing pantry or stocks are unmet"
        }
        OrganizerCollectionOutcome::DuePaymentUnmet => "Outstanding protected payments remain due",
        OrganizerCollectionOutcome::InsufficientCash => {
            "No eligible cash remains above the protected floor"
        }
        OrganizerCollectionOutcome::InsufficientContributionTime => {
            "Insufficient actual authorized household time"
        }
    }
}

fn collection_result(row: &OrganizerCollectionResolution) -> String {
    format!("Requested {} currency; collected {} currency; {} shared material hours. Result: {}. Original ruling resolved; no standing fallback. A collected gift can fund later aid; no membership, agreement or time gain is credited.", currency(row.fact.requested_cash_micros), currency(row.fact.collected_cash_micros), row.fact.performed_hours, collection_outcome(row.fact.outcome))
}

fn collection_history(client: &OrganizerClient, view: &OrganizerView, period: u64) -> String {
    let mut text = String::new();
    for row in client.collection_resolutions.iter().filter(|r| {
        r.practice.actor_id == view.actor_id
            && r.fact.actor_id == view.actor_id
            && r.fact.period == r.practice.period
            && r.practice.period <= period
    }) {
        let _ = writeln!(
            text,
            "COLLECTION · original admission {}; actual resolution {}. {}",
            row.fact.admitted_period,
            row.fact.period,
            collection_result(row)
        );
    }
    text
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::runtime_session::{
        OrganizerAgreement, OrganizerAidKind, OrganizerAidOption, OrganizerCommand,
        OrganizerCommitment, OrganizerGiftConsent, OrganizerStandingWork,
    };

    #[test]
    fn bounded_history_inspector_reports_total_and_routes_older_periods_to_archive() {
        let mut view = view();
        view.period = 325;
        view.total_receipt_count = 325;
        view.total_observation_count = 200;
        let client = OrganizerClient {
            view: Some(view.clone()),
            inspector: OrganizerInspector::Receipts,
            ..OrganizerClient::default()
        };
        let (_, text) = inspector(&client, 1);
        assert!(text.contains("Showing 0 recent receipt(s) of 325 committed through period 325"));
        assert!(text.contains("Open Our practice Archive"));
        assert!(!text.contains("No practice has completed"));
        assert!(
            aftermath(&OrganizerClient::default(), &view, 1).contains("Open Our practice Archive")
        );
        assert!(situation(&view, 1).contains("Open Cited workplace Archive"));
    }

    #[test]
    fn receipts_inspector_shows_accepted_aid_before_scheduled_dispatch() {
        use babylon_persistence::runtime_session::{OrganizerAidKind, OrganizerAidPending};
        let client = OrganizerClient {
            view: Some(view()),
            inspector: OrganizerInspector::Receipts,
            pending_aid: vec![OrganizerAidPending {
                kind: OrganizerAidKind::Remote,
                original_commitment_id: [11; 32],
                material_commitment_id: [12; 32],
                mandate_id: [13; 32],
                admitted_period: 2,
                dispatch_period: 3,
                good_id: [14; 32],
                unit_id: [15; 32],
            }],
            ..OrganizerClient::default()
        };
        let (_, earlier) = inspector(&client, 1);
        assert!(!earlier.contains("Pending remote solidarity"));
        assert!(!earlier.contains("Scheduled dispatch"));
        let (_, admitted) = inspector(&client, 2);
        assert!(admitted.contains("Pending remote solidarity: original admission 2"));
        assert!(admitted.contains("Scheduled dispatch: period 3; no delivery is credited."));
        assert!(!admitted.contains("Surviving delivery awaits actual arrival"));
        let (_, dispatched) = inspector(&client, 3);
        assert!(dispatched.contains("Pending remote solidarity: original admission 2; dispatch 3"));
        assert!(dispatched.contains("Surviving delivery awaits actual arrival"));
        assert!(!dispatched.contains("Scheduled dispatch"));
        assert!(!dispatched.contains("Granted "));
        assert!(!dispatched.contains("Completed contact evidence"));
    }

    fn aid_history_client() -> OrganizerClient {
        use babylon_persistence::runtime_session::{
            OrganizerAidMaterialPostings, OrganizerAidPending, OrganizerAidResolution,
            OrganizerAidSupportStatus, OrganizerReceipt,
        };
        use babylon_practice_contract::{OrganizerAidSupport, OrganizerTimeUse};
        let mut view = view();
        view.period = 3;
        let row = OrganizerAidResolution {
            pending: OrganizerAidPending {
                kind: OrganizerAidKind::Local,
                original_commitment_id: [11; 32],
                material_commitment_id: [12; 32],
                mandate_id: [13; 32],
                admitted_period: 2,
                dispatch_period: 3,
                good_id: [14; 32],
                unit_id: [15; 32],
            },
            support: OrganizerAidSupport {
                original_commitment_id: [11; 32],
                material_commitment_id: [12; 32],
                mandate_id: [13; 32],
                source_hash: [16; 32],
                dispatch_period: 3,
                period: 3,
                recipient_principal_id: [17; 32],
                good_id: [14; 32],
                unit_id: [15; 32],
                status: OrganizerAidSupportStatus::Granted {
                    granted_quantity: 4,
                    consumed_quantity: 5,
                },
                material_postings: OrganizerAidMaterialPostings {
                    dispatched_quantity: 4,
                    fulfillment_hours: 8,
                    payer_cash_reserved_micros: 18,
                    payer_cash_granted_micros: 12,
                    payer_cash_refunded_micros: 6,
                },
            },
            practice: OrganizerReceipt {
                receipt_id: [18; 32],
                commitment_id: Some([11; 32]),
                actor_id: view.actor_id,
                period: 3,
                choice: OrganizerChoice::LocalAid,
                standing_work: false,
                outcome: OrganizerOutcome::AidPracticeUncompleted,
                hours_spent: 3,
                partner_actor_id: Some(94),
                partner_response: OrganizerPartnerResponse::Refused,
                observation_ids: vec![],
                contact_product_id: None,
                time_use: vec![OrganizerTimeUse {
                    contributor_id: 1,
                    actor_id: view.actor_id,
                    hours: 3,
                }],
            },
        };
        OrganizerClient {
            view: Some(view),
            inspector: OrganizerInspector::Receipts,
            aid_resolutions: vec![row],
            ..OrganizerClient::default()
        }
    }

    fn aid_arrival_client() -> OrganizerClient {
        use babylon_persistence::runtime_session::{
            OrganizerAidMaterialPostings, OrganizerAidSupportStatus,
        };
        use babylon_practice_contract::OrganizerTimeUse;
        let mut client = aid_history_client();
        let actor_id = client.view.as_ref().unwrap().actor_id;
        let row = &mut client.aid_resolutions[0];
        row.pending.kind = OrganizerAidKind::Remote;
        row.practice.choice = OrganizerChoice::RemoteAid;
        row.support.period = 5;
        row.practice.period = 5;
        row.practice.outcome = OrganizerOutcome::AidPracticeUncompleted;
        row.practice.hours_spent = 3;
        row.practice.time_use = vec![OrganizerTimeUse {
            contributor_id: 1,
            actor_id,
            hours: 3,
        }];
        row.practice.partner_actor_id = Some(95);
        row.practice.partner_response = OrganizerPartnerResponse::Refused;
        row.support.status = OrganizerAidSupportStatus::Granted {
            granted_quantity: 3,
            consumed_quantity: 6,
        };
        row.support.material_postings = OrganizerAidMaterialPostings {
            dispatched_quantity: 0,
            fulfillment_hours: 0,
            payer_cash_reserved_micros: 0,
            payer_cash_granted_micros: 9,
            payer_cash_refunded_micros: 3,
        };
        client.view.as_mut().unwrap().period = 5;
        client
    }

    #[test]
    fn local_aid_history_separates_postings_from_coordination_and_preserves_gift_privacy() {
        let client = aid_history_client();
        let (_, local) = inspector(&client, 3);
        assert!(
            local.contains("Local: original admission 2; dispatch 3; actual resolution 3."),
            "{local}"
        );
        assert!(
            local.contains(
                "Granted 4 units; total same-period recipient consumption of the same good/unit: 5"
            ),
            "{local}"
        );
        assert!(local.contains("Aggregate consumption is not attribution to donated units or proof of additional time"), "{local}");
        assert!(local.contains("Actual material postings in period 3: dispatched food 4 units; donor household fulfillment 8 hours."), "{local}");
        assert!(
            local.contains("Aid payer cash: reserved 18; gift paid 12; refunded 6 micro-units."),
            "{local}"
        );
        assert!(
            local.contains("These are distinct movements, not repeated expenses."),
            "{local}"
        );
        assert!(
            local.contains("partner declined; coordination 3 hours"),
            "{local}"
        );
        assert!(
            local.contains("A declined practice never revokes a delivered gift"),
            "{local}"
        );
        assert!(!local.contains("coordination 8 hours"), "{local}");
        assert!(!local.contains(&"11".repeat(32)), "{local}");
    }

    #[test]
    fn routed_aid_dispatch_history_reports_actual_cost_without_crediting_delivery_or_coordination()
    {
        use babylon_persistence::runtime_session::OrganizerAidSupportStatus;
        let mut client = aid_history_client();
        let row = &mut client.aid_resolutions[0];
        row.pending.kind = OrganizerAidKind::Remote;
        row.practice.choice = OrganizerChoice::RemoteAid;
        row.practice.outcome = OrganizerOutcome::AidAwaitingSupport;
        row.practice.hours_spent = 0;
        row.practice.time_use.clear();
        row.practice.partner_actor_id = None;
        row.practice.partner_response = OrganizerPartnerResponse::NotRequested;
        row.support.status = OrganizerAidSupportStatus::AwaitingDelivery;
        row.support.material_postings.payer_cash_granted_micros = 0;
        let (_, dispatched) = inspector(&client, 3);
        assert!(
            dispatched.contains("Surviving freight remains pending"),
            "{dispatched}"
        );
        assert!(
            dispatched.contains("donor household fulfillment 8 hours"),
            "{dispatched}"
        );
        assert!(
            dispatched
                .contains("Aid payer cash: reserved 18; gift paid 0; refunded 6 micro-units."),
            "{dispatched}"
        );
        assert!(dispatched.contains("coordination 0 hours"), "{dispatched}");
        assert!(!dispatched.contains("Granted "), "{dispatched}");
    }

    #[test]
    fn routed_aid_arrival_history_settles_cash_without_new_dispatch_fulfillment_or_reservation() {
        let client = aid_arrival_client();
        let (_, arrival) = inspector(&client, 5);
        assert!(
            arrival.contains("Remote: original admission 2; dispatch 3; actual resolution 5."),
            "{arrival}"
        );
        assert!(arrival.contains("Actual material postings in period 5: dispatched food 0 units; donor household fulfillment 0 hours."), "{arrival}");
        assert!(
            arrival.contains("Aid payer cash: reserved 0; gift paid 9; refunded 3 micro-units."),
            "{arrival}"
        );
        assert!(
            arrival.contains(
                "Granted 3 units; total same-period recipient consumption of the same good/unit: 6"
            ),
            "{arrival}"
        );
        assert!(
            arrival.contains("partner declined; coordination 3 hours"),
            "{arrival}"
        );
        assert!(
            !arrival.contains("donor household fulfillment 8 hours"),
            "{arrival}"
        );
        assert!(!arrival.contains("reserved 18"), "{arrival}");
        assert!(
            !arrival.contains("Actual material postings in period 3"),
            "{arrival}"
        );
    }

    #[test]
    fn aid_history_filters_current_snapshot_rows_without_reconstructing_older_postings() {
        let client = aid_history_client();
        let (_, before) = inspector(&client, 2);
        assert!(!before.contains("Granted 4 units"), "{before}");
        assert!(!before.contains("Actual material postings"), "{before}");

        // A later Ready snapshot carries only its actual current support row.
        // Historical inspection must not reconstruct its earlier dispatch costs.
        let client = aid_arrival_client();
        let (_, historical) = inspector(&client, 4);
        assert!(!historical.contains("actual resolution 5"), "{historical}");
        assert!(
            !historical.contains("Actual material postings"),
            "{historical}"
        );
        assert!(!historical.contains("gift paid 9"), "{historical}");
        assert!(
            !historical.contains("Actual material postings in period 3"),
            "{historical}"
        );
    }

    fn aid_preview() -> babylon_persistence::runtime_session::OrganizerMaterialAidPreview {
        use babylon_persistence::runtime_session::{
            OrganizerAidCapacity, OrganizerAidOrdinaryOffer, OrganizerAidRouteStage,
            OrganizerAidTransportPreview, OrganizerMaterialAidPreview,
        };
        OrganizerMaterialAidPreview {
            kind: babylon_persistence::runtime_session::OrganizerAidKind::Remote,
            mandate_id: [1; 32],
            period: 0,
            donor_id: [2; 32],
            recipient_id: [3; 32],
            good_id: [4; 32],
            unit_id: [5; 32],
            donor_stock: 12,
            own_need: 4,
            grams_per_unit: 1000,
            payer_cash: 120,
            ordinary_offer: Some(OrganizerAidOrdinaryOffer {
                seller_id: [6; 32],
                unit_price: 25,
            }),
            maximum_quantity: 8,
            gift_cash_per_unit: 10,
            labor_unit_id: [7; 32],
            fulfillment_hours_per_unit: 2,
            coordination_hours: 3,
            receiving_consent: babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
            time: None,
            transport: OrganizerAidTransportPreview::Routed {
                route_id: [8; 32],
                from_node_id: [9; 32],
                to_node_id: [10; 32],
                stages: vec![OrganizerAidRouteStage {
                    stage_index: 0,
                    from_node_id: [9; 32],
                    to_node_id: [10; 32],
                    travel_periods: 2,
                    loss_ppm: 15000,
                    departure_period: 1,
                    capacities: vec![OrganizerAidCapacity {
                        corridor_id: [11; 32],
                        remaining_grams: Some(4000),
                    }],
                }],
            },
        }
    }

    fn aid_options() -> Vec<OrganizerAidOption> {
        [
            (OrganizerAidKind::Local, 94, "Harbor pantry collective"),
            (OrganizerAidKind::Remote, 95, "Northern relief association"),
        ]
        .into_iter()
        .map(
            |(kind, partner_actor_id, partner_label)| OrganizerAidOption {
                kind,
                partner_actor_id,
                partner_label: partner_label.into(),
                coordination_hours: 3,
                receiving_consent: OrganizerGiftConsent::Accept,
            },
        )
        .collect()
    }

    #[test]
    fn aid_terms_distinguish_gift_sale_past_time_and_uncertain_shared_route() {
        let preview = aid_preview();
        let text = aid_terms(&preview);
        assert!(text.contains("protected surplus: 8"));
        assert!(text.contains("Gift transfer: 10"));
        assert!(text.contains("food price: 25"));
        assert!(text.contains("No closed household time receipt"));
        assert!(text.contains("Earliest possible arrival: period 3; not a delivery guarantee"));
        assert!(text.contains("4000 grams; commercial freight competes"));
        assert!(text.contains("no cash, food, freight or time is reserved"));
        assert!(text.contains("no agreement is guaranteed"));
    }

    #[test]
    fn aid_cards_show_selected_partner_dates_and_current_consent() {
        for (kind, selected, label, other_label) in [
            (
                OrganizerAidKind::Local,
                OrganizerChoice::LocalAid,
                "Harbor pantry collective",
                "Northern relief association",
            ),
            (
                OrganizerAidKind::Remote,
                OrganizerChoice::RemoteAid,
                "Northern relief association",
                "Harbor pantry collective",
            ),
        ] {
            let mut view = view();
            view.period = 0;
            view.aid_options = aid_options();
            let mut preview = aid_preview();
            preview.kind = kind;
            if kind == OrganizerAidKind::Local {
                preview.transport =
                    babylon_persistence::runtime_session::OrganizerAidTransportPreview::Local;
            }
            let client = OrganizerClient {
                view: Some(view.clone()),
                aid: vec![preview],
                ..OrganizerClient::default()
            };
            let text = client_approach(&client, &view, selected);
            assert!(text.contains(label), "{text}");
            assert!(!text.contains(other_label), "{text}");
            assert!(text.contains("Material preview: period 0"), "{text}");
            assert!(
                text.contains("Scheduled material resolution: period 1"),
                "{text}"
            );
            assert!(
                text.contains("Current recipient receiving consent: accepted"),
                "{text}"
            );
            assert!(
                text.contains("later practice needs a separate agreement"),
                "{text}"
            );
            assert!(
                text.contains("no cash, food, freight or time is reserved"),
                "{text}"
            );
        }
    }

    #[test]
    fn aid_card_refuses_unattributed_or_stale_terms_without_fabricating_identity_or_date() {
        let mut view = view();
        view.period = 0;
        view.aid_options = aid_options();
        let mut client = OrganizerClient {
            view: Some(view.clone()),
            aid: vec![aid_preview()],
            ..OrganizerClient::default()
        };
        let label = "Northern relief association";
        for options in [
            vec![],
            vec![view.aid_options[0].clone()],
            vec![view.aid_options[1].clone(), view.aid_options[1].clone()],
            vec![OrganizerAidOption {
                partner_label: " ".into(),
                ..view.aid_options[1].clone()
            }],
            vec![OrganizerAidOption {
                receiving_consent: OrganizerGiftConsent::Refuse,
                ..view.aid_options[1].clone()
            }],
        ] {
            let mut unattributed = view.clone();
            unattributed.aid_options = options;
            let text = client_approach(&client, &unattributed, OrganizerChoice::RemoteAid);
            assert!(text.contains("UNAVAILABLE"), "{text}");
            assert!(text.contains("Refresh before choosing aid"), "{text}");
            assert!(!text.contains(label), "{text}");
            assert!(!text.contains("Harbor pantry collective"), "{text}");
        }
        view.period = 1;
        client.view = Some(view.clone());
        let stale = client_approach(&client, &view, OrganizerChoice::RemoteAid);
        assert!(
            stale.contains("No authenticated current material terms"),
            "{stale}"
        );
        assert!(stale.contains("Refresh before choosing aid"), "{stale}");
        assert!(!stale.contains("Current pantry"), "{stale}");
        assert!(!stale.contains("protected surplus: 8"), "{stale}");
        assert!(!stale.contains(label), "{stale}");
        assert!(
            !stale.contains("Current recipient receiving consent: accepted"),
            "{stale}"
        );

        view.period = u64::MAX;
        client.view = Some(view.clone());
        client.aid[0].period = u64::MAX;
        let overflow = client_approach(&client, &view, OrganizerChoice::RemoteAid);
        assert!(
            overflow.contains(&format!("Material preview: period {}", u64::MAX)),
            "{overflow}"
        );
        assert!(
            overflow.contains("Scheduled material resolution unavailable"),
            "{overflow}"
        );
        assert!(
            !overflow.contains("Scheduled material resolution: period 0"),
            "{overflow}"
        );

        view.aid_options[1].receiving_consent = OrganizerGiftConsent::Refuse;
        client.aid[0].receiving_consent = OrganizerGiftConsent::Refuse;
        let refused = client_approach(&client, &view, OrganizerChoice::RemoteAid);
        assert!(refused.contains(label), "{refused}");
        assert!(
            refused.contains("Current recipient receiving consent: refused; gift unavailable"),
            "{refused}"
        );
        assert!(
            refused.contains("later practice needs a separate agreement"),
            "{refused}"
        );
    }

    #[test]
    fn accepted_aid_keeps_resolution_and_later_coordination_separate_from_committed_practice_hours()
    {
        for (selected, kind) in [
            (OrganizerChoice::LocalAid, OrganizerAidKind::Local),
            (OrganizerChoice::RemoteAid, OrganizerAidKind::Remote),
        ] {
            let mut view = view();
            view.available_hours = 1;
            view.aid_options = aid_options();
            let mut preview = aid_preview();
            preview.kind = kind;
            preview.period = view.period;
            let commitment = OrganizerCommitment {
                command: OrganizerCommand {
                    campaign_id: [3; 16],
                    actor_id: view.actor_id,
                    authority_id: view.authority_id,
                    expected_period: view.period,
                    content_digest: view.content_digest,
                    resource_digest: view.resource_digest,
                    nonce: [4; 16],
                    choice: selected,
                },
                resolves_period: 6,
                commitment_id: [5; 32],
            };
            let mut client = OrganizerClient {
                view: Some(view.clone()),
                aid: vec![preview],
                commitment: Some(commitment),
                ..OrganizerClient::default()
            };
            let text = review(&client, false, false, false);
            assert!(
                text.contains("ACCEPTED · material resolution period 6"),
                "{text}"
            );
            assert!(text.contains("later coordination: 3 hours"), "{text}");
            assert!(
                text.contains(
                    "delivery, consumption, finite contributions and independent authorization"
                ),
                "{text}"
            );
            assert!(text.contains("no coordination time is reserved"), "{text}");
            assert!(!text.contains("organizer-hours committed"), "{text}");
            client.aid.clear();
            let missing = review(&client, false, false, false);
            assert!(
                missing.contains("later coordination requirement unavailable"),
                "{missing}"
            );
            assert!(
                !missing.contains("later coordination: 0 hours"),
                "{missing}"
            );
            for (choice, hours) in [
                (OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost), 12),
                (OrganizerChoice::Reinforce, 8),
            ] {
                client.view.as_mut().unwrap().available_hours = 16;
                client.commitment.as_mut().unwrap().command.choice = choice;
                let practice = review(&client, false, false, false);
                assert!(
                    practice.contains(&format!("{hours} of 16 organizer-hours committed")),
                    "{practice}"
                );
                assert!(
                    practice.contains("ACCEPTED · resolves period 6"),
                    "{practice}"
                );
            }
        }
    }

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
            total_observation_count: 0,
            observations: vec![],
            total_receipt_count: 0,
            receipts: vec![],
            positions: vec![],
            aid_options: vec![],
        }
    }

    fn inquiry_client(period: u64) -> OrganizerClient {
        use babylon_persistence::runtime_session::OrganizerPreview;

        let mut view = view();
        view.period = period;
        view.standing.authorized = true;
        view.standing.paused_reason = None;
        OrganizerClient {
            view: Some(view),
            preview: Some(OrganizerPreview {
                choice: OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
                current_period: period,
                resolves_period: period + 1,
                available_hours: 16,
                required_hours: 12,
                replaces_standing_work: true,
                refusal: None,
                observations: vec![],
            }),
            ..OrganizerClient::default()
        }
    }

    #[test]
    fn opening_inquiry_discloses_missing_report_and_cost_before_confirmation() {
        let client = inquiry_client(0);
        let review = review(&client, false, false, false);
        assert!(
            review.contains("No completed-period report exists"),
            "{review}"
        );
        assert!(
            review.contains("still spends 12 organizer-hours"),
            "{review}"
        );
        assert!(review.contains("Resolves period 1"), "{review}");
        assert!(
            review.contains("Replaces neighborhood work once"),
            "{review}"
        );
        assert!(review.lines().count() <= 4, "{review}");
        let card = approach(
            client.view.as_ref().unwrap(),
            client.preview.unwrap().choice,
        );
        assert!(card.contains("No completed-period report"), "{card}");
    }

    #[test]
    fn inquiry_names_the_completed_report_period_separately_from_resolution() {
        let client = inquiry_client(5);
        let review = review(&client, false, false, false);
        assert!(review.contains("Report requested: period 5"), "{review}");
        assert!(review.contains("Resolves period 6"), "{review}");
        assert!(
            review.contains("Partner participation is independent"),
            "{review}"
        );
        let card = approach(
            client.view.as_ref().unwrap(),
            client.preview.unwrap().choice,
        );
        assert!(card.contains("Report requested: period 5"), "{card}");
        assert!(card.contains("Resolves period 6"), "{card}");
    }

    #[test]
    fn briefing_preserves_source_and_age_without_exposing_future_reports_or_ids() {
        let mut view = view();
        let mut report = OrganizerObservation {
            observation_id: [1; 32],
            actor_id: view.actor_id,
            subject_id: view.workplace_id,
            source_actor_id: view.workplace_partner_id,
            observed_period: 2,
            acquired_period: 3,
            receipt_id: Some([7; 32]),
            report: OrganizerReport::Work {
                performed_labor_hours: 160,
                output_kg: 320,
                previous_labor_hours: None,
                previous_output_kg: None,
            },
        };
        view.observations.push(report.clone());
        report.observed_period = 4;
        report.acquired_period = 5;
        report.report = OrganizerReport::Maintenance {
            enabled_batches: 999,
            consumed_batches: 888,
            expired_batches: 777,
        };
        view.observations.push(report);
        let text = situation(&view, 3);
        assert!(
            text.contains("Observed period 2 · historical report"),
            "{text}"
        );
        assert!(text.contains("Fixture workplace contacts"), "{text}");
        assert!(text.contains("inquiry · acquired period 3"), "{text}");
        assert!(text.contains("320 kg"), "{text}");
        assert!(!text.contains("999"), "{text}");
        assert!(!text.contains("source actor"), "{text}");
        assert!(!text.contains(&"07".repeat(32)), "{text}");
        assert!(situation(&view, 1).contains("No workplace report obtained"));
    }

    #[test]
    fn aftermath_keeps_participation_separate_from_evidence_and_filters_history() {
        use babylon_persistence::runtime_session::OrganizerReceipt;

        let mut view = view();
        let mut receipt = OrganizerReceipt {
            receipt_id: [1; 32],
            commitment_id: Some([2; 32]),
            actor_id: view.actor_id,
            period: 1,
            choice: OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
            standing_work: false,
            outcome: OrganizerOutcome::EvidenceWithheld,
            hours_spent: 12,
            partner_actor_id: Some(view.workplace_partner_id),
            partner_response: OrganizerPartnerResponse::Participated,
            observation_ids: vec![],
            contact_product_id: None,
            time_use: vec![],
        };
        view.receipts.push(receipt.clone());
        receipt.period = 2;
        receipt.hours_spent = 8;
        receipt.choice = OrganizerChoice::Hold;
        receipt.standing_work = true;
        receipt.commitment_id = None;
        receipt.outcome = OrganizerOutcome::ContactCompleted;
        receipt.contact_product_id = Some([3; 32]);
        receipt.partner_actor_id = Some(view.neighborhood_partner_id);
        view.receipts.push(receipt.clone());
        receipt.actor_id = 999;
        receipt.period = 3;
        receipt.hours_spent = 99;
        view.receipts.push(receipt);

        let first = aftermath(&OrganizerClient::default(), &view, 1);
        assert!(first.contains("Period 1 · accepted ruling"), "{first}");
        assert!(first.contains("12 organizer-hours spent"), "{first}");
        assert!(
            first.contains("Fixture workplace contacts: participated"),
            "{first}"
        );
        assert!(first.contains("No report obtained"), "{first}");
        assert!(!first.contains("withheld"), "{first}");
        assert!(!first.contains("Contact recorded"), "{first}");
        let second = aftermath(&OrganizerClient::default(), &view, 5);
        assert!(second.contains("Period 2 · saved routine"), "{second}");
        assert!(
            second.contains("Contact recorded; agreement can renew next period"),
            "{second}"
        );
        assert!(!second.contains("99 organizer-hours"), "{second}");
        assert!(aftermath(&OrganizerClient::default(), &view, 0).contains("No practice completed"));

        // An explicit Hold still performs standing work, but its origin is an accepted ruling.
        view.receipts[1].commitment_id = Some([4; 32]);
        assert!(aftermath(&OrganizerClient::default(), &view, 2).contains("accepted ruling"));
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
    #[test]
    fn collection_dated_actual_refusal_is_actor_scoped_and_historical() {
        use babylon_practice_contract::{
            OrganizerCollectionFact, OrganizerCollectionOutcome, OrganizerCollectionResolution,
        };
        let mut client = aid_history_client();
        let view = client.view.clone().unwrap();
        let mut practice = client.aid_resolutions[0].practice.clone();
        practice.choice = OrganizerChoice::Collect;
        practice.outcome = OrganizerOutcome::CollectionRefused;
        practice.standing_work = false;
        practice.hours_spent = 0;
        let command = OrganizerCommand {
            campaign_id: [3; 16],
            actor_id: view.actor_id,
            authority_id: view.authority_id,
            expected_period: 2,
            content_digest: view.content_digest,
            resource_digest: view.resource_digest,
            nonce: [4; 16],
            choice: OrganizerChoice::Collect,
        };
        let row = OrganizerCollectionResolution {
            commitment: OrganizerCommitment {
                command,
                resolves_period: 3,
                commitment_id: [11; 32],
            },
            fact: OrganizerCollectionFact {
                period: 3,
                admitted_period: 2,
                original_commitment_id: [11; 32],
                command_nonce: [4; 16],
                mandate_id: [13; 32],
                source_hash: [16; 32],
                actor_id: view.actor_id,
                contributor_id: 1,
                household_principal_id: [17; 32],
                organization_account_id: [18; 32],
                labor_unit_id: [19; 32],
                requested_cash_micros: 400_000,
                collected_cash_micros: 0,
                performed_hours: 0,
                outcome: OrganizerCollectionOutcome::ProtectedConsumptionUnmet,
                transfer_ordinal: None,
                contribution_use_id: [0; 32],
            },
            practice,
        };
        client.collection_resolutions = vec![row.clone()];
        client
            .view
            .as_mut()
            .unwrap()
            .receipts
            .push(row.practice.clone());
        assert!(aftermath(&client, client.view.as_ref().unwrap(), 3)
            .contains("Household consumption is unmet"));
        assert!(
            !aftermath(&client, client.view.as_ref().unwrap(), 2).contains("collected 0 currency")
        );
        // Captured from an actual shared-engine partial close; retain its exact
        // amount, actor, original command and shared material time evidence.
        let partial: OrganizerCollectionResolution = serde_json::from_str(include_str!(
            "../../tests/fixtures/organizer_partial_collection.json"
        ))
        .unwrap();
        let resolved_period = partial.fact.period;
        let mut partial_view = view.clone();
        partial_view.actor_id = partial.fact.actor_id;
        partial_view.period = resolved_period;
        partial_view.receipts = vec![partial.practice.clone()];
        let partially_collected = OrganizerClient {
            view: Some(partial_view.clone()),
            collection_resolutions: vec![partial],
            ..OrganizerClient::default()
        };
        let actual = aftermath(&partially_collected, &partial_view, resolved_period);
        assert!(actual.contains("collected 0.000004 currency; 2 shared material hours"));
        assert!(actual.contains("Partially collected"));
        assert!(
            collection_history(&partially_collected, &partial_view, resolved_period)
                .contains("Partially collected")
        );
        assert!(
            collection_history(&partially_collected, &partial_view, resolved_period - 1).is_empty()
        );
        let text = collection_history(&client, &view, 3);
        assert!(text.contains("original admission 2; actual resolution 3"));
        assert!(text.contains("collected 0 currency; 0 shared material hours"));
        assert!(text.contains("Household consumption is unmet"));
        assert!(text.contains("no standing fallback"));
        assert!(collection_history(&client, &view, 2).is_empty());
        client.collection_resolutions[0].practice.actor_id = view.actor_id + 1;
        assert!(collection_history(&client, &view, 3).is_empty());
        client.collection = Some(
            babylon_persistence::runtime_session::OrganizerCollectionPreview {
                period: view.period,
                mandate_id: [8; 32],
                actor_id: view.actor_id,
                contributor_id: 1,
                contributor_label: "Fixture contributor".into(),
                source_hash: [16; 32],
                cash_consent: OrganizerGiftConsent::Accept,
                maximum_cash_micros: 400_000,
                protected_cash_floor_micros: 0,
                collection_hours: 2,
                organization_cash_micros: 1_000_000,
            },
        );
        let card = client_approach(&client, &view, OrganizerChoice::Collect);
        assert!(card.contains("up to 0.4 currency; 2 shared material hours"));
        assert!(card.contains("terms verified at period 3"));
        assert!(card.contains("Designed"));
        assert!(card.contains("mandatory protected needs"));
        assert!(card.contains("No cash or time is reserved"));
        assert!(!card.contains("household cash now"));
    }
    #[test]
    fn collection_currency_preserves_exact_micro_units_without_float_rounding() {
        assert_eq!(currency(0), "0");
        assert_eq!(currency(400_000), "0.4");
        assert_eq!(currency(1), "0.000001");
        assert_eq!(
            currency(i128::MAX),
            "170141183460469231731687303715884.105727"
        );
        assert_eq!(
            currency(i128::MIN),
            "-170141183460469231731687303715884.105728"
        );
    }
}
