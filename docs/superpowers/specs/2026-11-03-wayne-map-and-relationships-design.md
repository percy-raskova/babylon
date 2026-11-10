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

The Director approved national coverage with international trade at game resolution on 10 November 2026. This is the initial implementation candidate for PER-364; performance, native and human acceptance remain open. ADR296 records the architecture decision. `2026-11-10-national-game-grain.md` is the implementation plan.

The Lawverian construction uses finite source contributions `C`, representative principals `R`, and a total assignment `q: C -> R`. For an additive same-unit quantity `v`, its pushforward sums only within the assigned fibre. Require `sum(q_* v) = sum(v)` and compatibility with composed regrouping. Test these laws against opening quantities and source incidence. They do not establish `q(T(s)) = Tbar(q(s))` for the previous fine economy: independent balances, supplier ranking, service complements and finite freight defeat that claim. No automatic adjunction or class theory follows from grouping. Geography and the dialectic remain unchanged; these are subordinate authoring constructions.

Generate a **Designed representative economy by state and captured freight catchment**, before site/account/relationship construction. Use the complete current `NationalTransportReference::county_access()` mapping, not an old commuting-zone map. Keep all Wayne (`26163`) and Cook (`17031`) economic actors and households detailed. Preserve the twelve foreign groups and six dependencies exactly as separately generated counterparts. Keep county geometry and all county reference observations available.

Each background catchment has independent representative workplaces by productive function, source ownership and relative labor-reserve position; independent households by the same catchment/position and existing `HouseholdBudgetKey`. Distinct representative owners, public budgets, household budgets, time accounts and stocks remain separate throughout the engine. This replaces background old principals with a newly authored representation; it does not merge preserved firms and then claim unchanged behavior.

Do not add employment sharing to this candidate. The completed single profile measured 37,019,840 B across two retained roster arrays and a 0.02645-second incidence fold, without evidence of material warm-turn benefit or peak-copy lifetime. The chosen implementation reduces actual principals and their large supplier, staffing, purchase and route relation families.

### Captured geometry and finite membership

Existing input authority: `economic_catalog/national.rs::NationalSources::admit` checks the fifteen existing source kinds; no sixteenth dataset is needed. `national_transport/artifact.rs::decode_captured` validates the complete county-access roster. Each `CountyTransportAccess` supplies a county, a three-digit FAF zone and optional airport override. The current transport builder explicitly generates county→FAF local roads, FAF→trunk regional roads, finite gateway/terminal pools and airport exceptions (`tools/national_transport_network.py`, `tools/national_transport_graph.py`). These are already Designed routing constructs with source provenance.

1. Start with every county in the admitted current 3,144 roster. Refuse missing, duplicate or extra membership; do not infer an old FIPS replacement.
2. Make Wayne/Cook singleton **detailed** cells. This deliberately protects more than the minimum aid participant closure: every parent budget, employer, retailer, service provider, public account and named organization in those counties retains its original identity and opening construction.
3. Make a background singleton for every county with an airport override, any extra county-node incident edge beyond the reciprocal captured county↔its-FAF `local_road` pair, or a transport infrastructure node located in that county with kind Airport/Border/Bulk/Liquid/Marine/Trunk. These counties retain their distinct physical access; they may use representative actor labels, but no cross-county aggregation occurs there. A malformed expected pair is an explicit admission error, not a singleton fallback hiding corrupt data.
4. Form provisional groups from remaining counties by `(state FIPS, captured FAF zone)`, then apply the deterministic capacity refinement below. The resulting disjoint cells never cross the current service jurisdiction rule, which permits domestic service selection only within the same state (`opening/markets.rs::service_provider`). Select the cell's **real county hub** by greatest captured observed population, then ascending CountyGeoid. Keep its existing `EconomicLocation::County`, county logistics node and original local-road link. No `EconomicLocation::Region`, fake county or coordinate rewrite is introduced.
5. AFTER capacity refinement fixes final memberships and hubs, derive a labor-reserve position for each county within its final cell. Never retain labels computed against provisional groups. Compare `county.reserve * cell.force` against `cell.reserve * county.force` using checked u128 products; `force = employed + reserve`. The ordered labels are `NoLaborForce`, `BelowCellReserveRate`, `AtCellReserveRate`, `AboveCellReserveRate`. This is an allocation stratum, NOT a new political/class classifier or response curve. Missing controls refuse; zero labor force is explicit. It preserves differing reserve-support/payroll exposure instead of creating one universal background balance. Singleton cells have one occupied position.
6. A source county is assigned once to `(cell, position)`. Live workplace keys add `(EconomicFunction, QcewOwnership, ResidentWorkplaceSourceKind)`. Keep household enterprises, fallback employers and source-QCEW contributions distinguished. Live household keys add existing `HouseholdBudgetKey`, never combine ordinary/collective, historical earning/non-earning, or owner-exposed/non-owner budgets. Multiple occupied positions and ownerships provide independent counterparties where the source supplies them; do not fabricate employers merely to hit a target count. Existing finite primary/secondary domestic/foreign supplier choices still apply.

There is no arbitrary actor-count cap or claim that this yields a particular number. The exact candidate roster is the set of occupied keys. Report the counts of cells, protected cells, special-access singletons, occupied positions, representative sites/households/member incidences and relations from the candidate's ordinary construction; do not rerun the baseline profile. The supplied baseline is 57,238 admitted source cohorts and 60,634 sites; it is not a prediction of savings. State×FAF grouping has actual total membership in current inputs, unlike historical CZs.

### Explicit source-principal disposition

The reference source cohort denotes a source contribution and its source ownership label. In the coarse opening, background source cohort identities are **provenance records**, not additional live companies or shadow accounts. Their population, allocated employment/reserve, additive productive endowment and demand contributions enter exactly one representative. The representative SiteId is new, its budget is its own, and its future purchases, failure, profit and employment apply to that representative alone. No claims that old fine firms independently survived, that fine trajectories commute, or that old hashes match.

Background households likewise become newly Designed counted budgets within cell/position/budget key. Their within-cell money, food and time fungibility is intentional approximation. Different positions, budget keys and catchments remain unable to spend each other's resources without current explicit transfer mechanics. No national or state-wide household pantry/cash account exists. Keep source worker-class controls (all eight classes) in the contribution record; preserve the existing live Employee/WorkingOwner/UnpaidFamily compensation semantics. The reserve-position stratum does not relabel a person's class.

Background local financial institutions become explicitly labeled **catchment provisioning budgets**, with new IDs by `(cell, position)`; they are not claimed to be all the old county governments merged into one legal government. Their taxes, reserves, operating grants and ownership follow the existing finite policy within that position. Retain public/private/local/state/federal source ownership distinctions between workplace keys. New public site claims belong to their new position-specific public budget; private site claims go only to the corresponding position's owner-exposed households. Cross-position beneficial ownership is absent unless explicitly already authored. Any existing named political/consent authority found outside Wayne/Cook must be added to the exact protected closure and its contributions removed once before folding. Do not assign it to a representative by its location alone.

The existing Wayne↔Canada/Japan Designed capital-goods claims remain explicit because all Wayne principals are protected. Existing twelve foreign and six dependency populations, source classes, financial institutions and identities remain separate and unchanged in construction. Their trade outcomes can change with the domestic roster.

### Freight and service policy: no capacity windfall

The live representative is anchored at its real hub. Its logistics use the same captured transport network, existing route algorithm, finite shared pool IDs, cargo restrictions, max-period/max-loss route composition and actual merchant labor limits. Do not sum all member counties' last-mile capacities into the hub or multiply regional/gateway capacity by membership. A catchment's aggregate freight shares its **one original hub access lane** and all ordinary downstream regional/trunk/gateway pools; its capacity remains exactly the captured hub lane capacity. This is deliberately conservative, not 100% pooling of every county lane. Non-road/island/special-gateway counties remain singleton so no bulk path or terminal becomes available by reclassification.

This discards independently simulated background county last-mile activity and represents it at the hub. It does not assert those counties physically moved or acquired the hub's actual infrastructure. Their county dossiers show source geography plus “economic contribution represented in [catchment] at [hub]”; they must not show a catchment price or shortage as an observed individual county outcome. The original source graph remains captured and inspectable; unused source local lanes need not create live economic relations.

Trade paths between different live hubs, protected counties and foreign/dependency counterparts still consume their exact captured finite pools. Same-hub representative goods movements use existing local trade rules and merchant handling; this local fungibility is a declared Designed approximation. Service coverage stays within the state and uses actual finite service supply and buyer connections. No aggregate availability is copied to every buyer. Ownership/position separation prevents one universal service producer where multiple occupied keys exist.

#### Deterministic capacity refinement before the candidate is fixed

Apply this exact algorithm inside membership capture after existing source allocation and `aid::prepare`, before live actor construction. It uses only captured source allocation, household needs, recipes/commodity mass and actual transport links/pools. It adds no simulation run, profile, capacity, optimizer or policy mode.

For each ordinary county `c`, calculate:

- `D(c)`: recurring household food units from its source household allocation and the captured food need's actual persons/households basis. Use original parent margins exactly once, not parent plus aid child. All Wayne/Cook rows are already protected singleton cells. Current captured food demand is one person-period parcel per person; food mass `m` is 14,000 grams. Read both from captured policy, never hard-code them in the implementation.
- `H(c)`: sum `member.labor_force * work_hours_per_person` over source workplace allocations whose recipe outputs the food good. Include reserve workers, Employee/WorkingOwner/UnpaidFamily members where applicable, each once. Use checked arithmetic. This is an optimistic labor ceiling, not predicted attendance. Do not use current employed workers alone, opening pantry/retailer stock, cash or source payroll as recurring production.
- For a proposed set `S`, `U(S) = floor(sum H(c) / food_recipe.labor_hours_per_batch) * food_recipe.output_units_per_batch`. The current policy has one food-producing recipe; require that declared condition at admission or return `UnsupportedEssentialFoodRecipe`. This upper bound ignores inputs, services, equipment, reserve activation, protected-time shortfall and losses; treating them as unconstrained can only overestimate local output. Computing the floor AFTER total food hours is deliberately optimistic across source sites and future representative positions. This capacity bound is separate from opening endowment generation, which still sums the per-source floors exactly.
- `L(S) = max(0, sum D(c) - U(S)) * m`, checked in u128 then checked against the finite captured capacity. It is a lower bound on recurring essential import mass at the chosen grain. It does not include intermediate goods, exports, losses or bidirectional contention. It is not a full viability certificate.
- `C(c)`: minimum capacity among actual finite pools on the admitted reciprocal county↔FAF local access lane. The ordinary-county admission condition already excludes alternate county access and special gateways, so every external food delivery must cross that lane. Confirm general-cargo compatibility and the same shared pool in both directions; reject inconsistent capture rather than invent a road. The current local-road lane is 20,000,000,000 grams per period. Regional/gateway capacities stay additional independent constraints.

For EACH provisional `(state, FAF)` group:

1. Peel off each county with `L({c}) > C(c)` as a singleton. Record `PreExistingEssentialAccessDeficit` and its bound/capacity. This preserves pre-existing scarcity and its original access; it is not a failure that permits capacity inflation, a claim that the old whole economy was viable, or a reason to delete the county. Protected/special-access singleton cells also remain singleton and record their applicable bound or explicit `NotSingleRoadAccess` reason.
2. Sort remaining counties by descending captured population, then ascending CountyGeoid. Maintain bins in creation order. For each county, scan bins in that order; place it in the FIRST bin for which `L(bin ∪ {c}) <= C(hub(bin))`. If none accepts, create a new singleton bin. Its own bound passed step 1, so this step terminates without a fallback. A bin's first member is its hub: descending population order makes that exactly the stipulated largest-population member with canonical tie-break. No later county can change the hub or capacity. Recompute the candidate bound from additive D/H totals before every insertion. Never backtrack or optimize globally.
3. Canonicalize each final member list by CountyGeoid and assign its identity as described below. Recompute reserve positions against THIS final membership. Record final D, H, optimistic output U, lower-bound mass L, capacity C, member list and reason (`FitsCapturedHubAccess`, `CapacitySubdivision`, protected/special reason or pre-existing deficit) in the existing witness. Include the generation/source-policy digest. Reversed source iteration produces the same sorted input, bins, IDs and labels.

This is the one settled capacity-aware partition algorithm, not an alternative mode. A later food-producing county can reduce a bin's deficit; first-fit accepts that opportunity only in canonical order. It need not find the fewest hubs. An accepted lower bound does **not** prove affordability, sufficient merchant labor, full intermediate supply, export capacity, shared regional/gateway feasibility, or practical gameplay. Those remain real engine constraints and prototype acceptance questions. Do not promise elimination of source scarcity. This refinement specifically prevents a provable new essential-import obstruction from replacing independent ordinary local lanes by one lane when the optimistic recurring deficit already exceeds its capacity.

**Unique subgroup identity:** every catchment, including a non-singleton subdivision, uses `CatchmentKey { state, faf_zone, hub, membership_digest }`. Compute `membership_digest = SHA256(domain_tag || generation_policy_digest || member_count_u32_be || ascending_fixed_width_5_byte_CountyGeoids)`; require nonempty membership, unique members and hub membership. `CatchmentId` hashes the canonical complete key. Do not use `singleton: None` as the identity of all state×FAF subdivisions. Distinct disjoint non-singleton bins have distinct canonical membership bytes; on any digest/key collision with unequal membership, refuse `CatchmentIdentityCollision`. Keep the actual list alongside its digest so a hash is not the only membership witness.

**Finite RED/GREEN fixture:** two ordinary same-state/same-FAF counties each have D=1,000,000 food units and H=0, with independent 20,000,000,000-gram local lanes and sufficient unchanged 200,000,000,000-gram regional capacity. Each singleton has L=14,000,000,000; their proposed union has L=28,000,000,000. Require two bins, original lane identities/capacities and no capacity multiplier. Add four counties with D=600,000/H=0 each: first-fit makes two multi-county bins (16,800,000,000 each), and their keys must differ despite identical state/FAF and `singleton=None` in the obsolete design. Include a singleton whose own bound exceeds its lane: retain it with the pre-existing-deficit reason. Include food surplus and input-order reversal cases; recompute expected reserve labels after the final split. These fixtures exercise arithmetic and membership via the real post-aid/pre-actors folding entry point, not a disconnected helper. No new baseline run is needed.

Pre-measurement correction of this identified design hole does not consume the ONE corrective iteration reserved for measured acceptance failure. The initial measured candidate includes this deterministic refinement from the start. If it yields too little structural reduction or poor gameplay, report that result under the unchanged bounded contract.


Supplier selection remains the current deterministic algorithm: provider employment rank and SiteId tie-break, foreign rotation from buyer SiteId. New representative IDs and employment sizes therefore create new Designed supplier choices. Capture the resulting relationships; do not claim unchanged old ranks/rotations. Foreground actors retain IDs; their upstream national choices may change, which is an intended national counterfactual, not a rewrite of their aid terms.

### Initial quantities and counted incidence

Do not generate the full fine `EconomicOpening` then consolidate it. A bounded county-local source allocation pass may calculate old source weights and count tuples; this is not live economic expansion.

Reuse `allocate_home_county` as the bounded source-assignment roster; do not rewrite its county/member identity staging. Its existing weights, checked apportionment, class controls, household/payee assignment and synthetic fallback/household-enterprise rows are the exact provenance needed. Construct the empty Builder and run existing `aid::prepare` first, establishing child/parent remapping exactly. Immediately AFTER aid preparation and BEFORE `actors::domestic`, fold this source allocation plus household/time controls into representative keys. Wayne/Cook rows pass through with current IDs. No fine EconomicOpening, financial accounts, markets, routes or runtime graph is created. Retain compact immutable source assignment/witness as capture provenance, never as a second compiled live graph. Account every source county/cohort and synthetic fallback/household-enterprise contribution separately.

For each background `(workplace key, household key, attendance mode)` produce one counted live member. Sum employed/reserve independently and create one new StaffingMemberId/graph subject, StaffingPoolBinding, EmploymentTerms and payee link. Include cell and reserve-position in every new ID digest; EconomicLocation alone is insufficient because multiple independent positions share a hub. Bind member residence to the hub representation, and retain its actual county incidence only in the immutable source-contribution witness. Do not claim a fictitious commute or retain duplicate county worker capacity in the runtime graph.

For households, sum same-unit counts: persons, households, employed, reserve, eligible16+, inactive, armed and under16. Compile ordinary/collective protected needs from their unchanged bases. Put explicit aggregate eligible counts in the existing eligibility override map so `opening/household_time.rs` does not accidentally reread only the hub county's eligible population. Sum household initial cash/food and protected quantities under existing authoring; do not derive all household resources from employer cash. Graph workforce stocks and household available hours each have exactly one live authority.

For production, reuse existing formulas through ONE ephemeral `SourceSeed` at a time, fold its typed endowments immediately, and drop it. Do not create a Vec of fine EconomicSiteSeeds. Preserve sums of the per-source authored opening quantities where rounding matters. In particular, compute each source site's `floor(employed * work_hours_per_person / labor_hours_per_batch)` and sum those batches; do not replace it with floor of aggregate hours, which would create free opening productive batches. Sum authored input/output stocks, equipment/nameplate quantities, resource deposits and opening wage/input cash using checked quantities and exact micros. Keep additive units and stock owner keys explicit. Per-source metadata, missing/published measures and remainder witnesses remain immutable source evidence. No mean is summed as a total; source employment is still placement evidence, not double-counted ACS people.

Runtime production may thereafter use the representative's shared labor/material pool under current mechanics. This is the declared new model, not a promise of subsequent source-site capacity equivalence. Audit equations cover opening source accounting and current engine conservation; they do not equate the old and new dynamic trajectories.

### Concrete types and interfaces

Add `rust/crates/babylon-persistence/src/national_economy/grain.rs` with scoped `grain/tests.rs`. Keep membership, keys and folding together initially; split only if actual code size/cohesion warrants it. The types below specify necessary typed data, not a generic framework, one file per type or a required public API. Reuse existing source allocation/helpers. Expose one current fold operation, no old-mode switch.

```rust
pub struct NationalGrainPolicy {
    pub protected_counties: BTreeSet<CountyGeoid>,
    pub generation: NationalGrainGeneration, // current StateFafReservePositions
}
pub struct CatchmentKey {
    pub state: StateFips, pub faf_zone: FafZone, pub hub: CountyGeoid,
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
    pub county: CountyGeoid, pub destination: ContributionDestination,
    pub controls: ResidentCountyAllocation,
    // Typed source workplace/endowment and household/time contributions, canonical order.
}
pub enum ContributionDestination { Detailed(CountyGeoid), Representative { catchment: CatchmentId, position: ReservePosition } }
pub struct NationalGenerationWitness {
    pub source_digest: [u8; 32], pub policy_digest: [u8; 32],
    pub catchments: Vec<CapturedCatchment>, pub counties: Vec<CountyContribution>,
    pub source_incidence: Vec<SourceRepresentativeIncidence>,
}
pub struct NationalOpeningRoster {
    pub workplaces: ResidentWorkplaceAllocation,
    pub households: Vec<OpeningHouseholdAllocation>,
    pub household_time: Vec<OpeningHouseholdTimeAllocation>,
    pub workplace_endowments: BTreeMap<SiteId, OpeningProductiveEndowment>,
    pub representation: NationalGenerationWitness,
    pub financial_domains: BTreeMap<AccountId, FinancialDomainId>,
}

pub fn capture_membership(
    counties: &NationalCountyReference, transport: &NationalTransportReference,
    source: &ResidentWorkplaceAllocation, // existing post-aid source assignment
    households: &NationalHouseholdAllocation,
    protected: &ProtectedOpeningSelection, policy: &NationalGamePolicy,
) -> Result<CapturedNationalMembership, NationalGrainError>;

pub(crate) fn coarsen_source_allocation(
    source: ResidentWorkplaceAllocation, // consumed after aid::prepare
    households: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    aid: &NationalAidCapture, policy: &NationalGamePolicy,
    membership: &CapturedNationalMembership,
) -> Result<NationalOpeningRoster, NationalGrainError>;
```

Use existing strong identifiers where they exist; new catchment/domain IDs are immutable authoring identifiers, not simulation primitives. `StateFips`/`FafZone` are validated wrappers if no existing type matches. Error variants carry a county/key and reason: `IncompleteCountyMembership`, `UnexpectedAccess`, `ProtectedContributionOverlap`, `SourceIncidenceMismatch`, `HouseholdMargin`, `ClassMargin`, `TimeMargin`, `EndowmentUnit`, `MissingOwnerBudget`, `UnsupportedGeneration`, `UnsupportedEssentialFoodRecipe`, `CatchmentIdentityCollision`, `Arithmetic`. Refuse unknown policy generation; no backward adapter.

Add captured content in `content/scenarios/national/defines.toml`:

```toml
[grain]
evidence_class = "Designed"
generation = "state_faf_reserve_positions"
protected_counties = ["17031", "26163"]
hub_selection = "largest_observed_population_then_geoid"
access_capacity = "captured_hub_lane"
capacity_refinement = "essential_food_lower_bound_first_fit"
```

These are closed policy tags, not an extensible plugin system. Preserve all numeric game terms. No new thresholds/response curves; no values in source code that compete with defines. Wire the typed policy through `national_economy/policy/{game,admission,...}.rs` and captured source digest. Store witness once with admitted source/campaign capture and regenerate from those bytes on recovery; do not repeat the county×source incidence list in every material state or receipt. Authenticate its digest and validate regeneration. Receipt source IDs refer to the new live principals.

### Files and real consumer path

- `national_resident_allocation/allocation.rs`, `households.rs`: preserve the existing source allocation and its county-based `validate_totals` where possible. The new fold separately validates source county controls and live member pushforward; never run location-based source validation on hub-remapped rows. Small helper visibility extraction is sufficient if needed; no deep identity-staging rewrite.
- `national_economy/opening/build.rs`: retain `allocate_home_county` → `Builder::new` → `aid::prepare`; insert membership capture plus `coarsen_source_allocation` immediately AFTER aid preparation and BEFORE `actors::domestic`, funding, markets, finance and routes. This is pre-live-economic-expansion: bounded source assignment is evidence, not a fine EconomicOpening. Pass explicit household identity/time/endowment/domain maps into Builder. Only the generated current roster reaches the economic compiler.
- `opening/actors.rs`: consume explicit opening households and representative endowments; set `EconomicSiteSource::Designed` with witness key for representatives. Do not use `matches!(EconomicSiteSource::Qcew)` as the only source-ownership check: explicit retained `QcewOwnership` must reach `ActorContext` for representative public/private finance. Labels say “representative [function] — [catchment/position]”, not “[hub] observed workplace.”
- `national_economy` target-identity definitions: add one current representative target constructor using the whole key. Existing exact constructors remain for detailed/external actors only.
- `opening/financial.rs`: key representative public accounts and private owners by `FinancialDomainId`, not hub `EconomicLocation`. Otherwise same-hub positions silently merge budgets and share owner recipients. Institution display locations remain the hub; financial ownership uses explicit domain. Preserve detailed and external domain IDs and Wayne cross-border claims.
- `opening/markets.rs`, `equipment.rs`, `routes.rs`: consume only generated live roster. Prefer same financial position where a corresponding local retailer exists; use existing finite alternate supplier policy for other trades. Retail selection caches must include representative position/domain where household cash/handling authority would otherwise collapse. A selected retailer can serve multiple independent buyers, but its own stock/handling capacity is never duplicated. Preserve exact finite route pools, no per-member route expansion.
- `opening/household_time.rs`: use exact captured overrides for representative households; refuse any missing override instead of falling through to hub county eligibility. `opening/aid.rs` remains exact for Wayne/Cook parents, children and contribution budgets, including the $1 treasury, food allocation 0–4 units (280 is the food price/default contribution, not the allocation limit), cash allocation 0–1450 and cash target 1–1450, protected needs, routine/practice time, separate report permissions, partner consent/refusal and P+1/P+2 timing.
- `opening/detail.rs` / `national_household_refinement`: retire the misleading late “consolidation” claim. It can classify the already-coarse current principals for display/foreground selection, but the generation witness owns source-to-live incidence. Do not preserve two competing national-generation authorities.
- `economic_catalog/national.rs`, `model.rs`, `compile.rs`: admit and retain witness in `NationalSources`, return the coarse `EconomicOpening`, and use the ordinary compiler for graph, employment, material catalog, account/policy and route creation. No fine background `EconomicOpening` or duplicate register is retained.
- Ordinary runtime remains `MaterialReplaySession` → detached tick → material state/graph/events/receipts → atomic publication → existing persistence. Current wire schemas, canonical binary encoding, lookup/delta/zstd, replay and restart admission apply to the smaller real network. Identity changes require fresh campaigns, no migration.

### Minimum scoped read work

The initial economic candidate already reduces full national projection inputs. Also remove any unnecessary full `ProductionSnapshot` request from the ordinary organizer advance/briefing path: use authenticated `organizer_runtime/snapshot.rs` and `organizer_runtime/material_preview.rs` disclosures, committed organizer/gift/time facts and world-hash boundary already available. Keep this a routing change through current actor disclosure, not a second state/projection engine.

`observer_material/snapshot.rs::material_observation` currently constructs all production families via `production_projection/projection.rs::project_economic_current`; `KnownPreview` already avoids it. An organizer-local question must not create a full national DTO solely to discard it. If a missing field requires projection, add a typed `ProductionReadScope::Actor(ActorDisclosureScope)` at that shared projection boundary and select rows by the authenticated disclosed principals plus incident orders/routes, before expensive family DTO allocation. Do not filter only after building all families. The scope is server-derived, never an arbitrary client list that widens knowledge. Full national observer/inspection continues using `National`; evidence hashing binds the actual selected disclosure and scope. Do not relabel a scoped result as the full national production hash. Full observer still has authentic national inspection on demand.

No change to causal validation, committed source/receipt bytes, stored history or authentication is authorized by scoping. A complete state decode may still be required by current authentication; report it honestly. This work is secondary and cannot substitute for reduced actors/state/receipts.

### Executable laws and smallest meaningful checks

Use RED/GREEN for these changed contracts. No builds/tests were run for this spec.

1. Complete current county partition: exactly 3,144 admitted keys, each one destination, protected counties excluded from background sums, special-access counties singleton, capacity-aware first-fit subgroup membership and IDs exact, reserve labels recomputed against final groups, captured transport membership/digest exact. Reversed input insertion order yields identical witness and opening bytes.
2. Source pushforward: for each county, source household/person/employed/reserve/eight-class/time totals reconcile before folding; aggregate totals reconcile after folding. Sum same-unit source endowments and show the per-source floor case that would fail if floor moved after grouping. Unknown/suppressed source values remain tagged, not zero.
3. Classification factorization: if two contributions share a representative, their retained ownership/function/source-kind/attendance/household classes agree. Source class totals and each live class margin agree. For additive measure v and grouping q, `sum(q_*v) = sum(v)` and composed regrouping has the same total as one pushforward. These are finite accounting laws, not `q(T(s)) = Tbar(q(s))`.
4. Live identity joins: every staffing member has one household payee and pool, aggregate employment terms exactly match member force/compensation, eligible time covers force with current rules; no fine background member/site/account remains live. No source contribution is instantiated both detailed and representative. Every runtime graph stock has its one current owner.
5. Independent budgets: two same-hub positions with different balances cannot fund each other's payroll/purchases; public claims/taxes/support go to the correct domain. Cash/stock/time conservation and atomic refusal hold through real compile/tick, not just helper arithmetic. A starving position must not use another position's pantry.
6. Freight counterexample: two representative shipments share a finite original hub/regional/gateway pool; their combined serviced mass cannot exceed it. Opposite directions contend where current source pools say so. Island bulk still refuses; different gateways remain distinct; no capacity sum from multiple county local lanes. Local merchant labor is consumed once.
7. Foreground regression: compile Wayne/Cook pre/post candidate and compare protected opening identities, budget/food/money/time/aid terms exactly. Do not require identical subsequent national procurement trajectories. Run existing funded collect/local food/remote mixed/routine during arrival/cash-only/subsequent purchase and independent partner refusal tests through actual runtime, receipt, replay and restart paths; at-most-once nonce/response remains unchanged.
8. Knowledge and presentation: changing an undisclosed remote representative without changing disclosed consequences leaves the actor disclosure identical; declared source provenance/cell labels remain truthful. Full national observation includes all current live principals and source membership; county dossier never presents hub outcome as county-specific observed data.

Existing scoped Rust format/tests/clippy/BSL-sentinel and mechanics conformance/replay gates apply separately and serially. Do not generate documentation. Any intentional baseline change uses the repository ceremony and required record; do not modify a baseline merely to hide failed conservation or a performance miss.
