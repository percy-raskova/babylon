//! Live PER-22 place dossier producer proofs against the task-owned disposable
//! `PostgreSQL` runtime.
//!
//! Each test clones the validated Rust-active runtime template, commits real
//! ticks through `DurableReplayRuntimeV2`, and proves one place dossier
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
    ArchiveKnowledgeGrantV1, ArchivePageRefV1, ArchiveReceiptDispositionV1,
    ArchiveSchemaDispositionV1, ArchiveSubjectKindV1, ArchiveWorkerV1, CampaignId,
    DurableReplayRuntimeV2, FoundationContentBundleV1, PlaceDossierProducerV1,
    SemanticArchiveStoreV1, PLACE_DECISION_QUESTION_V1,
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
const PLACE_COUNT: usize = 745;
const MAX_PAGES_PER_RECEIPT: usize = 256;

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
        ReplaySessionIdV1::try_from("per22/place-producer-live").expect("session id"),
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

struct LivePlaceTarget {
    database: TestDatabase,
    config: Config,
    campaign_id: CampaignId,
}

impl LivePlaceTarget {
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

/// Grant the subject knowledge every place page needs to render, plus the
/// identity field and Wayne County subject for the Detroit assertions.
fn grant_place_knowledge(
    store: &SemanticArchiveStoreV1,
    campaign_id: CampaignId,
    geoids: &[String],
) {
    for geoid in geoids {
        store
            .grant_knowledge(
                campaign_id,
                &ArchiveKnowledgeGrantV1::try_new(
                    ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, geoid.clone())
                        .expect("place ref"),
                    "subject".to_owned(),
                    1,
                    ArchiveCitationV1::try_new(
                        "live-place-subject".to_owned(),
                        format!("place/{geoid}"),
                    )
                    .expect("subject citation"),
                )
                .expect("subject grant"),
            )
            .expect("place subject grant persists");
    }
    for (page_ref, grant_key, locator) in [
        (
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, "2622000".to_owned())
                .expect("Detroit ref"),
            "identity".to_owned(),
            "identity@tick-1".to_owned(),
        ),
        (
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, "26163".to_owned())
                .expect("Wayne ref"),
            "subject".to_owned(),
            "county/26163".to_owned(),
        ),
    ] {
        store
            .grant_knowledge(
                campaign_id,
                &ArchiveKnowledgeGrantV1::try_new(
                    page_ref,
                    grant_key,
                    1,
                    ArchiveCitationV1::try_new("live-place-field".to_owned(), locator)
                        .expect("field citation"),
                )
                .expect("field grant"),
            )
            .expect("field grant persists");
    }
}

fn place_page_count(config: &Config, campaign_id: CampaignId) -> i64 {
    config
        .connect(NoTls)
        .expect("page count connection")
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_meta.archive_page_v1 \
             WHERE campaign_id = $1::uuid AND subject_kind = 'place'",
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

fn place_page_rows(config: &Config, campaign_id: CampaignId) -> Vec<(String, i64, String)> {
    config
        .connect(NoTls)
        .expect("place page rows connection")
        .query(
            "SELECT subject_id, verified_tick, markdown FROM babylon_meta.archive_page_v1 \
             WHERE campaign_id = $1::uuid AND subject_kind = 'place' ORDER BY subject_id",
            &[campaign_id.as_uuid()],
        )
        .expect("place page rows query")
        .iter()
        .map(|row| {
            (
                row.try_get(0).expect("subject id decodes"),
                row.try_get(1).expect("verified tick decodes"),
                row.try_get(2).expect("markdown decodes"),
            )
        })
        .collect()
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_place_producer_drains_bootstrap_pages_across_receipts() {
    let target = LivePlaceTarget::create(
        "placeproducerdrain",
        0x2200_0000_0000_0000_0000_0000_0000_00b1,
        4,
    );

    let producer = PlaceDossierProducerV1::try_new(&target.config).expect("pinned products load");
    let plans = producer.desired_pages().expect("desired pages build");
    assert_eq!(plans.len(), PLACE_COUNT);
    let geoids = plans
        .iter()
        .map(|plan| plan.place_geoid().to_owned())
        .collect::<Vec<_>>();
    let store = SemanticArchiveStoreV1::new(&target.config);
    grant_place_knowledge(&store, target.campaign_id, &geoids);

    let mut worker = ArchiveWorkerV1::new(&target.config);
    let report = worker
        .sweep_once(target.campaign_id, &producer)
        .expect("place sweep drains the bootstrap backlog");
    let dispositions = report
        .dispositions()
        .iter()
        .map(|(tick, disposition)| (*tick, *disposition))
        .collect::<Vec<_>>();
    assert_eq!(
        dispositions,
        vec![
            (1, ArchiveReceiptDispositionV1::Applied),
            (2, ArchiveReceiptDispositionV1::Applied),
            (3, ArchiveReceiptDispositionV1::Applied),
            (4, ArchiveReceiptDispositionV1::Deferred),
        ],
        "three receipts drain every place; the fourth defers empty"
    );
    assert_eq!(
        report.verified_tick(),
        3,
        "the deferred tick 4 caps the watermark"
    );
    assert_eq!(place_page_count(&target.config, target.campaign_id), 745);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        3
    );

    let rows = place_page_rows(&target.config, target.campaign_id);
    assert_eq!(rows.len(), PLACE_COUNT);
    let mut sorted = rows.clone();
    sorted.sort_by(|left, right| left.0.cmp(&right.0));
    assert_eq!(rows, sorted, "stored place pages follow sorted GEOID order");
    for (tick, expected) in [
        (1, MAX_PAGES_PER_RECEIPT),
        (2, MAX_PAGES_PER_RECEIPT),
        (3, 233),
    ] {
        assert_eq!(
            rows.iter().filter(|row| row.1 == tick).count(),
            expected,
            "receipt {tick} published exactly {expected} bootstrap pages"
        );
    }

    let detroit = rows
        .iter()
        .find(|row| row.0 == "2622000")
        .expect("Detroit page published in the first receipt");
    assert_eq!(detroit.1, 1);
    assert!(detroit.2.contains("# Detroit city"));
    assert!(detroit.2.contains(PLACE_DECISION_QUESTION_V1));
    assert!(
        detroit.2.contains("[[county/26163|Wayne County]]"),
        "a granted county subject renders its known label"
    );
    assert!(
        detroit.2.contains(
            "census-place-authority-v1; census_place_identity_mi_2023.csv.gz#place_geoid=2622000"
        ),
        "the granted identity signal pins the exact artifact row"
    );

    let fenton = rows
        .iter()
        .find(|row| row.0 == "2627760")
        .expect("Fenton city published");
    for county in ["26049", "26093", "26125"] {
        assert!(
            fenton.2.contains(&format!("[[county/{county}")),
            "cross-county place keeps every county slice, including {county}"
        );
    }
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_place_producer_rerun_reconciles_without_duplicate_pages() {
    let target = LivePlaceTarget::create(
        "placeproducerrerun",
        0x2200_0000_0000_0000_0000_0000_0000_00b2,
        3,
    );

    let producer = PlaceDossierProducerV1::try_new(&target.config).expect("pinned products load");
    let store = SemanticArchiveStoreV1::new(&target.config);
    let geoids = producer
        .desired_pages()
        .expect("desired pages build")
        .iter()
        .map(|plan| plan.place_geoid().to_owned())
        .collect::<Vec<_>>();
    grant_place_knowledge(&store, target.campaign_id, &geoids);

    let mut worker = ArchiveWorkerV1::new(&target.config);
    let first = worker
        .sweep_once(target.campaign_id, &producer)
        .expect("first sweep drains every place across the three receipts");
    assert_eq!(first.applied_count(), 3);
    assert_eq!(first.deferred_count(), 0);
    assert_eq!(first.verified_tick(), 3);
    assert_eq!(place_page_count(&target.config, target.campaign_id), 745);

    let second = worker
        .sweep_once(target.campaign_id, &producer)
        .expect("rerun sweep reconciles");
    assert!(second.dispositions().is_empty());
    assert_eq!(second.verified_tick(), 3);
    assert_eq!(place_page_count(&target.config, target.campaign_id), 745);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        3
    );

    let rows = place_page_rows(&target.config, target.campaign_id);
    let mut unique = std::collections::BTreeSet::new();
    for (geoid, _, _) in &rows {
        assert!(unique.insert(geoid.clone()), "no duplicate place pages");
    }
    target.finish();
}
