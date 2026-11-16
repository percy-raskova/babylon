//! Load a single authenticated journal reading off the UI thread.
use super::reading::{Reading, Scope};
use crate::cli;
use crate::company_investment::ProcessLabel;
use crate::observer::{ObserverSession, Perspective};
use crate::observer_ui::ObserverUiState;
use crate::production::{
    navigation, PrimaryView, ProductionNavigation, ProductionObservation, ProductionReadingSection,
};
use babylon_material_circuit::{ProcessId, SiteId};
use babylon_persistence::money_journal::JournalError;
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};

pub(in crate::production) fn authorized(state: &ObserverSession) -> bool {
    state.perspective == Perspective::FullObserver && !state.organizer_enabled
}

#[derive(Default, PartialEq, Eq)]
pub(super) enum Selection {
    #[default]
    Inactive,
    Opening,
    SiteUnavailable,
    FrameUnavailable,
    Period(Scope),
}
impl Selection {
    fn current(
        observation: &ProductionObservation,
        navigation: &ProductionNavigation,
        primary: PrimaryView,
        ui: &ObserverUiState,
    ) -> Self {
        if !matches!(
            navigation.reading_section,
            ProductionReadingSection::Accounts | ProductionReadingSection::Investment
        ) || !authorized(&observation.state)
        {
            return Self::Inactive;
        }
        let frame = observation.frame.for_session(&observation.state);
        let snapshot = frame.and_then(|frame| frame.production.as_ref());
        if !navigation::readings_panel_visible(primary, navigation, ui, snapshot) {
            return Self::Inactive;
        }
        let Some((frame, snapshot)) = frame.zip(snapshot) else {
            return Self::FrameUnavailable;
        };
        let Some(site) = navigation
            .selected_site
            .as_deref()
            .and_then(|id| snapshot.sites.iter().find(|site| site.id == id))
        else {
            return Self::SiteUnavailable;
        };
        let Some(site_id) = cli::identity_bytes(&site.id) else {
            return Self::SiteUnavailable;
        };
        if observation.state.viewed_tick == 0 {
            return Self::Opening;
        }
        let Some((foundation, tick_hash)) = cli::identity_bytes(&frame.foundation_digest).zip(
            frame
                .tick_content_hash
                .as_deref()
                .and_then(cli::identity_bytes),
        ) else {
            return Self::FrameUnavailable;
        };
        Self::Period(Scope {
            context: observation.state.context(),
            reading: if navigation.reading_section == ProductionReadingSection::Investment {
                Reading::Investment(
                    site.processes
                        .iter()
                        .filter_map(|p| {
                            Some(ProcessLabel {
                                id: ProcessId::from_bytes(cli::identity_bytes(&p.id)?),
                                name: p.name.clone(),
                                unit: p.output_unit.clone(),
                            })
                        })
                        .collect(),
                )
            } else {
                Reading::Accounts
            },
            site: SiteId::from_bytes(site_id),
            foundation,
            tick_hash,
        })
    }
}

#[derive(Default)]
enum Status {
    #[default]
    Waiting,
    Publishing,
    Finished(String),
}

#[derive(Resource, Default)]
pub(crate) struct AccountsView {
    selection: Selection,
    status: Status,
}

impl AccountsView {
    pub(in crate::production) fn text(&self) -> &str {
        match &self.selection {
            Selection::Inactive => "Choose an operating site in the full observer to read its accounts.",
            Selection::Opening => "Opening foundation. Financial statements and investment decisions start with the first completed period.",
            Selection::SiteUnavailable => "Invalid operating-site identity in the selected frame.",
            Selection::FrameUnavailable => "Missing committed period identity. Financial readings are unavailable.",
            Selection::Period(scope) => match &self.status {
                Status::Waiting if matches!(scope.reading, Reading::Investment(_)) => "Reading the company’s investment decision…",
                Status::Waiting => "Reading the selected site’s accounts…",
                Status::Publishing => "Site accounts have not been published for this period. Waiting for publication…",
                Status::Finished(text) => text,
            }
        }
    }

    pub(super) fn select(&mut self, selection: Selection) {
        self.selection = selection;
        self.status = Status::Waiting;
    }

    pub(super) fn receive(&mut self, scope: &Scope, result: Result<String, JournalError>) {
        if !matches!(&self.selection, Selection::Period(current) if current == scope) {
            return;
        }
        self.status = match result {
            Ok(reading) => Status::Finished(reading),
            Err(JournalError::CoverageAbsent) => Status::Publishing,
            Err(JournalError::SiteAbsent) => {
                Status::Finished("This site has no entry in the published period.".into())
            }
            Err(JournalError::SourceChanged | JournalError::Projection) => Status::Finished(
                "The financial reading failed verification for the selected committed frame."
                    .into(),
            ),
            Err(error) => Status::Finished(format!(
                "Could not read the selected site’s financial evidence ({error})."
            )),
        };
    }
}

#[derive(Default)]
pub(in crate::production) struct Loader {
    pending: Option<(Scope, Task<Result<String, JournalError>>)>,
    retry_at: f64,
    delay: f64,
}

pub(in crate::production) fn update(
    observation: ProductionObservation,
    navigation: Res<ProductionNavigation>,
    primary: Res<PrimaryView>,
    ui: Res<ObserverUiState>,
    time: Res<Time<Real>>,
    mut view: ResMut<AccountsView>,
    mut loader: Local<Loader>,
) {
    if navigation.is_changed()
        || observation.frame.is_changed()
        || observation.state.is_changed()
        || primary.is_changed()
        || ui.is_changed()
    {
        let selected = Selection::current(&observation, &navigation, *primary, &ui);
        if view.selection != selected {
            view.select(selected);
            loader.retry_at = 0.0;
            loader.delay = 1.0;
        }
    }
    if let Some((_, task)) = &mut loader.pending {
        let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(task)) else {
            return;
        };
        if let Some((scope, _)) = loader.pending.take() {
            view.receive(&scope, result);
            if matches!(view.status, Status::Publishing) {
                loader.retry_at = time.elapsed_secs_f64() + loader.delay;
                loader.delay = (loader.delay * 2.0).clamp(1.0, 8.0);
            }
        }
    }
    let Selection::Period(scope) = &view.selection else {
        return;
    };
    if matches!(view.status, Status::Finished(_)) || time.elapsed_secs_f64() < loader.retry_at {
        return;
    }
    let requested = scope.clone();
    loader.pending = Some((
        scope.clone(),
        IoTaskPool::get().spawn(async move { requested.read() }),
    ));
}
