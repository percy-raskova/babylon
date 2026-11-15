//! Subscribe while this rail is waiting for durable journal coverage.
use super::state::Scope;
use babylon_persistence::money_journal::{JournalError, PeriodWindow};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use bevy::prelude::warn;
use bevy::tasks::{self, IoTaskPool, Task};
use std::sync::mpsc::{self, Sender, TryRecvError};
use std::task::Poll;
use std::time::Duration;

#[derive(Default)]
pub(super) enum Publication {
    #[default]
    Idle,
    Waiting {
        // Dropping the rail's subscription closes the confined connection on the next socket interval.
        _interest: Sender<()>,
        task: Task<Result<bool, JournalError>>,
    },
    Finished,
}

impl Publication {
    pub(super) fn poll(&mut self, scope: &Scope) -> Poll<bool> {
        if matches!(self, Self::Idle) {
            let (interest, receiver) = mpsc::channel();
            let campaign = scope.context.campaign;
            let last = scope.context.tick;
            let generation = scope.context.generation;
            let first = scope.periods.window(last).map_or(last, |prior| prior.first);
            let task = IoTaskPool::get().spawn(async move {
                let reader =
                    ObserverEconomyReader::from_observer_env().map_err(JournalError::Observer)?;
                let mut listener =
                    reader.watch_journal_periods(campaign, PeriodWindow { first, last })?;
                while let Err(TryRecvError::Empty) = receiver.try_recv() {
                    if listener.wait(Duration::from_millis(250))? {
                        bevy::log::info!(target: "babylon_client::timing",
                            stage = "journal_coverage_wake", campaign = %campaign.as_uuid(),
                            tick = last, generation, first, "Journal listener confirmed scoped coverage");
                        return Ok(true);
                    }
                }
                Ok(false)
            });
            *self = Self::Waiting {
                _interest: interest,
                task,
            };
        }
        let Self::Waiting { task, .. } = self else {
            return Poll::Ready(false);
        };
        let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(task)) else {
            return Poll::Pending;
        };
        *self = Self::Finished;
        match result {
            Ok(covered) => Poll::Ready(covered),
            Err(error) => {
                warn!(%error, "Journal notification unavailable, retrying the frame-bound report");
                Poll::Ready(false)
            }
        }
    }
}
