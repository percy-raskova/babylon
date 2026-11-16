//! Resolve the selected aggregate to locations of its actual settled or recorded endpoints.
use super::rail;
use super::state::{
    self, Action, Connection, ConnectionKey, Direction, MoneyView, Observation, Page, Quantity,
    Scope,
};
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use babylon_persistence::money_journal::{
    FlowDirection, FlowGroup, FlowPeer, FlowQuery, FlowRow, JournalError, LaborFlowRow,
};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};

pub(super) fn request(scope: &Scope, selected: &ConnectionKey, offset: u64) -> FlowQuery {
    let direction = match selected.direction {
        Direction::PaidTo => FlowDirection::Inbound,
        Direction::ReceivedFrom => FlowDirection::Outbound,
        Direction::Internal => FlowDirection::Within,
    };
    FlowQuery {
        group: FlowGroup::Location,
        peer: Some(FlowPeer {
            group: scope.group,
            key: selected.peer.clone(),
            direction,
        }),
        ..state::flow_query(scope, offset)
    }
}

#[derive(Clone, PartialEq, Eq)]
struct Geography {
    rows: Vec<Connection>,
    total: u64,
    remainder: Quantity,
}
impl Geography {
    fn from_page(page: &Page, selected: &Connection) -> Result<Self, JournalError> {
        let (actual, remainder) = match page {
            Page::Money(p) => {
                let amount = |r: &FlowRow| {
                    Quantity::Money(match selected.key.direction {
                        Direction::PaidTo => r.current.inflow_micros.clone(),
                        Direction::ReceivedFrom => r.current.outflow_micros.clone(),
                        Direction::Internal => r.current.internal_micros.clone(),
                    })
                };
                (amount(&p.total), amount(&p.remainder))
            }
            Page::Labor(p) => {
                let amount = |r: &LaborFlowRow| {
                    Quantity::Labor(match selected.key.direction {
                        Direction::PaidTo => r.current.inbound.clone(),
                        Direction::ReceivedFrom => r.current.outbound.clone(),
                        Direction::Internal => r.current.within.clone(),
                    })
                };
                (amount(&p.total), amount(&p.remainder))
            }
        };
        if actual != selected.quantity {
            return Err(JournalError::Projection);
        }
        Ok(Self {
            rows: page.connections(),
            total: page.total_groups(),
            remainder,
        })
    }
}

#[derive(Clone, Default, PartialEq, Eq)]
pub(super) struct Locations {
    offset: u64,
    result: Option<Result<Geography, JournalError>>,
}
impl Locations {
    pub(super) fn rows(&self) -> &[Connection] {
        self.result
            .as_ref()
            .and_then(|r| r.as_ref().ok())
            .map_or(&[], |g| g.rows.as_slice())
    }
    pub(super) fn can_navigate(&self, delta: i8) -> bool {
        match (&self.result, delta) {
            (Some(Ok(_)), -1) => self.offset > 0,
            (Some(Ok(g)), 1) => self.offset + 20 < g.total,
            (Some(Err(_)), 0) => true,
            _ => false,
        }
    }
    pub(super) fn navigate(&mut self, delta: i8) -> bool {
        if !self.can_navigate(delta) {
            return false;
        }
        self.offset = self.offset.saturating_add_signed(i64::from(delta) * 20);
        self.result = None;
        true
    }
}

// Updating these children separately preserves focus on the selected aggregate while its
// locations load. A map/Sankey switch keeps the same controls and their keyboard focus.
#[derive(Component, Default)]
pub(super) struct LocationList {
    displayed: Option<(ConnectionKey, Locations)>,
}

pub(super) fn draw_locations(
    mut commands: Commands,
    view: Res<MoneyView>,
    obs: Observation,
    mut lists: Query<(Entity, &mut LocationList)>,
) {
    let Ok((entity, mut list)) = lists.single_mut() else {
        return;
    };
    if !view.is_changed() && !obs.counties.is_changed() && !list.is_added() {
        return;
    }
    let selected = view.selected_row();
    let displayed = list.displayed.as_ref().map(|(key, page)| (key, page));
    let requested = selected.map(|row| (&row.key, &view.geography));
    if requested == displayed && !obs.counties.is_changed() {
        return;
    }
    list.displayed = requested.map(|(key, page)| (key.clone(), page.clone()));
    let mut parent = commands.entity(entity);
    parent.despawn_children();
    let (Some(scope), Some(selected)) = (view.scope.as_ref(), selected) else {
        return;
    };
    parent.with_children(|panel| location_controls(panel, &view, &obs, scope, selected));
}

fn location_controls(
    panel: &mut ChildSpawnerCommands,
    view: &MoneyView,
    obs: &Observation,
    scope: &Scope,
    selected: &Connection,
) {
    let label = |text| rail::label(text, 15.0, theme::PAPER, ObserverFontRole::Body);
    let page = match &view.geography.result {
        None => {
            panel.spawn(label(
                "Reading the selected connection’s locations…".to_owned(),
            ));
            return;
        }
        Some(Err(error)) => {
            panel.spawn(label(format!("Location detail unavailable ({error}).")));
            return;
        }
        Some(Ok(page)) if page.total == 0 => {
            panel.spawn(label(
                "No location movements in the selected periods.".to_owned(),
            ));
            return;
        }
        Some(Ok(page)) => page,
    };
    let offset = view.geography.offset;
    let end = (offset + 20).min(page.total);
    panel.spawn(label(format!(
        "Locations {}–{end} of {}",
        offset + 1,
        page.total
    )));
    for row in &page.rows {
        let name = rail::location(row.key.peer.as_deref(), &obs.atlas);
        let amount = rail::reading(&row.quantity);
        let text = format!("{name} · {amount}");
        if obs.followable_county(&row.key).is_some() {
            rail::control(
                panel,
                view,
                scope,
                Action::FollowLeg {
                    aggregate: selected.key.clone(),
                    leg: row.key.clone(),
                },
                format!("Open {text}"),
            );
        } else {
            panel.spawn(label(text));
        }
    }
    if page.total > end - offset {
        panel.spawn(label(format!(
            "Other locations · {}",
            rail::reading(&page.remainder)
        )));
    }
}

struct Pending {
    scope: Scope,
    selected: Connection,
    offset: u64,
    read: Task<Result<Geography, JournalError>>,
}
#[derive(Resource, Default)]
pub(super) struct Worker(Option<Pending>);
pub(super) fn update(mut view: ResMut<MoneyView>, mut worker: ResMut<Worker>) {
    if let Some(job) = &mut worker.0 {
        let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(&mut job.read))
        else {
            return;
        };
        if view.scope.as_ref() == Some(&job.scope)
            && view.selected_row() == Some(&job.selected)
            && view.geography.offset == job.offset
        {
            view.geography.result = Some(result);
        }
        worker.0 = None;
    }
    let Some(scope) = view.scope.as_ref() else {
        return;
    };
    if scope.group == FlowGroup::Location || view.geography.result.is_some() {
        return;
    }
    let Some(selected) = view.selected_row() else {
        return;
    };
    let offset = view.geography.offset;
    let requested = scope.clone();
    let chosen = selected.clone();
    worker.0 = Some(Pending {
        scope: scope.clone(),
        selected: selected.clone(),
        offset,
        read: IoTaskPool::get().spawn(async move {
            let query = request(&requested, &chosen.key, offset);
            let page = state::read_page(&requested, &query)?;
            Geography::from_page(&page, &chosen)
        }),
    });
}
pub(super) fn rows(view: &MoneyView) -> &[Connection] {
    if view
        .scope
        .as_ref()
        .is_some_and(|s| s.group == FlowGroup::Location)
    {
        &view.rows
    } else {
        view.geography.rows()
    }
}

#[cfg(test)]
mod tests {
    use super::super::state::{Action, Diagram, Measure, Target};
    use super::*;
    use crate::atlas::CountyAtlas;
    use crate::map::{MapPlugin, SelectedCounty};
    use crate::observer_focus::{ObserverFocusTarget, ObserverKeyboardActivate};
    use crate::observer_map3d::{CountyAnchors, MapOrbit};
    use crate::observer_ui::{ObserverFrame, ObserverViewport};
    use crate::ui::Interaction;
    use babylon_persistence::money_journal::LaborAmount;
    use babylon_persistence::observer_reader::ObserverCountyEconomy;

    fn group_page(row: &Connection) -> Page {
        use babylon_persistence::money_journal::{FlowPage, LaborDirections, LaborFlowPage};
        match &row.quantity {
            Quantity::Money(value) => {
                let group =
                    super::super::tests::counterparty(row.key.peer.as_deref(), value, "0", "0");
                Page::Money(Box::new(FlowPage {
                    groups: vec![group.clone()],
                    total: group,
                    remainder: super::super::tests::counterparty(None, "0", "0", "0"),
                }))
            }
            Quantity::Labor(amount) => {
                let zero = LaborAmount {
                    recorded_micro_hours: "0".into(),
                    unknown_basis_movements: "0".into(),
                    movement_count: "0".into(),
                };
                let group = LaborFlowRow {
                    key: row.key.peer.clone(),
                    label: None,
                    rank: Some(1),
                    groups: 1,
                    current: LaborDirections {
                        inbound: amount.clone(),
                        outbound: zero.clone(),
                        within: zero.clone(),
                        net_recorded_micro_hours: "0".into(),
                    },
                    comparison: None,
                    net_change_recorded_micro_hours: None,
                };
                let mut remainder = group.clone();
                remainder.groups = 0;
                remainder.current.inbound = zero;
                Page::Labor(Box::new(LaborFlowPage {
                    county_carry: None,
                    groups: vec![group.clone()],
                    total: group,
                    remainder,
                }))
            }
        }
    }

    fn leg_scene(diagram: Diagram, measure: Measure, group: FlowGroup) -> (App, Scope) {
        let (mut app, entity, mut scope, mut aggregate) =
            super::super::tests::interaction_fixture();
        scope.group = group;
        scope.measure = measure;
        aggregate.key.peer = Some(
            if group == FlowGroup::Industry {
                "food"
            } else {
                "company:0011"
            }
            .into(),
        );
        let mut leg = aggregate.clone();
        leg.key.peer = Some("county:26099".into());
        if measure == Measure::Labor {
            leg.quantity = Quantity::Labor(LaborAmount {
                recorded_micro_hours: "0".into(),
                unknown_basis_movements: "1".into(),
                movement_count: "1".into(),
            });
            aggregate.quantity = leg.quantity.clone();
        }
        let mut rows = vec![leg.clone()];
        for key in [
            None,
            Some("county:26163"),
            Some("county:26125"),
            Some("foreign:canada"),
        ] {
            let mut other = leg.clone();
            other.key.peer = key.map(str::to_owned);
            rows.push(other);
        }
        let world = app.world_mut();
        world
            .resource_mut::<ObserverFrame>()
            .0
            .as_mut()
            .expect("installed")
            .counties = ["26099", "26163"]
            .map(|key| ObserverCountyEconomy {
                county_geoid: key.into(),
                annual_avg_estabs_count: None,
                annual_avg_emplvl: None,
                total_annual_wages: None,
                annual_avg_wkly_wage: None,
            })
            .to_vec();
        {
            let mut view = world.resource_mut::<MoneyView>();
            view.scope = Some(scope.clone());
            view.measure = measure;
            view.diagram = diagram;
            view.rows = vec![aggregate.clone()];
            view.page = Some(group_page(&aggregate));
        }
        world.entity_mut(entity).insert(Target {
            scope: scope.clone(),
            offset: 0,
            action: Action::Select(aggregate.key.clone()),
        });
        world.trigger(ObserverKeyboardActivate {
            entity,
            context: Some(scope.context.clone()),
        });
        world.resource_mut::<MoneyView>().geography.result = Some(Ok(Geography {
            rows,
            total: 5,
            remainder: leg.quantity.clone(),
        }));
        world.spawn((state::MoneyRail, Node::default()));
        crate::visual_assets::install_test_assets(&mut app);
        app.add_plugins(MapPlugin)
            .init_asset::<StandardMaterial>()
            .init_resource::<CountyAnchors>()
            .init_resource::<MapOrbit>()
            .init_resource::<ObserverViewport>();
        state::install(&mut app);
        app.finish();
        app.cleanup();
        app.update();
        (app, scope)
    }

    fn visible_text(app: &mut App, fragment: &str) -> bool {
        let world = app.world_mut();
        world
            .query::<&Text>()
            .iter(world)
            .any(|text| text.0.contains(fragment))
    }

    #[test]
    fn selected_industry_geographic_arrows_and_sankey_keep_the_same_hue() {
        use super::super::{grouping, sankey_image, sankey_layout};
        use bevy::color::ColorToPacked;
        let (mut app, scope) = leg_scene(Diagram::Map, Measure::Money, FlowGroup::Industry);
        let atlas = app.world().resource::<CountyAtlas>();
        let counties = ["26163", "26099"].map(|id| atlas.index_of_fips(id).expect("county"));
        let anchors = CountyAnchors::from_atlas(atlas, &counties, Vec2::ZERO);
        app.insert_resource(anchors);
        app.update();
        let world = app.world_mut();
        let hue = grouping::industry_color(Some("food"));
        let mut arrows = world.query::<(&Target, &MeshMaterial3d<StandardMaterial>)>();
        let arrow = arrows.iter(world).find_map(|(target, handle)| {
            matches!(&target.action, Action::FollowLeg { leg, .. } if leg.peer.as_deref() == Some("county:26099"))
                .then_some(handle)
        }).expect("selectable industry leg to Macomb");
        assert_eq!(
            world
                .resource::<Assets<StandardMaterial>>()
                .get(&arrow.0)
                .expect("arrow material")
                .base_color,
            hue
        );
        let view = world.resource::<MoneyView>();
        let diagram = sankey_layout::layout(&scope.county, &view.rows);
        let image = sankey_image::paint(&diagram, view);
        let pixels = image.data.as_deref().expect("CPU diagram");
        for color in [hue, crate::observer_theme::PAPER] {
            let rgb = color.to_srgba().to_u8_array();
            assert!(
                pixels.as_chunks::<4>().0.contains(&rgb),
                "selected industry fill and outline"
            );
        }
    }

    #[test]
    fn a_retried_location_page_replaces_its_error_and_changed_recorded_hours() {
        let (mut app, _) = leg_scene(Diagram::Sankey, Measure::Labor, FlowGroup::Company);
        assert!(visible_text(
            &mut app,
            "unknown prior labor in 1 of 1 movements"
        ));
        let mut recovered = app
            .world_mut()
            .resource_mut::<MoneyView>()
            .geography
            .result
            .replace(Err(JournalError::Database))
            .expect("initial result")
            .expect("page");
        app.update();
        assert!(visible_text(&mut app, "Location detail unavailable"));
        let Quantity::Labor(amount) = &mut recovered.rows[0].quantity else {
            panic!("labor fixture")
        };
        amount.recorded_micro_hours = "3000000".into();
        app.world_mut().resource_mut::<MoneyView>().geography.result = Some(Ok(recovered));
        app.update();
        assert!(visible_text(
            &mut app,
            "3 recorded h, unknown prior labor in 1 of 1 movements"
        ));
        let mut view = app.world_mut().resource_mut::<MoneyView>();
        let rows = &mut view
            .geography
            .result
            .as_mut()
            .expect("result")
            .as_mut()
            .expect("page")
            .rows;
        let Quantity::Labor(amount) = &mut rows[0].quantity else {
            panic!("labor fixture")
        };
        amount.unknown_basis_movements = "0".into();
        app.update();
        assert!(visible_text(&mut app, "3 recorded h"));
        assert!(!visible_text(&mut app, "3 recorded h, unknown prior labor"));
    }

    #[test]
    fn aggregate_endpoint_controls_follow_only_disclosed_counties_in_map_and_sankey() {
        for (diagram, measure) in [
            (Diagram::Map, Measure::Money),
            (Diagram::Sankey, Measure::Labor),
        ] {
            let (mut app, scope) = leg_scene(diagram, measure, FlowGroup::Company);
            let world = app.world_mut();
            let mut buttons = world.query::<(Entity, &Children, &ObserverFocusTarget)>();
            let endpoints: Vec<_> = buttons
                .iter(world)
                .filter(|(_, children, _)| {
                    children.iter().any(|child| {
                        world.get::<Text>(child).is_some_and(|label| {
                            label.0.starts_with("Open ")
                                && label.0.contains(" · ")
                                && label.0.contains("County")
                        })
                    })
                })
                .map(|(entity, children, focus)| {
                    assert!(children
                        .iter()
                        .filter_map(|child| world.get::<Text>(child))
                        .any(|text| text.0.contains("Macomb") && text.0.contains("26099")));
                    (entity, focus.available)
                })
                .collect();
            assert_eq!(
                endpoints.len(),
                1,
                "only Macomb is a disclosed, distinct map county"
            );
            let (endpoint, enabled) = endpoints[0];
            assert!(enabled);
            let destination = world
                .resource::<CountyAtlas>()
                .index_of_fips("26099")
                .expect("Macomb");
            let home = world.resource::<SelectedCounty>().0;
            if measure == Measure::Money {
                use bevy::ecs::system::RunSystemOnce;
                world.entity_mut(endpoint).insert(Interaction::Pressed);
                world
                    .run_system_once(state::press_rail)
                    .expect("press rail");
            } else {
                world.trigger(ObserverKeyboardActivate {
                    entity: endpoint,
                    context: Some(scope.context.clone()),
                });
            }
            let world = app.world_mut();
            world.flush();
            assert_eq!(
                world.resource::<SelectedCounty>().0,
                Some(destination),
                "the {diagram:?} control opens its disclosed destination"
            );
            world.resource_mut::<SelectedCounty>().0 = home;
            world.resource_mut::<MoneyView>().geography = Locations::default();
            world.trigger(ObserverKeyboardActivate {
                entity: endpoint,
                context: Some(scope.context),
            });
            world.flush();
            assert_eq!(
                world.resource::<SelectedCounty>().0,
                home,
                "a previous geography page cannot open a county"
            );
        }
    }
}
