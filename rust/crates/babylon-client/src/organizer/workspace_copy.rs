//! Short card copy and dated navigation derived from the admitted view.
use babylon_persistence::runtime_session::{OrganizerReport, OrganizerView};
use std::fmt::Write as _;

use super::presentation;
use super::scene::OrganizerSubject;
use super::ui::Scope;
use super::workspace;
use super::{OrganizerClient, OrganizerInspector};
use crate::observer::{ObservationContext, ObserverSession, Perspective};
use crate::organizer::workspace::{
    ChoiceAvailability, ChoiceComparison, DispatchCoverage, DispatchDestination, DispatchRows,
    HourUse, PossibleBenefit, PracticeChoice, RoutineEffect,
};
use babylon_kernel::clock::CampaignDuration;
use babylon_persistence::identity::CampaignId;

/// One current resource reading shared by Organizer, World and Evidence headers.
pub(crate) fn resource_masthead(client: &OrganizerClient, session: &ObserverSession) -> String {
    let Some(means) = workspace::resources(client, session) else {
        return format!("P{} · Resources unavailable for this inspected context\nCollective cash unavailable · Organizer-hours unavailable · Shared household time unavailable", session.viewed_tick);
    };
    let cash = means
        .cash_micros
        .map_or_else(|| "unavailable".into(), crate::human_numbers::currency);
    let shared = means.shared_time.map_or_else(
        || "unavailable · next period unknown".into(),
        |(period, hours)| {
            format!(
                "{} h left in closed P{period} · next period unknown",
                crate::observer_ui::grouped(hours)
            )
        },
    );
    let endpoint = session
        .duration
        .and_then(CampaignDuration::final_period)
        .map_or_else(String::new, |period| format!(" / P{period}"));
    let routine = if means.standing_authorized {
        "authorized"
    } else {
        "paused"
    };
    format!("P{}{endpoint} committed · Collective cash {cash} · Organizer-hours pledged {}\nShared household time {shared} · Neighborhood {routine}", means.period, crate::observer_ui::grouped(means.organizer_hours))
}

/// Current earned subject knowledge for World; broad production remains undisclosed.
pub(crate) fn world_reports(client: &OrganizerClient, session: &ObserverSession) -> Option<String> {
    workspace::resources(client, session)?;
    let view = client.view.as_ref()?;
    let mut text = String::from("Earned reports · open Evidence to read");
    let mut reports: Vec<_> = view
        .observations
        .iter()
        .filter(|item| {
            item.actor_id == view.actor_id
                && view.knows_report_subject(item)
                && item.observed_period <= session.viewed_tick
                && item.acquired_period <= session.viewed_tick
        })
        .collect();
    reports.sort_by_key(|item| {
        (
            item.acquired_period,
            item.observed_period,
            item.observation_id,
        )
    });
    if reports.is_empty() {
        text.push_str("\nNo acquired report is available here. Open the known subject in the Archive for earlier evidence.");
    }
    for item in reports.iter().rev().take(2) {
        let _ = write!(
            text,
            "\n{}\n{}\nSource: {}",
            presentation::report_caption(item),
            presentation::report(&item.report),
            presentation::partner(view, item.source_actor_id)
        );
    }
    text.push_str(
        "\nEach report covers the facts its named source shared. The wider production circuit remains undisclosed.",
    );
    Some(text)
}

pub(super) fn availability(term: ChoiceAvailability) -> String {
    match term {
        ChoiceAvailability::Reviewable => "Available to review".into(),
        ChoiceAvailability::Historical => "History · return live to decide".into(),
        ChoiceAvailability::Complete => "Campaign complete".into(),
        ChoiceAvailability::Busy => "Awaiting committed state".into(),
        ChoiceAvailability::Accepted { resolves_period } => {
            format!("Ruling accepted for P{resolves_period}")
        }
        ChoiceAvailability::Refused(reason) => presentation::refusal(reason).into(),
        ChoiceAvailability::MissingTerms => "Terms unavailable · refresh the situation".into(),
        ChoiceAvailability::PendingAid {
            admitted_period,
            dispatch_period,
        } => format!("Route pending · admitted P{admitted_period}, dispatch P{dispatch_period}"),
        ChoiceAvailability::PeriodOverflow => "Resolution period unavailable".into(),
    }
}

fn aid_card_terms(choice: &PracticeChoice) -> Option<String> {
    use babylon_persistence::runtime_session::{
        OrganizerAidTransportPreview, OrganizerAllocation, OrganizerGiftConsent,
    };
    let OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = choice.allocation
    else {
        return None;
    };
    let aid = choice.aid?;
    let name = choice
        .partner
        .map_or("Partner attribution unavailable", |p| p.label);
    let hours = aid
        .food
        .as_ref()
        .and_then(|f| f.fulfillment_hours_per_unit.checked_mul(food_quantity));
    let route = aid
        .food
        .as_ref()
        .map_or("food terms unavailable", |f| match f.transport {
            OrganizerAidTransportPreview::Local => "local handoff",
            OrganizerAidTransportPreview::Routed { .. } => "freight · delay and loss possible",
        });
    if matches!(choice.availability, ChoiceAvailability::PendingAid { .. }) {
        return Some(format!("{name} · {route}\nUnsubmitted draft: {food_quantity} parcels + {}.\nEarlier support is still open on this route.", crate::human_numbers::currency(cash_micros)));
    }
    let cash = if aid.cash_receiving_consent == OrganizerGiftConsent::Refuse {
        "cash receiving refused"
    } else {
        "cash assessed at close"
    };
    let routine = if choice.routine == RoutineEffect::RemainsPaused {
        "Routine stays paused."
    } else {
        "Displaces routine once."
    };
    Some(format!("{name} · {route}\n{food_quantity} parcels + {} · {cash}\nUp to {} fulfillment h · {} possible coordination h\n{routine}",crate::human_numbers::currency(cash_micros),hours.map_or_else(||"unknown".into(),|h|h.to_string()),aid.coordination_hours))
}

/// Explain a blocked selected route beside its Review control.
pub(super) fn review_reason(
    client: &OrganizerClient,
    comparison: Option<&ChoiceComparison>,
) -> String {
    let Some(comparison) = comparison else {
        return String::new();
    };
    let Some(selected) = comparison
        .all_practices
        .iter()
        .find(|row| row.choice == comparison.draft_choice)
    else {
        return String::new();
    };
    let saving = if !client.draft_writable {
        "Draft saving unavailable; these amounts remain unsubmitted."
    } else if client.draft_dirty {
        "Draft changes awaiting save; these amounts remain unsubmitted."
    } else {
        "Amounts are a saved, unsubmitted draft."
    };
    match selected.availability {
        ChoiceAvailability::PendingAid { admitted_period, dispatch_period } => format!("Review blocked on this route: earlier support is open (admitted P{admitted_period}, dispatch P{dispatch_period}). {saving}"),
        _ => String::new(),
    }
}

pub(super) fn terms(choice: &PracticeChoice) -> String {
    use babylon_persistence::runtime_session::OrganizerAllocation;
    if let Some(terms) = aid_card_terms(choice) {
        return terms;
    }
    let parties = match (choice.target, choice.partner) {
        (Some(target), Some(partner)) if partner.subject != Some(target.subject) => {
            format!("At {} · with {}", target.label, partner.label)
        }
        (Some(target), Some(_)) => format!("With {}", target.label),
        (Some(target), None) => format!("From {}", target.label),
        (None, Some(partner)) => format!("With {}", partner.label),
        _ => "Party attribution unavailable".into(),
    };
    let cost = choice.hours.map_or_else(
        || "Hours unknown".into(),
        |hours| {
            let hours = crate::observer_ui::grouped(hours);
            match choice.hour_use {
                HourUse::Organizer => format!(
                    "{hours} of {} organizer-hours",
                    crate::observer_ui::grouped(choice.available_hours)
                ),
                HourUse::SharedMaterial => format!("{hours} shared material hours"),
                HourUse::LaterCoordination => format!("{hours} later coordination hours"),
            }
        },
    );
    let routine = match choice.routine {
        RoutineEffect::ReplacesOnce => "Replaces neighborhood work once",
        RoutineEffect::RemainsPaused => "Neighborhood work stays paused",
        RoutineEffect::Continues => "Continues neighborhood work",
        RoutineEffect::Pauses => "Pauses neighborhood work",
        RoutineEffect::Resumes => "Resumes neighborhood work",
    };
    let benefit = match choice.benefit {
        PossibleBenefit::Report {
            observed_period: Some(period),
        } => format!("Request the P{period} report if the partner participates."),
        PossibleBenefit::Report {
            observed_period: None,
        } => "No completed-period report exists yet.".into(),
        PossibleBenefit::WorkplaceContact => {
            "If the committee participates, contact can renew report sharing.".into()
        }
        PossibleBenefit::NeighborhoodContact => {
            "Attempt contact if the neighborhood group participates.".into()
        }
        PossibleBenefit::Collection => choice.collection.map_or_else(
            || "Collection terms unknown.".into(),
            |row| {
                format!(
                    "Voluntary gift up to {} currency after protected needs.",
                    crate::human_numbers::currency(match choice.allocation {
                        OrganizerAllocation::Collection { target_cash_micros } =>
                            target_cash_micros,
                        _ => row.maximum_cash_micros,
                    })
                )
            },
        ),
        PossibleBenefit::LocalGift | PossibleBenefit::RemoteGift => choice.aid.map_or_else(
            || "Gift terms unknown.".into(),
            |row| {
                format!(
                    "Offer up to {} units; delivery and later cooperation are separate.",
                    crate::observer_ui::grouped(row.maximum_quantity)
                )
            },
        ),
        PossibleBenefit::PauseRoutine => "Suspend the routine until explicitly resumed.".into(),
        PossibleBenefit::NoPractice => "No neighborhood practice will run.".into(),
    };
    let resolution = choice.resolves_period.map_or_else(
        || "Resolution unknown".into(),
        |period| format!("Resolves P{period}"),
    );
    format!(
        "{}\n{parties}\n{cost}   ·   {resolution}\n{routine}. {benefit}",
        choice.intent
    )
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Destination {
    Detail(DispatchDestination),
    Subject(OrganizerSubject),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct DatedLink {
    campaign: CampaignId,
    epoch: Option<u64>,
    durable_tick: u64,
    perspective: Perspective,
    period: u64,
    generation: u64,
    pub(super) destination: Destination,
}

impl DatedLink {
    pub(super) fn new(session: &ObserverSession, period: u64, destination: Destination) -> Self {
        let scope = session.context();
        Self {
            campaign: scope.campaign,
            epoch: session.lifecycle_epoch(),
            durable_tick: session.durable_tick,
            perspective: scope.perspective,
            period,
            generation: scope.generation,
            destination,
        }
    }
    pub(super) fn current(self, session: &ObserverSession) -> bool {
        session.accepts(&ObservationContext {
            campaign: self.campaign,
            perspective: self.perspective,
            tick: self.period,
            generation: self.generation,
        }) && self.epoch == session.lifecycle_epoch()
            && self.durable_tick == session.durable_tick
    }
}

#[derive(Default, Debug, PartialEq, Eq)]
pub(super) struct Bulletin {
    pub heading: String,
    pub copy: String,
    pub links: Vec<(String, DatedLink)>,
    pub compact: bool,
}

impl Bulletin {
    fn link(&mut self, session: &ObserverSession, period: u64, caption: String, dest: Destination) {
        let link = (caption, DatedLink::new(session, period, dest));
        if !self.links.contains(&link) {
            self.links.push(link);
        }
    }

    fn rows(
        &mut self,
        session: &ObserverSession,
        view: &OrganizerView,
        period: u64,
        rows: &DispatchRows,
    ) {
        for row in &rows.practices {
            let receipt = row.receipt;
            if let Some(partner) = row
                .partner
                .filter(|partner| receipt.partner_actor_id == Some(partner.actor_id))
            {
                if let Some(subject) = partner.subject {
                    self.link(
                        session,
                        period,
                        partner.label.into(),
                        Destination::Subject(subject),
                    );
                }
            }
            if let Some(row) = row.aid {
                use babylon_persistence::runtime_session::OrganizerFoodDelivery;
                let moved =
                    crate::observer_ui::grouped(row.support.material_postings.dispatched_quantity);
                let status = match row.support.status {
                    OrganizerFoodDelivery::NotRequested => "no food selected".into(),
                    OrganizerFoodDelivery::ReceivingRefused => "food receiving refused".into(),
                    OrganizerFoodDelivery::AwaitingDelivery => "awaiting delivery".into(),
                    OrganizerFoodDelivery::TerminalFailure => "food failed".into(),
                    OrganizerFoodDelivery::Granted { granted_quantity } => {
                        format!("{} granted", crate::observer_ui::grouped(granted_quantity))
                    }
                };
                let _ = writeln!(self.copy, "{moved} units dispatched · {status}");
            }
            self.link(
                session,
                period,
                "Practice receipt".into(),
                Destination::Detail(row.destination),
            );
        }
        for row in &rows.reports {
            let observation = row.observation;
            if let OrganizerReport::Partner { facts, .. } = &observation.report {
                if super::partner_copy::prior(view, observation, period, facts)
                    .is_some_and(|(_, old)| old == facts)
                {
                    continue;
                }
            }
            let _ = writeln!(
                self.copy,
                "{} · report observed P{}, acquired P{}\n{} · {}\n{}",
                row.source.label,
                observation.observed_period,
                observation.acquired_period,
                presentation::report_kind(&observation.report),
                presentation::report_origin(observation),
                presentation::report(&observation.report)
            );
            self.link(
                session,
                period,
                format!("Read {}", presentation::report_caption(observation)),
                Destination::Detail(row.destination),
            );
        }
        for row in &rows.encounters {
            let _ = writeln!(self.copy, "CITY PD VISIT · PERIOD {}\nA public venue check-in records City PD visiting {}. Organizer presence and police knowledge remain unknown.", row.encounter.resolve_period, row.subject.label);
            self.link(
                session,
                period,
                "Public venue record".into(),
                Destination::Detail(row.destination),
            );
            self.link(
                session,
                period,
                row.subject.label.into(),
                Destination::Subject(row.subject.subject),
            );
        }
    }
}

fn arrival_warning(client: &OrganizerClient, period: u64) -> Option<String> {
    use babylon_persistence::runtime_session::OrganizerAidTransportPreview;
    let view = client.view.as_ref()?;
    if view.period != period || !view.standing.authorized {
        return None;
    }
    let pending = client.pending_aid.iter().find(|row| {
        row.response.is_none()
            && row.dispatch_period <= period
            && row.dispatch_support.material_postings.dispatched_quantity > row.lost_quantity
    })?;
    let terms = client.aid.iter().find(|terms| {
        terms.period == period
            && terms.kind == pending.kind
            && terms.mandate_id == pending.mandate_id
            && terms.good_id == pending.good_id
            && terms.unit_id == pending.unit_id
    });
    let earliest = terms.and_then(|terms| match &terms.food.as_ref()?.transport {
        OrganizerAidTransportPreview::Routed { stages, .. } if !stages.is_empty() => stages
            .iter()
            .try_fold(pending.dispatch_period, |at, stage| {
                at.checked_add(u64::from(stage.travel_periods))
            }),
        _ => None,
    });
    let window = earliest.map_or_else(
        || "Arrival period unknown.".into(),
        |at| format!("Earliest possible arrival P{at}. Delay or loss can change the outcome."),
    );
    Some(format!("Food is in transit from P{}. {window} Coordination on arrival can compete with routine hours. Open Direction / routine to review Pause.",pending.dispatch_period))
}

pub(super) fn bulletin(scope: &Scope) -> Bulletin {
    let Some(dispatch) = workspace::dispatch(&scope.client, scope.session.viewed_tick) else {
        return Bulletin {
            heading: "Period dispatch".into(),
            copy: "Awaiting the period record.".into(),
            ..Bulletin::default()
        };
    };
    let mut bulletin = Bulletin {
        heading: format!("Period {} dispatch", dispatch.period),
        compact: dispatch.coverage == DispatchCoverage::Opening
            && dispatch.current.reports.is_empty()
            && dispatch.current.encounters.is_empty(),
        ..Bulletin::default()
    };
    bulletin.copy = presentation::dispatch_practices(&dispatch);
    bulletin.copy.push('\n');
    let unlinked = scope.client.aid_resolutions.iter().filter(|resolution| {
        !dispatch
            .current
            .practices
            .iter()
            .any(|row| row.aid == Some(*resolution))
    });
    let support = super::developments::current_support(unlinked, dispatch.period);
    if !support.is_empty() {
        let _ = writeln!(bulletin.copy, "{support}");
    }
    if let Some(warning) = arrival_warning(&scope.client, dispatch.period) {
        let _ = writeln!(bulletin.copy, "{warning}");
        bulletin.link(
            &scope.session,
            dispatch.period,
            "Review routine / Pause".into(),
            Destination::Detail(DispatchDestination::Inspector(
                OrganizerInspector::Direction,
            )),
        );
    }
    if dispatch.coverage == DispatchCoverage::ArchiveRequired {
        bulletin.link(
            &scope.session,
            dispatch.period,
            "Open practice Archive".into(),
            Destination::Detail(dispatch.missing_receipts),
        );
    }
    if let Some(view) = scope.client.view.as_ref() {
        bulletin.rows(&scope.session, view, dispatch.period, &dispatch.current);
    }
    bulletin.copy.truncate(bulletin.copy.trim_end().len());
    if !dispatch.history.practices.is_empty()
        || !dispatch.history.reports.is_empty()
        || !dispatch.history.encounters.is_empty()
    {
        bulletin.link(
            &scope.session,
            dispatch.period,
            "Dated history".into(),
            Destination::Detail(DispatchDestination::Inspector(OrganizerInspector::Receipts)),
        );
    }
    bulletin
}

#[cfg(test)]
mod arrival_tests {
    use super::arrival_warning;
    use super::OrganizerClient;
    use babylon_persistence::runtime_session::OrganizerSnapshot;
    #[test]
    fn actual_pending_food_warns_on_its_original_route_only_while_a_response_can_occur() {
        let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../../../babylon-persistence/tests/fixtures/national_organizer_pending_v19.json"
        ))
        .expect("captured dispatch");
        let mut client = OrganizerClient {
            view: Some(snapshot.view),
            aid: snapshot.aid,
            pending_aid: snapshot.pending_aid,
            ..OrganizerClient::default()
        };
        let warning = arrival_warning(&client, 1).expect("open food with active routine");
        assert!(
            warning.contains("Earliest possible arrival P2") && warning.contains("Pause"),
            "{warning}"
        );
        assert!(arrival_warning(&client, 0).is_none());
        client.view.as_mut().expect("view").standing.authorized = false;
        assert!(arrival_warning(&client, 1).is_none());
        client.view.as_mut().expect("view").standing.authorized = true;
        client.pending_aid[0].lost_quantity = 1;
        assert!(arrival_warning(&client, 1).is_none());
    }
}
