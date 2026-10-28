<!-- vale off -->
<!-- Research briefing: dated evidence with literal identifiers preserved. Not governed prose. -->

# 21 — The Opportunist Zoo: Adventurists, Patsocs, Sects, Circuit-Warriors, and the Streamer Complex

Read-only design and theory briefing, 2026-10-25. **Gap 2** of the porch series.

The question: in Babylon the player is not the only anti-establishment actor on the
board. Before the Pentagon ever resolves your name in a dossier, you are surrounded
by a historically accurate ecosystem of opportunists, adventurists, grifters and
wreckers competing for **the same workers, the same students, the same Supporter
Labor (SL), and the same Money**. What are they, mechanically, on Topology — and
what does the player do about them?

The answer in one line: **five cells, one bribe, five substitutes.** Each pathology
is a way of spending the imperial bribe $\Phi$ without building power, and each is
distinguished by *which single thing it substitutes* for the institution it failed
to build.

**Sources.** Read today, from disk: `/media/user/data/mim/textonly/`
(`MIM.essays/weatherman.crit`, `MIM.essays/on.trotskyism`,
`MIM.essays/american.leninism`, `MIM.essays/critique.of.rcp`,
`MIM.essays/personality.cults`, `MIM.essays/spartacist.league`,
`MIM.essays/reply.to.trotskyist`, `MIM.essays/mim.attitude`, `faq/mimcowards.html`,
`faq/mimvleft.html`, `faq/howtotellliberal.html`, `us.html`,
`classics/laboraristocracyenemy.txt`);
`/media/user/data/old-hdd/old-hdd/www.marxists.org/` (Lenin, *What Is To Be Done?*
ch. II and Conclusion; *"Left-Wing" Communism* ch. IV and V; Stalin, *Foundations of
Leninism* ch. I, II, IX; Mao, *Quotations* ch. 28 for the *Combat Liberalism*
passage; Debord, "On Chance" 1957 and "Never Work" 1963);
`/home/user/Downloads/babylon_books/ux/` (Debord, *A Game of War*, already briefed in
`research/09`). Repo: `docs/gameplay/2026-10-25-porch-01.md`,
`docs/gameplay/2026-10-25-porch-02.md`, `docs/gameplay/research/{04,06,12,16,17,19,20}`,
`project/research/history-sweep/brief-dt-patsoc.md`,
`ai/epochs/epoch3/{doctrine-tree,cohesion-mechanic,gramscian-wire-vision}.yaml`,
`rust/crates/babylon-graph/src/{capacity,dossier,exposure,induced,backfire}.rs`.

**Limits.** (1) The local Lenin snapshot holds only *WITBD* ch. II and the
Conclusion, and *"Left-Wing" Communism* ch. IV–V; ch. I of *WITBD* ("Freedom of
Criticism") and the rest of *LWC* are **absent from this host**, and
"Imperialism and the Split in Socialism" (1916) is not present at all — the labour
aristocracy is therefore sourced from the Comintern 1920 minutes as MIM quotes them,
not from that article. (2) The Mao snapshot has no full text of *Combat Liberalism*,
*On Correcting Mistaken Ideas in the Party*, or *Oppose Book Worship*; the Red Book
quotation chapter supplies the *Combat Liberalism* passage, and the other two are used
for their **arguments**, not quoted verbatim. (3) *The Society of the Spectacle* is
**not on this host** — the Debord mirror carries only "On Chance" and the "Never Work"
correspondence — so the two theses quoted below are from the standard Smith
translation and are used for argument, not as archival evidence; *A Game of War* is
present and was read in `research/09`. (4) The modern instances named in the
assignment (Palestine Action, Red Guards Austin, the Maoist Communist Union, the
streamer complex) are **not in the local corpus**; they are used as illustrations of
the *type*, and no factual claim about a named contemporary organization is
load-bearing. (5) Stalin's *Foundations* is present as ch. I, II and IX only; the
Short Course is cited through `research/04`.

**Guardrail.** MIM(P) / MLM-TW. Trotskyism appears here **only** as an
opportunist/wrecker deviation with its own failure signature — never as authority and
never as a mechanic worth borrowing. Nothing below treats "ultra-left" as secretly
correct, treats state fragmentation as state weakness, or licenses premature armed
action in the core. The taxonomy is a **description of failure modes available to the
player as much as to the NPCs**; it is not a licence to sneer at the wrecked.

---

## 0. The one-page answer

| # | `OpportunistCellKind` | Substitutes | For the missing | Converts | Drains | Terminal state |
|---|---|---|---|---|---|---|
| 1 | `MORALIST_ADVENTURIST` | **courage** | strategy | SL $\rightarrow$ state heat | **heat** | `SPECTACLE_SPENT`, at an accelerating rate |
| 2 | `STRASSERITE_GRIFTER` | **identity** | class | chauvinism $\rightarrow$ Money | **space** (the "left" slot in the local paper) | `CAPTURED` — it does not die, it changes owners |
| 3 | `DOCTRINAL_SECT` | **doctrine** | organization | dues $\rightarrow$ paper | **cadres** | `OSCILLATION_DEATH` or `POLICE_CONSTITUTED` |
| 4 | `PROTEST_CIRCUIT` | **activity** | roots | crisis $\rightarrow$ placards | **the moment** | `FRONT_GROUP_PROLIFERATION`; the shell survives forever |
| 5 | `SPECTACLE_INFLUENCER` | **audience** | cadre | **organizing hours $\rightarrow$ Money** | your households' 168-hour week | `LANDLORD`. **Nothing.** It succeeds |

Four of the five destroy themselves on a clock the player can read off their books.
The fifth is a **stable attractor**, it is the only one that grows when the movement
grows, and it is the one that looks most like an ally. That asymmetry is the whole
joke and the whole design.

**What this adds to the existing briefings.** `research/17` gives the twelve-cell
Caesarist State; `research/20` gives the four reactionary cells (buffer, militia,
posse, goon). This briefing adds the **missing column of the board**: the non-state,
non-reactionary cells that compete with the player for the *same* base and the *same*
money, and it adds three formal objects those briefings did not need:

1. **The 168-hour siphon** — the streamer's revenue is literally the organizing hours
   the player loses, taken out of porch-02's household identity. No new primitive.
2. **Splash as a dossier fact, not a radius** — there is no heat radius in metres. The
   radius is the State's induced adjacency, so breaking the *visible* connection is a
   real defence and being *more interesting* than the adventurist is a real failure.
3. **The ratchet** — the stunt dies; the appropriation does not. The adventurist's
   real victim is not the person arrested this period but the organizer of period 14,
   because the task-force line item is permanent.

---

## 1. Why the bribe breeds exactly these five

### 1.1 The two enemies are one mechanism

The spine of this entire taxonomy is a single page Lenin wrote in 1920, and it is
worth quoting at length because the game is going to implement it:

> "First and foremost, the struggle against opportunism which in 1914 definitely
> developed into social-chauvinism and definitely sided with the bourgeoisie, against
> the proletariat. … Bolshevism took shape, developed and became steeled in the long
> years of struggle against **petty-bourgeois revolutionism**, which smacks of
> anarchism … and, in all essential matters, does not measure up to the conditions and
> requirements of a consistently proletarian class struggle."
> — Lenin, *"Left-Wing" Communism*, ch. IV

> "the petty proprietor … who, under capitalism, always suffers oppression and very
> frequently a most acute and rapid deterioration in his conditions of life, and even
> ruin, **easily goes to revolutionary extremes, but is incapable of perseverance,
> organisation, discipline and steadfastness.**"
> — ibid.

> "The instability of such revolutionism, its barrenness, and its tendency to turn
> rapidly into **submission, apathy, phantasms**, and even a frenzied infatuation with
> one bourgeois fad or another — all this is common knowledge."
> — ibid.

> "**Anarchism was not infrequently a kind of penalty for the opportunist sins of the
> working-class movement. The two monstrosities complemented each other.**"
> — ibid.

That last sentence is the design premise. The adventurist and the opportunist are not
two unrelated pests; they are **a matched pair**, each generated by the other's
failure. Where a mass party refuses to lead, the moralist adventurer appears and does
something. Where the adventurer discredits the movement, the respectable opportunist
appears and offers to be reasonable. The zoo is not a list. It is a **reaction
cycle**, and the game can show it as one because the cells feed each other's
recruitment.

Lenin then names the three specific errors of the petty-bourgeois revolutionary party
(the SRs), and they map onto three of our five cells with almost embarrassing
precision:

| Lenin's charge against the SRs (*LWC* ch. IV) | Cell |
|---|---|
| "stubbornly refused … to understand the need for a strictly objective appraisal of the class forces and their alignment, **before taking any political action**" | `MORALIST_ADVENTURIST` |
| "considered itself particularly 'revolutionary', or 'Left', because of its recognition of **individual terrorism**, assassination" | `MORALIST_ADVENTURIST` again, and `DOCTRINAL_SECT` (`ULTRA_LEFT`) |
| "thought it very 'Left' to **sneer at the comparatively insignificant opportunist sins** of the German Social-Democratic Party, while they themselves **imitated the extreme opportunists** of that party" | `PROTEST_CIRCUIT` and `DOCTRINAL_SECT` |

The third is the one players will feel most personally, because it is the behaviour of
the people who will denounce *them*.

### 1.2 The bribe is the substrate ($\Phi$ without need)

Imperial rent $\Phi = W_c - V_c$ buys the core's working class above its own
reproduction cost (porch-02 §8; `research/06`, `research/07`). MIM states the
consequence without decoration:

> "MIM holds that the white working class is a bought off labor aristocracy and not a
> revolutionary proletariat."
> — `us.html`, dividing line 3

And Lenin, at the Second Congress of the Comintern, refusing to let "the masses" paper
over it:

> "One tendency is the revolutionaries, the workers who have just come to us, the
> enemies of the labour aristocracy. The other tendency is the labour aristocracy,
> which in all the civilised countries is represented by the old leaders. **Does
> Crispien stand with the tendency of the old leaders and the labour aristocracy or
> with the tendency of the new, revolutionary mass of workers, who are opposed to the
> labour aristocracy?**"
> — Lenin, 30 July 1920, Comintern Second Congress minutes, as quoted in
> `classics/laboraristocracyenemy.txt`

**The bribe does three things to the board, and each one is a cell-generator.**

1. **It creates surplus time and surplus money with no structural need to revolt.**
   A stratum with a car, a mortgage and a 401(k) has evenings free and a reason to
   keep the evenings free. That surplus is the *material base* of all five cells:
   the adventurer's bail fund, the Patsoc's small-business donors, the sect's paper
   subscription, the circuit's meeting hall, the streamer's subscription revenue.
2. **It creates the state's capacity to buy off and to spectacularise.** The same
   surplus funds the Fusion Center grant and the platform's content moderation. The
   bribe is not only paid to workers; it pays for the machinery that turns their
   politics into content.
3. **It makes the *correct* line materially counter-intuitive.** Third-Worldism is
   the only line that names the bribe as a bribe, which means the only line that
   tells the largest, best-resourced stratum in the country that it is not the main
   force. Every other cell offers that stratum a flattering role. That is why the zoo
   is crowded and the party is small, and the game should make the player *feel* the
   pull of that arithmetic every period, because it is the actual historical reason
   the American left is shaped like this.

MIM's four dividing lines exist precisely because the bribe generates endless
plausible-sounding positions, and the lines are the minimum test:

1. capitalist restoration in the USSR after 1953 and in China after 1976;
2. class struggle continues under socialism (defence of the Cultural Revolution);
3. **the white working class is a bought-off labor aristocracy, not a revolutionary
   proletariat**;
4. a disciplined party carrying out the mass line — not "Build a Democratic Workers'
   Party (an independent mass party)."
   — `us.html`, quoting and rebutting *Unity and Struggle*'s Principles of Unity

Cell 3a below is, mechanically, **the cell that fails dividing line 3 and calls the
failure a strategy**; cell 3b is the cell that fails line 4 and calls the failure
purity.

### 1.3 Petty-bourgeois individualism is the form ("rise above")

The bribe supplies the base. The *form* the pathologies take is named with unusual
precision in `faq/howtotellliberal.html`:

> "When there is sweep in Liberalism evident in practice … it comes from **the
> petty-bourgeoisie, gender aristocracy or national bourgeoisie — the in-between
> groups attempting to rise above classes, genders and nations.** … The expression of
> petty-bourgeois Liberalism is **vacillation or a fake neutrality**."

"Rise above" is the operative phrase and it is the formal definition of every cell in
this briefing. The adventurer rises above the tedious work of the mass line by
*acting*. The Patsoc rises above class by *nation*. The sect rises above the
unreliable masses by *doctrine*. The circuit rises above roots by *mobility*. The
streamer rises above organization by *reach*. Each is an attempt to be **above** the
class struggle rather than inside it, and each therefore produces the same tell: **the
inability to name an institution it has built.**

This is why the cells can be modelled with one update rule and one resource
conversion. Their internal diversity is real, but it lives in the authored transition
table, exactly where `research/17` §4.2 puts it: "Heterogeneous cells sharing one
update rule is still a cellular automaton in the strict sense … Heterogeneity lives in
the transition table, which is exactly where BSL belongs."

### 1.4 The five substitutes (the derivation)

Each cell substitutes one thing for the institution it did not build. The
substitution determines what it drains, because **you can only drain what you
actually take hold of.**

| Substitutes | For | Because it cannot face | So it consumes | Which is why its books show |
|---|---|---|---|---|
| courage | strategy | the appraisal of forces that might say *don't* | **heat** | a legal fund, and no institution |
| identity | class | the class relation inside its own base | **space** | a flag, a banner, and no strike |
| doctrine | organization | the unpredictable masses | **cadres** | more papers than members |
| activity | roots | staying in one place long enough to be known | **the moment** | placards, and no committee |
| audience | cadre | the slow, boring, unphotogenic work | **hours** | subscribers, and no hall |

The last row is the only one that is *not* a failure, and §1.6 explains why.

### 1.5 The MLM tests each cell fails

Stalin supplies the universal test, and it is the one the Ticker should implement
literally — **judge by deeds, not slogans**:

> "the testing of the policy of the parties of the Second International, **not by their
> slogans and resolutions (which cannot be trusted), but by their deeds, by their
> actions**; for only in this way can the confidence of the proletarian masses be won
> and deserved."
> — *Foundations of Leninism*, ch. II

> "revolutionary slogans and resolutions are not worth a farthing unless backed by
> deeds"
> — ibid.

> "**The attitude of a political party towards its own mistakes is one of the most
> important and surest ways of judging how earnest the party is** … Frankly admitting
> a mistake, ascertaining the reasons for it, analysing the circumstances which gave
> rise to it, and thoroughly discussing the means of correcting it — that is the
> earmark of a serious party."
> — ibid., quoting Lenin, *LWC*

Then the failure that no amount of courage fixes:

> "'Communist vainglory' … means that a man, who is a member of the Communist Party,
> and has not yet been purged from it, **imagines that he can solve all his problems
> by issuing communist decrees**."
> — *Foundations of Leninism*, ch. IX

Stalin's two named degenerations are the two poles of the zoo, and the game should use
them as its two visual archetypes of failure: **"empty 'revolutionary' Manilovism"**
(the adventurer's decree, the sect's resolution) and **"narrow and unprincipled
practicalism"** (the circuit's placard, the streamer's content calendar). Neither is
"Russian revolutionary sweep combined with American efficiency," which is what a
functioning organization looks like and what the player is trying to build.

MIM applies the same test to the American 1970s and gets the failure signature of cell
1 in one phrase:

> "The gamble that the masses would be sparked to revolt by focoists' heroic endeavors
> never paid off. If the focoists survive the battles, they burn out and sell out.
> **The focoist 'revolution' is never more than a flash of fury.** Weatherman was no
> exception."
> — `MIM.essays/weatherman.crit`

> "Without taking time to build mass support for Maoism, **the commitment of the
> individual cannot overcome the commitment of the bourgeoisie.** … by the early 70s,
> the weight of the responsibility on the tiny core of Weatherman proved too great."
> — ibid.

And MIM gives cell 3 its actual internal mechanism — not "they are stupid," but an
**oscillation with a material driver**:

> "'Left' economism is manifested in a **constant oscillation between viewing the
> masses as asses and believing that the masses would step forward automatically if
> there were a heroic example.**"
> — `MIM.essays/critique.of.rcp`

> "The mass-adulation-for-a-fetish … The reduction of politics to mass adulation for a
> fetish is an insult to both politically backwards and advanced people."
> — ibid., on the Avakian poster campaign ("Revolution in the 80s, Go For It!")

> "Authority and prestige can be established only naturally through struggle and
> practice. They can not be established artificially. **Prestige established
> artificially will inevitably collapse.**"
> — Mao, quoted in `MIM.essays/personality.cults`

That oscillation is *derivable from the cell's budget identity* (§2.6b), which is why
cell 3 gets a strain flag instead of two separate kinds. It is one organism with two
poses, and the pose changes when the money runs out.

### 1.6 Debord: the fifth cell is not a deviation, it is the system's own recuperation

The first four cells are failures *of the movement*. The fifth is a success *of the
system*, and that is why it cannot be modelled as a deviant faction.

> "In societies where modern conditions of production prevail, all of life presents
> itself as an immense accumulation of spectacles. Everything that was directly lived
> has moved away into a representation."
> — Debord, *The Society of the Spectacle*, thesis 1 (Smith translation; not on this
> host — see Limits)

> "The spectacle is not a collection of images; it is a **social relation between
> people that is mediated by images**."
> — ibid., thesis 4

The streamer is not a person who happens to be on Twitch. The streamer is the
**mediation function** in that second sentence, wearing a headset. And Debord's
concept of *recuperation* — the system's ability to absorb a revolt by restaging it as
a consumable — is the exact mechanism by which the streamer converts a wildcat strike
into a 40-minute segment that ends with a subscription link and a voter-registration
card.

This is why the failure signature of cell 5 is *nothing*. The other four are
deviations from the movement's own standard, so they can be measured against it. Cell
5 has no such standard: it is the **market form of political feeling**, and markets do
not fail, they clear.

It also explains why exposure fails against it (§3.3). Exposure is content. A
40-minute video about how a streamer is a grifter is a 40-minute video, and it will
outperform the organizing meeting it was supposed to promote, because the meeting
requires a Tuesday evening and the video requires a thumb.

The one thing Debord's own game gives us here is the topological lesson already in
`research/09`: in *A Game of War*, a unit's entire strength is a function of whether
its line of communication to an arsenal is intact. The streamer has **millions of
edges and no arsenal**. The player's party has few edges and an arsenal. That is the
difference the Topology screen must render so that a player can *see* it without a
legend (§4.1), and it is the difference that decides who is still there in period 200.

### 1.7 What is *not* in this taxonomy

- **Not a spectrum from "too radical" to "too moderate."** The five cells are not
  positions on a left-right axis. Cells 1 and 3b are the most "extreme" in rhetoric
  and the least dangerous to the state; cell 5 is the most "moderate" in rhetoric and
  the most useful to it. Any UI that renders them as a slider has destroyed the
  lesson.
- **Not a moral classification of individuals.** Every cell is a *role with a
  performance floor*. Per `research/04`'s reading of *Our Tasks*, a wrecker must
  produce real successes to keep cover; per porch-02, a node's figurehead can be
  captured while 97% of the rank and file is flippable. The cells are structures, and
  the people inside them are mostly honest.
- **Not a licence for the player to purge.** The zoo is a *recruitment reservoir* as
  much as a drain (§3.4). A player who treats every contact with a wrecked cell as
  contamination becomes cell 3b.

Mao's formulation in *Combat Liberalism* is the exact midpoint, and it is worth putting
on the Line screen because it is the sentence the whole zoo is a test of: a Communist
is one who "should adhere to principle and wage a tireless struggle against all
incorrect ideas and actions, **so as to consolidate the collective life of the Party
and strengthen the ties between the Party and the masses**"
(`Quotations from Chairman Mao Tse-tung`, ch. 28, quoting *Combat Liberalism*,
7 September 1937). Two clauses, and both are load-bearing. Struggle **and**
consolidate. The sect keeps the first and drops the second; the circuit keeps the
second and drops the first; the streamer drops both and calls the result a community.

---

## 2. The board: `OpportunistCellKind`

### 2.1 The cell, in the vocabulary already in the tree

Nothing here needs a new primitive. `babylon-graph/src/capacity.rs` (ADR184) already
says the whole thing, and `research/20` §2.1 already quotes it: `Capacity` belongs to
an organization, repression and revolutionary action are *the same allocation*, and
**the class difference lives entirely in replenishment**. An opportunist cell is an
`organization` node with:

| Field | Type | Authored? | Meaning |
|---|---|---|---|
| `kind` | `OpportunistCellKind` | content (BSL `defenum`) | which of the five |
| `mandate` | finite set of `(instrument, target_kind)` | content | what it can legally price |
| `capacity` | `Capacity{owner}` | derived | what it can pay for this period |
| `dossier` | `Dossier{owner}` | derived | what it believes about the movement and the state |
| `market` | `NodeId` of a `MEDIA_MARKET` | authored | whose 168-hour week it draws from |
| `reach` | $\sum_e \text{strength}_e(\rho^{\text{trans}}_e+\rho^{\text{org}}_e)$ over live edges into SL-holding nodes | derived | how many people it can actually ask, and how hard |
| `eta` | $\eta$ — SL $\rightarrow$ CL conversion | **Designed** | how much cadre it makes per supporter-hour |
| `mu` | $\mu$ — SL $\rightarrow$ Money monetization | **Designed** | how much money per supporter-hour |
| `legibility` | $\ell\in[0,1]$ | derived from instrument | fraction of its action visible in *State* resolution channels |
| `overhead` | `Currency` per period | derived from mandate | the paper, the hall, the server, the lawyer |
| `strain` | enum, `DOCTRINAL_SECT` only | authored rows | `RIGHT_OPPORTUNIST` $\vert$ `ULTRA_LEFT` |
| `patron` | optional `FUNDS` edge | authored/derived | platform, foundation, capital faction, foreign body |

`kind` should be a **content-declared** enum in the same shape as the existing
`OrgKind` (`(defenum OrgKind (STATE_APPARATUS BUSINESS POLITICAL_FACTION
CIVIL_SOCIETY))`, `babylon-bsl/src/declarations.rs`), not a hard-coded Rust enum, so
that a mod or fixture can add a sixth cell without a code change — consistent with
"Unknown mod and fixture IDs remain self-declared." The engine matches on the *string*
and the *transition table*, never on a closed set.

Two consequences fall out immediately and neither is coded:

- **The cell's `reach`, not its rhetoric, decides its income.** A cell with 400
  followers and no reciprocal edges is poor no matter how revolutionary the
  communiqué.
- **`legibility` is a property of the instrument, not of the cell's courage.** A
  printed communiqué is analog and nearly invisible; a livestreamed occupation is
  digital and 100% visible. Per `research/19`, the NSA sees "100% of digital edges …
  and 0.0% of analog human contact." The adventurer's choice of *medium* is therefore
  the single largest term in his splash, and the player can read it off the Topology
  before the arrest happens.

### 2.2 The five cells

All five spawn as `organization` nodes on Topology with a media market, a dossier
scope, and a replenishment channel. None is player-controlled. All five are responding
to the same $\Phi$ and bidding for the same $C_{pb}/C_{la}$ households that
`research/20`'s buffer and militia are also bidding for — which is why the county can
hold five left cells and two reactionary ones at once and still have nobody in a
union hall.

---

#### 1. `MORALIST_ADVENTURIST`

| | |
|---|---|
| **Real-world type** | Palestine Action-style direct action on arms capital; Weather Underground; RAF; Earth/Gaza-style sabotage campaigns; "if we do nothing we are complicit" |
| **Mandate** | `(SPECTACLE, SYMBOLIC_PROPERTY)`, `(SABOTAGE, PROPERTY)`, `(RECRUIT, STUDENT)`, `(PUBLISH, COMMUNIQUE)` |
| **Its own objective** | **moral coherence.** Its local maximum is the *absence of complicity*, which is why no outcome can ever satisfy it: the world is still complicit, so there is always another action |
| **Replenishment** | individual donations + legal fund + (in later states) expropriation |
| **$\eta$ (SL$\rightarrow$CL)** | $\approx 0$ and **negative in practice** — it burns trained people and produces no new ones |
| **$\mu$ (SL$\rightarrow$Money)** | **negative** — every action costs money per participant |
| **`legibility` $\ell$** | high by construction: the communiqué *is* the product |
| **Drain** | **heat.** Its product is a State candidate, not an institution |
| **Splash** | high, and it lands on every node sharing a `PRESENCE` territory or a front (§2.5) |
| **Tell** | the communiqué is longer than the membership list; the target was chosen for its image; it cannot name one institution it has built; its newest member is always its most serious |
| **Terminal** | `SPECTACLE_SPENT`: reach decays, intervals shorten, arrest terminates the curve (§2.6a) |

The one thing to get right: **this cell is not cowardly and not insincere.** Its
members are, on average, the bravest people on the board. That is exactly why it is
dangerous to the player's base — the students it recruits are the ones the player
wanted, and it recruits them by offering a Tuesday that *means something* instead of a
Tuesday spent folding a newspaper. The player's answer cannot be "don't care"; it has
to be an institution that makes the boring Tuesday mean more than the paint can.

---

#### 2. `STRASSERITE_GRIFTER`

| | |
|---|---|
| **Real-world type** | ACP/PatSoc/Red-Brown/"MAGA Communism"; Hamburg National Bolshevism 1919–21 as the ancestor case (`brief-dt-patsoc.md` §1.3); Traditionalist Worker Party as a US instance |
| **Mandate** | `(AGITATE, LABOR_ARISTOCRACY)`, `(ELECTORAL, SMALL_BUSINESS)`, `(TAIL, SHERIFF)`, `(PURGE, INTERNATIONALIST)` |
| **Its own objective** | **respectability inside the settler nation.** Its local maximum is being *invited* — by the chamber of commerce, the sheriff's cousin, the veterans' post |
| **Replenishment** | small-business donations, patriot-money, and sometimes a capital-faction patron (the historical shape: RM 10,000/month from the Rhenish-Westphalian coal syndicate to keep an internal counterweight alive, `brief-dt-patsoc.md` §1.5) |
| **$\eta$** | low but **nonzero** — it does recruit, and its recruits are the wrong class |
| **$\mu$** | **high** — it monetizes chauvinism efficiently. It is the only *movement* cell in the zoo that is well funded; the streamer is funded too, but a streamer is not a movement |
| **`legibility` $\ell$** | low on itself (the state likes a channel), high in the Corporate Feed (it is reported as "the left") |
| **Drain** | **space.** It occupies the "left" slot in the local paper, so the player's actual work is reported as an absence |
| **Splash** | low to itself; **high on the player** through shared fronts, because attribution in the Corporate Feed is by association, not by membership |
| **Tell** | the flag and the hammer in one image; "class unity" that never names a class relation; the sheriff's endorsement; the strike it has never won; the meeting that is 40% small landlords |
| **Terminal** | `CAPTURED` — absorbed by an actual fascist formation (its members become `MILITIA_AUTONOMOUS` recruits in `research/20`'s table) or by the state as an informant channel. **It does not die. It changes owners.** |

This cell is the only one whose *growth* is evidence against it, and the design should
make that legible: the Patsoc's `reach` rises while the county's strike count falls.
The player's counter is not exposure (exposure makes it a martyr, which is its
business model) but the **material test** already specified in
`brief-dt-patsoc.md` §3: classify the values and ask *who benefits materially*, then
show the base the answer. That is expensive (it costs Cadre Labor and it requires the
player to have an actual alternative), and it is the only thing that works.

---

#### 3. `DOCTRINAL_SECT` (two authored strains)

| | `RIGHT_OPPORTUNIST` (3a) | `ULTRA_LEFT` (3b) |
|---|---|---|
| **Real-world type** | First-Worldist "Maoism": the MCU type that keeps the mantle and drops Third-Worldism, treating the bribed labour aristocracy as the "main force"; the "independent mass party" line MIM rebuts in `us.html` | purity cults: masks, "revisionist pig," pickets of soup kitchens and bookstores, "get out of the trade unions," implosion with informants in the leadership |
| **Mandate** | `(AGITATE, LABOR_ARISTOCRACY)`, `(ENTRY, UNION_LOCAL)`, `(PUBLISH, THEORETICAL_JOURNAL)` | `(PURGE, RIVAL_LEFT)`, `(SPECTACLE, RIVAL_LEFT)`, `(PUBLISH, COMMUNIQUE)`, `(RECRUIT, STUDENT)` |
| **Its own objective** | **growth without a line**: maximum members at minimum theoretical cost | **line without growth**: maximum unfalsifiability at minimum contact with the masses |
| **Replenishment** | dues + paper + entryist capture of an existing body's treasury | dues + paper + the *status* of the cadre |
| **$\eta$** | low; produces disciplined people who cannot do anything | **negative**; produces disciplined people who destroy each other |
| **$\mu$** | near zero (dues) | near zero (dues) |
| **`legibility` $\ell$** | low | low, **and the cell's own security culture is the leak** |
| **Drain** | **cadres** — people the player could have trained, spent on the journal | **cadres**, and the player's allies, via guilt by association |
| **Tell** | "mass party," "main force," the labour aristocracy described as "workers"; a strategy that requires the bribed stratum to become anti-imperialist *first* | more papers than members; "freedom of criticism" demanded only by the faction that has none; the denunciation of the largest actual struggle in the city as insufficiently pure |
| **Terminal** | fails on the budget identity → flips to 3b (§2.6b) | `OSCILLATION_DEATH` or `POLICE_CONSTITUTED` (the leadership is the asset) |

**Why one kind with two strains rather than two kinds.** MIM's sentence is the
specification: "'Left' economism is manifested in a constant oscillation between
viewing the masses as asses and believing that the masses would step forward
automatically if there were a heroic example." The two poses are the *same* organism
under different budget pressure. 3a needs growth, so it flatters the labour
aristocracy. 3b needs cohesion, so it purifies. When the treasury breaks, growth
becomes impossible and purity becomes the only affordable product — so the cell flips,
and the flip is a split, and the split costs members. That cycle is a single
transition rule, and it is the most historically accurate thing in this briefing.

Lenin's answer to 3b's self-justification is worth putting on the screen verbatim,
because a player will hear it from a faction leader and should recognize it:

> "The mere presentation of the question — 'dictatorship of the party or dictatorship
> of the class; dictatorship (party) of the leaders, or dictatorship (party) of the
> masses?' — **testifies to most incredibly and hopelessly muddled thinking.**"
> — *LWC*, ch. V

and the German lefts' programme that produced it ("Get out of the trade unions!") is
the direct ancestor of every "don't work inside the institutions" pose the player will
meet.

**Why `POLICE_CONSTITUTED` belongs to this cell specifically.** The security culture
that makes a sect a sect — the masks, the compartmentalisation, the loyalty tests —
is also the structure that protects an informant, because it makes *internal
investigation* a betrayal. `research/17` §2.2 gives the mechanism at the top of the
movement (Malinovsky: at discipline $\approx 0.8$ the spy's labour output exceeds the
intelligence leaked, so the state is subsidizing the organization). The sect is that
equilibrium made into an ideology: **the more disciplined it looks, the better the
asset is protected.** The cell's terminal state is not exposure; it is that the
exposure never happens.

---

#### 4. `PROTEST_CIRCUIT_TROTSKYIST`

| | |
|---|---|
| **Real-world type** | the newspaper-and-front-group franchise: parachute into every crisis with pre-printed placards, fifty fronts, hostile entryism, "freedom of criticism," gone before arraignment |
| **Mandate** | `(SPECTACLE, CRISIS_SITE)`, `(ENTRY, UNITED_FRONT)`, `(PUBLISH, WEEKLY)`, `(SELL, NEWSPAPER)` |
| **Its own objective** | **the sale.** Its local maximum is newspaper sales and front-group count, the only metrics in politics that never require winning anything |
| **Replenishment** | paper sales + dues + a national organization transfer |
| **$\eta$** | near zero, and **negative toward the player**: it converts *your* SL into *its* placards |
| **$\mu$** | low, but *reliable* — the paper is a real revenue line, which is why the cell persists |
| **`legibility` $\ell$** | low, and **the state's dossier on it is thin — which is a verdict, not a mercy** |
| **Drain** | **the moment.** It arrives first and defines what the crisis means, so the player's slower, deeper work is narrated as a footnote to its press release |
| **Tell** | placards already printed; the front has a name, a bank account, a P.O. box and no members; leaves before the bail hearing; "freedom of criticism" as a demand rather than a practice; the resolution that expels the majority |
| **Terminal** | `FRONT_GROUP_PROLIFERATION` — splits into more fronts than it has cadres, and the split is a *property division* (the mailing list, the paper's name, the P.O. box). It survives forever as a shell |

The state's thin dossier deserves its own line in the design, because it is the
cruellest and most useful tell in the game. `research/17` §4.4: candidates are drawn
from $L_c$, and `decapitation_value` divides by signature-class size. A cell the state
has priced at near zero is a cell the state has *correctly* judged to be not worth
repressing. So the Topology screen can show, without any new mechanic: **the circuit's
node is not being watched, and that is what being harmless looks like.** A player who
wants the state's attention as a proof of seriousness has already become this cell.

---

#### 5. `SPECTACLE_INFLUENCER`

| | |
|---|---|
| **Real-world type** | the streamer/podcast/BreadTube complex: subscription revenue, parasocial reach, election-year sheepdogging back into the Democratic Party or the DSA |
| **Mandate** | `(BROADCAST, AUDIENCE)`, `(MONETIZE, AUDIENCE)`, `(ENDORSE, DEMOCRATIC_PARTY)`, `(SHEEPDOG, AUDIENCE)` |
| **Its own objective** | **audience retention.** Its local maximum is watch-time, which is *inversely* related to the audience's own organizational activity, because the hour is the same hour |
| **Replenishment** | subscription + platform share + sponsorship (`FUNDS` edge from a platform or a patron) |
| **$\eta$ (SL$\rightarrow$CL)** | **exactly zero, by construction.** That is the definition, not a tuning value |
| **$\mu$ (SL$\rightarrow$Money)** | **the highest of all five** — the most efficient supporter-hour-to-money machine ever built |
| **`legibility` $\ell$** | low on itself (it is a *channel*; the state prices it as media, and it is useful), high on anyone who appears on it |
| **Drain** | **your households' 168-hour week** (§2.4) — the only cell that consumes the raw material instead of organizing it |
| **Tell** | enormous audience, nonexistent institution; the call to action is a link; the merchandise; the election-year pivot; the studio that is nicer than the hall |
| **Terminal** | `LANDLORD`. It does not fail. It converts into a media landlord and an electoral broker, and it **grows when the movement grows**, because it feeds on the movement's own spectacle |

The design rule for this cell is one sentence: **its revenue is the player's lost
organizing hours, and the game should show both numbers in the same period.** Porch-02
§4 already gives the identity $E = (T_{\text{wage}} + T_{\text{repro}} +
T_{\text{commute}})/168$; the streamer adds a fourth term, $T_{\text{consume}}$, and
`research/14`'s ATUS/QCEW work already has the data shape for it. When the playtest
shows a player that the 90 minutes their best contact spent watching a video is the 90
minutes she did not spend at the tenant meeting, the cell has taught itself.

---

### 2.3 The finite state alphabet and the update rule

Five states for four cells, five for the fifth. Small on purpose: per
`ai/state-ai-algorithm.yaml`, a cell must be predictable enough to be exploited.

```
SEEKING → SURGING → PEAK → EXPOSED → SPENT          (cells 1–4)
SEEKING → SURGING → PEAK → SETTLED → LANDLORD       (cell 5)
```

Transitions read only four quantities, all derivable from the snapshot:
`(reach_ratio, income_ratio, own_heat, rival_cells_in_market)`. There is no opinion
term, no "radicalism" scalar, and no hidden morale.

One synchronous update, in the same shape as `research/17` §4.4:

```
OBSERVE   R'  = reach(c) over N(c)                    // reciprocity-weighted, live edges
INCOME    S_A = S_m · r_A / (Σ_j r_j + r_P)           // partition, no constant
          M_A = μ_kind · S_A
PRICE     candidates = { (m,t) ∈ mandate × scope(L_c) }
          yield(m,t) = believed_reach_gain(m,t) / cost(m,t)   // on L_c, never on truth
RANK      allocate(candidates) → funded[], declined[]  // existing total order
ACT       funded[] executed; ℓ from the instrument mix
SPLASH    σ(p) for p ∈ N_c(c)                          // agency dossier adjacency
SETTLE    overhead vs dues·n → strain flip / interval change
```

Three inherited properties do all the work:

- **The candidate set is drawn from `L_c`,** the cell's own dossier. The adventurer
  does not know the plant's security posture; he knows what a student told him. That
  is why he is caught, and it is not a dice roll.
- **Yield is a quotient, so redundancy defends the player** (`decapitation_value`
  divides by signature-class size). A distributed player structure divides its own
  splash as well as its own decapitation value — the same arithmetic, no new rule.
- **Declines are visible.** `AllocationOutcome.declined` carries the shortfall, and
  for these cells the decline is usually the interesting event: *wanted the plant,
  could only afford the recruitment table* is the whole tragedy of the sect.

### 2.4 The siphons: how they eat your SL and Money

`S_m` is the Supporter Labor available in media market $m$ this period, and it is
**not an abstract pool — it is the sum of leftover hours in the households the player
can reach.** Porch-02's identity gives each household a residual
$h_i = 168 - T^{wage}_i - T^{repro}_i - T^{commute}_i - T^{consume}_i$, and
`research/14` already carries the ATUS/QCEW/LODES series behind that identity — ATUS's
leisure-time categories are the natural home for the fourth term.

$$\dot S_A = S_m \cdot \frac{r_A}{\sum_{j \in \mathcal{A}_m} r_j + r_P}, \qquad
\dot M_A = \mu_A \, \dot S_A$$

where $r$ is **reach**: the sum of live edge strengths into SL-holding nodes,
**weighted by reciprocity** — and the weight has two components, because the two kinds
of edge are not the same relation:

$$r_A = \sum_{e \in \text{edges}(A)} \text{strength}_e \cdot
\left(\rho^{\text{trans}}_e + \rho^{\text{org}}_e\right)$$

$\rho^{\text{trans}}$ is the transactional component (money for content, dues for a
paper: the subscriber who pays is genuinely in a two-way relation).
$\rho^{\text{org}}$ is the organizational component (mutual obligation, attendance,
the person who will come on Tuesday when asked). A parasocial edge scores high on the
first and **zero on the second**; a cell-member edge scores on both.

$\mathcal{A}_m$ is the set of opportunist cells in the market; the player's own share is
the same formula with $r_P$. Four consequences, none of them coded:

1. **The market is zero-sum in the short run and positive-sum only in a crisis.**
   Every cell's growth is literally a subtraction from the others' income, which is
   why the zoo is cannibalistic and why the player can benefit from *their* competition
   (§3.1).
2. **The streamer wins the partition and loses nothing**, because its $r$ is enormous on
   the transactional component and its $\mu$ is huge. It will take the largest share of
   $S_m$ in any market it enters. This is correct and should not be balanced away.
3. **The player does not need to win the partition — only to convert what they get.**
   The player's payoff is $\eta_P \dot S_P$, and the streamer's is zero because
   $\eta_5 = 0$ by construction. A party with 40 two-way edges out-converts a cell with
   400 one-way edges, which is precisely porch-02's "a million followers and zero
   soldiers" — but stated as a *conversion* fact rather than a reach fact, so the
   correct play is not to chase reach. Losing the pool and keeping the cadre is a
   winning position; winning the pool and losing the cadre is the streamer's business
   model, and it is a losing position that pays well.
4. **$T^{consume}$ is subtracted before the player's SL exists at all.** The streamer
   does not merely outbid the player for a fixed pool; it shrinks the pool. That is
   the mechanic that makes "pacification" a *quantity* rather than an accusation, and
   it is why the same household can be sincerely radical and completely unavailable.

Money follows the same partition with a per-kind $\mu$, and the per-kind values are
the taxonomy's economic signature: the adventurist's $\mu$ is negative, the sect's is
near zero, the Patsoc's is high, the circuit's is small but reliable, and the
streamer's is the largest number on the board. **A player who reads only the Ticker
will conclude the Patsoc and the streamer are the successful ones**, which is true in
the only currency the Ticker prints, and false in the only currency that matters.

### 2.5 The splash: how a stunt becomes your raid

There is **no heat radius in metres.** The radius is in the State's dossier graph, and
that single decision makes the whole mechanic honest.

A stunt is not a "heat" event; it is a **candidate generator**. It writes a
resolvable, high-salience object into the dossiers of whichever agencies can see it,
and those agencies then do what they always do: rank candidates by
`decapitation_value` on their own `L_c` and fund down the list until the budget is
dry (`capacity.rs`; `research/17` §4.4). The player is in that list only if the
agency has **resolved a connection** between the stunt and the player.

$$\sigma(p) \;=\; \Theta^{\text{disp}}_c \cdot \frac{w_c(p)}{\sum_{q \in N_c(A)} w_c(q)}
\cdot \mathbb{1}\!\left[p \in N_c(A)\right]$$

- $\Theta^{\text{disp}}_c$ — the agency's discretionary thread budget after its own
  service obligations;
- $N_c(A)$ — the nodes the agency resolves as connected to cell $A$ (its induced
  adjacency over `PRESENCE`, `MEMBERSHIP`, `FUNDS`, and shared front letterheads);
- $w_c(p)$ — the agency's *believed* yield on $p$, which is
  `decapitation_value` on $L_c$.

Read the three clauses as three player decisions:

1. **$\mathbb{1}[p \in N_c(A)]$ is a membership question, not a geography question.**
   If you do not share a front, a hall, a bank account or a letterhead with the
   adventurer, the splash is **exactly zero** regardless of distance. Two organizers
   in the same city who have never co-signed anything are invisible to each other's
   raids. This is why the CPUSA's respectability was materially valuable and why the
   modern "coalition statement" is a liability with a signature line.
2. **The fraction is a ranking, so you can lose it by being boring.** If the
   adventurer is the most attractive target in $N_c(A)$, he absorbs the threads and
   you get the residue. That is the dark-comedy decoy in its honest form (§3.2): not a
   trick you play on the FBI, but a *position* you occupy in the FBI's ranking.
3. **The denominator includes your own redundancy.** A distributed structure divides
   its own $w_c(p)$ and falls in the ranking. Self-defence is structural, not
   rhetorical, and it is the same quotient that protects against decapitation.

**The ratchet.** This is the part that must not be softened. The agency's
appropriation next period is a function of `demonstrated` output (`research/17` §4.5),
and a stunt is `demonstrated`. So:

$$\text{stunt} \rightarrow \text{thread spent} \rightarrow \text{appropriation request}
\rightarrow \Theta_{c,t+1} > \Theta_{c,t}$$

**The cell dies; the thread budget does not.** The county's task-force line item is
permanent, and the organizer who pays for it is not the one arrested this period but
the one who tries to build a committee in period 14. That is the single most important
sentence in this briefing for the player to learn, and the Ticker can teach it without
a number: the *Corporate Feed* reports the grant as a success story in the same week
the *Liberated Signal* reports the arrest, and the *Intel Stream* shows the line item
persisting after the cell's node has gone dark.

### 2.6 The derived dynamics (three clocks)

#### (a) The adventurist's acceleration

The cell has no institution to hold it together, so **cohesion is maintained by
activity.** Reach decays (SL is volatile, porch-02 §5). To keep the same internal
cohesion, the interval between actions must shrink as reach falls:

$$T_{n+1} = T_n \cdot \frac{r_n}{r_{n-1}}$$

As $r$ decays, $T \to 0$ and the cell acts continuously until it is arrested. That is
"never more than a flash of fury" stated as a *rate*, not a moral judgement, and it
explains the observed pattern that these groups always escalate to the target that
ends them: not because they are insane, but because the interval has to keep shrinking
and only a higher-salience target can shrink it.

The symmetry with porch-02's Party clock is worth stating in the design doc because it
is a good joke and a true one: **`survival_interest` is the slow death of an
institution that outlived its purpose; the adventurist clock is the fast death of an
organization that refused to build one.** Same shape, opposite sign, 100× the tempo.

#### (b) The sect's oscillation

The cell has fixed overhead $O$ (paper, hall, server) that must be covered by dues
$d \cdot n$ where $n$ is membership. When

$$n < \frac{O}{d}$$

the treasury breaks. At that moment growth is unaffordable, so 3a's product (more
members) cannot be sold, and 3b's product (purity) can — because purity is free. The
strain flips. The flip is a split (porch-02 §3.1's antagonism gradient: the minority
stops trying to win the organization and starts appealing outside it), so
$n_{k+1} = n_k - \Delta_{\text{flip}}$, which makes the next breach arrive sooner.
Terminal: twelve people, three newspapers, four tendencies.

No constant is needed: $O/d$ is a **count of members**, printed on the cell's own
books, and the player can read it from the outside as "they are about to have a
split." That is a real intelligence product and it is exactly the sort of thing the
Wiki's vigilance case files are for.

#### (c) The streamer's non-decay

Reach grows with the *movement's* activity (it comments on struggles it did not make),
revenue grows with reach, and overhead is **not proportional to membership** — no
hall, no bail fund, no legal defense, no childcare. Its budget identity has no death
term. It is the only structurally immortal cell on the board.

That is why it must be fought politically rather than materially, and why the ordinary
tool fails: **exposure is content.** The correct pressures are in §3.3.

### 2.7 Determinism, classification, hashes

- **Synchronous, single pass, total order.** Cells iterate a `BTreeMap`-ordered set,
  never a `HashMap`. `allocate` already ranks by
  `(ratio desc, instrument, mode, target, cost, expected_yield)`, so equal inputs give
  equal funding order (`capacity.rs`; `research/17` §4.9).
- **Seeded, not sampled.** Any resolution roll takes `rng_seed` from the tick;
  decisions fold into `NominalWorldHash` only after the detached tick succeeds, per
  `MaterialReplaySession`.
- **Classification (ADR178 C1).** `mandate`, $\eta$, $\mu$ and `overhead` are
  **Designed**; `reach`, `legibility` and `splash` are **Derived**; nothing here is
  **Observed** and nothing is **Calibrated** except the $\eta$ ordering, which should
  be validated against the historical case set and never against a playtest feeling.
- **Loud rejections.** A `Candidate` with a foreign `actor`, non-positive cost, or a
  non-finite yield is a `GraphError`, not a clamp. If a cell's mandate names an
  instrument the content does not price, that is a load error, not a silent zero.

---

## 3. Player counterplay and the five temptations

### 3.1 Four instruments, and what each is actually for

| Instrument | Verb | Works against | Fails against | Real cost |
|---|---|---|---|---|
| **Political Exposure** | `PUBLISH(EXPOSE)` | 2 (Patsoc), 3a (right-opportunist), 4 (circuit) | 1 (martyrdom), 5 (it *is* content), 3b (reinforces the siege) | 1–2 CL; and it names you, which raises your own `legibility` |
| **United Front From Below** | `ENTRY(UF_BELOW)` | all five, at the rank-and-file layer | never fails *politically*; it fails *materially* when you have nothing to offer | 1 CL per period held; the leadership denounces you; liberal allies get nervous |
| **Refusal** | the 1903 / 1912 move | 3b, 4 (entryism), 5 (the interview) | nothing — but it forgoes the honeymoon | porch-02's exact list: fast growth, *falling* heat, Corporate Feed approval, and a soft line |
| **The Decoy / Referral** | `PUBLISH(AMPLIFY)` + a real tip | 1, 5 (temporarily) | 2 (the state protects a channel), 3b (already protected) | §3.2 — it is the most expensive option in the game and the cost is not Money |

**Exposure must target the material relation, not the person.** Exposing a streamer's
politics produces a segment; exposing the fact that his show's budget line pays for a
researcher and a lawyer but not a hall or a bail fund produces a *question in his own
audience*. The design rule: `PUBLISH(EXPOSE)` yields reach transfer **only if it names
a transaction** — a patron, a sponsorship, a salary, a platform deal, a landlord. If it
names an opinion, it yields nothing but reputation with people who already agree.

**UF-from-below is the main instrument and it is the one the player will under-use.**
`research/06` and porch-02 give the mechanism (Leningrad 1925: a delegation or chair can
be captured while 97% of the rank and file underneath can still be flipped by sending
emissaries straight to the base). Concretely: the cell's `reach` edges are the target,
not its `capacity`. A successful `ENTRY(UF_BELOW)` transfers a fraction of $r_A$ to
$r_P$ and, per §2.4, that transfer is *directly* a transfer of income. This is also the
only instrument that works on cell 2, because the Patsoc's base is full of people who
want a class politics and have been handed a flag instead.

**Refusal is the default, and the game must make it cost something visible.** Porch-02
§3.1 is precise: refusing to split gives "fast membership growth, more dues, *falling*
State heat, and the Corporate Feed quoting you approvingly — while your political
exposures go soft." So the `REFUSE` option must show the honeymoon in the *seal*: the
player is told what they are giving up, in countable terms, before they click. That is
the honest version of the temptation, and it is the one thing that makes the correct
play feel like a choice rather than a scold.

### 3.2 The decoy, honestly costed

The user's dark-comedy beat — trick the FBI into raiding the streamer while the real
cadres organize the rail yard — is a real mechanic and it should be implemented with
its real price, because the joke only lands if it is true.

**What it does.** `PUBLISH(AMPLIFY)` raises another cell's `legibility` $\ell$ (a
reporter's tip, a shared document, a well-placed post). That raises its $w_c$ in the
agency's ranking, so `allocate` moves threads off the player's neighborhood for 2–4
periods (§2.5, clause 2). The rail yard gets a quiet quarter. This is a genuine,
powerful, and historically attested capability — it is what an agent provocateur does
in reverse, and it is the kind of thing the state's own agencies do to each other.

**What it costs.** Three things, none of them a moral meter:

1. **A tradecraft signature.** Every referral teaches the agency one of the player's
   methods. Concretely: the player's own future `legibility` rises, permanently, for
   the *instruments* used in the referral. The state learns the mode
   (`research/17` §1.3: `INFILTRATE` and `DIVIDE` are the modes that degrade a
   movement from inside; a movement that uses them teaches them).
2. **The referral chain resolves through a person.** The game should name them. Not a
   statistic: a 23-year-old researcher, an 18-month file, a job lost. The Wiki records
   it under the player's own chapter, and the *Liberated Signal* prints it, because
   porch-01's rule is that the record prints everything ("a history that must print
   its own defeats because the record says they happened").
3. **The Corporate Feed's approval.** If the player does it, the Corporate Feed starts
   describing them as a "movement spokesperson" rather than a "radical." That is a
   *real resource* (it lowers `legibility` and opens doors) and it is bought with
   exactly this currency, which is the most honest way the game can say what
   respectability costs.

There is no fourth cost and there must not be one. The game does not deduct "morality."
It prints the receipt.

### 3.3 What actually works on the streamer

Exposure fails (§2.6c). Refusal is right but insufficient. What works is applying the
**Goods Clause to media**, which is porch-02's Base Area test turned on a broadcaster:

> A neighborhood with patrols that still depends on the State's clinics and food is not
> dual power. It is a Base Area only when your independent institutions replace
> administration by producing real goods.

Applied to cell 5: **a broadcast that produces no hall, no bail fund, no childcare and
no clinic is not a media institution, it is a rent stream.** The player's move is to
*accept* the platform and demand the goods — a line item for the legal fund, a hall, a
childcare shift at the event. Most will refuse, and the refusal is the segment: 200,000
people hear a man with a merchandise line explain why he cannot pay for a hall.

Three further pressures, in ascending order of cost:

- **Build the paper you need anyway.** The player's `PUBLISH` candidate has a different
  yield function: it builds institutions (a subscriber list that shows up, a print shop,
  a distribution crew). The streamer's builds watch-time. Competing on *his* terms is
  the trap; the paper that a real organization requires is not a media strategy, it is
  a by-product, and that is why it wins.
- **Peel the production layer, not the host.** Porch-02 §2: individuals are
  personification chrome on a collective node. The node is the researcher, the editor,
  the booker. They are underpaid, they are politically serious, and they are the ones
  who will be in a room in five years. `ENTRY(UF_BELOW)` on a media cell targets the
  crew.
- **Time.** The audience ages out, and the ones who do not were never available. This
  is the only "strategy" that costs nothing, and it is the reason a patient player
  outlives five streamers.

### 3.4 The reservoir: what a dead cell is worth

When any of cells 1–4 reaches a terminal state, its `reach` edges are released. They
become available `RECRUIT` candidates, and this is the player's **positive payoff for
patience** — the zoo dies and feeds the party.

But the harvest is not free, and the game must charge for it in the right currency:

- **The reception depends on the Goods Clause.** Released cadre join whoever has a
  hall, a paper, and something to do on Tuesday. A player without institutions gets
  none of them, and the released members go to the Patsoc or to a militia, per
  `research/20`.
- **The import carries the deviation.** A harvested adventurist brings the habit of
  action-as-catharsis; a harvested sectarian brings the habit of purity. Porch-02's
  consumer/investor problem is the mechanism: "as soon as a node wins clout …,
  opportunistic consumers flood in." The game should model this as a **strain
  pressure** on the player's own Line, not as a penalty: enough imported adventurists
  and the player's `DOCTRINAL` node acquires an adventurist row, and the next decision
  ceremony offers a stunt as the "obvious" option.
- **And the mirror risk is the point.** The player is not immune to any of the five.
  They are the five ways a good organization dies.

### 3.5 The five temptations (the player's own degeneration paths)

| When you are losing, you will want to | Which makes you | Existing trap id |
|---|---|---|
| do something, anything, that will be seen | `MORALIST_ADVENTURIST` | Faux-Vanguard LARP / premature armed struggle (`research/16`) |
| grow by speaking to the stratum that has the money and the numbers | `STRASSERITE_GRIFTER` | the PatSoc pipeline (`brief-dt-patsoc.md`; `doctrine-tree.yaml`) |
| defend the line by expelling everyone who disagrees | `DOCTRINAL_SECT` (3b) | Purity sectarianism |
| chase every crisis with a statement | `PROTEST_CIRCUIT` | "30 for 40" / Imperialist Economism |
| optimize for reach because reach is the only number that goes up | `SPECTACLE_INFLUENCER` | the Populist/Influencer Trap (porch-02 §5) |

The Line/Doctrine screen already has all five as traps. What this briefing adds is that
they are **also people on the map**, with books you can read, and that the player's own
drift and the NPC's life cycle use the same arithmetic. That is what makes the mirror
work: a player who watches the adventurist's interval shorten (§2.6a) and does not
recognize their own last four periods has learned nothing.

---

## 4. Gameplay feel

The Mao visibility rule governs: *would Mao have put it in the treatise?* Concrete
countable world-events — arrests, subscribers, halls, papers, dollars, crowds — may
show. Engine abstractions — $\eta$, $\sigma$, strain flags, transition weights — stay
buried. **The player never sees a number from §2.** They see five things.

### 4.1 Topology

The five cells must be **distinguishable at a glance, without a legend**, and the
distinction must be the *same distinction* the mechanics use.

| Cell | Colour / form | Edge pattern | Motion | What the player learns |
|---|---|---|---|---|
| `MORALIST_ADVENTURIST` | a single hard **white flare** | many thin media edges, one thick red edge to a high-security node, **brief** | blooms, dies, blooms elsewhere | salience without structure |
| `STRASSERITE_GRIFTER` | flag texture bleeding into red, **warm to the state** | warm thick edges to sheriff, chamber, veterans' post; cold edges to you | steady, smug, *invited* | it is inside the room you are outside of |
| `DOCTRINAL_SECT` | tight cluster of tiny nodes with **hot red edges between them** | almost no outward edges; papers as leaf nodes | vibrates, splits, re-forms | energy pointed inward |
| `PROTEST_CIRCUIT` | a moving **placard rectangle** | transient, identical, low-strength edges; satellites multiply | teleports county to county | presence without residence |
| `SPECTACLE_INFLUENCER` | huge soft **warm** node | millions of hair-thin edges: **strong on payment, zero on obligation**, and **no `MEMBERSHIP` edges at all** | slow breathing, never dims | **warm-diffuse is not warm-contiguous** |

That last row is the design's best visual joke and its most useful lesson. In
`research/20` §4.1 the raft is "warm and contiguous," and the player learns to trust
warmth. The streamer is *also* warm, and it is the only node on the board whose warmth
means nothing. The tell is structural and learnable: **edge count enormous, payment
strong, obligation zero, and not one membership edge.** A player who learns to check
obligation before warmth has learned the whole briefing.

Two further Topology behaviours:

- **The splash is drawn as a *contracting* ring, not an expanding one.** When an
  adventurist acts, the ring does not spread outward from the stunt; it contracts onto
  the nodes the State has *already resolved* as connected. So the player sees the ring
  pass over them only if they share a front, and the ring's path is literally the
  FBI's org chart. That is a screenshot-worthy frame and it teaches clause 1 of §2.5
  without a tooltip.
- **The zoo cannibalises in view.** When one cell's reach collapses, its edges visibly
  re-route to the nearest competitor before the player can act — unless the player has
  an institution to receive them (§3.4). The player who watches a dead sect's members
  walk into the Patsoc's meeting has understood the American left.

### 4.2 Ticker

The Ticker prints the books, and the books are the mechanic made legible without
becoming math. Four recurring lines, all consequences:

- **The hours line.** The household schedule from porch-02 gains a fourth term:
  `WAGE 41 | REPRO 29 | COMMUTE 6 | SCREEN 9 | LEFT 83`. When `SCREEN` rises, `LEFT`
  falls, and the player's available SL falls with it — in the same period, in the same
  ledger. No percentage, no bar, just a week with fewer hours in it.
- **The paper line.** A sect's print bill appears as a recurring debit against a
  shrinking dues credit, and the player can see the exact period the debit exceeds the
  credit. That is the split, three periods early, on the Ticker.
- **The grant line.** The stunt's consequence is printed as a *budget success*:
  "County commissioners approve $2.1M task force expansion to combat domestic
  extremism." The player who connects that line to last period's paint can has learned
  the ratchet.
- **The disappeared price.** Porch-02's tell, reused: when a county's working-class
  institutions stop being a market, the Corporate Feed stops printing a number for
  them. A county whose left is entirely cells 1–5 has no price for a hall, because
  nobody rents one.

**Three feeds, one event** (the paint, §4.3):

- **Corporate Feed:** *"Vandals damage Kentwood plant; FBI joins local task force as
  officials warn of rising domestic extremism."*
- **Liberated Signal:** *"Four arrested two counties away. The task force they paid for
  is now in our county. The paint was not ours; the bill is."*
- **Intel Stream:** `PERIOD 14 | KENTWOOD | OP: SABOTAGE(PROPERTY) | 4 ARREST |
  CELL MASS_LEGIBILITY 0.94 | TASK_FORCE_APPROP +1 | SPLASH: 3 NODES IN
  FRONT_LETTERHEAD | NO PLAYER CASUALTIES`

Facts pinned, meaning contested, mechanism never explained. The player infers §2.5
from three tellings of one Tuesday.

### 4.3 Decision Ceremony

Five named events, each with an honest seal: what is staked, what is unknown, no odds.

**1. "Forty Cans of Paint."**
> *Two counties over, someone sprayed the loading dock of the plant that makes the
> guidance housings. Four people were arrested. They are not yours. But the front you
> both sign letters for has one letterhead, and the field office has already requested
> the subscriber list.*

- **Disavow** — the letterhead coalition breaks; the Corporate Feed prints "the left
  eats its own"; you lose two liberal allies who were useful for permits.
- **Silence** — the splash lands. Two of your cells get a thread each for three
  periods.
- **Send an emissary to their rank and file** — 1 CL, three periods. You get the six
  serious people. One of them is an informant, and you will not know which until you
  have taught him something.

*Seal:* "The task force has already been funded. You will not know which of them it
was until period 19."

**2. "The Flag and the Hammer."**
> *The county's "American Workers' Committee" has invited your local to a unity rally.
> They have a banner, a bullhorn, and the sheriff's cousin as a speaker. Their leaflet
> says the plant closed because of the trade deal, which is true.*

- **Refuse** — they get the rally; the local paper writes that the left is divided.
- **Attend and take the mic** — you can win the room (200 people, 40 of them yours),
  but you will be photographed under the banner, and the photograph goes into the
  state's file and into *your* file, which is worse.
- **Expose** — 1 CL; they become martyrs; the sheriff's cousin gets a fundraiser.

*Seal:* "You may speak only if the banner comes down. They will not take it down
before you arrive."

The correct play is option 2 with the condition named — accept the workers, refuse the
flag. That is UF-from-below in one gesture, and the game should let the player *type
the condition* into the ceremony, then print it in the Wiki's record of the rally.

**3. "Freedom of Criticism."**
> *Eleven people from the League for a Revolutionary Party have applied to join your
> front. They have a newspaper, a resolution, and one demand: freedom of criticism
> inside the front. Your membership is 60 and growing.*

- **Admit** — +11, falling heat, the Corporate Feed calls you "broad-based." In four
  periods they have a faction and a separate dues system.
- **Refuse** — they denounce you; the liberal allies who vouched for them leave.
- **Admit and fight** — the 1903 move. Let them in, put the resolution on the floor,
  beat it, and accept the split on your terms. 2 CL and a Congress.

*Seal:* "Whichever you choose, the eleven will publish what you said in the meeting."

**4. "The Placards Arrive First."**
> *Your stewards have been organizing the rail yard for nine months. The strike
> authorization vote is Thursday. On Wednesday, three hundred pre-printed placards
> arrive from a national organization nobody in the yard has heard of, along with a
> press release naming the strike as theirs and a demand that your committee join
> fifty-one other fronts.*

- **Let them in** — 40 bodies, and they take the press. The company's law firm now has
  a name for the strike that is not yours.
- **Bar them** — they picket your picket, and the Corporate Feed gets a photograph of
  two left groups arguing at a gate.
- **Out-organize** — put your stewards on every gate before dawn, so that when the
  placards arrive there is nobody to hand them to. 2 CL, wins the vote, and their own
  paper reports the strike as a victory of the united front, which it will.

*Seal:* "The vote is Thursday. You have one night and eleven stewards."

Option 3 is the satisfying one, it is expensive, and it is the MLM answer: the mass
line beats the spectacle because the masses are already organized. A player who finds
it will remember it.

**5. "The Interview."**
> *He wants to do a segment on your campaign. Two hundred thousand people will see it.
> He has a lawyer, a booking agent, and a merchandise line. Your legal fund has
> $1,340.*

- **Accept** — SL spike, decays in three periods, and you are now a recurring
  character. From here, your `PUBLISH` yield starts pricing *his* audience.
- **Decline** — he calls you sectarian, and 200,000 people learn your name attached to
  an insult.
- **Accept on terms** — a line in his show's budget for your legal fund, a hall for the
  campaign, childcare at the event. He will refuse. The refusal *is* the segment, and
  it is the only version in which you gain anything, because 200,000 people hear a man
  with a merchandise line explain why he cannot pay for a hall.

*Seal:* "He will say yes to the interview and no to the hall. You do not know yet
which one he puts on air."

**6. "The Referral" (the dark one).**
> *You know where the streamer's researcher lives, and you know the field office has an
> open file on a group he mentioned on air. One call moves two threads off your rail
> yard for a quarter.*

- **Make the call** — 2 threads diverted for 3 periods; +1 tradecraft signature learned
  by the state, permanently; a 23-year-old's career ends; and the *Liberated Signal*
  prints it, because the record prints everything.
- **Don't** — the threads stay on you, and you lose one cadre in period 12 instead.

*Seal:* "There is no version of this in which nobody is arrested."

No morality meter. The receipt is the Wiki, the Signal, and a permanently higher
`legibility` for the instruments used. The Corporate Feed's approval if you do it —
and its unchanged hostility if you don't — is the actual asymmetry, and it is the
game's sharpest statement about respectability.

### 4.4 What the player must never see

| Buried | Shown instead |
|---|---|
| $\eta$, $\mu$, `reach` as numbers | who shows up on Tuesday; the paper's print bill; the hall's rent |
| $\sigma$ and the splash formula | the contracting ring on Topology, and the task-force line item |
| strain flags and transition weights | the split, three periods after the print bill crossed the dues line |
| "radicalism" or "purity" scores | the cell's placards, its paper count, its member count |
| the ratchet as a coefficient | the grant headline in the Corporate Feed, and the arrest in the Signal |

---

## 5. Falsifiers

- If any cell reaches its terminal state **without its budget identity failing**
  (overhead > dues·n; reach decay; appropriation no longer renewed), there is a hidden
  coefficient and ADR172's no-imposed-functional-forms rule has been violated.
- If **exposure can kill the streamer**, the streamer is being modelled as a deviant
  faction rather than as the mediation function, and the satire has collapsed into a
  grifter story.
- If the player's **optimal response to all five is the same move**, there is one cell,
  not five, and the taxonomy is decoration.
- If **splash lands on the player regardless of shared edges**, the dossier mechanism is
  decorative and February 1917's `candidates ⊆ L` lesson has been lost.
- If **harvesting a dead cell never imports its deviation**, the mirror is fake and the
  player is a spectator rather than a participant in the same physics.
- If the **five substitutes do not predict which resource drains**, the taxonomy is a
  list of jokes rather than a mechanism.
- If a playtest shows players **choosing the adventurist option because it is fun** and
  never paying the ratchet, the splash is too cheap and the whole briefing is wrong.

---

## 6. Open questions for the porch

1. **Content enum or engine enum?** Recommend `OpportunistCellKind` as a BSL `defenum`
   in the shape of the existing `OrgKind`, with the engine matching strings and
   transition-table rows — so a mod or a fixture can add a sixth cell. Confirm this is
   the intended extension point.
2. **Where does the media market live?** A `MEDIA_MARKET` node on Topology (capturable,
   holds edges, can be flipped) versus a column on the Physical Map (DMA boundaries).
   Recommend Topology, because the market must be *contested*, and because the
   streamer's `FUNDS` edge to a platform needs an endpoint.
3. **Is $T^{\text{consume}}$ inside the 168-hour identity or a separate field?** Inside,
   or the joke does not land: the point is that the streaming hour and the meeting hour
   are the *same hour*.
4. **Does the player ever get to run one of these cells?** Recommend no. They are what
   the player refuses to become. Letting the player run a streamer would convert the
   satire into a management game about a media business, which is a different and much
   worse product.
5. **How does the "tradecraft signature" cost work without becoming a morality meter?**
   The current sketch (permanent `legibility` increase for instruments used in a
   referral) is material and legible, but it needs a second pass against
   `research/19`'s NSA/CIA referral mechanics before it is specified.
6. **Is the Trotskyist circuit one cell or a franchise meta-cell?** Recommend franchise
   — a national body plus local fronts — because `FRONT_GROUP_PROLIFERATION` *is* the
   failure signature, and a single node cannot proliferate.
7. **Do the cells compete with each other in the same market, or is the market split by
   class?** Currently one pool per market, which makes the zoo cannibalistic (good, and
   historically true). A class-stratified pool would be more precise but would double
   the state space and might destroy the "same workers, same students" premise the
   Director asked for.

---

## 7. Sources read

**MIM / MLM-TW corpus** (`/media/user/data/mim/textonly/`, read today):
`MIM.essays/weatherman.crit` (Weatherman, focoism, "flash of fury", individual
commitment vs. mass base); `MIM.essays/on.trotskyism` (Mavrakis on Trotsky: dogmatism,
sloganeering, no revolution anywhere); `MIM.essays/american.leninism` (O'Brien's
"sizeism" and the measuring-rod problem); `MIM.essays/critique.of.rcp` ("left"
economism, the oscillation, commandism, the personality cult as a symptom of division
of labour); `MIM.essays/personality.cults` (Mao on artificial prestige);
`MIM.essays/spartacist.league`; `MIM.essays/reply.to.trotskyist`;
`MIM.essays/mim.attitude` = `faq/mimvleft.html` (mush coalitions vs. splits);
`faq/mimcowards.html` ("build public opinion and the independent institutions of the
oppressed to seize power"); `faq/howtotellliberal.html` ("rise above classes, genders
and nations"; "vacillation or a fake neutrality"); `us.html` (the four dividing lines;
"Build a Democratic Workers' Party" as the wrong answer);
`classics/laboraristocracyenemy.txt` (Lenin at the Comintern Second Congress, 30 July
1920; MC5's gloss that the labour aristocracy is the new petty bourgeoisie and that
even a correct-line party must periodically purge petty-bourgeois elements).

**Marxists Internet Archive mirror** (`/media/user/data/old-hdd/old-hdd/www.marxists.org/`,
read today): Lenin, *What Is To Be Done?* ch. II (trade-union consciousness; tail-ism;
"bowing to spontaneity") and Conclusion; Lenin, *"Left-Wing" Communism* ch. IV (the two
enemies; the SRs' three errors; "anarchism as a penalty for the opportunist sins") and
ch. V (the leaders/masses muddle; "Get out of the trade unions!"); Stalin, *Foundations
of Leninism* ch. I (the three contradictions), ch. II (method; judge by deeds;
self-criticism; the Kautsky polemic), ch. IX (style in work; "communist vainglory");
Mao, *Quotations* ch. 28 for the *Combat Liberalism* passage; Debord, "On Chance"
(1957) and "Never Work" (1963).

**Books** (`/home/user/Downloads/babylon_books/`): Debord, *A Game of War*
(`ux/`) — already briefed in `research/09`, used here only for the arsenal/line-of-
communication point. *The Society of the Spectacle* theses 1 and 4 are quoted from the
standard Smith translation and are **not** on this host.

**Repo**: `docs/gameplay/2026-10-25-porch-01.md` (decision ceremony; visibility rule;
three feeds); `docs/gameplay/2026-10-25-porch-02.md` (contradiction physics; Topology
blind spots; the three resources; the SPD clock; the 168-hour identity);
`docs/gameplay/research/04` (splits, wreckers who must succeed);
`research/06` (labour aristocracy, division tactics, node flips);
`research/12` (the two-key Party threshold); `research/16` (why focoism fails);
`research/17` (the Caesarist cell, `allocate`, dossier blindness, the appropriation
settlement); `research/19` (NSA digital/analog asymmetry, CIA referral mechanics);
`research/20` (the four reactionary cells, and the cell-schema this briefing extends);
`project/research/history-sweep/brief-dt-patsoc.md` (the five-node PatSoc pipeline, the
coal-syndicate patronage figure, reversibility before the fraternization node);
`ai/epochs/epoch3/{doctrine-tree,cohesion-mechanic,gramscian-wire-vision}.yaml`;
`rust/crates/babylon-graph/src/{capacity,dossier,exposure,induced,backfire}.rs`.

**Not verified from disk, and flagged as such**: *The Society of the Spectacle*;
*WITBD* ch. I ("Freedom of Criticism"); *LWC* ch. I–III, VI–X; Lenin, "Imperialism and
the Split in Socialism" (1916); the full texts of Mao's *Combat Liberalism*, *On
Correcting Mistaken Ideas in the Party*, and *Oppose Book Worship*; Stalin's
*Foundations* ch. III–VIII; the Short Course (cited via `research/04`); and every
contemporary instance named in the assignment — Palestine Action, Red Guards Austin,
the Maoist Communist Union, and the named streamers — which are illustrations of the
type, not evidence.

---

## 8. Director's Canonical Addendum: *Michael Scott Communism*, *KKKommunities of KKKare*, and *The Queer Qlux Qlan*

**Primary source:** Persephone, *"Michael Scott Communism: the error of substituting the masses for individual charisma (the office to trotskyist pipeline in action)"*, *The Topology of Dialectics*, Oct 8, 2026 (`/home/user/Documents/substack/The Topology of Dialectics - Michael Scott Communism.pdf`), read verbatim in full.

By explicit Director decree, the terminology, jokes, and three-part substitution law from *Michael Scott Communism*—together with **`KKKommunities of KKKare`** and **`The Queer Qlux Qlan` (`QQQ`)**—are **canonical in-game terminology** across the **Line / Doctrine (Screen 6)** trap registry, the **Wiki Vigilance Case Files**, the **Opportunist Zoo**, and the **Decision Ceremony / `Liberated Signal`** narrator lexicon:

### 8.1 *"I DECLARE BANKRUPTCY!" $\rightarrow$ "I DECLARE REVOLUTION!"* (`MichaelScottCommunism`)
- **The Law:** Michael Scott walks into the Dunder Mifflin bullpen and shouts *"I DECLARE BANKRUPTCY!"* believing a legal and material fact can be accomplished through a speech act. The Michael Scott Communist tries to accomplish a revolution by declaring it loudly, assertively, and unwaveringly ("the office-to-trotskyist pipeline in action").
- **The Three Substitutions of Michael Scott Communism (Vigilance Case File):**
  1. **Declaration Substitutes for Practice (*The News Herald Tribune Gazette Trailer-Park Drop*):**
     - Throwing 100 communist newspapers onto trailer-park doorsteps in Kansas with zero pre-existing relationship edges prints a proud Seal receipt (`100 newspapers distributed!`) and yields **`+0` Contacts, `+0` Mass Receptivity, and `+0` Cadre Labor** at Period Close: *"The paper circulated; the politics did not. You spammed people with junk mail that has Marxist terminology so the people delivering it could feel revolutionary. You're declaring bankruptcy in the conference room and wondering why your creditors are still calling."*
  2. **Personality Substitutes for Organization (*Charismatic Guruism — "Tony Soprano with a Longer Reading List"*):**
     - Mechanically coupled to the Borgatti–Everett singleton index (`|signature_class(leader)| == 1`). Whether modeled on Bob Avakian (RevComs), Black Hammer, or a local hyper-competent founder who insists on doing everything themselves, a Guru-centered chapter is **"a single point of failure with a revolutionary aesthetic... You don't have much of an organization. You have a personality with a mailing list."** When the Guru burns out, gets arrested, or finds a new hobby, the node's effective capacity drops to `0.00`.
  3. **Spectatorship Substitutes for Participation (*"Fuck a Social Media. It's Narcissism Fuel" + NSPM-7*):**
     - A thousand followers on `Digital` edges and zero people willing to run a meeting, wash a dish, or carry out a collective decision—while police and the NSA (`L_NSA = 0.95`) monitor every online performance of militancy under **NSPM-7** and hand out 30-year sentences for distributing radical literature.

### 8.2 `KKKommunities of KKKare`, `"Just Rally the Folx"`, and `The Queer Qlux Qlan` (`QQQ`)
- **`KKKommunities of KKKare` & `"Just Rally the Folx" Akkktivist Subkkkulture`:**
  - In high-$\Phi$ college and military-garrison counties (where half the local population consists of soldiers, military spouses, post workers, or veterans tied to an Army base, and *"no amount of passionate preaching can defeat the power of a paycheck on the scale of masses"*), anything to the left of the Democratic governor gets shoehorned into *"anodyne, milquetoast, bitch-made elections and KKKommunities of KKKare anarchism."*
  - Tokenizing dynamics on Topology: radlib/anarchist coalition nodes parade oppressed and trans comrades around *"like a Pokémon card to demonstrate how woke and diverse they are"*—right up until those comrades refuse to go with the flow and assert a disciplined anti-imperialist line, triggering the instant liberal snap-back: *"Oh, we do the dishes around here, feminism, kkkommunities of kkkare."*
- **`The Queer Qlux Qlan` (`QQQ` — Settler-Colonial Pinkwashing & Comprador Identity Cell):**
  - Canonical MIM(P) / Third-Worldist designation for white settler / labor-aristocrat LGBT and NGO nodes that identify with **whiteness and the imperial bribe ($\Phi$)** rather than solidarity with colonized nations.
  - Mechanically, `QueerQluxQlan` nodes operate as a specialized cultural-capture front (`CONGRESS_FOR_CULTURAL_FREEDOM` / Democratic Party NGO appendage): they weaponize identity terminology to police revolutionary organizations as "authoritarian/red-brown," defend gentrification and municipal police budgets, absorb CIA/foundation diversity grants, and rally behind U.S./Israeli military interventions under the banner of "progressive values."

### 8.3 The Antidote vs. Its Twin Trap (*"The Magical Power of Pancakes"*)
- Building a reproducible material program (e.g., an economically viable hot vegetarian kitchen or clinic that fulfills the **Goods Clause**) is the material antidote to Michael Scott Communism—**but only if it builds organizers rather than beneficiaries**:
  - **The Nonprofit Executive Director Trap:** If the leadership decides everything and the masses merely show up to receive a plate of food, *"Congratulations: you have replaced the Guru with a nonprofit executive director. Handing out breakfast does not cause people to become communists through the magical power of pancakes."* (Lowers household exhaustion $E_t$, converts **`0` beneficiaries into `Cadre Labor`**).
  - **The Black Panther / Mass-Line Resolution:** When the people eating the meals also organize shifts, contest decisions, and learn to reproduce the institution without the founder in the room, the program converts recipients into role-equivalent `Cadre Labor` (`|signature_class(v)| >= 2`), curing Guruism and building a real Life Raft.
