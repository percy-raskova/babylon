//! Native campaign catalog and read-only comparison of separately committed worlds.

mod aggregate;

#[path = "campaign_browser/state.rs"]
mod state;

#[allow(unused_imports)]
use state::{
    button, button_visible, collect, commands, compare_staffing, comparison_availability,
    comparison_cohort_ids, comparison_controls, comparison_text, dispatch_button, input,
    keyboard_button, matches_comparison, open_selected_campaign, paint, paint_buttons,
    parse_campaign, reader, receipt_text, refresh_scope, request_catalog, scoped_comparison_text,
    setup, staffing_difference, sync_focus_targets, text, write_comparison_cohort, BrowserButton,
    BrowserButtonAppearance, BrowserFocusTargets, BrowserPaintInput, BrowserPaintScope,
    BrowserScope, CampaignBrowserState, CatalogTask, CatalogText, ComparisonReadingBody,
    ComparisonTask, ComparisonText,
};
#[allow(unused_imports)]
pub(crate) use state::{preference_path, write_preference, ComparisonPanel};
pub use state::{CampaignBrowserCommand, CampaignBrowserPlugin, ComparisonSection};

#[allow(unused_imports)]
use crate::decision_surface::{DeclaredSurface, SurfaceId};
#[allow(unused_imports)]
use crate::observer::{ObservationContext, ObserverSession, Perspective};
#[allow(unused_imports)]
use crate::observer_controls::{availability, inspection_availability, ControlAvailability};
#[allow(unused_imports)]
use crate::observer_focus::{
    ObserverFocusPolicy, ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate,
    ObserverKeyboardClaim,
};
#[allow(unused_imports)]
use crate::observer_io::{ObserverSet, RuntimePipe, LAUNCHER_REQUIRED};
#[allow(unused_imports)]
use crate::observer_opening::OpeningPresentation;
#[allow(unused_imports)]
use crate::observer_theme as theme;
#[allow(unused_imports)]
use crate::observer_ui::{
    ObserverCampaignCatalog, ObserverCommand, ObserverFontRole, ObserverFrame, ObserverUiState,
};
#[allow(unused_imports)]
use crate::workforce::{validate_staffing_period, StaffingIdentity};
#[allow(unused_imports)]
use babylon_persistence::{
    identity::CampaignId,
    observer_reader::CampaignSummary,
    observer_reader::ObserverEconomyReader,
    observer_reader::ObserverEconomySnapshot,
    observer_reader::ObserverVisibility,
    production_observation::{ProductionSite, ProductionSnapshot, ProductionStaffingAccount},
};
#[allow(unused_imports)]
use bevy::ecs::{query::QueryData, system::SystemParam};
#[allow(unused_imports)]
use bevy::input_focus::tab_navigation::TabGroup;
#[allow(unused_imports)]
use bevy::tasks::{block_on, AsyncComputeTaskPool, Task};
#[allow(unused_imports)]
use std::collections::BTreeSet;
#[allow(unused_imports)]
use std::fmt::Write as _;
#[allow(unused_imports)]
use std::fs::{self, OpenOptions};
#[allow(unused_imports)]
use std::io::Write;
#[allow(unused_imports)]
use std::path::{Path, PathBuf};

#[allow(unused_imports)]
use bevy::prelude::*;
