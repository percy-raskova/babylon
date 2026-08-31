//! Sole production command for Rust-owned `PostgreSQL` persistence.

use std::ffi::{OsStr, OsString};
use std::process::ExitCode;

use babylon_bsl::rule_pipeline::split_content;
use babylon_bsl::rules_hash_of;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::sha256_of;
use babylon_kernel::tick_content_hash::RefDigestV1;
use babylon_kernel::ContentDigest;
use babylon_persistence::{
    activate_rust_persistence_v1, michigan_dynamic_hex_foundation_v1, preflight_schema_epoch,
    representative_h3_reference_cohort_v1, CampaignId, CommittedResolveTickV1,
    DurableReplayRuntimeV1, FoundationContentBundleV1, RustPersistenceRuntimeErrorV1,
};
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use babylon_tick::material_state::MaterialStateV1;
use babylon_tick::replay_session::ReplayTickSession;
use postgres::{Config, NoTls};
use uuid::Uuid;

const DSN_ENV: &str = "BABYLON_RUNTIME_DSN";
const CAMPAIGN_ENV: &str = "BABYLON_CAMPAIGN_ID";
const DEFAULT_CAMPAIGN_UUID: u128 = 0x2810_0000_0000_0000_0000_0000_0000_0001;
const MICHIGAN_SMOKE_TICKS: u64 = 60;
const MICHIGAN_SMOKE_RESTART_TICKS: &[u64] = &[1, 51, 52, 60];
const DEFINES: &[u8] = br#"{"alpha":1}"#;
const REFERENCE_BUNDLE_DOMAIN: &[u8] = b"babylon.h3.reference-bundle-composite.v1\0";
const SCENARIO: &str = r"
(scenario production/rust-runtime
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/draw coefficient extensive)
  (node class-a NodeType/SOCIAL_CLASS (social-class/draw 0.0c)))
";
const RULE: &str = r#"
(rule production/rust-runtime
  :role mechanic
  :evidence derived
  :material-basis "Rust persistence runtime exercise"
  :fuel 32
  (bindings (binding draw :field social-class/draw))
  (when #t)
  (effects
    (update-node self social-class/draw (set 0.25c))
    (emit EventType/CHECKPOINTED (subject self))))
"#;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Command {
    Activate,
    Bootstrap,
    Preflight,
    Run { ticks: u64 },
    Probe,
    Archive,
    MichiganSmoke,
}

fn main() -> ExitCode {
    let Ok(command) = parse_command(std::env::args_os().skip(1)) else {
        eprintln!(
            "babylon-runtime: expected activate, bootstrap, preflight, run --ticks N, probe, archive, or michigan-smoke"
        );
        return ExitCode::from(2);
    };
    let Some(raw_dsn) = std::env::var_os(DSN_ENV) else {
        eprintln!("babylon-runtime: {DSN_ENV} is required");
        return ExitCode::from(2);
    };
    let Ok(dsn) = raw_dsn.into_string() else {
        eprintln!("babylon-runtime: {DSN_ENV} must be valid UTF-8");
        return ExitCode::from(2);
    };
    let Ok(config) = dsn.parse::<Config>() else {
        eprintln!("babylon-runtime: {DSN_ENV} is not a valid PostgreSQL DSN");
        return ExitCode::from(2);
    };
    if let Err(error) = representative_h3_reference_cohort_v1() {
        eprintln!("babylon-runtime: embedded H3 reference fixture is invalid: {error}");
        return ExitCode::FAILURE;
    }

    match execute(command, &config) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("babylon-runtime: {error}");
            ExitCode::FAILURE
        }
    }
}

fn execute(command: Command, config: &Config) -> Result<(), String> {
    match command {
        Command::Preflight => {
            preflight_schema_epoch(config).map_err(|error| error.to_string())?;
            println!("Rust schema target and owner preflight complete.");
        }
        Command::Activate | Command::Bootstrap => {
            let report = activate_rust_persistence_v1(config).map_err(|error| error.to_string())?;
            println!(
                "Rust persistence authority active (prepared_epoch={}, active_epoch={}).",
                report.prepared_row().schema_epoch(),
                report.rust_active_row().schema_epoch(),
            );
        }
        Command::Run { ticks } => {
            activate_rust_persistence_v1(config).map_err(|error| error.to_string())?;
            run_to_tick(config, campaign_id()?, ticks, &[])?;
        }
        Command::MichiganSmoke => {
            activate_rust_persistence_v1(config).map_err(|error| error.to_string())?;
            run_to_tick(
                config,
                campaign_id()?,
                MICHIGAN_SMOKE_TICKS,
                MICHIGAN_SMOKE_RESTART_TICKS,
            )?;
        }
        Command::Probe => probe(config)?,
        Command::Archive => inspect_archive(config)?,
    }
    Ok(())
}

fn campaign_id() -> Result<CampaignId, String> {
    let uuid = match std::env::var(CAMPAIGN_ENV) {
        Ok(value) => Uuid::parse_str(&value)
            .map_err(|_| format!("{CAMPAIGN_ENV} must be a canonical UUID"))?,
        Err(std::env::VarError::NotPresent) => Uuid::from_u128(DEFAULT_CAMPAIGN_UUID),
        Err(std::env::VarError::NotUnicode(_)) => {
            return Err(format!("{CAMPAIGN_ENV} must be valid UTF-8"));
        }
    };
    Ok(CampaignId::from_uuid(uuid))
}

fn run_to_tick(
    config: &Config,
    campaign: CampaignId,
    target_tick: u64,
    restart_ticks: &[u64],
) -> Result<(), String> {
    let mut runtime = open_or_create_runtime(config, campaign)?;
    let mut completed = runtime
        .last_committed_tick()
        .map_or(0, babylon_persistence::CommittedResolveTickV1::get);
    if completed > target_tick {
        return Err(format!(
            "campaign tail {completed} is beyond requested target {target_tick}"
        ));
    }
    while completed < target_tick {
        let resolve_tick = completed
            .checked_add(1)
            .ok_or_else(|| "requested tick overflow".to_owned())?;
        let actions = OrderedPracticeActionBatchV1::empty(
            runtime.foundation().replay_session_identity().clone(),
            resolve_tick,
        )
        .map_err(|_| "empty action batch refused".to_owned())?;
        let receipt = runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .map_err(|error| error.to_string())?;
        completed = receipt.resolve_tick().get();
        println!(
            "Committed Rust tick {} (content_sha256={}).",
            completed,
            hex_digest(receipt.tick_content_hash().as_bytes()),
        );
        if restart_ticks.contains(&completed) {
            runtime = DurableReplayRuntimeV1::open(config, campaign)
                .map_err(|error| error.to_string())?;
            if runtime
                .last_committed_tick()
                .map(CommittedResolveTickV1::get)
                != Some(completed)
            {
                return Err("restart did not recover the acknowledged tail".to_owned());
            }
        }
    }
    println!(
        "Rust durable campaign {} is complete at tick {completed}.",
        campaign.as_uuid(),
    );
    Ok(())
}

fn open_or_create_runtime(
    config: &Config,
    campaign: CampaignId,
) -> Result<DurableReplayRuntimeV1<HypergraphStore>, String> {
    match DurableReplayRuntimeV1::open(config, campaign) {
        Ok(runtime) => Ok(runtime),
        Err(RustPersistenceRuntimeErrorV1::FoundationAbsent) => {
            let (session, bundle) = runtime_foundation()?;
            DurableReplayRuntimeV1::create(config, campaign, session, bundle)
                .map_err(|error| error.to_string())
        }
        Err(error) => Err(error.to_string()),
    }
}

fn runtime_foundation() -> Result<
    (
        ReplayTickSession<HypergraphStore>,
        FoundationContentBundleV1,
    ),
    String,
> {
    let (_, rules) = split_content(RULE).map_err(|_| "runtime rule parse refused".to_owned())?;
    let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
    let content = ContentDigest {
        defines_hash: sha256_of(DEFINES),
        rules_hash: rules_hash_of(&forms).map_err(|_| "runtime rule hash refused".to_owned())?,
    };
    let session_id = ReplaySessionIdV1::try_from("per281/rust-runtime")
        .map_err(|_| "runtime replay identity refused".to_owned())?;
    let seed = ReplaySeed::new(281);
    let foundation = michigan_dynamic_hex_foundation_v1()
        .map_err(|error| format!("Michigan foundation refused: {error}"))?;
    let mut reference_manifest = REFERENCE_BUNDLE_DOMAIN.to_vec();
    reference_manifest.extend_from_slice(&foundation.base_reference_cohort_digest());
    reference_manifest.extend_from_slice(&foundation.r8_section_digest());
    if sha256_of(&reference_manifest) != foundation.reference_bundle_digest() {
        return Err("Michigan reference-bundle digest mismatch".to_owned());
    }
    let reference = RefDigestV1::from_bytes(foundation.reference_bundle_digest());
    let session = ReplayTickSession::new(
        SCENARIO,
        None,
        RULE,
        HypergraphStore::new(),
        session_id,
        seed,
        content,
        reference,
        MaterialStateV1::try_new(foundation)
            .map_err(|_| "Michigan material foundation refused".to_owned())?,
    )
    .map_err(|_| "runtime tick-zero session refused".to_owned())?;
    let bundle =
        FoundationContentBundleV1::try_new(SCENARIO, None, RULE, DEFINES, &reference_manifest)
            .map_err(|error| error.to_string())?;
    Ok((session, bundle))
}

fn probe(config: &Config) -> Result<(), String> {
    let mut client = config
        .connect(NoTls)
        .map_err(|_| "database probe connection failed".to_owned())?;
    let authority_rows: i64 = client
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_meta.persistence_authority_ledger",
            &[],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|_| "authority probe failed".to_owned())?;
    let row = client
        .query_one(
            "SELECT pg_catalog.count(DISTINCT foundation.campaign_id), pg_catalog.max(marker.resolve_tick) \
             FROM babylon_state.campaign_foundation AS foundation \
             LEFT JOIN babylon_state.tick_commit AS marker \
               ON marker.campaign_id = foundation.campaign_id",
            &[],
        )
        .map_err(|_| "campaign-tail probe failed".to_owned())?;
    let campaigns: i64 = row
        .try_get(0)
        .map_err(|_| "campaign count decode failed".to_owned())?;
    let tail: Option<i64> = row
        .try_get(1)
        .map_err(|_| "campaign tail decode failed".to_owned())?;
    println!(
        "Rust authority rows={authority_rows}; durable campaigns={campaigns}; highest_tick={}.",
        tail.map_or_else(|| "none".to_owned(), |value| value.to_string()),
    );
    Ok(())
}

fn inspect_archive(config: &Config) -> Result<(), String> {
    let mut client = config
        .connect(NoTls)
        .map_err(|_| "Archive probe connection failed".to_owned())?;
    let row = client
        .query_one(
            "SELECT pg_catalog.count(*), pg_catalog.min(resolve_tick), pg_catalog.max(resolve_tick) \
             FROM babylon_state.archive_dirty_receipt_v1",
            &[],
        )
        .map_err(|_| "Archive dirty-receipt probe failed".to_owned())?;
    let receipts: i64 = row
        .try_get(0)
        .map_err(|_| "Archive receipt count decode failed".to_owned())?;
    let first: Option<i64> = row
        .try_get(1)
        .map_err(|_| "Archive first tick decode failed".to_owned())?;
    let last: Option<i64> = row
        .try_get(2)
        .map_err(|_| "Archive last tick decode failed".to_owned())?;
    println!(
        "Rust Archive dirty receipts={receipts}; tick_range={}..{}.",
        first.map_or_else(|| "none".to_owned(), |value| value.to_string()),
        last.map_or_else(|| "none".to_owned(), |value| value.to_string()),
    );
    Ok(())
}

fn hex_digest(bytes: &[u8; 32]) -> String {
    let mut encoded = String::with_capacity(64);
    for byte in bytes {
        use std::fmt::Write as _;
        write!(&mut encoded, "{byte:02x}").expect("writing to String cannot fail");
    }
    encoded
}

fn parse_command(mut args: impl Iterator<Item = OsString>) -> Result<Command, ()> {
    let Some(command) = args.next() else {
        return Err(());
    };
    match command.as_os_str() {
        value if value == OsStr::new("activate") && args.next().is_none() => Ok(Command::Activate),
        value if value == OsStr::new("bootstrap") && args.next().is_none() => {
            Ok(Command::Bootstrap)
        }
        value if value == OsStr::new("preflight") && args.next().is_none() => {
            Ok(Command::Preflight)
        }
        value if value == OsStr::new("probe") && args.next().is_none() => Ok(Command::Probe),
        value if value == OsStr::new("archive") && args.next().is_none() => Ok(Command::Archive),
        value if value == OsStr::new("michigan-smoke") && args.next().is_none() => {
            Ok(Command::MichiganSmoke)
        }
        value if value == OsStr::new("run") => {
            let flag = args.next().ok_or(())?;
            let ticks = args.next().ok_or(())?;
            if flag != OsStr::new("--ticks") || args.next().is_some() {
                return Err(());
            }
            let ticks = ticks.to_str().ok_or(())?.parse::<u64>().map_err(|_| ())?;
            if ticks == 0 || ticks > i64::MAX as u64 {
                return Err(());
            }
            Ok(Command::Run { ticks })
        }
        _ => Err(()),
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_command, Command, MICHIGAN_SMOKE_RESTART_TICKS, MICHIGAN_SMOKE_TICKS};

    #[test]
    fn michigan_smoke_restarts_at_the_initial_rollover_and_terminal_boundaries() {
        assert_eq!(MICHIGAN_SMOKE_TICKS, 60);
        assert_eq!(MICHIGAN_SMOKE_RESTART_TICKS, [1, 51, 52, 60]);
    }

    #[test]
    fn production_commands_are_closed() {
        assert_eq!(
            parse_command(vec!["activate".into()].into_iter()),
            Ok(Command::Activate)
        );
        assert_eq!(
            parse_command(vec!["bootstrap".into()].into_iter()),
            Ok(Command::Bootstrap)
        );
        assert_eq!(
            parse_command(vec!["preflight".into()].into_iter()),
            Ok(Command::Preflight)
        );
        assert_eq!(
            parse_command(vec!["run".into(), "--ticks".into(), "5".into()].into_iter()),
            Ok(Command::Run { ticks: 5 })
        );
        assert_eq!(
            parse_command(vec!["probe".into()].into_iter()),
            Ok(Command::Probe)
        );
        assert_eq!(
            parse_command(vec!["archive".into()].into_iter()),
            Ok(Command::Archive)
        );
        assert_eq!(
            parse_command(vec!["michigan-smoke".into()].into_iter()),
            Ok(Command::MichiganSmoke)
        );
        assert_eq!(parse_command(Vec::new().into_iter()), Err(()));
        assert_eq!(parse_command(vec!["run".into()].into_iter()), Err(()));
        assert_eq!(
            parse_command(vec!["run".into(), "--ticks".into(), "0".into()].into_iter()),
            Err(())
        );
        assert_eq!(parse_command(vec!["unknown".into()].into_iter()), Err(()));
    }
}
