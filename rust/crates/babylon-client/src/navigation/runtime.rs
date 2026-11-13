//! Capture accepted visits and restore presentation through the current reader owners.

use bevy::ecs::system::SystemParam;
use bevy::input_focus::InputFocus;
use bevy::prelude::*;
use controls::ModalAdmission;

use crate::atlas::CountyAtlas;
use crate::map::SelectedCounty;
use crate::observer::{ObserverSession, SessionPhase};
use crate::observer_focus::ObserverFocusSystems;
use crate::observer_io::ObserverSet;
use crate::observer_map3d::MapOrbit;
use crate::observer_ui::{ObserverFeedback, ObserverFrame, ObserverUiState};
use crate::organizer::{OrganizerClient, OrganizerInspector};
use crate::production::{PrimaryView, ProductionNavigation};
use crate::ui::dossier_card::DossierRefresh;
use crate::ui::dossier_navigation::{ArchiveCapture, ArchiveDetails, ArchiveNavigation};

use super::controls;
use super::history::{NavigationHistory, Route, ViewedPeriod, Visit};
use super::position::{self, PendingPosition, PositionCapture, SavedPosition};
use super::NavigationAction;

#[derive(SystemParam)]
struct Capture<'w, 's> {
    session: Res<'w, ObserverSession>,
    ui: Res<'w, ObserverUiState>,
    view: Res<'w, PrimaryView>,
    atlas: Res<'w, CountyAtlas>,
    selected: Res<'w, SelectedCounty>,
    organizer: Res<'w, OrganizerClient>,
    production: Option<Res<'w, ProductionNavigation>>,
    orbit: Option<Res<'w, MapOrbit>>,
    archive: ArchiveCapture<'w>,
    position: PositionCapture<'w, 's>,
}

impl Capture<'_, '_> {
    fn visit(&self) -> Visit {
        Visit {
            route: Route {
                period: ViewedPeriod::for_session(&self.session),
                primary: *self.view,
                county: self
                    .selected
                    .0
                    .and_then(|index| self.atlas.county(index))
                    .map(|county| county.fips.into()),
                organizer: (*self.view == PrimaryView::Organizer)
                    .then(|| self.organizer.navigation_route(self.session.viewed_tick)),
                production: self
                    .production
                    .as_ref()
                    .filter(|navigation| {
                        *self.view == PrimaryView::Production
                            || (*self.view == PrimaryView::Map
                                && navigation.selected_site.is_some())
                    })
                    .map(|navigation| navigation.navigation_route()),
                archive: self
                    .ui
                    .archive_open
                    .then(|| self.archive.capture())
                    .flatten(),
                archive_open: self.ui.archive_open,
                disclosure: self.ui.disclosure,
                history_open: self.ui.history_open,
                evidence_open: self.ui.evidence_open,
                economic_details_open: self.ui.economic_details_open,
            },
            lens: self.ui.lens.clone(),
            roads: self.ui.road_layer,
            sector: self.ui.network_sector,
            orbit: self.orbit.as_deref().cloned(),
            position: self.position.capture(),
        }
    }
}

fn capture_origin(
    capture: Capture,
    mut history: ResMut<NavigationHistory>,
    mut position: ResMut<PendingPosition>,
    mut commands: Commands,
) {
    if history.reconcile(&capture.session) {
        position.cancel();
        commands.queue(|world: &mut World| {
            if let Some(mut archive) = world.get_resource_mut::<ArchiveNavigation>() {
                archive.cancel();
            }
        });
    }
    if capture.session.organizer_enabled {
        history.capture_origin(capture.visit());
    }
}

fn settle(
    capture: Capture,
    mut history: ResMut<NavigationHistory>,
    mut position: ResMut<PendingPosition>,
    mut commands: Commands,
) {
    if history.has_accepted_route() {
        position.cancel();
        commands.queue(|world: &mut World| {
            if let Some(mut archive) = world.get_resource_mut::<ArchiveNavigation>() {
                archive.cancel();
            }
        });
    }
    history.settle(&capture.visit());
}

#[derive(SystemParam)]
struct Owners<'w> {
    session: ResMut<'w, ObserverSession>,
    ui: ResMut<'w, ObserverUiState>,
    view: ResMut<'w, PrimaryView>,
    client: ResMut<'w, OrganizerClient>,
    production: Option<ResMut<'w, ProductionNavigation>>,
    atlas: Res<'w, CountyAtlas>,
    selected: ResMut<'w, SelectedCounty>,
    frame: Option<Res<'w, ObserverFrame>>,
    refresh: Option<ResMut<'w, DossierRefresh>>,
    orbit: Option<ResMut<'w, MapOrbit>>,
    archive: Option<ResMut<'w, ArchiveNavigation>>,
    details: ArchiveDetails<'w>,
    feedback: Option<ResMut<'w, ObserverFeedback>>,
    focus: ResMut<'w, InputFocus>,
    time: Res<'w, Time>,
}

impl Owners<'_> {
    fn status(&mut self, message: &'static str) {
        if *self.view == PrimaryView::Organizer {
            self.client.message = message.into();
        }
        if let Some(feedback) = self.feedback.as_deref_mut() {
            feedback.reject(message, self.time.elapsed_secs_f64());
        }
    }

    fn close_detail(&mut self) -> bool {
        if *self.view == PrimaryView::Organizer
            && self.client.inspector != OrganizerInspector::Closed
        {
            self.client.close_navigation_detail(&mut self.focus);
        } else if self.ui.disclosure.take().is_some()
            || (self.ui.archive_open && self.details.close_top())
        {
        } else if self
            .production
            .as_ref()
            .is_some_and(|navigation| navigation.details_open)
            && *self.view == PrimaryView::Production
        {
            if let Some(navigation) = self.production.as_deref_mut() {
                navigation.details_open = false;
            }
        } else if self.ui.economic_details_open {
            self.ui.economic_details_open = false;
        } else if self.ui.evidence_open {
            self.ui.evidence_open = false;
        } else if self.ui.history_open {
            self.ui.history_open = false;
        } else {
            return false;
        }
        true
    }

    fn is_home(&self) -> bool {
        *self.view == PrimaryView::Organizer
            && self.session.viewed_tick == self.session.durable_tick
            && self.client.inspector == OrganizerInspector::Closed
            && !self.ui.archive_open
            && !self.ui.history_open
            && self.ui.disclosure.is_none()
            && !self.ui.evidence_open
            && !self.ui.economic_details_open
    }

    fn restore(&mut self, visit: &Visit) -> bool {
        *self.view = visit.route.primary;
        self.ui.archive_open = visit.route.archive_open;
        self.ui.disclosure = visit.route.disclosure;
        self.ui.history_open = visit.route.history_open;
        self.ui.evidence_open = visit.route.evidence_open;
        self.ui.economic_details_open = visit.route.economic_details_open;
        self.ui.lens.clone_from(&visit.lens);
        self.ui.road_layer = visit.roads;
        self.ui.network_sector = visit.sector;
        self.selected.0 = visit
            .route
            .county
            .as_deref()
            .and_then(|county| self.atlas.index_of_fips(county));
        if visit.route.county.is_some() && self.selected.0.is_none() {
            self.ui.archive_open = false;
            *self.view = PrimaryView::Map;
            self.status("That county is unavailable. Returned to World.");
            return true;
        }
        let Some(period) = visit.route.period.resolve(&self.session) else {
            self.ui.archive_open = false;
            *self.view = PrimaryView::Organizer;
            self.client.organizing_home();
            self.status("That period is unavailable. Returned to organizing.");
            return true;
        };
        if self.session.viewed_tick != period {
            self.client.navigation_context_changed();
            if matches!(
                self.session.phase,
                SessionPhase::Failed | SessionPhase::Closed
            ) {
                self.ui.archive_open = false;
                *self.view = PrimaryView::Organizer;
                self.client.organizing_home();
                self.status("The previous period is unavailable until the campaign connection is reconciled.");
                return true;
            }
            if self.session.advance_pending() || self.session.lifecycle_pending() {
                self.status(
                    "The previous period will reopen after the current operation finishes.",
                );
                return false;
            }
            self.session.inspect_tick(period);
            if let Some(refresh) = self.refresh.as_deref_mut() {
                refresh.bump();
            }
        }
        if let Some(route) = &visit.route.organizer {
            if self.session.phase == SessionPhase::Loading
                && self.client.body_for(&self.session).is_none()
            {
                return false;
            }
            self.client.restore_navigation(route, &self.session);
        } else if visit.route.primary == PrimaryView::Organizer {
            self.client.organizing_home();
        }
        if let (Some(navigation), Some(route)) =
            (self.production.as_deref_mut(), &visit.route.production)
        {
            let snapshot = self
                .frame
                .as_ref()
                .and_then(|frame| frame.for_session(&self.session))
                .and_then(|frame| frame.production.as_ref());
            if snapshot.is_none() && self.session.phase == SessionPhase::Loading {
                return false;
            }
            if let Some(message) = navigation.restore_navigation(route, snapshot, &self.session) {
                self.status(message);
            }
        }
        if let (Some(orbit), Some(saved)) = (self.orbit.as_deref_mut(), &visit.orbit) {
            orbit.clone_from(saved);
        }
        if let (Some(archive), Some(route)) = (self.archive.as_deref_mut(), &visit.route.archive) {
            archive.begin(route.clone());
        }
        true
    }
}

fn actions(
    mut requests: MessageReader<NavigationAction>,
    mut owners: Owners,
    mut history: ResMut<NavigationHistory>,
    mut position: ResMut<PendingPosition>,
    modal: ModalAdmission,
) {
    for action in requests.read() {
        if !owners.session.organizer_enabled
            || owners.ui.menu_open
            || owners.ui.splash_visible
            || owners.ui.comparison_open
            || !modal.allows()
        {
            continue;
        }
        owners.session.pause_playback();
        position.cancel();
        if let Some(archive) = owners.archive.as_deref_mut() {
            archive.cancel();
        }
        match action {
            NavigationAction::Back => {
                if owners.close_detail() {
                    history.closed_detail();
                } else if !history.can_go_back() {
                    owners.status("There is no previous view in this campaign.");
                } else if let Some(visit) = history.back() {
                    history.restore = Some(visit);
                }
            }
            NavigationAction::Home => {
                // Home supersedes a historical return waiting for the current operation.
                history.restore = None;
                if owners.is_home() {
                    continue;
                }
                let Some(mut visit) = history.origin.clone() else {
                    continue;
                };
                history.home_origin();
                visit.route = Route {
                    period: ViewedPeriod::Live,
                    primary: PrimaryView::Organizer,
                    county: Some("26163".into()),
                    organizer: None,
                    production: None,
                    archive: None,
                    archive_open: false,
                    disclosure: None,
                    history_open: false,
                    evidence_open: false,
                    economic_details_open: false,
                };
                visit.position = SavedPosition::default();
                owners.client.organizing_home();
                history.restore = Some(visit);
            }
        }
    }
    resume(&mut owners, &mut history, &mut position);
}

fn resume(owners: &mut Owners, history: &mut NavigationHistory, position: &mut PendingPosition) {
    let Some(visit) = history.restore.take() else {
        return;
    };
    if owners.restore(&visit) {
        position.begin(visit.position);
    } else {
        history.restore = Some(visit);
    }
}

fn continue_restore(
    mut owners: Owners,
    mut history: ResMut<NavigationHistory>,
    mut position: ResMut<PendingPosition>,
) {
    if history.reconcile(&owners.session) {
        position.cancel();
        if let Some(archive) = owners.archive.as_deref_mut() {
            archive.cancel();
        }
        return;
    }
    resume(&mut owners, &mut history, &mut position);
}

pub(crate) struct NavigationPlugin;

impl Plugin for NavigationPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<NavigationHistory>()
            .init_resource::<PendingPosition>()
            .add_message::<NavigationAction>()
            .add_systems(
                PreUpdate,
                (controls::sync_targets, position::sync_readings)
                    .in_set(ObserverFocusSystems::Eligibility),
            )
            .add_systems(Update, capture_origin.before(ObserverSet::Input))
            .add_systems(
                Update,
                controls::keyboard
                    .before(crate::observer_ui::keyboard)
                    .before(ObserverSet::Input),
            )
            .add_systems(
                Update,
                (controls::pointer, actions)
                    .chain()
                    .in_set(ObserverSet::Input),
            )
            .add_systems(
                Update,
                continue_restore
                    .after(ObserverSet::Receive)
                    .before(ObserverSet::Install),
            )
            .add_systems(Update, settle.after(ObserverSet::Paint))
            .add_systems(Update, controls::paint_buttons.in_set(ObserverSet::Paint))
            .add_systems(Last, position::restore_position)
            .add_observer(controls::keyboard_activate);
    }
}
