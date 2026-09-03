//! Pure PER-22 county dossier producer contracts.
//!
//! These tests pin the producer's semantic decisions without any database:
//! mapping-driven enumeration order, `%.6f` statblock formatting, the D2
//! absence-maximal signal discipline, the receipt-stamp-free dirty diff, the
//! pinned read-only SQL, batch/receipt binding, sorted links, and the redlink
//! form of unknown place targets.

use std::collections::BTreeMap;

use babylon_persistence::{
    county_page_input_v1, county_page_semantic_sha256_v1, format_county_statblock_value_v1,
    parse_stored_county_page_v1, select_dirty_county_pages_v1, ArchiveDirtyBatchV1,
    ArchivePageInputV1, ArchivePageRefV1, ArchiveSubjectKindV1, CountyPagePlanV1,
    CountyPlaceLinkV1, CountySignalV1, SemanticArchiveErrorV1, StoredCountyPageV1,
    ARCHIVE_COUNTY_FIELD_READ_SQL_V1, ARCHIVE_COUNTY_MAP_READ_SQL_V1,
    ARCHIVE_COUNTY_PAGE_READ_SQL_V1, COMMITTED_TICK_SOURCE_ID_V1, COUNTY_DECISION_QUESTION_V1,
    COUNTY_MEDIAN_WAGE_GRANT_KEY_V1, COUNTY_MEDIAN_WAGE_LABEL_V1, COUNTY_PHI_HOUR_GRANT_KEY_V1,
    COUNTY_PHI_HOUR_LABEL_V1,
};

fn signal(grant_key: &str, label: &str, value: &str) -> CountySignalV1 {
    CountySignalV1::try_new(grant_key.to_owned(), label.to_owned(), value.to_owned())
        .expect("county signal")
}

fn wayne_plan(signals: Vec<CountySignalV1>, links: Vec<CountyPlaceLinkV1>) -> CountyPagePlanV1 {
    CountyPagePlanV1::try_new(
        "26163".to_owned(),
        "wayne".to_owned(),
        "Wayne County".to_owned(),
        signals,
        links,
    )
    .expect("wayne plan")
}

fn detroit_link() -> CountyPlaceLinkV1 {
    CountyPlaceLinkV1::try_new("2622000".to_owned(), "Detroit city".to_owned())
        .expect("detroit link")
}

fn wayne_plan_full() -> CountyPagePlanV1 {
    wayne_plan(
        vec![
            signal(
                COUNTY_MEDIAN_WAGE_GRANT_KEY_V1,
                COUNTY_MEDIAN_WAGE_LABEL_V1,
                "21.000000",
            ),
            signal(
                COUNTY_PHI_HOUR_GRANT_KEY_V1,
                COUNTY_PHI_HOUR_LABEL_V1,
                "1.000000",
            ),
        ],
        vec![
            detroit_link(),
            CountyPlaceLinkV1::try_new("2674900".to_owned(), "Riverview city".to_owned())
                .expect("riverview link"),
        ],
    )
}

fn wayne_page_input_at(
    plan: &CountyPagePlanV1,
    resolve_tick: u64,
    tick_content_hash: [u8; 32],
) -> ArchivePageInputV1 {
    county_page_input_v1(plan, resolve_tick, tick_content_hash).expect("county page input")
}

fn wayne_markdown_at(verified_tick: u64, tick_content_hash: [u8; 32]) -> String {
    let hex = tick_content_hash
        .iter()
        .fold(String::new(), |mut hex, byte| {
            use std::fmt::Write as _;
            write!(hex, "{byte:02x}").expect("writing to String cannot fail");
            hex
        });
    format!(
        "---\nschema: babylon.archive-page.v1\nsubject: county/26163\n\
         verified_tick: {verified_tick}\ntick_content_hash: {hex}\n---\n\
         # Wayne County\n\nWhich neighboring place should organizers investigate next?\n\
         ## Signals\n\
         - **Median wage:** 21.000000 — committed-tick-v1; campaign/1/wayne\n\
         - **Imperial rent Φ:** 1.000000 — committed-tick-v1; campaign/1/wayne\n\
         ## Related\n\
         - [[place/2622000|Detroit city]]\n\
         - [[place/2674900]]\n"
    )
}

#[test]
fn decision_question_matches_the_established_county_fixture_phrasing() {
    assert_eq!(
        COUNTY_DECISION_QUESTION_V1,
        "Which neighboring place should organizers investigate next?"
    );
}

#[test]
fn committed_real_values_pin_python_statblock_formatting() {
    assert_eq!(
        format_county_statblock_value_v1(21.0).expect("format"),
        "21.000000"
    );
    assert_eq!(
        format_county_statblock_value_v1(1.0).expect("format"),
        "1.000000"
    );
    assert_eq!(
        format_county_statblock_value_v1(0.5).expect("format"),
        "0.500000"
    );
    assert_eq!(
        format_county_statblock_value_v1(f64::NAN),
        Err(SemanticArchiveErrorV1::InvalidText)
    );
    assert_eq!(
        format_county_statblock_value_v1(f64::INFINITY),
        Err(SemanticArchiveErrorV1::InvalidText)
    );
}

#[test]
fn absent_committed_fields_emit_no_signal() {
    let plan = wayne_plan(Vec::new(), vec![detroit_link()]);
    let page = wayne_page_input_at(&plan, 1, [0x11; 32]);
    assert!(
        page.signals().is_empty(),
        "a county with no committed median-wage or phi-hour emits no signal"
    );

    let stored = BTreeMap::new();
    let plans = [plan.clone()];
    let dirty = select_dirty_county_pages_v1(&plans, &stored, 256);
    assert_eq!(dirty.len(), 1, "a brand-new county page is still dirty");
}

#[test]
fn dirty_diff_excludes_receipt_stamps_but_catches_semantic_drift() {
    let plan = wayne_plan_full();
    let stored_page =
        parse_stored_county_page_v1("26163", "Wayne County", &wayne_markdown_at(99, [0xee; 32]))
            .expect("stored projection parses");
    let mut stored = BTreeMap::new();
    stored.insert("26163".to_owned(), stored_page);

    let plans = [plan.clone()];
    let dirty = select_dirty_county_pages_v1(&plans, &stored, 256);
    assert!(
        dirty.is_empty(),
        "only the receipt stamps changed, so the page is not dirty"
    );

    let drifted = wayne_plan(
        vec![signal(
            COUNTY_MEDIAN_WAGE_GRANT_KEY_V1,
            COUNTY_MEDIAN_WAGE_LABEL_V1,
            "22.000000",
        )],
        vec![detroit_link()],
    );
    let drifted = [drifted];
    let dirty = select_dirty_county_pages_v1(&drifted, &stored, 256);
    assert_eq!(dirty.len(), 1, "a changed signal value dirties the page");

    let requestioned = CountyPagePlanV1::try_new(
        "26163".to_owned(),
        "wayne".to_owned(),
        "Wayne County".to_owned(),
        Vec::new(),
        Vec::new(),
    )
    .expect("requestioned plan");
    let stored_page =
        parse_stored_county_page_v1("26163", "Wayne County", &wayne_markdown_at(1, [0x11; 32]))
            .expect("stored projection parses");
    let mut stored = BTreeMap::new();
    stored.insert("26163".to_owned(), stored_page);
    let requestioned = [requestioned];
    let dirty = select_dirty_county_pages_v1(&requestioned, &stored, 256);
    assert_eq!(
        dirty.len(),
        1,
        "a changed decision question dirties the page"
    );
}

#[test]
fn stored_projection_parser_refuses_template_drift() {
    assert!(
        parse_stored_county_page_v1("26163", "Wayne County", "not a page").is_none(),
        "malformed stored pages are treated as dirty"
    );
    let wrong_subject =
        wayne_markdown_at(1, [0x11; 32]).replace("subject: county/26163", "subject: county/26125");
    assert!(parse_stored_county_page_v1("26163", "Wayne County", &wrong_subject).is_none());
    let wrong_title = wayne_markdown_at(1, [0x11; 32]).replace("# Wayne County", "# Wayne");
    assert!(parse_stored_county_page_v1("26163", "Wayne County", &wrong_title).is_none());
}

#[test]
fn semantic_hash_covers_links_independent_of_known_labels() {
    let labeled = county_page_semantic_sha256_v1(
        "26163",
        "Wayne County",
        COUNTY_DECISION_QUESTION_V1,
        &[(
            COUNTY_MEDIAN_WAGE_LABEL_V1.to_owned(),
            "21.000000".to_owned(),
        )],
        &["2622000".to_owned()],
    );
    let redlink = county_page_semantic_sha256_v1(
        "26163",
        "Wayne County",
        COUNTY_DECISION_QUESTION_V1,
        &[(
            COUNTY_MEDIAN_WAGE_LABEL_V1.to_owned(),
            "21.000000".to_owned(),
        )],
        &["2622000".to_owned()],
    );
    assert_eq!(labeled, redlink);
    let other = county_page_semantic_sha256_v1(
        "26163",
        "Wayne County",
        COUNTY_DECISION_QUESTION_V1,
        &[(
            COUNTY_MEDIAN_WAGE_LABEL_V1.to_owned(),
            "21.000000".to_owned(),
        )],
        &["2622000".to_owned(), "2674900".to_owned()],
    );
    assert_ne!(labeled, other);
}

#[test]
fn plans_sort_signals_and_links_and_refuse_duplicates() {
    let plan = CountyPagePlanV1::try_new(
        "26163".to_owned(),
        "wayne".to_owned(),
        "Wayne County".to_owned(),
        vec![
            signal(
                COUNTY_PHI_HOUR_GRANT_KEY_V1,
                COUNTY_PHI_HOUR_LABEL_V1,
                "1.000000",
            ),
            signal(
                COUNTY_MEDIAN_WAGE_GRANT_KEY_V1,
                COUNTY_MEDIAN_WAGE_LABEL_V1,
                "21.000000",
            ),
        ],
        vec![
            CountyPlaceLinkV1::try_new("2674900".to_owned(), "Riverview city".to_owned())
                .expect("riverview link"),
            detroit_link(),
        ],
    )
    .expect("plan");
    let grant_keys = plan
        .signals()
        .iter()
        .map(CountySignalV1::grant_key)
        .collect::<Vec<_>>();
    assert_eq!(
        grant_keys,
        vec![
            COUNTY_MEDIAN_WAGE_GRANT_KEY_V1,
            COUNTY_PHI_HOUR_GRANT_KEY_V1
        ]
    );
    let geoids = plan
        .place_links()
        .iter()
        .map(CountyPlaceLinkV1::place_geoid)
        .collect::<Vec<_>>();
    assert_eq!(geoids, vec!["2622000", "2674900"]);

    assert_eq!(
        CountyPagePlanV1::try_new(
            "26163".to_owned(),
            "wayne".to_owned(),
            "Wayne County".to_owned(),
            vec![
                signal(
                    COUNTY_MEDIAN_WAGE_GRANT_KEY_V1,
                    COUNTY_MEDIAN_WAGE_LABEL_V1,
                    "21.000000"
                ),
                signal(
                    COUNTY_MEDIAN_WAGE_GRANT_KEY_V1,
                    COUNTY_MEDIAN_WAGE_LABEL_V1,
                    "22.000000"
                ),
            ],
            Vec::new(),
        ),
        Err(SemanticArchiveErrorV1::DuplicateKey)
    );
    assert_eq!(
        CountyPagePlanV1::try_new(
            "26163".to_owned(),
            "wayne".to_owned(),
            "Wayne County".to_owned(),
            Vec::new(),
            vec![detroit_link(), detroit_link()],
        ),
        Err(SemanticArchiveErrorV1::DuplicateKey)
    );
}

#[test]
fn page_input_pins_committed_tick_provenance_citations() {
    let page = wayne_page_input_at(&wayne_plan_full(), 7, [0x11; 32]);
    assert_eq!(page.verified_tick(), 7);
    assert_eq!(page.tick_content_hash(), &[0x11; 32]);
    assert_eq!(page.decision_question(), COUNTY_DECISION_QUESTION_V1);
    assert_eq!(page.signals().len(), 2);
    let median = &page.signals()[0];
    assert_eq!(median.grant_key(), COUNTY_MEDIAN_WAGE_GRANT_KEY_V1);
    assert_eq!(median.label(), COUNTY_MEDIAN_WAGE_LABEL_V1);
    assert_eq!(median.value(), "21.000000");
    assert_eq!(median.citation().source_id(), COMMITTED_TICK_SOURCE_ID_V1);
    assert_eq!(median.citation().locator(), "campaign/7/wayne");
    let phi = &page.signals()[1];
    assert_eq!(phi.grant_key(), COUNTY_PHI_HOUR_GRANT_KEY_V1);
    assert_eq!(phi.value(), "1.000000");
    assert_eq!(phi.citation().locator(), "campaign/7/wayne");
    let targets = page
        .links()
        .iter()
        .map(|link| link.target().clone())
        .collect::<Vec<_>>();
    assert_eq!(
        targets,
        vec![
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, "2622000".to_owned())
                .expect("detroit ref"),
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, "2674900".to_owned())
                .expect("riverview ref"),
        ]
    );
}

#[test]
fn dirty_selection_drains_at_most_the_batch_bound() {
    let plans = ["26093", "26125", "26163"]
        .into_iter()
        .map(|geoid| {
            CountyPagePlanV1::try_new(
                geoid.to_owned(),
                "territory".to_owned(),
                "County".to_owned(),
                Vec::new(),
                Vec::new(),
            )
            .expect("plan")
        })
        .collect::<Vec<_>>();
    let stored = BTreeMap::new();
    let dirty = select_dirty_county_pages_v1(&plans, &stored, 2);
    assert_eq!(dirty.len(), 2, "one receipt drains at most 256 pages");
    let geoids = dirty
        .iter()
        .map(|plan| plan.county_geoid())
        .collect::<Vec<_>>();
    assert_eq!(geoids, vec!["26093", "26125"], "drain follows GEOID order");
}

#[test]
fn batch_refuses_pages_bound_to_another_receipt() {
    let plan = wayne_plan_full();
    let first = wayne_page_input_at(&plan, 1, [0x11; 32]);
    let second = wayne_page_input_at(&plan, 2, [0x22; 32]);
    let batch = ArchiveDirtyBatchV1::try_new(1, [0x11; 32], vec![first]).expect("batch");
    assert_eq!(batch.pages().len(), 1);
    assert_eq!(
        ArchiveDirtyBatchV1::try_new(1, [0x11; 32], vec![second]),
        Err(SemanticArchiveErrorV1::ReceiptMismatch)
    );
}

#[test]
fn pinned_read_sql_stays_read_only_and_scope_exact() {
    assert!(ARCHIVE_COUNTY_MAP_READ_SQL_V1.contains("babylon_meta.territory_county_map_v1"));
    assert!(ARCHIVE_COUNTY_MAP_READ_SQL_V1.contains("county_geoid"));
    assert!(ARCHIVE_COUNTY_MAP_READ_SQL_V1.contains("ORDER BY county_geoid"));

    assert!(ARCHIVE_COUNTY_FIELD_READ_SQL_V1.contains("babylon_state.territory_state_v1"));
    assert!(ARCHIVE_COUNTY_FIELD_READ_SQL_V1.contains("babylon_state.territory_state_field_v1"));
    assert!(ARCHIVE_COUNTY_FIELD_READ_SQL_V1.contains("resolve_tick = $2"));
    assert!(ARCHIVE_COUNTY_FIELD_READ_SQL_V1.contains("territory/median-wage"));
    assert!(ARCHIVE_COUNTY_FIELD_READ_SQL_V1.contains("territory/phi-hour"));

    assert!(ARCHIVE_COUNTY_PAGE_READ_SQL_V1.contains("babylon_meta.archive_page_v1"));
    assert!(ARCHIVE_COUNTY_PAGE_READ_SQL_V1.contains("subject_kind = 'county'"));
    for sql in [
        ARCHIVE_COUNTY_MAP_READ_SQL_V1,
        ARCHIVE_COUNTY_FIELD_READ_SQL_V1,
        ARCHIVE_COUNTY_PAGE_READ_SQL_V1,
    ] {
        assert!(!sql.contains("archive_dirty_receipt_v1"));
        assert!(!sql.contains("tick_event"));
        assert!(!sql.contains("INSERT"));
        assert!(!sql.contains("UPDATE"));
    }
}

#[test]
fn stored_projection_validates_its_components() {
    assert_eq!(
        StoredCountyPageV1::try_new(
            "Wayne County".to_owned(),
            COUNTY_DECISION_QUESTION_V1.to_owned(),
            vec![("Median wage".to_owned(), "21.000000".to_owned())],
            vec!["2622000".to_owned()],
        )
        .expect("stored page")
        .place_geoids(),
        &["2622000".to_owned()]
    );
    assert!(StoredCountyPageV1::try_new(
        "Wayne County".to_owned(),
        COUNTY_DECISION_QUESTION_V1.to_owned(),
        Vec::new(),
        vec!["x".to_owned()],
    )
    .is_err());
}
