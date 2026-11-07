//! Typed decision and dispatch projections over admitted organizer records.

use babylon_persistence::runtime_session::{
    CityPdEncounter, OrganizerAidKind, OrganizerAidResolution, OrganizerChoice,
    OrganizerCollectionPreview, OrganizerCollectionResolution, OrganizerGiftConsent,
    OrganizerInquiry, OrganizerMaterialAidPreview, OrganizerObservation, OrganizerReceipt,
    OrganizerRefusal, OrganizerView,
};

use crate::observer::{ObserverSession, SessionPhase};

use super::scene::OrganizerSubject;
use super::{presentation, OrganizerClient, OrganizerInspector};

/// Current disclosed means; absence never stands for a zero balance.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct ResourceSummary {
    pub period: u64,
    pub cash_micros: Option<i128>,
    pub organizer_hours: u64,
    pub standing_authorized: bool,
    pub shared_time: Option<(u64, u64)>,
}

pub(super) fn resources(
    client: &OrganizerClient,
    session: &ObserverSession,
) -> Option<ResourceSummary> {
    let view = client.view.as_ref()?;
    let (_, scope) = client.body_for(session)?;
    if view.period != session.viewed_tick
        || view.period != session.durable_tick
        || scope.period != view.period
        || scope.actor_id != view.actor_id
        || scope.campaign_id != *session.campaign.as_uuid().as_bytes()
        || scope.content_digest != view.content_digest
    {
        return None;
    }
    Some(ResourceSummary {
        period: view.period,
        cash_micros: client
            .collection_preview()
            .map(|row| row.organization_cash_micros),
        organizer_hours: view.available_hours,
        standing_authorized: view.standing.authorized,
        shared_time: shared_household_time(client, view.period),
    })
}

fn shared_household_time(client: &OrganizerClient, period: u64) -> Option<(u64, u64)> {
    if period == 0 {
        return None;
    }
    let mut budget = None;
    for row in client.aid.iter().filter(|row| row.period == period) {
        let food = row.food.as_ref()?;
        let time = food.time.as_ref()?;
        if time.period != period || time.labor_unit_id != food.labor_unit_id {
            return None;
        }
        let disclosed = (
            row.donor_id,
            time.labor_unit_id,
            time.period,
            time.remaining_hours,
        );
        if budget.is_some_and(|previous| previous != disclosed) {
            return None;
        }
        budget = Some(disclosed);
    }
    budget.map(|(_, _, period, hours)| (period, hours))
}

pub(super) const ALL_PRACTICES: [OrganizerChoice; 9] = [
    OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
    OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived),
    OrganizerChoice::Reinforce,
    OrganizerChoice::Collect,
    OrganizerChoice::LocalAid,
    OrganizerChoice::RemoteAid,
    OrganizerChoice::Hold,
    OrganizerChoice::PauseStanding,
    OrganizerChoice::ResumeStanding,
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct NamedSubject<'a> {
    pub subject: OrganizerSubject,
    pub label: &'a str,
}

/// A partner need not have a disclosed scene node (for example, an aid recipient).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct NamedPartner<'a> {
    pub actor_id: u64,
    pub label: &'a str,
    pub subject: Option<OrganizerSubject>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum HourUse {
    Organizer,
    SharedMaterial,
    LaterCoordination,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum RoutineEffect {
    ReplacesOnce,
    RemainsPaused,
    Continues,
    Pauses,
    Resumes,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum PossibleBenefit {
    Report { observed_period: Option<u64> },
    WorkplaceContact,
    NeighborhoodContact,
    Collection,
    LocalGift,
    RemoteGift,
    PauseRoutine,
    NoPractice,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum ChoiceAvailability {
    Reviewable,
    Historical,
    Complete,
    Busy,
    Accepted {
        resolves_period: u64,
    },
    Refused(OrganizerRefusal),
    MissingTerms,
    PendingAid {
        admitted_period: u64,
        dispatch_period: u64,
    },
    PeriodOverflow,
}

/// Captured terms, never an admitted command or a predicted outcome.
#[derive(Debug)]
pub(super) struct PracticeChoice<'a> {
    pub choice: OrganizerChoice,
    pub allocation: babylon_persistence::runtime_session::OrganizerAllocation,
    pub title: &'static str,
    pub intent: &'static str,
    pub target: Option<NamedSubject<'a>>,
    pub partner: Option<NamedPartner<'a>>,
    pub captured_period: u64,
    pub hours: Option<u64>,
    pub hour_use: HourUse,
    pub available_hours: u64,
    pub routine: RoutineEffect,
    pub benefit: PossibleBenefit,
    pub resolves_period: Option<u64>,
    pub availability: ChoiceAvailability,
    pub collection: Option<&'a OrganizerCollectionPreview>,
    pub aid: Option<&'a OrganizerMaterialAidPreview>,
}

#[derive(Debug)]
pub(super) struct ChoiceComparison<'a> {
    pub draft_choice: OrganizerChoice,
    pub alternatives: [PracticeChoice<'a>; 2],
    pub all_practices: [PracticeChoice<'a>; ALL_PRACTICES.len()],
}

/// Inspecting comparison alternatives does not change the draft or selected subject.
pub(super) fn comparison<'a>(
    client: &'a OrganizerClient,
    session: &ObserverSession,
) -> Option<ChoiceComparison<'a>> {
    let view = client.view.as_ref()?;
    // A live DTO must not stand in for missing historical terms.
    if view.period != session.viewed_tick {
        return None;
    }
    let draft_choice = client.choice();
    let alternative = if draft_choice == OrganizerChoice::Hold {
        if practice(client, view, session, OrganizerChoice::Reinforce).availability
            == ChoiceAvailability::Reviewable
        {
            OrganizerChoice::Reinforce
        } else {
            ALL_PRACTICES
                .into_iter()
                .find(|choice| {
                    *choice != OrganizerChoice::Hold
                        && practice(client, view, session, *choice).availability
                            == ChoiceAvailability::Reviewable
                })
                .unwrap_or(OrganizerChoice::Reinforce)
        }
    } else {
        draft_choice
    };
    let alternatives = if matches!(
        draft_choice,
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
    ) {
        [OrganizerChoice::LocalAid, OrganizerChoice::RemoteAid]
    } else {
        [alternative, OrganizerChoice::Hold]
    };
    Some(ChoiceComparison {
        draft_choice,
        alternatives: alternatives.map(|choice| practice(client, view, session, choice)),
        all_practices: ALL_PRACTICES.map(|choice| practice(client, view, session, choice)),
    })
}

fn known_partner(view: &OrganizerView, actor_id: u64) -> NamedPartner<'_> {
    let subject = if actor_id == view.workplace_partner_id {
        Some(OrganizerSubject::WorkplaceCommittee(actor_id))
    } else if actor_id == view.neighborhood_partner_id {
        Some(OrganizerSubject::NeighborhoodGroup(actor_id))
    } else if actor_id == view.actor_id {
        Some(OrganizerSubject::Collective(actor_id))
    } else if view.aid_partners.iter().any(|p| p.actor_id == actor_id) {
        Some(OrganizerSubject::AidPartner(actor_id))
    } else {
        None
    };
    NamedPartner {
        actor_id,
        label: presentation::partner(view, actor_id),
        subject,
    }
}

fn aid_kind(choice: OrganizerChoice) -> Option<OrganizerAidKind> {
    match choice {
        OrganizerChoice::LocalAid => Some(OrganizerAidKind::Local),
        OrganizerChoice::RemoteAid => Some(OrganizerAidKind::Remote),
        _ => None,
    }
}

fn captured_parties<'a>(
    client: &'a OrganizerClient,
    view: &'a OrganizerView,
    choice: OrganizerChoice,
) -> (Option<NamedSubject<'a>>, Option<NamedPartner<'a>>) {
    match choice {
        OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce => (
            Some(NamedSubject {
                subject: OrganizerSubject::Workplace(view.workplace_id),
                label: &view.workplace_label,
            }),
            Some(known_partner(view, view.workplace_partner_id)),
        ),
        OrganizerChoice::Hold
        | OrganizerChoice::PauseStanding
        | OrganizerChoice::ResumeStanding => (
            Some(NamedSubject {
                subject: OrganizerSubject::NeighborhoodGroup(view.neighborhood_partner_id),
                label: &view.neighborhood_partner_label,
            }),
            Some(known_partner(view, view.neighborhood_partner_id)),
        ),
        OrganizerChoice::Collect => (
            client.collection_preview().map(|terms| NamedSubject {
                subject: OrganizerSubject::Contributor(terms.contributor_id),
                label: &terms.contributor_label,
            }),
            None,
        ),
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => (
            None,
            view.aid_partners
                .iter()
                .find(|partner| Some(partner.kind) == aid_kind(choice))
                .map(|partner| known_partner(view, partner.actor_id)),
        ),
    }
}

fn practice<'a>(
    client: &'a OrganizerClient,
    view: &'a OrganizerView,
    session: &ObserverSession,
    choice: OrganizerChoice,
) -> PracticeChoice<'a> {
    let collection = (choice == OrganizerChoice::Collect)
        .then(|| client.collection_preview())
        .flatten();
    let aid = client.aid_preview(choice);
    let hours = match choice {
        OrganizerChoice::Inquiry(_) => Some(view.inquiry_hours),
        OrganizerChoice::Reinforce | OrganizerChoice::ResumeStanding => Some(view.contact_hours),
        OrganizerChoice::Hold if view.standing.authorized => Some(view.contact_hours),
        OrganizerChoice::Hold | OrganizerChoice::PauseStanding => Some(0),
        OrganizerChoice::Collect => collection.map(|terms| terms.collection_hours),
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            aid.map(|terms| terms.coordination_hours)
        }
    };
    let routine = match choice {
        OrganizerChoice::PauseStanding => RoutineEffect::Pauses,
        OrganizerChoice::ResumeStanding => RoutineEffect::Resumes,
        OrganizerChoice::Hold if view.standing.authorized => RoutineEffect::Continues,
        OrganizerChoice::Hold => RoutineEffect::RemainsPaused,
        _ if view.standing.authorized => RoutineEffect::ReplacesOnce,
        _ => RoutineEffect::RemainsPaused,
    };
    let benefit = match choice {
        OrganizerChoice::Inquiry(_) => PossibleBenefit::Report {
            observed_period: (view.period > 0).then_some(view.period),
        },
        OrganizerChoice::Reinforce => PossibleBenefit::WorkplaceContact,
        OrganizerChoice::Hold if !view.standing.authorized => PossibleBenefit::NoPractice,
        OrganizerChoice::Hold | OrganizerChoice::ResumeStanding => {
            PossibleBenefit::NeighborhoodContact
        }
        OrganizerChoice::PauseStanding => PossibleBenefit::PauseRoutine,
        OrganizerChoice::Collect => PossibleBenefit::Collection,
        OrganizerChoice::LocalAid => PossibleBenefit::LocalGift,
        OrganizerChoice::RemoteAid => PossibleBenefit::RemoteGift,
    };
    let (target, partner) = captured_parties(client, view, choice);
    PracticeChoice {
        allocation: client.draft.as_ref().map_or(
            babylon_persistence::runtime_session::OrganizerAllocation::None,
            |d| match choice {
                OrganizerChoice::Collect => d.collection_allocation,
                OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => d.aid_allocation,
                _ => babylon_persistence::runtime_session::OrganizerAllocation::None,
            },
        ),
        choice,
        title: presentation::choice(choice),
        intent: presentation::flavor(view, choice),
        target,
        partner,
        captured_period: view.period,
        hours,
        hour_use: match choice {
            OrganizerChoice::Collect => HourUse::SharedMaterial,
            OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => HourUse::LaterCoordination,
            _ => HourUse::Organizer,
        },
        available_hours: view.available_hours,
        routine,
        benefit,
        resolves_period: view.period.checked_add(1),
        availability: availability(client, view, session, choice, hours),
        collection,
        aid,
    }
}

pub(super) fn reviewable(
    client: &OrganizerClient,
    session: &ObserverSession,
    choice: OrganizerChoice,
) -> bool {
    client
        .view
        .as_ref()
        .filter(|view| view.period == session.viewed_tick)
        .is_some_and(|view| {
            practice(client, view, session, choice).availability == ChoiceAvailability::Reviewable
        })
}

fn availability(
    client: &OrganizerClient,
    view: &OrganizerView,
    session: &ObserverSession,
    choice: OrganizerChoice,
    hours: Option<u64>,
) -> ChoiceAvailability {
    if session.viewed_tick != session.durable_tick {
        return ChoiceAvailability::Historical;
    }
    if session.phase == SessionPhase::Complete {
        return ChoiceAvailability::Complete;
    }
    if let Some(commitment) = &client.commitment {
        return ChoiceAvailability::Accepted {
            resolves_period: commitment.resolves_period,
        };
    }
    if !client.available(session) {
        return ChoiceAvailability::Busy;
    }
    if view.period.checked_add(1).is_none() {
        return ChoiceAvailability::PeriodOverflow;
    }
    if let Some(pending) = client.pending_aid.iter().find(|pending| {
        Some(pending.kind) == aid_kind(choice) && pending.admitted_period <= view.period
    }) {
        return ChoiceAvailability::PendingAid {
            admitted_period: pending.admitted_period,
            dispatch_period: pending.dispatch_period,
        };
    }
    if let Some(refusal) = client
        .preview
        .as_ref()
        .filter(|preview| {
            preview.choice == choice
                && preview.current_period == view.period
                && client.review_context.as_ref() == Some(&session.context())
        })
        .and_then(|preview| preview.refusal)
    {
        return ChoiceAvailability::Refused(refusal);
    }
    if choice == OrganizerChoice::Collect {
        return client
            .collection_preview()
            .map_or(ChoiceAvailability::MissingTerms, |terms| {
                match terms.cash_consent {
                    OrganizerGiftConsent::Accept => ChoiceAvailability::Reviewable,
                    OrganizerGiftConsent::Refuse => {
                        ChoiceAvailability::Refused(OrganizerRefusal::CollectionCashRefused)
                    }
                }
            });
    }
    if aid_kind(choice).is_some() {
        let Some(terms) = client.aid_preview(choice) else {
            return ChoiceAvailability::MissingTerms;
        };
        if terms.receiving_consent == OrganizerGiftConsent::Refuse
            && terms.cash_receiving_consent == OrganizerGiftConsent::Refuse
        {
            return ChoiceAvailability::Refused(OrganizerRefusal::AidReceivingRefused);
        }
        if !presentation::aid_terms_attributed(client, choice) || !client.choice_available(choice) {
            return ChoiceAvailability::MissingTerms;
        }
    } else if choice == OrganizerChoice::ResumeStanding && view.standing.authorized {
        return ChoiceAvailability::Refused(OrganizerRefusal::StandingWorkAlreadyActive);
    } else if hours.is_some_and(|hours| hours > view.available_hours) {
        return ChoiceAvailability::Refused(OrganizerRefusal::InsufficientCommittedTime);
    }
    ChoiceAvailability::Reviewable
}

/// A UI maps these destinations to its existing navigation handlers without text matching.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum DispatchDestination {
    Report([u8; 32]),
    Inspector(OrganizerInspector),
    ArchiveWorkplace,
    ArchiveOrganization,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum DispatchCoverage {
    Opening,
    Included,
    ArchiveRequired,
}

#[derive(Debug)]
pub(super) struct DispatchPractice<'a> {
    pub receipt: &'a OrganizerReceipt,
    pub partner: Option<NamedPartner<'a>>,
    pub collection: Option<&'a OrganizerCollectionResolution>,
    pub aid: Option<&'a OrganizerAidResolution>,
    pub destination: DispatchDestination,
}

#[derive(Debug)]
pub(super) struct DispatchReport<'a> {
    pub observation: &'a OrganizerObservation,
    pub source: NamedPartner<'a>,
    pub destination: DispatchDestination,
}

#[derive(Debug)]
pub(super) struct DispatchEncounter<'a> {
    pub encounter: &'a CityPdEncounter,
    pub subject: NamedSubject<'a>,
    pub destination: DispatchDestination,
}

#[derive(Debug, Default)]
pub(super) struct DispatchRows<'a> {
    pub practices: Vec<DispatchPractice<'a>>,
    pub reports: Vec<DispatchReport<'a>>,
    pub encounters: Vec<DispatchEncounter<'a>>,
}

#[derive(Debug)]
pub(super) struct PeriodDispatch<'a> {
    pub period: u64,
    pub coverage: DispatchCoverage,
    pub current: DispatchRows<'a>,
    pub history: DispatchRows<'a>,
    pub missing_receipts: DispatchDestination,
}

/// A missing current receipt is unknown; an older result cannot fill the gap.
pub(super) fn dispatch(client: &OrganizerClient, period: u64) -> Option<PeriodDispatch<'_>> {
    dispatch_for_view(client, client.view.as_ref()?, period)
}

pub(super) fn dispatch_for_view<'a>(
    client: &'a OrganizerClient,
    view: &'a OrganizerView,
    period: u64,
) -> Option<PeriodDispatch<'a>> {
    if period > view.period {
        return None;
    }
    let mut current = DispatchRows::default();
    let mut history = DispatchRows::default();
    collect_practices(client, view, period, &mut current, &mut history);
    collect_reports(view, period, &mut current, &mut history);
    collect_encounters(client, view, period, &mut current, &mut history);
    let coverage = if period == 0 {
        DispatchCoverage::Opening
    } else if current.practices.is_empty() {
        DispatchCoverage::ArchiveRequired
    } else {
        DispatchCoverage::Included
    };
    Some(PeriodDispatch {
        period,
        coverage,
        current,
        history,
        missing_receipts: DispatchDestination::ArchiveOrganization,
    })
}

fn collect_practices<'a>(
    client: &'a OrganizerClient,
    view: &'a OrganizerView,
    period: u64,
    current: &mut DispatchRows<'a>,
    history: &mut DispatchRows<'a>,
) {
    for receipt in &view.receipts {
        if receipt.actor_id != view.actor_id || receipt.period == 0 || receipt.period > period {
            continue;
        }
        let row = DispatchPractice {
            receipt,
            partner: receipt
                .partner_actor_id
                .map(|actor| known_partner(view, actor)),
            collection: client.collection_resolutions.iter().find(|row| {
                row.practice == *receipt
                    && row.fact.actor_id == view.actor_id
                    && row.fact.period == receipt.period
                    && Some(row.fact.original_commitment_id) == receipt.commitment_id
            }),
            aid: client.aid_resolutions.iter().find(|row| {
                row.practice == *receipt
                    && row.support.period == receipt.period
                    && Some(row.pending.original_commitment_id) == receipt.commitment_id
            }),
            destination: DispatchDestination::Inspector(OrganizerInspector::Receipts),
        };
        if receipt.period == period {
            current.practices.push(row);
        } else {
            history.practices.push(row);
        }
    }
}

fn collect_reports<'a>(
    view: &'a OrganizerView,
    period: u64,
    current: &mut DispatchRows<'a>,
    history: &mut DispatchRows<'a>,
) {
    for observation in &view.observations {
        if observation.actor_id != view.actor_id
            || !view.knows_report_subject(observation)
            || observation.observed_period > period
            || observation.acquired_period > period
        {
            continue;
        }
        let row = DispatchReport {
            observation,
            source: known_partner(view, observation.source_actor_id),
            destination: DispatchDestination::Report(observation.observation_id),
        };
        if period > 0 && observation.acquired_period == period {
            current.reports.push(row);
        } else {
            history.reports.push(row);
        }
    }
}

fn collect_encounters<'a>(
    client: &'a OrganizerClient,
    view: &'a OrganizerView,
    period: u64,
    current: &mut DispatchRows<'a>,
    history: &mut DispatchRows<'a>,
) {
    for encounter in &client.city_pd_encounters {
        if !disclosed_encounter(client, view, encounter) || encounter.resolve_period > period {
            continue;
        }
        let row = DispatchEncounter {
            encounter,
            subject: NamedSubject {
                subject: OrganizerSubject::Workplace(encounter.subject_id),
                label: &view.workplace_label,
            },
            destination: DispatchDestination::ArchiveWorkplace,
        };
        if encounter.resolve_period == period {
            current.encounters.push(row);
        } else {
            history.encounters.push(row);
        }
    }
}

fn disclosed_encounter(
    client: &OrganizerClient,
    view: &OrganizerView,
    encounter: &CityPdEncounter,
) -> bool {
    client
        .campaign
        .is_some_and(|campaign| *campaign.as_bytes() == encounter.campaign_id)
        && encounter.controlled_actor_id == view.actor_id
        && encounter.authority_id == view.authority_id
        && encounter.content_digest == view.content_digest
        && encounter.resource_digest == view.resource_digest
        && encounter.subject_id == view.workplace_id
        && encounter.resolve_period > 0
}

#[cfg(test)]
mod tests {
    use super::super::RequestKind;
    use super::*;
    use crate::observer::Perspective;
    use babylon_persistence::runtime_session::OrganizerAidFunding;
    use babylon_persistence::runtime_session::OrganizerAllocation;
    use babylon_persistence::runtime_session::{
        OrganizerAidOption, OrganizerAidPending, OrganizerAidTransportPreview, OrganizerOutcome,
        OrganizerPartnerResponse, OrganizerPreview, OrganizerReport,
    };

    fn view_mut(client: &mut OrganizerClient) -> &mut OrganizerView {
        client
            .view
            .as_mut()
            .expect("the fixture has an admitted organizer view")
    }

    fn receipt(period: u64) -> OrganizerReceipt {
        OrganizerReceipt {
            receipt_id: [1; 32],
            commitment_id: Some([2; 32]),
            actor_id: 90,
            period,
            choice: OrganizerChoice::Reinforce,
            standing_work: false,
            outcome: OrganizerOutcome::ContactCompleted,
            hours_spent: 8,
            partner_actor_id: Some(92),
            partner_response: OrganizerPartnerResponse::Participated,
            observation_ids: Vec::new(),
            contact_product_id: Some([3; 32]),
            time_use: Vec::new(),
        }
    }

    fn observation(observed_period: u64, acquired_period: u64) -> OrganizerObservation {
        OrganizerObservation {
            observation_id: [6; 32],
            actor_id: 90,
            subject_id: 91,
            source_actor_id: 92,
            observed_period,
            acquired_period,
            receipt_id: Some([1; 32]),
            report: OrganizerReport::Work {
                performed_labor_hours: 20,
                output_kg: 50,
                previous_labor_hours: None,
                previous_output_kg: None,
            },
        }
    }

    #[test]
    fn comparison_uses_actual_costs_and_paused_routine_without_changing_the_draft() {
        let (mut client, session) = super::super::tests::ready();
        client.selected_subject = Some(OrganizerSubject::Collective(90));
        // Michigan captures 12/8; the national scenario captures 2/2.
        for (inquiry, contact) in [(12, 8), (2, 2)] {
            view_mut(&mut client).inquiry_hours = inquiry;
            view_mut(&mut client).contact_hours = contact;
            let cards = comparison(&client, &session).expect("current terms are available");
            assert_eq!(
                cards.draft_choice,
                OrganizerChoice::Hold,
                "comparison is not selection"
            );
            assert_eq!(cards.alternatives[0].choice, OrganizerChoice::Reinforce);
            assert_eq!(cards.alternatives[0].hours, Some(contact));
            assert_eq!(cards.alternatives[0].routine, RoutineEffect::ReplacesOnce);
            assert_eq!(cards.alternatives[1].hours, Some(contact));
            assert_eq!(
                cards.all_practices.len(),
                ALL_PRACTICES.len(),
                "no practice is lost"
            );
            assert_eq!(cards.all_practices[0].hours, Some(inquiry));
            assert_eq!(
                cards.alternatives[0]
                    .target
                    .expect("captured target")
                    .subject,
                OrganizerSubject::Workplace(91),
                "selection cannot retarget a practice"
            );
            assert_eq!(
                cards.alternatives[0]
                    .partner
                    .expect("captured partner")
                    .actor_id,
                92
            );
        }
        view_mut(&mut client).standing.authorized = false;
        let cards = comparison(&client, &session).expect("paused terms remain inspectable");
        assert_eq!(cards.alternatives[0].routine, RoutineEffect::RemainsPaused);
        assert_eq!(cards.alternatives[1].hours, Some(0));
        assert_eq!(cards.alternatives[1].routine, RoutineEffect::RemainsPaused);
        assert_eq!(
            cards.alternatives[1].benefit,
            PossibleBenefit::NoPractice,
            "holding a paused routine cannot offer a contact"
        );
        assert_eq!(client.choice(), OrganizerChoice::Hold);
        assert_eq!(
            client.selected_subject,
            Some(OrganizerSubject::Collective(90))
        );
    }

    #[test]
    fn national_aid_compares_destinations_and_preserves_the_shared_basket() {
        use babylon_persistence::runtime_session::OrganizerSnapshot;
        let captured: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../../../babylon-persistence/tests/fixtures/national_organizer_opening_v19.json"
        ))
        .expect("released national opening snapshot");
        let (mut client, mut session) = super::super::tests::ready();
        session.ready(0, None);
        client.view = Some(captured.view);
        client.aid = captured.aid;
        let draft = client.draft.as_mut().expect("draft");
        draft.choice = OrganizerChoice::LocalAid;
        let cards = comparison(&client, &session).expect("current comparison");
        assert_eq!(
            cards.alternatives.map(|card| card.choice),
            [OrganizerChoice::LocalAid, OrganizerChoice::RemoteAid]
        );
        assert!(cards
            .all_practices
            .iter()
            .any(|card| card.choice == OrganizerChoice::Hold));
    }

    #[test]
    fn non_hold_compares_its_captured_practice_and_p0_has_no_completed_report() {
        let (mut client, mut session) = super::super::tests::ready();
        client.draft.as_mut().expect("fixture draft").choice =
            OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived);
        session.ready(0, None);
        view_mut(&mut client).period = 0;
        let mut opening_report = observation(0, 0);
        opening_report.receipt_id = None;
        view_mut(&mut client).observations.push(opening_report);
        let cards = comparison(&client, &session).expect("opening view exists");
        assert_eq!(cards.alternatives[0].choice, client.choice());
        assert_eq!(cards.alternatives[1].choice, OrganizerChoice::Hold);
        assert_eq!(
            cards.alternatives[0].benefit,
            PossibleBenefit::Report {
                observed_period: None
            },
            "P0 cannot offer a completed report"
        );
        assert_eq!(cards.alternatives[0].resolves_period, Some(1));
        assert_eq!(
            dispatch(&client, 0).expect("opening dispatch").coverage,
            DispatchCoverage::Opening
        );
        assert!(
            dispatch(&client, 0)
                .expect("opening dispatch")
                .current
                .reports
                .is_empty(),
            "opening knowledge is not a completed-period dispatch"
        );
        assert_eq!(
            dispatch(&client, 0)
                .expect("opening dispatch")
                .history
                .reports
                .len(),
            1,
            "captured opening knowledge remains available with its actual date"
        );
    }

    #[test]
    fn hold_falls_back_to_an_available_alternative_without_selecting_it() {
        let (mut client, mut session) = super::super::tests::ready();
        view_mut(&mut client).contact_hours = 20;
        view_mut(&mut client).inquiry_hours = 2;
        let cards = comparison(&client, &session).expect("current comparison");
        assert_eq!(
            cards.alternatives[0].choice,
            OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
            "a reviewable alternative replaces unavailable default contact"
        );
        assert_eq!(cards.alternatives[0].hours, Some(2));
        assert_eq!(
            client.choice(),
            OrganizerChoice::Hold,
            "fallback is never selection"
        );
        session.set_organizer_control_pending(true);
        let cards = comparison(&client, &session).expect("pending comparison");
        assert_eq!(
            cards.alternatives[0].choice,
            OrganizerChoice::Reinforce,
            "when none are reviewable, retain the default and explain unavailability"
        );
        assert_eq!(cards.alternatives[0].availability, ChoiceAvailability::Busy);
        assert_eq!(client.choice(), OrganizerChoice::Hold);
    }

    #[test]
    fn preview_refusals_pending_requests_and_historical_views_cannot_offer_writes() {
        let (mut client, mut session) = super::super::tests::ready();
        client.preview = Some(OrganizerPreview {
            allocation: OrganizerAllocation::None,
            choice: OrganizerChoice::Reinforce,
            current_period: 3,
            resolves_period: 4,
            available_hours: 16,
            required_hours: 8,
            replaces_standing_work: true,
            refusal: Some(OrganizerRefusal::HouseholdTimeAlreadySpent),
            observations: Vec::new(),
        });
        client.review_context = Some(session.context());
        assert_eq!(
            comparison(&client, &session)
                .expect("current comparison")
                .all_practices
                .iter()
                .find(|row| row.choice == OrganizerChoice::Reinforce)
                .expect("reinforcement remains reachable")
                .availability,
            ChoiceAvailability::Refused(OrganizerRefusal::HouseholdTimeAlreadySpent)
        );
        session.set_organizer_control_pending(true);
        assert_eq!(
            comparison(&client, &session)
                .expect("pending comparison")
                .alternatives[0]
                .availability,
            ChoiceAvailability::Busy
        );
        session.set_organizer_control_pending(false);
        session.inspect_tick(2);
        assert!(
            comparison(&client, &session).is_none(),
            "live terms cannot fill a held historical view"
        );
        view_mut(&mut client).period = 2;
        assert_eq!(
            comparison(&client, &session)
                .expect("matching historical terms")
                .alternatives[0]
                .availability,
            ChoiceAvailability::Historical
        );
        assert_eq!(
            client.choice(),
            OrganizerChoice::Hold,
            "inspection preserves the draft"
        );
    }

    fn admitted_resources(period: u64) -> (OrganizerClient, ObserverSession) {
        let (_, _, _, mut snapshot) = super::super::tests::status_fixture();
        let (mut client, mut session) = super::super::tests::ready();
        session.ready(period, None);
        view_mut(&mut client).period = period;
        snapshot.view.period = period;
        snapshot.body_scope.period = period;
        snapshot
            .city_pd_encounters
            .retain(|row| row.resolve_period <= period);
        client.queue(&mut session, RequestKind::Status, None);
        let request = client.outbox.take().expect("current-period status request");
        let babylon_persistence::runtime_session::RuntimeSessionRequest::OrganizerStatus {
            request_id,
            ..
        } = request
        else {
            panic!("fixture status request")
        };
        client
            .status(request_id, snapshot, &mut session)
            .expect("admitted current status");
        install_aid(&mut client);
        client.aid[0].period = period;
        client.aid[0].food.as_mut().expect("food offer").time =
            Some(babylon_persistence::runtime_session::OrganizerAidTime {
                period,
                labor_unit_id: [9; 32],
                remaining_hours: 6,
            });
        client.collection = Some(OrganizerCollectionPreview {
            period,
            mandate_id: [8; 32],
            actor_id: 90,
            contributor_id: 101,
            contributor_label: "Captured contributor".into(),
            source_hash: [16; 32],
            cash_consent: OrganizerGiftConsent::Accept,
            initial_cash_micros: 400_000,
            maximum_cash_micros: 400_000,
            protected_cash_floor_micros: 123_000,
            collection_hours: 5,
            organization_cash_micros: 1_234_560_000,
        });
        (client, session)
    }

    #[test]
    fn resource_cash_is_owned_and_absence_is_not_zero() {
        let (mut client, session) = admitted_resources(3);
        let summary = resources(&client, &session).expect("admitted resources");
        assert_eq!(
            summary.cash_micros,
            Some(1_234_560_000),
            "use collective account, never cap, floor or arbitrary aid payer"
        );
        assert_eq!(
            summary.organizer_hours, 16,
            "captured commitments are organizer hours"
        );
        client
            .collection
            .as_mut()
            .expect("collection")
            .organization_cash_micros = 0;
        assert_eq!(
            resources(&client, &session).expect("current").cash_micros,
            Some(0),
            "real zero is disclosed"
        );
        client.collection.as_mut().expect("collection").actor_id += 1;
        assert_eq!(
            resources(&client, &session).expect("current").cash_micros,
            None,
            "foreign accounts are not collective cash"
        );
        client.collection = None;
        client.aid.clear();
        let summary = resources(&client, &session)
            .expect("Michigan still discloses captured organizer commitments");
        assert_eq!(summary.cash_micros, None, "missing treasury is unavailable");
        assert_eq!(
            summary.shared_time, None,
            "fixed organizer commitments cannot invent household time"
        );
    }

    #[test]
    fn resource_shared_household_time_is_dated_once_and_conflicts_are_unavailable() {
        // The engine-backed opening_time_is_unknown_then_projection_uses_actual_unspent_closed_time
        // contract closes P2 with preview.period == time.period == 2; the internal
        // circuit is already at its next period, P3. The client view uses committed P2.
        for period in [2, 3] {
            let (mut client, session) = admitted_resources(period);
            let mut duplicate = client.aid[0].clone();
            duplicate.kind = OrganizerAidKind::Remote;
            duplicate.mandate_id = [17; 32];
            duplicate.recipient_actor_id = 18;
            client.aid.push(duplicate);
            assert_eq!(
                resources(&client, &session).expect("current").shared_time,
                Some((period, 6)),
                "producer-aligned committed receipt is counted once across mandates"
            );
            client.aid[1]
                .food
                .as_mut()
                .expect("food offer")
                .time
                .as_mut()
                .expect("closed receipt")
                .remaining_hours = 0;
            assert_eq!(
                resources(&client, &session).expect("current").shared_time,
                None,
                "conflicting disclosures must not choose a favorable row"
            );
            client.aid.pop();
            client.aid[0]
                .food
                .as_mut()
                .expect("food offer")
                .time
                .as_mut()
                .expect("closed receipt")
                .remaining_hours = 0;
            assert_eq!(
                resources(&client, &session).expect("current").shared_time,
                Some((period, 0)),
                "zero observed remainder is known"
            );
            for invalid_period in [0, period - 1, period + 1] {
                client.aid[0]
                    .food
                    .as_mut()
                    .expect("food offer")
                    .time
                    .as_mut()
                    .expect("closed receipt")
                    .period = invalid_period;
                assert_eq!(
                    resources(&client, &session).expect("current").shared_time,
                    None,
                    "stale and future receipts cannot stand in for the committed period"
                );
            }
            client.aid[0].food.as_mut().expect("food offer").time = None;
            assert_eq!(
                resources(&client, &session).expect("current").shared_time,
                None,
                "an absent receipt is unavailable, not zero"
            );
        }
        let (client, session) = admitted_resources(0);
        assert_eq!(
            resources(&client, &session)
                .expect("opening commitments")
                .shared_time,
            None,
            "P0 has no completed-period household receipt"
        );
    }

    #[test]
    fn resource_current_balances_never_fill_history_or_superseded_context() {
        let (client, mut session) = admitted_resources(3);
        session.inspect_tick(2);
        assert!(
            resources(&client, &session).is_none(),
            "current balances cannot fill history"
        );
        let (client, mut session) = admitted_resources(3);
        session.set_perspective(Perspective::PlayerKnowledge);
        assert!(
            resources(&client, &session).is_none(),
            "perspective changes require a fresh admission"
        );
        let (client, mut session) = admitted_resources(3);
        session.world_hash = Some("different world".into());
        assert!(
            resources(&client, &session).is_none(),
            "world identity changes require a fresh admission"
        );
    }

    fn install_aid(client: &mut OrganizerClient) {
        view_mut(client).aid_partners.push(
            babylon_persistence::runtime_session::OrganizerKnownAidPartner {
                kind: OrganizerAidKind::Local,
                actor_id: 95,
                label: "Recipient collective".into(),
            },
        );
        view_mut(client).aid_options.push(OrganizerAidOption {
            kind: OrganizerAidKind::Local,
            partner_actor_id: 95,
            partner_label: "Recipient collective".into(),
            coordination_hours: 3,
            receiving_consent: OrganizerGiftConsent::Accept,
        });
        client.aid.push(OrganizerMaterialAidPreview {
            initial_food_quantity: 1,
            initial_cash_micros: 0,
            cash_receiving_consent:
                babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
            kind: OrganizerAidKind::Local,
            mandate_id: [4; 32],
            period: 3,
            donor_id: [5; 32],
            recipient_actor_id: 95,
            good_id: [7; 32],
            unit_id: [8; 32],
            food: Some(
                babylon_persistence::runtime_session::OrganizerAidFoodPreview {
                    donor_stock: 12,
                    own_need: 4,
                    grams_per_unit: 1000,
                    ordinary_offer: None,
                    labor_unit_id: [9; 32],
                    fulfillment_hours_per_unit: 2,
                    time: None,
                    transport: OrganizerAidTransportPreview::Local,
                },
            ),
            funding: OrganizerAidFunding::Organization { cash_micros: 120 },
            maximum_cash_micros: 10,
            maximum_quantity: 8,
            coordination_hours: 3,
            receiving_consent: OrganizerGiftConsent::Accept,
        });
    }

    #[test]
    fn material_terms_distinguish_later_coordination_cash_refusal_and_pending_aid() {
        let (mut client, session) = super::super::tests::ready();
        install_aid(&mut client);
        client.collection = Some(OrganizerCollectionPreview {
            period: 3,
            mandate_id: [8; 32],
            actor_id: 90,
            contributor_id: 101,
            contributor_label: "Captured contributor".into(),
            source_hash: [16; 32],
            cash_consent: OrganizerGiftConsent::Refuse,
            initial_cash_micros: 400_000,
            maximum_cash_micros: 400_000,
            protected_cash_floor_micros: 0,
            collection_hours: 5,
            organization_cash_micros: 1_000_000,
        });
        let cards = comparison(&client, &session).expect("material comparison");
        let collection = cards
            .all_practices
            .iter()
            .find(|row| row.choice == OrganizerChoice::Collect)
            .expect("collection remains reachable even when refused");
        assert_eq!(collection.hours, Some(5));
        assert_eq!(collection.hour_use, HourUse::SharedMaterial);
        assert_eq!(
            collection.availability,
            ChoiceAvailability::Refused(OrganizerRefusal::CollectionCashRefused)
        );
        let aid = cards
            .all_practices
            .iter()
            .find(|row| row.choice == OrganizerChoice::LocalAid)
            .expect("local aid remains reachable");
        assert_eq!(aid.hours, Some(3));
        assert_eq!(aid.hour_use, HourUse::LaterCoordination);
        assert_eq!(
            aid.partner.expect("authenticated recipient").label,
            "Recipient collective"
        );
        assert_eq!(aid.availability, ChoiceAvailability::Reviewable);
        client.pending_aid.push(OrganizerAidPending {
            allocation: babylon_persistence::runtime_session::OrganizerAllocation::Aid {
                food_quantity: 4,
                cash_micros: 18,
            },
            dispatch_support: crate::organizer::tests::aid_dispatch_fixture(),
            response: None,
            lost_quantity: 0,

            kind: OrganizerAidKind::Local,
            original_commitment_id: [10; 32],
            material_commitment_id: [11; 32],
            mandate_id: [4; 32],
            admitted_period: 1,
            dispatch_period: 2,
            good_id: [7; 32],
            unit_id: [8; 32],
        });
        let cards = comparison(&client, &session).expect("pending aid is inspectable");
        assert_eq!(
            cards
                .all_practices
                .iter()
                .find(|row| row.choice == OrganizerChoice::LocalAid)
                .expect("local aid present")
                .availability,
            ChoiceAvailability::PendingAid {
                admitted_period: 1,
                dispatch_period: 2
            }
        );
    }

    #[test]
    fn dispatch_requires_exact_period_receipts_and_dates_delayed_reports_separately() {
        let (mut client, _) = super::super::tests::ready();
        view_mut(&mut client).receipts = vec![receipt(2)];
        view_mut(&mut client).observations = vec![observation(1, 3)];
        let rows = dispatch(&client, 3).expect("viewed dispatch");
        assert_eq!(
            rows.coverage,
            DispatchCoverage::ArchiveRequired,
            "an old receipt cannot become a quiet or current result"
        );
        assert!(rows.current.practices.is_empty());
        assert_eq!(rows.history.practices[0].receipt.period, 2);
        assert_eq!(rows.current.reports[0].observation.observed_period, 1);
        assert_eq!(rows.current.reports[0].observation.acquired_period, 3);
        assert_eq!(
            rows.current.reports[0].destination,
            DispatchDestination::Report([6; 32])
        );
        assert_eq!(
            rows.missing_receipts,
            DispatchDestination::ArchiveOrganization
        );
        view_mut(&mut client).receipts.push(receipt(3));
        let rows = dispatch(&client, 3).expect("included receipt");
        assert_eq!(rows.coverage, DispatchCoverage::Included);
        assert_eq!(rows.current.practices[0].receipt.period, 3);
        assert_eq!(
            rows.current.practices[0]
                .partner
                .expect("known partner")
                .subject,
            Some(OrganizerSubject::WorkplaceCommittee(92))
        );
        assert_eq!(
            dispatch(&client, 2)
                .expect("held period")
                .current
                .reports
                .len(),
            0,
            "a report acquired later cannot leak into history"
        );
    }

    #[test]
    fn dispatch_excludes_foreign_and_future_rows_and_keeps_prior_pd_in_dated_history() {
        let (mut client, _) = super::super::tests::ready();
        view_mut(&mut client).receipts = vec![receipt(2), receipt(3), receipt(4)];
        let mut foreign = receipt(3);
        foreign.actor_id = 999;
        view_mut(&mut client).receipts.push(foreign);
        view_mut(&mut client).observations =
            vec![observation(2, 2), observation(4, 3), observation(2, 4)];
        let mut foreign = observation(2, 3);
        foreign.actor_id = 999;
        view_mut(&mut client).observations.push(foreign);
        let mut unrelated = observation(2, 3);
        unrelated.subject_id = 999;
        view_mut(&mut client).observations.push(unrelated);
        let mut old = super::super::tests::encounter_fixture();
        let mut current = old.clone();
        current.resolve_period = 3;
        current.receipt_id = [8; 32];
        let mut foreign = current.clone();
        foreign.controlled_actor_id = 999;
        client.city_pd_encounters = vec![old.clone(), current, foreign];
        let rows = dispatch(&client, 3).expect("dispatch");
        assert_eq!(rows.current.practices.len(), 1);
        assert_eq!(rows.current.reports.len(), 0);
        assert_eq!(rows.history.reports.len(), 1);
        assert_eq!(rows.current.encounters.len(), 1);
        assert_eq!(rows.history.encounters.len(), 1);
        assert_eq!(rows.history.encounters[0].encounter.resolve_period, 2);
        assert_eq!(
            rows.current.encounters[0].destination,
            DispatchDestination::ArchiveWorkplace
        );
        old.authority_id = [9; 16];
        client.city_pd_encounters = vec![old];
        assert!(
            dispatch(&client, 3)
                .expect("dispatch")
                .history
                .encounters
                .is_empty(),
            "undisclosed authority cannot appear even as history"
        );
        assert!(
            dispatch(&client, 4).is_none(),
            "future period is not a dispatch"
        );
        assert_eq!(
            client.choice(),
            OrganizerChoice::Hold,
            "dispatch navigation data never rewrites a draft"
        );
    }

    #[test]
    fn dispatch_joins_actual_partial_collection_without_substituting_foreign_postings() {
        let partial: OrganizerCollectionResolution = serde_json::from_str(include_str!(
            "../../tests/fixtures/organizer_partial_collection.json"
        ))
        .expect("the retained shared-engine close is a typed collection result");
        let (mut client, _) = super::super::tests::ready();
        let period = partial.fact.period;
        view_mut(&mut client).period = period;
        view_mut(&mut client).actor_id = partial.fact.actor_id;
        view_mut(&mut client).receipts = vec![partial.practice.clone()];
        client.collection_resolutions = vec![partial.clone()];
        let rows = dispatch(&client, period).expect("actual collection dispatch");
        assert_eq!(
            rows.current.practices[0].collection,
            Some(&partial),
            "the dispatch must retain exact collected cash and shared-time facts"
        );
        client.collection_resolutions[0].fact.actor_id += 1;
        assert!(
            dispatch(&client, period)
                .expect("dispatch keeps lawful practice")
                .current
                .practices[0]
                .collection
                .is_none(),
            "a foreign material fact cannot fill the authorized receipt"
        );
    }
}
