# Wayne usability evidence — November 13, 2026

**Fixture-based native matrix and client gates passed.** This report retains
the approved November 13 workstream date; verification continued on November 14
UTC. Human and live-runtime acceptance remain open.

The organizer presents three dated resource chips, shorter choice summaries with
Details, Back and Organizing Home, an interface-only tour, visible processing
feedback and four geographic county colors. Current player help explains the
controls and uses commodity terminology.

Part of PER-336 and PER-292. This bounded result closes no broader player-agency
gate. The [November 6 report](wayne-playtest-followup-2026-11-06.md) and its
images remain unchanged. An uncoached human play session remains pending.

## Native scope and source

The diagnostic provides **fixture-based native rendering** through the real Bevy
renderer, shipped fonts/art, one Winit event loop and saved Screenshot
acknowledgements. Existing organizer fixtures pass current client admission;
the map combines the committed atlas with explicitly authored fixture readings.
It uses a generated campaign identity and fresh XDG presentation directories.
Human saves and preferences are preserved.

Keyboard coverage sends focused Bevy KeyboardInput press/release events through
the normal input dispatcher. Pointer coverage invokes ordinary Interaction
handlers. These are automated inputs, not a human or physical-device playtest.
The diagnostic submits no review, confirmation or period advance to a runtime.

| Item | Result |
| --- | --- |
| Implementation base | `7ccb77323` |
| Native-tested source | Eight source digests in [native manifest](wayne-usability-2026-11-13-assets/native-manifest.json); matrix identity preserved separately from later changes |
| Renderer | llvmpipe (LLVM 19.1.7, 256 bits), Vulkan, CPU; task-owned Xorg `:99` |
| Complete captures | `/tmp/wayne-usability-native-captures-03`, 84 original PNGs; complete hashes, dimensions and visual observations in the manifest |
| Committed images | Representative original PNGs in `wayne-usability-2026-11-13-assets/`; selection below |
| Full matrix | **Passed**: 84 acknowledged PNGs, 1 test passed, 0 failed, 1,002.44 seconds |

## Implementation decisions retained

These decisions bounded the implementation and verification. Their failure
consequences remain explicit after the temporary planning ledger is removed.

| Decision | Reason and boundary | Consequence if wrong |
| --- | --- | --- |
| Reuse the task-isolated checkout; branch from origin/dev | Preserve prepared caches and the sanctioned branch without another worktree | Isolation or source identity could be wrong, contaminating evidence or user changes |
| Economic resources remain presentation over existing authority | Reuse admitted cash/hours; add no labor, volunteer or reservation mechanic | The work would exceed usability scope and require new mechanical/authority validation |
| Assigned implementers own source; controller owns release/review coordination | Follow repository Subagent-Driven Development with explicit ownership | Unreviewed or conflicting edits could be mistaken for an integrated result |
| Permit disjoint palette/HUD work with exclusive paths and serialized Cargo/commits | Make independent progress while deferring shared HUD terminology to its owner | Overlap could corrupt build evidence, lose changes or invalidate fixed review ranges |
| Record accepted routes with a pre-input presentation snapshot; bound history to 128 visits | Coalesce same-frame accepted navigation; retain descriptors, not authority or arbitrary Changed events | Back could replay failed actions, stale data or an obsolete review |
| Wayne uses gold when idle, paper when selected and blue when hovered, plus its label | Keep focus independent of geographic fill without simultaneous extra strokes | Wayne could become ambiguous under selection/hover, requiring a new visual correction |
| Permit new unregistered leaf preparation until explicit integration release | Preserve active compilation/review while preparing later tasks | Early wiring or concurrent Cargo could change the tested source or invalidate task evidence |
| Allow shorter diagnostic pacing when actual schedule/readiness still proves the frame | Four frames traverse input, painting, layout, modal reconciliation and restored scroll; a saved screenshot acknowledgement needs no extra idle frames | A stale view could be captured; retain readiness/dimension assertions and visual inspection, and revert pacing if unstable |
| Add one 263-county Michigan/Indiana/Ohio native fixture capture for all four hues | Michigan itself uses only three assignments; exhaustive contracts already cover national adjacency and admission | Four-hue legibility could remain unproved; this regional raster cannot qualify simultaneous national rendering or a live campaign |

## Player behavior checked

The full changed-crate tests and native observations cover these presentation
boundaries. They do not qualify a runtime transaction or human comprehension.

| Boundary | Result |
| --- | --- |
| Resources | Cash and organizer-hours retain admitted values/units. Household time names its closed period and says next period unknown. Missing/stale disclosure remains unavailable; drafts/review reserve nothing. Native matrix and full contract gate passed. |
| Choice hierarchy and Details | Actual cost, partner, timing, routine replacement and conditional outcome stay visible. Details expands the selected practice; unavailable controls retain reasons. Native matrix and full contract gate passed. |
| Review/Confirm/Advance | Review and Confirm remain separate; Advance stays far right and gold-accented. No runtime transaction is qualified by the fixture diagnostic. Existing review/confirmation contracts passed; native position/accent checked. |
| Back/Home | Real handlers close the top detail or restore the prior view; Home returns live. Drafts, accepted commitments and pending operations remain intact. Current disclosure is reacquired; context changes invalidate review. Native matrix and full contract gate passed. |
| Tour | All seven anchors, Next/Previous, completion, Settings replay, shielding/focus and pause behavior. Native matrix passed; Skip/Escape, preference, unsupported-mode and unchanged-authority contracts passed in the full tests. |
| Processing | Actual operation stage/elapsed time persists through committed organizer refresh; Reduced Motion leaves activity bars still. No percentage or outcome is inferred. Fixture busy/reduced-motion rasters and full contracts passed. |
| Error/refusal | Archive has no configured reader DSN; its ordinary route must report unavailable. The client-error scene is explicitly authored fixture feedback, not a live runtime failure. Both messages observed at all four native fits. |
| Geography/commodities | Neutral county colors, labels/outlines, independent Wayne focus, metric palettes/legends and longer commodity controls. All fits inspected; regional four-hue raster plus palette/map contracts passed. |
| Accessibility/layout | All four fits retain required terms/reasons; real focus/scroll components and keyboard/pointer paths operate. Native matrix and full contract gate passed. |

## Native matrix and visual findings

Standard uses the existing **Automatic** setting. Expected UI scales are
1.0/1.15 at 1366×768 and 1.25/1.4375 at 1920×1080.

| Window | Interface | Resources/choices/details | Seven-step tour/replay | Navigation/inspectors | Neutral/economic/material map | Pending/Reduced Motion/error |
| --- | --- | --- | --- | --- | --- | --- |
| 1366×768 | Standard/Automatic | Pass | Pass | Pass | Pass (Michigan) | Pass |
| 1366×768 | Larger | Pass | Pass | Pass | Pass (Michigan) | Pass |
| 1920×1080 | Standard/Automatic | Pass | Pass | Pass | Pass (Michigan) | Pass |
| 1920×1080 | Larger | Pass | Pass | Pass | Pass (Michigan) | Pass |

The first partial run produced 16 acknowledged 1366×768 images before an invalid
extra Close lookup in the diagnostic stopped it. Actual lens selection already
closes its drawer; the harness now asserts that behavior. Its first compile also
needed an explicit collection type for RunSystemOnce. Neither setup error is a
product behavior RED or a passing matrix.

Native inspection found a real shared-header defect: connected World/Archive
status text collapsed into a one-character yellow column and overlapped the
body. The original HUD owner reproduced it with the shipped fonts: the 10-pixel-wide
status glyphs escaped the header, spanning y=-185..334. Reserving 190 pixels and
disabling shrink fixed it. The identical regression passed all 48 combinations
of current/historical/pending/closing status, connected route and required fit;
resource glyphs, period focus and the unchanged world-area contract stayed green.
Native confirmation at both 1366 Standard and the tightest 1366 Larger fit shows the complete status as a contained
two-line block, with readable resource chips and no body overlap.

A second native finding concerns hovered/selected Details cards: small gray
explanation text on the neutral hover background measured about 2.86:1 contrast.
The original HUD owner reproduced selected-idle marker contrast at 3.7487373:1
using actual painted colors and ancestor layers composited in linear light.
Smaller selected/hover/pressed fills passed 30 states across all four semantic
accents at 4.5:1, including actual cost/details text. Distinct state cues remain.
The repeated selected explanation was also removed while retaining its single
source and all distinct terms. The final 1366 Larger and Standard rasters confirm
readable selected Details, complete terms and retained focus/hover cues.

The next partial run produced all 21 first-fit images, then failed the Settings
lookup at 607.69 seconds. The diagnostic had initialized an impossible lifecycle
pair (Game with the default Home menu page); normal startup uses Game+InGame.
This is a fixture correction, separate from both product defects. No cancellation
occurred, and neither partial run is reported as a passing matrix.

The final harness first checks the automatic tour, skips it with focused Enter,
then opens World and uses the actual Menu → Settings → Replay interface tour
path. It captures all seven steps, exercises Previous/Next and completes the
tour at every fit. Later replays respect the actual remembered Settings page.
The fixture asserts unchanged draft, durable period, world hash and request
state; closing the tour leaves Play paused.

The normal Advance border carries the gold accent: observed pixels were
RGB(184,161,85), compared with the neighboring neutral underline RGB(186,194,200).
Its idle fill/text retain the ordinary panel/paper colors. No stronger fill was
requested after this inspection.

Michigan’s 83 county assignments use blue/sage/ochre (36/31/16 counties) and
no mauve. The Wayne matrix therefore checks the actual three-hue Michigan
composition; it cannot establish native distinguishability of the fourth hue.
A separate 1920 Standard regional fixture rendered all 263 Michigan, Indiana
and Ohio counties, including three actual mauve assignments (18061, 18155,
39131). All four hues are visibly distinct in that saved frame. The focused
test passed in 66.11 seconds. This supplements the 84-image matrix and does not
qualify simultaneous national rendering or a live campaign.

Initial oblique Organizer map labels overlap around Wayne and neighboring
counties. The county fills and boundaries remain distinguishable; this inherited
label-layout limit is recorded rather than presented as human usability acceptance.
The final 1366 Larger and Standard captures preserve this observation.

Software Vulkan used over two CPU cores during the partial runs. Bevy's default
Winit game mode already updates continuously when focused and at up to 60 Hz
when unfocused; no event-loop or renderer tuning was introduced.

The diagnostic's original 12-frame UI waits and eight post-acknowledgement idle
frames were conservative harness heuristics. The final pacing keeps every
capture/assertion and uses four UI frames: input dispatch, handler/painting/layout,
modal reconciliation and Last-stage focus/scroll restoration, then another layout
before capture. Actual readiness gates, loaded shipped assets, saved screenshot
acknowledgements and exact window/image dimensions remain required. Post-save
idle frames add no admission guarantee. The timeout remains 45 minutes; initial
tight-fit rasters show settled copy, focus, target outlines and restored scroll.
The complete four-fit run passed in 1,002.44 seconds with all 84 saved-image
acknowledgements and unchanged-authority assertions. Every final raster was
visually inspected; the controller independently sampled all four fits.

The first full changed-crate gate passed all 735 library tests (two native
tests ignored by default), then failed two of eight surface-contract integration
tests because the tour required an unregistered NavigationAction message in a
partial public-plugin composition. The canonical app and both native scenarios
already installed NavigationPlugin, which registers that message. The original
tour owner corrected install’s dependency ownership by registering the same
message. Bevy 0.20’s add_message checks for an existing Messages resource before
registering, so the canonical queue and behavior remain unchanged. No public
fixture API or optional-system bypass was added. The manifest distinguishes this
post-native source change; it makes no claim that all 85 images came from the
final commit. Registration removed both message panics (7/8 passed) and exposed
an independent missing decision-surface declaration on navigation text. The
original navigation owner adds direct declarations under the existing Observer
Shell contract; this is metadata, without rendering/input or gameplay-agency
changes. The focused surface contract then passed **8/8**, and the canonical tour
regression passed **16/16**. Logs are `/tmp/babylon-tour-install-contract.log`,
`/tmp/babylon-tour-install-regression.log` and
`/tmp/babylon-navigation-surface-contract.log`. The final changed-crate gate passed all 735 library and 36 integration tests
(three explicit native/live tests ignored by default); no assertion changed.

## Representative native images

These are unmodified saved renderer images. The complete matrix remains in the
temporary directory above; the manifest retains every image’s dimensions,
SHA-256 and visual observation. Its matrix-tested source hashes distinguish the
subsequent additive regional test/helper and tour-install message registration
from the 84-image run. It also records a later test-only explicit type import;
assertions and behavior are unchanged. The registration proof and tests are
described below.

| Image | Observation |
| --- | --- |
| [1366 Larger organizer](wayne-usability-2026-11-13-assets/1366x768-larger-organizer.png) | Tightest fit: dated chips, concise choices and rightmost Advance |
| [1920 Larger organizer](wayne-usability-2026-11-13-assets/1920x1080-larger-organizer.png) | Larger controls at the larger viewport |
| [Expanded Details](wayne-usability-2026-11-13-assets/1366x768-larger-expanded-details.png) | Corrected selected/hovered explanation contrast and full terms |
| [Archive refusal](wayne-usability-2026-11-13-assets/1366x768-larger-archive-unavailable.png) | Corrected status block and honest missing-reader message |
| [Resource tour](wayne-usability-2026-11-13-assets/1366x768-larger-tour-3.png) | Tour copy, focused Next and actual resource target outline |
| [Economic lens](wayne-usability-2026-11-13-assets/1920x1080-standard-world-economic.png) | Existing employment units, height/color encoding and legend |
| [Commodity controls](wayne-usability-2026-11-13-assets/1920x1080-standard-world-commodity-labels.png) | Longer cycle labels and separate unavailable material encoding |
| [Reduced Motion processing](wayne-usability-2026-11-13-assets/1366x768-larger-refresh-reduced-motion.png) | Static activity bars, actual stage/elapsed and unavailable actions |
| [Fixture error](wayne-usability-2026-11-13-assets/1366x768-standard-visible-error.png) | Explicitly authored fixture refresh-error footer |
| [Four-hue regional map](wayne-usability-2026-11-13-assets/1920x1080-standard-regional-neutral.png) | Actual 263-county Michigan/Indiana/Ohio fixture, including mauve |

## Independent implementation reviews

The controller obtained separate fixed-range reviews before native integration.
HUD and palette reviews found no open Critical/Important issue in their scoped
diffs; native legibility and full-map composition remained verification items.
Navigation review found that Home could leave a deferred historical Back queued.
The reviewed fix cancels that restoration before its already-home early return,
preserves the pending operation and tests the eventual live period. Tour review
found that raw map wheel/drag input bypassed the UI shield. The reviewed fix
blocks the actual camera consumer through the closing frame, resets interrupted
drags and retains fresh-gesture positive controls. Both fix reviews report all
findings addressed without new Critical/Important breakage.

Those reviews preceded the two native-found HUD corrections above. The native
header and card fixes each have an observed failing regression, a minimal
production correction and passing real-font/paint checks. Final Task 5 and
whole-branch independent review remain controller-owned after this evidence
commit; this report does not claim those future reviews have passed.

## Commands and gates

All heavy gates run serially. No documentation builds are part of this evidence.
The original HUD owner ran the same focused command before and after each
production correction:

| Regression command | Observed RED | Observed GREEN |
| --- | --- | --- |
| `cargo test -p babylon-client --lib shared_status_help_and_disabled_reasons --locked` | 0 passed / 1 failed; actual status glyphs escaped the header | 1 passed / 0 failed; 48 route/status/fit combinations |
| `cargo test -p babylon-client --lib practice_costs_and_details_keep_contrast --locked` | 0 passed / 1 failed; selected marker 3.7487373:1 | 1 passed / 0 failed; all text in 30 actual painter states at least 4.5:1 |

Logs retain the `red`/`green` suffixes under
`/tmp/babylon-native-header-*.log` and
`/tmp/babylon-native-card-contrast-*.log`. Initial fixture compile/lookup errors
above are not counted as product REDs.

```sh
source /workspace/babylon-cloud/activate.sh
source /workspace/babylon-cloud/native/software-vulkan.sh
cd /workspace/babylon/rust
DISPLAY=:99 XDG_RUNTIME_DIR=/tmp/wayne-usability-native-runtime \
  MESA_SHADER_CACHE_DIR=/tmp/wayne-usability-native-mesa-cache-02 \
  BABYLON_NATIVE_CAPTURE_DIR=/tmp/wayne-usability-native-captures-03 \
  cargo test -p babylon-client --lib fixture_based_native_rendering_matrix \
  --locked -- --ignored --nocapture --test-threads=1
# Same activated/display/cache environment; a separate fresh capture directory:
DISPLAY=:99 XDG_RUNTIME_DIR=/tmp/wayne-usability-native-runtime \
  MESA_SHADER_CACHE_DIR=/tmp/wayne-usability-native-mesa-cache-02 \
  BABYLON_NATIVE_CAPTURE_DIR=/tmp/wayne-usability-native-regional-01 \
  cargo test -p babylon-client --lib fixture_based_native_regional_palette \
  --locked -- --ignored --nocapture --test-threads=1
```

| Gate | Result |
| --- | --- |
| Native fixture matrix | **1 passed / 0 failed**, 84 acknowledged PNGs, 1,002.44s; `/tmp/babylon-usability-native-04.log` |
| Supplemental regional native map | **1 passed / 0 failed**, 1 acknowledged PNG, 66.11s; `/tmp/babylon-usability-native-regional-01.log` |
| `cargo test -p babylon-client --locked` | **771 passed / 0 failed / 3 ignored** (735 library + 36 integration); `/tmp/babylon-usability-client-full-final-02.log` |
| `cargo fmt --all -- --check` | Passed; `/tmp/babylon-usability-fmt.log` |
| `cargo clippy -p babylon-client --all-targets --locked -- -D warnings -D clippy::cognitive_complexity` | Passed, 8.36s; `/tmp/babylon-usability-clippy-final-02.log` |
| `cargo run -p bsl-lint --locked -- all` | Passed with advisory warnings; `/tmp/babylon-usability-bsl-final-02.log` |
| Current RST/doc8/Markdown hooks | Passed final targeted checks; `/tmp/babylon-usability-prose-final.log` |
| Targeted Vale | Unavailable: no executable or live repository configuration/version pin; no replacement config invented |

The partial native run printed read-only Mesa shader-cache and absent ALSA-device
diagnostics. The final run uses a task-owned cache and emits no read-only cache warning.
The ALSA no-device diagnostics remain; audio-device acceptance is not claimed.

The first final BSL run found one qualified type spelling in the new header
regression. An explicit ObserverViewport import corrected it without changing
assertions or behavior. Its failed log remains at
`/tmp/babylon-usability-bsl-final.log`; the exact corrected tree receives the
final gates above.

## Python and environment limits

The canonical `mise run --jobs 1 check` reported **4,007 passed, 75 failed,
27 skipped and 16 collection errors**. Governance mass and the ADR catalog passed;
the aggregate remains not green. A clean-baseline execution is not claimed.

Four modules could not collect because logging used a read-only default personal
path. Eighteen cases stopped early because pg_restore was absent from PATH.
The supported LOG_DIR override and already extracted pinned PostgreSQL 17 client
resolved those blockers without changing source or assertions. All four logging
modules and the exact 18 PostgreSQL failure nodes then passed: **36/36**.

The targeted rerun used the following activated environment and options, with the
original failing backup/native-pair nodes and the four logging modules:

```sh
export LOG_DIR=/tmp/babylon-usability-test-logs
export PATH=/workspace/babylon-cloud/postgres/client/usr/lib/postgresql/17/bin:$PATH
mise exec -- uv run --frozen pytest -q -n 0 \
  -m 'not red_phase and not slow and not requires_ollama' \
  tests/unit/cli/test_app.py tests/unit/cli/test_doctor.py \
  tests/unit/cli/test_ops.py tests/unit/tools/test_ingest_corpus.py \
  tests/unit/tools/test_wayne_qualification_backup.py::test_checksum_consistent_logical_recovery_refuses_incomplete_observations \
  tests/unit/tools/test_national_native_pair.py::test_complete_pair_reopens_both_real_evidence_bundles_and_fails_closed \
  'tests/unit/tools/test_national_native_pair.py::test_final_pair_refuses_review_defects[missing-capsule-source-]' \
  'tests/unit/tools/test_national_native_pair.py::test_final_pair_refuses_review_defects[wrong-decisions-released smoke workload]'
```

The backup node expands to 15 parameter cases. `mise run --jobs 1 check:static`
also passed hygiene, dynamic-link fence, Ruff (399 files), mypy (58 sources) and
frozen-lock checks. Palette/atlas **21/21** contracts passed, including all 6,071
positive-length shared rendered boundaries and deterministic generation.

The remaining **57 observed failures** concern unchanged native-process
contracts: this host lacks live per-task `/proc/.../children` records, and an
executable-write check receives EACCES where its contract requires ETXTBSY.
The affected tests and implicated sources have no diff from the original branch
base `2824cf38e`. No zero/empty census substitution, baseline edit or weaker
assertion was introduced. These contracts require a suitable Linux executor; repeating them on
the unchanged host would not establish green qualification.

Existing output also includes an AnyIO pytest-10 CallSpec2 deprecation warning,
a mypy unused-override note and non-gating BSL citation/style warnings. Five
boolean-state/argument hints concern the new native-test harness; the remaining
advisories predate that harness. No allowance or threshold changed. This is not
presented as pristine output.

## Acceptance still open

A live runtime/PostgreSQL campaign with normal startup and committed results
remains pending. So does a new uncoached friend session: start a fresh disposable
campaign, find/explain the three resources, compare two practices, use Details,
Review, Confirm and Advance, read the actual result, use Back/Home and skip/replay
the tour. Record hesitation, misunderstanding, assistance and task completion
from actual observation, with date/source/window/interface size. Check small
resource-caption readability and the oblique county-label overlap explicitly.

Automated rendering and existing tests do not substitute for that session,
physical pointer/keyboard acceptance or assistive-technology acceptance. Broader
PER-336/PER-292 and player-agency acceptance remain open. No push or merge was
performed by this task.
