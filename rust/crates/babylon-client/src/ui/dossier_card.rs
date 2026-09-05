//! PER-23 Slice 4 (ADR249 R5/R6/R9): the county dossier card — the client's
//! first styled card and its first Gameplay-role
//! [`DecisionSurfaceContract`](crate::decision_surface::DecisionSurfaceContract)
//! row, composed from typed Archive atoms (never stored Markdown, no Markdown
//! parser).
//!
//! **Why a dedicated plugin** (decided once, here): every other `ui` module
//! owns no plugin and wires into `TickLoopPlugin`, but the dossier card owns
//! a whole resource family — campaign identity, fetch state, the typed
//! projection, the page view — and that family must exist identically in the
//! windowed viewer and in headless test compositions riding `MinimalPlugins`.
//! A dedicated `DossierCardPlugin` adds the family in one place; both the
//! production `AppMode::Windowed` build and the headless CI tests add this
//! one plugin. The `AppMode::Headless` dossier CLI keeps its pure-JSONL path
//! (`crate::dossier`) — it answers agent queries, it renders no UI.
//!
//! **Fetch discipline**: a selection change resolves the atlas index to a
//! county FIPS and starts exactly one `AsyncComputeTaskPool` task against
//! the fog-safe reader; completion installs the [`ActiveCountyDossier`]
//! projection and the repaint derives ONLY from that resource — never from
//! the reader, never per frame. Starting a new fetch clears the projection
//! first, so an in-flight card never shows stale data (ADR249 R9's honest
//! pending state). A missing `BABYLON_READER_DSN` is an honest card line
//! ("Archive reader not configured"), never a panic — CI headless tests have
//! no Postgres.

use babylon_persistence::{
    ArchiveAtomSubjectKindV1, ArchiveAtomSubjectV1, ArchiveAtomV1, ArchiveSubjectKindV1,
    CampaignId, SemanticArchiveReaderV1,
};
use bevy::ecs::system::SystemParam;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::prelude::*;
use bevy::tasks::{block_on, AsyncComputeTaskPool, Task};

use crate::atlas::CountyAtlas;
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::dossier::{changelog_rows, effective_verification_tick, ChangelogRow};
use crate::map::SelectedCounty;
use crate::observer::{ObservationContext, ObserverSession};
use crate::observer_focus::{ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate};
use crate::observer_ui::{ObserverFeedback, ObserverUiState};
use crate::palette;
use crate::ui::dossier_compose::{
    atom_value_text, chip_text, chronicle_row_segments, compose_stub, compose_vague,
    dual_tick_segments, signal_atoms, signal_row_segments, DossierSegment, DossierTone, PlaceChip,
    DOSSIER_DECISION_QUESTION, INVESTIGATE_SEALED_CHIP,
};

/// `babylon-runtime`'s default campaign identity (`babylon-runtime.rs`), the
/// fallback when `BABYLON_CAMPAIGN_ID` is unset — the client reads the same
/// campaign the runtime writes by default.
const DEFAULT_CAMPAIGN_UUID: u128 = 0x2810_0000_0000_0000_0000_0000_0000_0001;
const CAMPAIGN_ENV: &str = "BABYLON_CAMPAIGN_ID";

/// The canonical campaign identity the dossier card reads under:
/// `BABYLON_CAMPAIGN_ID` when it is a canonical UUID, else the runtime's
/// pinned default campaign.
#[derive(Resource, Clone, Copy, Debug, PartialEq, Eq)]
pub struct DossierCampaignId(pub CampaignId);

impl Default for DossierCampaignId {
    fn default() -> Self {
        let from_env = std::env::var(CAMPAIGN_ENV).ok().and_then(|raw| {
            if let Ok(uuid) = uuid::Uuid::parse_str(&raw) {
                Some(uuid)
            } else {
                log::warn!("{CAMPAIGN_ENV} is not a canonical UUID; using the default campaign");
                None
            }
        });
        Self(CampaignId::from_uuid(from_env.unwrap_or_else(|| {
            uuid::Uuid::from_u128(DEFAULT_CAMPAIGN_UUID)
        })))
    }
}

/// Identity of the county observation that rendered a navigable Archive chip.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DossierRequestScope {
    /// The Archive campaign read by the card.
    pub campaign: CampaignId,
    /// The selected county whose page supplied the link.
    pub county_geoid: String,
    /// The held-selection refresh generation that supplied the page.
    pub refresh_generation: u64,
    /// Exact observer capability and week, absent only in conformance composition.
    pub observer: Option<ObservationContext>,
}

/// One requested subject page: a place-link chip click. Carries the public
/// kind word, the public subject id, and the resolved label when the Archive
/// acknowledges one (`None` for a fog chip) — everything an R6 placeholder
/// needs, with zero label bytes for the ungranted case.
#[derive(Message, Clone, Debug, PartialEq, Eq)]
pub struct SubjectPageRequest {
    /// Scope captured when the link was rendered; checked again on application.
    pub scope: DossierRequestScope,
    /// Public subject kind word ("place").
    pub kind: String,
    /// Public subject id (the place GEOID).
    pub id: String,
    /// The acknowledged label, or `None` below the fog.
    pub label: Option<String>,
}

/// Which page the card currently renders.
#[derive(Resource, Clone, Debug, PartialEq, Eq, Default)]
pub enum DossierPageView {
    /// The county dossier card itself.
    #[default]
    Card,
    /// An R6 placeholder for one requested subject page.
    Placeholder(SubjectPageRequest),
}

/// The typed county dossier projection the card composes from — Slice 3's
/// `county_dossier_card` JSONL semantics as a typed value: durable tick,
/// verified tick, visible atoms, resolved place chips, and the supersession
/// feed. The SAME resource feeds the windowed viewer and headless tests, so
/// both render identical card text from identical bytes.
#[derive(Clone, Debug, PartialEq)]
pub struct CountyDossierCardProjection {
    /// Five-digit county GEOID.
    pub geoid: String,
    /// The governed county title (the subject atom's text).
    pub title: String,
    /// The durable committed tick, or `None` before any commit.
    pub durable_tick: Option<u64>,
    /// The last page content change, or `None` while unmaterialized.
    pub content_tick: Option<u64>,
    /// Effective verification from page content and the contiguous processed prefix.
    pub verified_tick: Option<u64>,
    /// The position-ordered visible atoms (subject, signals, links).
    pub atoms: Vec<ArchiveAtomV1>,
    /// One chip per link atom, granted or fog.
    pub places: Vec<PlaceChip>,
    /// The supersession feed (ADR249 R9 consequence presentation).
    pub changelog: Vec<ChangelogRow>,
}

/// The projection the card currently renders. `None` while no fetch has
/// completed (or after a restart/selection clear).
#[derive(Resource, Clone, Debug, Default, PartialEq)]
pub struct ActiveCountyDossier(pub Option<CountyDossierCardProjection>);

/// Acknowledged runtime/Archive progress refreshes a held selection.
#[derive(Resource, Debug, Default)]
pub struct DossierRefresh(pub u64);
impl DossierRefresh {
    /// Advances the held-selection refresh generation.
    ///
    /// # Panics
    /// Panics if the refresh generation exhausts `u64`.
    pub fn bump(&mut self) {
        self.0 = self
            .0
            .checked_add(1)
            .expect("dossier refresh generation exhausted");
    }
}

/// Why one dossier fetch failed — the card renders each case honestly.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DossierFetchError {
    /// `BABYLON_READER_DSN` is missing or refused: the card renders "Archive
    /// reader not configured" (the CI headless reality, never a panic).
    ReaderAbsent(String),
    /// The reader admitted the DSN but a read failed mid-fetch.
    ReadFailed(String),
}

impl std::fmt::Display for DossierFetchError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ReaderAbsent(detail) => {
                write!(formatter, "Archive reader not configured ({detail})")
            }
            Self::ReadFailed(detail) => write!(formatter, "Archive fetch failed — {detail}"),
        }
    }
}

/// The fetch lifecycle: idle, one in-flight task per selection change, or the
/// last honest failure.
#[derive(Resource, Debug, Default)]
pub enum DossierFetchState {
    /// No fetch running and none failed.
    #[default]
    Idle,
    /// Current-page Archive queries cannot answer an older viewed week.
    HistoricalUnavailable,
    /// One task running for `fips`; the projection is already cleared.
    InFlight {
        /// The county FIPS being fetched.
        fips: String,
        /// Campaign identity captured when the request started.
        campaign: CampaignId,
        /// Refresh generation captured when the request started.
        generation: u64,
        /// The reader task (dropping it cancels the fetch).
        task: Task<Result<CountyDossierCardProjection, DossierFetchError>>,
    },
    /// The last fetch failed; the card renders the reason.
    Failed(DossierFetchError),
}

/// Runs the Slice 3 reader assembly against one county: durable tick, card
/// atoms, one title-scoped known-only search pass (county verified tick plus
/// place labels), place chips, and the supersession feed. Never called on
/// the main thread — only from the fetch task.
fn fetch_county_dossier(
    campaign: CampaignId,
    fips: &str,
) -> Result<CountyDossierCardProjection, DossierFetchError> {
    let read = |error: babylon_persistence::SemanticArchiveReaderErrorV1| {
        DossierFetchError::ReadFailed(error.to_string())
    };
    let reader = SemanticArchiveReaderV1::from_env()
        .map_err(|error| DossierFetchError::ReaderAbsent(error.to_string()))?;
    let durable_tick = reader
        .committed_tick_status(campaign)
        .map_err(read)?
        .map(|status| status.resolve_tick());
    let processed_tick = reader
        .archive_verification_status(campaign)
        .map_err(read)?
        .map(|status| status.processed_tick());
    let atoms = reader.county_card_atoms(campaign, fips).map_err(read)?;
    let title = atoms
        .iter()
        .find(|atom| atom.signal_key() == "subject")
        .and_then(|atom| match atom.value() {
            babylon_persistence::ArchiveAtomValueV1::Text(text) => Some(text.clone()),
            _ => None,
        })
        .unwrap_or_default();

    // One title-scoped known-only search pass resolves the county hit
    // (verified tick) and the place titles behind the link atoms — the same
    // single-pass discipline as the Slice 3 JSONL path.
    let hits = reader.search_known(campaign, &title, 50).map_err(read)?;
    let content_tick = hits
        .iter()
        .find(|hit| {
            hit.page_ref().kind() == ArchiveSubjectKindV1::County && hit.page_ref().id() == fips
        })
        .map(babylon_persistence::ArchiveSearchHitV1::verified_tick);
    let verified_tick = effective_verification_tick(content_tick, processed_tick);
    let places = atoms
        .iter()
        .filter_map(crate::dossier::place_link_geoid)
        .map(|geoid| {
            let hit = hits.iter().find(|hit| {
                hit.page_ref().kind() == ArchiveSubjectKindV1::Place && hit.page_ref().id() == geoid
            });
            match hit {
                Some(hit) => PlaceChip::known(
                    geoid,
                    hit.title().to_owned(),
                    // Pending = the place page's verified tick sits behind
                    // the durable tail: the Archive is still materializing
                    // that page (decision 2's honest lag state).
                    durable_tick.is_some_and(|durable| {
                        processed_tick
                            .unwrap_or(hit.verified_tick())
                            .max(hit.verified_tick())
                            < durable
                    }),
                ),
                None => PlaceChip::unknown(geoid),
            }
        })
        .collect::<Vec<_>>();

    let subject = ArchiveAtomSubjectV1::try_new(ArchiveAtomSubjectKindV1::County, fips.to_owned())
        .map_err(|error| DossierFetchError::ReadFailed(error.to_string()))?;
    let history = reader
        .subject_atom_history(campaign, &subject)
        .map_err(read)?;
    Ok(CountyDossierCardProjection {
        geoid: fips.to_owned(),
        title,
        durable_tick,
        content_tick,
        verified_tick,
        atoms,
        places,
        changelog: changelog_rows(&history),
    })
}

// ---- Card chrome ----

/// Which zone of the card one entity renders. One marker per zone so the
/// repaint finds its targets and headless tests can assert the whole zone
/// tree exists and renders the expected text (the same pub-marker pattern
/// `ui::countdown::CountdownPaneText` and friends use).
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub enum DossierZone {
    /// The county title line.
    Title,
    /// The ADR249 decision question, one per display.
    Question,
    /// The durable/verified dual-tick honesty header (R9).
    DualTick,
    /// The signal atom rows.
    Signals,
    /// The place-link chips.
    Places,
    /// The supersession feed.
    Chronicle,
    /// The actions footer (the sealed Investigate chip).
    Actions,
}

/// The card root marker.
#[derive(Component, Debug)]
pub struct DossierCardRoot;

/// A place-link chip entity; also carries the base border color so the
/// hover-out observer can restore it without re-deriving chip state.
#[derive(Component, Clone, Debug)]
struct PlaceChipNode {
    request: SubjectPageRequest,
    base_border: Color,
}

const CARD_SURFACE: SurfaceId = SurfaceId::CountyDossier;

fn tone_color(tone: DossierTone) -> Color {
    match tone {
        DossierTone::Bone => palette::BONE,
        DossierTone::BoneDim => palette::BONE.with_alpha(0.7),
        DossierTone::Gold => palette::GOLD,
        DossierTone::Crimson => palette::CRIMSON,
        DossierTone::Dim => palette::DIM,
    }
}

fn section_header(text: &str) -> impl Bundle {
    (
        Text::new(text),
        TextColor(palette::GOLD),
        TextFont {
            font_size: 11.0,
            ..default()
        },
        DeclaredSurface::new(CARD_SURFACE),
    )
}

fn gold_rule() -> impl Bundle {
    (
        Node {
            width: percent(100),
            height: px(1),
            ..default()
        },
        BackgroundColor(palette::GOLD.with_alpha(0.25)),
    )
}

/// `Startup` system: spawns the right-docked dossier card chrome — the
/// client's first styled card (FIELD panel, gold hairline border, soft
/// shadow, gold rules between zones), with every zone present but empty;
/// the repaint fills zones from resources.
fn spawn_dossier_card(mut commands: Commands) {
    let zone = |kind: DossierZone| (kind, DeclaredSurface::new(CARD_SURFACE));
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                right: px(24),
                top: px(24),
                bottom: px(24),
                width: px(384),
                flex_direction: FlexDirection::Column,
                row_gap: px(12),
                padding: UiRect::all(px(16)),
                border: UiRect::all(px(1)),
                border_radius: BorderRadius::all(px(6)),
                ..default()
            },
            BackgroundColor(palette::FIELD.with_alpha(0.93)),
            BorderColor::all(palette::GOLD.with_alpha(0.35)),
            BoxShadow::new(Color::BLACK.with_alpha(0.5), px(0), px(4), px(0), px(8)),
            ZIndex(5),
            Visibility::Hidden,
            DeclaredSurface::new(CARD_SURFACE),
            DossierCardRoot,
            TabGroup::new(20),
        ))
        .with_children(|card| {
            card.spawn((
                Text::new(""),
                TextColor(palette::BONE),
                TextFont {
                    font_size: 24.0,
                    ..default()
                },
                zone(DossierZone::Title),
                ObserverFocusTarget::reading(None),
            ));
            card.spawn((
                Text::new(""),
                TextColor(palette::GOLD),
                TextFont {
                    font_size: 13.0,
                    ..default()
                },
                zone(DossierZone::Question),
            ));
            card.spawn((
                Text::new(""),
                TextFont::default(),
                zone(DossierZone::DualTick),
            ));
            card.spawn(gold_rule());
            card.spawn(section_header("S I G N A L S"));
            card.spawn((
                Text::new(""),
                TextFont::default(),
                zone(DossierZone::Signals),
            ));
            card.spawn(gold_rule());
            card.spawn(section_header("P L A C E S"));
            card.spawn((
                Node {
                    flex_direction: FlexDirection::Row,
                    flex_wrap: FlexWrap::Wrap,
                    column_gap: px(6),
                    row_gap: px(6),
                    ..default()
                },
                zone(DossierZone::Places),
            ));
            card.spawn(gold_rule());
            card.spawn(section_header("C H R O N I C L E"));
            card.spawn((
                Text::new(""),
                TextFont::default(),
                zone(DossierZone::Chronicle),
            ));
            card.spawn(gold_rule());
            // Actions footer: the visibly-unavailable Investigate chip.
            card.spawn((
                Node {
                    align_self: AlignSelf::FlexEnd,
                    padding: UiRect::axes(px(8), px(4)),
                    border: UiRect::all(px(1)),
                    border_radius: BorderRadius::all(px(4)),
                    ..default()
                },
                BorderColor::all(palette::DIM),
                zone(DossierZone::Actions),
            ))
            .with_child((
                Text::new(INVESTIGATE_SEALED_CHIP),
                TextColor(palette::DIM),
                TextFont {
                    font_size: 11.0,
                    ..default()
                },
                DeclaredSurface::new(CARD_SURFACE),
            ));
        });
}

/// `Update` system: a selection change resolves the atlas index to a county
/// FIPS and starts exactly one fetch task; the projection and page view are
/// cleared first so in-flight never renders stale data. `None` (deselect,
/// restart) returns the fetch state to `Idle`.
// Bevy injects the independent selection context and fetch outputs separately.
#[allow(clippy::too_many_arguments)]
fn drive_dossier_fetch(
    selected: Res<SelectedCounty>,
    atlas: Res<CountyAtlas>,
    campaign: Res<DossierCampaignId>,
    refresh: Res<DossierRefresh>,
    observer: Option<Res<crate::observer::ObserverSession>>,
    mut historical: Local<bool>,
    mut state: ResMut<DossierFetchState>,
    mut projection: ResMut<ActiveCountyDossier>,
    mut view: ResMut<DossierPageView>,
) {
    let is_historical = observer
        .as_ref()
        .is_some_and(|state| state.viewed_tick != state.durable_tick);
    let history_changed = *historical != is_historical;
    *historical = is_historical;
    if !selected.is_changed() && !campaign.is_changed() && !refresh.is_changed() && !history_changed
    {
        return;
    }
    *view = DossierPageView::Card;
    projection.0 = None;
    // The current Archive reader has current-page semantics. Historical
    // inspection must not install today's dossier beside an older map.
    if is_historical {
        *state = DossierFetchState::HistoricalUnavailable;
        return;
    }
    let Some(index) = selected.0 else {
        *state = DossierFetchState::Idle;
        return;
    };
    let Some(county) = atlas.county(index) else {
        *state = DossierFetchState::Idle;
        return;
    };
    let fips = county.fips.to_owned();
    let fips_for_task = fips.clone();
    let campaign_id = campaign.0;
    let task = AsyncComputeTaskPool::get()
        .spawn(async move { fetch_county_dossier(campaign_id, &fips_for_task) });
    *state = DossierFetchState::InFlight {
        fips,
        campaign: campaign_id,
        generation: refresh.0,
        task,
    };
}

/// `Update` system: polls the in-flight task once per frame; on completion
/// installs the projection (success) or the honest failure (error).
fn collect_dossier_fetch(
    mut state: ResMut<DossierFetchState>,
    mut projection: ResMut<ActiveCountyDossier>,
    campaign: Res<DossierCampaignId>,
    refresh: Res<DossierRefresh>,
    selected: Res<SelectedCounty>,
    atlas: Res<CountyAtlas>,
) {
    let DossierFetchState::InFlight {
        fips,
        campaign: requested_campaign,
        generation,
        ..
    } = &*state
    else {
        return;
    };
    let selected_fips = selected
        .0
        .and_then(|index| atlas.county(index))
        .map(|county| county.fips);
    if *requested_campaign != campaign.0
        || *generation != refresh.0
        || selected_fips != Some(fips.as_str())
    {
        *state = DossierFetchState::Idle;
        projection.0 = None;
        return;
    }
    let expected_fips = fips.clone();
    // Polling an unfinished task is not a UI state change.
    let DossierFetchState::InFlight { task, .. } = state.bypass_change_detection() else {
        unreachable!("validated in-flight state");
    };
    let Some(result) = block_on(bevy::tasks::futures_lite::future::poll_once(task)) else {
        return;
    };
    *state = match result {
        Ok(card) if card.geoid == expected_fips => {
            projection.0 = Some(card);
            DossierFetchState::Idle
        }
        Ok(_) => DossierFetchState::Failed(DossierFetchError::ReadFailed(
            "Archive returned a different county than requested".to_owned(),
        )),
        Err(error) => DossierFetchState::Failed(error),
    };
}

/// Rebuilds one zone entity's content from toned segments: despawn the old
/// children, spawn one `TextSpan` per segment (the client's first span
/// children — per-span color and size).
fn set_segments(commands: &mut Commands, zone: Entity, segments: &[DossierSegment]) {
    commands.entity(zone).despawn_related::<Children>();
    for segment in segments {
        commands.entity(zone).with_child((
            TextSpan::new(segment.text.clone()),
            TextColor(tone_color(segment.tone)),
            TextFont {
                font_size: 14.0,
                ..default()
            },
            DeclaredSurface::new(CARD_SURFACE),
        ));
    }
}

/// Rebuilds one zone entity as a single styled line.
fn set_line(commands: &mut Commands, zone: Entity, text: String, color: Color, font_size: f32) {
    commands.entity(zone).despawn_related::<Children>();
    commands.entity(zone).with_child((
        TextSpan::new(text),
        TextColor(color),
        TextFont {
            font_size,
            ..default()
        },
        DeclaredSurface::new(CARD_SURFACE),
    ));
}

/// Rebuilds one zone entity's children as one multi-segment row per entry
/// (signal rows, chronicle rows) — each row a `Text` with `TextSpan`
/// children.
fn set_segment_rows(commands: &mut Commands, zone: Entity, rows: &[Vec<DossierSegment>]) {
    commands.entity(zone).despawn_related::<Children>().insert((
        Node {
            width: percent(100),
            min_width: px(0),
            max_width: percent(100),
            flex_direction: FlexDirection::Column,
            flex_shrink: 0.0,
            row_gap: px(12),
            ..default()
        },
        TextLayout::new_with_linebreak(bevy::text::LineBreak::WordOrCharacter),
    ));
    for row in rows {
        commands.entity(zone).with_children(|parent| {
            parent
                .spawn((
                    Text::new(""),
                    TextFont {
                        font_size: 14.0,
                        ..default()
                    },
                    TextLayout::new_with_linebreak(bevy::text::LineBreak::WordOrCharacter),
                    Node {
                        width: percent(100),
                        min_width: px(0),
                        max_width: percent(100),
                        flex_shrink: 0.0,
                        ..default()
                    },
                    DeclaredSurface::new(CARD_SURFACE),
                ))
                .with_children(|text| {
                    for segment in row {
                        text.spawn((
                            TextSpan::new(segment.text.clone()),
                            TextColor(tone_color(segment.tone)),
                            TextFont {
                                font_size: if segment.tone == DossierTone::Dim {
                                    11.0
                                } else {
                                    14.0
                                },
                                ..default()
                            },
                            DeclaredSurface::new(CARD_SURFACE),
                        ));
                    }
                });
        });
    }
}

/// Rebuilds the places zone's chip children from the projection's chips.
fn set_chips(
    commands: &mut Commands,
    zone: Entity,
    chips: &[PlaceChip],
    scope: &DossierRequestScope,
) {
    commands.entity(zone).despawn_related::<Children>();
    for chip in chips {
        let (text_color, base_border) = match (chip.is_known(), chip.is_pending()) {
            (true, false) => (palette::BONE, Color::NONE),
            // Pending (Archive lag) and fog chips both render DIM with a DIM
            // border; hover still lifts either to GOLD.
            (true, true) | (false, _) => (palette::DIM, palette::DIM.with_alpha(0.6)),
        };
        let request = chip_request(chip, scope);
        // `with_child` returns the PARENT, so the chip node is spawned inside
        // a `with_children` closure: the observers and the label text must
        // land on the CHIP, not the zone (the tree shape the hover/click
        // observers and the headless harness both depend on).
        commands.entity(zone).with_children(|parent| {
            parent
                .spawn((
                    Node {
                        padding: UiRect::axes(px(8), px(4)),
                        border: UiRect::all(px(1)),
                        border_radius: BorderRadius::all(px(4)),
                        ..default()
                    },
                    BackgroundColor(palette::MUTED_DARK.with_alpha(0.85)),
                    BorderColor::all(base_border),
                    ObserverFocusTarget::action(scope.observer.clone()),
                    PlaceChipNode {
                        request,
                        base_border,
                    },
                    DeclaredSurface::new(CARD_SURFACE),
                ))
                .observe(on_place_chip_click)
                .observe(on_place_chip_over)
                .observe(on_place_chip_out)
                .with_child((
                    Text::new(chip_text(chip)),
                    TextColor(text_color),
                    TextFont {
                        font_size: 13.0,
                        ..default()
                    },
                    DeclaredSurface::new(CARD_SURFACE),
                ));
        });
    }
}

fn chip_request(chip: &PlaceChip, scope: &DossierRequestScope) -> SubjectPageRequest {
    SubjectPageRequest {
        scope: scope.clone(),
        kind: "place".into(),
        id: chip.geoid().into(),
        label: chip
            .is_known()
            .then(|| chip_text(chip).replace(" · pending", "")),
    }
}

#[derive(SystemParam)]
struct DossierReadContext<'w> {
    campaign: Res<'w, DossierCampaignId>,
    refresh: Res<'w, DossierRefresh>,
    selected: Res<'w, SelectedCounty>,
    atlas: Option<Res<'w, CountyAtlas>>,
    projection: Res<'w, ActiveCountyDossier>,
    fetch: Res<'w, DossierFetchState>,
    observer: Option<Res<'w, ObserverSession>>,
    ui: Option<Res<'w, ObserverUiState>>,
}

impl DossierReadContext<'_> {
    fn visible(&self) -> bool {
        self.selected.0.is_some()
            && self.ui.as_ref().is_none_or(|ui| {
                ui.archive_open && !ui.menu_open && !ui.splash_visible && !ui.comparison_open
            })
    }

    fn admits(&self, request: &SubjectPageRequest, view: &DossierPageView) -> bool {
        if !self.visible()
            || *view != DossierPageView::Card
            || !matches!(*self.fetch, DossierFetchState::Idle)
            || request.scope.campaign != self.campaign.0
            || request.scope.refresh_generation != self.refresh.0
        {
            return false;
        }
        match (self.observer.as_ref(), request.scope.observer.as_ref()) {
            (Some(session), Some(scope))
                if session.accepts(scope) && session.viewed_tick == session.durable_tick => {}
            (None, None) => {}
            _ => return false,
        }
        let Some(card) = &self.projection.0 else {
            return false;
        };
        if card.geoid != request.scope.county_geoid {
            return false;
        }
        if let Some(atlas) = &self.atlas {
            if self
                .selected
                .0
                .and_then(|index| atlas.county(index))
                .is_none_or(|county| county.fips != request.scope.county_geoid)
            {
                return false;
            }
        } else if self.observer.is_some() {
            return false;
        }
        card.places
            .iter()
            .any(|chip| chip_request(chip, &request.scope) == *request)
    }
}

#[derive(SystemParam)]
struct DossierRefusal<'w> {
    feedback: Option<ResMut<'w, ObserverFeedback>>,
    time: Option<Res<'w, Time>>,
}

impl DossierRefusal<'_> {
    fn reject(&mut self) {
        if let Some(feedback) = &mut self.feedback {
            feedback.reject(
                "This Archive link belongs to an unavailable observation.",
                self.time
                    .as_ref()
                    .map_or(0.0, |time| time.elapsed_secs_f64()),
            );
        }
    }
}

fn dispatch_place_chip(
    request: &SubjectPageRequest,
    context: &DossierReadContext,
    view: &DossierPageView,
    refusal: &mut DossierRefusal,
    requests: &mut MessageWriter<SubjectPageRequest>,
) {
    if context.admits(request, view) {
        requests.write(request.clone());
    } else {
        refusal.reject();
    }
}

fn on_place_chip_click(
    click: On<Pointer<Click>>,
    chips: Query<&PlaceChipNode>,
    context: DossierReadContext,
    view: Res<DossierPageView>,
    mut refusal: DossierRefusal,
    mut requests: MessageWriter<SubjectPageRequest>,
) {
    if let Ok(chip) = chips.get(click.entity) {
        dispatch_place_chip(&chip.request, &context, &view, &mut refusal, &mut requests);
    }
}

fn keyboard_activate(
    event: On<ObserverKeyboardActivate>,
    chips: Query<&PlaceChipNode>,
    context: DossierReadContext,
    view: Res<DossierPageView>,
    mut refusal: DossierRefusal,
    mut requests: MessageWriter<SubjectPageRequest>,
) {
    let Ok(chip) = chips.get(event.entity) else {
        return;
    };
    if event.context != chip.request.scope.observer {
        refusal.reject();
        return;
    }
    dispatch_place_chip(&chip.request, &context, &view, &mut refusal, &mut requests);
}

type DossierFocusOwners = Or<(With<PlaceChipNode>, With<DossierZone>)>;

fn focus_eligibility(
    context: DossierReadContext,
    view: Res<DossierPageView>,
    mut targets: Query<(&mut ObserverFocusTarget, Option<&PlaceChipNode>), DossierFocusOwners>,
) {
    if !(context.campaign.is_changed()
        || context.refresh.is_changed()
        || context.selected.is_changed()
        || context.projection.is_changed()
        || context.fetch.is_changed()
        || view.is_changed()
        || targets.iter_mut().any(|(target, _)| target.is_added())
        || context
            .observer
            .as_ref()
            .is_some_and(DetectChanges::is_changed)
        || context.ui.as_ref().is_some_and(DetectChanges::is_changed))
    {
        return;
    }
    for (mut target, chip) in &mut targets {
        let mut next = target.clone();
        if let Some(chip) = chip {
            next.context.clone_from(&chip.request.scope.observer);
            next.available = context.admits(&chip.request, &view);
        } else {
            next.available = context.visible()
                && match (&context.observer, &next.context) {
                    (Some(session), Some(scope)) => session.accepts(scope),
                    (None, None) => true,
                    _ => false,
                };
        }
        target.set_if_neq(next);
    }
}

fn on_place_chip_over(
    over: On<Pointer<Over>>,
    mut chips: Query<&mut BorderColor, With<PlaceChipNode>>,
) {
    if let Ok(mut border) = chips.get_mut(over.entity) {
        *border = BorderColor::all(palette::GOLD);
    }
}

fn on_place_chip_out(out: On<Pointer<Out>>, mut chips: Query<(&mut BorderColor, &PlaceChipNode)>) {
    if let Ok((mut border, chip)) = chips.get_mut(out.entity) {
        *border = BorderColor::all(chip.base_border);
    }
}

/// `Update` system: applies pending [`SubjectPageRequest`]s to the page view.
/// Kept separate from [`repaint_dossier_card`] so the painter stays a pure
/// projection of resources.
fn apply_page_requests(
    mut view: ResMut<DossierPageView>,
    mut requests: MessageReader<SubjectPageRequest>,
    context: DossierReadContext,
    mut refusal: DossierRefusal,
) {
    for request in requests.read() {
        if context.admits(request, &view) {
            *view = DossierPageView::Placeholder(request.clone());
        } else {
            refusal.reject();
        }
    }
}

type DossierRoots<'w, 's> = Query<
    'w,
    's,
    (
        Entity,
        &'static mut Visibility,
        &'static mut Node,
        &'static mut BackgroundColor,
        &'static mut BorderColor,
        &'static mut BoxShadow,
    ),
    With<DossierCardRoot>,
>;

/// `Update` system: the pure repaint. Derives every zone's content from
/// [`ActiveCountyDossier`], [`DossierFetchState`], and [`DossierPageView`]
/// only — the same resources in windowed and headless compositions, which is
/// the parity proof. Nothing here touches the reader.
// Independent Bevy resources and disjoint root/zone queries are explicit here.
#[derive(SystemParam)]
struct DossierScopeIdentity<'w> {
    campaign: Res<'w, DossierCampaignId>,
    refresh: Res<'w, DossierRefresh>,
    observer: Option<Res<'w, ObserverSession>>,
}

#[allow(clippy::too_many_arguments)]
fn repaint_dossier_card(
    mut commands: Commands,
    identity: DossierScopeIdentity,
    selected: Res<SelectedCounty>,
    atlas: Option<Res<CountyAtlas>>,
    projection: Res<ActiveCountyDossier>,
    state: Res<DossierFetchState>,
    view: Res<DossierPageView>,
    zones: Query<(Entity, &DossierZone)>,
    observer_ui: Option<Res<crate::observer_ui::ObserverUiState>>,
    mut roots: DossierRoots,
) {
    let Ok((root, mut root_visibility, mut root_node, mut background, mut border, mut shadow)) =
        roots.single_mut()
    else {
        return;
    };
    if let Some(ui) = &observer_ui {
        if ui.is_added() {
            commands
                .entity(root)
                .insert(crate::observer_layout::ObserverRegion::Log);
            root_node.right = Val::Auto;
            root_node.bottom = Val::Auto;
            root_node.min_width = Val::Auto;
            root_node.max_width = Val::Auto;
            root_node.overflow = Overflow::scroll_y();
            root_node.border = UiRect::all(px(2));
            root_node.border_radius = BorderRadius::ZERO;
            *background = BackgroundColor(crate::observer_theme::PANEL);
            *border = BorderColor::all(crate::observer_theme::PAPER);
            *shadow = BoxShadow::default();
        }
    }
    if selected.0.is_none()
        || observer_ui.as_ref().is_some_and(|ui| {
            !ui.archive_open || ui.menu_open || ui.splash_visible || ui.comparison_open
        })
    {
        root_visibility.set_if_neq(Visibility::Hidden);
        return;
    }
    let became_visible = *root_visibility != Visibility::Visible;
    root_visibility.set_if_neq(Visibility::Visible);
    if !became_visible
        && !selected.is_changed()
        && !projection.is_changed()
        && !state.is_changed()
        && !view.is_changed()
    {
        return;
    }

    let county_title = selected
        .0
        .and_then(|index| atlas.as_ref()?.county(index))
        .map(|county| county.name);
    for (entity, zone) in &zones {
        match zone {
            DossierZone::Title => {
                commands.entity(entity).insert(ObserverFocusTarget::reading(
                    identity.observer.as_ref().map(|session| session.context()),
                ));
                paint_title(&mut commands, entity, &view, &projection, county_title);
            }
            DossierZone::Question => {
                paint_question(&mut commands, entity, &view, observer_ui.is_some());
            }
            DossierZone::DualTick => {
                paint_dual_tick(&mut commands, entity, &view, &state, &projection);
            }
            DossierZone::Signals => paint_signals(
                &mut commands,
                entity,
                &view,
                &projection,
                observer_ui.is_some(),
            ),
            DossierZone::Places => {
                paint_places(&mut commands, entity, &view, &projection, &identity);
            }
            DossierZone::Chronicle => paint_chronicle(&mut commands, entity, &view, &projection),
            DossierZone::Actions => {
                if observer_ui.is_some() {
                    commands.entity(entity).despawn_related::<Children>();
                    commands.entity(entity).with_child((
                        Text::new("READ-ONLY ARCHIVE"),
                        TextColor(crate::observer_theme::PAPER),
                        TextFont {
                            font_size: 11.0,
                            ..default()
                        },
                        DeclaredSurface::new(CARD_SURFACE),
                    ));
                }
                // Conformance keeps the sealed action contract. Observer
                // composition exposes only its actual read capability.
            }
        }
    }
}

fn paint_title(
    commands: &mut Commands,
    entity: Entity,
    view: &DossierPageView,
    projection: &ActiveCountyDossier,
    county_title: Option<&str>,
) {
    match view {
        DossierPageView::Card => {
            let title = projection
                .0
                .as_ref()
                .filter(|card| !card.title.is_empty())
                .map_or_else(
                    || county_title.unwrap_or("County Archive").to_owned(),
                    |card| card.title.clone(),
                );
            set_line(commands, entity, title, palette::BONE, 24.0);
        }
        DossierPageView::Placeholder(request) => {
            let title = request
                .label
                .clone()
                .unwrap_or_else(|| format!("unknown {} · {}", request.kind, request.id));
            set_line(commands, entity, title, palette::BONE, 24.0);
        }
    }
}

fn paint_question(commands: &mut Commands, entity: Entity, view: &DossierPageView, observer: bool) {
    let text = match view {
        DossierPageView::Card if observer => {
            "Which cited observations are available for this county?".to_owned()
        }
        DossierPageView::Card => DOSSIER_DECISION_QUESTION.to_owned(),
        DossierPageView::Placeholder(request) => {
            format!("What is known about {} {}?", request.kind, request.id)
        }
    };
    set_line(commands, entity, text, palette::GOLD, 13.0);
}

fn paint_dual_tick(
    commands: &mut Commands,
    entity: Entity,
    view: &DossierPageView,
    state: &DossierFetchState,
    projection: &ActiveCountyDossier,
) {
    match view {
        DossierPageView::Placeholder(_) => set_segments(commands, entity, &[]),
        DossierPageView::Card => match state {
            DossierFetchState::InFlight { .. } => set_segments(
                commands,
                entity,
                &[DossierSegment {
                    text: "Reading cited observations...".to_owned(),
                    tone: DossierTone::Dim,
                }],
            ),
            DossierFetchState::Failed(DossierFetchError::ReaderAbsent(_)) => set_segments(
                commands,
                entity,
                &[DossierSegment {
                    text: "Archive reader not configured".to_owned(),
                    tone: DossierTone::Dim,
                }],
            ),
            DossierFetchState::Failed(error @ DossierFetchError::ReadFailed(_)) => set_segments(
                commands,
                entity,
                &[DossierSegment {
                    text: error.to_string(),
                    tone: DossierTone::Crimson,
                }],
            ),
            DossierFetchState::HistoricalUnavailable => set_segments(
                commands, entity, &[DossierSegment {
                    text: "Historical Archive pages are unavailable. Return Live to inspect current knowledge.".to_owned(),
                    tone: DossierTone::Dim,
                }],
            ),
            DossierFetchState::Idle => {
                let mut segments = projection.0.as_ref().map_or_else(Vec::new, |card| {
                    dual_tick_segments(card.durable_tick, card.verified_tick)
                });
                if let Some(content_tick) = projection.0.as_ref().and_then(|card| card.content_tick) {
                    segments.push(DossierSegment {
                        text: format!("\nContent last changed at tick {content_tick}"),
                        tone: DossierTone::Dim,
                    });
                }
                if projection.0.as_ref().is_none_or(|card| card.atoms.is_empty()) {
                    segments.push(DossierSegment { text: "\nNo cited observations are available for this county.".into(), tone: DossierTone::Dim });
                }
                set_segments(commands, entity, &segments);
            }
        },
    }
}

fn paint_signals(
    commands: &mut Commands,
    entity: Entity,
    view: &DossierPageView,
    projection: &ActiveCountyDossier,
    observer: bool,
) {
    match view {
        DossierPageView::Card => {
            let rows = projection.0.as_ref().map_or_else(Vec::new, |card| {
                signal_atoms(&card.atoms)
                    .map(|atom| {
                        if observer {
                            observer_signal_segments(atom)
                        } else {
                            signal_row_segments(atom)
                        }
                    })
                    .collect::<Vec<_>>()
            });
            set_segment_rows(commands, entity, &rows);
        }
        DossierPageView::Placeholder(request) => {
            // R6(a): containment is the county the place links from —
            // public-record structure the dossier already carries.
            let containment = projection.0.as_ref().map(|card| card.title.clone());
            let mut lines = match (&request.label, &containment) {
                (Some(label), Some(county)) => compose_stub(label, Some(county)),
                (Some(label), None) => compose_stub(label, None),
                (None, _) => compose_vague(&request.kind, &request.id),
            };
            if observer {
                if let Some(reason) = lines.last_mut() {
                    "Further observations are unavailable in this read-only Archive."
                        .clone_into(reason);
                }
            }
            let segments = lines
                .iter()
                .enumerate()
                .map(|(index, line)| DossierSegment {
                    text: if index == 0 {
                        line.clone()
                    } else {
                        format!("\n{line}")
                    },
                    tone: if index == 0 {
                        match &request.label {
                            Some(_) => DossierTone::Bone,
                            None => DossierTone::Dim,
                        }
                    } else {
                        DossierTone::Crimson
                    },
                })
                .collect::<Vec<_>>();
            set_segments(commands, entity, &segments);
        }
    }
}

/// Human labels describe only the governed QCEW source's four exact fields.
/// Keep unknown fields verbatim and retain every citation and raw field key.
fn observer_signal_segments(atom: &ArchiveAtomV1) -> Vec<DossierSegment> {
    use crate::map_economy_lens::EconomyMetric;
    let metric = if atom.citation().source_id()
        == babylon_persistence::michigan_economy::QCEW_ECONOMICS_SOURCE_ID_V1
    {
        match atom.signal_key() {
            "qcew-employment" => Some(EconomyMetric::Employment),
            "qcew-total-annual-wages" => Some(EconomyMetric::Payroll),
            "qcew-average-weekly-wage" => Some(EconomyMetric::WeeklyWage),
            "qcew-establishments" => Some(EconomyMetric::Establishments),
            _ => None,
        }
    } else {
        None
    };
    let value = atom_value_text(atom.value());
    let label = match metric {
        Some(metric) => metric.label(),
        None => atom.signal_key(),
    };
    vec![
        DossierSegment {
            text: format!("{label}\n"),
            tone: DossierTone::BoneDim,
        },
        DossierSegment {
            text: metric.map_or_else(
                || value.clone(),
                |metric| format!("{value} {}", metric.unit()),
            ),
            tone: DossierTone::Bone,
        },
        DossierSegment {
            text: format!(
                "\nSource: {}\nLocator: {}\nField: {}",
                atom.citation().source_id(),
                atom.citation().locator(),
                atom.signal_key()
            ),
            tone: DossierTone::Dim,
        },
    ]
}

fn paint_places(
    commands: &mut Commands,
    entity: Entity,
    view: &DossierPageView,
    projection: &ActiveCountyDossier,
    identity: &DossierScopeIdentity,
) {
    match view {
        DossierPageView::Card => {
            let Some(card) = &projection.0 else {
                commands.entity(entity).despawn_related::<Children>();
                return;
            };
            let scope = DossierRequestScope {
                campaign: identity.campaign.0,
                county_geoid: card.geoid.clone(),
                refresh_generation: identity.refresh.0,
                observer: identity.observer.as_ref().map(|session| session.context()),
            };
            let chips = projection
                .0
                .as_ref()
                .map_or_else(Vec::new, |card| card.places.clone());
            set_chips(commands, entity, &chips, &scope);
        }
        DossierPageView::Placeholder(_) => {
            commands.entity(entity).despawn_related::<Children>();
        }
    }
}

fn paint_chronicle(
    commands: &mut Commands,
    entity: Entity,
    view: &DossierPageView,
    projection: &ActiveCountyDossier,
) {
    match view {
        DossierPageView::Card => {
            let rows = projection.0.as_ref().map_or_else(Vec::new, |card| {
                card.changelog
                    .iter()
                    .map(chronicle_row_segments)
                    .collect::<Vec<_>>()
            });
            set_segment_rows(commands, entity, &rows);
        }
        DossierPageView::Placeholder(_) => set_segments(commands, entity, &[]),
    }
}

type AddedCardNodes<'w, 's> = Query<
    'w,
    's,
    (&'static DeclaredSurface, &'static mut Node),
    (Added<Node>, Without<DossierCardRoot>),
>;

/// Apply observer typography to rendered card entities without changing the
/// shared Archive composition or the player-action conformance contract.
fn polish_observer_card(
    mut texts: Query<(&DeclaredSurface, &mut TextColor), Changed<TextColor>>,
    mut nodes: AddedCardNodes,
    mut lines: Query<(&DeclaredSurface, &mut Text), Changed<Text>>,
    mut spans: Query<(&DeclaredSurface, &mut TextSpan), Changed<TextSpan>>,
) {
    use crate::observer_theme as theme;
    fn supported_glyphs(value: &str) -> String {
        value
            .replace('·', "|")
            .replace('…', "...")
            .replace(['—', '–'], "-")
            .replace('→', ">")
            .replace('←', "<")
            .replace('φ', "phi")
    }
    for (surface, mut text) in &mut lines {
        if surface.id == CARD_SURFACE && !text.0.is_ascii() {
            let next = supported_glyphs(&text.0);
            if text.0 != next {
                text.0 = next;
            }
        }
    }
    for (surface, mut span) in &mut spans {
        if surface.id == CARD_SURFACE && !span.0.is_ascii() {
            let next = supported_glyphs(&span.0);
            if span.0 != next {
                span.0 = next;
            }
        }
    }
    for (surface, mut color) in &mut texts {
        if surface.id != CARD_SURFACE {
            continue;
        }
        let next = if color.0 == palette::DIM || color.0 == palette::BONE.with_alpha(0.7) {
            theme::GRAY
        } else if color.0 == palette::BONE {
            theme::PAPER
        } else if color.0 == palette::GOLD {
            theme::YELLOW
        } else if color.0 == palette::CRIMSON {
            theme::RED
        } else {
            color.0
        };
        if color.0 != next {
            color.0 = next;
        }
    }
    for (surface, mut node) in &mut nodes {
        if surface.id == CARD_SURFACE {
            node.flex_shrink = 0.0;
            node.min_width = px(0);
            node.max_width = percent(100);
        }
    }
}

/// Wires the dossier card's resource family and systems into an `App`.
pub struct DossierCardPlugin;

impl Plugin for DossierCardPlugin {
    fn build(&self, app: &mut App) {
        app.add_message::<SubjectPageRequest>()
            .init_resource::<DossierCampaignId>()
            .init_resource::<ActiveCountyDossier>()
            .init_resource::<DossierPageView>()
            .init_resource::<DossierFetchState>()
            .init_resource::<DossierRefresh>()
            .add_observer(keyboard_activate)
            .add_systems(
                PreUpdate,
                focus_eligibility.in_set(ObserverFocusSystems::Eligibility),
            )
            .add_systems(Startup, spawn_dossier_card)
            .add_systems(
                Update,
                (
                    // `.after(restart_on_n_key)`: the N-key restart clears
                    // the card THROUGH this system — its `SelectedCounty =
                    // None` write is the change this system reacts to, and
                    // the ordering makes the clear land in the same frame
                    // instead of one frame late. Vacuous when TickLoopPlugin
                    // is absent (headless unit compositions).
                    drive_dossier_fetch.after(crate::ui::story_card::restart_on_n_key),
                    collect_dossier_fetch,
                    apply_page_requests,
                    repaint_dossier_card,
                    polish_observer_card
                        .run_if(resource_exists::<crate::observer_ui::ObserverUiState>),
                )
                    .chain()
                    .after(crate::observer_io::ObserverSet::Install)
                    .before(crate::observer_io::ObserverSet::Paint),
            );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::{ArchiveAtomValueV1, ArchiveCitationV1, ArchiveEvidenceClassV1};

    fn chip_app() -> (App, Entity, SubjectPageRequest) {
        let campaign = CampaignId::from_uuid(uuid::Uuid::nil());
        let mut session = ObserverSession::new(campaign);
        session.ready(1, Some("a".repeat(64)));
        assert!(session.installed(&session.context()));
        let scope = DossierRequestScope {
            campaign,
            county_geoid: "26163".into(),
            refresh_generation: 0,
            observer: Some(session.context()),
        };
        let chip = PlaceChip::known("2622000", "Detroit", false);
        let request = chip_request(&chip, &scope);
        let atlas = CountyAtlas::parse(include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/map/county_atlas.bin"
        )))
        .unwrap();
        let selected = SelectedCounty(atlas.index_of_fips("26163"));
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(atlas)
            .insert_resource(selected)
            .insert_resource(session)
            .insert_resource(DossierCampaignId(campaign))
            .insert_resource(ObserverUiState {
                archive_open: true,
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .insert_resource(ActiveCountyDossier(Some(CountyDossierCardProjection {
                geoid: "26163".into(),
                title: "Wayne County".into(),
                durable_tick: Some(1),
                content_tick: Some(1),
                verified_tick: Some(1),
                atoms: vec![],
                places: vec![chip.clone()],
                changelog: vec![],
            })))
            .init_resource::<DossierRefresh>()
            .init_resource::<DossierFetchState>()
            .init_resource::<DossierPageView>()
            .init_resource::<ObserverFeedback>()
            .add_message::<SubjectPageRequest>()
            .add_observer(keyboard_activate)
            .add_systems(Startup, move |mut commands: Commands| {
                let zone = commands.spawn((Node::default(), TabGroup::new(20))).id();
                set_chips(&mut commands, zone, std::slice::from_ref(&chip), &scope);
            })
            .add_systems(PreUpdate, focus_eligibility)
            .add_systems(Update, apply_page_requests);
        app.update();
        app.update();
        let entity = app
            .world_mut()
            .query_filtered::<Entity, With<PlaceChipNode>>()
            .single(app.world())
            .unwrap();
        (app, entity, request)
    }

    #[test]
    fn keyboard_archive_chip_opens_the_exact_current_link() {
        let (mut app, entity, request) = chip_app();
        assert!(
            app.world()
                .get::<ObserverFocusTarget>(entity)
                .unwrap()
                .available
        );
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity,
            context: request.scope.observer.clone(),
        });
        assert_eq!(
            *app.world().resource::<DossierPageView>(),
            DossierPageView::Card
        );
        app.update();
        assert_eq!(
            *app.world().resource::<DossierPageView>(),
            DossierPageView::Placeholder(request)
        );
    }

    #[test]
    fn queued_archive_links_refuse_changed_campaign_county_generation_and_perspective() {
        for mutation in 0..5 {
            let (mut app, entity, request) = chip_app();
            app.world_mut().trigger(ObserverKeyboardActivate {
                entity,
                context: request.scope.observer.clone(),
            });
            match mutation {
                0 => {
                    app.world_mut().resource_mut::<DossierCampaignId>().0 =
                        CampaignId::from_uuid(uuid::Uuid::from_u128(9));
                }
                1 => app.world_mut().resource_mut::<SelectedCounty>().0 = None,
                2 => app.world_mut().resource_mut::<DossierRefresh>().bump(),
                3 => app
                    .world_mut()
                    .resource_mut::<ObserverSession>()
                    .set_perspective(crate::observer::Perspective::PlayerKnowledge),
                4 => {
                    app.world_mut()
                        .resource_mut::<ActiveCountyDossier>()
                        .0
                        .as_mut()
                        .unwrap()
                        .places[0] = PlaceChip::unknown("2622000");
                }
                _ => unreachable!(),
            }
            app.update();
            assert_eq!(
                *app.world().resource::<DossierPageView>(),
                DossierPageView::Card,
                "scope mutation {mutation} must reject an already queued known label"
            );
            assert!(app.world().resource::<ObserverFeedback>().message.is_some());
            assert!(
                !app.world()
                    .get::<ObserverFocusTarget>(entity)
                    .unwrap()
                    .available
            );
        }
    }

    #[test]
    fn archive_chip_rejects_forged_activation_context_and_idle_focus_does_not_change() {
        #[derive(Resource, Default)]
        struct ChangedTargets(usize);
        let (mut app, entity, request) = chip_app();
        app.init_resource::<ChangedTargets>().add_systems(
            PostUpdate,
            |changed: Query<(), Changed<ObserverFocusTarget>>,
             mut count: ResMut<ChangedTargets>| {
                count.0 = changed.iter().count();
            },
        );
        app.update();
        app.update();
        assert_eq!(app.world().resource::<ChangedTargets>().0, 0);
        let mut wrong = request.scope.observer.unwrap();
        wrong.tick += 1;
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity,
            context: Some(wrong),
        });
        app.update();
        assert_eq!(
            *app.world().resource::<DossierPageView>(),
            DossierPageView::Card
        );
        assert!(app.world().resource::<ObserverFeedback>().message.is_some());
    }

    fn signal_fixture(key: &str, source: &str) -> ArchiveAtomV1 {
        ArchiveAtomV1::try_new(
            CampaignId::from_uuid(uuid::Uuid::nil()),
            ArchiveAtomSubjectV1::try_new(ArchiveAtomSubjectKindV1::County, "26163".into())
                .unwrap(),
            key.into(),
            key.into(),
            ArchiveEvidenceClassV1::Observed,
            &ArchiveAtomValueV1::U64(1469),
            ArchiveCitationV1::try_new(
                source.into(),
                format!(
                    "county-economics.csv.gz#county_geoid=26163&sha256={}",
                    "a".repeat(64)
                ),
            )
            .unwrap(),
            1,
        )
        .unwrap()
    }

    #[test]
    fn observer_signal_labels_keep_exact_values_units_and_provenance() {
        let source = babylon_persistence::michigan_economy::QCEW_ECONOMICS_SOURCE_ID_V1;
        for (key, label, unit) in [
            ("qcew-employment", "Employment", "annual average jobs"),
            ("qcew-total-annual-wages", "Annual payroll", "USD / year"),
            (
                "qcew-average-weekly-wage",
                "Mean weekly wage",
                "USD / employee / week",
            ),
            (
                "qcew-establishments",
                "Establishments",
                "annual average establishments",
            ),
        ] {
            let atom = signal_fixture(key, source);
            let row = observer_signal_segments(&atom);
            assert_eq!(row[0].text, format!("{label}\n"));
            assert_eq!(row[1].text, format!("1469 {unit}"));
            assert!(row[2].text.contains(atom.citation().source_id()));
            assert!(row[2].text.contains(atom.citation().locator()));
            assert!(row[2].text.ends_with(&format!("Field: {key}")));
        }
        let foreign = signal_fixture("qcew-average-weekly-wage", "other-source");
        let row = observer_signal_segments(&foreign);
        assert_eq!(row[0].text, "qcew-average-weekly-wage\n");
        assert_eq!(
            row[1].text, "1469",
            "a matching key alone cannot invent a unit"
        );
    }

    #[test]
    fn rendered_signal_rows_stack_and_wrap_without_losing_citation_bytes() {
        let source = babylon_persistence::michigan_economy::QCEW_ECONOMICS_SOURCE_ID_V1;
        let rows: Vec<_> = ["qcew-employment", "qcew-average-weekly-wage"]
            .map(|key| observer_signal_segments(&signal_fixture(key, source)))
            .into();
        let expected: Vec<String> = rows
            .iter()
            .map(|row| row.iter().map(|part| part.text.as_str()).collect())
            .collect();
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .add_systems(Startup, move |mut commands: Commands| {
                let zone = commands.spawn((Text::new(""), DossierZone::Signals)).id();
                set_segment_rows(&mut commands, zone, &rows);
            });
        app.update();
        let world = app.world_mut();
        let (_, container, children) = world
            .query::<(&DossierZone, &Node, &Children)>()
            .single(world)
            .unwrap();
        assert_eq!(container.flex_direction, FlexDirection::Column);
        assert_eq!(container.width, percent(100));
        assert_eq!(container.min_width, px(0));
        assert_eq!(children.len(), expected.len());
        for (entity, expected) in children.iter().zip(expected) {
            let row = world.get::<Node>(entity).unwrap();
            assert_eq!(row.width, percent(100));
            assert_eq!(row.max_width, percent(100));
            assert_eq!(row.min_width, px(0));
            assert_eq!(row.flex_shrink.to_bits(), 0.0_f32.to_bits());
            assert_eq!(
                world.get::<TextLayout>(entity).unwrap().linebreak,
                bevy::text::LineBreak::WordOrCharacter
            );
            let spans = world.get::<Children>(entity).unwrap();
            let actual: String = spans
                .iter()
                .map(|span| world.get::<TextSpan>(span).unwrap().0.as_str())
                .collect();
            assert_eq!(actual, expected);
        }
    }

    #[test]
    fn campaign_default_uses_the_runtime_default_uuid_without_env() {
        let env = crate::test_support::EnvVarGuard::lock(CAMPAIGN_ENV);
        env.remove();
        assert_eq!(
            DossierCampaignId::default().0,
            CampaignId::from_uuid(uuid::Uuid::from_u128(DEFAULT_CAMPAIGN_UUID))
        );
    }

    #[test]
    fn campaign_default_reads_a_canonical_env_uuid() {
        let env = crate::test_support::EnvVarGuard::lock(CAMPAIGN_ENV);
        env.set("28100000-0000-0000-0000-000000000002");
        assert_eq!(
            DossierCampaignId::default().0,
            CampaignId::from_uuid(uuid::Uuid::from_u128(
                0x2810_0000_0000_0000_0000_0000_0000_0002
            ))
        );
    }

    #[test]
    fn fetch_error_display_is_honest() {
        assert_eq!(
            DossierFetchError::ReaderAbsent("missing env".to_owned()).to_string(),
            "Archive reader not configured (missing env)"
        );
        assert!(
            DossierFetchError::ReadFailed("connection refused".to_owned())
                .to_string()
                .starts_with("Archive fetch failed — ")
        );
    }
}
