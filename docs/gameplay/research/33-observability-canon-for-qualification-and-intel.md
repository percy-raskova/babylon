# 33 — The instrument and the alibi: observability canon as qualification contract, intel loop, and reckoning

Read-only web research, 2026-10-26. Question: **what does the production-observability canon actually
prescribe, and which of its mechanisms transfer intact to (a) a 2/52/325-period performance qualification,
(b) a fogged economy the player must instrument by organizing, and (c) an event-then-write `AuditReceipt`
trail whose endgame is a retrospective trace query?**

The requested book (Majors, Fong-Jones, Miranda, *Observability Engineering*, O'Reilly) is not on the local
shelves and was not read. Everything below comes from the free canon that book condenses: Honeycomb's product
documentation (`docs.honeycomb.io`), Charity Majors' published essays (`charity.wtf`, now served from
Substack), and the OpenTelemetry concept pages (`opentelemetry.io/docs/concepts`). Where a claim rests on the
book's argument rather than on a page I actually read, I say so and treat it as inference.

Every claim carries a class. **O** = stated in the cited source. **D** = my mapping to Babylon, which no
source endorses. There are no **A** (annotator) claims here; this briefing has one voice and its own
inferences are labelled rather than smuggled.

---

## 0. Thesis

1. The canon's unit is not the metric and not the log line but **one arbitrarily wide event per unit of
   work, stored raw, aggregated only at read time** — and Babylon already has that unit: the committed period.
2. A budget is not a test, it is an **SLO**: a per-period success criterion, a target proportion over a
   window, an error budget counted in periods, and a burn rate that pages *before* the window closes.
3. The player's fog is not missing data, it is **un-instrumented hops**: in the canon a black box cannot emit
   an event, and in Babylon an unorganized household cannot either. Organizing is instrumentation.
4. The reckoning is a **trace query over receipts that were written event-first**, and its evidentiary force
   comes from the canon's hardest rule: aggregation is a one-way trip, so the raw event is the only thing
   that can be re-interrogated later.
5. The canon's economics do not transfer. Honeycomb sells infinite cardinality; Babylon sells 10 MB per
   period. The transferable part is the *shape* (wide event, tail-sampled, SLO-bounded), not the licence
   (tag anything, ask anything, keep everything).

---

## 1. Thread A — the wide event is the qualification contract

### 1.1 What the canon prescribes (O)

The event is "anything that happens in your system that is worth tracking", and events should be **wide**:
"they can contain many different **fields**" because you attach "all of the additional data that it takes to
understand what your system did with that event"
([Honeycomb, *Instrumentation*, §"What is an Event?"](https://docs.honeycomb.io/get-started/observability/concepts/instrumentation.md)).

Majors states the operational form: "emit a single arbitrarily wide event per request per service hop", and
notes that mature datasets "are often 200-500 dimensions wide"
([*Live Your Best Life With Structured Events*, §"Events … must be arbitrarily wide and dense with
context"](https://charity.wtf/p/live-your-best-life-with-structured-events)). Adding dimensions is "still
just one write" — the cost is per event, not per field (same section).

Two consequences the canon draws, both load-bearing here:

- **Derive aggregates, never store them.** Structured events are the source of truth from which "you can
  always, always derive your pretty metrics and dashboards and aggregates"; "Aggregation is a one-way trip"
  (*Live Your Best Life*, §"Events … must be stored raw").
- **Pre-aggregation destroys future questions.** "By pre-aggregating you are forever-destroying your ability
  to answer any questions you didn't predict in advance"
  ([*Observability: A Manifesto*, quiz item 1](https://www.honeycomb.io/blog/observability-a-manifesto)).

Sub-operations get their own nested records: a span "represents a single unit of work", spans nest via parent
IDs, and "child spans represent sub-operations"
([OpenTelemetry, *Traces*, §"Spans"](https://opentelemetry.io/docs/concepts/signals/traces/)).

### 1.2 The game's exact analogue (D)

`docs/architecture-reset/09-acceptance-and-governance.md` §"Performance procedure" already specifies the
measurement in observability vocabulary without naming it: report "judgment, encoding, commit and projection
subphases without substituting one for total latency" (step 5), and "instrument bytes/chunks/entities visited
so bounded work can be inspected, not just inferred from a fast sample" (step 6). That is a demand for
sub-operation spans plus explicit dimension fields. The qualification run is the "unit of work". The period is
the event.

### 1.3 Mechanism A1 — one `PeriodEvent` per committed period, and it lives inside the save

Write exactly one wide record per committed period, and write it **as part of the tick's own commit**, not to
a side channel:

| field group | why it exists (canon) |
| --- | --- |
| `period`, `seed`, `content_hash`, `world_hash`, `graph_hash` | identity and correlation — an event must be "unique, ordered, and traceable" (*Live Your Best Life*, §"Events … must be unique, ordered, and traceable") |
| `judgment_ns`, `encoding_ns`, `commit_ns`, `briefing_ns` | sub-operation spans (OTel *Traces* §"Spans") |
| `chunks_visited`, `entities_visited`, `bytes_read`, `bytes_written` | the "not just inferred from a fast sample" demand (09 §"Performance procedure" step 6) |
| `peak_rss_bytes`, `sample_count`, `sample_gaps` | the 250 ms witness, including its own gaps (09 step 3) |
| `retained_growth_bytes`, `wal_bytes`, `temp_bytes` | retained versus transient accounting (09 §"Retained storage versus transient work") |
| `receipt_count`, `verdict`, `verdict_reason` | the per-period SLI, below |

**D.** This record should be charged to the 10 MB budget rather than exempted from it. At 325 periods the
whole series is on the order of a megabyte — roughly a tenth of a single period's allowance — and charging it
makes the budget honest instead of making qualification the one part of the game that gets a free pass. A
scheme that measures storage while sitting outside the storage budget measures the wrong thing.

**D.** Do not store `p95_advance_ms` or any other rollup. The canon's rule is that the aggregate is derivable
and the raw event is not (*Live Your Best Life*, same section). A stored p95 is a claim that can no longer be
audited; a stored per-period event is evidence.

### 1.4 Mechanism A2 — the budgets are an SLO with an error budget and a burn ladder

**O.** Honeycomb defines the parts precisely ([*What is an SLO?*, §"Key Concepts"](https://docs.honeycomb.io/notify/slos.md)):

- **SLI** — "A per-event measurement that defines whether your system succeeded or failed."
- **SLO** — "The target proportion … of successful SLIs over a rolling time window."
- **Error budget** — "The allowable amount of failure within the SLO window, measured by events or by time."
- **Burn rate** — "actual error rate / expected error rate"; 1.0 exhausts the budget exactly at the end of the
  window, 2.0 exhausts it halfway.
- **Burn alert** — "An alert triggered when the error budget is consumed unusually quickly."

**D.** Mapping, stated exactly:

| canon | Babylon |
| --- | --- |
| event | one committed period |
| SLI | `advance ≤ 30 s` **and** `retained growth ≤ 10 MB` **and** `peak RSS ≤ 4 GB` **and** briefing usable |
| SLO | e.g. 99.4 % of 325 periods ⇒ an error budget of **2 periods** |
| error budget | periods you may burn; separate budgets for latency, growth, memory (do not merge them — a merged SLI hides which wall you hit) |
| burn rate | consecutive-budget failures per window: 2 in 2 periods is a fast burn, 1 in 52 is a slow burn |
| exhaustion-time alert | "at this growth rate the 3.25 GB window closes in *N* periods" |
| burn alert | the smoke gates: the 2-period smoke is the fast-burn probe, the 52-period window the slow-burn probe |

Honeycomb's alert ladder is explicitly multi-window, not single-threshold: the 30-day example runs 2 %/1 h,
5 %/6 h, 10 %/3 d (same page, §"30 Day SLO Example"). **D.** Babylon should copy the ladder and not the
numbers, because a 30.1 s advance at period 300 and three 31 s advances at periods 12–14 are different
diseases with the same average.

**D.** One deviation from the canon is mandatory. Honeycomb's burn alerts page a human
(§"Use the Time Window to Determine the Notification Method"). A qualification run has no human in the loop,
so the burn alert must **degrade the run's claim**, not merely log: a fast burn aborts long-window
extrapolation and forces a diagnosis
(`docs/architecture-reset/09-acceptance-and-governance.md`: "One failed result produces a bounded diagnosis,
not an unattended cycle of slightly different long runs"). The alert's receiver is the evidence file.

### 1.5 Mechanism A3 — tail-sample the witness; never head-sample the verdict

**O.** Head sampling "is a blunt instrument" and "you cannot sample traces based on errors they contain or
their overall latency"
([Honeycomb, *When to Sample*, §"When to Use Head Sampling"](https://docs.honeycomb.io/manage-data-volume/sample/guidelines.md)).
Tail sampling decides "after the request has completed" (same page, §"When to Use Tail Sampling"), and
OpenTelemetry lists as a reason *not* to sample: "You are bound by circumstances such as regulation that
prohibit dropping data"
([OTel, *Sampling*, §"When not to sample"](https://opentelemetry.io/docs/concepts/sampling/)).

**D.** A 250 ms sampler over a 30 s advance yields ~120 samples; 325 periods is ~39 000 samples. The policy
follows from one asymmetry: at 0 ms you cannot know whether this period is the one the reckoning will
interrogate, so the retention decision must be made at commit time, from the period's own verdict.

- **Never sampled:** the `PeriodEvent` itself; every `AuditReceipt`; every period whose verdict is not clean;
  the full memory series for any period that touched a budget.
- **Summarised:** clean periods keep high-water, p50, p95, sample count and gaps, and may drop the series —
  because the raw series is *regenerable by replay* under determinism, which is a stronger guarantee than the
  canon ever has.
- **Sampled:** nothing that a qualification claim depends on. Sampling exists to protect the long window from
  the short one, not to make the numbers pass.

**D.** The sampler is wall-clock and therefore non-reproducible; it may be *evidence about a run* and must
never be an *input to mechanics*. Same for `peak_rss_bytes`. A memory sample that can change the next state
is a nondeterminism bug wearing an instrument's coat.

---

## 2. Thread B — the fog is un-instrumented hops, and organizing is instrumentation

### 2.1 What the canon prescribes (O)

**Observability is for questions you could not pose in advance.** "Observability is for unknown-unknowns.
Monitoring is for known-unknowns"
([*Live Your Best Life*, §"But what about monitoring?"](https://charity.wtf/p/live-your-best-life-with-structured-events)).
The control-theory sense is "how well internal states of a system can be inferred from knowledge of its
external outputs" (same section, quoting Wikipedia). OpenTelemetry's primer says the same in its own words:
observability "lets you ask questions about that system without knowing its inner workings", including
"'unknown unknowns'"
([OTel, *Observability primer*, §"What is Observability?"](https://opentelemetry.io/docs/concepts/observability-primer/)).

**Interrogation beats anticipation, and anticipation is cheating.** Achieving this "relies your ability to ask
brand new questions … *without shipping new code.* Shipping new code is cheating, because it means that you
knew in advance what the problem was in order to instrument it" (*Live Your Best Life*, same section).

**Instrumentation is a first-class engineering act, not a post-hoc add-on.** "Do you bake observability right
into your code as you're writing it? … You can't just tack this on after the fact" (*Observability: A
Manifesto*, quiz item 5).

**A black box cannot testify.** "We only gather observability events from services that we can and do
introspect. If it's a black box to us, that hop cannot generate an observability event"
(*Live Your Best Life*, §"Events are the building blocks of observability"). This is the single most
transferable sentence in the canon for Babylon.

**Investigation has a repeatable shape.** The core analysis loop is Define → Visualize → Investigate →
Evaluate, and "you should have to know very little before debugging an issue"
([Honeycomb, *Core Analysis Loop*](https://docs.honeycomb.io/get-started/honeycomb/core-analysis-loop.md)).
Its automation is a mechanical diff: "retrieve the values of all dimensions, both inside the isolated area
(the anomaly) and outside the area (the system baseline), diff them, and then sort by the difference"
(same page, §"Automating the Core Analysis Loop"). BubbleUp is that diff shipped as a feature: it "displays
outliers and explains how a subset of data differs from other data", with each field drawn as selection
(yellow) versus baseline (blue)
([*Identify Outliers*, intro and §"Interacting with BubbleUp Charts"](https://docs.honeycomb.io/investigate/analyze/identify-outliers.md)).

**Cardinality is where the needles are.** High cardinality means "many possible values for a single
attribute"; a high-cardinality field "can help uniquely identify a request"
([*High Cardinality*, §"What is Cardinality?"](https://docs.honeycomb.io/get-started/observability/concepts/high-cardinality.md)).
The canon's worked example of a needle is a conjunction of six high-cardinality dimensions — platform,
version, locale, install date, firmware, shard (*Observability: A Manifesto*, §"Observability requires high
cardinality and high dimensionality").

### 2.2 The game's exact analogue (D)

Babylon already has a metric-to-event upgrade ladder with a different name. `VeilTier::T0PricesOnly`
(`docs/gameplay/2026-10-26-onboarding-and-product-layer-design.md` §2, G1) is pre-aggregated metrics: the
player sees prices, not the transactions that made them. `T1ExploitationVisible`, `T2MarketScissors` and
`StructuralStateView` are progressively wider events on the same underlying world. Organizing a household or
a workplace is what converts a hop from black box to introspectable — the canon's precondition, enforced
politically rather than technically.

The player's `Verify` verb (provenance checks, receptivity-gated truth) is the core analysis loop with the
state's incentives attached; `docs/gameplay/2026-10-26-combat-design.md` already names "receptivity-gated
truth" and "checking provenance on offers" as the Verify step.

So the mapping is not metaphorical:

| canon | Babylon |
| --- | --- |
| hop that emits no event | household/worksite the organization has not reached |
| instrumentation | organizing: the visit, the meeting, the kitchen, the shop-floor committee |
| high-cardinality dimension | `household_id`, `workplace_id`, `person_id`, `county_id` |
| low-cardinality field | claim kind, source kind, corroboration count |
| selection vs baseline (BubbleUp) | "these 40 households" vs "the county" |
| core analysis loop | Read → Verify (→ Allocate → Seal) |

### 2.3 Mechanism B1 — receptivity gates the event, and the event is the only truth the player gets

**D.** A hop contributes observations **only if** `receptivity ≥ threshold` for that hop at that period. Below
threshold the engine still simulates the hop — the economy does not pause for the player's ignorance — but it
emits a **sealed** record: identity and existence, no internal dimensions. The player sees that something
happened at 14 Mill Street and cannot see what.

**D.** Three rules keep this from becoming a slot machine:

1. **No retroactive instrumentation.** Raising receptivity in period *N* opens the hop from period *N*
   forward. It does not backfill the fog. This is the canon's anti-cheating rule (*Live Your Best Life*:
   "Shipping new code is cheating") turned into a knowledge rule, and it matches the existing acceptance
   scenario "Late/backdated knowledge grant | No disclosure before actual acquisition; current grant cannot
   rewrite past knowledge" (09 §"Minimum correctness scenarios").
2. **Provenance is a link, not an attribute.** A claim points at the acquisition event that produced it
   (who told you, when, in what room) rather than at a confidence number. A confidence number is a
   pre-aggregation of trust: it destroys the ability to ask *why* you believed it, which is exactly the
   question the reckoning asks.
3. **Sealed hops are still chargeable.** An un-instrumented hop costs the player nothing to store and yields
   nothing to query. That is the correct incentive and it is the whole political economy of the loop.

### 2.4 Mechanism B2 — cardinality discipline: high on entities, closed on claims

**D.** The canon's "infinite cardinality" is unaffordable at 10 MB/period, and Majors says plainly that the
2.0 cost model moves the constraint rather than deleting it — costs become "traffic, architecture, and
density of your instrumentation"
([*Another observability 3.0 appears on the horizon*](https://charity.wtf/p/another-observability-3-0-appears-on-the-horizon)).
So the game must split the schema:

- **Open, high-cardinality, entity-valued:** identifiers of households, workplaces, people, counties, firms.
  Unbounded distinct values, one integer each, bounded width. This is where investigation happens.
- **Closed, enumerable, claim-valued:** source kind (`told`, `seen`, `record`, `inferred`), motive, date
  bucket, corroboration count, cost-of-being-wrong. A fixed vocabulary, because free-text tags are free-text
  omniscience and an unbounded column is an unbounded save.
- **Forbidden:** player-authored dimension names. Naming a dimension is choosing a future question
  (`Observability: A Manifesto` quiz item 1), and the game cannot afford an open question space of 325
  periods × arbitrary columns.

This is a real design constraint with a real cost: the player will sometimes want to slice by something the
schema does not carry. The canon's answer is "instrument it and wait"; Babylon's answer must be "you may add
an instrument, from now on, and pay for it" — which is exactly what an organizer does.

### 2.5 Mechanism B3 — the investigation verb is a deterministic diff, not a narrator

**D.** Implement BubbleUp's mechanic literally, over the wine-press of the player's known events:

1. Player selects a region — a period range × a county, or a household set — on a heatmap of any known
   measure.
2. The engine computes, for every **known** dimension, the distribution inside the selection and outside it,
   and ranks by absolute difference (the algorithm is stated in *Core Analysis Loop*, §"Automating the Core
   Analysis Loop").
3. Output is a ranked list of "this is what is unusual about the thing you selected", computed from recorded
   facts, with counts and denominators visible.

Why the diff and not the LLM: the canon's automation is arithmetic, and the repository's constitutional
compact is that "AI can parse, retrieve, and narrate. Only the engine judges mechanics"
(`AGENTS.md` §"Constitutional compact"). The narrator can phrase the finding — "the co-op on Grand River is
the only site where dues fell while hours rose" — but it must not produce the ranking. A ranked diff is
auditable; a paragraph is not.

**D.** The denominator is the honesty device. BubbleUp's tip is that the comparison is only meaningful when
selection and baseline actually differ, and that a selection inside the main cluster is unreadable
(*Identify Outliers*, §"Tips and Tricks"). The game's equivalent trap is the interesting one: the player who
only instruments their friends gets a baseline that is also their friends, and the diff finds nothing. **The
fog has a sampling bias and the player owns it.**

---

## 3. Thread C — the reckoning is a trace query over event-first receipts

### 3.1 What the canon prescribes (O)

**Events must be ordered and traceable.** "You need a unique request ID, and you need to propagate it through
your stack in some way that preserves sequence. Once you have that, traces are just a beautiful visualization
layer" (*Live Your Best Life*, §"Events … must be unique, ordered, and traceable").

**Raw retention is the whole point.** "Once you have aggregated your data and discarded the raw requests, you
have destroyed your ability to ask new questions of that data forever" (same section, §"Events … must be
stored raw").

**Causality across time gaps needs an explicit link.** A span link associates spans "implying a causal
relationship" where the subsequent operation is asynchronous and "we cannot predict when the subsequent
operations will start"; you "link the last span from the first trace to the first span in the second trace"
([OTel, *Traces*, §"Span Links"](https://opentelemetry.io/docs/concepts/signals/traces/)).

**Retention can be restored, at a cost and at a fidelity.** Archive rehydration "retrieves your full,
unsampled dataset from S3 storage on-demand"; you filter "by time range and indexed fields", and where a
filtered index leaves gaps in a trace you must "rehydrate again using the trace ID" to recover the missing
spans ([Honeycomb, *Query with Archive*, §"How It Works" and §"Enhancing Traces with Missing Spans"](https://docs.honeycomb.io/investigate/query/archive.md)).
Rehydration is metered and estimated before it runs.

**One class of data is exempt from sampling by principle**, not by preference: data you are forbidden to drop
(OTel, *Sampling*, §"When not to sample", quoted above).

### 3.2 The game's exact analogue (D)

`AGENTS.md` §"Live architecture" already describes the mechanism: `MaterialReplaySession` "publishes material
state, graph, events, and event-then-write `AuditReceipt` rows … only after the detached tick succeeds."
Event-then-write is a stronger guarantee than the canon's: the write is a *function of the event*, so the
event is sufficient to reconstruct the write, which is precisely what the canon can only approximate.

The reckoning is therefore a query with a known shape, not an investigation with an unknown one:

| canon | Babylon |
| --- | --- |
| trace | one committed period |
| span | one `AuditReceipt` row |
| span ordinal / parent | receipt `ordinal`, same-rank sequential composition |
| span attributes | rule role, evidence class, effect signature, magnitudes |
| span link | acquisition event that justified a knowledge grant |
| trace ID | period + campaign identity |
| archive rehydration | cited Archive page fetched on demand by receipt |

### 3.3 Mechanism C1 — the receipt is a span, and the reckoning asks four questions

**D.** Give every receipt the minimum a span needs — identity, order, parentage, timing, attributes, status —
and pre-register the reckoning's question set so that "explainable after the fact" has a test:

1. **What happened?** The ordered effect chain for the period, replayable from receipts alone.
2. **Why was it allowed?** Rule role and evidence class per effect (`Observed` / `Derived` / `Calibrated` /
   `Designed`, per `AGENTS.md` §"Constitutional compact").
3. **On what authority?** The knowledge grant and its acquisition link — which must pre-date the effect.
4. **What did we not know?** Sealed hops, ungranted knowledge, and the receipts that would exist had the
   organization reached further.

Question 4 is the one that makes the endgame an "oh shit" rather than a balance sheet, and it is only
answerable if sealed hops left *existence* records during play (§2.3). You cannot regret a hop you never
recorded.

**D.** The reckoning query must be pre-registered at campaign start, with its answers computable from
receipts alone. Two reasons: the canon's own cost warning (arbitrary questions require arbitrary retention),
and the anti-cheating rule — if the player could choose the reckoning question at the end, they would be
"shipping new code" after seeing the answer.

### 3.4 Mechanism C2 — a named non-sampleable floor, checked in CI

**D.** Enumerate the fields the reckoning cannot do without, and make that enumeration a test rather than a
convention:

```text
RECKONING_FLOOR = {period, campaign_id, receipt_ordinal, rule_id, role,
                   evidence_class, effect_signature, magnitude, grant_id,
                   acquisition_period, source_kind, world_hash}
```

Three properties, each borrowed:

- **Never sampled, never evicted** — the OTel "prohibited from dropping" carve-out.
- **Never aggregated** — a stored total is a destroyed question (*Live Your Best Life*).
- **Exactly enumerated** — the floor's consumers must equal the floor's fields, so CI rejects dead
  permissions. This is the same discipline `AGENTS.md` already imposes on restricted production footprints
  ("CI rejects dead permissions").

Everything outside the floor may be summarised, sampled, or rehydrated from the Archive on citation. The floor
is the line between "the reckoning can explain this" and "the reckoning can only assert it".

### 3.5 Mechanism C3 — rehydration is citation, not exploration

**D.** The Archive holds full-fidelity pages; the campaign holds the receipt index. A reckoning may cite a
page and pull it back — metered, attributed, and recorded as a read. It may not wander.

Honeycomb's Archive makes the trade visible by metering rehydration and requiring a high-cardinality index to
aim it (*Query with Archive*, §"Best Practices for Rehydration"). Babylon's determinism makes the trade
*sharper*, not softer: rehydration here is exact rather than approximate, so the only cost is latency and
storage, and the only discipline is that the query names what it wants before it gets it. An unbounded
"reconstruct everything" button would be a correct implementation of the canon and a design failure — it
converts the reckoning from an argument into a dump.

---

## 4. What the canon does not license

Stated plainly, because three of these are load-bearing and one is a trap.

1. **The fog is player-facing, not engine-facing.** Observability canon assumes operators cannot see inside
   a system they nonetheless built. Babylon's engine sees everything and must: "Equal input bytes must
   produce equal output bytes and hashes" (`AGENTS.md`). Do not let "unknown-unknowns" justify hidden state,
   nondeterministic mechanics, or an AI that invents what the engine knows. The player's ignorance is a
   *knowledge model*, not an engine limitation.
2. **"Cardinality is free" is false here.** Honeycomb's economics are per event (*Live Your Best Life*,
   §"Events … must be arbitrarily wide"), and its own 2.0 cost model still names instrumentation density as a
   cost driver (*Another observability 3.0*). At 10 MB/period, schema is a budget line. Pick it up front and
   refuse extension at runtime.
3. **Qualification telemetry is not a game display.** `AGENTS.md` §"Constitutional compact": "Each game
   display must answer a decision question. An administrative display cannot pass a game milestone." The
   `PeriodEvent` is evidence for the evidence file; it becomes a player surface only where it answers a
   decision — which is why Thread A's heatmap and Thread B's diff are the same widget viewed twice.
4. **A 250 ms sampler is not a mechanic.** It is wall-clock, therefore non-reproducible, therefore evidence
   about a run and never an input to state. If a sample can change the next period, determinism is already
   broken and no instrumentation will show it.

**Open questions I could not settle from the sources.**

- Does the reckoning's "what did we not know" question leak the fog forward into later campaigns? A player
  who learns the sealed-hop statistics may instrument better next run, which is legitimate learning or an
  unfair carry-over depending on the campaign boundary. Design decision, not research finding.
- Is a per-period SLO of 99.4 % over 325 periods the right shape, or does the growth budget deserve its own
  exhausted-at-3.25 GB curve independent of latency? The canon insists on separating performance from
  availability SLOs (*What is an SLO?*, §"Structuring SLOs": "Separate concerns"). I have followed that, but
  the numbers are placeholders.
- The canon's most quoted line — ask any question without shipping new code — is in tension with any fixed
  schema. Babylon resolves it by moving the cost to *organizing* rather than to *code*. Whether players
  experience that as freedom or as a paywall is a playtest question.

**Resolutions (Director, 2026-10-26).**

- R1 — carry-over: the *human's* learning crosses the campaign boundary freely (roguelike knowledge; cannot
  and should not be prevented). Nothing mechanical crosses: no stats, unlocks, retained intel, or seeded
  content repeats (new campaigns generate fresh content, so campaign-specific facts do not transfer). Sealed-hop
  statistics learned in a reckoning are knowledge *about the system*, equivalent to learning the rules — fair
  game. Each campaign's fog is re-earned inside it, per the visibility rule.
- R2 — growth gets its own curve: three budgets, three SLOs, one verdict by AND. Latency is a per-event rate
  (burnable periods per window); growth is a cumulative exhaustion curve against the 3.25 GB ceiling
  (gigabytes remaining); memory is an instantaneous gauge (never above 4 GB). Different mathematics, different
  alerts; the campaign verdict requires all three green.
- R3 — freedom, by contract, verified by playtest later. Organizing reads as freedom iff three guarantees hold
  in the investigate verb: (a) every cost is legible upfront (Standing Asks show the price before it is paid);
  (b) no single tollbooth — every truth is reachable by at least two of organizing, captured documents, or
  flipped assets; (c) the verb never returns empty — a deterministic diff that finds nothing says "nothing
  differs," which is itself information. Single tollbooth, hidden price, or empty answers would be a paywall;
  all three are refused by contract.

---

## 5. Evidence table

**O** = stated in the source. **D** = my inference or game mapping; no source endorses it.

| # | Claim | Class | Source (URL + section) | Game consequence |
| --- | --- | --- | --- | --- |
| 1 | An event is anything worth tracking; events should be wide, with many fields | O | [Honeycomb, Instrumentation, §What is an Event?](https://docs.honeycomb.io/get-started/observability/concepts/instrumentation.md) | one wide record per committed period |
| 2 | Emit a single arbitrarily wide event per request per hop; mature datasets are 200–500 dimensions | O | [Live Your Best Life, §…arbitrarily wide](https://charity.wtf/p/live-your-best-life-with-structured-events) | all subphase and resource fields on one record, not five |
| 3 | Extra dimensions cost "just one write" | O | same, same section | the marginal field is cheap; the marginal *event* is not |
| 4 | Aggregation is a one-way trip; derive metrics from raw events | O | same, §Events … must be stored raw | store `PeriodEvent`, never a stored p95 |
| 5 | Pre-aggregation destroys unpredicted questions | O | [Observability: A Manifesto, quiz 1](https://www.honeycomb.io/blog/observability-a-manifesto) | the Ticker shows aggregates; the case file holds events |
| 6 | A span is one unit of work; child spans are sub-operations | O | [OTel, Traces, §Spans](https://opentelemetry.io/docs/concepts/signals/traces/) | judgment/encoding/commit/briefing as child spans of the period |
| 7 | SLI = per-event success/failure measurement | O | [What is an SLO?, §Key Concepts](https://docs.honeycomb.io/notify/slos.md) | per-period verdict against all three budgets |
| 8 | SLO = target proportion over a rolling window | O | same | 99.4 % of 325 periods |
| 9 | Error budget = allowable failure, in events or time | O | same | N burnable periods |
| 10 | Burn rate = actual/expected error rate; 1.0 exhausts exactly at window end | O | same | overruns per window, not per-run average |
| 11 | Burn alert fires when budget depletes faster than expected | O | same | smoke gates as fast-burn probes |
| 12 | Multi-window alert ladder (2 %/1 h, 5 %/6 h, 10 %/3 d) | O | [Monitor SLOs, §30 Day SLO Example](https://docs.honeycomb.io/notify/slos/monitor.md) | copy the ladder shape, not the numbers |
| 13 | Separate performance from availability SLOs | O | [What is an SLO?, §Structuring SLOs](https://docs.honeycomb.io/notify/slos.md) | latency, growth, memory as distinct budgets |
| 14 | Head sampling cannot select on error or latency | O | [When to Sample, §When to Use Head Sampling](https://docs.honeycomb.io/manage-data-volume/sample/guidelines.md) | the 250 ms series cannot be head-sampled |
| 15 | Tail sampling decides after completion | O | same, §When to Use Tail Sampling | retention decided at commit, from the verdict |
| 16 | Regulatory retention is a reason not to sample | O | [OTel, Sampling, §When not to sample](https://opentelemetry.io/docs/concepts/sampling/) | `RECKONING_FLOOR` carve-out |
| 17 | Observability = inferring internal state from external outputs, incl. unknown-unknowns | O | [OTel, Observability primer, §What is Observability?](https://opentelemetry.io/docs/concepts/observability-primer/) | the veil is an inference problem, not a data-deletion problem |
| 18 | Observability is for unknown-unknowns; monitoring for known-unknowns | O | [Live Your Best Life, §But what about monitoring?](https://charity.wtf/p/live-your-best-life-with-structured-events) | Ticker = monitoring; case file = observability |
| 19 | "Shipping new code is cheating" — instrumentation must precede the question | O | same section | no retroactive instrumentation; no endgame-chosen question |
| 20 | Instrumentation is first-class during development, not added after | O | [Observability: A Manifesto, quiz 5](https://www.honeycomb.io/blog/observability-a-manifesto) | organizing is a build step, not a debug step |
| 21 | A black box hop cannot generate an observability event | O | [Live Your Best Life, §Events are the building blocks](https://charity.wtf/p/live-your-best-life-with-structured-events) | receptivity gate on observation emission |
| 22 | Core analysis loop: Define, Visualize, Investigate, Evaluate | O | [Core Analysis Loop](https://docs.honeycomb.io/get-started/honeycomb/core-analysis-loop.md) | Read/Verify/Allocate/Seal loop |
| 23 | Automating the loop = diff all dimensions inside vs outside the selection, sort by difference | O | same, §Automating the Core Analysis Loop | the investigation verb is a deterministic diff |
| 24 | BubbleUp compares a selection to a baseline across all fields | O | [Identify Outliers, §Interacting with BubbleUp Charts](https://docs.honeycomb.io/investigate/analyze/identify-outliers.md) | heatmap select → ranked "what is unusual" |
| 25 | A selection inside the main cluster is unreadable | O | same, §Tips and Tricks | a friends-only baseline finds nothing |
| 26 | High cardinality = many distinct values; it identifies a specific request | O | [High Cardinality, §What is Cardinality?](https://docs.honeycomb.io/get-started/observability/concepts/high-cardinality.md) | open cardinality on entity IDs |
| 27 | Cardinality cost is the 1.0 model; 2.0 shifts cost to traffic, architecture, instrumentation density | O | [Another observability 3.0](https://charity.wtf/p/another-observability-3-0-appears-on-the-horizon) | schema is a budget line at 10 MB/period |
| 28 | Events must be unique, ordered, traceable; propagate an ID preserving sequence | O | [Live Your Best Life, §…unique, ordered, traceable](https://charity.wtf/p/live-your-best-life-with-structured-events) | period/campaign identity plus receipt `ordinal` |
| 29 | Span links express causal association across asynchronous gaps | O | [OTel, Traces, §Span Links](https://opentelemetry.io/docs/concepts/signals/traces/) | grant links back to its acquisition event |
| 30 | Archive rehydration restores unsampled data by time range + indexed fields | O | [Query with Archive, §How It Works](https://docs.honeycomb.io/investigate/query/archive.md) | citation-time page fetch |
| 31 | Missing spans require rehydration by trace ID | O | same, §Enhancing Traces with Missing Spans | fetch the rest of the period by trace |
| 32 | Rehydration is estimated and metered before it runs | O | same, §Best Practices for Rehydration | cited reads are attributed and bounded |
| 33 | Qualification must report subphases without substituting one for total | O (repo) | [09-acceptance-and-governance, §Performance procedure](../../architecture-reset/09-acceptance-and-governance.md) step 5 | four named subphase spans per period |
| 34 | Instrument chunks/entities visited so bounded work is inspectable | O (repo) | same, step 6 | `chunks_visited`, `entities_visited` on the event |
| 35 | One failed result produces a bounded diagnosis, not an unattended retry | O (repo) | same, closing paragraph | burn alert degrades the claim and stops |
| 36 | Event-then-write receipts publish only after the detached tick succeeds | O (repo) | [AGENTS.md, §Live architecture](../../../AGENTS.md) | the receipt is a function of the event |
| 37 | CI rejects dead permissions in restricted footprints | O (repo) | same, §Live architecture | floor fields must equal floor consumers |
| 38 | Every game display answers a decision question; admin displays do not pass a milestone | O (repo) | same, §Constitutional compact | qualification telemetry is not a player screen |
| 39 | Each `PeriodEvent` should be charged inside the 10 MB budget | D | inference from rows 3–4 and 09 §Retained storage | ~1 MB across 325 periods, inside the accounting |
| 40 | Verdicts drive retention: clean periods summarise, dirty periods keep the full series | D | from rows 14–16 | tail-sampled witness |
| 41 | Receptivity gates event emission; a sealed hop records existence only | D | from rows 19–21 | organizing = instrumentation |
| 42 | Open cardinality on entities, closed vocabulary on claims, no player-authored dimensions | D | from rows 26–27 | schema discipline as political economy |
| 43 | The reckoning pre-registers four questions and is answerable from receipts alone | D | from rows 28–29 and row 19 | the endgame is a fixed query |
| 44 | A named, CI-checked `RECKONING_FLOOR` of never-sampled fields | D | rows 16, 37 | dead-field detection on the floor |
| 45 | Rehydration by citation, never by exploration | D | rows 30–32 | the reckoning argues, it does not dump |
| 46 | The 250 ms sample and peak RSS are evidence, never inputs | D | from `AGENTS.md` determinism clause | no sampling-dependent mechanics |

---

## 6. Sources and reading log

Read in full: Honeycomb *Instrumentation*; *High Cardinality*; *Core Analysis Loop*; *Identify Outliers*;
*What is an SLO?*; *Monitor SLOs*; *Traces, Metrics, and Logs*; *When to Sample*; *Query with Archive*;
OpenTelemetry *Observability primer*, *Traces*, *Sampling*; charity.wtf *Live Your Best Life With Structured
Events*, *Observability: A Manifesto* (Honeycomb blog), *The Truth About "MEH-TRICS"*, *The Cost Crisis in
Observability Tooling*, *Another observability 3.0 appears on the horizon*, *Is It Time To Version
Observability?*, *So You Want To Build An Observability Tool…*.

Read only as search excerpts, **not relied on**: *Notes on the Perfidy of Dashboards*; *Observability is a
Many-Splendored Definition*; *Questionable Advice: War Rooms? Really?!?*; *How Observability Differs from
Traditional Monitoring*; Honeycomb *Observability Concepts* index.

Not available locally, therefore **not used as evidence**: *Observability Engineering* (Majors, Fong-Jones,
Miranda, O'Reilly, 2022) and its second edition. Several claims above are the blog-and-docs form of that
book's arguments; I have cited the free pages rather than the book, so the citations are checkable. Where the
canon appears in this briefing as a single voice, that is a compression I made, not a claim that these
sources agree on everything — Majors' essays are polemic and the product docs are committee prose, and they
differ on how much cardinality is genuinely free.

`charity.wtf` now resolves through Substack; post paths are `/p/<slug>` rather than the old `/YYYY/MM/DD/<slug>/`
form. Old dated URLs 404. Cited URLs were fetched 2026-10-26.
