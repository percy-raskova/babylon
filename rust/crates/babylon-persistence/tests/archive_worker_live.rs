//! Live Archive worker proofs against the task-owned disposable `PostgreSQL` runtime.
//!
//! Each test clones the validated Rust-active runtime template, commits real
//! ticks through `DurableReplayRuntimeV2`, and then proves one worker
//! acceptance property against the committed dirty receipts.

use std::str::FromStr;

use babylon_bsl::rule_pipeline::split_content;
use babylon_bsl::rules_hash_of;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::sha256_of;
use babylon_kernel::tick_content_hash::RefDigestV1;
use babylon_kernel::ContentDigest;
use babylon_persistence::{
    michigan_dynamic_hex_foundation_v1, validate_legacy_connection_target, ArchiveCitationV1,
    ArchiveDirtyBatchV1, ArchiveDossierProducerV1, ArchiveKnowledgeGrantV1, ArchivePageInputV1,
    ArchivePageRefV1, ArchiveReceiptDispositionV1, ArchiveSchemaDispositionV1, ArchiveSignalV1,
    ArchiveSubjectKindV1, ArchiveSubjectV1, ArchiveWorkerV1, CampaignId, DurableReplayRuntimeV2,
    FoundationContentBundleV1, NullArchiveDossierProducerV1, PendingArchiveReceiptV1,
    SemanticArchiveErrorV1, SemanticArchiveStoreV1,
};
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use babylon_tick::material_state::MaterialStateV1;
use babylon_tick::replay_session::ReplayTickSession;
use postgres::{Config, NoTls};
use uuid::Uuid;

const DSN_ENV: &str = "BABYLON_LEGACY_ADOPTER_TEST_DSN";
const ACK_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK";
const ACK: &str = "I_UNDERSTAND_PER20_DROPS_SCRATCH_DATABASES_ROLES_AND_CREATED_BABYLON_INTEL";
const CANARY_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY";
const TEMPLATE_DB_ENV: &str = "BABYLON_RUNTIME_TEMPLATE_DB";
const DEFINES: &[u8] = br#"{"alpha":1}"#;
const REFERENCE_BUNDLE_DOMAIN: &[u8] = b"babylon.h3.reference-bundle-composite.v1\0";
const SCENARIO: &str =
    include_str!("../../babylon-tick/content/scenarios/struggle-spark-conformance.bscn");
const RULE: &str = include_str!("../../babylon-tick/content/rules/struggle-spark.bsl");
const WORKER_SEED: i64 = 2;

/// One distinct stub subject per receipt tick, because the Archive keeps one
/// current page per subject and converges repeated receipts onto it.
struct StubSubjectSpec {
    page_ref: ArchivePageRefV1,
    title: &'static str,
}

fn stub_subject_spec(tick: u64) -> StubSubjectSpec {
    let (kind, id, title) = match tick % 3 {
        1 => (ArchiveSubjectKindV1::County, "26163", "Wayne County"),
        2 => (ArchiveSubjectKindV1::Place, "2684000", "Detroit"),
        _ => (ArchiveSubjectKindV1::County, "26125", "Oakland County"),
    };
    StubSubjectSpec {
        page_ref: ArchivePageRefV1::try_new(kind, id.to_owned()).expect("stub subject ref"),
        title,
    }
}

fn detroit_page_ref() -> ArchivePageRefV1 {
    ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, "2684000".to_owned())
        .expect("Detroit ref")
}

fn stub_page_input(receipt: &PendingArchiveReceiptV1) -> ArchivePageInputV1 {
    let spec = stub_subject_spec(receipt.resolve_tick());
    let subject = ArchiveSubjectV1::try_new(
        spec.page_ref.kind(),
        spec.page_ref.id().to_owned(),
        spec.title.to_owned(),
    )
    .expect("stub subject");
    ArchivePageInputV1::try_new(
        subject,
        receipt.resolve_tick(),
        *receipt.tick_content_hash(),
        format!(
            "Which neighboring place should organizers investigate at tick {}?",
            receipt.resolve_tick()
        ),
        vec![ArchiveSignalV1::try_new(
            "employment".to_owned(),
            "Employment".to_owned(),
            "728576 jobs".to_owned(),
            ArchiveCitationV1::try_new(
                "qcew-2024".to_owned(),
                "fact_qcew_county_rollup county_fips=26163".to_owned(),
            )
            .expect("citation"),
        )
        .expect("signal")],
        Vec::new(),
    )
    .expect("stub page")
}

/// Stub producer that materializes one valid page per receipt.
struct StubPageProducer;

impl ArchiveDossierProducerV1 for StubPageProducer {
    fn produce(
        &self,
        _campaign_id: Uuid,
        receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1> {
        ArchiveDirtyBatchV1::try_new(
            receipt.resolve_tick(),
            *receipt.tick_content_hash(),
            vec![stub_page_input(receipt)],
        )
    }
}

/// Stub producer that refuses one scripted tick to prove exact resume.
struct FailAtTickProducer {
    fail_at_tick: u64,
}

impl ArchiveDossierProducerV1 for FailAtTickProducer {
    fn produce(
        &self,
        campaign_id: Uuid,
        receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1> {
        if receipt.resolve_tick() == self.fail_at_tick {
            return Err(SemanticArchiveErrorV1::InvalidText);
        }
        StubPageProducer.produce(campaign_id, receipt)
    }
}

/// Stub producer that returns a well-formed batch bound to the wrong tick
/// identity, proving the worker refuses identity drift before the store.
struct WrongTickProducer;

impl ArchiveDossierProducerV1 for WrongTickProducer {
    fn produce(
        &self,
        _campaign_id: Uuid,
        receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1> {
        let wrong = PendingArchiveReceiptV1::try_new(
            receipt.resolve_tick() + 1,
            *receipt.tick_content_hash(),
        )
        .expect("wrong-tick receipt boundary");
        ArchiveDirtyBatchV1::try_new(
            wrong.resolve_tick(),
            *wrong.tick_content_hash(),
            vec![stub_page_input(&wrong)],
        )
    }
}

/// Insert one dirty receipt row with no `tick_commit` marker, as a crash
/// residue or partial rollback would leave behind.
fn insert_orphan_dirty_receipt(
    config: &Config,
    campaign_id: CampaignId,
    resolve_tick: i64,
    tick_content_hash: [u8; 32],
) {
    config
        .connect(NoTls)
        .expect("orphan insert connection")
        .execute(
            "INSERT INTO babylon_state.archive_dirty_receipt_v1 \
             (campaign_id, resolve_tick, tick_content_hash) VALUES ($1::uuid, $2, $3)",
            &[
                campaign_id.as_uuid(),
                &resolve_tick,
                &&tick_content_hash[..],
            ],
        )
        .expect("orphan dirty receipt inserts without a marker");
}

fn dirty_receipt_count(config: &Config, campaign_id: CampaignId) -> i64 {
    config
        .connect(NoTls)
        .expect("dirty receipt count connection")
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_state.archive_dirty_receipt_v1 \
             WHERE campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .expect("dirty receipt count query")
        .try_get(0)
        .expect("dirty receipt count decodes")
}

fn validated_base_config() -> Config {
    assert_eq!(std::env::var(ACK_ENV).as_deref(), Ok(ACK));
    let canary = std::env::var(CANARY_ENV).expect("runner supplies the disposable canary");
    assert_eq!(canary.len(), 32);
    let dsn = std::env::var(DSN_ENV).expect("runner supplies the disposable DSN");
    let config = Config::from_str(&dsn).expect("runner DSN parses");
    validate_legacy_connection_target(&config).expect("loopback target");
    assert_eq!(config.get_user(), Some("test"));
    assert_eq!(config.get_dbname(), Some("postgres"));
    let actual: Option<String> = config
        .connect(NoTls)
        .expect("canary connection")
        .query_one(
            "SELECT pg_catalog.current_setting('babylon.per20_disposable', true)",
            &[],
        )
        .expect("canary query")
        .try_get(0)
        .expect("canary decode");
    assert_eq!(actual.as_deref(), Some(canary.as_str()));
    config
}

fn validated_template_name() -> String {
    let template = std::env::var(TEMPLATE_DB_ENV)
        .expect("runner supplies the validated Rust-active template database");
    let suffix = template
        .strip_prefix("per281_runtime_template_")
        .expect("runtime template uses the task-owned prefix");
    assert_eq!(suffix.len(), 12);
    assert!(suffix
        .bytes()
        .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte)));
    assert!(template
        .bytes()
        .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_'));
    template
}

struct TestDatabase {
    name: String,
    admin: Config,
    active: bool,
}

impl TestDatabase {
    fn create_from_template(base: &Config, template: &str, label: &str) -> Self {
        assert!(label.bytes().all(|byte| byte.is_ascii_lowercase()));
        assert!(template
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_'));
        let name = format!("per281_runtime_{label}_{}", std::process::id());
        let mut admin = base.clone();
        admin.dbname("postgres");
        let sql = format!("CREATE DATABASE \"{name}\" OWNER test TEMPLATE \"{template}\"");
        admin
            .connect(NoTls)
            .expect("admin connection")
            .batch_execute(&sql)
            .expect("runtime clone creation");
        let database = Self {
            name,
            admin,
            active: true,
        };
        let observation = database
            .config(base)
            .connect(NoTls)
            .expect("runtime clone connection")
            .query_one(
                "SELECT \
                   (SELECT pg_catalog.string_agg(ordinal::pg_catalog.text || ':' || \
                            state_tag::pg_catalog.text || ':' || schema_epoch::pg_catalog.text, \
                            ',' ORDER BY ordinal) \
                    FROM babylon_meta.persistence_authority_ledger), \
                   (SELECT pg_catalog.count(*) FROM babylon_meta.campaign)",
                &[],
            )
            .expect("runtime clone observation");
        assert_eq!(
            observation
                .try_get::<_, String>(0)
                .expect("authority ledger decodes"),
            "1:1:8,2:2:9"
        );
        assert_eq!(
            observation
                .try_get::<_, i64>(1)
                .expect("campaign count decodes"),
            0
        );
        database
    }

    fn config(&self, base: &Config) -> Config {
        let mut config = base.clone();
        config.dbname(&self.name);
        config
    }

    fn cleanup(mut self) {
        self.try_drop_database()
            .expect("runtime test database cleanup");
        self.active = false;
    }

    fn try_drop_database(&self) -> Result<(), ()> {
        let sql = format!("DROP DATABASE IF EXISTS \"{}\" WITH (FORCE)", self.name);
        self.admin
            .connect(NoTls)
            .map_err(|_| ())?
            .batch_execute(&sql)
            .map_err(|_| ())
    }
}

impl Drop for TestDatabase {
    fn drop(&mut self) {
        if !self.active {
            return;
        }
        if std::thread::panicking() {
            let _cleanup = self.try_drop_database();
            return;
        }
        self.try_drop_database()
            .expect("runtime test database cleanup");
        self.active = false;
    }
}

fn runtime_fixture_with_seed(
    seed: i64,
) -> (
    ReplayTickSession<HypergraphStore>,
    FoundationContentBundleV1,
) {
    let (_, rules) = split_content(RULE).expect("live rule parses");
    let forms = rules.into_iter().map(|rule| rule.form).collect::<Vec<_>>();
    let content = ContentDigest {
        defines_hash: sha256_of(DEFINES),
        rules_hash: rules_hash_of(&forms).expect("live rule hashes"),
    };
    let foundation = michigan_dynamic_hex_foundation_v1().expect("foundation decodes");
    let mut reference_manifest = REFERENCE_BUNDLE_DOMAIN.to_vec();
    reference_manifest.extend_from_slice(&foundation.base_reference_cohort_digest());
    reference_manifest.extend_from_slice(&foundation.r8_section_digest());
    assert_eq!(
        sha256_of(&reference_manifest),
        foundation.reference_bundle_digest()
    );
    let reference = RefDigestV1::from_bytes(foundation.reference_bundle_digest());
    let session = ReplayTickSession::new(
        SCENARIO,
        None,
        RULE,
        HypergraphStore::new(),
        ReplaySessionIdV1::try_from("per22/archive-worker-live").expect("session id"),
        ReplaySeed::new(seed),
        content,
        reference,
        MaterialStateV1::try_new(foundation).expect("material state"),
    )
    .expect("tick-zero session prepares");
    let bundle =
        FoundationContentBundleV1::try_new(SCENARIO, None, RULE, DEFINES, &reference_manifest)
            .expect("content bundle");
    (session, bundle)
}

fn commit_ticks(runtime: &mut DurableReplayRuntimeV2<HypergraphStore>, count: u64) {
    for tick in 1..=count {
        let actions = OrderedPracticeActionBatchV1::empty(
            runtime.foundation().replay_session_identity().clone(),
            tick,
        )
        .expect("empty action batch");
        let receipt = runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .expect("tick commits");
        assert_eq!(receipt.resolve_tick().get(), tick);
    }
}

fn grant_stub_knowledge(store: &SemanticArchiveStoreV1, campaign_id: CampaignId) {
    for tick in 1..=3 {
        let spec = stub_subject_spec(tick);
        for (grant_key, source_id) in [
            ("subject", "live-worker-subject"),
            ("employment", "live-worker-employment"),
        ] {
            store
                .grant_knowledge(
                    campaign_id,
                    &ArchiveKnowledgeGrantV1::try_new(
                        spec.page_ref.clone(),
                        grant_key.to_owned(),
                        1,
                        ArchiveCitationV1::try_new(
                            source_id.to_owned(),
                            format!("{grant_key}@tick-1"),
                        )
                        .expect("live grant citation"),
                    )
                    .expect("live knowledge grant"),
                )
                .expect("knowledge grant persists");
        }
    }
}

fn archive_page_count(config: &Config, campaign_id: CampaignId) -> i64 {
    config
        .connect(NoTls)
        .expect("page count connection")
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_meta.archive_page_v1 \
             WHERE campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .expect("page count query")
        .try_get(0)
        .expect("page count decodes")
}

fn receipt_consumption_count(config: &Config, campaign_id: CampaignId) -> i64 {
    config
        .connect(NoTls)
        .expect("consumption count connection")
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_meta.archive_receipt_consumption_v1 \
             WHERE campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .expect("consumption count query")
        .try_get(0)
        .expect("consumption count decodes")
}

struct LiveWorkerTarget {
    database: TestDatabase,
    config: Config,
    campaign_id: CampaignId,
}

impl LiveWorkerTarget {
    fn create(label: &str, campaign_uuid: u128, tick_count: u64) -> Self {
        assert!(tick_count > 0);
        let base = validated_base_config();
        let template = validated_template_name();
        let database = TestDatabase::create_from_template(&base, &template, label);
        let config = database.config(&base);
        let campaign_id = CampaignId::from_uuid(Uuid::from_u128(campaign_uuid));
        let (session, bundle) = runtime_fixture_with_seed(WORKER_SEED);
        let mut runtime = DurableReplayRuntimeV2::create(&config, campaign_id, session, bundle)
            .expect("runtime constructs after activation");
        commit_ticks(&mut runtime, tick_count);
        drop(runtime);
        let store = SemanticArchiveStoreV1::new(&config);
        match store.install_schema().expect("Archive schema installs") {
            ArchiveSchemaDispositionV1::Installed | ArchiveSchemaDispositionV1::AlreadyCurrent => {}
        }
        grant_stub_knowledge(&store, campaign_id);
        Self {
            database,
            config,
            campaign_id,
        }
    }

    fn finish(self) {
        self.database.cleanup();
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_worker_consumes_pending_receipts_in_tick_order() {
    let target = LiveWorkerTarget::create(
        "archiveworkerorder",
        0x2200_0000_0000_0000_0000_0000_0000_00a1,
        3,
    );

    let mut worker = ArchiveWorkerV1::new(&target.config);
    let report = worker
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("sweep applies every pending receipt");

    let dispositions = report.dispositions();
    let applied = dispositions
        .iter()
        .map(|(tick, disposition)| (*tick, *disposition))
        .collect::<Vec<_>>();
    assert_eq!(
        applied,
        vec![
            (1, ArchiveReceiptDispositionV1::Applied),
            (2, ArchiveReceiptDispositionV1::Applied),
            (3, ArchiveReceiptDispositionV1::Applied),
        ]
    );
    assert!(dispositions.windows(2).all(|pair| pair[0].0 < pair[1].0));
    assert_eq!(report.applied_count(), 3);
    assert_eq!(report.already_consumed_count(), 0);
    assert_eq!(report.deferred_count(), 0);
    assert_eq!(report.verified_tick(), 3);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        3
    );
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 3);

    let store = SemanticArchiveStoreV1::new(&target.config);
    let hits = store
        .search_known(target.campaign_id, "investigate at tick 2", 10)
        .expect("known-only search");
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0].page_ref(), &detroit_page_ref());
    assert_eq!(hits[0].verified_tick(), 2);
    assert!(hits[0].markdown().contains("728576 jobs"));
    assert_eq!(hits[0].citations().len(), 2);
    assert_eq!(hits[0].citations()[0].source_id(), "live-worker-subject");
    assert_eq!(hits[0].citations()[1].source_id(), "qcew-2024");
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_worker_rerun_reconciles_without_duplicate_publication() {
    let target = LiveWorkerTarget::create(
        "archiveworkerrerun",
        0x2200_0000_0000_0000_0000_0000_0000_00a2,
        2,
    );

    let mut worker = ArchiveWorkerV1::new(&target.config);
    let first = worker
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("first sweep applies");
    assert_eq!(first.applied_count(), 2);
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 2);

    let second = worker
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("rerun sweep reconciles");
    assert!(second.dispositions().is_empty());
    assert_eq!(second.applied_count(), 0);
    assert_eq!(second.already_consumed_count(), 0);
    assert_eq!(second.deferred_count(), 0);
    assert_eq!(
        second.verified_tick(),
        2,
        "an empty sweep reports the persisted contiguous watermark, not zero"
    );
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 2);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        2
    );
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_worker_crash_between_receipts_resumes_exactly() {
    let target = LiveWorkerTarget::create(
        "archiveworkerresume",
        0x2200_0000_0000_0000_0000_0000_0000_00a3,
        3,
    );

    let mut failing = ArchiveWorkerV1::new(&target.config);
    let failure = failing.sweep_once(target.campaign_id, &FailAtTickProducer { fail_at_tick: 2 });
    assert_eq!(failure, Err(SemanticArchiveErrorV1::InvalidText));
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        1
    );
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 1);

    let mut probe = ArchiveWorkerV1::new(&target.config);
    let pending = probe
        .sweep_once(target.campaign_id, &NullArchiveDossierProducerV1::new())
        .expect("probe sweep defers the surviving receipts");
    let pending_dispositions = pending
        .dispositions()
        .iter()
        .map(|(tick, disposition)| (*tick, *disposition))
        .collect::<Vec<_>>();
    assert_eq!(
        pending_dispositions,
        vec![
            (2, ArchiveReceiptDispositionV1::Deferred),
            (3, ArchiveReceiptDispositionV1::Deferred),
        ]
    );
    assert_eq!(
        pending.verified_tick(),
        1,
        "the deferred tick 2 caps the watermark at the contiguous prefix even though tick 1 applied"
    );
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        1
    );

    let mut resumed = ArchiveWorkerV1::new(&target.config);
    let resume = resumed
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("resumed sweep completes");
    let resumed_dispositions = resume
        .dispositions()
        .iter()
        .map(|(tick, disposition)| (*tick, *disposition))
        .collect::<Vec<_>>();
    assert_eq!(
        resumed_dispositions,
        vec![
            (2, ArchiveReceiptDispositionV1::Applied),
            (3, ArchiveReceiptDispositionV1::Applied),
        ]
    );
    assert_eq!(resume.verified_tick(), 3);
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 3);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        3
    );
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_worker_defers_empty_batches_without_consuming() {
    let target = LiveWorkerTarget::create(
        "archiveworkerdefer",
        0x2200_0000_0000_0000_0000_0000_0000_00a4,
        2,
    );

    let mut worker = ArchiveWorkerV1::new(&target.config);
    let deferred = worker
        .sweep_once(target.campaign_id, &NullArchiveDossierProducerV1::new())
        .expect("null sweep defers without consuming");
    let deferred_dispositions = deferred
        .dispositions()
        .iter()
        .map(|(tick, disposition)| (*tick, *disposition))
        .collect::<Vec<_>>();
    assert_eq!(
        deferred_dispositions,
        vec![
            (1, ArchiveReceiptDispositionV1::Deferred),
            (2, ArchiveReceiptDispositionV1::Deferred),
        ]
    );
    assert_eq!(deferred.applied_count(), 0);
    assert_eq!(deferred.verified_tick(), 0);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 0);

    let filled = worker
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("real producer fills the deferred receipts");
    let filled_dispositions = filled
        .dispositions()
        .iter()
        .map(|(tick, disposition)| (*tick, *disposition))
        .collect::<Vec<_>>();
    assert_eq!(
        filled_dispositions,
        vec![
            (1, ArchiveReceiptDispositionV1::Applied),
            (2, ArchiveReceiptDispositionV1::Applied),
        ]
    );
    assert_eq!(filled.verified_tick(), 2);
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 2);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        2
    );
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_worker_refuses_batch_identity_mismatch_without_consuming() {
    let target = LiveWorkerTarget::create(
        "archiveworkeridentity",
        0x2200_0000_0000_0000_0000_0000_0000_00a5,
        2,
    );

    let mut worker = ArchiveWorkerV1::new(&target.config);
    let failure = worker.sweep_once(target.campaign_id, &WrongTickProducer);
    assert_eq!(
        failure,
        Err(SemanticArchiveErrorV1::ReceiptMismatch),
        "a batch bound to another tick must stop the sweep before any consumption"
    );
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 0);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_worker_skips_orphan_dirty_receipt_without_marker() {
    let target = LiveWorkerTarget::create(
        "archiveworkerorphan",
        0x2200_0000_0000_0000_0000_0000_0000_00a6,
        2,
    );
    insert_orphan_dirty_receipt(&target.config, target.campaign_id, 3, [0xee; 32]);

    let mut worker = ArchiveWorkerV1::new(&target.config);
    let report = worker
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("orphan rows never reach the producer or stop the ordered sweep");
    let applied = report
        .dispositions()
        .iter()
        .map(|(tick, disposition)| (*tick, *disposition))
        .collect::<Vec<_>>();
    assert_eq!(
        applied,
        vec![
            (1, ArchiveReceiptDispositionV1::Applied),
            (2, ArchiveReceiptDispositionV1::Applied),
        ]
    );
    assert_eq!(report.verified_tick(), 2);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        2
    );
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 2);
    assert_eq!(
        dirty_receipt_count(&target.config, target.campaign_id),
        3,
        "the orphan row stays dirty, unconsumed, and out of the sweep's view"
    );
    target.finish();
}
