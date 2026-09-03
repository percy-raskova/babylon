use std::str::FromStr;

use babylon_persistence::{
    archive_batch_matches_receipt_v1, archive_contiguous_watermark_v1, classify_archive_receipt_v1,
    classify_archive_sweep_v1, ArchiveCitationV1, ArchiveDirtyBatchV1, ArchiveDossierProducerV1,
    ArchiveLinkV1, ArchivePageInputV1, ArchivePageRefV1, ArchiveReceiptDispositionV1,
    ArchiveReceiptPlanV1, ArchiveSignalV1, ArchiveSubjectKindV1, ArchiveSubjectV1,
    ArchiveWorkerSweepReportV1, CompositeArchiveDossierProducerV1, NullArchiveDossierProducerV1,
    PendingArchiveReceiptV1, SemanticArchiveErrorV1, SemanticArchiveStoreV1,
    ARCHIVE_PENDING_RECEIPTS_SQL_V1, ARCHIVE_SWEEP_MAX_RECEIPTS_V1, ARCHIVE_SWEEP_MAX_SCAN_V1,
    ARCHIVE_SWEEP_WATERMARK_SQL_V1,
};
use postgres::{Config, NoTls};
use uuid::Uuid;

const LIVE_DSN_ENV: &str = "BABYLON_LEGACY_ADOPTER_TEST_DSN";
const LIVE_CANARY_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY";

fn county_subject() -> ArchiveSubjectV1 {
    ArchiveSubjectV1::try_new(
        ArchiveSubjectKindV1::County,
        "26163".to_owned(),
        "Wayne County".to_owned(),
    )
    .expect("county identity")
}

fn county_page_input(resolve_tick: u64, tick_content_hash: [u8; 32]) -> ArchivePageInputV1 {
    ArchivePageInputV1::try_new(
        county_subject(),
        resolve_tick,
        tick_content_hash,
        "Which neighboring place should organizers investigate next?".to_owned(),
        vec![ArchiveSignalV1::try_new(
            "employment".to_owned(),
            "Employment".to_owned(),
            "728576 jobs".to_owned(),
            ArchiveCitationV1::try_new(
                "qcew-2024".to_owned(),
                "fact_qcew_county_rollup county_fips=26163".to_owned(),
            )
            .expect("citation"),
        )
        .expect("signal")],
        vec![ArchiveLinkV1::try_new(
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, "2684000".to_owned())
                .expect("Detroit ref"),
            "Detroit".to_owned(),
        )
        .expect("Detroit link")],
    )
    .expect("page input")
}

fn empty_batch(resolve_tick: u64, tick_content_hash: [u8; 32]) -> ArchiveDirtyBatchV1 {
    ArchiveDirtyBatchV1::try_new(resolve_tick, tick_content_hash, Vec::new()).expect("empty batch")
}

fn non_empty_batch(resolve_tick: u64, tick_content_hash: [u8; 32]) -> ArchiveDirtyBatchV1 {
    ArchiveDirtyBatchV1::try_new(
        resolve_tick,
        tick_content_hash,
        vec![county_page_input(resolve_tick, tick_content_hash)],
    )
    .expect("non-empty batch")
}

#[test]
fn pending_receipts_sql_finds_unconsumed_receipts_in_keyset_order_without_locking() {
    assert!(ARCHIVE_PENDING_RECEIPTS_SQL_V1
        .contains("LEFT JOIN babylon_meta.archive_receipt_consumption_v1"));
    assert!(ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("JOIN babylon_state.tick_commit AS marker"));
    assert!(ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("marker.campaign_id = d.campaign_id"));
    assert!(ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("marker.resolve_tick = d.resolve_tick"));
    assert!(ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("IS NULL"));
    assert!(ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("d.campaign_id = $1"));
    assert!(
        ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("d.resolve_tick > $3"),
        "the sweep pages past deferred receipts by keyset cursor, never OFFSET"
    );
    assert!(!ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("OFFSET"));
    assert!(ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("ORDER BY d.resolve_tick ASC"));
    assert!(
        ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("LIMIT $2"),
        "each pending page is a bounded chunk, not unbounded history"
    );
    assert!(!ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("FOR UPDATE"));
    assert!(!ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("SKIP LOCKED"));
    assert!(!ARCHIVE_PENDING_RECEIPTS_SQL_V1.contains("NOWAIT"));
}

#[test]
fn pending_receipts_sweep_chunk_and_scan_bound_are_positive_bounded_constants() {
    assert_eq!(ARCHIVE_SWEEP_MAX_RECEIPTS_V1, 256);
    assert_eq!(ARCHIVE_SWEEP_MAX_SCAN_V1, 4096);
}

#[test]
fn watermark_sql_derives_the_contiguous_consumed_prefix_from_durable_state() {
    assert!(ARCHIVE_SWEEP_WATERMARK_SQL_V1.contains("JOIN babylon_state.tick_commit AS marker"));
    assert!(ARCHIVE_SWEEP_WATERMARK_SQL_V1.contains("MIN(d.resolve_tick)"));
    assert!(ARCHIVE_SWEEP_WATERMARK_SQL_V1.contains("MAX(d.resolve_tick)"));
    assert!(ARCHIVE_SWEEP_WATERMARK_SQL_V1.contains("c.campaign_id IS NULL"));
    assert!(ARCHIVE_SWEEP_WATERMARK_SQL_V1.contains("d.campaign_id = $1::uuid"));
}

#[test]
fn worker_identity_is_the_store_contract_not_a_local_claim() {
    let source = std::include_str!("../src/archive_worker.rs");
    assert!(
        !source.contains("INSERT INTO babylon_meta.archive_receipt_consumption_v1"),
        "the worker must not re-implement the store's claim-by-insert"
    );
    assert!(
        source.contains("materialize_receipt"),
        "the worker must delegate consumption to the store"
    );
    assert!(
        source.contains("archive_worker_contract_sha256_v1"),
        "the worker must bind to the store's worker identity"
    );
}

#[test]
fn null_producer_returns_empty_but_valid_batch() {
    let producer = NullArchiveDossierProducerV1::new();
    let receipt = PendingArchiveReceiptV1::try_new(1, [0x11; 32]).expect("valid receipt");
    let batch = producer
        .produce(Uuid::nil(), &receipt)
        .expect("null batch is valid");

    assert!(batch.pages().is_empty());
    assert_eq!(empty_batch(1, [0x11; 32]).sha256(), batch.sha256());
}

#[test]
fn pending_receipt_refuses_tick_zero_and_bigint_overflow() {
    assert_eq!(
        PendingArchiveReceiptV1::try_new(0, [0x11; 32]),
        Err(SemanticArchiveErrorV1::InvalidVerifiedTick)
    );
    assert_eq!(
        PendingArchiveReceiptV1::try_new(i64::MAX as u64 + 1, [0x11; 32]),
        Err(SemanticArchiveErrorV1::InvalidVerifiedTick)
    );
}

#[test]
fn empty_sweep_report_has_zero_counts_and_verified_tick() {
    let report = ArchiveWorkerSweepReportV1::default();

    assert!(report.dispositions().is_empty());
    assert_eq!(report.deferred_count(), 0);
    assert_eq!(report.applied_count(), 0);
    assert_eq!(report.already_consumed_count(), 0);
    assert_eq!(report.verified_tick(), 0);
}

#[test]
fn sweep_report_aggregates_dispositions_and_carries_the_persisted_watermark() {
    let report = ArchiveWorkerSweepReportV1::new(
        vec![
            (1, ArchiveReceiptDispositionV1::Deferred),
            (2, ArchiveReceiptDispositionV1::Applied),
            (3, ArchiveReceiptDispositionV1::AlreadyConsumed),
            (4, ArchiveReceiptDispositionV1::Deferred),
        ],
        7,
    );

    assert_eq!(report.deferred_count(), 2);
    assert_eq!(report.applied_count(), 1);
    assert_eq!(report.already_consumed_count(), 1);
    assert_eq!(report.verified_tick(), 7);
    assert_eq!(report.dispositions().len(), 4);
}

#[test]
fn batch_identity_must_match_the_receipt_exactly() {
    let receipt = PendingArchiveReceiptV1::try_new(2, [0x22; 32]).expect("valid receipt");
    let matching = non_empty_batch(2, [0x22; 32]);
    let wrong_tick = non_empty_batch(3, [0x22; 32]);
    let wrong_hash = non_empty_batch(2, [0x33; 32]);

    assert_eq!(
        archive_batch_matches_receipt_v1(&matching, &receipt),
        Ok(())
    );
    assert_eq!(
        archive_batch_matches_receipt_v1(&wrong_tick, &receipt),
        Err(SemanticArchiveErrorV1::ReceiptMismatch)
    );
    assert_eq!(
        archive_batch_matches_receipt_v1(&wrong_hash, &receipt),
        Err(SemanticArchiveErrorV1::ReceiptMismatch)
    );
}

#[test]
fn contiguous_watermark_never_advances_past_a_pending_tick() {
    // No receipts at all: the watermark stays at zero.
    assert_eq!(archive_contiguous_watermark_v1(None, 0), 0);
    // Everything consumed: the watermark is the highest committed receipt.
    assert_eq!(archive_contiguous_watermark_v1(None, 7), 7);
    // Nothing consumed yet: an empty sweep still reports zero, not the backlog max.
    assert_eq!(archive_contiguous_watermark_v1(Some(1), 5), 0);
    // A deferred earlier tick caps the watermark even though later ticks applied.
    assert_eq!(archive_contiguous_watermark_v1(Some(3), 5), 2);
    // A single pending receipt at the backlog tail leaves the prefix before it.
    assert_eq!(archive_contiguous_watermark_v1(Some(5), 5), 4);
}

#[test]
fn classify_receipt_defers_empty_batch_and_materializes_non_empty_batch() {
    let empty = empty_batch(1, [0x11; 32]);
    let non_empty = non_empty_batch(2, [0x22; 32]);

    assert_eq!(
        classify_archive_receipt_v1(&empty),
        ArchiveReceiptPlanV1::Defer
    );
    assert_eq!(
        classify_archive_receipt_v1(&non_empty),
        ArchiveReceiptPlanV1::Materialize
    );
}

#[test]
fn classify_sweep_preserves_order_and_defers_or_materializes() {
    let plans = classify_archive_sweep_v1(vec![
        Ok(empty_batch(1, [0x11; 32])),
        Ok(non_empty_batch(2, [0x22; 32])),
        Ok(empty_batch(3, [0x33; 32])),
    ])
    .expect("ordered plans");

    assert_eq!(
        plans,
        vec![
            ArchiveReceiptPlanV1::Defer,
            ArchiveReceiptPlanV1::Materialize,
            ArchiveReceiptPlanV1::Defer,
        ]
    );
}

#[test]
fn classify_sweep_stops_at_first_producer_error() {
    let result = classify_archive_sweep_v1(vec![
        Ok(empty_batch(1, [0x11; 32])),
        Err(SemanticArchiveErrorV1::InvalidText),
        Ok(empty_batch(3, [0x33; 32])),
    ]);

    assert_eq!(result, Err(SemanticArchiveErrorV1::InvalidText));
}

/// Stub producer returning one scripted batch per receipt.
struct ScriptedProducer(ArchiveDirtyBatchV1);

impl ArchiveDossierProducerV1 for ScriptedProducer {
    fn produce(
        &self,
        _campaign_id: Uuid,
        _receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1> {
        Ok(self.0.clone())
    }
}

fn place_page_input(resolve_tick: u64, tick_content_hash: [u8; 32]) -> ArchivePageInputV1 {
    ArchivePageInputV1::try_new(
        ArchiveSubjectV1::try_new(
            ArchiveSubjectKindV1::Place,
            "2622000".to_owned(),
            "Detroit city".to_owned(),
        )
        .expect("place identity"),
        resolve_tick,
        tick_content_hash,
        "Which overlapping county should organizers investigate next?".to_owned(),
        Vec::new(),
        Vec::new(),
    )
    .expect("place page input")
}

#[test]
fn composite_merges_producer_pages_sorted_and_refuses_duplicate_subjects() {
    let receipt = PendingArchiveReceiptV1::try_new(1, [0x11; 32]).expect("receipt");
    let county_first = CompositeArchiveDossierProducerV1::new(vec![
        Box::new(ScriptedProducer(non_empty_batch(1, [0x11; 32]))),
        Box::new(ScriptedProducer(
            ArchiveDirtyBatchV1::try_new(1, [0x11; 32], vec![place_page_input(1, [0x11; 32])])
                .expect("place batch"),
        )),
    ]);
    let batch = county_first
        .produce(Uuid::nil(), &receipt)
        .expect("composite merge");
    let order = batch
        .pages()
        .iter()
        .map(|page| page.subject().page_ref().clone())
        .collect::<Vec<_>>();
    assert_eq!(
        order,
        vec![
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::County, "26163".to_owned())
                .expect("county ref"),
            ArchivePageRefV1::try_new(ArchiveSubjectKindV1::Place, "2622000".to_owned())
                .expect("place ref"),
        ],
        "merged pages follow deterministic page-reference order"
    );

    let duplicate = CompositeArchiveDossierProducerV1::new(vec![
        Box::new(ScriptedProducer(non_empty_batch(1, [0x11; 32]))),
        Box::new(ScriptedProducer(non_empty_batch(1, [0x11; 32]))),
    ]);
    assert_eq!(
        duplicate.produce(Uuid::nil(), &receipt),
        Err(SemanticArchiveErrorV1::DuplicateKey),
        "two producers may not claim the same page subject"
    );
}

#[test]
fn composite_refuses_merge_beyond_one_batch_bound() {
    let receipt = PendingArchiveReceiptV1::try_new(1, [0x11; 32]).expect("receipt");
    let county_pages = (0..ArchiveDirtyBatchV1::MAX_PAGES)
        .map(|index| {
            ArchivePageInputV1::try_new(
                ArchiveSubjectV1::try_new(
                    ArchiveSubjectKindV1::County,
                    format!("26{index:03}"),
                    "County".to_owned(),
                )
                .expect("full-bound identity"),
                1,
                [0x11; 32],
                "Which neighboring place should organizers investigate next?".to_owned(),
                Vec::new(),
                Vec::new(),
            )
            .expect("full-bound page")
        })
        .collect::<Vec<_>>();
    let single = CompositeArchiveDossierProducerV1::new(vec![
        Box::new(ScriptedProducer(
            ArchiveDirtyBatchV1::try_new(1, [0x11; 32], county_pages).expect("full-bound batch"),
        )),
        Box::new(ScriptedProducer(
            ArchiveDirtyBatchV1::try_new(1, [0x11; 32], vec![place_page_input(1, [0x11; 32])])
                .expect("overflow batch"),
        )),
    ]);
    assert_eq!(
        single.produce(Uuid::nil(), &receipt),
        Err(SemanticArchiveErrorV1::CountyDrainOverflow {
            dirty: ArchiveDirtyBatchV1::MAX_PAGES + 1,
            limit: ArchiveDirtyBatchV1::MAX_PAGES,
        }),
        "a merged dirty set beyond one receipt bound refuses loudly instead of truncating"
    );
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and one committed tick"]
fn live_worker_defers_every_pending_receipt_with_null_producer() {
    let (config, campaign_id) = live_contract_target();
    SemanticArchiveStoreV1::new(&config)
        .install_schema()
        .expect("schema install");
    let mut worker = babylon_persistence::ArchiveWorkerV1::new(&config);
    let report = worker
        .sweep_once(campaign_id, &NullArchiveDossierProducerV1::new())
        .expect("null sweep succeeds");

    assert_eq!(report.applied_count(), 0);
    assert_eq!(report.already_consumed_count(), 0);
    for (_, disposition) in report.dispositions() {
        assert_eq!(*disposition, ArchiveReceiptDispositionV1::Deferred);
    }
}

fn live_contract_target() -> (Config, babylon_persistence::CampaignId) {
    let dsn = std::env::var(LIVE_DSN_ENV).expect("disposable live DSN");
    let expected_canary = std::env::var(LIVE_CANARY_ENV).expect("disposable canary");
    let config = Config::from_str(&dsn).expect("live DSN parses");
    let mut client = config
        .clone()
        .connect(NoTls)
        .expect("live preflight connects");
    let actual_canary: String = client
        .query_one(
            "SELECT pg_catalog.current_setting('babylon.per20_disposable', true)",
            &[],
        )
        .expect("live canary query")
        .try_get(0)
        .expect("live canary decode");
    assert_eq!(actual_canary, expected_canary);

    let campaign_uuid =
        Uuid::parse_str(&std::env::var("BABYLON_ARCHIVE_TEST_CAMPAIGN_ID").expect("live campaign"))
            .expect("live campaign UUID");
    (
        config,
        babylon_persistence::CampaignId::from_uuid(campaign_uuid),
    )
}
