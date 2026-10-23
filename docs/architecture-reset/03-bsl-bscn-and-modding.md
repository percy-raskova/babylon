# 03 — A public content contract for BSL, BSCN and numeric settings

**Status: current source facts plus a proposed package contract.** Source snapshot:
`99f998e3dffb301a218a8a4e0ed809f440dafef2`. The examples below use existing Babylon syntax. Package manifests,
dependency resolution, external package selection and the acceptance workflow are proposals; this chapter does not
claim a working mod CLI or launcher.

Babylon already has the beginnings of the content separation observed in [Victoria 3](02-victoria-3-analysis.md):
BSCN describes structure, BSL describes permitted rules, and TOML supplies typed numeric controls. The reset should
finish that boundary before exposing an external mod ecosystem. The first deliverable is one local mod-like example
admitted through the same path as first-party content, as specified in [the implementation
packets](08-implementation-packets.md) and [acceptance requirements](09-acceptance-and-governance.md).

## What exists today

| Surface | Current responsibility | Important limit |
| --- | --- | --- |
| `.bscn` | Scenario declarations, fields, vocabulary and graph structure through the general loader | The national campaign's authored structure is declaration-only; generated economic opening data supplies its entities |
| `.bsl` | Typed rules with causal role, evidence class, material basis, fuel and causal placement | Does not add a mathematical primitive, waive effect permissions or rewrite the engine schedule |
| `defines.toml` | Typed, validated numeric parameters captured at campaign creation | Current schema has exact supported tables and fields, not arbitrary user settings |
| Native Rust | Material algorithms, typed state, conservation, execution and commit authority | Public content selects and parameterizes admitted behavior; it does not replace native authority |
| Captured foundation content | Immutable source and content identity used by campaigns | This is not yet a general external package resolver |

The [scenario loader](../../rust/crates/babylon-bsl/src/scenario.rs) supports a scenario with declarations and graph
forms, plus named declaration preludes. It resolves local names and rejects duplicates or unknown references.
Prelude composition permits declarations, not arbitrary node creation. Duplicate declarations are not generally a
merging mechanism: identical enum re-declaration has a specific supported case, while other repeated declarations
can fail.

The live [national structure](../../content/scenarios/national/structure.bscn) declares territories, businesses,
households, social classes, organizations and participant bodies. It declares an `ORGANIZATION_BODY` hyperedge
vocabulary and typed fields. It does not contain a full national world written out as millions of text objects. This
distinction must survive any user-facing documentation: the general BSCN loader and national source admission are
connected capabilities with different input responsibilities.

Rules pass grammar, typing, effect and causal checks. [Governed
attribution](../../rust/crates/babylon-bsl/src/causal_contract.rs) pins the role and evidence class of known
built-in IDs. Unknown mod IDs are self-declared, but remain subject to the relevant validation and effect
restrictions. Geography and captured resident counts have explicit write prohibitions. Native compositions have
additional ownership limits. A package cannot acquire authority by calling itself trusted.

The [phase compiler](../../rust/crates/babylon-tick/src/phase_order.rs) owns execution placement. It validates
anchors and sorts by execution key, then rule-ID bytes. Same-rank rules compose sequentially. Package discovery
order must not become a second scheduler. The proposed loader compiles content once for an admitted campaign; it
does not introduce a generic dependency graph of mod-authored simulation phases.

Current foundations already capture content. [Foundation
framing](../../rust/crates/babylon-persistence/src/foundation/content.rs), [economic
content](../../rust/crates/babylon-persistence/src/economic_content.rs) and [Michigan
construction](../../rust/crates/babylon-persistence/src/michigan_material.rs) show the admission and source-capture
boundary. Several first-party inputs use `include_str!`; saving captured source does not mean the current executable
discovers arbitrary mod directories.

## Proposed package identity and resolution

Version one should support a small manifest with the following required meanings. This is a schema proposal, not a
manifest accepted by today's code.

| Manifest property | Proposed meaning |
| --- | --- |
| Manifest version | Exactly the supported manifest schema, initially 1 |
| Package ID and version | Globally qualified stable identity and an exact human version label |
| Content contract | Exact supported content-ABI revision; unsupported inputs fail clearly |
| Source units | Stable logical source ID, kind, relative path and SHA-256 for each source |
| Dependencies | Exact package ID, version and manifest digest; no version-range solver or automatic downloading |
| Replacements | Exact logical source unit being replaced and its expected previous digest |

The following two manifests define a complete numeric replacement example. They are **proposed wire syntax**, not
files today's executable loads. All shown keys are required; empty dependency/replacement arrays are explicit. A
package's dependency identity is the SHA-256 of its exact UTF-8 manifest bytes, including its final LF; every source
must separately match its SHA-256. The manifest therefore pins the ordered sources and dependency identities. This
transport identity is distinct from the engine's admitted content digest.

The base package's `defines.toml` is the unchanged current Michigan file. With exactly the bytes below and one final
LF, its manifest SHA-256 is `ad2e40c369a427ceb89ce169ed638b2b6f82bcb9d829a24bf9b3aa7262e7e25e`:

```toml
format_version = 1
id = "babylon.michigan-regional"
version = "source-99f998e3"
content_abi = "babylon-content-v1"
host_profile = "michigan-regional-v6"
dependencies = []
replacements = []

[[entrypoints]]
source_id = "michigan/defines"
kind = "defines"
path = "defines.toml"
sha256 = "7176764f233190164c985ca3847c42e701ba5421824a4277a51e92739b55a2aa"
```

The replacement package contains the complete file with only 40 changed to 44, as worked below. Both source digests
were calculated from the current file bytes:

```toml
format_version = 1
id = "mods.local.michigan-hours"
version = "1"
content_abi = "babylon-content-v1"
host_profile = "michigan-regional-v6"

[[dependencies]]
id = "babylon.michigan-regional"
version = "source-99f998e3"
manifest_sha256 = "ad2e40c369a427ceb89ce169ed638b2b6f82bcb9d829a24bf9b3aa7262e7e25e"

[[entrypoints]]
source_id = "michigan/defines"
kind = "defines"
path = "defines.toml"
sha256 = "27c7b83e7b0a39dbfc77d325ddd85a7abd3f6538cfea24931088919b1517c7d8"

[[replacements]]
dependency_id = "babylon.michigan-regional"
source_id = "michigan/defines"
expected_sha256 = "7176764f233190164c985ca3847c42e701ba5421824a4277a51e92739b55a2aa"
```

`entrypoints` is an ordered array, with closed kinds `defines`, `scenario`, `prelude` and `rules`; order within each
kind is retained. Paths use normalized forward-slash relative components: reject empty, `.` or `..` components,
absolute paths, backslashes and escaping symlinks. Reject unknown fields at every level, duplicate source IDs
without an explicit replacement, malformed digests, unavailable exact dependencies and unsupported host/category
combinations. No source is admitted merely because filesystem discovery found it.

Sources are UTF-8, bounded, and admitted through the existing language parsers. Package paths remain within their
package: absolute paths, parent traversal and symlink escapes are rejected. The manifest parser must itself reject
unknown fields. Packaging must preserve source identities for diagnostics and content hashing, and must respect the
underlying source/composition bounds rather than removing them for mods.

Resolve exact dependencies first. Reject missing dependencies, digest mismatches and cycles. Use deterministic
topological ordering, with package-ID byte ordering for independent packages. This establishes reproducible assembly
and diagnostics; the phase compiler still determines execution.

Use **whole source-unit replacement** in version one. A mod that changes numeric defines supplies the complete
replacement defines unit. A mod that replaces a rule source supplies the complete unit, after which the final
content set is checked for duplicate rule IDs and all other semantic constraints. There is no implicit deep
TOML/JSON merge, filename-based last-wins rule or field-patch language.

Two packages replacing the same prior source are a conflict, even when one happens to sort later. A deliberate chain
must depend on the exact prior replacement and name its digest as the expected input. This makes the final source
set explainable: every changed unit has one explicit predecessor and one accepted successor. A conflict report names
both packages and the source unit; it does not silently select a winner.

New package-authored identities should use a package-qualified namespace. Explicit replacement of a built-in unit
may retain its established IDs, but those IDs retain their governed attribution. Package identity does not create a
bypass around built-in checks.

## One admission path, then captured content

First-party and mod sources must share the same admission pipeline:

1. Read the selected, bounded local sources and verify their declared digests.
2. Resolve dependencies and explicit replacements into one final source set.
3. Parse, resolve references, type-check, validate effects and compile the existing causal schedule.
4. Use the fixed host profile below and validate the resulting typed opening or fixture graph.
5. Capture exact sources, resolution result, content digest and required engine/content identities before publishing
   a campaign.

This is a proposed workflow, not a list of existing command names. Parsing or composition failure must leave no
partially admitted campaign. A useful diagnostic includes package, source, location, failing reference and specific
error. Runtime should hold the admitted immutable artifact and mutable world separately. It should not read, merge
or recompile mod text every period.

Version one has exactly two host profiles, both wrapping existing execution paths:

| Profile | Accepted effective source set | Existing host and acceptance scope |
| --- | --- | --- |
| `michigan-regional-v6` | Exactly one complete `defines` unit; no custom scenario, prelude or rule units | `MichiganMaterialCatalog::from_defines_toml`, then `MichiganContentPreset::FourWeekStandard.create_foundation` in [Michigan content](../../rust/crates/babylon-persistence/src/michigan_content.rs). Existing native catalog content supplies structure and rules. This is P7's full game-facing campaign witness: admit, open in the ordinary client, advance, store, reopen and replay the numeric modification. |
| `authored-graph-v1` | Exactly one `scenario`, zero or one declaration `prelude` unit and exactly one `rules` unit, which may contain multiple rules | Existing `ReplayTickSession`, `FoundationContentBundle::try_new` and `CampaignFoundation::capture` through the authored foundation path. The worked scenario uses no prelude. P7b must deliver a saved, viewable graph campaign; it does not claim an economic campaign. |

Selecting another profile is an explicit unsupported-profile error. Both profiles must complete capture, execution,
supported viewer consumption, durable storage, reopen and replay. The authored graph profile uses the existing graph
simulation path; it does not route arbitrary authored nodes into the national material catalog or create a second
simulation engine.

### Mandatory P7b: save and replay the authored graph campaign

The adapter is fixed, not an optional later design. Reuse the preparation pattern in
[`foundation_from_sources_with_seed`](../../rust/crates/babylon-persistence/src/michigan_economy.rs): construct the
real checked Michigan geographic `MaterialState` and its reference manifest; admit the resolved scenario, optional
prelude and rules through `ReplayTickSession::new` with an explicit campaign/session identity and seed. The
profile's defines bytes are the exact UTF-8 bytes `{}`; they do not supply economic coefficients. Capture the real
reference bytes and digest rather than substituting an empty reference or loading geography implicitly on reopen.

[`FoundationContentBundle::try_new`](../../rust/crates/babylon-persistence/src/foundation.rs) captures scenario,
prelude, rule, defines and reference sources. `CampaignFoundation::capture` then captures the tick-zero stable
graph, world registers, resolver manifest, prepared environment, session identity and seed. Its existing
reproduction check must prove that the captured scenario creates the captured graph. Retain these checks when
integrating the proposed owner; a package digest alone does not establish a valid world.

Store this profile in the **same SQLite container and owner** specified in [chapter
06](06-target-runtime-and-sqlite.md). `snapshot.manifest_bytes` identifies `authored-graph-v1` and its required
closed section set: stable graph, world registers, resolver, prepared environment, geographic material state and
replay identity. Captured content occupies the proposed `content_entry` table; opening/current/historical
roots use `snapshot`, `snapshot_chunk` and `state_chunk`. The profile has no economic circuit sections. Their
absence is declared by the profile, never mistaken for an incomplete economic snapshot. Use the same current-root
atomic publication, journal, integrity checks and retention rules; no parallel save format or fixture-only writer is
allowed.

Wire the supported graph viewer through the owner's bounded public projection. For this campaign, expose stable
subject identity, node type and the declared `social-class/probability` field as public, read-only fixture facts.
They remain visibly labeled Designed. Do not offer an unrestricted field browser or manufacture earned observations.
Player-command submission is unsupported for this profile and returns a specific unsupported-command error; ordinary
advance, save, reopen and historical inspection still work. An empty player-command set must not weaken command
validation in economic campaigns.

P7b acceptance starts with the two-node scenario below. A BSCN variant adds a third social-class node initialized to
`0.125p`; the viewer must show three nodes, and the `0.25i` rule gives the new node `0.375p` after one advance.
Separately compare the two BSL increments on the original two nodes. Capture each variant, advance, save, close,
replace the installed source files with different valid sources, and reopen. Readback and replay must use each
save's captured structure and rule, reproduce its original identities and effects, and retain its public history.
Parser tests and `run_once_into` alone cannot complete P7b.

P7b also routes the first-party [national declarations](../../content/scenarios/national/structure.bscn), [Michigan
material rule](../../content/scenarios/michigan/material-cycle.bsl) and [organizer
rules](../../content/scenarios/michigan/organizer-cycle.bsl) through this same resolved-source admission boundary.
Embedded defaults become inputs to that boundary, not a second bypass. This integration preserves each host's
accepted source categories; it does not admit arbitrary national scenario replacements. Apply the existing
attribution, field ownership, effect, reference and phase checks unchanged. Native material algorithms stay native.
At least the permitted probability-rule variant must reach an authentic saved graph campaign. This proves content
replacement through capture and replay while making no claim that the demonstration qualifies national economic
play.

Saved campaigns retain their captured content. Editing a local package affects a newly admitted campaign, not an
existing campaign silently. Each portable campaign contains its captured source bytes and exact dependency
identities; reopening must not depend on another save or a global content store. A disposable installation cache may
reuse admitted artifacts by content and engine identity, but losing that cache must not lose authored history or
prevent reconstruction from the campaign. These retention requirements align with [chapter
07](07-history-replay-and-archive.md).

This does not promise compatibility across arbitrary future engine versions. The repository's
one-current-implementation rule still applies: unsupported saves or content fail explicitly unless the Director
separately requests compatibility work.

## Worked example 1: a numeric change

**Existing syntax; proposed package replacement.** Copy the complete current [Michigan
defines](../../content/scenarios/michigan/defines.toml) as a replacement source unit and change just this table's
value:

```toml
[staffing]
WORK_HOURS_PER_PERSON_WEEK = 44
```

This excerpt is not a standalone valid defines file. The remaining required schema, duration, organizer, process,
route and other tables remain in the complete replacement. The change is **Designed**, not an observed statement
about working time.

The current [typed parser and validator](../../rust/crates/babylon-persistence/src/michigan_defines.rs) require an
integer between 1 and 168, a supported 28-day period and schema version 6. A period has four weeks. The new setting
therefore gives 176 hours per person per period. With the existing 20 employed sheet-rolling workers, available
labor becomes 3,520 hours instead of 3,200. The existing opening plan still requires 32 batches × 100 hours = 3,200
hours. Its throughput ceiling remains 32 batches. **This change does not establish higher output.**

The reverse example catches a real interaction: changing 40 to 32 alone leaves only 2,560 available hours, so the
existing 3,200-hour opening plan fails validation. Tuning is constrained by a coherent opening, not merely by a
scalar's range.

End-to-end acceptance for the proposed local content path is: verify that only the intended setting differs; admit
the complete replacement; inspect the captured typed setting and opening labor budget; run the ordinary material
close; confirm valid conservation and unchanged throughput limits; save and reopen; confirm that replay uses the
captured 44-hour setting after the source file changes. Reject zero, 169, fractional values, unknown keys and
infeasible opening plans before campaign publication. Existing campaigns using 40 remain pinned to their source.

## Worked example 2: scenario structure

**Existing general-loader syntax; bounded authored graph campaign proposed by P7b.** The following small scenario
declares an intensive probability field and two social-class nodes. It follows the scenario form already exercised
in [causal contract conformance](../../rust/crates/babylon-tick/tests/causal_contract_conformance.rs):

```lisp
(scenario mods/local-probability-fixture
  (deffield social-class/probability probability intensive)
  (node first NodeType/SOCIAL_CLASS
    (social-class/probability 0.25p))
  (node second NodeType/SOCIAL_CLASS
    (social-class/probability 0.5p)))
```

This is a deliberately small language/host fixture, not a realistic political model. It uses the current
`NodeType/SOCIAL_CLASS` vocabulary and probability literals. It neither adds a mathematical primitive nor changes
population counts, ownership or geography. Node names identify local authored objects; the loader resolves their
stable content identities. The `intensive` declaration prevents treating the field as an additive population total.

Its first acceptance is structural: load exactly two nodes, resolve the declared field and read back 0.25 and 0.5.
Duplicate local names, unknown node types, absent field declarations and out-of-domain initial values must fail. A
node-bearing source must be rejected if passed as a declaration-only prelude.

Its first execution check connects to the rule below through `run_once_into`, the existing host entry point used by
conformance tests. Completion then requires the P7b authored foundation, owner, viewer and saved replay path above,
including the third-node structural variant. A new external package distribution mechanism is unnecessary to prove
that connection.

This demonstration is **not a complete economic campaign**. The current national pipeline builds opening entities
from admitted source data rather than hydrating this arbitrary node file as a replacement national economy. The
selected v1 scope is `authored-graph-v1`; its existing generic foundation/replay path is fixed above. A parser
success cannot qualify it as a saved campaign. P7a's numeric Michigan modification supplies the separate economic
witness; P7b must complete the graph campaign witness.

## Worked example 3: a permitted scripted change

**Existing BSL forms; proposed fixture variant.** Apply this rule to the previous scenario:

```lisp
(rule mods/local-probability-step
  :role mechanic
  :evidence designed
  :material-basis "A bounded host fixture advances a declared probability field."
  :fuel 64
  (anchor :before survival)
  (bindings
    (binding probability :field social-class/probability))
  (when (<= probability 0.75p))
  (effects
    (update-node self social-class/probability (add 0.25i))))
```

The behavioral modification is the increment: a baseline variant uses `0.125i`; this variant uses `0.25i`. On the
same initial graph, the baseline produces 0.375 and 0.625, while this variant produces **0.5 and 0.75** after one
execution. These binary fractions avoid an accidental decimal-rounding claim. The guard bounds this variant's write
to at most 1.0. This field has no conservation meaning and is not an economic account or demographic authority.

The binding and typed update syntax come from [causal contract
conformance](../../rust/crates/babylon-tick/tests/causal_contract_conformance.rs); the explicit mod anchor comes
from [phase-anchor conformance](../../rust/crates/babylon-tick/tests/phase_anchor_conformance.rs). The grammar
supports `<=`. This example was checked against those source forms; it is a proposed combination, not a newly
executed conformance result. Its fixture declaration of `Designed` does not approve a new gameplay theory or grant a
production mod permission to invent arbitrary downstream outcomes. P7b nevertheless must deliver this bounded rule
variant through the real authored campaign capture, storage and viewer path, not leave it confined to a parser
demonstration.

Acceptance must trace the real path: scenario and rule admission, placement before survival, execution over the two
qualifying nodes, typed field updates, audit producer identity and resulting graph identity. Reversing input
discovery order must not change execution identity. The two increments must produce different content identities and
different post-state, while repeated identical inputs must reproduce the same result. Save/reopen and replay are
mandatory P7b acceptance, including after installed sources change.

Negative acceptance should use meaningful refusals: zero fuel; an unknown field; an invalid probability write; a
forbidden anchor inside the material causal spine; or an attempt to write `territory/county-fips`,
`household/persons` or `household/households`. The current contract prohibits those last fields for every rule role.
Invalid content must fail before hydration where its failure is statically knowable; runtime failure must discard
the detached candidate. Do not accept “the parser loaded it” as evidence of authority or correct publication.

## Native material authority stays explicit

The actual first-party [material rule](../../content/scenarios/michigan/material-cycle.bsl) invokes
`(material-cycle)` after metabolism. It does not reimplement the productive and distributive circuit in text. Native
Rust owns exact inventory movement, freight, staffing, settlement and the relevant conservation checks. Numeric
content changes must pass those algorithms; scripted rules cannot manufacture balances or overwrite native-owned
fields to obtain a desired outcome.

A new rule may use only supported language operations and its permitted causal role. Recognizers, intents and
external events retain their exact allowlists and default-deny behavior. No package introduces executable shocks
merely because the language has an external-event role. No package adds an arbitrary SQL query, native DLL, shell
command, network call, mathematical primitive, sigmoid or second fixed response curve. Extensions requiring new
primitives, weaker prohibitions or a reserved-theory change remain Director decisions under the existing
constitution.

The initial package surface should contain only the admitted data/rule source kinds. Launcher integration, Workshop
distribution, native extensions, live hot reload and automatic dependency fetching are outside this first delivery.
The useful milestone is smaller and observable: one first-party/local-mod content change reaches a newly admitted
campaign, produces the intended bounded effect, preserves exact authority and replay, and fails clearly when content
conflicts. That gives Babylon an inspectable modding foundation without adding a second engine or a second source of
truth.
