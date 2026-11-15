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
    pub(super) offset: usize,
    pub(super) rows: Option<Result<Vec<AccessRow>, AccessError>>,
    pub(super) source: String,
    pub(super) airports: Vec<AirportPoint>,
}

#[derive(Clone, PartialEq, Eq)]
pub(super) enum Command {
    Open,
    Leave,
    Origin(CountyGeoid),
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
                self.selected = Some(*peer);
                self.offset = index / PAGE * PAGE;
            }
            Command::Direction(direction) if self.enabled && self.direction != *direction => {
                self.direction = *direction;
                self.rows = None;
                self.offset = 0;
            }
            Command::Origin(county)
                if self.enabled
                    && (county.as_str() == scope.county || county.as_str() == WAYNE)
                    && self.origin != Some(*county) =>
            {
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
                view.freight.source = format!(
                    "Michigan regional reference · {} · {} · © OpenStreetMap contributors. {}",
                    reference.source_date,
                    reference.profile,
                    if let Some(error) = reference.supplement_error {
                        format!("Supplemental path matrix refused ({error:?}). Captured economic corridors remain available.")
                    } else if frame
                        .production
                        .as_ref()
                        .is_some_and(|p| !reference.graph_matches(p))
                    {
                        "Different campaign road graph. Displaying its captured economic corridors; regional reachability is unverified.".to_owned()
                    } else if reference.qualified() {
                        "Shortest permitted truck paths. Designed bands exclude terminal attachment.".to_owned()
                    } else {
                        "The complete path matrix is absent. Captured corridors establish only the listed economic connections.".to_owned()
                    }
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
