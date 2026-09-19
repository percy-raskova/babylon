//! Long qualification runs weekly/on demand; ordinary development retains input contracts.
use babylon_kernel::content_digest::sha256_of;
use babylon_persistence::simulation_experiment::{
    report, EmploymentStartingRow, ExperimentProfile, SimulationExperimentV1, StartingSnapshot,
};

fn spec(profile: ExperimentProfile) -> SimulationExperimentV1 {
    let (epoch, starting_snapshot) = match profile {
        ExperimentProfile::HistoricalEmployment => (
            Some("2010-01-01".to_owned()),
            Some(StartingSnapshot::Employment {
                date: "2010-01-01".to_owned(),
                series: [
                    ("26099/332", 8143),
                    ("26125/311", 2911),
                    ("26161/311", 615),
                    ("26163/331", 4464),
                    ("26163/3363", 17378),
                ]
                .into_iter()
                .map(|(id, jobs)| EmploymentStartingRow {
                    series_id: id.to_owned(),
                    jobs,
                })
                .collect(),
            }),
        ),
        ExperimentProfile::HistoricalFreight => (
            Some("2019-02-01".to_owned()),
            Some(StartingSnapshot::Freight {
                date: "2019-01-01".to_owned(),
                series_id: "detroit_canada_truck_import_hs72".to_owned(),
                arrived_kg: 121_292_613,
            }),
        ),
        _ => (None, None),
    };
    SimulationExperimentV1 {
        schema: "SimulationExperimentV1".to_owned(),
        profile,
        epoch,
        horizon: profile.horizon(),
        seed: 319,
        source_snapshot_sha256: starting_snapshot.as_ref().map(|_| "a".repeat(64)),
        starting_snapshot,
        interventions: vec![],
    }
}
#[test]
fn sustained_depletion_and_historical_profiles_close_replay_and_conservation() {
    for profile in [
        ExperimentProfile::Sustained,
        ExperimentProfile::Depletion,
        ExperimentProfile::HistoricalEmployment,
        ExperimentProfile::HistoricalFreight,
    ] {
        let result = report::run(&spec(profile)).unwrap();
        assert_eq!(result.trajectory.completed_periods, profile.horizon());
        assert_eq!(result.trajectory.observed_choice_count, 0);
        assert!(result.captured_setup.checkpoint_restarts > 0);
        assert_eq!(
            sha256_of(&result.captured_defines),
            hex_decode(&result.trajectory.experiment.resolved_inputs_sha256)
        );
        if profile == ExperimentProfile::Sustained {
            assert_eq!(result.captured_setup.final_year_active_periods, 13);
        }
        if profile == ExperimentProfile::HistoricalEmployment {
            assert_eq!(result.trajectory.employment.len(), 5 * 132);
        }
        if profile == ExperimentProfile::HistoricalFreight {
            assert_eq!(result.trajectory.freight.len(), 78);
            assert_eq!(result.trajectory.freight[0].arrived_kg, 0);
            assert_eq!(result.trajectory.freight[1].arrived_kg, 109_554_618);
        }
    }
}
fn hex_decode(s: &str) -> [u8; 32] {
    let mut a = [0; 32];
    for (i, b) in a.iter_mut().enumerate() {
        *b = u8::from_str_radix(&s[i * 2..i * 2 + 2], 16).unwrap();
    }
    a
}
