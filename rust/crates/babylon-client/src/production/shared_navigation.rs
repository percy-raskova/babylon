//! Production presentation restored only through the currently admitted snapshot.

use babylon_persistence::production_observation::ProductionSnapshot;

use super::{
    navigation, ProductionCommand, ProductionNavigation, ProductionPage, ProductionReadingSection,
};
use crate::observer::ObserverSession;

/// Selection and reading parameters; deliberately excludes local history and observations.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct ProductionRoute {
    site: Option<String>,
    process: Option<String>,
    county: Option<String>,
    county_open: bool,
    cohort_page: usize,
    relationship_page: usize,
    competitor_page: usize,
    flat: bool,
    details_open: bool,
    reading: ProductionReadingSection,
}

impl ProductionNavigation {
    pub(crate) fn navigation_route(&self) -> ProductionRoute {
        ProductionRoute {
            site: self.selected_site.clone(),
            process: self.selected_process.clone(),
            county: self.county_geoid.clone(),
            county_open: self.county_open,
            cohort_page: self.cohort_page,
            relationship_page: self.relationship_page,
            competitor_page: self.competitor_page,
            flat: self.flat,
            details_open: self.details_open,
            reading: self.reading_section,
        }
    }

    /// Returns a refusal for a vanished subject, leaving a stable county parent.
    pub(crate) fn restore_navigation(
        &mut self,
        route: &ProductionRoute,
        snapshot: Option<&ProductionSnapshot>,
        session: &ObserverSession,
    ) -> Option<&'static str> {
        self.county_geoid.clone_from(&route.county);
        self.county_open = route.county_open;
        self.flat = route.flat;
        self.reading_section = route.reading;
        self.cohort_page = route.cohort_page;
        self.relationship_page = route.relationship_page;
        self.competitor_page = route.competitor_page;
        self.details_open = route.details_open;
        self.selected_site = route.site.clone();
        self.selected_process = route.process.clone();
        let site = snapshot.and_then(|snapshot| {
            snapshot
                .sites
                .iter()
                .find(|site| route.site.as_ref() == Some(&site.id))
        });
        if route.site.is_some() && site.is_none() {
            self.selected_site = None;
            self.selected_process = None;
            self.county_open = true;
            self.details_open = false;
            self.relationship_page = 0;
            self.competitor_page = 0;
            return Some("That work relationship is unavailable. Returned to the county view.");
        }
        if route.process.is_some()
            && !site.is_some_and(|site| {
                site.processes
                    .iter()
                    .any(|process| route.process.as_ref() == Some(&process.id))
            })
        {
            self.selected_process = None;
            self.details_open = false;
            return Some("That process is unavailable. Returned to the work relationship.");
        }
        let mut missing_page = false;
        for (kind, page) in [
            (ProductionPage::Cohorts, self.cohort_page),
            (ProductionPage::Relationships, self.relationship_page),
            (ProductionPage::Competitors, self.competitor_page),
        ] {
            if page > 0
                && !navigation::command_enabled(
                    &ProductionCommand::Page {
                        kind,
                        page,
                        context: session.context(),
                    },
                    snapshot,
                    self,
                    session,
                )
            {
                match kind {
                    ProductionPage::Cohorts => self.cohort_page = 0,
                    ProductionPage::Relationships => self.relationship_page = 0,
                    ProductionPage::Competitors => self.competitor_page = 0,
                }
                missing_page = true;
            }
        }
        if missing_page {
            return Some("That reading page is unavailable. Returned to its first page.");
        }
        None
    }
}
