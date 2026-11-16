//! One county-level button per disclosed function. The reader preserves each exact site identity.
use super::{
    EconomyEntity, NetworkLegend, NetworkNode, NetworkProjection, NetworkSector,
    ObservationContext, ObserverFontRole, RelationshipObservation,
};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_focus::{ObserverFocusTarget, ObserverKeyboardActivate};
use crate::observer_map3d::symbols::GeographicSymbol;
use crate::observer_theme as theme;
use crate::production::ProductionCommand;
use crate::visual_assets::{MapSymbol, VisualAssets};
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_persistence::production_observation::{ProductionSite, ProductionSiteRole};
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;
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

fn choose(
    entity: Entity,
    targets: &Query<&Selection>,
    obs: &RelationshipObservation,
    active: &mut Active,
) {
    let Ok(target) = targets.get(entity) else {
        return;
    };
    if !super::usable(&obs.ui, *obs.view)
        || !obs.session.accepts(&target.context)
        || target.scope != obs.selected.0
        || super::super::disclosed_snapshot(&obs.frame, &obs.session).is_none()
    {
        return;
    }
    active.0 = (active.0.as_ref() != Some(target)).then(|| target.clone());
}

fn pointer(
    event: On<PointerClick>,
    targets: Query<&Selection>,
    obs: RelationshipObservation,
    mut active: ResMut<Active>,
) {
    if event.button == PointerButton::Primary {
        choose(event.entity, &targets, &obs, &mut active);
    }
}
fn keyboard(
    event: On<ObserverKeyboardActivate>,
    targets: Query<&Selection>,
    obs: RelationshipObservation,
    mut active: ResMut<Active>,
) {
    if targets
        .get(event.entity)
        .is_ok_and(|t| Some(&t.context) == event.context.as_ref())
    {
        choose(event.entity, &targets, &obs, &mut active);
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
) {
    let groups = workplace_groups(projection);
    let current_county = obs.anchors.selected(obs.selected.0);
    let selection = |group: &Group| Selection {
        context: obs.session.context(),
        scope: obs.selected.0,
        group: group.clone(),
    };
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
