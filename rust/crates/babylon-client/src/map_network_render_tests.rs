//! The ordinary unavailable heading must contain every wrapped native glyph.

use super::NetworkProjection;
use crate::observer_ui::{NetworkSector, ObserverUiState};
use crate::production::PrimaryView;
use bevy::prelude::*;
use bevy::text::TextLayoutInfo;

#[test]
fn rendered_unavailable_network_notice_fits_above_its_divider_at_all_native_fits() {
    for (viewport, larger, scale) in [
        (UVec2::new(1366, 768), false, 1.0),
        (UVec2::new(1366, 768), true, 1.15),
        (UVec2::new(1920, 1080), false, 1.25),
        (UVec2::new(1920, 1080), true, 1.4375),
    ] {
        let (mut app, font) = crate::test_support::ui_text_app();
        {
            let world = app.world_mut();
            let mut cameras = world.query::<&mut Camera>();
            let mut camera = cameras.single_mut(world).expect("UI camera");
            camera
                .computed
                .target_info
                .as_mut()
                .expect("target")
                .physical_size = viewport;
            camera.viewport.as_mut().expect("viewport").physical_size = viewport;
        }
        app.init_asset::<Image>()
            .init_asset::<TextureAtlasLayout>()
            .insert_resource(PrimaryView::Map)
            .insert_resource(super::super::tests::fixture().0)
            .insert_resource(ObserverUiState {
                larger_interface: larger,
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .add_systems(
                PostUpdate,
                bevy::ui::widget::text_system.after(bevy::ui::ui_layout_system),
            );
        crate::observer_ui::tests::install_resource_header_fixture(&mut app, viewport);
        let leaf = app
            .world_mut()
            .spawn(super::heading_bundle(
                &NetworkProjection::default(),
                NetworkSector::All,
            ))
            .id();
        app.world_mut()
            .get_mut::<TextFont>(leaf)
            .expect("body font")
            .font = font.into();
        app.finish();
        app.cleanup();
        for _ in 0..6 {
            app.update();
        }
        assert_eq!(app.world().resource::<UiScale>().0, scale);
        let node = app
            .world()
            .get::<ComputedNode>(leaf)
            .expect("measured heading");
        let layout = app
            .world()
            .get::<TextLayoutInfo>(leaf)
            .expect("actual glyphs");
        assert!(!layout.glyphs.is_empty());
        let transform = app
            .world()
            .get::<UiGlobalTransform>(leaf)
            .expect("notice transform")
            .affine();
        let bottom = transform.translation.y + node.size().y * 0.5 - node.border().max_inset.y;
        for glyph in &layout.glyphs {
            let max = transform.transform_point2(
                node.content_box().min + glyph.position + glyph.atlas_info.rect.size() * 0.5,
            );
            assert!(
                max.y <= bottom + 1.0,
                "notice glyph {max:?} crosses divider {bottom}; size {:?}",
                node.size()
            );
        }
    }
}
