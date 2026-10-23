//! Bounded, capability-scoped history. Charts never recompute a transition.

mod delivery_groups;

#[path = "observer_history/panel.rs"]
mod panel;

pub use panel::ObserverHistoryPlugin;
#[allow(unused_imports)]
use panel::{
    apply_history_action, bar_height, button_availability, fetch, fetch_history, focus_eligibility,
    history_button_context, history_buttons_need_paint, history_control_visibility, input,
    keyboard_activate, label, paint, paint_buttons, paint_log, reconcile_delivery_expansion, setup,
    spawn_delivery_entry, spawn_event_entry, spawn_log_entries, update, ChangedHistoryButtons,
    HistoryButton, HistoryButtonAppearance, HistoryFocusOwners, HistoryHint, HistoryInput,
    HistoryKeyboardActions, HistoryPanel, HistoryScope, HistoryState, HistoryTask, LogPanel,
    LogPresentation, LOG_ENTRIES,
};

#[allow(unused_imports)]
use crate::decision_surface::{DeclaredSurface, SurfaceId};
#[allow(unused_imports)]
use crate::observer::{ObservationContext, ObserverSession, Perspective};
#[allow(unused_imports)]
use crate::observer_controls::{inspection_availability, ControlAvailability};
#[allow(unused_imports)]
use crate::observer_focus::{ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate};
#[allow(unused_imports)]
use crate::observer_io::ObserverSet;
#[allow(unused_imports)]
use crate::observer_layout::ObserverRegion;
#[allow(unused_imports)]
use crate::observer_theme as theme;
#[allow(unused_imports)]
use crate::observer_ui::{grouped, ObserverFeedback, ObserverFrame, ObserverUiState};
#[allow(unused_imports)]
use crate::production::navigation::readings_panel_visible;
#[allow(unused_imports)]
use crate::production::{PrimaryView, ProductionCommand, ProductionNavigation};
#[allow(unused_imports)]
use crate::ui::dossier_card::DossierRefresh;
#[allow(unused_imports)]
use babylon_persistence::{
    observer_reader::{
        ObserverEconomyReader, ProductionHistoryTarget, ProductionOutputPoint as PeriodOutput,
    },
    production_observation::ProductionEvent,
};
#[allow(unused_imports)]
use bevy::ecs::{query::QueryData, system::SystemParam};
#[allow(unused_imports)]
use bevy::input_focus::tab_navigation::TabGroup;
#[allow(unused_imports)]
use bevy::tasks::{block_on, AsyncComputeTaskPool, Task};
#[allow(unused_imports)]
use delivery_groups::{
    delivery_log_entries, DeliveryGroup, DeliveryGroupKey, DeliveryLog, DeliveryLogEntry,
};

#[allow(unused_imports)]
use bevy::prelude::*;
