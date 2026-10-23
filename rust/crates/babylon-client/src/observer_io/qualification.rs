//! Optional facts from the native reader; the supervisor alone qualifies runs.

mod advance;
mod aid;
mod read;
mod recovery;

use super::PreparedObservation;
use crate::observer::{ObservationContext, ObserverSession, Perspective, SessionPhase};
use babylon_persistence::{
    identity::CampaignId,
    observer_reader::{
        ObserverEconomyReader, ObserverEconomySnapshot, ObserverMaterialCursor, ObserverVisibility,
    },
    qualification_audit::{
        policy::{canonical_digest, FrozenPolicy},
        MaterialAudit,
    },
};
use bevy::prelude::Resource;
use serde::Serialize;
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    os::unix::fs::{MetadataExt, OpenOptionsExt},
    path::{Path, PathBuf},
    time::Instant,
};

const RECORD_BYTES: usize = 4_194_304;

#[derive(Clone, PartialEq, Eq)]
pub(super) struct Configuration {
    campaign: CampaignId,
    policy: FrozenPolicy,
    directory: PathBuf,
}

#[derive(Clone, PartialEq, Eq)]
struct Scope {
    campaign: CampaignId,
    epoch: u64,
    foundation: [u8; 32],
}

/// Only explicit qualification transport construction may install this resource.
/// Ordinary play never reads these environment variables or folds receipts here.
#[derive(Resource)]
pub(crate) struct NativeAudit {
    configuration: Configuration,
    scope: Option<Scope>,
    audit: Option<MaterialAudit>,
    custody: aid::Custody,
    boundary: Option<recovery::Identity>,
    recovery: Option<recovery::Pending>,
    advance: Option<advance::Pending>,
}

pub(super) struct Work {
    configuration: Configuration,
    scope: Scope,
    audit: MaterialAudit,
    custody: aid::Custody,
    duration: babylon_kernel::clock::CampaignDuration,
    recovery: Option<recovery::Pending>,
}

#[derive(Serialize)]
struct Record {
    version: u8,
    scope: &'static str,
    runtime_epoch: u64,
    observation_generation: u64,
    production_read_elapsed_ns: u64,
    presentation_read_elapsed_ns: u64,
    audit_elapsed_ns: u64,
    tick: u64,
    tick_content_hash: Option<String>,
    opening: Option<Opening>,
    facts: Option<babylon_persistence::qualification_audit::BoundaryFacts>,
    aid: Option<babylon_persistence::qualification_audit::aid::Boundary>,
    aid_practices: serde_json::Value,
    economic_summary: babylon_persistence::qualification_audit::economic::Summary,
    aid_summary: babylon_persistence::qualification_audit::aid::Summary,
    trade_summary: serde_json::Value,
}

#[derive(Serialize)]
struct Opening {
    campaign: String,
    foundation_sha256: String,
    graph_foundation_sha256: String,
    policy_sha256: String,
    material_register_sha256: String,
    material_register_bytes: usize,
    #[serde(flatten)]
    geography: babylon_persistence::qualification_audit::CountyRoster,
}

pub(super) struct Candidate {
    scope: Scope,
    context: ObservationContext,
    audit: MaterialAudit,
    custody: aid::Custody,
    record: Record,
    identity: recovery::Identity,
    recovery: Option<recovery::Pending>,
}

impl NativeAudit {
    pub(crate) fn from_env(campaign: CampaignId) -> Result<Option<Self>, String> {
        let values = [
            "BABYLON_QUALIFICATION_POLICY",
            "BABYLON_QUALIFICATION_POLICY_SHA256",
            "BABYLON_QUALIFICATION_PERIODS",
            "BABYLON_QUALIFICATION_MATERIAL_DIRECTORY",
        ]
        .map(std::env::var_os);
        if values.iter().all(Option::is_none) {
            return Ok(None);
        }
        let [Some(path), Some(hash), Some(periods), Some(directory)] = values else {
            return Err("native audit requires a complete frozen supervisor configuration".into());
        };
        let hash = canonical_digest(
            hash.to_str()
                .ok_or("native audit policy hash is not canonical")?,
        )
        .map_err(|e| e.to_string())?;
        let periods = periods
            .to_str()
            .ok_or("native audit horizon is not canonical")?;
        let horizon: u64 = periods
            .parse()
            .map_err(|_| "native audit horizon is not canonical")?;
        if horizon.to_string() != periods {
            return Err("native audit horizon is not canonical".into());
        }
        let policy =
            FrozenPolicy::open(&PathBuf::from(path), hash, horizon).map_err(|e| e.to_string())?;
        let directory = PathBuf::from(directory);
        verify_directory(&directory)?;
        Ok(Some(Self {
            configuration: Configuration {
                campaign,
                policy,
                directory,
            },
            scope: None,
            audit: None,
            custody: aid::Custody::default(),
            boundary: None,
            recovery: None,
            advance: None,
        }))
    }

    pub(super) fn key(&self) -> Configuration {
        self.configuration.clone()
    }

    pub(super) fn begin(&mut self, session: &ObserverSession) -> Result<Option<Work>, String> {
        self.configuration
            .policy
            .verify()
            .map_err(|e| e.to_string())?;
        if session.campaign != self.configuration.campaign {
            return Err("native qualification requires its original campaign".into());
        }
        let scope = Scope {
            campaign: session.campaign,
            epoch: session
                .runtime_scope()
                .ok_or("native audit runtime scope absent")?
                .epoch,
            foundation: canonical_digest(
                session
                    .foundation_digest
                    .as_deref()
                    .ok_or("native audit foundation absent")?,
            )
            .map_err(|e| e.to_string())?,
        };
        if self.scope.as_ref().is_some_and(|bound| *bound != scope) {
            return Err("native audit scope changed; a separate admitted run is required".into());
        }
        if self.scope.is_none() {
            self.scope = Some(scope.clone());
        }
        if session.viewed_tick != session.durable_tick {
            return Ok(None);
        }
        let completed = self.audit.as_ref().map_or(0, MaterialAudit::completed_tick);
        if self.recovery.is_some() {
            if self.awaiting_recovery_status() {
                return Err("native recovery has not authenticated its restored status".into());
            }
        } else if session.viewed_tick == 0 {
            if self.custody.is_open() {
                return Ok(None);
            }
        } else if !admit_tick(
            completed,
            session.viewed_tick,
            self.configuration.policy.periods(),
        )? {
            return Ok(None);
        }
        let audit = match &self.audit {
            Some(audit) => audit.clone(),
            None => MaterialAudit::new(
                self.configuration
                    .policy
                    .scope(scope.campaign, scope.foundation),
            )
            .map_err(|e| e.to_string())?,
        };
        Ok(Some(Work {
            configuration: self.configuration.clone(),
            scope,
            audit,
            custody: self.custody.clone(),
            duration: session
                .duration
                .ok_or("native audit captured duration absent")?,
            recovery: self.recovery.clone(),
        }))
    }

    pub(super) fn commit(
        &mut self,
        session: &ObserverSession,
        candidate: Candidate,
    ) -> Result<(), String> {
        if self.scope.as_ref() != Some(&candidate.scope)
            || !publication_matches(
                session,
                &candidate.scope,
                &candidate.context,
                candidate.record.tick,
                candidate.record.tick_content_hash.as_deref(),
            )
            || candidate.audit.completed_tick() != session.durable_tick
        {
            return Err("native audit publication context changed".into());
        }
        self.configuration
            .policy
            .verify()
            .map_err(|e| e.to_string())?;
        if candidate.recovery != self.recovery {
            return Err("native recovery publication request changed".into());
        }
        let mut custody = self.custody.clone();
        custody.install(candidate.custody)?;
        let (name, mut bytes) = if let Some(recovery) = &candidate.recovery {
            recovery.verify_identity(&candidate.identity)?;
            (
                format!(
                    "recovery-{}-{}",
                    candidate.record.tick, candidate.scope.epoch
                ),
                serde_json::to_vec(&recovery.receipt(&self.configuration, &candidate.record)?)
                    .map_err(|_| "native recovery record encoding failed")?,
            )
        } else {
            (
                format!("material-{}", candidate.record.tick),
                serde_json::to_vec(&candidate.record)
                    .map_err(|_| "native audit record encoding failed")?,
            )
        };
        bytes.push(b'\n');
        let timing = if candidate.record.tick > 0 && candidate.recovery.is_none() {
            Some(
                self.advance
                    .as_ref()
                    .ok_or("native material publication lacks Advance custody")?
                    .receipt(&self.configuration, session, &candidate.record, &bytes)?,
            )
        } else {
            None
        };
        write_named_record(&self.configuration.directory, &name, &bytes)?;
        if let Some(timing) = timing {
            write_named_record(
                &self.configuration.directory,
                &format!("advance-{}", candidate.record.tick),
                &timing,
            )?;
            self.advance = None;
        }
        self.audit = Some(candidate.audit);
        self.custody = custody;
        self.boundary = Some(candidate.identity);
        self.recovery = None;
        Ok(())
    }

    pub(crate) fn status(
        &mut self,
        session: &ObserverSession,
        snapshot: babylon_persistence::runtime_session::OrganizerSnapshot,
    ) -> Result<(), String> {
        if let Some(recovery) = &self.recovery {
            recovery.verify_status(session, &snapshot)?;
        }
        self.custody.status(session, snapshot)?;
        if let Some(recovery) = &mut self.recovery {
            recovery.status_checked = true;
        }
        Ok(())
    }

    pub(crate) fn stage(
        &mut self,
        session: &ObserverSession,
        request: &babylon_persistence::runtime_session::RuntimeSessionRequest,
        preview: Option<&babylon_persistence::runtime_session::OrganizerPreview>,
    ) -> Result<(), String> {
        self.custody.stage(session, request, preview)
    }

    pub(crate) fn accepted(
        &mut self,
        session: &ObserverSession,
        request_id: u64,
        commitment: &babylon_persistence::runtime_session::OrganizerCommitment,
    ) -> Result<(), String> {
        let scope = self
            .scope
            .as_ref()
            .ok_or("native audit original scope absent")?;
        self.custody
            .accepted(&self.configuration, scope, session, request_id, commitment)
    }

    pub(crate) fn refused(&mut self, session: &ObserverSession, request_id: u64) {
        if let Some(scope) = session.runtime_scope() {
            self.custody.refused(scope, request_id);
        }
    }
}

fn publication_matches(
    session: &ObserverSession,
    scope: &Scope,
    context: &ObservationContext,
    tick: u64,
    hash: Option<&str>,
) -> bool {
    session.accepts(context)
        && matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        && session.runtime_scope().map(|s| s.epoch) == Some(scope.epoch)
        && session.campaign == scope.campaign
        && session
            .foundation_digest
            .as_deref()
            .and_then(|h| canonical_digest(h).ok())
            == Some(scope.foundation)
        && session.viewed_tick == session.durable_tick
        && tick == session.durable_tick
        && session.content_hash.as_deref() == hash
}

struct KnownBinding {
    campaign: String,
    tick: u64,
    foundation: String,
    hash: Option<String>,
    envelope: Option<String>,
}
impl KnownBinding {
    fn from_snapshot(snapshot: &ObserverEconomySnapshot) -> Self {
        Self {
            campaign: snapshot.campaign_id.clone(),
            tick: snapshot.resolve_tick,
            foundation: snapshot.foundation_digest.clone(),
            hash: snapshot.tick_content_hash.clone(),
            envelope: snapshot.envelope_digest.clone(),
        }
    }
    fn from_facts(facts: &babylon_persistence::qualification_audit::BoundaryFacts) -> Self {
        Self {
            campaign: facts.campaign.clone(),
            tick: facts.tick,
            foundation: facts.foundation_sha256.clone(),
            hash: Some(facts.tick_content_hash.clone()),
            envelope: Some(facts.envelope_digest.clone()),
        }
    }
    fn agrees(&self, snapshot: &ObserverEconomySnapshot) -> bool {
        snapshot.visibility == ObserverVisibility::KnownPreview
            && snapshot.production.is_none()
            && snapshot.nominal_world_hash.is_none()
            && snapshot.campaign_id == self.campaign
            && snapshot.resolve_tick == self.tick
            && snapshot.foundation_digest == self.foundation
            && snapshot.tick_content_hash == self.hash
            && snapshot.envelope_digest == self.envelope
    }
}

pub(super) fn awaiting_archive(session: &ObserverSession, qualified: bool) -> bool {
    qualified && session.viewed_tick > 0 && session.archive_verified_tick < session.durable_tick
}

fn elapsed(started: Instant) -> Result<u64, String> {
    u64::try_from(started.elapsed().as_nanos()).map_err(|_| "native audit duration overflow".into())
}

fn admit_tick(completed: u64, tick: u64, periods: u64) -> Result<bool, String> {
    if tick == 0 || tick > periods {
        return Err("native audit period outside frozen horizon".into());
    }
    if completed == tick {
        return Ok(false);
    }
    if completed.checked_add(1) != Some(tick) {
        return Err("native audit lacks the contiguous committed prefix".into());
    }
    Ok(true)
}

fn verify_directory(directory: &Path) -> Result<(), String> {
    let owner = fs::metadata("/proc/self")
        .map_err(|_| "native audit owner unavailable")?
        .uid();
    let metadata = directory
        .symlink_metadata()
        .map_err(|_| "native audit directory unavailable")?;
    if !directory.is_absolute()
        || directory.canonicalize().ok().as_deref() != Some(directory)
        || !metadata.is_dir()
        || metadata.uid() != owner
        || metadata.mode() & 0o777 != 0o700
    {
        return Err("native audit directory must be private, owned and free of symlinks".into());
    }
    Ok(())
}

fn exact_existing(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let metadata = path
        .symlink_metadata()
        .map_err(|_| "native audit record unavailable")?;
    if !metadata.is_file() || metadata.len() > RECORD_BYTES as u64 {
        return Err("native audit existing record is not bounded".into());
    }
    let mut prior = Vec::new();
    File::open(path)
        .map_err(|_| "native audit record unavailable")?
        .take(RECORD_BYTES as u64 + 1)
        .read_to_end(&mut prior)
        .map_err(|_| "native audit record unavailable")?;
    if prior != bytes {
        return Err("native audit existing record conflicts".into());
    }
    Ok(())
}

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut value = String::new();
    for byte in bytes {
        value.push(char::from(DIGITS[usize::from(byte >> 4)]));
        value.push(char::from(DIGITS[usize::from(byte & 15)]));
    }
    value
}

fn valid_record_name(name: &str) -> bool {
    name.strip_prefix("material-")
        .is_some_and(|tick| tick.parse::<u64>().is_ok_and(|n| n.to_string() == tick))
        || name.strip_prefix("advance-").is_some_and(|tick| {
            tick.parse::<u64>()
                .is_ok_and(|n| n > 0 && n.to_string() == tick)
        })
        || name
            .strip_prefix("aid-")
            .is_some_and(|id| canonical_digest(id).is_ok())
        || name.strip_prefix("recovery-").is_some_and(|suffix| {
            suffix.split_once('-').is_some_and(|(tick, epoch)| {
                [tick, epoch]
                    .into_iter()
                    .all(|value| value.parse::<u64>().is_ok_and(|n| n.to_string() == value))
            })
        })
}

#[cfg(test)]
fn write_record(directory: &Path, tick: u64, bytes: &[u8]) -> Result<(), String> {
    write_named_record(directory, &format!("material-{tick}"), bytes)
}

fn write_named_record(directory: &Path, name: &str, bytes: &[u8]) -> Result<(), String> {
    verify_directory(directory)?;
    if !valid_record_name(name) || bytes.is_empty() || bytes.len() > RECORD_BYTES {
        return Err("native audit record is not bounded".into());
    }
    let target = directory.join(format!("{name}.json"));
    if target
        .try_exists()
        .map_err(|_| "native audit output lookup failed")?
    {
        return exact_existing(&target, bytes);
    }
    let temporary = directory.join(format!(".{name}-{}.tmp", uuid::Uuid::new_v4()));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&temporary)
        .map_err(|_| "native audit temporary record failed")?;
    let result = (|| {
        file.write_all(bytes)
            .and_then(|()| file.sync_all())
            .map_err(|_| "native audit record write failed")?;
        verify_directory(directory)?;
        match fs::hard_link(&temporary, &target) {
            Ok(()) => {}
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
                exact_existing(&target, bytes)?;
            }
            Err(_) => return Err("native audit atomic publication failed".into()),
        }
        File::open(directory)
            .and_then(|file| file.sync_all())
            .map_err(|_| "native audit directory sync failed".into())
    })();
    drop(file);
    let cleanup = fs::remove_file(&temporary)
        .map_err(|_| "native audit temporary cleanup failed".to_string());
    result.and(cleanup)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fs, os::unix::fs::PermissionsExt, path::PathBuf};

    pub(super) struct Directory(pub(super) PathBuf);
    impl Directory {
        pub(super) fn new() -> Self {
            let path =
                std::env::temp_dir().join(format!("babylon-native-audit-{}", uuid::Uuid::new_v4()));
            fs::create_dir(&path).unwrap();
            fs::set_permissions(&path, fs::Permissions::from_mode(0o700)).unwrap();
            Self(path)
        }
    }
    impl Drop for Directory {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }

    #[test]
    fn boundary_records_are_exact_atomic_and_conflicting_records_are_preserved() {
        let directory = Directory::new();
        write_record(&directory.0, 1, b"original\n").unwrap();
        write_record(&directory.0, 1, b"original\n").unwrap();
        assert!(write_record(&directory.0, 1, b"changed\n").is_err());
        assert_eq!(
            fs::read(directory.0.join("material-1.json")).unwrap(),
            b"original\n"
        );
        assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 1);
        assert!(write_record(&directory.0, 2, &vec![0; RECORD_BYTES + 1]).is_err());
        assert!(!directory.0.join("material-2.json").exists());
    }

    #[test]
    fn failed_publication_and_changed_directory_publish_nothing() {
        let directory = Directory::new();
        fs::create_dir(directory.0.join("material-1.json")).unwrap();
        assert!(write_record(&directory.0, 1, b"facts\n").is_err());
        assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 1);
        fs::set_permissions(&directory.0, fs::Permissions::from_mode(0o755)).unwrap();
        assert!(write_record(&directory.0, 2, b"facts\n").is_err());
        assert!(!directory.0.join("material-2.json").exists());
    }

    #[test]
    fn native_boundary_continuity_refuses_missing_prefix_and_does_not_refold_refresh() {
        assert!(admit_tick(0, 1, 52).unwrap());
        assert!(!admit_tick(1, 1, 52).unwrap());
        assert!(admit_tick(0, 2, 52).is_err());
        assert!(admit_tick(2, 1, 52).is_err());
        assert!(admit_tick(52, 53, 52).is_err());
    }

    pub(super) fn fixture(directory: &Directory) -> (NativeAudit, ObserverSession) {
        let bytes =
            include_bytes!("../../../../../contracts/national_storage_qualification_v6.json");
        let path = directory.0.join("policy.json");
        fs::write(&path, bytes).unwrap();
        let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(1));
        let policy =
            FrozenPolicy::open(&path, babylon_kernel::content_digest::sha256_of(bytes), 52)
                .unwrap();
        let audit = NativeAudit {
            configuration: Configuration {
                campaign,
                policy,
                directory: directory.0.clone(),
            },
            scope: None,
            audit: None,
            custody: aid::Custody::default(),
            boundary: None,
            recovery: None,
            advance: None,
        };
        let mut session = ObserverSession::new(campaign);
        session.connected_fixture();
        session.ready(1, Some("b".repeat(64)));
        session.foundation_digest = Some("0a".repeat(32));
        session.duration = Some(babylon_kernel::clock::CampaignDuration::Continuous);
        (audit, session)
    }

    #[test]
    fn opening_is_authenticated_before_the_first_accepted_aid_offer() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        session.viewed_tick = 0;
        session.durable_tick = 0;
        session.content_hash = None;
        assert!(audit.begin(&session).unwrap().is_some());
        assert!(audit.audit.is_none());
        assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 1);
    }

    #[test]
    fn native_reopen_requires_an_authenticated_boundary_and_an_exact_sent_request() {
        use babylon_persistence::runtime_session::{RuntimeSessionRequest, RuntimeSessionTarget};
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        audit.begin(&session).unwrap();
        session.archive_verified_tick = session.durable_tick;
        let original_scope = session.runtime_scope().unwrap().clone();
        session
            .queue_campaign(RuntimeSessionTarget::Open {
                campaign_id: session.campaign.as_uuid().to_string(),
            })
            .unwrap();
        let request = session.pending_switch_request().unwrap();
        assert!(audit.stage_reopen(&session, &request).is_err());
        assert!(audit.recovery.is_none());
        let RuntimeSessionRequest::Switch { request_id, .. } = request else {
            panic!()
        };
        session.switch_sent();
        let mut new_scope = original_scope.clone();
        new_scope.epoch += 1;
        session
            .switching(request_id, &original_scope, new_scope.clone())
            .unwrap();
        assert!(audit
            .switching(request_id, &original_scope, &new_scope)
            .is_err());
        assert_eq!(audit.scope.as_ref().unwrap().epoch, original_scope.epoch);
        assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 1);
    }

    #[test]
    fn qualification_refuses_changed_policy_and_scope_before_reading() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        assert!(audit.begin(&session).unwrap().is_some());
        session.viewed_tick = 0;
        // Inspecting historical tick 0 at a positive durable tail does not fold.
        assert!(audit.begin(&session).unwrap().is_none());
        session.viewed_tick = 1;
        session.perspective = Perspective::PlayerKnowledge;
        assert!(audit.begin(&session).unwrap().is_some());
        session.perspective = Perspective::FullObserver;
        session.foundation_digest = Some("0b".repeat(32));
        assert!(audit.begin(&session).is_err());
        session.foundation_digest = Some("0a".repeat(32));
        fs::write(directory.0.join("policy.json"), b"{}").unwrap();
        assert!(audit.begin(&session).is_err());
        assert!(audit.audit.is_none());
        assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 1);
    }

    #[test]
    fn publication_requires_installed_generation_campaign_epoch_and_identity() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        audit.begin(&session).unwrap();
        let scope = audit.scope.as_ref().unwrap();
        let context = session.context();
        let hash = "b".repeat(64);
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        assert!(session.installed(&context));
        assert!(publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            2,
            Some(&hash)
        ));
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&"c".repeat(64))
        ));
        let mut wrong_scope = scope.clone();
        wrong_scope.epoch += 1;
        assert!(!publication_matches(
            &session,
            &wrong_scope,
            &context,
            1,
            Some(&hash)
        ));
        wrong_scope = scope.clone();
        wrong_scope.campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(2));
        assert!(!publication_matches(
            &session,
            &wrong_scope,
            &context,
            1,
            Some(&hash)
        ));
        session.foundation_digest = Some("0b".repeat(32));
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        session.foundation_digest = Some("0a".repeat(32));
        session.generation += 1;
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 1);
    }

    #[test]
    fn native_wayne_knowledge_view_keeps_its_visibility_during_private_audit() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        session.perspective = Perspective::PlayerKnowledge;
        assert!(audit.begin(&session).unwrap().is_some());
        assert_eq!(session.perspective, Perspective::PlayerKnowledge);
        assert!(audit.audit.is_none());
    }

    #[test]
    fn large_qualified_reads_wait_for_the_current_archive_acknowledgement() {
        let directory = Directory::new();
        let (_, mut session) = fixture(&directory);
        assert!(awaiting_archive(&session, true));
        assert!(!awaiting_archive(&session, false));
        session.archive_verified_tick = 1;
        assert!(!awaiting_archive(&session, true));
        session.archive_verified_tick = 0;
        session.viewed_tick = 0;
        assert!(!awaiting_archive(&session, true));
    }

    #[test]
    fn player_disclosure_binds_private_identity_without_exposing_material_facts() {
        let binding = KnownBinding {
            campaign: uuid::Uuid::from_u128(1).to_string(),
            tick: 1,
            foundation: "a".repeat(64),
            hash: Some("b".repeat(64)),
            envelope: Some("c".repeat(64)),
        };
        let mut snapshot = ObserverEconomySnapshot {
            campaign_id: binding.campaign.clone(),
            resolve_tick: 1,
            foundation_digest: binding.foundation.clone(),
            tick_content_hash: binding.hash.clone(),
            envelope_digest: binding.envelope.clone(),
            nominal_world_hash: None,
            visibility: ObserverVisibility::KnownPreview,
            counties: vec![],
            production: None,
        };
        assert!(binding.agrees(&snapshot));
        snapshot.envelope_digest = Some("d".repeat(64));
        assert!(!binding.agrees(&snapshot));
        snapshot.envelope_digest = binding.envelope.clone();
        snapshot.nominal_world_hash = Some("e".repeat(64));
        assert!(!binding.agrees(&snapshot));
        snapshot.nominal_world_hash = None;
        snapshot.visibility = ObserverVisibility::FullObserver;
        assert!(!binding.agrees(&snapshot));
    }

    #[test]
    fn stale_qualified_read_drains_before_another_reconstruction_can_start() {
        use super::super::{
            start_observation, ObservationCache, ObservationRead, PendingObservation,
        };
        use crate::observer_ui::ObserverFrame;
        use bevy::{
            prelude::{App, MinimalPlugins},
            tasks::AsyncComputeTaskPool,
        };

        let directory = Directory::new();
        let (audit, mut session) = fixture(&directory);
        session.archive_verified_tick = 1;
        let stale = session.context();
        session.generation += 1;
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(session)
            .insert_resource(audit)
            .init_resource::<ObservationCache>()
            .init_resource::<ObserverFrame>()
            .add_systems(bevy::prelude::Update, start_observation);
        let task = AsyncComputeTaskPool::get()
            .spawn(async { bevy::tasks::futures_lite::future::pending::<ObservationRead>().await });
        app.insert_resource(PendingObservation(Some((stale.clone(), task))));
        for _ in 0..2 {
            app.update();
        }
        assert_eq!(
            app.world()
                .resource::<PendingObservation>()
                .0
                .as_ref()
                .unwrap()
                .0,
            stale
        );
        assert_eq!(
            app.world().resource::<ObserverSession>().phase,
            SessionPhase::Loading
        );
        assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 1);
    }
}
