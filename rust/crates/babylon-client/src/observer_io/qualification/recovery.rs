//! Exact ordinary Open custody; a changed epoch alone never proves recovery.
use super::{hex, Configuration, NativeAudit, Record, Scope};
use crate::observer::{ObserverSession, SessionPhase};
use babylon_kernel::{clock::CampaignDuration, content_digest::sha256_of};
use babylon_persistence::{
    observer_reader::{ObserverEconomySnapshot, ObserverVisibility},
    runtime_session::{
        OrganizerSnapshot, RuntimeSessionRequest, RuntimeSessionScope, RuntimeSessionTarget,
        RUNTIME_SESSION_PROTOCOL_VERSION,
    },
    ProductionEvidenceDigest,
};
use serde::Serialize;
use std::time::Instant;

#[derive(Clone, PartialEq, Eq, Serialize)]
pub(super) struct Identity {
    campaign: String,
    foundation_sha256: String,
    pub(super) tick: u64,
    tick_content_hash: Option<String>,
    nominal_world_hash: Option<String>,
    envelope_digest: Option<String>,
    material_register_sha256: String,
    material_register_bytes: usize,
    production_evidence_sha256: String,
    production_evidence_body_bytes: usize,
    duration: CampaignDuration,
}

impl Identity {
    pub(super) fn capture(
        snapshot: &ObserverEconomySnapshot,
        register: [u8; 32],
        register_bytes: usize,
        evidence: ProductionEvidenceDigest,
        duration: CampaignDuration,
    ) -> Result<Self, String> {
        if snapshot.visibility != ObserverVisibility::FullObserver
            || snapshot.production.as_ref().map(|p| p.duration) != Some(duration)
            || !duration.contains(snapshot.resolve_tick)
        {
            return Err("native recovery requires complete authenticated production".into());
        }
        Ok(Self {
            campaign: snapshot.campaign_id.clone(),
            foundation_sha256: snapshot.foundation_digest.clone(),
            tick: snapshot.resolve_tick,
            tick_content_hash: snapshot.tick_content_hash.clone(),
            nominal_world_hash: snapshot.nominal_world_hash.clone(),
            envelope_digest: snapshot.envelope_digest.clone(),
            material_register_sha256: hex(&register),
            material_register_bytes: register_bytes,
            production_evidence_sha256: evidence.to_hex(),
            production_evidence_body_bytes: evidence.body_bytes(),
            duration,
        })
    }

    pub(super) fn agrees(&self, session: &ObserverSession) -> bool {
        self.campaign == session.campaign.as_uuid().to_string()
            && session.foundation_digest.as_ref() == Some(&self.foundation_sha256)
            && session.durable_tick == self.tick
            && session.viewed_tick == self.tick
            && session.content_hash == self.tick_content_hash
            && session.duration == Some(self.duration)
            && session.organizer_enabled
    }
}

#[derive(Clone, PartialEq, Eq)]
pub(super) struct Pending {
    request_id: u64,
    previous: RuntimeSessionScope,
    next: RuntimeSessionScope,
    source: Identity,
    foundation: [u8; 32],
    original_organizer_sha256: String,
    original_status: OrganizerSnapshot,
    started: Instant,
    switching: bool,
    ready_elapsed_ns: Option<u64>,
    pub(super) status_checked: bool,
}

#[derive(Serialize)]
pub(super) struct Receipt<'a> {
    version: u8,
    scope: &'static str,
    request_id: u64,
    previous_scope: &'a RuntimeSessionScope,
    restored_scope: &'a RuntimeSessionScope,
    policy_sha256: String,
    source: &'a Identity,
    original_organizer_sha256: String,
    cold_reopen_measurement: &'static str,
    runtime_ready_elapsed_ns: u64,
    cold_reopen_elapsed_ns: u64,
    authenticated_read: &'a Record,
}

impl Pending {
    pub(super) fn verify_identity(&self, identity: &Identity) -> Result<(), String> {
        if !self.switching
            || self.ready_elapsed_ns.is_none()
            || !self.status_checked
            || &self.source != identity
        {
            return Err("native restored material differs from its original boundary".into());
        }
        Ok(())
    }

    pub(super) fn verify_status(
        &self,
        session: &ObserverSession,
        actual: &OrganizerSnapshot,
    ) -> Result<(), String> {
        if self.ready_elapsed_ns.is_none()
            || session.runtime_scope() != Some(&self.next)
            || !self.source.agrees(session)
            || actual != &self.original_status
        {
            return Err("native restored organizer differs from its original status".into());
        }
        Ok(())
    }

    pub(super) fn receipt<'a>(
        &'a self,
        configuration: &Configuration,
        record: &'a Record,
    ) -> Result<Receipt<'a>, String> {
        let runtime_ready_elapsed_ns = self
            .ready_elapsed_ns
            .ok_or("native recovery timing lacks runtime Ready")?;
        let cold_reopen_elapsed_ns = super::elapsed(self.started)?;
        if runtime_ready_elapsed_ns
            .checked_add(record.production_read_elapsed_ns)
            .is_none_or(|minimum| cold_reopen_elapsed_ns < minimum)
        {
            return Err("native recovery timing omits its authenticated client read".into());
        }
        Ok(Receipt {
            version: 2,
            scope: "authenticated_native_checkpoint_reopen_v2",
            request_id: self.request_id,
            previous_scope: &self.previous,
            restored_scope: &self.next,
            policy_sha256: hex(&configuration
                .policy
                .scope(configuration.campaign, self.foundation)
                .policy),
            source: &self.source,
            original_organizer_sha256: self.original_organizer_sha256.clone(),
            cold_reopen_measurement: "client_enqueue_to_installed_authenticated_read",
            runtime_ready_elapsed_ns,
            cold_reopen_elapsed_ns,
            authenticated_read: record,
        })
    }
}

impl NativeAudit {
    pub(in crate::observer_io) fn stage_reopen(
        &mut self,
        session: &ObserverSession,
        request: &RuntimeSessionRequest,
    ) -> Result<(), String> {
        let RuntimeSessionRequest::Switch {
            protocol_version,
            request_id,
            scope: previous,
            target,
        } = request
        else {
            return Err("native recovery requires an ordinary campaign switch".into());
        };
        self.configuration
            .policy
            .verify()
            .map_err(|e| e.to_string())?;
        let Some(bound) = &self.scope else {
            // The initial ordinary Open/New admission has no prior boundary.
            let (RuntimeSessionTarget::Open { campaign_id }
            | RuntimeSessionTarget::New { campaign_id, .. }) = target;
            if *protocol_version != RUNTIME_SESSION_PROTOCOL_VERSION
                || campaign_id != &self.configuration.campaign.as_uuid().to_string()
                || session.runtime_scope() != Some(previous)
            {
                return Err(
                    "native qualification initial target differs from its admitted campaign".into(),
                );
            }
            return Ok(());
        };
        let source = self
            .boundary
            .as_ref()
            .ok_or("native recovery source boundary absent")?;
        if *protocol_version != RUNTIME_SESSION_PROTOCOL_VERSION
            || previous
                != session
                    .runtime_scope()
                    .ok_or("native recovery original scope absent")?
            || previous.epoch != bound.epoch
            || !matches!(target, RuntimeSessionTarget::Open { campaign_id } if campaign_id == &source.campaign)
            || !source.agrees(session)
            || !matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
            || session.advance_pending()
            || self.advance.is_some()
            || session.organizer_control_pending()
            || session.archive_verified_tick != source.tick
        {
            return Err(
                "native recovery request differs from the authenticated live boundary".into(),
            );
        }
        if let Some(pending) = &self.recovery {
            if pending.request_id == *request_id
                && &pending.previous == previous
                && !pending.switching
            {
                return Ok(());
            }
            return Err("native recovery already owns another request".into());
        }
        let original_status = self.custody.recovery_status(session)?;
        let original_organizer_sha256 = hex(&sha256_of(
            &serde_json::to_vec(&original_status)
                .map_err(|_| "native recovery original organizer encoding failed")?,
        ));
        self.recovery = Some(Pending {
            request_id: *request_id,
            previous: previous.clone(),
            next: RuntimeSessionScope {
                epoch: previous
                    .epoch
                    .checked_add(1)
                    .ok_or("native recovery epoch exhausted")?,
                campaign_id: Some(source.campaign.clone()),
            },
            source: source.clone(),
            foundation: bound.foundation,
            original_status,
            original_organizer_sha256,
            started: Instant::now(),
            switching: false,
            ready_elapsed_ns: None,
            status_checked: false,
        });
        Ok(())
    }

    pub(in crate::observer_io) fn switching(
        &mut self,
        request_id: u64,
        previous: &RuntimeSessionScope,
        next: &RuntimeSessionScope,
    ) -> Result<(), String> {
        if self.scope.is_none() {
            return Ok(());
        }
        let pending = self
            .recovery
            .as_mut()
            .ok_or("native recovery switch was not captured")?;
        if pending.request_id != request_id
            || &pending.previous != previous
            || &pending.next != next
            || pending.switching
        {
            return Err("native recovery switch identity differs".into());
        }
        pending.switching = true;
        Ok(())
    }

    pub(in crate::observer_io) fn reopened_ready(
        &mut self,
        session: &ObserverSession,
        request_id: u64,
    ) -> Result<(), String> {
        if self.scope.is_none() {
            return Ok(());
        }
        self.configuration
            .policy
            .verify()
            .map_err(|e| e.to_string())?;
        let pending = self
            .recovery
            .as_mut()
            .ok_or("native recovery Ready was not captured")?;
        if !pending.switching
            || pending.request_id != request_id
            || pending.ready_elapsed_ns.is_some()
            || session.runtime_scope() != Some(&pending.next)
            || !pending.source.agrees(session)
        {
            return Err("native recovery Ready differs from its original committed state".into());
        }
        pending.ready_elapsed_ns = Some(super::elapsed(pending.started)?);
        self.scope = Some(Scope {
            campaign: session.campaign,
            epoch: pending.next.epoch,
            foundation: pending.foundation,
        });
        Ok(())
    }

    pub(in crate::observer_io) fn awaiting_recovery_status(&self) -> bool {
        self.recovery
            .as_ref()
            .is_some_and(|pending| !pending.status_checked)
    }
}

#[cfg(test)]
pub(super) mod tests {
    use super::super::{
        aid,
        tests::{fixture, Directory},
        Candidate,
    };
    use super::*;
    use babylon_persistence::runtime_session::RuntimeSessionTail;

    pub(in crate::observer_io::qualification) fn source(
    ) -> (Directory, NativeAudit, ObserverSession, OrganizerSnapshot) {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        let status: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../../../../babylon-persistence/tests/fixtures/national_organizer_opening_v11.json"
        ))
        .unwrap();
        session.ready(0, None);
        session.duration = Some(status.duration);
        session.organizer_enabled = true;
        let work = audit.begin(&session).unwrap().unwrap();
        assert!(session.installed(&session.context()));
        audit.audit = Some(work.audit);
        audit.custody = aid::disclosed_control(&session, status.clone());
        // A controlled authenticated-source identity isolates transition checks.
        // Only the full production reader can construct it in live operation.
        audit.boundary = Some(Identity {
            campaign: session.campaign.as_uuid().to_string(),
            foundation_sha256: session.foundation_digest.clone().unwrap(),
            tick: 0,
            tick_content_hash: None,
            nominal_world_hash: Some("0c".repeat(32)),
            envelope_digest: None,
            material_register_sha256: "0d".repeat(32),
            material_register_bytes: 11,
            production_evidence_sha256: "0e".repeat(32),
            production_evidence_body_bytes: 12,
            duration: status.duration,
        });
        (directory, audit, session, status)
    }

    fn send(
        audit: &mut NativeAudit,
        session: &mut ObserverSession,
    ) -> (u64, RuntimeSessionScope, RuntimeSessionScope) {
        session
            .queue_campaign(RuntimeSessionTarget::Open {
                campaign_id: session.campaign.as_uuid().to_string(),
            })
            .unwrap();
        let request = session.pending_switch_request().unwrap();
        audit.stage_reopen(session, &request).unwrap();
        let before = audit.recovery.clone();
        audit.stage_reopen(session, &request).unwrap();
        assert!(
            audit.recovery == before,
            "backpressure cannot change the original source or clock"
        );
        let RuntimeSessionRequest::Switch {
            request_id, scope, ..
        } = request
        else {
            panic!()
        };
        session.switch_sent();
        let next = RuntimeSessionScope {
            epoch: scope.epoch + 1,
            campaign_id: scope.campaign_id.clone(),
        };
        (request_id, scope, next)
    }

    fn ready(
        audit: &mut NativeAudit,
        session: &mut ObserverSession,
        request_id: u64,
        previous: &RuntimeSessionScope,
        next: RuntimeSessionScope,
        status: &OrganizerSnapshot,
    ) {
        let foundation = session.foundation_digest.clone().unwrap();
        session
            .switching(request_id, previous, next.clone())
            .unwrap();
        audit.switching(request_id, previous, &next).unwrap();
        session
            .admitted(
                request_id,
                foundation,
                RuntimeSessionTail {
                    resolve_tick: 0,
                    tick_content_hash: None,
                },
            )
            .unwrap();
        session.duration = Some(status.duration);
        session.organizer_enabled = true;
        audit.reopened_ready(session, request_id).unwrap();
    }

    fn candidate(audit: &mut NativeAudit, session: &mut ObserverSession) -> Candidate {
        let work = audit.begin(session).unwrap().unwrap();
        assert!(work.recovery.is_some());
        assert!(session.installed(&session.context()));
        Candidate {
            scope: work.scope,
            context: session.context(),
            audit: work.audit,
            custody: work.custody,
            identity: audit.boundary.clone().unwrap(),
            recovery: work.recovery,
            record: Record {
                version: 4,
                scope: "authenticated_native_material_and_aid_facts_only",
                runtime_epoch: session.runtime_scope().unwrap().epoch,
                observation_generation: session.generation,
                production_read_elapsed_ns: 1,
                presentation_read_elapsed_ns: 1,
                audit_elapsed_ns: 1,
                tick: 0,
                tick_content_hash: None,
                opening: None,
                facts: None,
                aid: None,
                aid_practices: audit.custody.practices(),
                economic_summary: audit.audit.as_ref().unwrap().economic_summary(),
                aid_summary: audit.custody.summary(),
                trade_summary: audit.audit.as_ref().unwrap().trade_summary(),
            },
        }
    }

    #[test]
    fn checkpoint_reopen_preserves_the_original_folds_and_requires_the_full_read() {
        let (directory, mut audit, mut session, status) = source();
        let original_practices = audit.custody.practices();
        let (id, previous, next) = send(&mut audit, &mut session);
        assert!(audit.switching(id + 1, &previous, &next).is_err());
        ready(&mut audit, &mut session, id, &previous, next, &status);
        assert!(audit.awaiting_recovery_status());
        assert!(audit.begin(&session).is_err());
        assert_eq!(std::fs::read_dir(&directory.0).unwrap().count(), 1);
        let mut wrong = status.clone();
        wrong.aid[0].payer_cash += 1;
        assert!(audit.status(&session, wrong).is_err());
        assert!(audit.awaiting_recovery_status());
        audit.status(&session, status).unwrap();
        let result = candidate(&mut audit, &mut session);
        audit.commit(&session, result).unwrap();
        assert!(audit.recovery.is_none());
        assert_eq!(audit.audit.as_ref().unwrap().completed_tick(), 0);
        assert!(audit.custody.practices() == original_practices);
        let receipt: serde_json::Value = serde_json::from_slice(
            &std::fs::read(directory.0.join(format!(
                "recovery-0-{}.json",
                session.runtime_scope().unwrap().epoch
            )))
            .unwrap(),
        )
        .unwrap();
        assert_eq!(receipt["version"], 2);
        assert_eq!(
            receipt["cold_reopen_measurement"],
            "client_enqueue_to_installed_authenticated_read"
        );
        assert!(
            receipt["cold_reopen_elapsed_ns"].as_u64().unwrap()
                >= receipt["runtime_ready_elapsed_ns"]
                    .as_u64()
                    .unwrap()
                    .checked_add(
                        receipt["authenticated_read"]["production_read_elapsed_ns"]
                            .as_u64()
                            .unwrap()
                    )
                    .unwrap()
        );
        assert!(
            audit.begin(&session).unwrap().is_none(),
            "refresh must not replay opening or refold receipts"
        );
        let saved: serde_json::Value =
            serde_json::from_slice(&std::fs::read(directory.0.join("recovery-0-2.json")).unwrap())
                .unwrap();
        assert_eq!(saved["scope"], "authenticated_native_checkpoint_reopen_v2");
        assert_eq!(saved["restored_scope"]["epoch"], 2);
        assert!(saved["authenticated_read"]["facts"].is_null());
        assert!(!directory.0.join("material-0.json").exists());
    }

    #[test]
    fn impossible_client_read_timing_leaves_recovery_unpublished_and_pending() {
        let (directory, mut audit, mut session, status) = source();
        let (id, previous, next) = send(&mut audit, &mut session);
        ready(&mut audit, &mut session, id, &previous, next, &status);
        audit.status(&session, status).unwrap();
        let mut result = candidate(&mut audit, &mut session);
        result.record.production_read_elapsed_ns = u64::MAX;
        assert!(audit.commit(&session, result).is_err());
        assert!(audit.recovery.is_some());
        assert_eq!(std::fs::read_dir(&directory.0).unwrap().count(), 1);
    }

    #[test]
    fn changed_restored_material_or_failed_publication_cannot_erase_recovery_custody() {
        let (directory, mut audit, mut session, status) = source();
        let (id, previous, next) = send(&mut audit, &mut session);
        ready(&mut audit, &mut session, id, &previous, next, &status);
        audit.status(&session, status).unwrap();
        let mut result = candidate(&mut audit, &mut session);
        result.identity.material_register_sha256 = "0f".repeat(32);
        assert!(audit.commit(&session, result).is_err());
        assert!(audit.recovery.is_some());
        assert_eq!(std::fs::read_dir(&directory.0).unwrap().count(), 1);
        session.phase = SessionPhase::Loading;
        let result = candidate(&mut audit, &mut session);
        std::fs::create_dir(directory.0.join("recovery-0-2.json")).unwrap();
        assert!(audit.commit(&session, result).is_err());
        assert!(audit.recovery.is_some());
        assert_eq!(audit.audit.as_ref().unwrap().completed_tick(), 0);
        assert_eq!(std::fs::read_dir(&directory.0).unwrap().count(), 2);
    }

    #[test]
    fn ready_with_a_changed_tail_cannot_admit_another_epoch() {
        let (_directory, mut audit, mut session, status) = source();
        let (id, previous, next) = send(&mut audit, &mut session);
        let foundation = session.foundation_digest.clone().unwrap();
        session.switching(id, &previous, next.clone()).unwrap();
        audit.switching(id, &previous, &next).unwrap();
        session
            .admitted(
                id,
                foundation,
                RuntimeSessionTail {
                    resolve_tick: 1,
                    tick_content_hash: Some("a".repeat(64)),
                },
            )
            .unwrap();
        session.duration = Some(status.duration);
        session.organizer_enabled = true;
        assert!(audit.reopened_ready(&session, id).is_err());
        assert_eq!(audit.scope.as_ref().unwrap().epoch, previous.epoch);
        assert!(audit.awaiting_recovery_status());
    }

    #[test]
    fn accepted_but_unadvanced_ruling_requires_fresh_status_and_survives_reopen() {
        use babylon_persistence::runtime_session::{
            OrganizerChoice, OrganizerCommand, OrganizerCommitment,
        };
        let (_directory, mut audit, mut session, mut status) = source();
        let commitment = OrganizerCommitment {
            command: OrganizerCommand {
                campaign_id: *session.campaign.canonical_bytes(),
                actor_id: status.view.actor_id,
                authority_id: status.view.authority_id,
                expected_period: 0,
                content_digest: status.view.content_digest,
                resource_digest: status.view.resource_digest,
                nonce: [17; 16],
                choice: OrganizerChoice::Hold,
            },
            resolves_period: 1,
            commitment_id: [18; 32],
        };
        audit.accepted(&session, 9, &commitment).unwrap();
        assert!(audit.custody.recovery_status(&session).is_err());
        assert!(
            audit.status(&session, status.clone()).is_err(),
            "fresh response cannot lose accepted command"
        );
        status.pending = Some(commitment.clone());
        audit.status(&session, status.clone()).unwrap();
        let (id, previous, next) = send(&mut audit, &mut session);
        ready(&mut audit, &mut session, id, &previous, next, &status);
        let mut missing = status.clone();
        missing.pending = None;
        assert!(audit.status(&session, missing).is_err());
        audit.status(&session, status).unwrap();
        let result = candidate(&mut audit, &mut session);
        assert!(
            result
                .recovery
                .as_ref()
                .unwrap()
                .original_status
                .pending
                .as_ref()
                == Some(&commitment)
        );
        audit.commit(&session, result).unwrap();
        assert_eq!(session.durable_tick, 0);
        assert_eq!(audit.audit.as_ref().unwrap().completed_tick(), 0);
    }
}
