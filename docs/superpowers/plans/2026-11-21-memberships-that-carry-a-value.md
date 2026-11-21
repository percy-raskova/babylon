# Memberships That Carry a Value (Amendment AG clause i) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** The fact that a node belongs to a hyperedge carries declared, typed fields. The store keeps them,
the state hash covers them, a save and a load keep them, a scenario seeds them, and BSL reads them with
`membership-field-of` and writes them with `update-membership`, exactly as `docs/reference/bsl-language.rst`
§2.8, §2.9, §2.10, §2.12 and §3.9 clause 6 specify. A world with no membership field keeps every byte.

**Architecture:** The library's per-membership slot (`Hypergraph<(), String, M>`, `M` = `MembershipPayload`)
becomes a sorted map from field name to `f64`. `GraphSubstrate` gains a write, a read and a membership test;
`CanonicalState` gains one listing. The state hash gains section `0x08` and the stable graph gains section
`0x09`, both left out when empty, so every existing hash, vector and save stays the same. PostgreSQL gains one
table and the committed-tick rows gain tag 8. BSL gains `:member` on `deffield`, the annotated `(member ...)`
item in the scenario's `(hyperedge ...)` form, the accessor and the verb.

**Tech Stack:** Rust (`babylon-graph`, `babylon-bsl`, `babylon-tick`, `babylon-persistence`), the library
`hypergraph-rs` pinned by git revision, PostgreSQL schema in `babylon-persistence/migrations/current_schema.sql`.

**Authority:** `ai/decisions/ADR189_amendment_ag_attributed_membership_lattice_instances.yaml` clause (i) and
(iv); `ai/decisions/ADR198_program29_substrate_widening_charter.yaml` R4 (AG(i) is its own storage step, which
this is); `docs/reference/bsl-language.rst` rows D79 to D84; `docs/reference/bsl.ebnf` (it carries the rule dialect's
grammar already; the scenario's seeding form is added by Task 11); GitHub issue #653;
`reports/community-membership-shape-note-2026-08-18.md`. The housing design
(`docs/superpowers/specs/2026-11-21-homes-rent-and-nation-design.md`, H1) is the second consumer and the
shape of the end-to-end test.

**This plan is the storage step that #653 charters.** AG(i) is ratified; the plan adds no primitive and no
verb outside the ratified grammar. ADR198 R4 set AG(i)'s payload aside as "a separate, later ceremony", a
save-compatibility step of its own, and the Director's ruling in #653 chartered it. Its cost is the one such
a step has: the stored schema gains a table, so a database made before it is refused (local play databases
included) and is made again. Both new byte sections are left out when empty, so no state hash, no stable
graph, no tick vector and no file under `tests/baselines/` moves for a world without a membership field, and
no commit needs a `Baselines: blessed(<slug>)` trailer.

**Decided here, for the owner's review (Task 11 records them).** Where the documents are silent the plan
settles the point and records it as the language reference records such points, as a draft ruling in its
register, and in one decision record:

1. The scenario dialect's form for seeding a membership's values (Task 7). The reference rules that a
   hydrated membership carries its whole payload (§3.9 clause 6) and gives no syntax for it.
2. A hydrated member that is not of the annotated type is refused with `E-EVAL-033`, the code the verb uses.
3. The stable graph's new section is written only when it has rows, under the unchanged layout version 1.
   Every other section there is always written; a version bump would move every checkpoint digest and the
   world identity of worlds that carry no membership field.
4. A write to a membership is a recorded motion with its own effect signature.

**Out of scope, each a later plan:** the Allegiance and Electoral systems; nation hyperedges and their census
table; any rule that reads a nation; serving `add-hyperedge`/`remove-hyperedge`/`remove-node` inside rules
(all six shape verbs are refused at load, `babylon-bsl/src/structural_verbs.rs` `DEFERRED_SHAPE_VERBS`, so
the mint-time `(member ...)` item of a RULE's `add-hyperedge` stays refused with them); `scenario_seed.rs`
`HyperedgeSeed` (the nation plan seeds through it and adds its payload there).

## What the documents rule, and what this plan settles

| Question | Ruling | Source |
| --- | --- | --- |
| Field types | Same as node, edge and hyperedge fields: one `deffield`, one `:type`, one `:kind`. | ADR189 (i); §2.12 |
| Storage of a value | `f64`, as every non-currency graph field. `int` is checked exact below 2^53 at load (`scenario.rs` `attribute_value_int`); enum is its ordinal as `f64`. | code |
| Currency | Refused, with the edge and hyperedge lanes' own message (`currency_edge_unsupported_message`). There is no Currency lane off nodes. | code; §2.12 "nothing special-cased" |
| Defaults | None. A membership is written whole at mint and at hydration (`E-LOAD-047`). | §2.8 D83; §3.9 clause 6 |
| A member that leaves and returns | Its old values do not survive; the new membership carries only what is written at its new mint. The library starts it from `M::default()`, an empty map, so a read before a write is the honest null. | §2.8 D26 note; library `CHANGELOG.md` 0.2.0 |
| Pair that is not a membership | `E-EVAL-038`. Wrong hyperedge type or wrong member node type: `E-EVAL-033`. | §2.8, §2.10, D81, D82 |
| Wrong form for a qname | `E-LOAD-046`, static. `:member` on a node or edge owner: `E-LOAD-048`. `:member` naming a non-`NodeType`: `E-TYPE-011`. | §2.9, D79 |
| Range | `E-EVAL-020`, never a clamp. | §2.8 D82 |
| Order | Ascending member node id (D25). | §2.12, D84 |
| Cost | Accessor: 1 + operands. Verb: `STRUCTURAL_VERB_BASE` + operands + `UPDATE_OP_BASE`. No new ceiling axis. | §3.7 |
| A write to a member that leaves in the same step | Cannot happen today: nothing in a rule removes a member. Settled: the apply step tests the membership again and refuses `E-EVAL-038`, as `update-hyperedge`'s apply refuses a missing hyperedge. | settled here |
| Is the write a recorded motion? | Yes: a new `Write::MembershipAttribute` record and a new `EffectSignature::MembershipField`, like the other three update verbs. | settled here, from the three precedents |
| A hydrated member not of the annotated type | The reference fixes the code only for the verb (`E-EVAL-033`). Settled: hydration refuses with the same code, so one fact has one code. | settled here |
| Old saves | Field-free worlds keep their bytes. A database made before the new table is refused by `require_current_schema`, as AGENTS.md allows; no migration. | AGENTS.md "Git and merge rules" |

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`.
  Start every shell command with `cd` to it or to its `rust/`. Never push. No `.env`, no `uv.lock`.
- One cargo process on the machine at a time. Never pass `-j`. Only `mise exec -- cargo ...` and `mise run ...`.
- No pinned value of any existing test changes, and no assertion is loosened, except the refusal tests this
  plan names as flipped and the four things Task 5 names as expected to move (the stored schema's digest, the
  census fixtures, the persistence vector corpus and its counts, the lists of stored relations). If anything
  else moves, stop and tell the lead. Pinned values that must not move:
  `babylon-graph/src/state_hash.rs` tests `the_provided_encode_state_reproduces_the_pinned_bytes`,
  `the_canonical_encoding_is_pinned_byte_for_byte`, `the_golden_vector_hashes_to_its_pinned_digest` and the
  five section tests; `hypergraph_store.rs` `adding_a_read_only_query_method_does_not_move_the_state_hash`
  (`9577d951...`); `babylon-graph/tests/stable_identity.rs`
  `stable_graph_state_eight_sections_and_scalar_bytes_are_exact`;
  `contracts/tick_content_hash_v1_vectors.jsonl` lines 16-17 (`tests/tick_content_hash_contract.rs`);
  `contracts/persistence_semantic_vectors.jsonl` (existing rows); `babylon-tick/src/world_hash.rs` pins;
  `babylon-bsl/src/scenario.rs` `a_currency_free_scenario_encodes_byte_identically_to_before_this_train` and
  `enum_seeding_moves_no_existing_golden_bytes`.
- Values are finite `f64`; `-0.0` stores as `+0.0`; NaN and infinity are refused at the write and again at the
  hash. Every listing that reaches a hash or a byte form is sorted on its stated key.
- No code reads a membership by listing a hyperedge's members (`members_of`) to answer "is this a member" or
  "what is its value". That is the scan ADR193 removed (Review Focus 5).
- Every line number is a hint; find each place by its text.
- **One error code, one home.** `mise run check:bsl-sentinels` fails any `"E-..."` literal that appears in more
  than one `src/` file unless that exact set of files is in `ALLOWLIST`
  (`rust/crates/bsl-lint/src/namespace_unique.rs`). Tasks 6 to 9 raise codes from files that do not spell them
  today (`E-EVAL-033`, `E-PARSE-041` and `E-TYPE-014` from `scenario.rs`; `E-TYPE-011` from `declarations.rs`
  or `scenario.rs`; `E-LOAD-048` if two files need it). Route each through the typed error that already owns
  it. Only where that cannot be done, add an `ALLOWLIST` row for the code with a comment citing this plan.
- **Scoped gate, run by every task before its last commit,** one leg at a time, from `rust/`:
  `mise exec -- cargo fmt --all -- --check`;
  `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D clippy::cognitive_complexity`;
  `mise run rust:test:q -- -p <each crate the task touched>`; `mise run check:bsl-sentinels`. The last task
  runs `mise run rust:check-no-docs` once. Do not run `cargo doc` or `mise run ci:rust`.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then
  check `git log --oneline -1` (hooks can abort silently). Subject form `type(scope): description (#653)`, as
  this history cites GitHub issues. The body ends with `Part of PER-371` and a `Co-Authored-By` line naming
  the model.
- Prose lines at most 120 columns; Vale and format checks only on changed prose.

## Review Focus

1. **A field-free world's bytes move.** A section written with a zero count, or a layout version written into
   the stable graph bytes, moves every pinned hash and vector. Pinned by Task 3
   `an_empty_membership_listing_writes_no_eighth_section_bytes`, Task 4
   `a_membership_free_stable_graph_keeps_its_bytes`, and Task 1 `a_world_without_the_field_hashes_as_before`
   (a hex captured on the tree before anything changes, and run by every later task).
2. **One membership's value leaks into another.** The same group in two nations must keep two values; a store
   keyed by member alone, or a library write to only one stored direction, would merge them. Pinned by Task 2
   `overlapping_hyperedges_keep_separate_membership_values` and Task 10 `writing_one_nation_leaves_the_other`.
3. **A value outlives its membership.** `MemoryGraph` keeps a side map that must be swept on `remove_node` and
   `remove_hyperedge` (the hyperedge-attribute lane once missed this sweep, PR #682). Pinned by Task 2
   `membership_values_die_with_their_membership_and_never_return`.
4. **A membership-field qname slips through the wrong form.** `field-of`/`update-hyperedge` on a membership
   field, or `membership-field-of`/`update-membership` on a hyperedge's own field, would read or write the
   wrong store. Pinned by Task 6 `wrong_form_reads_and_writes_are_e_load_046`.
5. **The scan comes back.** A membership test through `members_of` is linear in the hyperedge's size per read;
   a nation has many members. No cheap test pins cost; the reviewer runs
   `rg -n 'members_of' rust/crates/babylon-bsl/src/evaluator.rs rust/crates/babylon-bsl/src/structural_verbs.rs`
   and checks that no new hit is on a membership path, and Task 2 adds a `storage_benchmark.rs` row.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `rust/crates/babylon-graph/Cargo.toml`, `rust/Cargo.lock` | Library pin | 1 |
| `rust/crates/babylon-bsl/tests/r9_chapters.rs` | The field-free twin and its pinned hash | 1 |
| `rust/crates/babylon-bsl/tests/hyperedge_lane_e2e.rs` | `OrderSpyGraph`, the third store, delegates the new methods | 2 |
| `rust/crates/babylon-graph/src/substrate.rs` | Three trait methods | 2 |
| `rust/crates/babylon-graph/src/hypergraph_store.rs` | `MembershipPayload` map; the methods; listing | 2, 3, 4 |
| `rust/crates/babylon-graph/src/memory.rs` | Side map, sweeps, the methods, listing | 2, 3 |
| `rust/crates/babylon-graph/src/conformance.rs` | Rows for both stores | 2 |
| `rust/crates/babylon-graph/tests/differential.rs`, `tests/storage_benchmark.rs` | Oracle ops; timing row | 2 |
| `rust/crates/babylon-graph/src/state_hash.rs` | Section `0x08`, layout version 5 | 3 |
| `rust/crates/babylon-graph/src/stable_state.rs` | Section `0x09`, decode, restore input, bounds | 4 |
| `contracts/tick_content_hash_v1.yaml` | The stable graph's tag 9, written only when it has rows | 4 |
| `rust/crates/babylon-graph/tests/stable_identity.rs` | Round trip | 4 |
| `rust/crates/babylon-persistence/src/semantic_codec.rs`, `semantic_vectors.rs`, `semantic_batches.rs` | Row tag 8 | 5 |
| `rust/crates/babylon-persistence/migrations/current_schema.sql`, `current_views.sql`, `src/fixtures/*census*.txt` | New table, its observer view, regenerated census | 5 |
| `rust/crates/babylon-persistence/src/runtime/session.rs`, `src/stored_tick/rows.rs`, `src/stored_tick/source.rs`, `src/checkpoint.rs`, `src/reader.rs`, `src/inspection_copy/rows.rs`, `src/observer_tick_components.rs` | Write, read, count | 5 |
| `contracts/persistence_semantic_vectors.jsonl` | One new row | 5 |
| `rust/crates/babylon-bsl/src/declarations.rs`, `src/scenario.rs` (`load_deffield`), `src/typecheck.rs` (`TypeEnv`) | `:member` | 6 |
| `rust/crates/babylon-bsl/src/scenario.rs` (`load_hyperedge`) | Annotated member items at hydration | 7 |
| `rust/crates/babylon-bsl/src/evaluator.rs`, `src/bound_checker.rs`, `src/rule_pipeline.rs`, `src/grammar.rs` | `membership-field-of` | 8 |
| `rust/crates/babylon-bsl/src/grammar.rs`, `src/structural_verbs.rs`, `src/write_log.rs`, `src/causal_contract.rs`, `src/identity_codec.rs`, `src/error_identity.rs`, `src/sfs_profile.rs`, `src/declarations.rs` | `update-membership` | 9 |
| `rust/crates/babylon-persistence/src/simulation_experiment/report/wiring/manifest.rs`, `rust/crates/babylon-tick/tests/causal_contract_conformance.rs` | New `EffectSignature` arm | 9 |
| `rust/crates/bsl-lint/src/sfs_non_authorability.rs` | The sentinel reads qnames in the new forms | 9 |
| `rust/crates/babylon-bsl/tests/r9_chapters.rs` | Family 23 module, the nation test | 10 |
| `docs/reference/bsl-language.rst`, `docs/reference/bsl.ebnf`, `docs/reference/graph-storage-capability-delta.md`, module docs | "Not served" corrected; the draft rulings registered | 11 |
| `ai/decisions/ADR316_attributed_membership_is_served.yaml`, `ai/decisions/index.yaml` | The decisions of this plan | 11 |

---

### Task 1: Move the library pin

**Files:** Modify `rust/crates/babylon-graph/Cargo.toml` (the `hypergraph-rs` `rev`), `rust/Cargo.lock`,
`rust/crates/babylon-bsl/tests/r9_chapters.rs` (new module after family 22:
`// === family 23 — Amendment AG (i)`, `mod ag_attributed_membership`, with one test for now).

**Decisions:**
1. `rev` = `fb2b4b85a76fcd512af46d4511c874024fc86e93`, the head of the library's pull request 4. That
   pull request is not merged yet. When it is, the lead moves the pin to the merge commit in a commit of its
   own. Keep `default-features = false`. The library's floor is Rust 1.90; the game builds with 1.99.1.
2. The library raised its own dependencies (rustworkx-core, petgraph, serde_json among them). The lock change is
   whatever `mise run rust:lock-refresh` writes; review it for crates other than `hypergraph-rs`'s tree.
3. `MembershipPayload` keeps `Default + Clone + PartialEq + Debug`, which the new library's `add_edge`,
   `copy` and `set_member_data` bounds need. Nothing else changes in this task.

4. **The twin comes first.** Before the pin moves, on the unchanged tree: write the field-free twin of Task
   10's nation fixture (the same node types, groups g1 and g2, nations n1 over {g1, g2} and n2 over {g1}, the
   hyperedge field Task 10 selects a nation by, NO membership `deffield`, bare member items), load it, and pin
   its `state_hash` hex in `a_world_without_the_field_hashes_as_before`. It needs nothing from Tasks 2 to 9.
   Every later task runs it, so a byte that moves for a field-free world is caught in the task that moved it.

- [ ] **Step 1:** Write `a_world_without_the_field_hashes_as_before` on the unchanged tree, run it once to
  read the hex, pin it, run it again and see it pass. Commit it alone:
  `test(bsl): pin a field-free world before memberships carry values (#653)`.
- [ ] **Step 1b:** For the pin itself there is no new test. The red state is the old revision lacking
  `member_data`; the green state is every existing `babylon-graph` test passing unchanged, including
  `adding_a_read_only_query_method_does_not_move_the_state_hash`.
- [ ] **Step 2:** Change `rev`; run `mise run rust:lock-refresh` (one build, warn the lead first: it is the
  machine's one build slot).
- [ ] **Step 3:** `mise run rust:test:q -- -p babylon-graph`, then `-p babylon-bsl -E
  'test(a_world_without_the_field_hashes_as_before)'`. Expected: all pass, no pin moved.
- [ ] **Run the gate. Commit** `chore(graph): pin hypergraph-rs at its membership-data branch (#653)`.

### Task 2: The store keeps a membership's fields

**Files:** Modify `substrate.rs`, `hypergraph_store.rs`, `memory.rs`, `conformance.rs`, `tests/differential.rs`,
`tests/storage_benchmark.rs`; and `rust/crates/babylon-bsl/tests/hyperedge_lane_e2e.rs`, whose `OrderSpyGraph`
(near line 360) is a third implementor of `GraphSubstrate`: it delegates the three new methods to the store
it wraps. Check with `rg -n 'impl GraphSubstrate for' rust/crates` that there is no fourth.

**Interfaces:**

```rust
// substrate.rs, GraphSubstrate gains (after hyperedge_attribute):
/// Write one `f64` field of the membership of `member` in `id`.
/// # Errors
/// No such hyperedge, no such node, `member` not in `id`'s member list, or a non-finite value.
fn update_membership_attribute(&mut self, id: HyperedgeId, member: NodeId, attribute: &str, value: f64)
    -> Result<(), GraphError>;
/// Read it back.
/// # Errors
/// The three existence faults above, or the field was never written on this membership (never a default).
fn membership_attribute(&self, id: HyperedgeId, member: NodeId, attribute: &str) -> Result<f64, GraphError>;
/// Whether `member` is in `id`'s member list, without listing the members.
/// # Errors
/// No such hyperedge, or no such node.
fn is_member(&self, id: HyperedgeId, member: NodeId) -> Result<bool, GraphError>;

// hypergraph_store.rs
#[derive(Debug, Default, Clone, PartialEq)]
struct MembershipPayload {
    /// qname -> value; a BTreeMap so listing order is the qname order.
    fields: BTreeMap<String, f64>,
}
```

**Decisions:**
1. `M` stays the library's membership slot, not a side table: the (member, hyperedge) pair is exactly the key
   the slot hangs on (ADR189 (i)'s "first-class in the model"), and the library removes the slot with the
   membership on `remove_node` and `remove_edge`, so there is no sweep to forget. A side map would need sweeps
   in both removals and would duplicate a key the library already holds.
2. A write reads the current map with `member_data`, inserts, and writes it back with `set_member_data` (both
   stored directions receive it, library doc). An empty map allocates nothing, so a field-free world costs no
   memory.
3. `is_member` = `inner.member_data(edge_key, node_key).is_some()` after the two existence checks; cost is the
   member's own membership count (petgraph `find_edge` walks the node's adjacency), never the hyperedge's size.
4. `MemoryGraph` gains `membership_attributes: HashMap<(HyperedgeId, NodeId, String), f64>`, swept in
   `remove_hyperedge` (rows of `id`) and in `remove_node` (rows naming the node, and rows of every hyperedge the
   cascade dropped), in one `retain` each, as the PR #683 note asks.
5. The trait-level doc of `remove_hyperedge` ("there is deliberately no `remove_member`") stays true: no member
   list changes here.

- [ ] **Step 1: Write the failing conformance rows** in `conformance.rs`, added to `run_substrate_conformance`:
  - `membership_attribute_round_trips_and_reads_honest_null`: write `nation/households` = 12.0 on (h, a); read
    gives 12.0; reading `nation/other` errs naming "never written"; reading (h, b) where b is a member with no
    write errs the same way.
  - `overlapping_hyperedges_keep_separate_membership_values`: nodes a, b in hyperedges h1 and h2 of one type;
    write (h1, a) = 3.0, (h2, a) = 7.0; both read back; writing (h1, a) = 4.0 leaves (h2, a) at 7.0.
  - `membership_write_is_loud_off_a_membership`: unknown hyperedge, unknown node, a live node not in the list,
    and `f64::NAN` each err and change no `encode_state` byte; `is_member` is `Ok(true)`, `Ok(false)` and `Err`
    for the three cases.
  - `membership_values_die_with_their_membership_and_never_return`: write (h, a); after `remove_node(a)` a
    read of (h, a) errs (no such node); write (h2, b), `remove_hyperedge(h2)`, `add_hyperedge` again over b:
    reading (new, b) errs "never written". (Task 3 adds the same check against the listing.)
- [ ] **Step 2:** `mise run rust:test:q -- -p babylon-graph -E 'test(conformance)'`. Expected: does not compile.
- [ ] **Step 3: Implement** the three methods on both stores, the payload, the sweeps. In `differential.rs`
  add an `update_membership_attribute` op to the script so both stores are compared after it. In
  `storage_benchmark.rs` add one printed row timing 10,000 `membership_attribute` reads on a 10,000-member
  hyperedge (non-gating, as the file's other rows).
- [ ] **Step 4:** `mise run rust:test:q -- -p babylon-graph`. Expected: all pass, no pin moved.
- [ ] **Run the gate. Commit** `feat(graph): memberships carry declared values (#653)`.

### Task 3: The state hash covers them

**Files:** Modify `state_hash.rs`, `hypergraph_store.rs`, `memory.rs`, and every other implementor of
`CanonicalState`. There are six today (`rg -n 'impl CanonicalState for' rust/crates`):
`babylon-graph/src/hypergraph_store.rs`, `src/memory.rs`, `src/state_hash.rs` (the test fixture),
`src/stable_element.rs`, `tests/stable_identity.rs`, and
`babylon-tick/tests/support/tick_content_hash_bound_operations.rs`.

**Interfaces:**

```rust
const TAG_MEMBERSHIP_ATTRIBUTES: u8 = 0x08;
pub const CANONICAL_LAYOUT_VERSION: u32 = 5;
// CanonicalState gains, REQUIRED (no default body, the 0x05-0x07 argument):
/// Every membership-attribute row as `(hyperedge, member, qname, value)`, in any order.
fn all_membership_attributes(&self) -> Vec<(HyperedgeId, NodeId, String, f64)>;
// StateEncoder gains:
pub fn write_membership_attributes(&mut self, rows: &[(HyperedgeId, NodeId, String, f64)])
    -> Result<(), GraphError>;
```

**Decisions:**
1. Layout: `0x08 ‖ u32 count ‖ per row, ascending (hyperedge id, member id, qname): u64 hyperedge ‖ u64 member ‖
   str qname ‖ u64 value-bits`. Written after `0x07`, only when non-empty. This is the module doc's rule for
   every future section; version 5 is recorded in the "Layout versions" list. The constant is never written
   into any bytes or hash: only the test that pins it moves.
2. The member id sits beside the hyperedge id rather than inside section `0x04`: changing `0x04` is "a contract
   change that invalidates every stored state hash" (module doc).
3. `HypergraphStore` lists by walking `inner.edge_ids()` and `inner.members_with_data(key)` once per hyperedge,
   skipping empty maps. Cost: the incidence count times each member's membership count; no id scan.

- [ ] **Step 1: Write the failing tests** in `state_hash.rs` tests (add the field to the `Facts` fixture):
  `an_empty_membership_listing_writes_no_eighth_section_bytes` (bytes equal those of the same facts before the
  field existed, using the existing pinned fixture); `the_eighth_section_is_pinned_byte_for_byte` (one row
  `(HyperedgeId(1), NodeId(2), "n/h", 1.0)`, hand-written bytes `0x08`, count 1, the two ids, `00 00 00 03 "n/h"`,
  `3f f0 00 ...`); `the_eighth_section_sorts_by_hyperedge_then_member_then_qname_regardless_of_listing_order`;
  `a_single_membership_attribute_moves_the_hash_and_trails_the_seven_sections`;
  `the_canonical_layout_version_is_pinned` asserts 5;
  `a_removed_member_leaves_no_listing_row` (write (h, a), `remove_node(a)`: `all_membership_attributes` has no
  row naming a, on both stores).
- [ ] **Step 2:** Run them (`-E 'test(state_hash)'`). Expected: does not compile.
- [ ] **Step 3: Implement**; the listings on both stores.
- [ ] **Step 4:** `mise run rust:test:q -- -p babylon-graph`, then `-p babylon-tick`. Expected: all pass, every
  pin in Global Constraints unchanged.
- [ ] **Run the gate. Commit** `feat(graph): hash membership values in section 0x08 (#653)`.

### Task 4: The stable graph and the checkpoint restore carry them

**Files:** Modify `stable_state.rs`, `hypergraph_store.rs` (`restore_stable_state`), `tests/stable_identity.rs`,
`contracts/tick_content_hash_v1.yaml`; and EVERY `StableGraphStateRowsInput { .. }` literal in the workspace
(`rg -n 'StableGraphStateRowsInput \{' rust`). There are eight today: `babylon-graph/src/stable_state.rs`
(two), `babylon-graph/tests/national_graph_admission.rs`,
`babylon-tick/tests/support/tick_content_hash_bound_operations.rs`,
`babylon-persistence/src/stored_tick/rows.rs`, `src/bin/babylon-runtime.rs`, and
`src/production_projection/staffing/paid_tests.rs` and `tests.rs`. The persistence literals get
`membership_f64: Vec::new()` here and the real lane in Task 5.

**Interfaces:**

```rust
/// `(hyperedge local name, member local name, qname, f64 bits)`.
pub type StableMembershipF64Row = (String, String, String, u64);
// StableGraphStateRowsInput gains `pub membership_f64: Vec<StableMembershipF64Row>`;
// StableGraphStateRows gains `pub fn membership_f64(&self) -> &[StableMembershipF64Row]`.
```

**Decisions:**
1. Section `0x09` after `0x08`, same row framing as `append_hyperedge_f64`, sorted by (hyperedge, member, qname)
   local-name byte order, **written only when non-empty**. `STABLE_GRAPH_STATE_LAYOUT_VERSION` stays 1: the
   version is written into the bytes and bound into `TickContentHashV1` and the world identity, so bumping it
   would move `contracts/tick_content_hash_v1_vectors.jsonl` and every checkpoint digest for worlds that carry
   no membership field. Leaving the empty section out is the state hash's own rule (ADR198 R2) applied here.
2. `decode` accepts end-of-bytes or a `0x09` section after `0x08`; a `0x09` with count 0 is refused (a second
   spelling of empty); trailing bytes after `0x09` are refused as today.
3. `validate_loaded_rows`/`compose_stable_graph_state_from_rows` refuse a row whose hyperedge is unknown or whose
   member is not in that hyperedge's member list, and a repeated key (`StableIdentityError` with a specific
   variant `MembershipNotInHyperedge`, and the existing duplicate variant).
4. `restore_stable_state` builds the membership values off to the side with the other maps and applies them
   after the topology check, through `inner.set_member_data`. It replaces the map of EVERY membership in the
   store, with an empty map where the source has no row, so no value of the live store survives a restore.
5. `validate_listing_bounds`, `stable_state_capacity`, the fact units and the `MAX_*` limits count the new
   rows, as they count the hyperedge-f64 rows.
6. `contracts/tick_content_hash_v1.yaml`, `stable_graph_v1` (near line 189): the tags list gains 9 and the
   sections gain "membership f64 rows, written only when there is at least one". No vector is added to
   `contracts/tick_content_hash_v1_vectors.jsonl`: its pinned corpus does not move.

- [ ] **Step 1: Write the failing tests:** `a_membership_free_stable_graph_keeps_its_bytes` (in
  `stable_identity.rs`: the eight-section fixture's bytes unchanged with an empty `membership_f64`);
  `membership_values_round_trip_through_stable_bytes_and_restore` (encode a store with two overlapping
  memberships carrying values, decode, `restore_stable_state` into a fresh load of the same topology, equal
  `state_hash`); `a_restore_clears_values_the_source_does_not_carry` (a live store with a value on (h, a),
  restored from a source of the same topology with no rows: the read errs "never written");
  `the_ninth_section_is_pinned_byte_for_byte` (one row, hand-written bytes, as the state hash's Task 3 test);
  `stable_graph_refuses_a_value_for_a_non_member` and `stable_graph_refuses_an_empty_ninth_section` (in
  `stable_state.rs` tests).
- [ ] **Step 2:** Run them. Expected: does not compile.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** `-p babylon-graph`, then `-p babylon-tick` (`tick_content_hash_contract.rs` passes
  unchanged), then `-p babylon-persistence` (its literals compile).
- [ ] **Run the gate. Commit** `feat(graph): carry membership values in the stable graph (#653)`.

### Task 5: A saved world keeps them

**Files:** listed in the File Structure row for Task 5. Find every place the hyperedge-f64 lane is written or
read with `rg -n 'hyperedge_f64' rust/crates/babylon-persistence` and add the membership lane beside each.

**Decisions:**
1. Committed-tick row: family `Graph`, tag 8, `encode_stable_graph_membership_f64(hyperedge, member, qname,
   value)`; key = hyperedge local name ‖ member local name ‖ qname; payload = the f64.
2. Table `babylon_state.graph_hyperedge_member_f64_v1 (campaign_id uuid, resolve_tick bigint, local_name text C,
   member text C, qname text C, value_bits bigint)`, check `resolve_tick >= 1`, primary key
   `(campaign_id, resolve_tick, local_name, member, qname)`, foreign key
   `(campaign_id, resolve_tick, local_name, member)` to `graph_hyperedge_member_v1`'s unique key. One INSERT per
   row, as `graph_hyperedge_f64_v1`.
3. **The census fixtures are regenerated, never edited by hand.** Each of the four
   `current_schema*_census.txt` (and the two `fresh_schema_census*.txt` if they list the relation) carries
   `# source|<file>|<sha256>` header lines that the unit test
   `current_census_provenance_matches_exact_constructed_sources` (`current_schema.rs`, near 592) checks, and
   each relation line is a digest of a live catalog row of the pinned PostgreSQL. Regenerate them from a
   fresh install of the changed schema in the pinned image (`babylon-postgres-runtime:local`, which exists
   on this machine), through the project's own runner (`mise run test:rust-postgres`,
   `tools/run_rust_postgres.sh`). Find how the census text is written (`rg -n 'census'
   rust/crates/babylon-persistence/src/postgres_catalog.rs rust/crates/babylon-persistence/src/current_schema.rs
   tools`), and say the exact command in your report. If you cannot regenerate them, return blocked: do not
   write a digest by hand. These files are not under `tests/baselines/`.
4. `checkpoint.rs` row count and `graph_row_count` add the new rows; the section-1 sha256 check
   (`stored_tick/rows.rs`) then covers them, so a database row lost is a refused load, not a quiet zero.
5. Grant lists for reader roles: copy whatever `graph_hyperedge_f64_v1` is granted.
6. **The observer's view.** Every stored-tick relation has a view for the observer, and both readers share the
   rows query (`stored_tick/source.rs`, near 40 and 83), so the new relation needs its own:
   `public.v_observer_graph_hyperedge_member_f64_v1` in `migrations/current_views.sql` (the pattern of the
   hyperedge-f64 view, near line 189) with its entry in the REVOKE list (near 326). Then every list of stored
   relations grows by one: `observer_tick_components.rs` (`[&str; 24]` becomes 25), the view names in
   `reader.rs` (near 96), `HELD_SQL` in `observer_reader/observer.rs` (near 1115), `bin/babylon-runtime.rs`
   (near 1528), and the live tests' lists in `tests/observer_material_live/tick_components.rs` (`[_; 24]`) and
   `statewide_qualified/maintenance.rs` (near 695).
7. **Expected to move, and only these:** `current_schema_sha256` (`current_schema.rs`, near 160), so every
   database made before this task is refused, local play databases included; the census fixtures and their
   header digests; `GOVERNED_VECTOR_ROWS` 54 to 55 and `GOVERNED_VECTOR_SHA256` (`semantic_vectors.rs`, near
   17); both 54s and the codec list (which gains `stable_graph_hyperedge_member_f64_v1`) in
   `tests/persistence_semantic_vectors.rs`; the lists of decision 6. Optionally a row in
   `docs/architecture-reset/evidence/storage-table-disposition.tsv`.
8. **Live tests.** The tests that reach a database are `#[ignore]` and `rust:test:q` skips them. They run
   only through `BABYLON_POSTGRES_LIVE_FOCUS=<focus> mise run test:rust-postgres`, which builds with the
   runner's own job count. Find the focus that covers the hyperedge-f64 lane (`rg -n 'LIVE_FOCUS|live_focus'
   tools/run_rust_postgres.sh rust/crates/babylon-persistence`), run it once after the unit tests pass, and
   name the focus and the command in your report. Tell the lead before you start it: it is a long build in
   the machine's one build slot.

- [ ] **Step 1: Write the failing tests:** a new row in `contracts/persistence_semantic_vectors.jsonl`
  (`stable_graph_hyperedge_member_f64_v1`, hand-written key and payload hex), run by the existing
  `shared_language_neutral_vectors_execute_every_codec_and_refusal`; in the live session tests that cover the
  hyperedge-f64 lane (`rg -n 'hyperedge_f64' rust/crates/babylon-persistence/tests`), one case
  `a_campaign_with_membership_values_restores_them` (commit, reload, equal stable bytes and state hash).
- [ ] **Step 2:** `mise run rust:test:q -- -p babylon-persistence -E 'test(semantic_vectors)'`. Expected: fails
  on the corpus digest and the row count (the corpus is pinned whole), then on the unknown vector kind.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** `-p babylon-persistence`, then the live focus of decision 8. Expected: all pass; every
  existing vector row is unchanged, and only the things decision 7 lists moved.
- [ ] **Run the gate. Commit** `feat(persistence): store membership values (#653)`.

### Task 6: `deffield ... :member`

**Files:** Modify `declarations.rs` (`parse_deffield`, `OwnedFieldDecl`), `scenario.rs` (`load_deffield`,
`Scenario`), `typecheck.rs` (`TypeEnv`), every `TypeEnv { .. }` literal (`rg -n 'TypeEnv \{' rust/crates` lists
65: 55 in `babylon-bsl`, 2 in `babylon-ls`, 7 in `babylon-tick`, 1 in the bsl test support), the place the production
`TypeEnv` is built from a scenario (`babylon-tick/src/tick_runner.rs`, near 601), and the rule load path that
sees `field-of`/`update-hyperedge` qnames.

**Interfaces:**

```rust
// typecheck.rs, TypeEnv gains:
/// Membership fields: qname -> member `NodeType` member name (e.g. "SOCIAL_CLASS"). The qname's
/// type and kind stay in `fields`.
pub membership_fields: BTreeMap<String, String>,
// declarations.rs, OwnedFieldDecl gains `pub member: Option<String>`.
```

**Decisions:**
1. The declaration and its type/kind live in `fields` like any field (one namespace, `E-LOAD-001` for a
   duplicate); `membership_fields` only marks which qnames are membership fields. A separate map keeps all 71
   `FieldDecl` literals untouched.
2. Rule dialect: `:member NodeType/X` as a fourth keyword in `parse_deffield`. Scenario dialect:
   `(deffield <qname> <type> <kind> :member NodeType/X)` and `(deffield <qname> enum <EnumType> :member NodeType/X)`.
3. Checks at load, as §2.9 orders them (`bsl-language.rst`, near 2128): an owner segment that renders nothing
   registered is `E-LOAD-023`, as for any field; an owner that is registered and is not a `HyperedgeType` is
   `E-LOAD-048`; the operand is a registered `NodeType` member or `E-TYPE-011`; the member half is part of
   the declaration's agreement with the kernel (`E-LOAD-022`); type `currency` is refused with the
   edge/hyperedge message.
4. `E-LOAD-046` at rule load, beside the existing field-init owner check: `field-of` or `update-hyperedge` naming
   a `membership_fields` qname, and `membership-field-of` or `update-membership` naming a qname that is not.

- [ ] **Step 1: Write the failing tests** (`declarations.rs`, `scenario.rs` tests):
  `deffield_member_declares_a_membership_field` (both dialects; `membership_fields["nation/households"]` is
  `"HOUSEHOLD_GROUP"`-style member name; type and kind in `fields`); `member_on_a_node_owner_is_e_load_048`;
  `member_naming_an_edge_type_is_e_type_011`; `a_currency_membership_field_is_refused`;
  `wrong_form_reads_and_writes_are_e_load_046` (all four directions).
- [ ] **Step 2:** `mise run rust:test:q -- -p babylon-bsl -E 'test(member)'`. Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** `-p babylon-bsl`, `-p babylon-ls`, `-p babylon-tick`. Expected: all pass.
- [ ] **Run the gate. Commit** `feat(bsl): declare membership fields with :member (#653)`.

### Task 7: A scenario seeds them

**Files:** Modify `scenario.rs` (`load_hyperedge` and its grammar comment).

**Interfaces:** the scenario form becomes
`(hyperedge <local-name> <HyperedgeType/MEMBER> (members <member-item>+))`, `<member-item>` = `<local-name>` |
`(member <NodeType/MEMBER> <local-name> (<qname> <value>)*)`.

**Decisions:**
1. If the hyperedge type declares any membership field for the member's node type, every item for such a member
   is annotated and writes exactly those fields: a bare item or a missing field is `E-LOAD-047`; a field twice is
   `E-PARSE-041`; a qname of another owner is `E-TYPE-014`; a member not of the annotated type is `E-EVAL-033`.
2. Values convert through `attribute_value` (the per-type literal law: `int` exact below 2^53, range-checked
   types refuse out of range), then `add_hyperedge` with the sorted members, then one
   `update_membership_attribute` per field. Hydration failing mid-way fails the whole load, as today.
3. Bare items under a payload-free type keep their meaning and bytes.
4. `load_hyperedge` (`scenario.rs`, near 2698) is close to the length and complexity limits and carries no
   allow. The annotated item is parsed and checked in a helper of its own, which is handed `fields` and
   `membership_fields`.
5. This form is not in `docs/reference/bsl-language.rst` §3.9 or `docs/reference/bsl.ebnf` today: the
   reference rules the obligation (clause 6) and gives no syntax. Task 11 writes the form into both and
   registers it as a draft ruling, as D156 did for `(edge-attr ...)`.

- [ ] **Step 1: Write the failing tests:** `annotated_members_seed_their_values` (two nations over the same two
  groups, values 120 and 30 for one group; `membership_attribute` reads each);
  `a_hydration_omitting_a_payload_field_is_e_load_047`; `a_bare_item_under_a_payload_type_is_e_load_047`;
  `a_payload_field_twice_is_e_parse_041`; `a_foreign_qname_is_e_type_014`;
  `a_member_not_of_the_annotated_type_is_e_eval_033`; `an_int_payload_past_2_pow_53_is_refused`.
- [ ] **Step 2:** `-p babylon-bsl -E 'test(scenario)'`. Expected: fail.
- [ ] **Step 3: Implement**; fix the stale `scenario.rs` module doc (lines 73-76) that says `hyperedge-attr`
  still refuses.
- [ ] **Step 4:** `-p babylon-bsl`. Expected: all pass, the two scenario byte pins unchanged.
- [ ] **Run the gate. Commit** `feat(bsl): seed membership values at hydration (#653)`.

### Task 8: `membership-field-of`

**Files:** Modify `evaluator.rs` (dispatch, `UNSERVED_EXPRESSION_HEADS` becomes `[_; 2]`, the served table, the
`field-of` doc at the `eval_field_of` header, and the loop of `every_seam_head_is_classified` near 3046, which
wants each AG-era head in exactly one of its two lists), `bound_checker.rs` (`ACCESSORS`), `grammar.rs`
(`ARITIES`), `rule_pipeline.rs` (`field_ref_for`), `src/query.rs` only if the referent check lives there.

**Interfaces:**

```rust
/// `(membership-field-of <hyperedge> <member> <qname>)` (§2.10, D81).
fn eval_membership_field_of(items: &[SExpr], env: &EvalEnv<'_>, host: &dyn IntrinsicHost, fuel: &mut u64)
    -> Result<Value, EvalError>;
// EvalCode gains `NotAMembership` => "E-EVAL-038".
```

**Decisions:**
1. Order: charge `ACCESSOR_BASE`; evaluate both operands (a `HyperedgeRef`, a `NodeRef`, else `E-EVAL-033`);
   `check_hyperedge_referent_type` against the qname's owner; member's `node_type_of` against
   `membership_fields[qname]` (`E-EVAL-033`); `is_member` false is `E-EVAL-038`; `membership_attribute`; then
   `tick::bind_field_value` so the type (and enum rendering) follows the declaration.
2. Bound: 1 + the two operands, never multiplied by a ceiling (D38).
3. `ARITIES` rows have the shape `(head, min, max, text)`: add `("membership-field-of", 3, 3, "exactly 3")`.
4. **A fold may read a payload.** `rule_pipeline.rs` `field_ref_for` (near 887) reduces a fold's body or
   `:weight` to a field only for a qname, a binding, or the 3-item `(field-of <expr> <qname>)`; anything else
   is refused as a compound fold. It gains the arm for the 4-item
   `(membership-field-of <expr> <expr> <qname>)`, giving the qname, so that the kind check of §3.4 sees the
   payload field's kind.

- [ ] **Step 1: Write the failing tests** (in `evaluator.rs` tests, over a seeded scenario from Task 7):
  `membership_field_of_reads_each_scalar_type` (int, coefficient, probability, enum);
  `membership_field_of_a_non_member_is_e_eval_038`; `membership_field_of_a_wrong_hyperedge_type_is_e_eval_033`;
  `membership_field_of_a_wrong_member_type_is_e_eval_033`;
  `a_fold_over_members_of_reads_in_ascending_member_id` (members hydrated in descending order, a body whose
  binary64 sum differs by order); `a_mean_over_members_reading_a_payload_needs_a_weight`
  (`(fold mean (members-of c ..) (membership-field-of c it q))` with an intensive `q` is `E-TYPE-042`, and
  loads with `:weight`). Flip `refusal_messages_name_their_slice`: drop the `#653` assertion and
  assert a read returns its value; keep `every_seam_head_is_classified` passing with the head moved to the
  served table.
- [ ] **Step 2:** `-p babylon-bsl -E 'test(membership)'`. Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** `-p babylon-bsl`. Expected: all pass.
- [ ] **Run the gate. Commit** `feat(bsl): serve membership-field-of (#653)`.

### Task 9: `update-membership`

**Files:** listed in the File Structure row for Task 9.

**Interfaces:**

```rust
// structural_verbs.rs
WriteTarget::Membership { hyperedge: HyperedgeId, member: NodeId }
fn collect_update_membership(&mut self, items: &[SExpr], env: &EvalEnv<'_>, host: &dyn IntrinsicHost,
    fuel: &mut u64) -> Result<PendingWrite, EvalError>;
fn apply_pending_membership_write(&mut self, pending: &PendingWrite /* as the hyperedge twin */)
    -> Result<(), EvalError>;
// write_log.rs
Write::MembershipAttribute { hyperedge: HyperedgeId, member: NodeId, field: String, previous: f64, value: f64 }
// causal_contract.rs
EffectSignature::MembershipField(String)   // and AllowedEffect::MembershipField(&'static str)
```

**Decisions:**
1. Copy `update-hyperedge` step for step (collect against the pre-state, apply in collected order): grammar
   `ARITIES` row `("update-membership", 4, 4, "exactly 4")` (the array becomes `[_; 26]` with Task 8's row);
   the closed `<update-op>` check, which reads `items.get(3)` for the other verbs (`grammar.rs`, near 845) and
   must read `items.get(4)` for this one; `STRUCTURAL_VERBS` cost; collect
   runs Task 8's referent and membership checks; apply re-tests `is_member` (`E-EVAL-038`), then
   `combine_and_check_finite`, `canonical_zero`, `store_range_check` (`E-EVAL-020`), the write, the record.
2. `identity_codec::encode_effect_signature`: `MembershipField` is tag `0x0b`, the next unused (`0x05` is
   `Shape`, `0x06`-`0x0a` are taken); `error_identity.rs` maps it to `ErrorIdentity::Field`; `sfs_profile.rs`
   renders `membership:{field}`; the persistence manifest renders `membership-field:{field}`;
   `causal_contract_conformance.rs` gains the arm. No content uses it, so no content digest moves.
3. `RESERVED_FORM_TAGS` gains `member`, `membership-field-of`, `update-membership` (`[&str; 56]`), closing the
   gap the evaluator doc calls filed; the evaluator doc paragraph is corrected.
4. `probability.rs` keeps `update-membership` in `SHARED_MATERIAL_EFFECTS`, and
   `tests/probability_contract.rs`'s membership leg keeps refusing: a probability kernel may not write shared
   graph state, which is a different law from service.
5. `sfs_profile.rs`'s guard matcher (qname at index 2) is not widened: no SFS rule writes a membership.
6. **The qname sits at index 3 in the new forms.** `causal_contract.rs` (near 916) and the sentinel
   `bsl-lint/src/sfs_non_authorability.rs` (near 1821) read a qname at index 2 of `field-of` and the `update-*`
   verbs. Both learn the new forms: `membership-field-of` and `update-membership` at index 3, and in a `.bscn`
   file the qnames of a `(member ...)` item. Without this an SFS field's qname passes through the new forms
   unseen. Test in `bsl-lint`: `an_sfs_qname_in_a_membership_form_is_refused`, one case for each of the three.
7. `contracts/tick_content_hash_v1.yaml` `effect_kinds` (near 341) gains `membership_field`.

- [ ] **Step 1: Write the failing tests** (`structural_verbs.rs` tests): `update_membership_under_each_update_op`
  (add, sub, set, scale on one membership; the twin membership of the same member unmoved);
  `update_membership_at_the_range_boundary_is_e_eval_020` (probability field set 1.5);
  `update_membership_of_a_non_member_is_e_eval_038`; `update_membership_records_one_write`
  (`Write::MembershipAttribute` with previous and value); `update_membership_signature_encodes_tag_0x0b`
  (in `identity_codec.rs`). Flip the `update-membership` leg of `refusal_messages_name_their_slice` to assert the
  expression-position refusal still names §2.8 (unchanged) and add a load test that a rule using the verb now
  loads (it no longer reaches E-LOAD-021).
- [ ] **Step 2:** `-p babylon-bsl -E 'test(update_membership)'`. Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** `-p babylon-bsl`, `-p babylon-tick`, `-p babylon-persistence` (manifest arm). Expected: pass.
- [ ] **Run the gate. Commit** `feat(bsl): serve update-membership (#653)`.

### Task 10: Family 23 and the nation case

**Files:** Modify `rust/crates/babylon-bsl/tests/r9_chapters.rs` (the family 23 module Task 1 began).

**Decisions:**
1. The nation fixture: a `HyperedgeType/NATION`, a node type for household groups, one
   `(deffield nation/households int extensive :member NodeType/<GROUP>)`, groups g1 and g2, nations n1 over
   {g1, g2} and n2 over {g1}, with (n1, g1) = 120, (n1, g2) = 40, (n2, g1) = 30. Each nation carries a
   hyperedge field of its own (`nation/code`, an `int`: 1 and 2) so that a rule can tell them apart. Manifest
   ceilings as the other families write them.
2. The "without the field" twin and its pinned hex are Task 1's: the same scenario with the membership
   `deffield` removed and bare member items.
3. **A rule has a node for its subject** (`tick.rs`, near 276): it cannot name `n1` or `g1`. So the rules of
   these tests are rules over the group node type, which reach a nation with
   `(for-each (hyperedges-of self HyperedgeType/NATION) :as n ...)` and select one by `nation/code`, and the
   write is `(update-membership n self nation/households (add 5))` under that guard. Each group carries a
   declared field of its own for the rule to bind and to write a read into.
4. Vectors of §6.2 family 23 that need a rule's `add-hyperedge` (mint-time items, the roster replacement) stay
   owed to the shape-verb lane; the module's doc says so and names their hydration twins in Task 7.

- [ ] **Step 1: Write the failing tests:**
  - `each_nation_reads_its_own_count`: a rule over the group type reads
    `(membership-field-of n self nation/households)` for each nation of the group into two group fields, one
    for each `nation/code`; g1 reads 120 for code 1 and 30 for code 2; g2 reads 40 for code 1.
  - `writing_one_nation_leaves_the_other`: a rule over the group type that, for the nation with code 1 only,
    writes `(update-membership n self nation/households (add 5))`, guarded so that it fires for g1 alone;
    after the tick (n1, g1) = 125, (n2, g1) = 30, (n1, g2) = 40; the state hash differs from before the tick.
  - `a_world_without_the_field_hashes_as_before` (Task 1's) still passes with its hex unchanged.
  - `an_intensive_payload_under_an_unweighted_mean_is_e_type_042` and the same fold with `:weight` loads;
    §2.12's two-hop worked shape loads; `a_fold_over_members_reading_payload_is_bounded_by_max_members`.
- [ ] **Step 2:** `-p babylon-bsl -E 'test(ag_attributed_membership)'`. Expected: the hash pin passes, and the
  rest pass only with Tasks 6 to 9 in.
- [ ] **Step 3:** Fixtures only. A failure here is a defect in the task that owns the code: fix it there, with
  the test that would have caught it.
- [ ] **Step 4:** `mise run rust:check-no-docs --dev` once. Expected: green.
- [ ] **Commit** `test(bsl): family 23, attributed membership and the nation case (#653)`.

### Task 11: Correct the documents

**Decisions:**
1. **The draft rulings.** In `docs/reference/bsl-language.rst`, §3.9 clause 6 gains the scenario form of Task 7,
   marked `[draft ruling — issue #653 — D<n>]` with the next free number of the Draft-Ruling Register, and the
   register gains that row. It records: the form itself; that a bare item or a missing field under a type that
   declares payload is `E-LOAD-047`; that a hydrated member not of the annotated type is `E-EVAL-033`; and
   that a write to a membership is a recorded motion with its own effect signature. Follow D156's row for the
   shape. `docs/reference/bsl.ebnf` gains the production if it carries the scenario dialect.
2. **The decision record.** `ai/decisions/ADR316_attributed_membership_is_served.yaml` (take the next free
   number if 316 is taken; follow the newest record's layout) and its row in `ai/decisions/index.yaml`. It
   states: the authority (Amendment AG clause i, ADR198 R4, the Director's ruling in #653, ADR315 rule H1 as
   the second consumer); that the value lives in the library's membership slot; state-hash section `0x08` and
   stable-graph section `0x09`, both written only when they have rows, and why the stable graph's layout
   version stays 1; the new table and view, and that a database made before them is refused and made again
   (the save-compatibility step R4 names); the four points decided here, as open to the owner's review; and
   what stays owed (the shape verbs in rules, the Allegiance and Electoral systems, the nation hyperedges).

**Files:** `docs/reference/bsl-language.rst` §2.12 "Implementation status" paragraph (served; the
`add-hyperedge` mint form waits on the shape verbs), the D-row register entry for #653 status if one exists
(`rg -n '#653' docs/reference/bsl-language.rst`); `docs/reference/graph-storage-capability-delta.md` (the
membership slot is used); the `MembershipPayload` doc in `hypergraph_store.rs`; the `GraphSubstrate` crate doc
("14 methods") and `state_hash.rs` / `stable_state.rs` module docs if not done in their tasks.

- [ ] **Step 1:** No test. Check with `rg -n 'unserved|refuse.*#653|#653-blocked' docs rust/crates` that no
  remaining text claims the lane is refused; hits in old reports and ADRs stay (AGENTS.md "Records").
- [ ] **Step 2:** Targeted Vale on the changed `.rst` and `.md` lines only; `yamllint -c .yamllint.yaml` on the
  decision record and the index.
- [ ] **Commit** `docs(bsl): attributed membership is served (#653)`.
