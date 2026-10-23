use super::*;
use crate::{ArchiveCitation, ArchiveKnowledgeGrant, CountyPagePlan};
use std::cell::RefCell;

fn plan(geoid: &str) -> CountyPagePlan {
    CountyPagePlan::try_new(
        geoid.into(),
        format!("county:{geoid}"),
        format!("County {geoid}"),
        Vec::new(),
        Vec::new(),
    )
    .unwrap()
}

fn knowledge(plans: &[CountyPagePlan]) -> ArchiveKnowledge {
    ArchiveKnowledge::try_new(
        plans
            .iter()
            .map(|plan| {
                ArchiveKnowledgeGrant::try_new(
                    plan.page_ref().unwrap(),
                    "subject".into(),
                    0,
                    ArchiveCitation::try_new("selection-control".into(), "county roster".into())
                        .unwrap(),
                )
                .unwrap()
            })
            .collect(),
    )
    .unwrap()
}

#[test]
fn hidden_plans_are_not_composed_and_known_plans_keep_source_order() {
    let plans = [plan("26163"), plan("26161"), plan("26099")];
    let known = knowledge(&[plans[0].clone(), plans[2].clone()]);
    let receipt = PendingArchiveReceipt::try_new(7, [7; 32]).unwrap();
    let calls = RefCell::new(Vec::new());
    let inputs = known_page_inputs(&receipt, &known, &plans, &|plan, tick, hash| {
        calls.borrow_mut().push(plan.county_geoid().to_owned());
        crate::county_page_input(plan, tick, hash)
    })
    .unwrap();
    assert_eq!(*calls.borrow(), ["26163", "26099"]);
    assert_eq!(inputs.len(), 2);
    for ((plan, input), expected) in inputs.iter().zip(["26163", "26099"]) {
        assert_eq!(plan.county_geoid(), expected);
        assert_eq!(input.subject().page_ref(), &plan.page_ref().unwrap());
        assert_eq!(input.verified_tick(), 7);
        assert_eq!(input.tick_content_hash(), &[7; 32]);
    }
}

#[test]
fn no_subject_grants_require_no_page_construction() {
    let plans = [plan("26163")];
    let known = ArchiveKnowledge::try_new(Vec::new()).unwrap();
    let receipt = PendingArchiveReceipt::try_new(7, [7; 32]).unwrap();
    assert!(known_page_inputs(&receipt, &known, &plans, &|_, _, _| {
        panic!("a hidden page must not be constructed")
    })
    .unwrap()
    .is_empty());
}

#[test]
fn eligible_page_errors_are_not_suppressed() {
    let plans = [plan("26163")];
    let known = knowledge(&plans);
    let receipt = PendingArchiveReceipt::try_new(7, [7; 32]).unwrap();
    assert!(matches!(
        known_page_inputs(&receipt, &known, &plans, &|_, _, _| {
            Err(SemanticArchiveError::InvalidText)
        }),
        Err(SemanticArchiveError::InvalidText)
    ));
}

#[test]
fn eligible_plan_cannot_emit_another_known_or_hidden_subject() {
    let plans = [plan("26163")];
    let known = knowledge(&[plans[0].clone(), plan("26161")]);
    let receipt = PendingArchiveReceipt::try_new(7, [7; 32]).unwrap();
    for other in ["26161", "26099"] {
        assert!(matches!(
            known_page_inputs(&receipt, &known, &plans, &|_, tick, hash| {
                crate::county_page_input(&plan(other), tick, hash)
            }),
            Err(SemanticArchiveError::StoredPageMismatch)
        ));
    }
}
