//! Contract tests for the temporary P1 `SQLite` persistence witness.
//!
//! These tests compare `SQLite` against the canonical identities that the
//! `PostgreSQL` campaign store records. The witness stores the same opaque
//! canonical frames and must return identical identities after a cold reopen.

use std::fs;
use std::path::PathBuf;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;

use babylon_kernel::content_digest;
use rusqlite::Connection;

use super::store::FaultPoint;
use super::store::SqliteWitnessStore;
use super::store::WitnessAcceptanceKind;
use super::store::WitnessCommitKind;
use super::store::WitnessCommitReceipt;
use super::store::WitnessError;
use super::store::WitnessJournalEntry;
use super::store::WitnessJournalKind;
use super::store::WitnessKnowledgeGrant;
use super::store::WitnessPeriodCommit;
use super::store::WITNESS_SCHEMA_VERSION;

const NONCE_ONE: [u8; 16] = [0x11; 16];
const NONCE_TWO: [u8; 16] = [0x22; 16];

struct TempRoot(PathBuf);

impl TempRoot {
    fn new() -> Self {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("the test clock is after the epoch")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "babylon-sqlite-witness-{}-{nanos}",
            std::process::id()
        ));
        fs::create_dir_all(&path).expect("the temporary witness root is creatable");
        Self(path)
    }

    fn database(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }
}

impl Drop for TempRoot {
    fn drop(&mut self) {
        let result = fs::remove_dir_all(&self.0);
        assert!(
            result.is_ok(),
            "the temporary witness root must be removable"
        );
    }
}

fn frame(domain: &[u8], period: u64, body: &[u8]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(domain.len() + 8 + body.len());
    bytes.extend_from_slice(domain);
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(body);
    bytes
}

fn opening() -> (Vec<u8>, Vec<u8>) {
    (
        frame(b"babylon.test.foundation.v1\0", 0, b"captured-content"),
        frame(b"babylon.test.material-state.v1\0", 0, b"opening-register"),
    )
}

fn period_frames(period: u64, label: &[u8]) -> (Vec<u8>, Vec<u8>) {
    (
        frame(b"babylon.test.material-state.v1\0", period, label),
        frame(b"babylon.test.tick-receipts.v1\0", period, label),
    )
}

fn assert_existing(receipt: &WitnessCommitReceipt, period: u64) {
    assert_eq!(
        receipt.kind,
        WitnessCommitKind::Existing,
        "period {period} must replay as an existing canonical commitment"
    );
    assert_eq!(
        receipt.period, period,
        "the replayed receipt keeps its period"
    );
}

fn commit_fixture<'a>(
    period: u64,
    register: &'a [u8],
    receipts: &'a [u8],
    journal: &'a [WitnessJournalEntry<'a>],
    knowledge: &'a [WitnessKnowledgeGrant<'a>],
) -> WitnessPeriodCommit<'a> {
    let world = format!("world-identity-{period}");
    WitnessPeriodCommit {
        period,
        world_hash: content_digest::sha256_of(world.as_bytes()),
        state_hash: content_digest::sha256_of(register),
        register,
        receipts,
        journal,
        knowledge,
    }
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one conformance scenario asserts the whole two-period trajectory"
)]
fn two_period_sqlite_witness_matches_postgres_canonical_identities() {
    let root = TempRoot::new();
    let database = root.database("campaign.sqlite");
    let (foundation, initial_register) = opening();
    let (register_one, receipts_one) = period_frames(1, b"period-one-state");
    let (register_two, receipts_two) = period_frames(2, b"period-two-state");
    let period_one_journal = [
        WitnessJournalEntry {
            kind: WitnessJournalKind::FreightUnresolved,
            subject_kind: Some(b"freight-route"),
            subject_id: Some(b"michigan-route-1"),
            payload: b"unresolved-freight-lot",
        },
        WitnessJournalEntry {
            kind: WitnessJournalKind::ChoiceReceipt,
            subject_kind: Some(b"choice-encounter"),
            subject_id: Some(b"encounter-1"),
            payload: b"choice-receipt-payload",
        },
    ];
    let choice = [WitnessJournalEntry {
        kind: WitnessJournalKind::ChoiceReceipt,
        subject_kind: Some(b"choice-encounter"),
        subject_id: Some(b"encounter-1"),
        payload: b"choice-receipt-payload",
    }];
    let resolved = [WitnessJournalEntry {
        kind: WitnessJournalKind::FreightResolved,
        subject_kind: Some(b"freight-route"),
        subject_id: Some(b"michigan-route-1"),
        payload: b"resolved-freight-lot",
    }];
    let earned = [WitnessKnowledgeGrant {
        player_id: 42,
        subject_kind: b"county",
        subject_id: b"michigan-wayne",
        observed_period: 1,
        payload: b"earned-county-fact".as_slice(),
    }];

    let period_one = commit_fixture(
        1,
        &register_one,
        &receipts_one,
        &period_one_journal,
        &earned,
    );
    let period_one_choice = commit_fixture(1, &register_one, &receipts_one, &choice, &earned);
    let period_two = commit_fixture(2, &register_two, &receipts_two, &resolved, &[]);

    let mut store = SqliteWitnessStore::open_at(&database).expect("the witness opens");
    store
        .capture_opening(&foundation, &initial_register)
        .expect("the opening is captured once");
    let accepted = store
        .accept_command(1, NONCE_ONE, b"organizer-command-before-period-1")
        .expect("the organizer command is durable before the advance");
    assert_eq!(
        accepted.kind,
        WitnessAcceptanceKind::Inserted,
        "the first command acceptance inserts"
    );

    let first = store
        .commit_period(&period_one)
        .expect("period one commits with the accepted command");
    assert_eq!(
        first.kind,
        WitnessCommitKind::Inserted,
        "period one inserts"
    );
    assert_eq!(
        first.world_hash, period_one.world_hash,
        "the witness preserves the caller's canonical world identity"
    );
    assert_eq!(
        first.state_hash, period_one.state_hash,
        "the witness preserves the caller's canonical state identity"
    );
    let with_choice = store
        .commit_period(&period_one_choice)
        .expect_err("a different canonical choice receipt for period one must refuse");
    assert!(
        matches!(
            with_choice,
            WitnessError::ConflictingPeriodCommit { period: 1 }
        ),
        "period one already has one immutable canonical commitment"
    );
    assert_eq!(
        store
            .read_scoped_subject(42, b"county", 1)
            .expect("period one knowledge is disclosed at period one"),
        b"earned-county-fact".as_slice(),
        "the earned fact is readable at its acquisition period"
    );

    let second = store
        .commit_period(&period_two)
        .expect("period two resolves the crossing freight");
    assert_eq!(
        second.kind,
        WitnessCommitKind::Inserted,
        "period two inserts"
    );
    assert!(
        second.journal_tail_seq > first.journal_tail_seq,
        "period two extends the permanent journal"
    );
    let replayed_second = store
        .commit_period(&period_two)
        .expect("an identical period two replay is idempotent");
    assert_existing(&replayed_second, 2);
    assert_eq!(
        replayed_second.journal_tail_seq, second.journal_tail_seq,
        "replay must not append a second period commit"
    );
    assert_eq!(
        replayed_second.journal_tail_hash, second.journal_tail_hash,
        "replay must reproduce the same journal tail identity"
    );
    drop(store);

    let mut reopened = SqliteWitnessStore::open_at(&database).expect("the witness cold reopens");
    let cold_one = reopened
        .commit_period(&period_one)
        .expect("the period one identity survives a cold reopen");
    assert_existing(&cold_one, 1);
    assert_eq!(
        cold_one.world_hash, first.world_hash,
        "cold reopen preserves the period one world identity"
    );
    assert_eq!(
        cold_one.state_hash, first.state_hash,
        "cold reopen preserves the period one state identity"
    );
    assert_eq!(
        cold_one.journal_tail_seq, first.journal_tail_seq,
        "cold reopen preserves the period one journal tail"
    );
    let cold_two = reopened
        .commit_period(&period_two)
        .expect("the period two identity survives a cold reopen");
    assert_existing(&cold_two, 2);
    assert_eq!(
        cold_two.journal_tail_hash, second.journal_tail_hash,
        "cold reopen preserves the period two journal identity"
    );
    assert_eq!(
        reopened
            .read_scoped_subject(42, b"county", 1)
            .expect("the earned fact survives a cold reopen"),
        b"earned-county-fact".as_slice(),
        "the knowledge payload is byte-identical after cold reopen"
    );

    let footprint = reopened
        .measure_footprint()
        .expect("the witness reports separate storage metrics");
    assert!(footprint.main_db_bytes > 0, "the main database has bytes");
    assert!(footprint.index_bytes > 0, "the index b-trees have bytes");
    assert!(
        footprint.rss_bytes.is_some(),
        "the host reports a resident set size"
    );

    let exported = root.database("exported.sqlite");
    let report = reopened
        .export_online_backup(&exported)
        .expect("the committed boundary exports online");
    assert!(
        report.integrity_verified,
        "the export passes integrity and identity verification"
    );
    assert!(
        report.destination_bytes > 0,
        "the export destination has bytes"
    );
    assert_eq!(
        reopened
            .measure_footprint()
            .expect("the footprint reports the last export")
            .export_bytes,
        report.destination_bytes,
        "the footprint records the published export bytes"
    );

    let mut exported_store =
        SqliteWitnessStore::open_at(&exported).expect("the published export opens independently");
    let exported_two = exported_store
        .commit_period(&period_two)
        .expect("the export preserves the period two identity");
    assert_existing(&exported_two, 2);
    assert_eq!(
        exported_two.journal_tail_hash, second.journal_tail_hash,
        "the export preserves the journal tail identity"
    );
    assert_eq!(
        exported_store
            .read_scoped_subject(42, b"county", 1)
            .expect("the export preserves earned authority"),
        b"earned-county-fact".as_slice(),
        "the export preserves the earned knowledge payload"
    );
}

#[test]
fn sqlite_witness_command_nonce_idempotency_and_single_commitment_refusal() {
    let root = TempRoot::new();
    let database = root.database("campaign.sqlite");
    let (foundation, initial_register) = opening();
    let mut store = SqliteWitnessStore::open_at(&database).expect("the witness opens");
    store
        .capture_opening(&foundation, &initial_register)
        .expect("the opening is captured once");

    let first = store
        .accept_command(1, NONCE_ONE, b"equal-command-bytes")
        .expect("the first commitment is accepted");
    assert_eq!(
        first.kind,
        WitnessAcceptanceKind::Inserted,
        "the first acceptance inserts"
    );
    let replay = store
        .accept_command(1, NONCE_ONE, b"equal-command-bytes")
        .expect("the equal retry returns the original acceptance");
    assert_eq!(
        replay.kind,
        WitnessAcceptanceKind::Existing,
        "the equal retry is not a new commitment"
    );
    assert_eq!(
        replay.acceptance_seq, first.acceptance_seq,
        "the equal retry returns the original acceptance sequence"
    );
    assert_eq!(
        replay.payload_hash, first.payload_hash,
        "the equal retry returns the original payload identity"
    );

    let conflicting = store
        .accept_command(1, NONCE_ONE, b"different-command-bytes")
        .expect_err("one nonce cannot authenticate different bytes");
    assert!(
        matches!(conflicting, WitnessError::ConflictingNonce),
        "the same nonce with different bytes is a conflict"
    );
    let second_commitment = store
        .accept_command(1, NONCE_TWO, b"equal-command-bytes")
        .expect_err("one period has one immutable accepted commitment");
    assert!(
        matches!(
            second_commitment,
            WitnessError::PeriodCommitmentAlreadyAccepted { period: 1 }
        ),
        "a second distinct commitment for the period refuses even with another nonce"
    );

    let (register, receipts) = period_frames(1, b"period-one-state");
    let period_one = commit_fixture(1, &register, &receipts, &[], &[]);
    store
        .commit_period(&period_one)
        .expect("period one commits with the accepted command");
    let retried_after_commit = store
        .accept_command(1, NONCE_ONE, b"equal-command-bytes")
        .expect("the original acknowledgement replays after the advance");
    assert_eq!(
        retried_after_commit.kind,
        WitnessAcceptanceKind::Existing,
        "a lost acknowledgement reconciles after the period advanced"
    );
    assert_eq!(
        retried_after_commit.acceptance_seq, first.acceptance_seq,
        "the reconciled acknowledgement keeps its original sequence"
    );
    store.inject_fault(FaultPoint::AfterAcceptBeforeAck);
    let lost = store
        .accept_command(2, NONCE_TWO, b"period-two-command")
        .expect_err("the injected fault loses the acceptance acknowledgement");
    assert!(
        matches!(lost, WitnessError::InjectedFault),
        "the acceptance seam reports its injected fault"
    );
    let next = store
        .accept_command(2, NONCE_TWO, b"period-two-command")
        .expect("the durable acceptance reconciles after the lost acknowledgement");
    assert_eq!(
        next.kind,
        WitnessAcceptanceKind::Existing,
        "the reconciled acceptance is not a second commitment"
    );
    assert_eq!(next.period, 2, "the acceptance is bound to the next period");
}

#[test]
fn sqlite_witness_scoped_read_refuses_undisclosed_or_future_acquired_fact() {
    let root = TempRoot::new();
    let database = root.database("campaign.sqlite");
    let (foundation, initial_register) = opening();
    let mut store = SqliteWitnessStore::open_at(&database).expect("the witness opens");
    store
        .capture_opening(&foundation, &initial_register)
        .expect("the opening is captured once");
    let (register_one, receipts_one) = period_frames(1, b"period-one-state");
    let period_one = commit_fixture(1, &register_one, &receipts_one, &[], &[]);
    store
        .commit_period(&period_one)
        .expect("period one commits without the future fact");
    assert!(
        matches!(
            store.read_scoped_subject(9, b"county", 1),
            Err(WitnessError::UndisclosedSubject)
        ),
        "period one does not disclose a fact acquired later"
    );

    let (register_two, receipts_two) = period_frames(2, b"period-two-state");
    let source = [WitnessJournalEntry {
        kind: WitnessJournalKind::ChoiceReceipt,
        subject_kind: Some(b"choice-encounter"),
        subject_id: Some(b"encounter-2"),
        payload: b"choice-receipt-period-two",
    }];
    let future_fact = [WitnessKnowledgeGrant {
        player_id: 9,
        subject_kind: b"county",
        subject_id: b"michigan-wayne",
        observed_period: 1,
        payload: b"fact-only-earned-in-period-two".as_slice(),
    }];
    let period_two = commit_fixture(2, &register_two, &receipts_two, &source, &future_fact);
    store
        .commit_period(&period_two)
        .expect("period two commits the earned fact");
    assert!(
        matches!(
            store.read_scoped_subject(9, b"county", 1),
            Err(WitnessError::UndisclosedSubject)
        ),
        "an observation period of one does not disclose a period-two acquisition"
    );
    assert_eq!(
        store
            .read_scoped_subject(9, b"county", 2)
            .expect("the acquisition period discloses the fact"),
        b"fact-only-earned-in-period-two".as_slice(),
        "the earned payload is readable at its acquisition period"
    );
    assert!(
        matches!(
            store.read_scoped_subject(9, b"county", 3),
            Err(WitnessError::FuturePeriod {
                current: 2,
                requested: 3
            })
        ),
        "a read beyond the committed present refuses"
    );
    assert!(
        matches!(
            store.read_scoped_subject(9, b"place", 2),
            Err(WitnessError::UndisclosedSubject)
        ),
        "an undisclosed subject refuses"
    );
    assert!(
        matches!(
            store.read_scoped_subject(10, b"county", 2),
            Err(WitnessError::UndisclosedSubject)
        ),
        "another player's fact is not disclosed"
    );
}

#[test]
fn sqlite_witness_crash_points_preserve_atomic_state_and_single_execution() {
    let root = TempRoot::new();
    let database = root.database("campaign.sqlite");
    let (foundation, initial_register) = opening();
    let (register_one, receipts_one) = period_frames(1, b"period-one-state");
    let (register_two, receipts_two) = period_frames(2, b"period-two-state");
    let period_one = commit_fixture(1, &register_one, &receipts_one, &[], &[]);
    let period_two = commit_fixture(2, &register_two, &receipts_two, &[], &[]);

    let mut store = SqliteWitnessStore::open_at(&database).expect("the witness opens");
    store
        .capture_opening(&foundation, &initial_register)
        .expect("the opening is captured once");
    store
        .accept_command(1, NONCE_ONE, b"command-before-the-crash")
        .expect("the command is durable before the crash");
    store.inject_fault(FaultPoint::BeforeCommit);
    let before = store
        .commit_period(&period_one)
        .expect_err("the injected fault aborts before the commit transaction");
    assert!(
        matches!(before, WitnessError::InjectedFault),
        "the seam reports its injected fault"
    );
    drop(store);

    let mut reopened = SqliteWitnessStore::open_at(&database).expect("the witness cold reopens");
    let after_crash = reopened
        .commit_period(&period_one)
        .expect("a crash before commit leaves the accepted command reconstructible");
    assert_eq!(
        after_crash.kind,
        WitnessCommitKind::Inserted,
        "the interrupted period was never visible"
    );
    let single = reopened
        .commit_period(&period_one)
        .expect("the post-crash retry is idempotent");
    assert_existing(&single, 1);
    assert_eq!(
        single.journal_tail_hash, after_crash.journal_tail_hash,
        "the consumed command executes exactly once"
    );
    assert_eq!(
        single.journal_tail_seq, after_crash.journal_tail_seq,
        "the retry appends no second command record"
    );
    drop(reopened);

    let mut lost_ack = SqliteWitnessStore::open_at(&database).expect("the witness reopens again");
    lost_ack.inject_fault(FaultPoint::AfterCommitBeforeAck);
    let lost = lost_ack
        .commit_period(&period_two)
        .expect_err("the injected fault loses the acknowledgement");
    assert!(
        matches!(lost, WitnessError::InjectedFault),
        "the post-commit seam reports its injected fault"
    );
    drop(lost_ack);

    let mut reconciled = SqliteWitnessStore::open_at(&database).expect("the witness reconciles");
    let reconciled_receipt = reconciled
        .commit_period(&period_two)
        .expect("the committed period reconciles exactly");
    assert_existing(&reconciled_receipt, 2);
    let reconciled_again = reconciled
        .commit_period(&period_two)
        .expect("the reconciled period stays idempotent");
    assert_existing(&reconciled_again, 2);
    assert_eq!(
        reconciled_again.journal_tail_seq, reconciled_receipt.journal_tail_seq,
        "reconciliation never performs the period twice"
    );

    let destination = root.database("interrupted.sqlite");
    reconciled.inject_fault(FaultPoint::DuringExport);
    let interrupted = reconciled
        .export_online_backup(&destination)
        .expect_err("the injected fault aborts the export before publication");
    assert!(
        matches!(interrupted, WitnessError::InjectedFault),
        "the export seam reports its injected fault"
    );
    assert!(
        !destination.exists(),
        "an interrupted export publishes no partial destination"
    );
    let published = reconciled
        .export_online_backup(&destination)
        .expect("the source remains exportable after an interrupted export");
    assert!(published.integrity_verified, "the retried export verifies");
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one refusal scenario covers each admitted malformed input"
)]
fn sqlite_witness_refuses_truncated_payload_and_wrong_schema_version() {
    let root = TempRoot::new();
    let truncated_database = root.database("truncated.sqlite");
    let (foundation, initial_register) = opening();
    let (register, receipts) = period_frames(1, b"period-one-state");
    let source = [WitnessJournalEntry {
        kind: WitnessJournalKind::ChoiceReceipt,
        subject_kind: Some(b"choice-encounter"),
        subject_id: Some(b"encounter-1"),
        payload: b"choice-receipt-payload",
    }];
    let earned = [WitnessKnowledgeGrant {
        player_id: 7,
        subject_kind: b"county",
        subject_id: b"michigan-wayne",
        observed_period: 1,
        payload: b"stored-fact-payload",
    }];
    let period_one = commit_fixture(1, &register, &receipts, &source, &earned);

    let mut store = SqliteWitnessStore::open_at(&truncated_database).expect("the witness opens");
    store
        .capture_opening(&foundation, &initial_register)
        .expect("the opening is captured once");
    store
        .commit_period(&period_one)
        .expect("period one commits the earned fact");
    drop(store);

    let raw = Connection::open(&truncated_database).expect("the witness database opens raw");
    raw.execute(
        "UPDATE knowledge_grant SET payload = substr(payload, 1, length(payload) - 1)",
        [],
    )
    .expect("the test truncates the stored knowledge payload");
    drop(raw);

    let reopened = SqliteWitnessStore::open_at(&truncated_database).expect("the witness reopens");
    let refusal = reopened
        .read_scoped_subject(7, b"county", 1)
        .expect_err("a truncated stored payload must refuse");
    assert!(
        matches!(
            refusal,
            WitnessError::IntegrityMismatch {
                field: "knowledge_grant.payload"
            }
        ),
        "the stored payload hash detects truncation"
    );

    let version_database = root.database("version.sqlite");
    let version_store = SqliteWitnessStore::open_at(&version_database).expect("the witness opens");
    drop(version_store);
    let raw = Connection::open(&version_database).expect("the version database opens raw");
    raw.pragma_update(None, "user_version", 99)
        .expect("the test writes a wrong schema version");
    drop(raw);
    let Err(version_refusal) = SqliteWitnessStore::open_at(&version_database) else {
        panic!("a wrong schema version must refuse");
    };
    match version_refusal {
        WitnessError::SchemaVersion { expected, actual } => {
            assert_eq!(expected, WITNESS_SCHEMA_VERSION);
            assert_eq!(actual, 99);
        }
        other => panic!("expected a schema version refusal, received {other}"),
    }

    let input_database = root.database("input.sqlite");
    let (foundation, initial_register) = opening();
    let mut input_store = SqliteWitnessStore::open_at(&input_database).expect("the witness opens");
    input_store
        .capture_opening(&foundation, &initial_register)
        .expect("the opening is captured once");
    let empty_register = commit_fixture(1, &[], &receipts, &[], &[]);
    let empty = input_store
        .commit_period(&empty_register)
        .expect_err("an empty register is truncated");
    assert!(
        matches!(empty, WitnessError::TruncatedPayload { field: "register" }),
        "an empty canonical register refuses before any write"
    );
    let oversized = vec![0_u8; super::store::MAX_WITNESS_REGISTER_BYTES + 1];
    let oversized_register = commit_fixture(1, &oversized, &receipts, &[], &[]);
    let too_large = input_store
        .commit_period(&oversized_register)
        .expect_err("an oversized register is bounded out");
    assert!(
        matches!(
            too_large,
            WitnessError::PayloadTooLarge {
                field: "register",
                ..
            }
        ),
        "the register allowance refuses an oversized frame"
    );
    let unsourced = commit_fixture(1, &register, &receipts, &[], &earned);
    let missing_source = input_store
        .commit_period(&unsourced)
        .expect_err("knowledge without a journal record has no source");
    assert!(
        matches!(missing_source, WitnessError::KnowledgeSourceMissing),
        "earned knowledge must cite a period journal record"
    );
    let duplicate = [
        WitnessKnowledgeGrant {
            player_id: 7,
            subject_kind: b"county",
            subject_id: b"michigan-wayne",
            observed_period: 1,
            payload: b"first-fact-payload",
        },
        WitnessKnowledgeGrant {
            player_id: 7,
            subject_kind: b"county",
            subject_id: b"michigan-wayne",
            observed_period: 1,
            payload: b"second-fact-payload",
        },
    ];
    let duplicated = commit_fixture(1, &register, &receipts, &source, &duplicate);
    let duplicate_refusal = input_store
        .commit_period(&duplicated)
        .expect_err("one identity acquires once per period");
    assert!(
        matches!(duplicate_refusal, WitnessError::DuplicateKnowledgeGrant),
        "a duplicate knowledge identity refuses"
    );
    let reserved = [WitnessJournalEntry {
        kind: WitnessJournalKind::OrganizerCommandConsumed,
        subject_kind: None,
        subject_id: None,
        payload: b"forged-command-record",
    }];
    let reserved_candidate = commit_fixture(1, &register, &receipts, &reserved, &[]);
    let reserved_refusal = input_store
        .commit_period(&reserved_candidate)
        .expect_err("a caller cannot forge a witness-owned journal record");
    assert!(
        matches!(
            reserved_refusal,
            WitnessError::ReservedJournalKind { code: 2 }
        ),
        "the command-consumption record stays witness-owned"
    );
    let orphan_resolution = [WitnessJournalEntry {
        kind: WitnessJournalKind::FreightResolved,
        subject_kind: Some(b"freight-route"),
        subject_id: Some(b"never-shipped"),
        payload: b"orphan-resolution",
    }];
    let orphan_candidate = commit_fixture(1, &register, &receipts, &orphan_resolution, &[]);
    let orphan_refusal = input_store
        .commit_period(&orphan_candidate)
        .expect_err("a resolution must reference an unresolved subject");
    assert!(
        matches!(orphan_refusal, WitnessError::UnresolvedFreightMissing),
        "an orphan freight resolution refuses"
    );
}
