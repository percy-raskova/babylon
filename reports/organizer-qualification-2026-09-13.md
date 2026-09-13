# Wayne organizer qualification — 13 September 2026

The bounded native Wayne organizer implementation connects player rulings to
saved practices, earned workplace reports and later cooperation under
[ADR262](../ai/decisions/ADR262_native_organizer_practice.yaml). The organizer
model and final Postgres organizer, reader, statewide and maintenance checks passed.
Client tests, format and Clippy also passed.

The 1366×768 route and fresh completed restart have native evidence.
The 1920×1080 route reached
period 7 and passed its fresh completed restart. Both resolutions have scoped
performance measurements. Native acceptance covers the recorded builds and
checks below. Publication **remains pending**.

This delivery is **Part of PER-9, PER-26 and PER-56**, from `dev`
`6c0db910115177e37ce3b6a49dff90c1efffef11`. Broader acceptance for those issues,
PER-27, PER-331/PER-332, G3/G4 and universal organizational struggle stays open.
This record makes no claim about current Linear status or merge approval.

## Verified model and persistence results

Links under `test-results/per9-organizer/` point to local, ignored evidence.
A public checkout does not necessarily include those files.

| Boundary | Passed result | Evidence |
| --- | --- | --- |
| Organizer model | **20 tests** cover distinct practices and costs, routine substitution, Pause/Resume, contact expiry and recovery. They also cover consumer removal, partner refusal and capacity, nonce and authority, replay, shared contributors and player/policy parity. Equal lawful knowledge gives equal previews and safe refusals across different hidden states. | [Model log](test-results/per9-organizer/logs/organizer-coverage-green.log), [contracts](../rust/crates/babylon-practice-contract/tests/organizer.rs) |
| Final organizer Postgres | The `organizer` focus passed **16 periods in 546.49 seconds**. Coverage includes durable admission, rollback, historical knowledge, later cooperation and the campaign horizon. Altered metadata causes refusal in the direct Archive producer, restart and failed-tick paths. | [Final organizer log](test-results/per9-organizer/logs/organizer-projection-live-green.log) |
| Final statewide and maintenance Postgres | The `statewide_qualified` focus passed **both connected tests in 1,804.51 seconds**. Four statewide campaigns ran through 16 periods. Four maintenance campaigns ran through three periods. The checks preserve freight/packaging comparisons, independent labor/parts constraints, whole-job accounting, delayed output, recovery, replay, rollback and restart. | [Final economic log](test-results/per9-organizer/logs/statewide-final-live-2.log) |
| Final restricted reader | The `reader` focus passed **23 tests**: five role checks, 14 observer cases, three production-history cases and one synthetic statewide campaign. They cover protocol 4, confined authority, historical disclosure, corruption refusal, Archive freshness, interrupted processes, shared freight and restart. | [Final reader log](test-results/per9-organizer/logs/reader-final-live.log) |
| Archive integrity regression | Live RED reached its intended assertion in **93.05 seconds**. Altered SQL metadata passed authentication while encoded bytes stayed unchanged. The repair checks the requested committed period and all subject, observation and receipt metadata in one repeatable-read transaction. **Two focused tests**, format and persistence Clippy passed. The final organizer Postgres run above also passed. | [Live RED](test-results/per9-organizer/logs/organizer-projection-live-red-2.log), [focused GREEN](test-results/per9-organizer/logs/archive-projection-scoped-green.log) |
| History review regression | Valid RED: **40 passed, 2 intended failures**. GREEN: **42 passed**. A history visit invalidates the review while preserving drafts and accepted commitments. Returning Live needs a fresh review. | [RED](test-results/per9-organizer/logs/history-preview-red-2.log), [GREEN](test-results/per9-organizer/logs/history-preview-green.log) |
| Draft evidence and resolving regressions | Valid RED: **18 passed, 6 intended failures**. These cover saved references, access limits, format refusal, persistent save warnings and distinct resolving feedback. The final client run below passes the repaired behaviors. | [RED](test-results/per9-organizer/logs/evidence-resolving-red-2.log) |
| Client before readability change | **392 library tests passed**, with no failures or ignored tests. Format and all-target client Clippy passed. The native checks below cover the recorded builds. | [Final tests](test-results/per9-organizer/logs/client-final-green-2.log), [format and Clippy](test-results/per9-organizer/logs/client-final-clippy.log) |
| UI readability | Valid RED: **one intended failure**, because Full HD used 100% scale instead of 125%. The full GREEN run passed **393 library tests**. After exact float-identity cleanup, the final focused test and all-target client Clippy passed. The native build completed in **85 seconds**. | [RED](test-results/per9-organizer/logs/client-readable-scale-red-2.log), [full GREEN](test-results/per9-organizer/logs/client-readable-scale-green.log), [final focused test](test-results/per9-organizer/logs/client-readable-scale-final-green.log), [final Clippy](test-results/per9-organizer/logs/client-readable-scale-clippy-2.log), [build](test-results/per9-organizer/logs/native-readable-build.log) |
| Grammar and certification | The derived tree-sitter corpus passed **35/35 parses**. Graph-only SFS contracts passed **30 tests**. That certification excludes material and organizer operations. | [Grammar](test-results/per9-organizer/logs/derived-grammar-green.log), [SFS](test-results/per9-organizer/logs/sfs-source-identity-green.log) |

All three final Postgres harness runs confirmed unchanged templates and zero
scratch clones. Each cleaned up its owned container and volume. The organizer
harness exited 0 after 707 seconds. The economic harness exited 0 after
1,900 seconds. The reader harness exited 0 after 1,471 seconds.

The [tick contracts](../rust/crates/babylon-tick/tests/organizer_replay.rs) compare
Inquiry, Reinforce, Hold and Pause from the same maintenance state. Their costs
are **12/8/8/0**. Organizer receipts and world identities differ, while physical
material state and material receipts stay equal. A failed commit preserves the
graph, material register, events, world hash and accepted input. A retry produces
the same candidate identity.

## Playable scope and causal limits

The normal menu offers **Organize in Wayne**. Its native workspace controls the
Designed Wayne Organizing Collective. The workplace committee and neighborhood
contact group have independent authority, permissions and participant
commitments. These fictional groups do not represent observed organizations or
the whole industrial workforce. The [player guide](../docs/how-to/organize-in-wayne.rst)
describes the route.

The collective supplies **16 organizer-hours per period**. Inquiry uses 12 hours
and contact uses 8. A participating partner uses 2 of its own 8 hours. The shared
allocator prevents contributors from supplying the same hours twice. Unused
hours expire.

Inquiry seeks one workplace work/output or maintenance report. Reinforce
performs workplace contact. Hold continues the authorized neighborhood routine.
Pause persists until explicit Resume, which uses 8 hours and performs that
routine. A specific commitment replaces standing work for one period. Failed
admission leaves the routine in place.

Admission binds authority, campaign, committed period, content, resources and
nonce. Persistence precedes acknowledgement. The next 28-day BSL tick resolves
accepted practices inside the existing atomic material transaction. Independent
partners control their responses. They cannot replace the player's ruling.

Contact completed in period `T` creates a receipt and product. The following
period must consume that product to renew the same agreement for `T+1` and
`T+2`. This is ADR232's scoped successor. It does not activate solidarity bonuses
or solidarity-funded budgets.

Earned observations carry actor, subject, source, observed period, acquisition
period and receipt identity. The resolving transaction writes observations,
receipts and Archive dirty records before its durable marker. The restricted
inspector and workplace/organization Archive read those records. An inquiry
grants no access to future values or provider-private accounts.

Factory work and recovery follow the maintenance economy. The loop does not
model shift schedules, wage losses or bargaining. Recruitment, strikes,
coalitions and universal faction simulation also stay outside this delivery.

A review belongs to the exact live observation context. Historical inspection
invalidates it. Returning Live preserves the draft, notes and selection but
needs a fresh Review before submission. Accepted commitments stay intact.
During an advancing period, the panel shows **Resolving** without crediting an
outcome. Without a commitment, it distinguishes an authorized routine from a
paused routine.

## Source, formats and preserved evidence

The current implementation uses runtime protocol **4**, captured Michigan
content/defines **5**, material-world register **4** and `OrganizerPracticeV1`.
Unsupported prior formats refuse without changing stored data. This delivery
adds no compatibility shim or save migration. The
[organizer contract](../contracts/organizer_practice_v1.yaml) specifies typed
identity, receipts and knowledge.

Personal drafts use schema **2**, separate from executable commitments. They
store the workplace, choice, notes, observation references and selected
reference. Campaign scope comes from the draft file's identity. Reopening a
reference checks the lawful workplace view again. Hidden, foreign and absent
reports give the same unavailable response. References grant no access or effects.

Unsupported schema-1 draft files stay unchanged. Saving stays disabled for the
refused draft, including on close. The workspace and inspectors keep that
warning visible. New writable drafts mark changes that await a disk save.
A report reference enters the personal draft before the automatic save succeeds.

The [build manifest](test-results/per9-organizer/native/final-source-manifest.json)
records staged tree `76cd4086e3adff398fb52bb0dfe2785165905cb8`, the Rust/content
trees and both binary SHA-256 hashes. This records the staged build snapshot.
The final commit remains pending.

The [readability manifest](test-results/per9-organizer/native/readability-source-manifest.json)
records staged tree `d4285f9f17517d8edcdeaa4ee39a901fc5ceac4b` and its new client
binary. Since the initial native build, only `observer_io.rs` and
`observer_ui.rs` changed. Core mechanics, captured content and the runtime binary
stay unchanged. Automatic scale is **100% at 1366×768** and **125% at 1920×1080**.
The Larger option multiplies that scale by **1.15**, giving **143.75% at
1920×1080**. The interface rounds its label to **144%**.

The [dependency-equivalence record](test-results/per9-organizer/source-recapture/dependency-equivalence.json)
records the defines schema change and new Designed organizer values.
Preexisting economic parameters stay unchanged. Recapture keeps **397 owners,
233 processes, 581 orders, 233 retail demands, 83 terminals, 7,085 physical edges
and 1,245 capacity groups**. Only the relevant defines pins advance.

This recapture does not rebuild roads, the path matrix or supplier selection.
It makes no claim to have the original matrix bytes. Before/after captures and
prior economic evidence stay available. The final economic regression passed
as recorded above.

The [SFS source audit](test-results/per9-organizer/source-recapture/sfs-audit.json)
records the changed refusal-source fingerprint. Its scope stays graph-only.
Historical ADRs, the HTML design, saves, evidence and unrelated worktrees
remain preserved.

No governed baseline changed in this diff. The
[ceremony gate](../tools/check_baseline_ceremony.py) defines that estate as
`tests/baselines/`. Changes to schema census files, authored-content digests and
SFS source/proof fixtures record the new formats and refusal-source identity.
They do not change preexisting economic parameters or extend SFS certification.

## Native route and restart at 1366×768

Private launches 3 and 4 completed campaign
`6335b309-5179-4953-9a9e-e0c66f170484` through period 8, then quit normally.
They used the client in the initial build manifest. The full action route
predates only the two-file readability change above. Launch 5 used the new
readability build for the completed restart and presentation checks.

| Period | Native result |
| --- | --- |
| 0 | A fresh process reopened pending Hold and preserved the notes `pi draft1366`. [Pending restart](test-results/per9-organizer/native/final-1366-pending-restart.png). |
| 1–2 | Hold spent 8 hours, then routine work spent 8 hours. The workplace reported 0 performed labor-hours versus 960 before. |
| 3 | Maintenance Inquiry spent 12 hours. Its workplace report describes period 2 and acquisition in period 3. |
| 4 | Routine work continued after an incorrect operator click. No accepted Reinforce commitment applied to this close. |
| 5 | Reinforce spent 8 hours and produced mutual contact evidence. Report sharing still showed the initial periods 0–3. [Accepted ruling at period 4](test-results/per9-organizer/native/final-1366-period4-reinforce-accepted.png), [period-5 receipt](test-results/per9-organizer/native/final-1366-contact-receipt.png). |
| 6 | Pause spent 0 hours. The period consumed the prior contact product and renewed sharing for periods 6–7. [Consumed contact](test-results/per9-organizer/native/final-1366-consumed-contact.png). |
| 7–8 | Work Inquiry spent 12 hours while the routine stayed paused. Resume then spent 8 hours and restored authorization. [Period 8](test-results/per9-organizer/native/final-1366-period8-resumed.png). |

The route checked P/I navigation, Tab and PageDown scrolling, citations and
history at period 2 while the durable period was 3. The saved later report
stayed unavailable in that historical view. Return Live cleared the review.

Removing an automatic-report reference removed only the personal reference.
The maintenance reference stayed in the draft. Intermediate capture names
remain preserved, including one named `final-1366-reinforce-accepted.png` that
shows no accepted ruling. The period-5 evidence above shows actual contact.

Launch 5 reopened completed period 8 in a fresh process at 1366×768.
[Workspace](test-results/per9-organizer/native/readable-1366-completed-restart.png),
[receipts](test-results/per9-organizer/native/readable-1366-completed-receipts.png),
[draft](test-results/per9-organizer/native/readable-1366-completed-draft.png) and
[reference](test-results/per9-organizer/native/readable-1366-reference-restart.png)
captures show the restored state. The
[draft check](test-results/per9-organizer/native/1366-completed-restart-draft-check.json)
confirms the same bytes and SHA-256 before and after this restart.

All seven scenes now have quiet intervals on the readability build at 1366×768:
decision, Direction, Relationships, evidence, receipts, Archive and held history.
The [interval log](test-results/per9-organizer/native/performance-intervals.jsonl)
uses labels `1366-readable-{scene}`. The
[held-history capture](test-results/per9-organizer/native/readable-1366-held-history.png)
shows period 7 with durable period 8. The scoped performance summary appears
below.

Native resize checks show the
[125% default](test-results/per9-organizer/native/readable-1920-default.png),
[144% menu](test-results/per9-organizer/native/readable-1920-larger-menu.png),
[keyboard review](test-results/per9-organizer/native/readable-1920-larger-review-keyboard.png)
and [receipts](test-results/per9-organizer/native/readable-1920-larger-receipts.png)
at 1920×1080. The
[restored 1366×768 view](test-results/per9-organizer/native/readable-1366-restored-scale.png)
checks responsive scale. These captures cover wrapping and focus. The
1920×1080 route below uses the readability build.

## Native evidence at 1920×1080

Campaign `3d362635-1f66-4103-ad81-e7ae0ddbdd04` uses the readability build at
125% automatic scale. A fresh process reopened pending Hold at period 0.
The [restart](test-results/per9-organizer/native/final-1920-pending-restart.png)
and [period-1 receipt](test-results/per9-organizer/native/final-1920-hold-receipt.png)
show that Hold spent 8 hours after resolution.

| Period | Verified native result |
| --- | --- |
| 2 | Routine work spent 8 hours. The workplace reported 0 performed labor-hours versus 960 before. |
| 3 | Maintenance Inquiry spent 12 hours. The report describes period 2 and acquisition in period 3. The consumer received 0 enabled, 0 used and 0 expired maintenance. Provider-private accounts stayed withheld. |
| 4 | Reinforce spent 8 hours and the partner participated. Mutual contact completed after the initial report-sharing agreement ended at period 3. The agreement still showed periods 0–3 before product consumption. [Receipt](test-results/per9-organizer/native/final-1920-contact-receipt.png), [agreement](test-results/per9-organizer/native/final-1920-contact-before-consumption.png). |
| 5 | Pause spent 0 hours. The period consumed the period-4 contact product and renewed workplace sharing for periods 5–6. [Consumed contact](test-results/per9-organizer/native/final-1920-consumed-contact.png). |
| 6 | Work Inquiry spent 12 hours. It acquired the period-5 report in period 6, with 0 kg output and 0 performed labor-hours. [Revised evidence](test-results/per9-organizer/native/final-1920-revised-work-evidence.png). |
| 7 | Resume performed 8 hours of standing work and the partner participated. The receipt list contains periods 1–7. [Completed receipts](test-results/per9-organizer/native/final-1920-completed-receipts.png). |

The personal draft kept both the automatic report and earned maintenance
reference, plus notes `pi draft1920`. The route opened the
[Archive](test-results/per9-organizer/native/final-1920-archive.png),
[held period 2](test-results/per9-organizer/native/final-1920-held-period2.png)
while live at period 3, and
[returned Live](test-results/per9-organizer/native/final-1920-live-saved-evidence.png)
with the reference intact and the old review invalidated. Tab and PageDown
reached the [completed receipts](test-results/per9-organizer/native/final-1920-receipts-keyboard.png).

The draft added the work report, then removed the automatic-report reference.
The [automatic report stayed inspectable](test-results/per9-organizer/native/final-1920-reference-removed-knowledge-retained.png).
Before normal Quit at period 7, the draft selected the work reference.
The [pre-restart record](test-results/per9-organizer/native/1920-completed-before-restart.json)
records 519 bytes, the notes, Resume choice and two references.

Launch 7 reopened period 7 with the same readability build. The
[completed restart](test-results/per9-organizer/native/final-1920-completed-restart.png)
shows the authorized routine, `pi draft1920` notes, Resume choice, two references
and no pending commitment. The
[restored receipts](test-results/per9-organizer/native/final-1920-completed-receipts-restart.png)
show period-7 standing work, period-6 Inquiry, period-5 Pause and period-4 contact.
The [selected reference](test-results/per9-organizer/native/final-1920-selected-reference-restart.png)
reopens the work report observed in period 5 and acquired in period 6.

The [draft check](test-results/per9-organizer/native/1920-completed-restart-draft-check.json)
confirms the same 519 bytes and SHA-256 before and after restart. No further
period advanced. The game then closed normally.

## Scoped native performance

The [performance summary](test-results/per9-organizer/native/performance-final.json)
contains 21 accepted intervals. This table selects the seven `1366-readable-*`
intervals and seven current `1920-*` intervals. Each quiet interval lasted
16 seconds on a private X11 display without competing heavy jobs. Only complete
300-frame windows in Ready state with a stable context enter the summary.

Each pair below gives the median of window medians, then the median of window
95th percentiles, in milliseconds. Values round to two decimals. These are
medians of window statistics, not percentiles pooled across all frames. They do
not predict desktop frame rates. The 1366×768 scenes use period 8, with held
period 7. The 1920×1080 scenes use periods 2–4, with held period 2 while live at 3.

| Scene | 1366×768 median pair (ms) | 1920×1080 median pair (ms) | Complete windows (1366 / 1920) |
| --- | --- | --- | --- |
| Decision | 4.63 / 5.62 | 7.25 / 10.32 | 10 / 6 |
| Direction | 4.75 / 5.71 | 7.51 / 10.17 | 9 / 5 |
| Relationships | 4.58 / 5.58 | 7.92 / 11.66 | 9 / 5 |
| Evidence | 4.66 / 5.49 | 7.47 / 10.30 | 10 / 6 |
| Receipts | 5.28 / 7.19 | 8.60 / 12.22 | 8 / 4 |
| Archive | 6.33 / 7.44 | 11.28 / 15.54 | 5 / 4 |
| Held history | 5.42 / 7.42 | 7.40 / 11.14 | 8 / 6 |

The [exclusion record](test-results/per9-organizer/native/performance-exclusions.json)
keeps one operator-overlapped relationships interval out of the results. The
replacement is `1920-relationships-quiet`. Raw intervals remain available.

## Earlier native and publication evidence

The [native handoff](test-results/per9-organizer/tooling/client/native-qualification-handoff.md)
and [launch log](test-results/per9-organizer/logs/native-private-2.log) record a
menu-led run through periods 1–7 after a pending Hold restart. The run exercised
Inquiry, Reinforce, Pause and Resume, citations, held knowledge and period-5
consumption of contact evidence. Notes and selection survived inspection and
the pending restart.

That run mixed **1366×768** and **1920×1080** and predates final client repairs.
It does not qualify either resolution or the final source. The handoff keeps
its scene samples and their limits. The newer 1366×768 route above supplies
separate native evidence.

The [earlier persistence handoff](test-results/per9-organizer/tooling/persistence/qualification-handoff.md)
keeps the isolated 311.50-second organizer run and its source limits. No
standalone stdout log exists for that run. The final organizer harness result
above supplies the current integrated evidence.

Earlier publication results:

| Check | Result and limit | Evidence |
| --- | --- | --- |
| `mise run check` | **2,371 passed, 18 skipped**, one warning. Tests took 61.57 seconds. Skips do not count as passing coverage. | [Python log](test-results/per9-organizer/logs/python-publication-3.log) |
| Integrated Rust | **2,605 passed, 8 failed, 33 skipped**. The exact eight failed tests then all passed. This does not complete final publication. | [Initial log](test-results/per9-organizer/logs/rust-publication-4.log), [exact rerun](test-results/per9-organizer/logs/rust-publication-regressions-green.log) |
| Native-derived regressions | Focused navigation and Pause explanation failed in RED, with 13 other tests passing. GREEN passed **383 client library tests**. The final client result appears above. The native checks below cover the recorded builds. | [RED](test-results/per9-organizer/logs/client-native-regressions-red.log), [GREEN](test-results/per9-organizer/logs/client-native-regressions-green.log) |

## Pending final acceptance

| Required evidence | Work still pending |
| --- | --- |
| Source and binaries | Write the commit identity and tested binary hashes to the post-commit sidecar. Keep both native build manifests. |
| Publication | Run the mandatory pre-push Rust `dev` gate after commit. It includes workspace format/Clippy, selected tests, `cargo test --workspace --doc --locked` and BSL sentinels. Record commands, results and skips in the PR or sidecar. Qualify CI, dependency/security checks and reviews against the final head. Do not build documentation. |
| Delivery | Attach final evidence to the partial PR. Merge approval remains separate. |

No merge forms part of this working qualification.
