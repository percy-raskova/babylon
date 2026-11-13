//! Visible shared navigation and keyboard admission without gameplay commands.

use crate::navigation::NavigationRegion as NavigationGroup;
use bevy::ecs::system::SystemParam;
use bevy::prelude::*;

use crate::observer::ObserverSession;
use crate::observer_focus::{
    FocusTree, ObserverFocusPolicy, ObserverFocusTarget, ObserverKeyboardActivate,
    ObserverKeyboardClaim,
};
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverFontRole, ObserverUiState};
use crate::organizer::ui::OrganizerInspectorRoot;
use crate::ui::{self, Interaction};

use super::position::NavigationFocus;

/// Native controls and interface-tour replay use this same navigation request.
#[derive(Message, Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum NavigationAction {
    Back,
    Home,
}

#[derive(Component)]
pub(crate) struct NavigationButton(pub(crate) NavigationAction);

#[derive(Component)]
pub(crate) struct NavigationRegion;

pub(crate) fn spawn(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            Node {
                column_gap: px(6),
                align_items: AlignItems::Center,
                flex_shrink: 0.0,
                ..default()
            },
            Name::new("wayne.navigation"),
            NavigationRegion,
        ))
        .with_children(|bar| {
            button(bar, "Back", NavigationAction::Back);
            button(bar, "Organizing Home", NavigationAction::Home);
        });
}

pub(crate) fn button(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    action: NavigationAction,
) -> Entity {
    parent
        .spawn((
            ui::pressable(),
            NavigationButton(action),
            match action {
                NavigationAction::Back => NavigationFocus::Back,
                NavigationAction::Home => NavigationFocus::Home,
            },
            ObserverFocusTarget::action(None),
            Node {
                padding: UiRect::axes(px(6), px(4)),
                flex_shrink: 0.0,
                border: UiRect::bottom(px(2)),
                ..default()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
        ))
        .with_child((
            Text::new(label),
            TextFont {
                font_size: FontSize::Px(14.0),
                ..default()
            },
            TextColor(theme::PAPER),
            ObserverFontRole::Body,
        ))
        .id()
}

#[derive(SystemParam)]
pub(super) struct ModalAdmission<'w, 's> {
    policy: Option<Res<'w, ObserverFocusPolicy>>,
    inspectors: Query<'w, 's, (), With<OrganizerInspectorRoot>>,
}

impl ModalAdmission<'_, '_> {
    pub(super) fn allows(&self) -> bool {
        self.policy
            .as_ref()
            .and_then(|policy| policy.modal)
            .is_none_or(|root| self.inspectors.contains(root))
    }
}

pub(super) fn sync_targets(
    session: Res<ObserverSession>,
    ui: Res<ObserverUiState>,
    modal: ModalAdmission,
    mut groups: Query<&mut Node, With<NavigationGroup>>,
    mut buttons: Query<&mut ObserverFocusTarget, With<NavigationButton>>,
) {
    let supported =
        session.organizer_enabled && !ui.menu_open && !ui.splash_visible && !ui.comparison_open;
    for mut node in &mut groups {
        let display = if supported {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != display {
            node.display = display;
        }
    }
    for mut target in &mut buttons {
        let mut next = target.clone();
        next.context = Some(session.context());
        next.available = supported && modal.allows();
        target.set_if_neq(next);
    }
}

pub(super) fn paint_buttons(
    mut buttons: Query<
        (
            &Interaction,
            &ObserverFocusTarget,
            &mut BackgroundColor,
            &mut BorderColor,
        ),
        With<NavigationButton>,
    >,
) {
    for (interaction, target, mut background, mut border) in &mut buttons {
        let color = if !target.available {
            theme::PANEL
        } else if *interaction == Interaction::Pressed {
            theme::COPPER.with_alpha(0.3)
        } else if *interaction == Interaction::Hovered {
            theme::PAPER.with_alpha(0.15)
        } else {
            theme::PANEL
        };
        background.set_if_neq(BackgroundColor(color));
        border.set_if_neq(BorderColor::all(
            if target.available && *interaction != Interaction::None {
                theme::YELLOW
            } else {
                theme::GRAY
            },
        ));
    }
}

pub(super) fn pointer(
    buttons: Query<(Entity, &Interaction, &NavigationButton), Changed<Interaction>>,
    tree: FocusTree,
    policy: Res<ObserverFocusPolicy>,
    mut actions: MessageWriter<NavigationAction>,
) {
    for (entity, interaction, button) in &buttons {
        if *interaction == Interaction::Pressed && tree.tabbable(entity, &policy) {
            actions.write(button.0);
        }
    }
}

pub(super) fn keyboard_activate(
    event: On<ObserverKeyboardActivate>,
    buttons: Query<&NavigationButton>,
    tree: FocusTree,
    policy: Res<ObserverFocusPolicy>,
    mut actions: MessageWriter<NavigationAction>,
) {
    if event.context != policy.context || !tree.tabbable(event.entity, &policy) {
        return;
    }
    if let Ok(button) = buttons.get(event.entity) {
        actions.write(button.0);
    }
}

pub(super) fn keyboard(
    keys: Res<ButtonInput<KeyCode>>,
    mut claimed: ResMut<ObserverKeyboardClaim>,
    session: Res<ObserverSession>,
    ui: Res<ObserverUiState>,
    modal: ModalAdmission,
    mut actions: MessageWriter<NavigationAction>,
) {
    if session.organizer_enabled
        && !ui.menu_open
        && !ui.splash_visible
        && !ui.comparison_open
        && modal.allows()
        && !claimed.claimed(KeyCode::ArrowLeft)
        && (keys.pressed(KeyCode::AltLeft) || keys.pressed(KeyCode::AltRight))
        && keys.just_pressed(KeyCode::ArrowLeft)
    {
        claimed.claim(KeyCode::ArrowLeft);
        actions.write(NavigationAction::Back);
    }
}
