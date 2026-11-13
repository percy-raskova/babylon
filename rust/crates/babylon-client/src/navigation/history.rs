//! Bounded local visit history; runtime projections and authority never enter the stack.

use babylon_persistence::identity::CampaignId;
use bevy::prelude::*;

use crate::map_economy_lens::MapLens;
use crate::observer::{ObserverSession, Perspective};
use crate::observer_map3d::MapOrbit;
use crate::observer_ui::{NetworkSector, ObserverDisclosure, RoadLayer};
use crate::organizer::navigation::OrganizerRoute;
use crate::production::shared_navigation::ProductionRoute;
use crate::production::PrimaryView;
use crate::ui::dossier_navigation::ArchiveRoute;

use super::position::SavedPosition;

const HISTORY_LIMIT: usize = 128;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ViewedPeriod {
    Live,
    Historical(u64),
}

impl ViewedPeriod {
    pub(crate) fn for_session(session: &ObserverSession) -> Self {
        if session.viewed_tick == session.durable_tick {
            Self::Live
        } else {
            Self::Historical(session.viewed_tick)
        }
    }

    pub(crate) fn resolve(self, session: &ObserverSession) -> Option<u64> {
        match self {
            Self::Live => Some(session.durable_tick),
            Self::Historical(period) => (period <= session.durable_tick).then_some(period),
        }
    }
}

/// Only the visible routes participate in visit identity; panning and lens changes do not.
#[derive(Clone, PartialEq, Eq)]
pub(crate) struct Route {
    pub(crate) period: ViewedPeriod,
    pub(crate) primary: PrimaryView,
    pub(crate) county: Option<String>,
    pub(crate) organizer: Option<OrganizerRoute>,
    pub(crate) production: Option<ProductionRoute>,
    pub(crate) archive: Option<ArchiveRoute>,
    pub(crate) archive_open: bool,
    pub(crate) disclosure: Option<ObserverDisclosure>,
    pub(crate) history_open: bool,
    pub(crate) evidence_open: bool,
    pub(crate) economic_details_open: bool,
}

#[derive(Clone)]
pub(crate) struct Visit {
    pub(crate) route: Route,
    pub(crate) lens: MapLens,
    pub(crate) roads: RoadLayer,
    pub(crate) sector: NetworkSector,
    pub(crate) orbit: Option<MapOrbit>,
    pub(crate) position: SavedPosition,
}

#[derive(Clone, Copy, PartialEq, Eq)]
struct NavigationScope {
    campaign: CampaignId,
    perspective: Perspective,
    epoch: Option<u64>,
}

/// Accepted handler markers authorize recording; a changed resource alone never does.
#[derive(Resource, Default)]
pub(crate) struct NavigationHistory {
    scope: Option<NavigationScope>,
    pub(crate) origin: Option<Visit>,
    back: Vec<Visit>,
    accepted_route: bool,
    suppress_recording: bool,
    detail_closed: bool,
    pub(crate) restore: Option<Visit>,
}

impl NavigationHistory {
    pub(crate) fn reconcile(&mut self, session: &ObserverSession) -> bool {
        let scope = NavigationScope {
            campaign: session.campaign,
            perspective: session.perspective,
            epoch: session.lifecycle_epoch(),
        };
        if self.scope == Some(scope) && session.organizer_enabled {
            return false;
        }
        *self = Self {
            scope: Some(scope),
            ..Self::default()
        };
        true
    }

    pub(crate) fn capture_origin(&mut self, origin: Visit) {
        self.origin = Some(origin);
        self.accepted_route = false;
        self.suppress_recording = false;
        self.detail_closed = false;
    }

    /// Called only after an intentional semantic route passes the owner's admission.
    pub(crate) fn accepted(&mut self) {
        self.accepted_route = true;
        self.restore = None;
    }

    pub(crate) fn has_accepted_route(&self) -> bool {
        self.accepted_route
    }

    pub(crate) fn settle(&mut self, destination: &Visit) {
        if self.detail_closed {
            if self
                .back
                .last()
                .is_some_and(|visit| visit.route == destination.route)
            {
                self.back.pop();
            }
            self.detail_closed = false;
        }
        if !self.accepted_route || self.suppress_recording {
            return;
        }
        let Some(origin) = self.origin.take() else {
            return;
        };
        if origin.route != destination.route {
            self.push(origin);
        }
        self.accepted_route = false;
    }

    pub(crate) fn can_go_back(&self) -> bool {
        !self.back.is_empty()
    }

    pub(crate) fn back(&mut self) -> Option<Visit> {
        self.suppress_recording = true;
        self.accepted_route = false;
        self.restore = None;
        self.back.pop()
    }

    pub(crate) fn closed_detail(&mut self) {
        self.suppress_recording = true;
        self.accepted_route = false;
        self.restore = None;
        self.detail_closed = true;
    }

    pub(crate) fn home_origin(&mut self) {
        if let Some(origin) = self.origin.clone() {
            self.push(origin);
        }
        self.suppress_recording = true;
        self.accepted_route = false;
        self.restore = None;
    }

    fn push(&mut self, visit: Visit) {
        if self
            .back
            .last()
            .is_some_and(|last| last.route == visit.route)
        {
            return;
        }
        if self.back.len() == HISTORY_LIMIT {
            self.back.remove(0);
        }
        self.back.push(visit);
    }
}
