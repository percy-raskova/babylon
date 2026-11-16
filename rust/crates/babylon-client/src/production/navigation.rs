//! Observer navigation, scoped command admission, and production selection.

use super::ProductionReadingSection;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_persistence::production_observation::{ProductionSite, ProductionSnapshot};

use bevy::ecs::system::SystemParam;
use bevy::prelude::*;

use crate::atlas::CountyAtlas;
use crate::map::SelectedCounty;
use crate::observer::ObserverSession;
use crate::observer_focus::ObserverFocusWorld;
use crate::observer_ui::{ObserverFrame, ObserverUiState};

use super::{
    PrimaryView, ProductionCommand, ProductionNavigation, ProductionObservation, ProductionPage,
    ProductionUi,
};
use crate::observer::Perspective;
use crate::production_brief;
use crate::production_freight;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::production_observation::ProductionProcess;
use std::collections::BTreeSet;

impl ProductionNavigation {
    pub(super) fn open_county(
        &mut self,
        county_geoid: &str,
        snapshot: Option<&ProductionSnapshot>,
    ) {
        self.county_geoid = Some(county_geoid.to_owned());
        let resume = snapshot.is_some_and(|snapshot| {
            snapshot.sites.iter().any(|site| {
                self.selected_site.as_ref() == Some(&site.id) && site.is_in_county(county_geoid)
            })
        });
        if !resume {
            self.county_open = true;
            self.details_open = false;
            self.cohort_page = 0;
            self.selected_site = None;
            self.household = None;
            self.history.clear();
        }
    }

    fn open_resident_receipt(
        &mut self,
        site: &str,
        principal: FinalDemandPrincipalId,
        ui: &mut ObserverUiState,
    ) {
        self.select_site(site);
        self.details_open = true;
        self.reading_section = ProductionReadingSection::Flow;
        self.household = Some(principal);
        ui.archive_open = false;
        ui.disclosure = None;
        ui.history_open = false;
    }

    fn set_page(&mut self, kind: ProductionPage, page: usize) {
        let target = match kind {
            ProductionPage::Cohorts => &mut self.cohort_page,
            ProductionPage::Relationships => &mut self.relationship_page,
            ProductionPage::Competitors => &mut self.competitor_page,
        };
        *target = page;
    }

    pub(super) fn select_site(&mut self, id: &str) {
        if self.selected_site.as_deref() != Some(id) {
            self.household = None;
        }
        if let Some(previous) = self.selected_site.take() {
            if previous != id {
                if self.history.len() == 128 {
                    self.history.remove(0);
                }
                self.history.push(previous);
            }
        }
        self.selected_site = Some(id.to_owned());
        self.county_open = false;
        self.relationship_page = 0;
        self.competitor_page = 0;
        self.selected_process = None;
    }

    fn contains_page(
        &self,
        snapshot: &ProductionSnapshot,
        kind: ProductionPage,
        page: usize,
    ) -> bool {
        let count = match kind {
            ProductionPage::Cohorts => snapshot
                .sites
                .iter()
                .filter(|site| {
                    self.county_geoid
                        .as_deref()
                        .is_some_and(|county| site.is_in_county(county))
                })
                .count(),
            ProductionPage::Relationships => self
                .selected_site
                .as_ref()
                .and_then(|id| snapshot.sites.iter().find(|site| site.id == *id))
                .map_or(0, |site| {
                    production_brief::dependency_sites(site, snapshot)
                        .iter()
                        .map(|(_, site)| &site.id)
                        .collect::<BTreeSet<_>>()
                        .len()
                }),
            ProductionPage::Competitors => match self
                .selected_site
                .as_deref()
                .map(|id| production_freight::competitor_sites(id, snapshot))
            {
                Some(Ok(sites)) => sites.len(),
                None => 0,
                Some(Err(_)) => return false,
            },
        };
        page < count.div_ceil(6).max(1)
    }

    /// Return whether the primary view and selected county should follow a previous site.
    fn back(&mut self, available: &ProductionControlAvailability) -> bool {
        if self.household.take().is_some() {
            return false;
        }
        if let Some(index) = available.previous_index {
            self.selected_site = Some(self.history[index].clone());
            self.history.truncate(index);
        } else if available.county_back {
            self.county_open = true;
            self.selected_site = None;
            self.details_open = false;
        }
        self.relationship_page = 0;
        self.competitor_page = 0;
        self.selected_process = None;
        available.previous_index.is_some()
    }

    pub(crate) fn process<'a>(&self, site: &'a ProductionSite) -> Option<&'a ProductionProcess> {
        site.processes
            .iter()
            .find(|process| self.selected_process.as_ref() == Some(&process.id))
            .or_else(|| site.processes.iter().min_by(|a, b| a.id.cmp(&b.id)))
    }
}

pub(super) struct ProductionControlAvailability {
    pub(super) scene: bool,
    pub(super) readings: bool,
    pub(super) previous_index: Option<usize>,
    pub(super) county_back: bool,
}

impl ProductionControlAvailability {
    pub(super) fn for_snapshot(
        snapshot: Option<&ProductionSnapshot>,
        navigation: &ProductionNavigation,
    ) -> Self {
        Self {
            scene: snapshot.is_some_and(|snapshot| !snapshot.sites.is_empty()),
            readings: !navigation.county_open
                && snapshot.is_some_and(|snapshot| !snapshot.sites.is_empty()),
            county_back: navigation.selected_site.is_some()
                && navigation.county_geoid.is_some()
                && !navigation.county_open,
            previous_index: snapshot.and_then(|snapshot| {
                navigation.history.iter().rposition(|id| {
                    navigation.selected_site.as_ref() != Some(id)
                        && snapshot.sites.iter().any(|site| site.id == *id)
                })
            }),
        }
    }

    pub(super) fn display(
        &self,
        command: &ProductionCommand,
        state: &ObserverSession,
    ) -> Option<Display> {
        let available = match command {
            ProductionCommand::Reading(
                ProductionReadingSection::Accounts | ProductionReadingSection::Investment,
            ) => self.readings && super::accounting::authorized(state),
            ProductionCommand::Back => self.previous_index.is_some() || self.county_back,
            ProductionCommand::Details | ProductionCommand::Reading(_) => self.readings,
            ProductionCommand::Flat => self.scene,
            _ => return None,
        };
        Some(if available {
            Display::Flex
        } else {
            Display::None
        })
    }

    pub(super) fn refusal(
        &self,
        command: &ProductionCommand,
        snapshot: Option<&ProductionSnapshot>,
        navigation: &ProductionNavigation,
        state: &ObserverSession,
    ) -> Option<&'static str> {
        match command {
            ProductionCommand::Reading(
                ProductionReadingSection::Accounts | ProductionReadingSection::Investment,
            ) if !super::accounting::authorized(state) => {
                Some("Financial readings require the full observer.")
            }
            ProductionCommand::Back
                if navigation.household.is_none()
                    && self.previous_index.is_none()
                    && !self.county_back =>
            {
                Some("There is no previous work view in this observation.")
            }
            ProductionCommand::Flat if !self.scene => {
                Some("Display controls need disclosed production relationships.")
            }
            ProductionCommand::Details | ProductionCommand::Reading(_)
                if navigation.county_open && !navigation.details_open =>
            {
                Some("Choose a county cohort before opening its readings.")
            }
            ProductionCommand::Details if !self.scene && !navigation.details_open => {
                Some("Exact readings need disclosed production relationships.")
            }
            ProductionCommand::Reading(_) if !self.scene => {
                Some("Exact readings need disclosed production relationships.")
            }
            ProductionCommand::ResidentReceipt {
                site_id,
                principal,
                context,
                county,
            } if !state.accepts(context)
                || !super::accounting::authorized(state)
                || !snapshot.is_some_and(|s| {
                    super::customers::served_at(s, site_id, *principal, context.tick, Some(county))
                }) =>
            {
                Some("This household receipt is unavailable for the selected retailer and period.")
            }
            ProductionCommand::Household {
                site_id,
                principal,
                context,
            } if !state.accepts(context)
                || !super::accounting::authorized(state)
                || !navigation.details_open
                || navigation.reading_section != ProductionReadingSection::Flow
                || navigation.selected_site.as_ref() != Some(site_id)
                || !snapshot.is_some_and(|s| {
                    super::customers::served(s, site_id, *principal, context.tick)
                }) =>
            {
                Some("This household receipt is unavailable for the selected retailer and period.")
            }
            ProductionCommand::Page { context, .. }
            | ProductionCommand::Process { context, .. }
                if !state.accepts(context) || !self.scene =>
            {
                Some("This circuit control belongs to another observation.")
            }
            ProductionCommand::Process { process_id, .. }
                if !snapshot.is_some_and(|snapshot| {
                    snapshot.sites.iter().any(|site| {
                        navigation.selected_site.as_ref() == Some(&site.id)
                            && site
                                .processes
                                .iter()
                                .any(|process| process.id == *process_id)
                    })
                }) =>
            {
                Some("This process is not disclosed for the selected owner.")
            }
            ProductionCommand::Page { kind, page, .. }
                if !snapshot
                    .is_some_and(|snapshot| navigation.contains_page(snapshot, *kind, *page)) =>
            {
                Some("This page is unavailable in the current observation.")
            }
            ProductionCommand::Select { site_id, context }
            | ProductionCommand::Focus { site_id, context }
                if !state.accepts(context)
                    || !snapshot.is_some_and(|snapshot| {
                        snapshot.sites.iter().any(|site| site.id == *site_id)
                    }) =>
            {
                Some("This work relationship is unavailable in the current observation.")
            }
            _ => None,
        }
    }
}

/// Reuse the same snapshot/context capability for opt-in ordinary native controls.
pub(crate) fn command_enabled(
    command: &ProductionCommand,
    snapshot: Option<&ProductionSnapshot>,
    navigation: &ProductionNavigation,
    state: &ObserverSession,
) -> bool {
    ProductionControlAvailability::for_snapshot(snapshot, navigation)
        .refusal(command, snapshot, navigation, state)
        .is_none()
}

/// A disclosed inspector temporarily occupies the log's shared side panel.
pub(crate) fn readings_panel_visible(
    view: PrimaryView,
    navigation: &ProductionNavigation,
    ui: &ObserverUiState,
    snapshot: Option<&ProductionSnapshot>,
) -> bool {
    view == PrimaryView::Production
        && navigation.details_open
        && !ui.history_open
        && ProductionControlAvailability::for_snapshot(snapshot, navigation).scene
        && !ui.archive_open
        && !ui.menu_open
        && !ui.comparison_open
        && !ui.splash_visible
}

#[derive(SystemParam)]
pub(crate) struct NavigationScene<'w> {
    atlas: Res<'w, CountyAtlas>,
    selected: ResMut<'w, SelectedCounty>,
}

impl NavigationScene<'_> {
    fn resident_county_refusal(
        &self,
        command: &ProductionCommand,
        view: PrimaryView,
    ) -> Option<&'static str> {
        let ProductionCommand::ResidentReceipt { county, .. } = command else {
            return None;
        };
        let selected = self.selected.0.and_then(|index| self.atlas.county(index));
        (view != PrimaryView::Map || selected.is_none_or(|place| place.fips != county))
            .then_some("Select this resident county on the map first.")
    }
}

pub(crate) fn navigate(
    mut commands: Commands,
    mut events: MessageReader<ProductionCommand>,
    mut view: ResMut<PrimaryView>,
    mut navigation: ResMut<ProductionNavigation>,
    observation: ProductionObservation,
    mut scene: NavigationScene,
    mut ui: ProductionUi,
) {
    let snapshot = observation
        .frame
        .for_session(&observation.state)
        .and_then(|frame| frame.production.as_ref());
    for event in events.read() {
        if ui.state.menu_open || ui.state.splash_visible || ui.state.comparison_open {
            continue;
        }
        if observation.state.organizer_enabled && matches!(event, ProductionCommand::Open) {
            commands.trigger(crate::organizer::ui::OrganizerEvidenceRequested);
            continue;
        }
        let available = ProductionControlAvailability::for_snapshot(snapshot, &navigation);
        if let Some(reason) = available
            .refusal(event, snapshot, &navigation, &observation.state)
            .or_else(|| scene.resident_county_refusal(event, *view))
        {
            ui.feedback.reject(reason, ui.time.elapsed_secs_f64());
            continue;
        }
        let mut sync_county = false;
        match event {
            ProductionCommand::Open => {
                sync_county = true;
                *view = PrimaryView::Production;
                ui.state.archive_open = false;
                ui.state.disclosure = None;
                if let Some(county) = scene.selected.0.and_then(|index| scene.atlas.county(index)) {
                    navigation.open_county(county.fips, snapshot);
                }
            }
            ProductionCommand::Map => {
                *view = PrimaryView::Map;
                ui.state.disclosure = None;
            }
            ProductionCommand::Flat => {
                navigation.flat = !navigation.flat;
            }
            ProductionCommand::Details => {
                navigation.details_open = !navigation.details_open;
                if !navigation.details_open {
                    navigation.household = None;
                }
            }
            ProductionCommand::Reading(section) => {
                navigation.household = None;
                navigation.reading_section = *section;
                navigation.details_open = true;
            }
            ProductionCommand::ResidentReceipt {
                site_id, principal, ..
            } => {
                navigation.open_resident_receipt(site_id, *principal, &mut ui.state);
                *view = PrimaryView::Production;
                sync_county = true;
            }
            ProductionCommand::Household { principal, .. } => {
                navigation.household = Some(*principal);
            }
            ProductionCommand::Page { kind, page, .. } => navigation.set_page(*kind, *page),
            ProductionCommand::Process { process_id, .. } => {
                navigation.selected_process = Some(process_id.clone());
                ui.state.history_open = true;
                navigation.details_open = false;
            }
            ProductionCommand::Back => {
                sync_county = navigation.back(&available);
                if sync_county {
                    *view = PrimaryView::Production;
                    ui.state.archive_open = false;
                    ui.state.disclosure = None;
                }
            }
            ProductionCommand::Select { site_id: id, .. }
            | ProductionCommand::Focus { site_id: id, .. } => {
                navigation.select_site(id);
                sync_county = true;
                *view = if matches!(event, ProductionCommand::Focus { .. }) {
                    PrimaryView::Map
                } else {
                    PrimaryView::Production
                };
                ui.state.archive_open = false;
                ui.state.disclosure = None;
            }
        }
        if matches!(event, ProductionCommand::Open | ProductionCommand::Map) {
            commands.trigger(ObserverFocusWorld);
        }
        if !sync_county {
            continue;
        }
        sync_selected_county(&navigation, snapshot, &scene.atlas, &mut scene.selected);
    }
}

pub(super) fn sync_selected_county(
    navigation: &ProductionNavigation,
    snapshot: Option<&ProductionSnapshot>,
    atlas: &CountyAtlas,
    selected: &mut SelectedCounty,
) {
    if let Some(site) = snapshot.and_then(|snapshot| {
        snapshot
            .sites
            .iter()
            .find(|site| navigation.selected_site.as_ref() == Some(&site.id))
    }) {
        selected.0 = (0..atlas.len()).find(|index| {
            atlas
                .county(*index)
                .is_some_and(|county| site.is_in_county(county.fips))
        });
    }
}

pub(super) fn sync_world_county(
    observation: ProductionObservation,
    view: Res<PrimaryView>,
    atlas: Res<CountyAtlas>,
    selected: Res<SelectedCounty>,
    mut navigation: ResMut<ProductionNavigation>,
) {
    if *view != PrimaryView::Map {
        return;
    }
    let snapshot = observation
        .frame
        .for_session(&observation.state)
        .and_then(|frame| frame.production.as_ref());
    let county = selected.0.and_then(|index| atlas.county(index));
    if let (Some(snapshot), Some(county)) = (snapshot, county) {
        if navigation.county_geoid.as_deref() != Some(county.fips) {
            navigation.open_county(county.fips, Some(snapshot));
        }
    }
}

pub(super) fn invalidate_navigation(
    state: Res<ObserverSession>,
    frame: Res<ObserverFrame>,
    mut navigation: ResMut<ProductionNavigation>,
    mut scope: Local<Option<(CampaignId, Perspective, Option<u64>)>>,
) {
    let current = (state.campaign, state.perspective, state.lifecycle_epoch());
    if scope.as_ref() != Some(&current) {
        navigation.selected_site = None;
        navigation.selected_process = None;
        navigation.household = None;
        navigation.county_open = false;
        navigation.county_geoid = None;
        navigation.relationship_page = 0;
        navigation.competitor_page = 0;
        navigation.cohort_page = 0;
        navigation.details_open = false;
        navigation.history.clear();
        *scope = Some(current);
    }
    if frame.is_changed() {
        if let Some(snapshot) = frame
            .for_session(&state)
            .and_then(|frame| frame.production.as_ref())
        {
            navigation
                .history
                .retain(|id| snapshot.sites.iter().any(|site| site.id == *id));
            if navigation
                .selected_site
                .as_ref()
                .is_some_and(|id| !snapshot.sites.iter().any(|site| site.id == *id))
            {
                navigation.selected_site = None;
            }
            if navigation.household.is_some_and(|id| {
                !navigation.selected_site.as_ref().is_some_and(|site| {
                    super::customers::served(snapshot, site, id, state.viewed_tick)
                })
            }) {
                navigation.household = None;
            }
        }
    }
}

/// Start with a visible dependency, then preserve the person's selection.
/// No subject can be chosen from an observation outside the current capability.
pub(super) fn focus_opening(
    state: Res<ObserverSession>,
    frame: Res<ObserverFrame>,
    view: Res<PrimaryView>,
    mut navigation: ResMut<ProductionNavigation>,
    atlas: Res<CountyAtlas>,
    mut selected: ResMut<SelectedCounty>,
) {
    if *view != PrimaryView::Production
        || navigation.selected_site.is_some()
        || navigation.county_open
    {
        return;
    }
    let Some(site) = frame
        .for_session(&state)
        .and_then(|frame| frame.production.as_ref())
        .and_then(production_brief::opening_site)
    else {
        return;
    };
    navigation.selected_site = Some(site.id.clone());
    selected.0 = (0..atlas.len()).find(|index| {
        atlas
            .county(*index)
            .is_some_and(|county| site.is_in_county(county.fips))
    });
}
