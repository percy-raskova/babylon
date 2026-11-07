//! National allocation publication and exact replay on an operator-owned SQL clone.

use super::{TestDatabase, ACK, ACK_ENV, CANARY_ENV, DSN_ENV, TEMPLATE_DB_ENV};
use crate::economic_catalog::{self, CapturedEconomicCatalog};
use crate::identity::CampaignId;
use crate::material_runtime::{
    CommitFault, DurableMaterialRuntime, MaterialRuntimeError, COMMIT_FAULT,
};
use crate::material_storage::{self, LookupAnchor, OpeningRegister};
use crate::organizer_runtime::OrganizerSnapshot;
use crate::qualification_audit::aid::Accepted;
use crate::qualification_audit::aid::Audit;
use crate::runtime_session::RuntimeSessionErrorCode;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::CashTransferPurpose;
use babylon_material_circuit::HouseholdConsumptionReceipt;
use babylon_material_circuit::HouseholdDemandReceipt;
use babylon_material_circuit::ServicePerformanceReceipt;
use babylon_material_circuit::{
    AccountId, AidOutcome, CircuitAccounting, FinalDemandPrincipalId, GoodId, MoneyLocation,
    MoneyTransferPurpose, OrganizationAccountId, OutboundOrderId,
};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_practice_contract::OrganizerObservation;
use babylon_practice_contract::OrganizerReceipt;
use babylon_practice_contract::{
    OrganizerAidKind, OrganizerAllocation, OrganizerChoice, OrganizerCommand, OrganizerCommitment,
    OrganizerOutcome,
};
use babylon_tick::material_world::MaterialReceiptHandle;
use babylon_tick::material_world::MaterialTickReceipts;
use babylon_tick::replay_session::ReplayCommitDisposition;
use fallible_iterator::FallibleIterator;
use postgres::config::Host;
use postgres::error::DbError;
use postgres::Transaction;
use postgres::{Client, Config, GenericClient, IsolationLevel, NoTls};
use serde::{Deserialize, Serialize};
use serde_json::Map;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::env;
use std::error::Error;
use std::fmt::Debug;
use std::fs::{self, DirBuilder, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Component, Path, PathBuf};
use std::result::Result as StdResult;
use std::str::FromStr;
use uuid::Uuid;

type Result<T> = StdResult<T, Box<dyn Error>>;
const EXACT: &str = "runtime::live_tests::organizer_allocation_atomic::national_collection_and_local_cash_survive_sql_retries";
const RUN: &str = "/media/user/data/worktrees/per364-wayne-solidarity-loop/qualification-01/sql-01";
const CASH: i128 = 1_450_000_000;
const STAGES: [&str; 21] = [
    "bootstrap",
    "clone",
    "schema",
    "foundation",
    "collect_preview",
    "collect_submit",
    "collect_conflict",
    "collect_pending_open",
    "p1_close",
    "aid_preview",
    "aid_submit",
    "aid_food_conflict",
    "aid_cash_conflict",
    "aid_pending_open",
    "stale_open",
    "p2_marker_rollback",
    "rollback_open",
    "p2_after_commit",
    "p2_stale_retry",
    "p2_completed_open",
    "p3_purchase",
];

fn check(condition: bool, reason: &str) -> Result<()> {
    if condition {
        Ok(())
    } else {
        Err(reason.into())
    }
}
fn same<T: PartialEq + Debug>(observed: &T, expected: &T, field: &str) -> Result<()> {
    if observed == expected {
        Ok(())
    } else {
        Err(format!("{field}: expected {expected:?}, observed {observed:?}").into())
    }
}
fn debug_error(error: impl Debug) -> Box<dyn Error> {
    format!("{error:?}").into()
}
fn hex(bytes: &[u8]) -> String {
    crate::michigan_economy::digest_hex(bytes)
}
fn hash(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}
fn hex_field(value: &str, len: usize) -> bool {
    value.len() == len
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
struct Artifact {
    path: String,
    bytes: u64,
    sha256: String,
}
#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
struct Db {
    name: String,
    oid: u32,
    owner_oid: u32,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Fixture {
    tag: String,
    focus: String,
    test: String,
    checkout: PathBuf,
    run: PathBuf,
    evidence: PathBuf,
    source_head: String,
    source: Artifact,
    inputs: Artifact,
    policy: Artifact,
    physical: Artifact,
    executable: Artifact,
    host: String,
    host_port: u16,
    container_port: u16,
    canary: String,
    ack: String,
    data_directory: String,
    cluster: String,
    login: String,
    role_oid: u32,
    bootstrap: Db,
    template: Db,
    campaign: String,
    preset: String,
    session: String,
    seed: u64,
}

fn file_identity(path: &Path, name: &str) -> Result<Artifact> {
    check(
        fs::symlink_metadata(path)?.is_file(),
        "evidence must be a regular file",
    )?;
    stream_identity(File::open(path)?, name)
}
fn stream_identity(file: File, name: &str) -> Result<Artifact> {
    let mut input = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut bytes = 0u64;
    loop {
        let chunk = input.fill_buf()?;
        if chunk.is_empty() {
            break;
        }
        hasher.update(chunk);
        let count = chunk.len();
        bytes = bytes
            .checked_add(u64::try_from(count)?)
            .ok_or("artifact byte length overflow")?;
        input.consume(count);
    }
    Ok(Artifact {
        path: name.to_owned(),
        bytes,
        sha256: hex(&hasher.finalize()),
    })
}
fn verify_ref(base: &Path, reference: &Artifact) -> Result<()> {
    let sub = Path::new(&reference.path);
    check(
        !sub.as_os_str().is_empty() && sub.components().all(|c| matches!(c, Component::Normal(_))),
        "unconfined evidence reference",
    )?;
    let target = base.join(sub);
    check(
        target.canonicalize()? == target && target.starts_with(base),
        "symlinked evidence reference",
    )?;
    same(
        &file_identity(&target, &reference.path)?,
        reference,
        "artifact readback",
    )
}
fn validate_bootstrap(config: &Config, port: u16) -> Result<()> {
    crate::postgres_catalog::validate_connection_target(config)?;
    check(
        matches!(config.get_hosts(),[Host::Tcp(ip)] if ip=="127.0.0.1")
            && config.get_ports() == [port]
            && port != 0
            && config.get_user() == Some("test")
            && config.get_dbname() == Some("postgres"),
        "bootstrap DSN differs from frozen test/postgres endpoint",
    )
}

impl Fixture {
    fn load() -> Result<(Self, Artifact, Config, CampaignId)> {
        let path = PathBuf::from(env::var("BABYLON_SQL_FIXTURE_FILE")?);
        let basis = Path::new(RUN).join("evidence");
        check(
            path == basis.join("sql-fixture-v1.json") && path.canonicalize()? == path,
            "unexpected or linked SQL fixture path",
        )?;
        let bytes = fs::read(&path)?;
        let digest = hash(&bytes);
        same(
            &digest,
            &env::var("BABYLON_SQL_FIXTURE_SHA256")?,
            "pinned fixture bytes",
        )?;
        let fixture: Self = serde_json::from_slice(&bytes)?;
        let checkout = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../..")
            .canonicalize()?;
        let template = format!(
            "per281_runtime_template_{}",
            fixture.canary.get(..12).ok_or("short canary")?
        );
        check(
            fixture.tag == "sql-fixture-v1"
                && fixture.focus == "organizer_allocation_atomic"
                && fixture.test == EXACT
                && fixture.run == Path::new(RUN)
                && fixture.evidence == basis
                && fixture.checkout == checkout
                && env::current_dir()?.canonicalize()? == checkout.join("rust")
                && hex_field(&fixture.source_head, 40),
            "fixture source/run/test identity",
        )?;
        check(
            hex_field(&fixture.canary, 32)
                && fixture.canary == env::var(CANARY_ENV)?
                && fixture.ack == ACK
                && fixture.ack == env::var(ACK_ENV)?
                && fixture.template.name == template
                && template == env::var(TEMPLATE_DB_ENV)?
                && fixture.template.owner_oid == fixture.role_oid
                && fixture.role_oid != 0
                && fixture.template.oid != 0
                && fixture.bootstrap.oid != 0
                && fixture.bootstrap.owner_oid != 0
                && fixture.template.oid != fixture.bootstrap.oid
                && fixture.bootstrap.name == "postgres"
                && fixture.login == "test"
                && fixture.host == "127.0.0.1"
                && fixture.container_port == 5432
                && fixture.data_directory == "/var/lib/postgresql/data"
                && fixture.cluster.parse::<u64>()?.to_string() == fixture.cluster
                && fixture.cluster != "0"
                && fixture.session == "national-independent-aid"
                && fixture.seed == 319
                && fixture.preset == "national-world",
            "invalid SQL fixture identities",
        )?;
        let uuid = Uuid::parse_str(&fixture.campaign)?;
        check(
            !uuid.is_nil() && uuid.to_string() == fixture.campaign,
            "campaign UUID",
        )?;
        let paths = [
            &fixture.source.path,
            &fixture.inputs.path,
            &fixture.policy.path,
            &fixture.physical.path,
            &fixture.executable.path,
        ];
        check(
            paths.into_iter().collect::<BTreeSet<_>>().len() == 5,
            "fixture artifacts must be distinct",
        )?;
        for reference in [
            &fixture.source,
            &fixture.inputs,
            &fixture.policy,
            &fixture.physical,
            &fixture.executable,
        ] {
            verify_ref(&basis, reference)?;
        }
        let running = stream_identity(File::open("/proc/self/exe")?, &fixture.executable.path)?;
        same(&running, &fixture.executable, "running executable bytes")?;
        let config = Config::from_str(&env::var(DSN_ENV)?)?;
        validate_bootstrap(&config, fixture.host_port)?;
        let reference = Artifact {
            path: "sql-fixture-v1.json".into(),
            bytes: u64::try_from(bytes.len())?,
            sha256: digest,
        };
        Ok((fixture, reference, config, CampaignId::from_uuid(uuid)))
    }
}

#[test]
fn bootstrap_rejects_same_loopback_login_on_unowned_port() {
    let other = Config::from_str("host=127.0.0.1 port=49158 user=test dbname=postgres")
        .expect("explicit local target");
    assert!(validate_bootstrap(&other, 49157).is_err());
    validate_bootstrap(&other, 49158).expect("exactly pinned endpoint");
}

#[test]
fn retained_clone_is_disarmed_before_creation() {
    let mut clone = TestDatabase::retained_allocation(&Config::new());
    let previously_armed = std::mem::replace(&mut clone.active, false);
    assert!(!previously_armed, "retention must be armed before CREATE");
    assert!(
        clone.try_drop_database().is_err(),
        "uncreated or retained clone cannot be dropped"
    );
}

struct Journal {
    base: PathBuf,
    authority: Artifact,
    previous: Artifact,
    index: usize,
    proven: usize,
    attachments: Vec<Artifact>,
}
impl Journal {
    fn new(base: PathBuf, fixture: Artifact) -> Self {
        Self {
            base,
            authority: fixture.clone(),
            previous: fixture,
            index: 0,
            proven: 0,
            attachments: Vec::new(),
        }
    }
    fn put(&self, name: &str, bytes: &[u8]) -> Result<Artifact> {
        let final_path = self.base.join(name);
        let partial = self.base.join(format!("{name}.partial"));
        let mut f = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&partial)?;
        f.write_all(bytes)?;
        f.sync_all()?;
        drop(f);
        fs::hard_link(&partial, &final_path)?;
        fs::remove_file(&partial)?;
        File::open(&self.base)?.sync_all()?;
        let reference = Artifact {
            path: name.to_owned(),
            bytes: u64::try_from(bytes.len())?,
            sha256: hash(bytes),
        };
        verify_ref(&self.base, &reference)?;
        Ok(reference)
    }
    fn record(&self, name: &str, value: &Value) -> Result<Artifact> {
        self.put(name, &serde_json::to_vec(value)?)
    }
    fn blob(&mut self, bytes: &[u8]) -> Result<Artifact> {
        let digest = hash(bytes);
        let name = format!("bytes-{digest}");
        let item = Artifact {
            path: name.clone(),
            bytes: u64::try_from(bytes.len())?,
            sha256: digest,
        };
        if self.base.join(&name).try_exists()? {
            verify_ref(&self.base, &item)?;
            let mut existing = BufReader::new(File::open(self.base.join(&name))?);
            let mut remainder = bytes;
            loop {
                let chunk = existing.fill_buf()?;
                if chunk.is_empty() {
                    break;
                }
                remainder = remainder
                    .strip_prefix(chunk)
                    .ok_or("collision in exported canonical bytes")?;
                let len = chunk.len();
                existing.consume(len);
            }
            check(remainder.is_empty(), "short canonical export")?;
        } else {
            self.put(&name, bytes)?;
        }
        if !self.attachments.contains(&item) {
            self.attachments.push(item.clone());
        }
        Ok(item)
    }
    fn facts(&mut self, value: &Value) -> Result<Artifact> {
        self.blob(&serde_json::to_vec(value)?)
    }
    fn write_phase(&mut self, phase: &str) -> Result<()> {
        let stage = STAGES[self.index - 1];
        let name = format!("stage-{:02}-{stage}-{phase}.json", self.index);
        self.previous=self.record(&name,&json!({"tag":"sql-stage-v1","phase":phase,"index":self.index,"stage":stage,"previous":self.previous,"authority":self.authority,"artifacts":self.attachments}))?;
        Ok(())
    }
    fn begin(&mut self, stage: &str) -> Result<()> {
        same(
            &STAGES.get(self.index).copied(),
            &Some(stage),
            "stage order",
        )?;
        self.proven = self.index;
        self.index += 1;
        self.attachments.clear();
        self.write_phase("attempt")
    }
    fn reached(&mut self, observation: &Value) -> Result<()> {
        self.facts(observation)?;
        self.write_phase("reached")
    }
    fn diverged(&mut self, error: &str) -> Result<()> {
        if self.index > 0 && self.previous.path.ends_with("-attempt.json") {
            self.reached(&json!({"observation_error":error}))?;
        }
        let stage = self.index.checked_sub(1).map_or("bootstrap", |v| STAGES[v]);
        let last = self.proven.checked_sub(1).map_or("none", |v| STAGES[v]);
        self.record("first-divergence-v1.json",&json!({"tag":"sql-divergence-v1","stage":stage,"last_proven":last,"previous":self.previous,"authority":self.authority,"error":error,"artifacts":self.attachments}))?;
        Ok(())
    }
}

// Preserve the last durable stage if an existing runtime assertion unwinds.
// The harness retains the original panic location and message in its transcript.
impl Drop for Journal {
    fn drop(&mut self) {
        if std::thread::panicking() {
            if let Err(error) = self.diverged(
                "unexpected Rust panic; see the libtest transcript for its location and message",
            ) {
                eprintln!("could not export the interrupted SQL stage: {error}");
            }
        }
    }
}
#[test]
fn unexpected_panic_preserves_reached_stage_and_divergence() {
    use std::os::unix::fs::DirBuilderExt;
    use std::time::{SystemTime, UNIX_EPOCH};
    let serial = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let base = env::temp_dir().join(format!(
        "babylon-allocation-stage-{}-{serial}",
        std::process::id()
    ));
    DirBuilder::new()
        .mode(0o700)
        .create(&base)
        .expect("unique test evidence directory");
    let fixture = base.join("synthetic");
    fs::write(&fixture, b"synthetic failure evidence only").expect("synthetic input");
    let reference = file_identity(&fixture, "synthetic").expect("synthetic identity");
    let worker = base.clone();
    let outcome = std::thread::spawn(move || {
        let mut journal = Journal::new(worker, reference);
        journal.begin("bootstrap").expect("attempt recorded");
        panic!("synthetic panic before the first SQL connection");
    })
    .join();
    assert!(outcome.is_err());
    let divergence: Value = serde_json::from_slice(
        &fs::read(base.join("first-divergence-v1.json")).expect("panic preserved"),
    )
    .expect("JSON");
    assert_eq!(divergence["last_proven"], "none");
    assert_eq!(divergence["stage"], "bootstrap");
    let previous: Artifact =
        serde_json::from_value(divergence["previous"].clone()).expect("reached ref");
    assert_eq!(previous.path, "stage-01-bootstrap-reached.json");
    verify_ref(&base, &previous).expect("durable reached record");
    assert!(!base.join("in-test-seal-v1.json").exists());
    fs::remove_dir_all(base).expect("remove only this freshly created synthetic test directory");
}
fn db_identity(sql: &mut impl GenericClient, name: &str) -> Result<Db> {
    let r = sql.query_one(
        "SELECT datname::text,oid,datdba FROM pg_catalog.pg_database WHERE datname=$1",
        &[&name],
    )?;
    Ok(Db {
        name: r.try_get(0)?,
        oid: r.try_get(1)?,
        owner_oid: r.try_get(2)?,
    })
}
fn sql_identity(sql: &mut Client, fx: &Fixture, db: &Db) -> Result<Value> {
    let r=sql.query_one("SELECT session_user::text,current_user::text,current_database()::text,current_setting('babylon.disposable_runtime'),current_setting('data_directory'),(pg_control_system()).system_identifier::text,(SELECT oid FROM pg_roles WHERE rolname=session_user),inet_server_port()", &[])?;
    let found = db_identity(sql, &db.name)?;
    let value = json!({"session_user":r.try_get::<_,String>(0)?,"current_user":r.try_get::<_,String>(1)?,"database":r.try_get::<_,String>(2)?,"canary":r.try_get::<_,String>(3)?,"data_directory":r.try_get::<_,String>(4)?,"cluster":r.try_get::<_,String>(5)?,"role_oid":r.try_get::<_,u32>(6)?,"server_port":r.try_get::<_,i32>(7)?,"identity":found});
    let expected = json!({"session_user":fx.login,"current_user":fx.login,"database":db.name,"canary":fx.canary,"data_directory":fx.data_directory,"cluster":fx.cluster,"role_oid":fx.role_oid,"server_port":fx.container_port,"identity":db});
    same(&value, &expected, "connected SQL identity")?;
    Ok(value)
}
fn table_export(
    journal: &mut Journal,
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    table: &str,
    columns: &str,
    keys: &str,
) -> Result<Artifact> {
    // Text returned by this cluster preserves exact numeric/bytea payloads.
    // Keep each table separate so an investigator can locate the first changed row.
    let statement = format!(
        "SELECT row_to_json(r)::text FROM (SELECT {columns} FROM {table} \
         WHERE campaign_id=$1 ORDER BY {keys}) r"
    );
    let mut rows = tx.query_raw(&statement, [campaign.as_uuid()])?;
    let mut bytes = Vec::new();
    while let Some(row) = rows.next()? {
        bytes.extend_from_slice(row.try_get::<_, &str>(0)?.as_bytes());
        bytes.push(b'\n');
    }
    journal.blob(&bytes)
}

fn package_rows(
    journal: &mut Journal,
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
) -> Result<Vec<Value>> {
    let query = "SELECT resolve_tick, identity_bytes, register_storage_bytes, receipt_storage_bytes,
            lookup_delta_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1 ORDER BY resolve_tick";
    let mut periods = Vec::new();
    let mut rows = tx.query_raw(query, [campaign.as_uuid()])?;
    while let Some(package) = rows.next()? {
        let mut period = json!({"period":package.try_get::<_,i64>("resolve_tick")?});
        for column in [
            "identity_bytes",
            "register_storage_bytes",
            "receipt_storage_bytes",
            "lookup_delta_bytes",
        ] {
            let reference = journal.blob(package.try_get::<_, &[u8]>(column)?)?;
            period[column] = serde_json::to_value(reference)?;
        }
        periods.push(period);
    }
    Ok(periods)
}
fn durable(journal: &mut Journal, client: &mut Client, campaign: CampaignId) -> Result<Artifact> {
    let mut tx = client
        .build_transaction()
        .isolation_level(IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()?;
    tx.batch_execute("SET LOCAL search_path TO pg_catalog; SET LOCAL bytea_output TO hex")?;
    let mut tables = Map::new();
    let subjects = "actor_id,subject_kind,subject_id";
    let grants = "subject_kind,subject_id,grant_key";
    for (name,columns,keys) in [
        ("babylon_state.tick_commit","resolve_tick,envelope_layout_version,tick_content_hash,envelope_digest","resolve_tick"),
        ("babylon_state.archive_dirty_receipt_v1","resolve_tick,tick_content_hash","resolve_tick"),
        ("babylon_state.organizer_command_v1","nonce,resolves_period,command_bytes,commitment_bytes,commitment_sha256,consumed_period","nonce"),
        ("babylon_state.organizer_subject_v1","actor_id,subject_kind,subject_id,title",subjects),
        ("babylon_state.organizer_observation_v1","observation_id,actor_id,subject_id,observed_period,acquired_period,observation_bytes","observation_id"),
        ("babylon_state.organizer_receipt_v1","receipt_id,actor_id,resolve_tick,receipt_bytes","receipt_id"),
        ("babylon_state.organizer_encounter_v1","receipt_id,actor_id,subject_id,resolve_tick,encounter_bytes","receipt_id"),
        ("babylon_meta.archive_provenance_v1","provenance_ref,source_id,locator","provenance_ref"),
        ("babylon_meta.archive_atom_v1","atom_id,subject_kind,subject_id,signal_key,grant_key,evidence_class,value_kind,value_text,value_f64,value_u64,value_bool,provenance_ref,valid_tick","atom_id"),
        ("babylon_meta.archive_knowledge_grant_v1","subject_kind,subject_id,grant_key,granted_tick,provenance_ref",grants),
        ("babylon_meta.archive_knowledge_grant_witness_v1","subject_kind,subject_id,grant_key,granted_tick,provenance_source_id,provenance_locator",grants),
        ("babylon_state.event_manifest_v1","resolve_tick,event_count,field_count,parent_chunks,field_chunks","resolve_tick"),
        ("babylon_state.event_parent_chunk_v1","resolve_tick,chunk,event_ordinals,type_ids,rule_ids,choice_ordinals","resolve_tick,chunk"),
        ("babylon_state.event_field_chunk_v1","resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values,currency_values,real_bits,ratio_bits,ratio_mins,ratio_maxs,bool_values,enum_types,enum_members,key_ids,key_scenario_ids","resolve_tick,chunk"),
        ("babylon_state.event_text_lookup_v1","text_id,first_tick,marker_tick,value","text_id"),
        ("babylon_state.event_key_lookup_v1","key_id,first_tick,marker_tick,value","key_id"),
        ("babylon_state.checkpoint_manifest","resolve_tick,completeness_tag,manifest_sha256,manifest_bytes","resolve_tick"),
        ("babylon_state.checkpoint_section_v1","resolve_tick,section_tag,ordinal,source_tag,decoded_length,decoded_sha256,inline_section_bytes","resolve_tick,section_tag,ordinal"),
    ] {
        let exported=table_export(journal,&mut tx,campaign,name,columns,keys)?;
        tables.insert(name.into(),serde_json::to_value(exported)?);
    }
    tables.insert(
        "material_tick_v3".into(),
        Value::Array(package_rows(journal, &mut tx, campaign)?),
    );
    tx.commit()?;
    journal.facts(&json!({"campaign":campaign.as_uuid().to_string(),"tables":tables}))
}
#[derive(Debug, PartialEq, Serialize)]
struct Snapshot {
    period: u64,
    world: String,
    marker: Option<Artifact>,
    envelope: Option<String>,
    register: Artifact,
    organizer: Artifact,
    durable: Artifact,
}
fn snapshot(
    j: &mut Journal,
    runtime: &DurableMaterialRuntime,
    sql: &mut Client,
    campaign: CampaignId,
) -> Result<Snapshot> {
    let state = runtime.organizer_snapshot().map_err(debug_error)?;
    let register = j.blob(runtime.session().material().canonical_bytes())?;
    let snapshot = Snapshot {
        period: runtime.session().completed_tick(),
        world: hex(&runtime.session().current_world_hash()?),
        marker: runtime
            .tail()
            .map(|m| j.blob(m.canonical_bytes()))
            .transpose()?,
        envelope: runtime.tail_envelope_digest().map(|d| hex(&d)),
        register,
        organizer: j.facts(&serde_json::to_value(state)?)?,
        durable: durable(j, sql, campaign)?,
    };
    j.facts(&serde_json::to_value(&snapshot)?)?;
    Ok(snapshot)
}
fn original(
    snapshot: &OrganizerSnapshot,
    campaign: CampaignId,
    nonce: [u8; 16],
    choice: OrganizerChoice,
    allocation: OrganizerAllocation,
) -> OrganizerCommand {
    OrganizerCommand {
        campaign_id: *campaign.canonical_bytes(),
        actor_id: snapshot.view.actor_id,
        authority_id: snapshot.view.authority_id,
        expected_period: snapshot.view.period,
        content_digest: snapshot.view.content_digest,
        resource_digest: snapshot.view.resource_digest,
        nonce,
        choice,
        allocation,
    }
}
fn previews(
    j: &mut Journal,
    runtime: &DurableMaterialRuntime,
    commands: &[OrganizerCommand],
) -> Result<()> {
    let results = commands
        .iter()
        .map(|c| runtime.preview_organizer_command(c))
        .collect::<Vec<_>>();
    j.reached(&json!({"commands":commands,"previews":results}))?;
    for (command, preview) in commands.iter().zip(results) {
        let p = preview.map_err(debug_error)?;
        same(&p.choice, &command.choice, "preview choice")?;
        same(&p.allocation, &command.allocation, "preview allocation")?;
        same(&p.refusal, &None, "otherwise admissible command")?;
        same(
            &p.current_period,
            &command.expected_period,
            "preview period",
        )?;
        same(
            &p.resolves_period,
            &(command.expected_period + 1),
            "preview close",
        )?;
    }
    Ok(())
}
fn admission(
    j: &mut Journal,
    rt: &DurableMaterialRuntime,
    sql: &mut Client,
    campaign: CampaignId,
    command: &OrganizerCommand,
    consumed: Option<i64>,
    expected: Option<&OrganizerCommitment>,
) -> Result<OrganizerCommitment> {
    let first = rt.submit_organizer_command(command);
    let retry = rt.submit_organizer_command(command);
    j.facts(&json!({"command":command,"first":first,"exact_retry":retry}))?;
    let rows=sql.query("SELECT command_bytes,commitment_bytes,commitment_sha256,consumed_period,resolves_period,nonce FROM babylon_state.organizer_command_v1 WHERE campaign_id=$1 AND (nonce=$2 OR resolves_period=$3) ORDER BY nonce",&[campaign.as_uuid(),&&command.nonce[..],&i64::try_from(command.expected_period+1)?])?;
    let mut stored = Vec::new();
    for row in &rows {
        stored.push(json!({"command":j.blob(&row.try_get::<_,Vec<u8>>(0)?)?,"commitment":j.blob(&row.try_get::<_,Vec<u8>>(1)?)?,"id":hex(&row.try_get::<_,Vec<u8>>(2)?),"consumed":row.try_get::<_,Option<i64>>(3)?,"resolves":row.try_get::<_,i64>(4)?,"nonce":hex(&row.try_get::<_,Vec<u8>>(5)?)}));
    }
    j.facts(&json!({"stored":stored}))?;
    let first = first.map_err(debug_error)?;
    same(
        &retry.map_err(debug_error)?,
        &first,
        "exact retry commitment",
    )?;
    if let Some(original) = expected {
        same(&first, original, "persisted original")?;
    }
    let [row] = rows.as_slice() else {
        return Err(format!("original has {} rows", rows.len()).into());
    };
    same(
        &row.try_get::<_, Vec<u8>>(0)?,
        &serde_json::to_vec(command)?,
        "command bytes",
    )?;
    same(
        &row.try_get::<_, Vec<u8>>(1)?,
        &serde_json::to_vec(&first)?,
        "commitment bytes",
    )?;
    same(
        &row.try_get::<_, Vec<u8>>(2)?,
        &first.commitment_id.to_vec(),
        "stored commitment identity",
    )?;
    same(
        &row.try_get::<_, Option<i64>>(3)?,
        &consumed,
        "consumed period",
    )?;
    Ok(first)
}
fn conflict(
    j: &mut Journal,
    rt: &DurableMaterialRuntime,
    sql: &mut Client,
    campaign: CampaignId,
    changed: &OrganizerCommand,
    before: &Snapshot,
) -> Result<()> {
    let r = rt.submit_organizer_command(changed);
    j.facts(&json!({"changed":changed,"result":r}))?;
    let after = snapshot(j, rt, sql, campaign)?;
    j.reached(&json!({"result":r,"expected":before,"observed":after}))?;
    same(
        &r,
        &Err(RuntimeSessionErrorCode::OrganizerNonceConflict),
        "changed amount under identical nonce",
    )?;
    same(&after, before, "rows and pending original after conflict")
}
fn open_pending(
    j: &mut Journal,
    case: &mut Case,
    old: DurableMaterialRuntime,
    commitment: &OrganizerCommitment,
    before: &Snapshot,
) -> Result<DurableMaterialRuntime> {
    let batch = j.blob(old.next_action_batch()?.canonical_bytes())?;
    drop(old);
    let rt = DurableMaterialRuntime::open(&case.config, case.campaign, case.digest)?;
    let reopened = snapshot(j, &rt, &mut case.sql, case.campaign)?;
    let current = rt.organizer_snapshot().map_err(debug_error)?;
    let actual = j.blob(rt.next_action_batch()?.canonical_bytes())?;
    admission(
        j,
        &rt,
        &mut case.sql,
        case.campaign,
        &commitment.command,
        None,
        Some(commitment),
    )?;
    let after_retry = snapshot(j, &rt, &mut case.sql, case.campaign)?;
    j.reached(&json!({"before":before,"reopened":reopened,"after_retry":after_retry,"batch":actual,"expected_batch":batch,"pending":current.pending}))?;
    same(&reopened, before, "fresh pending reopen")?;
    same(
        &after_retry,
        before,
        "exact retry preserves durable pending state",
    )?;
    same(
        &current.pending.as_ref(),
        &Some(commitment),
        "fresh pending original",
    )?;
    same(&actual, &batch, "fresh pending exact action batch")?;
    Ok(rt)
}
struct PeriodReader {
    opening: OpeningRegister,
    chain: [u8; 32],
}
impl PeriodReader {
    fn capture(rt: &DurableMaterialRuntime) -> Result<Self> {
        let opening = OpeningRegister::from_opening(rt.session().material())?;
        Ok(Self {
            chain: material_storage::initial_lookup_chain(&opening)?,
            opening,
        })
    }
    fn receipts(
        &mut self,
        j: &mut Journal,
        rt: &DurableMaterialRuntime,
        sql: &mut Client,
        campaign: CampaignId,
    ) -> Result<MaterialTickReceipts> {
        let identity = rt.tail().ok_or("missing committed identity")?;
        let tick = identity.resolve_tick();
        let row=sql.query_one("SELECT identity_bytes,receipt_storage_bytes,lookup_delta_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1 AND resolve_tick=$2",&[campaign.as_uuid(),&i64::try_from(tick)?])?;
        let id: Vec<u8> = row.try_get(0)?;
        same(
            &id.as_slice(),
            &identity.canonical_bytes(),
            "stored tick identity",
        )?;
        let lookup = material_storage::read_period_lookup(
            &self.opening,
            tick,
            &row.try_get::<_, Vec<u8>>(2)?,
            LookupAnchor::Previous(self.chain),
        )?;
        let (bytes, receipts) =
            crate::receipt_storage::decode_admitted(&row.try_get::<_, Vec<u8>>(1)?, &lookup.lookup)
                .map_err(debug_error)?;
        let raw = j.blob(&bytes)?;
        same(
            &raw.sha256,
            &hex(&identity.receipt_digest()),
            "committed canonical receipts",
        )?;
        same(&receipts.resolve_tick, &tick, "receipt period")?;
        self.chain = lookup.chain;
        Ok(receipts)
    }
}

fn treasury(rt: &DurableMaterialRuntime) -> Result<i128> {
    let state = rt.session().material();
    let cfg = state.organizer_config().ok_or("missing organizer")?;
    let account = cfg
        .collection
        .as_ref()
        .ok_or("missing collection authority")?
        .organization_account_id;
    let CircuitAccounting::Monetary(economy) = &state.state().accounting else {
        return Err("missing monetary register".into());
    };
    Ok(economy
        .book
        .cash(AccountId::Organization(OrganizationAccountId::from_bytes(
            account,
        )))?
        .micro_units())
}
fn audit_period(
    j: &mut Journal,
    audit: &mut Audit,
    rt: &DurableMaterialRuntime,
    campaign: CampaignId,
    receipts: MaterialTickReceipts,
) -> Result<()> {
    let register = rt.session().material();
    let CircuitAccounting::Monetary(economy) = &register.state().accounting else {
        return Err("missing monetary book".into());
    };
    let babylon_material_circuit::HouseholdTimeAccounting::Modeled(book) = &economy.household_time
    else {
        return Err("missing contribution book".into());
    };
    let admitted = crate::observer_reader::CommittedMaterialReceipts {
        campaign_id: campaign,
        identity: *rt.tail().ok_or("missing tail")?,
        material_register_bytes: register.canonical_bytes().len(),
        receipts: MaterialReceiptHandle::new(receipts),
        household_contributions: book.contributions.clone(),
    };
    let result = audit.read(
        rt.session().catalog(),
        &admitted,
        register,
        &rt.organizer_snapshot().map_err(debug_error)?,
    );
    j.facts(&json!({"audit":result.as_ref().map_err(|e|format!("{e:?}")),"time_debits":format!("{:?}",admitted.household_contributions)}))?;
    result.map_err(debug_error)?;
    Ok(())
}
fn collection(
    j: &mut Journal,
    rt: &DurableMaterialRuntime,
    rows: &MaterialTickReceipts,
    original: &OrganizerCommitment,
) -> Result<()> {
    let [gift] = rows.collections.as_slice() else {
        return Err(format!("unexpected collection receipts: {:?}", rows.collections).into());
    };
    let payer = AccountId::Household(gift.donor);
    let receiver = AccountId::Organization(gift.recipient);
    let refunds = rows
        .money_transfers
        .iter()
        .filter(|r| {
            matches!(
                r.purpose,
                MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::Service(_))
            ) && r.credit.location == MoneyLocation::Cash(payer)
        })
        .collect::<Vec<_>>();
    let transferred = rows
        .money_transfers
        .iter()
        .filter(|r| {
            r.debit.location == MoneyLocation::Cash(payer)
                && r.credit.location == MoneyLocation::Cash(receiver)
                && r.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
        })
        .collect::<Vec<_>>();
    j.facts(&json!({"collection":format!("{gift:?}"),"funded_transfer":format!("{transferred:?}"),"protected_refunds":format!("{refunds:?}"),"balance_micros":treasury(rt)?.to_string()}))?;
    same(
        &(
            gift.original_commitment_id,
            gift.command_nonce,
            gift.period,
            gift.requested.micro_units(),
            gift.collected.micro_units(),
            gift.performed_hours,
        ),
        &(
            original.commitment_id,
            original.command.nonce,
            1,
            CASH,
            CASH,
            2,
        ),
        "P1 collection",
    )?;
    let [movement] = transferred.as_slice() else {
        return Err("one original donor transfer required".into());
    };
    same(
        &(
            movement.debit.delta.micro_units(),
            movement.credit.delta.micro_units(),
        ),
        &(-CASH, CASH),
        "gift debits and credits",
    )?;
    let [refund] = refunds.as_slice() else {
        return Err("one protected service refund required".into());
    };
    same(
        &(
            refund.debit.delta.micro_units(),
            refund.credit.delta.micro_units(),
        ),
        &(-75_000_000, 75_000_000),
        "P1 service refund",
    )?;
    same(&treasury(rt)?, &1_451_000_000, "P1 organization treasury")
}
fn response(rt: &DurableMaterialRuntime, cmd: &OrganizerCommitment) -> Result<OrganizerReceipt> {
    let snapshot = rt.organizer_snapshot().map_err(debug_error)?;
    let mut matching = snapshot
        .aid_resolutions
        .iter()
        .filter(|r| r.pending.original_commitment_id == cmd.commitment_id);
    let result = matching.next().ok_or("missing cash recipient response")?;
    check(
        matching.next().is_none(),
        "cash recipient has duplicate responses",
    )?;
    let posts = &result.support.material_postings;
    same(
        &(
            posts.payer_cash_granted_micros,
            posts.fulfillment_hours,
            posts.dispatched_quantity,
        ),
        &(CASH, 0, 0),
        "P2 settled cash and food/time legs",
    )?;
    let response = &result.practice;
    same(
        &(response.period, response.commitment_id),
        &(2, Some(cmd.commitment_id)),
        "first response original and date",
    )?;
    check(
        matches!(
            response.outcome,
            OrganizerOutcome::AidPracticeCompleted
                | OrganizerOutcome::AidPracticeUncompleted
                | OrganizerOutcome::InsufficientTime
        ),
        "positive settlement needs adjudicated partner decision",
    )?;
    Ok(response.clone())
}
fn settlement(
    j: &mut Journal,
    rt: &DurableMaterialRuntime,
    rows: &MaterialTickReceipts,
    cmd: &OrganizerCommitment,
) -> Result<()> {
    let snap = rt.organizer_snapshot().map_err(debug_error)?;
    let projected = snap
        .aid_resolutions
        .iter()
        .find(|r| r.pending.original_commitment_id == cmd.commitment_id)
        .ok_or("missing local aid projection")?;
    let originals = rows
        .aid
        .iter()
        .filter(|r| r.commitment_id.as_bytes() == projected.pending.material_commitment_id)
        .collect::<Vec<_>>();
    let settled = originals
        .iter()
        .filter(|r| r.outcome == AidOutcome::CashGranted)
        .collect::<Vec<_>>();
    j.facts(&json!({"resolved_original":projected,"actual_aid_receipts":format!("{originals:?}"),"balance_micros":treasury(rt)?.to_string()}))?;
    let [cash] = settled.as_slice() else {
        return Err("expected exactly one cash settlement".into());
    };
    same(
        &(cash.cash_amount.micro_units(), cash.period),
        &(CASH, 2),
        "settlement of original",
    )?;
    check(
        originals.iter().all(|r| {
            matches!(
                r.outcome,
                AidOutcome::CashGranted | AidOutcome::CashRequested
            ) && r.quantity == 0
                && r.contribution_hours == 0
        }),
        "unexpected food or time debit",
    )?;
    same(&treasury(rt)?, &1_000_000, "P2 organization treasury")?;
    response(rt, cmd)?;
    Ok(())
}
fn good(name: &str) -> GoodId {
    let mut digest = Sha256::new();
    digest.update(b"NationalGoodV1\0");
    digest.update(name.as_bytes());
    GoodId::from_bytes(digest.finalize().into())
}
fn paid(
    rows: &MaterialTickReceipts,
    purpose: MoneyTransferPurpose,
    from: MoneyLocation,
    to: MoneyLocation,
) -> Result<i128> {
    let payments = rows
        .money_transfers
        .iter()
        .filter(|r| r.purpose == purpose)
        .collect::<Vec<_>>();
    let [payment] = payments.as_slice() else {
        return Err(format!("expected one {purpose:?}, observed {payments:?}").into());
    };
    let amount = payment.credit.delta.micro_units();
    same(
        &(payment.debit.location, payment.credit.location),
        &(from, to),
        "purchase cash endpoints",
    )?;
    check(
        amount > 0 && payment.debit.delta.micro_units() == -amount,
        "unbalanced payment",
    )?;
    Ok(amount)
}
fn purchases(
    j: &mut Journal,
    rt: &DurableMaterialRuntime,
    rows: &MaterialTickReceipts,
) -> Result<()> {
    let register = rt.session().material();
    let local = register
        .organizer_config()
        .ok_or("missing organizer")?
        .aid_bindings
        .iter()
        .find(|b| b.kind == OrganizerAidKind::Local)
        .ok_or("missing local binding")?;
    let recipient = FinalDemandPrincipalId::from_bytes(local.recipient_principal_id);
    let buyer = AccountId::Household(recipient);
    let demand = rows
        .household_demand
        .iter()
        .filter(|r| r.principal_id == recipient)
        .collect::<Vec<_>>();
    let services = rows
        .service_performance
        .iter()
        .filter(|r| r.buyer == buyer)
        .collect::<Vec<_>>();
    let use_rows = rows
        .household_consumption
        .iter()
        .filter(|r| r.principal_id == recipient)
        .collect::<Vec<_>>();
    let snapshot = rt.organizer_snapshot().map_err(debug_error)?;
    let reports = snapshot
        .view
        .observations
        .iter()
        .filter(|r| r.subject_id == local.partner.actor_id && r.observed_period == 3)
        .collect::<Vec<_>>();
    let orders = demand
        .iter()
        .map(|r| OutboundOrderId::LocalFinalDemand(r.order_id))
        .chain(
            services
                .iter()
                .map(|r| OutboundOrderId::Service(r.order_id)),
        )
        .collect::<BTreeSet<_>>();
    let moves = rows
        .money_transfers
        .iter()
        .filter(|r| match r.purpose {
            MoneyTransferPurpose::PurchaseReservation(id)
            | MoneyTransferPurpose::DeliverySettlement(id)
            | MoneyTransferPurpose::PurchaseRefund(id) => orders.contains(&id),
            _ => false,
        })
        .collect::<Vec<_>>();
    j.facts(&json!({"scope":hex(&recipient.as_bytes()),"orders":format!("{demand:?}"),"consumption":format!("{use_rows:?}"),"service":format!("{services:?}"),"postings":format!("{moves:?}"),"authorized_reports":reports}))?;
    let supply = demand
        .iter()
        .find(|r| r.good_id == good("materials"))
        .ok_or("missing manufactured supplies")?;
    let food = demand
        .iter()
        .find(|r| r.good_id == good("food"))
        .ok_or("missing food order")?;
    let use_goods = use_rows
        .iter()
        .find(|r| r.good_id == supply.good_id && r.unit_id == supply.unit_id)
        .ok_or("missing supplies consumption")?;
    let use_food = use_rows
        .iter()
        .find(|r| r.good_id == food.good_id && r.unit_id == food.unit_id)
        .ok_or("missing food use")?;
    let buyer_cash = MoneyLocation::Cash(buyer);
    manufactured_purchase(rows, buyer_cash, supply, use_goods)?;
    same(
        &(food.admitted_quantity, use_food.unmet_quantity),
        &(0, 4),
        "P3 food remains unmet",
    )?;
    let utility = services
        .iter()
        .find(|r| r.good_id == good("utility"))
        .ok_or("missing utility service")?;
    let (settle, refund) = utility_purchase(rows, buyer_cash, utility)?;
    disclosed_purchases(
        reports,
        snapshot.view.actor_id,
        food,
        use_food,
        utility,
        settle,
        refund,
    )
}
fn manufactured_purchase(
    rows: &MaterialTickReceipts,
    buyer_cash: MoneyLocation,
    supply: &HouseholdDemandReceipt,
    use_goods: &HouseholdConsumptionReceipt,
) -> Result<()> {
    let order = OutboundOrderId::LocalFinalDemand(supply.order_id);
    same(
        &(
            supply.admitted_quantity,
            supply.fulfilled_quantity,
            supply.unit_price.micro_units(),
            use_goods.consumed_quantity,
            use_goods.closing_quantity,
        ),
        &(8, 8, 147_000_000, 4, 4),
        "P3 manufactured supplies",
    )?;
    let reserve = MoneyLocation::PurchaseReserve(order);
    let retail = MoneyLocation::Cash(AccountId::Site(supply.retailer_site_id));
    same(
        &paid(
            rows,
            MoneyTransferPurpose::PurchaseReservation(order),
            buyer_cash,
            reserve,
        )?,
        &1_176_000_000,
        "P3 supplies reservation",
    )?;
    same(
        &paid(
            rows,
            MoneyTransferPurpose::DeliverySettlement(order),
            reserve,
            retail,
        )?,
        &1_176_000_000,
        "P3 supplies payment",
    )?;
    Ok(())
}
fn utility_purchase(
    rows: &MaterialTickReceipts,
    buyer_cash: MoneyLocation,
    utility: &ServicePerformanceReceipt,
) -> Result<(i128, i128)> {
    let order = OutboundOrderId::Service(utility.order_id);
    let reserve = MoneyLocation::PurchaseReserve(order);
    let provider = MoneyLocation::Cash(AccountId::Site(utility.provider_site_id));
    let settle = paid(
        rows,
        MoneyTransferPurpose::DeliverySettlement(order),
        reserve,
        provider,
    )?;
    let refund = paid(
        rows,
        MoneyTransferPurpose::PurchaseRefund(order),
        reserve,
        buyer_cash,
    )?;
    let reserved = paid(
        rows,
        MoneyTransferPurpose::PurchaseReservation(order),
        buyer_cash,
        reserve,
    )?;
    same(
        &reserved,
        &settle
            .checked_add(refund)
            .ok_or("service payment overflow")?,
        "P3 utility principal",
    )?;
    same(
        &(
            utility.admitted_quantity,
            utility.performed_quantity,
            settle,
            refund,
        ),
        &(3, 1, 75_000_000, 150_000_000),
        "P3 utility service and refund",
    )?;
    Ok((settle, refund))
}

fn disclosed_purchases(
    reports: Vec<&OrganizerObservation>,
    actor: u64,
    food: &HouseholdDemandReceipt,
    use_food: &HouseholdConsumptionReceipt,
    utility: &ServicePerformanceReceipt,
    settle: i128,
    refund: i128,
) -> Result<()> {
    let mut food_report = false;
    let mut utility_report = false;
    for observed in reports {
        check(
            observed.acquired_period == 3 && observed.actor_id == actor,
            "report period or observer mismatch",
        )?;
        if let babylon_practice_contract::OrganizerReport::Partner { facts, .. } = &observed.report
        {
            match facts {
                babylon_practice_contract::OrganizerPartnerFacts::FoodProvision {
                    commodity,
                    purchased,
                    unmet,
                    ..
                } if commodity.good_id == food.good_id.as_bytes() => {
                    same(
                        &(*purchased, *unmet),
                        &(food.fulfilled_quantity, use_food.unmet_quantity),
                        "P3 lawful food disclosure",
                    )?;
                    food_report = true;
                }
                babylon_practice_contract::OrganizerPartnerFacts::EssentialServices {
                    services,
                } => {
                    if let Some(service) = services
                        .iter()
                        .find(|r| r.commodity.good_id == utility.good_id.as_bytes())
                    {
                        same(
                            &(
                                service.performed,
                                service.settled_micros,
                                service.refunded_micros,
                            ),
                            &(utility.performed_quantity, settle, refund),
                            "P3 lawful utility disclosure",
                        )?;
                        utility_report = true;
                    }
                }
                _ => {}
            }
        }
    }
    check(
        food_report && utility_report,
        "missing actual partner food/service report",
    )
}

struct Case {
    config: Config,
    campaign: CampaignId,
    digest: [u8; 32],
    sql: Client,
    reader: PeriodReader,
    audit: Audit,
}
fn create_campaign(
    j: &mut Journal,
    fx: &Fixture,
    base: &Config,
    campaign: CampaignId,
) -> Result<(Case, DurableMaterialRuntime)> {
    let fixture = j.authority.clone();
    j.begin("bootstrap")?;
    let mut admin = base.connect(NoTls)?;
    let actual = sql_identity(&mut admin, fx, &fx.bootstrap)?;
    let template = db_identity(&mut admin, &fx.template.name)?;
    j.reached(&json!({"bootstrap":actual,"template":template}))?;
    same(&template, &fx.template, "frozen template")?;
    j.begin("clone")?;
    let database = TestDatabase::retained_allocation(base);
    same(
        &db_identity(&mut admin, &template.name)?,
        &template,
        "template at clone creation",
    )?;
    let exists = admin.query_opt(
        "SELECT oid FROM pg_catalog.pg_database WHERE datname=$1",
        &[&database.name],
    )?;
    check(exists.is_none(), "intended clone name already exists")?;
    let claim=j.record("sql-clone-claim-v1.json",&json!({"tag":"sql-clone-claim-v1","fixture":fixture,"pid":std::process::id(),"clone_name":database.name,"template":template,"owner_oid":fx.role_oid,"campaign":fx.campaign}))?;
    j.authority = claim.clone();
    database.create_clone(&mut admin, &template.name)?;
    let cloned = db_identity(&mut admin, &database.name)?;
    same(
        &db_identity(&mut admin, &template.name)?,
        &template,
        "template after clone creation",
    )?;
    let config = database.config(base);
    let mut sql = config.connect(NoTls)?;
    let observed = sql_identity(&mut sql, fx, &cloned)?;
    let clone_identity=j.record("sql-clone-identity-v1.json",&json!({"tag":"sql-clone-identity-v1","claim":claim,"clone":cloned,"template":template,"canary":fx.canary,"cluster":fx.cluster}))?;
    j.authority = clone_identity.clone();
    j.reached(&observed)?;
    same(&cloned.owner_oid, &fx.role_oid, "clone OWNER test")?;
    check(
        cloned.oid != template.oid && cloned.oid != fx.bootstrap.oid,
        "clone OID must be distinct",
    )?;
    j.begin("schema")?;
    let schema = super::session::verify_runtime_schema(&config);
    j.reached(&json!({"schema":schema.as_ref().map(|_|"verified").map_err(|e|format!("{e:?}"))}))?;
    schema?;
    j.begin("foundation")?;
    let content = CapturedEconomicCatalog::capture_national_campaign(
        economic_catalog::national_catalog_input(),
        campaign,
    )?;
    let content_sha = hex(&content.digest());
    let foundation = content.create_foundation(
        ReplaySessionId::try_from(fx.session.as_str()).map_err(debug_error)?,
        ReplaySeed::new(i64::try_from(fx.seed)?),
    )?;
    let digest = foundation.digest();
    let graph_sha = hash(foundation.graph_foundation.canonical_bytes());
    let runtime = DurableMaterialRuntime::create(&config, campaign, foundation)?;
    let found=sql.query_one("SELECT m.preset_id,m.content_sha256,m.foundation_sha256,g.foundation_sha256,c.replay_session_id,c.rng_seed FROM babylon_state.material_campaign_foundation_v3 m JOIN babylon_state.campaign_foundation g USING(campaign_id) JOIN babylon_state.campaign c USING(campaign_id) WHERE m.campaign_id=$1",&[campaign.as_uuid()])?;
    let observed = json!({"preset":found.try_get::<_,String>(0)?,"content_sha256":hex(&found.try_get::<_,Vec<u8>>(1)?),"foundation_sha256":hex(&found.try_get::<_,Vec<u8>>(2)?),"graph_foundation_sha256":hex(&found.try_get::<_,Vec<u8>>(3)?),"session":found.try_get::<_,String>(4)?,"seed":found.try_get::<_,i64>(5)?});
    let expected = json!({"preset":fx.preset,"content_sha256":content_sha,"foundation_sha256":hex(&digest),"graph_foundation_sha256":graph_sha,"session":fx.session,"seed":fx.seed});
    j.facts(&json!({"observed_foundation":observed,"captured_foundation":expected}))?;
    same(&observed, &expected, "SQL foundation")?;
    let owner=j.record("sql-owner-v1.json",&json!({"tag":"sql-owner-v1","fixture":fixture,"clone_identity":clone_identity,"bootstrap":fx.bootstrap,"template":template,"clone":cloned,"campaign":fx.campaign,"preset":fx.preset,"session":fx.session,"seed":fx.seed,"content_sha256":content_sha,"foundation_sha256":hex(&digest),"graph_foundation_sha256":graph_sha,"source":fx.source,"inputs":fx.inputs,"executable_sha256":fx.executable.sha256}))?;
    j.authority = owner;
    let actual = treasury(&runtime)?;
    j.reached(
        &json!({"foundation":observed,"organization_opening_cash_micros":actual.to_string()}),
    )?;
    same(&actual, &1_000_000, "opening organization treasury")?;
    let reader = PeriodReader::capture(&runtime)?;
    let audit = Audit::default();
    Ok((
        Case {
            config,
            campaign,
            digest,
            sql,
            reader,
            audit,
        },
        runtime,
    ))
}

fn collect_close(
    j: &mut Journal,
    case: &mut Case,
    mut runtime: DurableMaterialRuntime,
) -> Result<(DurableMaterialRuntime, OrganizerCommitment)> {
    let campaign = case.campaign;
    let p0 = runtime.organizer_snapshot().map_err(debug_error)?;
    case.audit
        .open(
            runtime.session().catalog(),
            runtime.session().material(),
            &p0,
        )
        .map_err(debug_error)?;
    let collect = original(
        &p0,
        campaign,
        [1; 16],
        OrganizerChoice::Collect,
        OrganizerAllocation::Collection {
            target_cash_micros: CASH,
        },
    );
    let less = OrganizerCommand {
        allocation: OrganizerAllocation::Collection {
            target_cash_micros: CASH - 1_000_000,
        },
        ..collect.clone()
    };
    j.begin("collect_preview")?;
    previews(j, &runtime, &[collect.clone(), less.clone()])?;
    j.begin("collect_submit")?;
    let collected = admission(j, &runtime, &mut case.sql, campaign, &collect, None, None)?;
    let opening_pending = snapshot(j, &runtime, &mut case.sql, campaign)?;
    j.reached(&json!({"pending":opening_pending,"commitment":collected}))?;
    j.begin("collect_conflict")?;
    conflict(
        j,
        &runtime,
        &mut case.sql,
        campaign,
        &less,
        &opening_pending,
    )?;
    j.begin("collect_pending_open")?;
    runtime = open_pending(j, case, runtime, &collected, &opening_pending)?;
    j.begin("p1_close")?;
    let actions = runtime.next_action_batch()?;
    j.blob(actions.canonical_bytes())?;
    runtime.advance_and_commit(&mut CollectingSink::default(), &actions)?;
    let rows = case.reader.receipts(j, &runtime, &mut case.sql, campaign)?;
    let p1 = snapshot(j, &runtime, &mut case.sql, campaign)?;
    let collections = format!("{:?}", rows.collections);
    let collection_result = collection(j, &runtime, &rows, &collected);
    let audit_result = audit_period(j, &mut case.audit, &runtime, campaign, rows);
    j.reached(&json!({"p1":p1,"cash":treasury(&runtime)?.to_string(),"collections":collections}))?;
    collection_result?;
    audit_result?;
    Ok((runtime, collected))
}
struct PendingAid {
    runtime: DurableMaterialRuntime,
    aided: OrganizerCommitment,
    pending: Snapshot,
}
fn admit_local(
    j: &mut Journal,
    case: &mut Case,
    mut runtime: DurableMaterialRuntime,
) -> Result<PendingAid> {
    let campaign = case.campaign;
    j.begin("aid_preview")?;
    let before = runtime.organizer_snapshot().map_err(debug_error)?;
    let aid = original(
        &before,
        campaign,
        [2; 16],
        OrganizerChoice::LocalAid,
        OrganizerAllocation::Aid {
            food_quantity: 0,
            cash_micros: CASH,
        },
    );
    let food = OrganizerCommand {
        allocation: OrganizerAllocation::Aid {
            food_quantity: 1,
            cash_micros: CASH,
        },
        ..aid.clone()
    };
    let reduced_cash = OrganizerCommand {
        allocation: OrganizerAllocation::Aid {
            food_quantity: 0,
            cash_micros: CASH - 1_000_000,
        },
        ..aid.clone()
    };
    previews(
        j,
        &runtime,
        &[aid.clone(), food.clone(), reduced_cash.clone()],
    )?;
    j.begin("aid_submit")?;
    let preview = runtime
        .preview_organizer_command(&aid)
        .map_err(debug_error)?;
    let aided = admission(j, &runtime, &mut case.sql, campaign, &aid, None, None)?;
    case.audit
        .accept(Accepted::capture(&aided, &preview, &before).map_err(debug_error)?)
        .map_err(debug_error)?;
    let pending = snapshot(j, &runtime, &mut case.sql, campaign)?;
    j.reached(&json!({"pending":pending,"commitment":aided}))?;
    j.begin("aid_food_conflict")?;
    conflict(j, &runtime, &mut case.sql, campaign, &food, &pending)?;
    j.begin("aid_cash_conflict")?;
    conflict(
        j,
        &runtime,
        &mut case.sql,
        campaign,
        &reduced_cash,
        &pending,
    )?;
    j.begin("aid_pending_open")?;
    runtime = open_pending(j, case, runtime, &aided, &pending)?;
    Ok(PendingAid {
        runtime,
        aided,
        pending,
    })
}
struct Writers {
    runtime: DurableMaterialRuntime,
    stale: DurableMaterialRuntime,
    actions: OrderedPracticeActionBatch,
    aided: OrganizerCommitment,
}
fn marker_rollback(j: &mut Journal, case: &mut Case, aid: PendingAid) -> Result<Writers> {
    let PendingAid {
        mut runtime,
        aided,
        pending,
    } = aid;
    let campaign = case.campaign;
    j.begin("stale_open")?;
    let stale = DurableMaterialRuntime::open(&case.config, campaign, case.digest)?;
    let stale_before = snapshot(j, &stale, &mut case.sql, campaign)?;
    let actions = runtime.next_action_batch()?;
    let batch = j.blob(actions.canonical_bytes())?;
    j.reached(&json!({"stale":stale_before,"batch":batch}))?;
    same(&stale_before, &pending, "second pending writer")?;
    j.begin("p2_marker_rollback")?;
    check(
        COMMIT_FAULT
            .with(|slot| slot.replace(Some(CommitFault::MarkerTrigger)))
            .is_none(),
        "fault already armed",
    )?;
    let mut failed_sink = CollectingSink::default();
    let failed = runtime.advance_and_commit(&mut failed_sink, &actions);
    let consumed = COMMIT_FAULT.with(|slot| slot.replace(None)).is_none();
    let mapped = failed
        .as_ref()
        .err()
        .map(crate::runtime_session::advance_error);
    let server = failed.as_ref().err().and_then(|error| match error {
        MaterialRuntimeError::Database(error) => error.as_db_error(),
        _ => None,
    });
    let code = server.map(|e| e.code().code());
    let message = server.map(DbError::message);
    let raw = json!({"result":format!("{failed:?}"),"sqlstate":code,"server_message":message,"runtime_code":mapped,"fault_consumed":consumed,"sink_events":failed_sink.events.len()});
    j.facts(&raw)?;
    case.sql = case.config.connect(NoTls)?;
    let rolled = snapshot(j, &runtime, &mut case.sql, campaign)?;
    let candidate=case.sql.query_one(
        "SELECT (SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1 AND resolve_tick=2),
         (SELECT count(*) FROM babylon_state.material_tick_v3 WHERE campaign_id=$1 AND resolve_tick=2),
         (SELECT count(*) FROM babylon_state.organizer_receipt_v1 WHERE campaign_id=$1 AND resolve_tick=2),
         (SELECT count(*) FROM babylon_state.organizer_observation_v1 WHERE campaign_id=$1 AND acquired_period=2),
         (SELECT count(*) FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND granted_tick=2),
         (SELECT count(*) FROM babylon_state.archive_dirty_receipt_v1 WHERE campaign_id=$1 AND resolve_tick=2)",
        &[campaign.as_uuid()])?;
    let counts = (0..6)
        .map(|k| candidate.try_get::<_, i64>(k))
        .collect::<StdResult<Vec<_>, _>>()?;
    j.reached(&json!({"before":pending,"after":rolled,"outcome":raw,"p2_marker_material_receipt_observation_grant_dirty":counts}))?;
    same(
        &counts,
        &vec![0; 6],
        "P2 candidate rows after marker failure",
    )?;
    same(&code, &Some("P0001"), "marker rollback SQLSTATE")?;
    same(
        &message,
        &Some("test-owned Archive wakeup failure"),
        "marker server message",
    )?;
    same(
        &mapped,
        &Some(RuntimeSessionErrorCode::CommitRefused),
        "mapped advance fault",
    )?;
    check(
        consumed && failed_sink.events.is_empty(),
        "fault was not consumed or events escaped",
    )?;
    same(&rolled, &pending, "full SQL and runtime rollback")?;
    j.begin("rollback_open")?;
    runtime = open_pending(j, case, runtime, &aided, &pending)?;
    Ok(Writers {
        runtime,
        stale,
        actions,
        aided,
    })
}
struct CompletedAid {
    runtime: DurableMaterialRuntime,
    aided: OrganizerCommitment,
    first: OrganizerReceipt,
}
fn reconcile_cash(
    j: &mut Journal,
    case: &mut Case,
    writers: Writers,
    collected: &OrganizerCommitment,
) -> Result<CompletedAid> {
    let Writers {
        mut runtime,
        mut stale,
        actions,
        aided,
    } = writers;
    let campaign = case.campaign;
    j.begin("p2_after_commit")?;
    check(
        COMMIT_FAULT
            .with(|slot| slot.replace(Some(CommitFault::AfterCommit)))
            .is_none(),
        "other fault armed",
    )?;
    let identity = runtime.advance_and_commit(&mut CollectingSink::default(), &actions)?;
    let disposition = runtime
        .diagnostic_receipt()
        .ok_or("missing ambiguous receipt")?
        .commit_disposition();
    let p2 = snapshot(j, &runtime, &mut case.sql, campaign)?;
    let rows = case.reader.receipts(j, &runtime, &mut case.sql, campaign)?;
    let aid_receipts = format!("{:?}", rows.aid);
    let settlement_result = settlement(j, &runtime, &rows, &aided);
    let audit_result = audit_period(j, &mut case.audit, &runtime, campaign, rows);
    j.reached(&json!({"disposition":format!("{disposition:?}"),"identity":hex(identity.canonical_bytes()),"p2":p2,"aid":aid_receipts}))?;
    same(
        &disposition,
        &ReplayCommitDisposition::ReconciledAfterAmbiguousCommit,
        "P2 ambiguous success",
    )?;
    settlement_result?;
    audit_result?;
    let first = response(&runtime, &aided)?;
    let response_bytes = serde_json::to_vec(&first)?;
    j.begin("p2_stale_retry")?;
    let retried = stale.advance_and_commit(&mut CollectingSink::default(), &actions)?;
    let stale_snapshot = snapshot(j, &stale, &mut case.sql, campaign)?;
    j.reached(&json!({"identity":hex(retried.canonical_bytes()),"disposition":format!("{:?}",stale.diagnostic_receipt().ok_or("missing stale receipt")?.commit_disposition()),"snapshot":stale_snapshot,"first_response":first}))?;
    same(
        &stale
            .diagnostic_receipt()
            .ok_or("missing stale retry disposition")?
            .commit_disposition(),
        &ReplayCommitDisposition::ReconciledAfterAmbiguousCommit,
        "stale retry disposition",
    )?;
    same(&retried, &identity, "stale exact marker")?;
    same(&stale_snapshot, &p2, "stale replay durable rows")?;
    j.begin("p2_completed_open")?;
    drop(stale);
    drop(runtime);
    runtime = DurableMaterialRuntime::open(&case.config, campaign, case.digest)?;
    let reopened = snapshot(j, &runtime, &mut case.sql, campaign)?;
    admission(
        j,
        &runtime,
        &mut case.sql,
        campaign,
        &collected.command,
        Some(1),
        Some(collected),
    )?;
    admission(
        j,
        &runtime,
        &mut case.sql,
        campaign,
        &aided.command,
        Some(2),
        Some(&aided),
    )?;
    let after_retries = snapshot(j, &runtime, &mut case.sql, campaign)?;
    j.reached(&json!({"p2":p2,"reopened":reopened,"after_retries":after_retries,"response":response(&runtime,&aided)?}))?;
    same(&reopened, &p2, "completed open")?;
    same(&after_retries, &p2, "completed exact retries")?;
    same(
        &serde_json::to_vec(&response(&runtime, &aided)?)?,
        &response_bytes,
        "reopened first response",
    )?;
    Ok(CompletedAid {
        runtime,
        aided,
        first,
    })
}
fn ordinary_purchases(j: &mut Journal, case: &mut Case, completed: CompletedAid) -> Result<()> {
    let CompletedAid {
        mut runtime,
        aided,
        first,
    } = completed;
    let campaign = case.campaign;
    let response_bytes = serde_json::to_vec(&first)?;
    j.begin("p3_purchase")?;
    let ordinary = runtime.next_action_batch()?;
    j.blob(ordinary.canonical_bytes())?;
    let identity = runtime.advance_and_commit(&mut CollectingSink::default(), &ordinary)?;
    let terminal = j.blob(identity.canonical_bytes())?;
    let rows = case.reader.receipts(j, &runtime, &mut case.sql, campaign)?;
    let p3 = snapshot(j, &runtime, &mut case.sql, campaign)?;
    j.facts(&json!({"terminal":p3,"identity":terminal,"earlier_response":first}))?;
    let purchases_result = purchases(j, &runtime, &rows);
    let audit_result = audit_period(j, &mut case.audit, &runtime, campaign, rows);
    let retained = response(&runtime, &aided)?;
    j.reached(&json!({"tick":identity.resolve_tick(),"snapshot":p3,"first_response":retained,"audit":case.audit.practice_report()}))?;
    purchases_result?;
    audit_result?;
    same(&identity.resolve_tick(), &3, "ordinary P3 terminal")?;
    same(
        &serde_json::to_vec(&retained)?,
        &response_bytes,
        "P3 retained original adjudication",
    )?;
    j.proven = j.index;
    j.record("in-test-seal-v1.json",&json!({"tag":"sql-in-test-seal-v1","owner":j.authority,"last":j.previous,"stage_count":STAGES.len(),"terminal_period":3,"terminal_identity":terminal}))?;
    Ok(())
}
fn run(j: &mut Journal, fx: &Fixture, base: &Config, campaign: CampaignId) -> Result<()> {
    let (mut case, opening) = create_campaign(j, fx, base, campaign)?;
    let (funded, collection) = collect_close(j, &mut case, opening)?;
    let pending = admit_local(j, &mut case, funded)?;
    let writers = marker_rollback(j, &mut case, pending)?;
    let completed = reconcile_cash(j, &mut case, writers, &collection)?;
    ordinary_purchases(j, &mut case, completed)
}

#[test]
#[ignore = "requires the separately released task-owned national allocation SQL fixture"]
fn national_collection_and_local_cash_survive_sql_retries() {
    let (fixture, reference, base, campaign) =
        Fixture::load().expect("authenticated SQL fixture before any connection");
    let mut journal = Journal::new(fixture.evidence.clone(), reference);
    if let Err(error) = run(&mut journal, &fixture, &base, campaign) {
        let export = journal.diverged(&error.to_string());
        drop(journal);
        panic!("SQL allocation witness failed: {error}; first-divergence export: {export:?}");
    }
}
