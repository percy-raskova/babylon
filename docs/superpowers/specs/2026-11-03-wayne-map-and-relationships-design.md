# Wayne map and relationships: design

**Status:** Approved on 2026-11-03. Workspace redesign approved on 2026-11-05.
The Director's exact November 3 decision was
“Approve this design and limited disclosure”. This approves the design and
the limited visibility ruling below. It does not prove native behavior or
accept a game gate.

The November 3 approval required the finite PER-336
closeout before implementation. The November 5
[execution plan](../plans/2026-11-05-wayne-game-workspace.md) uses current `dev`.

The earlier v3 interactive preview received “i feel like this
is great!” from the Director. That preview was visual evidence.

**Scope:** PER-292's bounded national Wayne organizer experience. The November 3
design used `d2b8ea14d` plus Task 7e under repair as historical context.
Neither this design nor its prerequisite claims the PER-355
14-cell acceptance or full Director acceptance of the active goal.

## Player purpose and first slice

The geographic world is the persistent home. The player must see where the
collective can act, understand a known partner's relationship and concern, and
follow an actual choice into its delayed consequence. The first playable slice
connects one path, rather than introducing a general topology browser:

1. Select the known Wayne Workplace Committee in Places or Relationships.
2. Read the disclosed contributor concern and distinguish agreement, routine
   contact, report and earned contact.
3. Open the cited evidence and return to the same subject.
4. Review Inquiry or Reinforce for the captured workplace and committee.
   The review must present actual terms and consequences before confirmation.
5. Confirm the action, then ask for one period advance through the existing flow.
6. After a durable commit, return to the same identities. Inspect the actual
   receipt and any newly available cited evidence.

A refusal, no report, no contact, or another lawful outcome remains valid.
Explain the actual result.

Inquiry and Reinforce do not target an arbitrary selected organization. When
offered from another selected subject, name the captured workplace and committee
as the action target and partner. Use the existing eligibility and review path.

Use the captured campaign's actual practice hours and cycle capacity. The old
2-hour examples describe their campaign. They set no universal cost. Show
displaced standing neighborhood work when applicable, independent partner response,
and report timing from the actual view. In period 0 no
completed-period report exists. Do not promise a report or successful contact.

Reviewing, navigating, or changing views does not advance time or submit a
command. An existing confirmation and the separate committed advance keep
their present semantics.

## Screen and interaction

Use native Bevy 0.20 and the existing client UI, fonts, palette, input and
selection facilities. The preview is visual evidence, not a UI implementation
or a literal layout specification. Target readable, usable native layouts at
1366×768 and 1920×1080, leaving the map as the primary surface. A compact
collective/context area, map-focus controls, and selected-subject detail must
leave space for the geography and the decision. Make keyboard focus, selected,
hover, unavailable and pending states distinguishable without color alone.
Do not turn the first screen into administrative cards or an economic dashboard.

**Places** uses the existing county atlas and fixed geography. Outline Wayne
County, FIPS `26163`, with an explicit selection cue. A county-level subject
dock or similar control lets the player select known subjects without inventing
workplace, venue, or neighborhood coordinates. The county label, legend and
controls must not obscure one another. County geography does not itself assert
that an organization has members, influence or a workplace at a point.

**Relationships** uses a deterministic semantic layout for disclosed entities
and relations. Names and relationship types remain visible and navigable. Use
distinct visual and textual treatments for agreement, routine `CONTACT`, earned
contact/cooperation, and actual native body incidence. Draw a relation only
when the viewed context permits its kind and endpoints. Avoid generic
lines that imply every node has the same kind of connection.

Position, hit targets, layout spacing, counts and interaction must depend only
on disclosed data. Hidden nodes and incidence cannot affect their geometry.

The controlled Wayne Organizing Collective and its disclosed contributor position
are distinct subjects. The known Workplace Committee, Neighborhood Contact Group,
and captured workplace are also distinct subjects. Preserve their stable
identities across map, list, relationship view, detail, evidence, action and
return navigation. The collective contributor position is not the committee's
own disclosed position. Selection persists across views and evidence navigation.

Hover or keyboard focus gives transient feedback without changing selection.
Keep the selected county and subject in sync where applicable. An existing draft
survives view and evidence navigation, subject to the existing validity rules.

## November 5 game workspace

The Director approved a full geographic background with compact controls above
it. A selected-group dossier sits at the right, with two directly comparable choices
along the bottom. Keep Wayne in focus on the existing county atlas. Places and
Relationships share stable selection and the same campaign, viewed period and
draft. The top strip names the collective, period, actual committed means,
standing neighborhood work and the separate advance control. Keep the ordinary
map, production and Archive destinations.

Give the collective, workplace committee and neighborhood group distinct,
reusable illustrations. A portrait personifies a group, without a named person,
faction seal, membership count, geographic location or disclosed relation. Use
the existing industrial ink, paper, rust, bone and brass estate, especially
[Red Apparatus](../../../design/bevy-assets/prompts/hero-red-apparatus.md),
[Bunker Oracle](../../../design/bevy-assets/prompts/concept-bunker-oracle.md)
and [Living Map](../../../design/bevy-assets/prompts/concept-living-map.md).
Keep image provenance in the existing
[asset catalog](../../../design/bevy-assets/manifest.toml).

The narrow Victoria 3 lesson is a contextual choice with its actual cost and
availability, plus deeper explanation on demand. Its shipped map-list decree
controls separate hover information from the click action. The local
[derivation design](2026-07-30-derivation-inspector-design.md) records related
explanation and comparison goals.

<!-- vale Vale.Spelling = NO -->
The narrow Stellaris lesson is a dispatch that can lead to a known subject.
Its shipped situation-log controls distinguish tracking a subject from moving
the camera to it. These observations concern
interface resources, not game-mechanics proof. Portraits follow Babylon's
existing art direction and [North Star](../../../NORTH_STAR.md).

The older [Victoria 3 study](../../../project/research/16-living-map/games/victoria-3.md)
and [Stellaris study](../../../project/research/16-living-map/games/stellaris.md)
are historical design inputs. Their broader prescriptions grant no live scope.
<!-- vale Vale.Spelling = YES -->
The [July map doctrine](../../gameplay/research/35-july-living-map-and-behemoth-threads.md)
provides the repository's map-first context.

The bottom deck names the captured target and partner, actual hours, displaced
routine, possible benefit, resolving period and availability for both choices.
When the personal draft is Hold, show Reinforce against Hold when available
without selecting Reinforce. A non-Hold draft compares itself against Hold.
All practices remains one reachable list, including both inquiries, collection,
local aid, remote solidarity, pause and resume. Keep collection shared material
time and later aid coordination distinct from fulfilled delivery or performed
organizer time. Paused routines stay paused unless explicitly resumed.

Use one inspector for deeper evidence, notes, relationships, practice history and
review. Keep the essential comparison visible at ordinary sizes. Larger text and
long names use stacked rows and one reading region that scrolls. Review shows the
authenticated actual terms. Review, Confirm and Advance remain separate actions.
Refused, unavailable, pending, historical, completed and failed states must
explain what the player can do next.

After a durable advance, show a period dispatch that leaves the workspace usable.
Include only receipts for the exact viewed period and authorized actor.
Show newly acquired reports with both observed and acquired dates, and actually
disclosed public City PD encounters.

Keep older receipts, reports and encounters in explicitly dated history. Period 0
has no completed-period result. If the snapshot has no receipt for the inspected
period, direct the player to the existing practice Archive. Do not invent a quiet
result. A delayed report is new knowledge about its observed period, not a newly
observed event. Participation, contact, report acquisition, gift dispatch and gift
arrival remain separate outcomes.

Dispatch links carry stable subject, report or existing inspector/Archive
identities. Opening and returning from evidence preserves the viewed context,
selected subject and captured draft. Historical and pending views cannot write or
replace a missing historical fact with current information. Overlay bounds and
camera geometry must agree: map click, drag and wheel input stop beneath the
comparison, dossier, inspector and dispatch. Reuse existing audio and reduced
motion settings for selection and committed-period feedback.

Qualify the real native composition at 1366×768 at scale 1, 1920×1080 at scales
1 and 1.25, and the existing larger text settings. Test both views, long names,
different captured costs, unknown and pending states, every practice, keyboard
access and evidence return. Screenshots and injected input do not prove human
comprehension or enjoyment.

## Knowledge and relation contract

The opening's existing disclosed contributor commitment is a position with
promised time, concern, objection and review condition. Promised time is not
performed time. Named partners and their currently valid agreements are not
membership. A captured routine `CONTACT` is not a completed action, a report,
or an earned contact product. The initial workplace venue notice is not an
earned contact. Opening report and receipt availability must come from the
selected campaign and viewed period, not from a hard-coded preview.

Native public hyperedges remain first-class. **Approved Director visibility
ruling for this design:** disclose the real controlled collective's
`ORGANIZATION_BODY` `HyperedgeId` and stable structural key. Disclose only the
organization/contributor incidence that controlled actor positions already
disclose at the viewed committed period. This is a **partial disclosed part**,
with no claim of completeness or hidden-member count. It grants no
partner-only incidence, partner ledger or whole-graph access. The current
snapshot exposes the own position and named partners.

The existing snapshot does not itself project that hyperedge ID or its member
list. This approval grants only the limited disclosure specified here. It does
not imply that the current reader already implements it.

Show the actual disclosed controlled-collective organization/contributor pair
in the first scene. Use an authenticated projection when the viewed committed
position supplies the pair.
Do not substitute a presentation grouping for native incidence or claim an
unavailable body is empty. Neither an organizer scalar ID nor a visual grouping
is a hyperedge ID. Label any separate Designed presentation grouping as such.
Never pass it off as observed incidence.

For lawfully projected incidence only, one disclosed member can use a halo,
two a capsule, and three or more a membrane. Label them as the disclosed
part when completeness is not authorized. Shape and count must not imply
that other members are absent. Unknown or unavailable, pending, known zero, and
known absent are distinct states. Do not project a hyperedge as a clique, infer
persons or a census, or display partner ledgers, hidden members or totals.

A narrow typed, provenance-bearing reader extension can carry authorized
hyperedge identity and incidence from Postgres-backed committed state to the
client if the current reader cannot. Bind it to campaign, actor and
perspective/knowledge scope. Also bind it to the viewed durable period, source,
evidence class, read generation and relevant content/world-hash freshness
identity.
Refuse a stale or mismatched response before installation.

Historical views allow no writes. They show only
agreements, receipts and knowledge valid at that viewed period. Reuse existing
runtime projection, evidence scopes, Archive reader, draft and action handlers.
Do not export the full register or add a parallel scheduler, API framework or
dependency. The builder chooses the smallest modules that uphold this boundary.

Show public City PD information only when an actually earned venue encounter
and its permitted citation disclose it. Never expose an undisclosed case,
schedule, roster, budget or other private agency information.

Automatic next-period contact consumption uses the actual prior product under
the existing runtime. A receipt's production field is not consumption. This
design adds no consumption receipt or mechanic. Consumption must not
manufacture an encounter or force a partner response. A venue notice,
permission, matching period or routine relation alone proves none of those
outcomes.

## Qualification and acceptance

After PER-336 closeout, exercise the real chain from
captured campaign data through the authorized runtime projection and native
Bevy selection. Continue through review, confirmation and one durable period
commit. Inspect the actual receipt, restricted Archive evidence and restart.
Check identity, selection, draft and return navigation across both views,
including an unavailable or refused result. UI construction or a synthetic
receipt alone does not prove that player path.

Use meaningful deterministic and privacy-negative checks. Replay the same
inputs. Reject stale, foreign or wrong-period projection installation. Check
that the projection excludes partner-only incidence, partner ledgers and all
other graph data without a grant, even when present in the source. Check that
hidden incidence cannot affect labels, counts, geometry or hit targets. Check
historical agreement and evidence scope.

Test cross-view selection and
draft preservation at the actual consumer boundary. Inspect the native screen
at both target resolutions, including keyboard operation, long names and
unavailable evidence. A human play session remains distinct from component and
runtime checks.

Use existing national qualification controls and run heavy work serially.
Measure the resource and persistence effects against the existing North Star
budget. Do not invent frame-rate ceilings. Playable acceptance is conditional
on a real, visible, explainable committed result and its evidence, not on a
predetermined partner response. Record failures and unavailable evidence
honestly. Do not claim the broader national or Director gate from this slice.

The [November 5 native evidence](../../../reports/wayne-game-workspace-2026-11-05.md)
records the bounded Michigan decisions, an interruption and recovery of
that same campaign through a distinct cold process. National performance,
physical input and human comprehension and enjoyment remain open.

## Out of scope and sources

This design authorizes no new game primitive, agency expansion, generalized
social graph reader, national map-mode suite, or economic network view. Broader
views need actual lawful data and their own scope. No skill installation,
new UI framework, compatibility layer, speculative metric or fixed outcome is
part of this design.

The controlling direction is [North Star](../../../NORTH_STAR.md) and the
[repository architecture](../../concepts/architecture.rst). The existing
opponent and witness constraints are in the
[first-state-opponent design](2026-10-29-first-state-opponent.md). Recheck current
behavior in the organizer
[view contract](../../../rust/crates/babylon-practice-contract/src/organizer/contract.rs),
[client presentation](../../../rust/crates/babylon-client/src/organizer/presentation.rs),
and [national policy](../../../content/scenarios/national/defines.toml) at the
qualified implementation head. The topology authority research is a bounded
source-reading aid, not a grant or current campaign observation.

## November 6 human testing corrections

Keep the collective's cash, captured organizer-hours and dated shared household
time visible in Organizer, World and Evidence. Read only admitted current
context. Missing treasury or household-time disclosure means unavailable,
including in the Michigan preset. It never means zero.

Cash belongs to the
collective account, not a personal wallet or the contribution cap. Organizer
hours describe captured commitments. Shared household time describes the
immediately closed period, with the next period unknown. Repeated aid mandates
for one household budget must not add its hours together. Conflicting budgets
or stale, historical or changed-context readings remain unavailable.

The latest closed receipt uses the same period index as the committed organizer
view. The engine's internal next period has a separate index. Reject stale and
future receipts. Period 0 has no closed household receipt.

Use grouped physical quantities and exact common-currency money with a dollar
sign and at least two decimal places: `$1,234.56`, `-$1.20`, `$0.000001`.
Preserve precision below one cent without floating-point conversion. This display does
not convert the common currency to USD. Keep identifiers, dates and hashes exact.

Give comparison cards, All practices and authenticated review one shared short
sentence about intended work. Flavor cannot claim an outcome, consent, named
people or a guaranteed benefit. Paused Hold leaves the pause in place. Opening
inquiries still state that no completed-period report exists. Actual receipts
remain factual. Keep costs, displaced routine, prerequisites and conditional
benefits readable beside the intent.

Play continues authorized standing or default work after each committed period.
It waits for both the current observation and authenticated organizer Status.
It never pipelines advances or resubmits a consumed one-off ruling from a draft.

Advance submits exactly one period and pauses. Speed changes the delay between
ready periods without confirming a ruling. Pause stops future scheduling. An
already detached atomic period can finish once.

Accepted report, inspector, saved-reference, Archive and Review navigation
pauses Play. A rejected stale link and ordinary subject selection leave its
state unchanged. History retains its existing pause. A newly admitted current
City PD notice pauses once with a readable reason in its admitted live context.
Older, repeated, hidden,
foreign or stale notices do not interrupt routine Play. Ordinary automatic
workplace reports do not stop each period.

World's full economy network still requires FullObserver and an exact current
frame. The map lens explains this boundary and opens the existing Observer
Campaigns chooser. An observer campaign uses a separate saved world. The current
organizer world remains available through Continue or Load Game. Opening the
chooser does not replace it or expand player knowledge.

Report reading starts with the selected kind and numerical answer, then the
named source and observed and received periods. A requested report about an
earlier period remains distinct from an automatic current report. Dispatch
shows the actual acquired answer and a dated Read action. That action retains
its exact report identity.

Changing reports starts at the top of one reading region. Return stays fixed and preserves the selected subject and draft.
Notebook controls and exact citation references follow the answer.

World can show current earned workplace reports within the existing organizer
scope when no wider production observation is available. It never fills that gap
from observer access. For an admitted production observation, county developments
use that period's disclosed event descriptions, with History for more records.
An empty event list does not prove that nothing changed.

Archive reading preserves the retained human labels and values. Evidence and
changes shows observed and published dates and retained coverage. A separate
Technical evidence control exposes exact source identifiers, locators, grant
keys, atom changes, hashes and the original publication. The retained reader
has no separate source title or historical display labels. The interface states
that limit. It does not construct titles from keys or later publications.
