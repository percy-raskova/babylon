//! A read-only production scene: exact receipts, cohort columns and actual lots.
//! County aggregates have no invented geographic placement.

#[cfg(test)]
mod tests;

pub(crate) mod maintenance;

pub(crate) mod navigation;

mod readings;

#[path = "production/view.rs"]
mod view;

pub(crate) use view::{button, ProductionCountyCohorts};
#[cfg(test)]
use view::{
    button_node, focus_eligibility, freight_markers, inputs, keyboard_activate, orbit_input,
    paint_disclosure, paint_labels, paint_readings, paint_scene, rebuild_county_cohorts,
    rebuild_dependencies, reset_inspector_scroll, setup, setup_readings_panel, ProductionBrief,
    ProductionButton, ProductionDependencies, ProductionDetailGroup, ProductionDetails,
    ProductionDisclosureLabel, ProductionFreightReading, ProductionLabel, ProductionLeader,
    ProductionOrbit, ProductionPanel, ProductionReadingBody, ProductionReadingHeadline,
    ProductionReadingSubject,
};
pub use view::{
    PrimaryView, ProductionCamera, ProductionCommand, ProductionNavigation, ProductionPage,
    ProductionPlugin, ProductionReadingSection,
};
use view::{ProductionObservation, ProductionUi};

#[cfg(test)]
use crate::observer::ObserverSession;
#[cfg(test)]
use crate::observer_focus::{
    ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate, ObserverKeyboardClaim,
};
#[cfg(test)]
use crate::observer_ui::{ObserverFeedback, ObserverFrame, ObserverUiState, ObserverViewport};
#[cfg(test)]
use crate::production_brief::{dependency_sites, DependencyDirection};
#[cfg(test)]
use crate::production_layout::{place_label, ProductionLayout};
#[cfg(test)]
use babylon_persistence::production_observation::{ProductionSite, ProductionSnapshot};
#[cfg(test)]
use bevy::input_focus::tab_navigation::TabGroup;
#[cfg(test)]
use bevy::window::PrimaryWindow;
#[cfg(test)]
use navigation::{focus_opening, invalidate_navigation, navigate, sync_world_county};
#[cfg(test)]
use readings::{describe, reading_headline};

#[cfg(test)]
use bevy::prelude::*;
