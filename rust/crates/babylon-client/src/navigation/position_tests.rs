//! Restoration exercises Bevy focus, hierarchy, geometry, and scroll components.

use bevy::input_focus::tab_navigation::TabGroup;

use super::*;
use crate::observer_focus::ObserverFocusTarget;

#[derive(Resource, Default)]
struct Captured(Option<SavedPosition>);

fn capture_once(position: PositionCapture, mut captured: ResMut<Captured>) {
    if captured.0.is_none() {
        captured.0 = Some(position.capture());
    }
}

fn reading(app: &mut App, root: Entity, offset: f32) -> Entity {
    app.world_mut()
        .spawn((
            Node {
                overflow: Overflow::scroll_y(),
                ..default()
            },
            ComputedNode {
                size: Vec2::splat(100.0),
                content_size: Vec2::new(100.0, 400.0),
                inverse_scale_factor: 1.0,
                ..default()
            },
            ChildOf(root),
            ObserverFocusTarget {
                available: true,
                ..ObserverFocusTarget::reading(None)
            },
            NavigationFocus::Reading(ReadingRegion::OrganizerWorkspace),
            ReadingRegion::OrganizerWorkspace,
            ScrollPosition(Vec2::new(0.0, offset)),
        ))
        .id()
}

#[test]
fn restored_focus_resolves_repainted_entities_and_offsets_are_applied_once() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .init_resource::<InputFocus>()
        .init_resource::<ObserverFocusPolicy>()
        .init_resource::<PendingPosition>()
        .init_resource::<Captured>()
        .add_systems(Update, capture_once)
        .add_systems(Last, restore_position);
    let root = app
        .world_mut()
        .spawn((Node::default(), TabGroup::new(0)))
        .id();
    let original = reading(&mut app, root, 160.0);
    app.world_mut()
        .resource_mut::<InputFocus>()
        .set(original, FocusCause::Navigated);
    app.update();
    let captured = app
        .world_mut()
        .resource_mut::<Captured>()
        .0
        .take()
        .expect("capture reads actual components");
    app.world_mut().despawn(original);
    let replacement = reading(&mut app, root, 0.0);
    app.world_mut()
        .resource_mut::<PendingPosition>()
        .begin(captured);
    app.update();
    app.update();
    assert_eq!(
        app.world().resource::<InputFocus>().get(),
        Some(replacement),
        "focus resolves a stable identity after repaint"
    );
    assert_eq!(
        app.world()
            .get::<ScrollPosition>(replacement)
            .expect("reading scroll")
            .0
            .y,
        160.0,
        "the actual scroll component is restored"
    );
    app.world_mut()
        .get_mut::<ScrollPosition>(replacement)
        .expect("reading scroll")
        .0
        .y = 220.0;
    app.update();
    assert_eq!(
        app.world()
            .get::<ScrollPosition>(replacement)
            .expect("reading scroll")
            .0
            .y,
        220.0,
        "completed restoration does not fight later user scrolling"
    );
}

#[test]
fn missing_focus_uses_a_valid_reading_and_clamps_to_current_geometry() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .init_resource::<InputFocus>()
        .init_resource::<ObserverFocusPolicy>()
        .init_resource::<PendingPosition>()
        .add_systems(Last, restore_position);
    let root = app
        .world_mut()
        .spawn((Node::default(), TabGroup::new(0)))
        .id();
    let target = reading(&mut app, root, 0.0);
    app.world_mut()
        .resource_mut::<PendingPosition>()
        .begin(SavedPosition {
            focus: Some(NavigationFocus::Home),
            entity: None,
            offsets: vec![(ReadingRegion::OrganizerWorkspace, Vec2::new(0.0, 900.0))],
        });
    for _ in 0..8 {
        app.update();
    }
    assert_eq!(
        app.world().resource::<InputFocus>().get(),
        Some(target),
        "a vanished control falls back to a tabbable reading"
    );
    assert_eq!(
        app.world()
            .get::<ScrollPosition>(target)
            .expect("reading scroll")
            .0
            .y,
        300.0,
        "saved offsets are clamped against current layout"
    );
}
