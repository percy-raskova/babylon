//! Resolve the selected aggregate to locations of its actual settled or recorded endpoints.
use super::rail;
use super::state::{
    self, Connection, ConnectionKey, Diagram, Direction, MoneyView, Page, Quantity, Scope,
};
use crate::atlas::CountyAtlas;
use babylon_persistence::money_journal::{
    FlowDirection, FlowGroup, FlowPeer, FlowQuery, FlowRow, JournalError, LaborFlowRow,
};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};
use std::fmt::Write as _;

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

#[derive(Default)]
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
    pub(super) fn describe(&self, atlas: &CountyAtlas) -> String {
        let Some(result) = &self.result else {
            return "Reading the selected connection’s locations…".to_owned();
        };
        let g = match result {
            Ok(g) => g,
            Err(error) => return format!("Location detail unavailable ({error})."),
        };
        if g.total == 0 {
            return "No location movements in the selected periods.".into();
        }
        let end = (self.offset + 20).min(g.total);
        let mut text = format!("Locations {}–{end} of {}", self.offset + 1, g.total);
        for r in &g.rows {
            let _ = write!(
                text,
                "\n{} · {}",
                rail::location(r.key.peer.as_deref(), atlas),
                rail::reading(&r.quantity)
            );
        }
        if g.total > end - self.offset {
            let _ = write!(text, "\nOther locations · {}", rail::reading(&g.remainder));
        }
        text
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
    if scope.group == FlowGroup::Location
        || view.diagram != Diagram::Map
        || view.geography.result.is_some()
    {
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
