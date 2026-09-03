//! PER-22 county dossier producer (slice 2) for the semantic Archive worker.
//!
//! [`CountyDossierProducerV1`] turns one committed dirty receipt into a
//! bounded batch of county dossier pages. Counties enumerate from the
//! campaign's declared `babylon_meta.territory_county_map_v1` rows in GEOID
//! order; titles, place links, and place labels resolve from the checked,
//! digest-pinned Michigan spatial reference products, so the receipt batch
//! hash folds the exact pinned artifact bytes in through the page content.
//!
//! # Page semantics
//!
//! Each page carries the governed census county name as its title, the
//! established county decision question, one grant-keyed signal per committed
//! per-tick territory field that exists at the receipt's resolve tick —
//! `territory/median-wage` and `territory/phi-hour` (Director ruling D2:
//! absence-maximal; every other county field projects absent) — and one link
//! per place overlapping the county. A committed field that is missing at the
//! resolve tick emits no signal, never a fabricated value. Signal values are
//! pre-formatted with the Python statblock's `%.6f` discipline and each
//! citation pins the committed provenance (`committed-tick-v1` at
//! `campaign/{resolve_tick}/{territory local name}`). Unknown place subjects
//! stay redlinks because the renderer hides labels for subjects no knowledge
//! grant covers.
//!
//! # Dirty detection
//!
//! A county is dirty when no stored page exists for it or when its semantic
//! projection — `(county_geoid, title, decision question, sorted signal
//! values, sorted link target ids)` — differs from the stored page's
//! projection. Receipt-stamped fields (`verified_tick`, `tick_content_hash`),
//! citation stamps, and grant-dependent label visibility never dirty a page:
//! the projection is recomputed from the stored Markdown with the pinned
//! `archive_page_v1.md.j2` shape. Malformed stored pages are treated as dirty,
//! which safely republishes drifted content.

use std::collections::{BTreeMap, BTreeSet};

use babylon_graph::stable_element::StableElementKeyV1;
use babylon_kernel::tick_content_hash::RefDigestV1;
use postgres::{Config, NoTls};
use sha2::{Digest as _, Sha256};
use uuid::Uuid;

use crate::archive::{database, decode, validate_text};
use crate::{
    michigan_spatial_reference_products_v1, representative_h3_reference_cohort_v1,
    ArchiveCitationV1, ArchiveDirtyBatchV1, ArchiveDossierProducerV1, ArchiveLinkV1,
    ArchivePageInputV1, ArchivePageRefV1, ArchiveSignalV1, ArchiveSubjectKindV1, ArchiveSubjectV1,
    CampaignId, PendingArchiveReceiptV1, SemanticArchiveErrorV1, SpatialReferenceProducts,
};

/// Stable decision question every county dossier page answers.
pub const COUNTY_DECISION_QUESTION_V1: &str =
    "Which neighboring place should organizers investigate next?";

/// Knowledge-grant key addressing the committed median-wage signal.
pub const COUNTY_MEDIAN_WAGE_GRANT_KEY_V1: &str = "median-wage";

/// Knowledge-grant key addressing the committed phi-hour signal.
pub const COUNTY_PHI_HOUR_GRANT_KEY_V1: &str = "phi-hour";

/// Player-facing label of the committed median-wage signal.
pub const COUNTY_MEDIAN_WAGE_LABEL_V1: &str = "Median wage";

/// Player-facing label of the committed phi-hour signal.
pub const COUNTY_PHI_HOUR_LABEL_V1: &str = "Imperial rent Φ";

/// Source identity pinning committed per-tick territory provenance.
pub const COMMITTED_TICK_SOURCE_ID_V1: &str = "committed-tick-v1";

/// Read-only declared county enumeration used by the county dossier.
pub const ARCHIVE_COUNTY_MAP_READ_SQL_V1: &str = "SELECT territory_local_name, county_geoid \
FROM babylon_meta.territory_county_map_v1 \
WHERE campaign_id = $1::uuid ORDER BY county_geoid, territory_local_name";

/// Read-only committed per-tick territory fields used by the county dossier.
///
/// Only the two D2-committed territory fields are selected; every row comes
/// from the committed tick the receipt names, never from material ledgers or
/// `MAX(tick)` shortcuts.
pub const ARCHIVE_COUNTY_FIELD_READ_SQL_V1: &str = "SELECT \
    t.territory_id, f.field_name, f.value_tag, f.real_bits \
    FROM babylon_state.territory_state_v1 t \
    JOIN babylon_state.territory_state_field_v1 f \
      ON f.campaign_id = t.campaign_id \
     AND f.resolve_tick = t.resolve_tick \
     AND f.territory_id = t.territory_id \
    WHERE t.campaign_id = $1::uuid AND t.resolve_tick = $2 \
      AND f.field_name IN ('territory/median-wage', 'territory/phi-hour') \
    ORDER BY t.territory_id, f.position";

/// Read-only stored county-page projection used by the dirty diff.
///
/// The query returns the exact stored page rows for one campaign, ordered by
/// subject, and never joins material or raw event ledgers.
pub const ARCHIVE_COUNTY_PAGE_READ_SQL_V1: &str = "SELECT subject_id, title, markdown \
FROM babylon_meta.archive_page_v1 \
WHERE campaign_id = $1::uuid AND subject_kind = 'county' \
ORDER BY subject_id";

/// Contract-pinned SHA-256 of the `dim_county` identity artifact that backs
/// the governed county names.
pub const PINNED_COUNTY_IDENTITY_ARTIFACT_SHA256_V1: [u8; 32] = [
    0x13, 0x0b, 0x76, 0x79, 0xd0, 0x44, 0x1d, 0x5c, 0x3c, 0x21, 0x83, 0xa2, 0xbe, 0xf8, 0x58, 0x07,
    0x3d, 0x30, 0x11, 0x03, 0x95, 0x50, 0xbf, 0xbf, 0x01, 0x5b, 0x38, 0x05, 0x66, 0xc7, 0x20, 0x32,
];

/// Contract-pinned SHA-256 of `census_place_identity_mi_2023.csv.gz`
/// (`contracts/census_place_authority_v1.yaml`), the place-label authority.
pub const PINNED_PLACE_IDENTITY_ARTIFACT_SHA256_V1: [u8; 32] = [
    0xcb, 0x86, 0x4b, 0x4f, 0x6f, 0x43, 0x90, 0x2b, 0xb8, 0x21, 0xe8, 0x4f, 0xe9, 0xa4, 0x05, 0x5a,
    0x90, 0x39, 0xe0, 0xa7, 0x4d, 0x8b, 0x83, 0x99, 0xf2, 0x09, 0xae, 0x6e, 0xd2, 0x6a, 0x8b, 0xe7,
];

/// Contract-pinned SHA-256 of
/// `census_county_place_h3_land_overlap_mi_2023.parquet`
/// (`contracts/county_place_h3_overlap_v1.yaml`), the place-link authority.
pub const PINNED_COUNTY_PLACE_OVERLAP_ARTIFACT_SHA256_V1: [u8; 32] = [
    0xfc, 0xb7, 0xba, 0xaf, 0x63, 0xa5, 0x42, 0x2a, 0xcc, 0xce, 0x87, 0x09, 0x99, 0x7d, 0xe8, 0xe4,
    0x09, 0x93, 0x6f, 0x71, 0x31, 0xfa, 0x0e, 0xf6, 0xb0, 0xa2, 0x87, 0x62, 0xfd, 0xfe, 0xe4, 0x2f,
];

const COUNTY_SEMANTIC_DOMAIN_V1: &[u8] = b"babylon.county-page-semantic.v1\0";
const COUNTY_IDENTITY_PRODUCT_CODE_V1: &str = "dim_county";
const PLACE_IDENTITY_PRODUCT_CODE_V1: &str = "census_place_identity_mi_2023";
const OVERLAP_PRODUCT_CODE_V1: &str = "census_county_place_h3_land_overlap_mi_2023";
const MEDIAN_WAGE_FIELD_V1: &str = "territory/median-wage";
const PHI_HOUR_FIELD_V1: &str = "territory/phi-hour";
const REAL_VALUE_TAG_V1: i16 = 3;

/// Format one committed real with the Python statblock's `%.6f` discipline.
///
/// # Errors
/// Refuses a non-finite value; committed values are canonical finite binary64
/// and any other input is a malformed committed state, never a display value.
pub fn format_county_statblock_value_v1(value: f64) -> Result<String, SemanticArchiveErrorV1> {
    if !value.is_finite() {
        return Err(SemanticArchiveErrorV1::InvalidText);
    }
    Ok(format!("{value:.6}"))
}

/// One grant-keyed county signal with its pre-formatted statblock value.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountySignalV1 {
    grant_key: String,
    label: String,
    value: String,
}

impl CountySignalV1 {
    /// Construct one bounded county signal.
    ///
    /// # Errors
    /// Refuses an unsafe grant key, label, or value.
    pub fn try_new(
        grant_key: String,
        label: String,
        value: String,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        crate::archive::validate_key(&grant_key)?;
        validate_text(&label)?;
        validate_text(&value)?;
        Ok(Self {
            grant_key,
            label,
            value,
        })
    }

    /// Construct one committed-real signal with `%.6f` formatting.
    ///
    /// # Errors
    /// Refuses a non-finite committed value or unsafe text.
    pub fn from_committed_real(
        grant_key: String,
        label: String,
        value: f64,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        Self::try_new(grant_key, label, format_county_statblock_value_v1(value)?)
    }

    /// Borrow the knowledge-grant address key.
    #[must_use]
    pub fn grant_key(&self) -> &str {
        &self.grant_key
    }

    /// Borrow the player-facing signal label.
    #[must_use]
    pub fn label(&self) -> &str {
        &self.label
    }

    /// Borrow the pre-formatted player-facing value.
    #[must_use]
    pub fn value(&self) -> &str {
        &self.value
    }
}

/// One overlapping place link of a county dossier page.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyPlaceLinkV1 {
    place_geoid: String,
    place_name: String,
}

impl CountyPlaceLinkV1 {
    /// Construct one place link with its governed census place label.
    ///
    /// # Errors
    /// Refuses a malformed place GEOID or unsafe place label.
    pub fn try_new(
        place_geoid: String,
        place_name: String,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, place_geoid.clone())?;
        validate_text(&place_name)?;
        Ok(Self {
            place_geoid,
            place_name,
        })
    }

    /// Borrow the seven-digit place GEOID.
    #[must_use]
    pub fn place_geoid(&self) -> &str {
        &self.place_geoid
    }

    /// Borrow the governed census place label.
    #[must_use]
    pub fn place_name(&self) -> &str {
        &self.place_name
    }
}

/// One desired county dossier page resolved from the declared mapping, the
/// committed per-tick territory fields, and the pinned products.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyPagePlanV1 {
    county_geoid: String,
    territory_local_name: String,
    title: String,
    signals: Vec<CountySignalV1>,
    place_links: Vec<CountyPlaceLinkV1>,
}

impl CountyPagePlanV1 {
    /// Construct one desired county page plan.
    ///
    /// # Errors
    /// Refuses a malformed county GEOID, unsafe text, or duplicate signal
    /// keys or link targets. Signals are stored sorted by grant key and links
    /// sorted by place GEOID.
    pub fn try_new(
        county_geoid: String,
        territory_local_name: String,
        title: String,
        signals: Vec<CountySignalV1>,
        place_links: Vec<CountyPlaceLinkV1>,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        ArchiveSubjectV1::try_new(
            ArchiveSubjectKindV1::County,
            county_geoid.clone(),
            title.clone(),
        )?;
        validate_text(&territory_local_name)?;
        let mut signals = signals;
        signals.sort_by(|left, right| left.grant_key.cmp(&right.grant_key));
        if signals
            .windows(2)
            .any(|pair| pair[0].grant_key == pair[1].grant_key)
        {
            return Err(SemanticArchiveErrorV1::DuplicateKey);
        }
        let mut place_links = place_links;
        place_links.sort_by(|left, right| left.place_geoid.cmp(&right.place_geoid));
        if place_links
            .windows(2)
            .any(|pair| pair[0].place_geoid == pair[1].place_geoid)
        {
            return Err(SemanticArchiveErrorV1::DuplicateKey);
        }
        Ok(Self {
            county_geoid,
            territory_local_name,
            title,
            signals,
            place_links,
        })
    }

    /// Borrow the five-digit county GEOID.
    #[must_use]
    pub fn county_geoid(&self) -> &str {
        &self.county_geoid
    }

    /// Borrow the scenario-local territory name the mapping declares.
    #[must_use]
    pub fn territory_local_name(&self) -> &str {
        &self.territory_local_name
    }

    /// Borrow the governed census county title.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Borrow the sorted grant-keyed signals.
    #[must_use]
    pub fn signals(&self) -> &[CountySignalV1] {
        &self.signals
    }

    /// Borrow the sorted overlapping place links.
    #[must_use]
    pub fn place_links(&self) -> &[CountyPlaceLinkV1] {
        &self.place_links
    }

    fn semantic_sha256(&self) -> [u8; 32] {
        county_page_semantic_sha256_v1(
            &self.county_geoid,
            &self.title,
            COUNTY_DECISION_QUESTION_V1,
            &self
                .signals
                .iter()
                .map(|signal| (signal.label.clone(), signal.value.clone()))
                .collect::<Vec<_>>(),
            &self
                .place_links
                .iter()
                .map(|link| link.place_geoid.clone())
                .collect::<Vec<_>>(),
        )
    }
}

/// Receipt-stamp-free semantic projection of one stored county page.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StoredCountyPageV1 {
    title: String,
    question: String,
    signals: Vec<(String, String)>,
    place_geoids: Vec<String>,
}

impl StoredCountyPageV1 {
    /// Construct one stored-page projection.
    ///
    /// # Errors
    /// Refuses unsafe text, a malformed place GEOID, or duplicate signals or
    /// links. Signals are stored sorted by label and links sorted by GEOID.
    pub fn try_new(
        title: String,
        question: String,
        signals: Vec<(String, String)>,
        place_geoids: Vec<String>,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        validate_text(&title)?;
        validate_text(&question)?;
        let mut signals = signals;
        signals.sort();
        if signals.windows(2).any(|pair| pair[0].0 == pair[1].0) {
            return Err(SemanticArchiveErrorV1::DuplicateKey);
        }
        for (label, value) in &signals {
            validate_text(label)?;
            validate_text(value)?;
        }
        let mut place_geoids = place_geoids;
        place_geoids.sort();
        let mut unique = BTreeSet::new();
        for geoid in &place_geoids {
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, geoid.clone())?;
            if !unique.insert(geoid.clone()) {
                return Err(SemanticArchiveErrorV1::DuplicateKey);
            }
        }
        Ok(Self {
            title,
            question,
            signals,
            place_geoids,
        })
    }

    /// Borrow the stored page title.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Borrow the stored decision question.
    #[must_use]
    pub fn question(&self) -> &str {
        &self.question
    }

    /// Borrow the sorted stored signal label/value pairs.
    #[must_use]
    pub fn signals(&self) -> &[(String, String)] {
        &self.signals
    }

    /// Borrow the sorted overlapping place GEOIDs.
    #[must_use]
    pub fn place_geoids(&self) -> &[String] {
        &self.place_geoids
    }

    /// Hash the exact receipt-stamp-free projection for one county subject.
    #[must_use]
    pub fn semantic_sha256(&self, county_geoid: &str) -> [u8; 32] {
        county_page_semantic_sha256_v1(
            county_geoid,
            &self.title,
            &self.question,
            &self.signals,
            &self.place_geoids,
        )
    }
}

/// Hash the exact receipt-stamp-free county page projection.
///
/// The projection covers the county GEOID, title, decision question, sorted
/// signal label/value pairs, and sorted place-link target ids.
/// `verified_tick` and `tick_content_hash` deliberately never enter the hash,
/// so a later receipt alone never re-publishes an unchanged page.
#[must_use]
pub fn county_page_semantic_sha256_v1(
    county_geoid: &str,
    title: &str,
    question: &str,
    signals: &[(String, String)],
    place_geoids: &[String],
) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(COUNTY_SEMANTIC_DOMAIN_V1);
    hash_text(&mut hasher, county_geoid);
    hash_text(&mut hasher, title);
    hash_text(&mut hasher, question);
    let sorted_signals = signals.iter().collect::<BTreeSet<_>>();
    hash_len(&mut hasher, sorted_signals.len());
    for (label, value) in sorted_signals {
        hash_text(&mut hasher, label);
        hash_text(&mut hasher, value);
    }
    let sorted_geoids = place_geoids.iter().collect::<BTreeSet<_>>();
    hash_len(&mut hasher, sorted_geoids.len());
    for geoid in sorted_geoids {
        hash_text(&mut hasher, geoid);
    }
    hasher.finalize().into()
}

/// Parse the semantic projection out of one stored rendered county page.
///
/// The parser is coupled to the pinned `archive_page_v1.md.j2` template
/// ([`crate::ARCHIVE_PAGE_TEMPLATE_SHA256_V1`]) and returns `None` for any
/// stored page whose frontmatter subject, title, question, signal, or
/// related-link shape drifted; callers treat `None` as dirty.
#[must_use]
pub fn parse_stored_county_page_v1(
    county_geoid: &str,
    title: &str,
    markdown: &str,
) -> Option<StoredCountyPageV1> {
    let mut lines = markdown.lines();
    if lines.next()? != "---" {
        return None;
    }
    let mut subject_exact = false;
    for line in lines.by_ref() {
        if line == "---" {
            break;
        }
        if let Some(value) = line.strip_prefix("subject: ") {
            subject_exact = value == format!("county/{county_geoid}");
        }
    }
    if !subject_exact {
        return None;
    }
    let stored_title = lines.next()?.strip_prefix("# ")?.to_owned();
    if stored_title != title {
        return None;
    }
    let mut question = None;
    let mut signals = Vec::new();
    let mut place_geoids = Vec::new();
    let mut section: Option<&str> = None;
    for line in lines {
        if let Some(rest) = line.strip_prefix("## ") {
            section = Some(rest);
            continue;
        }
        match section {
            Some("Signals") => {
                let entry = line.strip_prefix("- **")?;
                let (label, rest) = entry.split_once(":** ")?;
                let (value, _citation) = rest.split_once(" — ")?;
                if label.contains("**") {
                    return None;
                }
                signals.push((label.to_owned(), value.to_owned()));
            }
            Some("Related") => {
                let entry = line.strip_prefix("- [[")?;
                let inner = entry.strip_suffix("]]")?;
                let key = inner.split('|').next()?;
                let place = key.strip_prefix("place/")?;
                if place.len() != 7 || !place.bytes().all(|byte| byte.is_ascii_digit()) {
                    return None;
                }
                place_geoids.push(place.to_owned());
            }
            _ => {
                if line.is_empty() || line.starts_with("# ") || line.starts_with("- ") {
                    continue;
                }
                if question.is_some() {
                    return None;
                }
                question = Some(line.to_owned());
            }
        }
    }
    StoredCountyPageV1::try_new(stored_title, question?, signals, place_geoids).ok()
}

/// Select the dirty desired pages, sorted by county GEOID, bounded by `limit`.
///
/// A desired page is dirty when no stored projection exists for its subject
/// or when the stored projection hash differs. The bound drains at most
/// `limit` counties per receipt; the remainder waits for a later receipt.
#[must_use]
pub fn select_dirty_county_pages_v1<'a>(
    desired: &'a [CountyPagePlanV1],
    stored: &BTreeMap<String, StoredCountyPageV1>,
    limit: usize,
) -> Vec<&'a CountyPagePlanV1> {
    desired
        .iter()
        .filter(|plan| {
            stored.get(plan.county_geoid()).is_none_or(|page| {
                page.semantic_sha256(plan.county_geoid()) != plan.semantic_sha256()
            })
        })
        .take(limit)
        .collect()
}

/// Build the exact receipt-bound page input for one desired county page.
///
/// Each signal citation pins the committed tick provenance; the territory
/// local name is never rendered, only the campaign, tick, and source field.
///
/// # Errors
/// Refuses any unsafe page component.
pub fn county_page_input_v1(
    plan: &CountyPagePlanV1,
    resolve_tick: u64,
    tick_content_hash: [u8; 32],
) -> Result<ArchivePageInputV1, SemanticArchiveErrorV1> {
    let subject = ArchiveSubjectV1::try_new(
        ArchiveSubjectKindV1::County,
        plan.county_geoid.clone(),
        plan.title.clone(),
    )?;
    let signals = plan
        .signals
        .iter()
        .map(|signal| {
            ArchiveSignalV1::try_new(
                signal.grant_key.clone(),
                signal.label.clone(),
                signal.value.clone(),
                ArchiveCitationV1::try_new(
                    COMMITTED_TICK_SOURCE_ID_V1.to_owned(),
                    format!("campaign/{resolve_tick}/{}", plan.territory_local_name),
                )?,
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    let links = plan
        .place_links
        .iter()
        .map(|link| {
            ArchiveLinkV1::try_new(
                ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, link.place_geoid.clone())?,
                link.place_name.clone(),
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    ArchivePageInputV1::try_new(
        subject,
        resolve_tick,
        tick_content_hash,
        COUNTY_DECISION_QUESTION_V1.to_owned(),
        signals,
        links,
    )
}

/// Committed per-tick signal sources for one territory, absence-maximal.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
struct CommittedTerritoryFieldsV1 {
    median_wage: Option<f64>,
    phi_hour: Option<f64>,
}

/// Production county dossier producer over the checked reference products.
pub struct CountyDossierProducerV1 {
    config: Config,
    products: SpatialReferenceProducts,
}

impl CountyDossierProducerV1 {
    /// Load the checked reference products and bind the committed-state readers.
    ///
    /// # Errors
    /// Refuses loudly when the embedded reference products, their governing
    /// H3 cohort, or any contract-pinned artifact digest diverges.
    pub fn try_new(config: &Config) -> Result<Self, SemanticArchiveErrorV1> {
        let cohort = representative_h3_reference_cohort_v1()
            .map_err(|_| SemanticArchiveErrorV1::ArtifactDigest)?;
        let products = michigan_spatial_reference_products_v1(cohort)
            .map_err(|_| SemanticArchiveErrorV1::ArtifactDigest)?;
        verify_pinned_artifact_digests(&products)?;
        Ok(Self {
            config: config.clone(),
            products,
        })
    }

    /// Resolve every desired county page from the declared mapping and the
    /// committed per-tick territory fields at `resolve_tick`.
    ///
    /// The result is sorted by county GEOID. A committed field that is absent
    /// at the resolve tick emits no signal; a county whose governed identity
    /// is missing from the pinned products refuses loudly rather than
    /// fabricating a title.
    ///
    /// # Errors
    /// Returns any database, decode, or artifact-identity failure.
    pub fn desired_pages(
        &self,
        campaign_id: CampaignId,
        resolve_tick: u64,
    ) -> Result<Vec<CountyPagePlanV1>, SemanticArchiveErrorV1> {
        let county_names = self
            .products
            .counties()
            .iter()
            .map(|county| (county.county_geoid(), county.county_name()))
            .collect::<BTreeMap<_, _>>();
        let place_names = self
            .products
            .places()
            .iter()
            .map(|place| (place.place_geoid(), place.name_lsad()))
            .collect::<BTreeMap<_, _>>();
        let overlaps = self.products.county_place_land_areas().iter().fold(
            BTreeMap::<&str, BTreeSet<&str>>::new(),
            |mut overlaps, row| {
                overlaps
                    .entry(row.county_geoid())
                    .or_default()
                    .insert(row.place_geoid());
                overlaps
            },
        );
        let mapping = self.read_county_mapping(campaign_id)?;
        let committed = self.read_committed_fields(campaign_id, resolve_tick)?;
        mapping
            .into_iter()
            .map(|(county_geoid, territory_local_name)| {
                let title = (*county_names
                    .get(county_geoid.as_str())
                    .ok_or(SemanticArchiveErrorV1::StoredPageMismatch)?)
                .to_owned();
                let mut signals = Vec::new();
                if let Some(fields) = committed.get(&territory_local_name) {
                    if let Some(value) = fields.median_wage {
                        signals.push(CountySignalV1::from_committed_real(
                            COUNTY_MEDIAN_WAGE_GRANT_KEY_V1.to_owned(),
                            COUNTY_MEDIAN_WAGE_LABEL_V1.to_owned(),
                            value,
                        )?);
                    }
                    if let Some(value) = fields.phi_hour {
                        signals.push(CountySignalV1::from_committed_real(
                            COUNTY_PHI_HOUR_GRANT_KEY_V1.to_owned(),
                            COUNTY_PHI_HOUR_LABEL_V1.to_owned(),
                            value,
                        )?);
                    }
                }
                let place_links = overlaps
                    .get(county_geoid.as_str())
                    .into_iter()
                    .flatten()
                    .map(|place_geoid| {
                        let place_name = place_names
                            .get(place_geoid)
                            .ok_or(SemanticArchiveErrorV1::StoredPageMismatch)?;
                        CountyPlaceLinkV1::try_new(
                            (*place_geoid).to_owned(),
                            (*place_name).to_owned(),
                        )
                    })
                    .collect::<Result<Vec<_>, _>>()?;
                CountyPagePlanV1::try_new(
                    county_geoid,
                    territory_local_name,
                    title,
                    signals,
                    place_links,
                )
            })
            .collect()
    }

    /// Read the campaign's declared county mapping in GEOID order.
    ///
    /// # Errors
    /// Returns any database or decode failure from the read-only query.
    fn read_county_mapping(
        &self,
        campaign_id: CampaignId,
    ) -> Result<Vec<(String, String)>, SemanticArchiveErrorV1> {
        let mut client = self
            .config
            .connect(NoTls)
            .map_err(|error| database("connect county mapping reader", &error))?;
        let rows = client
            .query(ARCHIVE_COUNTY_MAP_READ_SQL_V1, &[campaign_id.as_uuid()])
            .map_err(|error| database("read county mapping", &error))?;
        rows.iter()
            .map(|row| {
                let local: String = decode(row, 0)?;
                let geoid: String = decode(row, 1)?;
                ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, geoid.clone())?;
                validate_text(&local)?;
                Ok((geoid, local))
            })
            .collect()
    }

    /// Read the committed per-tick territory fields at one exact tick.
    ///
    /// Only real-typed rows of the two D2-committed fields enter the
    /// projection; a territory missing at the tick contributes nothing.
    ///
    /// # Errors
    /// Returns any database or decode failure, and refuses a committed field
    /// whose stored tag or bits are malformed.
    fn read_committed_fields(
        &self,
        campaign_id: CampaignId,
        resolve_tick: u64,
    ) -> Result<BTreeMap<String, CommittedTerritoryFieldsV1>, SemanticArchiveErrorV1> {
        let resolve_tick =
            i64::try_from(resolve_tick).map_err(|_| SemanticArchiveErrorV1::InvalidVerifiedTick)?;
        let mut client = self
            .config
            .connect(NoTls)
            .map_err(|error| database("connect committed territory field reader", &error))?;
        let rows = client
            .query(
                ARCHIVE_COUNTY_FIELD_READ_SQL_V1,
                &[campaign_id.as_uuid(), &resolve_tick],
            )
            .map_err(|error| database("read committed territory fields", &error))?;
        let mut committed: BTreeMap<String, CommittedTerritoryFieldsV1> = BTreeMap::new();
        for row in &rows {
            let key: Vec<u8> = decode(row, 0)?;
            let Ok(StableElementKeyV1::Node { local_name, .. }) =
                StableElementKeyV1::from_canonical_bytes(&key)
            else {
                return Err(SemanticArchiveErrorV1::StoredPageMismatch);
            };
            let field_name: String = decode(row, 1)?;
            let value_tag: i16 = decode(row, 2)?;
            let real_bits: Option<i64> = decode(row, 3)?;
            if value_tag != REAL_VALUE_TAG_V1 {
                return Err(SemanticArchiveErrorV1::StoredPageMismatch);
            }
            let bits = real_bits.ok_or(SemanticArchiveErrorV1::StoredPageMismatch)?;
            let value = f64::from_bits(bits.cast_unsigned());
            if !value.is_finite() {
                return Err(SemanticArchiveErrorV1::StoredPageMismatch);
            }
            let fields = committed.entry(local_name).or_default();
            match field_name.as_str() {
                MEDIAN_WAGE_FIELD_V1 => fields.median_wage = Some(value),
                PHI_HOUR_FIELD_V1 => fields.phi_hour = Some(value),
                _ => {}
            }
        }
        Ok(committed)
    }

    /// Read the stored county-page projections for one campaign.
    ///
    /// # Errors
    /// Returns any database or decode failure from the read-only query.
    fn read_stored_pages(
        &self,
        campaign_id: CampaignId,
    ) -> Result<BTreeMap<String, StoredCountyPageV1>, SemanticArchiveErrorV1> {
        let mut client = self
            .config
            .connect(NoTls)
            .map_err(|error| database("connect county page reader", &error))?;
        let rows = client
            .query(ARCHIVE_COUNTY_PAGE_READ_SQL_V1, &[campaign_id.as_uuid()])
            .map_err(|error| database("read stored county pages", &error))?;
        let mut stored = BTreeMap::new();
        for row in &rows {
            let subject_id: String = decode(row, 0)?;
            let title: String = decode(row, 1)?;
            let markdown: String = decode(row, 2)?;
            if let Some(page) = parse_stored_county_page_v1(&subject_id, &title, &markdown) {
                stored.insert(subject_id, page);
            }
        }
        Ok(stored)
    }
}

impl ArchiveDossierProducerV1 for CountyDossierProducerV1 {
    fn produce(
        &self,
        campaign_id: Uuid,
        receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1> {
        let campaign_id = CampaignId::from_uuid(campaign_id);
        let desired = self.desired_pages(campaign_id, receipt.resolve_tick())?;
        let stored = self.read_stored_pages(campaign_id)?;
        let dirty = select_dirty_county_pages_v1(&desired, &stored, ArchiveDirtyBatchV1::MAX_PAGES);
        let pages = dirty
            .iter()
            .map(|plan| {
                county_page_input_v1(plan, receipt.resolve_tick(), *receipt.tick_content_hash())
            })
            .collect::<Result<Vec<_>, _>>()?;
        ArchiveDirtyBatchV1::try_new(receipt.resolve_tick(), *receipt.tick_content_hash(), pages)
    }
}

fn verify_pinned_artifact_digests(
    products: &SpatialReferenceProducts,
) -> Result<(), SemanticArchiveErrorV1> {
    for (code, pinned) in [
        (
            COUNTY_IDENTITY_PRODUCT_CODE_V1,
            PINNED_COUNTY_IDENTITY_ARTIFACT_SHA256_V1,
        ),
        (
            PLACE_IDENTITY_PRODUCT_CODE_V1,
            PINNED_PLACE_IDENTITY_ARTIFACT_SHA256_V1,
        ),
        (
            OVERLAP_PRODUCT_CODE_V1,
            PINNED_COUNTY_PLACE_OVERLAP_ARTIFACT_SHA256_V1,
        ),
    ] {
        let product = products
            .products()
            .iter()
            .find(|product| product.code() == code)
            .ok_or(SemanticArchiveErrorV1::ArtifactDigest)?;
        if product.artifact_sha256() != RefDigestV1::from_bytes(pinned) {
            return Err(SemanticArchiveErrorV1::ArtifactDigest);
        }
    }
    Ok(())
}

fn hash_text(hasher: &mut Sha256, text: &str) {
    hash_len(hasher, text.len());
    hasher.update(text.as_bytes());
}

fn hash_len(hasher: &mut Sha256, len: usize) {
    hasher.update(u64::try_from(len).unwrap_or(u64::MAX).to_be_bytes());
}
