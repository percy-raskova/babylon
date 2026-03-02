The Organization Model
======================

Why Babylon models organizations as four frozen Pydantic subtypes with
emergent topology, composition calculators, and a five-factor consciousness
effect formula.

.. contents:: On this page
   :local:
   :depth: 2


Why Four Subtypes?
------------------

The Babylon simulation does not treat organizations as a homogeneous
category. A police department, a factory, a revolutionary party, and a
church are fundamentally different kinds of social formations with
different relationships to the means of production, the state, and
the ideological apparatus. Collapsing them into a single ``Organization``
class would force every consumer of organization data to manually
distinguish subtypes through ad-hoc field checks.

The four subtypes derive from class analysis:

**StateApparatus** wields the monopoly on legitimate violence. It holds
jurisdiction, surveillance capacity, and legal authority. Its default
legal standing is SOVEREIGN -- it is the state. The defining attribute
is that it can coerce.

**Business** accumulates capital and employs labor. Its relationship to
communities is mediated through employment: a factory that employs 30%
of a town's workforce has leverage that does not come from ideology or
legitimacy but from material dependence. Business credibility in the
consciousness formula is therefore derived from employment share, not
from an abstract credibility field.

**PoliticalFaction** contests political power through ideology. It
carries an explicit ``ideology`` label and a ``consciousness_tendency``
that drives the direction of its consciousness effects. The player's
faction is a PoliticalFaction.

**CivilSocietyOrg** provides community services -- religious, educational,
media, labor. Its influence comes from ``legitimacy``, a probability
field representing community trust. Unlike state and capital, civil
society's power is earned, not imposed.

These four categories are not arbitrary. They map to the Gramscian
distinction between state, capital, and civil society, with political
factions as the organized expression of class consciousness.


Class Character
---------------

Every organization carries a ``class_character`` field: BOURGEOIS,
PROLETARIAN, or CONTESTED. This is not a moral judgment but a structural
analysis. Which class does this organization objectively serve?

The Detroit Police Department has ``class_character=BOURGEOIS`` because
the function of policing is the protection of property relations. The
Revolutionary Workers Party has ``class_character=PROLETARIAN`` because
its program advances the interests of the working class. First Baptist
Church has ``class_character=CONTESTED`` because its class character
depends on which class fraction controls its leadership and program.

Class character is set at construction, not computed. It represents the
current political-economic alignment of the organization, which may change
through gameplay but is not automatically derived from membership composition.


Consciousness Tendency and the Five-Factor Formula
---------------------------------------------------

Organizations do not simply exist -- they *act* on the communities where
they operate. The consciousness effect formula models how an organization
shifts collective identity in its territory.

The formula is a product of five factors::

   consciousness_delta = tendency_modifier x cadre_level x cohesion x credibility

The factors are:

1. **Tendency modifier** -- the direction and magnitude of ideological
   pressure. REVOLUTIONARY organizations push collective identity upward
   (+0.15). LIBERAL organizations suppress it (-0.05). FASCIST organizations
   exert non-CI tendency pressure (+0.10) without raising collective identity.

2. **Cadre level** -- leadership quality. A poorly led organization (0.1)
   has one-seventh the effect of a well-led one (0.7). This encodes the
   Leninist insight that revolutionary consciousness requires a vanguard.

3. **Cohesion** -- internal unity. A fractured organization cannot project
   ideological influence.

4. **Credibility** -- the community's reception of this organization's
   message. This varies by subtype: civil society uses legitimacy, business
   uses employment share, the state uses legal standing, factions use a
   default.

The product structure means any zero factor kills the effect entirely. An
organization with zero cohesion, no matter how revolutionary its program,
produces no consciousness change. This matches the materialist principle
that organizational capacity mediates ideological influence.

The FASCIST tendency deserves special note. Fascist organizations do not
raise collective identity -- consciousness of shared class interest is
antithetical to fascism. Instead, they exert *tendency pressure* that
competes with revolutionary tendency for ideological dominance. A community
under strong fascist pressure and weak revolutionary pressure drifts
toward fascist consciousness even if its collective identity does not
change. This models the historical observation that fascism succeeds not
by raising class consciousness but by redirecting class anger into
nationalist, racial, or ethnic channels.


Emergent Topology
-----------------

Organizations do not store their internal topology as a field.
``internal_topology`` is *emergent* -- it is computed from the COMMAND
edges that connect KeyFigure nodes within the organization.

The reason is simple: topology is a graph property, and the graph is
the simulation's source of truth. If topology were stored as a field on
the organization, it would need to be kept in sync with the actual edge
structure. Any desynchronization would mean the topology field lies.
By computing topology from the graph on demand, the classification is
always accurate.

Four topologies are recognized:

**STAR**: a single hub connected to all other members. The hub is the
sole articulation point. Removing it fragments the organization into
isolates. Churches, small businesses, and local police precincts
typically exhibit star topology.

**HIERARCHY**: a tree structure with N-1 edges. Information flows along
a chain of command. Military organizations and corporate structures
typically exhibit hierarchy.

**MESH**: high edge density (> 0.6). Members are heavily interconnected.
No single removal can fragment the network. Revolutionary cells that
have operated together for years tend toward mesh.

**CELL**: clusters connected by bridge nodes (articulation points).
The bridge nodes are structurally critical -- their removal disconnects
the clusters. Underground organizations deliberately adopt cell
topology to limit damage from infiltration.

Classification requires a minimum of 3 nodes. A 2-node pair is
classified as HIERARCHY (minimal chain of command), since a dyad
trivially has density 1.0 (which would falsely trigger MESH) and
degree 1 = N-1 (which would falsely trigger STAR).


Key Figures and Structural Vulnerability
----------------------------------------

Key figures are identified through articulation point analysis on the
COMMAND subgraph. An articulation point is a node whose removal
disconnects the graph -- removing it breaks the organization into
fragments that can no longer communicate through the command structure.

Each key figure carries a ``structural_importance`` score::

   importance = (components_after_removal - 1) / (n - 1)

This normalizes to [0, 1] where 1.0 means maximum fragmentation. The
hub of a 7-node star has importance 5/6 (0.833): removing it creates
6 isolates from 1 connected component.

The ``is_singleton`` flag indicates whether the key figure has a
structural equivalent -- another member with the same degree and the
same neighborhood. If no equivalent exists, the key figure is
irreplaceable. If an equivalent exists, the organization has structural
redundancy.

This analysis is grounded in the work of Sparrow (1991), who argued
that intelligence agencies can identify structurally critical members
of clandestine organizations through social network analysis even
without knowledge of member identities. The ``IntelMethodology`` model
encodes which SNA techniques a given agency has access to, from
basic centrality analysis (Local PD) through full structural
equivalence and template matching (FBI).


Legacy Migration
----------------

Before Feature 031, organizations existed in two legacy formats:
``factions.json`` (4 political factions with ideology fields) and
``institutions.json`` (7 institutions with type fields). The migration
system converts these into typed Organization subtypes.

The migration is one-time and one-way. There is no backward compatibility
layer. Legacy faction ideology maps to ``ConsciousnessTendency`` via
the R8 mapping table (Fascism -> FASCIST, Liberal Democracy -> LIBERAL,
Marxism-Leninism and MLM -> REVOLUTIONARY). Legacy institution type
maps to subtypes (State/Legal -> StateApparatus, Cultural/Economic/
Religious/Educational -> CivilSocietyOrg).

"Systemic Racism" (Inst001) is dropped during migration. Per
Constitution I.16, systemic racism is a social relation, not an
organization. It cannot be instantiated, defunded, or reformed in
the way that an organization can. Modeling it as an organization
would imply that racism is an agent rather than a structural condition.


See Also
--------

- :doc:`/reference/organizations` -- Complete API reference
- :doc:`/concepts/institution-model` -- Institution layer above organizations (Feature 040)
- :doc:`/concepts/george-jackson-model` -- Consciousness formation theory
- :doc:`/concepts/community-hypergraph` -- Hyperedge community layer
- :doc:`/concepts/topology` -- Percolation theory and network metrics
