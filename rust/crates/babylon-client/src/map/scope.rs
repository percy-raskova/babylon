//! Presentation scope comes from admitted county rows, never actor locations.
use std::collections::BTreeMap;

use babylon_kernel::geography::{CountyGeoid, CountyJurisdiction};
use babylon_persistence::{identity::CampaignId, observer_reader::ObserverCountyEconomy};
use bevy::prelude::*;

use super::{HoveredCounty, SelectedCounty};
use crate::atlas::CountyAtlas;
use crate::observer::ObserverSession;
use crate::observer_ui::ObserverFrame;

/// Fixed geography remains visible while another period of the same campaign loads.
#[derive(Resource, Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct CountyMapScope {
    identity: Option<(CampaignId, String)>,
    counties: Vec<usize>,
    preferred: Option<usize>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum MapScopeError {
    Empty,
    CountyOrder,
    NonDomestic(String),
    MissingAtlasCounty(String),
    AtlasIdentity,
    ChangedGeography,
}
impl std::fmt::Display for MapScopeError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "Campaign map scope refused: {self:?}")
    }
}
impl std::error::Error for MapScopeError {}

impl CountyMapScope {
    pub(crate) fn counties(&self) -> &[usize] {
        &self.counties
    }
    pub(crate) fn contains(&self, county: usize) -> bool {
        self.counties.binary_search(&county).is_ok()
    }
    pub(crate) fn adjacent(&self, selected: Option<usize>, forward: bool) -> Option<usize> {
        if self.counties.is_empty() {
            return None;
        }
        let current = selected.and_then(|county| self.counties.binary_search(&county).ok());
        let next = current.map_or(0, |index| {
            if forward {
                (index + 1) % self.counties.len()
            } else {
                (index + self.counties.len() - 1) % self.counties.len()
            }
        });
        Some(self.counties[next])
    }
    fn reconcile(
        &mut self,
        session: &ObserverSession,
        frame: Option<&ObserverFrame>,
        atlas: &CountyAtlas,
        selected: &mut SelectedCounty,
        hovered: &mut HoveredCounty,
    ) -> Result<(), MapScopeError> {
        let identity = session
            .foundation_digest
            .as_ref()
            .map(|digest| (session.campaign, digest.clone()));
        if self.identity != identity {
            self.identity = identity;
            self.counties.clear();
            self.preferred = selected.0.take().or(self.preferred);
            hovered.0 = None;
        }
        if self.identity.is_none() {
            return Ok(());
        }
        let Some(frame) = frame.and_then(|frame| frame.for_session(session)) else {
            return Ok(());
        };
        let admitted = admit_counties(atlas, &frame.counties)?;
        if !self.counties.is_empty() && self.counties != admitted {
            return Err(MapScopeError::ChangedGeography);
        }
        if self.counties != admitted {
            self.counties = admitted;
            selected.0 = self
                .preferred
                .take()
                .or(selected.0)
                .filter(|county| self.contains(*county))
                .or_else(|| {
                    atlas
                        .index_of_fips("26163")
                        .filter(|county| self.contains(*county))
                })
                .or_else(|| self.counties.first().copied());
            hovered.0 = None;
        }
        Ok(())
    }
}

fn admit_counties(
    atlas: &CountyAtlas,
    rows: &[ObserverCountyEconomy],
) -> Result<Vec<usize>, MapScopeError> {
    if rows.is_empty() {
        return Err(MapScopeError::Empty);
    }
    if rows
        .windows(2)
        .any(|pair| pair[0].county_geoid >= pair[1].county_geoid)
    {
        return Err(MapScopeError::CountyOrder);
    }
    let mut index = BTreeMap::new();
    for i in 0..atlas.len() {
        let county = atlas.county(i).ok_or(MapScopeError::AtlasIdentity)?;
        if index.insert(county.fips, i).is_some() {
            return Err(MapScopeError::AtlasIdentity);
        }
    }
    let mut admitted = Vec::with_capacity(rows.len());
    for row in rows {
        let county = CountyGeoid::try_from(row.county_geoid.as_str())
            .map_err(|_| MapScopeError::NonDomestic(row.county_geoid.clone()))?;
        if !matches!(
            county.jurisdiction(),
            CountyJurisdiction::State | CountyJurisdiction::DistrictOfColumbia
        ) {
            return Err(MapScopeError::NonDomestic(row.county_geoid.clone()));
        }
        admitted.push(
            *index
                .get(county.as_str())
                .ok_or_else(|| MapScopeError::MissingAtlasCounty(row.county_geoid.clone()))?,
        );
    }
    // Atlas lookup order is not an authority. Store ascending indices for selection.
    admitted.sort_unstable();
    Ok(admitted)
}

pub(super) fn sync_county_scope(
    atlas: Res<CountyAtlas>,
    frame: Option<Res<ObserverFrame>>,
    session: Option<ResMut<ObserverSession>>,
    mut scope: ResMut<CountyMapScope>,
    mut selected: ResMut<SelectedCounty>,
    mut hovered: ResMut<HoveredCounty>,
) {
    let Some(mut session) = session else { return };
    if !session.is_changed() && frame.as_ref().is_none_or(|frame| !frame.is_changed()) {
        return;
    }
    if session.phase == crate::observer::SessionPhase::Failed
        && frame.as_ref().is_none_or(|frame| !frame.is_changed())
    {
        return;
    }
    let mut next = scope.clone();
    if let Err(error) = next.reconcile(
        &session,
        frame.as_deref(),
        &atlas,
        &mut selected,
        &mut hovered,
    ) {
        next.counties.clear();
        selected.0 = None;
        hovered.0 = None;
        session.fail(error.to_string());
    }
    scope.set_if_neq(next);
}

#[cfg(test)]
mod tests {
    use super::*;
    fn atlas() -> CountyAtlas {
        CountyAtlas::parse(include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/map/county_atlas.bin"
        )))
        .unwrap()
    }
    fn rows(ids: &[&str]) -> Vec<ObserverCountyEconomy> {
        ids.iter()
            .map(|id| ObserverCountyEconomy {
                county_geoid: (*id).to_owned(),
                annual_avg_estabs_count: None,
                annual_avg_emplvl: None,
                total_annual_wages: None,
                annual_avg_wkly_wage: None,
            })
            .collect()
    }
    #[test]
    fn scope_refuses_duplicate_missing_dependency_and_foreign_counties() {
        let atlas = atlas();
        assert_eq!(admit_counties(&atlas, &[]), Err(MapScopeError::Empty));
        assert_eq!(
            admit_counties(&atlas, &rows(&["01001", "01001"])),
            Err(MapScopeError::CountyOrder)
        );
        assert_eq!(
            admit_counties(&atlas, &rows(&["01003", "01001"])),
            Err(MapScopeError::CountyOrder)
        );
        assert_eq!(
            admit_counties(&atlas, &rows(&["01000"])),
            Err(MapScopeError::MissingAtlasCounty("01000".into()))
        );
        assert_eq!(
            admit_counties(&atlas, &rows(&["72001"])),
            Err(MapScopeError::NonDomestic("72001".into()))
        );
        assert_eq!(
            admit_counties(&atlas, &rows(&["CAN"])),
            Err(MapScopeError::NonDomestic("CAN".into()))
        );
    }
    #[test]
    fn keyboard_selection_wraps_only_within_the_installed_scope() {
        let atlas = atlas();
        let counties = admit_counties(&atlas, &rows(&["02013", "15005"])).unwrap();
        let scope = CountyMapScope {
            counties: counties.clone(),
            ..default()
        };
        assert_eq!(scope.adjacent(None, true), Some(counties[0]));
        assert_eq!(scope.adjacent(Some(counties[0]), false), Some(counties[1]));
        assert_eq!(scope.adjacent(Some(counties[1]), true), Some(counties[0]));
        assert!(!scope.contains(atlas.index_of_fips("26163").unwrap()));
        assert_eq!(CountyMapScope::default().adjacent(None, true), None);
    }
}
