//! Leaf implementation for the parent module; public paths stay on the parent.

use super::{advance, aid, recovery};

use crate::observer::{ObservationContext, ObserverSession, SessionPhase};

use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::{ObserverEconomySnapshot, ObserverVisibility};
use babylon_persistence::qualification_audit::policy::FrozenPolicy;
use babylon_persistence::qualification_audit::MaterialAudit;

use bevy::prelude::Resource;

use serde::Serialize;

use aid::Custody;
use babylon_kernel::clock::CampaignDuration;
use babylon_persistence::qualification_audit::aid::Boundary;
use babylon_persistence::qualification_audit::policy;
use babylon_persistence::qualification_audit::BoundaryFacts;
use babylon_persistence::qualification_audit::CountyRoster;
use babylon_persistence::runtime_session::OrganizerCommitment;
use babylon_persistence::runtime_session::OrganizerPreview;
use babylon_persistence::runtime_session::OrganizerSnapshot;
use babylon_persistence::runtime_session::RuntimeSessionRequest;
use recovery::Identity;
use serde_json::Value;
use std::fs;
use std::fs::{File, OpenOptions};
use std::io::ErrorKind;
use std::io::{Read, Write};
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::{Path, PathBuf};
use std::time::Instant;

pub(in crate::observer_io) const RECORD_BYTES: usize = 4_194_304;

#[derive(Clone, PartialEq, Eq)]
pub(in crate::observer_io) struct Configuration {
    pub(super) campaign: CampaignId,
    pub(super) policy: FrozenPolicy,
    pub(super) directory: PathBuf,
}

#[derive(Clone, PartialEq, Eq)]
pub(in crate::observer_io) struct Scope {
    pub(super) campaign: CampaignId,
    pub(super) epoch: u64,
    pub(super) foundation: [u8; 32],
}

/// Only explicit qualification transport construction may install this resource.
/// Ordinary play never reads these environment variables or folds receipts here.
#[derive(Resource)]
pub(crate) struct NativeAudit {
    pub(super) configuration: Configuration,
    pub(super) scope: Option<Scope>,
    pub(super) audit: Option<MaterialAudit>,
    pub(super) custody: Custody,
    pub(super) boundary: Option<Identity>,
    pub(super) recovery: Option<recovery::Pending>,
    pub(super) advance: Option<advance::Pending>,
}

pub(in crate::observer_io) struct Work {
    pub(super) configuration: Configuration,
    pub(super) scope: Scope,
    pub(super) audit: MaterialAudit,
    pub(super) custody: Custody,
    pub(super) duration: CampaignDuration,
    pub(super) recovery: Option<recovery::Pending>,
}

#[derive(Serialize)]
pub(in crate::observer_io) struct Record {
    pub(super) version: u8,
    pub(super) scope: &'static str,
    pub(super) runtime_epoch: u64,
    pub(super) observation_generation: u64,
    pub(super) production_read_elapsed_ns: u64,
    pub(super) presentation_read_elapsed_ns: u64,
    pub(super) audit_elapsed_ns: u64,
    pub(super) tick: u64,
    pub(super) tick_content_hash: Option<String>,
    pub(super) opening: Option<Opening>,
    pub(super) facts: Option<BoundaryFacts>,
    pub(super) aid: Option<Boundary>,
    pub(super) aid_practices: Value,
    pub(super) economic_summary: babylon_persistence::qualification_audit::economic::Summary,
    pub(super) aid_summary: babylon_persistence::qualification_audit::aid::Summary,
    pub(super) trade_summary: Value,
}

#[derive(Serialize)]
pub(in crate::observer_io) struct Opening {
    pub(super) campaign: String,
    pub(super) foundation_sha256: String,
    pub(super) graph_foundation_sha256: String,
    pub(super) policy_sha256: String,
    pub(super) material_register_sha256: String,
    pub(super) material_register_bytes: usize,
    #[serde(flatten)]
    pub(super) geography: CountyRoster,
}

pub(in crate::observer_io) struct Candidate {
    pub(super) scope: Scope,
    pub(super) context: ObservationContext,
    pub(super) audit: MaterialAudit,
    pub(super) custody: Custody,
    pub(super) record: Record,
    pub(super) identity: Identity,
    pub(super) recovery: Option<recovery::Pending>,
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
        let hash = policy::canonical_digest(
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
            custody: Custody::default(),
            boundary: None,
            recovery: None,
            advance: None,
        }))
    }

    pub(in crate::observer_io) fn key(&self) -> Configuration {
        self.configuration.clone()
    }

    pub(in crate::observer_io) fn begin(
        &mut self,
        session: &ObserverSession,
    ) -> Result<Option<Work>, String> {
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
            foundation: policy::canonical_digest(
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

    pub(in crate::observer_io) fn commit(
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
        snapshot: OrganizerSnapshot,
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
        request: &RuntimeSessionRequest,
        preview: Option<&OrganizerPreview>,
    ) -> Result<(), String> {
        self.custody.stage(session, request, preview)
    }

    pub(crate) fn accepted(
        &mut self,
        session: &ObserverSession,
        request_id: u64,
        commitment: &OrganizerCommitment,
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

pub(in crate::observer_io) fn publication_matches(
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
            .and_then(|h| policy::canonical_digest(h).ok())
            == Some(scope.foundation)
        && session.viewed_tick == session.durable_tick
        && tick == session.durable_tick
        && session.content_hash.as_deref() == hash
}

pub(in crate::observer_io) struct KnownBinding {
    pub(super) campaign: String,
    pub(super) tick: u64,
    pub(super) foundation: String,
    pub(super) hash: Option<String>,
    pub(super) envelope: Option<String>,
}

impl KnownBinding {
    pub(super) fn from_snapshot(snapshot: &ObserverEconomySnapshot) -> Self {
        Self {
            campaign: snapshot.campaign_id.clone(),
            tick: snapshot.resolve_tick,
            foundation: snapshot.foundation_digest.clone(),
            hash: snapshot.tick_content_hash.clone(),
            envelope: snapshot.envelope_digest.clone(),
        }
    }
    pub(super) fn from_facts(facts: &BoundaryFacts) -> Self {
        Self {
            campaign: facts.campaign.clone(),
            tick: facts.tick,
            foundation: facts.foundation_sha256.clone(),
            hash: Some(facts.tick_content_hash.clone()),
            envelope: Some(facts.envelope_digest.clone()),
        }
    }
    pub(super) fn agrees(&self, snapshot: &ObserverEconomySnapshot) -> bool {
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

pub(in crate::observer_io) fn awaiting_archive(session: &ObserverSession, qualified: bool) -> bool {
    qualified && session.viewed_tick > 0 && session.archive_verified_tick < session.durable_tick
}

pub(in crate::observer_io) fn elapsed(started: Instant) -> Result<u64, String> {
    u64::try_from(started.elapsed().as_nanos()).map_err(|_| "native audit duration overflow".into())
}

pub(in crate::observer_io) fn admit_tick(
    completed: u64,
    tick: u64,
    periods: u64,
) -> Result<bool, String> {
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

pub(in crate::observer_io) fn verify_directory(directory: &Path) -> Result<(), String> {
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

pub(in crate::observer_io) fn exact_existing(path: &Path, bytes: &[u8]) -> Result<(), String> {
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

pub(in crate::observer_io) fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut value = String::new();
    for byte in bytes {
        value.push(char::from(DIGITS[usize::from(byte >> 4)]));
        value.push(char::from(DIGITS[usize::from(byte & 15)]));
    }
    value
}

pub(in crate::observer_io) fn valid_record_name(name: &str) -> bool {
    name.strip_prefix("material-")
        .is_some_and(|tick| tick.parse::<u64>().is_ok_and(|n| n.to_string() == tick))
        || name.strip_prefix("advance-").is_some_and(|tick| {
            tick.parse::<u64>()
                .is_ok_and(|n| n > 0 && n.to_string() == tick)
        })
        || name
            .strip_prefix("aid-")
            .is_some_and(|id| policy::canonical_digest(id).is_ok())
        || name.strip_prefix("recovery-").is_some_and(|suffix| {
            suffix.split_once('-').is_some_and(|(tick, epoch)| {
                [tick, epoch]
                    .into_iter()
                    .all(|value| value.parse::<u64>().is_ok_and(|n| n.to_string() == value))
            })
        })
}

#[cfg(test)]
pub(in crate::observer_io) fn write_record(
    directory: &Path,
    tick: u64,
    bytes: &[u8],
) -> Result<(), String> {
    write_named_record(directory, &format!("material-{tick}"), bytes)
}

pub(in crate::observer_io) fn write_named_record(
    directory: &Path,
    name: &str,
    bytes: &[u8],
) -> Result<(), String> {
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
            Err(error) if error.kind() == ErrorKind::AlreadyExists => {
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
