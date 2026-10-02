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
        period: u64,
    },
    Reading(ObservationContext),
}
impl Operation {
    fn current(state: &ObserverSession) -> Option<Self> {
        if state.quit_requested
            || matches!(state.phase, SessionPhase::Failed | SessionPhase::Closed)
        {
            return None;
        }
        if state.advance_pending() || state.phase == SessionPhase::Advancing {
            return state
                .durable_tick
                .checked_add(1)
                .map(|period| Self::Advancing {
                    campaign: state.campaign,
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
}
impl OperationProgress {
    fn observe(&mut self, state: &ObserverSession, now: Duration) {
        let operation = Operation::current(state);
        if operation != self.operation {
            self.operation = operation;
            self.started = now;
            self.seconds = 0;
        } else {
            self.seconds = now.saturating_sub(self.started).as_secs();
        }
    }
    pub(crate) fn caption(&self) -> Option<String> {
        let phase = match self.operation.as_ref()? {
            Operation::Opening { .. } => "Opening campaign".into(),
            Operation::Advancing { period, .. } => format!("Advancing and saving period {period}"),
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
    if operation != progress.operation || (operation.is_some() && seconds != progress.seconds) {
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
            "Advancing and saving period 1 · 7s elapsed"
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
