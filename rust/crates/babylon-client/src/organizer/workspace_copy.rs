//! Short card copy and dated navigation derived from the admitted view.
use std::fmt::Write as _;

use super::presentation;
use super::scene::OrganizerSubject;
use super::ui::Scope;
use super::workspace;
use super::{OrganizerClient, OrganizerInspector};
use crate::observer::{ObservationContext, ObserverSession, Perspective};
use crate::organizer::workspace::{
    ChoiceAvailability, DispatchCoverage, DispatchDestination, DispatchRows, HourUse,
    PossibleBenefit, PracticeChoice, RoutineEffect,
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

/// Current earned workplace knowledge for World; broad production remains undisclosed.
pub(crate) fn world_reports(client: &OrganizerClient, session: &ObserverSession) -> Option<String> {
    workspace::resources(client, session)?;
    let view = client.view.as_ref()?;
    let mut text = String::from("Earned workplace reports · open Evidence to read");
    let mut reports: Vec<_> = view
        .observations
        .iter()
        .filter(|item| {
            item.actor_id == view.actor_id
                && item.subject_id == view.workplace_id
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
        text.push_str("\nNo acquired workplace report is available here. Open Cited workplace Archive for retained evidence.");
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
        "\nThis is workplace report scope; the wider production circuit is not disclosed.",
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
        } => format!("Pending · admitted P{admitted_period}, dispatch P{dispatch_period}"),
        ChoiceAvailability::PeriodOverflow => "Resolution period unavailable".into(),
    }
}

pub(super) fn terms(choice: &PracticeChoice) -> String {
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
                    crate::human_numbers::currency(row.maximum_cash_micros)
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

    fn rows(&mut self, session: &ObserverSession, period: u64, rows: &DispatchRows) {
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
                use babylon_persistence::runtime_session::OrganizerAidSupportStatus;
                let moved =
                    crate::observer_ui::grouped(row.support.material_postings.dispatched_quantity);
                let status = match row.support.status {
                    OrganizerAidSupportStatus::NotRequested => "no food selected".into(),
                    OrganizerAidSupportStatus::ReceivingRefused => "food receiving refused".into(),
                    OrganizerAidSupportStatus::AwaitingDelivery => "awaiting delivery".into(),
                    OrganizerAidSupportStatus::TerminalFailure => "support failed".into(),
                    OrganizerAidSupportStatus::Granted {
                        granted_quantity,
                        consumed_quantity,
                    } => format!(
                        "{} granted · recipient consumed {} of the same good in total",
                        crate::observer_ui::grouped(granted_quantity),
                        crate::observer_ui::grouped(consumed_quantity)
                    ),
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
    if dispatch.coverage == DispatchCoverage::ArchiveRequired {
        bulletin.link(
            &scope.session,
            dispatch.period,
            "Open practice Archive".into(),
            Destination::Detail(dispatch.missing_receipts),
        );
    }
    bulletin.rows(&scope.session, dispatch.period, &dispatch.current);
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
