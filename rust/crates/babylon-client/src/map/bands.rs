//! Presentation color constants for the county map that live outside the
//! §9b role palette (`crate::palette`).
//!
//! **F4 fix (adversarial verification of PR #490).** The first cut
//! declared `PANEL` as a private `const` inline in `map/mesh.rs`. That
//! bypassed `tests/unit/render/test_rust_theme_parity.py`'s §9b parity
//! guard, which reads only `palette.rs` — not a false pass on `PANEL`
//! itself (`PANEL` is deliberately not a §9b token, so the guard was never
//! supposed to claim it), but a genuine gap: nothing watched for a STRAY
//! `Color::srgb_u8`/`Color::srgb` literal added to any OTHER file in this
//! crate. Two things close that gap: (1) `PANEL` now lives here, in the
//! file the B1 plan's Task 9 (Phase C, out of scope for this PR) is
//! specced to create and extend with the four-band diverging tension
//! channel (`pub fn band_color`, `pub const PANEL`) — so Task 9 finds one
//! existing declaration to extend, not a second one to reconcile; (2) the
//! parity guard itself grew a crate-wide sweep
//! (`test_no_stray_color_literals_outside_palette_or_a_declared_exemption`)
//! that fails on any `Color::srgb[_u8]` call outside `palette.rs` unless
//! its file is named in the guard's own `_SWEEP_EXEMPTIONS` registry with
//! a reason — `map/bands.rs` (this file) is that registry's first entry.
//!
//! **B2 Phase C, Task 10 (this edit).** Three band tables — Tension
//! (ADR191 R11's four-band diverging channel, ported unmodified),
//! Legitimation (Director ruling 1: reuses PANEL/DIM/CRIMSON), Population
//! Trend (BLOCKER 2 fix: sign-only, reuses all four tokens) — plus the
//! `ActiveLens`/`LensChanged` types and the one recolor system all three
//! lenses share. No new `Color::srgb[_u8]` literal: `DIM`/`CRIMSON`/`GOLD`
//! come from `crate::palette`, `PANEL` stays declared in this file.
//!
//! **Mechanical fix, recorded rather than silently applied.** The plan's
//! own code for this task spells the county-recolor signal
//! `#[derive(Event)] … EventReader<LensChanged> … EventWriter<LensChanged>`.
//! Bevy 0.18 renamed that whole buffered pub/sub family: `Event`/
//! `EventReader`/`EventWriter`/`App::add_event` are now the
//! *observer/trigger* system (`World::trigger`, `On<T>`); the buffered
//! queue this plugin actually needs is `Message`/`MessageReader`/
//! `MessageWriter`/`App::add_message` (confirmed by reading
//! `bevy_ecs::message`'s module tree and `bevy_ecs::prelude`, which
//! exports `Message`/`MessageReader`/`MessageWriter`/`Messages` but no
//! `EventReader`/`EventWriter` at all). `LensChanged` is declared
//! `#[derive(Message)]` here and read/written through
//! `MessageReader`/`MessageWriter` throughout this plan's remaining tasks
//! — the `.read()`/`.write(...)` method calls the plan's own code already
//! uses are unchanged, since those method names carried over from the old
//! API to the new one.

use bevy::color::{Color, ColorToComponents};
use bevy::prelude::{Message, Resource};

use crate::palette::{CRIMSON, DIM, GOLD};

/// `PANEL` is not a §9b token — the deleted Ratatui client declared
/// `PANEL = Rgb(32, 4, 4)` (`#200404`) locally, with a comment recording
/// that it deliberately misses `MUTED_DARK`. It is the map's "no honest
/// data this tick" absence fill: B1 Task 6 starts every fill vertex here
/// (the map opens honestly empty, no lens data has arrived yet), and
/// Phase C's four-band lens (Task 9) resolves an absent `w` to this same
/// color.
pub const PANEL: Color = Color::srgb_u8(32, 4, 4);

/// ADR191 R11's four-band diverging channel, transcribed verbatim from
/// `src/babylon/projection/topology/map_lenses.py::TENSION_BANDS`:
/// `w <= -0.15` is CRIMSON (Φ-source, bled), `-0.15 < w <= 0.15` is DIM
/// (neither pole), `w > 0.15` is GOLD (Φ-recipient, bribed), and absence is
/// `PANEL` — deliberately distinct from the DIM neutral band so nothing may
/// confuse "no data" with "neither pole."
#[must_use]
pub fn tension_band_color(w: Option<f64>) -> Color {
    match w {
        None => PANEL,
        Some(w) if w <= -0.15 => CRIMSON,
        Some(w) if w <= 0.15 => DIM,
        Some(_) => GOLD,
    }
}

/// Director ruling 1 (quoted in full at the top of this plan): "CRISIS →
/// crimson, UNSTABLE → dim gray, STABLE → gold's absence (panel dark)."
/// `Some(0.0)` (STABLE) and `None` (no data) deliberately render the SAME
/// color — a INVERSION of Tension's own non-confusion rule, intentional
/// per the ruling. The HUD (Task 11) is the only channel that can tell the
/// two apart.
#[must_use]
pub fn legitimation_band_color(class: Option<f64>) -> Color {
    match class {
        Some(0.0) => PANEL,
        Some(1.0) => DIM,
        Some(2.0) => CRIMSON,
        Some(other) => panic!("legitimation_band_color: out-of-encoding class {other}"),
        None => PANEL,
    }
}

/// BLOCKER 2 fix, Director-ruled (ruling ADR194/D97, quoted in full at the
/// end of this plan): "GOLD = growth, CRIMSON = decline, sign-only (no
/// invented threshold)." Unlike Legitimation, this lens's "unchanged"
/// state is NOT meant to look like absence — a genuinely unchanged county
/// is a real, meaningful reading, so `Some(0.0)` gets its own DIM band,
/// distinct from `PANEL`.
#[must_use]
pub fn population_trend_band_color(delta: Option<f64>) -> Color {
    match delta {
        Some(d) if d > 0.0 => GOLD,
        Some(d) if d < 0.0 => CRIMSON,
        Some(_) => DIM, // exactly 0.0 — no real demo tick reaches this
        None => PANEL,
    }
}

/// Which of the three lenses the map currently renders. `Copy` because
/// every reader takes it by value off a `Res<ActiveLens>`.
#[derive(Resource, Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActiveLens {
    Tension,
    Legitimation,
    PopulationTrend,
}

/// Signals that the active lens (or its live data) changed and the fill
/// mesh's vertex colors need repainting. A `Message`, not an `Event` — see
/// this file's module doc for why.
#[derive(Message)]
pub struct LensChanged;

const ATLAS_BYTES: &[u8] = include_bytes!("../../assets/map/county_atlas.bin");

/// One pass, one buffer, no mesh rebuild — reads whichever `LensReading`
/// `ActiveLens` names out of `CurrentLensData` (Task 8) and repaints every
/// county's own vertex range in the fill mesh with that lens's own band
/// function. Re-parses the embedded atlas locally (cheap: `CountyAtlas::parse`
/// is check-then-decode, no tessellation) rather than reaching through a
/// shared index resource, matching `map/camera.rs::spawn_camera`'s own
/// established convention of staying free of same-schedule resource-
/// availability assumptions.
pub(crate) fn recolor_on_lens_changed(
    mut messages: bevy::prelude::MessageReader<LensChanged>,
    active: bevy::prelude::Res<ActiveLens>,
    lens_data: bevy::prelude::Res<crate::lens::CurrentLensData>,
    surface: bevy::prelude::Res<super::MapSurface>,
    mut meshes: bevy::prelude::ResMut<bevy::prelude::Assets<bevy::prelude::Mesh>>,
) {
    if messages.read().next().is_none() {
        return;
    }
    let reading = match *active {
        ActiveLens::Tension => &lens_data.tension,
        ActiveLens::Legitimation => &lens_data.legitimation,
        ActiveLens::PopulationTrend => &lens_data.population_trend,
    };
    let color_fn: fn(Option<f64>) -> Color = match *active {
        ActiveLens::Tension => tension_band_color,
        ActiveLens::Legitimation => legitimation_band_color,
        ActiveLens::PopulationTrend => population_trend_band_color,
    };
    let atlas = crate::atlas::CountyAtlas::parse(ATLAS_BYTES)
        .unwrap_or_else(|e| panic!("county atlas failed to parse: {e}"));
    let Some(mesh) = meshes.get_mut(&surface.fill_mesh) else {
        return;
    };
    let Some(bevy::mesh::VertexAttributeValues::Float32x4(colors)) =
        mesh.attribute_mut(bevy::prelude::Mesh::ATTRIBUTE_COLOR)
    else {
        return;
    };
    for (fips, value) in &reading.cells {
        let Some(county_idx) = atlas.index_of_fips(fips) else {
            continue;
        };
        let (start, end) = surface.tessellation.county_vertex_range[county_idx];
        let rgba = color_fn(*value).to_linear().to_f32_array();
        for v in &mut colors[start as usize..end as usize] {
            *v = rgba;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::atlas::CountyAtlas;
    use crate::lens::{CurrentLensData, LensReading};
    use bevy::asset::AssetPlugin;
    use bevy::prelude::*;

    fn empty_reading() -> LensReading {
        LensReading {
            cells: Vec::new(),
            absent_reason: None,
        }
    }

    // ---- tension_band_color ----

    #[test]
    fn tension_band_color_edges_and_bands() {
        assert_eq!(tension_band_color(Some(-1.0)), CRIMSON);
        assert_eq!(
            tension_band_color(Some(-0.15)),
            CRIMSON,
            "the edge belongs to the band below it"
        );
        assert_eq!(tension_band_color(Some(-0.149)), DIM);
        assert_eq!(tension_band_color(Some(0.0)), DIM);
        assert_eq!(tension_band_color(Some(0.15)), DIM);
        assert_eq!(tension_band_color(Some(0.151)), GOLD);
        assert_eq!(tension_band_color(Some(1.0)), GOLD);
        assert_eq!(tension_band_color(None), PANEL);
    }

    #[test]
    fn tension_band_color_is_a_four_output_step_function() {
        let mut outputs = std::collections::HashSet::new();
        for i in 0..=40 {
            let w = -1.0 + (i as f64) * (2.0 / 40.0);
            outputs.insert(format!("{:?}", tension_band_color(Some(w)).to_srgba()));
        }
        outputs.insert(format!("{:?}", tension_band_color(None).to_srgba()));
        assert_eq!(
            outputs.len(),
            4,
            "expected exactly four distinct colors, got {outputs:?}"
        );
    }

    #[test]
    fn tension_band_color_never_confuses_absence_with_the_neutral_band() {
        assert_ne!(tension_band_color(Some(0.0)), tension_band_color(None));
    }

    // ---- legitimation_band_color ----

    #[test]
    fn legitimation_band_color_maps_the_three_classes() {
        assert_eq!(legitimation_band_color(Some(1.0)), DIM);
        assert_eq!(legitimation_band_color(Some(2.0)), CRIMSON);
    }

    /// Director ruling 1's intentional merge: STABLE and "no data" render
    /// the SAME color on purpose. Asserted EQUAL, not distinct — do not
    /// "fix" this back to the first cut's `GREEN_DARK`/`GOLD` design.
    #[test]
    fn legitimation_stable_and_absence_share_the_same_color_by_ruling() {
        assert_eq!(
            legitimation_band_color(Some(0.0)),
            legitimation_band_color(None)
        );
        assert_eq!(legitimation_band_color(Some(0.0)), PANEL);
    }

    // ---- population_trend_band_color ----

    #[test]
    fn population_trend_band_color_is_sign_only_with_no_size_cutoff() {
        assert_eq!(population_trend_band_color(Some(0.001)), GOLD);
        assert_eq!(population_trend_band_color(Some(1_000_000.0)), GOLD);
        assert_eq!(population_trend_band_color(Some(-0.001)), CRIMSON);
        assert_eq!(population_trend_band_color(Some(-1_000_000.0)), CRIMSON);
        assert_eq!(population_trend_band_color(Some(0.0)), DIM);
        assert_eq!(population_trend_band_color(None), PANEL);
    }

    #[test]
    fn population_trend_never_confuses_unchanged_with_absence() {
        assert_ne!(
            population_trend_band_color(Some(0.0)),
            population_trend_band_color(None)
        );
    }

    // ---- the recolor system ----

    fn known_fips(index: usize) -> String {
        let atlas = CountyAtlas::parse(ATLAS_BYTES).expect("committed atlas parses");
        atlas.county(index).expect("index in range").fips.to_owned()
    }

    #[test]
    fn legitimation_recolor_paints_the_known_cell_and_merges_stable_with_absence() {
        let mut app = App::new();
        app.add_plugins((MinimalPlugins, AssetPlugin::default()));
        app.add_plugins(super::super::MapPlugin);
        app.add_message::<LensChanged>();
        app.add_systems(Update, recolor_on_lens_changed);

        // Both resources `recolor_on_lens_changed` reads must exist BEFORE
        // the first `update()` — `MinimalPlugins` runs Startup and the
        // first Update pass within that same call, and the system param
        // validation panics loudly on a missing resource rather than
        // silently skipping (unlike Bevy's own warn-once-and-skip
        // behavior for an unregistered PLUGIN type).
        let crisis_fips = known_fips(0);
        let stable_fips = known_fips(1);
        let lens_data = CurrentLensData {
            tension: empty_reading(),
            legitimation: LensReading {
                cells: vec![
                    (crisis_fips.clone(), Some(2.0)),
                    (stable_fips.clone(), Some(0.0)),
                ],
                absent_reason: None,
            },
            population_trend: empty_reading(),
        };
        app.insert_resource(lens_data);
        app.insert_resource(ActiveLens::Legitimation);
        app.update(); // Startup: spawn_map_surface, spawn_camera; first Update: no message yet.

        app.world_mut()
            .resource_mut::<Messages<LensChanged>>()
            .write(LensChanged);
        app.update();

        let surface = app.world().resource::<super::super::MapSurface>();
        let atlas = CountyAtlas::parse(ATLAS_BYTES).expect("atlas");
        let crisis_idx = atlas
            .index_of_fips(&crisis_fips)
            .expect("known fips resolves");
        let stable_idx = atlas
            .index_of_fips(&stable_fips)
            .expect("known fips resolves");
        let other_idx = (0..atlas.len())
            .find(|&i| i != crisis_idx && i != stable_idx)
            .expect("atlas has a third county");

        let meshes = app.world().resource::<Assets<Mesh>>();
        let mesh = meshes
            .get(&surface.fill_mesh)
            .expect("fill mesh registered");
        let colors = match mesh
            .attribute(Mesh::ATTRIBUTE_COLOR)
            .expect("mesh carries color")
        {
            bevy::mesh::VertexAttributeValues::Float32x4(c) => c,
            other => panic!("unexpected color attribute shape: {other:?}"),
        };

        let expected_crisis = CRIMSON.to_linear().to_f32_array();
        let expected_stable = PANEL.to_linear().to_f32_array();
        let expected_untouched = PANEL.to_linear().to_f32_array(); // initial fill, never recolored

        let (cs, ce) = surface.tessellation.county_vertex_range[crisis_idx];
        let (ss, se) = surface.tessellation.county_vertex_range[stable_idx];
        let (os, oe) = surface.tessellation.county_vertex_range[other_idx];

        assert!(colors[cs as usize..ce as usize]
            .iter()
            .all(|c| *c == expected_crisis));
        assert!(colors[ss as usize..se as usize]
            .iter()
            .all(|c| *c == expected_stable));
        assert!(colors[os as usize..oe as usize]
            .iter()
            .all(|c| *c == expected_untouched));
        // The intentional merge, at the vertex-color level too, not just
        // the function's return value in isolation.
        assert_eq!(expected_stable, expected_untouched);
    }

    #[test]
    fn population_trend_recolor_shows_growth_gold_and_decline_crimson_and_never_matches_absence() {
        let mut app = App::new();
        app.add_plugins((MinimalPlugins, AssetPlugin::default()));
        app.add_plugins(super::super::MapPlugin);
        app.add_message::<LensChanged>();
        app.add_systems(Update, recolor_on_lens_changed);

        let growing_fips = known_fips(0);
        let declining_fips = known_fips(1);
        let lens_data = CurrentLensData {
            tension: empty_reading(),
            legitimation: empty_reading(),
            population_trend: LensReading {
                cells: vec![
                    (growing_fips.clone(), Some(37.0)),
                    (declining_fips.clone(), Some(-19.0)),
                ],
                absent_reason: None,
            },
        };
        app.insert_resource(lens_data);
        app.insert_resource(ActiveLens::PopulationTrend);
        app.update(); // Startup + first Update pass (no message yet).

        app.world_mut()
            .resource_mut::<Messages<LensChanged>>()
            .write(LensChanged);
        app.update();

        let surface = app.world().resource::<super::super::MapSurface>();
        let atlas = CountyAtlas::parse(ATLAS_BYTES).expect("atlas");
        let growing_idx = atlas
            .index_of_fips(&growing_fips)
            .expect("known fips resolves");
        let declining_idx = atlas
            .index_of_fips(&declining_fips)
            .expect("known fips resolves");

        let meshes = app.world().resource::<Assets<Mesh>>();
        let mesh = meshes
            .get(&surface.fill_mesh)
            .expect("fill mesh registered");
        let colors = match mesh
            .attribute(Mesh::ATTRIBUTE_COLOR)
            .expect("mesh carries color")
        {
            bevy::mesh::VertexAttributeValues::Float32x4(c) => c,
            other => panic!("unexpected color attribute shape: {other:?}"),
        };

        let (gs, ge) = surface.tessellation.county_vertex_range[growing_idx];
        let (ds, de) = surface.tessellation.county_vertex_range[declining_idx];
        let expected_gold = GOLD.to_linear().to_f32_array();
        let expected_crimson = CRIMSON.to_linear().to_f32_array();
        let expected_panel = PANEL.to_linear().to_f32_array();

        assert!(colors[gs as usize..ge as usize]
            .iter()
            .all(|c| *c == expected_gold));
        assert!(colors[ds as usize..de as usize]
            .iter()
            .all(|c| *c == expected_crimson));
        assert_ne!(expected_gold, expected_panel);
        assert_ne!(expected_crimson, expected_panel);
    }
}
