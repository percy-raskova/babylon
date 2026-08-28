use std::mem::size_of;

use babylon_kernel::tick_content_hash::RefDigestV1;
use postgres::{Config, NoTls};

use super::{
    attempt_install_transaction, conflict, install_michigan_spatial_reference_products,
    install_michigan_spatial_reference_products_using, prepare_install_transaction,
    rollback_preserving, CommitAttempt, SpatialReferenceInstallDisposition,
    SpatialReferenceInstallError, SpatialReferenceRelation,
};
use crate::{
    build_representative_h3_cohort_v1, install_representative_h3_cohort, H3CellId,
    H3ReferenceCohort, H3ReferenceInstallDisposition,
};

const SOURCE_FIXTURE: &[u8] = include_bytes!("../tests/fixtures/h3_reference_source_v1.bin");
const SOURCE_DOMAIN: &[u8] = b"babylon.h3.reference-source.v1\0";
const SOURCE_COUNT: usize = 48_764;
const BACKEND_TERMINATION_TIMEOUT_MILLIS: i64 = 5_000;
const ARTIFACT_DIGEST: [u8; 32] = [
    0xe6, 0x0d, 0x93, 0xa4, 0x3d, 0x6c, 0x66, 0xe8, 0x4f, 0x1e, 0x53, 0xec, 0xaf, 0x63, 0x3a, 0xf5,
    0x91, 0x1b, 0xd5, 0xb4, 0x8b, 0x0e, 0xf0, 0xad, 0x6a, 0x01, 0x2f, 0x6d, 0x9f, 0x5b, 0x13, 0xa9,
];
const EXPECTED_COUNTS: [i64; 8] = [7, 3_285, 745, 45_572, 22_509, 11_833, 31_881, 4_813];

pub(crate) fn verify_commit_protocol(config: &Config, admin: &Config) {
    let cohort = representative_cohort();
    let h3_report = install_representative_h3_cohort(config, &cohort)
        .expect("the exact H3 cohort must install before its reference products");
    assert_eq!(
        h3_report.disposition(),
        H3ReferenceInstallDisposition::Installed
    );
    assert_eq!(reference_counts(config), [0; 8]);

    let mut forced_failure = |client: &mut postgres::Client, bundle: &_| {
        let transaction = prepare_install_transaction(client, bundle)?;
        rollback_preserving(transaction, conflict(SpatialReferenceRelation::Products))
    };
    assert_eq!(
        install_michigan_spatial_reference_products_using(config, &cohort, &mut forced_failure,),
        Err(SpatialReferenceInstallError::Conflict {
            relation: SpatialReferenceRelation::Products,
        })
    );
    assert_eq!(reference_counts(config), [0; 8]);

    let mut first_attempt = true;
    let mut committed_ambiguity = |client: &mut postgres::Client, bundle: &_| {
        let backend_pid = backend_pid(client);
        let outcome = attempt_install_transaction(client, bundle)?;
        if first_attempt {
            first_attempt = false;
            assert_eq!(outcome, CommitAttempt::Committed);
            terminate_backend(admin, backend_pid);
            Ok(CommitAttempt::Ambiguous)
        } else {
            Ok(outcome)
        }
    };
    let report = install_michigan_spatial_reference_products_using(
        config,
        &cohort,
        &mut committed_ambiguity,
    )
    .expect("a committed ambiguous install must reconcile to the exact bundle");
    assert_eq!(
        report.disposition(),
        SpatialReferenceInstallDisposition::ReconciledAfterAmbiguousCommit
    );
    assert_eq!(report.product_count(), 7);
    assert_eq!(report.data_row_count(), 120_638);
    assert_eq!(report.commit_attempts(), 1);
    assert_eq!(reference_counts(config), EXPECTED_COUNTS);

    let retry = install_michigan_spatial_reference_products(config, &cohort)
        .expect("an exact bundle retry must be idempotent");
    assert_eq!(
        retry.disposition(),
        SpatialReferenceInstallDisposition::AlreadyPresent
    );
    assert_eq!(retry.commit_attempts(), 0);
    assert_eq!(reference_counts(config), EXPECTED_COUNTS);

    mutate_product_digest(config);
    let mutated_counts = reference_counts(config);
    assert_eq!(
        install_michigan_spatial_reference_products(config, &cohort),
        Err(SpatialReferenceInstallError::Conflict {
            relation: SpatialReferenceRelation::Products,
        })
    );
    assert_eq!(reference_counts(config), mutated_counts);
}

fn backend_pid(client: &mut postgres::Client) -> i32 {
    client
        .query_one("SELECT pg_catalog.pg_backend_pid()", &[])
        .unwrap()
        .try_get(0)
        .unwrap()
}

fn terminate_backend(admin: &Config, backend_pid: i32) {
    let terminated: bool = admin
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT pg_catalog.pg_terminate_backend($1, $2)",
            &[&backend_pid, &BACKEND_TERMINATION_TIMEOUT_MILLIS],
        )
        .unwrap()
        .try_get(0)
        .unwrap();
    assert!(terminated);
}

fn mutate_product_digest(config: &Config) {
    let changed = config
        .connect(NoTls)
        .unwrap()
        .execute(
            "UPDATE babylon_ref.reference_product \
             SET artifact_sha256 = pg_catalog.decode(pg_catalog.repeat('00', 32), 'hex') \
             WHERE product_code = 'dim_county'",
            &[],
        )
        .unwrap();
    assert_eq!(changed, 1);
}

fn reference_counts(config: &Config) -> [i64; 8] {
    let row = config
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT \
                (SELECT pg_catalog.count(*) FROM babylon_ref.reference_product), \
                (SELECT pg_catalog.count(*) FROM babylon_ref.county_identity), \
                (SELECT pg_catalog.count(*) FROM babylon_ref.place_identity), \
                (SELECT pg_catalog.count(*) FROM babylon_ref.h3_land_fraction), \
                (SELECT pg_catalog.count(*) FROM babylon_ref.h3_population_count), \
                (SELECT pg_catalog.count(*) FROM babylon_ref.h3_workplace_count), \
                (SELECT pg_catalog.count(*) FROM babylon_ref.county_h3_land_area), \
                (SELECT pg_catalog.count(*) FROM babylon_ref.county_place_h3_land_area)",
            &[],
        )
        .unwrap();
    std::array::from_fn(|index| row.get(index))
}

fn representative_cohort() -> H3ReferenceCohort {
    build_representative_h3_cohort_v1(RefDigestV1::from_bytes(ARTIFACT_DIGEST), &source_cells())
        .unwrap()
}

fn source_cells() -> Vec<H3CellId> {
    assert!(SOURCE_FIXTURE.starts_with(SOURCE_DOMAIN));
    let count_offset = SOURCE_DOMAIN.len();
    let payload_offset = count_offset + size_of::<u64>();
    let count = u64::from_be_bytes(
        SOURCE_FIXTURE[count_offset..payload_offset]
            .try_into()
            .unwrap(),
    );
    assert_eq!(usize::try_from(count).unwrap(), SOURCE_COUNT);
    assert_eq!(
        SOURCE_FIXTURE.len(),
        payload_offset + SOURCE_COUNT * size_of::<u64>()
    );
    SOURCE_FIXTURE[payload_offset..]
        .chunks_exact(size_of::<u64>())
        .take(SOURCE_COUNT)
        .map(|chunk| {
            let raw = u64::from_be_bytes(chunk.try_into().unwrap());
            H3CellId::try_from(raw).unwrap()
        })
        .collect()
}
