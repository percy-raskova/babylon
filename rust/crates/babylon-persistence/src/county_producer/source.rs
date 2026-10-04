//! Source-scoped county identities and explicitly captured local detail.
use std::collections::{BTreeMap, BTreeSet};

use super::{
    county_committed_signals, verify_pinned_artifact_digests, ArchiveCitation,
    CommittedTerritoryFields, CountyPagePlan, CountyPlaceLink, CountySignal, SemanticArchiveError,
    SpatialReferenceProducts, COMMITTED_TICK_SOURCE_ID,
};
use crate::national_counties::NationalCountyReference;

pub(super) const NATIONAL_COUNTY_SOURCE_ID: &str = "national-county-reference-2024-v1";
const NO_LOCAL_DETAIL_QUESTION: &str =
    "Which county should organizers investigate next? Captured local place detail unavailable.";

pub(crate) enum CountySource {
    Michigan(SpatialReferenceProducts),
    National {
        names: BTreeMap<String, String>,
        digest: [u8; 32],
        detail: Option<SpatialReferenceProducts>,
    },
}
impl CountySource {
    pub(crate) fn national(
        counties: &NationalCountyReference,
        detail: Option<&SpatialReferenceProducts>,
    ) -> Result<Self, SemanticArchiveError> {
        if let Some(detail) = detail {
            verify_pinned_artifact_digests(detail)?;
        }
        Ok(Self::National {
            names: counties
                .counties()
                .iter()
                .map(|row| (row.geoid().to_string(), row.name().to_owned()))
                .collect(),
            digest: counties.artifact_sha256(),
            detail: detail.cloned(),
        })
    }

    pub(super) fn plans(
        &self,
        mapping: Vec<(String, String)>,
        committed: &BTreeMap<String, CommittedTerritoryFields>,
    ) -> Result<Vec<CountyPagePlan>, SemanticArchiveError> {
        let names: BTreeMap<&str, &str> = match self {
            Self::Michigan(detail) => detail
                .counties()
                .iter()
                .map(|row| (row.county_geoid(), row.county_name()))
                .collect(),
            Self::National { names, .. } => names
                .iter()
                .map(|(key, name)| (key.as_str(), name.as_str()))
                .collect(),
        };
        let detail = match self {
            Self::Michigan(detail) => Some(detail),
            Self::National { detail, .. } => detail.as_ref(),
        };
        let links = detail.map(place_links).transpose()?.unwrap_or_default();
        mapping
            .into_iter()
            .map(|(geoid, local)| {
                let title = (*names
                    .get(geoid.as_str())
                    .ok_or(SemanticArchiveError::StoredPageMismatch)?)
                .to_owned();
                let fields = committed.get(&local).copied().unwrap_or_default();
                if matches!(self, Self::National { .. }) && fields.qcew.iter().any(Option::is_some)
                {
                    return Err(SemanticArchiveError::StoredPageMismatch);
                }
                let mut signals = county_committed_signals(&fields)?;
                if let Self::National { digest, .. } = self {
                    signals.push(identity_signal(&geoid, digest)?);
                }
                let mut plan = CountyPagePlan::try_new(
                    geoid.clone(),
                    local,
                    title,
                    signals,
                    links.get(&geoid).cloned().unwrap_or_default(),
                )?;
                if matches!(self, Self::National { .. }) && plan.place_links.is_empty() {
                    NO_LOCAL_DETAIL_QUESTION.clone_into(&mut plan.decision_question);
                }
                Ok(plan)
            })
            .collect()
    }
}
fn place_links(
    detail: &SpatialReferenceProducts,
) -> Result<BTreeMap<String, Vec<CountyPlaceLink>>, SemanticArchiveError> {
    let names: BTreeMap<_, _> = detail
        .places()
        .iter()
        .map(|row| (row.place_geoid(), row.name_lsad()))
        .collect();
    let mut links = BTreeMap::<String, Vec<CountyPlaceLink>>::new();
    let overlaps: BTreeSet<_> = detail
        .county_place_land_areas()
        .iter()
        .map(|row| (row.county_geoid(), row.place_geoid()))
        .collect();
    for (county, place) in overlaps {
        let name = names
            .get(place)
            .ok_or(SemanticArchiveError::StoredPageMismatch)?;
        links
            .entry(county.to_owned())
            .or_default()
            .push(CountyPlaceLink::try_new(
                place.to_owned(),
                (*name).to_owned(),
            )?);
    }
    Ok(links)
}
fn identity_signal(geoid: &str, digest: &[u8; 32]) -> Result<CountySignal, SemanticArchiveError> {
    let mut signal = CountySignal::try_new("identity".into(), "County GEOID".into(), geoid.into())?;
    signal.reference = Some(ArchiveCitation::try_new(
        NATIONAL_COUNTY_SOURCE_ID.into(),
        format!(
            "national_county_reference_2024.csv.gz#county_geoid={geoid}&sha256={}",
            crate::michigan_economy::digest_hex(digest)
        ),
    )?);
    Ok(signal)
}
pub(super) fn signal_citation(
    plan: &CountyPagePlan,
    signal: &CountySignal,
    tick: u64,
) -> Result<ArchiveCitation, SemanticArchiveError> {
    if let Some(reference) = &signal.reference {
        return Ok(reference.clone());
    }
    if crate::michigan_economy::QCEW_ECONOMICS_FIELD_KEYS.contains(&signal.grant_key.as_str()) {
        return Ok(crate::archive_foundation_grants::county_qcew_citation(
            &plan.county_geoid,
        ));
    }
    ArchiveCitation::try_new(
        COMMITTED_TICK_SOURCE_ID.into(),
        format!("campaign/{tick}/{}", plan.territory_local_name),
    )
}
