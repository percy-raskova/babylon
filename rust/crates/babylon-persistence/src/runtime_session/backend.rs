//! Explicit New/Open admission reuses the single durable material runtime.

use babylon_bsl::structural_verbs::CollectingSink;
use postgres::{Config, NoTls};

use super::{RuntimeSessionErrorCode, RuntimeSessionTail, RuntimeSessionTarget, SessionBackend};
use crate::{
    economic_content::{admit_economic_content, EconomicContentAdmission},
    identity::CampaignId,
    material_runtime::{DurableMaterialRuntime, MaterialRuntimeError},
    michigan_content::MichiganContentPreset,
    michigan_economy::digest_hex,
};

pub(super) struct DurableBackend {
    config: Config,
    campaign: CampaignId,
    runtime: DurableMaterialRuntime,
    tail: RuntimeSessionTail,
}
impl SessionBackend for DurableBackend {
    fn duration(&self) -> babylon_kernel::clock::CampaignDuration {
        self.runtime.session().duration()
    }
    fn has_organizer(&self) -> bool {
        self.runtime.has_organizer()
    }
    fn organizer_status(&self) -> Result<super::OrganizerSnapshot, RuntimeSessionErrorCode> {
        self.runtime.organizer_snapshot()
    }
    fn organizer_preview(
        &self,
        command: &super::OrganizerCommand,
    ) -> Result<super::OrganizerPreview, RuntimeSessionErrorCode> {
        self.runtime.preview_organizer_command(command)
    }
    fn organizer_submit(
        &self,
        command: &super::OrganizerCommand,
    ) -> Result<super::OrganizerCommitment, RuntimeSessionErrorCode> {
        self.runtime.submit_organizer_command(command)
    }
    fn tail(&self) -> RuntimeSessionTail {
        self.tail.clone()
    }
    fn advance(
        &mut self,
        expected: &RuntimeSessionTail,
    ) -> Result<RuntimeSessionTail, RuntimeSessionErrorCode> {
        if expected != &self.tail || durable_tail(&self.config, self.campaign)? != self.tail {
            return Err(RuntimeSessionErrorCode::StaleExpectedTail);
        }
        let actions = self
            .runtime
            .next_action_batch()
            .map_err(|error| advance_error(&error))?;
        let receipt = self
            .runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .map_err(|error| advance_error(&error))?;
        self.tail = RuntimeSessionTail {
            resolve_tick: receipt.resolve_tick(),
            tick_content_hash: Some(digest_hex(receipt.tick_content_hash().as_bytes())),
        };
        Ok(self.tail.clone())
    }
}

fn advance_error(error: &MaterialRuntimeError) -> RuntimeSessionErrorCode {
    // Operator diagnostics only: retain the safe database cause before the
    // protocol maps it to a deliberately bounded refusal code.
    if std::env::var("BABYLON_TIMINGS").as_deref() == Ok("1") {
        match error {
            MaterialRuntimeError::Graph(crate::RustPersistenceRuntimeError::Database {
                operation,
                diagnostic,
            }) => eprintln!(
                "babylon-session advance_refused operation={operation:?} sqlstate={:?}",
                diagnostic.as_ref().and_then(crate::PostgresDiagnostic::sqlstate)
            ),
            MaterialRuntimeError::Database(error)
            | MaterialRuntimeError::DatabaseLockRefused(error)
            | MaterialRuntimeError::DatabaseStatementCanceled(error) => eprintln!(
                "babylon-session advance_refused operation=\"material runtime advance\" sqlstate={:?}",
                crate::PostgresDiagnostic::capture(error).sqlstate()
            ),
            _ => {}
        }
    }
    match error {
        MaterialRuntimeError::Replay(
            babylon_tick::material_replay::MaterialReplayError::Horizon,
        ) => RuntimeSessionErrorCode::HorizonComplete,
        MaterialRuntimeError::DatabaseLockRefused(_) => RuntimeSessionErrorCode::StorageBusy,
        MaterialRuntimeError::DatabaseStatementCanceled(_) => {
            RuntimeSessionErrorCode::StorageCanceled
        }
        MaterialRuntimeError::TailConflict => RuntimeSessionErrorCode::StaleExpectedTail,
        _ => RuntimeSessionErrorCode::CommitRefused,
    }
}

fn durable_tail(
    config: &Config,
    campaign: CampaignId,
) -> Result<RuntimeSessionTail, RuntimeSessionErrorCode> {
    let bounded = crate::material_runtime::bounded_material_writer_config(config)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let mut client = bounded
        .connect(NoTls)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let row = client.query_opt("SELECT resolve_tick, tick_content_hash FROM babylon_state.tick_commit WHERE campaign_id = $1 ORDER BY resolve_tick DESC LIMIT 1", &[campaign.as_uuid()]).map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    match row {
        None => Ok(RuntimeSessionTail {
            resolve_tick: 0,
            tick_content_hash: None,
        }),
        Some(row) => {
            let tick: i64 = row
                .try_get(0)
                .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
            let hash: Vec<u8> = row
                .try_get(1)
                .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
            if tick <= 0 || hash.len() != 32 {
                return Err(RuntimeSessionErrorCode::StorageRefused);
            }
            Ok(RuntimeSessionTail {
                resolve_tick: u64::try_from(tick)
                    .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?,
                tick_content_hash: Some(digest_hex(&hash)),
            })
        }
    }
}

pub(super) fn open(
    config: &Config,
    target: &RuntimeSessionTarget,
    defines_path: &std::path::Path,
) -> Result<(DurableBackend, String), RuntimeSessionErrorCode> {
    let campaign = target.campaign()?;
    let bounded = crate::material_runtime::bounded_material_writer_config(config)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    crate::runtime::verify_runtime_schema(config)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    crate::install_reader_role(config).map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    crate::observer_reader::provision_observer_role(config)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let (runtime, foundation_digest) = match target {
        RuntimeSessionTarget::Open { .. } => {
            let mut client = bounded
                .connect(NoTls)
                .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
            let admitted = runtime_content(&mut client, campaign)?;
            (
                DurableMaterialRuntime::open(config, campaign, admitted.digest()),
                digest_hex(&admitted.digest()),
            )
        }
        RuntimeSessionTarget::New { preset, .. } => {
            let foundation = new_foundation(*preset, defines_path, campaign)?;
            let digest = digest_hex(&foundation.digest());
            (
                DurableMaterialRuntime::create_new(config, campaign, foundation),
                digest,
            )
        }
    };
    let runtime = runtime.map_err(|error| match error {
        MaterialRuntimeError::AlreadyExists => RuntimeSessionErrorCode::CampaignAlreadyExists,
        MaterialRuntimeError::MissingCampaign => RuntimeSessionErrorCode::CampaignAbsent,
        MaterialRuntimeError::LegacyCampaign | MaterialRuntimeError::FoundationMismatch => {
            RuntimeSessionErrorCode::ScenarioMismatch
        }
        _ => RuntimeSessionErrorCode::StorageRefused,
    })?;
    let tail = durable_tail(config, campaign)?;
    if runtime.session().completed_tick() != tail.resolve_tick {
        return Err(RuntimeSessionErrorCode::StorageRefused);
    }
    Ok((
        DurableBackend {
            config: config.clone(),
            campaign,
            runtime,
            tail,
        },
        foundation_digest,
    ))
}

fn new_foundation(
    preset: super::RuntimeSessionPreset,
    defines_path: &std::path::Path,
    campaign: CampaignId,
) -> Result<crate::material_runtime::MaterialRuntimeFoundation, RuntimeSessionErrorCode> {
    if preset == super::RuntimeSessionPreset::NationalWorld {
        let captured = crate::economic_catalog::CapturedEconomicCatalog::capture(
            crate::economic_catalog::national_catalog_input(),
            None,
        )
        .map_err(|error| {
            eprintln!("National source admission refused: {error}");
            RuntimeSessionErrorCode::ScenarioMismatch
        })?;
        return captured
            .create_foundation(
                babylon_kernel::replay::ReplaySessionId::try_from("national-world")
                    .map_err(|_| RuntimeSessionErrorCode::ScenarioMismatch)?,
                babylon_kernel::replay::ReplaySeed::new(319),
            )
            .map_err(|error| {
                eprintln!("National foundation refused: {error}");
                RuntimeSessionErrorCode::ScenarioMismatch
            });
    }
    let delivery = preset
        .delivery()
        .ok_or(RuntimeSessionErrorCode::ScenarioMismatch)?;
    // Only Michigan controls consume this mutable New-only parameter file.
    // Open and national New use their explicit captured-source paths.
    let catalog =
        crate::michigan_material::MichiganMaterialCatalog::load_for_preset(defines_path, delivery)
            .map_err(|error| {
                eprintln!("{error}");
                match error {
                    crate::MichiganDefinesError::Read(_) => RuntimeSessionErrorCode::DefinesMissing,
                    crate::MichiganDefinesError::TooLarge => {
                        RuntimeSessionErrorCode::DefinesTooLarge
                    }
                    crate::MichiganDefinesError::Toml(_) | crate::MichiganDefinesError::Utf8(_) => {
                        RuntimeSessionErrorCode::DefinesMalformed
                    }
                    _ => RuntimeSessionErrorCode::DefinesInvalid,
                }
            })?;
    MichiganContentPreset::new_campaign(delivery)
        .create_foundation_for_campaign(&catalog, campaign)
        .map_err(|_| RuntimeSessionErrorCode::ScenarioMismatch)
}

fn runtime_content(
    client: &mut impl postgres::GenericClient,
    campaign: CampaignId,
) -> Result<EconomicContentAdmission, RuntimeSessionErrorCode> {
    let row = client.query_opt("SELECT f.preset_id,f.duration_kind,f.final_period,f.content_sha256,f.foundation_sha256,g.foundation_sha256 AS graph_sha256,pg_catalog.sha256(g.content_bundle_bytes) AS source_sha256,f.foundation_bytes FROM babylon_state.material_campaign_foundation_v3 f JOIN babylon_state.campaign_foundation g USING(campaign_id) WHERE campaign_id=$1::uuid", &[campaign.as_uuid()])
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let Some(row) = row else {
        return Err(RuntimeSessionErrorCode::CampaignAbsent);
    };
    let id: String = row
        .try_get(0)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let duration = crate::material_runtime::read_duration(&row)
        .map_err(|_| RuntimeSessionErrorCode::ScenarioMismatch)?;
    let content: Vec<u8> = row
        .try_get("content_sha256")
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let foundation: Vec<u8> = row
        .try_get("foundation_sha256")
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let graph: Vec<u8> = row
        .try_get("graph_sha256")
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let scenario: Vec<u8> = row
        .try_get("source_sha256")
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let bytes: Vec<u8> = row
        .try_get("foundation_bytes")
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let admitted = admit_economic_content(&id, duration, &content, &foundation, 0, &bytes)
        .map_err(|_| RuntimeSessionErrorCode::ScenarioMismatch)?;
    admitted
        .validate_graph(&graph, &scenario)
        .map_err(|_| RuntimeSessionErrorCode::ScenarioMismatch)?;
    Ok(admitted)
}

#[cfg(test)]
mod defines_tests {
    use super::*;
    #[test]
    fn statewide_new_requires_qualified_sources_before_storage_admission() {
        use super::super::RuntimeSessionPreset;
        let directory =
            std::env::temp_dir().join(format!("babylon-statewide-defines-{}", std::process::id()));
        std::fs::create_dir(&directory).unwrap();
        let path = directory.join("defines.toml");
        let manifest = directory.join("statewide-sources.json");
        std::fs::write(
            &path,
            include_str!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../../content/scenarios/michigan/defines.toml"
            )),
        )
        .unwrap();
        for preset in [
            RuntimeSessionPreset::StatewideBaseline,
            RuntimeSessionPreset::StatewideFreightConstraint,
            RuntimeSessionPreset::StatewidePackagingShortage,
            RuntimeSessionPreset::StatewideBoth,
            RuntimeSessionPreset::StatewideMaintenanceBaseline,
            RuntimeSessionPreset::StatewideMaintenanceLaborShortage,
            RuntimeSessionPreset::StatewideMaintenancePartsShortage,
            RuntimeSessionPreset::StatewideMaintenanceBoth,
        ] {
            let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(31));
            assert!(matches!(
                new_foundation(preset, &path, campaign),
                Err(RuntimeSessionErrorCode::DefinesMissing)
            ));
            std::fs::write(&manifest, b"{}").unwrap();
            assert!(matches!(
                new_foundation(preset, &path, campaign),
                Err(RuntimeSessionErrorCode::DefinesInvalid)
            ));
            std::fs::remove_file(&manifest).unwrap();
        }
        std::fs::remove_file(&path).unwrap();
        std::fs::remove_dir(&directory).unwrap();
    }
    #[test]
    fn michigan_new_captures_changed_parameters_and_refuses_missing_or_malformed_sources() {
        let path =
            std::env::temp_dir().join(format!("babylon-defines-{}.toml", std::process::id()));
        let preset = super::super::RuntimeSessionPreset::Standard;
        let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(17));
        assert!(matches!(
            new_foundation(preset, &path, campaign),
            Err(RuntimeSessionErrorCode::DefinesMissing)
        ));
        let source = include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/michigan/defines.toml"
        ));
        std::fs::write(&path, source).unwrap();
        let first = new_foundation(preset, &path, campaign).unwrap();
        std::fs::write(
            &path,
            source.replace(
                "WORK_HOURS_PER_PERSON_WEEK = 40",
                "WORK_HOURS_PER_PERSON_WEEK = 45",
            ),
        )
        .unwrap();
        let second = new_foundation(preset, &path, campaign).unwrap();
        assert_ne!(first.digest(), second.digest());
        assert_ne!(
            first.initial_register().canonical_bytes(),
            second.initial_register().canonical_bytes()
        );
        std::fs::write(&path, "malformed = [").unwrap();
        assert!(matches!(
            new_foundation(preset, &path, campaign),
            Err(RuntimeSessionErrorCode::DefinesMalformed)
        ));
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn action_batch_tail_conflict_requires_current_state() {
        assert_eq!(
            advance_error(&MaterialRuntimeError::TailConflict),
            RuntimeSessionErrorCode::StaleExpectedTail
        );
    }

    #[test]
    fn action_batch_corruption_and_bounds_are_commit_failures_not_ruling_refusals() {
        for error in [
            MaterialRuntimeError::OrganizerStorage,
            MaterialRuntimeError::Bounds,
        ] {
            assert_eq!(
                advance_error(&error),
                RuntimeSessionErrorCode::CommitRefused
            );
        }
    }
}
