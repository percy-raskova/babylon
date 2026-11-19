//! One county-level button per disclosed function. The reader preserves each exact site identity.
#[path = "map_household_food.rs"]
mod household_food;
use super::CountyAnchors;
use super::{
    EconomyEntity, NetworkLegend, NetworkNode, NetworkProjection, NetworkSector,
    ObservationContext, ObserverFontRole, RelationshipObservation,
};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::map::SelectedCounty;
use crate::observer::ObserverSession;
use crate::observer_focus::{ObserverFocusTarget, ObserverKeyboardActivate};
use crate::observer_map3d::symbols::GeographicSymbol;
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverFrame, ObserverUiState};
use crate::production::PrimaryView;
use crate::production::ProductionCommand;
use crate::visual_assets::{MapSymbol, VisualAssets};
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_persistence::production_observation::{ProductionSite, ProductionSiteRole};
use bevy::ecs::system::SystemParam;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::input_focus::{FocusCause, InputFocus};
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;
use household_food::FoodPanel;
use std::collections::BTreeMap;

pub(super) fn kinds(site: &ProductionSite) -> Vec<MapSymbol> {
    let mut symbols = Vec::new();
    if site.roles.contains(&ProductionSiteRole::Production) {
        symbols.push(
            if EconomicFunction::from_source_key(&site.function)
                == Some(EconomicFunction::EnergyUtilities)
                || site.sector_code.as_deref() == Some("22")
            {
                MapSymbol::Utility
            } else {
                MapSymbol::Producer
            },
        );
    }
    if site.roles.contains(&ProductionSiteRole::Retail) {
        symbols.push(MapSymbol::Shop);
    }
    symbols
}

fn label(kind: MapSymbol) -> &'static str {
    match kind {
        MapSymbol::Producer => "Producers",
        MapSymbol::Shop => "Shops",
        MapSymbol::Utility => "Energy / utilities",
        _ => unreachable!("only workplace symbols enter the economic network"),
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Group {
    county: String,
    kind: MapSymbol,
}

#[derive(Clone, Component, PartialEq, Eq)]
pub(super) struct Selection {
    context: ObservationContext,
    scope: Option<usize>,
    group: Group,
}
#[derive(Resource, Default)]
pub(super) struct Active(Option<Selection>);

/// Follow the same county's food control when the map rebuilds around a selection.
#[derive(SystemParam)]
pub(super) struct LegendFocus<'w, 's> {
    focus: Option<ResMut<'w, InputFocus>>,
    controls: Query<'w, 's, &'static Selection>,
}

impl LegendFocus<'_, '_> {
    fn restore(&mut self, choice: &Selection, opened: bool, button: Entity) {
        let Some(focus) = self.focus.as_deref_mut() else {
            return;
        };
        let Some(previous) = focus
            .get()
            .and_then(|entity| self.controls.get(entity).ok())
        else {
            return;
        };
        if previous.context == choice.context
            && previous.group == choice.group
            && (previous.scope == choice.scope || opened)
        {
            focus.set(button, FocusCause::Navigated);
        }
    }
}

#[derive(SystemParam)]
struct FacilityInput<'w> {
    selected: ResMut<'w, SelectedCounty>,
    active: ResMut<'w, Active>,
    session: Res<'w, ObserverSession>,
    frame: Res<'w, ObserverFrame>,
    view: Res<'w, PrimaryView>,
    ui: Res<'w, ObserverUiState>,
    anchors: Res<'w, CountyAnchors>,
}

impl FacilityInput<'_> {
    fn choose(&mut self, target: &Selection) {
        if !super::usable(&self.ui, *self.view)
            || !self.session.accepts(&target.context)
            || target.scope != self.selected.0
            || super::super::disclosed_snapshot(&self.frame, &self.session).is_none()
        {
            return;
        }
        let mut choice = target.clone();
        if choice.group.kind == MapSymbol::FoodShortage {
            if let Some(anchor) = self.anchors.0.get(&choice.group.county) {
                choice.scope = Some(anchor.index);
                if self.selected.0 != choice.scope {
                    self.selected.0 = choice.scope;
                }
            }
        }
        self.active.0 = (self.active.0.as_ref() != Some(&choice)).then_some(choice);
    }
}

fn pointer(event: On<PointerClick>, targets: Query<&Selection>, mut input: FacilityInput) {
    if event.button != PointerButton::Primary {
        return;
    }
    if let Ok(target) = targets.get(event.entity) {
        input.choose(target);
    }
}
fn keyboard(
    event: On<ObserverKeyboardActivate>,
    targets: Query<&Selection>,
    mut input: FacilityInput,
) {
    let Ok(target) = targets.get(event.entity) else {
        return;
    };
    if Some(&target.context) == event.context.as_ref() {
        input.choose(target);
    }
}

fn caption(text: impl Into<String>, color: Color) -> impl Bundle {
    (
        Text::new(text),
        TextFont {
            font_size: FontSize::Px(14.0),
            ..default()
        },
        TextColor(color),
        ObserverFontRole::Body,
        Pickable::IGNORE,
    )
}

fn workplace_group(
    panel: &mut ChildSpawnerCommands,
    assets: &VisualAssets,
    target: Selection,
    sites: &[&NetworkNode],
    county_name: &str,
    selected: bool,
) {
    let context = target.context.clone();
    let mut focus = ObserverFocusTarget::action(Some(context.clone()));
    focus.available = true;
    let symbol = target.group.kind;
    panel
        .spawn((
            crate::ui::pressable(),
            focus,
            target,
            Node {
                align_items: AlignItems::Center,
                column_gap: px(6),
                border: UiRect::left(px(2)),
                ..default()
            },
            BorderColor::all(if selected { theme::YELLOW } else { theme::LAND }),
            BackgroundColor(theme::PANEL),
        ))
        .observe(pointer)
        .observe(keyboard)
        .with_children(|row| {
            row.spawn((
                symbol.image(assets),
                Node {
                    width: px(25),
                    height: px(25),
                    ..default()
                },
                Pickable::IGNORE,
            ));
            row.spawn(caption(
                format!("{} · {}", label(symbol), sites.len()),
                theme::PAPER,
            ));
        });
    if selected {
        panel.spawn(caption(
            format!("{county_name} · open a site"),
            theme::YELLOW,
        ));
        for node in sites {
            crate::production::button(
                panel,
                node.caption.lines().next().unwrap_or(&node.site_id),
                ProductionCommand::Select {
                    site_id: node.site_id.clone(),
                    context: context.clone(),
                },
            );
        }
    }
}

fn workplace_groups(projection: &NetworkProjection) -> BTreeMap<Group, Vec<&NetworkNode>> {
    let mut groups = BTreeMap::<Group, Vec<&NetworkNode>>::new();
    for node in projection.nodes.values() {
        for &kind in &node.symbols {
            groups
                .entry(Group {
                    county: node.county.clone(),
                    kind,
                })
                .or_default()
                .push(node);
        }
    }
    groups
}

pub(super) fn spawn(
    commands: &mut Commands,
    projection: &NetworkProjection,
    obs: &RelationshipObservation,
    visual: &VisualAssets,
    active: &Active,
    keyboard: &mut LegendFocus,
) {
    let groups = workplace_groups(projection);
    let current_county = obs.selected_place().map(|(county, _)| county);
    let selection = |group: &Group| Selection {
        context: obs.session.context(),
        scope: obs.selected.0,
        group: group.clone(),
    };
    let resident_hubs = FoodPanel::represented(obs, projection, active);
    for food in resident_hubs.values() {
        food.spawn_marker(commands, obs, visual);
    }
    let selected = active
        .0
        .as_ref()
        .filter(|s| *s == &selection(&s.group) && groups.contains_key(&s.group));
    for (group, sites) in &groups {
        let Some(anchor) = obs.anchors.0.get(&group.county) else {
            continue;
        };
        let focused = selected.is_some_and(|s| s.group == *group);
        GeographicSymbol {
            anchor: sites[0].position,
            symbol: group.kind,
            view: crate::production::PrimaryView::Map,
            surface: SurfaceId::ObserverProduction,
            label: format!(
                "{} · {} · {} cohorts",
                anchor.name,
                label(group.kind),
                sites.len()
            ),
            priority: if focused {
                0
            } else if current_county == Some(&group.county) {
                1
            } else {
                3
            },
        }
        .spawn(commands, visual, focused)
        .insert((selection(group), EconomyEntity))
        .observe(pointer);
    }
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                flex_direction: FlexDirection::Column,
                row_gap: px(3),
                padding: UiRect::all(px(8)),
                overflow: Overflow::scroll_y(),
                ..default()
            },
            BackgroundColor(theme::INK.with_alpha(0.94)),
            ZIndex(6),
            Visibility::Hidden,
            EconomyEntity,
            NetworkLegend,
            crate::observer_map3d::symbols::MapObstruction,
            TabGroup::new(24),
            DeclaredSurface::new(SurfaceId::ObserverProduction),
        ))
        .with_children(|panel| {
            if let Some(food) = current_county.and_then(|county| resident_hubs.get(county)) {
                food.spawn_reading(panel, visual, keyboard);
            }
            panel.spawn(caption("County workplaces", theme::PAPER));
            panel.spawn(caption("Symbols mark county groups.", theme::GRAY));
            for (group, sites) in &groups {
                if current_county != Some(&group.county)
                    && selected.is_none_or(|s| s.group != *group)
                {
                    continue;
                }
                let open = selected.is_some_and(|s| s.group == *group);
                workplace_group(
                    panel,
                    visual,
                    selection(group),
                    sites,
                    &obs.anchors.0[&group.county].name,
                    open,
                );
            }
            for &sector in &NetworkSector::GROUPS {
                if projection
                    .nodes
                    .values()
                    .any(|n| n.sector == sector && n.symbols.is_empty())
                {
                    panel.spawn(caption(
                        format!("■ {}", sector.label()),
                        super::sector_color(sector),
                    ));
                }
            }
        });
}

#[cfg(test)]
mod tests {
    use super::super::{EconomyNode, HoveredNode, NetworkScope};
    use super::*;
    use crate::map::SelectedCounty;
    use crate::map_economy_lens::{EconomyMetric, MapLens};
    use crate::observer::{ObserverSession, Perspective};
    use crate::observer_map3d::relationships::tests as relationships_fixture;
    use crate::observer_ui::ObserverUiState;
    use crate::production::{PrimaryView, ProductionNavigation};
    use std::collections::BTreeSet;

    fn mixed_county_scene() -> (App, ObservationContext) {
        use crate::observer_focus::{ObserverFocusPlugin, ObserverFocusPolicy};
        use bevy::input::InputPlugin;
        use bevy::window::PrimaryWindow;
        let (session, mut frame, anchors) = relationships_fixture::fixture();
        let production = frame
            .0
            .as_mut()
            .expect("frame")
            .production
            .as_mut()
            .expect("snapshot");
        let mut mixed = production.sites[0].clone();
        mixed.id = "cooperative".into();
        mixed.name = "Utility and shop".into();
        mixed.function = EconomicFunction::EnergyUtilities.source_key().into();
        mixed.roles.push(ProductionSiteRole::Retail);
        // A disclosed input from another Wayne group has no separate geographic endpoints.
        mixed.processes[0].inputs = production.sites[1].processes[0].inputs.clone();
        production.sites.push(mixed);
        let context = session.context();
        let mut app = App::new();
        crate::visual_assets::install_test_assets(&mut app);
        app.add_plugins((InputPlugin, ObserverFocusPlugin));
        app.world_mut().spawn((Window::default(), PrimaryWindow));
        app.world_mut()
            .resource_mut::<ObserverFocusPolicy>()
            .context = Some(context.clone());
        app.init_resource::<Assets<Mesh>>()
            .init_resource::<Assets<StandardMaterial>>()
            .init_resource::<NetworkScope>()
            .init_resource::<HoveredNode>()
            .init_resource::<Active>()
            .init_resource::<ProductionNavigation>()
            .insert_resource(SelectedCounty(Some(1)))
            .insert_resource(session)
            .insert_resource(frame)
            .insert_resource(anchors)
            .insert_resource(PrimaryView::Map)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .add_systems(Startup, super::super::setup_network)
            .add_systems(Update, super::super::rebuild_network);
        app.finish();
        app.cleanup();
        app.update();
        (app, context)
    }

    fn shortage_scene() -> (App, ObservationContext) {
        use babylon_persistence::national_economy;
        use babylon_persistence::qualification_audit::trade;
        use babylon_persistence::{
            CompletedHouseholdBalance, ProductionHouseholdAccount, ProductionHouseholdKind,
        };
        let (mut app, context) = mixed_county_scene();
        let world = app.world_mut();
        let mut frame = world.resource_mut::<crate::observer_ui::ObserverFrame>();
        let production = frame
            .0
            .as_mut()
            .expect("frame")
            .production
            .as_mut()
            .expect("snapshot");
        production.scenario_label = "national-world".into();
        let food = national_economy::commodity_good_id("food");
        let mut row = ProductionHouseholdAccount {
            kind: ProductionHouseholdKind::Ordinary,
            demand_principal_id: "c3".repeat(32),
            location: production.sites[0].location,
            retailer_site_id: production.sites[1].id.clone(),
            good_id: trade::hex(&food.as_bytes()),
            unit_id: "d4".repeat(32),
            good: "Captured food label".into(),
            unit: "person-period food parcel".into(),
            household_count: 3,
            person_count: 6,
            stock_on_hand: 0,
            required_per_period: 6,
            completed: Some(CompletedHouseholdBalance {
                period: context.tick,
                population_basis: None,
                opening_stock: 3,
                received: 0,
                support_granted: 1,
                support_dispatched: 0,
                required: 6,
                consumed: 4,
                unmet: 2,
                closing_stock: 0,
                desired: 9,
                requested: 9,
                admitted: 9,
                fulfilled: 0,
                expired: 9,
            }),
        };
        production.household_accounts.push(row.clone());
        row.good_id = "ff".repeat(32);
        production.household_accounts.push(row);
        app.update();
        (app, context)
    }

    #[test]
    fn selected_resident_food_shortage_opens_its_receipt_and_respects_the_observer_role() {
        let (mut app, context) = shortage_scene();
        let world = app.world_mut();
        let (marker, label) = world
            .query::<(Entity, &GeographicSymbol, &Selection)>()
            .iter(world)
            .find_map(|(e, s, t)| {
                (t.group.kind == MapSymbol::FoodShortage).then(|| (e, s.label.clone()))
            })
            .expect("a deficit at the household residence");
        assert!(label.contains("2 of 6") && label.contains("P3"), "{label}");
        world.trigger(ObserverKeyboardActivate {
            entity: marker,
            context: Some(context.clone()),
        });
        app.update();
        let world = app.world_mut();
        let text = world
            .query::<&Text>()
            .iter(world)
            .map(|t| t.0.as_str())
            .collect::<Vec<_>>()
            .join("\n");
        assert!(
            text.contains("4 consumed")
                && text.contains("0 purchased")
                && text.contains("1 received"),
            "{text}"
        );
        assert!(
            text.contains("c3c3c3c3") && text.contains("Open household receipt"),
            "{text}"
        );
        assert!(
            text.contains("Trace food retailer · b county cohort"),
            "{text}"
        );
        world
            .resource_mut::<ObserverSession>()
            .set_perspective(Perspective::PlayerKnowledge);
        app.update();
        let world = app.world_mut();
        assert!(!world
            .query::<&GeographicSymbol>()
            .iter(world)
            .any(|s| s.symbol == MapSymbol::FoodShortage));
    }

    fn counterpart_food_scene() -> (App, Entity) {
        use crate::observer_ui::{ObserverFrame, ObserverViewport};
        let (mut app, _) = shortage_scene();
        app.insert_resource(ObserverViewport(Some(Rect::new(15.0, 100.0, 780.0, 620.0))))
            .add_systems(
                Update,
                super::super::place_legend.after(super::super::rebuild_network),
            );
        let world = app.world_mut();
        {
            let mut frame = world.resource_mut::<ObserverFrame>();
            let snapshot = frame
                .0
                .as_mut()
                .expect("frame")
                .production
                .as_mut()
                .expect("national snapshot");
            let mut row = snapshot.household_accounts[0].clone();
            row.demand_principal_id = "b2".repeat(32);
            row.location = snapshot.sites[1].location;
            row.household_count = 5;
            snapshot.household_accounts.push(row);
        }
        app.update();
        let world = app.world_mut();
        let marks: BTreeMap<_, _> = world
            .query::<(Entity, &GeographicSymbol, &Selection)>()
            .iter(world)
            .filter(|(_, m, _)| m.symbol == MapSymbol::FoodShortage)
            .map(|(e, _, t)| (t.group.county.clone(), e))
            .collect();
        assert_eq!(marks.len(), 2, "one marker per represented residence");
        let entity = marks["26099"];
        (app, entity)
    }

    #[test]
    fn a_direct_counterpart_shortage_marker_opens_that_countys_resident_receipt() {
        use bevy::camera::NormalizedRenderTarget;
        use bevy::picking::backend::HitData;
        use bevy::picking::pointer::{Location, PointerId};
        use std::time::Duration;
        let (mut app, entity) = counterpart_food_scene();
        let world = app.world_mut();
        world.trigger(PointerClick {
            entity,
            pointer: Pointer::new(
                PointerId::Mouse,
                Location {
                    target: NormalizedRenderTarget::None {
                        width: 0,
                        height: 0,
                    },
                    position: Vec2::ZERO,
                },
            ),
            button: PointerButton::Primary,
            hit: HitData::new(Entity::PLACEHOLDER, 1.0, Some(Vec3::ZERO), Some(Vec3::Y)),
            duration: Duration::ZERO,
            count: 1,
        });
        app.update();
        let world = app.world_mut();
        assert_eq!(world.resource::<SelectedCounty>().0, Some(2));
        let copy = world
            .query::<&Text>()
            .iter(world)
            .map(|t| t.0.as_str())
            .collect::<Vec<_>>()
            .join("\n");
        assert!(
            copy.contains("Macomb County, MI · household food")
                && copy.contains("5 households")
                && copy.contains("b2b2b2b2"),
            "{copy}"
        );
        assert!(!copy.contains("c3c3c3c3"), "{copy}");
    }

    #[test]
    fn enter_on_a_counterpart_warning_focuses_its_expanded_food_reading() {
        use crate::production::tests as production_tests;
        use bevy::window::PrimaryWindow;
        let (mut app, entity) = counterpart_food_scene();
        let world = app.world_mut();
        // This headless fixture supplies visibility in place of map-camera projection.
        *world.get_mut::<Visibility>(entity).expect("map triangle") = Visibility::Visible;
        let window = world
            .query_filtered::<Entity, With<PrimaryWindow>>()
            .single(world)
            .expect("window");
        world
            .resource_mut::<InputFocus>()
            .set(entity, FocusCause::Navigated);
        production_tests::readings_key(&mut app, window, KeyCode::Enter);
        let world = app.world_mut();
        assert_eq!(world.resource::<SelectedCounty>().0, Some(2));
        let focused = world
            .resource::<InputFocus>()
            .get()
            .expect("the expanded reading owns keyboard input");
        let control = world
            .get::<Selection>(focused)
            .expect("focus followed the resident county's legend control");
        assert_eq!(control.group.county, "26099");
        assert_eq!(control.scope, Some(2));
        assert!(
            world.get::<GeographicSymbol>(focused).is_none(),
            "the next Tab now reaches the receipt in the legend"
        );
    }

    #[test]
    fn shortage_legend_keeps_unanchored_residence_and_distinguishes_zero_from_missing_reports() {
        use crate::atlas::CountyAtlas;
        use crate::observer_map3d::relationships::CountyAnchors;
        use crate::observer_ui::ObserverFrame;
        let (mut app, context) = shortage_scene();
        let atlas = CountyAtlas::parse(include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/map/county_atlas.bin"
        )))
        .expect("bundled county identities");
        let wayne = atlas.index_of_fips("26163").expect("Wayne");
        let world = app.world_mut();
        world.insert_resource(atlas);
        world.insert_resource(CountyAnchors::default());
        world.insert_resource(SelectedCounty(Some(wayne)));
        app.update();
        let world = app.world_mut();
        assert!(!world
            .query::<&GeographicSymbol>()
            .iter(world)
            .any(|m| m.symbol == MapSymbol::FoodShortage));
        let legend = world
            .query::<(Entity, &Selection, &ObserverFocusTarget)>()
            .iter(world)
            .find(|(_, t, f)| t.group.kind == MapSymbol::FoodShortage && f.available)
            .expect("keyboard fallback without a map coordinate")
            .0;
        world.trigger(ObserverKeyboardActivate {
            entity: legend,
            context: Some(context),
        });
        app.update();
        let world = app.world_mut();
        assert!(world
            .query::<&Text>()
            .iter(world)
            .any(|t| t.0.contains("4 consumed · 2 unmet")));
        {
            let mut frame = world.resource_mut::<ObserverFrame>();
            let rows = &mut frame
                .0
                .as_mut()
                .expect("authenticated frame")
                .production
                .as_mut()
                .expect("disclosed production")
                .household_accounts;
            let done = rows[0].completed.as_mut().expect("P3 food receipt");
            done.opening_stock = 5;
            done.consumed = 6;
            done.unmet = 0;
        }
        app.update();
        let world = app.world_mut();
        assert!(world
            .query::<&Text>()
            .iter(world)
            .any(|t| t.0.contains("no unmet food need recorded")));
        {
            let mut frame = world.resource_mut::<ObserverFrame>();
            frame
                .0
                .as_mut()
                .expect("authenticated frame")
                .production
                .as_mut()
                .expect("disclosed production")
                .household_accounts[0]
                .completed = None;
        }
        app.update();
        let world = app.world_mut();
        assert!(world
            .query::<&Text>()
            .iter(world)
            .any(|t| t.0.contains("no household food reading")));
    }

    #[test]
    fn county_symbols_open_disclosed_sites_and_leave_the_organizer_map() {
        let (mut app, context) = mixed_county_scene();
        for lens in [
            MapLens::Relationships,
            MapLens::Qcew(EconomyMetric::Employment),
        ] {
            app.world_mut().resource_mut::<ObserverUiState>().lens = lens;
            app.update();
            let world = app.world_mut();
            let anchors: BTreeMap<_, _> = world
                .query::<(&Selection, &GeographicSymbol)>()
                .iter(world)
                .map(|(selection, marker)| (selection.group.county.clone(), marker.anchor))
                .collect();
            let mesh = world
                .query_filtered::<&Mesh3d, (With<EconomyEntity>, Without<EconomyNode>)>()
                .single(world)
                .expect("one geographic arrow batch");
            let mesh = world
                .resource::<Assets<Mesh>>()
                .get(&mesh.0)
                .expect("render mesh");
            let vertices = mesh
                .attribute(Mesh::ATTRIBUTE_POSITION)
                .expect("arrow vertices")
                .as_float3()
                .expect("world coordinates");
            assert_eq!(
                vertices.len(),
                24,
                "one intercounty arrow, with no invented distance between Wayne sites"
            );
            let endpoint =
                |a: usize, b: usize| Vec3::from(vertices[a]).midpoint(Vec3::from(vertices[b]));
            assert!(endpoint(0, 1).abs_diff_eq(anchors["26163"], 0.0001));
            assert!(endpoint(8, 11).abs_diff_eq(anchors["26099"], 0.0001));
        }

        let world = app.world_mut();
        let mut buttons = world.query::<(Entity, &Selection, Has<GeographicSymbol>)>();
        let mut markers = BTreeSet::new();
        let mut shop_button = None;
        for (entity, selection, map) in buttons
            .iter(world)
            .filter(|(_, s, _)| s.group.county == "26163")
        {
            if map {
                markers.insert(selection.group.kind);
            } else if selection.group.kind == MapSymbol::Shop {
                shop_button = Some(entity);
            }
        }
        assert_eq!(
            markers,
            [MapSymbol::Producer, MapSymbol::Shop, MapSymbol::Utility].into()
        );
        world.trigger(ObserverKeyboardActivate {
            entity: shop_button.expect("shop legend choice"),
            context: Some(context),
        });
        app.update();
        let world = app.world_mut();
        assert!(world
            .query::<&Text>()
            .iter(world)
            .any(|t| t.0 == "Utility and shop · Energy/utilities"));
        world
            .resource_mut::<ObserverSession>()
            .set_perspective(Perspective::PlayerKnowledge);
        app.update();
        let world = app.world_mut();
        assert!(world
            .query::<&GeographicSymbol>()
            .iter(world)
            .next()
            .is_none());
        assert!(!world
            .query::<&Text>()
            .iter(world)
            .any(|t| t.0 == "Utility and shop · Energy/utilities"));
    }
}
