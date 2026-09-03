//! Pure PER-23 retrieval-boundary contract for the semantic Archive.
//!
//! These pins prove that `SemanticArchiveStoreV1::search_known` is the only
//! retrieval path PER-23 needs: every hit is self-contained with page, tick,
//! subject, signal content, and provenance citations, the search SQL never
//! names raw-ledger tables, the hit limit is bounded before any connection,
//! and stored page bytes are revalidated against their content digest on read.

use babylon_kernel::sha256_of;
use babylon_persistence::{
    archive_page_content_matches_digest_v1, ArchiveCitationV1, ArchiveKnowledgeGrantV1,
    ArchiveKnowledgeV1, ArchivePageInputV1, ArchivePageRefV1, ArchiveSignalV1,
    ArchiveSubjectKindV1, ArchiveSubjectV1, CampaignId, FogSafeArchiveRendererV1,
    SemanticArchiveErrorV1, SemanticArchiveStoreV1, ARCHIVE_SEARCH_SQL_V1, MAX_SEARCH_HITS,
};
use uuid::Uuid;

fn county() -> ArchiveSubjectV1 {
    ArchiveSubjectV1::try_new(
        ArchiveSubjectKindV1::County,
        "26163".to_owned(),
        "Wayne County".to_owned(),
    )
    .expect("county identity")
}

fn signal_citation() -> ArchiveCitationV1 {
    ArchiveCitationV1::try_new(
        "qcew-2024".to_owned(),
        "fact_qcew_county_rollup county_fips=26163".to_owned(),
    )
    .expect("signal citation")
}

fn page_input() -> ArchivePageInputV1 {
    ArchivePageInputV1::try_new(
        county(),
        42,
        [0x11; 32],
        "Which neighboring place should organizers investigate next?".to_owned(),
        vec![ArchiveSignalV1::try_new(
            "employment".to_owned(),
            "Employment".to_owned(),
            "728576 jobs".to_owned(),
            signal_citation(),
        )
        .expect("signal")],
        Vec::new(),
    )
    .expect("page input")
}

fn knowledge() -> ArchiveKnowledgeV1 {
    let county_ref = ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, "26163".to_owned())
        .expect("county ref");
    ArchiveKnowledgeV1::try_new(vec![
        ArchiveKnowledgeGrantV1::try_new(
            county_ref.clone(),
            "subject".to_owned(),
            42,
            ArchiveCitationV1::try_new("archive-subject".to_owned(), "county/26163".to_owned())
                .expect("subject citation"),
        )
        .expect("subject grant"),
        ArchiveKnowledgeGrantV1::try_new(
            county_ref,
            "employment".to_owned(),
            42,
            ArchiveCitationV1::try_new(
                "knowledge-event".to_owned(),
                "employment@tick-42".to_owned(),
            )
            .expect("field grant citation"),
        )
        .expect("field grant"),
    ])
    .expect("knowledge grants")
}

#[test]
fn search_hit_carries_page_tick_subject_signal_and_provenance() {
    fn hit_surface_is_complete(
        hit: &babylon_persistence::ArchiveSearchHitV1,
    ) -> (
        &babylon_persistence::ArchivePageRefV1,
        &str,
        u64,
        &str,
        [u8; 32],
        &[babylon_persistence::ArchiveCitationV1],
    ) {
        (
            hit.page_ref(),
            hit.title(),
            hit.verified_tick(),
            hit.markdown(),
            hit.content_sha256(),
            hit.citations(),
        )
    }
    let _ = hit_surface_is_complete;

    for column in [
        "page.subject_kind",
        "page.subject_id",
        "page.title",
        "page.verified_tick",
        "page.markdown",
        "page.content_sha256",
        "page.provenance_json",
    ] {
        assert!(
            ARCHIVE_SEARCH_SQL_V1.contains(column),
            "known-only search must select {column} so one hit is self-contained"
        );
    }
    assert!(ARCHIVE_SEARCH_SQL_V1.contains("FROM babylon_meta.archive_page_v1 AS page"));
    assert!(
        ARCHIVE_SEARCH_SQL_V1.contains("JOIN babylon_meta.archive_knowledge_grant_v1 AS knowledge")
    );

    let renderer = FogSafeArchiveRendererV1::new().expect("pinned template compiles");
    let page = renderer
        .render(&page_input(), &knowledge())
        .expect("known page renders");
    let signal = signal_citation();

    assert!(page.markdown().contains("**Employment:** 728576 jobs"));
    assert!(page.markdown().contains(signal.source_id()));
    assert!(page.markdown().contains(signal.locator()));
    assert_eq!(page.citations()[1], signal);
    assert_eq!(page.sha256(), sha256_of(page.markdown().as_bytes()));
}

#[test]
fn search_sql_never_names_raw_ledger_tables() {
    for raw_relation in [
        "archive_dirty_receipt_v1",
        "tick_commit",
        "tick_event",
        "hypergraph",
        "material",
        "babylon_state",
    ] {
        assert!(
            !ARCHIVE_SEARCH_SQL_V1.contains(raw_relation),
            "known-only search must not name {raw_relation}"
        );
    }
}

#[test]
fn known_search_limit_is_bounded_before_any_connection() {
    let store = SemanticArchiveStoreV1::new(&postgres::Config::new());
    let campaign_id =
        CampaignId::from_uuid(Uuid::from_u128(0x2200_0000_0000_0000_0000_0000_0000_00b1));

    assert_eq!(
        store.search_known(campaign_id, "employment", 0),
        Err(SemanticArchiveErrorV1::CollectionBound)
    );
    assert_eq!(
        store.search_known(campaign_id, "employment", MAX_SEARCH_HITS + 1),
        Err(SemanticArchiveErrorV1::CollectionBound)
    );
    assert_eq!(
        store.search_known(campaign_id, "  ", MAX_SEARCH_HITS),
        Ok(Vec::new())
    );
    assert_eq!(
        store.search_known(campaign_id, &"x".repeat(4_097), MAX_SEARCH_HITS),
        Err(SemanticArchiveErrorV1::InvalidText)
    );
}

#[test]
fn stored_page_content_is_revalidated_against_its_digest_on_read() {
    let markdown = "known page bytes";
    let digest = sha256_of(markdown.as_bytes());
    assert!(archive_page_content_matches_digest_v1(markdown, &digest));
    assert!(!archive_page_content_matches_digest_v1(
        "tampered page bytes",
        &digest
    ));
    assert!(!archive_page_content_matches_digest_v1(
        markdown,
        &[0xee; 32]
    ));
}
