//! Live PER-23 Slice 1 proofs for the read-only reader role and the
//! fog-safe committed-tick status view (ADR249 R8).
//!
//! Each test clones the validated Rust-active runtime template, commits real
//! ticks through `DurableReplayRuntimeV2`, installs the additive Archive and
//! reader-role schemas, and then proves one privilege property against the
//! live `PostgreSQL` privilege layer. No test runs `migrate_schema_epoch`
//! after installing the role or view: both are additive, non-epoch objects
//! and would fail the digest-pinned epoch census as unexpected extras.

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
    install_reader_role_v1, michigan_dynamic_hex_foundation_v1, validate_legacy_connection_target,
    ArchiveCitationV1, ArchiveDirtyBatchV1, ArchiveKnowledgeGrantV1, ArchivePageInputV1,
    ArchivePageRefV1, ArchiveSchemaDispositionV1, ArchiveSignalV1, ArchiveSubjectKindV1,
    ArchiveSubjectV1, CampaignId, DurableReplayRuntimeV2, FoundationContentBundleV1,
    ReaderRoleDispositionV1, SemanticArchiveReaderV1, SemanticArchiveStoreV1,
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
const READER_DSN_ENV: &str = "BABYLON_READER_DSN";
const DEFINES: &[u8] = br#"{"alpha":1}"#;
const REFERENCE_BUNDLE_DOMAIN: &[u8] = b"babylon.h3.reference-bundle-composite.v1\0";
const SCENARIO: &str =
    include_str!("../../babylon-tick/content/scenarios/struggle-spark-conformance.bscn");
const RULE: &str = include_str!("../../babylon-tick/content/rules/struggle-spark.bsl");
const READER_SEED: i64 = 3;

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

struct ReaderTarget {
    database: TestDatabase,
    config: Config,
    campaign_id: CampaignId,
}

/// One confined `LOGIN` role as a member of `babylon_reader`: the deployment
/// credential shape the reader handle is designed for (the reader role itself
/// is `NOLOGIN` by design).
struct ConfinedLogin {
    name: String,
    admin: Config,
    active: bool,
}

impl ConfinedLogin {
    const PASSWORD: &'static str = "readerconfined";

    fn create(base: &Config) -> Self {
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("clock is after the epoch")
            .as_nanos();
        let name = format!("per281_reader_login_{}_{unique:024x}", std::process::id());
        let mut admin = base.clone();
        admin.dbname("postgres");
        // The bounded startup options pin event_triggers=off; the runtime
        // hardening makes that parameter grant-only (see ScratchRole).
        admin
            .connect(NoTls)
            .expect("admin connection")
            .batch_execute(&format!(
                "CREATE ROLE {name} LOGIN PASSWORD '{}' \
                 NOSUPERUSER NOCREATEDB NOCREATEROLE; \
                 GRANT babylon_reader TO {name}; \
                 GRANT SET ON PARAMETER event_triggers TO {name}",
                Self::PASSWORD
            ))
            .expect("confined reader login creates");
        Self {
            name,
            admin,
            active: true,
        }
    }

    fn dsn(&self, host: &str, port: u16, database: &str) -> String {
        format!(
            "postgresql://{}:{}@{host}:{port}/{database}",
            self.name,
            Self::PASSWORD
        )
    }

    fn try_cleanup(&self) -> Result<(), postgres::Error> {
        self.admin.connect(NoTls)?.batch_execute(&format!(
            "REVOKE SET ON PARAMETER event_triggers FROM {role}; DROP ROLE IF EXISTS {role}",
            role = self.name
        ))
    }

    fn cleanup(mut self) {
        self.try_cleanup().expect("confined reader login cleanup");
        self.active = false;
    }
}

impl Drop for ConfinedLogin {
    fn drop(&mut self) {
        if !self.active {
            return;
        }
        if std::thread::panicking() {
            let _cleanup = self.try_cleanup();
            return;
        }
        self.try_cleanup().expect("confined reader login cleanup");
        self.active = false;
    }
}

impl ReaderTarget {
    /// Clone the template, commit `tick_count` real ticks for one campaign,
    /// install the additive Archive schema first (so the reader installer's
    /// archive-table revokes observe real tables), then install the reader
    /// role and tick-status view.
    fn create(label: &str, campaign_uuid: u128, tick_count: u64) -> Self {
        assert!(tick_count > 0);
        let base = validated_base_config();
        let template = validated_template_name();
        let database = TestDatabase::create_from_template(&base, &template, label);
        let config = database.config(&base);
        let campaign_id = CampaignId::from_uuid(Uuid::from_u128(campaign_uuid));
        let (session, bundle) = runtime_fixture_with_seed(READER_SEED);
        let mut runtime = DurableReplayRuntimeV2::create(&config, campaign_id, session, bundle)
            .expect("runtime constructs after activation");
        for tick in 1..=tick_count {
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
        drop(runtime);

        let store = SemanticArchiveStoreV1::new(&config);
        match store.install_schema().expect("Archive schema installs") {
            ArchiveSchemaDispositionV1::Installed | ArchiveSchemaDispositionV1::AlreadyCurrent => {}
        }
        assert_eq!(
            install_reader_role_v1(&config).expect("reader role installs"),
            ReaderRoleDispositionV1::Installed
        );
        assert_eq!(
            install_reader_role_v1(&config).expect("reader role reinstall reconciles"),
            ReaderRoleDispositionV1::AlreadyCurrent,
            "the exact role, view, and grants reinstall idempotently"
        );
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
        ReplaySessionIdV1::try_from("per23/reader-role-live").expect("session id"),
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

fn county_subject() -> ArchiveSubjectV1 {
    ArchiveSubjectV1::try_new(
        ArchiveSubjectKindV1::County,
        "26163".to_owned(),
        "Wayne County".to_owned(),
    )
    .expect("county identity")
}

fn county_page_input(tick_content_hash: [u8; 32]) -> ArchivePageInputV1 {
    ArchivePageInputV1::try_new(
        county_subject(),
        1,
        tick_content_hash,
        "Which neighboring place should organizers investigate next?".to_owned(),
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
    .expect("county page input")
}

/// Grant subject and employment knowledge, then materialize the tick-one
/// receipt so `search_known` has one known page to find.
fn materialize_county_page(config: &Config, campaign_id: CampaignId, tick_content_hash: [u8; 32]) {
    let store = SemanticArchiveStoreV1::new(config);
    let county_ref = ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, "26163".to_owned())
        .expect("county ref");
    for (grant_key, source_id) in [
        ("subject", "reader-live-subject"),
        ("employment", "reader-live-employment"),
    ] {
        store
            .grant_knowledge(
                campaign_id,
                &ArchiveKnowledgeGrantV1::try_new(
                    county_ref.clone(),
                    grant_key.to_owned(),
                    1,
                    ArchiveCitationV1::try_new(source_id.to_owned(), format!("{grant_key}@tick-1"))
                        .expect("live grant citation"),
                )
                .expect("live knowledge grant"),
            )
            .expect("knowledge grant persists");
    }
    let batch = ArchiveDirtyBatchV1::try_new(
        1,
        tick_content_hash,
        vec![county_page_input(tick_content_hash)],
    )
    .expect("live dirty batch");
    store
        .materialize_receipt(campaign_id, &batch)
        .expect("live receipt materializes");
}

fn tick_one_content_hash(config: &Config, campaign_id: CampaignId) -> [u8; 32] {
    let receipt: Vec<u8> = config
        .connect(NoTls)
        .expect("receipt connection")
        .query_one(
            "SELECT tick_content_hash FROM babylon_state.archive_dirty_receipt_v1 \
             WHERE campaign_id = $1::uuid AND resolve_tick = 1",
            &[campaign_id.as_uuid()],
        )
        .expect("tick-one receipt query")
        .try_get(0)
        .expect("tick-one receipt digest");
    receipt.try_into().expect("exact receipt digest width")
}

/// Run as the database owner: the role holds SELECT only on the view and no
/// table privilege anywhere else.
fn assert_owner_side_privilege_matrix(client: &mut postgres::Client) {
    let held = client
        .query(
            "SELECT relation::pg_catalog.text || ':' || privilege::pg_catalog.text \
             FROM (VALUES \
                 ('babylon_state.tick_commit'::pg_catalog.text), \
                 ('babylon_state.campaign'), \
                 ('babylon_meta.archive_page_v1'), \
                 ('babylon_meta.archive_knowledge_grant_v1'), \
                 ('babylon_meta.archive_receipt_consumption_v1')) AS tables(relation) \
             CROSS JOIN (VALUES \
                 ('SELECT'::pg_catalog.text), ('INSERT'), ('UPDATE'), ('DELETE'), \
                 ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')) AS privileges(privilege) \
             WHERE pg_catalog.has_table_privilege('babylon_reader', relation, privilege)",
            &[],
        )
        .expect("owner-side privilege matrix query")
        .iter()
        .map(|row| row.try_get::<_, String>(0).expect("matrix entry decodes"))
        .collect::<Vec<_>>();
    assert!(
        held.is_empty(),
        "babylon_reader must hold no base-table privileges, held={held:?}"
    );
    let view_select = client
        .query_one(
            "SELECT pg_catalog.has_table_privilege(\
                 'babylon_reader', 'public.v_committed_tick_status_v1', 'SELECT')",
            &[],
        )
        .expect("view SELECT privilege query")
        .try_get::<_, bool>(0)
        .expect("view SELECT privilege decodes");
    assert!(view_select, "babylon_reader holds SELECT on the view");
    let view_write = client
        .query_one(
            "SELECT pg_catalog.bool_or(priv) FROM (VALUES \
                 (pg_catalog.has_table_privilege(\
                     'babylon_reader', 'public.v_committed_tick_status_v1', 'INSERT')), \
                 (pg_catalog.has_table_privilege(\
                     'babylon_reader', 'public.v_committed_tick_status_v1', 'UPDATE')), \
                 (pg_catalog.has_table_privilege(\
                     'babylon_reader', 'public.v_committed_tick_status_v1', 'DELETE')) \
             ) AS writes(priv)",
            &[],
        )
        .expect("view write privilege query")
        .try_get::<_, bool>(0)
        .expect("view write privilege decodes");
    assert!(
        !view_write,
        "babylon_reader must not hold INSERT, UPDATE, or DELETE on the view"
    );
}

/// Every read a fog-safe reader must never reach, run under
/// `SET ROLE babylon_reader` on a superuser connection.
fn assert_reader_query_refusals(client: &mut postgres::Client) {
    for label_sql in [
        ("read the base tick_commit table", "SELECT pg_catalog.count(*) FROM babylon_state.tick_commit"),
        ("read the base campaign table", "SELECT pg_catalog.count(*) FROM babylon_state.campaign"),
        (
            "read archive pages",
            "SELECT pg_catalog.count(*) FROM babylon_meta.archive_page_v1",
        ),
        (
            "read archive knowledge grants",
            "SELECT pg_catalog.count(*) FROM babylon_meta.archive_knowledge_grant_v1",
        ),
        (
            "read archive receipt consumption",
            "SELECT pg_catalog.count(*) FROM babylon_meta.archive_receipt_consumption_v1",
        ),
        (
            "write through the tick-status view",
            "INSERT INTO public.v_committed_tick_status_v1 \
             (campaign_id, resolve_tick, envelope_layout_version, tick_content_hash, envelope_digest) \
             VALUES ('00000000-0000-0000-0000-000000000000', 1, 1, '\\x00'::bytea, '\\x00'::bytea)",
        ),
        (
            "write the base tick table",
            "INSERT INTO babylon_state.tick_commit \
             (campaign_id, resolve_tick, envelope_layout_version, tick_content_hash, envelope_digest) \
             VALUES ('00000000-0000-0000-0000-000000000000', 1, 1, '\\x00'::bytea, '\\x00'::bytea)",
        ),
        (
            "write archive knowledge grants",
            "INSERT INTO babylon_meta.archive_knowledge_grant_v1 \
             (campaign_id, subject_kind, subject_id, grant_key, granted_tick, \
              provenance_source_id, provenance_locator) \
             VALUES ('00000000-0000-0000-0000-000000000000', 'county', '26163', 'subject', 1, 's', 'l')",
        ),
    ] {
        let (label, sql) = label_sql;
        assert!(
            client.execute(sql, &[]).is_err(),
            "babylon_reader must not {label}"
        );
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_reader_role_reads_the_view_and_refuses_every_base_relation() {
    let target = ReaderTarget::create(
        "readerrolepriv",
        0x2300_0000_0000_0000_0000_0000_0000_00a1,
        2,
    );

    let mut client = target
        .config
        .connect(NoTls)
        .expect("privilege probe connection");
    assert_owner_side_privilege_matrix(&mut client);
    client
        .batch_execute("SET ROLE babylon_reader")
        .expect("superuser delegates to the reader role");

    let row = client
        .query_one(
            "SELECT resolve_tick, envelope_layout_version, tick_content_hash, envelope_digest \
             FROM public.v_committed_tick_status_v1 \
             WHERE campaign_id = $1::uuid \
             ORDER BY resolve_tick DESC LIMIT 1",
            &[target.campaign_id.as_uuid()],
        )
        .expect("babylon_reader selects the committed-tick status view");
    let resolve_tick: i64 = row.try_get(0).expect("view resolve tick decodes");
    assert_eq!(
        resolve_tick, 2,
        "the view exposes the acknowledged commit tail"
    );

    let expected = target
        .config
        .connect(NoTls)
        .expect("owner probe connection")
        .query_one(
            "SELECT envelope_layout_version, tick_content_hash, envelope_digest \
             FROM babylon_state.tick_commit \
             WHERE campaign_id = $1::uuid AND resolve_tick = 2",
            &[target.campaign_id.as_uuid()],
        )
        .expect("owner reads the base marker row");
    let layout: i16 = row.try_get(1).expect("view layout decodes");
    assert_eq!(
        layout,
        expected.try_get::<_, i16>(0).expect("base layout decodes"),
        "the view preserves the envelope identity exactly"
    );
    let content_hash: Vec<u8> = row.try_get(2).expect("view content hash decodes");
    assert_eq!(
        content_hash,
        expected
            .try_get::<_, Vec<u8>>(1)
            .expect("base content hash decodes"),
        "the view preserves the tick content hash exactly"
    );
    let envelope_digest: Vec<u8> = row.try_get(3).expect("view envelope digest decodes");
    assert_eq!(
        envelope_digest,
        expected
            .try_get::<_, Vec<u8>>(2)
            .expect("base envelope digest decodes"),
        "the view preserves the envelope digest exactly"
    );

    assert_reader_query_refusals(&mut client);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_reader_handle_reads_through_confined_login_and_refuses_writer_authority() {
    let target = ReaderTarget::create(
        "readerhandler",
        0x2300_0000_0000_0000_0000_0000_0000_00a2,
        2,
    );
    let tick_one_hash = tick_one_content_hash(&target.config, target.campaign_id);
    materialize_county_page(&target.config, target.campaign_id, tick_one_hash);

    let base = validated_base_config();
    let host = match base.get_hosts() {
        [postgres::config::Host::Tcp(address)] => address.clone(),
        other => panic!("runner DSN must name one loopback TCP host, got {other:?}"),
    };
    let port = base
        .get_ports()
        .first()
        .copied()
        .expect("runner DSN names a port");
    let login = ConfinedLogin::create(&base);
    std::env::set_var(
        READER_DSN_ENV,
        login.dsn(&host, port, &target.database.name),
    );
    let reader = SemanticArchiveReaderV1::from_env().expect("BABYLON_READER_DSN admits");
    std::env::remove_var(READER_DSN_ENV);

    let status = reader
        .committed_tick_status(target.campaign_id)
        .expect("confined login reads the committed-tick status")
        .expect("one committed tick exists");
    assert_eq!(status.resolve_tick(), 2);
    assert_eq!(status.campaign_id(), &target.campaign_id);
    let owner_tail: Vec<u8> = target
        .config
        .connect(NoTls)
        .expect("owner tail connection")
        .query_one(
            "SELECT tick_content_hash FROM babylon_state.tick_commit \
             WHERE campaign_id = $1::uuid AND resolve_tick = 2",
            &[target.campaign_id.as_uuid()],
        )
        .expect("owner tail query")
        .try_get(0)
        .expect("owner tail digest");
    assert_eq!(
        status.tick_content_hash()[..],
        owner_tail[..],
        "the reader status preserves the acknowledged commit tail hash exactly"
    );

    // Fog behavior: the confined credential holds no base-table privilege, so
    // the store search boundary refuses until the Slice 2 fog-safe search
    // views land — even though a known page exists.
    let search = reader.search_known(target.campaign_id, "728576", 10);
    assert!(
        matches!(
            search,
            Err(babylon_persistence::SemanticArchiveReaderErrorV1::Archive(
                babylon_persistence::SemanticArchiveErrorV1::Database { .. }
            ))
        ),
        "the confined reader must hit the fog wall on base tables, got {search:?}"
    );

    // The owner credential carries writer authority: the handle must refuse
    // to operate, not silently read with owner powers.
    let owner_dsn = format!(
        "postgresql://test:test@{host}:{port}/{}",
        target.database.name
    );
    std::env::set_var(READER_DSN_ENV, &owner_dsn);
    let owner_reader = SemanticArchiveReaderV1::from_env().expect("loopback owner DSN admits");
    std::env::remove_var(READER_DSN_ENV);
    let refused = owner_reader.committed_tick_status(target.campaign_id);
    match refused {
        Err(babylon_persistence::SemanticArchiveReaderErrorV1::WriterAuthorityRefused(held)) => {
            assert!(
                !held.is_empty(),
                "the refusal must carry the observed census"
            );
        }
        other => panic!("owner credentials must refuse with writer authority, got {other:?}"),
    }

    login.cleanup();
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_reader_installer_refuses_privilege_drift_and_view_identity_mismatch() {
    let target = ReaderTarget::create(
        "readerroledrift",
        0x2300_0000_0000_0000_0000_0000_0000_00a3,
        1,
    );
    let mut client = target
        .config
        .connect(NoTls)
        .expect("drift probe connection");

    // Drift: one extra effective privilege outside the exact footprint. The
    // installer must census and refuse, never silently re-grant.
    client
        .batch_execute("GRANT SELECT ON babylon_meta.archive_page_v1 TO babylon_reader")
        .expect("drift grant applies");
    let drift = install_reader_role_v1(&target.config).map(|_| ());
    match drift {
        Err(babylon_persistence::SemanticArchiveReaderErrorV1::PrivilegeDrift(held)) => assert!(
            held.contains(&"babylon_meta.archive_page_v1:SELECT".to_owned()),
            "the drift census names the offending entry, held={held:?}"
        ),
        other => panic!("privilege drift must refuse loudly, got {other:?}"),
    }
    client
        .batch_execute("REVOKE SELECT ON babylon_meta.archive_page_v1 FROM babylon_reader")
        .expect("drift revoke applies");
    assert_eq!(
        install_reader_role_v1(&target.config).map(|_| ()),
        Ok(()),
        "the census reconciles to AlreadyCurrent once the drift is revoked"
    );

    // Identity: a same-named base table is not the pinned view.
    client
        .batch_execute(
            "DROP VIEW public.v_committed_tick_status_v1; \
             CREATE TABLE public.v_committed_tick_status_v1(id bigint)",
        )
        .expect("impostor table replaces the view");
    assert_eq!(
        install_reader_role_v1(&target.config).map(|_| ()),
        Err(babylon_persistence::SemanticArchiveReaderErrorV1::ViewMismatch),
        "a non-view relation with the pinned name must refuse"
    );
    client
        .batch_execute("DROP TABLE public.v_committed_tick_status_v1")
        .expect("impostor table drops");
    assert_eq!(
        install_reader_role_v1(&target.config),
        Ok(ReaderRoleDispositionV1::Installed),
        "removal of the view reinstalls it transactionally"
    );

    target.finish();
}
