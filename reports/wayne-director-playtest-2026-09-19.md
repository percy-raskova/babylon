# Wayne Director session and interface repair

Date: 19 September 2026. Part of PER-336. The Director played with agent
facilitation, followed by an engineering review. This does not represent
unfamiliar-player research. The repeat human witness remains required before PER-292 proceeds.

## Observed session

The original build was `42ca3988a79f4ee5687a2aa16a7a41ef12624b88`.
Campaign `260a20e6-b60a-473e-be18-23c58e6b0c80` used the
`organize-in-wayne` profile in the separate local database
`babylon_per336_playtest_20260919`. The agent preserved existing campaigns. The
captured window was 1366 × 692, interface scale 1, reduced motion off, music
volume 0.25 and effects volume 0.4. The Director later confirmed mouse-only input.

Before coaching a choice, the facilitator asked what the organization was
trying to do and what the Director would choose. The Director inferred
workplace organizing and preferred investigation, but reported an unclear
purpose, excessive density and poor information organization. The campaign
reached committed period 1. Its Inquiry receipt proves a specific accepted
Inquiry input: the default routine constructs Hold and cannot produce that
receipt. The exact click sequence, hesitation and repeated clicks were not
recorded. This report does not infer them as observed behavior.

The screenshot shows the organization Archive beside a large map. The receipt
called the requested evidence “withheld” while also reporting partner
participation. At opening period 0 the workplace had no completed-period facts.
That wording attributed more meaning to the result than the evidence supports.
Empty sections and repeated freshness text further competed with the reading.

The guided witness paused at period 1 after this comprehension failure. No
numerical enjoyment score or claim about enjoyment is available.

The revised build at `a3cdc161273be54a1679662833a2ca48e2b19dc0` reopened
the preserved campaign. The repeat session reached committed period 2. The
Director then reported that Escape opened the start menu instead of the
in-game menu. The session log confirms the period-2 commit and later music
volume changes to 0.75. These records do not show which input device
submitted the ruling or how the Director interpreted its result.

The Director praised the revised appearance. They described a prospective
strategy: repeat investigations to maximize information, expecting details
about production or social power mapping. This is an intended
strategy, not an account of the period-2 result. The present inquiries supply
named work/output or maintenance reports. They do not discover a social power
map. PER-292 records that expectation for its bounded topology work.

Positive
appearance feedback does not prove comprehension or enjoyment of the loop.

## Research and mechanical audit

The local collection is `~/Downloads/babylon_books/ux`. The agent read selected
sections, rather than every book in full.

<!-- Preserve exact author names and published book titles. -->
<!-- vale Vale.Spelling = NO -->
<!-- vale ste.Contractions = NO -->

| Source | Sections consulted | Application |
| --- | --- | --- |
| Norman, *The Design of Everyday Things*, revised edition | Printed pp. 38–40, 71–73, 247 | Explain the controlled actor and connect action to interpreted result. |
| Krug, *Don't Make Me Think, Revisited* | Chapters 1, 3 and 9, particularly pp. 113–115 | Make choices scannable. Observe use rather than infer comprehension from preference. |
| Sylvester, *Designing Games* | Printed pp. 127–131 and 219–230 | Supply information needed for a decision without overwhelming it. |
| Salen and Zimmerman, *Rules of Play* | Chapter 3, local PDF pp. 48–50 | A visible result must also matter to later play. |
| Tufte, *Envisioning Information* | Printed pp. 53–55 and 67 | Use visual hierarchy and consistent fields for comparison. |
| Shneiderman, *Direct Manipulation* (1983) | Printed pp. 64–65 | Make exploration reversible without suggesting unavailable actions. |
| Lidwell, Holden and Butler, *Universal Principles of Design* | Progressive Disclosure, Recognition Over Recall, Chunking, Hick's Law | Keep decision essentials visible and label access to supporting detail. |

<!-- vale ste.Contractions = YES -->
<!-- vale Vale.Spelling = YES -->

Primary web sources included [NN/g on progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
and [complex application design](https://www.nngroup.com/articles/complex-application-design/),
plus the Victoria 3 team's accounts of [contextual UX improvements](https://www.paradoxinteractive.com/games/victoria-3/news/dev-diary-74-ux-improvements)
and [tutorials](https://www.paradoxinteractive.com/games/victoria-3/news/dev-diary-51-tutorials).
These support testable design choices. They do not prove that this layout
is fun or usable before someone plays it.

<!-- Preserve the supplied author's name. -->
<!-- vale Vale.Spelling = NO -->
The Director also supplied Anna Dasse's
[Game designers are the new UX/UI designers](https://www.gasstationbreakfast.blog/p/game-designers-are-the-new-uxui-designers)
(10 September 2026).
<!-- vale Vale.Spelling = YES -->

Its useful application here is to design feedback from
system state. An opening inquiry, an accepted commitment, a resolving period
and an acquired report need distinct explanations even when the visible
action names stay the same. The present repair uses explicit game state for
that distinction.

This does not prove a need for invisible player profiling or automatically
reordered controls. A long pause can mean deliberation rather than confusion.
Stable navigation and player-controlled help remain the design choice.
[W3C's consistent-navigation guidance](https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html)
explains the accessibility value of predictable repeated controls.

The article cites the [Gradual Generation paper](https://arxiv.org/abs/2601.17975).
That paper presents discoverable customization through intermediate generated views.
It does not study Babylon or prove that automatic rearrangement would improve this game.

The code audit traced the authored `organizer-cycle.bsl` through captured
organizer content, tick dispatch and practice-contract reducers.
It followed durable commitment and receipt storage into the restricted client/Archive projections.
The behaviors below have real consumers in that path.

| Choice | Present consequence | Limit |
| --- | --- | --- |
| Work/output or maintenance inquiry | Spends 12 organizer-hours, replaces one period of routine, requests one completed-period report. | It does not repair the workplace or grant continuing permission. Period 0 has no completed facts. |
| Reinforce workplace contact | Spends 8 hours. Mutual participation creates a product that the next period consumes to renew the workplace agreement. | Active sharing supplies an automatic report on an actual fall in performed work, not a full report every period. |
| Keep current routine / Hold | Attempts neighborhood contact for 8 hours if the collective has authorized the routine. Can renew that neighborhood agreement. | The workplace-report consumer does not read the neighborhood agreement. |
| Pause / Resume | Changes whether the saved routine continues in later periods. | Unused hours expire. The model permits one practice per period. |

Both authored partners have fixed participation policies, subject to time and
eligibility checks. This scenario does not show changing partner
strategies. An 8-hour versus 12-hour cost has less meaning than a
budget that supports simultaneous actions. A contact receipt does not imply
recruitment, demand, strike, wage or support consequences.

The strongest current tradeoff is learning a particular fact versus sustaining
access to future workplace signals. The neighborhood alternative has less
downstream meaning in this slice. That is missing interaction depth, not a reason
to fabricate a benefit or tune an arbitrary relationship score.

## Repair and verification

The repair puts the controlled collective, current period, available time,
routine, acquired evidence and last completed practice into a decision view.
Four aligned choices disclose cost, displacement, timing and partner dependence.
A persistent footer distinguishes draft, review, accepted ruling and resolution.
Notes and detailed records remain available through separate views. Archive
inspection gains an explicit return to the decision.

The repeat session exposed a separate navigation defect. Opening-screen logic
sent an open game menu back to the title screen. The repair gives the campaign
its own menu with Resume, Settings, Main menu and Quit. Escape closes Settings
or inspector before another navigation action can occur. An explicit Main menu
choice retains access to the existing Load and Reopen controls. A failed
advance displays its failure before any pending-operation message.

The opening Inquiry limitation appears before confirmation. The interface
describes report absence neutrally and separately from partner response. New
Archive receipts use that wording. Historical pages keep
their original bytes. No admission rule, BSL mechanic, captured input format or
persistence schema changes for this presentation repair.
New Archive practice labels also match the action labels in the decision view.

Regression tests first reproduced the missing opening warning, an unavailable
Notes focus target and a hidden save error. The repairs passed 416 client
tests, 230 persistence tests and 26 decision-surface and Archive contract tests.
The persistence suite explicitly skipped 32 live database tests. Three contract
tests that regenerate vectors also stayed disabled. The earlier organizer
delivery retains its full mechanical qualification. This repair does not claim
to repeat that entire witness.

The Escape repair first reproduced the unwanted title transition and a single
key press reaching two navigation handlers. Its client suite passed 418 tests.
Review then found the missing recovery route and hidden failure message. Both
received failing regressions before repair. All five focused menu tests passed.
The three Archive projection tests passed with matching practice labels while
retaining source attribution, actual outcomes and separate partner responses.

Native checks used a separate campaign,
`1c7691e6-132c-4c69-a30a-5d6aff626972`, with isolated settings and personal drafts.
At 1366 × 692, the agent selected, reviewed and confirmed Inquiry, observed
resolution and read the committed period-1 receipt. Scroll cues exposed the
supporting links. Archive return preserved the selected draft.

The verified
Archive page reported no acquired report separately from partner participation.
A second Inquiry remained accepted at period 1 when the game closed normally.
Reopening preserved that ruling. Its period-2 resolution supplied the requested
period-1 report, separately from an automatic period-2 report of reduced work.

The decision, report selection, Notes, routine controls and menu all had visible
pointer routes. The 1920 × 1080 window at automatic scale 1.25 fit the complete
decision view. A deliberate save failure in the isolated Notes directory showed
the error without losing text or submitting a command. Restoring write access
saved the text but exposed a stale error message.

A regression test reproduced
that fault. After the repair, the native retry saved the full text and cleared
the old failure. A separate test proves that an unrelated command error survives
successful draft saving. The campaign stayed at period 2.

Quit reached the
closed state without a game error, but that final launcher returned status 143.
The previous two complete native sessions returned 0. A bounded repeat with
the same binaries and the direct launcher reopened period 2 and returned 0
after Quit. The local evidence retains the unexplained earlier status.

An earlier local build reused a stale runtime artifact and published the old
Archive wording. The agent retained that failed evidence, removed only the
affected package outputs and rebuilt the binaries. The separate campaign above
then proved the new producer's stored and displayed result. Binary hashes,
source hashes, logs and captures are in the local evidence directory
`reports/test-results/per336-native/`. These local artifacts are not committed
with this report.

The repeat native check reopened the same separate campaign at period 2 and
1366 × 692. Escape opened the campaign menu. Settings returned to that menu,
then a second Escape resumed the decision. One Escape closed the Evidence
inspector without opening the menu.

Pointer Resume and explicit Main menu,
followed by Continue, also retained the decision. Both isolated personal draft
files retained the same bytes, and Quit returned 0. No period advanced.

## Expanded native route and Archive repair

Agent-operated checks on `9eb989ee60ab83c73eda0ec31d7a246002163578`
continued the separate campaign from period 2. They covered workplace contact,
explicit Hold, automatic neighborhood work, Pause, a normal close and reopen
with Pause preserved, and Hold while paused. Hold did not silently resume work.

At period 8, the material commit succeeded but the runtime refused Archive
publication. The displayed Archive remained at period 6. One normal Reopen
failed with the same refusal. A read-only audit found matching tick,
world, receipt and organizer projection identities through period 8.

The agent then ran the existing campaign-scoped Archive worker once. It consumed
the two pending receipts and verified period 8 without advancing the game.
The original route requires a recovery workaround and is not a clean native run.

After recovery, the route verified both expired agreements, workplace contact
and its later renewal, and a work/output inquiry. Resume restored automatic
neighborhood work. A native Reopen at period 12 and a maintenance inquiry passed.
Report navigation retained separate observed and acquired dates. The campaign
completed period 16.

Its closed choice cards and disabled ordinary advance
controls admitted no period 17. History remained readable. Stored markers were
exactly periods 1–16, with 10 consumed commands, 16 receipts and 5 observations.
The native application logged normal closure. The detached launch did not record
its exit status, so this report does not claim one.

The Archive investigation found a five-second idle transaction limit around
page production that uses separate connections. A live regression delayed the
producer for six seconds and reproduced transaction loss and a misclassified
closed-connection error. The repair gives that production step a bounded
30-second idle allowance and restores the normal limit before publication.

The original runtime discarded its inner error. The database log records an
idle timeout in the failure window. Linking that timeout to the period-8
refusal remains an inference.

It retains the `SERIALIZABLE` receipt/knowledge snapshot, existing SQL and lock
limits, schema checks and atomic publication. Closed connections and server
idle timeouts keep diagnostics that allow retries. Organizer hydration also
preserves database diagnostics through graph and territory-map errors.
Structural mismatches remain fatal. This changes Archive recovery, not game mechanics.

The delayed-production regression passed after repair and confirmed that a
retry did not duplicate the page. The existing live driver test also passed
startup catch-up, reconnection and shutdown with a full progress channel. The disposable
database harness verified cleanup. The local evidence preserves the original
native refusal, the manual recovery, failing regressions and passing checks as
distinct records in `reports/test-results/per336-native/expanded-native/`.

The complete affected Archive group passed all six live tests in 281.54 seconds.
Including compilation, its phase took 311 seconds within the unchanged
600-second limit. These checks cover cancellation rollback, notification/commit
atomicity and nested database diagnostics as well as delayed publication and
driver recovery. The harness verified removal of its container and volume.
Independent review found no remaining actionable issue.

A fresh corrected-runtime campaign,
`b75a6e85-0384-4110-886f-3cd09156b03b`, completed three inquiries,
workplace contact, Pause, Resume and two automatic periods. Native Reopen at
period 4 preserved the contact result and draft. The player advanced as soon
as the interface exposed durable completion. Archive lagged during that burst
and then verified period 8 without a manual worker or a refusal.

The final read-only snapshot matched markers 1–8, six consumed commands,
eight receipts and three observations. The routine remained authorized.
Measured advance times ranged from 9.29 to 11.53 seconds on this host.
Reopen took 21.73 seconds. The first card explicitly verified at period 8
arrived 13.25 seconds after the game became Ready there. These are local
measurements, not general performance guarantees.

Normal Quit logged closure without failure. Waiting supervisors recorded exit
status 0 for the launcher and the isolated display. The source hashes match
the reviewed repair. The replay record, timing ledger, captures and manifest
are in `reports/test-results/per336-native/corrected-native/`.

Both executables then rebuilt together against the repaired persistence library.
The final pair reopened that same campaign at period 8 and verified Archive
there. Its organization page displayed Inquiry, Reinforce, Pause and Resume
receipts with separate source, outcome and partner attribution. No ruling or
advance occurred. Native Menu and Quit worked, and both waiting supervisors
recorded exit status 0. The final-pair record keeps its own binary hashes,
captures and launch log beside the earlier witness.

During the same session, the Director's launcher ended unexpectedly and its
window disappeared while the agent inspected the completed launcher session.
The agent sent no Quit or advance command. The agent restored the same saved
period-2 campaign and the 75% music setting. The cause remains unproven. The
record does not treat process-launch lifetime as campaign persistence.
The restored campaign later logged a normal Quit at period 2.

## Exit and next witness

The original session found a comprehension blocker. Engineering verification of
the repair cannot close that human acceptance condition. Resume the preserved
campaign without coaching a preferred political choice. Ask the Director to
identify the controlled organization, explain two alternatives and predict
their cost, displacement and timing. After advancing, ask what happened
and what the result makes possible next.

Engineering checks covered Inquiry, Reinforce, Hold, persistent Pause/Resume,
agreement expiry and renewal, and reopening within the 16-period limit.
The Archive failure and recovery boundary remain explicit above. Human
observation still needs to show understandable consequences. Record hesitation,
unexpected results, repeated clicks, decisions and enjoyment in the Director's
own terms. Separate acceptance, resolution, acquired knowledge and continuing
permission. A successful replay is engineering evidence, not proof of fun.

Only after that witness passes can PER-292 test whether the bounded social
topology makes these relationships easier to understand. Deeper interactions
must give earned knowledge and competing commitments consequential uses.
More reports or a more elaborate graph alone would not prove that result.
