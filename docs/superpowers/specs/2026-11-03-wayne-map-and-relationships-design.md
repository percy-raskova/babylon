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

The November 6 approved solidarity loop adds a selected contribution target
and independent food and cash allocations, governed by ADR293.

National contribution input is $1–$1450, initially $280. Food is 0–4 person-period
packages, initially 1. Cash is $0–$1450, initially $0. Zero food and zero cash
cannot form valid aid. These Designed values belong in the national
scenario's existing defines file. Preserve the opening $1 treasury and real
household endowments.

At collection close, the household first covers current goods, its closing
stocks and due payments. For each essential service, count the units the
household paid for across its providers. Each due opening order must match
its own payment and performance records exactly once. If an essential need
remains unmet and the household paid for too few units, the gift stops.
If paid units cover the need but service falls short, the
household keeps the actual refunds for that need alongside its cash floor.

Only the eligible surplus can fund a gift. Consent, pledged hours and actual
available time still apply. This Designed rule uses a Derived refund from the
order's actual postings. The household can use its cash for ordinary purchases
in the next period.

Keep selected amounts distinct from actual amounts. One try can fulfill only
part of a selected leg. The rest ends without retry. Food moves physically.
Cash settles at the existing following-period support close, after ordinary
order admission, and can support ordinary purchasing in the next period.

The first positive received cash or actually consumed food delivery permits
one independent response under existing political and actual-time constraints.
Later arrivals do not retry it. Aid that delivers no support ends with an
explicit no-support result and no coordination cost. Giving and receiving
do not grant reporting rights, participation or membership.

Food qualification assigns bounded consumption credit to each original gift.
For a recipient, good, unit and close, ascending original commitment identity
receives at most its actual granted quantity from the remaining actual
household consumption. The household total stays separate. Two deliveries
cannot both use the same consumed unit.

This deterministic convention survives
receipt reordering and restart. It does not trace parcels or claim that a gift
caused more consumption. Cash still qualifies independently, and a first
response stays final even if a later food delivery receives zero credit.

The backend supplies required allocation identity, selected collection,
independent aid legs, captured initial targets and saved draft/command
construction. Original requests, dispatch facts and the first response remain
available through delayed delivery and restart.

In the national Wayne witness,
the contributing household received seven of eight utility units, kept its
$75 refund and gave $1,450. The organization then gave $1,450 to the local
partner. At the next purchasing close, its household bought eight
manufactured-supply bundles at $147, consumed four and kept four. Its food
need remained unmet.

The partner's reports cover the topics it agreed to
share. Native acceptance and a live campaign remain separate.

A sender can see the original allocation, food movement, actual cash gift
and independent practice response. The partner controls reports about
household consumption, services and available time. The engine assigns
bounded food credit internally to resolve joint work.

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
review. Keep both alternatives' essential comparison visible at ordinary sizes,
including Larger text and long names. Fit the paper to the actual terms and the
map to its remaining scene region. Longer inspector reading uses one region that
scrolls.

Review shows the authenticated actual terms. Review, Confirm and Advance remain
separate actions.
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
ADR294 requires ordinary timing and a separate complete memory member for each
named national workload. Both exercise the same controls, decisions, Play/Pause,
reports, Archive and cold restarts against the same build and captured inputs.
Each owns its database, personal state and verified backup/retirement custody.
Authenticate exact command/receipt/marker joins within each member and compare
actual ordered decision semantics across members, allowing legitimate nonce
differences. Only their final join can qualify. Keep policy v6 limits unchanged,
keep raw captured durations as diagnostics and never subtract imposed freezes.

ADR295 records positive live readiness before private proof. Install the ordinary
restricted frame and keep one accepted strictly actionable organizer status.
Then ask for `await_period_proof` in the existing observation task slot. The
matching material and Aid candidate must join accepted Archive completion.
Actual publication, custody and cursor installation precede local reply queue
acceptance.

Preserve the original clocks, full authentication for cold openings and reopens,
and all independent checks. Both actual positive arrival orders need native
evidence. This adds no player control or mechanic. Source and component checks
do not prove rendered behavior, input acceptance or a human session without
coaching.

The two-period smoke and ten-period walk do not replace 52/325-period or human
acceptance. See the [operator guide](../../how-to/debug-simulation-outcomes.rst)
and [measurement research](../../gameplay/research/39-native-measurement-method-2026-11-09.md).
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

### November 6 native evidence

The [November 6 follow-up evidence](../../../reports/wayne-playtest-followup-2026-11-06.md)
records compiled source `2bd365e98e48541ff37acea2042834a2d18b2ded`. New native
images show both complete alternatives and separate focused period/resource lines.
The wrapped network notice fits at the four actual Standard/Larger settings.
The owned run installed automatic periods 1/2, paused at 2 and stepped once to 3.
It read the exact inquiry with observation at 2 and acquisition at 3.

The Ready Archive page shows observation/publication at 3 and retains the reports'
earlier observation dates. The evidence records full restore equality and exact
fixture retirement. The first November 6 run remains visually limited with
retained period 1 Archive content.

The default atlas is more withdrawn and nearby county labels still crowd. Source
review found the map area, Home and picking consumers aligned. Physical picking
and post-fix human comprehension/enjoyment remain unqualified. Michigan treasury
and household-time bindings remain absent. The next game priority remains a
resource-funded commitment, independent partner response and visible material or
social follow-up. This evidence grants no new mechanic or broader gate acceptance.

### Captured partner reports

The two known aid groups keep their own actor identities when freight is pending or they withhold a report. Each group sets three independent Designed sharing scopes in the national scenario. Receiving a gift and taking part in joint work confer no report authority. An organization page grants access to each acquired report with its own observation ID, source actor, observed period and acquisition period.

A retained report opens its own Archive subject at the inspected period. A saved reference holds only the report ID. When that report leaves the recent view, its link opens the general Wayne Archive at the inspected period. The player can select a known organization to find its older reports. Returning preserves the decision subject and draft.

The opening food assessment compares the pantry stock at capture with the food the household needs. Neither partner asks for cash or quotes a price in this assessment. The opening brief classifies the $280 proposal as Designed. A later sale records its own terms.

A completed food report describes household consumption, unmet need, closing stock and ordinary purchases in the granted food unit. The essential service report names the granted household services and gives performed, satisfied, unmet, unused and expired units with actual settled and refunded cash.

The completed time report deducts the final period's posted contributions once from the residual household hours. Better housing service can coexist with the same residual hours. These Derived reports cover only the named topics. Household materials and unrelated cash uses remain unknown. When a household buys goods with fungible cash, the receipts cannot identify which gift paid for them.

### Choosing the amount

The decision paper keeps the selected group in view. The player can enter a whole-dollar contribution target. The initial target is $280. Compare collection with the current routine. For aid, enter food parcels and whole dollars independently. The two destinations share the same basket.

The entries stay on the screen when the player selects another partner. If the new terms allow those amounts, both cards and the review use them. A positive food amount needs food terms. A positive cash gift needs a cash payer. Notes and citations keep their own place in the draft, even when an amount needs correction before review.

The household owns the pantry. Each parcel that actually leaves costs two household hours. The resources above the map distinguish the treasury, pledged organizer time and dated household time.

A partner report can start a personal proposal and keep its citation. The player can change the amounts, review the terms and confirm the exact command. Advance resolves the next period. A new amount cancels earlier review. An invalid entry keeps the last valid saved basket and requires correction before review.

Cash keeps its dispatch date when food arrives later. The player can read the date of delivery and the date of the first partner response. A partner can respond once to settled cash before freight arrives. The household can buy goods at the next opportunity after settlement. A shared report can tell the player what the household received or consumed. If food in transit can still prompt a response, the player can review a pause in routine work.

A new support result or a first or changed shared shortfall can pause Play. A report with the same unmet quantity can carry a new date without interrupting Play. Reopening a campaign starts from the developments already on record. Independent national windowed qualification and human play remain pending.


## National game grain

The Director approved national coverage with international trade at game resolution on 10 November 2026. This initial
PER-364 candidate still needs performance, native and human acceptance. ADR296 records the decision.
`2026-11-10-national-game-grain.md` supplies the plan.

The Lawverian construction has finite source contributions `C`, representative principals `R` and a total assignment `q:
C -> R`. For each additive same-unit quantity `v`, pushforward sums within its assigned fiber. `sum(q_* v) = sum(v)` and
compatibility with composed regrouping must hold. Test both laws against opening quantities and source incidence.

These laws do not prove `q(T(s)) = Tbar(q(s))` for the old fine economy. Independent balances, supplier ranking, service
complements and finite freight prevent that claim. Grouping implies no automatic adjunction or class theory. Geography
and the dialectic remain unchanged. These authoring constructions add no primitive.

Generate a **Designed representative economy by state and captured freight catchment** before constructing sites,
accounts or relationships. Use current `NationalTransportReference::county_access()`, not historical commuting zones.
Keep all Wayne `26163` and Cook `17031` actors and households detailed. Keep twelve foreign groups and six dependencies
as separate counterparts with unchanged construction. Preserve county geometry and reference observations.

Background workplaces remain independent by catchment, productive function, source ownership and relative labor-reserve
position. Households remain independent by catchment, position and existing `HouseholdBudgetKey`. Keep representative
owners, public/household budgets, time accounts and stocks separate throughout the engine. These new principals replace
background principals. They do not preserve old firms or their behavior.

Do not add employment sharing. The sole completed profile measured 37,019,840 B across two roster arrays and a
0.02645-second incidence fold. The profile did not measure warm-turn performance or peak-copy lifetime. Reduce actual
principals and their supplier, staffing, buying and route relations instead.

### Captured geometry and finite membership

`economic_catalog/national.rs::NationalSources::admit` checks fifteen source kinds. Add no sixteenth dataset.
`national_transport/artifact.rs::decode_captured` validates the complete county-access roster. Each
`CountyTransportAccess` gives a county, three-digit FAF zone and optional airport override.

`tools/national_transport_network.py` and `tools/national_transport_graph.py` construct county→FAF roads, FAF→trunk
roads, finite gateway/terminal pools and airport exceptions. These Designed routes already carry source provenance.

1. Start with all 3,144 admitted counties.

   Refuse missing, duplicate or extra membership. Do not infer historical FIPS replacements.

2. Make Wayne/Cook singleton **detailed** cells.

   Protect every original parent budget, employer, retailer, service provider, public account and named organization
   there. This exceeds the smallest aid-participant closure.

3. Make special-access counties background singletons.

   This applies to any airport override or extra incident county-node edge beyond the captured reciprocal county↔its-FAF
   `local_road` pair. It also applies when the county hosts an Airport/Border/Bulk/Liquid/Marine/Trunk infrastructure
   node. Preserve physical access. These singletons can use representative labels. Do not group them across counties.
   Refuse malformed expected pairs explicitly rather than hiding corruption with singleton fallback.

4. Group remaining counties by `(state FIPS, captured FAF zone)` and apply capacity refinement.

   Cells cannot cross the existing same-state service rule in `opening/markets.rs::service_provider`. Choose each cell's
   real county hub by greatest observed captured population, then ascending `CountyGeoid`. Keep
   `EconomicLocation::County`, its logistics node and original local road. Add no `EconomicLocation::Region`, fake
   county or coordinate rewrite.

5. Derive each county's reserve position against its final cell, after refinement.

   Discard provisional labels. Compare `county.reserve * cell.force` with `cell.reserve * county.force` using checked
   u128 products. Use `force = employed + reserve`. Ordered labels are `NoLaborForce`, `BelowCellReserveRate`,
   `AtCellReserveRate`, `AboveCellReserveRate`. Refuse missing controls. Represent zero labor force explicitly.

   Singletons have one occupied position.

   This allocation stratum preserves reserve-support/payroll exposure. It adds no political/class classifier or response
   curve.

6. Assign each source county once to `(cell, position)`.

   Workplace keys also include `(EconomicFunction, QcewOwnership, ResidentWorkplaceSourceKind)`. Distinguish household
   enterprises, fallback employers and source-QCEW contributions. Household keys add existing `HouseholdBudgetKey`.
   Never combine ordinary/collective, historical earning/non-earning or owner-exposed/non-owner budgets. Use only
   occupied source keys.

   Do not fabricate employers to meet a count. Existing finite primary/secondary domestic/foreign supplier choices still
   apply.

   Set no actor-count cap or promised count. Report candidate cells, protected cells, special-access singletons,
   occupied positions, representative sites/households/member incidences and relations from ordinary construction. Do
   not rerun the baseline. Its 57,238 source cohorts and 60,634 sites do not predict savings. Current state×FAF inputs
   supply total membership, unlike historical commuting zones.

### Explicit source-principal disposition

Each source cohort records a contribution and source ownership. Background cohort IDs become **provenance records**,
without extra live companies or shadow accounts. Assign their population, employment/reserve, additive endowments and
demand once. Each representative receives a new SiteId and its own budget. Future buying, failure, profit and employment
belong to the representative alone. Claim no fine-firm survival, unchanged old/new trajectories or matching old hash.

Background households become Designed counted budgets by cell/position/budget key. Within-cell money, food and time
fungibility is intentional approximation. Different positions, keys and catchments cannot spend each other's resources
without current explicit transfers. Add no national or statewide household cash/pantry. Keep all eight worker-class
controls in source contributions and current Employee/WorkingOwner/UnpaidFamily compensation semantics. Reserve position
does not relabel class.

Background local institutions become **catchment provisioning budgets** with new `(cell, position)` IDs. Do not describe
them as merged legal county governments. Their taxes, reserves, operating grants and ownership follow existing finite
policy within that position. Keep public/private/local/state/federal workplace ownership distinct.

New public site claims belong to that position's public budget. Private claims belong only to its owner-exposed
households. Add no cross-position beneficial ownership unless already explicitly authored. Protect any existing named
political/consent authority outside Wayne/Cook. Remove its contribution exactly once before folding. Location alone
cannot assign it to a representative.

Keep Wayne↔Canada/Japan Designed capital-goods claims because Wayne principals remain protected. The twelve foreign and
six dependency populations, classes, institutions and identities keep their separate construction. Domestic roster
changes can change their trade outcomes.

### Freight and service policy: no capacity windfall

Anchor each representative at its real hub. Use captured routes, finite shared pools, cargo restrictions,
max-period/max-loss composition and actual merchant labor limits. Its freight shares **one original hub access lane**
and ordinary downstream regional/trunk/gateway pools. Keep the hub lane's captured capacity. Do not sum member-county
last-mile lanes or multiply downstream capacity by membership.

This conservative representation does not pool every county lane. Non-road, island and special-gateway counties remain
singletons. Reclassification cannot grant a bulk path or terminal.

Background last-mile activity now occurs at the hub in the model. Do not imply that counties physically moved or
acquired its infrastructure. County dossiers keep source geography and say “economic contribution represented in
[catchment] at [hub]”. Never present hub price/shortage as an observed county outcome. Keep the source graph captured
and inspectable. Unused local source lanes need not create live relations.

Trades among hubs, protected counties and foreign/dependency counterparts consume exact captured finite pools. Same-hub
goods use existing local trade and merchant handling. This local fungibility is a Designed approximation. Services
remain within-state with finite supply and buyer connections. Do not copy availability to every buyer. Occupied
ownership/position keys preserve distinct service producers.

#### Deterministic capacity refinement before fixing the candidate

Run this settled algorithm within membership capture after source allocation and `aid::prepare`, before live actors. Use
captured allocation, household needs, recipes/commodity mass and actual transport links/pools. Add no simulation run,
profile, capacity, optimizer or policy mode.

For each ordinary county `c`, calculate the following quantities.

**`D(c)`:** Recurring household food units, using source household allocation and the captured need's actual
persons/households basis. Count original parent margins once, without adding aid children. Wayne/Cook rows already
remain protected singletons. Current demand is one person-period parcel per person, with food mass `m = 14,000` grams.
Read both from captured policy rather than hard-coding them.

**`H(c)`:** Sum `member.labor_force * work_hours_per_person` across source workplace allocations whose recipe outputs
food. Include reserve and Employee/WorkingOwner/UnpaidFamily members where applicable, once each. Use checked
arithmetic. This optimistic labor ceiling does not predict attendance. Current employment alone, opening pantry/retail
stock, cash and payroll do not measure recurring production.

**`U(S)`:** For a proposed set `S`, use `floor(sum H(c) / food_recipe.labor_hours_per_batch) *
food_recipe.output_units_per_batch`. Admission must confirm exactly one food-producing recipe or return
`UnsupportedEssentialFoodRecipe`. Ignore inputs, services, equipment, reserve activation, protected-time shortfall and
losses for this optimistic upper bound. Unconstrained treatment can only overestimate output. Floor AFTER summing food
hours across sites and future positions. Opening endowments separately preserve per-source floors.

**`L(S)`:** Use `max(0, sum D(c) - U(S)) * m`. Calculate with checked u128 arithmetic and check against finite captured
capacity. This lower bound covers recurring essential import mass only. It excludes intermediate goods, exports, losses
and bidirectional contention. It cannot certify full viability.

**`C(c)`:** Use the lowest finite-pool capacity on the admitted reciprocal county↔FAF local lane. Ordinary-county
admission excludes alternate county access and special gateways, so external food must cross that lane. Confirm
general-cargo compatibility and the same shared pool both ways. Refuse inconsistent capture. Current local roads allow
20,000,000,000 grams per period. Regional/gateway limits remain independent constraints.

Apply these steps to EACH provisional `(state, FAF)` group.

1. Peel off every county with `L({c}) > C(c)` into a singleton.

   Record `PreExistingEssentialAccessDeficit`, its bound and capacity. Preserve scarcity and original access. Do not
   inflate capacity, claim old-economy viability or delete the county. Protected/special singletons stay singleton.
   Record their applicable bound or explicit `NotSingleRoadAccess` reason.

2. Sort remaining counties by descending population, then ascending `CountyGeoid`. Keep bins in creation order.

   For each county, scan bins in that order. Choose the FIRST bin satisfying `L(bin ∪ {c}) <= C(hub(bin))`. Otherwise
   create a singleton bin. Step 1 already admitted its own bound, so no fallback is necessary.

   The first member fixes the hub and capacity. Sorting guarantees greatest population with the canonical tie-break.
   Later counties cannot change either. Recompute candidate bounds from additive D/H totals before every insertion.
   Never backtrack or optimize globally.

3. Sort each final member list by `CountyGeoid` and assign its identity below.

   Recompute reserve positions against final membership. Record D, H, optimistic output U, lower-bound mass L, capacity
   C, members and reason in the witness. Reasons include `FitsCapturedHubAccess`, `CapacitySubdivision`,
   protected/special reasons and pre-existing deficit. Include generation/source-policy digests. Reversed source
   iteration must yield the same sorted input, bins, IDs and labels.

   This is the sole algorithm. A later food-producing county can reduce a bin's deficit. First-fit accepts that
   opportunity only in canonical order. It need not find the fewest hubs.

   A passing lower bound proves neither affordability nor adequate merchant labor, intermediate supply, export capacity
   or shared regional/gateway feasibility. It does not promise practical play or remove source scarcity. Engine
   constraints and prototype acceptance still apply. Refinement prevents a provable new essential-import obstruction
   where replacing independent lanes makes even optimistic recurring demand exceed one hub lane.

   **Unique subgroup identity:** Use `CatchmentKey { state, faf_zone, hub, membership_digest }` for every cell,
   including non-singleton subdivisions. Compute `membership_digest = SHA256(domain_tag || generation_policy_digest ||
   member_count_u32_be || ascending_fixed_width_5_byte_CountyGeoids)`. Membership must be nonempty and unique, and
   include the hub. `CatchmentId` hashes the complete canonical key.

   Do not identify every state×FAF subdivision with `singleton: None`. Distinct disjoint bins have different canonical
   membership bytes. Refuse `CatchmentIdentityCollision` if unequal memberships collide in digest/key. Keep the actual
   member list alongside its digest.

   **Finite RED/GREEN fixture:** Use two ordinary same-state/same-FAF counties, each with D=1,000,000 units and H=0.
   Give each its independent 20,000,000,000-gram local lane and unchanged adequate 200,000,000,000-gram regional
   capacity. Each singleton has L=14,000,000,000. Their union has L=28,000,000,000. Expect two bins, unchanged lane
   IDs/capacities and no multiplier.

   Add four counties, each with D=600,000 and H=0. First-fit must create two multi-county bins, each at 16,800,000,000
   grams. Their keys must differ despite equal state/FAF and the obsolete `singleton=None` identity. Keep an oversized
   singleton with its pre-existing-deficit reason. Cover food surplus and reversed input order. Recompute expected
   reserve labels after splitting.

   Exercise arithmetic/membership through the real post-aid/pre-actors entry point rather than an isolated helper. Run
   no new baseline. This pre-measurement design repair does not consume the ONE correction reserved for measured
   acceptance failure. Include refinement in the initial measured candidate. Report insufficient reduction or poor play
   under the unchanged bound.

   Keep deterministic supplier selection: provider employment rank, SiteId tie-break and buyer-SiteId foreign rotation.
   New representative IDs/sizes create new Designed choices. Capture those relations without claiming old
   ranks/rotations. Foreground IDs remain, but national suppliers can change. This intended counterfactual does not
   alter aid terms.

### Initial quantities and counted incidence

Do not construct and then combine a fine `EconomicOpening`. A bounded county-local allocation pass can calculate source
weights/count tuples without live expansion.

Reuse `allocate_home_county`, including weights, checked apportionment, class controls, household/payee assignment and
synthetic fallback/household-enterprise rows. Preserve its county/member identity staging. Construct empty Builder and
run `aid::prepare` to fix child/parent remapping. Immediately fold source allocation and household/time controls before
`actors::domestic`.

Pass Wayne/Cook rows through with current IDs. Construct no fine opening, financial accounts, markets, routes or runtime
graph. Keep compact immutable assignment/witness as capture provenance, without a second live graph. Account separately
for every county/cohort, fallback and household-enterprise contribution.

For each background `(workplace key, household key, attendance mode)`, create one counted member. Sum employed/reserve
separately. Create one StaffingMemberId/graph subject, StaffingPoolBinding, EmploymentTerms and payee link. Every new ID
digest must include cell and reserve position. Location alone cannot distinguish independent same-hub positions.

Bind the member home to the hub representation. Keep actual county incidence only in the immutable witness. Claim no
fictitious commute. Do not duplicate county worker capacity in the graph.

Sum household persons, households, employed, reserve, eligible16+, inactive, armed and under16 in matching units.
Compile ordinary/collective protected needs from unchanged bases. Put explicit eligible totals in the existing override
map. `opening/household_time.rs` must not reread hub-only eligibility. Sum initial cash, food and protected quantities
under existing authoring.

Do not derive all resources from employer cash. Graph workforce stocks and household hours each keep one live authority.

Generate production through ONE temporary `SourceSeed` at a time. Fold its typed endowments immediately, then drop it.
Do not create a vector of fine `EconomicSiteSeeds`. Preserve authored per-source rounding. Sum `floor(employed *
work_hours_per_person / labor_hours_per_batch)` source batches. Never floor combined hours for opening endowments: that
creates free batches.

Use checked quantities and exact micros for input/output stocks, equipment/nameplate quantities, resource deposits and
opening wage/input cash. Keep units and stock owner keys explicit. Preserve per-source metadata, missing/published
measures and rounding witnesses as immutable evidence. Do not sum means as totals. Employment remains placement
evidence, without counting ACS people twice.

Runtime can then use each representative's shared labor/material pool under current mechanics. This new model does not
preserve later source-site capacity exactly. Audit equations cover opening accounting and current conservation, without
equating old/new trajectories.

### Concrete types and interfaces

The facade `rust/crates/babylon-persistence/src/national_economy/grain.rs` exports the types and implementation from
`grain/build.rs`. Scoped `grain/tests.rs` and `grain/replay_tests.rs` check the fold and ordinary replay. These current
types carry the required data without a generic framework or file per type. Reuse existing allocation/helpers. Expose
one current fold operation without an old-mode switch.

```rust
pub struct NationalGrainPolicy {
    pub protected_counties: BTreeSet<CountyGeoid>,
    pub generation: NationalGrainGeneration, // current StateFafReservePositions
}
pub struct CatchmentKey {
    pub state: [u8; 2], pub faf_zone: [u8; 3], pub hub: CountyGeoid,
    pub membership_digest: [u8; 32],
}
pub enum ReservePosition { NoLaborForce, BelowCellReserveRate, AtCellReserveRate, AboveCellReserveRate }
pub struct RepresentativeWorkplaceKey {
    pub catchment: CatchmentId, pub position: ReservePosition,
    pub function: EconomicFunction, pub ownership: QcewOwnership,
    pub source_kind: ResidentWorkplaceSourceKind,
}
pub struct RepresentativeHouseholdKey {
    pub catchment: CatchmentId, pub position: ReservePosition, pub budget: HouseholdBudgetKey,
}
pub struct CountyContribution {
    pub controls: ResidentCountyAllocation,
    pub destination: ContributionDestination,
}
pub enum ContributionDestination { Detailed(CountyGeoid), Representative { catchment: CatchmentId, position: ReservePosition } }
pub struct NationalGenerationWitness {
    pub source_digest: [u8; 32], pub policy_digest: [u8; 32],
    pub catchments: Vec<CapturedCatchment>, pub counties: Vec<CountyContribution>,
    pub source_incidence: Vec<SourceRepresentativeIncidence>,
    pub member_incidence: Vec<MemberIncidence>,
    pub household_incidence: Vec<HouseholdIncidence>,
}
pub struct NationalOpeningRoster {
    pub workplaces: ResidentWorkplaceAllocation,
    pub households: Vec<OpeningHouseholdAllocation>,
    pub workplace_endowments: BTreeMap<SiteId, OpeningProductiveEndowment>,
    pub representation: NationalGenerationWitness,
    pub financial_domains: BTreeMap<AccountId, FinancialDomainId>,
}

pub fn capture_membership(
    counties: &NationalCountyReference, transport: &NationalTransportReference,
    source: &ResidentWorkplaceAllocation, // existing post-aid source assignment
    households: &NationalHouseholdAllocation,
    aid: &NationalAidCapture, policy: &NationalGamePolicy,
) -> Result<CapturedNationalMembership, NationalGrainError>;

pub(crate) fn coarsen_source_allocation(
    source: ResidentWorkplaceAllocation, // consumed after aid::prepare
    households: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    aid: &NationalAidCapture, policy: &NationalGamePolicy,
    membership: &CapturedNationalMembership,
) -> Result<NationalOpeningRoster, NationalGrainError>;
```

Reuse strong identifiers. New immutable catchment/domain authoring IDs add no simulation primitive. `CatchmentKey`
retains the admitted fixed-width state and FAF source keys. Each `OpeningHouseholdAllocation` carries its principal,
subject, domain, household margins and time allocation. `NationalOpeningRoster` holds no separate household-time vector.

Errors carry the county/key and reason. Preserve `IncompleteCountyMembership`, `UnexpectedAccess`,
`ProtectedContributionOverlap`, `SourceIncidenceMismatch`, `HouseholdMargin`, `ClassMargin`, `TimeMargin`,
`MissingOwnerBudget`, `MissingFinancialDomain`, `UnsupportedGeneration`, `UnsupportedEssentialFoodRecipe`,
`CatchmentIdentityCollision` and `Arithmetic`. Refuse unknown generation without a backward adapter.

Add captured policy in `content/scenarios/national/defines.toml`:

```toml
[grain]
evidence_class = "Designed"
generation = "state_faf_reserve_positions"
protected_counties = ["17031", "26163"]
hub_selection = "largest_observed_population_then_geoid"
access_capacity = "captured_hub_lane"
capacity_refinement = "essential_food_lower_bound_first_fit"
```

These closed tags add no plugin system, threshold or response curve. Preserve numeric game terms. Do not place competing
values in code. Wire typed policy through `national_economy/policy/{game,admission,...}.rs` and the source digest.

Store witness once with admitted source/campaign capture. Regenerate from those bytes on recovery. Authenticate its
digest and check regeneration. Do not repeat county×source incidence in every state/receipt. Receipt source IDs identify
new live principals.

### Files and real consumer path

**`national_resident_allocation/{allocation,households}.rs`:** Preserve allocation and county-based `validate_totals`
where possible. Check source county controls and live pushforward separately. Do not check hub-remapped rows as source
county rows. Expose small helpers if needed rather than rewriting identity staging.

**`national_economy/opening/build.rs`:** Keep `allocate_home_county` → `Builder::new` → `aid::prepare`. Insert
membership capture and `coarsen_source_allocation` before `actors::domestic`, funding, markets, finance and routes. Pass
explicit household identity/time/endowment/domain maps into Builder. Builder constructs the compiler's `EconomicOpening`
from the current roster, without first constructing fine background principals. Bounded assignment remains evidence
rather than a fine opening.

**`opening/actors.rs`:** Consume explicit households and endowments. Representatives use `EconomicSiteSource::Designed`
with a full SiteId-derived key and `source_ownership: Some(QcewOwnership)`. Original detailed fallback,
household-enterprise and external Designed sites keep `None`. Provenance remains Designed. Carry that ownership into
`ActorContext` for public/private finance. `matches!(EconomicSiteSource::Qcew)` alone cannot show ownership.

Representative labels name their function, real hub county and reserve position. World and inspection readings explain
that regional accounts can cover more than one county. Do not describe hub totals as observed county outcomes. Exact
membership must come from the admitted witness.

**Target identity:** Add one representative target constructor using its whole key. Keep exact constructors only for
detailed/external actors.

**`opening/financial.rs`:** Join representative public accounts and private owners by `FinancialDomainId`. Hub
`EconomicLocation` would merge same-hub budgets and owner recipients incorrectly. Display institutions at the hub, with
explicit domain ownership. Preserve detailed/external domain IDs and Wayne cross-border claims.

**`opening/{markets,equipment,routes}.rs`:** Consume only the live roster. Prefer the same financial position when it
has a local retailer. Otherwise use existing finite alternate suppliers. Retail caches must include position/domain
wherever cash or handling authority would collapse. One retailer can serve independent buyers without duplicating its
stock/handling capacity. Keep finite route pools without per-member route expansion.

**`opening/household_time.rs`:** Use exact representative eligibility overrides. Refuse missing overrides rather than
falling through to hub eligibility.

**`opening/aid.rs`:** Preserve exact Wayne/Cook parents, children, contribution budgets and $1 treasury. Food allocation
spans 0–4 units. The $280 default contribution/food price is not the allocation limit. Cash allocation spans $0–$1,450.
The contribution target spans $1–$1,450 and starts at $280.

Food starts at 1 unit and cash at $0. Refuse zero food with zero cash.

Keep 2-hour collection, 2-hour food fulfillment, coordination costs, protected needs and routine/practice time. Preserve
separate report permissions, partner consent/refusal and P+1/P+2 timing.

**`opening/detail.rs` / `national_household_refinement`:** Remove the late “consolidation” claim. Classification can
serve display/foreground selection of already-coarse principals. The generation witness alone owns source-to-live
incidence.

**`economic_catalog/{national,model,compile}.rs`:** Keep the admitted witness in `NationalSources` and return the coarse
`EconomicOpening`. Use ordinary compilation for graph, employment, material catalog, account/policy and routes. Keep no
fine background opening or duplicate register.

Runtime remains `MaterialReplaySession` → detached tick → material state/graph/events/receipts → atomic publication →
existing persistence. Apply current wire schemas, canonical binary encoding, lookup/delta/zstd, replay and restart
admission to the smaller network. The current compiler identity is `national-world-v7`. Admission specifically refuses
v6. Identity changes need fresh campaigns without migration.

### Required scoped read work

The economic candidate reduces full national projection inputs. The read audit confirms that ordinary organizer
advance/briefing uses authenticated `organizer_runtime/{snapshot,material_preview}.rs` and existing world-hash
boundaries. It does not ask for a full national `ProductionSnapshot`. Keep this route without another state/projection
engine.

`observer_material/snapshot.rs::material_observation` constructs all production families through
`production_projection/projection.rs::project_economic_current` for full inspection. `KnownPreview` already avoids this.
Local organizer questions must not create and discard national `DTOs`. Keep the current fields without new
`ProductionReadScope` or `ActorDisclosureScope` types.

Preserve full observer/inspection on demand, causal validation, committed source/receipt bytes, history and
authentication. Keep actor-safe disclosure unchanged when unrelated representative stock or prices change. Full material
and world identities must still change. Do not label a scoped hash as full national production authority. Report
required complete state decode honestly. Scoped reads cannot substitute for smaller actors, states and receipts.

### Executable laws and smallest meaningful checks

Use RED/GREEN for changed contracts. This specification records no completed builds/tests.

1. Check complete county partition and deterministic membership.

   Cover exactly 3,144 keys with one destination each. Exclude protected counties from background sums. Keep
   special-access singletons, exact capacity-first-fit groups/IDs, final reserve labels and transport membership/digest.
   Reversed insertion order must preserve witness/opening bytes.

2. Check source pushforward and per-source floors.

   Reconcile household/person/employed/reserve/eight-class/time totals per county before folding and total margins
   afterward. Sum same-unit endowments. Include nondivisible source floors that fail if applied after grouping. Keep
   unknown/suppressed measures tagged rather than zero.

3. Check classification factorization and finite accounting laws.

   Contributions sharing a representative must agree in retained ownership/function/source-kind/attendance/household
   classes. Reconcile source class totals and live margins. Check `sum(q_*v) = sum(v)` and equality of composed
   regrouping with one pushforward. These laws do not claim `q(T(s)) = Tbar(q(s))`.

4. Check live identity joins and unique ownership.

   Each staffing member has one payee and pool. Employment terms must match force/compensation, with eligible time
   covering force under current rules. Keep no fine background member/site/account live. Instantiate no contribution
   both detailed and representative. Each graph stock has one owner.

5. Check independent budgets through real compile/tick.

   Same-hub positions cannot spend each other's payroll and buying balances or pantry. Public claims, taxes and support
   must reach the correct domain. Check cash/stock/time conservation and atomic refusal beyond helper arithmetic.

6. Check shared freight constraints and merchant labor.

   Two shipments sharing a hub/regional/gateway pool cannot exceed its finite capacity together. Opposite directions
   contend where captured pools specify it. Island bulk still refuses. Gateways remain distinct. Do not sum county local
   capacities. Consume merchant labor once.

7. Check protected foreground opening and funded-loop regressions.

   Compare Wayne/Cook opening identities, budget/food/money/time/aid terms exactly. Later national procurement need not
   match. Exercise collect/local food/remote mixed/routine-during-arrival/cash-only/later buying and independent partner
   refusal through runtime, receipt, replay and restart. Preserve at-most-once nonce/response.

8. Check knowledge and truthful presentation.

   Undisclosed remote changes with unchanged disclosed consequences must preserve actor disclosure. Keep truthful
   cell/provenance labels. Full national observation includes all live principals and source membership. County dossiers
   cannot present hub outcomes as observed county data.

   Run scoped Rust format/tests/Clippy/BSL sentinel and mechanics conformance/replay separately and serially. Generate
   no documentation. Intentional baseline changes need the ceremony and record. Never alter a baseline to hide failed
   conservation or missed performance.
