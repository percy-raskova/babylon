use super::*;
use crate::simulation_experiment::{tests::spec, ExperimentProfile};
use babylon_tick::material_world::decode_material_receipts;

fn first_period(
    profile: ExperimentProfile,
) -> (
    WiringManifest,
    TickReport,
    MaterialTickReceipts,
    Vec<StaffingEvidence>,
) {
    let foundation = spec(profile).create_foundation().unwrap();
    let manifest = capture(&foundation).unwrap();
    let session = foundation
        .reconstruct_captured()
        .unwrap()
        .into_session()
        .unwrap();
    let candidate = super::super::prepare(&session).unwrap();
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
        decode_material_receipts(candidate.material().receipt_bytes()).unwrap(),
        super::super::staffing(&candidate).unwrap(),
    )
}

#[test]
fn counted_firing_without_material_effect_is_not_successful_execution() {
    let (manifest, mut report, receipts, staffing) = first_period(ExperimentProfile::DeliveryStock);
    assert!(verify(&manifest, &report, &receipts, &staffing).is_ok());
    report
        .audit_receipts
        .retain(|receipt| receipt.effect != EffectSignature::MaterialCycle);
    assert_eq!(
        verify(&manifest, &report, &receipts, &staffing),
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
        .unwrap();
    report.audit_receipts[material].evidence = EvidenceClass::Observed;
    assert!(verify(&manifest, &report, &receipts, &staffing).is_err());
    report.audit_receipts = original.clone();
    report.audit_receipts.push(original[material].clone());
    assert!(verify(&manifest, &report, &receipts, &staffing).is_err());
    report.audit_receipts = original.clone();
    report.audit_receipts[material].rule_id = "unselected/effect".to_owned();
    assert!(verify(&manifest, &report, &receipts, &staffing).is_err());
    report.audit_receipts = original;
    report
        .audit_receipts
        .retain(|r| r.effect != EffectSignature::NodeField(STAFFING_FIELDS[0].to_owned()));
    assert!(verify(&manifest, &report, &receipts, &staffing).is_err());
}

#[test]
fn coverage_matches_captured_subjects_and_native_family_selection() {
    let (manifest, report, receipts, mut staffing) = first_period(ExperimentProfile::DeliveryStock);
    let (coverage, execution) = verify(&manifest, &report, &receipts, &staffing).unwrap();
    assert_eq!(execution.len(), manifest.rules.len());
    assert_eq!(
        coverage.staffing_events,
        count(manifest.staffing_subjects.len()).unwrap()
    );
    assert_eq!(
        coverage.staffing_writes,
        coverage.staffing_events * count(STAFFING_FIELDS.len()).unwrap()
    );
    staffing[0].subject = "unselected-workforce".to_owned();
    assert!(verify(&manifest, &report, &receipts, &staffing).is_err());
    let (mut manifest, report, receipts, staffing) = first_period(ExperimentProfile::DeliveryStock);
    let family = manifest
        .material_families
        .iter_mut()
        .find(|family| family.family == "production")
        .unwrap();
    family.selected = false;
    family.captured_rows = 0;
    assert!(!receipts.production.is_empty());
    assert!(verify(&manifest, &report, &receipts, &staffing).is_err());
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
        let foundation = spec(profile).create_foundation().unwrap();
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
                .unwrap()
                .captured_rows,
            count(foundation.initial_register().state().process_outputs.len()).unwrap()
        );
        assert!(manifest
            .material_families
            .iter()
            .all(|r| r.selected == (r.captured_rows > 0)));
        assert!(manifest
            .bsl_families
            .iter()
            .all(|r| r.selected != r.rule_ids.is_empty()));
        assert!(manifest
            .bsl_families
            .iter()
            .find(|r| r.family == "metabolism")
            .unwrap()
            .rule_ids
            .is_empty());
        assert_eq!(
            manifest.native_compositions.is_empty(),
            foundation.labor().bindings().is_empty()
        );
        assert!(verify(&manifest, &report, &receipts, &staffing).is_ok());
    }
}
