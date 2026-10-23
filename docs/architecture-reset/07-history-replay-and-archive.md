# 07 — Permanent player history, bounded technical history and replay

**Status: PROPOSED, pending governance.** The player's history and earned knowledge are permanent. Ordinary restart
avoids scanning the full historical chain. Required current indexes for earned knowledge and consumed identities can
still grow with campaign age, and their actual decoded size counts against the memory budget. Exact old technical
detail is replayable under the pinned build/content, but is not all retained as eagerly queryable snapshots. This
distinction is an explicit product contract.

## Five retained layers

| Layer | Retention | Authority and use |
| --- | --- | --- |
| Captured content and opening | Permanent | Exact rules, definitions, policies, reference identity and initial world needed to reproduce the campaign |
| Current full causal snapshot | Replaced atomically at every successful commit | Sole ordinary restart root; complete current obligations, stocks, graph, organizer and disclosure/resource indexes |
| Historical checkpoints | Every thirteen periods; retain the latest **two** completed checkpoints | Faster replay near the present; ordinary integer chunk references share existing bytes |
| Permanent journal and earned knowledge | Permanent | Accepted commands, resolved batches, governed choices, player receipts, acquired observations/dossiers and compact period summaries |
| Exhaustive technical detail | Latest thirteen completed periods | Full material receipt families and technical events for nearby inspection; older detail regenerated when explicitly requested |

The opening is not one of the two rolling historical checkpoints. The current snapshot is not one either. At period
12, retain opening/current and no historical checkpoint. At period 13, retain opening/current/historical-13; current
and historical-13 share state chunks. At period 26, retain historical-13 and historical-26. At period 39, retire
historical-13, retaining historical-26 and historical-39. At period 40, the current root is 40 and the two
historical roots are 26 and 39. There is never a growing archive of every thirteenth checkpoint.

At completed period `t`, exhaustive detail covers `[max(1, t-12), t]`. Rotation happens in the same commit
transaction that installs the successor root. A failed rotation cannot publish a new period with missing required
current state. A failed commit leaves the preceding complete retention set valid. Opening content, player history
and knowledge do not expire at these boundaries.

## Ordinary restart must not replay history

Open admits save schema/build/content identity, selects the current root, validates its manifest, decodes every
required current chunk and reconstitutes the current in-memory owner. It validates the current command-consumption
witnesses, unresolved-command index, current disclosure index and their bound journal/knowledge sequence identities.
It does **not** replay historical material receipts, re-run every past rule, scan the lookup prefix from period one,
or regenerate every past dossier.

This replaces the current dependency documented in [material lookup reconstruction, lines
1670–1715](../../rust/crates/babylon-persistence/src/material_runtime.rs) and [cold observer history, lines
616–675](../../rust/crates/babylon-persistence/src/observer_material.rs). Removing that dependency requires a new
admitted root format and corresponding validators. A checksum over an incomplete subset cannot masquerade as an
independent root.

The current root contains the complete compact learned-authority index needed for current decisions, and current
causal fields needed for active products, agreements, outstanding aid and spent resource identities. Its manifest
binds the exact acquired-knowledge prefix and committed-journal prefix. Later accepted commands can exist beyond the
committed prefix without changing the world period; they are loaded through the unresolved-command index and checked
against the current command-admission contract. The manifest and journal tails make that distinction explicit.

Startup authenticates the bytes needed for the current root and pending inputs. It does not promise to discover
corruption in every cold historical entry immediately. A historical read authenticates its selected entry/payload
and snapshot-bound source identity; a complete replay/audit verifies the relevant journal chain and choice evidence.
Report a damaged historical range explicitly rather than refusing to show an otherwise independently valid current
campaign or fabricating history. If damage affects a current dependency, opening refuses before mutation.

There is no silent automatic fallback to an older historical checkpoint after an invalid current root. Recovery is
an explicit operation into a new destination, replaying the permanent input journal from the latest verified
checkpoint or opening, validating every intervening commit identity, and preserving the damaged save as evidence.
Recovery never overwrites the sole original.

## Journal contract and current causal indexes

The permanent journal records the exact accepted command and commitment, not merely a narrative paraphrase. Nonce
identity is permanent. A later resolution record states the exact executed or refused outcome; execution consumes
the original accepted input once. The configured controlled actor/input authority has one immutable commitment per
campaign/next period, with no cancellation or replacement mechanic added by this reset. The period commit binds its
ordered resolved action batch and governed choice receipts, including selected and unselected alternatives and exact
ticket intervals. Current standing work remains in state, and its actual resolved actions appear in the period
batch.

Keep full player-related outcome receipts, observations and contact/aid/collection product evidence. Keep compact
world period summaries for the scopes declared in chapter 05. A narrative sentence is a presentation of those facts,
never their replacement. The journal remains indexed by period, subject and sequence, so reading an old player
action is a small query rather than a replay of the economy.

Current `OrganizerState` repeats historical vectors inside its canonical state. The replacement moves
ordinary/aid/collection receipt bodies and observations into the permanent journal while retaining active authority
indexes and their origin IDs. Current product eligibility still checks its authenticated origin, and consumed IDs
still prevent double use. Preserve exact current household-time partitions and already consumed contribution
amounts; they are needed by the next admitted action. See [organizer fields, lines
322–334](../../rust/crates/babylon-practice-contract/src/organizer.rs), [cross-reference validation, lines
196–260](../../rust/crates/babylon-practice-contract/src/organizer/contract.rs), and [shared time calculation, lines
29–99](../../rust/crates/babylon-tick/src/material_world/organizer_time.rs).

The knowledge ledger records **actual acquisition** separately from a fact's observed period. An observation of
period 4 acquired in period 9 is unavailable in a period-4 view. A backdated source cannot enter an earlier
disclosure prefix. Old dossier views use the prefix recorded with that dossier or historical snapshot, never today's
expanded knowledge. A public-source capture existing in `content_entry` does not make every fact from that source
disclosed.

A granted fact is stored once with its source journal entry, actor/subject identity, actual acquisition period and
exact observed value/provenance. The current known-fact index is a compact derived representation authenticated by
the current root. It is not a second mutable authority that can grant knowledge independently. Current index
reconstruction reads the saved index and its bound witnesses; it does not scan the entire disclosure history on
every open.

## Archive becomes a player service

An advance produces the player's concise committed briefing and updates actual earned facts. Archive renders
requested known subjects and marked consequential changes. It does not need to materialize a national page for every
county every period before the player can continue.

A delivered or explicitly earned dossier becomes an immutable journal record containing the exact delivered
text/presentation payload, fact/citation references, source period, acquisition prefix and rendering/template
identity. Preserve that version permanently so the player can inspect what they knew then; rerunning a narrator is
not preservation of the original report. A later view may offer a newer report, clearly distinguished by period.
Undisclosed nationwide atoms and unrequested rendered pages are recomputable products; they have no permanent
retention entitlement solely because a worker could generate them.

The owner persists one archive-work cursor, at most 256 pending requests and one navigation record in the
independently writable `service_state` singleton defined in [chapter 06](06-target-runtime-and-sqlite.md), with a 1
MiB decoded limit. It is excluded from mechanical world identity but hashed and included in integrity checks and
portable exports. A serialized owner transaction accepts work without altering a mechanical snapshot. Completion
atomically publishes the permanent dossier journal record and updates the service cursor/request set. Publication is
idempotent by dossier request identity and exact knowledge/source identity. A crash before completion leaves the
request pending; a crash after publication returns the original record. Work completion cannot advance the economic
period or grant knowledge from outside its admitted prefix. Archive status exposes real queued/producing/published
states; it does not claim a global completed sweep proves a particular selected page.

While resolving a turn, keep the last committed map, known relationships and history navigable. The proposed
ordinary turn budget includes durable commit and the bounded player briefing, not an exhaustive national diagnostic
report. Requested background reports use the same restricted owner interface and cancellation boundary. Warm scoped
queries target one second and cold scoped queries two seconds; errors and missing knowledge remain explicit.

## Replay and build identity

For an explicit replay to period `q`, select the newest retained historical checkpoint at or before `q`; if none
exists, start from opening. Reconstruct canonical actions from the journal, use the exact captured rules/content and
replay realization identity, and compare every resulting world/commit identity and choice receipt. Replay into an
isolated temporary campaign state. It must not publish new knowledge, consume live commitments, or alter the
original save.

Old periods may require a long replay from opening because only two recent checkpoints survive. That cost is
accepted and shown before starting; normal history browsing still uses the permanent journal. Show actual replay
period/progress and allow cancellation. Do not promise constant-time arbitrary old-state inspection. If a player
requests exhaustive old production accounts, label the result as a verified replay reconstruction with source
period/build, not a retained historical report.

The save pins engine build identity, content hashes, format and deterministic realization policy. A release
preserves its replay-capable executable through the ordinary versioned distribution/recovery package; the campaign
is not bloated with a compiler toolchain. If that exact build is unavailable, replay refuses with its precise
required identity and recovery instruction. The current executable does not silently simulate old content under
changed rules. This proposal does not require old-save or old-engine compatibility in the new engine. Permanent
journal reading and a matching preserved executable are separate from claiming a new version can resume an old
campaign.

## Chunk reachability and honest storage accounting

Every successful period persists a complete logical current state. Physical chunks unchanged from the preceding
current root can retain their integer IDs after exact equality; the new manifest must still list the whole state.
Opening and the two historical roots can reference those chunks. Delete only chunks unreachable from all retained
snapshots/content within the same transaction. No external CAS, hash-only equality, or background garbage collector
with a separate publication protocol is introduced.

Use SQLite incremental auto-vacuum for bounded page reclamation after committed rotation, configured at database
creation. Do not run a full-file rewrite at every turn. An explicit compact export may produce a smaller independent
file; do not credit that reduction to ordinary saves unless the measured operation actually runs. Free pages,
main-file size, WAL/SHM, temporary export files and retained backups are separate reported quantities.

The **10 MB-per-period ambition** applies to complete positive retained growth, including permanent journal, new
current chunks, checkpoint additions, dictionaries, indexes and disclosure state. Report period-by-period physical
allocation before and after rotation, the gross bytes added, bytes made unreachable, actual file reclamation and
peak temporary/WAL allocation. Never subtract an old checkpoint's deletion to hide a new checkpoint spike. Also
report complete save size and average growth over thirteen- and twenty-six-period windows; a projection is not an
actual long-campaign result. The existing 10 GB/325-period target remains a separately reported comparison until
governance updates it.

Required retention tests cross periods 12/13/14 and 25/26/27/39/40, verify the exact root set and recent window,
then restart and replay a period older than the earliest retained historical checkpoint. Inject corruption into
current chunks, old technical detail, an acquired fact and a command resolution independently. Current corruption
must refuse; irrelevant cold corruption must be diagnosed on access; no repair may create future knowledge,
duplicate resource use, or erase permanent player history. The final national gate measures at most 4,000,000,000
bytes whole-game memory, at most 30 seconds ordinary turn latency, and at most 30 seconds cold open on the declared
16 GB test host. These remain proposed targets until measured.
