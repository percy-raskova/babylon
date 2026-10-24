use super::arguments::Inputs;
use super::report::{Candidate, Report};
use super::{arguments, run, synthetic, witness};

use babylon_kernel::content_digest;
use std::collections::BTreeMap;
use synthetic::SyntheticSources;

fn input() -> (Inputs, Candidate) {
    let fixture = synthetic::load();
    let food = fixture.qualification["processes"]
        .as_array()
        .expect("the JSON fixture field is an array")
        .iter()
        .find(|row| row["family"] == "prepared_food")
        .expect("the fixture holds the searched element");
    let candidate = Candidate {
        capacity_key: "synthetic-shared-road".to_owned(),
        food_process: format!(
            "{}-{}-prepared_food",
            food["county_geoid"]
                .as_str()
                .expect("the JSON fixture field is a string"),
            food["sector_code"]
                .as_str()
                .expect("the JSON fixture field is a string")
        ),
        constrained_grams: 1_000,
        shortage_opening: 0,
    };
    let defines = include_str!("../../../../../content/scenarios/michigan/defines.toml").to_owned();
    let qualification = serde_json::to_vec(&fixture.qualification)
        .expect("the value serializes to canonical JSON bytes");
    let physical = serde_json::to_vec(&fixture.physical)
        .expect("the value serializes to canonical JSON bytes");
    let hashes = BTreeMap::from([
        (
            "defines",
            super::hex(&content_digest::sha256_of(defines.as_bytes())),
        ),
        (
            "qualification",
            super::hex(&content_digest::sha256_of(&qualification)),
        ),
        (
            "physical",
            super::hex(&content_digest::sha256_of(&physical)),
        ),
    ]);
    (
        Inputs {
            defines,
            qualification,
            physical: fixture.physical,
            hashes,
        },
        candidate,
    )
}

#[test]
fn synthetic_candidates_require_independent_committed_economic_consequences() {
    let (inputs, candidate) = input();
    let mut report = run::experiment(&inputs, &candidate)
        .expect("the fixture call `experiment` succeeds for the authored inputs");
    assert!(report.qualified, "{:?}", report.witnesses.missing);
    assert_eq!(report.evidence_scope, "synthetic focused test only");
    assert!(!report.persisted);
    assert_eq!(report.cases.len(), 4);
    for case in report.cases.values() {
        assert_eq!(case.periods.len(), 16);
        assert!(case.foundation_bytes > case.captured_bytes);
        assert_eq!(case.captured_content_sha256.len(), 64);
        for period in &case.periods {
            assert_eq!(period.owners.len(), 397);
            assert_eq!(period.processes.len(), 233);
            assert_eq!(period.routes.len(), 579);
            assert_eq!(period.final_demand.len(), 233);
            assert!(
                period.selected_capacity_reserved_grams <= period.selected_capacity_opening_grams
            );
            assert!(period.maximum_family_rows < 65_536);
            assert_eq!(period.world_sha256.len(), 64);
            assert_eq!(period.material_receipts_sha256.len(), 64);
            assert!(period.receipt_bytes > 0);
        }
    }
    let freight = report
        .witnesses
        .freight
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert!(freight.downstream_output.period > freight.dispatch_period);
    assert!(freight.downstream_workforce.period > freight.dispatch_period);
    assert!(!freight.downstream_output.supply_chain_routes.is_empty());
    assert!(!freight.downstream_workforce.supply_chain_routes.is_empty());
    assert_eq!(
        report
            .witnesses
            .packaging
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .process,
        candidate.food_process
    );
    let sources = SyntheticSources::create();
    let destination = sources.path("candidate-report.json");
    arguments::write_report(&destination, &report)
        .expect("the fixture sink accepts the authored bytes");
    let bytes = std::fs::read(&destination).expect("the fixture reader returns its authored facts");
    assert!(bytes.len() <= arguments::MAX_REPORT_BYTES);
    assert!(arguments::write_report(&destination, &report).is_err());
    assert_eq!(
        std::fs::read(&destination).expect("the fixture reader returns its authored facts"),
        bytes
    );
    eprintln!(
        "Synthetic 4×16 committed candidate report: {} bytes; {}",
        bytes.len(),
        serde_json::to_string(&report.witnesses).expect("the fixture value formats as text")
    );

    refuse_partial_witnesses(&mut report);
}

fn refuse_partial_witnesses(report: &mut Report) {
    // Freight dispatch/output differences alone must not qualify without a
    // workforce consequence. Restore those factual fields before the next probe.
    let baseline_staffing: Vec<_> = report.cases[run::BASELINE]
        .periods
        .iter()
        .map(|period| {
            period
                .owners
                .iter()
                .map(|(key, owner)| (key.clone(), owner.staffing.clone()))
                .collect::<BTreeMap<_, _>>()
        })
        .collect();
    let freight_periods = &mut report
        .cases
        .get_mut(run::FREIGHT)
        .expect("the fixture holds the addressed entry")
        .periods;
    let actual_staffing: Vec<_> = freight_periods
        .iter_mut()
        .zip(&baseline_staffing)
        .map(|(period, replacement)| {
            period
                .owners
                .iter_mut()
                .map(|(key, owner)| {
                    (
                        key.clone(),
                        std::mem::replace(&mut owner.staffing, replacement[key].clone()),
                    )
                })
                .collect::<BTreeMap<_, _>>()
        })
        .collect();
    assert!(witness::find(report)
        .expect("the fixture holds the searched element")
        .freight
        .is_none());
    for (period, actual) in report
        .cases
        .get_mut(run::FREIGHT)
        .expect("the fixture holds the addressed entry")
        .periods
        .iter_mut()
        .zip(actual_staffing)
    {
        for (key, owner) in &mut period.owners {
            owner.staffing.clone_from(&actual[key]);
        }
    }
    let baseline_output: Vec<_> = report.cases[run::BASELINE]
        .periods
        .iter()
        .map(|period| {
            period
                .processes
                .iter()
                .map(|(key, process)| (key.clone(), process.output_units))
                .collect::<BTreeMap<_, _>>()
        })
        .collect();
    for (period, baseline) in report
        .cases
        .get_mut(run::FREIGHT)
        .expect("the fixture holds the addressed entry")
        .periods
        .iter_mut()
        .zip(&baseline_output)
    {
        for (key, process) in &mut period.processes {
            process.output_units = baseline[key];
        }
    }
    let missing_output = witness::find(report).expect("the fixture holds the searched element");
    assert!(missing_output.freight.is_none());
    assert!(missing_output.packaging.is_some());
    for (period, baseline) in report
        .cases
        .get_mut(run::PACKAGING)
        .expect("the fixture holds the addressed entry")
        .periods
        .iter_mut()
        .zip(&baseline_output)
    {
        period
            .processes
            .get_mut(&report.candidate.food_process)
            .expect("the fixture holds the addressed entry")
            .output_units = baseline[&report.candidate.food_process];
    }
    assert!(witness::find(report)
        .expect("the fixture holds the searched element")
        .packaging
        .is_none());
}

#[test]
fn candidate_refuses_mixed_source_pins_and_nondecreasing_interventions() {
    let (mut inputs, mut candidate) = input();
    let original = inputs
        .physical
        .terminal_source_pins
        .insert("defines_sha256".to_owned(), "00".repeat(32))
        .expect("the fixture call `insert` succeeds for the authored inputs");
    let error = run::experiment(&inputs, &candidate)
        .err()
        .expect("the fixture call `err` succeeds for the authored inputs")
        .to_string();
    assert!(error.contains("different defines bytes"), "{error}");
    inputs
        .physical
        .terminal_source_pins
        .insert("defines_sha256".to_owned(), original);
    candidate.constrained_grams = 0;
    let error = run::experiment(&inputs, &candidate)
        .err()
        .expect("the fixture call `err` succeeds for the authored inputs")
        .to_string();
    assert!(
        error.contains("capacity must be positive and strictly below"),
        "{error}"
    );
    candidate.constrained_grams = 1_000;
    candidate.shortage_opening = u64::MAX;
    let error = run::experiment(&inputs, &candidate)
        .err()
        .expect("the fixture call `err` succeeds for the authored inputs")
        .to_string();
    assert!(error.contains("stock must be strictly below"), "{error}");
}
