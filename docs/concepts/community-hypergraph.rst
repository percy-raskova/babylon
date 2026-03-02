Community as Hyperedge
======================

Why Babylon represents community membership with XGI hyperedges instead
of NetworkX edges, and what this means for solidarity computation,
state repression, and the simulation's ontology.

The Ontological Distinction
---------------------------

The Babylon simulation maintains two graph structures that model two
fundamentally different kinds of relationship:

**NetworkX edges** represent flows between exactly two entities. Value
extraction, solidarity transmission, repression, wages, tribute --
these are directional relationships where one entity acts on another.
Edge modes (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC)
and contradiction internals live here.

**XGI hyperedges** represent membership -- multiple entities belonging
to something together. Community, identity category, organizational
affiliation. A community is not a relationship between agents. It is
a thing agents are part of.

This distinction is ontological, not technical. Consider:

- "Agent A extracts value from Agent B" is a **flow** between two
  entities. It belongs in NetworkX.
- "Agents A, B, C, and D are all members of the Black church in
  Detroit" is **membership** in a collective structure. It belongs
  in XGI.

The reason this matters: the FBI did not surveil individuals who
happened to share attributes. COINTELPRO designated "Black Nationalist
Hate Groups" as a category and targeted the *community as a unit*.
This operation has no natural representation as modifications to
1,225 individual pairwise edges. It is one operation on one hyperedge.

Why Not Pairwise Edges?
-----------------------

The naive alternative -- representing a community of N members as
N*(N-1)/2 pairwise edges -- fails in three ways:

**Combinatorial explosion.** A community of 50 members produces 1,225
edges. A community of 500 produces 124,750. The graph becomes dominated
by community-membership edges that obscure the actual flow relationships
the simulation needs to compute.

**Lost collective semantics.** A clique of pairwise edges has no identity.
You cannot ask "what is the legal status of this community?" because
there is no community object -- only a pattern of edges. State repression
targeting a community requires iterating over the clique and modifying
each edge individually, with no guarantee of atomicity.

**Wrong ontology.** Community membership is not a relationship between
agents. It is a property of the collective structure. Two agents sharing
three community memberships does not mean they have three pairwise
relationships -- it means they are co-members of three collectives.
The distinction between potential (overlap) and actuality (solidarity
edge) is lost when both are represented as edges.

Overlap Creates Potential, Not Actuality
----------------------------------------

The most important design consequence of the hypergraph layer: community
overlap creates *solidarity potential*, not solidarity itself.

Two agents who share three community memberships have high overlap. This
means conditions exist for solidarity formation. But solidarity only
becomes real when organizing work -- a player verb (Educate, Aid,
Mobilize) -- creates or transforms a NetworkX SOLIDARITY edge between
them.

This implements a core theoretical commitment: material conditions
constrain but do not determine (Constitution I.7). Shared identity
creates the *possibility* of solidarity. Organization realizes it.

The formula penalizes solidarity potential by imperial rent differential.
Two agents who share community memberships but occupy vastly different
positions in the rent extraction hierarchy (one receives full imperial
rent, the other receives none) have reduced potential. Material
divergence impedes solidarity even with shared identity.

This is the labor aristocracy mechanism applied to community: shared
identity across the imperial divide does not automatically produce
solidarity. The white working class and the Black working class share
class position but differ in rent access. Community overlap exists;
solidarity potential is penalized.

State Repression of Collective Structures
-----------------------------------------

The hypergraph layer makes state repression mechanically coherent.
When the state designates a community as extremist:

1. The community's ``legal_status`` escalates (one-way ratchet)
2. All members' ``threat_score`` increases based on their visibility
3. Community ``infrastructure`` degrades (mutual aid, meeting spaces)
4. Members' ``reproduction_cost`` rises (loss of community support)

The state targets the hyperedge. The effects propagate to all nodes
(members) contained in it. This is a collective action against a
collective structure -- not 50 individual actions against 50 individuals.

Legal status escalation is one-way for the state. The state ratchets
up: LEGAL, SURVEILLED, DESIGNATED_EXTREMIST, DESIGNATED_TERRORIST,
CRIMINALIZED. Only player political struggle can reverse the escalation.
This reflects the historical reality: once the state designates a
community, that designation does not spontaneously expire.

Update Frequencies
------------------

The two layers update at different rates, reflecting the different
stability of what they model:

- **NetworkX edges** update per tick. Value flows, solidarity
  transmission, and repression are dynamic processes.
- **XGI hyperedges** update via alpha-smoothing. Identity and
  membership are stable -- they drift slowly, changing only through
  rare discrete events (disability onset, documentation status change,
  coming out).

Community state (heat, cohesion, infrastructure) also decays via
alpha-smoothing. Infrastructure decays naturally without maintenance --
CORE_ORGANIZER members counteract decay, but communities are not
self-sustaining. They require active organizing work.

This implements Constitution I.8 (Tragedy of Inevitability): existence
costs calories. Communities, like everything else in the simulation,
tend toward entropy without active maintenance.

Structural Differentiation (Feature 029)
-----------------------------------------

Feature 029 extends the hypergraph layer by differentiating community
hyperedges into three structural categories: **contradiction pairs**
(both hegemonic and marginalized sides exist as real hyperedges),
**institutional exclusion** (only the marginalized side organizes),
and **lifecycle phases** (universal temporal positions in the D-P-D'
circuit).

This taxonomy enables:

- **Contradiction axes** that formalize extraction relationships between
  hegemonic and marginalized communities
- **Community consciousness** modeling the ideological dimension of each
  hyperedge (collective identity, dominant tendency, contestation)
- **Infiltration resistance** derived from consciousness and cohesion
- **Cross-class bridge detection** where institutional exclusion
  communities span contradiction axes

See :doc:`consciousness-taxonomy` for the full theoretical treatment.

See Also
--------

- :doc:`consciousness-taxonomy` -- Three-category taxonomy and consciousness model
- :doc:`/reference/community-system` -- Complete API reference
- :doc:`topology` -- NetworkX graph model and solidarity networks
- :doc:`george-jackson-model` -- Bifurcation and solidarity routing
- :doc:`imperial-rent` -- Rent differential and labor aristocracy
- :doc:`unified-class-system` -- Filtration predicates and
  class-pair solidarity matrix
