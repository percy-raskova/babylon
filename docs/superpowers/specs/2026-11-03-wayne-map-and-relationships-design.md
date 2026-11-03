# Wayne map and relationships: design

**Status:** Approved on 2026-11-03. The Director's exact decision was
“Approve this design and limited disclosure”. This approves the design and
the limited visibility ruling below. It does not prove native behavior or
accept a game gate. The finite PER-336 closeout remains a prerequisite to
implementation.

The earlier v3 interactive preview received “i feel like this
is great!” from the Director. That preview was visual evidence.

**Scope:** PER-292's bounded national Wayne organizer experience. This design uses
`d2b8ea14d` plus Task 7e under repair as context. That work is not yet a
qualified base. PER-336's finite Wayne closeout precedes this
implementation. Neither this design nor that prerequisite claims the PER-355
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

Keep the captured 2-hour practice and 2-hour cycle capacity. Show displaced
standing neighborhood work when applicable, independent partner response, and
report timing from the actual view. In period 0 no
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
