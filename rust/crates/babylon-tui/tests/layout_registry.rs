//! Contract tests for `LayoutRegistry::{register,hit,clear}` (plan Task 14).
//!
//! Pins the hit-test contract the hover/peek foundation depends on:
//! innermost containing rect wins; a tie between equally-sized containing
//! rects goes to whichever was registered last; a point outside every
//! registered rect (or a registry with nothing registered yet, or one just
//! `clear()`-ed) misses with `None`.

use babylon_tui::layout_registry::{LayoutRegistry, WidgetId};
use ratatui::layout::Rect;

#[test]
fn miss_on_an_empty_registry() {
    let registry = LayoutRegistry::new();
    assert_eq!(registry.hit(0, 0), None);
}

#[test]
fn miss_on_a_point_outside_every_registered_rect() {
    let mut registry = LayoutRegistry::new();
    registry.register(
        WidgetId(1),
        Rect::new(0, 0, 10, 10),
        Some("outer".to_string()),
    );
    assert_eq!(registry.hit(50, 50), None);
}

#[test]
fn nested_rects_innermost_wins() {
    let mut registry = LayoutRegistry::new();
    registry.register(
        WidgetId(1),
        Rect::new(0, 0, 20, 20),
        Some("outer".to_string()),
    );
    registry.register(
        WidgetId(2),
        Rect::new(5, 5, 5, 5),
        Some("inner".to_string()),
    );

    let (id, area, entity) = registry
        .hit(6, 6)
        .expect("point (6,6) is inside both rects");
    assert_eq!(*id, WidgetId(2));
    assert_eq!(*area, Rect::new(5, 5, 5, 5));
    assert_eq!(entity.as_deref(), Some("inner"));
}

#[test]
fn nested_rects_innermost_wins_regardless_of_registration_order() {
    let mut registry = LayoutRegistry::new();
    // Inner registered first this time — the rule is area-based, not
    // registration-order-based, so the outcome must not change.
    registry.register(
        WidgetId(2),
        Rect::new(5, 5, 5, 5),
        Some("inner".to_string()),
    );
    registry.register(
        WidgetId(1),
        Rect::new(0, 0, 20, 20),
        Some("outer".to_string()),
    );

    let (id, _, entity) = registry
        .hit(6, 6)
        .expect("point (6,6) is inside both rects");
    assert_eq!(*id, WidgetId(2));
    assert_eq!(entity.as_deref(), Some("inner"));
}

#[test]
fn overlapping_same_size_rects_last_registered_wins() {
    let mut registry = LayoutRegistry::new();
    registry.register(
        WidgetId(1),
        Rect::new(0, 0, 10, 10),
        Some("first".to_string()),
    );
    registry.register(
        WidgetId(2),
        Rect::new(0, 0, 10, 10),
        Some("second".to_string()),
    );

    let (id, _, entity) = registry
        .hit(3, 3)
        .expect("point (3,3) is inside both rects");
    assert_eq!(*id, WidgetId(2));
    assert_eq!(entity.as_deref(), Some("second"));
}

#[test]
fn three_way_tie_last_registered_still_wins() {
    let mut registry = LayoutRegistry::new();
    registry.register(WidgetId(1), Rect::new(0, 0, 4, 4), Some("a".to_string()));
    registry.register(WidgetId(2), Rect::new(0, 0, 4, 4), Some("b".to_string()));
    registry.register(WidgetId(3), Rect::new(0, 0, 4, 4), Some("c".to_string()));

    let (id, _, entity) = registry
        .hit(1, 1)
        .expect("point (1,1) is inside all three rects");
    assert_eq!(*id, WidgetId(3));
    assert_eq!(entity.as_deref(), Some("c"));
}

#[test]
fn cleared_registry_misses_everything() {
    let mut registry = LayoutRegistry::new();
    registry.register(
        WidgetId(1),
        Rect::new(0, 0, 10, 10),
        Some("outer".to_string()),
    );
    assert!(registry.hit(1, 1).is_some());

    registry.clear();

    assert_eq!(registry.hit(1, 1), None);
}

#[test]
fn clear_then_register_starts_a_fresh_frame() {
    let mut registry = LayoutRegistry::new();
    registry.register(
        WidgetId(1),
        Rect::new(0, 0, 10, 10),
        Some("stale".to_string()),
    );
    registry.clear();
    registry.register(
        WidgetId(2),
        Rect::new(0, 0, 5, 5),
        Some("fresh".to_string()),
    );

    let (id, _, entity) = registry
        .hit(1, 1)
        .expect("point (1,1) is inside the fresh rect");
    assert_eq!(*id, WidgetId(2));
    assert_eq!(entity.as_deref(), Some("fresh"));
    // The stale rect's wider bounds are gone — a point that was only ever
    // inside it now misses.
    assert_eq!(registry.hit(7, 7), None);
}

#[test]
fn hit_test_bounds_are_exclusive_on_the_right_and_bottom() {
    let mut registry = LayoutRegistry::new();
    registry.register(
        WidgetId(1),
        Rect::new(0, 0, 10, 10),
        Some("box".to_string()),
    );

    assert!(registry.hit(9, 9).is_some());
    assert_eq!(registry.hit(10, 10), None);
}

#[test]
fn registered_entity_may_be_none() {
    let mut registry = LayoutRegistry::new();
    registry.register(WidgetId(1), Rect::new(0, 0, 10, 10), None);

    let (id, _, entity) = registry.hit(1, 1).expect("point (1,1) is inside the rect");
    assert_eq!(*id, WidgetId(1));
    assert_eq!(*entity, None);
}
