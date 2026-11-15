//! Period-bound money and labor queries with native connection selection.
use super::books::{self, Books, Worker as BooksWorker};
use super::compare::Periods;
use super::{geometry, rail, sankey};
use crate::atlas::CountyAtlas;
use crate::map::{CountyMapScope, MapScopeSet, SelectedCounty};
use crate::map_economy_lens::MapLens;
use crate::observer::{ObservationContext, ObserverSession, Perspective};
use crate::observer_focus::ObserverKeyboardActivate;
use crate::observer_io::ObserverSet;
use crate::observer_ui::{ObserverFrame, ObserverUiState};
use crate::production::PrimaryView;
use crate::ui::Interaction;
use babylon_material_circuit::SiteId;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{
    FlowGroup, FlowPage, FlowQuery, FlowRow, JournalError, LaborAmount, LaborFlowPage,
    LaborFlowRow, PeriodWindow,
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
    pub(super) quantity: Quantity,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) enum Quantity {
    Money(String),
    Labor(LaborAmount),
}

impl Quantity {
    pub(super) fn micros(&self) -> &str {
        match self {
            Self::Money(value) => value,
            Self::Labor(amount) => &amount.recorded_micro_hours,
        }
    }
}

/// A chosen direction within a foundation and county survives period reevaluation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Selection {
    campaign: CampaignId,
    foundation: String,
    home: String,
    measure: Measure,
    key: ConnectionKey,
}
impl Selection {
    fn for_scope(scope: &Scope, key: &ConnectionKey) -> Self {
        Self {
            campaign: scope.context.campaign,
            foundation: scope.foundation.clone(),
            home: scope.county.clone(),
            measure: scope.measure,
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
        let prior = peer.comparison.as_ref();
        for (direction, micros, before) in [
            (
                Direction::PaidTo,
                &peer.current.inflow_micros,
                prior.map(|p| &p.inflow_micros),
            ),
            (
                Direction::ReceivedFrom,
                &peer.current.outflow_micros,
                prior.map(|p| &p.outflow_micros),
            ),
            (
                Direction::Internal,
                &peer.current.internal_micros,
                prior.map(|p| &p.internal_micros),
            ),
        ] {
            if micros != "0" || before.is_some_and(|value| value != "0") {
                rows.push(Connection {
                    key: ConnectionKey {
                        peer: peer.key.clone(),
                        direction,
                    },
                    quantity: Quantity::Money(micros.clone()),
                });
            }
        }
    }
    rows
}

pub(super) fn labor_connections(groups: &[LaborFlowRow]) -> Vec<Connection> {
    let mut rows = Vec::new();
    for peer in groups {
        let prior = peer.comparison.as_ref();
        for (direction, amount, before) in [
            (
                Direction::PaidTo,
                &peer.current.inbound,
                prior.map(|p| &p.inbound),
            ),
            (
                Direction::ReceivedFrom,
                &peer.current.outbound,
                prior.map(|p| &p.outbound),
            ),
            (
                Direction::Internal,
                &peer.current.within,
                prior.map(|p| &p.within),
            ),
        ] {
            if amount.movement_count != "0"
                || before.is_some_and(|value| value.movement_count != "0")
            {
                rows.push(Connection {
                    key: ConnectionKey {
                        peer: peer.key.clone(),
                        direction,
                    },
                    quantity: Quantity::Labor(amount.clone()),
                });
            }
        }
    }
    rows
}

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
pub(super) enum Measure {
    #[default]
    Money,
    Labor,
}

pub(super) enum Page {
    Money(Box<FlowPage>),
    Labor(Box<LaborFlowPage>),
}

impl Page {
    pub(super) fn total_groups(&self) -> u64 {
        match self {
            Self::Money(p) => p.total.groups,
            Self::Labor(p) => p.total.groups,
        }
    }

    fn connections(&self) -> Vec<Connection> {
        match self {
            Self::Money(p) => connections(&p.groups),
            Self::Labor(p) => labor_connections(&p.groups),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Scope {
    pub(super) periods: Periods,
    pub(super) measure: Measure,
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

    pub(super) fn scope(&self, measure: Measure, periods: Periods) -> Option<Scope> {
        if !self.active() {
            return None;
        }
        let frame = self.frame.for_session(&self.session)?;
        let selected = self.atlas.county(self.selected.0?)?;
        Some(Scope {
            periods: periods.available(self.session.viewed_tick),
            measure,
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

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) enum Diagram {
    #[default]
    Map,
    Sankey,
}

#[derive(Resource, Default)]
pub(in crate::observer_map3d) struct MoneyView {
    pub(super) books: Books,
    pub(super) diagram: Diagram,
    pub(super) measure: Measure,
    pub(super) scope: Option<Scope>,
    pub(super) offset: u64,
    pub(super) page: Option<Page>,
    pub(super) rows: Vec<Connection>,
    pub(super) selected: Option<Selection>,
    pub(super) status: Status,
}

impl MoneyView {
    pub(in crate::observer_map3d) fn shows_sankey(&self) -> bool {
        self.diagram == Diagram::Sankey && self.scope.is_some()
    }

    pub(super) fn selected_row(&self) -> Option<&Connection> {
        let selected = self.selected.as_ref()?;
        let scope = self.scope.as_ref()?;
        if scope.measure != selected.measure
            || scope.county != selected.home
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
    task: Task<Result<Page, JournalError>>,
}

#[derive(Resource, Default)]
struct Loader {
    pending: Option<PendingPage>,
    retry_at: f64,
    delay: f64,
}

fn read_page(scope: &Scope, offset: u64) -> Result<Page, JournalError> {
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
        comparison: scope.periods.window(scope.context.tick),
        offset,
        viewport_4269: None,
    };
    match scope.measure {
        Measure::Money => reader
            .economic_payment_flows_for_frame(
                scope.context.campaign,
                &query,
                &scope.foundation,
                tick_hash,
            )
            .map(|page| Page::Money(Box::new(page))),
        Measure::Labor => reader
            .recorded_labor_flows_for_frame(
                scope.context.campaign,
                &query,
                &scope.foundation,
                tick_hash,
            )
            .map(|page| Page::Labor(Box::new(page))),
    }
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
        let mode = view
            .scope
            .as_ref()
            .map_or(Periods::Current, |scope| scope.periods);
        let scope = observation.scope(view.measure, mode);
        let selection_refused = view
            .selected
            .as_ref()
            .is_some_and(|selected| !selected.admitted(&observation));
        if view.scope != scope || selection_refused {
            let selected = view.selected.take().filter(|s| s.admitted(&observation));
            let diagram = if observation.active() {
                view.diagram
            } else {
                Diagram::Map
            };
            *view = MoneyView {
                diagram,
                measure: if observation.active() {
                    view.measure
                } else {
                    Measure::Money
                },
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
                        view.rows = page.connections();
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
        || (view.status == Status::Publishing && time.elapsed_secs_f64() < loader.retry_at)
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
    Diagram(Diagram),
    Measure(Measure),
    Select(ConnectionKey),
    Books { from: Option<u64>, to: Option<u64> },
    Site { offset: u64, site: SiteId },
    Page(u64),
    Compare(Periods),
    Follow,
    Frame,
    Retry,
}
#[derive(Component)]
pub(super) struct Target {
    pub(super) scope: Scope,
    pub(super) offset: u64,
    pub(super) action: Action,
}

pub(super) fn activate(
    target: &Target,
    observed: &Observation,
    view: &mut MoneyView,
    commands: &mut Commands,
) -> bool {
    if !observed.interactive()
        || observed
            .scope(target.scope.measure, target.scope.periods)
            .as_ref()
            != Some(&target.scope)
        || view.scope.as_ref() != Some(&target.scope)
        || view.offset != target.offset
    {
        return false;
    }
    match &target.action {
        Action::Books { from, to } if target.scope.measure == Measure::Money => {
            return view.books.navigate(*from, *to)
        }
        Action::Site { offset, site } if target.scope.measure == Measure::Money => {
            return view
                .books
                .open_site(*site, *offset, observed, &target.scope, commands)
        }
        Action::Compare(periods)
            if target.scope.context.tick > 1 && *periods != target.scope.periods =>
        {
            let mut scope = target.scope.clone();
            scope.periods = *periods;
            let selected = view.selected.take();
            *view = MoneyView {
                scope: Some(scope),
                measure: view.measure,
                diagram: view.diagram,
                selected,
                ..default()
            };
        }
        Action::Diagram(diagram) => view.diagram = *diagram,
        Action::Measure(measure) if *measure != target.scope.measure => {
            let mut scope = target.scope.clone();
            scope.measure = *measure;
            *view = MoneyView {
                measure: *measure,
                scope: Some(scope),
                diagram: view.diagram,
                ..default()
            };
        }
        Action::Select(key) if view.rows.iter().any(|row| &row.key == key) => {
            view.selected = Some(Selection::for_scope(&target.scope, key));
        }
        Action::Page(offset)
            if view
                .page
                .as_ref()
                .is_some_and(|p| *offset < p.total_groups()) =>
        {
            view.offset = *offset;
            view.page = None;
            view.rows.clear();
            view.status = Status::Waiting;
        }
        Action::Frame => {
            commands.trigger(geometry::FrameConnections {
                scope: target.scope.clone(),
                offset: target.offset,
            });
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
        .init_resource::<BooksWorker>()
        .add_observer(geometry::frame_connections)
        .add_systems(
            Update,
            books::update.after(update).before(ObserverSet::Paint),
        )
        .add_systems(Update, press_rail.in_set(ObserverSet::Input))
        .add_systems(Update, update.after(MapScopeSet).before(ObserverSet::Paint))
        .add_systems(
            Update,
            (rail::paint, geometry::render, sankey::paint).in_set(ObserverSet::Paint),
        )
        .add_systems(Update, rail::highlight.after(rail::paint));
}
