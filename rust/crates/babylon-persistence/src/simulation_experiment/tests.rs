use super::*;
use crate::sector_bundle::{michigan_sector_bundles, SectorBundle};

pub(super) fn spec(profile: ExperimentProfile) -> SimulationExperimentV1 {
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
fn closed_inputs_refuse_unknown_fields_dates_horizons_and_cross_profile_interventions() {
    for profile in [
        ExperimentProfile::DeliveryStock,
        ExperimentProfile::Sustained,
        ExperimentProfile::Depletion,
        ExperimentProfile::HistoricalEmployment,
        ExperimentProfile::HistoricalFreight,
    ] {
        let input = spec(profile);
        assert_eq!(
            SimulationExperimentV1::parse(&input.canonical_bytes().unwrap()).unwrap(),
            input
        );
        let mut bad = input.clone();
        bad.horizon += 1;
        assert_eq!(bad.validate(), Err(ExperimentError::Horizon));
        let mut value = serde_json::to_value(input).unwrap();
        value["arbitrary_override"] = serde_json::json!(42);
        assert_eq!(
            SimulationExperimentV1::parse(&serde_json::to_vec(&value).unwrap()),
            Err(ExperimentError::Input)
        );
    }
    let mut bad = spec(ExperimentProfile::HistoricalFreight);
    bad.epoch = Some("2019-01-01".to_owned());
    assert_eq!(bad.validate(), Err(ExperimentError::Epoch));
    let mut bad = spec(ExperimentProfile::Depletion);
    bad.interventions
        .push(ExperimentIntervention::TransportCapacityPermille { permille: 500 });
    assert_eq!(bad.validate(), Err(ExperimentError::Intervention));
    let mut bad = spec(ExperimentProfile::HistoricalEmployment);
    bad.interventions
        .push(ExperimentIntervention::OpeningSheetStock { kilograms: 10 });
    assert_eq!(bad.validate(), Err(ExperimentError::Intervention));
}
#[test]
fn player_horizon_stays_bounded_and_diagnostic_bundle_codec_captures_its_horizon() {
    let source = include_str!("../../../../../content/scenarios/michigan/defines.toml");
    assert!(
        crate::michigan_material::MichiganMaterialCatalog::from_defines_toml(
            &source.replace("HORIZON_PERIODS = 16", "HORIZON_PERIODS = 130")
        )
        .is_err()
    );
    let catalog = spec(ExperimentProfile::Sustained)
        .regional_catalog()
        .unwrap();
    assert_eq!(catalog.horizon_ticks(), 130);
    let captured: serde_json::Value = serde_json::from_slice(catalog.defines_bytes()).unwrap();
    assert_eq!(captured["defines"]["HORIZON_PERIODS"], 130);
    assert!(
        crate::michigan_content::MichiganContentPreset::FourWeekStandard
            .create_foundation(&catalog)
            .is_err()
    );
    for bundle in michigan_sector_bundles(&catalog).unwrap() {
        assert_eq!(bundle.horizon_ticks(), 130);
        assert_eq!(
            SectorBundle::decode(bundle.canonical_bytes(), bundle.sha256()).unwrap(),
            bundle
        );
        assert!(bundle
            .material_rows()
            .capacities
            .iter()
            .any(|r| r.period == 130));
        assert!(!bundle
            .material_rows()
            .capacities
            .iter()
            .any(|r| r.period > 130));
    }
}
#[test]
fn historical_jobs_initialize_only_the_named_five_workforce_accounts() {
    let input = spec(ExperimentProfile::HistoricalEmployment);
    let catalog = input.regional_catalog().unwrap();
    assert!(!catalog.graph_scenario_source().contains("qcew"));
    for (key, jobs, hours) in [
        ("sheet-rolling", 4464, 100),
        ("panel-forming", 8143, 20),
        ("subassembly-making", 17378, 40),
        ("meal-milling", 615, 10),
        ("meal-packaging", 2911, 20),
    ] {
        let pool = catalog
            .staffing()
            .pools
            .iter()
            .find(|p| p.key == key)
            .unwrap();
        assert_eq!(pool.employed, jobs);
        assert_eq!(pool.reserve, 0);
        let process = catalog.processes().iter().find(|p| p.key == key).unwrap();
        assert_eq!(process.capacity_batches_per_period, (jobs * 40 / hours) * 4);
        assert_eq!(
            process.opening_planned_batches,
            process.capacity_batches_per_period
        );
    }
    let f = input.create_foundation().unwrap();
    assert_eq!(
        f.reconstruct_captured().unwrap().canonical_bytes(),
        f.canonical_bytes()
    );
    let mut changed = input;
    changed.seed = 320;
    assert_ne!(changed.create_foundation().unwrap().digest(), f.digest());
}
#[test]
fn freight_is_a_real_foreign_inventory_boundary_with_bound_orders_and_no_county_claim() {
    let input = spec(ExperimentProfile::HistoricalFreight);
    let f = input.create_foundation().unwrap();
    let state = f.initial_register().state();
    assert!(state.process_outputs.is_empty());
    assert!(f.labor().bindings().is_empty());
    assert_eq!(state.orders.len(), 1);
    assert_eq!(state.orders[0].ordered, 8_545_260_204);
    assert_eq!(
        state.inventory.iter().map(|r| r.quantity).sum::<u64>(),
        8_654_814_822
    );
    assert_eq!(
        state.corridor_capacities[0].available_grams,
        109_554_618_000
    );
    let scenario = std::str::from_utf8(
        f.graph_foundation()
            .content_bundle()
            .scenario_source_bytes(),
    )
    .unwrap();
    assert!(scenario.contains("canadian-inventory-boundary"));
    assert!(scenario.contains("detroit-port-3801-entry"));
    assert!(!scenario.contains("county"));
    assert_eq!(f.reconstruct_captured().unwrap().digest(), f.digest());
    let mut contaminated = state.clone();
    contaminated
        .labor
        .push(babylon_material_circuit::LaborCapacityRow {
            site_id: state.inventory[0].site_id,
            unit_id: state.inventory[0].unit_id,
            period: 1,
            available: 1,
        });
    assert!(
        babylon_tick::material_staffing::StaffingComposition::inventory_only(&contaminated)
            .is_err()
    );
}
#[test]
fn gregorian_reporting_crosses_leap_days_and_years() {
    assert_eq!(report::date_after("2019-12-31", 60).unwrap(), "2020-02-29");
    assert_eq!(report::date_after("2020-02-29", 1).unwrap(), "2020-03-01");
    assert_eq!(
        report::date_after("2010-01-01", 131 * 28).unwrap(),
        "2020-01-17"
    );
    assert!(report::date_after("2019-02-29", 1).is_err());
}
