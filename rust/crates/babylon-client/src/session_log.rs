//! Session observability (Director ask 2026-09-04): structured `session`-target
//! events at every player-visible interaction seam, so one play session can be
//! reconstructed from the rotating file log ([`crate::logging`]) alone — what
//! county was selected, what page was requested, what the card installed, and
//! why a fetch failed.
//!
//! **Why a plugin of observers, not log lines inside each system**: the
//! interaction systems own Bevy's 7-parameter shape and stay pure projections
//! (see `ui::dossier_card`); bolting `log::info!` into them would spend their
//! parameter budget and mix presentation with telemetry. Change-detection
//! (`Res::is_changed`) and a second [`MessageReader`] over the same resources
//! and messages observe the exact same bytes without touching them — the log
//! can never lie about what the renderer saw, because it reads what the
//! renderer read.
//!
//! **Levels**: interaction events are `INFO` (the session narrative; the file
//! lane captures them and the stderr lane mirrors them). Nothing here logs per
//! frame or per tick — quiet systems stay quiet. **No wall-clock in events**:
//! the fmt layer timestamps each line, exactly as [`crate::logging`] mandates.

use bevy::prelude::*;

use crate::atlas::CountyAtlas;
use crate::map::SelectedCounty;
use crate::ui::dossier_card::{
    ActiveCountyDossier, DossierCampaignId, DossierFetchState, DossierPageView, SubjectPageRequest,
};

/// Wires the session observers into an `App`. Added to the windowed build
/// after [`crate::ui::dossier_card::DossierCardPlugin`] so its message
/// registration exists; every observer tolerates a missing resource family so
/// headless test compositions can add this plugin alone.
pub struct SessionLogPlugin;

impl Plugin for SessionLogPlugin {
    fn build(&self, app: &mut App) {
        app.add_message::<SubjectPageRequest>()
            .init_resource::<SelectedCounty>()
            .init_resource::<ActiveCountyDossier>()
            .init_resource::<DossierPageView>()
            .init_resource::<DossierFetchState>()
            .add_systems(Startup, log_session_start)
            .add_systems(
                Update,
                (
                    log_selection_changes,
                    log_subject_page_requests,
                    log_dossier_projection_changes,
                    log_page_view_changes,
                    log_fetch_state_changes,
                ),
            );
    }
}

/// `Startup`: the session's frame of reference — which campaign the dossier
/// surfaces read under.
fn log_session_start(campaign: Option<Res<DossierCampaignId>>) {
    match campaign {
        Some(campaign) => {
            bevy::log::info!(target: "session", "session start campaign={:?}", campaign.0.as_uuid());
        }
        None => {
            bevy::log::info!(target: "session", "session start campaign=<dossier surfaces absent>");
        }
    }
}

/// `Update`: county selection changes — the player's map clicks.
fn log_selection_changes(selected: Res<SelectedCounty>, atlas: Option<Res<CountyAtlas>>) {
    if selected.is_added() || !selected.is_changed() {
        return;
    }
    let Some(index) = selected.0 else {
        bevy::log::info!(target: "session", "county selection cleared");
        return;
    };
    if let Some(county) = atlas.as_deref().and_then(|atlas| atlas.county(index)) {
        bevy::log::info!(
            target: "session",
            "county selected fips={} name={:?}",
            county.fips,
            county.name
        );
    } else {
        bevy::log::info!(
            target: "session",
            "county selected index={index} (outside the atlas)"
        );
    }
}

/// `Update`: place-chip clicks — one line per requested subject page, with the
/// label only when the Archive acknowledged one (`None` carries zero label
/// bytes below the fog, and the log honors that).
fn log_subject_page_requests(mut requests: MessageReader<SubjectPageRequest>) {
    for request in requests.read() {
        if let Some(label) = &request.label {
            bevy::log::info!(
                target: "session",
                "subject page requested kind={} id={} label={:?}",
                request.kind,
                request.id,
                label
            );
        } else {
            bevy::log::info!(
                target: "session",
                "subject page requested kind={} id={} label=<fog>",
                request.kind,
                request.id
            );
        }
    }
}

/// `Update`: dossier projection installs and clears — what the card actually
/// composed from, at field-count resolution (the atoms themselves stay in the
/// Archive; the log records that they arrived).
fn log_dossier_projection_changes(projection: Res<ActiveCountyDossier>) {
    if projection.is_added() || !projection.is_changed() {
        return;
    }
    if let Some(card) = &projection.0 {
        bevy::log::info!(
            target: "session",
            "dossier installed geoid={} title={:?} atoms={} places={} changelog={} durable={:?} verified={:?}",
            card.geoid,
            card.title,
            card.atoms.len(),
            card.places.len(),
            card.changelog.len(),
            card.durable_tick,
            card.verified_tick
        );
    } else {
        bevy::log::info!(target: "session", "dossier cleared");
    }
}

/// `Update`: which page the card renders — the county card itself or one R6
/// placeholder.
fn log_page_view_changes(view: Res<DossierPageView>) {
    if view.is_added() || !view.is_changed() {
        return;
    }
    if let DossierPageView::Placeholder(request) = &*view {
        bevy::log::info!(
            target: "session",
            "page view: placeholder kind={} id={}",
            request.kind,
            request.id
        );
    } else {
        bevy::log::info!(target: "session", "page view: county card");
    }
}

/// `Update`: the fetch lifecycle, so a card that shows "Archive reader not
/// configured" or a hard failure is explained by the log line that precedes
/// it.
fn log_fetch_state_changes(state: Res<DossierFetchState>) {
    if state.is_added() || !state.is_changed() {
        return;
    }
    match &*state {
        DossierFetchState::Idle => bevy::log::info!(target: "session", "dossier fetch: idle"),
        DossierFetchState::InFlight { fips, .. } => {
            bevy::log::info!(target: "session", "dossier fetch started fips={fips}");
        }
        DossierFetchState::Failed(error) => {
            bevy::log::info!(target: "session", "dossier fetch failed: {error:?}");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::logging::RotatingSink;
    use crate::ui::dossier_card::{CountyDossierCardProjection, DossierFetchError};
    use bevy::log::tracing_subscriber::layer::SubscriberExt as _;
    use std::path::PathBuf;

    const ATLAS_BYTES: &[u8] = include_bytes!("../assets/map/county_atlas.bin");

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "babylon-session-logtest-{tag}-{}",
            std::process::id()
        ));
        std::fs::remove_dir_all(&dir).ok();
        std::fs::create_dir_all(&dir).expect("test log dir");
        dir
    }

    /// Boot the session app with the REAL rotating sink + fmt layer as the
    /// subscriber (never a copied pipeline), run one baseline update (Startup
    /// plus the observers' added-tick guard), then `drive` the interaction and
    /// one more update, and return the live file's contents. The schedules run
    /// single-threaded so the thread-local subscriber captures every system —
    /// the default multi-threaded executor would run them on the global
    /// `ComputeTaskPool`, where `with_default` does not reach.
    fn run_session_app(dir: &std::path::Path, drive: impl Fn(&mut App)) -> String {
        let sink = RotatingSink::open(dir, 1024 * 1024, 2).expect("sink opens");
        let layer = bevy::log::tracing_subscriber::fmt::Layer::default()
            .with_ansi(false)
            .with_writer(sink);
        let subscriber = bevy::log::tracing_subscriber::registry().with(layer);
        let mut app = App::new();
        app.add_plugins(SessionLogPlugin)
            .insert_resource(CountyAtlas::parse(ATLAS_BYTES).expect("committed atlas parses"));
        app.edit_schedule(Startup, |schedule| {
            schedule.set_executor_kind(bevy::ecs::schedule::ExecutorKind::SingleThreaded);
        });
        app.edit_schedule(Update, |schedule| {
            schedule.set_executor_kind(bevy::ecs::schedule::ExecutorKind::SingleThreaded);
        });
        bevy::log::tracing::subscriber::with_default(subscriber, || {
            app.update();
            drive(&mut app);
            app.update();
        });
        std::fs::read_to_string(dir.join("babylon-client.log")).expect("live log")
    }

    #[test]
    fn a_full_interaction_sequence_lands_in_the_file_log() {
        let dir = temp_dir("sequence");
        let log = run_session_app(&dir, |app| {
            let wayne = app
                .world()
                .resource::<CountyAtlas>()
                .index_of_fips("26163")
                .expect("the committed atlas carries Wayne County");
            app.world_mut().resource_mut::<SelectedCounty>().0 = Some(wayne);
            app.world_mut()
                .resource_mut::<Messages<SubjectPageRequest>>()
                .write(SubjectPageRequest {
                    kind: "place".to_owned(),
                    id: "2674900".to_owned(),
                    label: None,
                });
            *app.world_mut().resource_mut::<DossierPageView>() =
                DossierPageView::Placeholder(SubjectPageRequest {
                    kind: "place".to_owned(),
                    id: "2674900".to_owned(),
                    label: None,
                });
            app.world_mut().resource_mut::<ActiveCountyDossier>().0 =
                Some(CountyDossierCardProjection {
                    geoid: "26163".to_owned(),
                    title: "Wayne County".to_owned(),
                    durable_tick: Some(2),
                    verified_tick: Some(1),
                    atoms: Vec::new(),
                    places: Vec::new(),
                    changelog: Vec::new(),
                });
        });
        assert!(log.contains("session start campaign="), "startup: {log}");
        assert!(
            log.contains("county selected fips=26163"),
            "selection: {log}"
        );
        assert!(
            log.contains("subject page requested kind=place id=2674900 label=<fog>"),
            "chip: {log}"
        );
        assert!(
            log.contains("page view: placeholder kind=place id=2674900"),
            "view: {log}"
        );
        assert!(
            log.contains("dossier installed geoid=26163 title=\"Wayne County\" atoms=0 places=0 changelog=0 durable=Some(2) verified=Some(1)"),
            "install: {log}"
        );
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn clearing_the_selection_and_failing_a_fetch_are_logged_honestly() {
        let dir = temp_dir("clear-fail");
        let log = run_session_app(&dir, |app| {
            app.world_mut().resource_mut::<SelectedCounty>().0 = Some(usize::MAX);
            app.update();
            app.world_mut().resource_mut::<SelectedCounty>().0 = None;
            *app.world_mut().resource_mut::<DossierFetchState>() = DossierFetchState::Failed(
                DossierFetchError::ReaderAbsent("BABYLON_READER_DSN unset".to_owned()),
            );
        });
        assert!(
            log.contains("county selected index=18446744073709551615 (outside the atlas)"),
            "select: {log}"
        );
        assert!(log.contains("county selection cleared"), "clear: {log}");
        assert!(
            log.contains("dossier fetch failed: ReaderAbsent"),
            "fail: {log}"
        );
        std::fs::remove_dir_all(&dir).ok();
    }
}
