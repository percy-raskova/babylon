//! Period-bound payment reads and native connection selection.
use super::{geometry, rail};
use crate::atlas::CountyAtlas;
use crate::map::{CountyMapScope, MapScopeSet, SelectedCounty};
use crate::map_economy_lens::MapLens;
use crate::observer::{ObservationContext, ObserverSession, Perspective};
use crate::observer_focus::ObserverKeyboardActivate;
use crate::observer_io::ObserverSet;
use crate::observer_ui::{ObserverFrame, ObserverUiState};
use crate::production::PrimaryView;
use crate::ui::Interaction;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{
    FlowGroup, FlowPage, FlowQuery, FlowRow, JournalError, PeriodWindow,
};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use bevy::ecs::system::SystemParam;
use bevy::input_focus::{FocusCause, InputFocus};
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;
use bevy::tasks::{self, AsyncComputeTaskPool, Task};

#[derive(Component)]
pub(crate) struct MoneyRail;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Direction {
    PaidTo,
    ReceivedFrom,
    Internal,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct ConnectionKey {
    pub(super) peer: Option<String>,
    pub(super) direction: Direction,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Connection {
    pub(super) key: ConnectionKey,
    pub(super) micros: String,
}

/// A chosen direction within a foundation and county survives period reevaluation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Selection {
    campaign: CampaignId,
    foundation: String,
    home: String,
    key: ConnectionKey,
}
impl Selection {
    fn for_scope(scope: &Scope, key: &ConnectionKey) -> Self {
        Self {
            campaign: scope.context.campaign,
            foundation: scope.foundation.clone(),
            home: scope.county.clone(),
            key: key.clone(),
        }
    }
    fn admitted(&self, observation: &Observation) -> bool {
        observation.active()
            && self.campaign == observation.session.campaign
            && observation.session.foundation_digest.as_deref() == Some(self.foundation.as_str())
            && observation
                .selected
                .0
                .and_then(|index| observation.atlas.county(index))
                .is_some_and(|c| c.fips == self.home)
    }
}

// The SQL page reports inflow and outflow from the counterparty's perspective.
pub(super) fn connections(groups: &[FlowRow]) -> Vec<Connection> {
    let mut rows = Vec::new();
    for peer in groups {
        for (direction, micros) in [
            (Direction::PaidTo, &peer.current.inflow_micros),
            (Direction::ReceivedFrom, &peer.current.outflow_micros),
            (Direction::Internal, &peer.current.internal_micros),
        ] {
            if micros != "0" {
                rows.push(Connection {
                    key: ConnectionKey {
                        peer: peer.key.clone(),
                        direction,
                    },
                    micros: micros.clone(),
                });
            }
        }
    }
    rows
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Scope {
    pub(super) context: ObservationContext,
    pub(super) county: String,
    pub(super) foundation: String,
    pub(super) tick_hash: Option<String>,
}

#[derive(SystemParam)]
pub(super) struct Observation<'w> {
    pub(super) session: Res<'w, ObserverSession>,
    pub(super) frame: Res<'w, ObserverFrame>,
    pub(super) primary: Res<'w, PrimaryView>,
    pub(super) ui: Res<'w, ObserverUiState>,
    pub(super) atlas: Res<'w, CountyAtlas>,
    pub(super) selected: Res<'w, SelectedCounty>,
    pub(super) counties: Res<'w, CountyMapScope>,
}

impl Observation<'_> {
    pub(super) fn active(&self) -> bool {
        *self.primary == PrimaryView::Map
            && self.ui.lens == MapLens::Money
            && self.session.perspective == Perspective::FullObserver
            && !self.session.organizer_enabled
    }

    pub(super) fn interactive(&self) -> bool {
        self.active()
            && !self.ui.menu_open
            && !self.ui.splash_visible
            && !self.ui.comparison_open
            && !self.ui.archive_open
            && self.ui.disclosure.is_none()
            && !self.ui.history_open
    }

    fn scope(&self) -> Option<Scope> {
        if !self.active() {
            return None;
        }
        let frame = self.frame.for_session(&self.session)?;
        let selected = self.atlas.county(self.selected.0?)?;
        Some(Scope {
            context: self.session.context(),
            county: selected.fips.to_owned(),
            foundation: frame.foundation_digest.clone(),
            tick_hash: frame.tick_content_hash.clone(),
        })
    }
}

#[derive(Clone, Copy, Default, PartialEq, Eq)]
pub(super) enum Status {
    #[default]
    Waiting,
    Opening,
    Loading,
    Publishing,
    Failed(JournalError),
    Ready,
}

#[derive(Resource, Default)]
pub(super) struct MoneyView {
    pub(super) scope: Option<Scope>,
    pub(super) offset: u64,
    pub(super) page: Option<FlowPage>,
    pub(super) rows: Vec<Connection>,
    pub(super) selected: Option<Selection>,
    pub(super) status: Status,
}

impl MoneyView {
    pub(super) fn selected_row(&self) -> Option<&Connection> {
        let selected = self.selected.as_ref()?;
        let scope = self.scope.as_ref()?;
        if scope.county != selected.home
            || scope.foundation != selected.foundation
            || scope.context.campaign != selected.campaign
        {
            return None;
        }
        self.rows.iter().find(|row| row.key == selected.key)
    }
}

struct PendingPage {
    scope: Scope,
    offset: u64,
    task: Task<Result<FlowPage, JournalError>>,
}

#[derive(Resource, Default)]
struct Loader {
    pending: Option<PendingPage>,
    retry_at: f64,
    delay: f64,
}

fn read_page(scope: &Scope, offset: u64) -> Result<FlowPage, JournalError> {
    let tick_hash = scope
        .tick_hash
        .as_deref()
        .ok_or(JournalError::SourceChanged)?;
    let reader = ObserverEconomyReader::from_observer_env().map_err(JournalError::Observer)?;
    let query = FlowQuery {
        group: FlowGroup::Location,
        focus: Some(format!("county:{}", scope.county)),
        window: PeriodWindow {
            first: scope.context.tick,
            last: scope.context.tick,
        },
        comparison: None,
        offset,
        viewport_4269: None,
    };
    reader.economic_payment_flows_for_frame(
        scope.context.campaign,
        &query,
        &scope.foundation,
        tick_hash,
    )
}

fn update(
    observation: Observation,
    time: Res<Time<Real>>,
    mut view: ResMut<MoneyView>,
    mut loader: ResMut<Loader>,
) {
    if observation.session.is_changed()
        || observation.frame.is_changed()
        || observation.selected.is_changed()
        || observation.primary.is_changed()
        || observation.ui.is_changed()
    {
        let scope = observation.scope();
        let selection_refused = view
            .selected
            .as_ref()
            .is_some_and(|selected| !selected.admitted(&observation));
        if view.scope != scope || selection_refused {
            let selected = view.selected.take().filter(|s| s.admitted(&observation));
            *view = MoneyView {
                scope,
                selected,
                ..default()
            };
            loader.retry_at = 0.0;
            loader.delay = 1.0;
        }
    }
    if let Some(pending) = &mut loader.pending {
        // PostgreSQL reads block within a worker. Drain an obsolete read before launching its successor.
        let Some(result) =
            tasks::block_on(tasks::futures_lite::future::poll_once(&mut pending.task))
        else {
            return;
        };
        if let Some(PendingPage { scope, offset, .. }) = loader.pending.take() {
            if view.scope.as_ref() == Some(&scope) && view.offset == offset {
                match result {
                    Ok(page) => {
                        view.rows = connections(&page.groups);
                        view.page = Some(page);
                        view.status = Status::Ready;
                    }
                    Err(JournalError::CoverageAbsent) => {
                        view.status = Status::Publishing;
                        loader.retry_at = time.elapsed_secs_f64() + loader.delay;
                        loader.delay = (loader.delay * 2.0).clamp(1.0, 8.0);
                    }
                    Err(error) => view.status = Status::Failed(error),
                }
            }
        }
    }
    let Some(scope) = &view.scope else {
        return;
    };
    if scope.context.tick == 0 {
        if view.status != Status::Opening {
            view.status = Status::Opening;
        }
        return;
    }
    if !matches!(view.status, Status::Waiting | Status::Publishing)
        || time.elapsed_secs_f64() < loader.retry_at
    {
        return;
    }
    let scope = scope.clone();
    let requested = scope.clone();
    let offset = view.offset;
    loader.pending = Some(PendingPage {
        scope,
        offset,
        task: AsyncComputeTaskPool::get().spawn(async move { read_page(&requested, offset) }),
    });
    if view.status != Status::Publishing {
        view.status = Status::Loading;
    }
}

#[derive(Clone, PartialEq, Eq)]
pub(super) enum Action {
    Select(ConnectionKey),
    Page(u64),
    Follow,
    Retry,
}
#[derive(Component)]
pub(super) struct Target {
    pub(super) scope: Scope,
    pub(super) offset: u64,
    pub(super) action: Action,
}

fn activate(
    target: &Target,
    observed: &Observation,
    view: &mut MoneyView,
    commands: &mut Commands,
) -> bool {
    if !observed.interactive()
        || observed.scope().as_ref() != Some(&target.scope)
        || view.scope.as_ref() != Some(&target.scope)
        || view.offset != target.offset
    {
        return false;
    }
    match &target.action {
        Action::Select(key) if view.rows.iter().any(|row| &row.key == key) => {
            view.selected = Some(Selection::for_scope(&target.scope, key));
        }
        Action::Page(offset) if view.page.as_ref().is_some_and(|p| *offset < p.total.groups) => {
            view.offset = *offset;
            view.page = None;
            view.rows.clear();
            view.status = Status::Waiting;
        }
        Action::Follow => {
            if let Some(index) = view
                .selected_row()
                .and_then(|row| row.key.peer.as_deref())
                .and_then(|peer| peer.strip_prefix("county:"))
                .and_then(|geoid| observed.atlas.index_of_fips(geoid))
                .filter(|index| {
                    observed.counties.contains(*index) && Some(*index) != observed.selected.0
                })
            {
                commands.insert_resource(SelectedCounty(Some(index)));
            } else {
                return false;
            }
        }
        Action::Retry if matches!(view.status, Status::Failed(_)) => view.status = Status::Waiting,
        _ => return false,
    }
    true
}

// The rail uses the same UI interaction source as the observer shell buttons.
// Map geometry still resolves the actual mesh hit from its picking event.
pub(super) fn press_rail(
    rows: Query<(Entity, &Interaction, &Target), Changed<Interaction>>,
    observation: Observation,
    mut view: ResMut<MoneyView>,
    mut commands: Commands,
    mut focus: Option<ResMut<InputFocus>>,
) {
    for (entity, interaction, target) in &rows {
        if *interaction != Interaction::Pressed
            || !activate(target, &observation, &mut view, &mut commands)
        {
            continue;
        }
        if let Some(focus) = focus.as_deref_mut() {
            focus.set(entity, FocusCause::Pressed);
        }
    }
}

pub(super) fn pointer(
    event: On<PointerClick>,
    targets: Query<&Target>,
    obs: Observation,
    mut view: ResMut<MoneyView>,
    mut commands: Commands,
) {
    if event.button == PointerButton::Primary {
        if let Ok(target) = targets.get(event.entity) {
            activate(target, &obs, &mut view, &mut commands);
        }
    }
}
pub(super) fn keyboard(
    event: On<ObserverKeyboardActivate>,
    targets: Query<&Target>,
    obs: Observation,
    mut view: ResMut<MoneyView>,
    mut commands: Commands,
) {
    if let Ok(target) = targets.get(event.entity) {
        if event.context.as_ref() == Some(&target.scope.context) {
            activate(target, &obs, &mut view, &mut commands);
        }
    }
}

pub(in crate::observer_map3d) fn install(app: &mut App) {
    app.init_resource::<MoneyView>()
        .init_resource::<Loader>()
        .add_systems(Update, press_rail.in_set(ObserverSet::Input))
        .add_systems(Update, update.after(MapScopeSet).before(ObserverSet::Paint))
        .add_systems(
            Update,
            (rail::paint, geometry::render).in_set(ObserverSet::Paint),
        )
        .add_systems(Update, rail::highlight.after(rail::paint));
}
