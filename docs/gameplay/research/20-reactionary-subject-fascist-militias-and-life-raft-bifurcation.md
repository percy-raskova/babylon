# 20 — The Reactionary Subject, the Militia Cells, and the George Jackson Life Raft Bifurcation

Read-only design and theory briefing, 2026-10-25. **Gap 1** of the porch series.

The question: when imperial rent $\Phi = W_c - V_c$ falls and the two cushioned
strata — petty bourgeoisie ($C_{pb}$, the 90–99% tier) and labor aristocracy
($C_{la}$, the 50–90% tier) — lose the material basis of their status, **what
happens on the board?**

Three answers are on the table and only one of them is a game:

1. They route, by default, into **social-fascist opportunism** (the DSA/Green-New-
   Deal-on-the-backs-of-the-periphery channel).
2. They route, by default, into **autonomous fascist militias and revanchist
   posses**, which — if federal fiscal solvency breaks before the player wins —
   decompose the map into the **Warlord Trajectory**.
3. **Director ruling, 2026-10-25 (the George Jackson Life Raft Bifurcation):**
   (1) and (2) are **true-by-default, not set in stone**. A segment of both strata
   will jump ship onto a revolutionary raft *if and only if* an actual material
   alternative exists with a **proven track record** — functioning food, housing,
   clinics and defence, and demonstrated survival against State operations. They
   will not risk their lives against Palantir technofascism for a fiery speech, a
   moral scolding, or a vague "community of care."

This briefing grounds (3) in Marx, Zetkin, Stalin, Mao, George Jackson and
MIM(P); specifies the four non-state reactionary cell types as cellular automata
that compete in the same `Capacity::allocate` allocator as the State and the
player; and derives the bifurcation as **a ratio of two counts** with no sigmoid
and no magic number — including the proof that `Agitation` without
`MaterialProgramme` contributes exactly nothing to defection, and in fact
subtracts from it.

Everything below is game design. No Rust, no Python, no commits.

---

## 0. The one-page answer

The reactionary trajectory is not a law of the middle classes. It is **the stable
fixed point of a system whose raft is empty.** At period 0 the proven-track-record
stock is zero, so the defection ratio is zero, so every squeezed household takes
the best offer actually on the table — and the only offers on the table are
disbursements: the reformist buffer's fiscal transfer, and the militia's stipend,
bounty and per-diem. That is why the default is reactionary, and it is a
*theorem about initial conditions*, not a claim about human nature. The Director's
ruling is already inside the formalism: an empty raft is not an absorbing state.

The gameplay consequence is a genuine bifurcation with two self-reinforcing
branches, because **one household is simultaneously a unit of raft coverage and a
unit of militia subscription revenue.** Every defector raises the raft's proven
coverage *and* cuts the militia's replenishment, which raises the ratio further.
That is a tipping point, not an exchange rate, and it is why the middle of a
campaign feels like a cliff rather than a slope.

The three things the player must therefore build, in order, are: **edges** into
the strata (no rope, no rescue), **goods** that are actually delivered (not
promised), and **survival** under attack (an untested depot is charity, not a
raft).

---

## 1. Theoretical grounding

### 1.1 Marx, 1849: social-democracy *is* the petty-bourgeois form

The single most useful passage in the archive for modelling the DSA channel was
written about the Montagne. Marx describes the coalition of petty bourgeois and
workers that formed against the coalesced bourgeoisie, and then names its
content:

> "The peculiar character of social-democracy is epitomized in the fact that
> democratic-republican institutions are demanded as a means, not of doing away
> with two extremes, capital and wage labor, but of weakening their antagonism
> and transforming it into harmony. However different the means proposed for the
> attainment of this end may be, however much it may be trimmed with more or less
> revolutionary notions, the content remains the same. This content is the
> transformation of society in a democratic way, but a transformation within the
> bounds of the petty bourgeoisie."
> — *The Eighteenth Brumaire of Louis Bonaparte*, part on the Montagne

And the class mechanism, which is the *whole* of the DSA buffering problem:

> "What makes them representatives of the petty bourgeoisie is the fact that in
> their minds they do not get beyond the limits which the latter do not get
> beyond in life, that they are consequently driven, theoretically, to the same
> problems and solutions to which material interest and social position drive the
> latter practically."

Two design consequences fall out immediately.

**First, the DSA cell is not a villain and not a liar.** It represents its class
faithfully. Its programme *is* the class's own horizon: weaken the antagonism,
preserve the small property, harmonize. It will therefore never move $\Phi$. It
is not a plot; it is a *ceiling*, and the ceiling is the class position of the
people in it. Babylon should render DSA cadres sympathetically and their
programme as coherent — the trap is material, not moral.

**Second — and this is the sharpest single sentence in the whole source base for
the militias — Marx explains why the *squeezed* petty bourgeoisie ends up as a
client of an armed patron rather than an actor in its own name.** On the
small-holding peasants:

> "Their mode of production isolates them from one another instead of bringing
> them into mutual intercourse. … Thus the great mass of the French nation is
> formed by the simple addition of homologous magnitudes, much as potatoes in a
> sack form a sack of potatoes. Insofar as millions of families live under
> conditions of existence that separate their mode of life, their interests, and
> their culture from those of the other classes … they form a class. Insofar as
> there is merely a local interconnection among these small-holding peasants, and
> the identity of their interests forms no community, no national bond, and no
> political organization among them, they do not constitute a class. They are
> therefore incapable of asserting their class interest in their own name …
> **They cannot represent themselves, they must be represented.** Their
> representative must at the same time appear as their master, as an authority
> over them, an unlimited governmental power which protects them from the other
> classes and sends them rain and sunshine from above."

This is a statement about **topology**, not about peasants. A stratum whose
internal edges are absent has no capacity to act; the only available verb is to
*be represented*, and the representative is whoever arrives with force and
provisions. This gives Babylon its militia-capture rule in one line: **the
militia does not win the suburb by argument; it wins it by being the only
organization with edges into it.** A homeowner with a WhatsApp group, a church
basement and a county sheriff is already connected to an armed patron. He is not
connected to you. That asymmetry is worth more than any amount of agitation, and
it is *countable* (see §3.5).

And the crisis cry Marx records from the bourgeois side — *"Rather an end with
terror than terror without end!"* — is the demand for a Caesar, which is exactly
what a collapsing $\Phi$ produces on the right: not a programme, a
*decider*. It is also the correct emotional register for the militia's recruiting
pitch, and the narrator should use it.

**One correction to the existing spec.** `ai/epochs/epoch3/reactionary-subject.yaml`
asserts that the lumpenproletariat are "STRUCTURALLY incapable of fascism" and
that they have "NO_DEFECTION: Never joins fascist faction." Marx says the
opposite, and says it with the most famous passage in the book: Bonaparte
"constitutes himself chief of the lumpenproletariat, who here alone rediscovers
in mass form the interests which he personally pursues, who recognizes in this
scum, offal, refuse of all classes **the only class upon which he can base
himself unconditionally**." The Society of December 10 was built out of
"vagabonds, discharged soldiers, discharged jailbirds, escaped galley slaves,
swindlers, … beggars — in short, the whole indefinite, disintegrated mass."
The Freikorps and every twentieth-century militia recruitment drive agree.

The claim survives, but it must be restated materially rather than morally: the
lumpen **cannot fund a militia**, because they hold no surplus to subscribe. They
can *fill* one. A militia whose ranks are lumpen and whose treasury is petty-
bourgeois or sheriff-funded is exactly Bonaparte's Society of December 10 — real,
violent, and **structurally transient**, because it has no independent
replenishment. That restatement is worth keeping: it gives the player a real
target (the militia's *treasury*, not its street fighters) and it keeps Jackson's
actual insight intact, which is not that the lumpen are immune but that they have
"the least to lose," which makes them the most reliable *when organized and
paid in something other than money*.

### 1.2 Zetkin, 1923: fascism as the refuge of the ruined middle, and the two-part answer

Zetkin's *Fascism* (Labour Monthly, August 1923) supplies the mechanism and the
counter-weapon in the same document, and its counter-weapon is the Life Raft
avant la lettre.

**The recruitment pool.** Fascism draws on "deep misery for the petty
bourgeoisie, the small peasantry and the intellectuals," joined by "large masses
of ex-officers, who are now unemployed." Its base is "the disappointed and …
those whose existence is ruined." It is "a sort of refuge for the politically
shelterless." She explicitly includes workers who have given up:

> "These masses of disappointed socialist sympathisers are joined by large
> circles of the proletariat, of workers who have given up their faith not only
> in socialism, but also in their own class."

**The two features, in every country.** Fascism has exactly two: "the pretence of
a revolutionary programme, which is cleverly adapted to the interests and demands
of the large masses, and, on the other hand, the application of most brutal
violence." And its origin story is a *simulated raft*: "the cause of the first
success of the Fascisti was that it made its start with a revolutionary gesture.
Its pretended aim was to fight to retain the revolutionary conquests … Its slogan
was directed against all the exploiters."

This is the competitive core of the design and it must not be lost: **the militia
and the raft are bidding for the same household with the same claim.** Both say
*I will keep you alive and give you back your dignity.* One disburses a promise
and a rifle; the other disburses bread. The equation in §3 must therefore be able
to tell them apart *mechanically*, and the only way to do that is to count
**delivered goods** on one side and **paid receipts** on the other, with no term
for rhetoric on either.

**The answer, and it is two-part.** Zetkin refuses the purely ideological reply:

> "We have to overcome Fascism not only militarily, but also politically and
> ideologically. … We must endeavour either to win over or to neutralise those
> wide masses who are still in the Fascist camp. … they are not only trying to
> escape from their present tribulations, but … they are longing for a new
> philosophy."

and then names what actually wins them — a *material programme*, not a sermon:

> "I welcomed the proposal of Comrade Zinoviev … to take up the struggle for the
> **Workers' and Peasants' Government**. … It means that the salvation of the wide
> masses of the small peasantry will be achieved through Communism."

followed immediately by the second half:

> "The proletariat must have a well organised apparatus of self-defence. Whenever
> Fascism uses violence, it must be met with proletarian violence."

**Bread and guns. Not bread or guns.** That is the Life Raft: the Goods Clause
(food, housing, clinic, justice) *plus* demonstrated capacity to survive attack.
Zetkin's structure is precisely the two-factor form of §3, and it is why a player
who builds clinics but no defence will watch the clinics burn and lose the stock
in a single period — the raft is the conjunction, not either factor.

Zetkin also supplies the *defeat* pathway: the Italian proletariat lost the
factory occupations first, and "after the defeat of the proletariat in the
occupation of the factories … great masses of the proletariat joined the
Mussolini organisation." Defeat, not argument, moves the middle. Babylon should
therefore make **a public defeat of the player cost raft stock even when the
player keeps the line** — which pairs exactly with `research/16`'s "losing a base
area while keeping your Line is a survivable strategic retreat; losing the Line
is defeat." Here the refinement is: a lost base area also costs *credibility with
the vacillating stratum*, which is the exact quantity $\sigma$ in §3.

### 1.3 Stalin: why the opportunist buffer and the phrasemonger are the same failure

Two passages from *Foundations of Leninism* (1924) do the work, and both are
gifts because they are already in the player's own idiom.

On the buffer's class logic:

> "The opportunists adapted themselves to the bourgeois because of their
> adaptive, petty-bourgeois nature; the 'orthodox,' in their turn, adapted
> themselves to the opportunists in order to 'preserve unity' with them, in the
> interests of 'peace within the party.' Thus the link between the policy of the
> bourgeois and the policy of the 'orthodox' was closed, and, as a result,
> opportunism reigned supreme."
> — ch. II, "The Historical Roots of Leninism"

That is the *internal* half of the DSA problem, and it is the mechanic behind
porch-02's `Conciliator / Buffer` stage in the four-stage antagonism gradient: the
buffer is worse than the deviation because it shields it. It also means the DSA
cell has a legitimately attractive interior — it is where unity is preserved —
which is why the player's own organization can be captured by it.

On the phrasemonger, from "Style in Work":

> "'Communist vainglory,' says Lenin, 'means that a man, who is a member of the
> Communist Party, and has not yet been purged from it, imagines that he can
> solve all his problems by issuing communist decrees.' … Lenin usually
> contrasted hollow 'revolutionary' phrasemongering with plain everyday work. …
> 'Fewer pompous phrases, more plain, everyday work.'"

Stalin's name for the correct combination — "Russian revolutionary sweep **and**
American efficiency" — is a good in-world label for the raft: audacity in line,
bookkeeping in goods. And the degeneration of each alone is exactly the two
failure modes the player will actually commit: sweep without efficiency becomes
"revolutionary Manilovism" (the fiery speech), efficiency without sweep becomes
"narrow, unprincipled practicalism" (the NGO that delivers goods and never
contests power).

That second degeneration deserves its own name on the board, because it is the
most seductive trap for a well-meaning player: **a raft with no politics is a
charity, and a charity is a militia's easiest target and the State's cheapest
concession.** MIM(P)'s answer to this is in §1.5.

### 1.4 Mao, 1927: the middle joins when the association demonstrably holds power

The Hunan Report contains the cleanest empirical statement of the Life Raft
bifurcation in the entire canon, and it is a statement about *probability
assessment*, not sentiment. Of the middle peasants:

> "How about the middle peasants? Theirs is a vacillating attitude. They think
> that the revolution will not bring them much good. They have rice cooking in
> their pots and no creditors knocking on their doors at midnight. They, too,
> judging a thing by whether it ever existed before, knit their brows and think
> to themselves, **'Can the peasant association really last?'** 'Can the Three
> People's Principles prevail?' Their conclusion is, **'Afraid not!'** …
> In the first period, people from the association would call on a middle
> peasant, register in hand, and say, 'Will you please join the peasant
> association?' The middle peasant would reply, 'There's no hurry!' **It was not
> until the second period, when the peasant associations were already exercising
> great power, that the middle peasants came in.**"

Read that as a specification. The middle peasant is not asking *is this just?* or
*is this true?* He is asking **"can it last?"** — a durability estimate against
the State's capacity to destroy it. His answer is "afraid not" until the
association *demonstrably exercises power*. Then he comes in. That is
$P(S\mid R) > P(S\mid A)$, written in 1927, in a village, about rice.

Mao adds the edge clause and the opportunist caveat in the same breath:

> "It is essential for the peasant associations to get the middle peasants to
> join and to do a good deal more explanatory work among them."

and on the rich peasants, who join without conviction:

> "When the rich peasants join the associations, they generally enter the name of
> some sixty or seventy-year-old member of the family, for they are in constant
> dread of 'conscription'. After joining, the rich peasants are not keen on doing
> any work for the associations. They remain inactive throughout."

That is porch-02's Weinstein problem (opportunistic *consumers* flood in once a
node wins clout) stated as an observed rural behaviour: the defector who arrives
for the goods and does no work. The raft therefore needs the *maintenance* clause
(§3.7: never missed a period, never smashed) or it will inflate its own stock with
tourists.

### 1.5 George Jackson and MIM(P): the raft must be *political* power, and it must be *attacked*

**Jackson.** The MIM(P) archive's own memorial essay states the position that
makes the raft a revolutionary and not a humanitarian instrument:

> "He showed them how Amerika's prisons were full of poor minorities … Brother
> George taught the other prisoners that they were part of a larger class of
> people who had been targeted and oppressed by the imperialistic ways of this
> country. He got others to join him in changing their condition. He organized
> and educated them around demands for prison reform. **He simultaneously showed
> them that in the end prisons could not be changed. Change could only come from
> a full-scale revolution.**"
> — "The Dragon," *MIM(Prisons)*, August 2005

The raft is not reform. Reform is the *proof of sincerity*, and the proof is what
earns the right to say "and this is why it cannot be won inside the system."
That ordering matters for the Decision Ceremony in §4: the player who delivers
goods and then proposes revolution has credibility; the player who proposes
revolution and has no goods is a phrasemonger, and Zetkin already told us where
those masses go instead.

**The breakfast programme.** MIM's account of why the State destroyed the Black
Panther Party is the best available evidence that a survival programme is
*already* political power, and that the State's own targeting is the test of it:

> "The most talked-about reasons for governmental attack on the BPP were the
> **Survival Programs** which the FBI knew were used for 'indoctrination.' …
> J. Edgar Hoover exhorted local FBI offices to put a stop to the 'nefarious
> activity' of feeding Black children free breakfasts before school in the
> morning. … In the Community Survival programs and rallies the government saw a
> scary potential for organizing Black people in an armed rebellion against the
> state. So rather than just take action to cut down these specific programs, the
> FBI worked through a campaign to take out the Panthers as an organization."
> — *MIM Notes* 83, December 1993

Two mechanical consequences, both non-obvious and both load-bearing:

1. **Free breakfast is not a modifier; it is a targeting decision.** The State
   allocates against the *institution*, not against the rhetoric. So the Goods
   Clause must be an entity on the graph that can be attacked, destroyed and
   rebuilt — never a passive "+food" buff on a county. A buff cannot be shot at,
   and therefore cannot generate a track record.
2. **Being attacked is what converts charity into proof.** An unopposed depot is
   a soup kitchen. A depot that was burned and rebuilt twice is a *base area*.
   This is the whole of §3.7 and it is why the raft cannot be bought with money
   alone.

MIM also refuses the charity reading in its own voice — "Myth #5: The Panthers
were just charity workers" — and records the Panther formula: "Feed the youth and
they will feed the revolution," with "a free breakfast program [was] born in
Oakland. To the half-baked, the narrow-minded and the avaricious fool, this may
seem as though the Black Panther Party now endorses reform action and is no
longer interested in revolution" (*MIM Theory* 10, "Maoism Restored: The Black
Panther Newspaper, 1968–69").

**France 1968 — the negative case, and it is worth more than the positive one.**
MIM's reading of the French general strike is the empirical refutation of the
"just show them the system is cracking and the middle will come" theory, and it
is the strongest single warrant for the Director's ruling:

> "In 1968, the middle classes — the petty-bourgeoisie and labor aristocracy —
> could clearly see that imperialism was not invincible. … The result was **not**
> a middle-class identification with the proletariat. Instead the middle classes
> went into action on their own: they dissed their government, their trade unions
> and their school administrations just as the anarchists told them to do, but no
> more. They did not want power, just the aggrandizement of their own class's
> illusion of independence from the laws of economics. … Second, and part of the
> whole romance of 1968, is that the revolution quickly withered after **a few
> wage concessions and an election**."
> — *MIM Theory* 10

That is a fourth channel, and the design must have it or the player will not
recognise their own mistakes: **a perceived crack in the enemy is not a raft.** If
the raft is absent, a shock to the middle class produces *sterile revolt* —
moralist, individualist, decentralized, and reversible by concession — and then
it is bought back. Babylon should render this as an actual third basin with an
actual decay rate, not as a null result, because "we had a general strike and they
voted for the strongman eighteen months later" is one of the most important
lessons the game can teach and no other game teaches it.

**Why the labor aristocracy is cheap to win back.** MIM's account of the U.S.
1960s names the mechanism in the phrase that should go straight into the data
model: the Euro-American workers were "intoxicated by superprofits," and "the
movement was too proletarian for the tastes of Euro-Amerikan workers." An
intoxicated stratum does not need to be argued out of fascism; it needs to be
*supplied* a substitute. Which means its defection is real but **fragile** — the
same stratum that jumps to the raft will jump back the moment the raft misses a
period and the old wage packet reappears. $\mathrm{LR}$'s "never missed a period"
clause is therefore not bookkeeping fussiness; it is the modeling of exactly this
fragility.

### 1.6 Synthesis: the default is an initial condition, not a nature

| Source | What it establishes | What it kills in the design |
|---|---|---|
| Marx, *18 Brumaire* | Social democracy is the petty-bourgeois *form*; isolated smallholders must be represented | DSA as villainy; militia recruitment by persuasion |
| Marx, *18 Brumaire* | Bonaparte's base was the lumpen, unconditionally | `NO_DEFECTION` for $L_u$; but see the treasury restatement |
| Zetkin 1923 | Refuge of the ruined middle; **pretence** of a programme + violence | Any rhetorical term in the defection equation |
| Zetkin 1923 | Workers' and Peasants' Government + self-defence apparatus | Raft = goods *or* guns; it is goods **and** guns |
| Stalin 1924 | Opportunism's petty-bourgeois adaptation; phrasemongering as vainglory | Agitation as a positive term anywhere in $\Lambda$ |
| Mao 1927 | The middle joins when the association "exercis[es] great power" | Defection as a function of persuasion or of the *news* |
| Jackson / MIM(P) | Survival programmes are political power; the FBI attacked the breakfasts | The Goods Clause as a passive county buff |
| MIM, France 1968 | A crack in the enemy without a raft produces sterile, reversible revolt | A two-channel model; it is three, plus the raft |

**The ruling, restated formally.** The reactionary trajectory is the attractor of
the system with $\mathrm{LR} \equiv 0$. It is *not* the only attractor, and
$\mathrm{LR}=0$ is not absorbing. Research `13` §4.3 supplies the correct
mathematics: the origin is "stable to small perturbations, but not to large
ones — locally stable, but not globally stable." The reactionary basin is wide;
the raft basin is narrow and must be entered; and **hysteresis** means the
crossing is one-way in both directions — a county whose books have flipped to
captivity does not flip back, and a stratum that has been provisioned by a
surviving institution does not un-learn that it can be done.

---

## 2. The board: four non-state reactionary cells as cellular automata

### 2.1 What a cell *is*, in the vocabulary already in the tree

`babylon-graph/src/capacity.rs` (ADR184, Director ruling 2026-07-30) already
gives us the whole mechanism, and it gives it without a privileged mechanic:

> "**Capacity belongs to organizations.** … 'The state' is not a node type. …
> A budget with no owner would make the state a force of nature rather than a set
> of organizations with means."
>
> "**Repression and revolutionary action are the same allocation.** A union local
> and a political police force both rank what they could do by yield per unit
> spent and fund down the list until the money runs out. Neither gets a privileged
> mechanic; the historical asymmetry is the *size* of the budget and nothing else.
> **The class difference lives entirely in replenishment.**"
>
> "**Yield is computed on `L`, never on truth.** … an actor allocates against what
> it BELIEVES it would gain."

That is the entire specification for fascist militias, posses, company goons and
comprador buffers. They are not scripted antagonists and they are not a "fascism
meter." They are `organization` nodes with:

- a **budget** per instrument (`Currency`, micro-units, ADR184 R8),
- a **dossier** $L_c$ — their own private, partial, frequently wrong picture,
- a **local objective function** (what they are trying to maximise, which is not
  the same as what the ruling class wants),
- a **`Candidate` list** priced in money and ranked by believed-yield-per-unit,
- and a **replenishment function** — and *this* is where the class content lives.

The single most important consequence: **a militia is not scary because it is
evil; it is scary because its replenishment rises while yours falls.** That is
the whole of the mid-game, and it needs no tuning.

### 2.2 The four cells

All four spawn as `organization` nodes on Topology with a county seat, a dossier
scope, and a replenishment channel. None is player-controlled. All four are
*responding to the same $\Phi$ collapse* and all four are bidding for the same
$C_{pb}/C_{la}$ households.

| | **`BUFFER_COMPRADOR`** | **`MILITIA_AUTONOMOUS`** | **`POSSE_REVANCHIST`** | **`COMPANY_GOON`** |
|---|---|---|---|---|
| **Real-world type** | DSA chapter, NGO, faith-based fiscal conduit, patronage machine | Patriot Front, Minutemen, Freikorps, Oath-Keeper-style franchise | Sheriff's volunteer posse, homeowners' militia, "constitutional sheriff" | Pinkerton/private security, strikebreaking firm, plant guard force |
| **Instrument** | `FISCAL`, `ELECTORAL` | `ARMED`, `STREET` | `ARMED`, `CUSTODY` | `ARMED`, `LOCKOUT` |
| **Objective (its own)** | retain office, grants, and the coalition | visibility, status, membership growth | jail beds, forfeiture revenue, territorial autonomy | contract retention, plant throughput |
| **Replenishment** | dues + foundation grants + municipal budget | $C_{pb}/C_{la}$ subscription + national franchise transfer | **county per-diem + asset forfeiture + state/federal grants** | corporate contract |
| **Dossier scope** | ward / county electorate | county + national network | county jail, courthouse, roads | one plant, one port, one rail corridor |
| **Candidate modes** | `SPACE`, `BUDGET`, `TRIBUNE`, `NON_COOPERATION` | `POGROM`, `VIGILANTISM`, `INTIMIDATE`, `ARM` | `SWEEP`, `CURFEW`, `CIVIL_FORFEITURE`, `DEPUTIZE` | `BREAK_STRIKE`, `BLACKLIST`, `EVICT`, `ARM` |
| **What it disburses** | transfer $b^D$ per household | stipend/bounty $b^M$ per *eligible* household | wage + protection $b^M$ per *eligible* household | wage to scabs only |
| **Its ceiling** | the federal/state fisc: $b^D \propto F_t$ | the strata's discretionary surplus above subsistence | criminalisation rate (more laws → more beds) | the firm's balance sheet |
| **Failure mode** | absorption (committee chair, staffer drift), preemption, or the money simply runs out | **treasury collapse** — a lumpen-filled, petty-bourgeois-funded militia is Bonaparte's Society of December 10 and dissolves | federal reassertion, or the county's books un-flipping | the plant closes anyway |
| **Narrative signature** | reasonable, credentialed, sincerely anti-fascist | young, uniformed, photographed, online | middle-aged, deputized, legally armed, "just following the sheriff" | anonymous, contractual, indemnified |

The **`BUFFER_COMPRADOR`** deserves emphasis because it is the one the player will
under-rate. It is not a paper tiger: it wins real offices and passes real bills
(porch-02, Screen 2). It fails at exactly five material barriers — capital strike
and bond downgrades, court injunctions and preemption, police-union
insubordination, absorption, and the $\Phi$ ceiling. Its function in the class
struggle is not to reform anything; it is to **hold the middle strata in
circulation while the fisc can still pay them.** When the fisc breaks, it stops
paying, and its base is *released* — which is the critical moment.

### 2.3 Coverage is a partition on one side and a measure on the other

Here is a real, coefficient-free distinction between the militia and the raft, and
it explains why militias need an enemy in a way that is quantitative rather than
moral.

A militia's disbursement is **conditional on an ascribed predicate**:

$$P(S\mid A)^c_{\text{militia}} = \frac{1}{N^c}\#\left\{i : w_i + b^M_i \ge s_i \ \wedge\ \mathrm{eligible}(i)\right\}$$

where `eligible` is a predicate over race, religion, homeowner status, veteran
status, or simply "not the target." A raft's disbursement is **unconditional on
ascription**:

$$P(S\mid R)^c_{\text{raft}} = \frac{\mathrm{LR}^c}{N^c}\cdot\frac{O}{R},\qquad \mathrm{LR}^c = \#\{i : \text{served every period since open} \wedge \text{institution survived every operation}\}$$

The militia's coverage therefore has a **maximum equal to the size of the
included group**, and — this is the point — *the value of inclusion is
proportional to the size of the excluded group.* A militia in a homogeneous
county with no scapegoat has a coverage ratio near 1 and almost nothing to offer,
because there is no one to exclude and therefore no scarcity in belonging. A
militia in a mixed county has a coverage ratio below 1 *and* a real product. Hence
the observed pattern, derived rather than authored: **militias flourish where
there is a target and wither where there is not**, and a player who homogenizes a
county (by driving one group out) *strengthens* the militia, while a player who
builds a united front across the divide *lowers its product* — not because of
morality, but because inclusion has stopped being scarce.

### 2.4 Escalation without a threshold: the militia attacks the raft because the raft is the target

Porch-02 and `research/17` establish that State repression escalates because a
target *rises in the ranking*, not because "heat crossed 0.7." The same arithmetic
gives militia behaviour for free, via `Candidate.expected_yield` computed on the
cell's own dossier:

| Target | Believed yield | Cost | Rank effect as the raft grows |
|---|---|---|---|
| A picket line | high (stops production, visible) | low (unarmed, public, police-tolerated) | constant |
| A semi-colony block | high (terror, dispersal) | medium | constant |
| A food depot | **rises**: destroying it is the only way to break the record | medium | **rises** |
| A clinic | **rises**: the most-cited good, and the hardest to rebuild | high | **rises** |
| A cadre | high but replaceable (see `exposure`'s replaceability quotient) | high | *falls* as redundancy grows |

So the militia does not attack the raft out of spite. **The raft is the target
because the raft is what makes the militia's target valuable.** Every period the
depot delivers, the militia's believed yield on burning it goes up, because a
record is worth more than a building. This is the mechanism that makes the
"demonstrated survival" term $\sigma$ non-optional: the difficulty curve of the
raft is that *success attracts the operation that tests it*. And it means the
player cannot have a proven track record without having been attacked, which is
exactly the historical record (Hoover and the breakfasts) and exactly Mao's
"exercising great power."

Note what this also does to the *player's* allocation: `Capacity::allocate` is
shared. A `MILITIA_AUTONOMOUS` cell spending on `ARM` and the player spending on
`DEFEND` are drawing from two different budgets at the same target with the same
ranking logic. There is no "combat" special case; the contest is two allocators
pointed at one node.

### 2.5 The Warlord flip is a change in the county's books, not a political choice

`ai/epochs/epoch3/warlord-trajectory.yaml` currently branches on
`bourgeois_solvency`, `military_loyalty`, `revanchist_cohesion` and
`settler_consciousness` — four fuzzy functions with unnamed thresholds, plus
`prisoner_organization >= 0.5`. That is unbuildable under the constitution
(thresholds, no state snapshot). The trajectory file's *insight* is correct and
should be kept: "the apparatus of violence outlives its economic base," and
"the key split is between traditional military and local police." What needs
replacing is the branching condition.

The condition is already in the file, unwritten, in the
`private_prison_precursor` block: "CoreCivic and GEO Group as proto-warlord
enterprises … Lobbying for criminalization (expanding captive population)." A
proto-warlord enterprise is one whose revenue comes from captives. So the flip
condition is a comparison of two receipts on one county's books:

$$\boxed{\ \text{Warlord flip at } t \iff R^{\text{captive}}_{j,t} > R^{\text{tax}}_{j,t}\ }$$

where $R^{\text{captive}}$ is the county's receipts from per-diem bed billing,
convict labour, civil forfeiture and carceral grants, and $R^{\text{tax}}$ is its
receipts from property and sales tax. Both are integers on the county ledger. No
threshold, no cohesion score, no settler-consciousness function. The sheriff's
`Capacity::allocate` ranking then flips *by itself*: when beds pay more than
taxpayers, `DEPUTIZE` and `SWEEP` outrank `PATROL`, and the county becomes a
prison-plantation because patrolling is the less profitable instrument — not
because anyone chose necropolitics.

This is the correct Marxist reading of the file's own central claim.
`warlord-trajectory.yaml` says the transition is "not merely a political change
(who holds power) but a transition in the relations of production." A transition
in relations of production is a transition in *how the ruling cell is
replenished.* The jail-revenue-over-tax-revenue crossing is that transition,
stated as a book entry, and it is legible to the player as a dossier line: *"the
county now earns more from its prisoners than from its residents."*

Three further consequences follow, all of them free:

- **Federal solvency enters only through the tax side.** $R^{\text{tax}}$ falls
  with $F_t$ (intergovernmental transfers and property-tax arrears), while
  $R^{\text{captive}}$ rises with criminalisation. So the crossing is *caused* by
  $\Phi$ collapse without $\Phi$ appearing in the condition. The trajectory file's
  year-0/year-100 wealth collapse is the empirical signature of the same motion.
- **The three trajectories become three book states**, not three scripts:

  | State | Condition on the county's books | Name |
  |---|---|---|
  | A | $F_t \ge 1$ and military paid and loyal | Classical Concentration / bourgeois necropolis |
  | B | $R^{\text{captive}} > R^{\text{tax}}$ | **Warlord era** (necropolitical prison-plantation) |
  | C | $\mathrm{LR}$ proven **and** $O/R$ rising | Revolutionary rupture |
  | — | none of the above | Contested collapse |

- **Hysteresis is automatic and historically right.** Once a county's revenue
  base is captivity, restoring the tax base requires *un-criminalising* a
  population that is now the revenue source — which the cell will price as
  suicide. So the warlord branch is one-way, matching `research/13` §4.3's
  "once large-amplitude oscillations have begun, they cannot be turned off." The
  player who breaks the State's finances to win a county may hand it to the
  sheriff. That is a real strategic dilemma and it should be a real one, not a
  scripted punishment.

### 2.6 The buffer's ceiling and the critical moment

The `BUFFER_COMPRADOR` cell's disbursement $b^D$ is a *fiscal* transfer, so it is
bounded by federal and state solvency:

$$b^D_{j,t} = \frac{\text{transfers actually paid to households in } j \text{ this period}}{N^c_j}$$

Note the phrase "actually paid." Not appropriated, not promised, not legislated —
*paid*. This is the single mechanic that makes the DSA channel honest, and it
kills porch-02's "$\Phi$ ceiling" complaint at the root: a DSA government can pass
anything it likes, and if the receipts are not there, $b^D$ does not move, and
nothing has happened to any household's survival probability.

The critical moment is then a comparison of two measured averages, not a date:

$$\text{the buffer holds } C_{pb}/C_{la} \iff \bar b^D_{j,t} \ \ge\ \bar b^M_{j,t}$$

with $b^D \propto F_t$ falling and $b^M$ rising with criminalisation and with the
strata's residual subscription. When the inequality flips, the DSA base is
**released into the militias** — this is the historical 1919–1933 sequence Zetkin
describes from the other end, and it is the reason the game's mid-point is
terrifying rather than merely hard.

And the raft is the only thing that can catch the released base. Not because it is
better, but because it is *the only other organization with edges into those
households* (§3.5). Which is why the player's work in the early game — the boring
work of church suppers, small-business associations, VFW halls and union locals —
is the whole game.

---

## 3. The Life Raft bifurcation equation

### 3.0 The constraints, stated once

`CONSTITUTION.md` v4.3.0 and ADR173: **no sigmoid, no stipulated response shape,
no magic constant.** Research `13`'s one-line filter applies to every symbol
below:

> "A magic number answers *how strongly*. A state snapshot answers *what is*. If
> it can be written as (measured numerator) ÷ (measured denominator) on the same
> period-$t$ snapshot, it is a state snapshot wearing a costume and must be
> recomputed each tick."

The permitted operations are `+ − × ÷`, comparison, `min`/`max`, and a fold over a
population. The permitted constants are `0`, `1`, and exact integers that denote
*designed objects* (the four Goods Clause categories) or *durations*.

The equation below uses **no fitted exponent, no steepness, no weight, and no
probability distribution**. Every symbol is either a count of households, a count
of periods, a count of operations, or a sum of money actually disbursed.

### 3.1 Symbols

All quantities are period-$t$ snapshots, for county $j$ and class
$c \in \{C_{pb}, C_{la}\}$.

| Symbol | Meaning | Measurement | Class |
|---|---|---|---|
| $N^c_j$ | households of class $c$ in county $j$ | census fold | Observed |
| $w_i$ | household $i$'s income this period | wage + transfer receipts | Observed |
| $s_i$ | household $i$'s subsistence requirement | local rent + food + utilities + transport | Derived |
| $b^D_i$ | reformist-buffer transfer **actually paid** to $i$ | municipal/state/federal disbursement ledger | Observed |
| $b^M_i$ | militia/posse disbursement **actually paid** to $i$ (stipend, bounty, deputy wage, protection) | cell budget ledger | Observed |
| $g_{i,k}$ | whether household $i$ received good $k\in\{\text{food},\text{house},\text{clinic},\text{justice}\}$ from a player institution **this period, without state grant or police referral** | institution delivery ledger | Observed |
| $\mathrm{age}_r$ | periods institution $r$ has been open | graph | Observed |
| $\mathrm{miss}_r$ | periods institution $r$ failed to deliver while open | graph | Observed |
| $S_r$ | hostile operations attempted against institution $r$ | ops ledger | Observed |
| $S^{\text{fail}}_r$ | of those, operations that did not end the institution | ops ledger | Observed |
| $O_j$ | player organizational stock in county $j$ | graph: org nodes + SOLIDARITY edges | Derived |
| $R_j$ | coercive capacity allocated against county $j$ | `Capacity` allocation, `fact_coercive_infrastructure` | Derived |
| $\Phi_t$ | imperial rent, $W_c/V_c - 1$ | §3.4 of `13` | Derived |

### 3.2 The two survival measures

**Survival by acquiescence — the technofascist offer.**

This is ADR173's measure — *the fraction of a class whose wealth clears
subsistence* — with **one added term that is a receipt, not a coefficient**. A
bribe is income; if the DSA pays it or the sheriff wages it, it belongs in the
household's wealth for that period.

$$P(S\mid A)^c_{j,t} \;=\; \frac{1}{N^c_j}\sum_{i\in c,j} \mathbf{1}\!\left[\,w_{i,t} + \max\!\left(b^D_{i,t},\,b^M_{i,t}\right)\;\ge\; s_{i,t}\,\right]$$

Three deliberate choices:

- **$\max$, not sum.** A household takes the better of the two offers on the
  table; it is not paid twice, and no household can be a DSA constituent and a
  militia dependent at once. This is also what makes the DSA/militia split
  *derived*: the class divides between the two patrons by comparing
  $b^D_i$ to $b^M_i$ household by household, with no weight anywhere.
- **Disbursed only.** Nothing appropriated, promised, platformed or orated enters.
  This is the formal statement of the Director's ruling that a fiery speech buys
  nothing.
- **No new primitive.** One `+` and one `max` on a fold the engine already
  performs for `P(S|A)`.

**Survival by rupture — the raft.**

$$P(S\mid R)^c_{j,t} \;=\; \underbrace{\frac{\mathrm{LR}^c_{j,t}}{N^c_j}}_{\text{coverage}}\;\cdot\;\underbrace{\frac{O_{j,t}}{R_{j,t}}}_{\text{defence}}$$

with the **proven-track-record stock**

$$\mathrm{LR}^c_{j,t} \;=\; \#\left\{\,i \in c,j \;:\; \underbrace{\textstyle\bigwedge_{k} g_{i,k}=1}_{\text{all four Goods Clause goods, this period}}\ \wedge\ \underbrace{\mathrm{miss}_{r(i)}=0}_{\text{never missed}}\ \wedge\ \underbrace{S^{\text{fail}}_{r(i)} = S_{r(i)} > 0}_{\text{survived every attempt, and was tested}}\,\right\}$$

Read the three conjuncts as the design's whole thesis:

1. **All four goods, not one.** A clinic with no food is a rumour. The four are
   the MIM Program Point 5 list — bread, housing defence, clinic, peer
   jury/justice — and they must be conjunctive because the *claim* being tested
   is that the alternative can administer life, not that it can distribute one
   commodity.
2. **Never missed a period.** This is the κ requirement, and it is a *record*
   rather than a threshold: $\mathrm{miss}_r = 0$ since opening. There is no
   "three consecutive periods" constant to declare, and one failure is a record
   with a hole in it. It is legible in-world as a Wiki line: *"Delmar Food Depot
   — open 14 periods, 3 attacks, 0 interruptions."*
3. **Tested and survived.** $S^{\text{fail}} = S > 0$ is the load-bearing clause.
   An untested institution satisfies $0 = 0$ and therefore **fails** the strict
   $S>0$ requirement. This is deliberate and it is the formal version of §1.5:
   *an unopposed depot is charity; a depot that has been burned and rebuilt is a
   base area.* The engine can express the untested case honestly as Marx's
   barrier — the ratio $\sigma = S^{\text{fail}}/S = 0/0$ is undefined, i.e. the
   relation has not yet been determined, which is precisely `research/09`'s
   $0/0 \to dy/dx$ doctrine. The household counts as *served* and does not count
   as *proven*. The player sees a functioning depot and no defections, and must
   work out why.

**On the product.** Coverage × defence is a product of two measured ratios with a
plain reading: *the fraction of your class standing on the raft* × *your ability
to hold it*. It contains no fitted exponent. A porch that prefers the weaker-link
reading may substitute $\min(\mathrm{LR}/N,\ O/R)$; both are coefficient-free and
the choice is a modelling decision, not a tuning knob. The falsifier in §3.9
distinguishes them empirically.

### 3.3 The defection condition, and its collapse into integers

$$\boxed{\ \Lambda^c_{j,t} \;=\; \frac{P(S\mid R)^c_{j,t}}{P(S\mid A)^c_{j,t}} \;>\; 1\ }$$

Substituting, the comparison is:

$$\mathrm{LR}^c_{j,t}\cdot O_{j,t} \;>\; R_{j,t}\cdot \#\left\{i : w_i + \max(b^D_i,b^M_i) \ge s_i\right\}$$

**Every symbol is an integer count or a sum of money.** The only constant is
$1$, and $1$ is not a magic number — it is unity, the definition of "better than
the alternative." This is the strictest possible form of the constitution's
requirement, and it is why the raft needs no difficulty slider: the player is
competing against a *count of households who are currently being kept alive by
someone else*.

Note what $\Lambda$ is **not**: it is not a probability, it is a ratio of two
measures, and the engine never exponentiates it. Defection is a comparison, not a
draw. (If a game-feel need for graded rather than binary defection appears, the
honest graded quantity is the *count of households with $\Lambda>1$ and an edge*,
which is an integer and needs no distribution — see §3.4.)

### 3.4 The flow, and why it is a bifurcation rather than a slope

$$\Delta \mathrm{LR}^c_{j,t+1} \;=\; \#\left\{\, i \in N^c_j \;:\; \Lambda^c_{j,t}>1 \ \wedge\ \exists\,e_{i\to r},\ r \in \mathrm{LR}^c_j \,\right\}$$

The defectors are exactly the households that clear unity **and already have an
edge to someone on the raft.** No edge, no defection — the raft is a physical
object and it must be *thrown*; the rope is an existing relation. This is the
"fish in water" clause and it is the reason the player's early game is
relationship-building rather than propaganda.

Now the feedback, which is where the bifurcation lives. **One household plays two
roles at once:**

- it is one unit of $\mathrm{LR}$ (raising coverage next period), and
- it is one unit of militia *subscription revenue* (so $\bar b^M$ falls next
  period because the subscriber base shrank).

Formally, since $\bar b^M_j = \left(\sum_{i \in \text{subscribers}} \text{dues}_i\right) / N^c_j$
and subscribers are precisely those not on the raft:

$$\frac{\partial \Lambda}{\partial \mathrm{LR}} \;>\; 0 \quad\text{through both factors:}\quad \text{coverage}\uparrow \ \text{and}\ P(S\mid A)\downarrow$$

This is what makes the middle of a campaign a cliff. It is not an S-curve someone
drew; it is the arithmetic consequence of two conservation facts — **people are
finite, and patrons are funded by people.** No other game has this, because no
other game makes the same population serve as both the revolutionary base and the
reactionary treasury.

Symmetrically, the militia has a positive feedback of its own in the other
direction: as it grows it can pay more, which recruits more, which pays more. Both
branches are self-reinforcing, which is the definition of a bistable system, and
which is why the Director's "true-by-default, not set in stone" is the correct
description: there are two stable branches and the board starts on the wide one.

### 3.5 The edge clause, and why the DSA can hold a class it cannot feed

The third conjunct of the defection flow — $\exists e_{i\to r}$ — is the single
most important line in this briefing for the player's actual decisions, because
it explains a puzzle that would otherwise look like a bug: **DSA can hold the
middle strata while delivering nothing, and a player with a magnificent raft can
be ignored by the same households.**

The answer is that the two organizations have different edges, and defection is
gated on edges, not on quality:

- The DSA cell's edges run into $C_{la}$ union locals, $C_{pb}$ business
  associations, faith networks. It is *inside* the stratum already.
- The militia's edges run into the same churches, the VFW post, the sheriff's
  office and the homeowner WhatsApp group. Also inside.
- The player's edges run wherever the player has organized. If the player has
  spent 20 periods in the semi-colony and never built a single edge into Maple
  Heights, then $\Lambda$ can be arbitrarily large and
  $\Delta\mathrm{LR} = 0$ — **the raft is real and nobody can reach it.**

That is a genuinely instructive failure, and it is the mechanical expression of
Mao's "it is essential for the peasant associations to … do a good deal more
explanatory work among them" and of Zetkin's "win over or neutralise those wide
masses." It also gives the player a *specific, cheap, non-obvious* action:
`BUILD_EDGE` into a $C_{pb}$ institution, which costs Cadre Labor and buys no
goods at all, and which is worthless until the raft exists — and then is
everything. A game where the correct move is to spend resources on something that
does nothing for ten periods, and then wins the mid-game, is a game that teaches
something.

### 3.6 Why agitation is not merely useless but *negative*

This is the required proof, and it is short because it is structural rather than
arithmetic. **Agitation appears in no term of $\Lambda$ on the raft side.** It is
not multiplied by zero; there is no slot for it. Concretely:

- $A_t$ (rallies, speeches, paper sales, social-media reach) does not enter
  $\mathrm{LR}$: $\mathrm{LR}$ counts delivered goods, and agitation delivers none.
- $A_t$ does not enter $O_t$: organizational stock is org nodes and SOLIDARITY
  edges, and a crowd is neither (porch-02's Populist/Influencer Trap: "a million
  followers and zero soldiers").
- $A_t$ *does* enter $R_t$: State attention and militia believed-yield are both
  computed on the legible projection, and agitation is the cheapest thing on the
  board to see (`synopticon-spec.yaml`: "The State does not hate you. The State
  processes you"; risk scoring ingests Pattern-of-Life over ticks). So agitation
  **raises** $R_j$, which **lowers** $P(S\mid R)$.
- $A_t$ *does* enter the militia's recruitment pool, via the household-level
  condition below.

Therefore, for fixed goods and fixed defence:

$$\frac{\partial \Lambda}{\partial A} \;<\; 0$$

**The fiery speech is not neutral; it is a transfer from the raft to the
militia.** It costs Cadre Labor, it raises the repression allocated against your
base area, and it supplies the militia with the agitation it needs to recruit. It
is the single most expensive mistake available to a player, and the game should
punish it without ever explaining why — the player should discover, three periods
later, that the depot got raided and the suburb got a new militia chapter.

The existing `Fascist_Pull = Agitation × (Entitlement / (Solidarity + 0.1))` in
`reactionary-subject.yaml` gets the sign right on Solidarity and gets everything
else wrong (see §3.9). It should be replaced by the household conjunction:

$$\text{militia recruits}^c_{j,t} = \#\left\{i \in c,j \;:\; \underbrace{\Delta w_{i,t} < 0}_{\text{income actually fell}}\ \wedge\ \underbrace{\mathrm{eligible}(i)}_{\text{ascribed predicate}}\ \wedge\ \underbrace{\exists e_{i\to m},\ m\in\text{militia}}_{}\ \wedge\ \underbrace{b^M_i > b^D_i}_{\text{the militia outbids the buffer}}\right\}$$

Four Booleans over a population. Note what replaces the magic loss-aversion
coefficient $\lambda = 2.25$ that research `13` row 5 flags: **loss aversion is
not a psychological constant, it is the measure of households whose income
actually fell this period.** That is a strictly better model and it needs no
constant at all.

### 3.7 Worked example, small integers

Wayne County, period 14. $N^{C_{pb}} = 4{,}000$ households in the suburb belt.

- Reformist buffer pays $b^D$ to 1,100 households, enough to clear subsistence.
- Militia pays $b^M$ to 250 households (deputies, informers, stipends).
- $\#\{w_i + \max(b^D,b^M) \ge s_i\} = 1{,}340$. So $P(S\mid A) = 0.335$.
- The player runs four institutions. `LR` = 900 households (all four goods, no
  missed period, every institution tested and surviving).
- $O_j = 6$ effective org units; $R_j = 9$ units allocated against the county.
  So $O/R = 0.667$.
- $P(S\mid R) = (900/4000)\cdot 0.667 = 0.225 \times 0.667 = 0.150$.
- $\Lambda = 0.150 / 0.335 = 0.448 < 1$. **No defection.** The median
  shopkeeper stays with the buffer, because the buffer is still paying.

Period 22, after $\Phi$ collapse. Federal transfers are cut: $b^D$ now reaches
300 households. The militia, now on county per-diem, reaches 600.
$\#\{w+\max\} = 780 \Rightarrow P(S\mid A) = 0.195$. The player has rebuilt the
depot twice: $\mathrm{LR} = 1{,}500$, $O/R = 0.60$. $P(S\mid R) = 0.375 \times 0.60
= 0.225$. $\Lambda = 1.15 > 1$. **Defection fires.**

And it does not stop, because the 1,500 on the raft are 1,500 fewer militia
subscribers: next period $b^M$ is lower and $P(S\mid A)$ falls further while
$\mathrm{LR}$ rises. Two periods later the suburb has flipped and the militia's
treasury is empty. *That* is the George Jackson Life Raft Bifurcation, in
numbers, with no constant anywhere in the arithmetic.

Reverse the example: same county, same collapse, but the player built a clinic
and a hall and held three magnificent rallies instead of a depot and a defence
committee. $\mathrm{LR} = 0$ (no household has all four goods, and no institution
has been tested). $\Lambda = 0$. Every one of the 780 squeezed households takes
the militia's offer. The rallies raised $R_j$ from 9 to 13, so even a later raft
would have to clear a higher bar. **The fiery speech did not fail to persuade;
it actively armed the other side.**

### 3.8 The four basins

| Basin | Condition | What the player sees | Reversible? |
|---|---|---|---|
| **Buffer holds** | $\bar b^D \ge \bar b^M$ and $F_t \ge 1$ | the suburb is quiet, the DSA is winning elections, the press is friendly | yes, until $F_t$ breaks |
| **Sterile revolt** | $\Lambda < 1$, buffer failing, no militia yet | wildcat strikes, moralist splinters, occupations with no defence, consumer ingress | **yes, cheaply** — "a few wage concessions and an election" |
| **Warlord** | $R^{\text{captive}} > R^{\text{tax}}$ | the jail grows, the tax office shrinks, deputies multiply | **no** (hysteresis) |
| **Raft** | $\Lambda > 1$ sustained | the depot, the clinic, the jury; defections crossing the canvas | **no** (institutions persist) |

Two of the four are one-way. That asymmetry — the two *political* outcomes are
irreversible and the two *spontaneous* ones are reversible — is the deepest thing
this model says, and it is the reason the game is worth playing twice.

### 3.9 Conformance debt: what must be retired

`ai/epochs/epoch3/reactionary-subject.yaml` contains three constructs that cannot
survive the constitution and should be replaced by the forms above:

| Site | Current form | Violation | Replacement |
|---|---|---|---|
| `chauvinism_mechanic.defection_check.formula` | `Defection_Probability = sigmoid(χ − D)` | ADR173: stipulated S-curve; also a `random()` draw | $\Lambda^c > 1$, a comparison of integer products |
| `fascist_recruitment.recruitment_formula` | `Agitation × (Entitlement / (Solidarity + 0.1))` | magic `0.1`; product of intensities carries a stipulated shape; agitation as a positive term | the four-Boolean household conjunction (§3.6) |
| `lumpen_mechanics.police_enemy_trait` | "STRUCTURALLY incapable of fascism", `NO_DEFECTION` | inference from class interest contradicted by *18 Brumaire* | "cannot **fund** a militia; can fill one" — treasury rule (§1.1) |
| `classes.*.entitlement` / `volatility` | fixed intensities with `+0.01 per tick` accumulation | stored derived quantity; per-tick increments are rates the state should supply | $E$ falls out of $\Delta w$ and $b$; drop the fields |
| `warlord-trajectory.yaml` `branching_condition` | four fuzzy functions, `>= 0.5`, `> threshold` | unnamed thresholds | $R^{\text{captive}} > R^{\text{tax}}$ (§2.5) |

### 3.10 Falsifiers

1. **The product form.** If $\min(\mathrm{LR}/N, O/R)$ predicts observed defection
   episodes materially better than the product across a campaign sweep, the weaker
   link is the right physics. Both are coefficient-free; this is a testable choice.
2. **The tested-ness clause.** If removing $S>0$ (so that untested depots count)
   produces no change in player behaviour or outcomes, the clause is doing no
   work and should be cut rather than kept as flavour.
3. **Agitation's sign.** If a campaign sweep shows players who agitate without
   goods doing *better* on $\Lambda$-driven defections than players who build
   goods, the model is wrong and the whole Zetkin/Stalin reading with it.
4. **The jail/tax crossing.** If any historically documented county flipped to
   convict-lease warlordism *without* captive revenue exceeding tax revenue, the
   condition is falsified and the trajectory file's fuzzy version was right after
   all.
5. **Two-way hysteresis.** If a county that has flipped to captivity returns to
   tax-funded policing on any plausible player input, the hysteresis claim is
   false and the trajectory should be a dial after all.

---

## 4. Gameplay feel: what the player actually sees

The Mao visibility rule governs: "show only what a participant could learn from
reading a communist history book … Concrete countable world-events (funds,
chapters, votes, crowds) may show; engine-computed abstractions (scores,
multipliers, trigger weights) stay buried." **The player never sees $\Lambda$.**
They see four things.

### 4.1 Topology

- **The two reactionary clusters read differently at a glance, and that is the
  whole lesson.** The buffer hub is *soft grey*, many thin edges into $C_{la}$
  locals and business associations, pulsing slowly — legitimate, boring,
  established. The militia nodes are *cold white*, few hard short edges into a
  church basement, a VFW post and a sheriff's office, and they flicker. The
  player learns to read the difference without a legend.
- **The raft is warm and contiguous.** Base-area institutions show as solid warm
  nodes with thick edges into households and into each other. Contiguity is
  visible: a raft with a gap is a raft with a gap, and the militia attacks the
  gap.
- **Defection is a physical crossing.** When $\Lambda$ clears unity, edges
  *recolour and re-route* and nodes detach from the reactionary cluster and move
  across the canvas to the raft. Over two or three periods a whole arc of the
  suburb visibly migrates. This is the single most satisfying frame in the game
  and it must never be a popup.
- **Under fog, the dossier lies.** Reading Maple Heights through a compromised
  node prints `Calm / No Militia Detected` on a county where the posse mustered
  last Tuesday. The lie is only detectable by `SOCIAL_INVESTIGATION` or by an
  attack.
- **The player's own composition rots in view.** Opportunistic consumers
  arriving after a win show as pale, low-weight nodes with one edge and no
  activity — Mao's rich peasants "in the name of some sixty or seventy-year-old
  member of the family." A player who does not look will not notice the node
  getting whiter.

### 4.2 Physical Map

- **The four Goods Clause goods are buildings, not icons.** A county with a
  proven raft shows a depot, a roofed block, a clinic, and a hall where the jury
  sits — with visible damage states. A burned depot shows as a burned depot until
  it is rebuilt. This is what makes §3.7's "tested and survived" legible without
  a number.
- **The warlord county is legible from orbit.** The jail glyph grows; the
  tax-office glyph shrinks; deputy nodes multiply along the roads. A player who
  has watched three counties do this will recognise the fourth before the dossier
  confirms it.
- **Contiguity and the semi-colonies.** Base areas in the Black Belt / Aztlán /
  Indigenous treaty territory show as continuous fill; municipal base areas show
  as islands in a hostile field. The map tells the player which terrain they
  chose, without a tooltip.

### 4.3 Ticker

The Ticker carries the *books*, and the books are the mechanic made visible
without becoming math:

- **The county ledger page.** Two columns — receipts from residents, receipts
  from captives. The crossing is a fact in the world, printable, and the player
  reads it the way a reader of a local paper would: *"the county now earns more
  from its prisoners than from its residents."* No percentage, no bar.
- **The transfer line goes to zero.** $b^D$ falling is rendered as a line in the
  municipal budget drying up, with the households it used to reach named in the
  Corporate Feed as "programme participants" and in the Liberated Signal as
  "people about to be handed to the posse."
- **The disappeared price.** Porch-02's tell, unchanged and now load-bearing: the
  Corporate Feed **stops printing a market price** for bread in a county whose
  depot is real, because that good has left the commodity market. This is the
  single best Base Area indicator in the game and it is a *consequence*, not a
  gauge.
- **The wage concession.** When the militia buys back a sterile revolt, the
  Ticker shows a wage line ticking up and a militia subscription line ticking
  down, in the same period. The player who reads both understands 1968 without
  being told.

### 4.4 Decision Ceremony

The defection moment is a **named event with a face**, not a threshold:

> *"The Maple Heights Small Business Association requests a meeting. They want to
> know whether the Delmar depot will still be running in the spring."*

The choice is real and both options are expensive:

- **Extend the raft** — commit Cadre Labor and goods capacity to a stratum that
  has been your enemy's base. Cost: Cadre, goods, and the temporary neglect of a
  semi-colony node. Reward: $\mathrm{LR}$ coverage in a class you could not
  otherwise reach, and 1,500 fewer militia subscribers.
- **Refuse** — keep the Cadre where the work is. The association goes to the
  sheriff, and the posse gets a treasurer.

And the *seal* (porch-01's immediate answer) must be honest about what is unknown:
*"They will want a guarantee you cannot give. You will not know whether the depot
holds until someone tries to burn it."* The player is told the stake, not the
odds — which is exactly the position of a real organizer, and exactly Mao's
middle peasant asking "can it last?"

The **Party Congress** ceremony (porch-02, Screen 6) gets a second use here: the
rectification that decides whether the new defectors are *admitted as members* or
held as sympathisers. Admitting them brings their entropy and their chauvinism
(the existing `C_la` trap); holding them at arm's length slows $\mathrm{LR}$
growth. There is no right answer, which is the point.

### 4.5 The three feeds, on the same event

- **Corporate Feed:** *"Community leaders praise sheriff's new volunteer safety
  program; local clinic closure blamed on 'unauthorized structures.'"*
- **Liberated Signal:** *"They burned the depot on Tuesday. We rebuilt it by
  Friday. Twelve families who voted for the sheriff in the spring asked where to
  bring flour."*
- **Intel Stream:** `PERIOD 22 | WAYNE CO | OP: ARSON vs INSTITUTION(FOOD_DEPOT)
  | FAILED | LR 1500 (+600) | MILITIA BUDGET -18% | NO CASUALTIES`

Facts pinned, meaning contested, mechanism never explained. The player infers the
equation from three tellings of the same Tuesday, which is the only way it will
ever feel like history rather than a spreadsheet.

---

## 5. Open questions for the porch

1. **Does the raft extend to the *whole* class or to households?** The equation is
   household-level because Mao's middle peasant is a household. But the node model
   is collective (porch-02: "every node is a collective entity"). Should
   $\mathrm{LR}$ be counted per household and aggregated, or per collective node
   with a membership count? The former is honest and expensive; the latter is
   cheap and risks re-introducing the stored-shape problem research `13` §5.2
   warns about.
2. **What is the correct rendering of a *partial* Goods Clause?** Three goods out
   of four currently scores zero. That is a hard conjunct and it may be too
   brittle for play (a player with food, clinic and hall but no jury sees nothing
   for many periods). The alternative — a count of goods rather than a conjunction
   — trades brittleness for a $k/4$ ratio that is still coefficient-free. This is
   a playtest question, not a theory question, but the theory prefers the
   conjunction.
3. **Should `COMPANY_GOON` be a separate cell or a `Candidate` mode of the firm?**
   Pinkerton is a contract, not an organization with its own politics; but the
   1937 Memorial Day massacre and the Battle of the Overpass were political
   events. The `Capacity` model says a cell is whatever owns a budget, so the answer
   probably depends on whether the game wants industrial-scale goon violence to be
   *purchasable* by the bourgeoisie (cell) or *emergent* from firm losses
   (candidate).
4. **Where does the "intoxicated" labor aristocracy's *entry* cost live?** MIM's
   line implies defection is cheap to reverse. Should a defector returning to the
   militia reduce $\mathrm{LR}$ by one and *also* poison the record
   ($\mathrm{miss}_r$ for their institution, or a reputation scar)? The second is
   more honest and harder to model.
5. **Does the sterile-revolt basin need its own named actor?** France 1968 needs a
   place on the board. An `ANARCHIST_MILIEU` cell with a short lifespan and no
   replenishment would be true to the source and would let the player *see* their
   own deviation before it collapses.
6. **Is the federal solvency ratio $F_t$ one number or per-programme?** The
   warlord crossing depends on intergovernmental transfers, which are not the same
   as entitlements. A single $F_t$ hides which county lost which pipe, and the
   pipes are the story.

---

## 6. Sources read

**Repository (read directly).**
`ai/epochs/epoch3/reactionary-subject.yaml` (full, 682 lines) ·
`ai/epochs/epoch3/warlord-trajectory.yaml` (full, 214 lines) ·
`ai/epochs/epoch3/synopticon-spec.yaml` (header, theory, kill chain) ·
`ai/epochs/epoch3/repression-logic.yaml` (header, overview) ·
`docs/gameplay/2026-10-25-porch-01.md` (full) ·
`docs/gameplay/2026-10-25-porch-02.md` (full) ·
`docs/gameplay/porch-handoff.md` (full) ·
`docs/gameplay/00-overview.md` (full) ·
`docs/gameplay/research/13-differential-equations-chaos-and-wealth-dynamics.md`
(full — §0 filter, §1.3 measure-vs-threshold, §3.4 $\Phi$ and the MIM boundary,
§3.7 the crossover, §4.3 basins and hysteresis, Part II magic-number inventory) ·
`rust/crates/babylon-graph/src/capacity.rs` (module doc, `Candidate`, `Capacity::allocate`).

**Marxists Internet Archive** (`/media/user/data/old-hdd/old-hdd/www.marxists.org/`).
Clara Zetkin, *Fascism* (Labour Monthly, August 1923; `archive/zetkin/1923/08/fascism.htm`, read in full) ·
Karl Marx, *The Eighteenth Brumaire of Louis Bonaparte* (`archive/marx/works/download/pdf/18th-Brumaire.pdf`, text extracted; passages on the Montagne and social-democracy, on the Society of December 10, and on the small-holding peasants) ·
Joseph Stalin, *The Foundations of Leninism* (`reference/archive/stalin/works/1924/foundations-leninism/`, ch. II "The Historical Roots of Leninism" and ch. IX "Style in Work") ·
Mao Zedong, *Report on an Investigation of the Peasant Movement in Hunan* (`reference/archive/mao/selected-works/volume-1/mswv1_2.htm`, the middle-peasant and rich-peasant passages). **Not available on this disk:** Mao, *Analysis of the Classes in Chinese Society* — `mswv1_1.htm` is absent from the archive; the Hunan Report carries the same class-routing argument with a sharper durability formulation and is used instead, with no quotation attributed to the missing text.

**MIM(P)** (`/media/user/data/mim/textonly/`).
*MIM Notes* 83 (December 1993), the Black Panther Party / Survival Programs article (`mn/mn083.txt`) ·
*MIM Theory* 10, "Maoism Restored: The Black Panther Newspaper, 1968–69" (`mt/mt10bpp.html`) — the France 1968 analysis, "Myth #5", "Feed the youth and they will feed the revolution" ·
*MIM Theory* 10 cover and contents (`mt/mt10.html`) ·
"Why Maoism, not democratic socialism: Part I" (`MIM.essays/democratic.socialism`) ·
"The Dragon" and "Self-sacrifice needed", *MIM(Prisons)* prisoner essays (`agitation/prisons/essays/the.dragon.html`, `self.sacrifice.html`) ·
MIM Notes letter on survival programs as the basis for building-to-win (`mn/mn048.txt`).

**Guardrail honoured.** No Trotsky. Trotskyism appears nowhere as a source of
mechanics. Theory sources are Marx, Zetkin, Stalin, Mao, George Jackson as read
through MIM(P), and MIM. No claim above is attributed to a file that was not
opened, and the one unavailable text is named as unavailable rather than
paraphrased from memory.
