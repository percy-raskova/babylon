//! Leaf implementation for the parent module; public paths stay on the parent.

#[allow(unused_imports)]
use super::{contract, Arc, Mutex, Output, Progress, Result, Watchdog};

#[allow(unused_imports)]
use super::{artifacts, json, observe, run, PathBuf};

pub(crate) fn output_argument(
    args: impl IntoIterator<Item = std::ffi::OsString>,
) -> Result<PathBuf> {
    let args: Vec<_> = args.into_iter().collect();
    if args.len() != 2 || args[0] != "--output" {
        return Err(contract(
            "usage: michigan_experiment --output /absolute/new-directory",
        ));
    }
    let path = PathBuf::from(&args[1]);
    if !path.is_absolute() {
        return Err(contract("output directory must be absolute"));
    }
    Ok(path)
}

pub(crate) fn execute(output: &mut Output, progress: &Mutex<Progress>) -> Result<()> {
    let provenance = artifacts::provenance()?;
    let cases = run::cases()?;
    let experiment_identity = run::experiment_identity(&cases)?;
    let experiment_digest = run::digest_json(&experiment_identity)?;
    // Retain exact preparation even when a later transition fails.
    output.write_json("inputs.json", &experiment_identity)?;
    let mut results = Vec::new();
    for case in cases {
        *progress
            .lock()
            .map_err(|_| contract("progress mutex poisoned"))? = Progress {
            case: Some(case.spec.id.to_owned()),
            last_completed_period: 0,
        };
        let result = run::run_case(&case, |row| {
            output.append_period(row)?;
            progress
                .lock()
                .map_err(|_| contract("progress mutex poisoned"))?
                .last_completed_period = row.period;
            Ok(())
        })?;
        results.push(result);
    }
    let summary = run::summarize(&results)?;
    run::qualify(&results, &summary)?;
    output.write_json("summary.json", &summary)?;
    let checksums = output.checksums()?;
    output.write_json("manifest.json", &json!({
        "schema": "MichiganDeliveryStockExperimentManifestV1",
        "status": "complete",
        "experiment_digest": experiment_digest,
        "inputs": experiment_identity,
        "case_foundations": results.iter().map(|result| json!({"case": result.case, "identity": result.foundation})).collect::<Vec<_>>(),
        "provenance": provenance,
        "persistence": false,
        "postgresql_parity_qualified": false,
        "seed": 319,
        "seed_override_supported": false,
        "governed_realization_consumers": 0,
        "observed_choice_receipts": 0,
        "bounds": {"cases": 4, "periods_per_case": 16, "period_records": 64,
            "wall_seconds_after_compilation": 60, "artifact_bytes": 4 * 1024 * 1024,
            "concurrent_sessions": 1, "full_graph_dumps": false},
        "files_sha256": checksums,
        "evidence": {"parameters": "Designed", "outcomes": "Derived",
            "constraint_bounds": "Derived diagnostics for one process per Michigan site; ties do not prove independent causal bottlenecks"}
    }))
}
