# Observer qualification — 2026-09-13

This record separates the final bounded observer acceptance from retained earlier
passes. The final executable supports the native discovery exercise at
1366×768 and 1920×1080. This is partial evidence for PER-319, PER-293, PER-33
and PER-257. It does not close Gate 3 or Gate 4 and claims no player action.

## Final source and native acceptance

The final native build includes maintenance, the complete music catalog, and
the observer repairs. Its Git parent alone does not identify the implementation:
the build used uncommitted source. [Build provenance](test-results/per293-observer/native-current/build-provenance-catalog-projection-fixed.json)
pins the 973-file inventory at 06:23:08 UTC and these executable hashes:

- Client: `862c76dbbe1bb7d86076653d2eca6d09a2e94e97ca2f5997bfcc48ef4e3b152c`.
- Runtime: `a7a1dfafed40af910b23b3821aced40ce571bf2237a21fe7a12215dce864a6bf`.
- Inventory: `78024779521e8e2cb79bd12bb3307c61df860a5b263e34409292dcfe75473e7b`.

The later SQL-injection repair changes only a live test. Publication lint also
wrapped three contract lines. The
[parsed-YAML check](test-results/per293-observer/native-current/contract-format-only.json)
proves their content stayed the same. A later source edit updates only the
declared contract fingerprint to match those bytes. That constant has no runtime
consumer.

All other inventoried production source, assets, and captured content
match the native build. These debug binaries are not a newly published release.

The [final native log](test-results/per293-observer/logs/native-final-catalog-projection-fixed.log)
and [capture index](test-results/per293-observer/native-current/native-evidence-final.json)
join campaign, period, perspective, selected subject, and presentation state.
The index preserves screenshot hashes and explicitly corrects misleading
filenames, including captures made before an asynchronous read completed.
The earlier [integrated capture index](test-results/per293-observer/native-current/native-evidence-before-final-repairs.json)
retains the discovery evidence that led to the last two repairs.

| Final-source statewide save | Campaign UUID | Native result |
| --- | --- | --- |
| Baseline | `fd20cbc9-1650-469e-9f8b-0ba3de4d946b` | Fresh-process resume at period 6. Earlier native Advance committed period 6 |
| Freight constraint | `38fe342f-50e2-439b-af0c-1f2f3f7ec8ab` | Direct Open at period 5. Held periods 1 and 3 |
| Packaging shortage | `a50e963f-0d21-4846-be8e-70caf7e4e588` | Direct Open at period 5. Merchant, fulfillment, and historical Archive inspection |
| Both constraints | `9d082ad8-7392-4734-890e-180c9cb549dc` | Direct Open at period 5. Same-period comparisons |

All four maintenance saves also reached Ready in this executable. The
[maintenance record](maintenance-qualification-2026-09-13.md) gives their complete
job/output/recovery witness and the new campaign created and advanced
entirely through the native menu. Existing campaigns and earlier binary pairs
remain retained separately.

The native-created campaign `c81094f6-99c5-41d6-80ba-7cbfc645241e` also reopened
in a separate native process, PID 2389000. It reached Ready at viewed/durable
period 3, with Archive verified through period 3. The 1366×768 inspection showed
Wayne metal-parts output of 960 kg. It also showed 6 employed and 6 reserve workers,
16 consumed service batches, and 44 kg of provider parts.

The prior process, PID 2270950, reported Closed with `failed=false`. The
[fresh-resume record](test-results/per293-observer/native-current/native-created-maintenance-fresh-resume.json),
[log](test-results/per293-observer/logs/native-maintenance-fresh-resume-final.log),
and [capture](test-results/per293-observer/native-current/final/maintenance-fresh-process-output-p3.png)
preserve this final restart check. The game remains open at the recovered producer.

### Completed discovery exercise

Saved campaigns, Continue, Open and Compare appear above the new-campaign
families at both resolutions. Continue returns to the world. Map county/cohort
selection leads to Circuit, whose supplier, buyer, shared-freight participant,
and maintenance service links keep distinct meanings. Readings and comparison
controls remain accessible while their contents scroll.

<!-- Vale: St. Ignace is the source place name in the Archive row. -->
| Final native inspection | Result | Representative capture under `native-current/final/` |
| --- | --- | --- |
| Bridge, freight CURRENT / baseline COMPARED, period 1 | 709 / 2,207 kg reserved. 291 / 97,793 kg remaining. Reservations remain separate from arrivals | `1366-freight-baseline-bridge-p1.png`, `1920-freight-baseline-bridge-p1.png` |
| Mackinac food, freight CURRENT / both COMPARED, period 1 | 1,600 / 800 kg. 16 / 8 completed batches. Holding the freight constraint common isolates the packaging difference | `1366-freight-both-food-p1.png`, `1920-freight-both-food-p1.png` |
| Chippewa household wares, freight CURRENT / baseline COMPARED, period 3 | 1 / 8 items. 1 / 3 employed and 11 / 9 reserve | `1366-freight-baseline-chippewa-p3.png`, `1920-freight-baseline-chippewa-p3.png` |
| Wayne metal parts, baseline CURRENT / freight COMPARED, period 1 | Unaffected opening output: 960 / 960 kg, 8 / 8 employed and 4 / 4 reserve. Both use the same opening material and labor before later delivery differences | `1366-wayne-baseline-freight-unaffected-p1.png`, `1920-wayne-baseline-freight-unaffected-p1.png` |
| Chippewa relationships | Luce wood and Antrim parts are suppliers. Navigation reaches Mackinac food as a shared-capacity participant | `1920-chippewa-relationships-p1.png` |
| Packaging Mackinac wholesaler, period 5 | Food: 300 opened + 200 received locally − 300 transferred = 200 kg closing. Handling is not production | `1366-packaging-wholesale-flow-p5.png`, `1920-packaging-wholesale-flow-p5.png` |
| Packaging Mackinac retailer, period 5 | Food: 6,400 kg ordered, 1,200 fulfilled, 5,200 outstanding. Consumption is explicitly not recorded | `1366-packaging-retail-fulfillment-p5.png`, `1920-packaging-retail-fulfillment-p5.png` |
| Held Archive, viewed 3 / durable 5 | County and <!-- vale Vale.Spelling = NO -->St. Ignace<!-- vale Vale.Spelling = YES --> place keep original publication at period 1 and verification through the viewed period 3 | `1366-mackinac-archive-held3.png`, `1920-mackinac-archive-held3.png`, `1366-st-ignace-held3-citation-expanded.png` |
| Restricted preview | Circuit withholds production and service accounts. Public cited place identity remains available | `1366-known-circuit-held3.png`, `1920-known-circuit-held3.png`, `1366-known-archive-held3.png` |

The food and wares quantities are explicit kilograms and items. Modeled workers
and labor-hours remain distinct from observed annual-average QCEW jobs. Merchant
handling, delivery fulfillment, consumption, and monetary payment are separate
concepts: this slice records quantity realization and does not model payments or
household consumption. The exercise uses native controls to inspect and
explain these accounts. Terminal tools only launch and keep qualification evidence.

### Repairs and music

History now authenticates a bounded production series through the existing
reader instead of repeatedly constructing full per-period observations. Its
corruption, reopen, and preview-refusal contracts remain enforced. Comparison
starts with the selected cohort and keeps Close and section controls fixed.
Output labels use committed quantities and units instead of treating all outputs
as batch counts. The campaign menu groups presets and puts saved work first.

Native qualification found two later blockers. Catalog refresh and held-period
changes silently reset the chosen comparison. Selection now uses the campaign
identity across refreshes and ordering changes. A removed save stays unavailable
until explicitly reselected.

[RED](test-results/per293-observer/logs/catalog-selection-red.log)
records three failed regressions. [GREEN](test-results/per293-observer/logs/catalog-projection-final-green-build.log)
records all seven catalog checks passing. The same build repairs the maintenance
projection's merchant coverage count, as the maintenance report explains.

All 36 existing MIDI compositions now have embedded audio renders: 92.238 minutes and
88,379,983 music bytes. The six existing sound effects remain. Finite tracks
advance through the catalog automatically. The menu shows title and position.

The native session exercised Next `[J]`, volume/mute `[B]`, and campaign handoff. The log records track progression, mute/restore, and preserved music
state across campaign switches. This is playback/control evidence, not a claim
that the evaluator listened to every track or that event-specific cues exist.

### Final verification disposition

The full no-documentation Rust publication run passed 2,561 tests, with 33
ignored, zero failures, and zero flaky tests. Formatting, workspace Clippy,
replay/conformance contracts, and BSL sentinels also passed. See the
[publication log](test-results/per293-observer/logs/integrated-rust-publication-3.log).

Later catalog/projection repairs passed their RED/GREEN checks, scoped
all-target Clippy, and native rebuild. The final SQL-injection test repair
passed persistence all-target Clippy in 27.08 seconds and the live proof below.

<!-- Vale: PostgreSQL is the database project's proper name. -->
<!-- vale Vale.Terms = NO -->
The required statewide PostgreSQL run passed the unchanged four original
cases through 16 periods each. Its new maintenance test exposed an invalid
injection setup. The repaired, isolated maintenance rerun passed all four
three-period cases and SQL rollback/retry in 496.09 seconds. Both attempts
and their distinct statuses remain in the maintenance record.
<!-- vale Vale.Terms = YES -->

The [client/Archive live test](test-results/per293-observer/logs/postgres-client-final.log)
passed in 72.37 seconds. It covered compiled CLI reads, confined authority,
dossier/search/changelog, restart, and quiet-worker refresh of held content.
Harness cleanup finished with status zero. The outer `mise run` process
separately reported SIGTERM and returned 1. Its cause remains unknown. This
record distinguishes the completed test and cleanup from the failed outer invocation.

The Python [check](test-results/per293-observer/logs/integrated-python-check.log)
passed hygiene, locks, governance, formatting, Ruff and mypy. It then recorded
2,359 passing tests, 18 skips, and one tracked-music-selector failure. Staging
the 34 new renders corrected that selector. Its focused regression then
[passed](test-results/per293-observer/logs/music-staged-selector-green.log).
The original failing invocation remains visible.

<!-- Vale: PostgreSQL is the database project's proper name. -->
<!-- vale Vale.Terms = NO -->
The separate three-test PostgreSQL History pass below covers the earlier reader
run's single unfinished history test. This record keeps that timeout.
No governed baseline changed. No documentation build ran.
<!-- vale Vale.Terms = YES -->

The first final-commit pre-push run passed 2,563 tests and failed one contract
fingerprint assertion. YAML line wrapping changed the source bytes without
updating their declared SHA. The freight permutation and continuation assertions
passed before that check. The fingerprint repair changes no transition or wire
encoding. The original [RED run](test-results/per293-observer/logs/final-push.log)
remains retained. The [focused GREEN check](test-results/per293-observer/logs/contract-fingerprint-green.log)
and [scoped Clippy check](test-results/per293-observer/logs/contract-fingerprint-clippy.log)
passed after the fingerprint correction.

Hosted repository hygiene then rejected the 34 newly committed music tracks.
Its named size limits still covered only the original themes. The repair gives
those exact 34 paths the same 12 MiB bound as the pre-commit hook. The original
2 MiB theme limits and 1 MiB general limit remain.

The [new regression](test-results/per293-observer/logs/audio-hygiene-red-proven.log)
failed before the repair. The [focused checks](test-results/per293-observer/logs/audio-hygiene-green.log)
then passed 24 tests, including exact boundaries and unrelated-path refusal.
The full [Python and repository check](test-results/per293-observer/logs/final-python-check-green.log)
passed 2,361 tests with 18 skips in 89.15 seconds. Hygiene, formatting, lint,
type checks, locks, and governance checks passed in that same invocation.

### Final frame behavior and held-read latency

[Final performance evidence](test-results/per293-observer/native-current/performance-final.json)
uses explicitly marked 16-second intervals after the heavy gates completed.
Only complete, stable, Ready windows of 300 frames count. The campaign is the
native-created maintenance Both case, durable period 3. Flow is live and the
remaining scenes hold period 2. The selected cohort is Wayne metal parts.
The controls show paused playback, UI scale 1, and reduced motion off.

| Resolution | Scene | Windows | Median FPS | Frame median, ms | Window p95 median, ms |
| --- | --- | ---: | ---: | ---: | ---: |
| 1366×768 | Circuit 3D, Flow | 1 | 59.780 | 16.7240 | 17.5940 |
| 1920×1080 | Circuit 3D, Flow | 3 | 59.940 | 16.6730 | 17.4440 |
| 1920×1080 | Circuit 2D, Flow | 2 | 59.840 | 16.6605 | 19.2865 |
| 1366×768 | Circuit 2D, Flow | 3 | 59.790 | 16.7340 | 18.1410 |
| 1366×768 | Circuit 2D, held History | 2 | 59.790 | 16.7380 | 18.4095 |
| 1920×1080 | Circuit 2D, held History | 2 | 59.940 | 16.6695 | 18.2805 |
| 1920×1080 | Circuit 3D, held History | 3 | 59.940 | 16.6520 | 18.2320 |
| 1366×768 | Circuit 3D, held History | 3 | 59.360 | 16.7380 | 19.2420 |
| 1366×768 | World | 2 | 59.790 | 16.7395 | 18.2110 |
| 1920×1080 | World | 3 | 59.940 | 16.6870 | 17.7450 |
| 1920×1080 | World, Archive | 2 | 59.940 | 16.6695 | 18.1185 |
| 1366×768 | World, Archive | 3 | 59.800 | 16.7210 | 17.6670 |
| 1920×1080 | Restricted Circuit | 2 | 59.935 | 16.6675 | 18.0440 |
| 1366×768 | Restricted Circuit | 2 | 59.790 | 16.7130 | 17.4735 |

These are medians of window statistics, not pooled frame percentiles or a general
hardware guarantee. A mislabeled interval remains retained and excluded. The
sampler intentionally suppresses comparison overlays, so both comparison
intervals have no FPS result. The native inspection covered their content and controls.

After the heavy gates, authenticated held-period-2 History reads completed in
**3.226 seconds at 1366×768** and **3.482 seconds at 1920×1080**. Both returned
three points. Captures show their populated charts. A period-1 read took
2.814 seconds and a live-period-3 read took 3.874 seconds.

This data latency is separate from rendering. The earlier 65.6-second capture interval below is an
observation bound, not a comparable query duration. These results give no speedup ratio.

Broader fog-safe player decisions, earned investigation facts, executable player
actions, universal organizational struggle, payments, recurring demand, and
household consumption remain unfinished. The organizer exercise is explicitly
a [design fixture](../design/organizer-workplace/README.md). This acceptance does
not qualify a release or give merge permission.

## Historical source and evidence boundary

The baseline executable source is
`a0fcb0a515cc1e66e0d39b2ece4076530d9ddce6`. The build record identifies
`codex/PER-293-observer-qualification` and guidance-only checkout differences.
Rust and captured content match that source. The later History and comparison
repairs must pass their own final-source checks.

- Client SHA-256: `71a166e7f33d4d6603baa7765829d7518b1aa6f478893a19605b20d5ad279c91`.
- Runtime SHA-256: `a4342d40f00334dddcde269c18483c113809e413c2608c446cead925615d5b68`.

[Build provenance](test-results/per293-observer/native/build-provenance.json)
also pins authored defines and statewide source, qualification and physical
input files. These are debug binaries, not a newly published release.

[Campaign preparation](test-results/per293-observer/campaigns.json) and its
per-campaign protocol/runtime logs keep foundation, content and envelope
identities. [Tool provenance](test-results/per293-observer/tooling/native-window/provenance.json)
records reused helpers from the earlier PER-330 worktree and their adaptations.
Reusing those helpers does not reuse the earlier run's qualification result.

The baseline frame record has capture time `2026-09-13T02:11:06.746764Z`.
It pins the first 147,413 bytes / 381 complete lines of `logs/native-launch.log`
with SHA-256 `8839f374790df7cd05e403d76d555c805f419da745230e3cecaa43e97c96841b`.
Frame-record SHA-256: `c0145e414c321056a45abb7bc859b863bd07ece94987e3bb02f4ddd519e0f09e`.

The [visibility check](test-results/per293-observer/native/frame-evidence-before-repair-visible-scenes.json)
adds explicit menu, splash and comparison state to each group. All stable
samples have these three states closed. Counts and measurements match the
original record. Its SHA-256 is
`6ed1a0c9a2ab42de4cb07616432a78c1a0cd82fcf0813ae3a02f3388d17e35d5`.

All linked `test-results/per293-observer/` artifacts are local retained evidence.
The repository and public PR do not contain these files. Their relative links
refer to this checkout's evidence directory.

The [canonical observer guide](../docs/how-to/debug-simulation-outcomes.rst)
defines the inspection steps and the expected economic landmarks. Earlier PRs,
experiments and native reports remain historical evidence. They do not certify
these campaigns or the repaired source.

## Retained campaigns and completed observations

The runtime created all four campaigns with the baseline source and committed
each through period 5. It reopened each campaign without a native UI and recorded
a successful restart check. Their preparation-time Archive `processed_tick`
was 1. This is separate from durability.
The later baseline native session reached Archive processed period 5.

| Preset | Retained campaign UUID | Baseline native coverage |
| --- | --- | --- |
| `statewide-baseline` | `3f3200d1-7666-4fba-bb73-77f323c2313b` | Session observations below at both resolutions |
| `statewide-freight-constraint` | `1fd25e5e-613e-40b4-90a5-3d3175442752` | Comparison from baseline at period 3. Its own native Open/resume remains pending |
| `statewide-packaging-shortage` | `98558449-e3f5-476d-8010-4ffe1df9773f` | Headless preparation/restart only. Native session pending |
| `statewide-both` | `509b9708-33d1-483a-9da0-702022ebfdab` | Headless preparation/restart only. Native session pending |

The retained baseline observations show the following bounded results.

| Resolution / scene | Observed result | Capture evidence under `test-results/per293-observer/native/` |
| --- | --- | --- |
| 1366×768, World / period 5 | 397 cohorts, 83 counties and 813/813 commodity links. County and cohort selection lead to Circuit | `1366-baseline-world-live.png`, `1366-chippewa-selected.png`, `1366-chippewa-circuit-live.png` |
| 1366×768, Chippewa Circuit / held period 3 | Household wares show 8 items, 3 employed / 9 reserve, and Flow, Work and Sources readings. Durable period remains 5 | `1366-chippewa-period3-flow.png`, `1366-chippewa-period3-work.png`, `1366-chippewa-period3-sources-flat.png` |
| 1366×768, History | Chart eventually shows unavailable foundation receipts, period-2 zero and period-3 output 8. Captures show 3D and 2D views | `1366-chippewa-period3-history.png`, `1366-chippewa-period3-history-settled.png`, `1366-chippewa-period3-flat-history.png` |
| 1366×768, saved comparison / period 3 | Baseline and freight campaign IDs and matching period are visible. Totals show 3,872 / 3,867 employed and 2,884 / 2,889 reserve. Freight details precede the selected cohort and scrolling removes Close | `1366-baseline-freight-period3-comparison.png`, `1366-baseline-freight-period3-bridge.png`, `1366-after-comparison-escape.png` |
| 1920×1080, World and Circuit / held period 3 | Selected Chippewa network and 3D/2D History remain visible with durable period 5 | `1920-chippewa-world-history3.png`, `1920-chippewa-period3-history.png`, `1920-chippewa-period3-flat-history.png` |
| 1920×1080, Archive / held period 3 | County dossier reports content published at period 1, verified through period 3, with durable period 5. Expanded QCEW source citations and place links are visible | `1920-chippewa-period3-archive.png`, `1920-chippewa-period3-archive-evidence-expanded.png` |
| 1920×1080, restricted preview / held period 3 | Economic network and Circuit relationships are unavailable. Public QCEW observations remain in the cited county dossier | `1920-known-preview-history3.png`, `1920-known-preview-circuit.png` |

Session/presentation logs also keep the restricted Circuit state at 1366×768.
The baseline session closes with `failed=false`, viewed period 3, durable period 5
and Archive processed period 5. That close is not a native resume qualification
of all four campaigns. The baseline comparison captures do not yet show a
usable selected-cohort 8-versus-1 inspection sequence.

## Frame behavior and data latency

[Frame evidence](test-results/per293-observer/native/frame-evidence-before-repair.json)
contains 264 complete windows of 300 frames: 257 stable-context windows
(77,100 frames) and seven transition windows (2,100 frames). The table preserves
each stable group separately. `g` is its zero-based JSON `groups` index. Values
are medians of the recorded 300-frame-window statistics, rounded for display.
**The window-p95 median is not a pooled frame-time p95.**

All listed samples use the retained baseline campaign, durable period 5, paused
playback, UI scale 1 and reduced motion off. Except for the Wayne row, the county
is Chippewa. Full-observer perspective applies unless marked restricted.
Session `Ready` and stable presentation context do not prove that every
asynchronous chart read has completed.

| g | Resolution | Scene / viewed period | Windows | Median FPS | Median frame median, ms | Median window p95, ms |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 13 | 1366×768 | World, Wayne / 5 | 26 | 59.790 | 16.7130 | 18.4155 |
| 11 | 1366×768 | World, Chippewa / 5 | 12 | 59.790 | 16.7320 | 17.7095 |
| 10 | 1366×768 | Circuit 3D / 5 | 5 | 59.780 | 16.7240 | 18.1140 |
| 15 | 1366×768 | Circuit 3D, History / 5 | 7 | 59.790 | 16.7100 | 18.4920 |
| 9 | 1366×768 | Circuit 3D / 3 | 1 | 59.780 | 16.7220 | 17.7930 |
| 14 | 1366×768 | Circuit 3D, History / 3 | 18 | 59.790 | 16.7280 | 18.5315 |
| 19 | 1366×768 | Circuit 3D, Flow reading / 3 | 30 | 59.790 | 16.7210 | 18.1895 |
| 22 | 1366×768 | Circuit 3D, Work reading / 3 | 19 | 59.790 | 16.7250 | 18.2470 |
| 21 | 1366×768 | Circuit 3D, Sources reading / 3 | 9 | 59.790 | 16.7190 | 18.4310 |
| 20 | 1366×768 | Circuit 2D, Sources reading / 3 | 14 | 59.790 | 16.7270 | 18.0740 |
| 17 | 1366×768 | Circuit 2D, History / 3 | 13 | 59.780 | 16.7230 | 18.6690 |
| 8 | 1366×768 | Restricted Circuit / 3 | 4 | 59.795 | 16.7230 | 17.8115 |
| 12 | 1920×1080 | World, selected cohort / 3 | 10 | 59.940 | 16.6795 | 17.9750 |
| 18 | 1920×1080 | Circuit 3D, History / 3 | 34 | 59.940 | 16.6680 | 18.3450 |
| 16 | 1920×1080 | Circuit 2D, History / 3 | 11 | 59.930 | 16.6700 | 18.7780 |
| 24 | 1920×1080 | World, Archive / 3 | 36 | 59.940 | 16.6815 | 17.8215 |
| 23 | 1920×1080 | Restricted World, Archive / 3 | 6 | 59.940 | 16.6860 | 17.7390 |
| 7 | 1920×1080 | Restricted Circuit / 3 | 2 | 59.935 | 16.6945 | 17.9275 |

The table excludes seven windows with a transition or a non-Ready frame.
They remain in groups 0–6. No group is a dedicated comparison-panel benchmark.
These results bound rendering observations on this host. They do not prove
universal 60-FPS performance or resolve an older run's slowdown.

History data readiness was materially slower than drawing frames. The following
times use UTC on 2026-09-13. Held period 3 first became Ready at **01:45:34.771**.
Its chart still showed “Reading committed periods...” at **01:45:42.381**.
It displayed the data by **01:46:40.365**.

Completion lies between the latter two observations.
Approximately 65.6 seconds separate Ready from the populated
capture. This is an upper observation bound, not an exact load duration. The log
separately measures that period's authenticated observation read at
4,395,610 microseconds. Neither measurement is a frame-time percentile.

## Completed checks during the repairs

These logs record checks during repair work. They do not replace the pending
checks on the final source and executable.

| Scope | Result | Local evidence |
| --- | --- | --- |
| Comparison | RED: four added tests failed and 14 passed before implementation. GREEN: all 18 passed after the repair | [RED](test-results/per293-observer/logs/comparison-red.log), [GREEN](test-results/per293-observer/logs/comparison-green-2.log) |
| Client History | All 27 tests passed | [Client log](test-results/per293-observer/logs/client-history-green.log) |
| Persistence reader unit tests | All six tests passed | [Reader unit log](test-results/per293-observer/logs/reader-unit-green.log) |
| Postgres production history | All three tests passed in 244.60 seconds. Fresh bootstrap took 83 seconds. Cleanup checks passed with final status 0 | [Production history log](test-results/per293-observer/logs/postgres-history-green.log) |
| Postgres harness partition | The reader test rejected the missing separate history phase before the repair. All 67 harness tests passed after the repair | [RED](test-results/per293-observer/logs/history-harness-red.log), [GREEN](test-results/per293-observer/logs/history-harness-green-2.log) |
| Actual statewide Postgres campaigns | All four presets passed 16 persisted periods each, including replay, restart, held reads and restricted preview. The test took 1,268.30 seconds. Cleanup completed with status 0 | [Statewide qualification log](test-results/per293-observer/logs/postgres-statewide-qualified.log) |

The comparison regressions cover section selection, selection-first ordering,
same-period and visibility refusal, and controls outside the reading that scrolls.
The production-history tests cover exact snapshots and reopen, corruption before
the displayed suffix, and preview refusal without campaign or target disclosure.

The [original full reader run](test-results/per293-observer/logs/postgres-reader-green.log)
did not pass despite its log filename. Its five role tests passed in 296.06 seconds.
The material phase recorded 16 of 17 passes before its 600-second timeout,
which returned status 124. Its cleanup checks passed. The separate production-history
run completed all three history tests, but does not make the earlier full run green.

The statewide qualification ran before maintenance integration. Each campaign
reopened after changes to, and removal of, its copied authoring sources.
The run used `BABYLON_POSTGRES_LIVE_FOCUS=statewide_qualified mise run test:rust-postgres`.
Fresh bootstrap took 91 seconds, and the complete harness took 1,371 seconds.
It verified removal of its own container and volume.

The retained native campaigns use a different database and remain intact.
Later material encodings and maintenance
content still need their own qualification.

The qualified `observer_material_live` executable had SHA-256
`e5aec1cc2b5d94975e9b04217c079ca17c0d5590818e271d253d83d47e77fa5b`.

## Observer repair snapshot before the input pause

This section adds native evidence for the repaired observer build. It leaves the
original baseline evidence above intact. Campaign labels here refer to the four
exact IDs in the retained-campaign table. That table describes baseline coverage.

[Repair build provenance](test-results/per293-observer/native/final-observer-build-provenance.json)
records the build at `2026-09-13T03:17:03.727409Z`, based on
`41844cf72a29e8b9a588696cc25d24b216b88ea3` with local observer repairs.
It pins individual source files and captured inputs, including the later scrolling
and output-quantity corrections.

- Tracked Rust patch SHA-256: `0e7b451abe77e5a95eba95298762976399e8b50c2ba6542456e83797f88cefc6`.
- Client SHA-256: `0e9d28fe9c6a617649ff913b233ab2ba9ed2e4665fd4a2dd66d08baf7b296242`.
- Runtime SHA-256: `095628307a50b6e66e715fa2f52fb5451a6cd74250e0cce115d2c83d10d80f6c`.

This snapshot precedes the music expansion. It does not qualify a later executable
or replace the pending final commit and publication checks.

The [native log](test-results/per293-observer/logs/native-final.log) records all four
campaigns reaching Ready at viewed and durable period 5. The baseline opened in a
fresh native process. Its Connecting state began at `03:17:21.562478` UTC.
The other rows show native campaign switches and reopen, not separate process starts.

| Campaign | First Ready at period 5, UTC on 2026-09-13 |
| --- | --- |
| Baseline | `03:17:46.899775` |
| Freight | `03:34:43.270240` |
| Both | `03:37:35.971488` |
| Packaging | `03:40:36.384232` |

### Completed native inspections in this snapshot

The table records visible readings and their scope. Merchant screenshots show no
campaign name or UUID. Their campaign identity comes from the joined session and
presentation log. Filenames alone do not prove either campaign or selected cohort.
Capture names below refer to the local `test-results/per293-observer/native/` directory.

| Campaign / comparison | Resolution and observed result | Capture evidence |
| --- | --- | --- |
| Baseline CURRENT / Freight COMPARED, period 3 | Both resolutions put selected Chippewa household wares first: 8 / 1 items produced and 3 / 1 employed. Page Down reveals later cohorts with Close and section controls fixed | `1366-final-comparison-cohorts3.png`, `1366-final-comparison-page-down.png`, `1920-final-comparison-cohorts3.png`, `1920-final-comparison-scrolled.png` |
| Freight CURRENT / Baseline COMPARED, period 1 | 1366×768 Shared freight shows Mackinac Bridge reservations of 709 / 2,207 kg. Opening capacity is 1,000 / 100,000 kg, with 291 / 97,793 kg remaining | `1366-final-freight-baseline-bridge1.png` |
| Freight CURRENT / Both COMPARED, period 1 | 1366×768 Mackinac food shows 1,600 / 800 kg produced, from 16 / 8 completed batches at 100 kg per batch. **The filename incorrectly suggests a baseline comparison** | `1366-final-freight-base-food1.png` |
| Both CURRENT / Baseline COMPARED, period 3 | 1920×1080 Mackinac food shows 100 / 300 kg produced and 1 / 1 employed | `1920-final-both-baseline-food3.png` |
| Baseline History | 1366×768 period 5 shows unavailable foundation receipts, then 16, 0, 8, 0, 0 items. The 1920×1080 flat view at period 3 shows the corresponding prefix | `1366-final-chippewa-history5-ready.png`, `1920-final-flat-history3-verified.png` |
| Packaging food History | 1366×768 period 5 shows unavailable foundation receipts, then 800, 0, 400, 300, 200 kg produced across periods 1–5 | `1366-final-packaging-food5.png` |
| Packaging food, period 3 | 1366×768 Flow, Work and Sources show 400 kg, four batches and 1 employed + 11 reserve. Work uses 160 of 160 hours. The Designed recipe stays separate from Observed QCEW values | `1366-final-packaging-food-flow3.png`, `1366-final-packaging-food-work3.png`, `1366-final-packaging-food-sources3.png` |
| Packaging Mackinac wholesaler, period 3 | 1366×768 food stock opens at 160 kg, receives 400 locally, transfers 160 and closes at 400. Work shows 24 employed, 0 reserve and 3,360 used + 480 unused = 3,840 hours | `1366-final-wholesale-flow3-verified.png`, `1366-final-wholesale-work3.png` |
| Packaging Mackinac retailer, period 3 | Both resolutions show 6,400 kg ordered, zero fulfilled and 6,400 outstanding for each displayed good. The larger capture shows closing food stock of 800 kg and mineral feedstock/logs of 2,880 kg each | `1366-final-retail-flow3.png`, `1920-final-retail-flow3.png` |
| Packaging Mackinac retailer, period 5 | 1920×1080 food demand shows 6,400 kg ordered, 1,200 fulfilled and 5,200 outstanding. Work shows 24 employed + 0 reserve and 3,773 used + 67 unused = 3,840 hours. Both captures show Archive verified for period 5 | `1920-final-retail-flow5.png`, `1920-final-retail-work5.png` |
| Baseline Archive, held period 3 / durable 5 | 1920×1080 Chippewa County and `Sault Ste. Marie` city citations show content published at period 1 and current verification through period 3 | `1920-final-county-citations3.png`, `1920-final-place-citations3.png` |
| Baseline restricted preview, held period 3 / durable 5 | 1920×1080 World hides the economy network while public QCEW and four place links remain visible. Circuit at both resolutions explicitly discloses no production relationships | `1920-final-known-world3.png`, `1920-final-known-circuit3.png`, `1366-final-known-circuit3.png` |

The food Flow account at period 3 keeps the packaging shortage visible:
45 kg opened + 27 arrived = 40 consumed + 32 closed. Sources gives the Designed
100 kg batch recipe: 10 kg paper, 20 kg animal products, 60 kg grain and 10 kg water.
The retail Flow text distinguishes fulfillment from consumption. Work distinguishes
modeled people and hours from observed QCEW jobs and records no wage payments.

County citations name `qcew-county-economics-v1` and its county CSV fields.
Place citations name `census-place-authority-v1`, GEOID `2671740` and county `26033`.
The original place publication records `place/2671740` and `verified_tick 1`.
That original record remains distinct from the displayed verification through period 3.

The settled period-5 retail files have these SHA-256 hashes. These bytes show
Archive verified for period 5, superseding an earlier inspection of those filenames.

- `1920-final-retail-flow5.png`: `f77a1d14f17795be75565a2fb3a5025879b88eec5d07c1402e0424e0a5fa92eb`.
- `1920-final-retail-work5.png`: `f213f7ce6e55aa33905b40c4e6952e6c8067f92b9e3d21cdf40869b367116c7e`.

### Frame observations before the input pause

[The frozen frame record](test-results/per293-observer/native/frame-evidence-final-before-input-pause.json)
has capture time `2026-09-13T03:50:02.427724Z`. It pins 175,076 bytes and
468 complete lines of `native-final.log`. No incomplete final line was present.

- Log prefix SHA-256: `e6d92b697ff0eac646a2c4751686756a66963a06cc81dad3722fac11183695b6`.
- Frame-record SHA-256: `e0931303967ff73ad59ca7c4779fe1e1e1c75b871758503a57588e0cfebb5576`.

The record has 122 complete 300-frame windows. Of these, 111 windows have stable
Ready context, totaling 33,300 frames. The other 11 windows total 3,300 frames
and remain in groups 0–9 and 21. The table preserves each stable group separately.
Values are medians of 300-frame-window statistics. **These are not pooled frame percentiles.**

All stable samples have durable period 5, paused playback, UI scale 1 and reduced
motion off. All these samples have the menu, splash and comparison closed.
Full-observer perspective applies except for group 12. Food and merchant rows
refer to Mackinac. A selected site or open History panel does not prove completed
data loading or a completed economic comparison.

| g | Campaign | Resolution | Scene / viewed period | Windows | Median FPS | Median frame median, ms | Median window p95, ms |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 10 | Freight | 1366×768 | World, Mackinac / 5 | 5 | 59.780 | 16.7270 | 18.0800 |
| 11 | Freight | 1366×768 | Circuit 2D, food History / 1 | 4 | 59.780 | 16.7195 | 18.6205 |
| 12 | Baseline | 1366×768 | Restricted Circuit 2D, Chippewa / 3 | 10 | 59.790 | 16.7180 | 17.6075 |
| 13 | Baseline | 1920×1080 | Circuit 3D, Chippewa / 3 | 4 | 59.940 | 16.6820 | 17.5760 |
| 14 | Baseline | 1366×768 | Circuit 3D, Chippewa / 5 | 5 | 59.780 | 16.7240 | 17.7340 |
| 15 | Baseline | 1366×768 | World, Wayne / 5 | 3 | 59.790 | 16.7240 | 17.6820 |
| 16 | Baseline | 1920×1080 | Circuit 2D, Chippewa History / 3 | 4 | 59.920 | 16.6990 | 18.0785 |
| 17 | Baseline | 1920×1080 | Circuit 3D, Chippewa History / 3 | 11 | 59.940 | 16.6820 | 18.0500 |
| 18 | Baseline | 1366×768 | Circuit 3D, Chippewa History / 5 | 12 | 59.790 | 16.7150 | 18.2930 |
| 19 | Both | 1366×768 | World, Clare, History open / 5 | 5 | 59.330 | 16.7490 | 19.2550 |
| 20 | Both | 1366×768 | Circuit 2D, food History / 3 | 4 | 59.780 | 16.7305 | 18.4950 |
| 22 | Packaging | 1366×768 | Circuit 2D, food selected / 3 | 5 | 59.790 | 16.7220 | 17.6290 |
| 23 | Packaging | 1366×768 | World, Monroe / 5 | 4 | 59.790 | 16.7215 | 17.7845 |
| 24 | Packaging | 1366×768 | World, Wayne / 5 | 4 | 59.795 | 16.7420 | 18.1975 |
| 25 | Packaging | 1366×768 | Circuit 2D, food History / 5 | 4 | 59.780 | 16.7130 | 18.9965 |
| 26 | Packaging | 1366×768 | Circuit 2D, Wayne History / 3 | 4 | 59.585 | 16.7255 | 18.2160 |
| 27 | Packaging | 1920×1080 | Circuit 2D, retail Flow / 3 | 3 | 59.940 | 16.6870 | 18.3260 |
| 28 | Packaging | 1366×768 | Circuit 2D, food Flow / 3 | 5 | 59.790 | 16.7200 | 18.0480 |
| 29 | Packaging | 1366×768 | Circuit 2D, wholesale Flow / 3 | 2 | 59.790 | 16.7245 | 17.9270 |
| 30 | Baseline | 1920×1080 | World, Chippewa Archive / 3 | 13 | 59.940 | 16.6760 | 17.6350 |

These samples give no separate comparison-panel benchmark. The latest session
in the prefix is Packaging, viewed period 3, durable period 5, Ready and
`failed=false`, with Archive processed through period 5. The last presentation
has the menu open. Native input stopped after keyboard/focus guards reported
active desktop use, which the Director confirmed. This record makes no performance
claim after the pinned prefix. Native interaction stays paused while the Director
uses the desktop.

### Completed History reads in the repair snapshot

The frozen log prefix records the following successful authenticated History reads.
Durations measure the logged read operation, not whole-screen loading or frame time.
Times use UTC on 2026-09-13. Site prefixes identify the full site IDs in the log.

| Completion UTC | Campaign | Period | Site prefix | Read duration, microseconds | Points |
| --- | --- | ---: | --- | ---: | ---: |
| 03:20:37.193785 | Baseline | 5 | `24471c46` | 4,556,760 | 6 |
| 03:21:44.840159 | Baseline | 3 | `24471c46` | 3,929,934 | 4 |
| 03:35:37.877928 | Freight | 5 | `44de7115` | 4,898,201 | 6 |
| 03:35:46.053726 | Freight | 1 | `44de7115` | 2,787,565 | 2 |
| 03:38:14.884745 | Both | 5 | `01654aac` | 4,804,212 | 6 |
| 03:38:48.286270 | Both | 5 | `44de7115` | 5,505,137 | 6 |
| 03:38:56.857801 | Both | 3 | `44de7115` | 3,676,330 | 4 |
| 03:40:45.313524 | Packaging | 5 | `01654aac` | 5,186,682 | 6 |
| 03:40:47.744455 | Packaging | 5 | `44de7115` | 5,291,603 | 6 |
| 03:41:20.188473 | Packaging | 3 | `44de7115` | 3,684,739 | 4 |
| 03:48:48.580775 | Packaging | 5 | `4d6325c9` | 4,947,957 | 6 |
| 03:48:57.219590 | Packaging | 3 | `4d6325c9` | 3,684,718 | 4 |

The baseline period-5 History query appears at `03:20:32.636568` and completes
at `03:20:37.193785`. At held period 3, Ready appears at `03:21:40.945591` and
the History read completes at `03:21:44.840159`. These service completions and the
populated captures above supply different evidence from the initial baseline's
bounded observation interval. Neither converts that earlier interval into an
exact load duration.

## Pending final-source qualification

The observer repair snapshot completes only the checks identified above.
Keep the following acceptance work open. Preserve both native evidence sets.

**Final source: pending.** Record the final commit, clean/dirty source
disposition, client/runtime hashes, and any changed captured-content identities.
Qualify later source and the music expansion against their own executable bytes.

**Final qualification: pending.** Record the applicable final format, test,
Clippy and repository checks against the final source. The broader Postgres
reader and publication gates remain open. Keep the earlier repair results separate.

**Comparison checks: partial.** Both resolutions now show selected-cohort-first
comparison and fixed controls through scrolling. The captured bridge and food
comparisons cover only their stated campaigns and periods. Complete the unaffected
Wayne comparison and the full Chippewa / period-2 matrix. Keep complete freight
and totals access, same-period identity, units and missing-versus-zero/fog checks
in the final acceptance pass.

**History checks: partial.** The repair snapshot has 12 successful timed reads,
populated charts and separately grouped frame observations. Later source still
needs its own checks. Preserve the foundation/zero distinction and transition samples.

**Campaign coverage: partial.** All four retained campaigns now have native
Open/reopen evidence at period 5. The baseline also has a fresh-process start.
The final baseline advance to period 6 and fresh restart afterward remain pending.
Complete the remaining economic matrix, unaffected chain, workforce conservation
and exact saved-comparison coverage before claiming all four campaigns qualified.

**Restricted and Archive checks: partial.** The repair snapshot shows county/place
citations and restricted World at 1920×1080, plus restricted Circuit at both
resolutions. Keep publication, verification and durable periods separate.
Complete any remaining final-source coverage against the canonical guide.

**Broader acceptance: open.** These bounded observations do not prove full
Gate 3 / Gate 4 acceptance or complete the parent issues. Keep any later human
comprehension feedback separately from the executable and native checks above.
