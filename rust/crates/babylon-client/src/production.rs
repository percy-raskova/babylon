//! A read-only production scene: exact receipts, cohort columns and actual lots.
//! County aggregates have no invented geographic placement.

#[cfg(test)]
pub(crate) mod tests;

pub(crate) mod maintenance;

pub(crate) mod navigation;

mod readings;

#[path = "production/view.rs"]
mod view;

pub(crate) use view::{button, ProductionCountyCohorts};
pub use view::{
    PrimaryView, ProductionCamera, ProductionCommand, ProductionNavigation, ProductionPage,
    ProductionPlugin, ProductionReadingSection,
};
use view::{ProductionObservation, ProductionUi};
