//! Sole production command for Rust-owned `PostgreSQL` persistence.

use std::ffi::{OsStr, OsString};
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
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
    CommittedTickReceiptV1, DurableReplayRuntimeV1, FoundationContentBundleV1,
    RustPersistenceRuntimeErrorV1,
};
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use babylon_tick::material_state::MaterialStateV1;
use babylon_tick::replay_session::{ReplayCommitDispositionV1, ReplayTickSession};
use postgres::{Config, NoTls};
use uuid::Uuid;

const DSN_ENV: &str = "BABYLON_RUNTIME_DSN";
const CAMPAIGN_ENV: &str = "BABYLON_CAMPAIGN_ID";
const DEFAULT_CAMPAIGN_UUID: u128 = 0x2810_0000_0000_0000_0000_0000_0000_0001;
const MICHIGAN_SMOKE_TICKS: u64 = 60;
const MICHIGAN_SMOKE_RESTART_TICKS: &[u64] = &[1, 51, 52, 60];
const TICK_REPORT_SCHEMA_V1: &str = "babylon.simulation.tick-report.v1";
const DEFINES: &[u8] = br#"{"alpha":1}"#;
const REFERENCE_BUNDLE_DOMAIN: &[u8] = b"babylon.h3.reference-bundle-composite.v1\0";
const SCENARIO: &str = r"
(scenario production/michigan-rust-runtime
  (defvocabulary NodeType (TERRITORY))
  (deffield territory/median-wage real intensive)
  (deffield territory/phi-hour real intensive)
  (deffield territory/phi-savings-adjustment coefficient intensive)
  (deffield territory/rate-accumulation probability intensive)
  (deffield territory/dist-year int extensive)
  (defconst class-dynamics/hours-per-year 2080)
  (defconst class-dynamics/v-reproduction 12)
  (defconst class-dynamics/accumulation-halt-floor-ratio 0.8c)
  (defconst class-dynamics/phi-cap 0.05c)
  (defconst class-dynamics/savings-proletariat 0.03c)
  (defconst class-dynamics/wealth-threshold 142000)
  (defconst class-dynamics/max-accumulation-rate 0.08c)
  (node wayne NodeType/TERRITORY
    (territory/median-wage 21.0r)
    (territory/phi-hour 1.0r)
    (territory/phi-savings-adjustment 0.0c)
    (territory/rate-accumulation 0.0p)
    (territory/dist-year 2010)))
";
const RULE: &str = r#"
(rule class-dynamics/a01-rollover-accumulation-smoke
  :role mechanic
  :evidence derived
  :material-basis "At the annual boundary, wage and imperial-rent-supported savings change class accumulation"
  :fuel 128
  (bindings
    (binding phase-of-year :tick-in-cycle 52)
    (binding median-wage :field territory/median-wage)
    (binding phi-adjustment :field territory/phi-savings-adjustment)
    (binding hours-per-year :const class-dynamics/hours-per-year)
    (binding v-reproduction :const class-dynamics/v-reproduction)
    (binding halt-floor-ratio :const class-dynamics/accumulation-halt-floor-ratio)
    (binding savings-proletariat :const class-dynamics/savings-proletariat)
    (binding wealth-threshold :const class-dynamics/wealth-threshold)
    (binding max-rate :const class-dynamics/max-accumulation-rate)
    (binding wage-floor :expr (* (- v-reproduction 0c) halt-floor-ratio))
    (binding raw-annual-wage :expr (* median-wage hours-per-year))
    (binding effective-wage :expr (if (< median-wage wage-floor)
                                      (- 0 0c)
                                      raw-annual-wage))
    (binding savings-raw :expr (+ savings-proletariat phi-adjustment))
    (binding savings :expr (if (< savings-raw 1) savings-raw (- 1 0c)))
    (binding annual-accumulation :expr (* effective-wage savings))
    (binding accumulation-ratio :expr (if (> annual-accumulation 0)
                                          (/ annual-accumulation wealth-threshold)
                                          (- 0 0c)))
    (binding rate :expr (if (< accumulation-ratio max-rate)
                            accumulation-ratio
                            max-rate)))
  (when (= phase-of-year 0))
  (effects
    (update-node self territory/rate-accumulation (set rate))
    (update-node self territory/dist-year (add 1))
    (emit EventType/MICHIGAN_YEAR_ROLLOVER
      (subject self)
      (phi-adjustment phi-adjustment)
      (accumulation-rate rate))))

(rule economics/phi-savings-coupling-smoke
  :role mechanic
  :evidence derived
  :material-basis "Imperial rent purchases class entry by increasing the savings rate against annual wage"
  :fuel 128
  (bindings
    (binding median-wage :field territory/median-wage)
    (binding phi-hour :field territory/phi-hour)
    (binding hours-per-year :const class-dynamics/hours-per-year)
    (binding v-reproduction :const class-dynamics/v-reproduction)
    (binding halt-floor-ratio :const class-dynamics/accumulation-halt-floor-ratio)
    (binding phi-cap :const class-dynamics/phi-cap)
    (binding wage-floor :expr (* (- v-reproduction 0c) halt-floor-ratio))
    (binding raw-annual-wage :expr (* median-wage hours-per-year))
    (binding effective-wage :expr (if (< median-wage wage-floor)
                                      (- 0 0c)
                                      raw-annual-wage))
    (binding uncapped-adjustment :expr (if (or (= effective-wage 0) (= phi-hour 0))
                                          (- 0 0c)
                                          (/ (* phi-hour hours-per-year) effective-wage)))
    (binding phi-adjustment :expr (if (< uncapped-adjustment phi-cap)
                                      uncapped-adjustment
                                      phi-cap)))
  (when #t)
  (effects
    (update-node self territory/phi-savings-adjustment (set phi-adjustment))))
"#;

#[derive(Clone, Debug, Eq, PartialEq)]
enum Command {
    Activate,
    Bootstrap,
    Preflight,
    Run {
        ticks: u64,
        report_jsonl: Option<PathBuf>,
    },
    Probe,
    Archive,
    MichiganSmoke {
        report_jsonl: Option<PathBuf>,
    },
}

fn main() -> ExitCode {
    let Ok(command) = parse_command(std::env::args_os().skip(1)) else {
        eprintln!(
            "babylon-runtime: expected activate, bootstrap, preflight, run --ticks N [--report-jsonl PATH], probe, archive, or michigan-smoke [--report-jsonl PATH]"
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
        Command::Run {
            ticks,
            report_jsonl,
        } => {
            let mut report_writer = report_jsonl
                .as_deref()
                .map(TickReportJsonlWriter::create)
                .transpose()?;
            activate_rust_persistence_v1(config).map_err(|error| error.to_string())?;
            run_to_tick(config, campaign_id()?, ticks, &[], report_writer.as_mut())?;
        }
        Command::MichiganSmoke { report_jsonl } => {
            let mut report_writer = report_jsonl
                .as_deref()
                .map(TickReportJsonlWriter::create)
                .transpose()?;
            activate_rust_persistence_v1(config).map_err(|error| error.to_string())?;
            run_to_tick(
                config,
                campaign_id()?,
                MICHIGAN_SMOKE_TICKS,
                MICHIGAN_SMOKE_RESTART_TICKS,
                report_writer.as_mut(),
            )?;
        }
        Command::Probe => probe(config, configured_campaign_id()?)?,
        Command::Archive => inspect_archive(config)?,
    }
    Ok(())
}

fn campaign_id() -> Result<CampaignId, String> {
    Ok(configured_campaign_id()?
        .unwrap_or_else(|| CampaignId::from_uuid(Uuid::from_u128(DEFAULT_CAMPAIGN_UUID))))
}

fn configured_campaign_id() -> Result<Option<CampaignId>, String> {
    let uuid = match std::env::var(CAMPAIGN_ENV) {
        Ok(value) => Some(
            Uuid::parse_str(&value)
                .map_err(|_| format!("{CAMPAIGN_ENV} must be a canonical UUID"))?,
        ),
        Err(std::env::VarError::NotPresent) => None,
        Err(std::env::VarError::NotUnicode(_)) => {
            return Err(format!("{CAMPAIGN_ENV} must be valid UTF-8"));
        }
    };
    Ok(uuid.map(CampaignId::from_uuid))
}

fn run_to_tick(
    config: &Config,
    campaign: CampaignId,
    target_tick: u64,
    restart_ticks: &[u64],
    mut report_writer: Option<&mut TickReportJsonlWriter>,
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
        if let Some(writer) = report_writer.as_deref_mut() {
            writer.write_receipt(&receipt)?;
        }
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
    println!("Rust durable campaign is complete at tick {completed}.");
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct RuleTickReportV1 {
    rule_id: String,
    considered: usize,
    fired: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct SimulationTickReportV1 {
    resolve_tick: u64,
    commit_disposition: &'static str,
    graph_before: [u8; 32],
    graph_after: [u8; 32],
    world_before: [u8; 32],
    world_after: [u8; 32],
    considered: usize,
    fired: usize,
    per_rule: Vec<RuleTickReportV1>,
    event_count: usize,
    event_digest: [u8; 32],
    audit_receipt_count: usize,
    material_row_count: usize,
    material_row_digest: [u8; 32],
    tick_content_hash: [u8; 32],
}

impl SimulationTickReportV1 {
    fn try_from_receipt(receipt: &CommittedTickReceiptV1) -> Result<Self, String> {
        let considered = receipt.per_rule_considered();
        let fired = receipt.per_rule_fired();
        if considered.len() != fired.len() {
            return Err("acknowledged tick report rule counts are misaligned".to_owned());
        }
        let mut per_rule = Vec::with_capacity(considered.len());
        for ((considered_id, considered_count), (fired_id, fired_count)) in
            considered.iter().zip(fired)
        {
            if considered_id != fired_id {
                return Err("acknowledged tick report rule identities are misaligned".to_owned());
            }
            per_rule.push(RuleTickReportV1 {
                rule_id: considered_id.clone(),
                considered: *considered_count,
                fired: *fired_count,
            });
        }
        let commit_disposition = match receipt.commit_disposition() {
            ReplayCommitDispositionV1::Committed => "committed",
            ReplayCommitDispositionV1::ReconciledAfterAmbiguousCommit => {
                "reconciled_after_ambiguous_commit"
            }
        };
        Ok(Self {
            resolve_tick: receipt.resolve_tick().get(),
            commit_disposition,
            graph_before: receipt.graph_before(),
            graph_after: receipt.graph_after(),
            world_before: receipt.world_before(),
            world_after: receipt.world_after(),
            considered: receipt.considered(),
            fired: receipt.fired(),
            per_rule,
            event_count: receipt.event_count(),
            event_digest: receipt.event_digest(),
            audit_receipt_count: receipt.audit_receipt_count(),
            material_row_count: receipt.material_row_count(),
            material_row_digest: receipt.material_row_digest(),
            tick_content_hash: *receipt.tick_content_hash().as_bytes(),
        })
    }

    fn json_value(&self) -> serde_json::Value {
        let per_rule = self
            .per_rule
            .iter()
            .map(|rule| {
                serde_json::json!({
                    "rule_id": rule.rule_id.as_str(),
                    "considered": rule.considered,
                    "fired": rule.fired,
                })
            })
            .collect::<Vec<_>>();
        serde_json::json!({
            "schema": TICK_REPORT_SCHEMA_V1,
            "resolve_tick": self.resolve_tick,
            "commit_disposition": self.commit_disposition,
            "graph": {
                "before_sha256": hex_digest(&self.graph_before),
                "after_sha256": hex_digest(&self.graph_after),
            },
            "world": {
                "before_sha256": hex_digest(&self.world_before),
                "after_sha256": hex_digest(&self.world_after),
            },
            "rules": {
                "considered": self.considered,
                "fired": self.fired,
                "per_rule": per_rule,
            },
            "events": {
                "count": self.event_count,
                "digest_sha256": hex_digest(&self.event_digest),
            },
            "audit_receipts": {
                "count": self.audit_receipt_count,
            },
            "material_rows": {
                "count": self.material_row_count,
                "digest_sha256": hex_digest(&self.material_row_digest),
            },
            "tick_content_hash": hex_digest(&self.tick_content_hash),
        })
    }
}

struct TickReportJsonlWriter {
    output: BufWriter<File>,
}

impl TickReportJsonlWriter {
    fn create(path: &Path) -> Result<Self, String> {
        let file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|_| "tick report path must be new and writable".to_owned())?;
        Ok(Self {
            output: BufWriter::new(file),
        })
    }

    fn write_receipt(&mut self, receipt: &CommittedTickReceiptV1) -> Result<(), String> {
        self.write_report(&SimulationTickReportV1::try_from_receipt(receipt)?)
    }

    fn write_report(&mut self, report: &SimulationTickReportV1) -> Result<(), String> {
        serde_json::to_writer(&mut self.output, &report.json_value()).map_err(|_| {
            format!(
                "tick report JSON serialization failed after durable tick {}",
                report.resolve_tick
            )
        })?;
        self.output
            .write_all(b"\n")
            .and_then(|()| self.output.flush())
            .map_err(|_| {
                format!(
                    "tick report JSONL write failed after durable tick {}",
                    report.resolve_tick
                )
            })
    }
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

fn probe(config: &Config, selected_campaign: Option<CampaignId>) -> Result<(), String> {
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
    let (selected_campaign_state, selected_tail_label) = match selected_campaign {
        Some(campaign) => {
            let selected_tail: Option<i64> = client
                .query_one(
                    "SELECT pg_catalog.max(resolve_tick) \
                     FROM babylon_state.tick_commit \
                     WHERE campaign_id = $1::uuid",
                    &[campaign.as_uuid()],
                )
                .and_then(|row| row.try_get(0))
                .map_err(|_| "selected campaign-tail probe failed".to_owned())?;
            (
                "configured",
                selected_tail.map_or_else(|| "none".to_owned(), |value| value.to_string()),
            )
        }
        None => ("unset", "unqueried".to_owned()),
    };
    println!(
        "Rust authority rows={authority_rows}; selected_campaign={selected_campaign_state}; \
         selected_tail={selected_tail_label}; global_durable_campaigns={campaigns}; \
         global_highest_tick={}.",
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
        value if value == OsStr::new("michigan-smoke") => {
            let report_jsonl = parse_report_jsonl_only(args)?;
            Ok(Command::MichiganSmoke { report_jsonl })
        }
        value if value == OsStr::new("run") => {
            let mut ticks = None;
            let mut report_jsonl = None;
            while let Some(flag) = args.next() {
                if flag == OsStr::new("--ticks") {
                    if ticks.is_some() {
                        return Err(());
                    }
                    let value = args.next().ok_or(())?;
                    ticks = Some(value.to_str().ok_or(())?.parse::<u64>().map_err(|_| ())?);
                } else if flag == OsStr::new("--report-jsonl") {
                    if report_jsonl.is_some() {
                        return Err(());
                    }
                    report_jsonl = Some(parse_report_path(args.next().ok_or(())?)?);
                } else {
                    return Err(());
                }
            }
            let ticks = ticks.ok_or(())?;
            if ticks == 0 || ticks > i64::MAX as u64 {
                return Err(());
            }
            Ok(Command::Run {
                ticks,
                report_jsonl,
            })
        }
        _ => Err(()),
    }
}

fn parse_report_jsonl_only(
    mut args: impl Iterator<Item = OsString>,
) -> Result<Option<PathBuf>, ()> {
    let Some(flag) = args.next() else {
        return Ok(None);
    };
    if flag != OsStr::new("--report-jsonl") {
        return Err(());
    }
    let path = parse_report_path(args.next().ok_or(())?)?;
    if args.next().is_some() {
        return Err(());
    }
    Ok(Some(path))
}

fn parse_report_path(value: OsString) -> Result<PathBuf, ()> {
    if value.is_empty() {
        Err(())
    } else {
        Ok(PathBuf::from(value))
    }
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_graph::hypergraph_store::HypergraphStore;
    use babylon_graph::substrate::{GraphSubstrate, NodeId};
    use babylon_kernel::SessionId;
    use babylon_tick::TickSession;

    use super::{
        parse_command, Command, RuleTickReportV1, SimulationTickReportV1, TickReportJsonlWriter,
        MICHIGAN_SMOKE_RESTART_TICKS, MICHIGAN_SMOKE_TICKS, RULE, SCENARIO, TICK_REPORT_SCHEMA_V1,
    };

    static REPORT_PATH_SEQUENCE: AtomicU64 = AtomicU64::new(0);

    fn report_path(label: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "babylon-runtime-{label}-{}-{}.jsonl",
            std::process::id(),
            REPORT_PATH_SEQUENCE.fetch_add(1, Ordering::Relaxed),
        ))
    }

    fn report_fixture() -> SimulationTickReportV1 {
        SimulationTickReportV1 {
            resolve_tick: 7,
            commit_disposition: "reconciled_after_ambiguous_commit",
            graph_before: [0x11; 32],
            graph_after: [0x22; 32],
            world_before: [0x33; 32],
            world_after: [0x44; 32],
            considered: 5,
            fired: 3,
            per_rule: vec![
                RuleTickReportV1 {
                    rule_id: "vitality/example".to_owned(),
                    considered: 2,
                    fired: 1,
                },
                RuleTickReportV1 {
                    rule_id: "lifecycle/example".to_owned(),
                    considered: 3,
                    fired: 2,
                },
            ],
            event_count: 1,
            event_digest: [0x55; 32],
            audit_receipt_count: 2,
            material_row_count: 9,
            material_row_digest: [0x66; 32],
            tick_content_hash: [0x77; 32],
        }
    }

    fn territory_value(session: &TickSession<HypergraphStore>, field: &str) -> f64 {
        session
            .graph()
            .node_attribute(NodeId(0), field)
            .unwrap_or_else(|error| panic!("Wayne {field}: {}", error.message))
    }

    #[test]
    fn michigan_smoke_drives_phi_accumulation_on_the_tick_52_rollover() {
        let session_id = SessionId::new("per281/michigan-rollover-contract")
            .expect("the fixed smoke identity is nonempty");
        let mut session = TickSession::new(SCENARIO, RULE, HypergraphStore::new(), session_id)
            .expect("the production Michigan smoke content must load");

        for tick in 1..=51 {
            let report = session
                .advance(&mut CollectingSink::default())
                .unwrap_or_else(|error| panic!("Michigan pre-rollover tick {tick}: {error}"));
            assert_eq!(
                report
                    .per_rule_fired
                    .iter()
                    .find(|(rule, _)| rule == "class-dynamics/a01-rollover-accumulation-smoke")
                    .map(|(_, fired)| *fired),
                Some(0),
                "the annual mechanics stay inert before tick 52"
            );
            assert_eq!(
                territory_value(&session, "territory/rate-accumulation").to_bits(),
                0.0_f64.to_bits(),
                "the annual accumulation rate stays at its seed before rollover"
            );
        }

        let phi_adjustment = territory_value(&session, "territory/phi-savings-adjustment");
        assert!(
            phi_adjustment > 0.0 && phi_adjustment < 0.05,
            "the uncapped Phi-to-savings gradient must be live before rollover"
        );

        let report = session
            .advance(&mut CollectingSink::default())
            .expect("Michigan tick 52 must cross the annual boundary");
        assert_eq!(
            report
                .per_rule_fired
                .iter()
                .find(|(rule, _)| rule == "class-dynamics/a01-rollover-accumulation-smoke")
                .map(|(_, fired)| *fired),
            Some(1),
            "the real class-dynamics accumulation path fires at tick 52"
        );
        assert_eq!(
            territory_value(&session, "territory/dist-year").to_bits(),
            2011.0_f64.to_bits(),
            "the annual distribution year advances exactly once"
        );
        let rate = territory_value(&session, "territory/rate-accumulation");
        assert!(
            rate > 0.0 && rate < 0.08,
            "wage, Phi, and savings must produce a bounded accumulation rate"
        );
    }

    #[test]
    fn michigan_smoke_restarts_at_the_initial_rollover_and_terminal_boundaries() {
        assert_eq!(MICHIGAN_SMOKE_TICKS, 60);
        assert_eq!(MICHIGAN_SMOKE_RESTART_TICKS, [1, 51, 52, 60]);
    }

    #[test]
    fn report_jsonl_is_deterministic_flushed_and_secret_safe() {
        let first_path = report_path("first");
        let second_path = report_path("second");
        let report = report_fixture();
        let mut first = TickReportJsonlWriter::create(&first_path).expect("new first report path");
        first.write_report(&report).expect("first report row");
        let first_bytes = std::fs::read(&first_path).expect("flushed first report row");
        let mut second =
            TickReportJsonlWriter::create(&second_path).expect("new second report path");
        second.write_report(&report).expect("second report row");
        let second_bytes = std::fs::read(&second_path).expect("flushed second report row");

        assert_eq!(first_bytes, second_bytes);
        assert_eq!(first_bytes.last(), Some(&b'\n'));
        let row: serde_json::Value =
            serde_json::from_slice(&first_bytes).expect("one valid JSON object");
        assert_eq!(row["schema"], TICK_REPORT_SCHEMA_V1);
        assert_eq!(row["resolve_tick"], 7);
        assert_eq!(
            row["commit_disposition"],
            "reconciled_after_ambiguous_commit"
        );
        assert_eq!(row["rules"]["considered"], 5);
        assert_eq!(row["rules"]["fired"], 3);
        assert_eq!(row["rules"]["per_rule"][0]["considered"], 2);
        assert_eq!(row["rules"]["per_rule"][0]["fired"], 1);
        assert_eq!(row["events"]["count"], 1);
        assert_eq!(row["audit_receipts"]["count"], 2);
        assert_eq!(row["material_rows"]["count"], 9);
        let rendered = String::from_utf8(first_bytes).expect("report is UTF-8");
        for forbidden in [
            "BABYLON_RUNTIME_DSN",
            "postgres://",
            "hostname",
            "timestamp",
        ] {
            assert!(!rendered.contains(forbidden), "leaked {forbidden}");
        }

        drop(first);
        drop(second);
        std::fs::remove_file(first_path).expect("remove first report fixture");
        std::fs::remove_file(second_path).expect("remove second report fixture");
    }

    #[test]
    fn report_jsonl_refuses_to_overwrite_an_existing_path() {
        let path = report_path("existing");
        let writer = TickReportJsonlWriter::create(&path).expect("new report path");

        assert!(TickReportJsonlWriter::create(&path).is_err());

        drop(writer);
        std::fs::remove_file(path).expect("remove report fixture");
    }

    #[test]
    fn report_jsonl_write_failure_names_the_already_durable_tick() {
        let path = report_path("read-only");
        std::fs::write(&path, b"").expect("create read-only report fixture");
        let read_only = std::fs::File::open(&path).expect("open fixture without write access");
        let mut writer = TickReportJsonlWriter {
            output: std::io::BufWriter::new(read_only),
        };

        let error = writer
            .write_report(&report_fixture())
            .expect_err("read-only report must refuse the acknowledged row");

        assert_eq!(error, "tick report JSONL write failed after durable tick 7");
        std::fs::remove_file(path).expect("remove read-only report fixture");
    }

    #[test]
    fn production_commands_accept_the_closed_supported_surface() {
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
            Ok(Command::Run {
                ticks: 5,
                report_jsonl: None,
            })
        );
        assert_eq!(
            parse_command(
                vec![
                    "run".into(),
                    "--report-jsonl".into(),
                    "report.jsonl".into(),
                    "--ticks".into(),
                    "5".into(),
                ]
                .into_iter()
            ),
            Ok(Command::Run {
                ticks: 5,
                report_jsonl: Some("report.jsonl".into()),
            })
        );
        assert_eq!(
            parse_command(
                vec![
                    "run".into(),
                    "--ticks".into(),
                    "5".into(),
                    "--report-jsonl".into(),
                    "report.jsonl".into(),
                ]
                .into_iter()
            ),
            Ok(Command::Run {
                ticks: 5,
                report_jsonl: Some("report.jsonl".into()),
            })
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
            Ok(Command::MichiganSmoke { report_jsonl: None })
        );
        assert_eq!(
            parse_command(
                vec![
                    "michigan-smoke".into(),
                    "--report-jsonl".into(),
                    "report.jsonl".into(),
                ]
                .into_iter()
            ),
            Ok(Command::MichiganSmoke {
                report_jsonl: Some("report.jsonl".into()),
            })
        );
    }

    #[test]
    fn production_commands_refuse_invalid_or_ambiguous_arguments() {
        assert_eq!(parse_command(Vec::new().into_iter()), Err(()));
        assert_eq!(parse_command(vec!["run".into()].into_iter()), Err(()));
        assert_eq!(
            parse_command(vec!["run".into(), "--ticks".into(), "0".into()].into_iter()),
            Err(())
        );
        assert_eq!(
            parse_command(
                vec![
                    "run".into(),
                    "--ticks".into(),
                    "5".into(),
                    "--ticks".into(),
                    "6".into(),
                ]
                .into_iter()
            ),
            Err(())
        );
        assert_eq!(
            parse_command(
                vec![
                    "michigan-smoke".into(),
                    "--report-jsonl".into(),
                    "first.jsonl".into(),
                    "--report-jsonl".into(),
                    "second.jsonl".into(),
                ]
                .into_iter()
            ),
            Err(())
        );
        assert_eq!(
            parse_command(vec!["michigan-smoke".into(), "--unknown".into()].into_iter()),
            Err(())
        );
        assert_eq!(parse_command(vec!["unknown".into()].into_iter()), Err(()));
    }
}
