//! The map, network and reader share the same origin, direction and selected terminal.
use super::state::{MoneyView, Observation, Scope};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::freight_access::{
    AccessDirection, AccessError, AccessRow, AirportPoint, Reference,
};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};
use std::path::PathBuf;

pub(super) const PAGE: usize = 8;
const WAYNE: &str = "26163";

#[derive(Default)]
pub(super) struct Freight {
    pub(super) enabled: bool,
    pub(super) origin: Option<CountyGeoid>,
    pub(super) direction: AccessDirection,
    pub(super) selected: Option<EconomicLocation>,
    pub(super) point: Option<Point>,
    pub(super) offset: usize,
    pub(super) rows: Option<Result<Vec<AccessRow>, AccessError>>,
    pub(super) source: String,
    pub(super) airports: Vec<AirportPoint>,
}

#[derive(Clone, PartialEq, Eq)]
pub(super) enum Point {
    Origin,
    Airport(String),
}

#[derive(Clone, PartialEq, Eq)]
pub(super) enum Command {
    Open,
    Leave,
    Origin(CountyGeoid),
    Point(CountyGeoid, Point),
    Direction(AccessDirection),
    Select(Option<CountyGeoid>, AccessDirection, EconomicLocation),
    Page(usize),
}

pub(super) type PageKey = (
    Option<CountyGeoid>,
    AccessDirection,
    usize,
    Option<Result<usize, AccessError>>,
);

impl Freight {
    pub(super) fn next_frame(&self) -> Self {
        Self {
            enabled: self.enabled,
            origin: self.origin,
            direction: self.direction,
            selected: self.selected,
            offset: self.offset,
            ..default()
        }
    }
    pub(super) fn page_key(&self) -> Option<PageKey> {
        self.enabled.then(|| {
            (
                self.origin,
                self.direction,
                self.offset,
                self.rows
                    .as_ref()
                    .map(|r| r.as_ref().map(Vec::len).map_err(|e| *e)),
            )
        })
    }
    pub(super) fn selection(&self, peer: EconomicLocation) -> Command {
        Command::Select(self.origin, self.direction, peer)
    }
    pub(super) fn all_rows(&self) -> &[AccessRow] {
        self.rows
            .as_ref()
            .and_then(|r| r.as_ref().ok())
            .map(Vec::as_slice)
            .unwrap_or_default()
    }
    pub(super) fn visible(&self) -> &[AccessRow] {
        self.rows
            .as_ref()
            .and_then(|r| r.as_ref().ok())
            .and_then(|rows| rows.get(self.offset..rows.len().min(self.offset + PAGE)))
            .unwrap_or_default()
    }
    pub(super) fn pressed(&self, command: &Command) -> Option<bool> {
        match command {
            Command::Select(origin, direction, location) => Some(
                self.origin == *origin
                    && self.direction == *direction
                    && self.selected == Some(*location),
            ),
            Command::Point(county, point) => {
                Some(self.origin == Some(*county) && self.point.as_ref() == Some(point))
            }
            Command::Direction(direction) => Some(self.direction == *direction),
            _ => None,
        }
    }
    pub(super) fn apply(&mut self, command: &Command, scope: &Scope) -> bool {
        match command {
            Command::Open if !self.enabled => {
                self.enabled = true;
                self.origin = WAYNE.parse().ok();
            }
            Command::Leave if self.enabled => {
                self.enabled = false;
            }
            Command::Select(origin, direction, peer)
                if self.enabled && self.origin == *origin && self.direction == *direction =>
            {
                let Some(index) = self.all_rows().iter().position(|r| r.peer == *peer) else {
                    return false;
                };
                self.point = None;
                self.selected = Some(*peer);
                self.offset = index / PAGE * PAGE;
            }
            Command::Point(county, point)
                if self.enabled
                    && self.origin == Some(*county)
                    && match point {
                        Point::Origin => true,
                        Point::Airport(id) => self.airports.iter().any(|p| &p.id == id),
                    } =>
            {
                self.selected = None;
                self.point = Some(point.clone());
            }
            Command::Direction(direction) if self.enabled && self.direction != *direction => {
                self.point = None;
                self.direction = *direction;
                self.rows = None;
                self.offset = 0;
            }
            Command::Origin(county)
                if self.enabled
                    && (county.as_str() == scope.county || county.as_str() == WAYNE)
                    && self.origin != Some(*county) =>
            {
                self.airports.clear();
                self.source.clear();
                self.point = None;
                self.origin = Some(*county);
                self.selected = None;
                self.rows = None;
                self.offset = 0;
            }
            Command::Page(offset)
                if self.enabled
                    && self.offset.abs_diff(*offset) == PAGE
                    && self
                        .rows
                        .as_ref()
                        .is_some_and(|r| r.as_ref().is_ok_and(|rows| *offset < rows.len())) =>
            {
                self.point = None;
                self.offset = *offset;
                self.selected = None;
            }
            _ => return false,
        }
        true
    }
}

#[derive(Resource, Default)]
pub(super) struct Source {
    task: Option<Task<Result<Reference, AccessError>>>,
    ready: Option<Result<Reference, AccessError>>,
}

pub(super) fn update(obs: Observation, mut view: ResMut<MoneyView>, mut source: ResMut<Source>) {
    if !obs.active() || !view.freight.enabled || view.freight.rows.is_some() {
        return;
    }
    let Some(origin) = view.freight.origin else {
        return;
    };
    let Some(frame) = obs.frame.for_session(&obs.session) else {
        return;
    };
    if let Some(ready) = &source.ready {
        let result = match ready {
            Ok(reference) => {
                let graph_note = match frame.production.as_ref() {
                    Some(p) if p.road_source.is_none() => {
                        "Campaign has no road source. Michigan roads are an independent regional comparison."
                    }
                    Some(p) if reference.graph_matches(p) => "Campaign and regional road graphs match.",
                    Some(_) => "Different campaign road graph. Regional paths and county attachments withheld.",
                    None => "",
                };
                let matrix_note = if let Some(error) = reference.supplement_error {
                    format!("Supplemental path matrix refused ({error:?}).")
                } else if reference.qualified() {
                    "Regional path lengths exclude both Designed county attachments.".to_owned()
                } else {
                    "Complete regional path matrix absent.".to_owned()
                };
                view.freight.source = format!(
                    "Michigan regional reference · {} · {} · © OpenStreetMap contributors. {graph_note} {matrix_note}",
                    reference.source_date,
                    reference.profile,
                );
                view.freight.airports = reference.airport_points(origin).to_vec();
                reference.connections(frame, origin, view.freight.direction)
            }
            Err(error) => Err(*error),
        };
        if let Ok(rows) = &result {
            if let Some(index) = view
                .freight
                .selected
                .and_then(|peer| rows.iter().position(|r| r.peer == peer))
            {
                view.freight.offset = index / PAGE * PAGE;
            } else {
                view.freight.selected = None;
                if view.freight.offset >= rows.len() {
                    view.freight.offset = 0;
                }
            }
        }
        view.freight.rows = Some(result);
    } else if let Some(task) = source.task.as_mut() {
        if let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(task)) {
            source.ready = Some(result);
            source.task = None;
        }
    } else {
        source.task = Some(IoTaskPool::get().spawn(async {
            let path = std::env::var_os("BABYLON_MICHIGAN_ROAD_MATRIX").map(PathBuf::from);
            Reference::load(path.as_deref())
        }));
    }
}

#[cfg(test)]
mod tests {
    use super::super::freight_rail::Detail;
    use super::super::state::{Action, Diagram, MoneyRail, Target};
    use super::super::{freight_plot, freight_rail, rail, tests};
    use super::{AccessDirection, Command, Point, Reference, Source};
    use crate::atlas::CountyAtlas;
    use crate::map::SelectedCounty;
    use crate::observer_focus::ObserverKeyboardActivate;
    use crate::observer_ui::ObserverFrame;
    use bevy::prelude::*;

    fn activate(app: &mut App, action: &Action) {
        let world = app.world_mut();
        let (entity, target) = world
            .query::<(Entity, &Target)>()
            .iter(world)
            .find(|(_, t)| &t.action == action)
            .expect("active freight control");
        world.trigger(ObserverKeyboardActivate {
            entity,
            context: Some(target.scope.context.clone()),
        });
        app.update();
    }

    fn assert_directed_attachments(world: &mut World, from: &str, to: &str) {
        let detail = world
            .query_filtered::<&Text, With<Detail>>()
            .single(world)
            .expect("selected freight detail");
        for (role, name) in [("From", from), ("To", to)] {
            let distance = if name == "Wayne" {
                "0.432419 km"
            } else {
                "0.39184 km"
            };
            let line = detail.0.lines().find(|line| line.starts_with(role));
            assert!(
                line.is_some_and(|l| l.contains(name) && l.contains(distance)),
                "{role} should identify {name} and its Designed attachment of {distance}: {detail:?}"
            );
        }
        assert!(
            detail.0.contains("Designed"),
            "attachment evidence class: {detail:?}"
        );
        assert!(
            detail.0.contains("Regional path unverified"),
            "missing matrix: {detail:?}"
        );
        assert!(
            world
                .query::<&Text>()
                .iter(world)
                .any(|t| t.0.contains("independent regional comparison")),
            "a campaign without a declared road source uses an independent comparison"
        );
    }

    #[test]
    fn freight_selection_names_directed_endpoints_and_keeps_designed_attachments_separate() {
        let (mut app, _, _, _) = tests::interaction_fixture();
        let mut snapshot = crate::production::tests::snapshot();
        let wayne = "26163".parse().expect("Wayne GEOID");
        let kent = "county:26081".parse().expect("Kent location");
        snapshot.sites[0].location = "county:26163".parse().expect("Wayne location");
        snapshot.sites[1].location = kent;
        app.world_mut()
            .resource_mut::<ObserverFrame>()
            .0
            .as_mut()
            .expect("fixture frame")
            .production = Some(snapshot);
        app.world_mut().spawn((MoneyRail, Node::default()));
        app.insert_resource(Source {
            task: None,
            ready: Some(Reference::load(None)),
        })
        .add_systems(
            Update,
            (
                super::update,
                rail::paint,
                freight_plot::paint,
                freight_rail::detail,
            )
                .chain(),
        );
        app.update();
        activate(&mut app, &Action::Freight(Command::Open));
        let outbound = AccessDirection::Outbound;
        activate(
            &mut app,
            &Action::Freight(Command::Select(Some(wayne), outbound, kent)),
        );
        for (diagram, direction, from, to) in [
            (Diagram::Map, outbound, "Wayne", "Kent"),
            (Diagram::Sankey, AccessDirection::Inbound, "Kent", "Wayne"),
        ] {
            activate(&mut app, &Action::Diagram(diagram));
            activate(&mut app, &Action::Freight(Command::Direction(direction)));
            assert_directed_attachments(app.world_mut(), from, to);
        }
        let suffolk: super::CountyGeoid = "25025".parse().expect("Suffolk County GEOID");
        let county = app
            .world()
            .resource::<CountyAtlas>()
            .index_of_fips("25025")
            .expect("Suffolk County in atlas");
        assert_eq!(
            app.world()
                .resource::<super::MoneyView>()
                .freight
                .airports
                .as_slice(),
            []
        );
        app.world_mut().resource_mut::<SelectedCounty>().0 = Some(county);
        app.world_mut()
            .resource_mut::<super::MoneyView>()
            .scope
            .as_mut()
            .expect("live map scope")
            .county = suffolk.to_string();
        app.update();
        activate(&mut app, &Action::Freight(Command::Origin(suffolk)));
        activate(
            &mut app,
            &Action::Freight(Command::Point(
                suffolk,
                Point::Airport("airport:BOS".into()),
            )),
        );
        let world = app.world_mut();
        let detail = world
            .query_filtered::<&Text, With<Detail>>()
            .single(world)
            .expect("Logan point reader");
        assert!(
            detail.contains("airport:BOS") && detail.contains("42.36294444, -71.00638888"),
            "actual admitted facility geometry: {detail:?}"
        );
    }
}
