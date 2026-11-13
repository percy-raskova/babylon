//! Seven explanatory callouts over the current authenticated organizer interface.

use std::path::PathBuf;

use bevy::ecs::system::SystemParam;
use bevy::input_focus::{FocusCause, InputFocus, InputFocusSystems};
use bevy::prelude::*;
use bevy::ui::UiSystems;
use bevy::window::PrimaryWindow;

use super::{preferences, view};
use crate::navigation::position::PendingPosition;
use crate::navigation::NavigationAction;
use crate::observer::{ObserverSession, SessionPhase};
use crate::observer_focus::{
    FocusTree, ObserverFocusPolicy, ObserverFocusSystems, ObserverFocusTarget,
    ObserverKeyboardActivate, ObserverKeyboardClaim,
};
use crate::observer_io::ObserverSet;
use crate::observer_opening::{OpeningPresentation, OpeningStage};
use crate::observer_ui::ObserverUiState;
use crate::organizer::{workspace, OrganizerClient, OrganizerInspector};
use crate::production::PrimaryView;
use crate::ui::Interaction;
use preferences::Outcome;
use uuid::Uuid;

/// The shell includes this existing presentation modal in its focus policy.
#[derive(Component)]
pub(crate) struct TourRoot;

#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum TourControl {
    Previous,
    Next,
    Skip,
    Replay,
}

#[derive(Resource)]
pub(super) struct InterfaceTour {
    pub(super) preference: Result<PathBuf, String>,
    pub(super) outcome: Option<Outcome>,
    pub(super) campaign: Option<Uuid>,
    pub(super) step: Option<usize>,
    pub(super) replay_requested: bool,
    pub(super) home_requested: bool,
    pub(super) save_error: Option<String>,
    pub(super) return_focus: Option<Entity>,
    pub(super) restore_focus: bool,
}

impl Default for InterfaceTour {
    fn default() -> Self {
        let preference = preferences::path();
        let outcome = preference
            .as_deref()
            .ok()
            .and_then(|path| preferences::read(path).ok().flatten());
        Self {
            preference,
            outcome,
            campaign: None,
            step: None,
            replay_requested: false,
            home_requested: false,
            save_error: None,
            return_focus: None,
            restore_focus: false,
        }
    }
}

impl InterfaceTour {
    fn finish(&mut self, outcome: Outcome) {
        self.outcome = Some(outcome);
        self.step = None;
        self.replay_requested = false;
        self.home_requested = false;
        self.save_error = match &self.preference {
            Ok(path) => preferences::write(path, outcome).err(),
            Err(error) => Some(error.clone()),
        };
        if let Some(error) = &self.save_error {
            warn!("{error}");
        }
    }
}

#[derive(SystemParam)]
struct TourScope<'w> {
    session: ResMut<'w, ObserverSession>,
    client: Res<'w, OrganizerClient>,
    ui: ResMut<'w, ObserverUiState>,
    primary: Res<'w, PrimaryView>,
    opening: Option<Res<'w, OpeningPresentation>>,
}

impl TourScope<'_> {
    fn replay_available(&self) -> bool {
        self.session.organizer_enabled
            && matches!(
                self.session.phase,
                SessionPhase::Ready | SessionPhase::Complete
            )
            && !self.session.quit_requested
            && !self.session.lifecycle_pending()
            && !self.session.advance_pending()
            && !self.session.organizer_control_pending()
            && self.client.pending.is_none()
            && self.client.outbox.is_none()
            && !self.client.status_due
            && self
                .opening
                .as_deref()
                .is_none_or(|opening| opening.stage == OpeningStage::Game)
    }

    fn ready(&self) -> bool {
        self.replay_available()
            && self.session.viewed_tick == self.session.durable_tick
            && self.client.status_refusal(&self.session).is_none()
            && workspace::resources(&self.client, &self.session).is_some()
    }

    fn unobstructed(&self) -> bool {
        *self.primary == PrimaryView::Organizer
            && !self.ui.menu_open
            && !self.ui.splash_visible
            && !self.ui.comparison_open
            && !self.ui.archive_open
            && !self.ui.history_open
            && self.ui.disclosure.is_none()
            && self.client.inspector == OrganizerInspector::Closed
            && self
                .opening
                .as_deref()
                .is_none_or(|opening| opening.stage == OpeningStage::Game)
    }
}

/// Runs before shell focus admission so the first visible frame is shielded.
fn synchronize(
    mut scope: TourScope,
    mut tour: ResMut<InterfaceTour>,
    mut roots: Query<&mut Node, With<TourRoot>>,
    mut controls: Query<(&TourControl, &mut ObserverFocusTarget)>,
    focus: Res<InputFocus>,
    mut navigation: MessageWriter<NavigationAction>,
    position: Option<Res<PendingPosition>>,
) {
    let campaign = *scope.session.campaign.as_uuid();
    if tour.campaign != Some(campaign) {
        tour.campaign = Some(campaign);
        tour.step = None;
        tour.replay_requested = false;
        tour.home_requested = false;
        tour.return_focus = None;
        tour.restore_focus = false;
    }
    let ready = scope.ready();
    let available = ready
        && scope.unobstructed()
        && position
            .as_deref()
            .is_none_or(|position| !position.is_restoring());
    // Settings closes in the activating frame. On this next admission pass,
    // the shell clears its modal before the shared Home handler reads this.
    if tour.replay_requested
        && !tour.home_requested
        && !available
        && !scope.ui.menu_open
        && !scope.ui.splash_visible
        && !scope.ui.comparison_open
    {
        navigation.write(NavigationAction::Home);
        tour.home_requested = true;
    }
    if available && (tour.replay_requested || (tour.outcome.is_none() && tour.step.is_none())) {
        tour.step = Some(0);
        tour.replay_requested = false;
        tour.home_requested = false;
        tour.return_focus = focus.get();
    }
    let active = available && tour.step.is_some();
    if scope.ui.interface_tour_open && !active && tour.step.is_none() {
        tour.restore_focus = true;
    }
    if active && scope.session.playing {
        scope.session.pause_playback();
    }
    if scope.ui.interface_tour_open != active {
        scope.ui.interface_tour_open = active;
    }
    for mut root in &mut roots {
        let display = if active { Display::Flex } else { Display::None };
        if root.display != display {
            root.display = display;
        }
    }
    for (control, mut target) in &mut controls {
        let mut next = target.clone();
        next.context = Some(scope.session.context());
        next.available = if *control == TourControl::Replay {
            scope.replay_available()
                && scope.ui.menu_open
                && !scope.ui.splash_visible
                && !scope.ui.comparison_open
        } else {
            active && (*control != TourControl::Previous || tour.step != Some(0))
        };
        target.set_if_neq(next);
    }
}

/// The shared modal stack restores UI targets; also preserve prior world focus.
fn restore_focus(
    mut tour: ResMut<InterfaceTour>,
    policy: Res<ObserverFocusPolicy>,
    tree: FocusTree,
    windows: Query<(), With<PrimaryWindow>>,
    mut focus: ResMut<InputFocus>,
) {
    if !tour.restore_focus || policy.modal.is_some() {
        return;
    }
    tour.restore_focus = false;
    if let Some(entity) = tour.return_focus.take() {
        if windows.contains(entity) || tree.tabbable(entity, &policy) {
            focus.set(entity, FocusCause::Navigated);
        }
    }
}

fn activate(control: TourControl, scope: &mut TourScope, tour: &mut InterfaceTour) {
    if control == TourControl::Replay {
        if scope.replay_available()
            && scope.ui.menu_open
            && !scope.ui.splash_visible
            && !scope.ui.comparison_open
        {
            tour.replay_requested = true;
            tour.home_requested = false;
            scope.ui.menu_open = false;
            scope.session.pause_playback();
        }
        return;
    }
    if !scope.ui.interface_tour_open || !scope.ready() || !scope.unobstructed() {
        return;
    }
    let Some(step) = tour.step else { return };
    match control {
        TourControl::Previous => tour.step = Some(step.saturating_sub(1)),
        TourControl::Next if step + 1 < view::STEP_COUNT => tour.step = Some(step + 1),
        TourControl::Next => {
            tour.finish(Outcome::Completed);
        }
        TourControl::Skip => {
            tour.finish(Outcome::Skipped);
        }
        TourControl::Replay => {}
    }
}

fn pointer_controls(
    controls: Query<(&Interaction, &TourControl), Changed<Interaction>>,
    mut scope: TourScope,
    mut tour: ResMut<InterfaceTour>,
) {
    for (interaction, control) in &controls {
        if *interaction == Interaction::Pressed {
            activate(*control, &mut scope, &mut tour);
        }
    }
}

fn keyboard_control(
    event: On<ObserverKeyboardActivate>,
    controls: Query<(&TourControl, &ObserverFocusTarget)>,
    mut scope: TourScope,
    mut tour: ResMut<InterfaceTour>,
) {
    let Ok((control, target)) = controls.get(event.entity) else {
        return;
    };
    if target.available && event.context == Some(scope.session.context()) {
        activate(*control, &mut scope, &mut tour);
    }
}

fn escape(
    keys: Res<ButtonInput<KeyCode>>,
    mut scope: TourScope,
    mut tour: ResMut<InterfaceTour>,
    mut claim: ResMut<ObserverKeyboardClaim>,
) {
    if scope.ui.interface_tour_open && keys.just_pressed(KeyCode::Escape) {
        claim.claim(KeyCode::Escape);
        activate(TourControl::Skip, &mut scope, &mut tour);
    }
}

pub(crate) fn settings_button(parent: &mut ChildSpawnerCommands) {
    view::control(parent, "Replay interface tour", TourControl::Replay);
}

pub(crate) fn install(app: &mut App) {
    app.init_resource::<InterfaceTour>()
        .add_systems(Startup, view::spawn)
        .add_systems(
            PreUpdate,
            synchronize.before(ObserverFocusSystems::Eligibility),
        )
        .add_systems(
            PreUpdate,
            restore_focus
                .after(ObserverFocusSystems::Prepare)
                .before(InputFocusSystems::Dispatch),
        )
        .add_systems(
            Update,
            (pointer_controls, escape)
                .chain()
                .in_set(ObserverSet::Input)
                .before(crate::observer_ui::keyboard),
        )
        .add_systems(Update, view::paint.in_set(ObserverSet::Paint))
        .add_systems(PostUpdate, view::position.after(UiSystems::Layout))
        .add_observer(keyboard_control);
}
