//! Directed freight diagrams share peer identities with the geographic map and accessible list.
use super::super::relationships::{self, CountyAnchors};
use super::super::MAP_LAYER;
use super::freight::{Command, Freight, PageKey, Point};
use super::freight_rail;
use super::geometry::Ribbon;
use super::rail;
use super::state::{self, Action, MoneyView, Observation, Scope, Target};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_layout::ObserverRegion;
use crate::observer_map3d::symbols::GeographicSymbol;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::production::PrimaryView;
use crate::visual_assets::{MapSymbol, VisualAssets};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_persistence::freight_access::{Access, AccessDirection, AccessRow};
use bevy::camera::visibility::RenderLayers;
use bevy::prelude::*;

fn county_position(location: EconomicLocation, anchors: &CountyAnchors) -> Option<Vec3> {
    let EconomicLocation::County(county) = location else {
        return None;
    };
    anchors.county_position(county.geoid().as_str())
}

pub(super) fn frame(freight: &Freight, anchors: &CountyAnchors) -> Option<(Vec3, Vec3)> {
    let origin = freight.origin?;
    let home = anchors.county_position(origin.as_str())?;
    let mut limits = (home, home);
    let mut include = |point: Vec3| {
        limits = (limits.0.min(point), limits.1.max(point));
    };
    if let Some(Point::Airport(id)) = &freight.point {
        let p = freight.airports.iter().find(|p| &p.id == id)?;
        include(anchors.facility_position(origin.as_str(), &p.longitude, &p.latitude)?);
    } else if let Some(peer) = freight.selected {
        if let Some(endpoint) = county_position(peer, anchors) {
            include(endpoint);
        }
    } else {
        for row in freight.visible() {
            if let Some(endpoint) = county_position(row.peer, anchors) {
                include(endpoint);
            }
        }
    }
    Some(limits)
}

/// All admitted atlas endpoints remain pickable. Full-size artwork follows the active list page.
pub(super) fn geography(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    view: &MoneyView,
    scope: &Scope,
    anchors: &CountyAnchors,
    colors: &[Handle<StandardMaterial>; 4],
    visual: &VisualAssets,
) {
    let freight = &view.freight;
    let Some(origin) = freight.origin else { return };
    let Some(home) = anchors.county_position(origin.as_str()) else {
        return;
    };
    let target = |action| Target {
        scope: scope.clone(),
        offset: view.offset,
        action: Action::Freight(action),
    };
    let make_marker = |commands: &mut Commands, anchor, symbol, label, priority, active, action| {
        GeographicSymbol {
            anchor,
            symbol,
            label,
            priority,
            view: PrimaryView::Map,
            surface: SurfaceId::ObserverProduction,
        }
        .spawn(commands, visual, active)
        .insert((Ribbon, target(action)))
        .observe(state::pointer);
    };
    make_marker(
        commands,
        home,
        MapSymbol::Origin,
        format!("Comparison origin · county {origin}"),
        0,
        freight.point == Some(Point::Origin),
        Command::Point(origin, Point::Origin),
    );
    for point in &freight.airports {
        if let Some(anchor) =
            anchors.facility_position(origin.as_str(), &point.longitude, &point.latitude)
        {
            let selected = Point::Airport(point.id.clone());
            let active = freight.point.as_ref() == Some(&selected);
            make_marker(
                commands,
                anchor,
                MapSymbol::Airport,
                format!("FAA airport · {}", point.name),
                if active { 0 } else { 2 },
                active,
                Command::Point(origin, selected),
            );
        }
    }
    for (index, row) in freight.all_rows().iter().enumerate() {
        let Some(peer) = county_position(row.peer, anchors) else {
            continue;
        };
        let selected = freight.selected == Some(row.peer);
        let on_page = (freight.offset..freight.offset + super::freight::PAGE).contains(&index);
        let captured = !row.corridors.is_empty();
        if on_page || selected {
            make_marker(
                commands,
                peer,
                MapSymbol::Terminal,
                format!("Freight endpoint · {}", row.peer),
                if selected { 0 } else { 3 },
                selected,
                freight.selection(row.peer),
            );
        } else {
            // Compact diamond for the overview. Clicking it brings its full icon and list page into view.
            commands
                .spawn((
                    Mesh3d(meshes.add(Cuboid::new(4.0, 1.5, 4.0))),
                    MeshMaterial3d(colors[if captured { 0 } else { 2 }].clone()),
                    Transform::from_translation(peer)
                        .with_rotation(Quat::from_rotation_y(std::f32::consts::FRAC_PI_4)),
                    RenderLayers::layer(MAP_LAYER),
                    Ribbon,
                    target(freight.selection(row.peer)),
                    DeclaredSurface::new(SurfaceId::ObserverProduction),
                ))
                .observe(state::pointer);
        }
        if let Some(mesh) = access_ribbon(freight, row, home, peer, on_page) {
            commands
                .spawn((
                    Mesh3d(meshes.add(mesh)),
                    MeshMaterial3d(colors[usize::from(!captured)].clone()),
                    Transform::default(),
                    RenderLayers::layer(MAP_LAYER),
                    Ribbon,
                    target(freight.selection(row.peer)),
                    DeclaredSurface::new(SurfaceId::ObserverProduction),
                ))
                .observe(state::pointer);
        }
    }
}

fn access_ribbon(
    freight: &Freight,
    row: &AccessRow,
    home: Vec3,
    peer: Vec3,
    on_page: bool,
) -> Option<Mesh> {
    let captured = !row.corridors.is_empty();
    if peer == home || !(captured || (on_page && matches!(row.access, Access::Reachable { .. }))) {
        return None;
    }
    let (from, to) = if freight.direction == AccessDirection::Outbound {
        (home, peer)
    } else {
        (peer, home)
    };
    let width = if freight.selected == Some(row.peer) {
        3.5
    } else if captured {
        2.0
    } else {
        1.1
    };
    relationships::freight_ribbon(from, to, width, !captured)
}

type CanvasKey = (Scope, PageKey);

fn network_row(
    panel: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    row: &AccessRow,
    left: &str,
    right: &str,
) {
    let linked = matches!(row.access, Access::Reachable { .. }) || !row.corridors.is_empty();
    let color = if !row.corridors.is_empty() {
        theme::YELLOW
    } else if linked {
        theme::BLUE
    } else {
        theme::GRAY
    };
    panel
        .spawn(Node {
            width: percent(100),
            align_items: AlignItems::Center,
            ..default()
        })
        .with_children(|line| {
            line.spawn(Node {
                width: percent(33),
                min_width: px(0),
                ..default()
            })
            .with_child(rail::label(
                left,
                15.0,
                theme::PAPER,
                ObserverFontRole::Body,
            ));
            line.spawn(Node {
                width: percent(12),
                height: px(2),
                ..default()
            })
            .insert(BackgroundColor(if linked { color } else { theme::INK }));
            line.spawn(rail::label(
                if linked { "▶" } else { "·" },
                16.0,
                color,
                ObserverFontRole::Body,
            ));
            line.spawn(Node {
                width: percent(49),
                min_width: px(0),
                flex_direction: FlexDirection::Column,
                ..default()
            })
            .with_children(|end| {
                rail::control(
                    end,
                    view,
                    scope,
                    Action::Freight(view.freight.selection(row.peer)),
                    format!("{left} → {right}\n{}", freight_rail::reading(row)),
                );
            });
        });
}

pub(super) fn paint(
    mut commands: Commands,
    view: Res<MoneyView>,
    obs: Observation,
    mut current: Local<Option<(CanvasKey, Entity)>>,
) {
    if !view.is_changed()
        && !obs.session.is_changed()
        && !obs.ui.is_changed()
        && !obs.primary.is_changed()
    {
        return;
    }
    let key = view
        .scope
        .as_ref()
        .filter(|_| obs.interactive() && view.shows_sankey())
        .and_then(|s| view.freight.page_key().map(|p| (s.clone(), p)));
    if current.as_ref().map(|(k, _)| k) == key.as_ref() {
        return;
    }
    if let Some((_, old)) = current.take() {
        commands.entity(old).despawn();
    }
    let Some(key) = key else {
        return;
    };
    let scope = &key.0;
    let freight = &view.freight;
    let outbound = freight.direction == AccessDirection::Outbound;
    let name = freight_rail::origin_name(freight, &obs.atlas);
    let mut root = commands.spawn((
        ObserverRegion::World,
        Node {
            position_type: PositionType::Absolute,
            flex_direction: FlexDirection::Column,
            padding: UiRect::all(px(14)),
            row_gap: px(8),
            overflow: Overflow::scroll_y(),
            ..default()
        },
        BackgroundColor(theme::INK),
        ZIndex(5),
        DeclaredSurface::new(SurfaceId::ObserverProduction),
    ));
    root.with_children(|panel| {
        panel.spawn(rail::label(
            format!("Terminal network · {name}"),
            20.0,
            theme::PAPER,
            ObserverFontRole::Display,
        ));
        panel.spawn(rail::label(
            if outbound {
                "Origin → destinations"
            } else {
                "Origins → destination"
            },
            16.0,
            theme::GRAY,
            ObserverFontRole::Body,
        ));
        for row in freight.visible() {
            let peer = freight_rail::peer_name(row, &obs.atlas);
            let (left, right) = if outbound {
                (name.as_str(), peer.as_str())
            } else {
                (peer.as_str(), name.as_str())
            };
            network_row(panel, &view, scope, row, left, right);
        }
    });
    *current = Some((key, root.id()));
}

#[cfg(test)]
mod tests {
    use super::super::{geometry, tests};
    use super::*;
    use crate::atlas::CountyAtlas;
    use crate::observer_ui::ObserverFrame;
    use crate::visual_assets::VisualAssetsPlugin;
    use babylon_persistence::freight_access::Reference;
    use bevy::asset::AssetPlugin;
    use bevy::image::ImagePlugin;

    fn assert_county_self_markers(world: &mut World, origin: Vec3) {
        let symbols: Vec<_> = world
            .query::<(&GeographicSymbol, &Target)>()
            .iter(world)
            .map(|(marker, _)| (marker.symbol, marker.anchor))
            .collect();
        assert!(symbols.contains(&(MapSymbol::Origin, origin)));
        assert!(symbols.contains(&(MapSymbol::Terminal, origin)));
        assert!(symbols
            .iter()
            .all(|(symbol, _)| *symbol != MapSymbol::Airport));
    }

    #[test]
    fn freight_map_retains_its_self_endpoint_and_places_faa_art_at_the_observed_point() {
        let (mut app, _, mut scope, _) = tests::interaction_fixture();
        let wayne = "26163".parse().expect("Wayne GEOID");
        let suffolk = "25025".parse().expect("Suffolk MA GEOID");
        let location = EconomicLocation::domestic_county(wayne).expect("domestic county");
        let reference = Reference::load(None).expect("pinned regional reference");
        assert_eq!(reference.airport_points(wayne), []);
        let airport = reference
            .airport_points(suffolk)
            .iter()
            .find(|airport| airport.id == "airport:BOS")
            .expect("pinned Logan point")
            .clone();
        let atlas = app.world().resource::<CountyAtlas>();
        let county = atlas
            .index_of_fips(wayne.as_str())
            .expect("Wayne in county atlas");
        let coastal_county = atlas
            .index_of_fips(suffolk.as_str())
            .expect("Suffolk in county atlas");
        let anchors = CountyAnchors::from_atlas(
            atlas,
            &[county, coastal_county],
            atlas.county(county).expect("county").centroid,
        );
        let origin = anchors
            .county_position(wayne.as_str())
            .expect("county anchor");
        let airport_anchor = anchors
            .facility_position(suffolk.as_str(), &airport.longitude, &airport.latitude)
            .expect("continental projection");
        assert!(
            airport_anchor.distance(
                anchors
                    .county_position(suffolk.as_str())
                    .expect("Suffolk anchor")
            ) > 0.1
        );
        app.add_plugins((
            MinimalPlugins,
            AssetPlugin::default(),
            ImagePlugin::default(),
            bevy::text::TextPlugin,
            bevy::render::texture::TexturePlugin,
            VisualAssetsPlugin,
        ))
        .insert_resource(anchors)
        .init_resource::<Assets<Mesh>>()
        .init_resource::<Assets<StandardMaterial>>()
        .add_systems(Update, geometry::render);
        let mut frame = app
            .world()
            .resource::<ObserverFrame>()
            .0
            .clone()
            .expect("fixture frame");
        frame.production = Some(crate::production::tests::snapshot());
        let self_row = reference
            .connections(&frame, wayne, AccessDirection::Outbound)
            .expect("regional access")
            .into_iter()
            .find(|row| row.peer == location)
            .expect("county self comparison");
        let mut view = app.world_mut().resource_mut::<MoneyView>();
        assert!(view.freight.apply(&Command::Open, &scope));
        view.freight.rows = Some(Ok(vec![self_row]));
        app.finish();
        app.cleanup();
        app.update();
        let world = app.world_mut();
        assert_county_self_markers(world, origin);
        scope.county = suffolk.to_string();
        let mut view = world.resource_mut::<MoneyView>();
        view.scope = Some(scope.clone());
        assert!(view.freight.apply(&Command::Origin(suffolk), &scope));
        view.freight.airports = reference.airport_points(suffolk).to_vec();
        view.freight.rows = Some(reference.connections(&frame, suffolk, AccessDirection::Outbound));
        app.update();
        let world = app.world_mut();
        let action = world
            .query::<(&GeographicSymbol, &Target)>()
            .iter(world)
            .find_map(|(marker, target)| {
                (marker.symbol == MapSymbol::Airport && marker.anchor == airport_anchor)
                    .then(|| target.action.clone())
            })
            .expect("FAA point carries an action");
        let Action::Freight(command) = action else {
            panic!("expected freight selection")
        };
        let mut view = world.resource_mut::<MoneyView>();
        assert!(view.freight.apply(&command, &scope));
        assert!(matches!(&view.freight.point, Some(Point::Airport(id)) if id==&airport.id));
        assert!(!view.freight.apply(
            &Command::Point(wayne, Point::Airport("absent".into())),
            &scope
        ));
    }
}
