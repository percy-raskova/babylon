//! Bounded ordered receipt draining with coherent committed progress.

#[cfg(test)]
mod live_tests;

#[path = "worker/sweep.rs"]
mod sweep;

pub(crate) use sweep::sweep;
#[cfg(test)]
use sweep::sweep_locked;

#[cfg(test)]
use super::publication;
