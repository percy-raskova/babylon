# First state opponent: City PD observation contract

**Status: Director-approved contract, 2026-10-29; first PD integration delivered,
acceptance closeout in progress on 2026-11-04.** The
Director approved this first opponent contract on 2026-10-29. ADR291 records the
approved political content and its bounded footprint; schema and conformance
changes must accompany implementation. This first witness does not complete the
PER-355 14-cell acceptance or redefine the full active Goal.

## Decision and authority

The player should be able to recognize a state organization observing known
public organizing, understand an observed encounter, and decide what to do next.
The first opponent is a Designed City PD unit with its own known cases, finite
means, and objective: complete documentation of known public organizing
activity. It has independent authority and an objective of its own. Its
decisions, resources, and knowledge can respond to player acts that the agency
lawfully observes, including in counterfactual runs.

Constitution Articles III and V require eligible actors, costs, next-period
material effects, lawful knowledge, receipts, determinism, and atomic commits.
Article VIII requires Director ceremony, schema and conformance updates, and a
recording ADR for new governed political vocabulary. The current intent
allowlist admits only `organizer/organizer-practice` (ADR262), not this action:
`rust/crates/babylon-bsl/src/causal_contract.rs`. ADR184 establishes
organization-owned capacity and dossiers; it does not authorize an unlisted
political effect. `docs/gameplay/research/17-serge-sparrow-rand-and-bonapartist-state-ai.md`
and `docs/gameplay/2026-10-25-porch-02.md` are design evidence, not live law.

## Director-approved terms

- `OBSERVE_PUBLIC_ACTIVITY`: a priced, overt visit to an already-known,
  in-jurisdiction public organizing activity. Its sole knowledge effect is to
  add eligible, provenance-bearing public facts actually available at that
  visit to the acting agency's private case and dossier. A visit can produce
  no new facts. It does not authorize a search of private contacts.
- `AgencyAppropriation`: a declared public-account-to-agency-account allocation
  for a named agency. It competes with other captured allocations according to
  their explicit priorities and available public funds.
- Investigator payment and attendance: reserve and pay a named investigator's
  positive wage from the agency account to a bound household account, and debit
  the investigator's finite, eligible attendance. A funded shift is a possible
  implementation if its existing contract can represent that binding; the
  implementation must prove the actual source, recipient, hours and payment.

These terms authorize no arrest, repression, seizure, informant, guaranteed
discovery, political outcome, or automatic relationship change. They add no
heat scalar, primitive, fixed response curve, or scripted endgame. Ordinary
ledger and deterministic scheduling changes do not themselves settle political
authority. ADR291 records the Director's approval of this exact political
intent, knowledge and material footprints, and disclosure rules.

## Captured content and prerequisites

Capture a Designed City PD organization and jurisdiction, organization account,
public payer and authority, one investigator and household account, available
attendance, appropriation terms, wage, overt-visit cost, and agency objective.
Capture actor-owned case records identifying already-known public organizing
activity, the source and period of each lead, eligible public observations,
and lawful witnesses. Each fact has provenance and an explicit visibility scope.
Values are Designed or taken from existing sourced wage or service values with
their source and vintage; fictional actors and bindings are not observed claims.

The national financial opening currently creates public accounts by economic
location, including county locations. A Wayne county-scoped account is not a
literal city treasury. For this witness, use the Wayne county-scoped public
account as an explicitly Designed fiscal proxy for the City PD appropriation.
The account remains county-scoped and is not a claim about a literal municipal
treasury. Current public allocations admit household support and provider
grants, not organization recipients
(`rust/crates/babylon-material-circuit/src/financial/validation.rs`). No live
PD actor, appropriation binding, investigator attendance, case producer, or
eligible observation source has been established for this witness.

## Period, knowledge, and material contract

At committed T, the PD considers only its own open, in-jurisdiction case leads
already present in its dossier. Rank eligible `OBSERVE_PUBLIC_ACTIVITY`
candidates by the Designed expected completion of one known case record per
unit of positive cost through its own `Capacity`. No current hidden edge,
unknown actor, hidden node attribute, or player's undisclosed intent affects
candidate selection, price, ranking, or the observation preview. An empty
candidate set means no action. Deterministic decisions generate T+1 intents;
they do not change T material state.

Use the same committed T snapshot for player and agency decisions. At T+1,
resolve due claims in captured priority and stable identity order against the
real available account balances and finite attendance, with no duplicate
principal or double spending. Public appropriations occur at financial opening;
current-period taxes collected later cannot finance that opening. Funding must
come from opening cash or earlier committed receipts. The PD starts with zero
cash and no opening transfer. The ordinary first-period appropriation can be
partial or zero; only its committed result can support a period-2 visit. A
failure or shortfall is explicit and must not invent a completed visit.

The only permitted writes are: a conserved public-to-agency appropriation;
the agency-to-investigator wage and attendance use; the agency's private case,
eligible observed facts and dossier updates; the action's typed receipts and
audit evidence; and any resulting ordinary public-allocation receipts. There is
no authoritative write to the player's relationships or hidden knowledge.
The player sees the visit only through a disclosed witness or venue observation;
neither that receipt nor an unavailable response exposes the agency's case list,
private dossier, undisclosed subjects, or hidden graph shape. A public-budget
receipt reports actual paid and unfunded amounts within its own disclosure scope.

Captured definitions, actor-specific private state, pending intents, balances,
resource use and receipts must participate in canonical world identity and the
same detached tick, Postgres commit, restart and publication boundary as the
organizer. The topology consumes disclosed receipts and retained identities;
it does not create authority, simulate outcomes or bypass fog.

## Acceptance evidence

- A normal campaign runs the PD witness through reviewable input, T+1 action,
  durable commit, player-visible encounter, and restart; a no-PD control shows
  the actual budget consequence without forcing a particular political result.
- Vary unknown edges, attributes and actors while holding the PD's dossier and
  public facts fixed: candidates, rankings, action and disclosed receipt stay
  identical. Separate agencies can hold different beliefs about the same graph.
- Permute case, actor and input order: canonical decisions, postings, receipts
  and world hash match. No known lead, insufficient funds, insufficient time,
  and an unproductive visit each produce their honest distinct result.
- Reconcile every appropriation and wage with two-sided postings, balances,
  finite hours and allocation receipts. Demonstrate a shared-budget shortfall
  only when the captured resources and priority actually cause it.
- A failed or ambiguous commit exposes no partial tick; committed save/restart
  reproduces private cases, pending intents, accounting and receipts. The
  player projection does not reveal an undisclosed agency target or dossier.
