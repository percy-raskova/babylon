# 02 — What Victoria 3 actually teaches us

**Status: read-only investigation, followed by architectural recommendations.** Victoria 3 is a useful example of
organizing a large strategy game around shared definitions, grouped populations and compact mutable objects. It does
not establish that Babylon should copy its simulation, scripting language or persistence format. The relevant lesson
is to decide which distinctions deserve live objects, then give immutable content, working state, caches and saved
history different responsibilities.

## Identity and method

The installed copy inspected on 2026-10-23 identifies itself as **Victoria 3 1.13.11, Matcha**, Steam build
**24799966**. This identifies the local artifact, not the latest public release. The [launcher
settings](</home/user/.local/share/Steam/steamapps/common/Victoria 3/launcher/launcher-settings.json>) and [Steam
manifest](/home/user/.local/share/Steam/steamapps/appmanifest_529340.acf) supply those identities. Its native
executable is an x86-64 ELF PIE with symbols and DWARF debug information:

| Artifact | Verified identity |
| --- | --- |
| [Native executable](</home/user/.local/share/Steam/steamapps/common/Victoria 3/binaries/victoria3>) | 1,576,608,824 bytes; SHA-256 `7574598cfb51ec478d7b012dd1696a0acb4161a9a4170a741353c89aff3abe2e` |
| Game revision | `15aa89ae429b6bcff8d195f2a650f98ba95cd64c` |
| Clausewitz revision | `a93467deb3d07433163df1bf541cce7a05dd110e`, branch `caligula/release/1.13.x` |
| Sample save metadata | Version 1.13.9; older than the installed executable |

REA 6.4.0 was used for artifact inspection. It successfully inventoried the ZIP portion of a save. Its native
analysis providers were unavailable: Ghidra and IDA were unconfigured, Hopper absent, and the pwntools interpreter
required for binary-layout inspection unconfigured. **No REA decompilation was performed.** Native findings below
instead come from offline ELF symbols, DWARF types and bounded disassembly using GDB 16.3 and binutils 2.44. GDB
auto-loading and debuginfod were disabled; the game was neither launched nor attached to. Installed files were not
modified.

This distinction matters. A type layout establishes fields and ownership. A symbol establishes an available
implementation entry point. Neither, alone, establishes execution frequency, total memory consumption or a complete
loading algorithm. Public developer diaries are separately labeled historical explanations.

## Installation bytes are mostly assets

A regular-file inventory found the following sizes. These counts exclude symlink targets and distinguish base
content from DLC; they are not heap measurements.

| Installed area | Bytes | Interpretation |
| --- | ---: | --- |
| `game/gfx` | 10,160,670,804 | Graphics dominate the installation |
| `game/dlc` | 3,064,117,620 | Additional assets and content |
| `game/sound` | 995,964,747 | Sound assets |
| `game/localization` | 116,637,674 | Localized text |
| `game/map_data` | 98,909,735 | Authored map data |
| `game/common` | 25,208,910 | 3,091 definition and related files |
| `game/gui` | 6,028,997 | UI definitions |

The Steam manifest reports 17,433,879,543 installed bytes. That is not evidence of a 17 GB economic database. A
simple top-level-definition count in base text files found 53 goods, 15 population types, 115 building templates,
433 production methods, 197 method groups and 317 cultures. These are static definition counts, not exhaustive DLC
or runtime entity counts.

The important separation is visible without guessing at the engine. In [building
definitions](</home/user/.local/share/Steam/steamapps/common/Victoria 3/game/common/buildings/02_agro.txt>), a rye
farm refers to production-method-group identifiers. [Those
groups](</home/user/.local/share/Steam/steamapps/common/Victoria
3/game/common/production_method_groups/02_agro.txt>) refer to method identifiers.
[Methods](</home/user/.local/share/Steam/steamapps/common/Victoria 3/game/common/production_methods/02_agro.txt>)
provide input/output and employment modifiers. A building instance need not repeat the full authored recipe,
presentation and labor definitions.

**Recommendation:** Babylon should retain immutable typed definitions once, address them by stable IDs and keep only
changing quantities in campaign state. Its current compression and identity tables already do some of this; [chapter
04](04-babylon-current-architecture.md) distinguishes those existing mechanisms from the proposed stronger runtime
separation.

## “Database” can mean an in-memory object registry

Native DWARF establishes a concrete population storage design. `CPopManager` owns `CPdxRefManager<CPop>`, which owns
`TPdxRefDatabase<CPop, 8u>`. That type derives from `NPdx::TComponentStorage<CPop, 8u>`. Its layout contains pages
of aligned object slots, an ID lookup array, object-count and slot-management fields, and reference/version masks. A
page holds 1,024 core population objects.

The observed `CPop` core is **88 bytes**. It contains shared definition pointers, scalar and fixed-point values, and
four-byte references for relationships such as state, workplace and culture. The base reference object carries an
ID. This directly supports “paged in-memory object registry with references” for this particular database. It is not
a document-store record or a relational row fetched for each economic calculation.

The 88-byte figure is emphatically **not total memory per population**. Separate typed component arrays hold
population size, political strength, acceptance, food security, qualifications, money, job satisfaction and other
attributes. `SPopCachedData` occupies 16 bytes in the observed layout; `SPopEphemeralData` occupies 144 bytes and
includes trend objects. Indexes, allocation slack, shared definitions, other components and historical samples add
further memory.

`SPopManagerCache` indexes populations by several useful relationships, including state/type, country and culture. A
`CUpdateSpreader<CPop, 30u>` is also present. The latter identifies an update-spreading mechanism, but its template
argument does not prove a particular real-time or simulation-day schedule without tracing its callers.

The launcher has SQLite tables for mods, playsets and DLC. That does not make SQLite Victoria 3's economic
simulation backend. Conversely, finding these native registries does not prove that no SQL library is used anywhere.
The narrow conclusion is enough: the game's central population object ownership demonstrably differs from “one giant
JSON document in a database.”

**Recommendation:** Babylon's simulation owner should hold admitted typed state in memory, with durable storage at
explicit commit boundaries. Choosing SQLite, PostgreSQL or a document store is a separate persistence decision.
Changing that product cannot remove unnecessary live objects or repeated reconstruction.

## Populations are groups, and small groups are deliberately merged

The authored [North American population history](</home/user/.local/share/Steam/steamapps/common/Victoria
3/game/common/history/pops/05_north_america.txt>), lines 549–572, describes Michigan with five initialization groups
totaling **152,000 people**. That is five authored records representing many people. Employment and later processes
can split groups, so it is not evidence that Michigan always has five runtime populations.

The installed [defines](</home/user/.local/share/Steam/steamapps/common/Victoria
3/game/common/defines/00_defines.txt>), lines 1646–1671, explicitly describe consolidation of economically or
politically insignificant small populations within a building or state. Minor, moderate, aggressive and maximum
workforce thresholds are 10, 30, 50 and 100. Additional thresholds govern the number of same-profession groups.
Global scaling uses a 50,000–100,000 population-object range; these numbers are neither represented people nor a
hard object cap. The installed [game rules](</home/user/.local/share/Steam/steamapps/common/Victoria
3/game/common/game_rules/00_game_rules.txt>), lines 97–114, select moderate consolidation by default.

This is a visible design tradeoff: preserve distinctions while they affect gameplay, and consolidate some
differences when their cost exceeds their effect. Babylon should make its own rule explicit. Household and workplace
grouping must preserve ownership, access to necessary goods, labor position, bottlenecks and organized relationships
where those differences change a player's options. A rare identity must not disappear merely because its population
is small. National coverage does not require equally detailed objects everywhere. [Chapter
05](05-data-and-model-contract.md) specifies the proposed uneven-detail model.

## Saves compress well; that is a different optimization

A single local autosave was inspected without reporting personal campaign details. Its total size was 9,180,515
bytes: a 1,772-byte prefix followed by a ZIP archive. The archive contained one `gamestate` member, **72,336,841
bytes uncompressed and 9,178,627 bytes compressed**, using DEFLATE. That is approximately **7.88× compression**, or
an 87.3% reduction in member bytes.

REA could not open the custom `.v3` framing directly. An exact copy of the ZIP suffix was made in analysis scratch
space, its CRC verified, and REA's safe artifact graph provider inventoried it. The [preserved REA
observation](evidence-victoria/rea-archive-observation.json) contains evidence ID
`ev_a98330281f68bf8a36a4964167e24f52ea0a8bb9106de451ff0e47c9791e0b09`; its nested inventory is
`ev_df14b0c8565a91bd7121d8045687dcc93bad60b42bccf176e51f3886829ff25e`. The original save SHA-256 was
`20aae8cc91d765410be99627aa53d81c4f97d055f8a1aa00cb756c5789fe7437`; the derived ZIP SHA-256 is recorded in the
observation. Neither the save nor its gameplay contents are included in this dossier.

These are one save's measurements, from version 1.13.9. They do not establish average campaign growth,
current-version loading time or memory footprint. Archive inventory also does not decode the member's semantic
schema. Repetition is consistent with good compression, but compression does not reduce how many economic entities
the tick must visit. Babylon needs both representation reduction and compressed persistence, in that order of
responsibility.

## Caches and trends have their own structures

The observed `CTrend` layout is 48 bytes before its separately allocated data. It includes a sample rate,
samples-per-channel setting and channel map; channels carry latest-sample information and numeric sample arrays.
`CTrendManager` contains a weekly counter and collections of selected population, country and interest-group update
targets. This supports explicit sampled history structures, not an assertion that every field is saved every tick.
Exact retention duration was not established.

Bounded disassembly of `CPopManager::WriteMembers` at `0x3c00220` showed a test of `CGameState::_WriteCachedMembers`
at `0x3c00252`, followed by conditional cached-member writing. Separate `WriteCachedMembers` and
`RecalculateCachedData` methods exist. Thus the implementation distinguishes ordinary state from caches and has a
controlled path for cache serialization. The inspection did not establish when each save mode enables that flag or
whether all caches are reconstructible.

**Recommendation:** Babylon should give each cache an explicit owner, dependency key, invalidation condition and
rebuild rule. A permanent player journal and deterministic replay inputs are different from sampled chart history or
disposable presentation caches. [Chapter 07](07-history-replay-and-archive.md) defines that retention split; it must
preserve the Director's permanent-history requirement.

## Modding is a content architecture

Installed resources separate definitions, initial history, reusable scripted effects and triggers, numeric defines,
localization and GUI declarations. Country history invokes shared starting effects; population history supplies
wealth and literacy setup separately. Native symbols include `CJominiScriptedEffectTemplateDatabase`,
`CJominiScriptedTriggerTemplateDatabase` and definition-registry initialization methods. These support parsed and
registered content, without proving the full loader's conflict behavior.

There are useful warnings in the shipped documentation.
[`script_values.md`](</home/user/.local/share/Steam/steamapps/common/Victoria
3/game/common/script_values/script_values.md>) says formulas are computed when evaluated and operations follow
authored order. [`scripted_guis.md`](</home/user/.local/share/Steam/steamapps/common/Victoria
3/game/common/scripted_guis/scripted_guis.md>) warns that visible tooltips re-evaluate frequently and recommends
preparing expensive lists elsewhere. [`_on_actions.md`](</home/user/.local/share/Steam/steamapps/common/Victoria
3/game/common/on_actions/_on_actions.md>) explains that duplicate trigger/effect blocks can conflict and recommends
composing named child actions. “Text-driven” does not automatically mean cheap or unambiguous.

Launcher configuration exposes loose-file and ZIP mod support. Its SQLite schema records dependencies, enabled mods
and playset positions. No installed mod bundle was available for a controlled conflict experiment. Exact dependency
resolution, replacement priority and native reload behavior remain unverified. The design in [chapter
03](03-bsl-bscn-and-modding.md) therefore specifies Babylon's own explicit rules rather than claiming to reproduce
Victoria's loader.

## Historical developer explanations and the resulting boundary

Paradox's 2022 modding diary describes Jomini-based scripting, mirrored content paths, metadata, localization and
coordinated history changes. Its 2023 performance diary describes task dependencies, safe simulation/UI handoffs,
deterministic ordering around parallel work, dirty modifier dependencies, grouped populations and special object
allocators. These historical explanations corroborate the separation visible in the installed artifacts; they are
not a benchmark of this installation. See [Dev Diary 60:
Modding](https://www.paradoxinteractive.com/games/victoria-3/news/victoria-3-dev-diary-60-modding) and [Dev Diary
76: Performance](https://www.paradoxinteractive.com/games/victoria-3/news/dev-diary-76-performance).

The architectural implication is concrete. Keep reusable content immutable. Keep the changing world compact and
typed. Compute affected results in memory. Publish bounded views for the UI. Store committed state, replay inputs
and worthwhile history deliberately. Neither category theory nor a new database makes those decisions automatically,
and Victoria 3's extensive simulation is not a scope requirement for Babylon's game.
