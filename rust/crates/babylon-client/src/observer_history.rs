//! Bounded, capability-scoped history. Charts never recompute a transition.

use babylon_persistence::{ObserverEconomyReaderV1, ProductionEventV1, ProductionSiteV1};
use bevy::ecs::{query::QueryData, system::SystemParam};
use bevy::prelude::*;
use bevy::tasks::{block_on, AsyncComputeTaskPool, Task};

use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer::{ObservationContext, ObserverSession, Perspective};
use crate::observer_calendar::CampaignMonth;
use crate::observer_controls::{inspection_availability, ControlAvailability};
use crate::observer_io::ObserverSet;
use crate::observer_layout::ObserverRegion;
use crate::observer_theme as theme;
use crate::observer_ui::{grouped, ObserverFeedback, ObserverFrame, ObserverUiState};
use crate::production::{ProductionCommand, ProductionNavigation};
use crate::ui::dossier_card::DossierRefresh;

const CHART_WEEKS: u64 = 12;

#[derive(Clone, Debug, PartialEq, Eq)]
struct HistoryScope {
    context: ObservationContext,
    site: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct WeeklyOutput {
    week: u64,
    planned: Option<u64>,
    produced: Option<u64>,
}

impl WeeklyOutput {
    fn from_site(week: u64, site: &ProductionSiteV1) -> Result<Self, String> {
        let quantity = |batches: Option<u64>| {
            batches
                .map(|batches| {
                    batches.checked_mul(site.output_per_batch).ok_or_else(|| {
                        "Output quantity exceeds its exact integer range.".to_owned()
                    })
                })
                .transpose()
        };
        Ok(Self {
            week,
            planned: quantity(site.planned_batches)?,
            produced: quantity(site.produced_batches)?,
        })
    }
}

type HistoryTask = Task<Result<Vec<WeeklyOutput>, String>>;

#[derive(Resource, Default)]
struct HistoryState {
    scope: Option<HistoryScope>,
    pending: Option<HistoryTask>,
    points: Vec<WeeklyOutput>,
    error: Option<String>,
    selected_event: Option<(ObservationContext, ProductionEventV1)>,
    focus_selected_event: bool,
}

#[derive(Component)]
struct HistoryPanel;
#[derive(Component)]
struct LogPanel;
#[derive(Component)]
struct HistoryHint;
#[derive(Component, Clone)]
enum HistoryButton {
    Week {
        context: ObservationContext,
        week: u64,
    },
    Event {
        context: ObservationContext,
        event: ProductionEventV1,
    },
}

fn label(value: impl Into<String>, size: f32, color: Color) -> impl Bundle {
    (
        Text::new(value),
        TextFont {
            font_size: size,
            ..default()
        },
        TextColor(color),
        Node {
            flex_shrink: 0.0,
            min_width: px(0),
            max_width: percent(100),
            ..default()
        },
        DeclaredSurface::new(SurfaceId::ObserverProduction),
    )
}

fn setup(mut commands: Commands) {
    commands.spawn((
        Node {
            position_type: PositionType::Absolute,
            padding: UiRect::all(px(12)),
            row_gap: px(8),
            flex_direction: FlexDirection::Column,
            overflow: Overflow::scroll_y(),
            border: UiRect::top(px(2)),
            ..default()
        },
        BackgroundColor(theme::INK),
        BorderColor::all(theme::YELLOW),
        ZIndex(9),
        Visibility::Hidden,
        HistoryPanel,
        ObserverRegion::History,
        DeclaredSurface::new(SurfaceId::ObserverProduction),
    ));
    commands.spawn((
        Node {
            position_type: PositionType::Absolute,
            padding: UiRect::all(px(16)),
            row_gap: px(12),
            flex_direction: FlexDirection::Column,
            overflow: Overflow::scroll_y(),
            border: UiRect::left(px(2)),
            ..default()
        },
        BackgroundColor(theme::INK),
        BorderColor::all(theme::PAPER.with_alpha(0.6)),
        ZIndex(6),
        LogPanel,
        Visibility::Visible,
        ObserverRegion::Log,
        DeclaredSurface::new(SurfaceId::ObserverProduction),
    ));
}

fn button_availability(
    button: &HistoryButton,
    session: &ObserverSession,
    frame: &ObserverFrame,
) -> ControlAvailability {
    use ControlAvailability::{Disabled, Enabled};
    let (context, week) = match button {
        HistoryButton::Week { context, week } => (context, *week),
        HistoryButton::Event { context, event } => (context, event.week),
    };
    if !session.accepts(context) {
        return Disabled("History changed; wait for its current observation");
    }
    let available = inspection_availability(session);
    if available != Enabled {
        return available;
    }
    if week > session.durable_tick {
        return Disabled("That week has not committed");
    }
    match button {
        HistoryButton::Week { .. } if week == session.viewed_tick => {
            Disabled("Already viewing this committed week")
        }
        HistoryButton::Event { event, .. } => {
            let valid = frame
                .for_session(session)
                .and_then(|frame| frame.production.as_ref())
                .is_some_and(|snapshot| snapshot.events.iter().any(|current| current == event));
            if valid {
                Enabled
            } else {
                Disabled("This event is unavailable in the current observation")
            }
        }
        HistoryButton::Week { .. } => Enabled,
    }
}

#[derive(SystemParam)]
struct HistoryInput<'w> {
    session: ResMut<'w, ObserverSession>,
    frame: Res<'w, ObserverFrame>,
    history: ResMut<'w, HistoryState>,
    ui: Res<'w, ObserverUiState>,
    refresh: ResMut<'w, DossierRefresh>,
    feedback: ResMut<'w, ObserverFeedback>,
    time: Res<'w, Time>,
}

fn input(
    buttons: Query<(&Interaction, &HistoryButton), Changed<Interaction>>,
    mut context: HistoryInput,
) {
    let HistoryInput {
        session,
        frame,
        history,
        ui,
        refresh,
        feedback,
        time,
    } = &mut context;
    if ui.menu_open || ui.splash_visible || ui.comparison_open {
        return;
    }
    for (interaction, button) in &buttons {
        if *interaction != Interaction::Pressed
            || (!ui.history_open && matches!(button, HistoryButton::Week { .. }))
        {
            continue;
        }
        if let ControlAvailability::Disabled(reason) = button_availability(button, session, frame) {
            feedback.reject(reason, time.elapsed_secs_f64());
            continue;
        }
        feedback.message = None;
        let week = match button {
            HistoryButton::Week { week, .. } => *week,
            HistoryButton::Event { event, .. } => event.week,
        };
        session.pause_month();
        if session.viewed_tick != week {
            session.inspect_tick(week);
            refresh.bump();
        }
        // The committed evidence is revalidated after this week loads.
        history.selected_event = match button {
            HistoryButton::Event { event, .. } => Some((session.context(), event.clone())),
            HistoryButton::Week { .. } => None,
        };
        history.focus_selected_event = history.selected_event.is_some();
    }
}

fn fetch(scope: &HistoryScope) -> Result<Vec<WeeklyOutput>, String> {
    let Some(site_id) = &scope.site else {
        return Ok(Vec::new());
    };
    let reader = match scope.context.perspective {
        Perspective::FullObserver => ObserverEconomyReaderV1::from_observer_env(),
        Perspective::PlayerKnowledge => ObserverEconomyReaderV1::from_known_env(),
    }
    .map_err(|error| error.to_string())?;
    let mut points = Vec::new();
    for week in scope.context.tick.saturating_sub(CHART_WEEKS - 1)..=scope.context.tick {
        let frame = reader
            .snapshot(scope.context.campaign, week)
            .map_err(|error| error.to_string())?;
        let Some(site) = frame
            .production
            .as_ref()
            .and_then(|snapshot| snapshot.sites.iter().find(|site| site.id == *site_id))
        else {
            return Err("Production history is not disclosed by this read capability.".into());
        };
        points.push(WeeklyOutput::from_site(week, site)?);
    }
    Ok(points)
}

fn update(
    session: Res<ObserverSession>,
    frame: Res<ObserverFrame>,
    ui: Res<ObserverUiState>,
    navigation: Res<ProductionNavigation>,
    mut history: ResMut<HistoryState>,
    mut links: MessageWriter<ProductionCommand>,
) {
    let scope = HistoryScope {
        context: session.context(),
        site: navigation.selected_site.clone(),
    };
    if history.scope.as_ref() != Some(&scope) {
        history.pending = None;
        history.points.clear();
        history.error = None;
        history.scope = Some(scope.clone());
    }
    if history
        .selected_event
        .as_ref()
        .is_some_and(|(context, _)| !session.accepts(context))
    {
        history.selected_event = None;
        history.focus_selected_event = false;
    }
    if let Some((_, event)) = history
        .selected_event
        .clone()
        .filter(|_| history.focus_selected_event)
    {
        if let Some(snapshot) = frame
            .for_session(&session)
            .and_then(|frame| frame.production.as_ref())
        {
            if snapshot.events.contains(&event) {
                if let Some(site) = event.subject_site_ids.first() {
                    if navigation.selected_site.as_ref() != Some(site) {
                        links.write(ProductionCommand::Select {
                            site_id: site.clone(),
                            context: session.context(),
                        });
                    }
                }
            } else {
                history.selected_event = None;
            }
            history.focus_selected_event = false;
        }
    }
    if !ui.history_open || ui.menu_open || ui.comparison_open {
        return;
    }
    if frame.for_session(&session).is_none() {
        return;
    }
    if history.pending.is_none()
        && history.points.is_empty()
        && history.error.is_none()
        && scope.site.is_some()
    {
        history.pending = Some(AsyncComputeTaskPool::get().spawn(async move { fetch(&scope) }));
    }
    if history.pending.is_some() {
        let result = history
            .bypass_change_detection()
            .pending
            .as_mut()
            .and_then(|task| block_on(bevy::tasks::futures_lite::future::poll_once(task)));
        if let Some(result) = result {
            history.pending = None;
            match result {
                Ok(points) => history.points = points,
                Err(error) => history.error = Some(error),
            }
        }
    }
}

#[allow(clippy::cast_precision_loss, clippy::cast_possible_truncation)]
fn bar_height(value: Option<u64>, maximum: u64) -> f32 {
    value.map_or(0.0, |value| {
        ((value as f64 / maximum.max(1) as f64) * 56.0) as f32
    })
}

#[derive(QueryData)]
#[query_data(mutable)]
struct HistoryButtonAppearance {
    interaction: &'static Interaction,
    button: &'static HistoryButton,
    background: &'static mut BackgroundColor,
    border: &'static mut BorderColor,
}

type ChangedHistoryButtons = (
    With<HistoryButton>,
    Or<(Changed<Interaction>, Changed<HistoryButton>)>,
);

fn history_buttons_need_paint(
    session: Res<ObserverSession>,
    frame: Res<ObserverFrame>,
    ui: Res<ObserverUiState>,
    history: Res<HistoryState>,
    changed_buttons: Query<(), ChangedHistoryButtons>,
    added_hints: Query<(), Added<HistoryHint>>,
) -> bool {
    session.is_changed()
        || frame.is_changed()
        || ui.is_changed()
        || history.is_changed()
        || !changed_buttons.is_empty()
        || !added_hints.is_empty()
}

fn paint_buttons(
    session: Res<ObserverSession>,
    frame: Res<ObserverFrame>,
    ui: Res<ObserverUiState>,
    mut buttons: Query<HistoryButtonAppearance>,
    mut hints: Query<&mut Text, With<HistoryHint>>,
) {
    if ui.menu_open || ui.splash_visible || ui.comparison_open {
        return;
    }
    let mut hint = match inspection_availability(&session) {
        ControlAvailability::Enabled => "Select a committed week or event to inspect.",
        ControlAvailability::Disabled(reason) => reason,
    };
    for mut item in &mut buttons {
        let available = button_availability(item.button, &session, &frame);
        if *item.interaction != Interaction::None {
            if let ControlAvailability::Disabled(reason) = available {
                hint = reason;
            }
        }
        let enabled = available == ControlAvailability::Enabled;
        let color = match item.interaction {
            _ if !enabled => theme::INK,
            Interaction::Pressed => theme::RED.with_alpha(0.5),
            Interaction::Hovered => theme::YELLOW.with_alpha(0.25),
            Interaction::None => theme::PANEL,
        };
        item.background.set_if_neq(BackgroundColor(color));
        let border = if !enabled {
            theme::GRAY.with_alpha(0.3)
        } else if *item.interaction != Interaction::None {
            theme::YELLOW
        } else if matches!(item.button, HistoryButton::Event { .. }) {
            theme::BLUE
        } else {
            theme::GRAY
        };
        item.border.set_if_neq(BorderColor::all(border));
    }
    for mut text in &mut hints {
        text.set_if_neq(Text::new(hint));
    }
}

fn paint(
    mut commands: Commands,
    session: Res<ObserverSession>,
    frame: Res<ObserverFrame>,
    history: Res<HistoryState>,
    ui: Res<ObserverUiState>,
    navigation: Res<ProductionNavigation>,
    mut panels: Query<(Entity, &mut Visibility), With<HistoryPanel>>,
) {
    let Ok((panel, mut visibility)) = panels.single_mut() else {
        return;
    };
    visibility.set_if_neq(if ui.history_open && !ui.menu_open && !ui.comparison_open {
        Visibility::Visible
    } else {
        Visibility::Hidden
    });
    if !(history.is_changed()
        || frame.is_changed()
        || ui.is_changed()
        || navigation.is_changed()
        || session.is_changed())
    {
        return;
    }
    commands.entity(panel).despawn_children();
    if !ui.history_open {
        return;
    }
    let context = session.context();
    let snapshot = frame
        .for_session(&session)
        .and_then(|frame| frame.production.as_ref());
    commands.entity(panel).with_children(|panel| {
        panel.spawn((label("", 11.0, theme::GRAY), HistoryHint));
        let Some(snapshot)=snapshot else {
            panel.spawn(label("HISTORY / production evidence unavailable in this observation",14.0,theme::GRAY));
            return;
        };
        if let Some((scope, event)) = &history.selected_event {
            if session.accepts(scope) && snapshot.events.iter().any(|current| current == event) {
                panel.spawn(label(format!("SELECTED / WEEK {} / {}\n{}\nRECEIPT {}", event.week, event.kind, event.description, event.receipt_digest), 12.0, theme::YELLOW));
            }
        }
        let site=navigation.selected_site.as_ref().and_then(|id|snapshot.sites.iter().find(|site|site.id==*id));
        if let Some(site)=site {
            panel.spawn(label(format!("{} / {} {} per week | P planned / D produced",site.name,site.output_unit,site.output_good),13.0,theme::YELLOW));
            if let Some(error)=&history.error {panel.spawn(label(error,13.0,theme::RED));}
            else if history.points.is_empty() {panel.spawn(label("Reading committed weeks...",13.0,theme::GRAY));}
            else {
                let maximum=history.points.iter().flat_map(|point|[point.planned,point.produced]).flatten().max().unwrap_or(1);
                panel.spawn(Node{column_gap:px(5),align_items:AlignItems::End,flex_shrink:0.0,overflow:Overflow::scroll_x(),..default()}).with_children(|chart| {
                    for point in &history.points {
                        chart.spawn((Button,HistoryButton::Week{context:context.clone(),week:point.week},
                            Node{min_width:px(48),padding:UiRect::all(px(3)),row_gap:px(3),flex_direction:FlexDirection::Column,
                                border:UiRect::bottom(px(2)),..default()},
                            BorderColor::all(if point.week==session.viewed_tick {theme::YELLOW}else{theme::GRAY}),
                            BackgroundColor(theme::PANEL),
                            DeclaredSurface::new(SurfaceId::ObserverProduction)))
                        .with_children(|column| {
                            column.spawn(Node{height:px(56),column_gap:px(4),align_items:AlignItems::End,..default()}).with_children(|bars| {
                                bars.spawn((Node{width:px(16),height:px(bar_height(point.planned,maximum)),..default()},BackgroundColor(theme::GRAY)));
                                bars.spawn((Node{width:px(16),height:px(bar_height(point.produced,maximum)),..default()},BackgroundColor(theme::YELLOW)));
                            });
                            column.spawn(label(format!("P {}\nD {}\nW{:02}",point.planned.map_or_else(||"-".into(),grouped),point.produced.map_or_else(||"-".into(),grouped),point.week),11.0,theme::PAPER));
                        });
                    }
                });
                panel.spawn(label(format!("Scale 0-{} {} | - means no production receipt at foundation. Click a week to inspect.",grouped(maximum),site.output_unit),11.0,theme::GRAY));
            }
        } else {panel.spawn(label("Select a producer to chart its committed output. The log locates affected subjects.",13.0,theme::YELLOW));}

    });
}

/// The log reads the same committed observation as the map. It is independent
/// of chart disclosure and never fabricates communications or player acts.
fn paint_log(
    mut commands: Commands,
    session: Res<ObserverSession>,
    frame: Res<ObserverFrame>,
    history: Res<HistoryState>,
    ui: Res<ObserverUiState>,
    mut panels: Query<(Entity, &mut Visibility), With<LogPanel>>,
) {
    let Ok((entity, mut visibility)) = panels.single_mut() else {
        return;
    };
    visibility.set_if_neq(
        if ui.menu_open || ui.splash_visible || ui.comparison_open || ui.archive_open {
            Visibility::Hidden
        } else {
            Visibility::Visible
        },
    );
    if !(session.is_changed() || frame.is_changed() || history.is_changed() || ui.is_changed()) {
        return;
    }
    commands.entity(entity).despawn_children();
    let context = session.context();
    let snapshot = frame
        .for_session(&session)
        .and_then(|frame| frame.production.as_ref());
    commands.entity(entity).with_children(|panel| {
        panel.spawn(label("L O G", 22.0, theme::PAPER));
        panel.spawn((label("", 11.0, theme::GRAY), HistoryHint));
        let Some(snapshot) = snapshot else {
            panel.spawn(label("No production developments are available in this observation.", 13.0, theme::GRAY));
            return;
        };
        if let Some((scope, event)) = &history.selected_event {
            if session.accepts(scope) && snapshot.events.iter().any(|current| current == event) {
                panel.spawn(label(format!("EXAMINING / {}\n{}", event.kind.to_uppercase(), event.description), 13.0, theme::YELLOW));
                panel.spawn(label(format!("Committed week {}. Follow the affected subjects in the world. Receipt details are in Trends [H].", event.week), 11.0, theme::GRAY));
            }
        }
        if snapshot.events.is_empty() {
            panel.spawn(label("No developments are recorded through this point in the campaign. Run a month from the live edge to follow production and deliveries.", 14.0, theme::PAPER));
            return;
        }
        let shown = snapshot.events.len().min(160);
        panel.spawn(label(format!("Latest {shown} of {} committed developments. Select an entry to locate its subjects and inspect that point in time.", snapshot.events.len()), 11.0, theme::GRAY));
        let mut previous_month = None;
        for event in snapshot.events.iter().rev().take(shown) {
            let month = CampaignMonth::at_week(event.week).number;
            if previous_month != Some(month) {
                panel.spawn(label(format!("CAMPAIGN MONTH {month}"), 12.0, theme::YELLOW))
                    .insert(Node { margin: UiRect::top(px(8)), flex_shrink: 0.0, ..default() });
                previous_month = Some(month);
            }
            panel.spawn((Button, HistoryButton::Event { context: context.clone(), event: event.clone() },
                Node { padding: UiRect::axes(px(10), px(9)), border: UiRect::left(px(2)),
                    flex_direction: FlexDirection::Column, row_gap: px(5), flex_shrink: 0.0,
                    min_width: px(0), ..default() },
                BorderColor::all(theme::BLUE), BackgroundColor(theme::PANEL),
                DeclaredSurface::new(SurfaceId::ObserverProduction)))
                .with_children(|entry| {
                    entry.spawn(label(event.kind.to_uppercase(), 11.0, theme::BLUE));
                    entry.spawn(label(&event.description, 13.0, theme::PAPER));
                    entry.spawn(label(format!("Week {} / inspect consequence", event.week), 10.0, theme::GRAY));
                });
        }
    });
}

pub struct ObserverHistoryPlugin;
impl Plugin for ObserverHistoryPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<HistoryState>()
            .add_systems(Startup, setup)
            .add_systems(Update, input.in_set(ObserverSet::Input))
            .add_systems(
                Update,
                update
                    .after(ObserverSet::Install)
                    .before(ObserverSet::Paint),
            )
            .add_systems(
                Update,
                (
                    paint,
                    paint_log,
                    paint_buttons.run_if(history_buttons_need_paint),
                )
                    .chain()
                    .in_set(ObserverSet::Paint),
            );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::observer::SessionPhase;
    use babylon_persistence::{
        CampaignId, ObserverEconomySnapshotV1, ObserverVisibilityV1, ProductionSnapshotV1,
    };

    fn event(week: u64) -> ProductionEventV1 {
        ProductionEventV1 {
            id: format!("delivery-{week}"),
            week,
            subject_site_ids: vec!["producer".into()],
            kind: "delivery".into(),
            description: "Committed input delivery".into(),
            receipt_digest: "a".repeat(64),
        }
    }

    fn history_app(event: ProductionEventV1) -> (App, Entity) {
        let mut session = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(1)));
        session.ready(3, None);
        session.foundation_digest = Some("foundation".into());
        assert!(session.installed(&session.context()));
        let frame = ObserverFrame(Some(ObserverEconomySnapshotV1 {
            campaign_id: session.campaign.as_uuid().to_string(),
            resolve_tick: 3,
            foundation_digest: "foundation".into(),
            nominal_world_hash: None,
            tick_content_hash: None,
            envelope_digest: None,
            visibility: ObserverVisibilityV1::FullObserver,
            counties: vec![],
            production: Some(ProductionSnapshotV1 {
                labor_accounts: Vec::new(),
                scenario_label: "Designed test campaign".into(),
                horizon_week: 16,
                sites: vec![],
                routes: vec![],
                freight: vec![],
                events: vec![event],
                observed_contexts: Vec::new(),
                process_attributions: Vec::new(),
                provenance: vec![],
            }),
        }));
        let mut app = App::new();
        app.insert_resource(session)
            .insert_resource(frame)
            .insert_resource(ObserverUiState {
                history_open: true,
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .init_resource::<HistoryState>()
            .init_resource::<DossierRefresh>()
            .init_resource::<ObserverFeedback>()
            .init_resource::<Time>()
            .add_systems(
                Update,
                (input, paint_buttons.run_if(history_buttons_need_paint)).chain(),
            );
        let hint = app.world_mut().spawn((Text::new(""), HistoryHint)).id();
        (app, hint)
    }

    fn spawn_button(app: &mut App, button: HistoryButton, interaction: Interaction) -> Entity {
        app.world_mut()
            .spawn((
                button,
                interaction,
                BackgroundColor(theme::PANEL),
                BorderColor::all(theme::BLUE),
            ))
            .id()
    }

    #[derive(Resource, Default, Debug, PartialEq, Eq)]
    struct HistoryPaintChanges {
        visibility: usize,
        backgrounds: usize,
        borders: usize,
        text: usize,
    }

    type ChangedHistoryVisibility<'w, 's> = Query<
        'w,
        's,
        (),
        (
            Or<(With<HistoryPanel>, With<LogPanel>)>,
            Changed<Visibility>,
        ),
    >;

    fn record_paint_changes(
        panels: ChangedHistoryVisibility,
        backgrounds: Query<(), (With<HistoryButton>, Changed<BackgroundColor>)>,
        borders: Query<(), (With<HistoryButton>, Changed<BorderColor>)>,
        text: Query<(), Changed<Text>>,
        mut changes: ResMut<HistoryPaintChanges>,
    ) {
        *changes = HistoryPaintChanges {
            visibility: panels.iter().count(),
            backgrounds: backgrounds.iter().count(),
            borders: borders.iter().count(),
            text: text.iter().count(),
        };
    }

    fn history_buttons(app: &mut App) -> Vec<Entity> {
        let mut buttons = app
            .world_mut()
            .query_filtered::<Entity, With<HistoryButton>>();
        let mut entities = buttons.iter(app.world()).collect::<Vec<_>>();
        entities.sort_unstable();
        entities
    }

    #[test]
    fn idle_history_with_sixty_events_keeps_entities_and_components_unchanged() {
        let (mut app, _) = history_app(event(3));
        let events = (0..60)
            .map(|index| ProductionEventV1 {
                id: format!("delivery-3-{index}"),
                ..event(3)
            })
            .collect();
        app.world_mut()
            .resource_mut::<ObserverFrame>()
            .0
            .as_mut()
            .unwrap()
            .production
            .as_mut()
            .unwrap()
            .events = events;
        app.init_resource::<ProductionNavigation>()
            .init_resource::<HistoryPaintChanges>()
            .add_systems(Update, (paint, paint_log).chain().before(paint_buttons))
            .add_systems(PostUpdate, record_paint_changes);
        app.world_mut().spawn((HistoryPanel, Visibility::Hidden));
        app.world_mut().spawn((LogPanel, Visibility::Visible));
        app.update();
        let buttons = history_buttons(&mut app);
        assert_eq!(buttons.len(), 60);
        assert!(app.world().resource::<HistoryPaintChanges>().text > 0);

        app.update();
        assert_eq!(history_buttons(&mut app), buttons);
        assert_eq!(
            *app.world().resource::<HistoryPaintChanges>(),
            HistoryPaintChanges::default(),
            "idle history must not mark unchanged presentation components as changed"
        );
    }

    #[derive(Resource, Default)]
    struct ButtonPaintPasses(usize);

    fn record_button_paint(mut passes: ResMut<ButtonPaintPasses>) {
        passes.0 += 1;
    }

    #[test]
    fn button_paint_gate_skips_idle_and_wakes_for_real_ecs_changes() {
        let event = event(3);
        let (mut app, _) = history_app(event.clone());
        app.init_resource::<ButtonPaintPasses>().add_systems(
            Update,
            record_button_paint.run_if(history_buttons_need_paint),
        );
        let context = app.world().resource::<ObserverSession>().context();
        let entity = spawn_button(
            &mut app,
            HistoryButton::Event { context, event },
            Interaction::None,
        );
        app.update();
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 1);
        for (index, interaction) in [Interaction::Hovered, Interaction::None]
            .into_iter()
            .enumerate()
        {
            *app.world_mut().get_mut::<Interaction>(entity).unwrap() = interaction;
            app.update();
            assert_eq!(app.world().resource::<ButtonPaintPasses>().0, index + 2);
        }
        let context = app.world().resource::<ObserverSession>().context();
        *app.world_mut().get_mut::<HistoryButton>(entity).unwrap() =
            HistoryButton::Week { context, week: 2 };
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 4);
        app.world_mut().resource_mut::<ObserverFrame>().0 = None;
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 5);
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .set_perspective(Perspective::PlayerKnowledge);
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 6);
        app.world_mut().resource_mut::<ObserverUiState>().menu_open = true;
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 7);
        app.world_mut().resource_mut::<HistoryState>().error = Some("Unavailable".into());
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 8);
        app.world_mut().spawn((HistoryHint, Text::new("")));
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 9);
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 9);
        let context = app.world().resource::<ObserverSession>().context();
        spawn_button(
            &mut app,
            HistoryButton::Week { context, week: 1 },
            Interaction::None,
        );
        app.update();
        assert_eq!(app.world().resource::<ButtonPaintPasses>().0, 10);
    }

    #[test]
    fn unchanged_interaction_repaints_when_evidence_or_capability_changes() {
        let event = event(3);
        let (mut app, _) = history_app(event.clone());
        let context = app.world().resource::<ObserverSession>().context();
        let entity = spawn_button(
            &mut app,
            HistoryButton::Event {
                context,
                event: event.clone(),
            },
            Interaction::None,
        );
        app.update();
        assert_eq!(
            app.world().get::<BackgroundColor>(entity).unwrap().0,
            theme::PANEL
        );
        app.world_mut()
            .resource_mut::<ObserverFrame>()
            .0
            .as_mut()
            .unwrap()
            .production
            .as_mut()
            .unwrap()
            .events[0]
            .receipt_digest = "b".repeat(64);
        app.update();
        assert_eq!(
            app.world().get::<BackgroundColor>(entity).unwrap().0,
            theme::INK
        );
        app.world_mut()
            .resource_mut::<ObserverFrame>()
            .0
            .as_mut()
            .unwrap()
            .production
            .as_mut()
            .unwrap()
            .events[0] = event;
        app.update();
        assert_eq!(
            app.world().get::<BackgroundColor>(entity).unwrap().0,
            theme::PANEL
        );
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .set_perspective(Perspective::PlayerKnowledge);
        app.update();
        assert_eq!(
            app.world().get::<BackgroundColor>(entity).unwrap().0,
            theme::INK
        );
        *app.world_mut().get_mut::<Interaction>(entity).unwrap() = Interaction::Pressed;
        app.update();
        assert!(app
            .world()
            .resource::<HistoryState>()
            .selected_event
            .is_none());
        assert_eq!(
            app.world().resource::<ObserverFeedback>().message,
            Some("History changed; wait for its current observation")
        );
    }

    #[test]
    fn pending_week_and_event_buttons_explain_refusal_without_selecting_evidence() {
        for choose_event in [false, true] {
            let event = event(3);
            let (mut app, _) = history_app(event.clone());
            let context = {
                let mut session = app.world_mut().resource_mut::<ObserverSession>();
                session.begin_advance().unwrap();
                session.context()
            };
            let button = if choose_event {
                HistoryButton::Event { context, event }
            } else {
                HistoryButton::Week { context, week: 2 }
            };
            let entity = spawn_button(&mut app, button, Interaction::Pressed);
            app.update();
            let session = app.world().resource::<ObserverSession>();
            assert_eq!(session.viewed_tick, 3);
            assert!(session.advance_pending());
            assert_eq!(session.phase, SessionPhase::Advancing);
            assert!(app
                .world()
                .resource::<HistoryState>()
                .selected_event
                .is_none());
            assert_eq!(app.world().resource::<DossierRefresh>().0, 0);
            assert_eq!(
                app.world().resource::<ObserverFeedback>().message,
                Some("Wait for the current week to finish committing")
            );
            assert_eq!(
                app.world().get::<BackgroundColor>(entity).unwrap().0,
                theme::INK
            );
        }
    }

    #[test]
    fn hovering_disabled_history_explains_without_mutating_feedback() {
        let (mut app, hint) = history_app(event(2));
        let context = {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.begin_advance().unwrap();
            session.context()
        };
        spawn_button(
            &mut app,
            HistoryButton::Week { context, week: 2 },
            Interaction::Hovered,
        );
        app.update();
        app.update();
        assert_eq!(
            app.world().get::<Text>(hint).unwrap().0,
            "Wait for the current week to finish committing"
        );
        assert_eq!(app.world().resource::<ObserverFeedback>().revision, 0);
        assert!(app.world().resource::<ObserverFeedback>().message.is_none());
    }

    #[test]
    fn valid_event_navigation_refreshes_the_dossier_and_binds_selected_evidence() {
        let event = event(2);
        let (mut app, _) = history_app(event.clone());
        let context = app.world().resource::<ObserverSession>().context();
        app.world_mut().resource_mut::<ObserverSession>().playing = true;
        spawn_button(
            &mut app,
            HistoryButton::Event {
                context,
                event: event.clone(),
            },
            Interaction::Pressed,
        );
        app.update();
        let session = app.world().resource::<ObserverSession>();
        assert_eq!(session.viewed_tick, 2);
        assert_eq!(session.phase, SessionPhase::Loading);
        assert!(!session.playing);
        assert_eq!(app.world().resource::<DossierRefresh>().0, 1);
        assert_eq!(
            app.world().resource::<HistoryState>().selected_event,
            Some((session.context(), event))
        );
    }

    #[test]
    fn log_navigation_works_with_trends_closed_and_clears_on_perspective_change() {
        use bevy::ecs::system::RunSystemOnce;
        let event = event(2);
        let (mut app, _) = history_app(event.clone());
        app.world_mut()
            .resource_mut::<ObserverUiState>()
            .history_open = false;
        app.world_mut().spawn((LogPanel, Visibility::Visible));
        app.world_mut().run_system_once(paint_log).unwrap();
        let mut query = app.world_mut().query::<(Entity, &HistoryButton)>();
        let button = query
            .iter(app.world())
            .find_map(|(entity, button)| {
                matches!(button, HistoryButton::Event { .. }).then_some(entity)
            })
            .unwrap();
        app.world_mut()
            .entity_mut(button)
            .insert(Interaction::Pressed);
        app.update();
        assert_eq!(app.world().resource::<ObserverSession>().viewed_tick, 2);
        assert!(app
            .world()
            .resource::<HistoryState>()
            .selected_event
            .is_some());

        app.world_mut()
            .resource_mut::<ObserverSession>()
            .set_perspective(Perspective::PlayerKnowledge);
        app.world_mut().run_system_once(paint_log).unwrap();
        let mut query = app.world_mut().query::<&HistoryButton>();
        assert_eq!(query.iter(app.world()).count(), 0);
        let mut texts = app.world_mut().query::<&Text>();
        assert!(!texts
            .iter(app.world())
            .any(|text| text.0.contains(&event.description)));
    }

    #[test]
    fn an_examined_event_focuses_once_without_overriding_later_navigation() {
        use bevy::ecs::system::RunSystemOnce;
        let event = event(3);
        let (mut app, _) = history_app(event.clone());
        app.world_mut()
            .resource_mut::<ObserverUiState>()
            .history_open = false;
        app.init_resource::<ProductionNavigation>()
            .add_message::<ProductionCommand>();
        let context = app.world().resource::<ObserverSession>().context();
        {
            let mut history = app.world_mut().resource_mut::<HistoryState>();
            history.selected_event = Some((context, event));
            history.focus_selected_event = true;
        }
        app.world_mut().run_system_once(update).unwrap();
        let messages = app
            .world_mut()
            .resource_mut::<Messages<ProductionCommand>>()
            .drain()
            .count();
        assert_eq!(messages, 1);
        app.world_mut()
            .resource_mut::<ProductionNavigation>()
            .selected_site = Some("other".into());
        app.world_mut().run_system_once(update).unwrap();
        assert_eq!(
            app.world_mut()
                .resource_mut::<Messages<ProductionCommand>>()
                .drain()
                .count(),
            0
        );
        assert!(app
            .world()
            .resource::<HistoryState>()
            .selected_event
            .is_some());
    }

    #[test]
    fn event_navigation_rejects_changed_evidence_and_stale_capability_context() {
        let mut event = event(2);
        let (mut app, _) = history_app(event.clone());
        let context = app.world().resource::<ObserverSession>().context();
        event.receipt_digest = "b".repeat(64);
        let button = HistoryButton::Event { context, event };
        assert_eq!(
            button_availability(
                &button,
                app.world().resource::<ObserverSession>(),
                app.world().resource::<ObserverFrame>(),
            ),
            ControlAvailability::Disabled("This event is unavailable in the current observation")
        );
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .set_perspective(Perspective::PlayerKnowledge);
        assert_eq!(
            button_availability(
                &button,
                app.world().resource::<ObserverSession>(),
                app.world().resource::<ObserverFrame>(),
            ),
            ControlAvailability::Disabled("History changed; wait for its current observation")
        );
    }

    #[test]
    fn exact_history_distinguishes_foundation_zero_and_overflow() {
        let mut site = ProductionSiteV1 {
            id: "site".into(),
            county_geoid: "26163".into(),
            name: "cohort".into(),
            industry_code: "331".into(),
            observed_employment: None,
            output_good_id: "a".repeat(64),
            output_unit_id: "b".repeat(64),
            output_good: "sheet".into(),
            output_unit: "kg".into(),
            output_per_batch: 10,
            available_batches: 8,
            planned_batches: None,
            produced_batches: None,
            inventory: vec![],
            inputs: vec![],
            labor: vec![],
        };
        assert_eq!(WeeklyOutput::from_site(0, &site).unwrap().produced, None);
        site.planned_batches = Some(8);
        site.produced_batches = Some(0);
        assert_eq!(
            WeeklyOutput::from_site(1, &site).unwrap(),
            WeeklyOutput {
                week: 1,
                planned: Some(80),
                produced: Some(0)
            }
        );
        site.produced_batches = Some(u64::MAX);
        assert!(WeeklyOutput::from_site(2, &site).is_err());
    }
}
