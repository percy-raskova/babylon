//! On-demand, full-observer disclosure of the source observations behind a function.
use super::state::MoneyView;
use crate::observer_io::ObservationCache;
use crate::observer_ui;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::FlowGroup;
use babylon_persistence::national_cohorts::IndustrySourceComposition;
use babylon_persistence::observer_reader::{ObserverEconomyError, ObserverEconomyReader};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};

type Reading = Result<Option<IndustrySourceComposition>, ObserverEconomyError>;

#[derive(Default)]
pub(super) struct Sources {
    pub(super) expanded: bool,
    result: Option<Reading>,
}

pub(super) fn selected(view: &MoneyView) -> Option<EconomicFunction> {
    if view.scope.as_ref()?.group != FlowGroup::Industry {
        return None;
    }
    EconomicFunction::from_source_key(view.selected_row()?.key.peer.as_deref()?)
}

impl Sources {
    pub(super) fn describe(&self) -> String {
        use std::fmt::Write as _;
        match &self.result {
            None => "Reading the captured industry sources…".into(),
            Some(Ok(None)) => "This campaign has no national QCEW member table.".into(),
            Some(Err(error)) => {
                format!("Industry sources unavailable ({error}). Close and reopen to retry.")
            }
            Some(Ok(Some(data))) => {
                let mut text = format!(
                    "{} · BLS QCEW 2024\nCampaign-wide source composition across admitted counties and ownership groups. These annual-average workplace jobs describe the source of the modeled industry. Period payments and labor hours are measured separately.",
                    data.function.label()
                );
                for row in &data.rows {
                    let jobs = if row.published_cells == 0 {
                        "Jobs undisclosed".into()
                    } else {
                        format!("{} reported jobs", observer_ui::grouped(row.known_jobs))
                    };
                    write!(
                        text,
                        "\nNAICS {} · {jobs} · {} reporting cells, {} suppressed",
                        row.naics, row.published_cells, row.suppressed_cells
                    )
                    .expect("String write");
                }
                text
            }
        }
    }

    pub(super) fn toggle(&mut self) {
        self.expanded = !self.expanded;
        if self.expanded && matches!(&self.result, Some(Err(_))) {
            self.result = None;
        }
    }
}

struct Pending {
    campaign: CampaignId,
    foundation: String,
    function: EconomicFunction,
    read: Task<Reading>,
}

#[derive(Resource, Default)]
pub(super) struct Worker(Option<Pending>);

pub(super) fn update(
    mut view: ResMut<MoneyView>,
    mut worker: ResMut<Worker>,
    cache: Option<Res<ObservationCache>>,
) {
    let function = selected(&view);
    if let Some(pending) = &mut worker.0 {
        let Some(result) =
            tasks::block_on(tasks::futures_lite::future::poll_once(&mut pending.read))
        else {
            return;
        };
        if function == Some(pending.function)
            && view.scope.as_ref().is_some_and(|scope| {
                scope.context.campaign == pending.campaign && scope.foundation == pending.foundation
            })
        {
            view.industry.result = Some(result);
        }
        worker.0 = None;
    }
    let (Some(function), Some(scope)) = (function, &view.scope) else {
        return;
    };
    if !view.industry.expanded || view.industry.result.is_some() || view.freight.enabled {
        return;
    }
    let campaign = scope.context.campaign;
    let foundation = scope.foundation.clone();
    let requested = foundation.clone();
    let reader = cache.as_deref().and_then(ObservationCache::full_reader);
    worker.0 = Some(Pending {
        campaign,
        foundation,
        function,
        read: IoTaskPool::get().spawn(async move {
            let reader = reader.map_or_else(ObserverEconomyReader::from_observer_env, Ok)?;
            reader.industry_source_composition(campaign, &requested, function)
        }),
    });
}
