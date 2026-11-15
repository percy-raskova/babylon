//! Site statement totals and bounded site navigation for a full-observer county.
use super::rail;
use super::state::{Action, Measure, MoneyView, Observation, Scope};
use crate::dossier;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::production::{self, ProductionCommand, ProductionReadingSection};
use babylon_material_circuit::SiteId;
use babylon_persistence::money_journal::{CountySiteAccounts, CountySitePage, JournalError};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};

#[derive(Default)]
pub(super) struct Books {
    pub(super) offset: Option<u64>,
    result: Option<Result<CountySiteAccounts, JournalError>>,
}

impl Books {
    pub(super) fn key(&self) -> (Option<u64>, bool) {
        (self.offset, self.result.is_some())
    }

    pub(super) fn navigate(&mut self, from: Option<u64>, to: Option<u64>) -> bool {
        if self.offset != from {
            return false;
        }
        let valid = match (from, to) {
            (None, Some(0)) | (Some(_), None) => true,
            (Some(start), Some(next)) => {
                matches!(&self.result, Some(Ok(CountySiteAccounts::Monetary(page))) if next < page.site_count && start.abs_diff(next)==6)
            }
            _ => false,
        };
        if valid {
            self.offset = to;
            self.result = None;
        }
        valid
    }

    pub(super) fn open_site(
        &self,
        id: SiteId,
        offset: u64,
        observed: &Observation,
        scope: &Scope,
        commands: &mut Commands,
    ) -> bool {
        if self.offset != Some(offset)
            || !matches!(&self.result, Some(Ok(CountySiteAccounts::Monetary(page))) if page.sites.contains(&id))
        {
            return false;
        }
        let site_id = dossier::hex_bytes(id.as_bytes());
        let site = observed
            .frame
            .for_session(&observed.session)
            .and_then(|frame| frame.production.as_ref())
            .and_then(|production| {
                production
                    .sites
                    .iter()
                    .find(|site| site.id == site_id && site.is_in_county(&scope.county))
            });
        if site.is_none() {
            return false;
        }
        commands.write_message(ProductionCommand::Select {
            site_id,
            context: scope.context.clone(),
        });
        commands.write_message(ProductionCommand::Reading(
            ProductionReadingSection::Accounts,
        ));
        true
    }
}

struct Pending {
    scope: Scope,
    offset: u64,
    read: Task<Result<CountySiteAccounts, JournalError>>,
}

#[derive(Resource, Default)]
pub(super) struct Worker(Option<Pending>);

fn read(scope: &Scope, offset: u64) -> Result<CountySiteAccounts, JournalError> {
    let reader = ObserverEconomyReader::from_observer_env().map_err(JournalError::Observer)?;
    let county = scope
        .county
        .as_str()
        .try_into()
        .map_err(|_| JournalError::Projection)?;
    let hash = scope
        .tick_hash
        .as_deref()
        .ok_or(JournalError::SourceChanged)?;
    reader.county_site_accounts_for_frame(
        scope.context.campaign,
        scope.context.tick,
        county,
        &scope.foundation,
        hash,
        offset,
    )
}

pub(super) fn update(mut view: ResMut<MoneyView>, mut worker: ResMut<Worker>) {
    if let Some(pending) = &mut worker.0 {
        let Some(result) =
            tasks::block_on(tasks::futures_lite::future::poll_once(&mut pending.read))
        else {
            return;
        };
        if view.scope.as_ref() == Some(&pending.scope) && view.books.offset == Some(pending.offset)
        {
            view.books.result = Some(result);
        }
        worker.0 = None;
    }
    let (Some(scope), Some(offset)) = (&view.scope, view.books.offset) else {
        return;
    };
    if view.books.result.is_some() || scope.measure != Measure::Money || scope.context.tick == 0 {
        return;
    }
    let requested = scope.clone();
    worker.0 = Some(Pending {
        scope: scope.clone(),
        offset,
        read: IoTaskPool::get().spawn(async move { read(&requested, offset) }),
    });
}

pub(super) fn panel(
    rail: &mut ChildSpawnerCommands,
    view: &MoneyView,
    obs: &Observation,
    scope: &Scope,
) -> bool {
    if scope.measure != Measure::Money || scope.context.tick == 0 {
        return false;
    }
    let from = view.books.offset;
    let Some(offset) = from else {
        rail::control(
            rail,
            view,
            scope,
            Action::Books { from, to: Some(0) },
            "County site accounts".into(),
        );
        return false;
    };
    rail::control(
        rail,
        view,
        scope,
        Action::Books { from, to: None },
        "Back to payments".into(),
    );
    rail.spawn(rail::label(
        format!("Operating sites · period {}", scope.context.tick),
        18.0,
        theme::PAPER,
        ObserverFontRole::Display,
    ));
    let Some(result) = &view.books.result else {
        rail.spawn(rail::label(
            "Reading operating-site statements…",
            15.0,
            theme::GRAY,
            ObserverFontRole::Body,
        ));
        return true;
    };
    let page = match result {
        Ok(CountySiteAccounts::Monetary(page)) => page,
        Ok(CountySiteAccounts::PhysicalOnly) => {
            rail.spawn(rail::label(
                "Physical books only. This period has no monetary statements.",
                15.0,
                theme::GRAY,
                ObserverFontRole::Body,
            ));
            return true;
        }
        Err(error) => {
            rail.spawn(rail::label(
                format!("County site statements are unavailable ({error})."),
                15.0,
                theme::GRAY,
                ObserverFontRole::Body,
            ));
            return true;
        }
    };
    if page.site_count == 0 {
        rail.spawn(rail::label(
            "No recorded operating sites in this county.",
            15.0,
            theme::PAPER,
            ObserverFontRole::Body,
        ));
        return true;
    }
    rail.spawn(rail::label(format!(
        "{} operating sites\nChange in spendable cash  {}\nPeriod profit or loss  {}\nClosing retained earnings  {}",
        page.site_count,rail::amount(&page.cash_change_micros),rail::amount(&page.period_profit_micros),rail::amount(&page.closing_retained_earnings_micros)
    ),17.0,theme::PAPER,ObserverFontRole::Exact));
    site_links(rail, view, obs, scope, page, offset);
    true
}

fn site_links(
    rail: &mut ChildSpawnerCommands,
    view: &MoneyView,
    obs: &Observation,
    scope: &Scope,
    page: &CountySitePage,
    offset: u64,
) {
    let snapshot = obs
        .frame
        .for_session(&obs.session)
        .and_then(|frame| frame.production.as_ref());
    for &site in &page.sites {
        let site_id = dossier::hex_bytes(site.as_bytes());
        if let Some(source) = snapshot.and_then(|p| {
            p.sites
                .iter()
                .find(|s| s.id == site_id && s.is_in_county(&scope.county))
        }) {
            rail::control(
                rail,
                view,
                scope,
                Action::Site { offset, site },
                format!("Accounts · {}", production::site_subject(source)),
            );
        } else {
            rail.spawn(rail::label(
                format!("Site {site_id} · operating details unavailable"),
                15.0,
                theme::GRAY,
                ObserverFontRole::Body,
            ));
        }
    }
    if offset >= 6 {
        rail::control(
            rail,
            view,
            scope,
            Action::Books {
                from: Some(offset),
                to: Some(offset - 6),
            },
            "Previous sites".into(),
        );
    }
    if offset.saturating_add(6) < page.site_count {
        rail::control(
            rail,
            view,
            scope,
            Action::Books {
                from: Some(offset),
                to: Some(offset + 6),
            },
            "More sites".into(),
        );
    }
}
