use super::super::{ExperimentError, StaffingEvidence};
use super::manifest::{count, WiringManifest};
use super::{manifest, tests};
use crate::simulation_experiment::tests::spec;
use crate::simulation_experiment::ExperimentProfile;
use babylon_bsl::causal_contract::{EffectSignature, EvidenceClass};
use babylon_tick::material_staffing::STAFFING_FIELDS;
use babylon_tick::material_world::MaterialTickReceipts;
use babylon_tick::TickReport;

use babylon_tick::material_world;

fn first_period(
    profile: ExperimentProfile,
) -> (
    WiringManifest,
    TickReport,
    MaterialTickReceipts,
    Vec<StaffingEvidence>,
) {
    let foundation = tests::spec(profile)
        .create_foundation()
        .expect("the authored catalog builds the foundation");
    let manifest = manifest::capture(&foundation).expect("the fixture captures the authored state");
    let session = foundation
        .reconstruct_captured()
        .expect("the fixture call `reconstruct_captured` succeeds for the authored inputs")
        .into_session()
        .expect("the fixture opens a session");
    let candidate = super::super::prepare(&session)
        .expect("the fixture call `prepare` succeeds for the authored inputs");
    let report = candidate.graph_report().report();
    let copied_report = TickReport {
        before: report.before,
        after: report.after,
        world_before: report.world_before,
        world_after: report.world_after,
        considered: report.considered,
        fired: report.fired,
        per_rule_considered: report.per_rule_considered.clone(),
        per_rule_fired: report.per_rule_fired.clone(),
        audit_receipts: report.audit_receipts.clone(),
        choice_receipts: report.choice_receipts.clone(),
        committed_events: report.committed_events.clone(),
    };
    (
        manifest,
        copied_report,
        material_world::decode_material_receipts(candidate.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type"),
        super::super::staffing(&candidate)
            .expect("the fixture call `staffing` succeeds for the authored inputs"),
    )
}

#[test]
fn counted_firing_without_material_effect_is_not_successful_execution() {
    let (manifest, mut report, receipts, staffing) = first_period(ExperimentProfile::DeliveryStock);
    assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_ok());
    report
        .audit_receipts
        .retain(|receipt| receipt.effect != EffectSignature::MaterialCycle);
    assert_eq!(
        manifest::verify(&manifest, &report, &receipts, &staffing),
        Err(ExperimentError::Incomplete)
    );
}

#[test]
fn coverage_refuses_misattributed_duplicate_and_unselected_effects() {
    let (manifest, mut report, receipts, staffing) = first_period(ExperimentProfile::DeliveryStock);
    let original = report.audit_receipts.clone();
    let material = original
        .iter()
        .position(|r| r.effect == EffectSignature::MaterialCycle)
        .expect("the fixture sequence holds the addressed position");
    report.audit_receipts[material].evidence = EvidenceClass::Observed;
    assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_err());
    report.audit_receipts = original.clone();
    report.audit_receipts.push(original[material].clone());
    assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_err());
    report.audit_receipts = original.clone();
    report.audit_receipts[material].rule_id = "unselected/effect".to_owned();
    assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_err());
    report.audit_receipts = original;
    report
        .audit_receipts
        .retain(|r| r.effect != EffectSignature::NodeField(STAFFING_FIELDS[0].to_owned()));
    assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_err());
}

#[test]
fn coverage_matches_captured_subjects_and_native_family_selection() {
    let (manifest, report, receipts, mut staffing) = first_period(ExperimentProfile::DeliveryStock);
    let (coverage, execution) = manifest::verify(&manifest, &report, &receipts, &staffing)
        .expect("the fixture call `verify` succeeds for the authored inputs");
    assert_eq!(execution.len(), manifest.rules.len());
    assert_eq!(
        coverage.staffing_events,
        count(manifest.staffing_subjects.len())
            .expect("the fixture call `count` succeeds for the authored inputs")
    );
    assert_eq!(
        coverage.staffing_writes,
        coverage.staffing_events
            * count(STAFFING_FIELDS.len())
                .expect("the fixture call `count` succeeds for the authored inputs")
    );
    staffing[0].subject = "unselected-workforce".to_owned();
    assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_err());
    let (mut manifest, report, receipts, staffing) = first_period(ExperimentProfile::DeliveryStock);
    let family = manifest
        .material_families
        .iter_mut()
        .find(|family| family.family == "production")
        .expect("the fixture holds the searched element");
    family.selected = false;
    family.captured_rows = 0;
    assert_ne!(receipts.production.len(), 0);
    assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_err());
}

#[test]
fn captured_selection_and_real_first_period_cover_each_admitted_profile() {
    for profile in [
        ExperimentProfile::DeliveryStock,
        ExperimentProfile::Sustained,
        ExperimentProfile::Depletion,
        ExperimentProfile::HistoricalEmployment,
        ExperimentProfile::HistoricalFreight,
    ] {
        let foundation = tests::spec(profile)
            .create_foundation()
            .expect("the authored catalog builds the foundation");
        let (manifest, report, receipts, staffing) = first_period(profile);
        assert_eq!(
            manifest.staffing_subjects.len(),
            foundation.labor().bindings().len()
        );
        assert_eq!(
            manifest
                .material_families
                .iter()
                .find(|r| r.family == "production")
                .expect("the fixture holds the searched element")
                .captured_rows,
            count(foundation.material_catalog().process_outputs.len())
                .expect("the fixture call `count` succeeds for the authored inputs")
        );
        assert!(manifest
            .material_families
            .iter()
            .all(|r| r.selected == (r.captured_rows > 0)));
        assert!(manifest
            .bsl_families
            .iter()
            .all(|r| r.selected != r.rule_ids.is_empty()));
        assert_eq!(
            manifest
                .bsl_families
                .iter()
                .find(|r| r.family == "metabolism")
                .expect("the fixture holds the searched element")
                .rule_ids
                .len(),
            0
        );
        assert_eq!(
            manifest.native_compositions.is_empty(),
            foundation.labor().bindings().is_empty()
        );
        assert!(manifest::verify(&manifest, &report, &receipts, &staffing).is_ok());
    }
}
