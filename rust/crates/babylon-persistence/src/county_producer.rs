//! PER-22 county dossier producer (slice 2) for the semantic Archive worker.
//!
//! [`CountyDossierProducer`] turns one committed dirty receipt into a
//! bounded batch of county dossier pages. Counties enumerate from the
//! campaign's declared `babylon_meta.territory_county_map_v1` rows in GEOID
//! order. Current economic campaigns resolve identity from their captured county
//! roster and place links only from explicitly captured local detail. Authored
//! controls retain their explicit fixed Michigan reference scope.
//!
//! # Page semantics
//!
//! Each page carries the governed census county name as its title, the
//! established county decision question, one grant-keyed signal per committed
//! per-tick territory field that exists at the receipt's resolve tick —
//! the four public QCEW baseline integer fields, or the established
//! `territory/median-wage` and `territory/phi-hour` real fields — and one link
//! per place overlapping the county. A committed field that is missing at the
//! resolve tick emits no signal, never a fabricated value. Signal values are
//! exact decimal integers for QCEW and `%.6f` for the established real fields.
//! Public baseline citations pin the QCEW artifact and county row; established
//! real-field citations pin `campaign/{resolve_tick}/{territory local name}`.
//! Unknown place subjects
//! stay redlinks because the renderer hides labels for subjects no knowledge
//! grant covers.
//!
//! # Dirty detection
//!
//! A county is dirty when no stored page exists for it or when its semantic
//! projection — `(county_geoid, title, decision question, grant-visible
//! signals with citations, place link names)` — differs from the stored page's
//! projection. The projection folds the grant-visible rendering: each signal
//! counts only while the campaign grants that field key on the county, and a
//! place link name counts only while the campaign grants that place subject,
//! both snapshotted at the receipt tick through [`ARCHIVE_COUNTY_GRANTS_SQL`].
//! A page published redacted therefore re-dirties the moment later grants
//! reveal its signals or link names, and the next sweep republishes it.
//! Receipt-stamped fields (`verified_tick`, `tick_content_hash`, and the tick
//! segment of each citation locator) never dirty a page: the projection is
//! recomputed from the stored Markdown with the pinned `archive_page_v1.md.j2`
//! shape ([`crate::ARCHIVE_PAGE_TEMPLATE_SHA256`] bytes folded into the
//! hash), stripping the receipt-stamped frontmatter. Malformed stored pages
//! are treated as dirty, which safely republishes drifted content.
//!
//! # Drain bound
//!
//! The producer never truncates a dirty set and never refuses an over-bound
//! one. When more than [`ArchiveDirtyBatch::MAX_PAGES`] counties are dirty
//! for one receipt it selects the leading `limit` entries in geoid order and
//! reports the exact undrained tail count ([`ArchiveDirtySelection`]), so
//! the sweep stages one bounded batch and the receipt stays pending until
//! the tail drains across successive sweeps. Michigan's 83 mapped counties
//! keep the production county drain a normal complete batch, leaving most of
//! the shared page budget for the place producer (PER-318).

mod source;

pub(crate) use source::CountySource;

#[cfg(test)]
mod captured_tests;

#[path = "county_producer/dossier.rs"]
mod dossier;

pub use dossier::{
    county_committed_signals, county_page_input, county_page_semantic_sha256,
    desired_county_projection, filter_granted_county_plans, format_county_statblock_value,
    parse_stored_county_page, select_dirty_county_pages, CommittedTerritoryFields,
    CountyDossierProducer, CountyGrantIndex, CountyPagePlan, CountyPageProjection, CountyPlaceLink,
    CountySignal, CountySignalProjection, ARCHIVE_COUNTY_FIELD_READ_SQL, ARCHIVE_COUNTY_GRANTS_SQL,
    ARCHIVE_COUNTY_MAP_READ_SQL, ARCHIVE_COUNTY_PAGE_READ_SQL, COMMITTED_TICK_SOURCE_ID,
    COUNTY_DECISION_QUESTION, COUNTY_MEDIAN_WAGE_GRANT_KEY, COUNTY_MEDIAN_WAGE_LABEL,
    COUNTY_PHI_HOUR_GRANT_KEY, COUNTY_PHI_HOUR_LABEL, PINNED_COUNTY_IDENTITY_ARTIFACT_SHA256,
};
#[allow(unused_imports)]
use dossier::{
    hash_len, hash_text, parse_committed_locator, parse_signal_bullet, parse_subject_scheme_link,
    verify_pinned_artifact_digests, COUNTY_IDENTITY_PRODUCT_CODE, COUNTY_SEMANTIC_DOMAIN,
    COUNTY_SUBJECT_GRANT_KEY, INT_VALUE_TAG, MEDIAN_WAGE_FIELD, OVERLAP_PRODUCT_CODE,
    PHI_HOUR_FIELD, PLACE_IDENTITY_PRODUCT_CODE, QCEW_LABELS, REAL_VALUE_TAG,
};

#[allow(unused_imports)]
use crate::archive::{database, decode, validate_text, ARCHIVE_PAGE_TEMPLATE_SHA256};
#[allow(unused_imports)]
use crate::michigan_economy::{
    QCEW_ECONOMICS_ARTIFACT_SHA256, QCEW_ECONOMICS_FIELD_KEYS, QCEW_ECONOMICS_SOURCE_ID,
};
#[allow(unused_imports)]
use crate::place_producer::{
    PINNED_COUNTY_PLACE_OVERLAP_ARTIFACT_SHA256, PINNED_PLACE_IDENTITY_ARTIFACT_SHA256,
};
#[allow(unused_imports)]
use crate::{
    h3_reference_cohort::representative_h3_reference_cohort, identity::CampaignId,
    spatial_reference_products::michigan_spatial_reference_products,
    spatial_reference_products::SpatialReferenceProducts, ArchiveCitation, ArchiveDirtySelection,
    ArchiveDossierProducer, ArchiveLink, ArchivePageInput, ArchivePageRef, ArchiveProducerOutcome,
    ArchiveSignal, ArchiveSubject, ArchiveSubjectKind, PendingArchiveReceipt, SemanticArchiveError,
};
#[allow(unused_imports)]
use babylon_graph::stable_element::StableElementKey;
#[allow(unused_imports)]
use babylon_kernel::tick_content_hash::RefDigest;
#[allow(unused_imports)]
use postgres::{Config, NoTls};
#[allow(unused_imports)]
use sha2::{Digest as _, Sha256};
#[allow(unused_imports)]
use source::{signal_citation, NATIONAL_COUNTY_SOURCE_ID};
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
#[allow(unused_imports)]
use uuid::Uuid;
