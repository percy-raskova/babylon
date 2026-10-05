# National qualification: measured failure and bounded repair

This record preserves the October 4 development run and its repair boundary.
It supplies evidence for PER-341, PER-342 and PER-343. It does not change game
law, qualification policy or Linear scope. No two-period, 52-period, 325-period
or native play qualification has passed. Actual play has not assessed enjoyment.

## Actual national result

The interrupted `current-national-playable-smoke004` used source
`e26576965e1af04504872b85baa31993b4105e89` and all 3,144 counties. Its captured
policy SHA-256 was
`aa571e8ad694e8af37f8ff298039db2e8499bf9fa8763c7c0d538382e7ab22af`.
The authoritative current policy is
[national_storage_qualification_v3.json](../../../contracts/national_storage_qualification_v3.json).
Its decimal 40 MB ceiling, 23 MB target and 10 GB retained-save limit remain
unchanged. A model year has thirteen periods. Projections cannot pass the
separate 325-period gate.

| Boundary | Observation | Disposition |
| --- | --- | --- |
| Opening | Postgres retained 284,882,611 bytes | Measured baseline |
| Period 1 advance | 63.608457838 seconds | Committed |
| Period 1 Archive and dossiers | 166.041777085 seconds. No pending receipt | Completed |
| Period 1 complete production read | Approximately 119 seconds | Completed |
| Period 1 recovery | Retained database 330,200,755 bytes after reopen | Completed |
| Period 1 charged growth | 45,809,664 bytes, including positive component growth and residual | Failed 40 MB ceiling |
| Period 2 advance | 65.059275628 seconds | Committed |
| Period 2 Archive | No pages or consumption marker published | Failed deadline. Incomplete |

Period 1's signed net growth was 45,318,144 bytes. Positive parent growth accounts
for 45,637,632 bytes and residual growth adds 172,032 bytes.
491,520 bytes of unrelated shrinkage cannot hide growth. Recovery added no
charged retained growth. The report lists WAL separately. It does not add WAL to
retained save bytes or use WAL to reduce them.

The first-period constant-growth projection is 595,525,632 bytes per model year
and 15,173,023,411 bytes after 325 periods including the opening. These are
projections from one measured boundary, not sustained-growth evidence.

Period 2 reconstruction reached 10,455,660 KiB resident memory and 2,020,896 KiB
swap. The existing host `cgroup` throttled allocation with its original limits.
SQL clients were outside transactions. The operator stopped the exact owned
engine process after verifying its executable and start identity. The original
failed timing result remains failed regardless of a later repair.

The committed marker identities were:

- Period 1: `a1e973a3e1fa7fcf4d42d2a850c349c970c4ae198eba2aaef980b3b7e03e1cae`.
- Period 2: `fb86900461c9a8297f9551208a23a834db094ccfb62540771cd1f1d246089c11`.

Local evidence remains under
`reports/test-results/per342-qualification/2026-10-04/`. Preserve
`current-national-playable-smoke004`, its launch directory and
`archive2-delay-diagnostic002`. The launcher log SHA-256 is
`b6a752687a773b75a8fd33fb1512d0225c4db41dc96692489c99793e57eda3c4`.

## Bounded repair

The repair removes the permanently joined foundation byte vector. One borrowed
descriptor supplies ordered framing, checked length, digest and exact component
equality. Full exports remain explicit and fallible. The canonical format and
hashes keep their original values. The decoder refuses corruption, truncation
and trailing bytes.

Archive admits and validates the prior register first, retains its organizer
configuration and state, then releases that register before admitting the
current register. Archive uses the existing authenticated envelope attestation
instead of allocating another complete envelope. Durable reconciliation still
compares complete canonical bytes.

The qualification reader now exists only for its complete production read.
The reader releases its admitted opening before recovery and the next Archive boundary.
Creating and dropping that reader remain inside the measured production phase.
No cache, weaker authentication, county reduction or budget increase supplies
the repair.

Direct consumers now call explicit foundation export. An existing graph
count assertion omitted the two captured inactive recipient classes in Wayne
and Cook. Its correction checks the exact captured class set, household and
person relationships, zero employment and reserve, and reuse of the staffed
donor. It does not add a literal count offset or change production graph data.

The framing controls failed RED because the shared descriptor was absent, then
passed GREEN. Five envelope controls, the binary single-owner control and 456
persistence library tests passed, with 59 existing ignored tests. Production
sources remained frozen during those checks. Failed intermediate compilation,
consumer and lint attempts remain retained rather than overwritten.

The final `foundation-memory-final-green006` gate passed format, strict
all-target Clippy and all six direct consumer targets: 25 tests passed and two
database-only tests remained ignored. Its wall time was 327.399928049 seconds
including compilation and the large national source round trips. Its log
SHA-256 is `c282a04d82c4c650f863507af22925229c0236779d08a156966cf116b186be1a`.
The gate used no database, ran heavy work serially and generated no documentation.

These tests do not show national memory, storage, recovery or play success.
Measure those effects through the full shared consumers after publication.

## Save ownership and recovery evidence

Only one national fixture is active across worktrees:

- Campaign: `db5fa123-22c4-4a5a-8ebd-8b6b2df9b3d1`.
- Container: `babylon-runtime-pg-07d2b15c18f9`.
- Exact container ID: `4a792f1ae04d9aae690b03a3ad2cf024d98362707cfe86639a30bd83c65701a3`.
- Exact volume: `ecbca870fd630d5c80b14120ed62f5cb92a1023113820203d3d6ffa7784fcc6e`.
- Lease: `/home/user/projects/game/babylon/.git/babylon-national-storage/active`.

`smoke004-preserve-before-repair001` contains a private custom dump of
243,899,083 bytes, SHA-256
`72b8b0d78e3b964165ed331df1336624407523c138670064d1237b125ee3c199`.
Its private `globals.private.sql` file is 2,429 bytes, SHA-256
`32492663a48595b13e08ab8975978a54c009a23321b192b1c3adfe8dbe4e99d3`.
The archive directory is readable and original committed state retains its identity.
The operator has not verified a full restore and engine reopen from this dump.

Keep these files private and outside Git. Fixture retirement still needs exact
recovery proof. Do not create a competing national game or broadly clean volumes.

Read-only receipt attribution in `retained-receipt-family-screen001` measured
18,157,960 stored package bytes for period 1 and 16,757,812 for period 2. Period
1's largest payloads were money transfers, income, service performance and
procurement. This was packet-header attribution with framing and identity
checks, not a substitute for full typed decoding. Further history encoding must
earn its complexity with measured total retained savings and recovery evidence.
Postgres remains the baseline. External archives remain deferred.

## Review and continuation boundary

PR [991](https://github.com/percy-raskova/babylon/pull/991) publishes foundation
authentication and qualification evidence repair. PR
[992](https://github.com/percy-raskova/babylon/pull/992) adds funded, settled
trade qualification. This memory repair follows those changes. Each bounded
delivery uses non-closing PER references. Broader acceptance stays open.

Merge approval covers merges. Security finding dismissal needs separate approval. Automatic
approval review rejected the proposed dismissal of CodeQL alerts 84–88. The
operator dismissed no finding. Separate explicit classification approval and fresh
exact-head CI, review and merge checks remain necessary. Use the repository's
prescribed merge command.

The other chat, “Review economic engine design,” owns the foundation descriptor
work in `/media/user/data/worktrees/per343-foundation-memory/babylon`. This chat
owns Archive and qualification consumer changes. Heavy checks run serially here.
The dirty `/media/user/data/worktrees/413b/babylon` remains protected and is not
a source for a blanket commit or cleanup.

Continuation requires a measured complete Archive boundary and recovery using
the repaired implementation, followed by an independent two-period smoke.
After actual storage and timing admission pass, run 52 committed periods with
recovery at every boundary, then separately measure the complete 325-period
save. Native Wayne play must assess opportunity cost, clear consequences and
actual enjoyment. Do not substitute a projection, compiler gate or administrative
read for these outcomes.

Source commitments and qualifications remain in the
[economic circuit source study](2026-09-20-economic-circuit-source-study.md).
The eight-period fixed-price control is accounting evidence, not national or
play qualification. No reserved theory line changes in this repair.
