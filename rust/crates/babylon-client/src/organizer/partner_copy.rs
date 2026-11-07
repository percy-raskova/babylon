//! Game copy for the earned, named topics in a partner observation.
use crate::human_numbers;
use crate::observer_ui;
use babylon_persistence::runtime_session::{
    OrganizerObservation, OrganizerPartnerFacts, OrganizerReport, OrganizerReportCommodity,
    OrganizerView,
};

pub(super) fn comparable(left: &OrganizerPartnerFacts, right: &OrganizerPartnerFacts) -> bool {
    use OrganizerPartnerFacts::{
        EssentialServices, FoodProvision, OpeningAssessment, ParticipationTime,
    };
    let same = |a: &OrganizerReportCommodity, b: &OrganizerReportCommodity| {
        a.good_id == b.good_id && a.unit_id == b.unit_id
    };
    match (left, right) {
        (OpeningAssessment { commodity: a, .. }, OpeningAssessment { commodity: b, .. })
        | (FoodProvision { commodity: a, .. }, FoodProvision { commodity: b, .. }) => same(a, b),
        (EssentialServices { services: a }, EssentialServices { services: b }) => {
            a.len() == b.len()
                && a.iter()
                    .zip(b)
                    .all(|(a, b)| same(&a.commodity, &b.commodity))
        }
        (ParticipationTime { labor_unit: a, .. }, ParticipationTime { labor_unit: b, .. }) => {
            a == b
        }
        _ => false,
    }
}

pub(super) fn prior<'a>(
    view: &'a OrganizerView,
    item: &OrganizerObservation,
    current_period: u64,
    facts: &OrganizerPartnerFacts,
) -> Option<(&'a OrganizerObservation, &'a OrganizerPartnerFacts)> {
    super::developments::earlier(view, item, current_period)
        .filter_map(|r| match &r.report {
            OrganizerReport::Partner {
                facts: previous, ..
            } if comparable(previous, facts) => Some((r, previous)),
            _ => None,
        })
        .max_by_key(|(r, _)| (r.observed_period, r.acquired_period, r.observation_id))
}

pub(super) fn headline(facts: &OrganizerPartnerFacts) -> String {
    match facts {
        OrganizerPartnerFacts::OpeningAssessment {
            opening_stock,
            required,
            ..
        } => format!(
            "Opening pantry: {} parcels on hand, {} required",
            observer_ui::grouped(*opening_stock),
            observer_ui::grouped(*required)
        ),
        OrganizerPartnerFacts::FoodProvision {
            consumed, required, ..
        } => format!(
            "Food consumed: {} of {} parcels required",
            observer_ui::grouped(*consumed),
            observer_ui::grouped(*required)
        ),
        OrganizerPartnerFacts::EssentialServices { services } => services.first().map_or_else(
            || "Shared service requirements".to_owned(),
            |s| {
                format!(
                    "{}: {} {} unmet",
                    s.commodity.label,
                    observer_ui::grouped(s.unmet),
                    s.commodity.unit_label
                )
            },
        ),
        OrganizerPartnerFacts::ParticipationTime { remaining, .. } => {
            format!(
                "{} household hours remained at close",
                observer_ui::grouped(*remaining)
            )
        }
    }
}

pub(super) fn detail(facts: &OrganizerPartnerFacts) -> String {
    use OrganizerPartnerFacts::{
        EssentialServices, FoodProvision, OpeningAssessment, ParticipationTime,
    };
    match facts {
        OpeningAssessment { commodity, required, opening_stock } => format!(
            "Opening food assessment. {} {} on hand. Current requirement {}.",
            observer_ui::grouped(*opening_stock),commodity.unit_label,observer_ui::grouped(*required)
        ),
        FoodProvision { commodity,required,consumed,unmet,closing,purchased,settled_micros } => format!(
            "Food provision · {} {} unmet. Consumed {} of {} required; {} in closing stock. Ordinary purchases: {} parcels, {} settled.",
            observer_ui::grouped(*unmet), commodity.unit_label, observer_ui::grouped(*consumed),
            observer_ui::grouped(*required),observer_ui::grouped(*closing),observer_ui::grouped(*purchased),
            human_numbers::currency(*settled_micros)
        ),
        EssentialServices { services } => services.iter().map(|service| format!(
            "{} · {} {} unmet. Required {}, performed {}, satisfied {}, unused {}, expired {}. Settled {}, refunded {}.",
            service.commodity.label,observer_ui::grouped(service.unmet),service.commodity.unit_label,
            observer_ui::grouped(service.required),observer_ui::grouped(service.performed),observer_ui::grouped(service.satisfied),
            observer_ui::grouped(service.unused),observer_ui::grouped(service.expired),
            human_numbers::currency(service.settled_micros),human_numbers::currency(service.refunded_micros)
        )).collect::<Vec<_>>().join("\n"),
        ParticipationTime { attended,protected,unpaid,contributed,remaining,.. } => format!(
            "Completed participation time · {} household hours remaining. Attended {}, protected {}, unpaid work {}, contributions {}.",
            observer_ui::grouped(*remaining),observer_ui::grouped(*attended),observer_ui::grouped(*protected),
            observer_ui::grouped(*unpaid),observer_ui::grouped(*contributed)
        ),
    }
}
