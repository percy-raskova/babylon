//! Nonmodal header feedback for actual operations; animation carries no percentage.

use super::ui;
use crate::observer_io::ObserverSet;
use crate::observer_progress::OperationProgress;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverUiState;
use bevy::prelude::*;

/// Headings share their header space with pending operation feedback.
#[derive(Component)]
pub(crate) struct IdleHeading;
/// Stable tour anchor; feedback never intercepts navigation or committed readings.
#[derive(Component)]
pub(crate) struct ProcessingFeedback;
#[derive(Component)]
struct ActivityBar(u128);
/// The operation's real stage and elapsed-time text, also used for layout verification.
#[derive(Component)]
pub(crate) struct ProcessingCaption;

pub(crate) fn spawn(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            ProcessingFeedback,
            Name::new("wayne.processing"),
            Pickable::IGNORE,
            Node {
                display: Display::None,
                flex_grow: 1.0,
                flex_basis: px(0),
                min_width: px(0),
                align_items: AlignItems::Center,
                column_gap: px(5),
                ..default()
            },
        ))
        .with_children(|feedback| {
            for index in 0..3 {
                feedback.spawn((
                    ActivityBar(index),
                    Node {
                        width: px(3),
                        height: px(15),
                        flex_shrink: 0.0,
                        ..default()
                    },
                    BackgroundColor(theme::YELLOW),
                ));
            }
            feedback
                .spawn((ui::text("", 14.0, theme::YELLOW), ProcessingCaption))
                .insert(Node {
                    flex_grow: 1.0,
                    flex_basis: px(0),
                    min_width: px(0),
                    ..default()
                })
                .insert(TextFont {
                    font_size: FontSize::Px(14.0),
                    weight: FontWeight::BOLD,
                    ..default()
                });
        });
}

fn paint(
    progress: Option<Res<OperationProgress>>,
    ui: Res<ObserverUiState>,
    time: Res<Time<Real>>,
    mut headings: Query<&mut Node, (With<IdleHeading>, Without<ProcessingFeedback>)>,
    mut regions: Query<&mut Node, (With<ProcessingFeedback>, Without<IdleHeading>)>,
    mut texts: Query<&mut Text, With<ProcessingCaption>>,
    mut bars: Query<(&ActivityBar, &mut BackgroundColor)>,
) {
    let caption = progress.as_deref().and_then(OperationProgress::caption);
    for mut node in &mut headings {
        let display = if caption.is_some() {
            Display::None
        } else {
            Display::Flex
        };
        if node.display != display {
            node.display = display;
        }
    }
    for mut node in &mut regions {
        let display = if caption.is_some() {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != display {
            node.display = display;
        }
    }
    for mut text in &mut texts {
        text.set_if_neq(Text::new(caption.as_deref().unwrap_or_default()));
    }
    let active = (time.elapsed().as_millis() / 250) % 3;
    for (bar, mut color) in &mut bars {
        let alpha = if ui.reduced_motion || bar.0 == active {
            1.0
        } else {
            0.25
        };
        color.set_if_neq(BackgroundColor(theme::YELLOW.with_alpha(alpha)));
    }
}

pub(super) fn install(app: &mut App) {
    app.add_systems(Update, paint.in_set(ObserverSet::Paint));
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::observer::ObserverSession;
    use babylon_persistence::identity::CampaignId;
    use bevy::time::TimeUpdateStrategy;
    use std::time::Duration;
    use uuid::Uuid;

    fn bar_colors(app: &mut App) -> Vec<Color> {
        let world = app.world_mut();
        let mut bars: Vec<_> = world
            .query::<(&ActivityBar, &BackgroundColor)>()
            .iter(world)
            .map(|(bar, color)| (bar.0, color.0))
            .collect();
        bars.sort_by_key(|(index, _)| *index);
        bars.into_iter().map(|(_, color)| color).collect()
    }

    #[test]
    fn real_pending_feedback_animates_indeterminately_and_reduced_motion_is_static() {
        let mut state = ObserverSession::new(CampaignId::from_uuid(Uuid::from_u128(7)));
        state.ready(3, None);
        assert!(state.installed(&state.context()));
        state.set_organizer_control_pending(true);
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(state)
            .insert_resource(ObserverUiState {
                reduced_motion: true,
                ..default()
            })
            .insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_millis(
                250,
            )))
            .init_resource::<OperationProgress>()
            .add_systems(Startup, |mut commands: Commands| {
                commands.spawn(Node::default()).with_children(spawn);
            })
            .add_systems(Update, (crate::observer_progress::track, paint).chain());
        app.update();
        let first = bar_colors(&mut app);
        for _ in 0..3 {
            app.update();
        }
        assert_eq!(
            bar_colors(&mut app),
            first,
            "Reduced Motion never pulses activity bars"
        );
        let world = app.world_mut();
        let caption = world
            .query_filtered::<&Text, With<ProcessingCaption>>()
            .single(world)
            .expect("real progress caption");
        assert!(
            caption.0.contains("Updating the organizer view") && caption.0.contains("elapsed"),
            "the actual authenticated refresh stays prominent: {}",
            caption.0
        );
        assert!(
            !caption.0.contains('%'),
            "activity never suggests a simulated percentage"
        );
        world.resource_mut::<ObserverUiState>().reduced_motion = false;
        app.update();
        let animated = bar_colors(&mut app);
        app.update();
        assert_ne!(
            bar_colors(&mut app),
            animated,
            "ordinary motion marks activity without estimating completion"
        );
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .set_organizer_control_pending(false);
        app.update();
        let world = app.world_mut();
        let node = world
            .query_filtered::<&Node, With<ProcessingFeedback>>()
            .single(world)
            .expect("progress anchor");
        assert_eq!(
            node.display,
            Display::None,
            "feedback ends only when actual pending state clears"
        );
    }
}
