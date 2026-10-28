# Babylon architecture reset: start here

This is an implementation dossier for DeepSeek Flash V4.1 in OpenCode. It records the Director's direction, the
evidence behind it, and a bounded sequence for replacing Babylon's oversized campaign representation with a
game-sized runtime and embedded saves.

**Status: proposed implementation specification, not implemented behavior or a ratified constitutional amendment.**
Writing this dossier does not qualify the current national game. The documentation task changes no engine, database,
save, tracker, or historical report.

Research date: **23 October 2026**. Inspected Babylon source: **`99f998e3dffb301a218a8a4e0ed809f440dafef2`**. Both
the research checkout and the primary checkout had this HEAD. `PER-337`, `PER-342`, and `PER-343` remained open in
the inspected Linear state. Source and policy can drift; packet P0 checks that narrowly before implementation.

## Director decisions

1. Babylon is an entertainment-first political-economy game. Detail must earn its cost through a player decision, a
   legible consequence, or a necessary causal relationship.
2. Preserve national county participation. Use **authored, stable differences in detail**, not a camera-driven
   change in the underlying economy.
3. Target **SQLite campaign persistence and compact typed Rust state**. PostgreSQL is the comparison baseline during
   the bounded witness, not a second production backend to maintain.
4. Target a **16 GB desktop**, **4,000,000,000 bytes of combined running-game memory**, and ordinary four-week
   advances within **30 seconds**, including durable saving and the briefing needed to continue. These are design
   targets awaiting executable evidence.
5. Keep permanent player history and replay inputs. Complete technical detail is not automatically permanent
   campaign state.
6. Treat **BSL/BSCN as Babylon's moddable authored-content layer**, with typed TOML controls. Reuse the existing
   language and interpreter boundary.
7. Keep one current implementation. Preserve older saves as evidence; refuse unsupported versions without building
   compatibility machinery solely to keep them playable.

The 10 MB-per-period storage ambition remains. Older 40 MB development allowances are not the redesigned game's
target. [Acceptance and governance](09-acceptance-and-governance.md) defines the distinction and the proposed
defaults introduced by this dossier.

## Read by purpose

| Need | Read |
| --- | --- |
| Understand the expensive dead ends | [01: Evidence and failed approaches](01-evidence-and-failed-approaches.md) |
| Understand what Victoria 3 actually demonstrates | [02: Victoria 3 analysis](02-victoria-3-analysis.md) |
| Implement authored content and mod support | [03: BSL/BSCN and modding](03-bsl-bscn-and-modding.md) |
| Locate current code and consumers | [04: Current architecture](04-babylon-current-architecture.md) |
| Decide where each datum belongs | [05: Data and model contract](05-data-and-model-contract.md) |
| Implement the embedded save owner | [06: Runtime and SQLite](06-target-runtime-and-sqlite.md) |
| Implement history, recovery and Archive | [07: History, replay and Archive](07-history-replay-and-archive.md) |
| Execute a bounded unit of work | [08: Implementation packets](08-implementation-packets.md) |
| Establish approval and acceptance | [09: Acceptance and governance](09-acceptance-and-governance.md) |

Read this file and 08/09 first. Then load only the chapters and source files required by the selected packet. Do not
read the entire ADR corpus, every old chat, or every source file at the start of each session.

## Copy-paste implementation prompt

```text
Implement the next authorized packet in docs/architecture-reset/08-implementation-packets.md.

First read repository AGENTS.md, docs/architecture-reset/README.md, the selected
packet, and the relevant sections of 09-acceptance-and-governance.md. Treat
this dossier as an implementation proposal. Do not claim its proposed APIs,
SQLite schema, CLI, or performance targets already exist.

Run P0's narrow source/ownership reconciliation once. Do not repeat the
historical research. If the current source differs, inspect the relevant diff
and explain whether it changes the packet. Use current Linear identity and
scope when implementation is authorized; do not silently reassign issues.

Before activating SQLite as authoritative campaign storage, verify the
specific storage/governance amendment has Director approval. An isolated,
non-production comparison witness may be developed while that approval is
pending. Do not treat permission to write this dossier as amendment ratification.

Keep the engine's deterministic judgment in Rust memory. Use the specified
compact state, SQLite owner, typed scoped readers and captured BSL/BSCN/TOML
content. No generic multi-backend framework, runtime dual writer, silent
fallback, old-save compatibility layer, second scripting language or new
mathematical primitive is authorized by this dossier.

For each packet: identify the relevant failure, make the narrow change,
trace it to its real consumer, run the smallest sufficient checks, and retain
the exact results. Use RED/GREEN for meaningful regression tests. Do not
run Sphinx, cargo doc or ci:rust. Do not repeat broad gates when the source
and evidence have not changed. Serialize heavy jobs and respect current
fixture/native-session ownership.

Keep gameplay and scientific claims separate. A passing codec test does not
prove a playable game; a forecast is not an actual long-run measurement.
Do not lower a requirement or edit a baseline to hide failure.

If a packet fails its stop condition, preserve the result and report the
specific blocker. Do not switch database engines, invent a new architecture,
or launch an open-ended optimization loop. Continue independent authorized
work only where the blocker cannot invalidate it.

Finish with the packet completion record from chapter 08: exact head, changed
behavior, checks, measurements, limitations, and next eligible packet. Do not
claim broader acceptance. Follow the repository's commit/PR/merge rules and
the user's current authorization; this prompt is not blanket merge authority.
```

## How to interpret the evidence

- **Current source:** inspected code at the pinned commit. Static inspection establishes implementation shape, not
  runtime performance.
- **Historical measurement:** a preserved observation from a named run/chat. It is not a new benchmark at the pinned
  commit.
- **Observed shipped artifact:** bytes, types, symbols or resources in the installed Victoria 3 version. Static
  analysis is not an execution trace.
- **Proposed:** a decision or interface for implementation, including every new SQLite table and content-package
  command.
- **Unknown:** an evidence gap. Unknown does not mean zero cost, unsupported forever, or permission to invent an
  answer.

The central diagnosis is that Babylon already computes ticks in memory. Costs accumulate in oversized state,
repeated admission/canonicalization, history-dependent reconstruction, large observation products, and retained
evidence. Compression and identity sharing already exist. The redesign must reduce those obligations; changing a
database driver alone does not accomplish it.

The [source identity manifest](evidence/source-identity.json) records the checked repository files and hashes. The
[documentation verification record](evidence/documentation-verification.json) separates completed documentation
checks from implementation and performance work that has not run. Chapter 05 links the complete disposition
inventories; chapter 01 links the compact chat evidence index.

## Boundaries and preservation

Preserve exact accounting, immutable geography, native hyperedges, typed causal roles, evidence classes, atomic
publication, finite time and scoped knowledge. Coarse representations must not erase poverty, ownership, access
constraints, unresolved shipments or the costs of organization. The theory discussion does not establish a universal
lossless compression theorem.

This dossier is the canonical handoff for this investigation, not a competing live architecture authority. After
implementation and ratification, update the existing live architecture, Constitution, contracts and contributor
instructions at the identified points. Keep historical reports and old ADRs intact; supersede them explicitly where
required.

Repository files are linked relative to this folder. Absolute Victoria paths are local evidence locations and may
not exist on another computer. Do not bundle proprietary executables or personal save contents with a public PR. The
retained REA observation contains metadata, not the game or save payload.
