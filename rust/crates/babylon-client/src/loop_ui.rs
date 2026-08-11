//! The B2 tick loop's own UI plumbing: Space advances the tick, a text
//! node shows the counter and the deterministic hash — the honesty proof
//! (III.7) rendered where the player can see it move.
//!
//! **Mechanical fixes, recorded rather than silently applied.**
//!
//! 1. The plan's own code for this task writes
//!    `mut lens_changed: EventWriter<crate::map::LensChanged>`. Bevy 0.18
//!    renamed the whole buffered pub/sub family (`map/bands.rs`'s own
//!    module doc has the full citation): `LensChanged` is a `Message`,
//!    read/written through `MessageReader`/`MessageWriter` — the
//!    `.write(...)` method call the plan's own code already uses is
//!    unchanged, since that method name carried over to the new API.
//! 2. The plan's own code constructs `crate::map::CurrentLensData { .. }`.
//!    `CurrentLensData` (and `LensReading`) are declared in `lens.rs`
//!    (Task 8's own File Structure entry), never re-exported through
//!    `map` — the correct path is `crate::lens::CurrentLensData`.
//! 3. `recolor_on_lens_changed`/`hud::refresh_hud` were deferred out of
//!    `MapPlugin` (Task 12's own recorded deviation, `map/mod.rs`'s module
//!    doc) precisely because they need `CurrentLensData`, which
//!    `TickLoopPlugin` is what actually provides — this plugin registers
//!    both, re-exported `pub(crate)` from `map` for exactly this purpose.

use crate::engine_link::EngineSession;
use bevy::prelude::*;

#[derive(Resource, Default)]
pub struct TickCounter(pub i64);

#[derive(Component)]
pub struct HashReadout;

#[derive(Component)]
pub struct TickCounterReadout;

pub struct TickLoopPlugin;

impl Plugin for TickLoopPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(TickCounter::default());
        // `.after(map::spawn_map_surface)`: this system fires the FIRST
        // `LensChanged` at tick 0, and `recolor_on_lens_changed` reads the
        // `MapSurface` resource `MapPlugin`'s OWN Startup system creates.
        // Bevy does not order same-schedule systems by plugin-registration
        // order alone — this ordering constraint must be explicit, not
        // implied by `main.rs` listing `MapPlugin` before `TickLoopPlugin`.
        app.add_systems(
            Startup,
            spawn_engine_session_and_hud.after(crate::map::spawn_map_surface),
        );
        app.add_systems(Update, (advance_on_space, refresh_readouts).chain());
        // Deferred here from MapPlugin (Task 12's recorded deviation) —
        // both need Res<CurrentLensData>, which spawn_engine_session_and_hud
        // (above) inserts at Startup, strictly before either can run as an
        // Update system.
        app.add_systems(
            Update,
            (crate::map::recolor_on_lens_changed, crate::map::refresh_hud),
        );
    }
}

fn spawn_engine_session_and_hud(
    mut commands: Commands,
    mut lens_changed: MessageWriter<crate::map::LensChanged>,
) {
    let session =
        EngineSession::start().unwrap_or_else(|e| panic!("engine session failed to start: {e}"));
    // Tick 0's own LensReadings — the map must show something correct
    // (or correctly absent) on first launch, before any Space press. The
    // Population Trend reading is `Some(0.0)` (DIM) everywhere at this
    // point, since `population_baseline` IS the tick-0 state — real
    // divergence appears only after the first `advance()`.
    let lens_data = crate::lens::CurrentLensData {
        tension: crate::lens::county_tension(session.inner.graph()),
        legitimation: crate::lens::county_legitimation(
            session.inner.graph(),
            &session.node_by_fips,
        ),
        population_trend: crate::lens::county_population_trend(
            session.inner.graph(),
            &session.node_by_fips,
            &session.population_baseline,
        ),
    };
    commands.insert_resource(lens_data);
    commands.insert_resource(session);
    lens_changed.write(crate::map::LensChanged);
    commands.spawn((
        Text::new("tick 0"),
        TextColor(crate::palette::BONE),
        Node {
            position_type: PositionType::Absolute,
            bottom: px(24),
            right: px(24),
            ..default()
        },
        TickCounterReadout,
    ));
    commands.spawn((
        Text::new("hash: (not yet run)"),
        TextColor(crate::palette::DIM),
        Node {
            position_type: PositionType::Absolute,
            bottom: px(4),
            right: px(24),
            ..default()
        },
        HashReadout,
    ));
}

fn advance_on_space(
    keys: Res<ButtonInput<KeyCode>>,
    mut session: ResMut<EngineSession>,
    mut counter: ResMut<TickCounter>,
    mut lens_data: ResMut<crate::lens::CurrentLensData>,
    mut lens_changed: MessageWriter<crate::map::LensChanged>,
    mut hud_tick: ResMut<crate::map::HudTick>,
) {
    if !keys.just_pressed(KeyCode::Space) {
        return;
    }
    session
        .advance()
        .unwrap_or_else(|e| panic!("tick advance failed: {e}"));
    counter.0 = session.inner.tick();
    hud_tick.0 = session.inner.tick();
    // Recompute all THREE LensReadings against the POST-tick graph before
    // firing LensChanged — the recolor system only ever reads whatever is
    // already in CurrentLensData when the event fires, so a press that
    // advanced the tick but never refreshed this resource would leave the
    // map showing stale (or, on the very first press, entirely absent)
    // data forever. This is the wiring that makes "watch state change"
    // literally true rather than merely possible.
    lens_data.tension = crate::lens::county_tension(session.inner.graph());
    lens_data.legitimation =
        crate::lens::county_legitimation(session.inner.graph(), &session.node_by_fips);
    lens_data.population_trend = crate::lens::county_population_trend(
        session.inner.graph(),
        &session.node_by_fips,
        &session.population_baseline,
    );
    lens_changed.write(crate::map::LensChanged);
}

fn refresh_readouts(
    counter: Res<TickCounter>,
    session: Res<EngineSession>,
    mut tick_text: Query<&mut Text, (With<TickCounterReadout>, Without<HashReadout>)>,
    mut hash_text: Query<&mut Text, With<HashReadout>>,
) {
    if !counter.is_changed() {
        return;
    }
    if let Ok(mut t) = tick_text.single_mut() {
        t.0 = format!("tick {}", counter.0);
    }
    if let Ok(mut h) = hash_text.single_mut() {
        // The last hash this session computed — sink carries no hash, so
        // read it back off the session's own last report by re-deriving
        // from the graph directly (state_hash is cheap at this scale, see
        // the Global Constraints Scale Note — 18 nodes, 0 hyperedges).
        if let Ok(hash) =
            babylon_graph::state_hash::CanonicalState::state_hash(session.inner.graph())
        {
            h.0 = format!("hash: {}", babylon_tick::hex(&hash));
        }
    }
}
