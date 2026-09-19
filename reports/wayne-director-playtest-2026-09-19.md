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

The opening Inquiry limitation appears before confirmation. The interface
describes report absence neutrally and separately from partner response. New
Archive receipts use that wording. Historical pages keep
their original bytes. No admission rule, BSL mechanic, captured input format or
persistence schema changes for this presentation repair.

Regression tests first reproduced the missing opening warning, an unavailable
Notes focus target and a hidden save error. The repairs passed 416 client
tests, 230 persistence tests and 26 decision-surface and Archive contract tests.
The persistence suite explicitly skipped 32 live database tests. Three contract
tests that regenerate vectors also stayed disabled. The earlier organizer
delivery retains its full mechanical qualification. This repair does not claim
to repeat that entire witness.

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

## Exit and next witness

The original session found a comprehension blocker. Engineering verification of
the repair cannot close that human acceptance condition. Resume the preserved
campaign without coaching a preferred political choice. Ask the Director to
identify the controlled organization, explain two alternatives and predict
their cost, displacement and timing. After advancing, ask what happened
and what the result makes possible next.

Then cover Inquiry, Reinforce, Hold, persistent Pause/Resume, agreement expiry
and renewal, and reopening within the 16-period limit. Record hesitation,
unexpected results, repeated clicks, decisions and enjoyment in the Director's
own terms. Separate acceptance, resolution, acquired knowledge and continuing
permission. A successful replay is engineering evidence, not proof of fun.

Only after that witness passes can PER-292 test whether the bounded social
topology makes these relationships easier to understand. Deeper interactions
must give earned knowledge and competing commitments consequential uses.
More reports or a more elaborate graph alone would not prove that result.
