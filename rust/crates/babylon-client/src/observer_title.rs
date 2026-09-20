//! The game's illustrated front door and its real campaign destinations.

use bevy::ecs::system::SystemParam;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer::{ObserverSession, SessionPhase};
use crate::observer_controls::{availability, ControlAvailability};
use crate::observer_focus::{
    ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate, ObserverKeyboardClaim,
};
use crate::observer_io::ObserverSet;
use crate::observer_opening::{MenuPage, OpeningPresentation, OpeningStage};
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverCommand, ObserverFontRole, ObserverUiState};
use crate::visual_assets::VisualAssets;

#[derive(Component)]
pub(crate) struct TitleMenuRoot;
#[derive(Component)]
struct TitleBackdrop;
#[derive(Component)]
struct TitleArt;
#[derive(Component)]
struct TitleHeading;
#[derive(Component)]
struct TitleStatus;
#[derive(Component)]
struct TitleActionCaption;

#[derive(Component, Clone, Copy, PartialEq, Eq)]
enum TitleAction {
    Continue,
    NewGame,
    LoadGame,
    Campaigns,
    Settings,
    Quit,
    Home,
    Resume,
    GameSettings,
    MainMenu,
    GameQuit,
}

fn label(value: &str, size: f32, role: ObserverFontRole) -> impl Bundle {
    (
        Text::new(value),
        TextFont {
            font_size: size,
            ..default()
        },
        TextColor(theme::PAPER),
        role,
        DeclaredSurface::new(SurfaceId::TitleLockup),
    )
}

fn action_button(parent: &mut ChildSpawnerCommands, action: TitleAction, caption: &str) {
    parent
        .spawn((
            Button,
            action,
            Node {
                width: percent(100),
                min_height: px(43),
                padding: UiRect::axes(px(18), px(5)),
                border: UiRect::left(px(3)),
                align_items: AlignItems::Center,
                flex_shrink: 0.0,
                ..default()
            },
            BackgroundColor(Color::NONE),
            BorderColor::all(Color::NONE),
            ObserverFocusTarget::action(None),
            DeclaredSurface::new(SurfaceId::TitleLockup),
        ))
        .observe(pointer_action)
        .with_child((
            label(caption, 25.0, ObserverFontRole::Body),
            TitleActionCaption,
        ));
}

pub(crate) fn spawn_back_button(parent: &mut ChildSpawnerCommands) {
    action_button(parent, TitleAction::Home, "‹  Back");
}

pub(crate) fn spawn_game_menu(parent: &mut ChildSpawnerCommands) {
    for (action, caption) in [
        (TitleAction::Resume, "Resume campaign [Esc]"),
        (TitleAction::GameSettings, "Settings"),
        (TitleAction::MainMenu, "Main menu"),
        (TitleAction::GameQuit, "Quit game"),
    ] {
        action_button(parent, action, caption);
    }
    parent.spawn((label("", 14.0, ObserverFontRole::Body), TitleStatus));
}

fn spawn_title(mut commands: Commands, assets: Res<VisualAssets>) {
    spawn_backdrop(&mut commands, &assets);
    spawn_home(&mut commands);
}

fn spawn_backdrop(commands: &mut Commands, assets: &VisualAssets) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: px(0),
                right: px(0),
                top: px(0),
                bottom: px(0),
                overflow: Overflow::clip(),
                ..default()
            },
            BackgroundColor(theme::INK),
            Visibility::Hidden,
            ZIndex(15),
            TitleBackdrop,
            DeclaredSurface::new(SurfaceId::TitleLockup),
        ))
        .with_children(|backdrop| {
            backdrop.spawn((
                ImageNode::new(assets.hero_liberty.clone()).with_mode(NodeImageMode::Stretch),
                Node {
                    position_type: PositionType::Absolute,
                    ..default()
                },
                TitleArt,
                Pickable::IGNORE,
                DeclaredSurface::new(SurfaceId::TitleLockup),
            ));
            backdrop.spawn((
                Node {
                    position_type: PositionType::Absolute,
                    left: px(0),
                    right: px(0),
                    top: px(0),
                    bottom: px(0),
                    ..default()
                },
                BackgroundGradient::from(LinearGradient::to_right(vec![
                    ColorStop::new(theme::INK.with_alpha(0.02), percent(0)),
                    ColorStop::new(theme::INK.with_alpha(0.08), percent(30)),
                    ColorStop::new(theme::INK.with_alpha(0.78), percent(57)),
                    ColorStop::new(theme::INK.with_alpha(0.96), percent(100)),
                ])),
                Pickable::IGNORE,
                DeclaredSurface::new(SurfaceId::TitleLockup),
            ));
        });
}

fn spawn_home(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: percent(56),
                right: percent(6),
                top: percent(13),
                bottom: percent(7),
                flex_direction: FlexDirection::Column,
                overflow: Overflow::scroll_y(),
                ..default()
            },
            ScrollPosition::default(),
            Visibility::Hidden,
            ZIndex(20),
            TitleMenuRoot,
            TabGroup::modal(),
            DeclaredSurface::new(SurfaceId::TitleLockup),
        ))
        .with_children(|menu| {
            menu.spawn((
                label("BABYLON", 108.0, ObserverFontRole::Display),
                TitleHeading,
            ));
            menu.spawn((
                label("THE FALL OF AMERICA", 21.0, ObserverFontRole::Body),
                Node {
                    margin: UiRect::top(px(-8)),
                    flex_shrink: 0.0,
                    ..default()
                },
            ));
            menu.spawn((
                Node {
                    width: px(56),
                    height: px(3),
                    margin: UiRect::vertical(px(30)),
                    flex_shrink: 0.0,
                    ..default()
                },
                BackgroundColor(theme::RED),
                DeclaredSurface::new(SurfaceId::TitleLockup),
            ));
            menu.spawn(Node {
                flex_direction: FlexDirection::Column,
                row_gap: px(5),
                width: percent(100),
                max_width: px(380),
                flex_shrink: 0.0,
                ..default()
            })
            .with_children(|actions| {
                for (action, caption) in [
                    (TitleAction::Continue, "Continue"),
                    (TitleAction::NewGame, "New Game"),
                    (TitleAction::LoadGame, "Load Game"),
                    (TitleAction::Campaigns, "Observer Campaigns"),
                    (TitleAction::Settings, "Settings"),
                    (TitleAction::Quit, "Quit"),
                ] {
                    action_button(actions, action, caption);
                }
            });
            menu.spawn((
                label("", 14.0, ObserverFontRole::Body),
                TitleStatus,
                Node {
                    margin: UiRect::top(px(24)),
                    max_width: px(420),
                    flex_shrink: 0.0,
                    ..default()
                },
            ));
        });
}

pub(crate) fn can_continue(session: &ObserverSession) -> bool {
    matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        && session.foundation_digest.is_some()
        && !session.lifecycle_pending()
        && !session.advance_pending()
        && !session.organizer_control_pending()
        && !session.quit_requested
}

fn action_enabled(
    action: TitleAction,
    opening: &OpeningPresentation,
    session: &ObserverSession,
) -> bool {
    if action == TitleAction::Quit {
        return true;
    }
    if session.quit_requested {
        return false;
    }
    match action {
        TitleAction::Continue | TitleAction::Resume => {
            !opening.launch_pending && can_continue(session)
        }
        TitleAction::NewGame => {
            !opening.launch_pending
                && !session.lifecycle_pending()
                && availability(ObserverCommand::NewOrganizerCampaign, session)
                    == ControlAvailability::Enabled
        }
        _ => true,
    }
}

fn action_visible(
    action: TitleAction,
    opening: &OpeningPresentation,
    ui: &ObserverUiState,
) -> bool {
    if !ui.menu_open || ui.splash_visible || ui.comparison_open {
        return false;
    }
    match action {
        TitleAction::Home => match opening.stage {
            OpeningStage::Title => opening.menu_page != MenuPage::Home,
            OpeningStage::Game => opening.menu_page == MenuPage::Settings,
            _ => false,
        },
        TitleAction::Resume
        | TitleAction::GameSettings
        | TitleAction::MainMenu
        | TitleAction::GameQuit => {
            opening.stage == OpeningStage::Game && opening.menu_page == MenuPage::InGame
        }
        _ => opening.stage == OpeningStage::Title && opening.menu_page == MenuPage::Home,
    }
}

#[derive(SystemParam)]
struct TitleInput<'w> {
    opening: ResMut<'w, OpeningPresentation>,
    session: Res<'w, ObserverSession>,
    ui: Res<'w, ObserverUiState>,
    commands: MessageWriter<'w, ObserverCommand>,
}
impl TitleInput<'_> {
    fn activate(&mut self, action: TitleAction) {
        if !action_visible(action, &self.opening, &self.ui)
            || !action_enabled(action, &self.opening, &self.session)
        {
            return;
        }
        match action {
            TitleAction::Continue | TitleAction::Resume => {
                self.commands.write(ObserverCommand::Menu);
            }
            TitleAction::NewGame => {
                self.commands.write(ObserverCommand::NewOrganizerCampaign);
            }
            TitleAction::LoadGame => self.opening.menu_page = MenuPage::SavedGames,
            TitleAction::Campaigns => self.opening.menu_page = MenuPage::Campaigns,
            TitleAction::Settings | TitleAction::GameSettings => {
                self.opening.menu_page = MenuPage::Settings;
            }
            TitleAction::MainMenu => {
                self.opening.stage = OpeningStage::Title;
                self.opening.menu_page = MenuPage::Home;
            }
            TitleAction::Quit | TitleAction::GameQuit => {
                self.commands.write(ObserverCommand::Quit);
            }
            TitleAction::Home => {
                self.opening.menu_page = if self.opening.stage == OpeningStage::Game {
                    MenuPage::InGame
                } else {
                    MenuPage::Home
                };
            }
        }
    }
}
fn pointer_action(event: On<Pointer<Click>>, actions: Query<&TitleAction>, mut input: TitleInput) {
    if event.button == bevy::picking::pointer::PointerButton::Primary {
        if let Ok(action) = actions.get(event.entity) {
            input.activate(*action);
        }
    }
}
fn focused_action(
    event: On<ObserverKeyboardActivate>,
    actions: Query<&TitleAction>,
    mut input: TitleInput,
) {
    if event.context.is_none() {
        if let Ok(action) = actions.get(event.entity) {
            input.activate(*action);
        }
    }
}
fn keyboard(
    keys: Res<ButtonInput<KeyCode>>,
    claimed: Res<ObserverKeyboardClaim>,
    mut input: TitleInput,
) {
    if !input.ui.menu_open || input.ui.comparison_open {
        return;
    }
    if keys.just_pressed(KeyCode::Escape) && !claimed.claimed(KeyCode::Escape) {
        if input.opening.stage == OpeningStage::Game && input.opening.menu_page == MenuPage::InGame
        {
            input.activate(TitleAction::Resume);
        } else {
            input.activate(TitleAction::Home);
        }
    }
    if input.opening.menu_page == MenuPage::Home {
        for (key, action) in [
            (KeyCode::KeyC, TitleAction::Continue),
            (KeyCode::KeyN, TitleAction::NewGame),
            (KeyCode::KeyQ, TitleAction::Quit),
        ] {
            if keys.just_pressed(key) && !claimed.claimed(key) {
                input.activate(action);
            }
        }
    } else if input.opening.menu_page == MenuPage::InGame {
        for (key, action) in [
            (KeyCode::KeyC, TitleAction::Resume),
            (KeyCode::KeyQ, TitleAction::GameQuit),
        ] {
            if keys.just_pressed(key) && !claimed.claimed(key) {
                input.activate(action);
            }
        }
    }
}

fn eligibility(
    opening: Res<OpeningPresentation>,
    session: Res<ObserverSession>,
    ui: Res<ObserverUiState>,
    mut targets: Query<(&TitleAction, &mut ObserverFocusTarget)>,
) {
    for (action, mut target) in &mut targets {
        let available =
            action_visible(*action, &opening, &ui) && action_enabled(*action, &opening, &session);
        if target.available != available {
            target.available = available;
        }
    }
}

type TitleRootFilter = Or<(With<TitleMenuRoot>, With<TitleBackdrop>)>;

fn paint(
    opening: Res<OpeningPresentation>,
    session: Res<ObserverSession>,
    ui: Res<ObserverUiState>,
    mut roots: Query<(&mut Visibility, Has<TitleMenuRoot>), TitleRootFilter>,
    mut actions: Query<(
        &Interaction,
        &TitleAction,
        &mut BackgroundColor,
        &mut BorderColor,
        &Children,
        &mut Node,
    )>,
    mut captions: Query<&mut TextColor, With<TitleActionCaption>>,
    mut status: Query<&mut Text, With<TitleStatus>>,
) {
    let shown = opening.stage == OpeningStage::Title && ui.menu_open;
    for (mut visibility, home) in &mut roots {
        visibility.set_if_neq(
            if shown && (!home || opening.menu_page == MenuPage::Home) && !ui.comparison_open {
                Visibility::Visible
            } else {
                Visibility::Hidden
            },
        );
    }
    for (interaction, action, mut background, mut border, children, mut node) in &mut actions {
        node.display = if action_visible(*action, &opening, &ui) {
            Display::Flex
        } else {
            Display::None
        };
        let enabled = action_enabled(*action, &opening, &session);
        let hovered = enabled && *interaction != Interaction::None;
        background.set_if_neq(BackgroundColor(if hovered {
            theme::PAPER.with_alpha(0.055)
        } else {
            Color::NONE
        }));
        border.set_if_neq(BorderColor::all(if hovered {
            theme::RED
        } else {
            Color::NONE
        }));
        for child in children {
            if let Ok(mut color) = captions.get_mut(*child) {
                color.set_if_neq(TextColor(if !enabled {
                    theme::PAPER.with_alpha(0.35)
                } else if *interaction == Interaction::Pressed {
                    theme::RED
                } else {
                    theme::PAPER
                }));
            }
        }
    }
    let caption = if session.quit_requested {
        "Closing game…"
    } else if opening.launch_pending {
        "Starting your game…"
    } else if matches!(session.phase, SessionPhase::Failed | SessionPhase::Closed) {
        session
            .error
            .as_deref()
            .unwrap_or("Campaign unavailable. Load a saved game or start a new one.")
    } else if session.advance_pending() {
        "Finishing the current period…"
    } else if session.lifecycle_pending()
        || matches!(
            session.phase,
            SessionPhase::Connecting | SessionPhase::Loading
        )
    {
        "Opening campaign…"
    } else {
        ""
    };
    for mut text in &mut status {
        text.set_if_neq(Text::new(caption));
    }
}

fn layout(
    windows: Query<&Window, With<PrimaryWindow>>,
    scale: Res<UiScale>,
    assets: Res<VisualAssets>,
    images: Res<Assets<Image>>,
    mut art: Query<&mut Node, With<TitleArt>>,
    mut headings: Query<&mut TextFont, With<TitleHeading>>,
) {
    let Ok(window) = windows.single() else {
        return;
    };
    let viewport = Vec2::new(window.width(), window.height()) / scale.0;
    if let Some(image) = images.get(&assets.hero_liberty) {
        let source = image.size().as_vec2();
        let cover = (viewport.x / source.x).max(viewport.y / source.y);
        let extent = source * cover;
        for mut node in &mut art {
            node.width = px(extent.x);
            node.height = px(extent.y);
            node.left = px((viewport.x - extent.x) * 0.25);
            node.top = px((viewport.y - extent.y) * 0.5);
        }
    }
    for mut font in &mut headings {
        font.font_size = (viewport.x * 0.077).clamp(60.0, 126.0);
    }
}

pub(crate) struct ObserverTitlePlugin;
impl Plugin for ObserverTitlePlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<OpeningPresentation>()
            .add_systems(Startup, spawn_title)
            .add_observer(focused_action)
            .add_systems(
                PreUpdate,
                eligibility.in_set(ObserverFocusSystems::Eligibility),
            )
            .add_systems(Update, keyboard.in_set(ObserverSet::Input))
            .add_systems(Update, (paint, layout).in_set(ObserverSet::Paint));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::identity::CampaignId;

    #[test]
    fn native_title_buttons_route_pages_and_emit_the_real_organizer_command() {
        let mut app = App::new();
        let mut session = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(1)));
        session.connected_fixture();
        session.ready(0, None);
        session.foundation_digest = Some("admitted".into());
        assert!(session.installed(&session.context()));
        app.add_plugins(MinimalPlugins)
            .insert_resource(session)
            .insert_resource(OpeningPresentation {
                stage: OpeningStage::Title,
                ..default()
            })
            .insert_resource(ObserverUiState {
                splash_visible: false,
                ..default()
            })
            .add_message::<ObserverCommand>()
            .add_observer(focused_action)
            .add_systems(Startup, |mut commands: Commands| spawn_home(&mut commands));
        app.update();
        for (action, page) in [
            (TitleAction::LoadGame, MenuPage::SavedGames),
            (TitleAction::Settings, MenuPage::Settings),
            (TitleAction::Campaigns, MenuPage::Campaigns),
            (TitleAction::NewGame, MenuPage::Home),
        ] {
            app.world_mut()
                .resource_mut::<OpeningPresentation>()
                .menu_page = MenuPage::Home;
            let entity = app
                .world_mut()
                .query::<(Entity, &TitleAction)>()
                .iter(app.world())
                .find_map(|(entity, candidate)| (*candidate == action).then_some(entity))
                .unwrap();
            app.world_mut().trigger(ObserverKeyboardActivate {
                entity,
                context: None,
            });
            assert_eq!(
                app.world().resource::<OpeningPresentation>().menu_page,
                page
            );
        }
        let messages: Vec<_> = app
            .world_mut()
            .resource_mut::<Messages<ObserverCommand>>()
            .drain()
            .collect();
        assert_eq!(messages, [ObserverCommand::NewOrganizerCampaign]);
        assert!(app.world().resource::<ObserverUiState>().menu_open);
        assert!(
            !app.world().resource::<OpeningPresentation>().launch_pending,
            "only an accepted runtime queue may mark a launch pending"
        );
    }

    fn game_menu_app() -> App {
        let mut session = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(1)));
        session.connected_fixture();
        session.ready(2, None);
        session.foundation_digest = Some("admitted".into());
        assert!(session.installed(&session.context()));
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(session)
            .insert_resource(OpeningPresentation {
                stage: OpeningStage::Game,
                menu_page: MenuPage::InGame,
                ..default()
            })
            .insert_resource(ObserverUiState {
                splash_visible: false,
                ..default()
            })
            .init_resource::<ButtonInput<KeyCode>>()
            .init_resource::<ObserverKeyboardClaim>()
            .add_message::<ObserverCommand>()
            .add_observer(focused_action)
            .add_systems(Update, (keyboard, eligibility, paint).chain())
            .add_systems(Startup, |mut commands: Commands| {
                spawn_home(&mut commands);
                commands.spawn(Node::default()).with_children(|parent| {
                    spawn_game_menu(parent);
                    spawn_back_button(parent);
                });
            });
        app.update();
        app
    }

    fn activate(app: &mut App, action: TitleAction) {
        let entity = app
            .world_mut()
            .query::<(Entity, &TitleAction)>()
            .iter(app.world())
            .find_map(|(entity, candidate)| (*candidate == action).then_some(entity))
            .unwrap();
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity,
            context: None,
        });
    }

    #[test]
    fn escape_menu_routes_settings_back_and_resume_without_enabling_title_actions() {
        let mut app = game_menu_app();
        let context = app.world().resource::<ObserverSession>().context();
        for (action, target) in app
            .world_mut()
            .query::<(&TitleAction, &ObserverFocusTarget)>()
            .iter(app.world())
        {
            if matches!(
                action,
                TitleAction::Continue | TitleAction::NewGame | TitleAction::Settings
            ) {
                assert!(
                    !target.available,
                    "hidden title controls must remain unavailable"
                );
            }
        }
        activate(&mut app, TitleAction::Settings);
        assert_eq!(
            app.world().resource::<OpeningPresentation>().menu_page,
            MenuPage::InGame
        );
        activate(&mut app, TitleAction::GameSettings);
        assert_eq!(
            app.world().resource::<OpeningPresentation>().menu_page,
            MenuPage::Settings
        );
        for expected_commands in [vec![], vec![ObserverCommand::Menu]] {
            app.world_mut()
                .resource_mut::<ButtonInput<KeyCode>>()
                .press(KeyCode::Escape);
            app.update();
            assert_eq!(
                app.world().resource::<OpeningPresentation>().menu_page,
                MenuPage::InGame
            );
            let commands: Vec<_> = app
                .world_mut()
                .resource_mut::<Messages<ObserverCommand>>()
                .drain()
                .collect();
            assert_eq!(commands, expected_commands);
            app.world_mut()
                .resource_mut::<ButtonInput<KeyCode>>()
                .reset_all();
        }
        assert_eq!(app.world().resource::<ObserverSession>().context(), context);
        assert_eq!(
            app.world().resource::<OpeningPresentation>().stage,
            OpeningStage::Game
        );
    }

    fn failed_game_menu() -> App {
        let mut app = game_menu_app();
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        assert!(session.begin_advance().is_some());
        session.fail("Period acknowledgment was lost. Reopen the campaign.".into());
        app.update();
        app
    }

    #[test]
    fn game_menu_recovery_retains_failure_explanation_while_advance_is_pending() {
        let mut app = failed_game_menu();
        assert!(app.world().resource::<ObserverSession>().advance_pending());
        for text in app
            .world_mut()
            .query_filtered::<&Text, With<TitleStatus>>()
            .iter(app.world())
        {
            assert_eq!(
                text.0,
                "Period acknowledgment was lost. Reopen the campaign."
            );
        }
    }

    #[test]
    fn game_menu_recovery_can_reach_existing_load_and_reopen() {
        let mut app = failed_game_menu();
        let context = app.world().resource::<ObserverSession>().context();
        activate(&mut app, TitleAction::Resume);
        assert!(app
            .world()
            .resource::<Messages<ObserverCommand>>()
            .is_empty());
        let main_menu = app
            .world_mut()
            .query::<(&Text, &ChildOf)>()
            .iter(app.world())
            .find_map(|(text, parent)| (text.0 == "Main menu").then_some(parent.parent()))
            .expect("a failed campaign needs an explicit path to the existing recovery menu");
        assert!(
            app.world()
                .get::<ObserverFocusTarget>(main_menu)
                .unwrap()
                .available
        );
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity: main_menu,
            context: None,
        });
        assert_eq!(
            app.world().resource::<OpeningPresentation>().stage,
            OpeningStage::Title
        );
        activate(&mut app, TitleAction::LoadGame);
        assert!(app
            .world()
            .resource::<OpeningPresentation>()
            .saved_games_visible());
        assert_eq!(
            availability(
                ObserverCommand::ReopenCampaign,
                app.world().resource::<ObserverSession>()
            ),
            ControlAvailability::Enabled
        );
        assert!(app
            .world()
            .resource::<Messages<ObserverCommand>>()
            .is_empty());
        assert_eq!(app.world().resource::<ObserverSession>().context(), context);
        assert!(app.world().resource::<ObserverSession>().advance_pending());
    }

    #[test]
    fn continue_requires_an_admitted_observation_and_no_pending_authority() {
        let mut session = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::new_v4()));
        assert!(!can_continue(&session));
        session.ready(0, None);
        assert!(session.installed(&session.context()));
        assert!(
            !can_continue(&session),
            "a phase alone does not establish an admitted foundation"
        );
        session.foundation_digest = Some("admitted".into());
        assert!(can_continue(&session));
        session.set_organizer_control_pending(true);
        assert!(!can_continue(&session));
        session.set_organizer_control_pending(false);
        session.quit_requested = true;
        assert!(!can_continue(&session));
    }
}
