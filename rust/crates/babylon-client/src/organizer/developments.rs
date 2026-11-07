//! Dated changes that can interrupt Play, derived from the admitted sender and report views.
use super::presentation;
use babylon_persistence::runtime_session::{
    OrganizerAidResolution, OrganizerAllocation, OrganizerCollectionResolution,
    OrganizerFoodDelivery, OrganizerObservation, OrganizerOutcome, OrganizerPartnerFacts,
    OrganizerReport, OrganizerReportCommodity, OrganizerView,
};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum Notice {
    Collection([u8; 32]),
    Dispatch([u8; 32]),
    Delivery([u8; 32]),
    Loss([u8; 32]),
    Response([u8; 32], [u8; 32]),
    Terminal([u8; 32]),
    Need([u8; 32], [u8; 32], [u8; 32]),
}

#[derive(Default)]
pub(super) struct Developments {
    live_period: Option<u64>,
    seen: BTreeSet<Notice>,
}
impl Developments {
    pub(super) fn install(
        &mut self,
        view: &OrganizerView,
        collections: &[OrganizerCollectionResolution],
        resolutions: &[OrganizerAidResolution],
    ) -> Option<String> {
        let period = view.period;
        if self.live_period.is_some_and(|p| p > period) {
            return None;
        }
        let opening = self.live_period.is_none();
        if self.live_period != Some(period) {
            self.seen.clear();
            self.live_period = Some(period);
        }
        let mut changes = Vec::new();
        for row in collections {
            if row.fact.period == period && row.practice.actor_id == view.actor_id {
                changes.push((
                    Notice::Collection(row.practice.receipt_id),
                    presentation::collection_result(row),
                ));
            }
        }
        for row in resolutions {
            support_changes(&mut changes, row, period);
        }
        for r in view.observations.iter().filter(|r| {
            r.actor_id == view.actor_id
                && view.knows_report_subject(r)
                && r.observed_period == period
                && r.acquired_period == period
        }) {
            shortfalls(view, r, &mut changes);
        }
        let mut fresh = Vec::new();
        for (id, message) in changes {
            if self.seen.insert(id) && !opening {
                fresh.push(message);
            }
        }
        (!fresh.is_empty()).then(|| fresh.join(" · "))
    }
}

pub(super) fn dispatch_line(row: &OrganizerAidResolution) -> String {
    let transfer = &row.pending.dispatch_support;
    let postings = &transfer.material_postings;
    let OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = row.pending.allocation
    else {
        return "Original aid request unavailable.".into();
    };
    let mut remainder = String::new();
    if postings.payer_cash_granted_micros > 0 && postings.payer_cash_granted_micros < cash_micros {
        remainder.push_str(" Partial cash settlement. The remainder closes unpaid.");
    }
    if postings.dispatched_quantity > 0 && postings.dispatched_quantity < food_quantity {
        remainder.push_str(" Partial food dispatch. The rest will not be retried.");
    }
    format!("P{} request: {} food parcels and {}. P{} dispatch: {} parcels, {} household hours; cash {} ({}).{remainder}",
        row.pending.admitted_period,food_quantity,crate::human_numbers::currency(cash_micros),transfer.dispatch_period,postings.dispatched_quantity,postings.fulfillment_hours,crate::human_numbers::currency(postings.payer_cash_granted_micros),transfer.cash_status.label())
}

pub(super) fn response_line(row: &OrganizerAidResolution) -> Option<String> {
    let response = row.pending.response.as_ref().or_else(|| {
        matches!(
            row.practice.outcome,
            OrganizerOutcome::AidPracticeCompleted
                | OrganizerOutcome::AidPracticeUncompleted
                | OrganizerOutcome::InsufficientTime
        )
        .then_some(&row.practice)
    })?;
    Some(format!(
        "P{} partner response: {}. {} coordination hours used.",
        response.period,
        presentation::response(response.partner_response),
        response.hours_spent
    ))
}

fn support_changes(out: &mut Vec<(Notice, String)>, row: &OrganizerAidResolution, period: u64) {
    let s = &row.support;
    if s.period != period {
        return;
    }
    let original = row.pending.original_commitment_id;
    if s.dispatch_period == period {
        out.push((Notice::Dispatch(original), dispatch_line(row)));
    }
    if s.material_postings.lost_quantity > 0 {
        out.push((
            Notice::Loss(original),
            format!(
                "{} food parcels lost in P{period}.",
                s.material_postings.lost_quantity
            ),
        ));
    }
    let physical = match s.status {
        OrganizerFoodDelivery::Granted { granted_quantity } => Some(format!(
            "{granted_quantity} food parcels granted in P{period}."
        )),
        OrganizerFoodDelivery::ReceivingRefused => {
            Some(format!("Food receiving refused in P{period}."))
        }
        OrganizerFoodDelivery::TerminalFailure => {
            Some(format!("Food delivery ended without a grant in P{period}."))
        }
        OrganizerFoodDelivery::AwaitingDelivery | OrganizerFoodDelivery::NotRequested => None,
    };
    if let Some(line) = physical {
        out.push((Notice::Delivery(original), line));
    }
    if let Some(first) = row.pending.response.as_ref().filter(|r| r.period == period) {
        if let Some(line) = response_line(row) {
            out.push((Notice::Response(original, first.receipt_id), line));
        }
    } else if row.practice.period == period
        && matches!(
            row.practice.outcome,
            OrganizerOutcome::AidPracticeCompleted
                | OrganizerOutcome::AidPracticeUncompleted
                | OrganizerOutcome::InsufficientTime
        )
    {
        if let Some(line) = response_line(row) {
            out.push((Notice::Response(original, row.practice.receipt_id), line));
        }
    }
    if row.practice.outcome == OrganizerOutcome::NoQualifyingSupport {
        out.push((
            Notice::Terminal(original),
            "No qualifying support. No coordination time used.".into(),
        ));
    }
}

pub(super) fn current_support(rows: &[OrganizerAidResolution], period: u64) -> String {
    let mut changes = Vec::new();
    for row in rows {
        support_changes(&mut changes, row, period);
    }
    changes
        .into_iter()
        .map(|(_, line)| line)
        .collect::<Vec<_>>()
        .join("\n")
}

pub(super) fn earlier<'a>(
    view: &'a OrganizerView,
    current: &OrganizerObservation,
    period: u64,
) -> impl Iterator<Item = &'a OrganizerObservation> {
    let (reader, subject, source, observed) = (
        view.actor_id,
        current.subject_id,
        current.source_actor_id,
        current.observed_period,
    );
    view.observations.iter().filter(move |r| {
        r.actor_id == reader
            && r.subject_id == subject
            && r.source_actor_id == source
            && r.observed_period < observed
            && r.acquired_period <= period
    })
}

fn shortfalls(view: &OrganizerView, row: &OrganizerObservation, out: &mut Vec<(Notice, String)>) {
    let OrganizerReport::Partner { facts, .. } = &row.report else {
        return;
    };
    let measure = |commodity: &OrganizerReportCommodity,
                   unmet: u64,
                   service: bool,
                   out: &mut Vec<(Notice, String)>| {
        let prior = earlier(view, row, row.acquired_period)
            .filter_map(|r| {
                let OrganizerReport::Partner { facts: before, .. } = &r.report else {
                    return None;
                };
                let same = |c: &OrganizerReportCommodity| {
                    c.good_id == commodity.good_id && c.unit_id == commodity.unit_id
                };
                let value = match before {
                    OrganizerPartnerFacts::FoodProvision {
                        commodity: c,
                        unmet,
                        ..
                    } if !service && same(c) => *unmet,
                    OrganizerPartnerFacts::EssentialServices { services } if service => {
                        services.iter().find(|r| same(&r.commodity))?.unmet
                    }
                    _ => return None,
                };
                Some((
                    (r.observed_period, r.acquired_period, r.observation_id),
                    value,
                ))
            })
            .max_by_key(|(key, _)| *key)
            .map(|(_, v)| v);
        if prior.map_or(unmet > 0, |v| v != unmet) {
            out.push((
                Notice::Need(row.observation_id, commodity.good_id, commodity.unit_id),
                format!(
                    "{} reports {}: {} {} unmet in P{}.",
                    presentation::partner(view, row.source_actor_id),
                    commodity.label,
                    unmet,
                    commodity.unit_label,
                    row.observed_period
                ),
            ));
        }
    };
    match facts {
        OrganizerPartnerFacts::FoodProvision {
            commodity, unmet, ..
        } => measure(commodity, *unmet, false, out),
        OrganizerPartnerFacts::EssentialServices { services } => {
            for s in services {
                measure(&s.commodity, s.unmet, true, out);
            }
        }
        _ => {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::runtime_session::{OrganizerCollectionResolution, OrganizerSnapshot};
    use serde::Deserialize;

    #[derive(Deserialize)]
    struct Period {
        view: OrganizerView,
        collection_resolutions: Vec<OrganizerCollectionResolution>,
        aid_resolutions: Vec<OrganizerAidResolution>,
    }
    impl Period {
        fn install(&self, changes: &mut Developments) -> Option<String> {
            changes.install(
                &self.view,
                &self.collection_resolutions,
                &self.aid_resolutions,
            )
        }
    }
    #[test]
    fn actual_national_cash_service_and_unchanged_food_notices_follow_their_own_dates() {
        let periods: Vec<Period> = serde_json::from_str(include_str!(
            "../../tests/fixtures/wayne_public_developments_v18.json"
        ))
        .expect("funded national witness");
        let opening: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../../../babylon-persistence/tests/fixtures/national_organizer_opening_v18.json"
        ))
        .expect("national opening");
        let mut changes = Developments::default();
        assert_eq!(
            changes.install(
                &opening.view,
                &opening.collection_resolutions,
                &opening.aid_resolutions
            ),
            None
        );
        let p1 = periods[0]
            .install(&mut changes)
            .expect("first disclosed completed shortfalls, collection");
        assert!(p1.contains("unmet") && p1.contains("$1,450.00"), "{p1}");
        let p2 = periods[1]
            .install(&mut changes)
            .expect("actual cash and response");
        assert!(
            p2.contains("$1,450.00") && p2.contains("P2 partner response"),
            "{p2}"
        );
        assert!(
            !p2.contains("unmet"),
            "unchanged dated reports are quiet: {p2}"
        );
        assert_eq!(periods[1].install(&mut changes), None);
        let p3 = periods[2]
            .install(&mut changes)
            .expect("two changed service shortfalls");
        assert_eq!(p3.matches("unmet").count(), 2, "{p3}");
        assert!(
            !p3.contains("food") && !p3.contains("response") && !p3.contains("purchases"),
            "{p3}"
        );
        assert_eq!(
            periods[0].install(&mut changes),
            None,
            "historical navigation"
        );
        assert_eq!(periods[2].install(&mut changes), None, "Return Live");
        assert_eq!(
            periods[2].install(&mut Developments::default()),
            None,
            "cold open seeds existing results"
        );
    }
}
