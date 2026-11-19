//! The interface tour's presentation, rendering and local preference owners.

#[path = "interface_tour_preferences.rs"]
mod preferences;
#[path = "interface_tour_runtime.rs"]
mod runtime;
#[cfg(test)]
#[path = "interface_tour_tests.rs"]
mod tests;
#[path = "interface_tour_view.rs"]
mod view;

pub(super) use runtime::install;
pub(crate) use runtime::{settings_button, TourRoot};
