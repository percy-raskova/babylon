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
use bevy::prelude::*;
use bevy::tasks::{block_on, AsyncComputeTaskPool, Task};

use crate::atlas::CountyAtlas;
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::dossier::{changelog_rows, ChangelogRow};
use crate::map::SelectedCounty;
use crate::palette;
use crate::ui::dossier_compose::{
    chip_text, chronicle_row_segments, compose_stub, compose_vague, dual_tick_segments,
    signal_atoms, signal_row_segments, DossierSegment, DossierTone, PlaceChip,
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

/// One requested subject page: a place-link chip click. Carries the public
/// kind word, the public subject id, and the resolved label when the Archive
/// acknowledges one (`None` for a fog chip) — everything an R6 placeholder
/// needs, with zero label bytes for the ungranted case.
#[derive(Message, Clone, Debug, PartialEq, Eq)]
pub struct SubjectPageRequest {
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
    /// The county page's verified tick, or `None` while unmaterialized.
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
    /// One task running for `fips`; the projection is already cleared.
    InFlight {
        /// The county FIPS being fetched.
        fips: String,
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
    let verified_tick = hits
        .iter()
        .find(|hit| {
            hit.page_ref().kind() == ArchiveSubjectKindV1::County && hit.page_ref().id() == fips
        })
        .map(babylon_persistence::ArchiveSearchHitV1::verified_tick);
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
                    durable_tick.is_some_and(|durable| hit.verified_tick() < durable),
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
        verified_tick,
        atoms,
        places,
        changelog: changelog_rows(&history),
    })
}

// ---- Card chrome ----

/// Which zone of the card one entity renders. One marker per zone so the
/// repaint finds its targets and the structural test can assert the whole
/// zone tree exists.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
enum DossierZone {
    Title,
    Question,
    DualTick,
    Signals,
    Places,
    Chronicle,
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
fn drive_dossier_fetch(
    selected: Res<SelectedCounty>,
    atlas: Res<CountyAtlas>,
    campaign: Res<DossierCampaignId>,
    mut state: ResMut<DossierFetchState>,
    mut projection: ResMut<ActiveCountyDossier>,
    mut view: ResMut<DossierPageView>,
) {
    if !selected.is_changed() {
        return;
    }
    *view = DossierPageView::Card;
    projection.0 = None;
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
    *state = DossierFetchState::InFlight { fips, task };
}

/// `Update` system: polls the in-flight task once per frame; on completion
/// installs the projection (success) or the honest failure (error).
fn collect_dossier_fetch(
    mut state: ResMut<DossierFetchState>,
    mut projection: ResMut<ActiveCountyDossier>,
) {
    let DossierFetchState::InFlight { task, .. } = &mut *state else {
        return;
    };
    let Some(result) = block_on(bevy::tasks::futures_lite::future::poll_once(task)) else {
        return; // still running
    };
    *state = match result {
        Ok(card) => {
            projection.0 = Some(card);
            DossierFetchState::Idle
        }
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
    commands.entity(zone).despawn_related::<Children>();
    for row in rows {
        commands.entity(zone).with_children(|parent| {
            parent
                .spawn((
                    Text::new(""),
                    TextFont {
                        font_size: 14.0,
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
                                font_size: 14.0,
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
fn set_chips(commands: &mut Commands, zone: Entity, chips: &[PlaceChip]) {
    commands.entity(zone).despawn_related::<Children>();
    for chip in chips {
        let (text_color, base_border) = match (chip.is_known(), chip.is_pending()) {
            (true, false) => (palette::BONE, Color::NONE),
            // Pending (Archive lag) and fog chips both render DIM with a DIM
            // border; hover still lifts either to GOLD.
            (true, true) | (false, _) => (palette::DIM, palette::DIM.with_alpha(0.6)),
        };
        let label = match chip {
            known if known.is_known() => Some(chip_text(known).replace(" · pending", "")),
            _ => None,
        };
        let request = SubjectPageRequest {
            kind: "place".to_owned(),
            id: chip.geoid().to_owned(),
            label,
        };
        commands
            .entity(zone)
            .with_child((
                Node {
                    padding: UiRect::axes(px(8), px(4)),
                    border: UiRect::all(px(1)),
                    border_radius: BorderRadius::all(px(4)),
                    ..default()
                },
                BackgroundColor(palette::MUTED_DARK.with_alpha(0.85)),
                BorderColor::all(base_border),
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
    }
}

fn on_place_chip_click(
    click: On<Pointer<Click>>,
    chips: Query<&PlaceChipNode>,
    mut requests: MessageWriter<SubjectPageRequest>,
) {
    if let Ok(chip) = chips.get(click.entity) {
        requests.write(chip.request.clone());
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
/// Kept separate from [`repaint_dossier_card`] so the painter holds the Bevy
/// 7-parameter system shape and stays a pure projection of resources.
fn apply_page_requests(
    mut view: ResMut<DossierPageView>,
    mut requests: MessageReader<SubjectPageRequest>,
) {
    for request in requests.read() {
        *view = DossierPageView::Placeholder(request.clone());
    }
}

/// `Update` system: the pure repaint. Derives every zone's content from
/// [`ActiveCountyDossier`], [`DossierFetchState`], and [`DossierPageView`]
/// only — the same resources in windowed and headless compositions, which is
/// the parity proof. Nothing here touches the reader.
fn repaint_dossier_card(
    mut commands: Commands,
    selected: Res<SelectedCounty>,
    projection: Res<ActiveCountyDossier>,
    state: Res<DossierFetchState>,
    view: Res<DossierPageView>,
    zones: Query<(Entity, &DossierZone)>,
    mut roots: Query<&mut Visibility, With<DossierCardRoot>>,
) {
    let Ok(mut root_visibility) = roots.single_mut() else {
        return;
    };
    if selected.0.is_none() {
        *root_visibility = Visibility::Hidden;
        return;
    }
    *root_visibility = Visibility::Visible;

    for (entity, zone) in &zones {
        match zone {
            DossierZone::Title => paint_title(&mut commands, entity, &view, &projection),
            DossierZone::Question => paint_question(&mut commands, entity, &view),
            DossierZone::DualTick => {
                paint_dual_tick(&mut commands, entity, &view, &state, &projection);
            }
            DossierZone::Signals => paint_signals(&mut commands, entity, &view, &projection),
            DossierZone::Places => paint_places(&mut commands, entity, &view, &projection),
            DossierZone::Chronicle => paint_chronicle(&mut commands, entity, &view, &projection),
            DossierZone::Actions => {
                // The sealed Investigate chip is static chrome; nothing to
                // repaint. Gate 5 (PER-26) swaps this zone's content when the
                // verb opens.
            }
        }
    }
}

fn paint_title(
    commands: &mut Commands,
    entity: Entity,
    view: &DossierPageView,
    projection: &ActiveCountyDossier,
) {
    match view {
        DossierPageView::Card => {
            let title = projection
                .0
                .as_ref()
                .map_or_else(|| "…".to_owned(), |card| card.title.clone());
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

fn paint_question(commands: &mut Commands, entity: Entity, view: &DossierPageView) {
    let text = match view {
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
                    text: "Fetching dossier…".to_owned(),
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
            DossierFetchState::Idle => {
                let segments = projection.0.as_ref().map_or_else(Vec::new, |card| {
                    dual_tick_segments(card.durable_tick, card.verified_tick)
                });
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
) {
    match view {
        DossierPageView::Card => {
            let rows = projection.0.as_ref().map_or_else(Vec::new, |card| {
                signal_atoms(&card.atoms)
                    .map(signal_row_segments)
                    .collect::<Vec<_>>()
            });
            set_segment_rows(commands, entity, &rows);
        }
        DossierPageView::Placeholder(request) => {
            // R6(a): containment is the county the place links from —
            // public-record structure the dossier already carries.
            let containment = projection.0.as_ref().map(|card| card.title.clone());
            let lines = match (&request.label, &containment) {
                (Some(label), Some(county)) => compose_stub(label, Some(county)),
                (Some(label), None) => compose_stub(label, None),
                (None, _) => compose_vague(&request.kind, &request.id),
            };
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

fn paint_places(
    commands: &mut Commands,
    entity: Entity,
    view: &DossierPageView,
    projection: &ActiveCountyDossier,
) {
    match view {
        DossierPageView::Card => {
            let chips = projection
                .0
                .as_ref()
                .map_or_else(Vec::new, |card| card.places.clone());
            set_chips(commands, entity, &chips);
        }
        DossierPageView::Placeholder(_) => set_chips(commands, entity, &[]),
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

/// Wires the dossier card's resource family and systems into an `App`.
pub struct DossierCardPlugin;

impl Plugin for DossierCardPlugin {
    fn build(&self, app: &mut App) {
        app.add_message::<SubjectPageRequest>()
            .init_resource::<DossierCampaignId>()
            .init_resource::<ActiveCountyDossier>()
            .init_resource::<DossierPageView>()
            .init_resource::<DossierFetchState>()
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
                )
                    .chain(),
            );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
