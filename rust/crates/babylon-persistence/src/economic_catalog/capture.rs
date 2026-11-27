//! Source-only durable capture and deterministic importer selection.
use super::preset::NationalGraph;
use crate::national_economy::grain::NationalGenerationWitness;

use super::national::NationalSources;
use super::{
    codec, CatalogGeography, EconomicCatalogError, EconomicCatalogInput, EconomicOpening,
    EconomicProjectionView, SourceArtifact, SourceArtifactKind,
};
use crate::national_economy::county_review::{CountyReviewCapture, CountyReviewOpening};
use babylon_practice_contract::CityPdConfig;
use babylon_practice_contract::CountyReviewConfig;
use babylon_practice_contract::OrganizerConfig;
use babylon_practice_contract::OrganizerReviewConfig;

use babylon_kernel::clock::CampaignDuration;

use super::control::MichiganSources;
use crate::identity::CampaignId;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::national_economy::companies::{CompanyCapture, CompanyFinances};
use crate::national_economy::NationalGamePolicy;
use crate::national_economy::{NationalAidCapture, NationalSupportClaimant};
use crate::national_household_allocation::HouseholdBudgetKey;
use crate::national_household_refinement::NationalDetailPartition;
use crate::spatial_reference_products::SpatialReferenceProducts;
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::TradeSet;
use babylon_material_circuit::{CompanyConditionOrder, FinalDemandPrincipalId, SiteId};
use babylon_tick::h3_runtime::MichiganDynamicHexFoundation;
use std::collections::BTreeSet;
use std::fmt::Formatter;

type Result<T> = std::result::Result<T, EconomicCatalogError>;

/// Explicit campaign choice; the control preserves the organizer's public route.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NationalOpponent {
    CityPd,
    None,
}

pub(super) enum CapturedSources {
    National(Box<NationalSources>),
    Michigan(Box<MichiganSources>),
}
/// One durable source table and current compiler pin. The opening is regenerated
/// in memory; no derived per-site or global state is encoded inside the catalog.
pub struct CapturedEconomicCatalog {
    compiler: &'static str,
    pub(super) input: EconomicCatalogInput,
    pub(super) sources: CapturedSources,
    pub(super) opening: EconomicOpening,
    pub(super) bytes: Vec<u8>,
    pub(super) digest: [u8; 32],
    pub(super) local_detail: Option<MichiganDynamicHexFoundation>,
    spatial_detail: Option<SpatialReferenceProducts>,
    /// The county review's configuration with the roster it opens with, regenerated from the
    /// opening on every capture; only the configuration is encoded.
    county_review: Option<CountyReviewOpening>,
}
impl std::fmt::Debug for CapturedEconomicCatalog {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CapturedEconomicCatalog")
            .field("scenario", &self.input.scenario_id)
            .field("preset", &self.input.preset_id)
            .field("compiler", &self.compiler_version())
            .field("digest", &self.digest)
            .finish_non_exhaustive()
    }
}
impl PartialEq for CapturedEconomicCatalog {
    fn eq(&self, other: &Self) -> bool {
        self.bytes == other.bytes
    }
}
impl Eq for CapturedEconomicCatalog {}
impl CapturedEconomicCatalog {
    /// Admit all sources, regenerate once, and optionally compare supplied inputs
    /// against the complete deterministic result before accepting authority.
    /// # Errors
    /// Refuses incomplete/malformed evidence, incompatible compiler scope or a
    /// supplied opening differing from the source-derived initialization.
    pub fn capture(
        mut input: EconomicCatalogInput,
        expected: Option<&EconomicOpening>,
    ) -> Result<Self> {
        input.sources.sort_by_key(SourceArtifact::kind);
        for pair in input.sources.windows(2) {
            if pair[0].kind() == pair[1].kind() {
                return Err(EconomicCatalogError::DuplicateSource(pair[0].kind()));
            }
        }
        validate_text_sources(&input)?;
        let compiler = compiler_for(&input)?;
        let graph = NationalGraph::from_compiler(compiler);
        if graph == NationalGraph::Companies {
            super::preset::capture_company_graph(&mut input);
        }
        // Check framing and byte bounds before source expansion or generation.
        // Check and release request framing before expansion; finalize after admission.
        drop(codec::encode(&input, compiler)?);
        let local_detail = local_detail(&input)?;
        let spatial_detail = spatial_detail(&input, local_detail.as_ref())?;
        let (sources, mut opening) = match input.geography {
            CatalogGeography::NationalCounties
            | CatalogGeography::NationalCountiesWithMichiganDetail => {
                let (sources, opening) = NationalSources::admit(&input, graph)?;
                (CapturedSources::National(Box::new(sources)), opening)
            }
            CatalogGeography::MichiganControl => {
                let (sources, opening) = MichiganSources::admit(&mut input)?;
                (CapturedSources::Michigan(Box::new(sources)), opening)
            }
        };
        if let (CapturedSources::National(national), Some(config)) = (&sources, &input.organizer) {
            check_organizer(config, &input, national, &opening, (graph, compiler))?;
        }
        if let Some(config) = &input.city_pd {
            let CapturedSources::National(national) = &sources else {
                return Err(EconomicCatalogError::Identity);
            };
            if input.organizer.is_none()
                || *config
                    != crate::national_economy::city_pd::assemble(
                        config.campaign_id,
                        &input,
                        &opening,
                        &national.aid,
                    )?
            {
                return Err(EconomicCatalogError::Identity);
            }
            crate::national_economy::city_pd::add_opening(&mut opening, config)?;
        }
        let county_review = match &input.county_review {
            None => None,
            Some(config) => {
                let CapturedSources::National(national) = &sources else {
                    return Err(EconomicCatalogError::Identity);
                };
                let assembled =
                    assemble_county_review(config.campaign_id, &input, &opening, national)?;
                if assembled.config != *config {
                    return Err(EconomicCatalogError::Identity);
                }
                Some(assembled)
            }
        };
        if expected.is_some_and(|expected| *expected != opening) {
            return Err(EconomicCatalogError::Opening("supplied opening mismatch"));
        }
        let bytes = codec::encode(&input, compiler)?;
        let digest = content_digest::sha256_of(&bytes);
        Ok(Self {
            compiler,
            input,
            sources,
            opening,
            bytes,
            digest,
            local_detail,
            spatial_detail,
            county_review,
        })
    }
    /// Capture a playable national campaign with authenticated immutable organizer content.
    /// # Errors
    /// Refuses nonnational input, contradictory captured actors, unavailable actual workplace,
    /// invalid source-derived config or malformed current framing.
    pub fn capture_national_campaign(
        input: EconomicCatalogInput,
        campaign: CampaignId,
    ) -> Result<Self> {
        Self::capture_national_campaign_with_opponent(input, campaign, NationalOpponent::CityPd)
    }

    /// Capture the same public organizer route with an explicit opponent choice.
    /// # Errors
    /// Refuses a nonnational source or inconsistent authored terms.
    pub fn capture_national_campaign_with_opponent(
        input: EconomicCatalogInput,
        campaign: CampaignId,
        opponent: NationalOpponent,
    ) -> Result<Self> {
        if input.organizer.is_some() || input.city_pd.is_some() || input.county_review.is_some() {
            return Err(EconomicCatalogError::Identity);
        }
        let mut catalog = Self::capture(input, None)?;
        let CapturedSources::National(national) = &catalog.sources else {
            return Err(EconomicCatalogError::Identity);
        };
        let graph = NationalGraph::from_compiler(catalog.compiler);
        let index = catalog
            .input
            .sources
            .iter()
            .position(|row| row.kind() == SourceArtifactKind::Rules)
            .ok_or(EconomicCatalogError::Source(SourceArtifactKind::Rules))?;
        catalog.input.sources[index] = SourceArtifact::capture(
            SourceArtifactKind::Rules,
            super::preset::national_organizer_rules(graph),
        );
        let source_basis =
            content_digest::sha256_of(&codec::encode(&catalog.input, catalog.compiler)?);
        let config = crate::national_economy::organizer::assemble(
            *campaign.canonical_bytes(),
            crate::national_economy::organizer::NationalOrganizerSourceBasis(source_basis),
            &catalog.opening,
            &national.aid,
            national.support_claimant.as_ref(),
            &catalog.input,
        )?;
        catalog.input.organizer = Some(config);
        if opponent == NationalOpponent::CityPd {
            let city_pd = crate::national_economy::city_pd::assemble(
                *campaign.canonical_bytes(),
                &catalog.input,
                &catalog.opening,
                &national.aid,
            )?;
            crate::national_economy::city_pd::add_opening(&mut catalog.opening, &city_pd)?;
            catalog.input.city_pd = Some(city_pd);
            let county = assemble_county_review(
                *campaign.canonical_bytes(),
                &catalog.input,
                &catalog.opening,
                national,
            )?;
            if let Some(organizer) = &mut catalog.input.organizer {
                organizer.review = Some(organizer_review(&county.config)?);
            }
            catalog.input.county_review = Some(county.config.clone());
            catalog.county_review = Some(county);
            catalog.input.sources[index] = SourceArtifact::capture(
                SourceArtifactKind::Rules,
                super::preset::national_county_review_rules(graph),
            );
        }
        catalog.bytes = codec::encode(&catalog.input, catalog.compiler)?;
        catalog.digest = content_digest::sha256_of(&catalog.bytes);
        Ok(catalog)
    }
    /// Captured national gift bindings, regenerated only from admitted source bytes.
    #[must_use]
    pub fn national_aid_capture(&self) -> Option<&NationalAidCapture> {
        match &self.sources {
            CapturedSources::National(sources) => Some(&sources.aid),
            CapturedSources::Michigan(_) => None,
        }
    }
    /// Independently accounted Wayne support claimant, regenerated from admitted source bytes.
    #[must_use]
    pub fn national_support_claimant(&self) -> Option<&NationalSupportClaimant> {
        match &self.sources {
            CapturedSources::National(sources) => sources.support_claimant.as_ref(),
            CapturedSources::Michigan(_) => None,
        }
    }
    /// Captured opening budget for an exact household principal, where authored.
    #[must_use]
    pub fn national_household_budget(
        &self,
        principal: FinalDemandPrincipalId,
    ) -> Option<HouseholdBudgetKey> {
        match &self.sources {
            CapturedSources::National(sources) => sources.household_keys.get(&principal).copied(),
            CapturedSources::Michigan(_) => None,
        }
    }
    /// The observed wage a domestic site pays, micros an hour, under policy schema 8; the wage of a site with
    /// no employee is in no row of the opening, so the census reads it here.
    #[must_use]
    pub fn national_workplace_wage(&self, site: SiteId) -> Option<Currency> {
        match &self.sources {
            CapturedSources::National(sources) => sources.workplace_wages.get(&site).copied(),
            CapturedSources::Michigan(_) => None,
        }
    }
    /// Captured national agency terms, when this campaign includes the opponent.
    #[must_use]
    pub fn city_pd_config(&self) -> Option<&CityPdConfig> {
        self.input.city_pd.as_ref()
    }
    /// Captured county review terms, when this campaign includes the opponent's county.
    #[must_use]
    pub fn county_review_config(&self) -> Option<&CountyReviewConfig> {
        self.input.county_review.as_ref()
    }
    /// The county review's configuration and the roster it opens with.
    pub(crate) fn county_review_opening(&self) -> Option<&CountyReviewOpening> {
        self.county_review.as_ref()
    }
    /// Captured organizer terms shared by the national control and opponent.
    #[must_use]
    pub fn organizer_config(&self) -> Option<&OrganizerConfig> {
        self.input.organizer.as_ref()
    }
    /// Authored national detail partition held by the same admitted source owner.
    /// The foundation content bundle stores this catalog, so the partition survives
    /// foundation capture without regenerating the opening.
    #[must_use]
    pub fn national_detail(&self) -> Option<&NationalDetailPartition> {
        match &self.sources {
            CapturedSources::National(sources) => Some(&sources.detail),
            CapturedSources::Michigan(_) => None,
        }
    }
    /// The source-authenticated generation witness is regenerated once on admission.
    #[must_use]
    pub fn national_generation(&self) -> Option<&NationalGenerationWitness> {
        match &self.sources {
            CapturedSources::National(sources) => Some(&sources.representation),
            CapturedSources::Michigan(_) => None,
        }
    }
    /// Reopening uses only these captured bytes and the supported compiler version.
    /// # Errors
    /// Refuses changed digest, unsupported versions or noncanonical source framing.
    pub fn decode(bytes: &[u8], expected_digest: [u8; 32]) -> Result<Self> {
        if bytes.len() > codec::MAX_CATALOG_BYTES {
            return Err(EconomicCatalogError::Bound);
        }
        if content_digest::sha256_of(bytes) != expected_digest {
            return Err(EconomicCatalogError::Digest);
        }
        let (input, compiler) = codec::decode(bytes)?;
        if compiler_for(&input)? != compiler {
            return Err(EconomicCatalogError::CompilerVersion);
        }
        let catalog = Self::capture(input, None)?;
        if catalog.bytes != bytes {
            return Err(EconomicCatalogError::WireNoncanonical);
        }
        Ok(catalog)
    }
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.bytes
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
    #[must_use]
    pub const fn compiler_version(&self) -> &'static str {
        self.compiler
    }
    /// Whole-site company membership fixed by a company-enabled national foundation.
    #[must_use]
    pub fn national_companies(&self) -> Option<&CompanyCapture> {
        match &self.sources {
            CapturedSources::National(sources) => sources.companies.as_ref(),
            CapturedSources::Michigan(_) => None,
        }
    }
    /// Immutable treasury transfers and ultimate claims rebuilt from authenticated opening sources.
    #[must_use]
    pub fn national_company_finances(&self) -> Option<&CompanyFinances> {
        match &self.sources {
            CapturedSources::National(sources) => sources.finances.as_ref(),
            CapturedSources::Michigan(_) => None,
        }
    }
    #[must_use]
    pub const fn opening(&self) -> &EconomicOpening {
        &self.opening
    }
    #[must_use]
    pub fn view(&self) -> EconomicProjectionView<'_> {
        EconomicProjectionView {
            scenario_id: &self.input.scenario_id,
            preset_id: &self.input.preset_id,
            duration: self.input.duration,
            source_digest: self.digest,
            opening: &self.opening,
            sources: match &self.sources {
                CapturedSources::National(s) => s.view(),
                CapturedSources::Michigan(s) => s.view(),
            },
        }
    }
    pub(crate) fn spatial_detail(&self) -> Option<&SpatialReferenceProducts> {
        self.spatial_detail.as_ref()
    }
    pub(crate) fn has_organizer(&self) -> bool {
        self.input.organizer.is_some()
    }
    #[must_use]
    pub fn source(&self, kind: SourceArtifactKind) -> Option<&[u8]> {
        self.input
            .sources
            .binary_search_by_key(&kind, SourceArtifact::kind)
            .ok()
            .map(|i| self.input.sources[i].bytes())
    }
}
/// The captured organizer must be exactly the one the sources and the county review derive.
fn check_organizer(
    config: &OrganizerConfig,
    input: &EconomicCatalogInput,
    national: &NationalSources,
    opening: &EconomicOpening,
    (graph, compiler): (NationalGraph, &str),
) -> Result<()> {
    let mut source_only = input.clone();
    source_only.organizer = None;
    source_only.city_pd = None;
    source_only.county_review = None;
    let rules = source_only
        .sources
        .iter_mut()
        .find(|row| row.kind() == SourceArtifactKind::Rules)
        .ok_or(EconomicCatalogError::Source(SourceArtifactKind::Rules))?;
    *rules = SourceArtifact::capture(
        SourceArtifactKind::Rules,
        super::preset::national_organizer_rules(graph),
    );
    let source_basis = content_digest::sha256_of(&codec::encode(&source_only, compiler)?);
    let expected_config = crate::national_economy::organizer::assemble(
        config.campaign_id,
        crate::national_economy::organizer::NationalOrganizerSourceBasis(source_basis),
        opening,
        &national.aid,
        national.support_claimant.as_ref(),
        input,
    )?;
    let expected_config = OrganizerConfig {
        review: input
            .county_review
            .as_ref()
            .map(organizer_review)
            .transpose()?,
        ..expected_config
    };
    if *config == expected_config {
        Ok(())
    } else {
        Err(EconomicCatalogError::Identity)
    }
}

/// What the organizer's configuration holds of the county review: the county, the first session
/// and the identity of the county's configuration.
fn organizer_review(config: &CountyReviewConfig) -> Result<OrganizerReviewConfig> {
    Ok(OrganizerReviewConfig {
        county_geoid: std::str::from_utf8(&config.county)
            .map_err(|_| EconomicCatalogError::Identity)?
            .to_owned(),
        first_session_period: config.first_session_period,
        county_config_digest: babylon_practice_contract::county_review_config_digest(config)
            .map_err(|_| EconomicCatalogError::Identity)?,
    })
}

/// Assembles the county review from the captured policy, the hearing and the opening the
/// campaign's national sources produced.
fn assemble_county_review(
    campaign: [u8; 16],
    input: &EconomicCatalogInput,
    opening: &EconomicOpening,
    national: &NationalSources,
) -> Result<CountyReviewOpening> {
    let policy = NationalGamePolicy::from_captured_bytes(source(
        input,
        SourceArtifactKind::NationalGamePolicy,
    )?)
    .map_err(|_| EconomicCatalogError::Source(SourceArtifactKind::NationalGamePolicy))?;
    let hearing = input
        .organizer
        .as_ref()
        .and_then(|organizer| organizer.hearing.as_ref())
        .ok_or(EconomicCatalogError::Identity)?;
    let claimant = national
        .support_claimant
        .as_ref()
        .ok_or(EconomicCatalogError::Identity)?;
    let county = crate::national_economy::county_review::assemble(
        campaign,
        &CountyReviewCapture {
            opening,
            policy: &policy,
            aid: &national.aid,
            claimant,
            household_keys: &national.household_keys,
            hearing,
            pay: national.pay(),
        },
    )?;
    let city_pd = input
        .city_pd
        .as_ref()
        .ok_or(EconomicCatalogError::Identity)?;
    crate::national_economy::county_review::check_payroll_site(&county.config, city_pd)?;
    Ok(county)
}

fn compiler_for(input: &EconomicCatalogInput) -> Result<&'static str> {
    input
        .duration
        .validate()
        .map_err(|_| EconomicCatalogError::Identity)?;
    match input.geography {
        CatalogGeography::NationalCounties
        | CatalogGeography::NationalCountiesWithMichiganDetail
            if input.scenario_id == crate::national_economy::NATIONAL_SCENARIO_ID
                && input.duration == CampaignDuration::Continuous =>
        {
            let kind = SourceArtifactKind::NationalGamePolicy;
            let policy = NationalGamePolicy::from_captured_bytes(source(input, kind)?)
                .map_err(|_| EconomicCatalogError::Source(kind))?;
            match (input.preset_id.as_str(), policy.companies) {
                ("national-world", None) => Ok("national-world-v7"),
                ("national-world", Some(terms))
                    if terms.experiment.is_none() && policy.trades == TradeSet::Twelve =>
                {
                    Ok("national-world-v13")
                }
                ("national-world", Some(terms)) if terms.experiment.is_none() => {
                    Ok(match terms.portfolio.condition_order {
                        CompanyConditionOrder::FirstApplicable if policy.city_pd.is_some() => {
                            "national-world-v12"
                        }
                        CompanyConditionOrder::FirstApplicable
                            if policy.household_support_claimant.is_some() =>
                        {
                            "national-world-v11"
                        }
                        CompanyConditionOrder::HighDemandBeforeSpare => "national-world-v8",
                        CompanyConditionOrder::FirstApplicable
                            if policy.household_lifecycle.is_some() =>
                        {
                            "national-world-v10"
                        }
                        CompanyConditionOrder::FirstApplicable => "national-world-v9",
                    })
                }
                ("national-company-scale-experiment", Some(terms))
                    if terms.experiment.is_some() && policy.trades == TradeSet::Twelve =>
                {
                    Err(EconomicCatalogError::ExperimentOnTwelveTrades)
                }
                ("national-company-scale-experiment", Some(terms))
                    if terms.experiment.is_some()
                        && input.geography == CatalogGeography::NationalCounties
                        && input.organizer.is_none()
                        && input.city_pd.is_none()
                        && input.county_review.is_none() =>
                {
                    Ok(match terms.portfolio.condition_order {
                        CompanyConditionOrder::FirstApplicable
                            if policy.household_support_claimant.is_some() =>
                        {
                            "national-company-scale-v4"
                        }
                        CompanyConditionOrder::HighDemandBeforeSpare => "national-company-scale-v1",
                        CompanyConditionOrder::FirstApplicable
                            if policy.household_lifecycle.is_some() =>
                        {
                            "national-company-scale-v3"
                        }
                        CompanyConditionOrder::FirstApplicable => "national-company-scale-v2",
                    })
                }
                _ => Err(EconomicCatalogError::Identity),
            }
        }
        CatalogGeography::MichiganControl
            if input.scenario_id == crate::michigan_cohorts::MICHIGAN_COHORT_SCENARIO =>
        {
            Ok("michigan-control-v2")
        }
        _ => Err(EconomicCatalogError::Identity),
    }
}
pub(super) fn source(input: &EconomicCatalogInput, kind: SourceArtifactKind) -> Result<&[u8]> {
    input
        .sources
        .iter()
        .find(|row| row.kind() == kind)
        .map(SourceArtifact::bytes)
        .ok_or(EconomicCatalogError::Source(kind))
}
pub(super) fn source_coverage(
    input: &EconomicCatalogInput,
    required: &[SourceArtifactKind],
    optional: &[SourceArtifactKind],
) -> Result<()> {
    let found: BTreeSet<_> = input.sources.iter().map(SourceArtifact::kind).collect();
    for kind in required {
        if !found.contains(kind) {
            return Err(EconomicCatalogError::Source(*kind));
        }
    }
    for kind in found {
        if !required.contains(&kind) && !optional.contains(&kind) {
            return Err(EconomicCatalogError::UnexpectedSource(kind));
        }
    }
    Ok(())
}
fn local_detail(input: &EconomicCatalogInput) -> Result<Option<MichiganDynamicHexFoundation>> {
    let bytes = input
        .sources
        .iter()
        .find(|s| s.kind() == SourceArtifactKind::MichiganDynamicHexes);
    match (input.geography, bytes) {
        (CatalogGeography::NationalCounties, None) => Ok(None),
        (
            CatalogGeography::MichiganControl
            | CatalogGeography::NationalCountiesWithMichiganDetail,
            Some(bytes),
        ) => crate::decode_michigan_dynamic_hex_foundation(bytes.bytes())
            .map(Some)
            .map_err(|_| EconomicCatalogError::Source(SourceArtifactKind::MichiganDynamicHexes)),
        _ => Err(EconomicCatalogError::Source(
            SourceArtifactKind::MichiganDynamicHexes,
        )),
    }
}

fn spatial_detail(
    input: &EconomicCatalogInput,
    local: Option<&MichiganDynamicHexFoundation>,
) -> Result<Option<SpatialReferenceProducts>> {
    let kind = SourceArtifactKind::MichiganSpatialProducts;
    let bytes = input.sources.iter().find(|row| row.kind() == kind);
    match (local, bytes) {
        (None, None) => Ok(None),
        (Some(local), Some(bytes)) => {
            SpatialReferenceProducts::decode_captured(bytes.bytes(), local)
                .map(Some)
                .map_err(|_| EconomicCatalogError::Source(kind))
        }
        _ => Err(EconomicCatalogError::Source(kind)),
    }
}

fn validate_text_sources(input: &EconomicCatalogInput) -> Result<()> {
    for kind in [
        SourceArtifactKind::GraphDeclarations,
        SourceArtifactKind::Rules,
        SourceArtifactKind::PreludeDeclarations,
    ] {
        if let Some(row) = input.sources.iter().find(|row| row.kind() == kind) {
            if row.bytes().len() > 1_048_576
                || row.bytes().contains(&0)
                || std::str::from_utf8(row.bytes()).is_err()
            {
                return Err(EconomicCatalogError::Source(kind));
            }
        }
    }
    Ok(())
}

impl CapturedEconomicCatalog {
    /// Capture a freshly authored Michigan control and its explicit local detail.
    /// Reuse local detail already captured by a decoded control. Subsequent
    /// decoding uses these bytes, never the current fixture accessor.
    /// # Errors
    /// Refuses missing original source inputs or any change during regeneration.
    pub fn from_michigan(catalog: &MichiganMaterialCatalog) -> Result<Self> {
        let mut sources = catalog.captured_sources().to_vec();
        if !sources
            .iter()
            .any(|source| source.kind() == SourceArtifactKind::MichiganDynamicHexes)
        {
            sources.push(SourceArtifact::capture(
                SourceArtifactKind::MichiganDynamicHexes,
                crate::michigan_dynamic_hex_foundation_fixture_parts().concat(),
            ));
        }
        if !sources
            .iter()
            .any(|source| source.kind() == SourceArtifactKind::MichiganSpatialProducts)
        {
            sources.push(SourceArtifact::capture(
                SourceArtifactKind::MichiganSpatialProducts,
                crate::spatial_reference_products::fixture_bytes().to_vec(),
            ));
        }
        let input = EconomicCatalogInput {
            scenario_id: crate::michigan_cohorts::MICHIGAN_COHORT_SCENARIO.to_owned(),
            preset_id: catalog
                .experiment()
                .map_or(catalog.preset().id(), |spec| spec.profile.foundation_id())
                .to_owned(),
            duration: catalog.duration(),
            sources,
            geography: CatalogGeography::MichiganControl,
            organizer: catalog.organizer_config().cloned(),
            city_pd: None,
            county_review: None,
        };
        Self::capture(
            input,
            Some(&super::michigan::import_michigan_opening(catalog)?),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::michigan_material::MichiganMaterialCatalog;

    #[test]
    fn missing_or_changed_captured_detail_cannot_reload_the_embedded_fixture() {
        let control = MichiganMaterialCatalog::from_defines_toml(include_str!(
            "../../../../../content/scenarios/michigan/defines.toml"
        ))
        .expect("the authored input admits the derived value");
        let captured = CapturedEconomicCatalog::from_michigan(&control)
            .expect("the Michigan fixture content loads");
        let mut missing = captured.input.clone();
        missing
            .sources
            .retain(|row| row.kind() != SourceArtifactKind::MichiganSpatialProducts);
        assert!(matches!(
            CapturedEconomicCatalog::capture(missing, None),
            Err(EconomicCatalogError::Source(
                SourceArtifactKind::MichiganSpatialProducts
            ))
        ));
        let mut changed = captured.input;
        let source = changed
            .sources
            .iter_mut()
            .find(|row| row.kind() == SourceArtifactKind::MichiganSpatialProducts)
            .expect("the fixture holds the searched element");
        let mut bytes = source.bytes().to_vec();
        bytes[52] ^= 1;
        *source = SourceArtifact::capture(SourceArtifactKind::MichiganSpatialProducts, bytes);
        assert!(matches!(
            CapturedEconomicCatalog::capture(changed, None),
            Err(EconomicCatalogError::Source(
                SourceArtifactKind::MichiganSpatialProducts
            ))
        ));
    }
    fn previous_compiler_refuses(catalog: &CapturedEconomicCatalog, compiler: &str) {
        let previous =
            codec::encode(&catalog.input, compiler).expect("the fixture value encodes canonically");
        // Genuine prior compiler framing and an exact recomputed digest: refusal
        // must come from supported authority, not damaged or unauthenticated bytes.
        assert_eq!(
            CapturedEconomicCatalog::decode(&previous, content_digest::sha256_of(&previous)),
            Err(EconomicCatalogError::CompilerVersion)
        );
    }
    #[test]
    fn the_fixture_compiles_as_v13_and_the_shipped_input_as_v12() {
        let fixture = super::super::preset::national_catalog_input_for(include_bytes!(
            "../../tests/fixtures/national_twelve_trades.defines.toml"
        ))
        .expect("the fixture parses");
        assert_eq!(compiler_for(&fixture), Ok("national-world-v13"));
        assert_eq!(
            compiler_for(&super::super::preset::national_catalog_input()),
            Ok("national-world-v12")
        );
    }
    #[test]
    fn previous_national_world_compiler_is_refused() {
        let catalog =
            CapturedEconomicCatalog::capture(super::super::preset::national_catalog_input(), None)
                .expect("the fixture captures the authored state");
        previous_compiler_refuses(&catalog, "national-world-v6");
    }
    #[test]
    fn national_catalog_retains_the_authored_detail_partition() {
        let catalog =
            CapturedEconomicCatalog::capture(super::super::preset::national_catalog_input(), None)
                .expect("the national preset captures its admitted opening");
        let detail = catalog
            .national_detail()
            .expect("the national source owner retains the authored partition");
        assert_ne!(detail.background_households().len(), 0);
        assert_ne!(detail.background_workplaces().len(), 0);
        assert_ne!(detail.foreground().household_principals().len(), 0);
        assert_eq!(
            detail.background_households().len() + detail.foreground().household_principals().len(),
            catalog.opening().households.len(),
            "foundation capture keeps the same conserved partition the opening published"
        );
        let background = detail.background_households();
        assert!(background
            .iter()
            .any(|row| row.key.budget == HouseholdBudgetKey::PooledExternal));
        for row in background {
            assert_eq!(
                catalog.national_household_budget(row.key.principal),
                Some(row.key.budget)
            );
        }
        let claimant = catalog
            .national_support_claimant()
            .expect("independent Wayne claimant");
        assert_eq!(
            catalog.national_household_budget(claimant.principal),
            Some(HouseholdBudgetKey::NoEarnerNonowner)
        );
        assert!(detail
            .foreground()
            .household_principals()
            .contains(&claimant.principal));
        assert_eq!(
            claimant.source_hash,
            content_digest::sha256_of(
                source(&catalog.input, SourceArtifactKind::NationalGamePolicy)
                    .expect("exact current national policy")
            )
        );
        for child in &catalog
            .national_aid_capture()
            .expect("captured aid cohorts")
            .children
        {
            assert_eq!(
                catalog.national_household_budget(child.principal),
                Some(child.budget)
            );
            assert_eq!(
                catalog.national_household_budget(child.parent),
                Some(child.budget)
            );
        }
    }
    #[test]
    fn previous_michigan_control_v1_compiler_is_refused() {
        let control = MichiganMaterialCatalog::from_defines_toml(include_str!(
            "../../../../../content/scenarios/michigan/defines.toml"
        ))
        .expect("the authored input admits the derived value");
        let catalog = CapturedEconomicCatalog::from_michigan(&control)
            .expect("the Michigan fixture content loads");
        previous_compiler_refuses(&catalog, "michigan-control-v1");
    }
}
