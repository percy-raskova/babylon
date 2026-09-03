//! PER-22 place dossier producer (slice 3) for the semantic Archive worker.
//!
//! [`PlaceDossierProducerV1`] turns one committed dirty receipt into a bounded
//! batch of place dossier pages resolved lazily from the checked Michigan
//! spatial reference products. Nothing is materialized into `PostgreSQL`
//! reference tables: place geometry and county overlap resolve from the
//! digest-pinned products fixture at produce time, so the receipt batch hash
//! folds the exact pinned artifact bytes in through the page content.
//!
//! # Page semantics
//!
//! Every page carries the census identity (`name_lsad`) as its title, one
//! grant-keyed `identity` signal whose citation pins the exact
//! `census_place_identity_mi_2023` artifact row, the stable place decision
//! question, and one link per overlapping county slice. Cross-county places
//! keep every slice — a place overlapping three counties links to all three,
//! sorted by county GEOID, and never collapses to a dominant county. No
//! committed place-level state exists (D2 absence-maximal ruling), so the
//! page publishes no other signals; the renderer drops the identity signal
//! anyway until a campaign grants it.
//!
//! # Dirty detection
//!
//! A place is dirty when no stored page exists for it or when its semantic
//! projection — `(place_geoid, title, decision question, sorted overlapping
//! county GEOIDs)` — differs from the stored page's projection. Receipt-
//! stamped fields (`verified_tick`, `tick_content_hash`) and grant-dependent
//! label visibility never dirty a page: the projection is recomputed from the
//! stored Markdown with the pinned `archive_page_v1.md.j2` shape, stripping
//! the receipt-stamped frontmatter. Malformed stored pages are treated as
//! dirty, which safely republishes drifted content.
//!
//! # Bootstrap drain
//!
//! The first sweep after campaign creation sees every place as new. Each
//! receipt therefore publishes at most [`ArchiveDirtyBatchV1::MAX_PAGES`]
//! places, sorted by place GEOID, and the remainder waits for later receipts;
//! once every place is published with unchanged semantic content, the
//! producer returns an empty batch and the worker defers the receipt.

use std::collections::{BTreeMap, BTreeSet};

use babylon_kernel::tick_content_hash::RefDigestV1;
use postgres::{Config, NoTls};
use sha2::{Digest as _, Sha256};
use uuid::Uuid;

use crate::archive::{database, decode};
use crate::{
    michigan_spatial_reference_products_v1, representative_h3_reference_cohort_v1,
    ArchiveCitationV1, ArchiveDirtyBatchV1, ArchiveDossierProducerV1, ArchiveLinkV1,
    ArchivePageInputV1, ArchivePageRefV1, ArchiveSignalV1, ArchiveSubjectKindV1, ArchiveSubjectV1,
    CampaignId, PendingArchiveReceiptV1, SemanticArchiveErrorV1, SpatialReferenceProducts,
};

/// Stable decision question every place dossier page answers.
pub const PLACE_DECISION_QUESTION_V1: &str =
    "Which overlapping county should organizers investigate next?";

/// Source identity of the census place authority contract artifact.
pub const PLACE_IDENTITY_SOURCE_ID_V1: &str = "census-place-authority-v1";

/// Grant key addressing the one place identity signal.
pub const PLACE_IDENTITY_GRANT_KEY_V1: &str = "identity";

/// Player-facing label of the place identity signal.
pub const PLACE_IDENTITY_SIGNAL_LABEL_V1: &str = "Census identity";

/// Artifact locator prefix pinning one identity row.
pub const PLACE_IDENTITY_LOCATOR_PREFIX_V1: &str =
    "census_place_identity_mi_2023.csv.gz#place_geoid=";

/// Contract-pinned SHA-256 of `census_place_identity_mi_2023.csv.gz`
/// (`contracts/census_place_authority_v1.yaml`).
pub const PINNED_PLACE_IDENTITY_ARTIFACT_SHA256_V1: [u8; 32] = [
    0xcb, 0x86, 0x4b, 0x4f, 0x6f, 0x43, 0x90, 0x2b, 0xb8, 0x21, 0xe8, 0x4f, 0xe9, 0xa4, 0x05, 0x5a,
    0x90, 0x39, 0xe0, 0xa7, 0x4d, 0x8b, 0x83, 0x99, 0xf2, 0x09, 0xae, 0x6e, 0xd2, 0x6a, 0x8b, 0xe7,
];

/// Contract-pinned SHA-256 of
/// `census_county_place_h3_land_overlap_mi_2023.parquet`
/// (`contracts/county_place_h3_overlap_v1.yaml`).
pub const PINNED_COUNTY_PLACE_OVERLAP_ARTIFACT_SHA256_V1: [u8; 32] = [
    0xfc, 0xb7, 0xba, 0xaf, 0x63, 0xa5, 0x42, 0x2a, 0xcc, 0xce, 0x87, 0x09, 0x99, 0x7d, 0xe8, 0xe4,
    0x09, 0x93, 0x6f, 0x71, 0x31, 0xfa, 0x0e, 0xf6, 0xb0, 0xa2, 0x87, 0x62, 0xfd, 0xfe, 0xe4, 0x2f,
];

/// Read-only stored place-page projection used by the dirty diff.
///
/// The query returns the exact stored page rows for one campaign, ordered by
/// subject, and never joins material or raw event ledgers.
pub const ARCHIVE_PLACE_PAGE_READ_SQL_V1: &str = "SELECT subject_id, title, markdown \
FROM babylon_meta.archive_page_v1 \
WHERE campaign_id = $1::uuid AND subject_kind = 'place' \
ORDER BY subject_id";

const PLACE_SEMANTIC_DOMAIN_V1: &[u8] = b"babylon.place-page-semantic.v1\0";
const PLACE_PRODUCT_CODE_V1: &str = "census_place_identity_mi_2023";
const OVERLAP_PRODUCT_CODE_V1: &str = "census_county_place_h3_land_overlap_mi_2023";

/// One overlapping county slice of a place dossier page.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlaceCountySliceV1 {
    county_geoid: String,
    county_name: String,
}

impl PlaceCountySliceV1 {
    /// Construct one county slice with its governed census county name.
    ///
    /// # Errors
    /// Refuses a malformed county GEOID or unsafe county name.
    pub fn try_new(
        county_geoid: String,
        county_name: String,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, county_geoid.clone())?;
        ArchiveSubjectV1::try_new(
            ArchiveSubjectKindV1::County,
            county_geoid.clone(),
            county_name.clone(),
        )?;
        Ok(Self {
            county_geoid,
            county_name,
        })
    }

    /// Borrow the five-digit county GEOID.
    #[must_use]
    pub fn county_geoid(&self) -> &str {
        &self.county_geoid
    }

    /// Borrow the governed census county name.
    #[must_use]
    pub fn county_name(&self) -> &str {
        &self.county_name
    }
}

/// One desired place dossier page resolved from the pinned products.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlacePagePlanV1 {
    place_geoid: String,
    title: String,
    county_links: Vec<PlaceCountySliceV1>,
}

impl PlacePagePlanV1 {
    /// Construct one desired place page plan.
    ///
    /// # Errors
    /// Refuses a malformed place GEOID, an unsafe title, or duplicate county
    /// slices. County slices are stored sorted by county GEOID.
    pub fn try_new(
        place_geoid: String,
        title: String,
        county_links: Vec<PlaceCountySliceV1>,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        ArchiveSubjectV1::try_new(
            ArchiveSubjectKindV1::Place,
            place_geoid.clone(),
            title.clone(),
        )?;
        let mut county_links = county_links;
        county_links.sort_by(|left, right| left.county_geoid.cmp(&right.county_geoid));
        if county_links
            .windows(2)
            .any(|pair| pair[0].county_geoid == pair[1].county_geoid)
        {
            return Err(SemanticArchiveErrorV1::DuplicateKey);
        }
        Ok(Self {
            place_geoid,
            title,
            county_links,
        })
    }

    /// Borrow the seven-digit place GEOID.
    #[must_use]
    pub fn place_geoid(&self) -> &str {
        &self.place_geoid
    }

    /// Borrow the census `name_lsad` page title.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Borrow the sorted per-county slices.
    #[must_use]
    pub fn county_links(&self) -> &[PlaceCountySliceV1] {
        &self.county_links
    }

    fn semantic_sha256(&self) -> [u8; 32] {
        place_page_semantic_sha256_v1(
            &self.place_geoid,
            &self.title,
            PLACE_DECISION_QUESTION_V1,
            &self
                .county_links
                .iter()
                .map(|slice| slice.county_geoid.clone())
                .collect::<Vec<_>>(),
        )
    }
}

/// Receipt-stamp-free semantic projection of one stored place page.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StoredPlacePageV1 {
    title: String,
    question: String,
    county_geoids: Vec<String>,
}

impl StoredPlacePageV1 {
    /// Construct one stored-page projection.
    ///
    /// # Errors
    /// Refuses unsafe text or a malformed county GEOID.
    pub fn try_new(
        title: String,
        question: String,
        county_geoids: Vec<String>,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        crate::archive::validate_text(&title)?;
        crate::archive::validate_text(&question)?;
        let mut unique = BTreeSet::new();
        for geoid in &county_geoids {
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, geoid.clone())?;
            if !unique.insert(geoid.clone()) {
                return Err(SemanticArchiveErrorV1::DuplicateKey);
            }
        }
        Ok(Self {
            title,
            question,
            county_geoids,
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

    /// Borrow the sorted overlapping county GEOIDs.
    #[must_use]
    pub fn county_geoids(&self) -> &[String] {
        &self.county_geoids
    }

    /// Hash the exact receipt-stamp-free projection for one place subject.
    #[must_use]
    pub fn semantic_sha256(&self, place_geoid: &str) -> [u8; 32] {
        place_page_semantic_sha256_v1(
            place_geoid,
            &self.title,
            &self.question,
            &self.county_geoids,
        )
    }
}

/// Hash the exact receipt-stamp-free place page projection.
///
/// The projection covers the place GEOID, title, decision question, and the
/// sorted overlapping county GEOIDs. `verified_tick` and
/// `tick_content_hash` deliberately never enter the hash, so a later receipt
/// alone never re-publishes an unchanged page.
#[must_use]
pub fn place_page_semantic_sha256_v1(
    place_geoid: &str,
    title: &str,
    question: &str,
    county_geoids: &[String],
) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(PLACE_SEMANTIC_DOMAIN_V1);
    hash_text(&mut hasher, place_geoid);
    hash_text(&mut hasher, title);
    hash_text(&mut hasher, question);
    let sorted = county_geoids
        .iter()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    hash_len(&mut hasher, sorted.len());
    for geoid in sorted {
        hash_text(&mut hasher, geoid);
    }
    hasher.finalize().into()
}

/// Parse the semantic projection out of one stored rendered place page.
///
/// The parser is coupled to the pinned `archive_page_v1.md.j2` template
/// ([`crate::ARCHIVE_PAGE_TEMPLATE_SHA256_V1`]) and returns `None` for any
/// stored page whose frontmatter subject, title, question, or related-link
/// shape drifted; callers treat `None` as dirty.
#[must_use]
pub fn parse_stored_place_page_v1(
    place_geoid: &str,
    title: &str,
    markdown: &str,
) -> Option<StoredPlacePageV1> {
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
            subject_exact = value == format!("place/{place_geoid}");
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
    let mut county_geoids = Vec::new();
    let mut in_related = false;
    for line in lines {
        if let Some(rest) = line.strip_prefix("## ") {
            in_related = rest == "Related";
            continue;
        }
        if in_related {
            if let Some(entry) = line.strip_prefix("- [[") {
                let inner = entry.strip_suffix("]]")?;
                let key = inner.split('|').next()?;
                let county = key.strip_prefix("county/")?;
                if county.len() != 5 || !county.bytes().all(|byte| byte.is_ascii_digit()) {
                    return None;
                }
                county_geoids.push(county.to_owned());
            }
            continue;
        }
        if line.starts_with("# ") || line.starts_with("- ") || line.is_empty() {
            continue;
        }
        if question.is_none() {
            question = Some(line.to_owned());
            continue;
        }
        return None;
    }
    StoredPlacePageV1::try_new(stored_title, question?, county_geoids).ok()
}

/// Select the dirty desired pages, sorted by place GEOID, bounded by `limit`.
///
/// A desired page is dirty when no stored projection exists for its subject
/// or when the stored projection hash differs. The bound drains at most
/// `limit` places per receipt; the remainder waits for a later receipt.
#[must_use]
pub fn select_dirty_place_pages_v1<'a>(
    desired: &'a [PlacePagePlanV1],
    stored: &BTreeMap<String, StoredPlacePageV1>,
    limit: usize,
) -> Vec<&'a PlacePagePlanV1> {
    desired
        .iter()
        .filter(|plan| {
            stored.get(plan.place_geoid()).is_none_or(|page| {
                page.semantic_sha256(plan.place_geoid()) != plan.semantic_sha256()
            })
        })
        .take(limit)
        .collect()
}

/// Build the exact receipt-bound page input for one desired place page.
///
/// # Errors
/// Refuses any unsafe page component.
pub fn place_page_input_v1(
    plan: &PlacePagePlanV1,
    resolve_tick: u64,
    tick_content_hash: [u8; 32],
) -> Result<ArchivePageInputV1, SemanticArchiveErrorV1> {
    let subject = ArchiveSubjectV1::try_new(
        ArchiveSubjectKindV1::Place,
        plan.place_geoid.clone(),
        plan.title.clone(),
    )?;
    let signal = ArchiveSignalV1::try_new(
        PLACE_IDENTITY_GRANT_KEY_V1.to_owned(),
        PLACE_IDENTITY_SIGNAL_LABEL_V1.to_owned(),
        plan.title.clone(),
        ArchiveCitationV1::try_new(
            PLACE_IDENTITY_SOURCE_ID_V1.to_owned(),
            format!("{PLACE_IDENTITY_LOCATOR_PREFIX_V1}{}", plan.place_geoid),
        )?,
    )?;
    let links = plan
        .county_links
        .iter()
        .map(|slice| {
            ArchiveLinkV1::try_new(
                ArchivePageRefV1::try_new(
                    ArchiveSubjectKindV1::County,
                    slice.county_geoid.clone(),
                )?,
                slice.county_name.clone(),
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    ArchivePageInputV1::try_new(
        subject,
        resolve_tick,
        tick_content_hash,
        PLACE_DECISION_QUESTION_V1.to_owned(),
        vec![signal],
        links,
    )
}

/// Production place dossier producer over the checked reference products.
pub struct PlaceDossierProducerV1 {
    config: Config,
    products: SpatialReferenceProducts,
}

impl PlaceDossierProducerV1 {
    /// Load the checked reference products and bind the stored-page reader.
    ///
    /// # Errors
    /// Refuses loudly when the embedded reference products, their governing
    /// H3 cohort, or either contract-pinned artifact digest diverges.
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

    /// Resolve every desired place page from the pinned products.
    ///
    /// The result is sorted by place GEOID. Each place keeps every
    /// overlapping county slice; no county membership is collapsed.
    ///
    /// # Errors
    /// Refuses unsafe product text; the checked fixture already pinned every
    /// row count, subject, and measure during construction.
    pub fn desired_pages(&self) -> Result<Vec<PlacePagePlanV1>, SemanticArchiveErrorV1> {
        let county_names = self
            .products
            .counties()
            .iter()
            .map(|county| (county.county_geoid(), county.county_name()))
            .collect::<BTreeMap<_, _>>();
        let slices = self.products.county_place_land_areas().iter().fold(
            BTreeMap::<&str, BTreeSet<&str>>::new(),
            |mut slices, row| {
                slices
                    .entry(row.place_geoid())
                    .or_default()
                    .insert(row.county_geoid());
                slices
            },
        );
        self.products
            .places()
            .iter()
            .map(|place| {
                let county_links = slices
                    .get(place.place_geoid())
                    .into_iter()
                    .flatten()
                    .map(|county_geoid| {
                        let county_name = county_names
                            .get(county_geoid)
                            .ok_or(SemanticArchiveErrorV1::StoredPageMismatch)?;
                        PlaceCountySliceV1::try_new(
                            (*county_geoid).to_owned(),
                            (*county_name).to_owned(),
                        )
                    })
                    .collect::<Result<Vec<_>, _>>()?;
                PlacePagePlanV1::try_new(
                    place.place_geoid().to_owned(),
                    place.name_lsad().to_owned(),
                    county_links,
                )
            })
            .collect()
    }

    /// Read the stored place-page projections for one campaign.
    ///
    /// # Errors
    /// Returns any database or decode failure from the read-only query.
    fn read_stored_pages(
        &self,
        campaign_id: CampaignId,
    ) -> Result<BTreeMap<String, StoredPlacePageV1>, SemanticArchiveErrorV1> {
        let mut client = self
            .config
            .connect(NoTls)
            .map_err(|error| database("connect place page reader", &error))?;
        let rows = client
            .query(ARCHIVE_PLACE_PAGE_READ_SQL_V1, &[campaign_id.as_uuid()])
            .map_err(|error| database("read stored place pages", &error))?;
        let mut stored = BTreeMap::new();
        for row in &rows {
            let subject_id: String = decode(row, 0)?;
            let title: String = decode(row, 1)?;
            let markdown: String = decode(row, 2)?;
            if let Some(page) = parse_stored_place_page_v1(&subject_id, &title, &markdown) {
                stored.insert(subject_id, page);
            }
        }
        Ok(stored)
    }
}

impl ArchiveDossierProducerV1 for PlaceDossierProducerV1 {
    fn produce(
        &self,
        campaign_id: Uuid,
        receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1> {
        let desired = self.desired_pages()?;
        let stored = self.read_stored_pages(CampaignId::from_uuid(campaign_id))?;
        let dirty = select_dirty_place_pages_v1(&desired, &stored, ArchiveDirtyBatchV1::MAX_PAGES);
        let pages = dirty
            .iter()
            .map(|plan| {
                place_page_input_v1(plan, receipt.resolve_tick(), *receipt.tick_content_hash())
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
            PLACE_PRODUCT_CODE_V1,
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
