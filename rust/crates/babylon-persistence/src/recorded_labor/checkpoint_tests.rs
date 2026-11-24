//! Resume a trace from a disposable source-bound checkpoint.
use super::{RecordedLaborError, RecordedLaborLedger};
use crate::production_projection::recurring_fixture;
use babylon_kernel::content_digest;
use babylon_tick::material_world::{self, MaterialWorldRegister};

#[test]
fn checkpoint_resumes_real_carry_and_refuses_corrupt_or_unrelated_boundaries() {
    let (catalog, state) = recurring_fixture::materials();
    let foundation = [1; 32];
    let opening = MaterialWorldRegister::try_new(&catalog, 0, state).expect("admitted foundation");
    let mut fresh =
        RecordedLaborLedger::from_foundation(&catalog, foundation, &opening).expect("bound ledger");
    let first = opening.prepare_next(&catalog).expect("first close");
    let first_receipts = material_world::decode_material_receipts(first.receipt_bytes())
        .expect("committed receipts");
    fresh
        .advance(&catalog, &opening, first.register(), &first_receipts)
        .expect("first report");
    let checkpoint = fresh.checkpoint().expect("compact cache");
    let restore = |campaign, register, bytes: &[u8], sha| {
        RecordedLaborLedger::restore_checkpoint(&catalog, campaign, register, bytes, sha)
    };
    assert_eq!(
        restore(
            [2; 32],
            first.register(),
            &checkpoint.bytes,
            checkpoint.sha256
        )
        .err(),
        Some(RecordedLaborError::CheckpointBinding)
    );
    assert_eq!(
        restore(foundation, &opening, &checkpoint.bytes, checkpoint.sha256).err(),
        Some(RecordedLaborError::CheckpointBinding)
    );
    let mut altered = checkpoint.bytes.clone();
    *altered.last_mut().expect("positive stock") ^= 1;
    assert_eq!(
        restore(foundation, first.register(), &altered, checkpoint.sha256).err(),
        Some(RecordedLaborError::CheckpointDigest)
    );
    let mut trailing = checkpoint.bytes.clone();
    trailing.push(0);
    assert_eq!(
        restore(
            foundation,
            first.register(),
            &trailing,
            content_digest::sha256_of(&trailing)
        )
        .err(),
        Some(RecordedLaborError::CheckpointFormat)
    );
    let mut resumed = restore(
        foundation,
        first.register(),
        &checkpoint.bytes,
        checkpoint.sha256,
    )
    .expect("restore");
    assert_eq!(
        resumed.checkpoint().expect("canonical re-encoding"),
        checkpoint
    );
    let second = first
        .register()
        .prepare_next(&catalog)
        .expect("second close");
    let r =
        material_world::decode_material_receipts(second.receipt_bytes()).expect("second receipts");
    assert_eq!(
        resumed
            .advance(&catalog, first.register(), second.register(), &r)
            .expect("resumed report"),
        fresh
            .advance(&catalog, first.register(), second.register(), &r)
            .expect("uninterrupted report")
    );
}

#[test]
fn checkpoint_validates_the_physical_quantity_commitment_and_format_version() {
    use super::checkpoint::{self, Source};
    use super::{LaborBasis, LaborId, LaborNode};
    use babylon_recorded_labor::{Book, Position};
    use std::collections::BTreeMap;
    let node = LaborNode::Equipment {
        cohort: LaborId([5; 32]),
    };
    let source = Source {
        foundation: [1; 32],
        catalog: [2; 32],
        register: [3; 32],
        completed: 4,
    };
    let book = Book::from([(
        node,
        Position {
            quantity: 7,
            basis: LaborBasis {
                recorded_micro_hours: 8,
                unknown_opening: true,
            },
        },
    )]);
    let checkpoint = checkpoint::encode(source, &book).expect("cache");
    assert_eq!(
        checkpoint::decode(
            source,
            BTreeMap::from([(node, 8)]),
            &checkpoint.bytes,
            checkpoint.sha256
        ),
        Err(RecordedLaborError::CheckpointBinding)
    );
    let mut unsupported = checkpoint.bytes;
    unsupported[8..10].copy_from_slice(&u16::MAX.to_be_bytes());
    assert_eq!(
        checkpoint::decode(
            source,
            BTreeMap::from([(node, 7)]),
            &unsupported,
            content_digest::sha256_of(&unsupported)
        ),
        Err(RecordedLaborError::CheckpointVersion)
    );
}
