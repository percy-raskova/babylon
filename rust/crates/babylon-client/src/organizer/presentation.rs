//! Text projections over granted organizer records, never material ledger truth.
use babylon_persistence::runtime_session::OrganizerAidFoodPreview;

use babylon_persistence::runtime_session::OrganizerAllocation;
use babylon_persistence::runtime_session::{
    OrganizerAidFunding, OrganizerAidOption, OrganizerChoice, OrganizerCollectionOutcome,
    OrganizerCollectionResolution, OrganizerCommitment, OrganizerGiftConsent, OrganizerInquiry,
    OrganizerMaterialAidPreview, OrganizerObservation, OrganizerOutcome, OrganizerPartnerResponse,
    OrganizerPauseReason, OrganizerPreview, OrganizerRefusal, OrganizerReport, OrganizerView,
};
use std::fmt::Write as _;

use super::evidence::EvidenceMode;
use super::workspace::{DispatchPractice, PeriodDispatch};
use super::{OrganizerClient, OrganizerInspector};

const REINFORCE_PURPOSE: &str = "Purpose: Try to contact the workplace partner for future report sharing. This is not household aid.";
const REINFORCE_CONSEQUENCE: &str = "If contact is completed, it can renew a report-sharing agreement later; it does not itself provide a report.";

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

/// Intended work only; actual receipts use factual choice and outcome paths.
pub(super) fn flavor(view: &OrganizerView, choice: OrganizerChoice) -> &'static str {
    match choice {
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost) => {
            "Put the workplace's account of work and output on the table."
        }
        OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived) => {
            "Ask what kept the work going, and what went unrepaired."
        }
        OrganizerChoice::Reinforce => "Keep a line open to the people at work.",
        OrganizerChoice::Collect => "Pass the hat; household needs and consent come first.",
        OrganizerChoice::LocalAid => "Put food toward a nearby household's needs.",
        OrganizerChoice::RemoteAid => {
            "Send support across the distance; the route still has to carry it."
        }
        OrganizerChoice::Hold if view.standing.authorized => {
            "Keep showing up for the neighborhood contact work."
        }
        OrganizerChoice::Hold => "Leave the pause in place for another period.",
        OrganizerChoice::PauseStanding => "Call a pause in the neighborhood contact work.",
        OrganizerChoice::ResumeStanding => "Put the neighborhood contact work back on the agenda.",
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
        OrganizerRefusal::PendingAidConflict => "The earlier commitment to this partner is still open, including its freight. A new cash-only proposal also waits for closure.",
        OrganizerRefusal::HouseholdTimeAlreadySpent => {
            "Those household hours were already committed to a resolved period."
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
    } else if let Some(option) = view
        .aid_partners
        .iter()
        .find(|option| option.actor_id == actor)
    {
        &option.label
    } else {
        "An attributed participant"
    }
}

pub(super) fn report(value: &OrganizerReport) -> String {
    match value {
        OrganizerReport::Partner { facts, .. } => super::partner_copy::detail(facts),
        OrganizerReport::ReducedWork { previous_labor_hours, performed_labor_hours } => format!(
            "Less work was performed: {} labor-hours, compared with {} in the previous period.", crate::observer_ui::grouped(*performed_labor_hours), crate::observer_ui::grouped(*previous_labor_hours)
        ),
        OrganizerReport::Work { performed_labor_hours, output_kg, previous_labor_hours, previous_output_kg } => {
            let mut text = format!("Work performed: {} labor-hours. Output: {} kg.", crate::observer_ui::grouped(*performed_labor_hours), crate::observer_ui::grouped(*output_kg));
            if let Some(hours) = previous_labor_hours { let _ = write!(text, " Previous work: {} labor-hours.", crate::observer_ui::grouped(*hours)); }
            if let Some(output) = previous_output_kg { let _ = write!(text, " Previous output: {} kg.", crate::observer_ui::grouped(*output)); } else { text.push_str(" Earlier output was not reported."); }
            text
        },
        OrganizerReport::Maintenance { enabled_batches, consumed_batches, expired_batches } => format!(
            "Maintenance service received: {} enabled batches; {} used; {} expired. These are consumer records, not the provider's private accounts.", crate::observer_ui::grouped(*enabled_batches), crate::observer_ui::grouped(*consumed_batches), crate::observer_ui::grouped(*expired_batches)
        ),
    }
}

pub(super) fn report_kind(value: &OrganizerReport) -> &'static str {
    match value {
        OrganizerReport::Partner { facts, .. } => facts.title(),
        OrganizerReport::Work { .. } => "Work and output",
        OrganizerReport::ReducedWork { .. } => "Reduced work",
        OrganizerReport::Maintenance { .. } => "Maintenance received",
    }
}

pub(super) fn report_origin(item: &OrganizerObservation) -> &'static str {
    if matches!(item.report, OrganizerReport::Partner { .. }) {
        "Shared partner report · derived from captured material evidence"
    } else if item.receipt_id.is_some() {
        "Requested inquiry"
    } else if item.observed_period == 0 && item.acquired_period == 0 {
        "Captured initial report · period 0"
    } else {
        "Automatic report"
    }
}

pub(super) fn report_caption(item: &OrganizerObservation) -> String {
    format!(
        "{} · observed P{}, received P{} · {}",
        match &item.report {
            OrganizerReport::Partner { facts, .. } => super::partner_copy::headline(facts),
            other => report_kind(other).to_owned(),
        },
        item.observed_period,
        item.acquired_period,
        report_origin(item)
    )
}

pub(super) fn observation(
    view: &OrganizerView,
    item: &OrganizerObservation,
    current_period: u64,
) -> String {
    let mut text = format!(
        "{}\n\nSource: {}\nObserved period {} · Received period {}\n{}\nSubject: {}",
        report(&item.report),
        partner(view, item.source_actor_id),
        item.observed_period,
        item.acquired_period,
        report_origin(item),
        if matches!(item.report, OrganizerReport::Partner { .. }) {
            partner(view, item.subject_id)
        } else {
            &view.workplace_label
        },
    );
    if let OrganizerReport::Partner { facts, .. } = &item.report {
        let prior = super::partner_copy::prior(view, item, current_period, facts);
        if let Some((r, previous)) = prior {
            let _ = write!(
                text,
                "\nEarlier shared report P{}. {}",
                r.observed_period,
                super::partner_copy::detail(previous)
            );
        } else {
            text.push_str("\nEarlier comparable report unknown.");
        }
        text.push_str("\nShared topics cover the named requirements only. Other purchases and the uses of any particular gift remain unknown.");
    }
    if item.observed_period < current_period {
        text.push_str("\nHISTORICAL REPORT · These facts describe the earlier observed period.");
    }
    if item.receipt_id.is_some() {
        text.push_str("\nReceived through your inquiry. Acquiring this report did not cause its work or output.");
    }
    text
}

pub(super) fn situation(view: &OrganizerView, subject_id: u64, period: u64) -> String {
    let latest = view
        .observations
        .iter()
        .filter(|item| {
            item.actor_id == view.actor_id
                && item.subject_id == subject_id
                && view.knows_report_subject(item)
                && item.acquired_period <= period
                && item.observed_period <= period
        })
        .max_by_key(|item| (item.observed_period, item.acquired_period));
    latest.map_or_else(
        || {
            if subject_id != view.workplace_id {
                format!("{} · No report from this partner is available at period {period}.",partner(view,subject_id))
            } else if period == 0 {
                "No completed-period report exists yet. An inquiry now still costs time; it cannot obtain that report.".into()
            } else if period != view.period {
                "Open Cited workplace Archive to review earned reports at the inspected period.".into()
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
    format!("Contributor concerns (background): {concern}\nCurrent neighborhood routine: {routine}\nPartners choose whether to participate.")
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
    format!(
        "{}\n{}",
        flavor(view, choice),
        approach_terms(client, view, choice)
    )
}

fn approach_terms(
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
    if let Some(pending) = client
        .pending_aid
        .iter()
        .find(|pending| {
            pending.kind == preview.kind
                && pending.mandate_id == preview.mandate_id
                && pending.admitted_period <= view.period
        })
        .filter(|_| {
            view.period == preview.period
                && preview.receiving_consent == OrganizerGiftConsent::Accept
                && !view
                    .aid_options
                    .iter()
                    .any(|option| option.kind == preview.kind)
        })
    {
        let kind = match pending.kind {
            babylon_persistence::runtime_session::OrganizerAidKind::Local => "local aid",
            babylon_persistence::runtime_session::OrganizerAidKind::Remote => "remote solidarity",
        };
        let progress = if view.period < pending.dispatch_period {
            "Accepted support awaits its scheduled dispatch; no delivery is credited."
        } else if pending.kind == babylon_persistence::runtime_session::OrganizerAidKind::Remote {
            "Accepted support remains in transit; arrival is not yet credited."
        } else {
            "Accepted support remains pending. Read its actual result in Practice history."
        };
        let response=pending.response.as_ref().map_or_else(||"Later coordination still needs independent authorization.".to_owned(),|r|format!("Partner response in P{}: {}. Later food will not consume more coordination hours.",r.period,response(r.partner_response)));
        return format!("PENDING SUPPORT · {kind}\nOriginal admission: period {}; dispatch: period {}.\n{progress}\nOpen Practice history to follow this commitment's dispatch, arrival or terminal failure.\nAnother {kind} ruling remains unavailable while this support is pending. {response}", pending.admitted_period, pending.dispatch_period);
    }
    let recipient = aid_recipient(view, preview);
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
    let food_consent = match preview.receiving_consent {
        OrganizerGiftConsent::Accept => "accepted",
        OrganizerGiftConsent::Refuse => "refused",
    };
    let cash_consent = match preview.cash_receiving_consent {
        OrganizerGiftConsent::Accept => "accepted",
        OrganizerGiftConsent::Refuse => "refused",
    };
    if recipient.is_some() {
        let _ = writeln!(text, "Current recipient receiving consent: food {food_consent}; cash {cash_consent}; later practice needs a separate agreement.");
    } else {
        let _ = writeln!(text, "Current receiving consent is unverified; preview recorded food {food_consent}; cash {cash_consent}. Refresh before choosing aid.");
    }
    text.push_str(&aid_terms(preview));
    text.push_str(if view.standing.authorized {
        " Replaces neighborhood work once when admitted."
    } else {
        " The neighborhood routine remains paused."
    });
    text
}

fn aid_recipient<'a>(
    view: &'a OrganizerView,
    preview: &OrganizerMaterialAidPreview,
) -> Option<&'a OrganizerAidOption> {
    let mut options = view
        .aid_options
        .iter()
        .filter(|option| option.kind == preview.kind);
    options.next().filter(|option| {
        options.next().is_none()
            && view.period == preview.period
            && option.partner_actor_id == preview.recipient_actor_id
            && option.receiving_consent == preview.receiving_consent
            && !option.partner_label.trim().is_empty()
    })
}

pub(super) fn aid_terms_attributed(client: &OrganizerClient, choice: OrganizerChoice) -> bool {
    client
        .view
        .as_ref()
        .zip(client.aid_preview(choice))
        .is_some_and(|(view, terms)| aid_recipient(view, terms).is_some())
}

fn aid_review_terms(client: &OrganizerClient, choice: OrganizerChoice) -> String {
    let Some(view) = &client.view else {
        return "UNAVAILABLE · Current material terms are unavailable. Refresh before choosing aid.".into();
    };
    let Some(terms) = client.aid_preview(choice) else {
        return "UNAVAILABLE · Current material terms are unavailable. Refresh before choosing aid.".into();
    };
    let Some(recipient) = aid_recipient(view, terms) else {
        return "UNAVAILABLE · Recipient attribution unavailable. Refresh before choosing aid."
            .into();
    };
    let consent = match terms.receiving_consent {
        OrganizerGiftConsent::Accept => "accepted",
        OrganizerGiftConsent::Refuse => "refused for food",
    };
    let food = terms.food.as_ref().map_or_else(
        || "Food delivery is unavailable.".into(),
        |food| format!("Food mandate ceiling: up to {} food units ({} grams each); protected surplus: {} units. Actual fulfillment may be lower.\nFulfillment: {} household hours per dispatched unit.", crate::observer_ui::grouped(terms.maximum_quantity), crate::observer_ui::grouped(food.grams_per_unit), crate::observer_ui::grouped(food.donor_stock.saturating_sub(food.own_need)), crate::observer_ui::grouped(food.fulfillment_hours_per_unit)),
    );
    format!("Recipient: {}\n{food}\nIndependent cash cap: {} currency. {}.\nReceiving consent: {consent}.", recipient.partner_label, crate::human_numbers::currency(terms.maximum_cash_micros), aid_cash_text(terms.funding))
}

fn selected_aid(
    client: &OrganizerClient,
    allocation: OrganizerAllocation,
    choice: OrganizerChoice,
    resolves: u64,
) -> String {
    let OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = allocation
    else {
        return "Selected allocation unavailable.".into();
    };
    let terms = client.aid_preview(choice);
    let hours = terms
        .and_then(|t| t.food.as_ref())
        .and_then(|food| food.fulfillment_hours_per_unit.checked_mul(food_quantity));
    let next = resolves.checked_add(1).map_or_else(
        || "outside the campaign clock".to_owned(),
        |p| format!("P{p}"),
    );
    format!("Selected: {food_quantity} food parcels and {}. Up to {} donor household hours if all selected parcels dispatch. Cash receiving: {}. At P{resolves} cash can settle after ordinary orders. The next ordinary purchase opportunity is {next}; purchases and prices are uncertain. Food travels separately. First positive cash or actually consumed food permits one independent response.",crate::human_numbers::currency(cash_micros),hours.map_or_else(||"unknown".into(),|h|h.to_string()),terms.map_or("unknown",|t|match t.cash_receiving_consent{OrganizerGiftConsent::Accept=>"accepted",OrganizerGiftConsent::Refuse=>"refused"}))
}

fn aid_cash_text(funding: OrganizerAidFunding) -> String {
    match funding {
        OrganizerAidFunding::Unavailable => "Cash funding unavailable".into(),
        OrganizerAidFunding::Mandated => {
            "Cash gift authorized. The payer balance is private".into()
        }
        OrganizerAidFunding::Organization { cash_micros } => format!(
            "Organization cash: {} currency",
            crate::human_numbers::currency(cash_micros)
        ),
    }
}

fn collection_review_terms(client: &OrganizerClient) -> String {
    let Some(terms) = client.collection_preview() else {
        return "UNAVAILABLE · Current collection terms are unavailable. Refresh before choosing collection.".into();
    };
    let consent = match terms.cash_consent {
        OrganizerGiftConsent::Accept => "accepted independently",
        OrganizerGiftConsent::Refuse => "refused independently",
    };
    format!("Contributor: {}\nVoluntary gift: up to {} currency; {} shared material hours. Cash consent: {consent}.\nProtected cash floor: {} currency. Protected consumption, closing stocks and due payments come first. If a fully funded essential need remains unmet, the household keeps its refund. An unmet service without full funding blocks the gift. A partial gift still costs the fixed hours. Organization cash: {} currency. No cash or time is reserved.", terms.contributor_label, crate::human_numbers::currency(terms.maximum_cash_micros), crate::observer_ui::grouped(terms.collection_hours), crate::human_numbers::currency(terms.protected_cash_floor_micros), crate::human_numbers::currency(terms.organization_cash_micros))
}

fn aid_terms(preview: &OrganizerMaterialAidPreview) -> String {
    let mut text = format!(
        "{}. Independent cash cap: {} currency, separate from food.\n",
        aid_cash_text(preview.funding),
        crate::human_numbers::currency(preview.maximum_cash_micros)
    );
    if let Some(food) = &preview.food {
        let surplus = food.donor_stock.saturating_sub(food.own_need);
        let _ = writeln!(text, "Donor household pantry: {} units; own food need: {}; protected surplus: {}.\nCaptured food maximum: {} food units ({} grams per unit); actual fulfillment may be lower.\nFulfillment: {} household hours per dispatched unit; later coordination: {} hours. These compete with other work.", crate::observer_ui::grouped(food.donor_stock), crate::observer_ui::grouped(food.own_need), crate::observer_ui::grouped(surplus), crate::observer_ui::grouped(preview.maximum_quantity), crate::observer_ui::grouped(food.grams_per_unit), crate::observer_ui::grouped(food.fulfillment_hours_per_unit), crate::observer_ui::grouped(preview.coordination_hours));
        append_aid_constraints(&mut text, food);
    } else {
        text.push_str("Food delivery is unavailable.\n");
    }
    text.push_str("Preview only: no cash, food, freight or time is reserved. Later ordinary work has first call on time. Settled cash or bounded consumed-food credit may permit a separate independently authorized practice; no agreement is guaranteed.");
    text
}

fn append_aid_constraints(text: &mut String, food: &OrganizerAidFoodPreview) {
    use babylon_persistence::runtime_session::OrganizerAidTransportPreview;
    if let Some(offer) = &food.ordinary_offer {
        let _ = writeln!(text, "Ordinary quoted food price: {} currency per unit; this gift is not a purchase at that price.", crate::human_numbers::currency(offer.unit_price));
    } else {
        text.push_str("No ordinary food quote is available for comparison.\n");
    }
    match &food.time {
        Some(time) => {
            let _ = writeln!(text, "Last closed period {}: {} household hours remain. This is observed past supply, not next-period reserved time.", time.period, crate::observer_ui::grouped(time.remaining_hours));
        }
        None => text.push_str(
            "No closed household time receipt yet; available future hours are unknown.\n",
        ),
    }
    match &food.transport {
        OrganizerAidTransportPreview::Local => text.push_str("Local food can reach the pantry in its dispatch period; the donor's own food needs and available household hours still constrain fulfillment.\n"),
        OrganizerAidTransportPreview::Routed { stages, .. } => {
            let earliest = stages.last().and_then(|stage| stage.departure_period.checked_add(u64::from(stage.travel_periods)));
            if let Some(period) = earliest { let _ = writeln!(text, "Earliest possible arrival: period {period}; not a delivery guarantee."); }
            else { text.push_str("Earliest arrival is unavailable; no arrival guarantee.\n"); }
            for stage in stages {
                let _ = writeln!(text, "Route stage {}: {} periods; loss {} per million; departure preview period {}.", stage.stage_index, stage.travel_periods, stage.loss_ppm, stage.departure_period);
                for capacity in &stage.capacities {
                    match capacity.remaining_grams {
                        Some(grams) => { let _ = writeln!(text, "Shared corridor remaining capacity: {} grams; commercial freight competes for it.", crate::observer_ui::grouped(grams)); }
                        None => text.push_str("Shared corridor capacity at future departure is unknown.\n"),
                    }
                }
            }
        }
    }
}

fn aid_history(client: &OrganizerClient, period: u64) -> String {
    use babylon_persistence::runtime_session::OrganizerFoodDelivery;
    let mut text = String::from("\nAID SUPPORT · separate from workplace observations\n");
    for pending in &client.pending_aid {
        if client
            .view
            .as_ref()
            .is_some_and(|view| view.period == period)
            && pending.admitted_period <= period
        {
            let label = match pending.kind {
                babylon_persistence::runtime_session::OrganizerAidKind::Local => "local aid",
                babylon_persistence::runtime_session::OrganizerAidKind::Remote => {
                    "remote solidarity"
                }
            };
            if period < pending.dispatch_period {
                let _ = writeln!(text, "Pending {label}: original admission {}. Scheduled dispatch: period {}; no delivery is credited.", pending.admitted_period, pending.dispatch_period);
            } else {
                let coordination = pending.response.as_ref().map_or_else(
                    || "Independent response awaits qualifying support.".to_owned(),
                    |r| {
                        format!(
                            "Partner response in P{}: {}. No repeat on arrival.",
                            r.period,
                            response(r.partner_response)
                        )
                    },
                );
                let _=writeln!(text,"Pending {label}: original admission {}; dispatch {}. Surviving delivery awaits actual arrival. {coordination}",pending.admitted_period,pending.dispatch_period);
            }
        }
    }
    for row in client
        .aid_resolutions
        .iter()
        .filter(|row| row.practice.period <= period && row.support.period <= period)
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
            OrganizerFoodDelivery::NotRequested => text.push_str("No food selected.\n"),
            OrganizerFoodDelivery::AwaitingDelivery => {
                text.push_str("Surviving freight remains pending.\n");
            }
            OrganizerFoodDelivery::ReceivingRefused => {
                text.push_str("Food receiving was refused; cash settles independently.\n");
            }
            OrganizerFoodDelivery::TerminalFailure => {
                text.push_str("Terminal food failure; no food grant and no surviving delivery.\n");
            }
            OrganizerFoodDelivery::Granted { granted_quantity } => {
                let _ = writeln!(
                    text,
                    "Granted {} units.",
                    crate::observer_ui::grouped(granted_quantity)
                );
            }
        }
        let postings = &row.support.material_postings;
        let _ = writeln!(
            text,
            "Actual material postings in period {}: dispatched food {} units; donor household fulfillment {} hours.",
            row.support.period, crate::observer_ui::grouped(postings.dispatched_quantity), crate::observer_ui::grouped(postings.fulfillment_hours)
        );
        let _ = writeln!(
            text,
            "Freight loss in P{}: {} units.",
            row.support.period,
            crate::observer_ui::grouped(postings.lost_quantity)
        );
        let _ = writeln!(text, "{}", super::developments::dispatch_line(row));
        if let Some(first) = super::developments::response_line(row) {
            let _ = writeln!(text, "{first}");
        }
        if row.practice.outcome == OrganizerOutcome::AidResponseRetained {
            let _=writeln!(text,"P{} delivery update. The original response is final. Additional coordination: 0 hours.",row.support.period);
            continue;
        }
        let _ = writeln!(text, "Independent outcome: {}; partner {}; coordination {} hours. A declined practice never revokes a delivered gift.", outcome(row.practice.outcome), response(row.practice.partner_response), crate::observer_ui::grouped(row.practice.hours_spent));
    }
    text
}

pub(super) fn approach(view: &OrganizerView, choice: OrganizerChoice) -> String {
    let hours = crate::observer_ui::grouped(practice_hours(view, choice));
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
            format!("{hours} organizer-hours\nTarget: {} · Partner: {}\n{report}\n{displacement}\nResolves period {resolves} · partner decides", view.workplace_label, view.workplace_partner_label)
        }
        OrganizerChoice::Reinforce => {
            let disclosure = if view.public_workplace_contact { "\nA completed contact is publicly recorded at the workplace desk" } else { "" };
            format!("{hours} organizer-hours\nTarget: {} · Partner: {}\n{REINFORCE_PURPOSE}\n{REINFORCE_CONSEQUENCE}{disclosure}\n{displacement}\nResolves period {resolves} · partner decides", view.workplace_label, view.workplace_partner_label)
        },
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

pub(super) fn dispatch_practices(dispatch: &PeriodDispatch) -> String {
    if dispatch.current.practices.is_empty() {
        let period = dispatch.period;
        return if period == 0 {
            "Opening period · No practice completed at period 0.".into()
        } else {
            format!("No receipt from this period is included in the recent window. Open Our practice Archive to review period {period}.")
        };
    }
    dispatch
        .current
        .practices
        .iter()
        .map(practice_summary)
        .collect::<Vec<_>>()
        .join("\n\n")
}

fn practice_summary(row: &DispatchPractice) -> String {
    let receipt = row.receipt;
    let origin = if receipt.commitment_id.is_some() {
        "accepted ruling"
    } else {
        "saved routine"
    };
    if receipt.choice == OrganizerChoice::Collect {
        let actual = row.collection;
        return actual.map_or_else(
            || format!("Period {} · {origin}\nCollection ruling resolved. Open Our practice Archive for the actual cash and shared-time result.", receipt.period),
            |row| format!("Period {} · {origin}\n{}\n{}", receipt.period, choice(receipt.choice), collection_result(row)),
        );
    }
    let participant = row
        .partner
        .map_or("Partner participation", |partner| partner.label);
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

/// Show only venue-log records earned by the controlled organizer by this period.
pub(super) fn encounter_history(
    client: &OrganizerClient,
    view: &OrganizerView,
    period: u64,
) -> String {
    let mut text = String::new();
    let Some(dispatch) = super::workspace::dispatch_for_view(client, view, period) else {
        return text;
    };
    for encounter in dispatch
        .history
        .encounters
        .iter()
        .chain(&dispatch.current.encounters)
    {
        let row = encounter.encounter;
        let _ = write!(
            text,
            "\n\nCITY PD VISIT · PERIOD {}\nA public venue check-in records City PD visiting {}. It does not establish whether our organizers were present or what City PD learned. Other activity remains unknown.\nOpen Cited workplace Archive for the source.",
            row.resolve_period, view.workplace_label
        );
    }
    text
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
        view.period, view.organization_label, crate::observer_ui::grouped(view.available_hours), partner(view, view.standing.partner_actor_id), crate::observer_ui::grouped(view.contact_hours))
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
    let _ = write!(
        text,
        "\n{}",
        aid_review_terms(client, commitment.command.choice)
    );
    let _ = write!(
        text,
        "\n{}",
        selected_aid(
            client,
            commitment.command.allocation,
            commitment.command.choice,
            commitment.resolves_period
        )
    );
    if let Some(preview) = client.aid_preview(commitment.command.choice) {
        let _ = write!(
            text,
            "\nLater coordination: {} hours, if authorized.",
            crate::observer_ui::grouped(preview.coordination_hours)
        );
    }
    text.push_str("\nRuling fixed. Advance for material resolution. Coordination can follow positive cash or consumed food, subject to finite contributions and independent authorization; no coordination time is reserved.");
    text
}

fn accepted_collection_review(
    client: &OrganizerClient,
    commitment: &OrganizerCommitment,
) -> String {
    let terms = client.collection_preview().map_or_else(
        || "Captured original collection ruling".into(),
        |m| {
            format!(
                "{} · up to {} currency · {} shared material hours",
                m.contributor_label,
                crate::human_numbers::currency(m.maximum_cash_micros),
                crate::observer_ui::grouped(m.collection_hours)
            )
        },
    );
    let routine = client
        .view
        .as_ref()
        .map_or("Neighborhood routine status unavailable.", |view| {
            if view.standing.authorized {
                "Replaces neighborhood work once; no standing fallback."
            } else {
                "The neighborhood routine remains paused; no standing fallback."
            }
        });
    let selected = match commitment.command.allocation {
        OrganizerAllocation::Collection { target_cash_micros } => {
            crate::human_numbers::currency(target_cash_micros)
        }
        _ => "unavailable".into(),
    };
    format!("ACCEPTED · collection resolution period {}\nSelected contribution target {selected}.\n{terms}. Protected needs and fixed shared time are checked at close.\n{routine} Actual full, partial or refused payment appears after Advance. Later aid needs its own ruling.", commitment.resolves_period)
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
        return accepted_review(client, commitment);
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
    preview_review(client, preview)
}

fn preview_review(client: &OrganizerClient, preview: &OrganizerPreview) -> String {
    let mut text = format!("REVIEW · {}", choice(preview.choice));
    if let OrganizerAllocation::Collection { target_cash_micros } = preview.allocation {
        let _ = write!(
            text,
            "\nSelected contribution target: {} currency.",
            crate::human_numbers::currency(target_cash_micros)
        );
    }
    if let Some(view) = &client.view {
        let _ = write!(text, "\n{}", flavor(view, preview.choice));
    }
    if let (OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce, Some(view)) =
        (preview.choice, &client.view)
    {
        let _ = write!(
            text,
            "\nTarget: {} · Partner: {}",
            view.workplace_label, view.workplace_partner_label
        );
    }
    if preview.choice == OrganizerChoice::Reinforce {
        let _ = write!(text, "\n{REINFORCE_PURPOSE}");
    }
    match preview.choice {
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            let _ = write!(
                text,
                "\n{}\n{}",
                selected_aid(
                    client,
                    preview.allocation,
                    preview.choice,
                    preview.resolves_period
                ),
                aid_review_terms(client, preview.choice)
            );
        }
        OrganizerChoice::Collect => {
            let _ = write!(text, "\n{}", collection_review_terms(client));
            let _ = write!(
                text,
                "\nCost: {} of {} organizer-hours",
                crate::observer_ui::grouped(preview.required_hours),
                crate::observer_ui::grouped(preview.available_hours)
            );
        }
        _ => {
            let _ = write!(
                text,
                "\nCost: {} of {} organizer-hours",
                crate::observer_ui::grouped(preview.required_hours),
                crate::observer_ui::grouped(preview.available_hours)
            );
        }
    }
    let _ = write!(text, "\n{}", preview_routine(preview));
    if matches!(
        preview.choice,
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
    ) {
        if let Some(terms) = client.aid_preview(preview.choice) {
            let _ = write!(text, "\nLater coordination: {} hours, conditional on positive cash or consumed food, finite contributions and separate independent authorization.", crate::observer_ui::grouped(terms.coordination_hours));
            text.push('\n');
            if let Some(food) = &terms.food {
                append_aid_constraints(&mut text, food);
            }
        }
        text.push_str("\nPreview only: no cash, food, freight or time is reserved.");
    }
    if preview.choice == OrganizerChoice::Reinforce {
        let _ = write!(text, "\n{REINFORCE_CONSEQUENCE}");
        if client
            .view
            .as_ref()
            .is_some_and(|view| view.public_workplace_contact)
        {
            text.push_str("\nIf contact is completed, the workplace desk records it; Confirm alone creates no record.");
        }
    }
    append_preview_result(&mut text, client, preview);
    text
}

fn preview_routine(preview: &OrganizerPreview) -> &'static str {
    match preview.choice {
        OrganizerChoice::Collect | OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
            if matches!(
                preview.refusal,
                Some(OrganizerRefusal::WrongCampaign | OrganizerRefusal::WrongAuthority)
            ) =>
        {
            "Routine effect is unavailable for this preview."
        }
        OrganizerChoice::Collect
        | OrganizerChoice::LocalAid
        | OrganizerChoice::RemoteAid
        | OrganizerChoice::Inquiry(_)
        | OrganizerChoice::Reinforce
            if preview.replaces_standing_work =>
        {
            "Replaces neighborhood work once; later work remains subject to eligibility."
        }
        OrganizerChoice::Collect
        | OrganizerChoice::LocalAid
        | OrganizerChoice::RemoteAid
        | OrganizerChoice::Inquiry(_)
        | OrganizerChoice::Reinforce => "The neighborhood routine remains paused.",
        OrganizerChoice::PauseStanding => {
            "Pauses the saved routine until you explicitly resume it."
        }
        OrganizerChoice::ResumeStanding => {
            "Authorizes and performs the saved routine; continues afterward while eligible."
        }
        OrganizerChoice::Hold => "Keeps the saved routine; does not resume a paused routine.",
    }
}

fn append_preview_result(text: &mut String, client: &OrganizerClient, preview: &OrganizerPreview) {
    if let Some(reason) = preview.refusal {
        let _ = write!(text, "\nUNAVAILABLE · {}", refusal(reason));
    } else {
        if matches!(preview.choice, OrganizerChoice::Inquiry(_)) {
            if preview.current_period == 0 {
                let _ = write!(text, "\nNo completed-period report exists. An admitted inquiry still spends {} organizer-hours.", crate::observer_ui::grouped(preview.required_hours));
            } else {
                let _ = write!(
                    text,
                    "\nReport requested: period {}. No report is guaranteed.",
                    preview.current_period
                );
            }
        }
        if preview.choice == OrganizerChoice::Collect {
            text.push_str(
                "\nReview reserves nothing; the actual collection or refusal follows Advance.",
            );
        } else if preview.choice != OrganizerChoice::PauseStanding {
            text.push_str("\nPartner participation is independent.");
        }
    }
    let terms_unavailable = match preview.choice {
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            !aid_terms_attributed(client, preview.choice)
        }
        OrganizerChoice::Collect => client.collection_preview().is_none(),
        _ => false,
    };
    if preview.refusal.is_some() || terms_unavailable {
        let _ = write!(
            text,
            "\nProposed resolution: period {}. This choice cannot be confirmed as shown.",
            preview.resolves_period
        );
    } else {
        let resolution = if matches!(
            preview.choice,
            OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
        ) {
            "Scheduled material resolution"
        } else {
            "Resolves"
        };
        let _ = write!(
            text,
            "\n{resolution} period {} · Confirm sets the ruling; Advance shows the actual result.",
            preview.resolves_period
        );
    }
}

fn accepted_review(client: &OrganizerClient, commitment: &OrganizerCommitment) -> String {
    if matches!(
        commitment.command.choice,
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
    ) {
        return accepted_aid_review(client, commitment);
    }
    if commitment.command.choice == OrganizerChoice::Collect {
        return accepted_collection_review(client, commitment);
    }
    let mut text = format!(
        "ACCEPTED · resolves period {}\n{}",
        commitment.resolves_period,
        choice(commitment.command.choice)
    );
    if let Some(view) = &client.view {
        if matches!(
            commitment.command.choice,
            OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce
        ) {
            let _ = write!(
                text,
                "\nTarget: {} · Partner: {}",
                view.workplace_label, view.workplace_partner_label
            );
        }
        let hours = crate::observer_ui::grouped(practice_hours(view, commitment.command.choice));
        let _ = write!(
            text,
            " · {hours} of {} organizer-hours committed",
            crate::observer_ui::grouped(view.available_hours)
        );
    }
    if commitment.command.choice == OrganizerChoice::Reinforce {
        let _ = write!(text, "\n{REINFORCE_PURPOSE}\n{REINFORCE_CONSEQUENCE}");
    }
    text.push_str("\nRuling fixed. Advance to resolve; partners decide their participation.");
    text
}

pub(super) fn outcome(value: OrganizerOutcome) -> &'static str {
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
        OrganizerOutcome::NoQualifyingSupport => "Support did not qualify joint work",
        OrganizerOutcome::AidResponseRetained => "Earlier coordination response retained",
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

pub(super) fn response(value: OrganizerPartnerResponse) -> &'static str {
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
    let id = client.selected_evidence_id(period);
    let item = id.and_then(|id| client.lawful_evidence(id, period));
    let title = item.map_or_else(
        || "Acquired reports".into(),
        |item| {
            let ids = client.evidence_ids(period);
            let index = ids
                .iter()
                .position(|id| *id == item.observation_id)
                .map_or(1, |i| i + 1);
            let title = match &item.report {
                OrganizerReport::Partner { facts, .. } => super::partner_copy::headline(facts),
                other => report_kind(other).to_owned(),
            };
            format!("{title} · {} of {}", index, ids.len())
        },
    );
    let mut text = item.map_or_else(|| {
        if id.is_some() && saved {
            "This reference is unavailable in this inspected view. Open Report Archive to browse at this period, or select another saved reference. The draft keeps the reference.".into()
        } else if id.is_some() {
            "The selected report is unavailable in this inspected view. Select another report or open Archive from a known subject.".into()
        } else if saved {
            "No saved references. Open Evidence and keep a report in the draft.".into()
        } else if period != view.period {
            "Select a known subject to browse its Archive at this period.".into()
        } else {
            "No acquired report is available at this period.".into()
        }
    }, |item| observation(view, item, period));
    if item.is_some_and(|r| !matches!(r.report, OrganizerReport::Partner { .. }))
        || client.evidence.mode == EvidenceMode::Subject(view.workplace_id)
    {
        text.push_str("\n\nREPORT SCOPE\nWorkplace reports do not establish aid delivery, household consumption or independent participation. Provider-private accounts remain undisclosed.");
    }
    if let EvidenceMode::Subject(id) = client.evidence.mode {
        let subject = if id == view.workplace_id {
            &view.workplace_label
        } else {
            partner(view, id)
        };
        let _ = write!(
            text,
            "\n{subject} · {} retained report(s) available at period {period}.",
            client.evidence_ids(period).len()
        );
    } else if period == view.period {
        let _ = write!(text, "\n{} recent and latest report(s) shown; {} acquired through committed period {}. Earlier reports remain in the Archive for their subject.", view.observations.len(), view.total_observation_count, view.period);
    } else {
        text.push_str("\nThe as-of total is unavailable. Each known subject has its own Archive at the inspected period.");
    }
    if saved {
        text.push_str("\n\nCURRENT PERSONAL DRAFT · saved references are present-day notebook context, not a historical reconstruction.");
    }
    if let Some(id) = id {
        text.push_str(
            match (client.evidence_is_saved(id), period == view.period) {
                (true, true) => "\n\nIN PERSONAL DRAFT",
                (false, true) => "\n\nNOT IN PERSONAL DRAFT",
                (true, false) => "\n\nIN CURRENT PERSONAL DRAFT",
                (false, false) => "\n\nNOT IN CURRENT PERSONAL DRAFT",
            },
        );
    }
    text.push_str(
        "\n\nReferences are personal presentation, not new knowledge or executable instructions.",
    );
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
        OrganizerInspector::Practices => ("All practices".into(), String::new()),
        OrganizerInspector::Review => ("Review the ruling".into(), String::new()),
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
            let mut text = if period == view.period {
                format!("RECENT COMMITTED PRACTICE HISTORY\nShowing {visible} recent receipt(s) of {} committed through period {}. Open Our practice Archive for older receipts at the inspected period.\nFactory output and maintenance recovery remain separate from organizational outcomes.\n\n", view.total_receipt_count, view.period)
            } else {
                "RECENT COMMITTED PRACTICE HISTORY\nThe as-of total is unavailable. Open Our practice Archive for receipts at the inspected period.\nFactory output and maintenance recovery remain separate from organizational outcomes.\n\n".into()
            };
            let visible_receipts = view
                .receipts
                .iter()
                .filter(|receipt| receipt.period <= period && receipt.actor_id == view.actor_id)
                .rev();
            for receipt in visible_receipts {
                let _ = writeln!(text, "PERIOD {} · {}\n{} · {} organizer-hours spent\nPartner: {}\n{} evidence record(s). {}\n", receipt.period,
                    if receipt.standing_work { "Standing work" } else { choice(receipt.choice) }, outcome(receipt.outcome), receipt.hours_spent,
                    response(receipt.partner_response), receipt.observation_ids.len(),
                    if receipt.contact_product_id.is_some() { "Completed contact evidence can support a later report-exchange commitment." } else { "No new contact product was produced by this practice." });
            }
            if period == view.period
                && !view
                    .receipts
                    .iter()
                    .any(|receipt| receipt.period <= period && receipt.actor_id == view.actor_id)
            {
                text.push_str(if view.total_receipt_count > 0 && period > 0 { "No receipt for this period is included in the available window. Open Our practice Archive for the inspected period." } else { "No practice has completed at this period." });
            }
            text.push_str(&aid_history(client, period));
            text.push_str(&collection_history(client, view, period));
            text.push_str(&encounter_history(client, view, period));
            ("Practice receipts and aftermath".into(), text)
        }
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
    let mut source = String::with_capacity(64);
    for byte in m.source_hash {
        let _ = write!(source, "{byte:02x}");
    }
    format!("Contributor: {} (participant {}). Designed terms verified at period {}; source {}.\nVoluntary household gift: up to {} currency; {} shared material hours. Independent cash consent: {}. Protected cash floor: {} currency; mandatory protected needs and due payments are checked at close. Protected consumption and closing stocks come first. If a fully funded essential need remains unmet, the household keeps its refund. An unmet service without full funding blocks the gift. A positive amount below the cap is a partial gift and still uses the fixed hours. Organization cash now: {} currency.\nResolves period {}. {} No cash or time is reserved. Later aid needs its own ruling; no immediate membership, agreement or time gain.", m.contributor_label, m.contributor_id, m.period, source, crate::human_numbers::currency(m.maximum_cash_micros), crate::observer_ui::grouped(m.collection_hours), consent, crate::human_numbers::currency(m.protected_cash_floor_micros), crate::human_numbers::currency(m.organization_cash_micros), resolves, displacement)
}

fn collection_outcome(outcome: OrganizerCollectionOutcome) -> &'static str {
    match outcome {
        OrganizerCollectionOutcome::Collected => "Collected in full",
        OrganizerCollectionOutcome::PartiallyCollected => "Partially collected",
        OrganizerCollectionOutcome::CashConsentRefused => "Household cash consent was refused",
        OrganizerCollectionOutcome::ProtectedConsumptionUnmet => "Household consumption is unmet",
        OrganizerCollectionOutcome::ProtectedServiceUnmet => {
            "An unmet essential service lacked full funding"
        }
        OrganizerCollectionOutcome::ProtectedClosingStockUnmet => {
            "Protected closing pantry or stocks are unmet"
        }
        OrganizerCollectionOutcome::DuePaymentUnmet => "Outstanding protected payments remain due",
        OrganizerCollectionOutcome::InsufficientCash => {
            "No eligible cash remains after the protected floor and service refunds"
        }
        OrganizerCollectionOutcome::InsufficientContributionTime => {
            "Insufficient actual authorized household time"
        }
    }
}

pub(super) fn collection_result(row: &OrganizerCollectionResolution) -> String {
    format!("Requested {} currency; collected {} currency; {} shared material hours. Result: {}. Original ruling resolved; no standing fallback. A collected gift can fund later aid; no membership, agreement or time gain is credited.", crate::human_numbers::currency(row.fact.requested_cash_micros), crate::human_numbers::currency(row.fact.collected_cash_micros), crate::observer_ui::grouped(row.fact.performed_hours), collection_outcome(row.fact.outcome))
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

    fn aftermath(client: &OrganizerClient, view: &OrganizerView, period: u64) -> String {
        dispatch_practices(
            &super::super::workspace::dispatch_for_view(client, view, period)
                .expect("retained period"),
        )
    }

    use babylon_persistence::runtime_session::{
        OrganizerAgreement, OrganizerAidCashStatus, OrganizerAidKind, OrganizerAidOption,
        OrganizerCommand, OrganizerCommitment, OrganizerGiftConsent, OrganizerStandingWork,
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
        assert!(!text.contains("325"));
        assert!(text.contains("as-of total is unavailable"));
        assert!(text.contains("Open Our practice Archive"));
        assert!(!text.contains("No practice has completed"));
        assert!(
            aftermath(&OrganizerClient::default(), &view, 1).contains("Open Our practice Archive")
        );
        assert!(situation(&view, view.workplace_id, 1).contains("Open Cited workplace Archive"));

        let mut no_current_totals = view.clone();
        no_current_totals.total_receipt_count = 0;
        no_current_totals.total_observation_count = 0;
        assert_eq!(
            situation(&view, view.workplace_id, 1),
            situation(&no_current_totals, no_current_totals.workplace_id, 1)
        );
        assert_eq!(
            aftermath(&client, &view, 1),
            aftermath(&client, &no_current_totals, 1)
        );
        let without_totals = OrganizerClient {
            view: Some(no_current_totals),
            inspector: OrganizerInspector::Receipts,
            ..OrganizerClient::default()
        };
        assert_eq!(text, inspector(&without_totals, 1).1);
    }

    #[test]
    fn receipts_inspector_shows_accepted_aid_before_scheduled_dispatch() {
        use babylon_persistence::runtime_session::{OrganizerAidKind, OrganizerAidPending};
        let client = OrganizerClient {
            view: Some(view()),
            inspector: OrganizerInspector::Receipts,
            pending_aid: vec![OrganizerAidPending {
                allocation: babylon_persistence::runtime_session::OrganizerAllocation::Aid {
                    food_quantity: 4,
                    cash_micros: 18,
                },
                dispatch_support: crate::organizer::tests::aid_dispatch_fixture(),
                response: None,
                lost_quantity: 0,

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
        assert!(!admitted.contains("Pending remote solidarity"));
        assert!(!admitted.contains("Scheduled dispatch"));
        assert!(!admitted.contains("Surviving delivery awaits actual arrival"));
        let (_, dispatched) = inspector(&client, 3);
        assert!(!dispatched.contains("Pending remote solidarity"));
        assert!(!dispatched.contains("Surviving delivery awaits actual arrival"));
        let (_, live) = inspector(&client, 5);
        assert!(live.contains("Pending remote solidarity: original admission 2; dispatch 3"));
        assert!(!dispatched.contains("Scheduled dispatch"));
        assert!(!dispatched.contains("Granted "));
        assert!(!dispatched.contains("Completed contact evidence"));
    }

    fn aid_history_client() -> OrganizerClient {
        use babylon_persistence::runtime_session::OrganizerAidTransfer;
        use babylon_persistence::runtime_session::{
            OrganizerAidMaterialPostings, OrganizerAidPending, OrganizerAidResolution,
            OrganizerFoodDelivery, OrganizerReceipt,
        };
        use babylon_practice_contract::OrganizerTimeUse;
        let mut view = view();
        view.period = 3;
        let row = OrganizerAidResolution {
            pending: OrganizerAidPending {
                allocation: babylon_persistence::runtime_session::OrganizerAllocation::Aid {
                    food_quantity: 4,
                    cash_micros: 18,
                },
                dispatch_support: crate::organizer::tests::aid_dispatch_fixture(),
                response: None,
                lost_quantity: 0,

                kind: OrganizerAidKind::Local,
                original_commitment_id: [11; 32],
                material_commitment_id: [12; 32],
                mandate_id: [13; 32],
                admitted_period: 2,
                dispatch_period: 3,
                good_id: [14; 32],
                unit_id: [15; 32],
            },
            support: OrganizerAidTransfer {
                cash_status: OrganizerAidCashStatus::Granted,
                original_commitment_id: [11; 32],
                material_commitment_id: [12; 32],
                mandate_id: [13; 32],
                dispatch_period: 3,
                period: 3,
                good_id: [14; 32],
                unit_id: [15; 32],
                status: OrganizerFoodDelivery::Granted {
                    granted_quantity: 4,
                },
                material_postings: OrganizerAidMaterialPostings {
                    dispatched_quantity: 4,
                    fulfillment_hours: 8,
                    payer_cash_granted_micros: 12,
                    lost_quantity: 0,
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

    #[test]
    fn sender_history_keeps_cash_disposition_and_actual_freight_loss() {
        let mut client = aid_history_client();
        let row = &mut client.aid_resolutions[0];
        row.support.cash_status =
            babylon_persistence::runtime_session::OrganizerAidCashStatus::ReceivingRefused;
        row.support.material_postings.payer_cash_granted_micros = 0;
        row.support.material_postings.lost_quantity = 1;
        row.pending.dispatch_support = row.support.clone();
        let period = row.practice.period;
        let text = aid_history(&client, period);
        assert!(
            text.contains("Cash at dispatch P3: $0.00 (receiving refused)")
                && text.contains("Freight loss in P3: 1")
        );
        client.aid_resolutions[0].support.cash_status =
            babylon_persistence::runtime_session::OrganizerAidCashStatus::Unfunded;
        client.aid_resolutions[0].pending.dispatch_support =
            client.aid_resolutions[0].support.clone();
        assert!(aid_history(&client, period).contains("Cash at dispatch P3: $0.00 (unfunded)"));
    }

    fn aid_arrival_client() -> OrganizerClient {
        use babylon_persistence::runtime_session::{
            OrganizerAidMaterialPostings, OrganizerFoodDelivery,
        };
        use babylon_practice_contract::OrganizerTimeUse;
        let mut client = aid_history_client();
        let actor_id = client
            .view
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .actor_id;
        let row = &mut client.aid_resolutions[0];
        row.pending.kind = OrganizerAidKind::Remote;
        row.pending.allocation = babylon_persistence::runtime_session::OrganizerAllocation::Aid {
            food_quantity: 4,
            cash_micros: 0,
        };
        row.support.cash_status = OrganizerAidCashStatus::NotRequested;
        row.pending.dispatch_support.cash_status = OrganizerAidCashStatus::NotRequested;
        row.pending
            .dispatch_support
            .material_postings
            .payer_cash_granted_micros = 0;
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
        row.support.status = OrganizerFoodDelivery::Granted {
            granted_quantity: 3,
        };
        row.support.material_postings = OrganizerAidMaterialPostings {
            dispatched_quantity: 0,
            fulfillment_hours: 0,
            payer_cash_granted_micros: 0,
            lost_quantity: 0,
        };
        client
            .view
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .period = 5;
        client
    }

    #[test]
    fn repaired_later_freight_keeps_original_cash_and_first_response_dates() {
        let mut client = aid_arrival_client();
        let row = &mut client.aid_resolutions[0];
        row.pending.allocation = OrganizerAllocation::Aid {
            food_quantity: 4,
            cash_micros: 37_000_000,
        };
        row.pending.dispatch_support.cash_status = OrganizerAidCashStatus::Granted;
        row.pending
            .dispatch_support
            .material_postings
            .payer_cash_granted_micros = 37_000_000;
        let mut first = row.practice.clone();
        first.period = row.pending.dispatch_period;
        first.receipt_id = babylon_practice_contract::organizer_receipt_id(
            [34; 16],
            first.actor_id,
            first.period,
            row.pending.original_commitment_id,
        )
        .expect("unique dispatch response");
        row.pending.response = Some(first);
        row.support.cash_status = OrganizerAidCashStatus::Granted;
        row.support.material_postings.lost_quantity = 1;
        row.pending.lost_quantity = 1;
        row.practice.outcome = OrganizerOutcome::AidResponseRetained;
        row.practice.receipt_id = babylon_practice_contract::organizer_receipt_id(
            [34; 16],
            row.practice.actor_id,
            row.practice.period,
            row.pending.original_commitment_id,
        )
        .expect("unique delivery receipt");
        row.practice.partner_response = OrganizerPartnerResponse::NotRequested;
        row.practice.partner_actor_id = None;
        row.practice.hours_spent = 0;
        row.practice.time_use.clear();
        let (_, text) = inspector(&client, 5);
        assert!(text.contains("Cash at dispatch P3: $37.00"), "{text}");
        assert!(
            text.contains("Freight loss in P5: 1")
                && text.contains("P3 partner response:")
                && text.contains("Additional coordination: 0"),
            "{text}"
        );
        assert!(
            !text.contains("37000000 cash micros") && !text.contains("gift paid $0.00"),
            "{text}"
        );
        let now = super::super::developments::current_support(&client.aid_resolutions, 5);
        assert!(
            now.contains("lost in P5") && !now.contains("$37") && !now.contains("partner response"),
            "{now}"
        );
    }

    #[test]
    fn local_aid_history_separates_postings_from_coordination_and_preserves_gift_privacy() {
        let client = aid_history_client();
        let (_, local) = inspector(&client, 3);
        assert!(
            local.contains("Local: original admission 2; dispatch 3; actual resolution 3."),
            "{local}"
        );
        assert!(local.contains("Granted 4 units."), "{local}");
        assert!(
            !local.contains("recipient consumption") && !local.contains("consumption credit"),
            "{local}"
        );
        assert!(local.contains("Actual material postings in period 3: dispatched food 4 units; donor household fulfillment 8 hours."), "{local}");
        assert!(
            local.contains("Cash at dispatch P3: $0.000012 (granted)"),
            "{local}"
        );
        assert!(
            !local.contains("reserved") && !local.contains("refunded"),
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
        use babylon_persistence::runtime_session::OrganizerFoodDelivery;
        let mut client = aid_history_client();
        let row = &mut client.aid_resolutions[0];
        row.pending.kind = OrganizerAidKind::Remote;
        row.practice.choice = OrganizerChoice::RemoteAid;
        row.practice.outcome = OrganizerOutcome::AidAwaitingSupport;
        row.practice.hours_spent = 0;
        row.practice.time_use.clear();
        row.practice.partner_actor_id = None;
        row.practice.partner_response = OrganizerPartnerResponse::NotRequested;
        row.support.status = OrganizerFoodDelivery::AwaitingDelivery;
        row.support.material_postings.payer_cash_granted_micros = 0;
        row.support.cash_status = OrganizerAidCashStatus::Unfunded;
        row.pending.dispatch_support = row.support.clone();
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
            dispatched.contains("Cash at dispatch P3: $0.00 (unfunded)"),
            "{dispatched}"
        );
        assert!(dispatched.contains("coordination 0 hours"), "{dispatched}");
        assert!(!dispatched.contains("Granted "), "{dispatched}");
    }

    #[test]
    fn routed_food_only_arrival_history_has_no_cash_or_new_dispatch_fulfillment() {
        let client = aid_arrival_client();
        let (_, arrival) = inspector(&client, 5);
        assert!(
            arrival.contains("Remote: original admission 2; dispatch 3; actual resolution 5."),
            "{arrival}"
        );
        assert!(arrival.contains("Actual material postings in period 5: dispatched food 0 units; donor household fulfillment 0 hours."), "{arrival}");
        assert!(
            arrival.contains("Cash at dispatch P3: $0.00 (not requested)"),
            "{arrival}"
        );
        assert!(arrival.contains("Granted 3 units."), "{arrival}");
        assert!(
            arrival.contains("partner declined; coordination 3 hours"),
            "{arrival}"
        );
        assert!(
            !arrival.contains("donor household fulfillment 8 hours"),
            "{arrival}"
        );
        assert!(!arrival.contains("reserved $0.000018"), "{arrival}");
        assert!(
            !arrival.contains("Actual material postings in period 3"),
            "{arrival}"
        );
    }

    #[test]
    fn failed_food_keeps_independent_cash_grant_visible() {
        let mut client = aid_history_client();
        let row = client
            .aid_resolutions
            .first_mut()
            .expect("cash-grant copy fixture");
        row.support.status =
            babylon_persistence::runtime_session::OrganizerFoodDelivery::TerminalFailure;
        row.support.material_postings.dispatched_quantity = 0;
        row.support.material_postings.fulfillment_hours = 0;
        row.pending.dispatch_support = row.support.clone();
        row.pending.response = Some(row.practice.clone());
        let (_, text) = inspector(&client, 3);
        assert!(
            text.contains("Terminal food failure; no food grant"),
            "{text}"
        );
        assert!(
            text.contains("Cash at dispatch P3: $0.000012 (granted)"),
            "{text}"
        );
        assert!(!text.contains("no support was granted"));
    }

    #[test]
    fn uncredited_food_stays_visible_without_qualifying_joint_work() {
        let mut client = aid_history_client();
        let row = client.aid_resolutions.first_mut().expect("copy fixture");
        row.pending.allocation = babylon_practice_contract::OrganizerAllocation::Aid {
            food_quantity: 1,
            cash_micros: 0,
        };
        row.support.status = babylon_persistence::runtime_session::OrganizerFoodDelivery::Granted {
            granted_quantity: 1,
        };
        row.support.cash_status = OrganizerAidCashStatus::NotRequested;
        row.support.material_postings.dispatched_quantity = 1;
        row.support.material_postings.fulfillment_hours = 2;
        row.support.material_postings.payer_cash_granted_micros = 0;
        row.pending.dispatch_support = row.support.clone();
        row.practice.outcome = OrganizerOutcome::NoQualifyingSupport;
        row.practice.hours_spent = 0;
        row.practice.time_use.clear();
        row.practice.partner_actor_id = None;
        row.practice.partner_response = OrganizerPartnerResponse::NotRequested;
        let (_, text) = inspector(&client, 3);
        assert!(text.contains("Granted 1 units"), "{text}");
        assert!(!text.contains("consumption credit"), "{text}");
        assert!(
            text.contains("Support did not qualify joint work"),
            "{text}"
        );
        assert!(!text.contains("no grant"));
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
        assert!(!historical.contains("Cash at dispatch P3:"), "{historical}");
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
            initial_food_quantity: 1,
            initial_cash_micros: 0,
            cash_receiving_consent:
                babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
            kind: babylon_persistence::runtime_session::OrganizerAidKind::Remote,
            mandate_id: [1; 32],
            period: 0,
            donor_id: [2; 32],
            recipient_actor_id: 95,
            good_id: [4; 32],
            unit_id: [5; 32],
            food: Some(OrganizerAidFoodPreview {
                donor_stock: 12,
                own_need: 4,
                grams_per_unit: 1000,
                ordinary_offer: Some(OrganizerAidOrdinaryOffer {
                    seller_id: [6; 32],
                    unit_price: 25,
                }),
                labor_unit_id: [7; 32],
                fulfillment_hours_per_unit: 2,
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
            }),
            funding: OrganizerAidFunding::Organization { cash_micros: 120 },
            maximum_quantity: 8,
            maximum_cash_micros: 10,
            coordination_hours: 3,
            receiving_consent: babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
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
        assert!(text.contains("Independent cash cap: $0.00001 currency, separate from food"));
        assert!(text.contains("food price: $0.000025"));
        assert!(text.contains("No closed household time receipt"));
        assert!(text.contains("Earliest possible arrival: period 3; not a delivery guarantee"));
        assert!(text.contains("4,000 grams; commercial freight competes"));
        assert!(text.contains("no cash, food, freight or time is reserved"));
        assert!(text.contains("no agreement is guaranteed"));
    }

    #[test]
    fn aid_card_keeps_food_refusal_separate_from_available_cash_receiving() {
        let mut view = view();
        view.period = 0;
        view.aid_options = aid_options();
        view.aid_options[1].receiving_consent = OrganizerGiftConsent::Refuse;
        let mut terms = aid_preview();
        terms.receiving_consent = OrganizerGiftConsent::Refuse;
        let client = OrganizerClient {
            view: Some(view.clone()),
            aid: vec![terms],
            ..OrganizerClient::default()
        };

        assert!(
            client.choice_available(OrganizerChoice::RemoteAid),
            "accepted cash receiving keeps the mixed-consent choice available"
        );
        let text = client_approach(&client, &view, OrganizerChoice::RemoteAid);
        assert!(
            text.contains("Current recipient receiving consent: food refused; cash accepted"),
            "{text}"
        );
        assert!(!text.contains("gift unavailable"), "{text}");
        assert!(
            text.contains("later practice needs a separate agreement"),
            "{text}"
        );
    }

    #[test]
    fn local_food_only_review_keeps_pantry_and_hours_independent_of_cash_funding() {
        let mut view = view();
        view.period = 0;
        view.aid_options = aid_options();
        let mut terms = aid_preview();
        terms.kind = OrganizerAidKind::Local;
        terms.recipient_actor_id = 94;
        terms.funding = OrganizerAidFunding::Unavailable;
        terms
            .food
            .as_mut()
            .expect("the fixture carries food terms")
            .transport = babylon_persistence::runtime_session::OrganizerAidTransportPreview::Local;
        let client = OrganizerClient {
            view: Some(view.clone()),
            aid: vec![terms],
            preview: Some(OrganizerPreview {
                allocation: OrganizerAllocation::Aid {
                    food_quantity: 1,
                    cash_micros: 0,
                },
                choice: OrganizerChoice::LocalAid,
                current_period: 0,
                resolves_period: 1,
                available_hours: 16,
                required_hours: 0,
                replaces_standing_work: false,
                refusal: None,
                observations: vec![],
            }),
            ..OrganizerClient::default()
        };

        assert!(
            client.choice_available(OrganizerChoice::LocalAid),
            "food receiving permits the food-only choice without cash funding"
        );
        let detail = client_approach(&client, &view, OrganizerChoice::LocalAid);
        let review = review(&client, false, false, false);
        assert!(
            review.contains("Selected: 1 food parcels and $0"),
            "{review}"
        );
        for text in [&detail, &review] {
            assert!(text.contains("protected surplus: 8"), "{text}");
            assert!(
                text.contains("Fulfillment: 2 household hours per dispatched unit"),
                "{text}"
            );
            assert!(text.contains("Cash funding unavailable"), "{text}");
            assert!(
                text.contains("Local food can reach the pantry in its dispatch period; the donor's own food needs and available household hours still constrain fulfillment"),
                "{text}"
            );
            assert!(!text.contains("own needs, cash and time"), "{text}");
        }
        assert!(
            review.contains("Partner participation is independent"),
            "{review}"
        );
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
            preview.recipient_actor_id = if kind == OrganizerAidKind::Local {
                94
            } else {
                95
            };
            if kind == OrganizerAidKind::Local {
                preview.food.as_mut().expect("food offer").transport =
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
                text.contains("Current recipient receiving consent: food accepted; cash accepted"),
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
                partner_actor_id: 1,
                ..view.aid_options[1].clone()
            }],
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
            !stale.contains("Current recipient receiving consent: food accepted; cash accepted"),
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
            refused.contains("Current recipient receiving consent: food refused; cash accepted"),
            "{refused}"
        );
        assert!(
            refused.contains("later practice needs a separate agreement"),
            "{refused}"
        );
    }

    fn pending_remote_card_client(period: u64) -> OrganizerClient {
        use babylon_persistence::runtime_session::OrganizerAidPending;
        let mut view = view();
        view.period = period;
        view.aid_options = aid_options()
            .into_iter()
            .filter(|option| option.kind == OrganizerAidKind::Local)
            .collect();
        let mut remote = aid_preview();
        remote.period = period;
        let pending = OrganizerAidPending {
            allocation: babylon_persistence::runtime_session::OrganizerAllocation::Aid {
                food_quantity: 4,
                cash_micros: 18,
            },
            dispatch_support: crate::organizer::tests::aid_dispatch_fixture(),
            response: None,
            lost_quantity: 0,

            kind: remote.kind,
            original_commitment_id: [11; 32],
            material_commitment_id: [12; 32],
            mandate_id: remote.mandate_id,
            admitted_period: 0,
            dispatch_period: 1,
            good_id: remote.good_id,
            unit_id: remote.unit_id,
        };
        let mut local = remote.clone();
        local.kind = OrganizerAidKind::Local;
        local.recipient_actor_id = 94;
        local.food.as_mut().expect("food offer").transport =
            babylon_persistence::runtime_session::OrganizerAidTransportPreview::Local;
        OrganizerClient {
            view: Some(view),
            aid: vec![remote, local],
            pending_aid: vec![pending],
            ..OrganizerClient::default()
        }
    }

    #[test]
    fn pending_support_card_uses_original_dates_and_keeps_new_admission_disabled() {
        for period in [0, 1, 4] {
            let client = pending_remote_card_client(period);
            let text = client_approach(
                &client,
                client
                    .view
                    .as_ref()
                    .expect("the fixture set the optional field before this read"),
                OrganizerChoice::RemoteAid,
            );
            assert!(
                text.contains("Original admission: period 0; dispatch: period 1"),
                "{text}"
            );
            assert!(text.contains("Practice history"), "{text}");
            assert!(
                text.contains("Another remote solidarity ruling remains unavailable"),
                "{text}"
            );
            if period == 0 {
                assert!(text.contains("awaits its scheduled dispatch"), "{text}");
                assert!(!text.contains("in transit"), "{text}");
            } else {
                assert!(
                    text.contains("remains in transit; arrival is not yet credited"),
                    "{text}"
                );
            }
            assert!(!text.contains("Refresh"), "{text}");
            assert!(!text.contains("consent is unverified"), "{text}");
            assert!(!text.contains("Scheduled material resolution"), "{text}");
            assert!(!client.choice_available(OrganizerChoice::RemoteAid));
            assert!(client.choice_available(OrganizerChoice::LocalAid));
            assert!(client.choice_available(OrganizerChoice::Hold));
        }
    }

    #[test]
    fn pending_support_card_preserves_missing_evidence_and_consent_refusal() {
        let mut missing = pending_remote_card_client(1);
        missing.aid.clear();
        let text = client_approach(
            &missing,
            missing
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read"),
            OrganizerChoice::RemoteAid,
        );
        assert!(
            text.contains("No authenticated current material terms"),
            "{text}"
        );
        assert!(!text.contains("remains in transit"), "{text}");

        let mut unrelated = pending_remote_card_client(1);
        unrelated.pending_aid[0].mandate_id = [99; 32];
        let text = client_approach(
            &unrelated,
            unrelated
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read"),
            OrganizerChoice::RemoteAid,
        );
        assert!(text.contains("Recipient attribution unavailable"), "{text}");
        assert!(!text.contains("remains in transit"), "{text}");

        let mut refused = pending_remote_card_client(1);
        refused.aid[0].receiving_consent = OrganizerGiftConsent::Refuse;
        let mut option = aid_options().remove(1);
        option.receiving_consent = OrganizerGiftConsent::Refuse;
        refused
            .view
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .aid_options
            .push(option);
        let text = client_approach(
            &refused,
            refused
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read"),
            OrganizerChoice::RemoteAid,
        );
        assert!(
            text.contains("Current recipient receiving consent: food refused; cash accepted"),
            "{text}"
        );
        assert!(!text.contains("remains in transit"), "{text}");
        assert!(!refused.choice_available(OrganizerChoice::RemoteAid));
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
            preview.recipient_actor_id = if kind == OrganizerAidKind::Local {
                94
            } else {
                95
            };
            preview.period = view.period;
            let commitment = OrganizerCommitment {
                command: OrganizerCommand {
                    allocation: OrganizerAllocation::None,
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
            assert!(text.contains("Later coordination: 3 hours"), "{text}");
            assert!(
                text.contains(
                    "positive cash or consumed food, subject to finite contributions and independent authorization"
                ),
                "{text}"
            );
            assert!(text.contains("no coordination time is reserved"), "{text}");
            assert!(!text.contains("organizer-hours committed"), "{text}");
            client.aid.clear();
            let missing = review(&client, false, false, false);
            assert!(
                missing.contains("Current material terms are unavailable"),
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
                client
                    .view
                    .as_mut()
                    .expect("the fixture set the optional field before this borrow")
                    .available_hours = 16;
                client
                    .commitment
                    .as_mut()
                    .expect("the fixture set the optional field before this borrow")
                    .command
                    .choice = choice;
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

    #[test]
    fn workplace_publication_is_disclosed_only_for_the_captured_route() {
        let mut view = view();
        assert!(!approach(&view, OrganizerChoice::Reinforce).contains("publicly recorded"));
        view.public_workplace_contact = true;
        assert!(approach(&view, OrganizerChoice::Reinforce).contains("publicly recorded"));
        assert!(!approach(&view, OrganizerChoice::Hold).contains("publicly recorded"));
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
            public_workplace_contact: false,
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
            aid_partners: vec![],
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
                allocation: OrganizerAllocation::None,
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
        let card = approach(
            client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read"),
            client
                .preview
                .expect("the fixture client carries its preview")
                .choice,
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
            client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read"),
            client
                .preview
                .expect("the fixture client carries its preview")
                .choice,
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
        let text = situation(&view, view.workplace_id, 3);
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
        assert!(situation(&view, view.workplace_id, 1).contains("Open Cited workplace Archive"));
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
        let second = aftermath(&OrganizerClient::default(), &view, 2);
        assert!(second.contains("Period 2 · saved routine"), "{second}");
        assert!(
            second.contains("Contact recorded; agreement can renew next period"),
            "{second}"
        );
        assert!(!second.contains("99 organizer-hours"), "{second}");
        let missing_current = aftermath(&OrganizerClient::default(), &view, 5);
        assert!(
            missing_current.contains("Archive"),
            "missing current receipts must route to Archive: {missing_current}"
        );
        assert!(
            !missing_current.contains("Contact recorded"),
            "a previous period's contact is not the current result: {missing_current}"
        );
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
        let agreement = &mut client
            .view
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .agreements[0];
        agreement.valid_from_period = 4;
        agreement.valid_through_period = 6;
        agreement.source_product_id = Some([7; 32]);
        let (_, renewed) = inspector(&client, 2);
        assert!(renewed.contains("IN SCOPE AT CURRENT PERIOD"));
        assert!(renewed.contains("periods 4–6"));
        assert!(renewed.contains("current committed period"));
        assert!(means(
            client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read")
        )
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
        assert!(automatic.contains("Automatic report"));
        assert!(automatic.contains("Source: Fixture workplace contacts"));
        assert!(!automatic.contains("source actor 92"));
        assert!(!automatic.contains("Captured initial report"));
        item.observed_period = 0;
        item.acquired_period = 0;
        assert!(observation(&view, &item, 5).contains("Captured initial report · period 0"));
        item.receipt_id = Some([7; 32]);
        assert!(observation(&view, &item, 5).contains("Received through your inquiry"));
        assert!(!observation(&view, &item, 5).contains(&"07".repeat(32)));
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
                    allocation: OrganizerAllocation::None,
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
            assert!(text.contains(&format!("Cost: {hours} of 16 organizer-hours")));
            assert!(text.contains("Resolves period 6"));
            assert!(!text.contains("preserves the explicit standing-work authorization"));
        }
    }
    #[test]
    #[allow(
        clippy::too_many_lines,
        reason = "`collection_dated_actual_refusal_is_actor_scoped_and_historical` keeps one authored boundary's fixture and assertions together"
    )]
    fn collection_dated_actual_refusal_is_actor_scoped_and_historical() {
        use babylon_practice_contract::{
            OrganizerCollectionFact, OrganizerCollectionOutcome, OrganizerCollectionResolution,
        };
        let mut client = aid_history_client();
        let view = client.view.clone().expect("the fixture value clones");
        let mut practice = client.aid_resolutions[0].practice.clone();
        practice.choice = OrganizerChoice::Collect;
        practice.outcome = OrganizerOutcome::CollectionRefused;
        practice.standing_work = false;
        practice.hours_spent = 0;
        let command = OrganizerCommand {
            allocation: OrganizerAllocation::Collection {
                target_cash_micros: 400_000,
            },
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
            .expect("the fixture set the optional field before this borrow")
            .receipts
            .push(row.practice.clone());
        assert!(aftermath(
            &client,
            client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read"),
            3
        )
        .contains("Household consumption is unmet"));
        assert!(!aftermath(
            &client,
            client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read"),
            2
        )
        .contains("collected $0.00 currency"));
        let text = collection_history(&client, &view, 3);
        assert!(text.contains("original admission 2; actual resolution 3"));
        assert!(text.contains("collected $0.00 currency; 0 shared material hours"));
        assert!(text.contains("Household consumption is unmet"));
        assert!(text.contains("no standing fallback"));
        assert_eq!(collection_history(&client, &view, 2).len(), 0);
        client.collection_resolutions[0].practice.actor_id = view.actor_id + 1;
        assert_eq!(collection_history(&client, &view, 3).len(), 0);
        client.collection = Some(
            babylon_persistence::runtime_session::OrganizerCollectionPreview {
                period: view.period,
                mandate_id: [8; 32],
                actor_id: view.actor_id,
                contributor_id: 1,
                contributor_label: "Fixture contributor".into(),
                source_hash: [16; 32],
                cash_consent: OrganizerGiftConsent::Accept,
                initial_cash_micros: 400_000,
                maximum_cash_micros: 400_000,
                protected_cash_floor_micros: 0,
                collection_hours: 2,
                organization_cash_micros: 1_000_000,
            },
        );
        let card = client_approach(&client, &view, OrganizerChoice::Collect);
        assert!(card.contains("up to $0.40 currency; 2 shared material hours"));
        assert!(card.contains("terms verified at period 3"));
        assert!(card.contains("Designed"));
        assert!(card.contains("mandatory protected needs"));
        assert!(card.contains("No cash or time is reserved"));
        assert!(!card.contains("household cash now"));
    }
    #[test]
    fn actual_partial_collection_appears_in_aftermath_and_actor_scoped_history() {
        // Captured from an actual shared-engine partial close; retain its exact
        // amount, actor, original command and shared material time evidence.
        let partial: OrganizerCollectionResolution = serde_json::from_str(include_str!(
            "../../tests/fixtures/organizer_partial_collection.json"
        ))
        .expect("the authored JSON matches the declared schema");
        let resolved_period = partial.fact.period;
        let mut partial_view = aid_history_client()
            .view
            .expect("the fixture client carries its view");
        partial_view.actor_id = partial.fact.actor_id;
        partial_view.period = resolved_period;
        partial_view.receipts = vec![partial.practice.clone()];
        let partially_collected = OrganizerClient {
            view: Some(partial_view.clone()),
            collection_resolutions: vec![partial],
            ..OrganizerClient::default()
        };
        let actual = aftermath(&partially_collected, &partial_view, resolved_period);
        assert!(actual.contains("collected $0.000004 currency; 2 shared material hours"));
        assert!(actual.contains("Partially collected"));
        assert!(
            collection_history(&partially_collected, &partial_view, resolved_period)
                .contains("Partially collected")
        );
        assert_eq!(
            collection_history(&partially_collected, &partial_view, resolved_period - 1).len(),
            0
        );
    }

    #[test]
    fn large_reports_preserve_grouped_labor_and_output_units() {
        let text = report(&OrganizerReport::Work {
            performed_labor_hours: 1_234_567,
            output_kg: 9_876_543,
            previous_labor_hours: Some(1_000_000),
            previous_output_kg: Some(9_000_000),
        });
        for quantity in [
            "1,234,567 labor-hours",
            "9,876,543 kg",
            "1,000,000 labor-hours",
            "9,000,000 kg",
        ] {
            assert!(
                text.contains(quantity),
                "report retains exact grouped quantity {quantity}: {text}"
            );
        }
    }

    #[test]
    fn collection_currency_preserves_exact_micro_units_without_float_rounding() {
        assert_eq!(crate::human_numbers::currency(0), "$0.00");
        assert_eq!(crate::human_numbers::currency(1_234_560_000), "$1,234.56");
        assert_eq!(crate::human_numbers::currency(-1_200_000), "-$1.20");
        assert_eq!(crate::human_numbers::currency(400_000), "$0.40");
        assert_eq!(crate::human_numbers::currency(1), "$0.000001");
        assert_eq!(
            crate::human_numbers::currency(i128::MAX),
            "$170,141,183,460,469,231,731,687,303,715,884.105727"
        );
        assert_eq!(
            crate::human_numbers::currency(i128::MIN),
            "-$170,141,183,460,469,231,731,687,303,715,884.105728"
        );
    }
}
