//! Elapsed wall time for acknowledged client lifecycle phases, never a forecast.
use crate::observer::{ObservationContext, ObserverSession, SessionPhase};
use babylon_persistence::identity::CampaignId;
use bevy::prelude::*;
use std::time::Duration;

#[derive(Clone, Debug, PartialEq, Eq)]
enum Operation {
    Opening {
        campaign: CampaignId,
        epoch: Option<u64>,
    },
    Advancing {
        campaign: CampaignId,
        request: u64,
        period: u64,
    },
    Reading(ObservationContext),
}
impl Operation {
    fn current(state: &ObserverSession) -> Option<Self> {
        if matches!(state.phase, SessionPhase::Failed | SessionPhase::Closed) {
            return None;
        }
        if state.advance_pending() || state.phase == SessionPhase::Advancing {
            let request = state.pending_advance_request()?;
            return state
                .durable_tick
                .checked_add(1)
                .map(|period| Self::Advancing {
                    campaign: state.campaign,
                    request,
                    period,
                });
        }
        if state.lifecycle_pending() || state.phase == SessionPhase::Connecting {
            return Some(Self::Opening {
                campaign: state.campaign,
                epoch: state.lifecycle_epoch(),
            });
        }
        (state.phase == SessionPhase::Loading).then(|| Self::Reading(state.context()))
    }
}

#[derive(Resource, Default)]
pub(crate) struct OperationProgress {
    operation: Option<Operation>,
    started: Duration,
    seconds: u64,
    stage: Option<babylon_persistence::runtime_session::RuntimeAdvanceStage>,
    hidden: bool,
}
impl OperationProgress {
    fn observe(&mut self, state: &ObserverSession, now: Duration) {
        self.hidden = state.quit_requested;
        let operation = Operation::current(state);
        if operation == self.operation {
            self.seconds = now.saturating_sub(self.started).as_secs();
        } else {
            self.stage = None;
            self.operation = operation;
            self.started = now;
            self.seconds = 0;
        }
    }
    pub(crate) fn report_stage(
        &mut self,
        session: &ObserverSession,
        request: u64,
        tick: u64,
        stage: babylon_persistence::runtime_session::RuntimeAdvanceStage,
        now: Duration,
    ) -> Result<(), String> {
        let prior = if Operation::current(session) == self.operation {
            self.stage
        } else {
            None
        };
        session.validate_advance_stage(request, tick, stage, prior)?;
        self.observe(session, now);
        self.stage = Some(stage);
        Ok(())
    }

    pub(crate) fn caption(&self) -> Option<String> {
        if self.hidden {
            return None;
        }
        let phase = match self.operation.as_ref()? {
            Operation::Opening { .. } => "Opening campaign".into(),
            Operation::Advancing { period, .. } => {
                use babylon_persistence::runtime_session::RuntimeAdvanceStage as Stage;
                match self.stage {
                    None => format!("Period {period} requested; awaiting commit"),
                    Some(stage) => {
                        let label = match stage {
                            Stage::PreparingCommitments => "Preparing commitments",
                            Stage::ResolvingEconomy => "Resolving economy",
                            Stage::PreparingStorage => "Preparing storage",
                            Stage::SavingPeriod => "Saving period",
                        };
                        format!("Period {period} · {label}")
                    }
                }
            }
            Operation::Reading(context) if context.tick == 0 => {
                "Loading opening observation".into()
            }
            Operation::Reading(context) => format!("Loading saved period {}", context.tick),
        };
        Some(format!("{phase} · {}s elapsed", self.seconds))
    }
}

pub(crate) fn track(
    state: Res<ObserverSession>,
    time: Res<Time<Real>>,
    mut progress: ResMut<OperationProgress>,
) {
    let operation = Operation::current(&state);
    let seconds = time.elapsed().saturating_sub(progress.started).as_secs();
    // Clock-only repaint must not rebuild the national economic projection.
    if state.quit_requested != progress.hidden
        || operation != progress.operation
        || (operation.is_some() && seconds != progress.seconds)
    {
        progress.observe(&state, time.elapsed());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn progress_distinguishes_open_commit_and_authenticated_read_without_advancing_time() {
        let mut state = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(7)));
        let mut progress = OperationProgress::default();
        progress.observe(&state, Duration::from_secs(10));
        progress.observe(&state, Duration::from_secs(22));
        assert_eq!(
            progress.caption().unwrap(),
            "Opening campaign · 12s elapsed"
        );
        state.ready(0, None);
        progress.observe(&state, Duration::from_secs(25));
        assert_eq!(
            progress.caption().unwrap(),
            "Loading opening observation · 0s elapsed"
        );
        assert!(state.installed(&state.context()));
        progress.observe(&state, Duration::from_secs(29));
        assert!(progress.caption().is_none());
        let request = state.begin_advance().unwrap();
        assert!(state.begin_advance().is_none());
        progress.observe(&state, Duration::from_secs(30));
        progress.observe(&state, Duration::from_secs(37));
        assert_eq!(
            progress.caption().unwrap(),
            "Period 1 requested; awaiting commit · 7s elapsed"
        );
        assert_eq!(state.durable_tick, 0);
        assert!(state.acknowledge(request, 1, Some("committed".into())));
        progress.observe(&state, Duration::from_secs(38));
        assert_eq!(
            progress.caption().unwrap(),
            "Loading saved period 1 · 0s elapsed"
        );
        assert!(state.begin_advance().is_none());
        assert!(state.installed(&state.context()));
        progress.observe(&state, Duration::from_secs(40));
        assert!(progress.caption().is_none());
    }
    #[test]
    fn real_stage_before_tracker_preserves_elapsed_and_clears_on_ack_or_failure() {
        use babylon_persistence::runtime_session::RuntimeAdvanceStage as Stage;
        for terminal in ["commit", "failure", "reopen"] {
            let mut state = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(7)));
            state.ready(3, None);
            let context = state.context();
            assert!(state.installed(&context));
            let request = state.begin_advance().unwrap();
            let mut progress = OperationProgress::default();
            // First stage arrives before track has seen the pending request.
            progress
                .report_stage(
                    &state,
                    request,
                    4,
                    Stage::PreparingCommitments,
                    Duration::from_secs(30),
                )
                .unwrap();
            progress
                .report_stage(
                    &state,
                    request,
                    4,
                    Stage::ResolvingEconomy,
                    Duration::from_secs(37),
                )
                .unwrap();
            assert_eq!(
                progress.caption().unwrap(),
                "Period 4 · Resolving economy · 7s elapsed"
            );
            let before = progress.caption();
            assert!(progress
                .report_stage(
                    &state,
                    request,
                    4,
                    Stage::ResolvingEconomy,
                    Duration::from_secs(38)
                )
                .is_err());
            assert_eq!(
                progress.caption(),
                before,
                "duplicate refusal leaves presentation unchanged"
            );
            match terminal {
                "commit" => assert!(state.acknowledge(request, 4, Some("hash".into()))),
                "failure" => state.fail("transport uncertainty".into()),
                "reopen" => state.ready(3, None),
                _ => unreachable!(),
            }
            progress.observe(&state, Duration::from_secs(39));
            assert_eq!(progress.stage, None);
            if terminal == "failure" {
                assert!(progress.caption().is_none());
                assert!(state.advance_pending());
            } else {
                assert!(progress
                    .caption()
                    .unwrap()
                    .starts_with("Loading saved period"));
            }
        }
    }

    #[test]
    fn failed_or_replaced_read_has_no_stale_elapsed_progress() {
        let mut state = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(7)));
        state.ready(2, None);
        let mut progress = OperationProgress::default();
        progress.observe(&state, Duration::from_secs(5));
        state.inspect_tick(1);
        progress.observe(&state, Duration::from_secs(25));
        assert_eq!(
            progress.caption().unwrap(),
            "Loading saved period 1 · 0s elapsed"
        );
        state.fail("Read refused".into());
        progress.observe(&state, Duration::from_secs(30));
        assert!(progress.caption().is_none());
    }
}
