//! Lazy source codes for a selected workplace disclosed by its own national QCEW cohort.
use super::{
    accounting, navigation, PrimaryView, ProductionNavigation, ProductionObservation,
    ProductionReadingSection,
};
use crate::observer_io::ObservationCache;
use crate::observer_ui::ObserverUiState;
use babylon_material_circuit::SiteId;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::{ObserverEconomyError, ObserverEconomyReader};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};

#[derive(Clone, PartialEq, Eq)]
struct Selection {
    campaign: CampaignId,
    foundation: String,
    site: SiteId,
}

impl Selection {
    fn current(
        observed: &ProductionObservation,
        navigation: &ProductionNavigation,
        view: PrimaryView,
        ui: &ObserverUiState,
    ) -> Option<Self> {
        if navigation.reading_section != ProductionReadingSection::Sources
            || !accounting::authorized(&observed.state)
        {
            return None;
        }
        let frame = observed.frame.for_session(&observed.state)?;
        let snapshot = frame.production.as_ref()?;
        let site = navigation.selected_site.as_deref()?;
        if !navigation::readings_panel_visible(view, navigation, ui, Some(snapshot))
            || !snapshot
                .national_observed_contexts
                .iter()
                .any(|r| r.site_id == site)
        {
            return None;
        }
        Some(Self {
            campaign: observed.state.campaign,
            foundation: frame.foundation_digest.clone(),
            site: SiteId::from_bytes(crate::cli::identity_bytes(site)?),
        })
    }
}

type Reading = Result<Vec<String>, ObserverEconomyError>;

#[derive(Resource, Default)]
pub(crate) struct Codes {
    selected: Option<Selection>,
    text: Option<String>,
    pending: Option<(Selection, Task<Reading>)>,
}

impl Codes {
    pub(super) fn text(&self) -> Option<&str> {
        self.selected.as_ref().map(|_| {
            self.text
                .as_deref()
                .unwrap_or("Reading cohort NAICS codes…")
        })
    }
}

pub(super) fn update(
    observed: ProductionObservation,
    navigation: Res<ProductionNavigation>,
    view: Res<PrimaryView>,
    ui: Res<ObserverUiState>,
    cache: Option<Res<ObservationCache>>,
    mut codes: ResMut<Codes>,
) {
    let selection = Selection::current(&observed, &navigation, *view, &ui);
    if codes.selected != selection {
        codes.selected = selection;
        codes.text = None;
    }
    if let Some(pending) = codes.bypass_change_detection().pending.as_mut() {
        let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(&mut pending.1))
        else {
            return;
        };
        if codes.selected.as_ref() == codes.pending.as_ref().map(|p| &p.0) {
            codes.text = Some(match result {
                Ok(codes) => format!("Source members · NAICS {}", codes.join(", ")),
                Err(reason) => format!("Cohort NAICS codes unavailable ({reason})."),
            });
        }
        codes.pending = None;
    }
    let Some(key) = codes
        .selected
        .as_ref()
        .filter(|_| codes.text.is_none())
        .cloned()
    else {
        return;
    };
    let reader = cache.as_deref().and_then(ObservationCache::full_reader);
    let requested = key.clone();
    codes.pending = Some((
        key,
        IoTaskPool::get().spawn(async move {
            let reader = reader.map_or_else(ObserverEconomyReader::from_observer_env, Ok)?;
            reader.site_source_member_codes(
                requested.campaign,
                &requested.foundation,
                requested.site,
            )
        }),
    ));
}
