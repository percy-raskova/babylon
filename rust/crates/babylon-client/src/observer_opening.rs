//! Presentation-only opening sequence. It cannot advance or admit a campaign.

use bevy::asset::io::embedded::EmbeddedAssetRegistry;
use bevy::ecs::system::SystemParam;
use bevy::image::{ImageLoaderSettings, ImageSampler};
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::prelude::*;
use bevy::render::render_resource::AsBindGroup;
use bevy::shader::ShaderRef;
use bevy::window::PrimaryWindow;
use std::path::{Path, PathBuf};

use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_focus::{ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate};
use crate::observer_io::ObserverSet;
use crate::observer_ui::{ObserverCommand, ObserverFontRole, ObserverUiState};

pub(crate) const PRODUCTION_DURATION: f32 = 9.0;
const IMPACT: f32 = 6.5;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum OpeningStage {
    #[default]
    Warning,
    Production,
    Title,
    Game,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum MenuPage {
    #[default]
    Home,
    InGame,
    SavedGames,
    Campaigns,
    Settings,
}

#[derive(Resource, Default)]
pub(crate) struct OpeningPresentation {
    pub stage: OpeningStage,
    pub menu_page: MenuPage,
    pub launch_pending: bool,
    pub elapsed: f32,
}

impl OpeningPresentation {
    pub(crate) fn begin_production(&mut self) {
        self.stage = OpeningStage::Production;
        self.elapsed = 0.0;
    }

    fn show_title(&mut self, ui: &mut ObserverUiState) {
        self.stage = OpeningStage::Title;
        self.menu_page = MenuPage::Home;
        ui.splash_visible = false;
        ui.menu_open = true;
    }

    pub(crate) fn saved_games_visible(&self) -> bool {
        self.stage == OpeningStage::Title && self.menu_page == MenuPage::SavedGames
    }
}

#[derive(Component)]
pub(crate) struct ProductionRoot;
#[derive(Component)]
struct ProductionSignature;
#[derive(Component)]
struct StaticSignature;
#[derive(Component)]
struct ProductionCaption(bool);
#[derive(Component)]
struct SkipProduction;
#[derive(Message)]
struct ProductionSkip;

#[derive(AsBindGroup, Asset, TypePath, Debug, Clone)]
struct SignatureMaterial {
    #[uniform(0)]
    clock: Vec4,
    #[uniform(1)]
    pen: Vec4,
    #[texture(2)]
    #[sampler(3)]
    ink: Handle<Image>,
}

impl UiMaterial for SignatureMaterial {
    fn fragment_shader() -> ShaderRef {
        "embedded://opening/production.wgsl".into()
    }
}

#[derive(Resource)]
struct SignaturePen(Vec<[f32; 4]>);

impl SignaturePen {
    fn at(&self, seconds: f32) -> Vec4 {
        let next = self.0.partition_point(|point| point[0] <= seconds);
        let first = self.0[next.saturating_sub(1)];
        let last = self.0[next.min(self.0.len() - 1)];
        let amount = ((seconds - first[0]) / (last[0] - first[0]).max(0.001)).clamp(0.0, 1.0);
        Vec4::new(
            first[1] + (last[1] - first[1]) * amount,
            first[2] + (last[2] - first[2]) * amount,
            last[3],
            0.0,
        )
    }
}

fn label(value: &str, size: f32) -> impl Bundle {
    (
        Text::new(value),
        TextFont {
            font_size: size,
            ..default()
        },
        TextColor(Color::srgb(0.98, 0.88, 0.78)),
        ObserverFontRole::Display,
        TextLayout::new_with_justify(Justify::Center),
        DeclaredSurface::new(SurfaceId::TitleLockup),
    )
}

fn spawn_production(
    mut commands: Commands,
    server: Res<AssetServer>,
    mut materials: ResMut<Assets<SignatureMaterial>>,
) {
    let ink = server.load_with_settings(
        "embedded://opening/signature-ink.png",
        |settings: &mut ImageLoaderSettings| {
            settings.is_srgb = false;
            settings.sampler = ImageSampler::nearest();
        },
    );
    let material = materials.add(SignatureMaterial {
        clock: Vec4::ZERO,
        pen: Vec4::ZERO,
        ink,
    });
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                width: percent(100),
                height: percent(100),
                overflow: Overflow::clip(),
                ..default()
            },
            BackgroundColor(Color::srgb(0.015, 0.008, 0.021)),
            ZIndex(110),
            Visibility::Hidden,
            TabGroup::modal(),
            ProductionRoot,
            DeclaredSurface::new(SurfaceId::TitleLockup),
        ))
        .with_children(|screen| {
            screen.spawn((
                Node {
                    position_type: PositionType::Absolute,
                    width: percent(100),
                    top: percent(0),
                    ..default()
                },
                label("A", 50.0),
                ProductionCaption(false),
            ));
            screen.spawn((
                Node {
                    position_type: PositionType::Absolute,
                    ..default()
                },
                MaterialNode(material),
                ProductionSignature,
                Name::new("Persephone Raskova"),
                DeclaredSurface::new(SurfaceId::TitleLockup),
            ));
            screen.spawn((
                Text::new("Persephone\nRaskova"),
                TextFont::from_font_size(300.0),
                TextColor(Color::srgb(0.97, 0.80, 0.91)),
                TextLayout::new_with_justify(Justify::Center),
                bevy::text::LineHeight::RelativeToFont(0.9),
                ObserverFontRole::Script,
                Node {
                    position_type: PositionType::Absolute,
                    width: percent(100),
                    top: percent(4),
                    display: Display::None,
                    ..default()
                },
                StaticSignature,
                DeclaredSurface::new(SurfaceId::TitleLockup),
            ));
            screen.spawn((
                Node {
                    position_type: PositionType::Absolute,
                    width: percent(100),
                    bottom: percent(3),
                    ..default()
                },
                label("PRODUCTION", 60.0),
                ProductionCaption(true),
            ));
            screen
                .spawn((
                    Button,
                    SkipProduction,
                    Node {
                        position_type: PositionType::Absolute,
                        right: px(28),
                        bottom: px(18),
                        padding: UiRect::axes(px(16), px(9)),
                        ..default()
                    },
                    BackgroundColor(Color::NONE),
                    ObserverFocusTarget::action(None),
                    DeclaredSurface::new(SurfaceId::TitleLockup),
                ))
                .observe(skip_pointer)
                .with_child((
                    Text::new("SKIP  [ENTER]"),
                    TextFont::from_font_size(15.0),
                    TextColor(Color::srgb(0.65, 0.53, 0.62)),
                    ObserverFontRole::Body,
                ));
        });
}

fn skip_pointer(
    event: On<Pointer<Click>>,
    opening: Res<OpeningPresentation>,
    mut skips: MessageWriter<ProductionSkip>,
) {
    if event.button == bevy::picking::pointer::PointerButton::Primary
        && opening.stage == OpeningStage::Production
    {
        skips.write(ProductionSkip);
    }
}

fn skip_focused(
    event: On<ObserverKeyboardActivate>,
    targets: Query<(), With<SkipProduction>>,
    opening: Res<OpeningPresentation>,
    mut skips: MessageWriter<ProductionSkip>,
) {
    if event.context.is_none()
        && targets.contains(event.entity)
        && opening.stage == OpeningStage::Production
    {
        skips.write(ProductionSkip);
    }
}

fn keyboard(
    keys: Res<ButtonInput<KeyCode>>,
    opening: Res<OpeningPresentation>,
    mut skips: MessageWriter<ProductionSkip>,
    mut commands: MessageWriter<ObserverCommand>,
) {
    if opening.stage != OpeningStage::Production {
        return;
    }
    if keys.just_pressed(KeyCode::KeyQ) {
        commands.write(ObserverCommand::Quit);
    } else if [
        KeyCode::Enter,
        KeyCode::NumpadEnter,
        KeyCode::Escape,
        KeyCode::Space,
    ]
    .iter()
    .any(|key| keys.just_pressed(*key))
    {
        skips.write(ProductionSkip);
    }
}

fn advance(
    time: Res<Time>,
    mut opening: ResMut<OpeningPresentation>,
    mut ui: ResMut<ObserverUiState>,
    mut skips: MessageReader<ProductionSkip>,
    session: Option<Res<crate::observer::ObserverSession>>,
) {
    if let Some(session) = session {
        if opening.launch_pending {
            if (matches!(
                session.phase,
                crate::observer::SessionPhase::Failed | crate::observer::SessionPhase::Closed
            ) && !session.lifecycle_pending())
                || session.runtime_disconnected()
                || session.quit_requested
            {
                opening.launch_pending = false;
            } else if !ui.splash_visible && crate::observer_title::can_continue(&session) {
                ui.menu_open = false;
                opening.launch_pending = false;
            }
        }
    }
    let skipped = skips.read().count() > 0;
    match opening.stage {
        OpeningStage::Production => {
            opening.elapsed += time.delta_secs();
            let duration = if ui.reduced_motion {
                3.0
            } else {
                PRODUCTION_DURATION
            };
            if skipped || opening.elapsed >= duration {
                opening.show_title(&mut ui);
            }
        }
        OpeningStage::Title if !ui.menu_open && !ui.comparison_open => {
            opening.stage = OpeningStage::Game;
            opening.menu_page = MenuPage::InGame;
        }
        _ => {}
    }
}

fn eligibility(
    opening: Res<OpeningPresentation>,
    mut targets: Query<&mut ObserverFocusTarget, With<SkipProduction>>,
) {
    for mut target in &mut targets {
        let visible = opening.stage == OpeningStage::Production;
        if target.available != visible {
            target.available = visible;
        }
    }
}

type AnimatedSignatureFilter = (With<ProductionSignature>, Without<StaticSignature>);
type StaticSignatureFilter = (With<StaticSignature>, Without<ProductionSignature>);

#[derive(SystemParam)]
struct ProductionNodes<'w, 's> {
    roots: Query<'w, 's, &'static mut Visibility, With<ProductionRoot>>,
    signature: Query<
        'w,
        's,
        (&'static mut Node, &'static MaterialNode<SignatureMaterial>),
        AnimatedSignatureFilter,
    >,
    captions: Query<
        'w,
        's,
        (
            &'static ProductionCaption,
            &'static mut TextFont,
            &'static mut TextColor,
        ),
        Without<StaticSignature>,
    >,
    static_names: Query<'w, 's, (&'static mut Node, &'static mut TextFont), StaticSignatureFilter>,
}

fn animate(
    opening: Res<OpeningPresentation>,
    ui: Res<ObserverUiState>,
    pen: Res<SignaturePen>,
    windows: Query<&Window, With<PrimaryWindow>>,
    scale: Res<UiScale>,
    mut nodes: ProductionNodes,
    mut materials: ResMut<Assets<SignatureMaterial>>,
) {
    let visible = opening.stage == OpeningStage::Production;
    for mut root in &mut nodes.roots {
        root.set_if_neq(if visible {
            Visibility::Visible
        } else {
            Visibility::Hidden
        });
    }
    if !visible {
        return;
    }
    let Ok(window) = windows.single() else {
        return;
    };
    let width = window.width() / scale.0;
    let height = window.height() / scale.0;
    let size = Vec2::new(width.min(height * 1.78), width.min(height * 1.78) * 0.5);
    let seconds = if ui.reduced_motion {
        8.8
    } else {
        opening.elapsed
    };
    for (mut node, mut font) in &mut nodes.static_names {
        node.display = if ui.reduced_motion {
            Display::Flex
        } else {
            Display::None
        };
        font.font_size = size.x * 0.227;
    }
    for (mut node, handle) in &mut nodes.signature {
        node.display = if ui.reduced_motion {
            Display::None
        } else {
            Display::Flex
        };
        node.width = px(size.x);
        node.height = px(size.y);
        node.left = px((width - size.x) * 0.5);
        node.top = px((height - size.y) * 0.12);
        if let Some(material) = materials.get_mut(handle) {
            material.clock = Vec4::new(
                seconds,
                if ui.reduced_motion { 1.0 } else { 0.0 },
                size.x,
                size.y,
            );
            material.pen = pen.at(seconds);
        }
    }
    for (caption, mut font, mut color) in &mut nodes.captions {
        let base = height * if caption.0 { 0.073 } else { 0.05 };
        let impact = ((seconds - IMPACT) * 10.0).max(0.0);
        font.font_size = base
            * if caption.0 && seconds >= IMPACT && !ui.reduced_motion {
                1.0 + (-impact).exp() * 1.5
            } else {
                1.0
            };
        color.0 = Color::srgba(
            0.98,
            0.88,
            0.78,
            if caption.0 && seconds < IMPACT {
                0.0
            } else {
                1.0
            },
        );
    }
}

pub(crate) struct OpeningPlugin;
impl Plugin for OpeningPlugin {
    fn build(&self, app: &mut App) {
        let registry = app.world().resource::<EmbeddedAssetRegistry>();
        for (name, bytes) in [
            (
                "production.wgsl",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/opening/production.wgsl"
                )) as &[u8],
            ),
            (
                "signature-ink.png",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/opening/signature-ink.png"
                )) as &[u8],
            ),
        ] {
            registry.insert_asset(PathBuf::from(name), &Path::new("opening").join(name), bytes);
        }
        let points: Vec<[f32; 4]> = serde_json::from_str(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/opening/signature-pen.json"
        )))
        .expect("authored production pen trajectory must be valid");
        assert!(
            !points.is_empty(),
            "production pen trajectory must not be empty"
        );
        app.init_resource::<OpeningPresentation>()
            .insert_resource(SignaturePen(points))
            .add_plugins(UiMaterialPlugin::<SignatureMaterial>::default())
            .add_message::<ProductionSkip>()
            .add_observer(skip_focused)
            .add_systems(Startup, spawn_production)
            .add_systems(
                PreUpdate,
                eligibility.in_set(ObserverFocusSystems::Eligibility),
            )
            .add_systems(Update, keyboard.in_set(ObserverSet::Input))
            .add_systems(
                Update,
                (advance, animate)
                    .chain()
                    .after(ObserverSet::Install)
                    .before(ObserverSet::Paint),
            );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::ecs::system::RunSystemOnce;

    #[test]
    fn recovery_launch_waits_for_the_new_campaign_after_a_previous_failure() {
        let mut world = World::new();
        let mut session = crate::observer::ObserverSession::new(
            babylon_persistence::identity::CampaignId::from_uuid(uuid::Uuid::from_u128(1)),
        );
        session.connected_fixture();
        session.fail("Previous campaign refused".into());
        session
            .queue_campaign(
                babylon_persistence::runtime_session::RuntimeSessionTarget::Open {
                    campaign_id: uuid::Uuid::from_u128(2).to_string(),
                },
            )
            .unwrap();
        world.insert_resource(session);
        world.insert_resource(Time::<()>::default());
        world.insert_resource(OpeningPresentation {
            stage: OpeningStage::Title,
            launch_pending: true,
            ..default()
        });
        world.insert_resource(ObserverUiState {
            splash_visible: false,
            ..default()
        });
        world.init_resource::<Messages<ProductionSkip>>();
        world.run_system_once(advance).unwrap();
        assert!(world.resource::<OpeningPresentation>().launch_pending);
        assert!(world.resource::<ObserverUiState>().menu_open);
    }

    #[test]
    fn production_skip_opens_title_without_emitting_gameplay_commands() {
        let mut world = World::new();
        world.insert_resource(Time::<()>::default());
        world.insert_resource(OpeningPresentation {
            stage: OpeningStage::Production,
            ..default()
        });
        world.insert_resource(ObserverUiState::default());
        world.init_resource::<Messages<ProductionSkip>>();
        world.init_resource::<Messages<ObserverCommand>>();
        world.write_message(ProductionSkip);
        world.run_system_once(advance).unwrap();
        assert_eq!(
            world.resource::<OpeningPresentation>().stage,
            OpeningStage::Title
        );
        assert!(!world.resource::<ObserverUiState>().splash_visible);
        assert!(world.resource::<ObserverUiState>().menu_open);
        assert!(world.resource::<Messages<ObserverCommand>>().is_empty());
    }

    #[test]
    fn escape_menu_keeps_game_stage_after_explicit_entry() {
        let mut world = World::new();
        world.insert_resource(Time::<()>::default());
        world.insert_resource(OpeningPresentation {
            stage: OpeningStage::Title,
            ..default()
        });
        world.insert_resource(ObserverUiState {
            splash_visible: false,
            ..default()
        });
        world.init_resource::<Messages<ProductionSkip>>();
        world.run_system_once(advance).unwrap();
        assert_eq!(
            world.resource::<OpeningPresentation>().stage,
            OpeningStage::Title
        );
        world.resource_mut::<ObserverUiState>().menu_open = false;
        world.run_system_once(advance).unwrap();
        assert_eq!(
            world.resource::<OpeningPresentation>().stage,
            OpeningStage::Game
        );
        world.resource_mut::<ObserverUiState>().menu_open = true;
        world.run_system_once(advance).unwrap();
        assert_eq!(
            world.resource::<OpeningPresentation>().stage,
            OpeningStage::Game,
            "opening the campaign menu must not return to the title screen"
        );
        assert_eq!(
            world.resource::<OpeningPresentation>().menu_page,
            MenuPage::InGame
        );
    }
}
