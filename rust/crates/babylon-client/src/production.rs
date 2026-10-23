//! A read-only production scene: exact receipts, cohort columns and actual lots.
//! County aggregates have no invented geographic placement.

#[cfg(test)]
mod tests;

pub(crate) mod maintenance;

pub(crate) mod navigation;

mod readings;

#[path = "production/view.rs"]
mod view;

#[allow(unused_imports)]
use view::{
    block, button_node, focus_eligibility, freight_markers, inputs, keyboard_activate, orbit_input,
    page_controls, paint_buttons, paint_disclosure, paint_labels, paint_readings, paint_scene,
    panel_contents, production_command_context, queue_production_button, rail, readings_contents,
    rebuild, rebuild_county_cohorts, rebuild_dependencies, reset_inspector_scroll, setup,
    setup_panel, setup_readings_panel, spawn_county_cohorts, spawn_freight,
    spawn_freight_participants, spawn_routes, spawn_site_label, spawn_sites, text,
    visible_dependency_directions, ButtonVisuals, CameraParts, InspectorScrollScope,
    InspectorScrolls, LabelFilter, LabelParts, LeaderFilter, LeaderParts, PanelParts,
    ProductionBrief, ProductionButton, ProductionDependencies, ProductionDetailGroup,
    ProductionDetails, ProductionDisclosureLabel, ProductionFocusOwners, ProductionFreightReading,
    ProductionGeometry, ProductionGeometryContext, ProductionInputContext, ProductionLabel,
    ProductionLabels, ProductionLeader, ProductionObservation, ProductionOrbit, ProductionPanel,
    ProductionPointer, ProductionReadingBody, ProductionReadingHeadline, ProductionReadingSubject,
    ProductionScene, ProductionUi, ReadingFocusTargets, ReadingMarkers, ReadingText, SceneGeometry,
};
#[allow(unused_imports)]
pub(crate) use view::{button, ProductionCountyCohorts};
pub use view::{
    PrimaryView, ProductionCamera, ProductionCommand, ProductionNavigation, ProductionPage,
    ProductionPlugin, ProductionReadingSection,
};

#[allow(unused_imports)]
use crate::decision_surface::{DeclaredSurface, SurfaceId};
#[allow(unused_imports)]
use crate::observer::{ObservationContext, ObserverSession};
#[allow(unused_imports)]
use crate::observer_focus::{
    ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate, ObserverKeyboardClaim,
};
#[allow(unused_imports)]
use crate::observer_io::ObserverSet;
#[allow(unused_imports)]
use crate::observer_theme as theme;
#[allow(unused_imports)]
use crate::observer_ui::{
    grouped, ObserverFeedback, ObserverFrame, ObserverUiState, ObserverViewport,
};
#[allow(unused_imports)]
use crate::production_brief::{
    committed_plan_status, dependency_flow_summary, dependency_sites, describe_brief,
    describe_overview, DependencyDirection,
};
#[allow(unused_imports)]
use crate::production_freight::{account_brief, competitor_sites, shared_accounts};
#[allow(unused_imports)]
use crate::production_layout::{path_point, place_label, relation_path, ProductionLayout};
#[allow(unused_imports)]
use babylon_persistence::{
    production_observation::ProductionSite, production_observation::ProductionSnapshot,
};
#[allow(unused_imports)]
use bevy::camera::{visibility::RenderLayers, ScalingMode, Viewport};
#[allow(unused_imports)]
use bevy::ecs::system::SystemParam;
#[allow(unused_imports)]
use bevy::input_focus::tab_navigation::TabGroup;
#[allow(unused_imports)]
use bevy::light::CascadeShadowConfigBuilder;
#[allow(unused_imports)]
use bevy::window::PrimaryWindow;
#[allow(unused_imports)]
use navigation::{
    focus_opening, invalidate_navigation, navigate, readings_panel_visible, sync_world_county,
    ProductionControlAvailability,
};
#[allow(unused_imports)]
use readings::{describe, reading_headline};

#[allow(unused_imports)]
use bevy::prelude::*;
