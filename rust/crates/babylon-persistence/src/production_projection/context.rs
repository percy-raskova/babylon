//! Captured source context with native geographic scope and explicit missingness.

#[cfg(test)]
mod tests;

#[path = "context/rows.rs"]
mod rows;

pub(crate) use rows::attach_observed_context;
#[cfg(test)]
use rows::{checked_context, context_rows, subtotal};

#[cfg(test)]
use crate::observer_reader::ObserverVisibility;
#[cfg(test)]
use crate::production_observation::ProductionSnapshot;
#[cfg(test)]
use crate::ArchiveEvidenceClass;
