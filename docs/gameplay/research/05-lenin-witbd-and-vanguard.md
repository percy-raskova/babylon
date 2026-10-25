# 05 — Lenin, *What Is To Be Done?*, and the Vanguard Problem

Research briefing, read-only sweep, 2026-10-25. Question: **what does Lenin's 1902
argument give a game that wants the player to feel the difference between motion and
consciousness?**

## What was read

- `.../marxists.org/archive/lenin/works/1901/witbd/` — `index.htm`, `ch02.htm`
  (Spontaneity of the Masses / Consciousness of the Social-Democrats), `ch03.htm`
  (Trade-Unionist Politics and Social-Democratic Politics), `concl.htm`. **The local
  mirror holds only these three chapters.** Chapters I (Dogmatism and "Freedom of
  Criticism"), IV (Primitiveness of the Economists and Organisation of the
  Revolutionaries) and V (The "Plan" for an All-Russia Political Newspaper) were fetched
  from `marxists.org/.../witbd/{ch01,ch04,ch05}.htm` and read in full. The gap matters:
  the two chapters this task cares most about — topology and the newspaper — are exactly
  the ones absent locally.
- `prolewiki/Exports/Library/` — *Imperialism… The division of the world among the great
  powers*; *Backward Europe and advanced Asia*; *Materialism and empirio-criticism… The
  criterion of practice in the theory of knowledge*.
- Vocabulary ground truth: `docs/gameplay/2026-10-25-porch-01.md`,
  `research/02-systems-and-surfaces.md`, `docs/commentary/theoretical-foundations.rst`.

**Guardrail honoured.** No Trotsky, no permanent revolution, no super-imperialism. Where
the text runs out, the correction comes from MLM-TW/MIM(P) positions already encoded in
`theoretical-foundations.rst`, not from the deviation.

---

## 0. Thesis

**"What Is To Be Done?" is not a pamphlet about propaganda. It is a pamphlet about the
difference between an activity and the sphere the activity takes place in — and Babylon's
characteristic failure mode is a beautiful, textured activity in too small a sphere.**

The book repeats one structure four times:

| The narrow thing | The wide thing | What the narrow thing *is* |
|---|---|---|
| spontaneous strike | class-political struggle | trade-unionism |
| amateur study circle | organisation of revolutionaries | a raid's easy prey |
| local leaflet | all-Russia newspaper | a rumour with a deadline |
| "freedom of criticism" | integral theory | a reformist appendage |

Each row is a **trap that looks like the real thing and pays better in the short run.**
That is a design brief.

---

## 1. Spontaneity vs. consciousness — why "just clicking strikes" traps the player

Lenin is not saying workers are stupid. He is saying the *relation* contains the limit:

> "The working class, exclusively by its own effort, is able to develop only trade union
> consciousness, i.e., the conviction that it is necessary to combine in unions, fight the
> employers, and strive to compel the government to pass necessary labour legislation."
> (ch. II)

The mechanism, stated twice with unusual bluntness:

> "Class political consciousness can be brought to the workers **only from without**, that
> is, only from outside the economic struggle… The sphere from which alone it is possible
> to obtain this knowledge is the sphere of relationships of all classes and strata to the
> state and the government, the sphere of the interrelations between all classes."
> (ch. III §E)

The ceiling is informational, not moral. Inside the wage relation you learn exactly one
thing: what the boss and the state do to *you*. That is real knowledge and it is the whole
content of a good union. What you cannot learn inside it is where you sit in a system,
because the wage relation is precisely what hides the system from the people standing in
it. Hence the sentence that belongs on the Topology screen:

> "In order to become a Social-Democrat, the worker must have a clear picture in his mind
> of the economic nature and the social and political features of the landlord and the
> priest, the high state official and the peasant, the student and the vagabond."
> (ch. III §C)

Operationally: *"the Social Democrats must go among all classes of the population; they
must dispatch units of their army in all directions."*

**Why it is a trap and not a difficulty slider:** because the narrow sphere *pays*. The
Economists were, in Lenin's words, "successful because they adapted themselves to the
backward workers" (ch. III). The strike loop wins raises; raises are popular; popularity
recruits; recruitment feels like progress. Every signal inside the loop is green. The only
thing that does not grow is the capacity to answer a question posed from outside it — a war,
an injunction, a fascist formation, a general repression — because those arrive as *state*
events, and the trade-unionist party has never built an edge to the state relation or to any
stratum outside the wage.

> "the workers, were not, and could not be, conscious of the irreconcilable antagonism of
> their interests to the whole of the modern political and social system." (ch. II)

And the outcome, in the sharpest line in the book: "working-class trade-unionist politics is
precisely **working-class bourgeois politics**" (ch. III §F). Not "becomes" — *is*. The
narrow form is not a lesser version of the wide form. It is a different class's politics
wearing the working class's clothes.

### Design consequence: two non-fungible registers

Babylon currently has one `Ψ` and one bifurcation term, which flattens the book's argument.
Split it:

- **Trade-union consciousness (TUC)** — from strikes, grievances, won contracts,
  shop-floor organisation. Buys cohesion, dues, willingness to strike again, immunity to
  company-union capture. **Caps out.** Cannot be spent on anything in the state relation.
- **Political consciousness (PC)** — from exposures (§3) and study only. Buys the ability
  to act on other classes, to read state moves a period early, to hold a line under
  repression.

**TUC does not convert to PC at any exchange rate.** A player with enormous TUC and no PC is
not "most of the way there." They are a strong union in a country about to outlaw unions,
and the game will not say so. Neither renders as a bar: TUC is legible from what the org can
**do** (a strike holds, a contract is signed), PC from what it can **say** and **see** (an
exposure lands outside the industry; a state move is anticipated early).

**The ceiling must speak.** Do not padlock political actions. When the player reaches past the
ceiling, answer with a *character* — the trusted shop steward who says "let's stick to what we
can win." That is the ceiling voiced in the world's own language, it is a real argument, and it
is the first symptom. The lock is the content.

---

## 2. Primitiveness (*kustarnichestvo*) and the Topology screen

Chapter IV §A is not metaphor; it is a tick sequence:

> "A students' circle establishes contacts with workers and sets to work, without any
> connection with the old members of the movement, without any connection with study
> circles in other districts… without any systematic plan of activity covering any length
> of time."

> "They marched to war like peasants from the plough, armed only with clubs."

Then growth, then the state's read:

> "the police, in almost every case, knew the principal leaders of the local movement, since
> they had already 'gained a reputation' for themselves in their student days, and the police
> waited only for the right moment to make their raid… they always permitted several of the
> persons known to them to remain at liberty **'for breeding'**."

> "Usually the initiation of such actions ends in an immediate and complete fiasco."

Three mechanics are already fully specified there:

1. **Reputation is accumulated observability.** The amateur is not caught by infiltration.
   They are caught because they are *known* — from student days, public speaking, signing
   things. Visibility is a stock.
2. **The state farms you.** Known nodes are left alive on purpose. A node that survives
   because it is useful and well-connected is being *cultivated*; the raid that takes the
   hub takes the closure of everything the hub knew.
3. **The raid is instantaneous and complete.** "A single night raid by the tsarist
   janizaries" (ch. V). An organisation that cannot survive one night is not a smaller
   organisation. It is not an organisation.

**"Primitiveness" is a *theory*, not inexperience.** Lenin is careful: lack of training is
excusable and universal. What he attacks is the justification — "'primitiveness' embraces
something more than lack of training… attempts to justify this narrowness and to elevate it to
a special 'theory', i.e., subservience to spontaneity on this question too." Design
instruction: **the amateur path must have an ideology, sincerely held by characters the player
likes.** "We're not going to become bureaucrats." "We organise where we live." "A cell that
can't act on its own is dead." All true-sounding. All fatal against a state with attention to
spend.

### The professional, precisely

Chapter IV §C draws the distinction the screen should be built on — **two organisations,
different jobs, different shapes**:

| | Workers' organisation | Organisation of revolutionaries |
|---|---|---|
| Membership | all who want the fight | those who make this their *profession* |
| Size | "as broad as possible" | "must perforce not be very extensive" |
| Exposure | "as public as conditions will allow" | "as secret as possible" |
| Internally | trade and craft distinctions remain | "all distinctions as between workers and intellectuals… effaced" |

Both are necessary. The union is public, broad and legible *on purpose* — its openness is
its power. The cadre network is small, secret and **without internal status distinctions**,
because rank is what survives a raid worst: it is written down in who-defers-to-whom.
"Secrecy is such a necessary condition for this kind of organisation that all the other
conditions (number and selection of members, functions, etc.) must be made to conform to it"
(ch. IV §E).

### Mapping onto Topology — no new primitive needed

- **Amateur node (study circle / front group).** High output, high visibility. Enters the
  Lavender score through `velocity` (does a lot, fast) and `centrality` (only thing in its
  district). One Monitor thread maps it.
- **Professional node (cadre cell).** Lower output per node, lower per-node observability,
  redundant edges. Costs more per action, touches fewer people, and — the part players
  hate — **cannot absorb a spontaneous upsurge**, because it is small by construction.

That last cost is not a balancing knob. It is Lenin's answer to Nadezhdin, and the best line
in Chapter V for game purposes:

> "For the very reason that the masses are not ours it is stupid and unseemly to shout about
> an immediate 'assault'… For the very reason that the masses may overwhelm and sweep aside
> the regular troops we must without fail 'manage to keep up' with the spontaneous upsurge by
> our work of 'introducing extremely systematic organisation' in the regular troops."

As a mechanic: **when an upsurge fires, capacity to *lead* it scales with professionalisation;
capacity to be *present* for it scales with breadth.** The amateur org is in the streets and
cannot steer. The sect can steer and is not in the streets. The skill ceiling is holding both.

### Raid resolution: closure, not dice

The state seizes a node it has already mapped (existing Lavender threshold), and the seizure
takes the **transitive closure of "known-by"** from that node. Amateur topology = high fan-out
from one hub = the whole org falls in a night. Professional topology = cellular = one cell
falls and the survivors do not know each other's names. **"For breeding":** nodes known but
unseized survive with a probability the player cannot see. A node that survives because it was
useful is bait — the existing `Gospel` doctrine (`decoy probability is informational only`)
pointed at the player's own graph. Determinism holds: closure over a known graph is a pure
function, and *which* nodes the state holds is fog, not randomness.

---

## 3. Political exposures and the newspaper as *collective organiser*

The load-bearing word is not "scaffolding":

> "A newspaper is not only a collective propagandist and a collective agitator, it is also a
> collective organiser… it marks the contours of the structure and **facilitates communication
> between the builders**, permitting them to distribute the work and to view the common results
> achieved by their organised labour." (ch. V §B)

Everyone quotes the scaffolding. The mechanic is **"facilitates communication between the
builders."** The paper is not content; it is a **protocol** — the thing that makes distributed
work commensurable so results from separate places can be *combined* instead of merely
accumulated. The bricklayer image says the same: "is it 'paper' work to use a line to help them
find the correct place for the bricklaying… to enable them to use, not only every brick, but
even every piece of brick which, cemented to the bricks laid before and after it, forms a
finished, continuous line?" Without the line, bricks are laid "scattered so that the enemy can
shatter the structure as if it were made of sand and not of bricks." With it, **every piece of
brick counts** — including the fragments, i.e. the partial reports from places too weak to act
alone.

### The respawn property — the most underrated mechanic in the book

> "picture to yourselves a very ordinary occurrence in Russia — the total round-up of our
> comrades in one or several localities. In the absence of a single, common, regular activity
> that combines all the local organisations, such round-ups frequently result in the
> interruption of the work for many months. If, however, all the local organisations had one
> common activity, then, even in the event of a very serious round-up, **two or three energetic
> persons could in the course of a few weeks establish contact between the common centre and new
> youth circles**."

A resurrection rate, stated as mechanism. New circles "spring up very quickly even now" — the
supply of people is not the bottleneck; **continuity is.** Hence: **raid recovery time is a
function of whether a common activity exists, not of how many cadres survived.** That also
explains, without a lecture, why the state targets the press first: kill the paper and every
future raid costs the movement months instead of weeks.

### Exposures, not calls

> "To catch some criminal red-handed and immediately to brand him publicly in all places is of
> itself far more effective than any number of 'calls'… Calls for action, not in the general, but
> in the concrete, sense of the term can be made only at the place of action… Our business as
> Social-Democratic publicists is to deepen, expand, and intensify political exposures and
> political agitation." (ch. III §C)

The design claim underneath: **the "call to action" button is the weakest verb in the game and
should be.** A call is cheap, generic, additive. An exposure is specific, dated, attributable
and *multiplicative* — it travels through strata the org does not organise, because a scandal is
interesting to everyone. That is exactly how it lifts the ceiling. Lenin's list of what a worker
should learn to respond to is deliberately cross-class — police brutality, persecution of sects,
flogging of peasants, censorship, torture of soldiers, "the persecution of the most innocent
cultural undertakings": "the most backward worker will understand, or will *feel*, that the
students and religious sects, the peasants and the authors are being abused and outraged by
those same dark forces that are oppressing and crushing him at every step of his life."

So: **exposure is the only action that builds edges to classes you do not organise.** It is how
"go among all classes" becomes a move instead of a mission statement.

**MIM(P) guardrail: exposures are not tailing.** Going among other classes is not following them.
Lenin's formula is "as theoreticians, as propagandists, as agitators, and as organisers," and the
exposure must be told *from a Social-Democratic point of view and no other* (ch. III §C). The
MLM-TW/MIM(P) name for the failure is the popular front: anti-imperialism that dissolves the
party's independence into a bloc led by the national bourgeoisie or the metropole's liberal wing.
In game terms, an exposure aimed at a *useful ally* gets softened — and a softened exposure still
costs distribution and attention, but returns no PC. Tailing is not a moral failing in the model.
It is a bad trade the player will make anyway, because allies are convenient.

---

## 4. "Freedom of criticism" as the opportunist trap

Chapter I reads as sectarian only if you miss the diagnostic. The opportunists are not wrong
about this or that; they demand **coexistence instead of substitution**: "Those who are really
convinced that they have made progress in science would not demand freedom for the new views to
continue side by side with the old, but the substitution of the new views for the old." And what
the slogan cashes out to: "the much vaunted freedom of criticism does not imply substitution of
one theory for another, but freedom from all integral and pondered theory; it implies eclecticism
and lack of principle" (ch. I §D).

The marsh passage is choice architecture, not an insult:

> "We are marching in a compact group along a precipitous and difficult path, firmly holding each
> other by the hand… And now some among us begin to cry out: Let us go into the marsh!… You are
> free not only to invite us, but to go yourselves wherever you will… Only let go of our hands."

Note what is *not* said: the marsh is not forbidden. It is a different place with a different
destination; the only thing at stake is whether the two paths stay coupled.

**Tailism, the second form.** The Economists' programme, per Lenin's paraphrase, demands that
revolutionaries "recognise the sovereign character of the present movement," that the "ideologists"
not "divert" it from the path "determined by the interaction of material elements and material
environment," and that they endorse the struggle "which it is possible for the workers to wage
under the present conditions" — "the only possible struggle, that which they are actually waging
at the present time." Every clause is defensible alone. Material conditions do determine the
terrain. You cannot ask for the impossible. Respecting where people actually are is basic
organising hygiene. The error is in the *aggregate*, which converts a description of the present
into a prohibition on the future.

### Design: degeneration as a rate, not an event

Do not script a "become reformist" event. Build **line drift** with four consequences, each of
which the player experiences first as a success:

1. **Growth is fast.** A big tent recruits sympathy faster than a cadre org by a wide margin.
   This must be true or the trap has no teeth.
2. **Heat falls.** Respectability is real protection; the Lavender score drops because the org
   stops doing what raised it. The player reads this as good play.
3. **Exposures soften.** Any exposure aimed at a faction inside the tent loses specificity: no
   name, no date, no charge. Softened exposures still cost distribution and attention, but return
   no PC. Quiet, per-action, invisible for ten periods.
4. **The Corporate Feed quotes you.** Hegemony's existing machinery supplies the receipt free: a
   legitimate interlocutor gets named approvingly in the official story. The player reads their own
   absorption as a compliment.

When the crisis arrives — war, injunction, fascist formation — the org cannot answer, because its
whole apparatus was built to be acceptable to the people now abolishing it. Lenin's word is not
betrayal but *appendage*: "in practice it meant a strivings to convert the nascent working-class
movement into an appendage of the liberals" (ch. I §C). **No teleology check:** the game never says
"you have degenerated." It reports a fact (the Signal's own archive shows exposures getting
vaguer), lets the player notice, and lets them be wrong.

**The symmetric error must be equally available.** Chapter IV §B insists the Economists and the
"excitative terror" advocates are the *same* mistake from opposite ends: "Both these trends, the
opportunists and the 'revolutionists', bow to the prevailing amateurism; neither believes that it
can be eliminated." A player who over-corrects into vanguardism — raids before roots, exposures with
no distribution, "the masses will follow" — must fail for the reason Lenin gives: the masses are not
yours, they will move without asking, and an organisation not embedded in the upsurge "misses the
revolution itself."

---

## 5. Where the text runs out, and where MLM-TW corrects it

1. **A polemic of 1902, not a plan.** Written before 1905, before the soviets, before the split
   hardened; Lenin abridged it in 1907, dropping a section of Chapter V as "details of the
   organisational relationships and minor polemical remarks." Use it as a diagnostic instrument,
   not a constitution.
2. **The "outside" is national in the text, global under imperialism.** Lenin's answer to "where
   does consciousness come from" is an all-Russia newspaper. Under finance capital the decisive
   outside is the periphery — the source of the rent that buys quiescence in the core. *Imperialism*
   supplies the frame: "Finance capital does not want liberty, it wants domination," and the epoch's
   characteristic form is not colony-vs-metropole alone but "a variety of forms of dependent
   countries… officially politically independent, but in fact enmeshed in the net of financial and
   diplomatic dependence."
3. **So Babylon needs two ceilings.** The **sphere ceiling** (WITBD) is lifted by exposures and
   study — ideological. The **rent ceiling** (MLM-TW, `theoretical-foundations.rst`) holds that
   `W_c > V_c` makes the core worker's material interest run *against* revolution, so no line,
   however correct, lifts it; only material crisis plus internationalist solidarity does, which is
   why the bifurcation term exists and why Germany 1933 and Russia 1917 differ. Synthesis: **the
   newspaper can lift the first ceiling and cannot touch the second.** A perfect paper in a boom is
   a correct party with no army. Crisis without a paper is fascism. That is the whole game.
4. ***Backward Europe and advanced Asia*** gives the core bourgeoisie its motive: "the commanding
   bourgeoisie, fearing the growth and increasing strength of the proletariat, comes out in support
   of everything backward, moribund and medieval." A bourgeoisie that allies with reaction at home
   allies with reaction abroad — the fascist-consolidation engine, requiring no new system, only
   this sentence as the Corporate Feed's house style.
5. **The criterion of practice.** "The standpoint of life, of practice, should be first and
   fundamental in the theory of knowledge" — but "the criterion of practice can never, in the nature
   of things, either confirm or refute any human idea *completely*." Practice judges; it does not
   canonise. A deterministic simulator that refuses to be an oracle is not hedging; it is applying
   the criterion correctly. The sim is the practice, replay is the test, and neither claims to have
   finished the argument.

**Guardrail restated.** Nothing here draws on permanent revolution. Babylon's periodisation is
protracted people's war and stage theory; its imperialism is inter-imperial rivalry over a divided
world — not a unified global capitalist class, not a revolution that never lands.

---

## 6. Proposals (small, testable, visible-rule compliant)

| # | Proposal | Player sees | Under the hood |
|---|---|---|---|
| P1 | **Two registers.** TUC and PC, non-convertible. | What the org can *do* vs what it can *say* and foresee. No bars. | Two stocks, different sources and spend surfaces. |
| P2 | **Exposure economy.** PC's only source; needs a named crime, an audience outside the working class, and a channel. | A leaflet that travels, or one that stops at the factory gate. | `{target, date, charge, reach_set}`; PC accrues to `reach_set`. |
| P3 | **The line is a protocol.** With an all-Russia organ, partial reports from weak localities *compose* into a national picture; without it they accumulate as fragments. | A map that resolves. | Join over intel-ledger entries keyed to a common activity. |
| P4 | **Raid = closure.** Seizure takes the transitive closure of "known-by." | One night, then a list of names. | Graph closure over an observed subgraph. |
| P5 | **Breeding.** Known-but-unseized nodes are sometimes deliberate. | Survival that looks lucky. | Existing `Gospel` decoy doctrine aimed at the player's graph. |
| P6 | **Common activity sets respawn.** Recovery depends on the paper, not on survivors. | New circles in weeks, or work stopped for months. | `recovery = f(common_activity_alive)`. |
| P7 | **"Unity" is a button with a receipt.** Merge with a broader formation. | +members, +money, −heat, −line clarity. | Growth-rate choice with a delayed price. |
| P8 | **Inaction has a direction.** No decision means drift to the least common denominator. | The official story becoming warmer. | `line_clarity` decays; decay gates exposure specificity. |
| P9 | **The ceiling speaks.** Reaching past PC yields a character's objection, not a padlock. | An argument from someone they trust. | — |
| P10 | **Two-error symmetry.** Putschism and tailism both reachable, both fail for their own reasons, neither flagged by the UI. | Two plausible mentors, two dead ends. | — |

**Lines worth stealing** (Signal, wiki, tutorial vocabulary): "they marched to war like peasants
from the plough, armed only with clubs" · "remain at liberty *for breeding*" · "a single night
raid by the tsarist janizaries" · "not the trade union secretary, but the tribune of the people"
· "freedom from all integral and pondered theory" · "only let go of our hands" · "put an end to
the third period."

---

## 7. Open questions for the porch

1. **Does the player ever get told about the two registers?** The Veil of Money precedent says
   visible-but-veiled with a path ("Study: Value Theory"). P9 says never named, only voiced. These
   conflict. Which is Babylon?
2. **Is PC a stock or a lens?** A stock can be ground up in a raid, which matches the book's pathos
   but punishes twice. A lens makes theoretical development permanent and only organisation mortal.
   Lenin implies the second — the paper persists, the people do not.
3. **How does the rent ceiling present without a spreadsheet?** `W_c > V_c` is a formula and the
   visibility rule forbids showing it. What does a player *see* when their class is being bribed — a
   wage that keeps beating the cost of living, and a militancy that keeps disappointing them? That
   may be enough, and it is the most MLM-TW-specific thing in the game.
4. **Does the paper die?** If the state can kill the common activity, P6 becomes the central stake.
   If it cannot, the paper is a permanent upgrade and the raid loses its teeth. Lenin says the state
   targets it first; the design should probably agree.
