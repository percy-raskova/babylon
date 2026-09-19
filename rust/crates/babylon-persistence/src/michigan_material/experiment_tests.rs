use super::*;
use crate::simulation_experiment::{ExperimentProfile, SimulationExperimentV1};

fn historical_spec() -> SimulationExperimentV1 {
    SimulationExperimentV1::parse(
        &serde_json::to_vec(&serde_json::json!({
            "schema":"SimulationExperimentV1", "profile":"historical_employment",
            "epoch":"2010-01-01", "horizon":131, "seed":319,
            "source_snapshot_sha256":"a".repeat(64),
            "starting_snapshot":{"kind":"employment", "date":"2010-01-01", "series":[
                {"series_id":"26099/332", "jobs":8143},
                {"series_id":"26125/311", "jobs":2911},
                {"series_id":"26161/311", "jobs":615},
                {"series_id":"26163/331", "jobs":4464},
                {"series_id":"26163/3363", "jobs":17378}
            ]}, "interventions":[]
        }))
        .unwrap(),
    )
    .unwrap()
}

#[test]
fn stored_experiments_refuse_internally_consistent_but_underived_opening_rows() {
    let catalog = historical_spec().regional_catalog().unwrap();
    for mutation in 0..8 {
        let mut capture = catalog.capture.clone();
        match mutation {
            0 => capture.normalized.staffing.pools[0].employed += 1,
            1 => capture.normalized.staffing.pools[0].reserve = 1,
            2 => capture.normalized.processes[0].capacity_batches_per_period += 1,
            3 => capture.normalized.processes[0].opening_planned_batches -= 1,
            4 => capture.normalized.processes[0].inputs[0].opening_quantity -= 1,
            5 => capture.normalized.routes[0].ordered_quantity -= 1,
            6 => capture.normalized.corridors[0].capacity_grams_per_period -= 1,
            7 => {
                let spec = capture.experiment.as_mut().unwrap();
                let crate::simulation_experiment::StartingSnapshot::Employment { series, .. } =
                    spec.starting_snapshot.as_mut().unwrap()
                else {
                    unreachable!()
                };
                series[0].jobs += 1;
                capture.observed_defines = spec.canonical_bytes().unwrap();
            }
            _ => unreachable!(),
        }
        // Keep the graph and source encoding internally consistent. Rejection
        // must come from the observed-input/derived-row contract itself.
        capture.graph_scenario_source =
            crate::simulation_experiment::regional::scenario(&capture.normalized);
        let bytes = serde_json::to_vec(&capture).unwrap();
        assert!(
            MichiganMaterialCatalog::from_stored_defines(&bytes).is_err(),
            "mutation {mutation}"
        );
    }
}

#[test]
fn stored_experiments_accept_derived_rows_and_joint_admitted_interventions() {
    for profile in [
        ExperimentProfile::DeliveryStock,
        ExperimentProfile::Sustained,
        ExperimentProfile::Depletion,
        ExperimentProfile::HistoricalEmployment,
    ] {
        let mut spec = historical_spec();
        spec.profile = profile;
        spec.horizon = profile.horizon();
        if profile != ExperimentProfile::HistoricalEmployment {
            spec.epoch = None;
            spec.source_snapshot_sha256 = None;
            spec.starting_snapshot = None;
        }
        if matches!(
            profile,
            ExperimentProfile::Sustained | ExperimentProfile::DeliveryStock
        ) {
            spec.interventions = vec![
                crate::simulation_experiment::ExperimentIntervention::TransportCapacityPermille {
                    permille: 500,
                },
                crate::simulation_experiment::ExperimentIntervention::OpeningSheetStock {
                    kilograms: 320,
                },
            ];
        }
        let catalog = spec.regional_catalog().unwrap();
        assert_eq!(
            MichiganMaterialCatalog::from_stored_defines(catalog.defines_bytes()).unwrap(),
            catalog
        );
    }
}
