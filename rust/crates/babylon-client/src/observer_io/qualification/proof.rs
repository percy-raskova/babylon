//! The ordinary installed frame precedes one explicitly requested private fold.

use super::state::KnownBinding;
use super::{Candidate, NativeAudit, Scope, Work};
use crate::observer::{ObservationContext, ObserverSession, Perspective, SessionPhase};
use babylon_persistence::observer_reader::{ObserverEconomySnapshot, ObserverMaterialCursor};
use serde::Serialize;

#[derive(Clone)]
pub(in crate::observer_io) struct InstalledKnown {
    pub(super) scope: Scope,
    pub(super) context: ObservationContext,
    pub(super) binding: KnownBinding,
    pub(super) world_hash: String,
    pub(super) presentation_read_elapsed_ns: u64,
    revision: u64,
    request_id: u64,
}

pub(super) struct Fence {
    installed: InstalledKnown,
    sequence: u64,
}

pub(super) enum Progress {
    AwaitingFence(InstalledKnown),
    Requested(Fence),
    Reading(Fence),
    AwaitingJoin {
        fence: Fence,
        candidate: Box<Candidate>,
        cursor: Box<ObserverMaterialCursor>,
    },
    Published {
        fence: Fence,
        receipt: PeriodProofReceipt,
    },
    Acknowledged {
        fence: Fence,
        receipt: PeriodProofReceipt,
    },
    Refused {
        fence: Fence,
        reason: &'static str,
    },
}

#[derive(Serialize)]
pub(crate) struct PeriodProofReceipt {
    campaign_id: String,
    scope_epoch: u64,
    foundation_sha256: String,
    policy_sha256: String,
    generation: u64,
    tick: u64,
    tick_content_hash: Option<String>,
    world_hash: String,
    envelope_digest: Option<String>,
    request_id: u64,
    archive_verified_tick: u64,
    material_record_sha256: String,
}

impl InstalledKnown {
    fn matches(&self, audit: &NativeAudit, session: &ObserverSession) -> bool {
        audit.scope.as_ref() == Some(&self.scope)
            && session.accepts(&self.context)
            && session.perspective == Perspective::PlayerKnowledge
            && !session.playing
            && !session.quit_requested
            && !session.lifecycle_pending()
            && matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
            && session.foundation_digest.as_ref() == Some(&self.binding.foundation)
            && session.content_hash == self.binding.hash
            && session.world_hash.as_ref() == Some(&self.world_hash)
            && audit.custody.revision == self.revision
            && audit
                .advance
                .as_ref()
                .and_then(|a| a.live_known_request(session))
                == Some(self.request_id)
    }

    pub(super) fn agrees(&self, candidate: &Candidate) -> bool {
        candidate.scope == self.scope
            && candidate.context == self.context
            && candidate.audit.completed_tick() == self.context.tick
            && candidate.record.tick == self.context.tick
            && candidate.record.runtime_epoch == self.scope.epoch
            && candidate.record.observation_generation == self.context.generation
            && candidate.recovery.is_none()
            && candidate.custody.revision == self.revision
            && candidate.record.presentation_read_elapsed_ns == self.presentation_read_elapsed_ns
            && candidate.record.facts.as_ref().is_some_and(|facts| {
                KnownBinding::from_facts(facts) == self.binding
                    && facts.nominal_world_hash == self.world_hash
            })
    }
}

impl NativeAudit {
    fn proof_running(&mut self, session: &ObserverSession) -> Result<(), &'static str> {
        if session.quit_requested {
            self.refuse_period_proof("period_proof_quit");
            return Err("period_proof_quit");
        }
        Ok(())
    }

    pub(in crate::observer_io) fn proof_allows_next_source(&self) -> bool {
        matches!(self.proof, None | Some(Progress::Acknowledged { .. }))
    }

    pub(in crate::observer_io) fn live_known_close(&self, session: &ObserverSession) -> bool {
        session.viewed_tick > 0
            && self.recovery.is_none()
            && self
                .advance
                .as_ref()
                .and_then(|a| a.live_known_request(session))
                .is_some()
    }

    pub(crate) fn advance_request_id(&self, session: &ObserverSession) -> Option<u64> {
        self.advance
            .as_ref()
            .and_then(|a| a.live_known_request(session))
            .or_else(|| self.period_proof_receipt(session).map(|r| r.request_id))
    }

    pub(in crate::observer_io) fn installed_known(
        &mut self,
        session: &ObserverSession,
        snapshot: &ObserverEconomySnapshot,
        presentation_read_elapsed_ns: u64,
    ) -> Result<(), String> {
        if !self.live_known_close(session) || self.proof.is_some() {
            return Err("native ordinary presentation lacks its unique live close".into());
        }
        let binding = KnownBinding::from_snapshot(snapshot);
        if !binding.agrees(snapshot)
            || binding
                .hash
                .as_deref()
                .is_none_or(|h| super::canonical_digest(h).is_err())
            || binding
                .envelope
                .as_deref()
                .is_none_or(|h| super::canonical_digest(h).is_err())
            || !matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        {
            return Err(
                "native ordinary presentation is not the installed restricted boundary".into(),
            );
        }
        self.proof = Some(Progress::AwaitingFence(InstalledKnown {
            scope: self.scope.clone().ok_or("native ordinary scope absent")?,
            context: session.context(),
            binding,
            world_hash: session
                .world_hash
                .clone()
                .ok_or("native accepted world tail absent")?,
            presentation_read_elapsed_ns,
            revision: self.custody.revision,
            request_id: self
                .advance_request_id(session)
                .ok_or("native original Advance absent")?,
        }));
        Ok(())
    }

    pub(crate) fn request_period_proof(
        &mut self,
        session: &ObserverSession,
        sequence: u64,
    ) -> Result<(), &'static str> {
        self.proof_running(session)?;
        let Some(Progress::AwaitingFence(known)) = self.proof.as_ref() else {
            return Err("period_proof_not_awaiting_fence");
        };
        if sequence == 0
            || !known.matches(self, session)
            || session.playing
            || session.lifecycle_pending()
            || session.organizer_control_pending()
            || !matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        {
            return Err("period_proof_context_changed");
        }
        self.configuration
            .policy
            .verify()
            .map_err(|_| "period_proof_policy_changed")?;
        let Some(Progress::AwaitingFence(installed)) = self.proof.take() else {
            unreachable!("the same exclusive borrow admitted the installed witness");
        };
        self.proof = Some(Progress::Requested(Fence {
            installed,
            sequence,
        }));
        Ok(())
    }

    /// Do not acquire a new source while a stale blocking task still needs draining.
    pub(in crate::observer_io) fn proof_context_current(&self, session: &ObserverSession) -> bool {
        match &self.proof {
            Some(Progress::AwaitingFence(known)) => known.matches(self, session),
            Some(
                Progress::Requested(fence)
                | Progress::Reading(fence)
                | Progress::AwaitingJoin { fence, .. },
            ) => fence.installed.matches(self, session),
            Some(Progress::Refused { .. }) => false,
            Some(Progress::Published { .. }) => {
                self.period_proof_receipt(session).is_some()
                    && !session.playing
                    && !session.lifecycle_pending()
                    && matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
            }
            None | Some(Progress::Acknowledged { .. }) => true,
        }
    }

    pub(in crate::observer_io) fn proof_reading(&self, context: &ObservationContext) -> bool {
        matches!(&self.proof, Some(Progress::Reading(f)) if &f.installed.context == context)
    }

    pub(crate) fn refuse_period_proof(&mut self, reason: &'static str) {
        self.proof = self.proof.take().map(|progress| match progress {
            Progress::Requested(fence)
            | Progress::Reading(fence)
            | Progress::AwaitingJoin { fence, .. }
            | Progress::Published { fence, .. }
            | Progress::Acknowledged { fence, .. } => Progress::Refused { fence, reason },
            other => other,
        });
    }

    pub(in crate::observer_io) fn take_proof_work(
        &mut self,
        session: &ObserverSession,
        snapshot: Option<&ObserverEconomySnapshot>,
    ) -> Result<Option<(Work, InstalledKnown)>, String> {
        self.proof_running(session)?;
        let Some(Progress::Requested(fence)) = &self.proof else {
            return Ok(None);
        };
        if !fence.installed.matches(self, session)
            || snapshot.is_none_or(|s| !fence.installed.binding.agrees(s))
        {
            self.refuse_period_proof("period_proof_context_changed");
            return Err("native proof no longer names its actual installed frame".into());
        }
        let work = self
            .begin(session)?
            .ok_or("native proof lacks a new contiguous fold")?;
        let Some(Progress::Requested(fence)) = self.proof.take() else {
            unreachable!();
        };
        let installed = fence.installed.clone();
        self.proof = Some(Progress::Reading(fence));
        Ok(Some((work, installed)))
    }

    pub(in crate::observer_io) fn proof_read_finished(
        &mut self,
        session: &ObserverSession,
        candidate: Candidate,
        cursor: Option<ObserverMaterialCursor>,
    ) -> Result<(), String> {
        self.proof_running(session)?;
        let Some(Progress::Reading(fence)) = &self.proof else {
            return Err("native proof result lacks its original fence".into());
        };
        if !fence.installed.matches(self, session) || !fence.installed.agrees(&candidate) {
            self.refuse_period_proof("period_proof_context_changed");
            return Err(
                "native proof result differs from its installed frame or accepted revision".into(),
            );
        }
        let cursor = cursor
            .filter(|c| {
                c.completed_tick() == session.durable_tick && c.admission_handle().is_some()
            })
            .ok_or("native proof authenticated cursor or retained admission absent")?;
        let archive_accepted = self
            .advance
            .as_ref()
            .is_some_and(|a| a.archive_completed(session));
        bevy::log::info!(target: "babylon_client::timing",
            stage = "qualified_period_proof_candidate",
            tick = fence.installed.context.tick,
            runtime_epoch = fence.installed.scope.epoch,
            generation = fence.installed.context.generation,
            advance_request_id = fence.installed.request_id,
            control_sequence = fence.sequence,
            archive_accepted,
            archive_verified_tick = session.archive_verified_tick,
            "private proof candidate validated against its installed boundary");
        let Some(Progress::Reading(fence)) = self.proof.take() else {
            unreachable!();
        };
        self.proof = Some(Progress::AwaitingJoin {
            fence,
            candidate: Box::new(candidate),
            cursor: Box::new(cursor),
        });
        Ok(())
    }

    pub(in crate::observer_io) fn join_period_proof(
        &mut self,
        session: &ObserverSession,
        snapshot: Option<&ObserverEconomySnapshot>,
    ) -> Result<Option<ObserverMaterialCursor>, String> {
        self.proof_running(session)?;
        let Some(Progress::AwaitingJoin { fence, .. }) = &self.proof else {
            return Ok(None);
        };
        if !fence.installed.matches(self, session)
            || snapshot.is_none_or(|s| !fence.installed.binding.agrees(s))
        {
            self.refuse_period_proof("period_proof_context_changed");
            return Err("native proof join context changed".into());
        }
        if !self
            .advance
            .as_ref()
            .is_some_and(|a| a.archive_completed(session))
        {
            return Ok(None);
        }
        let Some(Progress::AwaitingJoin {
            fence,
            candidate,
            cursor,
        }) = self.proof.take()
        else {
            unreachable!();
        };
        let policy_sha256 = super::hex(
            &self
                .configuration
                .policy
                .scope(
                    fence.installed.scope.campaign,
                    fence.installed.scope.foundation,
                )
                .policy,
        );
        match self.commit(session, *candidate) {
            Ok(material_record_sha256) => {
                let known = &fence.installed;
                let receipt = PeriodProofReceipt {
                    campaign_id: known.binding.campaign.clone(),
                    scope_epoch: known.scope.epoch,
                    foundation_sha256: known.binding.foundation.clone(),
                    policy_sha256,
                    generation: known.context.generation,
                    tick: known.context.tick,
                    tick_content_hash: known.binding.hash.clone(),
                    world_hash: known.world_hash.clone(),
                    envelope_digest: known.binding.envelope.clone(),
                    request_id: known.request_id,
                    archive_verified_tick: session.archive_verified_tick,
                    material_record_sha256,
                };
                self.proof = Some(Progress::Published { fence, receipt });
                Ok(Some(*cursor))
            }
            Err(error) => {
                self.proof = Some(Progress::Refused {
                    fence,
                    reason: "period_proof_publication_failed",
                });
                Err(error)
            }
        }
    }

    pub(crate) fn period_proof_outcome(&self, sequence: u64) -> Option<Result<(), &'static str>> {
        match &self.proof {
            Some(Progress::Published { fence, .. }) if fence.sequence == sequence => Some(Ok(())),
            Some(Progress::Refused { fence, reason }) if fence.sequence == sequence => {
                Some(Err(reason))
            }
            _ => None,
        }
    }

    pub(crate) fn fence_reply_ready(
        &self,
        session: &ObserverSession,
        sequence: u64,
        snapshot: Option<&ObserverEconomySnapshot>,
    ) -> Result<(), &'static str> {
        if session.quit_requested {
            return Err("period_proof_quit");
        }
        if !matches!(&self.proof, Some(Progress::Published { fence, .. })
            if fence.sequence == sequence && snapshot.is_some_and(|s| fence.installed.binding.agrees(s)))
            || self.period_proof_receipt(session).is_none()
            || session.playing
            || session.lifecycle_pending()
            || session.advance_pending()
            || !matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        {
            return Err("period_proof_context_changed");
        }
        self.configuration
            .policy
            .verify()
            .map_err(|_| "period_proof_policy_changed")
    }

    /// Called only after the validated numbered reply enters the existing local
    /// transport queue. This attests local acceptance, never peer receipt.
    pub(crate) fn fence_reply_queued(&mut self, sequence: u64) {
        let Some(Progress::Published { fence, receipt }) = self.proof.take() else {
            unreachable!("an exclusive flush validated this published fence before try_send");
        };
        assert_eq!(
            fence.sequence, sequence,
            "the exclusive flush retains its original control"
        );
        self.proof = Some(Progress::Acknowledged { fence, receipt });
    }

    pub(crate) fn period_proof_receipt(
        &self,
        session: &ObserverSession,
    ) -> Option<&PeriodProofReceipt> {
        if session.quit_requested {
            return None;
        }
        match &self.proof {
            Some(
                Progress::Published { fence, receipt } | Progress::Acknowledged { fence, receipt },
            ) if session.accepts(&fence.installed.context)
                && self.scope.as_ref() == Some(&fence.installed.scope)
                && session.runtime_scope().map(|s| s.epoch) == Some(receipt.scope_epoch)
                && session.world_hash.as_deref() == Some(receipt.world_hash.as_str())
                && session.archive_verified_tick == receipt.archive_verified_tick
                && self.custody.revision == fence.installed.revision
                && self.boundary.as_ref().is_some_and(|b| b.agrees(session)) =>
            {
                Some(receipt)
            }
            _ => None,
        }
    }
}

#[cfg(test)]
pub(in crate::observer_io) mod tests {
    use super::super::recovery;
    use super::super::tests::Directory;
    use super::*;
    use crate::observer_io::runtime;
    use crate::observer_ui::ObserverFrame;
    use babylon_persistence::observer_reader::ObserverVisibility;
    use babylon_persistence::runtime_session::{
        OrganizerSnapshot, RuntimeSessionRequest, RuntimeSessionTail,
        RUNTIME_SESSION_PROTOCOL_VERSION,
    };
    use std::sync::Mutex;

    pub(crate) fn with_source(check: impl FnOnce(NativeAudit, ObserverSession, OrganizerSnapshot)) {
        let (_directory, audit, session, status) = recovery::tests::source();
        check(audit, session, status);
    }

    pub(in crate::observer_io) fn installed_close(
    ) -> (Directory, NativeAudit, ObserverSession, ObserverFrame) {
        let (directory, mut audit, mut session, _status) = recovery::tests::source();
        session.perspective = Perspective::PlayerKnowledge;
        let request_id = session.begin_advance().expect("admitted ordinary close");
        let request = RuntimeSessionRequest::Advance {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            scope: session.runtime_scope().expect("scope").clone(),
            request_id,
            expected_tail: RuntimeSessionTail {
                resolve_tick: 0,
                tick_content_hash: None,
                world_hash: None,
            },
        };
        audit.advance_sent(
            audit
                .prepare_advance(&session, &request)
                .expect("actual sent custody"),
        );
        assert!(session.acknowledge(request_id, 1, Some("ab".repeat(32))));
        session.world_hash = Some("cd".repeat(32));
        audit
            .advance_committed(&session, request_id)
            .expect("accepted Commit");
        let context = session.context();
        let known = ObserverEconomySnapshot {
            campaign_id: session.campaign.as_uuid().to_string(),
            resolve_tick: 1,
            foundation_digest: session.foundation_digest.clone().expect("foundation"),
            nominal_world_hash: None,
            tick_content_hash: session.content_hash.clone(),
            envelope_digest: Some("ef".repeat(32)),
            visibility: ObserverVisibility::KnownPreview,
            counties: Vec::new(),
            production: None,
        };
        let mut frame = ObserverFrame::default();
        assert!(runtime::install_observation(
            &mut session,
            &context,
            runtime::PreparedObservation::new(known),
            &mut frame,
            false
        ));
        audit
            .installed_known(
                &session,
                frame.for_session(&session).expect("actual installed frame"),
                17,
            )
            .expect("compact witness of actual successful install");
        (directory, audit, session, frame)
    }

    #[test]
    fn actual_known_install_waits_for_explicit_fence_and_rejects_duplicates() {
        let (directory, mut audit, session, frame) = installed_close();
        assert!(audit
            .take_proof_work(&session, frame.for_session(&session))
            .expect("no request")
            .is_none());
        assert!(audit.period_proof_receipt(&session).is_none());
        audit
            .request_period_proof(&session, 7)
            .expect("one admitted fence");
        assert!(audit.request_period_proof(&session, 8).is_err());
        let (work, installed) = audit
            .take_proof_work(&session, frame.for_session(&session))
            .expect("private task admission")
            .expect("one private task");
        assert_eq!(installed.presentation_read_elapsed_ns, 17);
        assert_eq!(work.audit.completed_tick(), 0);
        assert!(audit
            .take_proof_work(&session, frame.for_session(&session))
            .expect("already reading")
            .is_none());
        assert!(audit.period_proof_outcome(7).is_none());
        assert!(!directory.0.join("material-1.json").exists());
        assert!(!directory.0.join("advance-1.json").exists());
    }

    #[test]
    fn quit_is_terminal_before_any_period_proof_join() {
        for archive_first in [false, true] {
            let (directory, mut audit, mut session, frame) = installed_close();
            if archive_first {
                session.archive_verified_tick = 1;
                audit
                    .advance_archive_progress(&session)
                    .expect("matching Archive");
            }
            audit.request_period_proof(&session, 7).expect("fence");
            let (work, _) = audit
                .take_proof_work(&session, frame.for_session(&session))
                .expect("admitted read")
                .expect("requested work");
            drop(work);
            session.quit_requested = true;
            assert!(
                audit
                    .join_period_proof(&session, frame.for_session(&session))
                    .is_err(),
                "Quit must refuse before inspecting or committing any staged candidate"
            );
            assert_eq!(
                audit.period_proof_outcome(7),
                Some(Err("period_proof_quit"))
            );
            assert_eq!(
                audit.request_period_proof(&session, 8),
                Err("period_proof_quit")
            );
            assert!(audit
                .take_proof_work(&session, frame.for_session(&session))
                .is_err());
            assert!(!directory.0.join("material-1.json").exists());
            assert!(!directory.0.join("advance-1.json").exists());
        }
    }

    #[test]
    fn unbounded_player_play_keeps_the_existing_qualified_read_path() {
        let (_directory, mut audit, mut session, _status) = recovery::tests::source();
        session.perspective = Perspective::PlayerKnowledge;
        assert!(session.start_playback());
        let request_id = session.begin_advance().expect("ordinary unbounded Play");
        let request = RuntimeSessionRequest::Advance {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            scope: session.runtime_scope().expect("scope").clone(),
            request_id,
            expected_tail: RuntimeSessionTail {
                resolve_tick: 0,
                tick_content_hash: None,
                world_hash: None,
            },
        };
        audit.advance_sent(
            audit
                .prepare_advance(&session, &request)
                .expect("sent ordinary Play"),
        );
        assert!(session.acknowledge(request_id, 1, Some("ab".repeat(32))));
        session.world_hash = Some("cd".repeat(32));
        audit
            .advance_committed(&session, request_id)
            .expect("accepted ordinary Play commit");
        assert!(
            !audit.live_known_close(&session),
            "only the actual bounded Play witness may select early presentation"
        );
    }

    #[test]
    fn an_unacknowledged_fence_cannot_rekey_onto_an_old_published_source() {
        for action in ["arm", "advance", "reopen"] {
            let (_pending_directory, mut pending, _known_session, _frame) = installed_close();
            let (_directory, mut audit, mut session, _status) = recovery::tests::source();
            // Preserve an actual installed pending witness while presenting the
            // old published source. No completed audit or cursor is fabricated.
            audit.proof = pending.proof.take();
            match action {
                "arm" => assert!(
                    !audit.can_arm_play(&session),
                    "an unacknowledged fence must retain the source lock"
                ),
                "advance" => {
                    let request_id = session
                        .begin_advance()
                        .expect("old source remains ordinary Ready");
                    let request = RuntimeSessionRequest::Advance {
                        protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
                        scope: session.runtime_scope().expect("scope").clone(),
                        request_id,
                        expected_tail: RuntimeSessionTail {
                            resolve_tick: 0,
                            tick_content_hash: None,
                            world_hash: None,
                        },
                    };
                    assert!(audit.prepare_advance(&session, &request).is_err());
                }
                "reopen" => {
                    session
                        .queue_campaign(
                            babylon_persistence::runtime_session::RuntimeSessionTarget::Open {
                                campaign_id: session.campaign.as_uuid().to_string(),
                            },
                        )
                        .expect("old source may queue ordinary recovery");
                    let request = session.pending_switch_request().expect("queued recovery");
                    assert!(audit.stage_reopen(&session, &request).is_err());
                }
                _ => unreachable!(),
            }
        }
    }

    #[test]
    fn private_fence_refuses_changed_installed_identity_and_accepted_revision() {
        for fault in ["generation", "epoch", "marker", "envelope", "revision"] {
            let (_directory, mut audit, mut session, mut frame) = installed_close();
            audit
                .request_period_proof(&session, 7)
                .expect("admitted fence");
            match fault {
                "generation" => session.generation += 1,
                "epoch" => {
                    let previous = session.runtime_scope().expect("scope").clone();
                    session
                        .queue_campaign(
                            babylon_persistence::runtime_session::RuntimeSessionTarget::Open {
                                campaign_id: session.campaign.as_uuid().to_string(),
                            },
                        )
                        .expect("queued conflicting recovery");
                    let RuntimeSessionRequest::Switch { request_id, .. } =
                        session.pending_switch_request().expect("request")
                    else {
                        unreachable!();
                    };
                    session.switch_sent();
                    session
                        .switching(
                            request_id,
                            &previous,
                            babylon_persistence::runtime_session::RuntimeSessionScope {
                                epoch: previous.epoch + 1,
                                campaign_id: previous.campaign_id.clone(),
                            },
                        )
                        .expect("actual changed epoch");
                }
                "marker" => session.content_hash = Some("de".repeat(32)),
                "envelope" => {
                    frame.0.as_mut().expect("frame").envelope_digest = Some("de".repeat(32));
                }
                "revision" => audit.custody.revision += 1,
                _ => unreachable!(),
            }
            assert!(
                audit
                    .take_proof_work(&session, frame.for_session(&session))
                    .is_err(),
                "{fault}"
            );
            assert_eq!(
                audit.period_proof_outcome(7),
                Some(Err("period_proof_context_changed"))
            );
            assert_eq!(
                audit.audit.as_ref().expect("prior audit").completed_tick(),
                0
            );
            assert_eq!(audit.boundary.as_ref().expect("prior authority").tick, 0);
        }
    }

    #[test]
    fn early_ordinary_ready_never_authorizes_the_next_advance_or_reopen() {
        let (_directory, mut audit, mut session, _frame) = installed_close();
        session
            .queue_campaign(
                babylon_persistence::runtime_session::RuntimeSessionTarget::Open {
                    campaign_id: session.campaign.as_uuid().to_string(),
                },
            )
            .expect("ordinary ready may queue a request");
        let queued = session.pending_switch_request().expect("queued request");
        assert!(audit.stage_reopen(&session, &queued).is_err());
        // The original clock, published boundary and fold remain the source.
        assert!(audit.advance.is_some());
        assert_eq!(audit.boundary.as_ref().expect("prior source").tick, 0);
        let (_directory, mut audit, mut session, _frame) = installed_close();
        let (requests, receiver) = std::sync::mpsc::sync_channel(1);
        let (_sender, responses) = std::sync::mpsc::channel();
        let pipe = runtime::RuntimePipe {
            requests,
            responses: Mutex::new(responses),
        };
        assert!(runtime::send_advance(&pipe, &mut session, Some(&mut audit)).is_none());
        assert!(receiver.try_recv().is_err());
        assert!(audit.advance.is_some());
        assert_eq!(
            audit.audit.as_ref().expect("prior fold").completed_tick(),
            0
        );
    }
}
