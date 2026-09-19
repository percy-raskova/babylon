//! Bounded diagnostic runner using the authoritative material runtime.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_persistence::simulation_experiment::{report, SimulationExperimentV1};
use babylon_persistence::{identity::CampaignId, material_runtime::DurableMaterialRuntime};
use babylon_practice_contract::OrderedPracticeActionBatch;
use serde::Serialize;
use serde_json::json;
use std::{
    io::Write,
    path::{Path, PathBuf},
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut out = String::new();
    for b in bytes {
        write!(&mut out, "{b:02x}").expect("String write");
    }
    out
}
fn write(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    f.write_all(bytes)?;
    f.sync_all()?;
    Ok(())
}
fn json_file(path: &Path, value: &impl Serialize) -> Result<()> {
    write(path, &serde_json::to_vec_pretty(value)?)
}
fn run() -> Result<()> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    let mut input = None;
    let mut output = None;
    let mut dsn = None;
    let mut iter = args.chunks_exact(2);
    for pair in &mut iter {
        match pair[0].as_str() {
            "--input" if input.is_none() => input = Some(PathBuf::from(&pair[1])),
            "--output" if output.is_none() => output = Some(PathBuf::from(&pair[1])),
            "--dsn" if dsn.is_none() => dsn = Some(pair[1].clone()),
            _ => return Err(
                "usage: simulation_experiment --input SPEC --output ABSOLUTE_DIRECTORY [--dsn DSN]"
                    .into(),
            ),
        }
    }
    if !iter.remainder().is_empty() {
        return Err("missing flag value".into());
    }
    let input = input.ok_or("missing --input")?;
    let output = output.ok_or("missing --output")?;
    if !output.is_absolute() {
        return Err("output directory must be absolute".into());
    }
    std::fs::create_dir_all(&output)?;
    if std::fs::metadata(&input)?.len() > 65_536 {
        return Err("experiment input exceeds bound".into());
    }
    let spec = SimulationExperimentV1::parse(&std::fs::read(input)?)?;
    // Capture replayable input before execution, including failures.
    write(
        &output.join("canonical_experiment.json"),
        &spec.canonical_bytes()?,
    )?;
    let run = report::run(&spec)?;
    json_file(&output.join("trajectory.json"), &run.trajectory)?;
    json_file(&output.join("periods.json"), &run.periods)?;
    json_file(&output.join("captured_setup.json"), &run.captured_setup)?;
    write(&output.join("captured_defines.bin"), &run.captured_defines)?;
    write(&output.join("foundation.bin"), &run.foundation_bytes)?;
    let mut artifact_names = vec![
        "canonical_experiment.json",
        "trajectory.json",
        "captured_setup.json",
        "periods.json",
        "captured_defines.bin",
        "foundation.bin",
    ];
    if let Some(dsn) = dsn {
        persisted_parity(&spec, &run, &dsn, &output)?;
        artifact_names.extend(["parity.json", "campaign.json"]);
    }
    let mut checksums = std::collections::BTreeMap::new();
    for name in artifact_names {
        checksums.insert(
            name,
            hex(&babylon_kernel::content_digest::sha256_of(&std::fs::read(
                output.join(name),
            )?)),
        );
    }
    json_file(
        &output.join("manifest.json"),
        &json!({"schema":"SimulationExperimentManifestV1", "status":"complete", "files_sha256":checksums}),
    )?;
    println!(
        "{} completed {} periods; {} checkpoint restarts; {} observed choices",
        spec.profile.id(),
        run.trajectory.completed_periods,
        run.captured_setup.checkpoint_restarts,
        run.trajectory.observed_choice_count
    );
    Ok(())
}
fn persisted_parity(
    spec: &SimulationExperimentV1,
    run: &report::ExperimentRun,
    dsn: &str,
    output: &Path,
) -> Result<()> {
    let config: postgres::Config = dsn.parse()?;
    let foundation = spec.create_foundation()?;
    let digest = foundation.digest();
    let mut id: [u8; 16] = digest[..16]
        .try_into()
        .map_err(|_| "campaign identity length")?;
    // Each invocation claims a distinct campaign; duplicate deterministic inputs
    // must not take ownership of an existing campaign's durable state.
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos()
        .to_be_bytes();
    for (a, b) in id.iter_mut().zip(nonce) {
        *a ^= b;
    }
    let campaign = CampaignId::from_uuid(uuid::Uuid::from_bytes(id));
    let mut runtime = DurableMaterialRuntime::create(&config, campaign, foundation)?;
    // Retain the exact owned campaign even when a later parity check fails.
    // The caller's disposable database lifecycle owns cleanup.
    json_file(
        &output.join("campaign.json"),
        &json!({"campaign_id":campaign.as_uuid().to_string()}),
    )?;
    let mut restarts = 0;
    for expected in &run.periods {
        let actions = OrderedPracticeActionBatch::empty(
            runtime.session().graph_session().session_identity().clone(),
            expected.period,
        )
        .map_err(|error| format!("invalid empty practice batch: {error:?}"))?;
        let actual = runtime.advance_and_commit(&mut CollectingSink::default(), &actions)?;
        if hex(&actual.result_world_hash()) != expected.world_hash
            || hex(actual.tick_content_hash().as_bytes()) != expected.tick_content_sha256
        {
            return Err("persisted trajectory differs from in-memory replay".into());
        }
        if expected.period.is_multiple_of(13) || expected.period == spec.horizon {
            drop(runtime);
            runtime = DurableMaterialRuntime::open(&config, campaign, digest)?;
            restarts += 1;
            if hex(&runtime.session().current_world_hash()?) != expected.world_hash {
                return Err("durable reconstruction differs from committed trajectory".into());
            }
        }
    }
    json_file(
        &output.join("parity.json"),
        &json!({"schema":"SimulationExperimentParityV1","mode":"postgresql","matched":true,"periods":spec.horizon,"restarts":restarts,"foundation_sha256":hex(&digest),"final_world_hash":hex(&runtime.session().current_world_hash()?)}),
    )?;
    Ok(())
}

fn main() -> std::process::ExitCode {
    match run() {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(error) => {
            if let Some(output) = std::env::args()
                .skip(1)
                .collect::<Vec<_>>()
                .chunks_exact(2)
                .find(|p| p[0] == "--output")
                .map(|p| PathBuf::from(&p[1]))
            {
                if output.is_absolute() && output.is_dir() {
                    if let Err(artifact_error) = json_file(
                        &output.join("failure.json"),
                        &json!({"schema":"SimulationExperimentFailureV1", "error":error.to_string()}),
                    ) {
                        eprintln!("could not retain failure evidence: {artifact_error}");
                    }
                }
            }
            eprintln!("simulation experiment failed: {error}");
            std::process::ExitCode::FAILURE
        }
    }
}
