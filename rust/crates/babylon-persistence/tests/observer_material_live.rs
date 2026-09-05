//! Full material reads, historical identity, and SQL-denied preview on a disposable clone.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_persistence::{
    install_observer_economy_schema_v1, install_reader_role_v1,
    material_runtime::{michigan_material_runtime_foundation_v2, DurableMaterialRuntimeV3},
    michigan_economy::{
        michigan_economy_v1, MichiganCountyEconomyV1, QCEW_ECONOMICS_ARTIFACT_SHA256_V1,
        QCEW_ECONOMICS_FIELD_KEYS_V1, QCEW_ECONOMICS_SOURCE_ID_V1,
    },
    michigan_material::MichiganDeliveryPresetV1,
    observer_reader::{ObserverEconomyErrorV1, ObserverEconomyReaderV1, ObserverVisibilityV1},
    validate_legacy_connection_target, ArchiveAtomSubjectKindV1, ArchiveAtomSubjectV1,
    ArchiveAtomV1, ArchiveAtomValueV1, ArchiveEvidenceClassV1, ArchiveReceiptDispositionV1,
    ArchiveSearchHitV1, ArchiveWorkerV1, CampaignId, CompositeArchiveDossierProducerV1,
    CountyDossierProducerV1, PlaceDossierProducerV1, SemanticArchiveReaderV1,
};
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use babylon_tick::material_world::MaterialWorldRegisterV2;
use postgres::{Config, NoTls};
use uuid::Uuid;

const ACK: &str = "I_UNDERSTAND_PER20_DROPS_SCRATCH_DATABASES_ROLES_AND_CREATED_BABYLON_INTEL";

struct DisposableTarget {
    admin: Config,
    writer: Config,
    database: String,
    roles: Vec<String>,
}

fn michigan_archive_producer(config: &Config) -> CompositeArchiveDossierProducerV1 {
    CompositeArchiveDossierProducerV1::new(vec![
        Box::new(CountyDossierProducerV1::try_new(config).unwrap()),
        Box::new(PlaceDossierProducerV1::try_new(config).unwrap()),
    ])
}

fn advance_material_week(runtime: &mut DurableMaterialRuntimeV3) {
    let tick = runtime.session().completed_tick() + 1;
    let actions = OrderedPracticeActionBatchV1::empty(
        runtime.session().graph_session().session_identity().clone(),
        tick,
    )
    .unwrap();
    runtime
        .advance_and_commit(&mut CollectingSink::default(), &actions)
        .unwrap();
}

fn assert_archive_progress(
    reader: &SemanticArchiveReaderV1,
    campaign: CampaignId,
    durable: u64,
    processed: u64,
) {
    let status = reader
        .archive_verification_status(campaign)
        .unwrap()
        .unwrap();
    assert_eq!(status.durable_tick(), durable);
    assert_eq!(status.processed_tick(), processed);
    let committed = reader.committed_tick_status(campaign).unwrap().unwrap();
    assert_eq!(*committed.campaign_id(), campaign);
    assert_eq!(committed.resolve_tick(), durable);
}

fn assert_public_qcew_card(
    atoms: &[ArchiveAtomV1],
    page: &ArchiveSearchHitV1,
    campaign: CampaignId,
    county: &MichiganCountyEconomyV1,
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
    let signals: Vec<_> = atoms
        .iter()
        .filter(|atom| QCEW_ECONOMICS_FIELD_KEYS_V1.contains(&atom.signal_key()))
        .collect();
    assert_eq!(signals.len(), 4);
    assert_eq!(page.page_ref().id(), county.county_geoid);
    assert_eq!(
        page.verified_tick(),
        1,
        "content remains sourced from week one"
    );
    assert_eq!(page.atoms(), atoms);
    let locator = format!(
        "qcew_county_economics_mi_2024.csv.gz#county_geoid={}&sha256={QCEW_ECONOMICS_ARTIFACT_SHA256_V1}",
        county.county_geoid
    );
    for (key, label, value) in expected {
        let atom = signals
            .iter()
            .find(|atom| atom.signal_key() == key)
            .unwrap();
        assert_eq!(*atom.campaign_id(), campaign);
        assert_eq!(atom.subject().kind(), ArchiveAtomSubjectKindV1::County);
        assert_eq!(atom.subject().id(), county.county_geoid);
        assert_eq!(atom.grant_key(), key);
        assert_eq!(atom.evidence_class(), ArchiveEvidenceClassV1::Observed);
        assert_eq!(atom.value(), &ArchiveAtomValueV1::Text(value.to_string()));
        assert_eq!(atom.valid_tick(), 1);
        assert_eq!(atom.citation().source_id(), QCEW_ECONOMICS_SOURCE_ID_V1);
        assert_eq!(atom.citation().locator(), locator);
        assert!(page.citations().contains(atom.citation()));
        assert!(page
            .markdown()
            .contains(&format!("- **{label}:** {value} —")));
    }
    assert!(atoms
        .iter()
        .all(|atom| !matches!(atom.signal_key(), "median-wage" | "production" | "phi-hour")));
}

fn assert_all_county_cards(
    reader: &SemanticArchiveReaderV1,
    campaign: CampaignId,
) -> Vec<ArchiveSearchHitV1> {
    let pages = reader.search_known(campaign, "QCEW 2024", 100).unwrap();
    assert_eq!(pages.len(), 83);
    for (page, county) in pages.iter().zip(michigan_economy_v1().unwrap().counties()) {
        let atoms = reader
            .county_card_atoms(campaign, &county.county_geoid)
            .unwrap();
        assert_public_qcew_card(&atoms, page, campaign, county);
    }
    pages
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed Michigan ticks"]
fn live_michigan_all_county_cards_keep_public_source_and_quiet_restart_freshness() {
    let mut target = DisposableTarget::create();
    let campaign =
        CampaignId::from_uuid(Uuid::from_u128(0x0044_0000_0000_0000_0000_0000_0000_0002));
    let preset = MichiganDeliveryPresetV1::Standard;
    let mut runtime = DurableMaterialRuntimeV3::create(
        &target.writer,
        campaign,
        michigan_material_runtime_foundation_v2(preset).unwrap(),
    )
    .unwrap();
    install_reader_role_v1(&target.writer).unwrap();
    install_observer_economy_schema_v1(&target.writer).unwrap();
    let config = target.login("babylon_reader", "countycards");
    let reader = SemanticArchiveReaderV1::new(&config).unwrap();
    assert!(reader
        .county_card_atoms(campaign, "26163")
        .unwrap()
        .is_empty());
    for relation in [
        "babylon_meta.archive_knowledge_grant_v1",
        "babylon_state.territory_state_field_v1",
    ] {
        let error = config
            .connect(NoTls)
            .unwrap()
            .query(&format!("SELECT * FROM {relation} LIMIT 1"), &[])
            .unwrap_err();
        assert_eq!(
            error.code(),
            Some(&postgres::error::SqlState::INSUFFICIENT_PRIVILEGE)
        );
    }
    advance_material_week(&mut runtime);
    assert_archive_progress(&reader, campaign, 1, 0);
    let mut worker = ArchiveWorkerV1::new(&target.writer);
    let producer = michigan_archive_producer(&target.writer);
    let first = worker.sweep_once(campaign, &producer).unwrap();
    assert_eq!(
        first.dispositions(),
        &[(1, ArchiveReceiptDispositionV1::Paged)]
    );
    assert_archive_progress(&reader, campaign, 1, 0);
    let pages = assert_all_county_cards(&reader, campaign);
    drop((runtime, worker, producer));
    assert_restart_drains_and_verifies_quiet_weeks(&target, &reader, campaign, &pages);
}

fn assert_restart_drains_and_verifies_quiet_weeks(
    target: &DisposableTarget,
    reader: &SemanticArchiveReaderV1,
    campaign: CampaignId,
    pages: &[ArchiveSearchHitV1],
) {
    let held_county =
        ArchiveAtomSubjectV1::try_new(ArchiveAtomSubjectKindV1::County, "26163".to_owned())
            .unwrap();
    let held_atoms = reader
        .county_card_atoms(campaign, held_county.id())
        .unwrap();

    let mut runtime = DurableMaterialRuntimeV3::open(
        &target.writer,
        campaign,
        michigan_material_runtime_foundation_v2(MichiganDeliveryPresetV1::Standard).unwrap(),
    )
    .unwrap();
    let mut worker = ArchiveWorkerV1::new(&target.writer);
    let producer = michigan_archive_producer(&target.writer);
    for _ in 0..4 {
        if worker
            .sweep_once(campaign, &producer)
            .unwrap()
            .verified_tick()
            == 1
        {
            break;
        }
    }
    assert_archive_progress(reader, campaign, 1, 1);
    assert_eq!(
        reader.search_known(campaign, "QCEW 2024", 100).unwrap(),
        pages
    );
    assert!(worker
        .sweep_once(campaign, &producer)
        .unwrap()
        .dispositions()
        .is_empty());

    for tick in 2..=3 {
        advance_material_week(&mut runtime);
        assert_archive_progress(reader, campaign, tick, tick - 1);
        assert_eq!(
            reader
                .county_card_atoms(campaign, held_county.id())
                .unwrap(),
            held_atoms
        );
        let quiet = worker.sweep_once(campaign, &producer).unwrap();
        assert_eq!(
            quiet.dispositions(),
            &[(tick, ArchiveReceiptDispositionV1::Applied)]
        );
        assert_archive_progress(reader, campaign, tick, tick);
        assert_eq!(
            reader.search_known(campaign, "QCEW 2024", 100).unwrap(),
            pages
        );
        assert_eq!(
            reader
                .subject_atom_history(campaign, &held_county)
                .unwrap()
                .len(),
            held_atoms.len()
        );
        drop(runtime);
        runtime = DurableMaterialRuntimeV3::open(
            &target.writer,
            campaign,
            michigan_material_runtime_foundation_v2(MichiganDeliveryPresetV1::Standard).unwrap(),
        )
        .unwrap();
        assert_eq!(runtime.session().completed_tick(), tick);
    }
}
impl DisposableTarget {
    fn create() -> Self {
        assert_eq!(
            std::env::var("BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK").as_deref(),
            Ok(ACK)
        );
        let canary = std::env::var("BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY").unwrap();
        assert_eq!(canary.len(), 32);
        let admin: Config = std::env::var("BABYLON_LEGACY_ADOPTER_TEST_DSN")
            .unwrap()
            .parse()
            .unwrap();
        validate_legacy_connection_target(&admin).unwrap();
        assert_eq!(admin.get_user(), Some("test"));
        assert_eq!(admin.get_dbname(), Some("postgres"));
        let mut connection = admin.connect(NoTls).unwrap();
        let actual: Option<String> = connection
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.per20_disposable',true)",
                &[],
            )
            .unwrap()
            .get(0);
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        let template = std::env::var("BABYLON_RUNTIME_TEMPLATE_DB").unwrap();
        let suffix = template.strip_prefix("per281_runtime_template_").unwrap();
        assert_eq!(suffix.len(), 12);
        assert!(suffix.bytes().all(|byte| byte.is_ascii_hexdigit()));
        let database = format!("per281_runtime_materialobserver_{}", std::process::id());
        connection
            .batch_execute(&format!(
                "CREATE DATABASE \"{database}\" OWNER test TEMPLATE \"{template}\""
            ))
            .unwrap();
        let mut writer = admin.clone();
        writer.dbname(&database);
        Self {
            admin,
            writer,
            database,
            roles: Vec::new(),
        }
    }

    fn login(&mut self, group: &str, suffix: &str) -> Config {
        assert!(matches!(group, "babylon_observer" | "babylon_reader"));
        assert!(suffix.bytes().all(|byte| byte.is_ascii_lowercase()));
        let role = format!("g4_material_{suffix}_{}", std::process::id());
        let mut connection = self.writer.connect(NoTls).unwrap();
        connection.batch_execute(&format!("CREATE ROLE \"{role}\" LOGIN PASSWORD 'reader' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; GRANT {group} TO \"{role}\"; GRANT SET ON PARAMETER event_triggers TO \"{role}\"")).unwrap();
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
                let removed = connection.batch_execute(&format!("REVOKE SET ON PARAMETER event_triggers FROM \"{role}\"; DROP ROLE IF EXISTS \"{role}\""));
                if !std::thread::panicking() {
                    removed.expect("owned role cleanup");
                }
            }
        }
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed material ticks"]
fn live_material_observer_preserves_history_and_denies_preview_blob_authority() {
    let mut target = DisposableTarget::create();
    let preset = MichiganDeliveryPresetV1::Standard;
    let campaign =
        CampaignId::from_uuid(Uuid::from_u128(0x0044_0000_0000_0000_0000_0000_0000_0001));
    let mut runtime = DurableMaterialRuntimeV3::create(
        &target.writer,
        campaign,
        michigan_material_runtime_foundation_v2(preset).unwrap(),
    )
    .unwrap();
    install_reader_role_v1(&target.writer).unwrap();
    install_observer_economy_schema_v1(&target.writer).unwrap();
    install_observer_economy_schema_v1(&target.writer).unwrap();
    let observer_config = target.login("babylon_observer", "observer");
    let known_config = target.login("babylon_reader", "known");
    let observer =
        ObserverEconomyReaderV1::connect(&observer_config, ObserverVisibilityV1::FullObserver)
            .unwrap();
    let known = ObserverEconomyReaderV1::connect(&known_config, ObserverVisibilityV1::KnownPreview)
        .unwrap();
    let archive = SemanticArchiveReaderV1::new(&known_config).unwrap();
    let zero = observer.snapshot(campaign, 0).unwrap();
    assert_eq!(zero.counties.len(), 83);
    assert_eq!(zero.production.as_ref().unwrap().sites.len(), 5);
    assert!(known.snapshot(campaign, 0).unwrap().production.is_none());
    assert!(known_config
        .connect(NoTls)
        .unwrap()
        .query(
            "SELECT register_bytes FROM public.v_observer_material_state_v1",
            &[]
        )
        .is_err());
    assert_eq!(observer.campaigns().unwrap(), known.campaigns().unwrap());
    assert_eq!(observer.campaigns().unwrap()[0].durable_tick, 0);
    let mut history_at_two = None;
    for tick in 1..=6 {
        let actions = OrderedPracticeActionBatchV1::empty(
            runtime.session().graph_session().session_identity().clone(),
            tick,
        )
        .unwrap();
        runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .unwrap();
        let snapshot = observer.snapshot(campaign, tick).unwrap();
        assert_eq!(snapshot.foundation_digest, zero.foundation_digest);
        assert_eq!(snapshot.resolve_tick, tick);
        assert_eq!(snapshot.counties.len(), 83);
        assert!(snapshot
            .production
            .as_ref()
            .unwrap()
            .events
            .iter()
            .all(|event| event.week <= tick));
        assert!(known.snapshot(campaign, tick).unwrap().production.is_none());
        archive.committed_tick_status(campaign).unwrap();
        if tick == 2 {
            history_at_two = Some(snapshot);
        }
        if tick == 3 {
            runtime = DurableMaterialRuntimeV3::open(
                &target.writer,
                campaign,
                michigan_material_runtime_foundation_v2(preset).unwrap(),
            )
            .unwrap();
            assert_eq!(runtime.session().completed_tick(), 3);
        }
    }
    assert_eq!(
        observer.snapshot(campaign, 2).unwrap(),
        history_at_two.unwrap()
    );
    assert_eq!(observer.campaigns().unwrap()[0].durable_tick, 6);
    assert_eq!(
        observer.snapshot(campaign, 7),
        Err(ObserverEconomyErrorV1::TickAbsent)
    );

    let mut connection = target.writer.connect(NoTls).unwrap();
    assert_corrupted_register_is_rejected(&mut connection, &observer, campaign);

    let known_role = known_config.get_user().unwrap();
    connection
        .batch_execute(&format!(
            "GRANT SELECT ON public.v_observer_material_state_v1 TO \"{known_role}\""
        ))
        .unwrap();
    assert_eq!(
        known.snapshot(campaign, 6),
        Err(ObserverEconomyErrorV1::Authority)
    );
}

fn assert_corrupted_register_is_rejected(
    connection: &mut postgres::Client,
    observer: &ObserverEconomyReaderV1,
    campaign: CampaignId,
) {
    // A syntactically valid stored register mutation cannot retain its committed identity.
    let original: Vec<u8> = connection.query_one("SELECT register_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1 AND resolve_tick=6", &[campaign.as_uuid()]).unwrap().get(0);
    let register = MaterialWorldRegisterV2::decode(&original).unwrap();
    let mut state = register.state().clone();
    state.inventory[0].quantity += 1;
    let corrupt = MaterialWorldRegisterV2::try_new(6, state).unwrap();
    connection.execute("UPDATE babylon_state.material_tick_v3 SET register_bytes=$2 WHERE campaign_id=$1 AND resolve_tick=6", &[campaign.as_uuid(), &corrupt.canonical_bytes()]).unwrap();
    assert_eq!(
        observer.snapshot(campaign, 6),
        Err(ObserverEconomyErrorV1::InvalidProjection)
    );
    connection.execute("UPDATE babylon_state.material_tick_v3 SET register_bytes=$2 WHERE campaign_id=$1 AND resolve_tick=6", &[campaign.as_uuid(), &original]).unwrap();
}
