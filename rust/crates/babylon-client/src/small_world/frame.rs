//! The frame builder: a period of the small world as the hypergraph library's frame.
//!
//! Task 5 only proves that the library's plugin runs inside the client; the builder itself
//! is filled in by the next task.

#[cfg(test)]
mod tests {
    use bevy::prelude::*;
    use bevy::time::TimeUpdateStrategy;
    use hypergraph_rs_bevy::{
        FieldConfig, FieldFrame, FieldPlugin, FieldStyles, FieldSystems, Flow, FlowReport,
        FrameRefused, Glyph, Palette, ParticleFrame, ParticleId, ParticleStyle, ShowPeriod,
        StreamStyle,
    };
    use std::num::NonZeroU64;
    use std::time::Duration;

    #[derive(Resource, Default)]
    struct Refusals(Vec<FrameRefused>);

    fn collect(mut refused: MessageReader<FrameRefused>, mut out: ResMut<Refusals>) {
        out.0.extend(refused.read().cloned());
    }

    fn styles() -> FieldStyles {
        FieldStyles {
            particles: vec![ParticleStyle {
                glyph: Glyph::Disc,
                size: 0.3,
                swatch: 0,
            }],
            sets: Vec::new(),
            streams: vec![StreamStyle {
                beat: 0,
                unit: NonZeroU64::MIN,
                full: Glyph::Streak,
                hollow: Glyph::Ring,
                size: 0.1,
                swatch: 0,
                share_drawn: 1.0,
                max_marks: 8,
            }],
            region_outline: None,
        }
    }

    fn palette() -> Palette {
        Palette {
            ramp: [Color::BLACK, Color::WHITE, Color::WHITE],
            no_reading: Color::BLACK,
            swatches: vec![Color::WHITE],
        }
    }

    #[test]
    fn the_library_plugin_runs_in_the_client() {
        let plugin = FieldPlugin::new(
            FieldConfig::three_beats(Duration::from_millis(1_000)),
            styles(),
            palette(),
        )
        .expect("a valid plugin");
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .add_plugins(AssetPlugin::default())
            .init_asset::<Mesh>()
            .init_asset::<Image>()
            .init_asset::<StandardMaterial>()
            .insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_millis(
                10,
            )))
            .init_resource::<Refusals>()
            .add_plugins(plugin)
            .add_systems(Update, collect.after(FieldSystems::Animate));
        app.finish();
        app.cleanup();
        let frame = FieldFrame {
            period: 1,
            particles: vec![ParticleFrame {
                id: "p".to_owned(),
                at: Vec3::new(1.0, 0.1, -1.0),
                style: 0,
            }],
            flows: vec![Flow {
                stream: 0,
                from: Vec3::new(1.0, 0.1, -1.0),
                to: Vec3::new(4.0, 0.1, -1.0),
                amount: 3,
                hollow: false,
            }],
            ..FieldFrame::default()
        };
        app.world_mut().write_message(ShowPeriod(Box::new(frame)));
        for _ in 0..3 {
            app.update();
        }
        assert_eq!(app.world().resource::<Refusals>().0.len(), 0);
        assert_eq!(app.world().resource::<FlowReport>().period, Some(1));
        let mut ids = app.world_mut().query::<&ParticleId>();
        let found: Vec<String> = ids.iter(app.world()).map(|id| id.0.clone()).collect();
        assert_eq!(found, vec!["p".to_owned()]);
    }
}
