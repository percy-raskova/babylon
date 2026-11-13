//! Stable identities for restoring actual native focus and reading offsets.

use crate::observer::ObserverSession;
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_ui::ObserverUiState;
use crate::ui::dossier_navigation::ArchiveNavigation;
use babylon_persistence::ArchivePageRef;
use bevy::ecs::system::SystemParam;
use bevy::input_focus::{FocusCause, InputFocus};
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

use crate::observer_focus::{self, FocusTree, ObserverFocusPolicy};
use crate::observer_ui::ObserverCommand;
use crate::organizer::navigation::OrganizerFocus;
use crate::production::{ProductionCommand, ProductionPage, ProductionReadingSection};

/// Stable reading regions survive body repaint and entity replacement.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ReadingRegion {
    OrganizerScene,
    OrganizerWorkspace,
    OrganizerDispatch,
    OrganizerInspector,
    ProductionPanel,
    ProductionReading,
    ObserverInspector,
    Archive,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum ProductionFocus {
    Open,
    Map,
    Flat,
    Details,
    Reading(ProductionReadingSection),
    Cohorts(usize),
    Relationships(usize),
    Competitors(usize),
    Process(String),
    Back,
    Focus(String),
    Select(String),
}

impl ProductionFocus {
    pub(crate) fn from_command(command: &ProductionCommand) -> Self {
        match command {
            ProductionCommand::Open => Self::Open,
            ProductionCommand::Map => Self::Map,
            ProductionCommand::Flat => Self::Flat,
            ProductionCommand::Details => Self::Details,
            ProductionCommand::Reading(section) => Self::Reading(*section),
            ProductionCommand::Page { kind, page, .. } => match kind {
                ProductionPage::Cohorts => Self::Cohorts(*page),
                ProductionPage::Relationships => Self::Relationships(*page),
                ProductionPage::Competitors => Self::Competitors(*page),
            },
            ProductionCommand::Process { process_id, .. } => Self::Process(process_id.clone()),
            ProductionCommand::Back => Self::Back,
            ProductionCommand::Focus { site_id, .. } => Self::Focus(site_id.clone()),
            ProductionCommand::Select { site_id, .. } => Self::Select(site_id.clone()),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum ArchiveFocus {
    Subject(ArchivePageRef),
    Back,
    More,
    First,
    Details,
    Technical,
}

/// An action identity contains no authority context and is rechecked against the focus tree.
#[derive(Component, Clone, Debug, PartialEq, Eq)]
pub(crate) enum NavigationFocus {
    Organizer(OrganizerFocus),
    Observer(ObserverCommand),
    Production(ProductionFocus),
    Archive(ArchiveFocus),
    Reading(ReadingRegion),
    Back,
    Home,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct SavedPosition {
    focus: Option<NavigationFocus>,
    entity: Option<Entity>,
    offsets: Vec<(ReadingRegion, Vec2)>,
}

#[derive(SystemParam)]
pub(crate) struct PositionCapture<'w, 's> {
    focus: Option<Res<'w, InputFocus>>,
    keys: Query<'w, 's, &'static NavigationFocus>,
    readings: Query<
        'w,
        's,
        (
            &'static ReadingRegion,
            &'static ScrollPosition,
            &'static ComputedNode,
        ),
    >,
}

impl PositionCapture<'_, '_> {
    pub(crate) fn capture(&self) -> SavedPosition {
        let entity = self.focus.as_ref().and_then(|focus| focus.get());
        SavedPosition {
            focus: entity
                .and_then(|entity| self.keys.get(entity).ok())
                .cloned(),
            entity,
            offsets: self
                .readings
                .iter()
                .filter_map(|(region, position, computed)| {
                    (!computed.is_empty() && position.0.is_finite())
                        .then_some((*region, position.0))
                })
                .collect(),
        }
    }
}

#[derive(Resource, Default)]
pub(crate) struct PendingPosition(Option<PositionRestore>);

struct PositionRestore {
    saved: SavedPosition,
    frames: u8,
}

impl PendingPosition {
    pub(crate) const fn is_restoring(&self) -> bool {
        self.0.is_some()
    }

    pub(crate) fn begin(&mut self, saved: SavedPosition) {
        self.0 = Some(PositionRestore { saved, frames: 0 });
    }

    pub(crate) fn cancel(&mut self) {
        self.0 = None;
    }
}

/// The focus owner cancels its obsolete reveal request after the offsets have been restored.
#[derive(Event)]
pub(crate) struct NavigationPositionRestored;

pub(crate) fn sync_readings(
    session: Res<ObserverSession>,
    ui: Res<ObserverUiState>,
    mut targets: Query<&mut ObserverFocusTarget, With<ReadingRegion>>,
) {
    for mut target in &mut targets {
        let mut next = target.clone();
        next.context = Some(session.context());
        next.available = !ui.menu_open && !ui.splash_visible && !ui.comparison_open;
        target.set_if_neq(next);
    }
}

/// Current admitted destinations for a saved focus identity or its safe fallback.
#[derive(SystemParam)]
pub(crate) struct PositionTargets<'w, 's> {
    tree: FocusTree<'w, 's>,
    policy: Res<'w, ObserverFocusPolicy>,
    keys: Query<'w, 's, (Entity, &'static NavigationFocus)>,
    windows: Query<'w, 's, Entity, With<PrimaryWindow>>,
}

/// Runs in Last, after owner resets, layout, and ordinary focus reveal.
pub(crate) fn restore_position(
    mut pending: ResMut<PendingPosition>,
    mut focus: ResMut<InputFocus>,
    targets: PositionTargets,
    mut readings: Query<(&ReadingRegion, &ComputedNode, &mut ScrollPosition)>,
    mut commands: Commands,
    archive: Option<Res<ArchiveNavigation>>,
) {
    let PositionTargets {
        tree,
        policy,
        keys,
        windows,
    } = targets;
    let Some(restore) = pending.0.as_mut() else {
        return;
    };
    if archive
        .as_ref()
        .is_some_and(|archive| archive.is_restoring())
    {
        return;
    }
    if archive
        .as_ref()
        .is_some_and(|archive| archive.restoration_failed())
    {
        restore.saved = SavedPosition::default();
    }
    restore.frames = restore.frames.saturating_add(1);
    // The next Prepare pass must observe the restored screen and its modal policy first.
    if restore.frames < 2 {
        return;
    }
    let target = restore
        .saved
        .focus
        .as_ref()
        .and_then(|saved| {
            keys.iter().find_map(|(entity, key)| {
                (key == saved && tree.tabbable(entity, &policy)).then_some(entity)
            })
        })
        .or_else(|| {
            restore
                .saved
                .entity
                .filter(|entity| tree.tabbable(*entity, &policy))
        });
    if target.is_none() && restore.saved.focus.is_some() && restore.frames < 8 {
        return;
    }
    let target = target.or_else(|| {
        keys.iter().find_map(|(entity, key)| {
            (matches!(key, NavigationFocus::Reading(_)) && tree.tabbable(entity, &policy))
                .then_some(entity)
        })
    });
    if let Some(entity) = target.or_else(|| windows.single().ok()) {
        focus.set(entity, FocusCause::Navigated);
    }
    for (region, computed, mut position) in &mut readings {
        if computed.is_empty() {
            continue;
        }
        if let Some((_, offset)) = restore
            .saved
            .offsets
            .iter()
            .find(|(saved, _)| saved == region)
        {
            if let Some(maximum) = observer_focus::scroll_max(computed) {
                position.0 = offset.clamp(Vec2::ZERO, maximum);
            }
        }
    }
    commands.trigger(NavigationPositionRestored);
    pending.0 = None;
}

#[cfg(test)]
#[path = "position_tests.rs"]
mod tests;
