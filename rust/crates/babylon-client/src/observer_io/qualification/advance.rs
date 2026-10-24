//! Clock custody stays with the live client, outside detached reader candidates.

use super::MaterialAudit;
use super::{Configuration, NativeAudit, Record};
use crate::observer::{ObserverSession, SessionPhase};
use babylon_kernel::content_digest;
use babylon_persistence::runtime_session::{
    RuntimeSessionRequest, RuntimeSessionScope, RuntimeSessionTail,
    RUNTIME_SESSION_PROTOCOL_VERSION,
};
use serde::Serialize;
use std::time::Instant;

pub(in crate::observer_io) struct Pending {
    request_id: u64,
    scope: RuntimeSessionScope,
    foundation: String,
    expected: RuntimeSessionTail,
    started: Instant,
    committed: Option<Committed>,
    archive_elapsed_ns: Option<u64>,
}

struct Committed {
    tail: RuntimeSessionTail,
    started: Instant,
    advance_elapsed_ns: u64,
}

#[derive(Serialize)]
struct Receipt<'a> {
    version: u8,
    scope: &'static str,
    clock: &'static str,
    advance_measurement: &'static str,
    archive_measurement: &'static str,
    request_id: u64,
    runtime_scope: &'a RuntimeSessionScope,
    foundation_sha256: &'a str,
    policy_sha256: String,
    expected_tail: &'a RuntimeSessionTail,
    committed_tail: &'a RuntimeSessionTail,
    advance_elapsed_ns: u64,
    archive_elapsed_ns: u64,
    material_record_sha256: String,
}

fn interval(started: Instant, completed: Instant) -> Result<u64, String> {
    completed
        .checked_duration_since(started)
        .and_then(|duration| u64::try_from(duration.as_nanos()).ok())
        .ok_or_else(|| "native advance clock interval is invalid".into())
}

impl Pending {
    fn matches_scope(&self, session: &ObserverSession) -> bool {
        session.runtime_scope() == Some(&self.scope)
            && self.scope.campaign_id.as_deref()
                == Some(session.campaign.as_uuid().to_string().as_str())
            && session.foundation_digest.as_deref() == Some(&self.foundation)
    }

    pub(super) fn receipt(
        &self,
        configuration: &Configuration,
        session: &ObserverSession,
        record: &Record,
        material_bytes: &[u8],
    ) -> Result<Vec<u8>, String> {
        let committed = self
            .committed
            .as_ref()
            .ok_or("native timing publication lacks accepted Commit")?;
        let archive_elapsed_ns = self
            .archive_elapsed_ns
            .ok_or("native timing publication lacks accepted Archive completion")?;
        if !self.matches_scope(session)
            || configuration.campaign != session.campaign
            || record.tick != committed.tail.resolve_tick
            || record.tick_content_hash != committed.tail.tick_content_hash
            || record.runtime_epoch != self.scope.epoch
            || record.facts.is_none()
            || record.opening.is_some()
            || session.durable_tick != record.tick
            || session.archive_verified_tick != record.tick
            || session.content_hash != record.tick_content_hash
            || !matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        {
            return Err(
                "native timing publication differs from its authenticated material boundary".into(),
            );
        }
        configuration.policy.verify().map_err(|e| e.to_string())?;
        let receipt = Receipt {
            version: 1,
            scope: "native_enqueue_commit_archive_timing_v1",
            clock: "monotonic",
            advance_measurement: "client_enqueue_to_accepted_commit",
            archive_measurement: "accepted_commit_to_accepted_archive_completion",
            request_id: self.request_id,
            runtime_scope: &self.scope,
            foundation_sha256: &self.foundation,
            policy_sha256: super::hex(
                &configuration
                    .policy
                    .scope(
                        configuration.campaign,
                        super::canonical_digest(&self.foundation).map_err(|e| e.to_string())?,
                    )
                    .policy,
            ),
            expected_tail: &self.expected,
            committed_tail: &committed.tail,
            advance_elapsed_ns: committed.advance_elapsed_ns,
            archive_elapsed_ns,
            material_record_sha256: super::hex(&content_digest::sha256_of(material_bytes)),
        };
        let mut bytes =
            serde_json::to_vec(&receipt).map_err(|_| "native advance timing encoding failed")?;
        bytes.push(b'\n');
        Ok(bytes)
    }
}

impl NativeAudit {
    pub(in crate::observer_io) fn prepare_advance(
        &self,
        session: &ObserverSession,
        request: &RuntimeSessionRequest,
    ) -> Result<Pending, String> {
        let RuntimeSessionRequest::Advance {
            protocol_version,
            scope,
            request_id,
            expected_tail,
        } = request
        else {
            return Err("native timing requires an ordinary Advance request".into());
        };
        self.configuration
            .policy
            .verify()
            .map_err(|e| e.to_string())?;
        let bound = self
            .scope
            .as_ref()
            .ok_or("native timing source scope absent")?;
        let source = self
            .boundary
            .as_ref()
            .ok_or("native timing authenticated source boundary absent")?;
        if self.advance.is_some()
            || self.recovery.is_some()
            || *protocol_version != RUNTIME_SESSION_PROTOCOL_VERSION
            || session.campaign != self.configuration.campaign
            || session.runtime_scope() != Some(scope)
            || scope.epoch != bound.epoch
            || !source.agrees(session)
            || self.audit.as_ref().map(MaterialAudit::completed_tick) != Some(source.tick)
            || session.phase != SessionPhase::Advancing
            || session.pending_advance_request() != Some(*request_id)
            || session.archive_verified_tick != source.tick
            || expected_tail.resolve_tick != source.tick
            || expected_tail.tick_content_hash != session.content_hash
            || source
                .tick
                .checked_add(1)
                .is_none_or(|tick| tick > self.configuration.policy.periods())
        {
            return Err(
                "native timing request differs from its authenticated source boundary".into(),
            );
        }
        Ok(Pending {
            request_id: *request_id,
            scope: scope.clone(),
            foundation: super::hex(&bound.foundation),
            expected: expected_tail.clone(),
            started: Instant::now(),
            committed: None,
            archive_elapsed_ns: None,
        })
    }

    pub(in crate::observer_io) fn advance_sent(&mut self, pending: Pending) {
        self.advance = Some(pending);
    }

    pub(in crate::observer_io) fn advance_committed(
        &mut self,
        session: &ObserverSession,
        request_id: u64,
    ) -> Result<(), String> {
        let completed = Instant::now();
        let pending = self
            .advance
            .as_mut()
            .ok_or("native Commit lacks a sent Advance clock")?;
        if pending.committed.is_some()
            || request_id != pending.request_id
            || !pending.matches_scope(session)
            || pending.expected.resolve_tick.checked_add(1) != Some(session.durable_tick)
            || session.advance_pending()
            || session
                .content_hash
                .as_deref()
                .is_none_or(|hash| super::canonical_digest(hash).is_err())
        {
            return Err("native Commit clock differs from its sent request".into());
        }
        let advance_elapsed_ns = interval(pending.started, completed)?;
        pending.committed = Some(Committed {
            tail: RuntimeSessionTail {
                resolve_tick: session.durable_tick,
                tick_content_hash: session.content_hash.clone(),
            },
            started: completed,
            advance_elapsed_ns,
        });
        Ok(())
    }

    pub(in crate::observer_io) fn advance_archive_progress(
        &mut self,
        session: &ObserverSession,
    ) -> Result<(), String> {
        let completed = Instant::now();
        let Some(pending) = &mut self.advance else {
            return Ok(());
        };
        if !pending.matches_scope(session) {
            return Err("native Archive clock scope changed".into());
        }
        let Some(committed) = &pending.committed else {
            // The previous period's Archive progress is not a Commit receipt.
            return Ok(());
        };
        if session.durable_tick != committed.tail.resolve_tick
            || session.content_hash != committed.tail.tick_content_hash
        {
            return Err("native Archive clock differs from accepted Commit".into());
        }
        if session.archive_verified_tick == committed.tail.resolve_tick
            && pending.archive_elapsed_ns.is_none()
        {
            pending.archive_elapsed_ns = Some(interval(committed.started, completed)?);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::super::recovery::tests as recovery_tests;
    use super::super::NativeAudit;
    use crate::observer::{ObserverSession, SessionPhase};
    use crate::observer_io::runtime;
    use crate::observer_io::tests as io_tests;

    use crate::observer_io::RuntimePipe;
    use crate::observer_ui::{ObserverCommand, ObserverUiState};
    use crate::organizer::OrganizerClient;
    use babylon_persistence::runtime_session::{
        RuntimeSessionRequest, RuntimeSessionResponse, RuntimeSessionTail,
        RUNTIME_SESSION_PROTOCOL_VERSION,
    };
    use bevy::prelude::*;
    use std::time::Duration;

    #[test]
    fn ordinary_manual_and_playback_paths_own_commit_and_archive_clock_custody() {
        for automated in [false, true] {
            let (_directory, audit, session, _status) = recovery_tests::source();
            let (mut app, requests, responses) = io_tests::quit_app();
            let scope = session
                .runtime_scope()
                .expect("the fixture runtime scope exists")
                .clone();
            app.insert_resource(audit)
                .insert_resource(session)
                .init_resource::<OrganizerClient>();
            if automated {
                app.add_systems(Update, runtime::playback.after(runtime::handle_commands));
                app.world_mut()
                    .resource_mut::<Time>()
                    .advance_by(Duration::from_secs(1));
            }
            app.world_mut()
                .resource_mut::<ObserverUiState>()
                .splash_visible = false;
            app.world_mut()
                .resource_mut::<Messages<ObserverCommand>>()
                .write(if automated {
                    ObserverCommand::TogglePlay
                } else {
                    ObserverCommand::Step
                });
            app.update();
            let RuntimeSessionRequest::Advance { request_id, .. } = requests
                .try_recv()
                .expect("the producer sends before this receive")
            else {
                panic!("ordinary client must send Advance");
            };
            assert!(app.world().resource::<NativeAudit>().advance.is_some());
            responses
                .send(Ok(RuntimeSessionResponse::ArchiveProgress {
                    request_id: None,
                    scope: scope.clone(),
                    durable_tick: 0,
                    verified_tick: 0,
                }))
                .expect("the receiver stays alive for the send");
            app.update();
            assert!(app
                .world()
                .resource::<NativeAudit>()
                .advance
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .committed
                .is_none());
            responses
                .send(Ok(RuntimeSessionResponse::Committed {
                    request_id,
                    scope: scope.clone(),
                    tail: RuntimeSessionTail {
                        resolve_tick: 1,
                        tick_content_hash: Some("ab".repeat(32)),
                    },
                }))
                .expect("the receiver stays alive for the send");
            app.update();
            assert_eq!(
                app.world().resource::<ObserverSession>().phase,
                SessionPhase::Loading
            );
            let audit = app.world().resource::<NativeAudit>();
            assert!(audit
                .advance
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .committed
                .is_some());
            assert!(audit
                .advance
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .archive_elapsed_ns
                .is_none());
            responses
                .send(Ok(RuntimeSessionResponse::ArchiveProgress {
                    request_id: None,
                    scope,
                    durable_tick: 1,
                    verified_tick: 1,
                }))
                .expect("the receiver stays alive for the send");
            app.update();
            assert!(app
                .world()
                .resource::<NativeAudit>()
                .advance
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .archive_elapsed_ns
                .is_some());
        }
    }

    #[test]
    fn failed_enqueue_retains_no_clock_or_completed_timing_record() {
        let (directory, audit, session, _status) = recovery_tests::source();
        let (mut app, _requests, _responses) = io_tests::quit_app();
        let scope = session
            .runtime_scope()
            .expect("the fixture runtime scope exists")
            .clone();
        app.insert_resource(audit).insert_resource(session);
        app.world()
            .resource::<RuntimePipe>()
            .requests
            .try_send(RuntimeSessionRequest::Stop {
                protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
                scope,
                request_id: 999,
            })
            .expect("the bounded channel has capacity for the fixture message");
        app.world_mut()
            .resource_mut::<Messages<ObserverCommand>>()
            .write(ObserverCommand::Step);
        app.update();
        assert_eq!(
            app.world().resource::<ObserverSession>().phase,
            SessionPhase::Failed
        );
        assert!(app.world().resource::<NativeAudit>().advance.is_none());
        assert!(!directory.0.join("advance-1.json").exists());
    }

    #[test]
    fn commit_and_archive_clocks_require_the_exact_sent_request() {
        let (_directory, mut audit, mut session, _status) = recovery_tests::source();
        let request_id = session
            .begin_advance()
            .expect("the session begins the authored advance");
        let request = RuntimeSessionRequest::Advance {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            scope: session
                .runtime_scope()
                .expect("the fixture runtime scope exists")
                .clone(),
            request_id,
            expected_tail: RuntimeSessionTail {
                resolve_tick: 0,
                tick_content_hash: None,
            },
        };
        let pending = audit
            .prepare_advance(&session, &request)
            .expect("the session prepares the authored advance");
        assert!(audit.advance.is_none(), "failed enqueue cannot own a clock");
        audit.advance = Some(pending);
        assert!(audit.prepare_advance(&session, &request).is_err());
        audit
            .advance_archive_progress(&session)
            .expect("the fixture call `advance_archive_progress` succeeds for the authored inputs");
        assert!(audit
            .advance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .archive_elapsed_ns
            .is_none());
        assert!(session.acknowledge(request_id, 1, Some("ab".repeat(32))));
        assert!(audit.advance_committed(&session, request_id + 1).is_err());
        assert!(audit
            .advance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .committed
            .is_none());
        audit
            .advance_committed(&session, request_id)
            .expect("the fixture call `advance_committed` succeeds for the authored inputs");
        assert!(audit.advance_committed(&session, request_id).is_err());
        audit
            .advance_archive_progress(&session)
            .expect("the fixture call `advance_archive_progress` succeeds for the authored inputs");
        assert!(audit
            .advance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .archive_elapsed_ns
            .is_none());
        session.archive_verified_tick = 1;
        audit
            .advance_archive_progress(&session)
            .expect("the fixture call `advance_archive_progress` succeeds for the authored inputs");
        let original = audit
            .advance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .archive_elapsed_ns;
        assert!(original.is_some());
        audit
            .advance_archive_progress(&session)
            .expect("the fixture call `advance_archive_progress` succeeds for the authored inputs");
        assert_eq!(
            audit
                .advance
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .archive_elapsed_ns,
            original
        );
        session.content_hash = Some("cd".repeat(32));
        assert!(audit.advance_archive_progress(&session).is_err());
    }

    #[test]
    fn unadmitted_source_and_changed_scope_cannot_start_or_complete_a_clock() {
        let (_directory, mut audit, mut session, _status) = recovery_tests::source();
        let request_id = session
            .begin_advance()
            .expect("the session begins the authored advance");
        let request = RuntimeSessionRequest::Advance {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            scope: session
                .runtime_scope()
                .expect("the fixture runtime scope exists")
                .clone(),
            request_id,
            expected_tail: RuntimeSessionTail {
                resolve_tick: 0,
                tick_content_hash: Some("ab".repeat(32)),
            },
        };
        assert!(audit.prepare_advance(&session, &request).is_err());
        let mut request = request;
        if let RuntimeSessionRequest::Advance { expected_tail, .. } = &mut request {
            expected_tail.tick_content_hash = None;
        }
        audit.advance = Some(
            audit
                .prepare_advance(&session, &request)
                .expect("the session prepares the authored advance"),
        );
        assert!(session.acknowledge(request_id, 1, Some("ab".repeat(32))));
        session.foundation_digest = Some("cd".repeat(32));
        assert!(audit.advance_committed(&session, request_id).is_err());
        assert!(audit
            .advance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .committed
            .is_none());
    }
}
