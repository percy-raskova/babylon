//! Leaf implementation for the parent module; public paths stay on the parent.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_persistence::michigan_economy;

use babylon_persistence::archive_revision::{
    ArchiveDossierBounds, ArchiveDossierPage, ArchiveDossierPending, ArchiveDossierRead,
    ArchiveDossierState, ArchiveDossierUnavailable, ArchiveReadScope, ArchiveSearchState,
};

use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::DurableMaterialRuntime;
use babylon_persistence::michigan_content::MichiganContentPreset;
use babylon_persistence::michigan_economy::{
    MichiganCountyEconomy, QCEW_ECONOMICS_ARTIFACT_SHA256, QCEW_ECONOMICS_FIELD_KEYS,
    QCEW_ECONOMICS_SOURCE_ID,
};
use babylon_persistence::michigan_material::MichiganDeliveryPreset;
use babylon_persistence::observer_reader::{
    ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
};
use babylon_persistence::{
    ArchiveAtomSubjectKind, ArchiveAtomValue, ArchiveEvidenceClass, ArchivePageRef,
    ArchiveReceiptDisposition, ArchiveSubjectKind, ArchiveWorker, SemanticArchiveReader,
    SemanticArchiveStore,
};

use babylon_practice_contract::OrderedPracticeActionBatch;

use babylon_tick::material_world::MaterialWorldRegister;

use postgres::{Config, NoTls};

use std::sync::atomic::{AtomicU64, Ordering};

use std::sync::{Mutex, Once};

use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::MaterialCatalog;
use babylon_persistence::material_storage::LookupAnchor;
use babylon_persistence::michigan_material::MichiganMaterialCatalog;
use babylon_persistence::observer_reader;
use babylon_persistence::observer_reader::CommittedMaterialReceipts;
use babylon_persistence::observer_reader::ObserverEconomySnapshot;
use babylon_persistence::observer_reader::ObserverMaterialCursor;
use babylon_persistence::postgres_catalog;
use babylon_persistence::runtime_session;
use babylon_tick::material_replay::IdentifiedMaterialTick;
use postgres::Client;
use serde_json::Value;
use std::io::Cursor;
use std::path::Path;
use uuid::Uuid;

pub(crate) const ACK: &str =
    "I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES";

pub(crate) static NEXT_DISPOSABLE_TARGET: AtomicU64 = AtomicU64::new(0);

// Role existence is cluster-wide, but the production installers' schema locks
// are database-local. Initialize the groups before any parallel clone or child
// session can install its own grants. The owned harness runs this binary alone.
pub(crate) static OBSERVER_GROUP_ROLES: Once = Once::new();

// PostgreSQL parameter ACLs are cluster-wide even when test databases differ.
// The owned harness runs this test binary alone; only these short shared-row
// mutations serialize, while each clone's material/Archive proof runs freely.
pub(crate) static PARAMETER_ACL_WRITE: Mutex<()> = Mutex::new(());

pub(crate) struct DisposableTarget {
    sequence: u64,
    admin: Config,
    pub(super) writer: Config,
    database: String,
    roles: Vec<String>,
}

pub(crate) fn advance_material_period(runtime: &mut DurableMaterialRuntime) {
    let actions = runtime
        .next_action_batch()
        .expect("the fixture call `next_action_batch` succeeds for the authored inputs");
    runtime
        .advance_and_commit(&mut CollectingSink::default(), &actions)
        .expect("the prepared tick advances and commits");
}

pub(crate) fn assert_archive_progress(
    reader: &SemanticArchiveReader,
    campaign: CampaignId,
    durable: u64,
    processed: u64,
) {
    let status = reader
        .archive_verification_status(campaign)
        .expect("the fixture call `archive_verification_status` succeeds for the authored inputs")
        .expect("the nested fixture result is present");
    assert_eq!(status.durable_tick(), durable);
    assert_eq!(status.processed_tick(), processed);
    let committed = reader
        .committed_tick_status(campaign)
        .expect("the fixture call `committed_tick_status` succeeds for the authored inputs")
        .expect("the nested fixture result is present");
    assert_eq!(*committed.campaign_id(), campaign);
    assert_eq!(committed.resolve_tick(), durable);
}

pub(crate) fn assert_public_qcew_card(
    page: &ArchiveDossierPage,
    campaign: CampaignId,
    county: &MichiganCountyEconomy,
) {
    let expected = [
        (
            "qcew-establishments",
            "QCEW 2024 annual-average establishments",
            county.annual_avg_estabs_count,
        ),
        (
            "qcew-employment",
            "QCEW 2024 annual-average employment (jobs)",
            county.annual_avg_emplvl,
        ),
        (
            "qcew-total-annual-wages",
            "QCEW 2024 total annual wages (USD)",
            county.total_annual_wages,
        ),
        (
            "qcew-average-weekly-wage",
            "QCEW 2024 average weekly wage (USD/week)",
            county.annual_avg_wkly_wage,
        ),
    ];
    let atoms = &page.atoms;
    let signals: Vec<_> = atoms
        .iter()
        .filter(|atom| QCEW_ECONOMICS_FIELD_KEYS.contains(&atom.signal_key()))
        .collect();
    assert_eq!(signals.len(), 4);
    assert_eq!(
        page.content_source.tick(),
        1,
        "content remains sourced from period one"
    );
    assert_eq!(page.content_source.campaign_id(), campaign);
    assert_eq!(
        page.content_sha256,
        babylon_kernel::content_digest::sha256_of(page.markdown.as_bytes())
    );
    let locator = format!(
        "qcew_county_economics_mi_2024.csv.gz#county_geoid={}&sha256={QCEW_ECONOMICS_ARTIFACT_SHA256}",
        county.county_geoid
    );
    for (key, label, value) in expected {
        let atom = signals
            .iter()
            .find(|atom| atom.signal_key() == key)
            .expect("the fixture holds the searched element");
        assert_eq!(*atom.campaign_id(), campaign);
        assert_eq!(atom.subject().kind(), ArchiveAtomSubjectKind::County);
        assert_eq!(atom.subject().id(), county.county_geoid);
        assert_eq!(atom.grant_key(), key);
        assert_eq!(atom.evidence_class(), ArchiveEvidenceClass::Observed);
        assert_eq!(atom.value(), &ArchiveAtomValue::Text(value.to_string()));
        assert_eq!(atom.valid_tick(), 1);
        assert_eq!(atom.citation().source_id(), QCEW_ECONOMICS_SOURCE_ID);
        assert_eq!(atom.citation().locator(), locator);
        assert!(page.citations.contains(atom.citation()));
        assert!(page.markdown.contains(&format!("- **{label}:** {value} —")));
    }
    assert!(atoms
        .iter()
        .all(|atom| !matches!(atom.signal_key(), "median-wage" | "production" | "phi-hour")));
}

pub(crate) fn current_archive_scope(
    reader: &SemanticArchiveReader,
    campaign: CampaignId,
) -> ArchiveReadScope {
    let status = reader
        .committed_tick_status(campaign)
        .expect("the fixture call `committed_tick_status` succeeds for the authored inputs")
        .expect("the nested fixture result is present");
    assert_eq!(*status.campaign_id(), campaign);
    ArchiveReadScope::committed(campaign, status.resolve_tick(), *status.tick_content_hash())
        .expect("the fixture observation carries the committed value")
}

pub(crate) fn read_county(
    reader: &SemanticArchiveReader,
    scope: &ArchiveReadScope,
    geoid: &str,
) -> ArchiveDossierRead {
    reader
        .dossier_as_of(
            scope,
            &ArchivePageRef::try_new(ArchiveSubjectKind::County, geoid.to_owned())
                .expect("the authored fixture satisfies the constructor invariants"),
            &ArchiveDossierBounds::try_new(100, None)
                .expect("the authored fixture satisfies the constructor invariants"),
        )
        .expect("the fixture dossier exists at the authored period")
}

pub(crate) fn assert_scoped_page<'a>(
    read: &'a ArchiveDossierRead,
    scope: &ArchiveReadScope,
    expected: ArchiveSearchState,
) -> &'a ArchiveDossierPage {
    assert_eq!(&read.scope, scope);
    match (&read.state, expected) {
        (
            ArchiveDossierState::Ready {
                page,
                verified_through_tick,
            },
            ArchiveSearchState::Ready,
        ) => {
            assert_eq!(*verified_through_tick, scope.tick());
            page
        }
        (
            ArchiveDossierState::Pending {
                page: Some(page),
                reason,
            },
            ArchiveSearchState::Pending(expected),
        ) => {
            assert_eq!(*reason, expected);
            assert_eq!(page.changes.changes.len(), 0);
            assert!(page.changes.next_cursor.is_none());
            page
        }
        other => panic!("unexpected scoped page state: {other:?}"),
    }
}

pub(crate) fn assert_all_county_cards(
    reader: &SemanticArchiveReader,
    scope: &ArchiveReadScope,
    expected: ArchiveSearchState,
) -> Vec<ArchiveDossierPage> {
    let search = reader
        .search_as_of(scope, "QCEW 2024", 100)
        .expect("the fixture call `search_as_of` succeeds for the authored inputs");
    assert_eq!(&search.scope, scope);
    assert_eq!(search.state, expected);
    assert!(!search.truncated);
    assert_eq!(search.hits.len(), 83);
    search
        .hits
        .iter()
        .zip(
            michigan_economy::michigan_economy()
                .expect("the Michigan economy fixture builds")
                .counties(),
        )
        .map(|(hit, county)| {
            assert_eq!(hit.subject.kind(), ArchiveSubjectKind::County);
            assert_eq!(hit.subject.id(), county.county_geoid);
            let read = read_county(reader, scope, &county.county_geoid);
            assert_eq!(read.subject, hit.subject);
            let page = assert_scoped_page(&read, scope, expected);
            assert_eq!(page.revision_id, hit.revision_id);
            assert_eq!(page.content_source, hit.content_source);
            assert_eq!(page.title, hit.title);
            assert_public_qcew_card(page, scope.campaign_id(), county);
            page.clone()
        })
        .collect()
}

pub(crate) fn assert_retained_content(actual: &ArchiveDossierPage, original: &ArchiveDossierPage) {
    assert_eq!(actual.revision_id, original.revision_id);
    assert_eq!(actual.effective_tick, original.effective_tick);
    assert_eq!(actual.content_source, original.content_source);
    assert_eq!(actual.title, original.title);
    assert_eq!(actual.question, original.question);
    assert_eq!(actual.signals, original.signals);
    assert_eq!(actual.markdown, original.markdown);
    assert_eq!(actual.content_sha256, original.content_sha256);
    assert_eq!(actual.citations, original.citations);
    assert_eq!(actual.atoms, original.atoms);
    // Target readiness and history coverage are scoped observations, not source bytes.
    let labels = |page: &ArchiveDossierPage| {
        page.links
            .iter()
            .map(|link| (link.target.clone(), link.retained_label.clone()))
            .collect::<Vec<_>>()
    };
    assert_eq!(labels(actual), labels(original));
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed Michigan ticks"]
pub(crate) fn live_michigan_all_county_cards_keep_public_source_and_quiet_restart_freshness() {
    let mut target = DisposableTarget::create();
    let campaign =
        CampaignId::from_uuid(Uuid::from_u128(0x0044_0000_0000_0000_0000_0000_0000_0002));
    SemanticArchiveStore::new(&target.writer)
        .verify_schema()
        .expect("the authored fixture satisfies the rule");
    // Keep the revision table without planner statistics through the full drain.
    // This lock permits worker DML but blocks automatic VACUUM/ANALYZE without
    // changing the admitted schema. Knowledge tables remain unlocked because
    // pinning a cohort deliberately analyzes them before its first read.
    let mut cold_connection = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut cold_statistics = cold_connection
        .transaction()
        .expect("the test database opens a transaction");
    cold_statistics
        .batch_execute(
            "SET LOCAL lock_timeout TO '5s'; \
             LOCK TABLE babylon_meta.archive_page_revision_v2 \
             IN SHARE UPDATE EXCLUSIVE MODE",
        )
        .expect("the test database applies the schema statements");
    assert_revision_statistics_absent(&mut cold_statistics);
    let preset = MichiganDeliveryPreset::Standard;
    let mut runtime = DurableMaterialRuntime::create(
        &target.writer,
        campaign,
        MichiganContentPreset::new_campaign(preset)
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation"),
    )
    .expect("the test database creates the fixture campaign");
    babylon_persistence::install_reader_role(&target.writer)
        .expect("the test database installs the reader role");
    observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    let config = target.login("babylon_reader", "countycards");
    let reader = SemanticArchiveReader::new(&config)
        .expect("the constructor accepts the authored fixture arguments");
    let foundation = read_county(&reader, &ArchiveReadScope::foundation(campaign), "26163");
    assert_eq!(
        foundation.state,
        ArchiveDossierState::Unavailable(ArchiveDossierUnavailable::FoundationHasNoPage)
    );
    for relation in [
        "babylon_meta.archive_knowledge_grant_v1",
        "babylon_state.territory_state_field_v1",
    ] {
        let error = config
            .connect(NoTls)
            .expect("the test database accepts the connection")
            .query(&format!("SELECT * FROM {relation} LIMIT 1"), &[])
            .expect_err("the fixture call `query` fails for the authored inputs");
        assert_eq!(
            error.code(),
            Some(&postgres::error::SqlState::INSUFFICIENT_PRIVILEGE)
        );
    }
    advance_material_period(&mut runtime);
    assert_archive_progress(&reader, campaign, 1, 0);
    let mut worker = ArchiveWorker::new(&target.writer);
    let producer = babylon_persistence::captured_archive_producer(&target.writer, campaign)
        .expect("the fixture call `captured_archive_producer` succeeds for the authored inputs");
    let first = worker
        .sweep_once(campaign, &producer)
        .expect("the fixture sweep completes");
    assert_eq!(
        first.dispositions(),
        &[(1, ArchiveReceiptDisposition::Paged)]
    );
    assert_archive_progress(&reader, campaign, 1, 0);
    let scope = current_archive_scope(&reader, campaign);
    let pages = assert_all_county_cards(
        &reader,
        &scope,
        ArchiveSearchState::Pending(ArchiveDossierPending::ReceiptProcessing),
    );
    drop((runtime, worker, producer));
    assert_restart_drains_and_verifies_quiet_periods(&target, &reader, &scope, &pages);
    assert_revision_statistics_absent(&mut cold_statistics);
    cold_statistics
        .rollback()
        .expect("the open transaction rolls back");
}

pub(crate) fn assert_revision_statistics_absent(client: &mut impl postgres::GenericClient) {
    let count: i64 = client
        .query_one(
            "SELECT count(*) FROM pg_catalog.pg_statistic \
             WHERE starelid='babylon_meta.archive_page_revision_v2'::pg_catalog.regclass",
            &[],
        )
        .expect("the seeded row is present exactly once")
        .get(0);
    assert_eq!(
        count, 0,
        "revision reads must succeed without planner statistics"
    );
}

pub(crate) fn assert_restart_drains_and_verifies_quiet_periods(
    target: &DisposableTarget,
    reader: &SemanticArchiveReader,
    first_scope: &ArchiveReadScope,
    pages: &[ArchiveDossierPage],
) {
    let campaign = first_scope.campaign_id();
    let mut runtime = DurableMaterialRuntime::open(
        &target.writer,
        campaign,
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation")
            .digest(),
    )
    .expect("the fixture opens the authored source");
    let mut worker = ArchiveWorker::new(&target.writer);
    let producer = babylon_persistence::captured_archive_producer(&target.writer, campaign)
        .expect("the fixture call `captured_archive_producer` succeeds for the authored inputs");
    for _ in 0..4 {
        if worker
            .sweep_once(campaign, &producer)
            .expect("the fixture sweep completes")
            .verified_tick()
            == 1
        {
            break;
        }
    }
    assert_archive_progress(reader, campaign, 1, 1);
    let ready_pages = assert_all_county_cards(reader, first_scope, ArchiveSearchState::Ready);
    assert_eq!(ready_pages.len(), pages.len());
    for (ready, staged) in ready_pages.iter().zip(pages) {
        assert_retained_content(ready, staged);
    }
    let held_read = read_county(reader, first_scope, "26163");
    let held = assert_scoped_page(&held_read, first_scope, ArchiveSearchState::Ready);
    assert!(held.changes.next_cursor.is_none());
    assert_eq!(held.changes.changes.len(), held.atoms.len());
    for change in &held.changes.changes {
        assert_eq!(change.publication_tick, 1);
        assert!(change.before.is_none());
        assert!(held.atoms.contains(
            change
                .after
                .as_ref()
                .expect("the fixture set the optional field before this read")
        ));
    }
    let resweep = worker
        .sweep_once(campaign, &producer)
        .expect("the fixture sweep completes");
    assert_eq!(resweep.dispositions().len(), 0);
    for tick in 2..=3 {
        advance_material_period(&mut runtime);
        let scope = current_archive_scope(reader, campaign);
        assert_eq!(scope.tick(), tick);
        assert_archive_progress(reader, campaign, tick, tick - 1);
        let pending = read_county(reader, &scope, "26163");
        assert_retained_content(
            assert_scoped_page(
                &pending,
                &scope,
                ArchiveSearchState::Pending(ArchiveDossierPending::ReceiptProcessing),
            ),
            held,
        );
        let quiet = worker
            .sweep_once(campaign, &producer)
            .expect("the fixture sweep completes");
        assert_eq!(
            quiet.dispositions(),
            &[(tick, ArchiveReceiptDisposition::Applied)]
        );
        assert_archive_progress(reader, campaign, tick, tick);
        let current_pages = assert_all_county_cards(reader, &scope, ArchiveSearchState::Ready);
        assert_eq!(current_pages.len(), pages.len());
        for (current, original) in current_pages.iter().zip(pages) {
            assert_retained_content(current, original);
        }
        let current = read_county(reader, &scope, "26163");
        assert_eq!(
            assert_scoped_page(&current, &scope, ArchiveSearchState::Ready).changes,
            held.changes
        );
        let historical = read_county(reader, first_scope, "26163");
        assert_eq!(
            assert_scoped_page(&historical, first_scope, ArchiveSearchState::Ready),
            held
        );
        drop(runtime);
        runtime = DurableMaterialRuntime::open(
            &target.writer,
            campaign,
            MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
                .create_foundation(&crate::test_support::catalog())
                .expect("the authored catalog builds the foundation")
                .digest(),
        )
        .expect("the fixture opens the authored source");
        assert_eq!(runtime.session().completed_tick(), tick);
        assert_eq!(read_county(reader, &scope, "26163"), current);
    }
}

impl DisposableTarget {
    pub(super) fn create() -> Self {
        assert_eq!(
            std::env::var("BABYLON_POSTGRES_DISPOSABLE_ACK").as_deref(),
            Ok(ACK)
        );
        let canary = std::env::var("BABYLON_POSTGRES_DISPOSABLE_CANARY")
            .expect("the fixture variable is bound");
        assert_eq!(canary.len(), 32);
        let admin: Config = std::env::var("BABYLON_POSTGRES_TEST_DSN")
            .expect("the fixture variable is bound")
            .parse()
            .expect("the authored literal parses as the declared type");
        postgres_catalog::validate_connection_target(&admin)
            .expect("the authored fixture satisfies the rule");
        assert_eq!(admin.get_user(), Some("test"));
        assert_eq!(admin.get_dbname(), Some("postgres"));
        let mut connection = admin
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let actual: Option<String> = connection
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.disposable_runtime',true)",
                &[],
            )
            .expect("the seeded row is present exactly once")
            .get(0);
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        let template =
            std::env::var("BABYLON_RUNTIME_TEMPLATE_DB").expect("the fixture variable is bound");
        let suffix = template
            .strip_prefix("per281_runtime_template_")
            .expect("the fixture call `strip_prefix` succeeds for the authored inputs");
        assert_eq!(suffix.len(), 12);
        assert!(suffix.bytes().all(|byte| byte.is_ascii_hexdigit()));
        let sequence = NEXT_DISPOSABLE_TARGET
            .try_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                value.checked_add(1)
            })
            .expect("disposable target sequence remains bounded");
        let database = format!(
            "per281_runtime_materialobserver_{}_{sequence}",
            std::process::id()
        );
        connection
            .batch_execute(&format!(
                "CREATE DATABASE \"{database}\" OWNER test TEMPLATE \"{template}\""
            ))
            .expect("the test database applies the schema statements");
        let mut writer = admin.clone();
        writer.dbname(&database);
        let target = Self {
            sequence,
            admin,
            writer,
            database,
            roles: Vec::new(),
        };
        OBSERVER_GROUP_ROLES.call_once(|| {
            babylon_persistence::install_reader_role(&target.writer)
                .expect("initialize shared reader group");
            observer_reader::provision_observer_role(&target.writer)
                .expect("initialize shared observer group");
        });
        target
    }

    pub(super) fn login(&mut self, group: &str, suffix: &str) -> Config {
        assert!(matches!(group, "babylon_observer" | "babylon_reader"));
        assert!(suffix.bytes().all(|byte| byte.is_ascii_lowercase()));
        let role = format!(
            "g4_material_{suffix}_{}_{}",
            std::process::id(),
            self.sequence
        );
        let mut connection = self
            .writer
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let created = {
            let _guard = PARAMETER_ACL_WRITE
                .lock()
                .expect("the fixture lock is never poisoned");
            connection.batch_execute(&format!("CREATE ROLE \"{role}\" LOGIN PASSWORD 'reader' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; GRANT {group} TO \"{role}\"; GRANT SET ON PARAMETER event_triggers TO \"{role}\""))
        };
        created.expect("the test database returns the created row");
        self.roles.push(role.clone());
        let mut config = self.writer.clone();
        config.user(&role).password("reader");
        config
    }
}

impl Drop for DisposableTarget {
    fn drop(&mut self) {
        if let Ok(mut connection) = self.admin.connect(NoTls) {
            let dropped = connection.batch_execute(&format!(
                "DROP DATABASE IF EXISTS \"{}\" WITH (FORCE)",
                self.database
            ));
            if !std::thread::panicking() {
                dropped.expect("owned clone cleanup");
            }
            for role in &self.roles {
                let removed = {
                    let _guard = PARAMETER_ACL_WRITE
                        .lock()
                        .expect("the fixture lock is never poisoned");
                    connection.batch_execute(&format!("REVOKE SET ON PARAMETER event_triggers FROM \"{role}\"; DROP ROLE IF EXISTS \"{role}\""))
                };
                if !std::thread::panicking() {
                    removed.expect("owned role cleanup");
                }
            }
        }
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
pub(crate) fn live_material_observer_reuse_authenticates_actual_foundation_bytes() {
    let mut target = DisposableTarget::create();
    let catalog = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .expect("the authored input admits the derived value");
    let campaign =
        CampaignId::from_uuid(Uuid::from_u128(0x0044_0000_0000_0000_0000_0000_0000_0041));
    let mut runtime = DurableMaterialRuntime::create(
        &target.writer,
        campaign,
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&catalog)
            .expect("the authored catalog builds the foundation"),
    )
    .expect("the test database creates the fixture campaign");
    observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    let observer_config = target.login("babylon_observer", "observer");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
            .expect("the test database accepts the connection");
    let mut cursor = None;
    let admitted = observer
        .snapshot_with_cursor(campaign, 0, &mut cursor)
        .expect("the fixture snapshot carries its cursor");
    assert_eq!(
        cursor
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .completed_tick(),
        0
    );
    advance_material_period(&mut runtime);
    let committed = observer.committed_material_observation(campaign, 1).expect(
        "the fixture call `committed_material_observation` succeeds for the authored inputs",
    );
    assert_eq!(
        observer.committed_material_receipts(campaign, 1).expect(
            "the fixture call `committed_material_receipts` succeeds for the authored inputs"
        ),
        committed.accounting
    );
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    assert_foundation_byte_changes_refused(
        &mut writer,
        &observer,
        campaign,
        &mut cursor,
        &admitted,
    );
    assert_foundation_identity_changes_refused(
        &mut writer,
        &observer,
        campaign,
        &mut cursor,
        &admitted,
    );
    assert_foundation_clock_changes_refused(
        &mut writer,
        &observer,
        campaign,
        &mut cursor,
        &admitted,
    );
    let recovered = observer.committed_material_observation(campaign, 1).expect(
        "the fixture call `committed_material_observation` succeeds for the authored inputs",
    );
    assert_eq!(recovered.snapshot, committed.snapshot);
    assert_eq!(recovered.accounting, committed.accounting);
    assert_eq!(recovered.production_evidence, committed.production_evidence);
}

pub(crate) fn assert_foundation_byte_changes_refused(
    writer: &mut Client,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    cursor: &mut Option<ObserverMaterialCursor>,
    admitted: &ObserverEconomySnapshot,
) {
    // All identifiers here are fixed test-owned SQL names, never player input.
    for (table, column) in [
        ("campaign_foundation", "stable_graph"),
        ("campaign_foundation", "world_registers"),
        ("campaign_foundation", "resolver_manifest"),
        ("campaign_foundation", "prepared_environment"),
        ("campaign_foundation", "content_bundle_bytes"),
        ("campaign_foundation", "defines_hash"),
        ("campaign_foundation", "rules_hash"),
        ("campaign_foundation", "ref_digest"),
        ("campaign_foundation", "foundation_sha256"),
        ("material_campaign_foundation_v3", "initial_register_bytes"),
        ("material_campaign_foundation_v3", "content_sha256"),
        ("material_campaign_foundation_v3", "foundation_sha256"),
    ] {
        let original: Vec<u8> = writer
            .query_one(
                &format!("SELECT {column} FROM babylon_state.{table} WHERE campaign_id=$1"),
                &[campaign.as_uuid()],
            )
            .expect("the seeded row is present exactly once")
            .get(0);
        let mut changed = original.clone();
        changed[0] ^= 1;
        let update = format!("UPDATE babylon_state.{table} SET {column}=$2 WHERE campaign_id=$1");
        assert_eq!(
            writer
                .execute(&update, &[campaign.as_uuid(), &changed])
                .expect("the test database applies the setup statement"),
            1
        );
        // For body mutations every stored hash claim remains unchanged.
        let refused = observer.snapshot_with_cursor(campaign, 0, cursor);
        let refused_receipts = observer.committed_material_receipts(campaign, 1);
        let refused_production = observer.committed_material_observation(campaign, 1);
        writer
            .execute(&update, &[campaign.as_uuid(), &original])
            .expect("the test database applies the setup statement");
        assert!(
            matches!(refused, Err(ObserverEconomyError::ScenarioMismatch)),
            "{table}.{column}"
        );
        assert!(
            matches!(
                refused_receipts,
                Err(ObserverEconomyError::ScenarioMismatch)
            ),
            "{table}.{column} receipts"
        );
        assert!(
            matches!(
                refused_production,
                Err(ObserverEconomyError::ScenarioMismatch)
            ),
            "{table}.{column} production"
        );
        assert_eq!(
            cursor
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .completed_tick(),
            0
        );
        assert_eq!(
            observer
                .snapshot_with_cursor(campaign, 0, cursor)
                .expect("the fixture snapshot carries its cursor"),
            *admitted
        );
    }
}

pub(crate) fn assert_foundation_identity_changes_refused(
    writer: &mut Client,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    cursor: &mut Option<ObserverMaterialCursor>,
    admitted: &ObserverEconomySnapshot,
) {
    let original = writer.query_one(
        "SELECT replay_session_id,rng_seed FROM babylon_state.campaign_foundation WHERE campaign_id=$1",
        &[campaign.as_uuid()],
    ).expect("the seeded row is present exactly once");
    let session: String = original.get(0);
    let seed: i64 = original.get(1);
    for change_session in [true, false] {
        let changed_session = if change_session {
            format!("{session}x")
        } else {
            session.clone()
        };
        let changed_seed = if change_session { seed } else { seed ^ 1 };
        let update = "UPDATE babylon_state.campaign_foundation SET replay_session_id=$2,rng_seed=$3 WHERE campaign_id=$1";
        writer
            .execute(
                update,
                &[campaign.as_uuid(), &changed_session, &changed_seed],
            )
            .expect("the test database applies the setup statement");
        let refused = observer.snapshot_with_cursor(campaign, 0, cursor);
        writer
            .execute(update, &[campaign.as_uuid(), &session, &seed])
            .expect("the test database applies the setup statement");
        assert!(matches!(
            refused,
            Err(ObserverEconomyError::ScenarioMismatch)
        ));
        assert_eq!(
            observer
                .snapshot_with_cursor(campaign, 0, cursor)
                .expect("the fixture snapshot carries its cursor"),
            *admitted
        );
    }
}

pub(crate) fn assert_foundation_clock_changes_refused(
    writer: &mut Client,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    cursor: &mut Option<ObserverMaterialCursor>,
    admitted: &ObserverEconomySnapshot,
) {
    let original = writer.query_one(
        "SELECT preset_id,duration_kind,final_period FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1",
        &[campaign.as_uuid()],
    ).expect("the seeded row is present exactly once");
    let preset: String = original.get(0);
    let duration: String = original.get(1);
    let final_period: Option<i64> = original.get(2);
    let clock_update = "UPDATE babylon_state.material_campaign_foundation_v3 SET preset_id=$2,duration_kind=$3,final_period=$4 WHERE campaign_id=$1";
    for (changed_preset, changed_duration, changed_period) in [
        ("national-world", duration.as_str(), final_period),
        (preset.as_str(), "continuous", None),
        (
            preset.as_str(),
            "finite",
            Some(final_period.unwrap_or(0) + 1),
        ),
    ] {
        if changed_preset == preset
            && changed_duration == duration
            && changed_period == final_period
        {
            continue;
        }
        writer
            .execute(
                clock_update,
                &[
                    campaign.as_uuid(),
                    &changed_preset,
                    &changed_duration,
                    &changed_period,
                ],
            )
            .expect("the test database applies the setup statement");
        let refused = observer.snapshot_with_cursor(campaign, 0, cursor);
        writer
            .execute(
                clock_update,
                &[campaign.as_uuid(), &preset, &duration, &final_period],
            )
            .expect("the test database applies the setup statement");
        assert!(matches!(
            refused,
            Err(ObserverEconomyError::ScenarioMismatch)
        ));
        assert_eq!(
            observer
                .snapshot_with_cursor(campaign, 0, cursor)
                .expect("the fixture snapshot carries its cursor"),
            *admitted
        );
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed material ticks"]
#[allow(
    clippy::too_many_lines,
    reason = "`live_material_observer_preserves_history_and_denies_preview_blob_authority` keeps one authored boundary's fixture and assertions together"
)]
pub(crate) fn live_material_observer_preserves_history_and_denies_preview_blob_authority() {
    let mut target = DisposableTarget::create();
    let preset = MichiganDeliveryPreset::Standard;
    let catalog = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .expect("the authored input admits the derived value");
    let campaign =
        CampaignId::from_uuid(Uuid::from_u128(0x0044_0000_0000_0000_0000_0000_0000_0001));
    let mut runtime = DurableMaterialRuntime::create(
        &target.writer,
        campaign,
        MichiganContentPreset::new_campaign(preset)
            .create_foundation(&catalog)
            .expect("the authored catalog builds the foundation"),
    )
    .expect("the test database creates the fixture campaign");
    assert_single_foundation_storage(&target.writer, campaign, runtime.session().catalog());
    babylon_persistence::install_reader_role(&target.writer)
        .expect("the test database installs the reader role");
    observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    let observer_config = target.login("babylon_observer", "observer");
    let known_config = target.login("babylon_reader", "known");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
            .expect("the test database accepts the connection");
    let known = ObserverEconomyReader::connect(&known_config, ObserverVisibility::KnownPreview)
        .expect("the test database accepts the connection");
    let archive = SemanticArchiveReader::new(&known_config)
        .expect("the constructor accepts the authored fixture arguments");
    let mut cursor = None;
    let zero = opening_roles(&observer, &known, &known_config, campaign, &mut cursor);
    let mut history_at_two = None;
    for tick in 1..=18 {
        advance_material_period(&mut runtime);
        let snapshot = observer
            .snapshot_with_cursor(campaign, tick, &mut cursor)
            .expect("the fixture snapshot carries its cursor");
        assert_eq!(
            cursor
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .completed_tick(),
            tick
        );
        assert_eq!(snapshot.foundation_digest, zero.foundation_digest);
        assert_eq!(snapshot.resolve_tick, tick);
        assert_eq!(snapshot.counties.len(), 83);
        assert_material_accounts(&snapshot);
        assert_known_material_absence(
            &mut known
                .snapshot(campaign, tick)
                .expect("the fixture captures a consistent snapshot"),
        );
        archive
            .committed_tick_status(campaign)
            .expect("the fixture call `committed_tick_status` succeeds for the authored inputs");
        if tick == 2 {
            history_at_two = Some(snapshot);
        }
        if tick == 3 {
            runtime = DurableMaterialRuntime::open(
                &target.writer,
                campaign,
                MichiganContentPreset::new_campaign(preset)
                    .create_foundation(&catalog)
                    .expect("the authored catalog builds the foundation")
                    .digest(),
            )
            .expect("the fixture opens the authored source");
            assert_eq!(runtime.session().completed_tick(), 3);
            let fresh =
                ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
                    .expect("the test database accepts the connection");
            assert_eq!(
                fresh
                    .snapshot(campaign, 2)
                    .expect("the fixture captures a consistent snapshot"),
                history_at_two.clone().expect("the fixture value clones")
            );
            assert_material_accounts(
                &fresh
                    .snapshot(campaign, 3)
                    .expect("the fixture captures a consistent snapshot"),
            );
            assert_committed_accounting_observation(
                &observer,
                &fresh,
                campaign,
                runtime
                    .tail()
                    .expect("the fixture sequence holds more than one row"),
            );
            assert_authenticated_time_debits(&fresh, campaign, &runtime);
        }
    }
    assert_eq!(
        observer
            .snapshot_with_cursor(campaign, 2, &mut cursor)
            .expect("the fixture snapshot carries its cursor"),
        history_at_two.expect("the fixture session reaches period two")
    );
    assert_eq!(
        cursor
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .completed_tick(),
        18
    );
    assert_eq!(
        observer
            .campaigns()
            .expect("the fixture lists the authored campaigns")[0]
            .durable_tick,
        18
    );
    assert_eq!(
        observer.snapshot(campaign, 19),
        Err(ObserverEconomyError::TickAbsent)
    );

    let mut connection = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    assert_corrupted_register_is_rejected(
        &mut connection,
        &observer,
        campaign,
        runtime.session().catalog(),
        &mut cursor,
    );

    let known_role = known_config
        .get_user()
        .expect("the fixture call `get_user` succeeds for the authored inputs");
    connection
        .batch_execute(&format!(
            "GRANT SELECT ON public.v_observer_material_state_v1 TO \"{known_role}\""
        ))
        .expect("the test database applies the schema statements");
    assert_eq!(
        known.snapshot(campaign, 18),
        Err(ObserverEconomyError::Authority)
    );
}

pub(crate) fn assert_preview_blob_denied(known_config: &Config) {
    assert!(known_config
        .connect(NoTls)
        .expect("the test database accepts the connection")
        .query(
            "SELECT register_storage_bytes FROM public.v_observer_material_state_v1",
            &[]
        )
        .is_err());
}

pub(crate) fn identity_hex(bytes: [u8; 32]) -> String {
    use std::fmt::Write as _;
    bytes
        .iter()
        .fold(String::with_capacity(64), |mut result, byte| {
            write!(result, "{byte:02x}").expect("the in-memory formatter accepts the written text");
            result
        })
}

pub(crate) fn opening_roles(
    observer: &ObserverEconomyReader,
    known: &ObserverEconomyReader,
    known_config: &Config,
    campaign: CampaignId,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> ObserverEconomySnapshot {
    let zero = observer
        .snapshot_with_cursor(campaign, 0, cursor)
        .expect("the fixture snapshot carries its cursor");
    assert_eq!(zero.counties.len(), 83);
    assert_eq!(
        zero.production
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .sites
            .len(),
        5
    );
    assert_material_accounts(&zero);
    assert_known_material_absence(
        &mut known
            .snapshot(campaign, 0)
            .expect("the fixture captures a consistent snapshot"),
    );
    assert_captured_foundation_denied(known_config);
    assert!(matches!(
        observer.committed_material_receipts(campaign, 0),
        Err(ObserverEconomyError::TickAbsent)
    ));
    assert!(matches!(
        known.committed_material_receipts(campaign, 1),
        Err(ObserverEconomyError::Authority)
    ));
    assert!(matches!(
        observer.committed_material_receipts(campaign, 1),
        Err(ObserverEconomyError::TickAbsent)
    ));

    assert!(matches!(
        observer.committed_material_observation(campaign, 0),
        Err(ObserverEconomyError::TickAbsent)
    ));
    assert!(matches!(
        known.committed_material_observation(campaign, 1),
        Err(ObserverEconomyError::Authority)
    ));
    assert!(matches!(
        observer.committed_material_observation(campaign, 1),
        Err(ObserverEconomyError::TickAbsent)
    ));

    assert_eq!(
        observer
            .campaigns()
            .expect("the fixture lists the authored campaigns"),
        known
            .campaigns()
            .expect("the fixture lists the authored campaigns")
    );
    assert_eq!(
        observer
            .campaigns()
            .expect("the fixture lists the authored campaigns")[0]
            .durable_tick,
        0
    );
    zero
}

pub(crate) fn assert_known_material_absence(snapshot: &mut ObserverEconomySnapshot) {
    assert_eq!(snapshot.visibility, ObserverVisibility::KnownPreview);
    assert!(snapshot.production.is_none());
    assert!(snapshot
        .production_evidence_digest()
        .expect("the evidence body has a digest")
        .is_none());
}

pub(crate) fn assert_material_accounts(snapshot: &ObserverEconomySnapshot) {
    use babylon_persistence::production_observation::ProductionDeliveryStage;
    use std::collections::{BTreeMap, BTreeSet};

    let rows = snapshot
        .production
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert!(rows
        .events
        .iter()
        .all(|event| event.period <= snapshot.resolve_tick));
    if snapshot.resolve_tick == 0 {
        assert!(rows.material_balance.is_none());
        assert_eq!(rows.events.len(), 0);
        return;
    }
    let balance = rows
        .material_balance
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(balance.period, snapshot.resolve_tick);
    assert_ne!(balance.rows.len(), 0);
    let mut principals = BTreeSet::new();
    let mut arrivals = BTreeMap::new();
    for event in &rows.events {
        let expected_stage = match event.kind.as_str() {
            "arrival" => Some(ProductionDeliveryStage::Arrival),
            "delivery" => Some(ProductionDeliveryStage::Delivery),
            "quantity realization" => Some(ProductionDeliveryStage::QuantityRealization),
            _ => None,
        };
        assert_eq!(
            event.delivery_evidence.as_ref().map(|row| row.stage),
            expected_stage
        );
        let Some(evidence) = &event.delivery_evidence else {
            continue;
        };
        let route = rows
            .routes
            .iter()
            .find(|route| route.id == evidence.supplier_relation_id)
            .expect("the fixture holds the searched element");
        assert_eq!(evidence.good_id, route.good_id);
        assert_eq!(evidence.unit_id, route.unit_id);
        assert!(evidence.quantity > 0);
        let catalog = crate::test_support::catalog();
        let source = catalog
            .routes()
            .iter()
            .find(|row| identity_hex(row.id().as_bytes()) == route.physical_route_id)
            .expect("the fixture holds the searched element");
        assert_eq!(
            evidence.order_id,
            identity_hex(source.order_id().as_bytes())
        );
        if event.period == balance.period && evidence.stage == ProductionDeliveryStage::Arrival {
            let key = (&route.buyer_site_id, &evidence.good_id, &evidence.unit_id);
            *arrivals.entry(key).or_insert(0_u128) += u128::from(evidence.quantity);
        }
    }
    for row in &balance.rows {
        let principal = (&row.site_id, &row.good_id, &row.unit_id);
        assert!(principals.insert(principal));
        assert_eq!(
            u128::from(row.opening)
                + u128::from(row.arrivals)
                + u128::from(row.local_received)
                + u128::from(row.produced),
            u128::from(row.consumed)
                + u128::from(row.dispatched)
                + u128::from(row.local_transferred)
                + u128::from(row.final_demand_fulfilled)
                + u128::from(row.closing)
        );
        assert_eq!(
            u128::from(row.arrivals),
            arrivals.remove(&principal).unwrap_or(0)
        );
        let site = rows
            .sites
            .iter()
            .find(|site| site.id == row.site_id)
            .expect("the fixture holds the searched element");
        let closing = site
            .inventory
            .iter()
            .find(|stock| stock.good_id == row.good_id && stock.unit_id == row.unit_id)
            .map_or(0, |stock| stock.quantity);
        assert_eq!(row.closing, closing);
    }
    assert!(arrivals.is_empty());
}

pub(crate) fn assert_corrupted_register_is_rejected(
    connection: &mut Client,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    catalog: &MaterialCatalog,
    cursor: &mut Option<ObserverMaterialCursor>,
) {
    // A syntactically valid stored register mutation cannot retain its committed identity.
    let base: Vec<u8> = connection.query_one(
        "SELECT initial_register_bytes FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1",
        &[campaign.as_uuid()],
    ).expect("the seeded row is present exactly once").get(0);
    let opening = babylon_persistence::material_storage::seed(catalog, &base)
        .expect("the fixture seeds the authored rows");
    let rows = connection.query(
        "SELECT resolve_tick, register_storage_bytes, receipt_storage_bytes, lookup_delta_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1 AND resolve_tick<=18 ORDER BY resolve_tick",
        &[campaign.as_uuid()],
    ).expect("the seeded rows are readable");
    assert_eq!(rows.len(), 18);
    let mut chain = babylon_persistence::material_storage::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let mut original = None;
    for (index, row) in rows.into_iter().enumerate() {
        assert_eq!(
            row.get::<_, i64>(0),
            i64::try_from(index + 1).expect("the fixture value fits the target range")
        );
        let lookup = babylon_persistence::material_storage::read_period_lookup(
            &opening,
            u64::try_from(index + 1).expect("the fixture value fits the target range"),
            &row.get::<_, Vec<u8>>(3),
            LookupAnchor::Previous(chain),
        )
        .expect("the committed lookup table reads");
        chain = lookup.chain;
        if index == 17 {
            let package: Vec<u8> = row.get(1);
            let receipt_package: Vec<u8> = row.get(2);
            let (canonical, receipts) = babylon_persistence::material_storage::decode(
                catalog,
                &opening,
                18,
                &package,
                &receipt_package,
                &lookup.lookup,
                lookup.chain,
            )
            .expect("the committed canonical bytes decode");
            let register = MaterialWorldRegister::decode_external(catalog, canonical.clone())
                .expect("the committed canonical bytes decode");
            let mut state = register.state().clone();
            state.inventory[0].quantity += 1;
            let corrupt = MaterialWorldRegister::try_new(catalog, 18, state)
                .expect("the authored fixture satisfies the constructor invariants");
            let encoded = babylon_persistence::material_storage::encode(
                &corrupt,
                &receipts,
                &opening,
                lookup.previous_chain,
            )
            .expect("the fixture value encodes canonically");
            // Changing a quantity adds no identities. Existing receipt and delta stay valid.
            assert_eq!(encoded.lookup.entries(), lookup.lookup.entries());
            let (reconstructed, preserved_receipts) =
                babylon_persistence::material_storage::decode(
                    catalog,
                    &opening,
                    18,
                    &encoded.register_storage_bytes,
                    &receipt_package,
                    &lookup.lookup,
                    lookup.chain,
                )
                .expect("the committed canonical bytes decode");
            assert_eq!(reconstructed, corrupt.canonical_bytes());
            assert_eq!(preserved_receipts, receipts);
            connection.execute("UPDATE babylon_state.material_tick_v3 SET register_storage_bytes=$2 WHERE campaign_id=$1 AND resolve_tick=18", &[campaign.as_uuid(), &encoded.register_storage_bytes]).expect("the test database applies the setup statement");
            original = Some(package);
        }
    }
    let original = original.expect("the fixture captures the original value");
    assert_eq!(
        observer.snapshot_with_cursor(campaign, 18, cursor),
        Err(ObserverEconomyError::InvalidProjection)
    );
    assert!(matches!(
        observer.committed_material_receipts(campaign, 18),
        Err(ObserverEconomyError::InvalidProjection)
    ));

    assert!(matches!(
        observer.committed_material_observation(campaign, 18),
        Err(ObserverEconomyError::InvalidProjection)
    ));

    assert_eq!(
        cursor
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .completed_tick(),
        18
    );
    connection.execute("UPDATE babylon_state.material_tick_v3 SET register_storage_bytes=$2 WHERE campaign_id=$1 AND resolve_tick=18", &[campaign.as_uuid(), &original]).expect("the test database applies the setup statement");
    assert_material_accounts(
        &observer
            .snapshot_with_cursor(campaign, 18, cursor)
            .expect("the fixture snapshot carries its cursor"),
    );
}

#[test]
#[ignore = "requires the existing disposable PostgreSQL harness and restricted reader roles"]
#[allow(
    clippy::too_many_lines,
    reason = "`live_regional_content_revisions_resume_exactly_and_catalog_filters_before_its_limit` keeps one authored boundary's fixture and assertions together"
)]
pub(crate) fn live_regional_content_revisions_resume_exactly_and_catalog_filters_before_its_limit()
{
    use babylon_persistence::michigan_content::MICHIGAN_CONTENT_PRESETS;
    let mut target = DisposableTarget::create();
    let mut campaigns = Vec::new();
    let numbered_presets = MICHIGAN_CONTENT_PRESETS
        .into_iter()
        .filter(|preset| !preset.delivery().is_statewide())
        .enumerate();
    for (index, preset) in numbered_presets {
        let campaign = CampaignId::from_uuid(Uuid::from_u128(
            10_000 + u128::try_from(index).expect("the fixture value fits the target range"),
        ));
        let mut runtime = DurableMaterialRuntime::create(
            &target.writer,
            campaign,
            preset
                .create_foundation(&crate::test_support::catalog())
                .expect("the authored catalog builds the foundation"),
        )
        .expect("the test database creates the fixture campaign");
        advance_material_period(&mut runtime);
        advance_material_period(&mut runtime);
        campaigns.push((campaign, preset, runtime));
    }
    babylon_persistence::install_reader_role(&target.writer)
        .expect("the test database installs the reader role");
    observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    let observer = ObserverEconomyReader::connect(
        &target.login("babylon_observer", "catalogobserver"),
        ObserverVisibility::FullObserver,
    )
    .expect("the test database accepts the connection");
    let known_config = target.login("babylon_reader", "catalogknown");
    let known = ObserverEconomyReader::connect(&known_config, ObserverVisibility::KnownPreview)
        .expect("the test database accepts the connection");
    for (campaign, preset, runtime) in &mut campaigns {
        assert_revision_resume(
            &target.writer,
            *campaign,
            *preset,
            runtime,
            &observer,
            &known,
        );
    }
    let before = observer
        .campaigns()
        .expect("the fixture lists the authored campaigns");
    assert_eq!(before.len(), 4);
    assert_eq!(
        before
            .iter()
            .map(|row| (row.id.clone(), row.preset.clone()))
            .collect::<std::collections::BTreeSet<_>>(),
        campaigns
            .iter()
            .map(|(campaign, preset, _)| (campaign.as_uuid().to_string(), preset.id().to_owned()))
            .collect::<std::collections::BTreeSet<_>>()
    );
    assert!(before.iter().all(|row| row.durable_tick == 4));
    assert_eq!(
        before,
        known
            .campaigns()
            .expect("the fixture lists the authored campaigns")
    );
    let unknown = insert_unadmitted_catalog_rows(&target.writer, campaigns[0].0);
    // A safe header is discoverable without disclosing its opaque Designed values.
    // Only the full capability authenticates stored material content.
    let discovered = observer
        .campaigns()
        .expect("the fixture lists the authored campaigns");
    assert_eq!(
        discovered,
        known
            .campaigns()
            .expect("the fixture lists the authored campaigns")
    );
    assert_eq!(discovered.len(), before.len() + 1);
    assert_eq!(&discovered[1..], before.as_slice());
    assert_eq!(discovered[0].id, unknown[65].as_uuid().to_string());
    assert_eq!(unknown.len(), 66);
    for reader in [&observer, &known] {
        assert_eq!(
            reader.snapshot(unknown[0], 0),
            Err(ObserverEconomyError::ScenarioMismatch)
        );
    }
    assert_eq!(
        observer.snapshot(unknown[65], 0),
        Err(ObserverEconomyError::ScenarioMismatch)
    );
    let opaque = known
        .snapshot(unknown[65], 0)
        .expect("the fixture captures a consistent snapshot");
    assert!(opaque.production.is_none());
    assert!(opaque.nominal_world_hash.is_none());
    assert_eq!(opaque.counties.len(), 83);
    assert!(opaque.counties.iter().all(|county| {
        county.annual_avg_estabs_count.is_none()
            && county.annual_avg_emplvl.is_none()
            && county.total_annual_wages.is_none()
            && county.annual_avg_wkly_wage.is_none()
    }));
    assert!(known_config
        .connect(NoTls)
        .expect("the test database accepts the connection")
        .query(
            "SELECT register_storage_bytes FROM public.v_observer_material_state_v1",
            &[]
        )
        .is_err());
}

pub(crate) fn assert_revision_resume(
    config: &Config,
    campaign: CampaignId,
    preset: babylon_persistence::michigan_content::MichiganContentPreset,
    runtime: &mut DurableMaterialRuntime,
    observer: &ObserverEconomyReader,
    known: &ObserverEconomyReader,
) {
    let history = observer
        .snapshot(campaign, 1)
        .expect("the fixture captures a consistent snapshot");
    assert_eq!(history.counties.len(), 83);
    assert_eq!(
        history
            .production
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .sites
            .len(),
        5
    );
    let at_two = observer
        .snapshot(campaign, 2)
        .expect("the fixture captures a consistent snapshot");
    assert_material_accounts(&history);
    assert_material_accounts(&at_two);
    let actions = OrderedPracticeActionBatch::empty(
        runtime.session().graph_session().session_identity().clone(),
        3,
    )
    .expect("the empty authored batch constructs");
    let uninterrupted = runtime
        .session()
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    let mut reopened = DurableMaterialRuntime::open(
        config,
        campaign,
        preset
            .admitted(&crate::test_support::catalog())
            .expect("the fixture admits the authored value")
            .digest(),
    )
    .expect("the fixture opens the authored source");
    assert_eq!(reopened.session().completed_tick(), 2);
    let restored = reopened
        .session()
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    assert_eq!(uninterrupted.identity(), restored.identity());
    assert_eq!(
        uninterrupted.material().register().canonical_bytes(),
        restored.material().register().canonical_bytes()
    );
    assert_eq!(
        uninterrupted.material().receipt_bytes(),
        restored.material().receipt_bytes()
    );
    assert_eq!(
        observer
            .snapshot(campaign, 2)
            .expect("the fixture captures a consistent snapshot"),
        at_two
    );
    advance_material_period(&mut reopened);
    assert_material_accounts(
        &observer
            .snapshot(campaign, 3)
            .expect("the fixture captures a consistent snapshot"),
    );
    assert_eq!(
        observer
            .snapshot(campaign, 1)
            .expect("the fixture captures a consistent snapshot"),
        history
    );
    assert_known_material_absence(
        &mut known
            .snapshot(campaign, 3)
            .expect("the fixture captures a consistent snapshot"),
    );
    assert_session_admits_stored_revision(config, campaign, observer);
    assert_eq!(
        observer
            .snapshot(campaign, 1)
            .expect("the fixture captures a consistent snapshot"),
        history
    );
    *runtime = reopened;
}

pub(crate) fn assert_session_admits_stored_revision(
    config: &Config,
    campaign: CampaignId,
    observer: &ObserverEconomyReader,
) {
    use babylon_persistence::runtime_session::{
        RuntimeSessionRequest, RuntimeSessionResponse, RuntimeSessionScope, RuntimeSessionTail,
        RuntimeSessionTarget, RUNTIME_SESSION_PROTOCOL_VERSION,
    };
    let current = observer
        .snapshot(campaign, 3)
        .expect("the fixture captures a consistent snapshot");
    let scope = RuntimeSessionScope {
        epoch: 1,
        campaign_id: Some(campaign.as_uuid().to_string()),
    };
    let requests = [
        RuntimeSessionRequest::Switch {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: 1,
            scope: RuntimeSessionScope {
                epoch: 0,
                campaign_id: None,
            },
            target: RuntimeSessionTarget::Open {
                campaign_id: campaign.as_uuid().to_string(),
            },
        },
        RuntimeSessionRequest::Advance {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            scope: scope.clone(),
            request_id: 2,
            expected_tail: RuntimeSessionTail {
                resolve_tick: 3,
                tick_content_hash: current.tick_content_hash,
            },
        },
        RuntimeSessionRequest::Stop {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            scope,
            request_id: 3,
        },
    ];
    let mut lines = Vec::new();
    for request in &requests {
        serde_json::to_writer(&mut lines, request)
            .expect("the in-memory writer accepts the JSON bytes");
        lines.push(b'\n');
    }
    let mut output = Vec::new();
    runtime_session::run_runtime_session(
        config,
        Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/michigan/defines.toml"
        )),
        Cursor::new(lines),
        &mut output,
    )
    .expect("the fixture run completes");
    assert_streamed_native_advance(&output, campaign);
    let responses = std::str::from_utf8(&output)
        .expect("the fixture bytes came from a UTF-8 string")
        .lines()
        .map(|line| {
            serde_json::from_str::<RuntimeSessionResponse>(line)
                .expect("the fixture world holds the addressed component")
        })
        .collect::<Vec<_>>();
    assert!(
        matches!(&responses[0], RuntimeSessionResponse::Hello { protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION, scope }
        if scope.epoch == 0 && scope.campaign_id.is_none())
    );
    assert!(
        matches!(&responses[2], RuntimeSessionResponse::Ready { foundation_digest, tail, .. }
        if foundation_digest == &current.foundation_digest && tail.resolve_tick == 3),
        "stored revision did not become ready: {responses:#?}"
    );
    assert!(responses.iter().any(|response| matches!(response, RuntimeSessionResponse::Committed { request_id: 2, tail, .. } if tail.resolve_tick == 4)),
        "stored revision advance did not commit: {responses:#?}");
    assert_eq!(
        observer
            .snapshot(campaign, 4)
            .expect("the fixture captures a consistent snapshot")
            .foundation_digest,
        current.foundation_digest
    );
}

pub(crate) fn assert_streamed_native_advance(output: &[u8], campaign: CampaignId) {
    let streamed: Vec<_> = output
        .split(|byte| *byte == b'\n')
        .filter(|line| !line.is_empty())
        .map(|line| {
            serde_json::from_slice::<Value>(line)
                .expect("the fixture world holds the addressed component")
        })
        .collect();
    let progress: Vec<_> = streamed
        .iter()
        .filter(|row| row["type"] == "advance_progress")
        .collect();
    assert_eq!(
        progress.len(),
        4,
        "actual native advance must stream four boundaries"
    );
    for (row, stage) in progress.iter().zip([
        "preparing_commitments",
        "resolving_economy",
        "preparing_storage",
        "saving_period",
    ]) {
        assert_eq!(row["stage"], stage);
        assert_eq!(row["request_id"], 2);
        assert_eq!(row["resolve_tick"], 4);
        assert_eq!(row["scope"]["epoch"], 1);
        assert_eq!(row["scope"]["campaign_id"], campaign.as_uuid().to_string());
    }
    let committed = streamed
        .iter()
        .position(|row| row["type"] == "committed")
        .expect("the fixture sequence holds the addressed position");
    assert!(streamed
        .iter()
        .enumerate()
        .filter(|(_, row)| row["type"] == "advance_progress")
        .all(|(index, _)| index < committed));
}

// Deliberately malformed metadata is confined to this test's disposable clone.
// The 65 unknown UUIDs sort before every admitted campaign, exposing LIMIT-before-
// admission bugs. The final row mixes an admitted preset with a changed digest.
pub(crate) fn insert_unadmitted_catalog_rows(
    config: &Config,
    source: CampaignId,
) -> Vec<CampaignId> {
    let mut client = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut tx = client
        .transaction()
        .expect("the test database opens a transaction");
    let mut ids = Vec::new();
    for number in 1..=66_u128 {
        let campaign = CampaignId::from_uuid(Uuid::from_u128(number));
        tx.execute("INSERT INTO babylon_state.campaign (campaign_id,replay_layout_version,rng_layout_version,replay_session_id,rng_seed,defines_hash,rules_hash,ref_digest,geography_scope,local_h3_ref_digest) SELECT $1,replay_layout_version,rng_layout_version,replay_session_id,rng_seed,defines_hash,rules_hash,ref_digest,geography_scope,local_h3_ref_digest FROM babylon_state.campaign WHERE campaign_id=$2", &[campaign.as_uuid(), source.as_uuid()]).expect("the test database applies the setup statement");
        tx.execute("INSERT INTO babylon_state.campaign_foundation (campaign_id,stable_graph,world_registers,resolver_manifest,prepared_environment,replay_session_id,rng_seed,defines_hash,rules_hash,ref_digest,content_bundle_bytes,foundation_sha256) SELECT $1,stable_graph,world_registers,resolver_manifest,prepared_environment,replay_session_id,rng_seed,defines_hash,rules_hash,ref_digest,content_bundle_bytes,foundation_sha256 FROM babylon_state.campaign_foundation WHERE campaign_id=$2", &[campaign.as_uuid(), source.as_uuid()]).expect("the test database applies the setup statement");
        let preset = if number == 66 {
            // Opaque material content still needs a complete public county family.
            // Without this mapping, snapshot refusal would concern missing county
            // rows rather than whether the reader authenticates material bytes.
            assert_eq!(tx.execute(
                "INSERT INTO babylon_meta.campaign (campaign_id,slug,engine_version,defines_hash,last_tick,status,rng_seed,content_digest) \
                 SELECT $1,$1::uuid::text,engine_version,defines_hash,0,'ACTIVE',rng_seed,content_digest \
                 FROM babylon_meta.campaign WHERE campaign_id=$2",
                &[campaign.as_uuid(), source.as_uuid()],
            ).expect("the test database applies the setup statement"), 1);
            assert_eq!(tx.execute(
                "INSERT INTO babylon_meta.territory_county_map_v1 (campaign_id,territory_local_name,county_geoid) \
                 SELECT $1,territory_local_name,county_geoid FROM babylon_meta.territory_county_map_v1 WHERE campaign_id=$2",
                &[campaign.as_uuid(), source.as_uuid()],
            ).expect("the test database applies the setup statement"), 83);
            // No knowledge grants are copied: all observed values must stay hidden.
            MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard).id()
        } else {
            "unadmitted-fixture-v1"
        };
        tx.execute("INSERT INTO babylon_state.material_campaign_foundation_v3 (campaign_id,preset_id,duration_kind,final_period,content_sha256,initial_register_bytes,foundation_sha256) SELECT $1,$3,duration_kind,final_period,content_sha256,initial_register_bytes,pg_catalog.set_byte(foundation_sha256,0,(pg_catalog.get_byte(foundation_sha256,0)+1)%256) FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$2", &[campaign.as_uuid(), source.as_uuid(), &preset]).expect("the test database applies the setup statement");
        ids.push(campaign);
    }
    tx.commit().expect("the fixture transaction commits");
    ids
}

mod current_authority {
    use super::{
        ArchivePageRef, ArchiveSubjectKind, ArchiveWorker, CampaignId, CollectingSink,
        DisposableTarget, DurableMaterialRuntime, MichiganContentPreset, MichiganDeliveryPreset,
        OrderedPracticeActionBatch, Uuid,
    };
    use babylon_persistence::material_runtime::MaterialRuntimeFoundation;
    use babylon_persistence::ArchiveCitation;
    use babylon_persistence::ArchiveKnowledgeGrant;
    use babylon_persistence::RetainedMetadataStore;
    use babylon_persistence::SemanticArchiveStore;
    use postgres::Client;
    use postgres::NoTls;
    use std::sync::Barrier;

    fn foundation() -> MaterialRuntimeFoundation {
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation")
    }

    #[test]
    #[ignore = "requires task-owned disposable PostgreSQL runtime"]
    fn live_current_identity_corruption_refuses_open_and_commit_without_repair() {
        for missing in [true, false] {
            let target = DisposableTarget::create();
            let campaign = CampaignId::from_uuid(Uuid::from_u128(21_001));
            let source = foundation();
            let digest = source.digest();
            let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, source)
                .expect("the test database creates the fixture campaign");
            let before = runtime
                .session()
                .current_world_hash()
                .expect("the committed session publishes a world hash");
            let mut sql = target
                .writer
                .connect(NoTls)
                .expect("the test database accepts the connection");
            if missing {
                sql.execute("DELETE FROM babylon_meta.current_schema", &[])
                    .expect("the test database applies the setup statement");
            } else {
                sql.execute(
                    "UPDATE babylon_meta.current_schema SET schema_sha256=$1",
                    &[&&[0_u8; 32][..]],
                )
                .expect("the test database applies the setup statement");
            }
            assert!(DurableMaterialRuntime::open(&target.writer, campaign, digest).is_err());
            let metadata = RetainedMetadataStore::new(&target.writer);
            assert!(metadata
                .set_campaign_status(
                    campaign,
                    babylon_persistence::CampaignCatalogStatus::Abandoned
                )
                .is_err());
            assert!(metadata.replace_watchlist(campaign, &[]).is_err());
            assert!(metadata.delete_campaign(campaign).is_err());
            let store = SemanticArchiveStore::new(&target.writer);
            let grant = ArchiveKnowledgeGrant::try_new(
                ArchivePageRef::try_new(ArchiveSubjectKind::County, "26163".to_owned())
                    .expect("the authored fixture satisfies the constructor invariants"),
                "schema-refusal-probe".to_owned(),
                0,
                ArchiveCitation::try_new("fixture".to_owned(), "schema-refusal-probe".to_owned())
                    .expect("the authored fixture satisfies the constructor invariants"),
            )
            .expect("the authored fixture satisfies the constructor invariants");
            assert!(matches!(
                store.grant_knowledge(campaign, &grant),
                Err(babylon_persistence::SemanticArchiveError::CurrentSchema(_))
            ));
            let sweep = ArchiveWorker::new(&target.writer)
                .sweep_once(campaign, &babylon_persistence::NullArchiveDossierProducer);
            assert!(matches!(
                sweep,
                Err(babylon_persistence::SemanticArchiveError::CurrentSchema(_))
            ));
            let status: String = sql
                .query_one(
                    "SELECT status FROM babylon_meta.campaign WHERE campaign_id=$1",
                    &[campaign.as_uuid()],
                )
                .expect("the seeded row is present exactly once")
                .get(0);
            assert_eq!(status, "ACTIVE");
            let grants: i64 = sql.query_one("SELECT count(*) FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key='schema-refusal-probe'", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
            assert_eq!(grants, 0);

            let actions = OrderedPracticeActionBatch::empty(
                runtime.session().graph_session().session_identity().clone(),
                1,
            )
            .expect("the empty authored batch constructs");
            let mut sink = CollectingSink::default();
            assert!(runtime.advance_and_commit(&mut sink, &actions).is_err());
            assert_eq!(
                runtime
                    .session()
                    .current_world_hash()
                    .expect("the committed session publishes a world hash"),
                before
            );
            assert_eq!(runtime.session().completed_tick(), 0);
            assert!(runtime.tail().is_none());
            assert_eq!(sink.events.len(), 0);
            let rows = sql
                .query("SELECT schema_sha256 FROM babylon_meta.current_schema", &[])
                .expect("the seeded rows are readable");
            if missing {
                assert!(rows.is_empty());
            } else {
                assert_eq!(rows[0].get::<_, Vec<u8>>(0), vec![0; 32]);
            }
            assert_eq!(
                sql.query_one(
                    "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1",
                    &[campaign.as_uuid()]
                )
                .expect("the seeded row is present exactly once")
                .get::<_, i64>(0),
                0
            );
        }
    }

    fn exact_retained_graph_vectors(
        sql: &mut Client,
        campaign: CampaignId,
    ) -> Vec<(i64, Vec<i64>)> {
        let vectors = sql.query("SELECT vector_id,node_ids FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=$1 ORDER BY vector_id", &[campaign.as_uuid()]).expect("the seeded rows are readable")
            .into_iter().map(|row| (row.get(0), row.get(1))).collect::<Vec<_>>();
        assert_ne!(vectors.len(), 0);
        for (expected, (actual, _)) in vectors.iter().enumerate() {
            assert_eq!(
                *actual,
                i64::try_from(expected).expect("the fixture value fits the target range")
            );
        }
        assert_eq!(
            vectors
                .iter()
                .map(|(_, ids)| ids)
                .collect::<std::collections::BTreeSet<_>>()
                .len(),
            vectors.len()
        );
        vectors
    }

    #[test]
    #[ignore = "requires task-owned disposable PostgreSQL runtime"]
    #[allow(
        clippy::too_many_lines,
        reason = "`live_concurrent_identical_material_commit_publishes_one_exact_candidate` keeps one authored boundary's fixture and assertions together"
    )]
    fn live_concurrent_identical_material_commit_publishes_one_exact_candidate() {
        use babylon_persistence::material_runtime::MaterialRuntimeError;

        let target = DisposableTarget::create();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(21_002));
        let source = foundation();
        let digest = source.digest();
        let first = DurableMaterialRuntime::create(&target.writer, campaign, source)
            .expect("the test database creates the fixture campaign");
        let second = DurableMaterialRuntime::open(&target.writer, campaign, digest)
            .expect("the fixture opens the authored source");
        let initial_world = first
            .session()
            .current_world_hash()
            .expect("the committed session publishes a world hash");
        let initial_material = first.session().material().canonical_bytes().to_vec();
        let barrier = Barrier::new(2);
        // Join both initial attempts before a refused contender can retry. One
        // attempt must have succeeded; an unrelated failure never becomes a retry.
        let attempts = std::thread::scope(|scope| {
            let handles = [first, second]
                .into_iter()
                .map(|mut runtime| {
                    let barrier = &barrier;
                    scope.spawn(move || {
                        let actions = OrderedPracticeActionBatch::empty(
                            runtime.session().graph_session().session_identity().clone(),
                            1,
                        )
                        .expect("the empty authored batch constructs");
                        let mut sink = CollectingSink::default();
                        barrier.wait();
                        let outcome = runtime.advance_and_commit(&mut sink, &actions);
                        (runtime, actions, sink, outcome)
                    })
                })
                .collect::<Vec<_>>();
            handles
                .into_iter()
                .map(|handle| {
                    handle
                        .join()
                        .expect("the fixture worker finishes without panic")
                })
                .collect::<Vec<_>>()
        });
        assert!(attempts.iter().any(|(_, _, _, outcome)| outcome.is_ok()));
        let mut vectors_sql = target
            .writer
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let committed_vectors = exact_retained_graph_vectors(&mut vectors_sql, campaign);
        let mut results = Vec::new();
        for (mut runtime, actions, mut sink, outcome) in attempts {
            let identity = match outcome {
                Ok(identity) => identity,
                Err(MaterialRuntimeError::DatabaseLockRefused(error)) => {
                    assert_eq!(
                        error.code(),
                        Some(&postgres::error::SqlState::LOCK_NOT_AVAILABLE)
                    );
                    assert_eq!(
                        runtime
                            .session()
                            .current_world_hash()
                            .expect("the committed session publishes a world hash"),
                        initial_world
                    );
                    assert_eq!(
                        runtime.session().material().canonical_bytes(),
                        initial_material
                    );
                    assert_eq!(runtime.session().completed_tick(), 0);
                    assert_eq!(runtime.session().graph_session().completed_tick(), 0);
                    assert!(runtime.tail().is_none());
                    assert!(runtime.diagnostic_receipt().is_none());
                    assert_eq!(sink.events.len(), 0);
                    runtime
                        .advance_and_commit(&mut sink, &actions)
                        .expect("one retry after the competing commit finished must reconcile")
                }
                Err(error) => panic!("unexpected concurrent commit refusal: {error:?}"),
            };
            results.push((
                identity,
                runtime.session().material().canonical_bytes().to_vec(),
                runtime
                    .diagnostic_receipt()
                    .expect(
                        "the fixture call `diagnostic_receipt` succeeds for the authored inputs",
                    )
                    .commit_disposition(),
            ));
        }
        assert_eq!(
            exact_retained_graph_vectors(&mut vectors_sql, campaign),
            committed_vectors
        );
        let [a, b] = results.as_slice() else {
            panic!("both concurrent candidates must be acknowledged");
        };
        assert_eq!(a.0, b.0);
        assert_eq!(a.1, b.1);
        assert_ne!(a.2, b.2);
        let reopened = DurableMaterialRuntime::open(&target.writer, campaign, digest)
            .expect("the fixture opens the authored source");
        assert_eq!(reopened.tail(), Some(&a.0));
        assert_eq!(reopened.session().material().canonical_bytes(), a.1);
        let mut sql = target
            .writer
            .connect(NoTls)
            .expect("the test database accepts the connection");
        assert_eq!(
            sql.query_one(
                "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .expect("the seeded row is present exactly once")
            .get::<_, i64>(0),
            1
        );
    }
}

pub(crate) fn assert_single_foundation_storage(
    writer: &Config,
    campaign: CampaignId,
    catalog: &MaterialCatalog,
) {
    let mut storage = writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let duplicate_columns: i64 = storage.query_one(
        "SELECT count(*) FROM information_schema.columns WHERE table_schema='babylon_state' AND table_name='material_campaign_foundation_v3' AND column_name='foundation_bytes'", &[]
    ).expect("the seeded row is present exactly once").get(0);
    assert_eq!(
        duplicate_columns, 0,
        "the complete foundation must have no second stored owner"
    );
    let captured: Vec<u8> = storage.query_one(
        "SELECT initial_register_bytes FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1", &[campaign.as_uuid()]
    ).expect("the seeded row is present exactly once").get(0);
    assert_eq!(
        MaterialWorldRegister::decode_external(catalog, captured.clone())
            .expect("the committed canonical bytes decode")
            .completed_tick(),
        0
    );
}

pub(crate) fn assert_captured_foundation_denied(known: &Config) {
    assert_preview_blob_denied(known);
    assert!(known
        .connect(NoTls)
        .expect("the test database accepts the connection")
        .query(
            "SELECT content_bundle_bytes FROM public.v_observer_material_foundation_v1",
            &[]
        )
        .is_err());
}

pub(crate) fn self_consistent_changed_period_lookup(
    catalog: &MaterialCatalog,
    base: &[u8],
    delta: &[u8],
) -> Vec<u8> {
    let opening = babylon_persistence::material_storage::seed(catalog, base)
        .expect("the fixture seeds the authored rows");
    let c0 = babylon_persistence::material_storage::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let original_table = babylon_persistence::material_storage::read_period_lookup(
        &opening,
        1,
        delta,
        LookupAnchor::Previous(c0),
    )
    .expect("the committed lookup table reads");
    let prefix = b"BabylonPeriodLookupV3\0".len() + 2 + 32 + 8 + 32;
    let additions = &original_table.lookup.entries()[opening.lookup().entries().len()..];
    let mut packed = u32::try_from(additions.len())
        .expect("the fixture value fits the target range")
        .to_be_bytes()
        .to_vec();
    for entry in additions {
        packed.push(entry.kind as u8);
        packed.extend_from_slice(&entry.bytes);
    }
    assert_ne!(additions.len(), 0);
    let replacement = (0..=original_table.lookup.entries().len())
        .map(|counter| {
            let mut bytes = [0; 32];
            bytes[..8].copy_from_slice(
                &u64::try_from(counter)
                    .expect("the fixture value fits the target range")
                    .to_be_bytes(),
            );
            bytes
        })
        .find(|candidate| {
            original_table
                .lookup
                .entries()
                .iter()
                .all(|entry| &entry.bytes != candidate)
        })
        .expect("the fixture holds the searched element");
    packed[5..37].copy_from_slice(&replacement);
    let compressed = zstd::bulk::compress(&packed, 3)
        .expect("the fixture call `compress` succeeds for the authored inputs");
    let mut self_consistent = delta[..prefix].to_vec();
    self_consistent.extend_from_slice(&(packed.len() as u64).to_be_bytes());
    self_consistent.extend_from_slice(&babylon_kernel::content_digest::sha256_of(&packed));
    // All-literal V3 descriptors are exactly these logical packed additions.
    self_consistent.extend_from_slice(&(packed.len() as u64).to_be_bytes());
    self_consistent.extend_from_slice(&babylon_kernel::content_digest::sha256_of(&packed));
    self_consistent.extend_from_slice(&(compressed.len() as u64).to_be_bytes());
    self_consistent.extend_from_slice(&compressed);
    let changed_table = babylon_persistence::material_storage::read_period_lookup(
        &opening,
        1,
        &self_consistent,
        LookupAnchor::Previous(c0),
    )
    .expect("the committed lookup table reads");
    assert_ne!(changed_table.chain, original_table.chain);
    self_consistent
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and restricted reader roles"]
#[allow(
    clippy::too_many_lines,
    reason = "`cold_restart_and_history_refuse_corrupt_or_missing_earlier_period_lookup` keeps one authored boundary's fixture and assertions together"
)]
pub(crate) fn cold_restart_and_history_refuse_corrupt_or_missing_earlier_period_lookup() {
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(41_209));
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let foundation_digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
        .expect("the test database creates the fixture campaign");
    for _ in 0..3 {
        advance_material_period(&mut runtime);
    }
    let tail = *runtime
        .tail()
        .expect("the fixture sequence holds more than one row");
    let world = runtime
        .session()
        .current_world_hash()
        .expect("the committed session publishes a world hash");
    babylon_persistence::install_reader_role(&target.writer)
        .expect("the test database installs the reader role");
    observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    let observer_config = target.login("babylon_observer", "localperiodhistory");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
            .expect("the test database accepts the connection");
    let healthy = observer
        .snapshot(campaign, 3)
        .expect("the fixture captures a consistent snapshot");
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let saved = writer.query_one(
        "SELECT identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid AND resolve_tick=1",
        &[campaign.as_uuid()],
    ).expect("the seeded row is present exactly once");
    let identity: Vec<u8> = saved.get(0);
    let register: Vec<u8> = saved.get(1);
    let receipts: Vec<u8> = saved.get(2);
    let delta: Vec<u8> = saved.get(3);
    // Recompute the literal chunk checksum/compression after changing one typed
    // identity. Refusal must come from historical authentication, not a broken frame.
    let base: Vec<u8> = writer.query_one(
        "SELECT initial_register_bytes FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1::uuid",
        &[campaign.as_uuid()],
    ).expect("the seeded row is present exactly once").get(0);
    let self_consistent =
        self_consistent_changed_period_lookup(runtime.session().catalog(), &base, &delta);
    assert_eq!(writer.execute(
        "UPDATE babylon_state.material_tick_v3 SET lookup_delta_bytes=$2 WHERE campaign_id=$1::uuid AND resolve_tick=1",
        &[campaign.as_uuid(), &self_consistent],
    ).expect("the test database applies the setup statement"), 1);
    let changed_restart =
        DurableMaterialRuntime::open(&target.writer, campaign, foundation_digest).is_err();
    let changed_history = observer.snapshot(campaign, 3);
    assert_eq!(writer.execute(
        "UPDATE babylon_state.material_tick_v3 SET lookup_delta_bytes=$2 WHERE campaign_id=$1::uuid AND resolve_tick=1",
        &[campaign.as_uuid(), &delta],
    ).expect("the test database applies the setup statement"), 1);
    assert!(
        changed_restart,
        "checksummed old table cannot keep the committed tail anchor"
    );
    assert_eq!(
        changed_history,
        Err(ObserverEconomyError::InvalidProjection)
    );
    assert_eq!(
        observer
            .snapshot(campaign, 3)
            .expect("the fixture captures a consistent snapshot"),
        healthy
    );

    let mut wrong_period = delta.clone();
    let tick_offset = b"BabylonPeriodLookupV3\0".len() + 2 + 32;
    wrong_period[tick_offset..tick_offset + 8].copy_from_slice(&2_u64.to_be_bytes());
    assert_eq!(writer.execute(
        "UPDATE babylon_state.material_tick_v3 SET lookup_delta_bytes=$2 WHERE campaign_id=$1::uuid AND resolve_tick=1",
        &[campaign.as_uuid(), &wrong_period],
    ).expect("the test database applies the setup statement"), 1);
    let restart_refused =
        DurableMaterialRuntime::open(&target.writer, campaign, foundation_digest).is_err();
    let history_refused = observer.snapshot(campaign, 3);
    assert_eq!(writer.execute(
        "UPDATE babylon_state.material_tick_v3 SET lookup_delta_bytes=$2 WHERE campaign_id=$1::uuid AND resolve_tick=1",
        &[campaign.as_uuid(), &delta],
    ).expect("the test database applies the setup statement"), 1);
    assert!(
        restart_refused,
        "tail3 cannot hide a corrupt tick1 dependency"
    );
    assert_eq!(
        history_refused,
        Err(ObserverEconomyError::InvalidProjection)
    );
    assert_eq!(
        observer
            .snapshot(campaign, 3)
            .expect("the fixture captures a consistent snapshot"),
        healthy
    );

    assert_eq!(writer.execute(
        "DELETE FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid AND resolve_tick=1",
        &[campaign.as_uuid()],
    ).expect("the test database applies the setup statement"), 1);
    let restart_refused =
        DurableMaterialRuntime::open(&target.writer, campaign, foundation_digest).is_err();
    let history_refused = observer.snapshot(campaign, 3);
    assert_eq!(writer.execute(
        "INSERT INTO babylon_state.material_tick_v3(campaign_id,resolve_tick,identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes) VALUES($1::uuid,1,$2,$3,$4,$5)",
        &[campaign.as_uuid(), &identity, &register, &receipts, &delta],
    ).expect("the test database applies the setup statement"), 1);
    assert!(restart_refused, "tail3 cannot hide a missing tick1 row");
    assert_eq!(history_refused, Err(ObserverEconomyError::TickAbsent));
    assert_eq!(
        observer
            .snapshot(campaign, 3)
            .expect("the fixture captures a consistent snapshot"),
        healthy
    );
    let reopened = DurableMaterialRuntime::open(&target.writer, campaign, foundation_digest)
        .expect("the fixture opens the authored source");
    assert_eq!(reopened.tail(), Some(&tail));
    assert_eq!(
        reopened
            .session()
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        world
    );
    assert_eq!(runtime.tail(), Some(&tail));
    assert_eq!(
        runtime
            .session()
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        world
    );
}

pub(crate) fn assert_committed_accounting_observation(
    observer: &ObserverEconomyReader,
    reopened: &ObserverEconomyReader,
    campaign: CampaignId,
    tail: &IdentifiedMaterialTick,
) {
    let original = observer
        .committed_material_receipts(campaign, 3)
        .expect("the fixture call `committed_material_receipts` succeeds for the authored inputs");
    let after_restart = reopened
        .committed_material_receipts(campaign, 3)
        .expect("the fixture call `committed_material_receipts` succeeds for the authored inputs");
    assert_eq!(original.campaign_id, campaign);
    assert_eq!(original.identity, *tail);
    assert_eq!(
        original.identity.resolve_tick(),
        original.receipts.resolve_tick
    );
    assert_eq!(original, after_restart);
    assert!(
        !original.receipts.production.is_empty(),
        "actual complete physical-control receipt family"
    );
    assert_combined_observation(observer, reopened, campaign, &original);
    let historical = observer
        .committed_material_receipts(campaign, 2)
        .expect("the fixture call `committed_material_receipts` succeeds for the authored inputs");
    assert_eq!(historical.identity.resolve_tick(), 2);
    assert_eq!(historical.receipts.resolve_tick, 2);
    assert_eq!(
        historical,
        reopened.committed_material_receipts(campaign, 2).expect(
            "the fixture call `committed_material_receipts` succeeds for the authored inputs"
        )
    );
    assert!(matches!(
        observer.committed_material_receipts(campaign, 4),
        Err(ObserverEconomyError::TickAbsent)
    ));
}

pub(crate) fn assert_combined_observation(
    observer: &ObserverEconomyReader,
    reopened: &ObserverEconomyReader,
    campaign: CampaignId,
    accounting: &CommittedMaterialReceipts,
) {
    let combined = observer.committed_material_observation(campaign, 3).expect(
        "the fixture call `committed_material_observation` succeeds for the authored inputs",
    );
    let mut separate = observer
        .snapshot(campaign, 3)
        .expect("the fixture captures a consistent snapshot");
    let evidence = separate
        .production_evidence_digest()
        .expect("the evidence body has a digest")
        .expect("the nested fixture result is present");
    assert_eq!(combined.accounting, *accounting);
    assert_eq!(combined.snapshot, separate);
    assert_eq!(combined.production_evidence, evidence);
    let historical = reopened.committed_material_observation(campaign, 2).expect(
        "the fixture call `committed_material_observation` succeeds for the authored inputs",
    );
    assert_eq!(
        historical.accounting,
        observer.committed_material_receipts(campaign, 2).expect(
            "the fixture call `committed_material_receipts` succeeds for the authored inputs"
        )
    );
    let mut historical_snapshot = observer
        .snapshot(campaign, 2)
        .expect("the fixture captures a consistent snapshot");
    assert_eq!(
        historical.production_evidence,
        historical_snapshot
            .production_evidence_digest()
            .expect("the evidence body has a digest")
            .expect("the nested fixture result is present")
    );
    assert_eq!(historical.snapshot, historical_snapshot);
    assert!(matches!(
        observer.committed_material_observation(campaign, 4),
        Err(ObserverEconomyError::TickAbsent)
    ));
}

pub(crate) fn assert_authenticated_time_debits(
    reader: &ObserverEconomyReader,
    campaign: CampaignId,
    runtime: &DurableMaterialRuntime,
) {
    let observed = reader
        .committed_material_receipts(campaign, 3)
        .expect("the fixture call `committed_material_receipts` succeeds for the authored inputs");
    let expected = match &runtime.session().material().state().accounting {
        CircuitAccounting::PhysicalControl => &[][..],
        CircuitAccounting::Monetary(economy) => match &economy.household_time {
            HouseholdTimeAccounting::NotModeled => &[][..],
            HouseholdTimeAccounting::Modeled(book) => book.contributions.as_slice(),
        },
    };
    assert_eq!(
        observed.identity,
        *runtime
            .tail()
            .expect("the fixture sequence holds more than one row")
    );
    assert_eq!(observed.household_contributions, expected);
    assert!(observed
        .household_contributions
        .iter()
        .all(|row| row.period == 3));
    assert_eq!(
        observed,
        reader.committed_material_receipts(campaign, 3).expect(
            "the fixture call `committed_material_receipts` succeeds for the authored inputs"
        )
    );
}
