//! Pure contracts for the PER-22 place dossier producer.
//!
//! These tests pin the producer's decision semantics without any database:
//! GEOID validation, sorted enumeration, cross-county slice retention, the
//! bounded bootstrap drain, receipt-stamp-insensitive dirty detection, and
//! the contract-pinned artifact digests.

use std::collections::BTreeMap;
use std::str::FromStr;

use babylon_persistence::{
    parse_stored_place_page_v1, place_page_input_v1, place_page_semantic_sha256_v1,
    select_dirty_place_pages_v1, ArchiveDirtyBatchV1, ArchiveKnowledgeGrantV1, ArchiveKnowledgeV1,
    ArchivePageInputV1, ArchivePageRefV1, ArchiveSubjectKindV1, FogSafeArchiveRendererV1,
    PlaceCountySliceV1, PlaceDossierProducerV1, PlacePagePlanV1, SemanticArchiveErrorV1,
    StoredPlacePageV1, ARCHIVE_PLACE_PAGE_READ_SQL_V1,
    PINNED_COUNTY_PLACE_OVERLAP_ARTIFACT_SHA256_V1, PINNED_PLACE_IDENTITY_ARTIFACT_SHA256_V1,
    PLACE_DECISION_QUESTION_V1,
};
use postgres::Config;

const CONTRACT_PLACE_IDENTITY_SHA256: &str =
    "cb864b4f6f43902bb821e84fe9a4055a9039e0a74d8b8399f209ae6ed26a8be7";
const CONTRACT_COUNTY_PLACE_OVERLAP_SHA256: &str =
    "fcb7baaf63a5422accce8709997de8e409936f7131fa0ef6b0a28762fdfee42f";

fn contract_digest(hex: &str) -> [u8; 32] {
    let bytes = hex.as_bytes();
    let mut digest = [0_u8; 32];
    for (index, byte) in digest.iter_mut().enumerate() {
        let high = (bytes[index * 2] as char).to_digit(16).expect("hex digit");
        let low = (bytes[index * 2 + 1] as char)
            .to_digit(16)
            .expect("hex digit");
        *byte = u8::try_from((high << 4) | low).expect("two hex nibbles fit one byte");
    }
    digest
}

fn producer() -> PlaceDossierProducerV1 {
    let config = Config::from_str("postgresql://unused:unused@127.0.0.1:1/unused")
        .expect("idle producer config parses");
    PlaceDossierProducerV1::try_new(&config).expect("pinned reference products load")
}

fn desired_pages() -> Vec<PlacePagePlanV1> {
    producer()
        .desired_pages()
        .expect("desired place pages build")
}

fn plan(geoid: &str, title: &str, counties: &[(&str, &str)]) -> PlacePagePlanV1 {
    PlacePagePlanV1::try_new(
        geoid.to_owned(),
        title.to_owned(),
        counties
            .iter()
            .map(|(geoid, name)| {
                PlaceCountySliceV1::try_new((*geoid).to_owned(), (*name).to_owned())
                    .expect("county slice")
            })
            .collect(),
    )
    .expect("place page plan")
}

fn detroit_plan() -> PlacePagePlanV1 {
    plan("2622000", "Detroit city", &[("26163", "Wayne")])
}

#[test]
fn geoid_validation_accepts_only_seven_digit_place_identities() {
    assert_eq!(
        PlacePagePlanV1::try_new("26163".to_owned(), "Too short".to_owned(), Vec::new()),
        Err(SemanticArchiveErrorV1::InvalidIdentity)
    );
    assert_eq!(
        PlacePagePlanV1::try_new("268400A".to_owned(), "Not digits".to_owned(), Vec::new()),
        Err(SemanticArchiveErrorV1::InvalidIdentity)
    );
    let valid =
        PlacePagePlanV1::try_new("2622000".to_owned(), "Detroit city".to_owned(), Vec::new())
            .expect("valid plan");
    assert_eq!(valid.place_geoid(), "2622000");

    let pages = desired_pages();
    assert_eq!(pages.len(), 745, "exactly the 745 pinned places enumerate");
    for page in &pages {
        assert_eq!(page.place_geoid().len(), 7);
        assert!(page.place_geoid().bytes().all(|byte| byte.is_ascii_digit()));
        assert!(page.place_geoid().starts_with("26"));
        assert!(!page.title().is_empty());
    }
}

#[test]
fn places_enumerate_in_sorted_geoid_order() {
    let pages = desired_pages();
    let mut sorted = pages
        .iter()
        .map(PlacePagePlanV1::place_geoid)
        .collect::<Vec<_>>();
    sorted.sort_unstable();
    let enumerated = pages
        .iter()
        .map(PlacePagePlanV1::place_geoid)
        .collect::<Vec<_>>();
    assert_eq!(enumerated, sorted);
    assert_eq!(enumerated.first().copied(), Some("2600380"));
    assert_eq!(enumerated.last().copied(), Some("2689320"));
}

#[test]
fn cross_county_places_keep_every_county_slice() {
    let pages = desired_pages();
    let multi = pages
        .iter()
        .filter(|page| page.county_links().len() > 1)
        .collect::<Vec<_>>();
    assert_eq!(
        multi.len(),
        30,
        "the contract pins exactly 30 cross-county places"
    );

    let three = pages
        .iter()
        .find(|page| page.county_links().len() == 3)
        .expect("at least one three-county place exists");
    let geoids = three
        .county_links()
        .iter()
        .map(PlaceCountySliceV1::county_geoid)
        .collect::<Vec<_>>();
    let mut sorted = geoids.clone();
    sorted.sort_unstable();
    assert_eq!(geoids, sorted, "county slices stay sorted by county GEOID");

    let input = place_page_input_v1(three, 42, [0x11; 32]).expect("three-county page input");
    let links = input.links();
    assert_eq!(links.len(), 3, "every overlapping county becomes one link");
    for link in links {
        assert_eq!(link.target().kind(), ArchiveSubjectKindV1::County);
        assert_eq!(link.target().id().len(), 5);
        assert!(!link.known_label().is_empty());
    }
}

#[test]
fn bootstrap_drain_bounds_each_receipt_to_max_pages_sorted() {
    let pages = desired_pages();
    let stored = BTreeMap::new();
    let dirty = select_dirty_place_pages_v1(&pages, &stored, ArchiveDirtyBatchV1::MAX_PAGES);

    assert_eq!(dirty.len(), ArchiveDirtyBatchV1::MAX_PAGES);
    let geoids = dirty
        .iter()
        .map(|page| page.place_geoid().to_owned())
        .collect::<Vec<_>>();
    let mut sorted = geoids.clone();
    sorted.sort_unstable();
    assert_eq!(geoids, sorted, "the drain is sorted by place GEOID");
    assert_eq!(geoids.first().map(String::as_str), Some("2600380"));
    let batch_ceiling = geoids.last().expect("bounded batch is non-empty").clone();
    let remainder = pages
        .iter()
        .find(|page| page.place_geoid() > batch_ceiling.as_str())
        .expect("places beyond the first receipt exist");
    assert!(
        !geoids.iter().any(|geoid| geoid == remainder.place_geoid()),
        "the remainder waits for a later receipt"
    );

    let continued = select_dirty_place_pages_v1(&pages, &stored, usize::MAX);
    assert_eq!(
        continued.len(),
        745,
        "the unbounded drain covers every place"
    );
}

#[test]
fn dirty_diff_excludes_receipt_stamped_fields() {
    let stamped_first =
        place_page_input_v1(&detroit_plan(), 1, [0x11; 32]).expect("first receipt page input");
    let stamped_second =
        place_page_input_v1(&detroit_plan(), 2, [0x22; 32]).expect("second receipt page input");
    assert_ne!(
        stamped_first.verified_tick(),
        stamped_second.verified_tick()
    );
    assert_ne!(
        stamped_first.tick_content_hash(),
        stamped_second.tick_content_hash()
    );

    let first_hash = place_page_semantic_sha256_v1(
        detroit_plan().place_geoid(),
        detroit_plan().title(),
        PLACE_DECISION_QUESTION_V1,
        &["26163".to_owned()],
    );
    let second_hash = place_page_semantic_sha256_v1(
        detroit_plan().place_geoid(),
        detroit_plan().title(),
        PLACE_DECISION_QUESTION_V1,
        &["26163".to_owned()],
    );
    assert_eq!(
        first_hash, second_hash,
        "the receipt stamp never dirties a page"
    );

    let changed_links = place_page_semantic_sha256_v1(
        detroit_plan().place_geoid(),
        detroit_plan().title(),
        PLACE_DECISION_QUESTION_V1,
        &["26163".to_owned(), "26125".to_owned()],
    );
    assert_ne!(first_hash, changed_links);
    let changed_question = place_page_semantic_sha256_v1(
        detroit_plan().place_geoid(),
        detroit_plan().title(),
        "Which overlapping county should organizers investigate first?",
        &["26163".to_owned()],
    );
    assert_ne!(first_hash, changed_question);
}

#[test]
fn dirty_diff_compares_stored_page_semantic_projection() {
    let renderer = FogSafeArchiveRendererV1::new().expect("pinned template compiles");
    let input = place_page_input_v1(&detroit_plan(), 1, [0x11; 32]).expect("page input");
    let knowledge = knowledge_for(&[&detroit_plan()]);
    let first_page = renderer
        .render(&input, &knowledge)
        .expect("granted page renders");

    let stored = parse_stored_place_page_v1("2622000", "Detroit city", first_page.markdown())
        .expect("rendered page parses back");
    assert_eq!(stored.question(), PLACE_DECISION_QUESTION_V1);
    assert_eq!(stored.county_geoids(), &["26163".to_owned()]);

    // An identical semantic projection at a later receipt stamp stays clean.
    let stamped_later = renderer
        .render(
            &place_page_input_v1(&detroit_plan(), 2, [0x22; 32]).expect("later page input"),
            &knowledge,
        )
        .expect("later page renders");
    let stored_later =
        parse_stored_place_page_v1("2622000", "Detroit city", stamped_later.markdown())
            .expect("later rendered page parses back");
    assert_eq!(
        stored.semantic_sha256("2622000"),
        stored_later.semantic_sha256("2622000"),
        "only the receipt stamp changed, so the projection is unchanged"
    );

    let mut stored_map = BTreeMap::new();
    stored_map.insert("2622000".to_owned(), stored);
    let pages = [detroit_plan()];
    let dirty = select_dirty_place_pages_v1(&pages, &stored_map, usize::MAX);
    assert!(
        dirty.is_empty(),
        "unchanged semantic content is not re-published"
    );

    // Grant drift (a redlink where a label was known) must not dirty either.
    let pages = [detroit_plan()];
    let redlink_only = ArchiveKnowledgeV1::try_new(vec![subject_grant("2622000")])
        .expect("subject-only knowledge");
    let redlink_rendered = renderer
        .render(
            &place_page_input_v1(&detroit_plan(), 3, [0x33; 32]).expect("third page input"),
            &redlink_only,
        )
        .expect("redlink page renders");
    let redlink_stored =
        parse_stored_place_page_v1("2622000", "Detroit city", redlink_rendered.markdown())
            .expect("redlink page parses back");
    let mut redlink_map = BTreeMap::new();
    redlink_map.insert("2622000".to_owned(), redlink_stored);
    assert!(
        select_dirty_place_pages_v1(&pages, &redlink_map, usize::MAX).is_empty(),
        "grant visibility is receipt-stamped state, not semantic content"
    );

    // A missing subject is new and must be published.
    let fresh = [detroit_plan()];
    assert_eq!(
        select_dirty_place_pages_v1(&fresh, &BTreeMap::new(), usize::MAX).len(),
        1
    );
    // Drifted stored content is republished.
    let drifted = StoredPlacePageV1::try_new(
        "Detroit city".to_owned(),
        PLACE_DECISION_QUESTION_V1.to_owned(),
        vec!["26163".to_owned(), "26099".to_owned()],
    )
    .expect("drifted stored page");
    let mut drifted_map = BTreeMap::new();
    drifted_map.insert("2622000".to_owned(), drifted);
    let drifted_pages = [detroit_plan()];
    assert_eq!(
        select_dirty_place_pages_v1(&drifted_pages, &drifted_map, usize::MAX).len(),
        1
    );
}

#[test]
fn malformed_stored_pages_are_dirty_not_fatal() {
    assert!(parse_stored_place_page_v1("2622000", "Detroit city", "not a page").is_none());
    assert!(parse_stored_place_page_v1("2622000", "Other title", "# Detroit city\n\nq").is_none());

    let pages = vec![detroit_plan()];
    let mut stored = BTreeMap::new();
    // A stored row whose title column disagrees with its markdown republishes.
    let title_drift = render_markdown(&detroit_plan(), &[("26163", "Wayne")]);
    assert!(parse_stored_place_page_v1("2622000", "Different city", &title_drift).is_none());
    let parsed = parse_stored_place_page_v1("2622000", "Detroit city", &title_drift)
        .expect("well-formed stored page parses");
    stored.insert("2622000".to_owned(), parsed);
    assert_eq!(
        select_dirty_place_pages_v1(&pages, &stored, usize::MAX).len(),
        0
    );
}

#[test]
fn artifact_digests_match_the_governing_contracts() {
    assert_eq!(
        PINNED_PLACE_IDENTITY_ARTIFACT_SHA256_V1,
        contract_digest(CONTRACT_PLACE_IDENTITY_SHA256)
    );
    assert_eq!(
        PINNED_COUNTY_PLACE_OVERLAP_ARTIFACT_SHA256_V1,
        contract_digest(CONTRACT_COUNTY_PLACE_OVERLAP_SHA256)
    );
}

#[test]
fn place_page_read_sql_is_pinned() {
    assert_eq!(
        ARCHIVE_PLACE_PAGE_READ_SQL_V1,
        "SELECT subject_id, title, markdown \
FROM babylon_meta.archive_page_v1 \
WHERE campaign_id = $1::uuid AND subject_kind = 'place' \
ORDER BY subject_id"
    );
    assert!(ARCHIVE_PLACE_PAGE_READ_SQL_V1.contains("babylon_meta.archive_page_v1"));
    assert!(ARCHIVE_PLACE_PAGE_READ_SQL_V1.contains("subject_kind = 'place'"));
}

#[test]
fn batch_from_produced_pages_matches_the_receipt() {
    let receipt = babylon_persistence::PendingArchiveReceiptV1::try_new(7, [0x77; 32])
        .expect("receipt boundary");
    let pages = desired_pages();
    let dirty = select_dirty_place_pages_v1(&pages, &BTreeMap::new(), 3);
    let inputs = dirty
        .iter()
        .map(|page| place_page_input_v1(page, receipt.resolve_tick(), *receipt.tick_content_hash()))
        .collect::<Result<Vec<ArchivePageInputV1>, _>>()
        .expect("page inputs");
    for input in &inputs {
        assert_eq!(input.verified_tick(), receipt.resolve_tick());
        assert_eq!(input.tick_content_hash(), receipt.tick_content_hash());
        assert_eq!(input.decision_question(), PLACE_DECISION_QUESTION_V1);
        assert_eq!(
            input.signals().len(),
            1,
            "one identity citation per place row"
        );
        assert_eq!(input.signals()[0].grant_key(), "identity");
        assert_eq!(
            input.signals()[0].citation().source_id(),
            "census-place-authority-v1"
        );
        assert!(input.signals()[0]
            .citation()
            .locator()
            .contains("#place_geoid="));
    }
    let batch =
        ArchiveDirtyBatchV1::try_new(receipt.resolve_tick(), *receipt.tick_content_hash(), inputs)
            .expect("dirty batch");
    assert_eq!(batch.pages().len(), 3);
}

fn subject_grant(geoid: &str) -> ArchiveKnowledgeGrantV1 {
    ArchiveKnowledgeGrantV1::try_new(
        ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, geoid.to_owned())
            .expect("place ref"),
        "subject".to_owned(),
        1,
        babylon_persistence::ArchiveCitationV1::try_new(
            "archive-subject".to_owned(),
            format!("place/{geoid}"),
        )
        .expect("subject citation"),
    )
    .expect("subject grant")
}

fn field_grant(geoid: &str, key: &str) -> ArchiveKnowledgeGrantV1 {
    ArchiveKnowledgeGrantV1::try_new(
        ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, geoid.to_owned())
            .expect("place ref"),
        key.to_owned(),
        1,
        babylon_persistence::ArchiveCitationV1::try_new(
            "archive-field".to_owned(),
            format!("{key}@tick-1"),
        )
        .expect("field citation"),
    )
    .expect("field grant")
}

fn county_subject_grant(county_geoid: &str) -> ArchiveKnowledgeGrantV1 {
    ArchiveKnowledgeGrantV1::try_new(
        ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, county_geoid.to_owned())
            .expect("county ref"),
        "subject".to_owned(),
        1,
        babylon_persistence::ArchiveCitationV1::try_new(
            "archive-subject".to_owned(),
            format!("county/{county_geoid}"),
        )
        .expect("county citation"),
    )
    .expect("county grant")
}

fn knowledge_for(plans: &[&PlacePagePlanV1]) -> ArchiveKnowledgeV1 {
    let mut grants = Vec::new();
    for plan in plans {
        grants.push(subject_grant(plan.place_geoid()));
        grants.push(field_grant(plan.place_geoid(), "identity"));
        for slice in plan.county_links() {
            grants.push(county_subject_grant(slice.county_geoid()));
        }
    }
    ArchiveKnowledgeV1::try_new(grants).expect("knowledge grants")
}

fn render_markdown(plan: &PlacePagePlanV1, _counties: &[(&str, &str)]) -> String {
    let renderer = FogSafeArchiveRendererV1::new().expect("pinned template compiles");
    let input = place_page_input_v1(plan, 9, [0x99; 32]).expect("page input");
    let knowledge = knowledge_for(&[plan]);
    renderer
        .render(&input, &knowledge)
        .expect("page renders")
        .markdown()
        .to_owned()
}
