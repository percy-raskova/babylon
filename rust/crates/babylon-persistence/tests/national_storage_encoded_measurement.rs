//! Authoritative national save growth through the owned, rotating `PostgreSQL` harness.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_persistence::{
    economic_catalog::CapturedEconomicCatalog,
    identity::CampaignId,
    install_current_schema,
    material_runtime::{DurableMaterialRuntime, MaterialRuntimeFoundation},
    postgres_catalog::validate_connection_target,
    preflight_current_schema,
};
use postgres::{Config, NoTls};
use std::{
    fs::{self, File, OpenOptions},
    io::Write,
    path::PathBuf,
    process::Command,
    str::FromStr,
    time::{Duration, Instant},
};
use uuid::Uuid;

#[path = "fixtures/national_capture.rs"]
mod national_capture;
#[path = "support/national_playable.rs"]
mod national_playable;

#[derive(serde::Serialize)]
struct NativeTimingSample {
    tick: u64,
    elapsed_ns: u64,
}

#[derive(serde::Serialize)]
struct NativeRunTiming {
    periods: u64,
    elapsed_ns: u64,
    compilation_included: bool,
}

#[derive(serde::Serialize)]
struct NativeTimingEvidence {
    version: u32,
    source: &'static str,
    clock: &'static str,
    campaign: String,
    advances: Vec<NativeTimingSample>,
    cold_reopens: Vec<NativeTimingSample>,
    archive_catchups: Vec<NativeTimingSample>,
    production_reads: Vec<NativeTimingSample>,
    run: NativeRunTiming,
}

fn elapsed_ns(duration: Duration) -> u64 {
    let value = u64::try_from(duration.as_nanos()).expect("native duration fits exact u64 ns");
    assert!(
        i64::try_from(value).is_ok(),
        "native duration fits signed evidence range"
    );
    value
}

fn write_native_timings(evidence: &NativeTimingEvidence) {
    let directory = PathBuf::from(
        std::env::var("BABYLON_STORAGE_REPORT_DIRECTORY")
            .expect("owned evidence directory required"),
    );
    assert!(directory.is_absolute() && directory.is_dir());
    let target = directory.join("native-timings.json");
    assert!(
        !target.exists(),
        "never replace previous native timing evidence"
    );
    let temporary = directory.join("native-timings.json.partial");
    let bytes = serde_json::to_vec(evidence).expect("bounded timing evidence encodes");
    assert!(
        bytes
            .len()
            .checked_add(1)
            .is_some_and(|length| length <= 1_048_576),
        "timing evidence exceeds one MiB bound"
    );
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .expect("create new atomic timing evidence");
    file.write_all(&bytes)
        .expect("write complete timing evidence");
    file.write_all(b"\n").expect("finish timing evidence");
    file.sync_all().expect("sync timing evidence");
    drop(file);
    fs::rename(&temporary, &target).expect("publish complete timing evidence");
    File::open(&directory)
        .expect("open evidence directory")
        .sync_all()
        .expect("sync evidence publication");
}

fn save_qualification_ticks() -> u64 {
    let directory = PathBuf::from(
        std::env::var("BABYLON_STORAGE_REPORT_DIRECTORY")
            .expect("captured report directory required"),
    );
    assert!(directory.is_absolute() && directory.is_dir());
    let bytes = fs::read(directory.join("policy.json")).expect("captured storage policy exists");
    let policy: serde_json::Value =
        serde_json::from_slice(&bytes).expect("captured storage policy parses");
    assert_eq!(policy["county_count"].as_u64(), Some(3_144));
    assert_eq!(policy["qualification_ticks"].as_u64(), Some(52));
    let maximum = policy["save_qualification_ticks"]
        .as_u64()
        .expect("save qualification ticks is an exact positive integer");
    assert!(maximum > 0 && i64::try_from(maximum).is_ok());
    maximum
}

fn snapshot(stage: &str, campaign: CampaignId) {
    let script = PathBuf::from(
        std::env::var("BABYLON_STORAGE_SNAPSHOT_SCRIPT")
            .expect("current encoded snapshot script required"),
    );
    assert!(
        script.is_absolute(),
        "snapshot script must be an exact absolute path"
    );
    let status = Command::new("mise")
        .args(["exec", "--", "uv", "run", "--frozen", "python"])
        .arg(script)
        .arg(stage)
        .args(["--campaign", &campaign.as_uuid().to_string()])
        .status()
        .expect("read-only storage snapshot runner starts");
    assert!(
        status.success(),
        "read-only storage snapshot failed for {stage}"
    );
}

fn capture_foundation() -> (MaterialRuntimeFoundation, [u8; 32]) {
    let started = Instant::now();
    let catalog = CapturedEconomicCatalog::capture(national_capture::input(), None).unwrap();
    assert_eq!(catalog.opening().sites.len(), 60_634);
    // Three aid children partition retained parent budgets; they add no people.
    assert_eq!(catalog.opening().households.len(), 15_696);
    let foundation = catalog
        .create_foundation(
            ReplaySessionId::try_from("national-save-growth-current17").unwrap(),
            ReplaySeed::new(319),
        )
        .unwrap();
    let foundation_digest = foundation.digest();
    eprintln!(
        "current national capture+foundation elapsed={:?}, bytes={}",
        started.elapsed(),
        foundation.canonical_len().unwrap()
    );
    (foundation, foundation_digest)
}

fn playable_mode(value: Option<&str>) -> Result<bool, &'static str> {
    match value {
        None | Some("raw-economic") => Ok(false),
        Some("playable-aid") => Ok(true),
        Some(_) => Err("national capture mode must be raw-economic or playable-aid"),
    }
}

#[test]
fn national_capture_mode_is_explicit_and_unknown_modes_refuse() {
    assert_eq!(playable_mode(None), Ok(false));
    assert_eq!(playable_mode(Some("raw-economic")), Ok(false));
    assert_eq!(playable_mode(Some("playable-aid")), Ok(true));
    assert!(playable_mode(Some("national")).is_err());
    assert!(playable_mode(Some("")).is_err());
}

fn owned_config() -> Config {
    let canary = std::env::var("BABYLON_STORAGE_CANARY").expect("owned canary required");
    assert_eq!(canary.len(), 32);
    let config = Config::from_str(
        &std::env::var("BABYLON_NATIONAL_STORAGE_WRITER_DSN").expect("owned writer required"),
    )
    .expect("owned writer config parses");
    validate_connection_target(&config).expect("validated loopback target");
    let mut connection = config.connect(NoTls).expect("owned writer connects");
    let actual: Option<String> = connection
        .query_one(
            "SELECT current_setting('babylon.disposable_runtime',true)",
            &[],
        )
        .unwrap()
        .get(0);
    assert_eq!(actual.as_deref(), Some(canary.as_str()));
    let attrs: (bool, bool, bool, bool, bool) = {
        let row = connection.query_one(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user", &[],
        ).unwrap();
        (row.get(0), row.get(1), row.get(2), row.get(3), row.get(4))
    };
    assert_eq!(attrs, (false, false, false, false, false));
    drop(connection);
    config
}

fn fresh_measurement_campaign(config: &Config) -> CampaignId {
    let mut connection = config.connect(NoTls).expect("owned writer reconnects");
    let campaign = CampaignId::from_uuid(
        Uuid::parse_str(
            &std::env::var("BABYLON_NATIONAL_STORAGE_CAMPAIGN")
                .expect("fresh measurement campaign required"),
        )
        .unwrap(),
    );
    let existing: i64 = connection.query_one(
        "SELECT count(*) FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1", &[campaign.as_uuid()],
    ).unwrap().get(0);
    assert_eq!(existing, 0, "never overwrite an existing campaign");
    drop(connection);
    campaign
}

#[test]
#[ignore = "requires exact task-owned PostgreSQL and storage recorder environment"]
fn actual_encoded_national_tick_measures_postgresql_growth_and_recovery() {
    let run_started = Instant::now();
    let config = owned_config();
    preflight_current_schema(&config).expect("fresh owned current schema preflight");
    let schema = install_current_schema(&config).expect("exact atomic current schema install");
    eprintln!(
        "current schema installed and admitted: {:?}",
        schema.disposition
    );
    let campaign = fresh_measurement_campaign(&config);
    let periods: u64 = std::env::var("BABYLON_NATIONAL_STORAGE_PERIODS")
        .unwrap_or_else(|_| "2".to_owned())
        .parse()
        .unwrap();
    assert!((1..=save_qualification_ticks()).contains(&periods));
    let mode = std::env::var("BABYLON_NATIONAL_CAPTURE_MODE").ok();
    let playable = playable_mode(mode.as_deref()).expect("explicit national capture mode");
    assert!(
        !playable || periods >= 2,
        "playable aid proof requires at least two periods"
    );
    let mut advances = Vec::new();
    let mut cold_reopens = Vec::new();
    snapshot("schema-baseline", campaign);
    if playable {
        national_playable::qualify(&config, campaign, periods, run_started);
        return;
    }
    let (foundation, foundation_digest) = capture_foundation();
    let started = Instant::now();
    let mut runtime = DurableMaterialRuntime::create(&config, campaign, foundation).unwrap();
    eprintln!(
        "authoritative opening commit elapsed={:?}",
        started.elapsed()
    );
    snapshot("opening-created", campaign);
    for tick in 1..=periods {
        let actions = runtime.next_action_batch().unwrap();
        let started = Instant::now();
        let identity = runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .unwrap();
        let committed_elapsed = started.elapsed();
        let parity_started = Instant::now();
        assert_eq!(identity.resolve_tick(), tick);
        assert_eq!(runtime.session().completed_tick(), tick);
        let world = runtime.session().current_world_hash().unwrap();
        assert_eq!(identity.result_world_hash(), world);
        let register = runtime.session().material().digest();
        let parity_elapsed = parity_started.elapsed();
        advances.push(NativeTimingSample {
            tick,
            elapsed_ns: elapsed_ns(committed_elapsed),
        });
        eprintln!(
            "authoritative national tick={tick} committed_elapsed={:?} register_bytes={} world_hash={:02x?}",
            committed_elapsed,
            runtime.session().material().canonical_bytes().len(),
            world
        );
        eprintln!("authoritative national tick={tick} parity_elapsed={parity_elapsed:?}");
        snapshot(&format!("tick-{tick:02}"), campaign);
        drop(runtime);
        let started = Instant::now();
        runtime = DurableMaterialRuntime::open(&config, campaign, foundation_digest).unwrap();
        let restart_elapsed = started.elapsed();
        let parity_started = Instant::now();
        assert_eq!(runtime.session().completed_tick(), tick);
        assert_eq!(runtime.session().current_world_hash().unwrap(), world);
        assert_eq!(runtime.session().material().digest(), register);
        let parity_elapsed = parity_started.elapsed();
        cold_reopens.push(NativeTimingSample {
            tick,
            elapsed_ns: elapsed_ns(restart_elapsed),
        });
        eprintln!("authoritative restart tick={tick} elapsed={restart_elapsed:?}");
        eprintln!("authoritative restart tick={tick} parity_elapsed={parity_elapsed:?}");
        snapshot(&format!("tick-{tick:02}-reopened"), campaign);
    }
    drop(runtime);
    write_native_timings(&NativeTimingEvidence {
        version: 2,
        source: "authoritative_native_instants_v2",
        clock: "monotonic",
        campaign: campaign.as_uuid().to_string(),
        advances,
        cold_reopens,
        archive_catchups: Vec::new(),
        production_reads: Vec::new(),
        run: NativeRunTiming {
            periods,
            elapsed_ns: elapsed_ns(run_started.elapsed()),
            compilation_included: false,
        },
    });
}

fn expected_digest(name: &str) -> [u8; 32] {
    let text = std::env::var(name).expect("explicit retained-game digest required");
    assert_eq!(text.len(), 64);
    let mut digest = [0; 32];
    for (index, pair) in text.as_bytes().chunks_exact(2).enumerate() {
        digest[index] = u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap();
    }
    digest
}

#[test]
#[ignore = "read-only recovery of one explicitly identified retained measurement game"]
fn retained_national_tick_reopens_without_creating_or_advancing() {
    let canary = std::env::var("BABYLON_STORAGE_CANARY").expect("owned canary required");
    assert_eq!(canary.len(), 32);
    let config = Config::from_str(
        &std::env::var("BABYLON_NATIONAL_STORAGE_WRITER_DSN").expect("owned writer required"),
    )
    .expect("owned writer config parses");
    validate_connection_target(&config).expect("validated loopback target");
    let mut connection = config.connect(NoTls).expect("owned writer connects");
    let actual: Option<String> = connection
        .query_one(
            "SELECT current_setting('babylon.disposable_runtime',true)",
            &[],
        )
        .unwrap()
        .get(0);
    assert_eq!(actual.as_deref(), Some(canary.as_str()));
    drop(connection);
    let campaign = CampaignId::from_uuid(
        Uuid::parse_str(
            &std::env::var("BABYLON_NATIONAL_STORAGE_CAMPAIGN")
                .expect("explicit retained campaign required"),
        )
        .unwrap(),
    );
    let tick: u64 = std::env::var("BABYLON_STORAGE_REOPEN_TICK")
        .expect("explicit retained tick required")
        .parse()
        .unwrap();
    assert!((1..=save_qualification_ticks()).contains(&tick));
    let expected_foundation = expected_digest("BABYLON_STORAGE_REOPEN_FOUNDATION_SHA256");
    let expected_register = expected_digest("BABYLON_STORAGE_REOPEN_REGISTER_SHA256");
    let expected_world = expected_digest("BABYLON_STORAGE_REOPEN_WORLD_SHA256");
    let started = Instant::now();
    let runtime = DurableMaterialRuntime::open(&config, campaign, expected_foundation).unwrap();
    let restart_elapsed = started.elapsed();
    let parity_started = Instant::now();
    assert_eq!(runtime.session().completed_tick(), tick);
    assert_eq!(runtime.tail().unwrap().resolve_tick(), tick);
    assert_eq!(runtime.tail().unwrap().result_world_hash(), expected_world);
    assert_eq!(
        runtime.session().current_world_hash().unwrap(),
        expected_world
    );
    assert_eq!(runtime.session().material().digest(), expected_register);
    let parity_elapsed = parity_started.elapsed();
    eprintln!("authoritative retained restart tick={tick} elapsed={restart_elapsed:?}");
    eprintln!("authoritative retained restart tick={tick} parity_elapsed={parity_elapsed:?}");
    snapshot(&format!("tick-{tick:02}-reopened"), campaign);
}
