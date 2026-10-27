Architecture Boundary
=====================

``CONSTITUTION.md`` v4.3.0 governs the architecture. ``NORTH_STAR.md`` gives
the game direction and gate order. This page describes the current Rust
implementation and persistence boundary.

System Boundary
---------------

Babylon has these primary boundaries:

#. A pure Rust engine judges one four-week tick.
#. Live Rust BSL rules control causal changes and finite material kernels.
#. Recognizers and events remain deterministic.
#. Executable shocks remain absent. The bounded Wayne organizer resolves
   admitted player and independent policy practices through the BSL action phase.
#. ``babylon-persistence`` owns authoritative game-managed PostgreSQL schema,
   writes, restart, and durability.
#. Python builds reference data and supplies current repository and operator
   tools. The frozen simulation and its mutable SQLite runtime are retired.
#. Bevy offers observer campaigns and a restricted native organizer workspace.

One tick judges one fixed 28-day interval and produces one durable commit.
There are 13 periods in a modeled year; this is a 364-day simulation calendar,
not variable-length Gregorian months. Current Michigan campaigns bind the interval
in their canonical content. Their authored TOML defines the work schedule,
recipes, workforce, stocks, orders, throughput, route durations, and
an explicit campaign duration. The supplied campaign continues without a designed final
period; finite experiments retain explicit stopping periods. Opening resources
and commitments remain finite. The supplied work schedule yields 160 Designed
labor hours per person per period. Continuous campaigns capture standing
capacity supplies and current budgets instead of lifetime schedules.
Definitions normalize regional and statewide authoring into one current content model.
New captures that model, the generated graph scenario, observed source cells,
and observed definitions. Statewide capture also retains resolved physical
paths, selected edge geometry, terminal attachments, and network authority.
Open reconstructs those saved facts without consulting changed source files
or rerouting. Admission refuses older Michigan content and keeps its stored
data. Development has no save migration or compatibility compiler.
The interval contract is ``contracts/simulation_interval_v1.yaml``.

The current Michigan material campaign captures one BSL ``material/period``
rule. Its ``material-cycle`` body invokes the existing typed production,
freight, local transfers, merchant handling, and staffing transition at the
after-metabolism boundary. A material campaign requires exactly one invocation;
there is no unconditional native fallback. BSCN constructs the county,
business, sector and workforce graph from captured sources and declarations.
The existing TOML parameters supply the typed physical accounts. Rust keeps
the exact accounting and allocation algorithms. The authored rule, parameters
and scenario all participate in campaign identity and restart.
The runtime embeds the Michigan BSL and BSCN declaration fragment at build
time. New campaigns capture those shipped sources; reopening a campaign uses
its saved sources.
The built-in ``production.bsl`` annual labor calibration remains a conformance
reference; it does not parameterize this campaign. Observed annual QCEW facts
and source weekly wages keep their original units.

Standard and Delayed keep independent freight capacities. The two shared
freight presets route sheet metal and milled meal through one Designed regional
kilogram pool, with 800 or 160 kg per period. Panel freight stays independent.
Native good quantities keep exact gram coefficients. The compiler emits
one budget for each active capacity principal and period. A timed journey
reserves its distinct principals through a proportional base allocation and
canonical whole-unit residual allocation within each existing outbound pass.
Every allocation remains bounded by admitted demand, stock, funded labor and
all timed route capacities. After the residual phase, no unmet order can receive
another whole native unit within the remaining resources. Stable order identity
supplies a declared secondary priority. This does not prove optimal throughput
or fairness.
The regional service remains schematic. Statewide physical paths keep road
geometry separate from one-period travel and Designed capacity groups.
County terminal attachments do not identify factory locations.

The statewide roster admits source-supported commodity producers and physical
merchants. Processes at one owner share inventory and one workforce
pool. Source jobs and payroll remain context rather than modeled production
or labor. An added upstream process changes executable content without adding
another economic owner.

Merchants keep commodity identity while spending handling capacity and labor.

Handling receipts record an independent physical ceiling for each order
before shared competition and current handling labor. Summed handling need
describes prospective workload. It does not describe a simultaneous dispatch plan.
Zero base grants still face full labor coefficients during residual allocation.
ADR285 governs this Designed policy.

Routed arrivals precede outbound handling. County-local transfers
between owners debit the supplier and credit the buyer without a road stage,
transit lot, or physical-arrival receipt. The allocator fixes all outbound
grants before local credits, preventing recursive forwarding in the same close. Local
retail fulfillment completes finite end-buyer orders and creates no household
stock. It establishes neither consumption nor payment.

Authenticated Circuit readings derive stock movement, capacity reservations,
handling, and staffing from committed registers and receipts. They connect
shared-capacity competitors to output and workforce effects while preserving
the distinction between reservations, local transfers, and physical arrivals.
The roster and compiler do not certify a qualified statewide road graph or
the comparison's causal witnesses. ADR260 requires those checks and the
Director's comprehension session. Intervention identities and quantities
remain subject to that qualification.

Ordinary BSL rules derive and write world data through governed causal
operations. External shocks must not write downstream results directly.
AI may parse, retrieve, and narrate; it must not judge a game rule. The Python
``babylon doctor`` command checks whether the runtime database is reachable.
The corpus tools keep their declared sources and exclusion policy.

Live Rust Path
--------------

The shipping engine path is:

``babylon-kernel``
   Deterministic types and contracts.

``babylon-graph``
   Native relations, hyperedges, and canonical hashes.

``babylon-bsl``
   The BSL lexer, parser, checker, typed finite-kernel analysis, exact
   forecasting, loader, and evaluator.

``babylon-tick``
   The four-week tick, replay identity, material state, and atomic publication.

``babylon-material-circuit``
   Physical production, routed freight, local transfers, merchant handling,
   finite final fulfillment, conserved staffing, and funded monetary accounts.

``babylon-persistence``
   Rust-owned PostgreSQL activation, campaign foundation, checkpoint restart,
   typed semantic rows, commit markers, and Archive dirty receipts.

``babylon-client``
   The Bevy administrative viewer.

Each four-week tick runs on detached state and buffers its events. The tick becomes
observable only after all rule, hash, and persistence boundaries succeed.
``GraphStateHash`` identifies graph bytes only. ``NominalWorldHash`` also binds
completed time, allocator cursors, and the governed phase-schedule digest.
``TickContentHash`` binds the identified replay result.
``ReplayTickSession`` publishes ``TickContentHash`` atomically. Replay
identity and campaign durability identity are separate typed inputs.

A finite kernel distributes exact ``Mass`` over one enum-ordered family of
bounded material effect bundles. It consumes one replay-keyed integer ticket
draw and applies only the selected bundle. The choice produces a separate
``ChoiceReceipt`` even when the selected bundle changes no material state.
Deterministic mechanics are the one-outcome case. Events own no authored
probability. The language assumes no independence between choices.

Authoritative Persistence
-------------------------

``babylon-runtime`` is the production composition root. It verifies the current
schema and serves the observer through ``DurableMaterialRuntime``. That runtime
accepts one captured economic foundation, judges one period, and commits graph
and material evidence together. Callers cannot submit a pre-judged report.

The current source envelope pins exact artifact bytes, rules, policy and compiler
identity. It regenerates one shared opening for native graph admission and the
initial material register. Authored Michigan controls use an explicit importer.
National county sources use the same compiler and replay session.

The foundation stores one complete initial material register alongside the
captured graph and source components. Postgres does not store a second full
foundation containing those same components. Runtime and full observer reads
share reconstruction, authenticate canonical framing before regeneration and
must reproduce the expected regenerated digest. Known preview cannot read the
component view.
External binary captures keep their exact framing and canonical decode checks.

The national opening has passed complete capture and decode. A national period
advance and playable campaign need separate qualification.

Save growth is a separate national qualification criterion. Measure each material
collection and receipt family, then Postgres database and relation growth after
actual committed periods, including TOAST and indexes. Report uncompressed
canonical bytes separately from physical storage, compression and WAL generation.
Separate one-time captured sources from recurring restart state and history.
Avoid counting TOAST twice.

Annual projections state their period count: thirteen
28-day periods form the 52-week model year, while twelve ticks are a separate
comparison. Changing row counts and limited observations qualify any projection.

Before final playable-build qualification, remove avoidable repeated invariant
content or identities supported by that census. Any lossless storage encoding
must check decoded canonical hashes. A changed canonical format needs its
explicit ceremony. Keep complete county coverage, exact accounting, atomic
publication, restart, replay and recovery. Measure row churn and expected savings
before recommending lookup, periodic checkpoint, delta or separate history
changes. Typed lookup tables are the selected representation for shared identities
and definitions. Store each lookup entry once and use compact references in
recurring rows. The engine can cache those tables in memory. Lookup references
must preserve identity kinds and reconstruct the exact canonical bytes; table
names alone do not establish a reduction in disk usage.

Current material storage uses opening-based section deltas and a shared typed
lookup for state and receipts. Runtime and full observer reconstruct and validate
the complete canonical bytes. Its first actual commit retained 336,437,248 bytes
with exact cold recovery, so it still fails the storage ceiling. Graph names and
types now use campaign-owned SQL lookups; period membership and binary64 values
use bounded parallel arrays behind the same logical reader views. Opening
identities are stored once. Its first actual graph-packed commit retained
212,729,856 bytes. Event names and native keys now use SQL lookups; event fields
use bounded typed arrays behind the same logical views. Its first actual commit
retained 86,343,680 bytes with exact cold recovery and complete county coverage.
The opening added 263,184,384 bytes. Newly introduced event keys added 15,220,736
bytes and are fully charged. Parallel event expansion and nine authenticated
checkpoint source references reduce actual growth to 65,708,032 bytes. Only
world registers remain inline; graph, semantic and six captured sections reuse
their existing admitted sources. The complete original checkpoint manifest and
envelope still authenticate reconstructed canonical bytes. Checkpoint growth is
16,384 bytes, compared with the previous 20,652,032-byte copies.
Outer advance and cold-recovery observations were 95.13 and 137.64 seconds,
compared with 208.25 and 251.82 before this repair. Those timers included subsequent
parity checks, so they do not isolate committed advance or open latency. Storage
still fails its target; these observations are not long-run qualification.
These measurements precede the material lookup ownership change below.

A subsequent run shares Node event scopes and names through the existing graph
string lookup. It retains 50,495,488 bytes for one committed period and charges
263,258,112 bytes for the opening. All 3,144 counties, canonical material and
receipt hashes, the tick content hash and world hash match the previous run.
Cold recovery passes. Outer advance and recovery observations were 95.40 and
140.22 seconds, including parity checks. This result still fails the provisional
storage budget. Thirteen times its measured charge is 656,441,344 bytes; that
is a single-period extrapolation, not a measured year.

ADR274 gives each material period the immutable opening seed plus its own
state and receipt identities. Pending and in-transit identities repeat
where needed; retired identities do not accumulate in the runtime lookup.
Consecutive lookup chunks bind to the unchanged tail state
anchor. Both codecs retain full canonical admission and exact hashes. Valid
receipts from another period refuse before state staging. Native recovery still
scans historical lookup bytes, and staging still rebuilds local maps.
One subsequent national period retained 50,487,296 bytes and charged 263,258,112
bytes for the opening. Canonical state, receipts, tick content and world hashes
match the preceding run, with all 3,144 counties and exact cold recovery. Advance
and recovery outer observations were 64.57 and 135.97 seconds, including parity
checks. Thirteen times this charge
is 656,334,848 bytes; this remains a single-period extrapolation. The storage and
long-run performance qualifications remain open. Historical corruption controls and long-run native
qualification remain separate from this successful opening, advance and reopen.

ADR276 replaces literal period additions with current V3 lookup descriptors.
The encoder selects an opening-row recipe only when it reproduces the same typed
identity. Unmatched identities stay literal. The decoded ordered table, logical
hash and chain stay the same. The reader checks separate descriptor lengths,
hashes and grammar limits before decompression.

State storage remains V2. The reader refuses unsupported old lookup framing.
SQL relations and the canonical engine format stay the same.

The October 3 current run charges 35,069,952 bytes for one period and 263,135,232
bytes for the opening. It covers all 3,144 counties and passes native cold
recovery. The advance takes 64.617 seconds and cold open takes 112.108 seconds.
These timers stop before parity checks.

Lookup storage occupies 1,190,192 bytes. State and complete receipts occupy
5,892,522 and 19,051,336 bytes. The complete retained charge still exceeds
the 23,000,000-byte optimization target and fits the approved 40,000,000-byte
development ceiling. Multiplying this charge by thirteen gives 455,909,376 bytes,
excluding opening. This single-period projection proves neither annual growth
nor p95 performance. The economic control does not prove organizer play or
enjoyment.

ADR278 records the Director's clarified priority: reduce the complete save's
disk use. Postgres remains the default for living state and history. Parquet
needs a measured reduction in total retained bytes that justifies its complexity.
The earlier ADR277 archive proposal is optional.

Age alone does not make a record ready for archiving. An unpaid wage, pending
shipment or consent remains live until resolved. Keep causal memory and trends
needed by future decisions. Append sealed immutable files for any export instead
of rewriting one growing file. DuckDB and Arrow need a concrete consumer.

Full archive implementation remains deferred. A native admitted checkpoint must
first remove recovery's dependence on the old history prefix. Direct cold queries,
exact restoration, interrupted publication and actual disk reclamation need
separate proof. Charge archives, retained identity tables and live checkpoints
together. Arrow batches or a different container format alone do not prove
savings.

The Director approved the longer-term Designed total-save target of
10,000,000,000 bytes at twenty-five model years, or 325 periods. This target
does not limit campaign duration. The ordinary 52-period development check and
the actual 325-period save check remain separate. Projections cannot qualify the
longer check.

Count the allocated opening database, including its schema, plus
charged period and restart growth. External storage needs separate accounting.
Report cluster overhead, WAL and temporary peaks separately.

ADR279 repairs measured territory duplication. It stores each exact identity
and ordered typed field set once, then records integer period membership.
Current SQL views expand those references for county and historical readers.
Digest buckets narrow candidates. Complete canonical bytes prove equality.

Opening definitions count toward opening storage. Changed fields create new
immutable definitions. Metadata, marker guards and canonical reconstruction
protect completeness and temporal validity. This representation changes no
engine quantities or hashes.

ADR283 shares exact ordered graph memberships across periods and attribute
chunks. A hash index finds candidate matches. Comparing complete arrays decides
identity.

References bind a campaign and committed origin. Dense IDs and fixed definitions
protect historical reconstruction and concurrent retry. Local Postgres controls
pass. National storage and timing measurements remain pending.

The preceding smoke006 completed both committed periods, authenticated
Archive publication, complete production evidence, independent accounting and
exact restart recovery. It failed qualification: final native elapsed time was
941.64 seconds against the 900-second limit. Charged retained growth was
42,188,800 and 32,129,024 bytes. The first period exceeded the 40 MB ceiling.
Neither restart added retained growth. Advances took 66.05 and 61.17 seconds.

The opening allocated database was 284,808,883 bytes. The two-period average
projects 12,361,455,283 bytes after 325 periods, above the 10 GB limit. This is
not an actual long-save qualification. Peak sampled native memory was
10,177,679,360 bytes, with 15,429,632 bytes of swap. Postgres memory was outside
that sample. The failed smoke and its exact source and policy remain preserved
under current-national-playable-smoke006.

A later compatible lazy Archive repair reopened the same period-two
campaign in 108.15 seconds. It refreshed settled Archive progress in 4.03 seconds
and completed Stop in 0.38 seconds. Original material, commit and consumption
identities stayed unchanged. This separate runtime process peaked at
6,972,039,168 memory bytes without swap. It does not replace the failed smoke
or qualify a fresh run.

Storage uses independently authenticated lossless frames with canonical hashes
over decoded bytes. A current-save screen restored every tested frame exactly.
Compared with level three, the Designed ``zstd`` level-nine setting reduced
fixed-mode payloads by 800,907 and 1,043,420 bytes. Compression required 0.83 and
0.90 seconds more. These component measurements do not prove complete
Postgres savings or committed advance timing.

An exact provenance experiment reconstructed all copied atom, grant and page
rows. Their combined storage fell from 12,320,768 to 8,658,944 bytes with indexes,
TOAST and lookup overhead. This measurement covers the whole two-period corpus.

ADR284 records private citation storage. Original strings define semantic
identities. Frozen page references stay independent of later authoritative
grants. Twenty-three local Postgres controls pass, including exact lookup
reuse, corruption refusal, publication rollback, historical reads and confined
consumers. Integrated national growth and timing still need qualification.

Earlier failed fixtures keep their source records and independently verified
backups. The smoke006 backup matched all 65 tables and sequence state. The matching
preserved engine reopened the inactive restored copy in 108.46 seconds,
refreshed Archive in 4.10 seconds and stopped in 0.41 seconds. Original state
and its ownership lease remained unchanged. We retired that exact container
and volume before opening smoke007 as the sole active national test fixture.

Smoke007 committed period one. Archive published 2,816 pages before the
180-second response deadline expired. Its consumption marker remains absent.
The failed run and source records remain preserved. This incomplete boundary
does not prove retained growth, a completed smoke or native play acceptance.

An independent restore matched all 67 tables and sequence state. Its preserved
engine reopened the partial campaign in 89.27 seconds and completed remaining
Archive work in 50.84 seconds. All 3,144 county subjects were present and the
consumption marker matched the committed tick. Material and commit components
remained unchanged. The worker left the original failed database unchanged. This partial
backlog recovery does not replace a fresh smoke qualification.

Frozen page citations now resolve through an ordered read of existing campaign
definitions. Four local Postgres controls passed, covering exact references,
missing and foreign citations, publication rollback and historical receipt
identity. National timing measurements remain pending.

The focused resolver control also refused a duplicate definition combined with
a missing citation. It completed in 20.89 seconds, excluding compilation.

A catalog query screen preserved all 154 rows and digests. The revised query
shares normalized routine privileges and materializes a complete dependency
join. Execution fell from about 1.94 to 1.33 seconds across three samples of
each query.

Fresh authentication and collection bounds remain required. Live admission
passed for all four role configurations. Changed extension privileges and
dependencies caused admission refusal. This query measurement and these
controls do not prove successful Archive catch-up.

We preserved both partial and completed smoke007 backups. Independent restores
matched all 67 tables and sequence state. Exact ownership checks then retired
its container and volume. Smoke008 is the sole retained national test fixture.

Smoke008 completed both committed periods, authenticated Archive publication,
complete production evidence, independent accounting and exact restart recovery.
It failed qualification: elapsed time was 972.20 seconds against the 900-second
limit. Remote aid dispatched no goods and refunded all reserved cash. Local aid
delivered four units and enabled an independently authorized practice. The
positive aid check remains incomplete. Native play has not run.

An exact detached first-period replay reproduced the original register, receipt
and world identities. The planned 56 kg remote shipment had enough donor goods and time.
Its final proportional corridor share floored to zero native units, while that
corridor retained 2,776,077 kg after actual dispatches. Each inspected route
resource had enough capacity for that shipment. The old no-redistribution policy
caused this artifact. Small controls for its replacement do not prove national
aid delivery.

Charged retained growth was 37,707,776 and 29,401,088 bytes, below the 40 MB
development ceiling but above the 23 MB target. Neither restart added retained
growth.

Advances took 69.28 and 63.54 seconds. Archive completed in 177.39 and
99.42 seconds. Complete production reads took 120.11 and 120.80 seconds.
Cold reopens took 85.22 and 105.45 seconds. These individual phase results do
not pass the complete smoke or prove a 52-sample timing distribution.

The opening allocated database was 284,456,627 bytes. The two-period average
projects 11,189,647,027 bytes after 325 periods, above the 10 GB limit. This is
not an actual long-save qualification. Native memory peaked at 10,166,202,368
bytes without observed swap. Postgres memory was outside that measurement.
The failed smoke, source, policy and corrected sampling metadata remain
preserved under current-national-playable-smoke008.

The 52-period, actual 325-period and native play qualifications remain incomplete.

A later cold complete production read preserved the original evidence
digest and its 809,432,538-byte body. It took 145.18 seconds and peaked at
6,067,683,328 bytes without observed swap. The preceding read took 147.17 seconds
and peaked at 6,024,806,400 bytes. These measurements show no material improvement.

The native probe passed its identity checks. Its diagnostic launcher then
mishandled a successful exit, so the wrapper result failed. Both records and an
explicit closure remain preserved.

The reader also held a read transaction during
reconstruction, with sampled age reaching 131.02 seconds. This remains separate
from the short Archive publication controls.

Graph component views resolve nodes, names and types through exact lookup IDs.
Separate dependent lookup queries prevent stale statistics from multiplying whole
campaign lookup tables before matching those IDs. Marker checks, permissions
and canonical component authentication remain required.

A regression holds
prior campaign statistics while adding a new campaign. The original node read
timed out at five seconds. The revised views returned all 1,696 nodes in 26 ms
and all 8,800 binary64 attributes in 60 ms, matching the live graph exactly.
The control took 30.04 seconds. This scoped result does not prove national
timing, memory, storage or play qualification.

Persistence uses the pinned ``mimalloc`` heap allocator for its Rust consumers,
including the runtime, client and qualification processes. In a separate
authenticated cold read, releasing the reader and observation reduced remaining
memory from 3,312,087,040 to 1,500,897,280 bytes. Peak memory remained
5,199,081,472 bytes. This allocator reduces retained heap memory. Postgres
growth and live reconstruction size still need independent measurement.
The isolated read does not qualify national advances or sustained play.

ADR280 records the Director's definitive provisional development benchmarks.
Defer marginal storage redesign when measured development limits allow play.
The 23 MB storage target remains an optimization target.
The earlier 10 MB ambition is not an acceptance gate.

* Focused economic and game play controls: under sixty seconds, excluding compilation.
* National committed advance: aim for sixty to ninety seconds. The p95 limit is 120 seconds.
* Cold load: under 180 seconds, with visible progress.
* National smoke check: two periods and recovery within 900 seconds.
* Full 52-period qualification: preferably under four hours, including recovery.


The four-hour preference cannot truncate required proof. One advance cannot
prove p95.

Immediately acknowledge processing and keep the last committed
map, reports, relationships and notes navigable. Show actual stages and elapsed
time. Percentages need measurable completion. Link consequential changes to
player commitments and let players skip lengthy narration or animation.
Qualify these behaviors through actual play.

The session protocol reports actual stage starts: preparing commitments,
resolving the economy, preparing storage and saving the period. Each report
identifies its ``request_id``, lifecycle scope and next period. The client checks their
order and changes only presentation. Stage changes preserve elapsed time and
the committed observation. Only the commit acknowledgement advances the
durable period. If the progress pipe fails, reopen to reconcile a possible commit.

Native aid replies encode money as canonical decimal strings and decode it as
exact signed 128-bit integers. Numeric tokens and malformed or overflowing
strings refuse. Canonical engine receipts keep their existing encoding.

The optional national playable qualification uses the same session path for
campaign admission, aid commitments, advances and recovery. It verifies actual
committed receipt families through ``ObserverEconomyReader`` with a separate
full-observer credential. The reader authenticates the foundation, complete
history, current and previous envelopes, and committed identity before exposing
receipts and the closing period's household contribution debits. Preview readers
have no authority to read them. Ordinary snapshots do not copy these vectors.

Full observers authenticate organizer actions from the disclosed committed
intents. The reader admits the command against the authenticated prior state
and matches its commitment identity to the closing receipt. It then reconstructs
the entire ordered batch, including standing work, delayed aid and independent
responses, and compares exact bytes and digest. Runtime recovery also checks
consumption against the private command ledger. Restricted previews keep
their existing boundary.

The national Postgres runner preserves source, input and evidence manifests.
Its default success disposition removes the exact disposable container and volume.
The ``retain-for-native`` option preserves a successful playable
fixture and its lease, recording the original scope, terminal markers and evidence
hashes. Smoke success cannot claim full qualification. An existing-campaign
native Open rechecks ownership, retained evidence, combined source and both
executable hashes before launching the existing runtime/client pair. It holds the
same supervisor lock through native exit and never provisions another game.
A shared lease in the Git common directory prevents concurrent national games
across worktrees. Retained legacy leases also block admission.
Its exclusive lock uses a separate ``flock --close`` supervisor so worker
descendants cannot keep the lock after the runner exits. Failed runs retain an
atomic summary and immutable progress records. The collector is maintained under
``tools/devtools`` and the runner pins ``PostgreSQL`` build and configuration sources.

Playable evidence version five binds independent aid, trade, and economic
accounting to the same authenticated complete observation. Derived trade totals reconcile
original procurement terms, delivery, realization and matched settlement.
The audit keeps only unresolved order terms. Full national and long-save
checks test for settled trade in both directions and actual foreign production.
The shorter smoke preserves incomplete transit evidence.

Full national and long-save admission also requires recurrence within the
captured terminal window, whose Designed default is thirteen periods. Paid
purchases, consumption, funded wages, and procurement settlements each need
more than one positive period. Their timing can differ.

A separate bounded
custody witness follows production through paid delivery and retail handoff to
consumption. It starts from the authenticated register before that window and
subtracts opening stocks, transit, aid, and unproven supply. Standing pantry
buffers do not erase renewal, and sales of initial supplier stocks do not prove
it. The shorter smoke records this witness without claiming sustained renewal.

The national development storage benchmark has a Designed ceiling of
40,000,000 bytes per committed tick, recorded in
``contracts/national_storage_qualification_v5.json``. It reports the separate
23,000,000-byte optimization target and the longer-term total-save result.
Count all retained campaign relations and indexes, including receipts, graph
history and checkpoint growth.
Charge new shared objects and dictionaries to
their creation tick.

The allocation charge sums positive growth of ordinary parent relations and
positive database growth outside those relations. Subtract signed parent deltas
from the database delta to identify that remaining growth. Charge commit and
recovery intervals separately. Shrinking another relation cannot conceal a
growing history or unlisted allocation. Parent totals already include their
TOAST heap and indexes.

Policy version five records this measurement contract and separate material
register and production-evidence byte budgets.
Retained earlier results keep their captured policy and evaluator.

ADR273 preserves the earlier interim decision. ADR280 owns current development
readiness. The earlier 10 MB goal remains
a future optimization goal. The measured 22.57 MB shared-compression prototype
counts only material payloads. It does not prove total retained growth.

One active disposable national test campaign rotates between qualification runs
after preserving unique evidence. Old saves and unrelated sessions remain protected.

Thirteen periods have a 520 decimal MB development ceiling per model year.
The 52-period ceiling is 2,080 MB, plus opening. These Designed allowances do not
measure sustained growth. Full county coverage and exact accounting, causal
integrity, atomicity, replay and recovery remain required.

A short run cannot qualify the 52-period horizon.

Use one isolated measurement database and actual marker-last runtime commits.
Keep the complete history and check the county roster, canonical evidence and
world hashes after restart. Record opening cost separately, with WAL generation,
temporary disk, memory, restart and recovery evidence alongside the storage
ceiling. Current development can replace the Postgres representation without
compatibility layers. Preserve incompatible saves as data and refuse their formats.


Production, freight, merchant handling, local transfers, retail fulfillment,
and staffing share one material state. Production updates that state's fields
through the common checked inventory operations. Staffing binds production or
merchant work to a conserved pool. ``ProductionEvidenceDigest`` binds the
complete authorized projection, sorting unordered rows while preserving event,
geometry, and physical path order.

Supplier relationships reference a shared ``PhysicalRouteDefinition`` by its
captured route identity. Each relationship retains its parties, commodity,
units and quantities. The definition holds travel time, ordered stages,
capacity memberships and available geometry once. ``PhysicalRouteIndex``
checks every definition and reference before borrowing the shared paths for
display. Invalid definitions remain distinguishable from an empty route list.

Version 16 presentation evidence binds both collections. Material save and
receipt formats keep their existing identities.

The complete presentation body streams into the hash with a Designed ceiling
of 1,000,000,000 bytes. Projected memory and retained database growth
have their own measurements and budgets.

The material state explicitly selects a physical accounting control or monetary
accounts. Both use the same allocator. Monetary orders must name funded escrow.
Dispatch holds that money until actual arrival or local handoff.
Physical loss refunds the buyer.

Employers fund attendance before work. Wage
obligations and payment remain separate receipts, while later labor receipts
distinguish used, paid idle, unfunded, and unplanned hours. The detached close checks cash
plus reserves before it can publish. Canonical state captures pending orders
and earned unpaid wages for restart.

Captured recurring policies connect household stocks and needs, affordable
purchases, consumption and unmet needs to that same material close. Funded
orders keep their accepted price. Handoffs credit resident stocks before
consumption. Unfilled recurring retail requests expire and refund their reserve.
Resolved orders retire together with their escrow. Receipts preserve their
admission, fulfillment and expiry for later inspection.

Merchant and resident accounts carry a checked ``EconomicLocation``: a domestic
county, one of twelve foreign counterparts, or an explicit US dependency.
Distinct household cohorts may share a location and retain separate stocks and
cash. Retail handoffs require matching locations. Goods crossing locations must
reach the receiving merchant through the captured delivery circuit. The current
state preserves those identities in six canonical bytes and refuses older formats.
County projections select domestic locations explicitly; foreign markets never
acquire invented county identifiers. The shared paid controls exercise these
namespaces; nationwide campaign admission remains a separate integration step.

Each recurring need declares a person or household basis and an exact positive
coefficient. Goods admission, pantry consumption, service admission and service
satisfaction use that same requirement. This permits housing to depend on homes
while food depends on residents. Neither calculation changes either population
count. Captured controls explicitly retain their person-based requirements.

Procurement accounts for inventory and outstanding inbound orders, including
goods in transit once. Later production and attendance plans respond to
sales, funded unfilled requests and closing stock. Offers can change their next
quote through a captured bounded inventory policy. A second outbound pass
dispatches newly funded firm orders through the remaining shared resources.
Local firm credits occur after both passes, so they cannot feed another dispatch
in the same close. The eight-period fixed-price control exercises this loop.

The observer authenticates admissions, settlement and retirement between
adjacent material states. It reports household stocks, consumption and unmet
needs separately from retail handoffs. Order drill-down keeps active and
latest-period rows with explicit cumulative totals. Campaign comparisons use
stable resident and retailer identities as generated order identities change.

Household stock accounts keep ordinary purchases, received support and dispatched
support separate. Routed gifts arrive before that period's demand admission.
Local gifts transfer after admission and before consumption. Gift cash settles
through its own reserve.

Gift shipments reserve the same dated route capacity
as commercial freight. Full-observer receipts join these movements to the
closing accounts. The current presentation evidence hash covers the support
flows and their capacity reservations.

Resident goods and service disclosures include the captured
``ProductionHouseholdKind``. An ``Ordinary`` cohort must have more than zero
households. Its person count must equal or exceed its household count.
A ``CollectiveResidence`` cohort must have more than zero persons and zero
ordinary households. Version 16 presentation evidence includes this
classification and checks consumption and stock accounts.

The current Michigan campaign still selects the physical control. National
content, rolling budgets, investment and the playable household and solidarity
connections remain separate acceptance work. ADR263 records the approved
direction and distinguishes its requirements from verified implementation.

Practice has one typed contract for actors, stable targets, authority, intents,
resource quotes, resolved batches, and ordered actions. The evidence driver
uses that contract directly. Seeded replay and sealed carrier keys govern BSL
and tick execution. Scenario and rule diagnostics use an explicit deterministic
identity and the production collect-and-apply adjudicator.

Fresh initialization constructs the complete current schema in one transaction,
under the advisory lock. Its schema identity is the final initialization write.
Admission verifies the exact schema, ownership, and permitted role grants.
Reference-data installation and reader-role provisioning have separate duties.
Both use the current schema. The runtime refuses incompatible databases before
mutation and preserves their data.

.. Vale: these paragraphs preserve literal persistence and schema identifiers.
.. vale ste.UnapprovedWords = NO
.. vale ste.NounClusters = NO

The runtime owns three schemas:

``babylon_ref``
   Immutable geography, H3 cohorts, and exact reference artifacts.

``babylon_state``
   Campaign foundation, typed graph and material rows, events, checkpoints,
   ``tick_event_v2`` and ``tick_event_field_v2``,
   ``tick_choice_receipt_v1`` with ``tick_choice_receipt_branch_v1`` and
   ``tick_choice_receipt_carrier_element_v1`` children, the commit marker
   ``tick_commit``, and
   ``archive_dirty_receipt_v1``.

``babylon_meta``
   The authority ledger plus typed campaign and navigation metadata.

One marker-last transaction writes the complete typed tick estate. It writes
choice receipts and choice-linked event metadata before a required full
checkpoint and one Archive dirty receipt. It then writes the commit marker.

The runtime acknowledges the tick only after ``COMMIT`` or exact
ambiguous-commit reconciliation. Retry and restart must reproduce the same
material envelope bytes. Material campaign markers record
``envelope_layout_version = 3``; material readers require that layout.

.. vale ste.NounClusters = YES
.. vale ste.UnapprovedWords = YES

Restart reconstructs the captured foundation and loads the latest complete
material checkpoint bound to the committed tail. A delta checkpoint is never a restore root.
Missing, duplicate, out-of-order, or digest-mismatched sections refuse before
the runtime resumes.

Geographic Reader Boundary
--------------------------

Captured national geography identifies all 3,144 domestic counties. Foreign
counterparts and dependencies have separate typed locations. Optional H3 and
place detail must name a supplied, checked local capture. National county
coverage does not imply fine geometry. The database keeps the complete campaign
reference digest separate from the optional local H3 reference key.

Rust reads those typed relations directly. Python has no game-state reader or
compatibility projection. The consuming Rust paths check reference transport,
hierarchy, ordering, and current restricted readers. Archive startup uses the
captured county roster and registers place producers and their public grants
only where captured detail exists. Sweeps reuse producer context. Missing local
detail remains unavailable.

Future H3 storage work must trace reference admission, county and place joins,
historical reads and restricted observer queries. Current cell IDs use
``bigint``, which already occupies eight bytes. Resolution and parent cells can
be derived from an H3 ID, but removing stored columns must preserve their
consumers. Cell-set compaction does not encode arbitrary per-cell economic
quantities. Measure populated captures and query plans before changing
extensions or indexes. The retained national run showed no H3-related period
growth, so this work is not a current storage priority.

Reference Data and Operator Tools
---------------------------------

PER-48 is decided. The one-way cutover is complete. Rust owns authoritative
game-managed Postgres. Python continues only in the roles declared below.

The retired Python simulation is available at ``p27-python-freeze``. BSL
citations read that tag; Rust owns the executable schedule, mechanics, replay
and persistence contracts. Python builds reference artifacts and supports
current repository and operator commands. Those tools do not adjudicate ticks
or read authoritative transition rows.

Client and Archive Boundary
---------------------------

The Bevy client offers administrative observer campaigns and **Organize in
Wayne**, a restricted player campaign. The organizer workspace submits typed
rulings and displays durable acknowledgement before calling them submitted.
Each next 28-day tick resolves accepted work or the saved standing routine.
Draft notes and selection are separate presentation state and cannot execute.

The captured Designed collective, workplace committee and neighborhood group
have independent authority and participant time commitments. Inquiry costs
12 of the collective's 16 hours. Contact work costs 8. A participating partner
uses 2 of its own 8 hours. The shared allocator prevents contributors from
supplying the same hours twice. Unused hours expire.

Factory conditions continue to follow the maintenance economy under every
political choice. The model does not calculate shift schedules or wage losses.

A contact product completed in period T can renew its report-sharing
agreement for T+1 and T+2. The following period's reducer must consume its
receipt first.

Inquiry attempts to get a specific workplace report. Committed expenditure
does not guarantee disclosure. An acquired report retains observed and acquired
periods, source, and receipt. It grants no permanent access to future values
or provider-private accounts.

Circuit and held history in this campaign use
those earned observations. Historical inspection cannot admit past actions.
The scoped successor is ADR262 and ``contracts/organizer_practice_v1.yaml``.

In observer campaigns, World opens with the complete disclosed economy as a
schematic network over level county geography. All admitted owner cohorts remain
visible, including isolated cohorts. Commodity links preserve supplier and buyer
identities; county-local
transfers and finite retail orders connect merchants to end buyers. Display
offsets separate aggregate owners without claiming factory locations.
Selecting a node highlights its direct links while retaining the wider network.
Industry filters retain the selected industry and its direct trading neighbors.

Modeled employed people, modeled reserve, and observed QCEW have separate
height lenses. Physical lenses need a specific good and
unit. They do not add unlike goods into an output total. Workforce totals
count each pool once.

A county selection leads to paged owner cohorts, then
Circuit detail with at most six incident relationship groups per page.
Shared-capacity competitors have their own navigation rather than appearing
as suppliers. Physical road layers reuse captured geometry and remain separate
from the schematic economy network. Both read the authenticated observation;
neither introduces a supplier graph or allocation engine of its own.

The Readings panel retains subject, period, output or handling, and workforce
context above its Flow, Freight, Work, and Sources sections. Foundation
accounts, unavailable evidence, and completed zero values remain distinct.
Comparison reads the same committed period in saved campaigns. It does not
advance either world. Restricted knowledge previews contain no material
projection or production-evidence digest.

The Wayne maintenance family adds one provider and one consumer binding to
the typed material state. Current service limits consumer batches. Whole
jobs use spare parts and current labor, then enable batches for the following
period. Unused service expires.

Prospective material and nameplate capacity set work requests before
service or employment limits production. An idle workplace can ask for work
and recover. The existing BSL material cycle,
staffing, captured content, and atomic commit own these effects. Circuit
readings distinguish service from parts deliveries and show its completion,
expiry, and next-period output ceiling. These are administrative accounts.

Organizer inquiries can earn only the bounded workplace record projection.
Provider-private maintenance accounts remain unavailable to the player.

Each committed tick emits an Archive dirty receipt. The Rust Archive worker
binds each receipt to an exact dirty batch, worker contract, and pinned
knowledge-grant snapshot. It publishes immutable county, place, workplace
and organizational report dossiers
with validated content and known citations. The scoped reader admits the
requested committed period, retained publication, and disclosed links together.
Global Archive progress cannot certify a selected page.

The campaign publication lock spans capture, computation and publication.
The worker captures the exact committed receipt and frozen knowledge in a
short transaction, then closes that transaction before producer work. The
organizer producer also captures its complete historical inputs before detached
admission and rendering. Publication checks receipt and knowledge again, then
commits each page batch with its pin. The final batch writes the consumption
marker last in that transaction. Cancellation or changed inputs cannot leave
a newly prepared pin without its published batch.

ADR281 stores frozen membership as authenticated complete bases and exact
additions. The ``Designed`` default uses thirteen-period segments. Reconstruction
checks the base, every intervening addition set, and the requested complete
set against their original counts and hashes.

Actual admission periods govern membership. Late backdated grants cannot change
earlier disclosure. New bases or additions commit atomically with publication.
Admission refuses the earlier physical schema. Operators preserve incompatible
games as evidence.

The runtime owns one Archive listener and worker. Empty Postgres notifications
signal committed tick markers and campaign creation. The listener registers
before reading durable work at startup and after reconnect. It drains retained
work through the existing worker. An idle notification timeout performs no
maintenance query. Notifications carry no world state or player intent.
The ordered worker decides whether to produce before the driver admits the
captured catalog producer. A settled sweep does not hydrate it. The driver
reuses successful admission and checks cancellation before and after admission.
Publication keeps its existing receipt and knowledge authentication.

One coordinator owns the session control pipe and tick acknowledgements.
It flushes ``Committed`` before handling the resulting Archive progress. Bevy accepts
progress only for its acknowledged campaign and durable period, then refreshes
its scoped read. It does not poll for Archive maintenance.

Shutdown requests cooperative cancellation and observes actual worker
completion. A database connection that stays open beyond the existing process
deadline cannot claim successful shutdown.

ADR254 records this scheduling boundary. Organizer admission persists before
acknowledgement, and the existing resolving transaction writes action knowledge,
contact products, receipts and Archive dirty records before its durable marker.
Failed ticks preserve accepted commitments for retry. Checkpoint reconstruction
verifies derived organizer rows against the complete authoritative register.
Broader player-agency and organizational-struggle acceptance remains open.

Event payloads contain observed or derived material facts, never probability.
Committed event metadata records the emitting rule and can carry an
automatically derived reference to the ``ChoiceReceipt`` that a finite
projection observed. Removing an event sink cannot change a material
trajectory.

Flow
----

This flow shows the current Michigan material campaign. Solid arrows are live.
Dashed arrows are later gate work.

.. Vale: the Mermaid block contains literal crate and schema identifiers.
.. vale off

.. mermaid::

   flowchart LR
       REF["babylon_ref"] --> TICK["Rust material tick"]
       DEFINES["Saved authored parameters"] --> TICK
       BSL["Saved BSL material-cycle invocation"] --> TICK
       MATERIAL["Production, circulation, staffing"] --> TICK
       EMPTY["Exact empty action batch"] --> TICK
       TICK --> IDENTIFIED["IdentifiedMaterialTick"]
       IDENTIFIED --> RUNTIME["DurableMaterialRuntime"]
       RUNTIME --> STATE["babylon_state typed rows"]
       STATE --> RECEIPT["ChoiceReceipt rows"]
       STATE --> MARKER["tick_commit"]
       STATE --> DIRTY["archive_dirty_receipt_v1"]
       MARKER --> VIEW["Bevy administrative viewer"]
       PY["Reference builders"] --> DATA["SQLite and Parquet artifacts"]
       DATA --> REF
       DIRTY --> ARCHIVE["Semantic Archive worker"]
       ARCHIVE -.-> CHOICE["Player decision"]

.. vale on

Invariants
----------

Tick identity
   Equal inputs produce equal graph, nominal-world, replay-tick, envelope, and
   typed semantic row bytes. Equal kernel instances produce equal allocation,
   draw, selection, and receipt bytes. Only the marker establishes durability.

Pure judgment
   Relation, BSL, and tick crates have no database dependency. Storage begins
   only after detached judgment succeeds.

Single authority
   No compatibility view, adapter, fallback, dual writer, dual storage, or
   runnable midpoint exists.

Native topology
   Hyperedges remain first-class public elements. Incidence data is an internal
   storage method.

Source honesty
   Each substantive value is ``Observed``, ``Derived``, ``Calibrated``, or
   ``Designed``.

Finite contingency
   Kernels select bounded material effects. Recognizers deterministically
   observe post-state. Exact event likelihood sums the branches that make the
   recognizer emit that event. Events never own probability.

Player relevance
   An administrative display cannot pass a game milestone. The persistence
   cutover is necessary infrastructure, not the playable decision loop.

Related Pages
-------------

- :doc:`/reference/persistence`
- :doc:`/concepts/persistence-architecture`
- :doc:`/concepts/topology`
- :doc:`/reference/bsl-language`
