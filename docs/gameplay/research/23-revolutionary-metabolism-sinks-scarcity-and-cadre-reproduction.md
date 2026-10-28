# 23 — The Revolutionary Metabolism: Sinks, Scarcity, and the Reproduction of Cadre

Read-only design and theory briefing, 2026-10-25. **Gap 4** of the porch series.

The question: *if sources exceed sinks, by Period 100 the player has infinite
resources and the game becomes spreadsheet clicking. So how are Cadre Labor (CL),
Money, and Supporter Labor (SL) consumed, strained and reproduced — so that
scarcity is a visceral political drama every single period, and never an upkeep
slider?*

The framing in `ai/epochs/epoch3/resource-sinks.yaml` is the thing to kill. It
opens with "without sinks, economies inflate. By tick 100, player has infinite
resources" and then answers with `burnout: rate 0.02`, `defection: base_rate
0.01`, `enthusiasm_decay: rate 0.03`, `life_pressures: rate 0.02`,
`attention_decay: rate 0.05`, `knowledge_atrophy: rate 0.02`. Six decay rates,
one of them annotated "People have jobs, families, survival needs." That
annotation is the whole mechanic, and the file has thrown it away and kept a
number.

This briefing's claim is that **the sink already exists, as a checked invariant
in `babylon-material-circuit`, and nobody has noticed.** `HouseholdTimeReceipt`
already partitions a household's 672 available hours per period into
`attended + protected + unpaid_allocated + contribution_available`, already
enforces that the household's own reproduction is satisfied *before* the
movement gets a single hour, and already carries
`unpaid_unresolved_hours` — the movement's shortfall — as a first-class
receipt field. Scarcity is not something to add. It is something to *locate*.

So the design job is not "invent sinks." It is:

> **Put the four real claims on the same sealed capacity, so that the player's
> political choices determine which claim loses.**

The four claims, in the imperial core, are the household's reproduction, the
household's wage, the movement's cadre-hours, and the state's coercion. Money is
a *derivative* of the first two — Mao, 1942: "it is the economy that determines
finance." That sentence is a design constraint, not a slogan. A game where money
is a resource you farm has already contradicted it.

Everything below is game design. No Rust, no Python, no commits.

---

## 0. The one-page answer

**1. The first sink is the household's, and it is lexicographic.** The engine
already refuses to allocate a movement hour while a single protected household
hour is unresolved (`protected_unresolved_hours != 0 ⇒ unpaid_allocated = 0 ∧
contribution_available = 0`). That is a **cliff, not a slope.** A cadre whose
child is sick does not contribute 2% less; her household contributes *nothing*
that period, and the movement's capacity drops by a whole person. This is the
single most important fact in the file, and it is already true.

**2. The middle is eaten by a wage comparison, not a defection roll.** Lenin,
1919: the top strata are "bribed by 'soft jobs' and other bourgeois sops." The
cadre and the labor aristocrat are on **one gradient**, one rung apart. A
$90,000 union staff job is the same mechanism as the super-wage, and the
movement's stipend is a rung on the same ladder. Whether a cadre leaves is four
booleans on measured quantities — is the stipend below the rung she can reach,
is her household claim unresolved, is there a door, and did the stipend row
pro-rata short — with no rate anywhere.

**3. Concentration is a purchase paid in cash, and cash only.** Lenin's
professional must be "maintained by the Party" because he "must not be left to
work eleven hours a day in a factory." Mao's 1945 constraint makes it sharper:
a *concentrated* force "will be unable to engage in production to support
itself." So going heavy converts a self-provisioning mass into a cash-burning
apparatus — one variable, three effects, zero coefficients.

**4. How you get money determines who you become, because money sits on
somebody's book.** Stalin, 1906: trade unions "have their own separate funds,
their own leading bodies, call their own congresses and, officially, are not
bound by the decisions of political parties." A legal treasury is not a
subsidiary; it is a second treasury with a different franchise, and its payroll
grows to meet its take. `survival_interest` is not a rot meter. It is a
**headcount on a payroll.**

**5. A strike or a siege is a larder with a date on it, and the turn is a rent
period.** `TICK_DURATION_DAYS = 28`. Rent is due monthly. Therefore the eviction
clock and the turn clock are the *same clock*, arithmetically, with no design
choice made. And because `PricePolicy::Responsive` is already implemented, the
larder's own consumption raises the price at which it must be refilled. The
siege is endogenous.

**The positive loop, stated once.** Five sinks, one return. Spending stock on
*shared reproduction* (a kitchen, a clinic, childcare, a housing defence) lowers
each served household's `protected_hours`, which lowers `E`, which raises
`contribution_available`, which raises the movement's hours — three periods
later, as labour, not money. That is Mao's Changkang township, where solving
fuel, rice, salt and housing produced **80–88% recruitment and 4,500 yuan of
bonds from a population of 1,500**, while Tingchow, which solved nothing and
pushed only Red Army expansion, land tax and bonds, lost its council, its
recruitment, *and* its bond sales. The sink that returns capacity is the game.

---

## 1. Theoretical grounding: the dual metabolic crisis

### 1.1 Mao, 1934: the Tingchow failure is a sink failure, and it is total

*Be Concerned with the Well-Being of the Masses, Pay Attention to Methods of
Work* (27 January 1934) is the single most load-bearing text in this briefing,
because it contains a controlled comparison with numbers in it.

The negative case:

> "They talk only about expanding the Red Army, enlarging the transport corps,
> collecting the land tax and selling bonds; as for other matters, they neither
> discuss nor attend to them, and even ignore them altogether. … The problems
> facing the people of Tingchow city were that they had no firewood, no salt was
> on sale because the capitalists were hoarding it, some people had no houses to
> live in, and rice was both scarce and dear. … That is why when the new
> workers' and peasants' representative council was elected in the city, a
> hundred or more representatives were unwilling to attend after the first few
> council meetings had discussed only the expansion of the Red Army and
> mobilization for the transport corps, entirely ignoring the well-being of the
> masses, so that the council was unable to go on meeting. **The result was that
> very little was achieved in regard to the expansion of the Red Army and
> mobilization for the transport corps.**"

Read the last sentence twice. Tingchow did not trade reproduction for
extraction. It spent everything on extraction and **got less extraction**. The
sink was not a tax on the player's resources; it was the *precondition of the
resource existing at all.*

The positive case:

> "In Changkang when fire broke out in a poor peasant's house destroying one and
> a half rooms, the township government appealed to the masses to contribute
> money to help him. In another instance, three persons were starving, so the
> township government and the mutual-aid society immediately gave them rice.
> During the food shortage last summer, the township government obtained rice
> from Kunglueh County, more than two hundred li away, for the relief of the
> masses."

and the return on it, in Mao's own arithmetic:

> "In Changkang 80 per cent of the young men and women have joined the Red Army,
> and in Tsaihsi the figure is 88 per cent. There has been a big sale of bonds,
> too, and 4,500 yuan worth have been sold in Changkang which has a population
> of 1,500."

Three design consequences, none of them a rate:

- **The sink categories are a household's actual week, itemised.** Mao's list is
  "fuel, rice, cooking oil and salt, sickness and hygiene, and marriage," plus
  "the women want to learn ploughing and harrowing," "the children want to go to
  school," "the wooden bridge over there is too narrow," "many people suffer
  from boils." These are the four Goods Clause categories of `research/20`
  (food, housing, clinic, justice) *plus* fuel, schooling, and a bridge. Babylon
  should adopt Mao's list rather than MIM's abstraction, because Mao's list is
  observable on a Ticker and MIM's is a slogan.
- **The mechanism of conversion is *demonstrated competence*, not persuasion.**
  Mao does not say the masses were argued into the Red Army. He says they were
  shown that the government "represent[s] their interests" and that "our lives
  are intimately bound up with theirs," and then they joined. `research/20` §1.5
  already established this as the FBI's own reading of the Panther breakfasts.
  The 80% figure is the *calibration* for how strongly demonstrated competence
  converts.
- **The bond figure is a ratio.** 4,500 yuan from 1,500 people is three yuan per
  person, from a poor peasant township, in a blockaded base area. Compare Mao
  1942: five million yuan of bonds from a border region of 1,500,000 people —
  3.33 yuan per person. Two independent documents, eleven years apart, two
  different scales, and the per-capita voluntary extraction figure is the same
  order. That is a usable *Calibrated* parameter and it is not invented.

And the sentence that names the whole design:

> "We are the leaders and organizers of the revolutionary war as well as the
> leaders and organizers of the life of the masses. **To organize the
> revolutionary war and to improve the life of the masses are our two major
> tasks.**"

Not one task with a maintenance cost. **Two tasks**, competing for one stock of
hours.

### 1.2 Mao, 1942: the economy determines finance, and extraction must repay

*Economic and Financial Problems in the Anti-Japanese War* (December 1942) is the
sink document, and its first principle forbids the whole "money as a resource"
framing:

> "They do not know that while a good or a bad financial policy affects the
> economy, **it is the economy that determines finance.** Without a well-based
> economy it is impossible to solve financial difficulties, and without a growing
> economy it is impossible to attain financial sufficiency."

Three operative rules follow.

**Rule 1 — the ceiling on extraction is repayment.** This is the design's central
constraint on every money sink, and it is stated as a political economy, not a
balance target:

> "But while taking from the people we must at the same time help them to
> replenish and expand their economy. That is to say, appropriate steps and
> methods must be adopted to help the people develop their agriculture, animal
> husbandry, handicrafts, salt industry and commerce, **so that they gain at the
> same time as they give and, moreover, gain more than they give; only thus can
> we sustain a long war against Japan.**"

and its violation has a name:

> "Another mistake is 'draining the pond to catch the fish', that is, making
> endless demands on the people, disregarding their hardship and considering only
> the needs of the government and the army. That is a Kuomintang mode of thinking
> which we must never adopt."

**Rule 2 — the burden is a curve with a repayment leg, not a level.** Mao gives
three dated stages, with the numbers to prove he means it (public grain from the
Shensi-Kansu-Ningsia Border Region, population 1,500,000):

| Stage | Period | Grain taken | What it was for |
|---|---|---|---|
| 1 | 1937–1939 | "very little" | "they were able to build up considerable strength" |
| 2 | 1940–1942 | 90,000 / 200,000 / 160,000 *tan* | blockade, famine goods, "dire straits" |
| 3 | 1943–1944 | falling again | "if the public sector of our economy continues to grow … the people's burden will again be lightened" |

So the sink schedule is *deliberately non-stationary*: you take heavily in the
crisis and you **pay it back by building the public economy**, and the payback is
the mechanism by which you can take again. That is the shape of the siege
mechanic in §3.5, taken directly from the text.

**Rule 3 — cadre overhead is non-productive expenditure, and it is the easiest
thing to cut and the hardest to cut well.** Mao's "better troops and simpler
administration" has five named objectives — "simplification, unification,
efficiency, economy and opposition to bureaucracy" — and the argument is
explicitly fiscal:

> "Simplification will reduce non-productive expenditures and increase our
> income from production; it will not only have a direct and healthy effect on
> our finances, but will lighten the people's burdens and benefit them
> economically."

with the failure list named as a list of *sinks*: "corruption and graft,
over-elaborate organization, meaningless 'standardization' and red tape." Every
one of those is a place where the organization's money goes and no good comes
out. Babylon's cadre upkeep should be those four things, itemised, not a
per-cadre constant.

### 1.3 Mao, 1943: the nine-to-one rule

*Spread the Campaigns to Reduce Rent, Increase Production and "Support the
Government and Cherish the People"* (1 October 1943) contains the only ratio in
the corpus that a designer can lift without inventing anything:

> "In the financial and economic field, the Party and government personnel at the
> county and district levels should **devote nine-tenths of their energy to
> helping the peasants increase production, and only one-tenth to collecting
> taxes from them. If pains are taken with the first task, the second will be
> easy.**"

Nine to one. From a Party directive. With a causal claim attached ("the second
will be easy"). This is the **cadre-hours allocation law**, and it is the
cleanest possible replacement for `resource-sinks.yaml`'s flat maintenance
costs: the sink is not "cadre cost 0.05 per tick," it is **a contest between two
uses of the same hours, in which the text tells you the correct ratio is 9:1 and
tells you why.**

*Some Questions Concerning Methods of Leadership* (1 June 1943) supplies the
complementary rule, about where the cadre's hours should *physically* be:

> "if persons in leading positions confine themselves to a general call — if they
> do not personally, in some of the organizations, go deeply and concretely into
> the work called for, **make a break-through at some single point**, gain
> experience and use this experience for guiding other units — then they will
> have no way of testing the correctness or of enriching the content of their
> general call."

That is a rule against the pure-staff organization: a leadership whose hours are
all spent on coordination has no point of production and therefore no
information. It is a sink *failure mode* that the player must be able to fall
into: the party that is all apparatus and no bench.

### 1.4 Mao, 1945: self-provisioning is bounded by concentration

*On Production by the Army for Its Own Support* (27 April 1945) gives the
constraint that makes the underground/legal choice a real trade rather than a
stance:

> "In the near future we shall have to take the necessary number of military
> formations from the areas where they are now engaged in dispersed operations,
> and concentrate them for attack on particular enemy objectives. **Such big
> formations for concentrated action will be unable to engage in production to
> support themselves**, and, what is more, will need large supplies from the
> rear; only the local troops and regional formations remaining behind (and they
> will still be considerable) will be able both to fight and to engage in
> production as before."

This is the load-bearing sentence for Mechanic 3. **Self-provisioning capacity is
a decreasing function of concentration.** Not a modifier: a *category* fact. A
concentrated formation cannot farm. So:

- dispersed cadre can be paid partly in kind (they keep their wage job, they
  contribute hours, the party feeds them at the margin);
- concentrated cadre can only be paid in cash (they have no wage, no plot, no
  time);
- therefore **the underground apparatus is a pure money sink, and the mass work
  is not.** The two are not two settings of one dial; they have different
  payment currencies.

And the political return on the dispersed form is stated as a *police* fact, not
a moral one:

> "Once an armed force begins to 'keep house' for itself, **encroachments upon
> the property of the people seldom or never occur.** As the army and the people
> exchange labour and help each other in production, the friendship between them
> is strengthened."

Self-provisioning is therefore the mechanism that *stops requisition*, which is
the mechanism that *stops the base from hating you*. And Mao's caution is the
counterweight: "Formally speaking, we are violating the principle of division of
labour," and it is only correct because of "the poverty and disunity of the
country … and the protracted and dispersed people's guerrilla war."

*Production is Also Possible in the Guerrilla Zone* (31 January 1945) supplies
the *quantities*, which are integers and therefore usable:

> "each person has 0.5 *liang* of cooking oil and salt and 1 *chin* of
> vegetables per day, and 1.5 *chin* of meat per month. Furthermore,
> tooth-brushes, tooth-powder and reading primers, which for years were
> unavailable, are now all provided."

and the surplus case, which is the conversion mechanic's calibration:

> "The fourth district contingent has set up a felt-cap workshop, an oil press
> and a flour mill, and in seven months has netted a profit of 500,000 yuan in
> local currency. Not only has it settled its own difficulties but it is
> satisfying the needs of the people in its guerrilla zone. The soldiers can now
> provide all their own woollen sweaters and socks."

A unit under blockade, moving several times a day, ran three processing
enterprises at a profit *and* provisioned itself. That is the design target for
the "conversion" leg of the siege.

### 1.5 Lenin, 1919: the cadre and the labor aristocrat are on one gradient

This is the passage that unifies the "exhaustion at the bottom" and "bribery at
the middle" halves of the assignment into a single mechanism, and it is four
lines long. *How the Bourgeoisie Utilises Renegades* (1919):

> "The breakaway of the top strata of the working class, **corrupted by a
> middle-class way of life and opportunism and bribed by 'soft jobs' and other
> bourgeois sops**, began to take shape on a world scale in the autumn of 1914
> … In all the advanced countries we see corruption, bribery, desertion to the
> bourgeoisie by the leaders of the working class and its top strata in
> consequence of the doles handed out by the bourgeoisie, who provide these
> leaders with **'soft jobs,'** give crumbs from their profits to these upper
> strata, shift the burden of the worst paid and hardest work to backward workers
> brought into the country, and enhance the privileges of the 'labour
> aristocracy' as compared with the majority of the working class."

"Soft jobs." Not ideology, not false consciousness, not a loyalty bar. A job.

The design consequence is exact and it is the answer to "why the imperial core
eats cadres alive": **the cadre is one rung above the labor aristocrat on the
same ladder.** The labor aristocracy is bought with the union wage; the cadre is
bought with the union *staff* wage; the NGO programme officer and the
public-sector professional are the rungs in between. So the movement is not
competing against apathy. It is competing against a wage ladder that its own
members can climb, and the ladder's lowest rung is the party stipend.

The MIM(P) archive's own annotation on this passage pushes it further, and the
game should not soften it:

> "As time goes on through the 20th century, these workers receive more and more
> super-profits to become a petty-bourgeoisie and it becomes a concession to the
> enemy to speak of them as having merely false consciousness."

Applied to cadres: **what looks like a cadre's "commitment" is partly her
position on the ladder.** Mechanic 2 makes that testable rather than asserted,
and the result is uncomfortable in exactly the right way — see §3.2's selection
effect.

### 1.6 Lenin, 1902: the professional is a line item, and the fund is a target list

*What Is To Be Done?* ch. IV §C draws the distinction the whole apparatus rests
on:

> "the organisation of the revolutionaries must consist first and foremost of
> people who make revolutionary activity their profession … Such an organisation
> **must perforce not be very extensive and must be as secret as possible.**"

and then, in the passage that turns a slogan into a budget:

> "A worker-agitator who is at all gifted and 'promising' **must not be left to
> work eleven hours a day in a factory. We must arrange that he be maintained by
> the Party**; that he may go underground in good time; that he change the place
> of his activity, if he is to enlarge his experience, widen his outlook, and be
> able to hold out for at least a few years in the struggle against the
> gendarmes."

Three things follow, and the third is the dilemma.

**(a) The stipend is the wage the cadre forgoes.** "Maintained by the Party" is
not a bonus. It is the replacement of a household's income, which means it must
be measured against the wage the cadre could actually earn — which is Mechanic
2's `w^P`.

**(b) Few professionals, and the reason is secrecy, not thrift.** "to concentrate
all secret functions in the hands of **as small a number of professional
revolutionaries as possible**." The bound on `c` is not money first; it is that
each additional full-timer is another person who must know the centre.

**(c) The fund is simultaneously the movement's memory and the state's evidence.**
Lenin analyses the Economists' mutual-benefit-fund rules with visible relish:

> "To organise a fund … to which subscriptions of **two kopeks per ruble** should
> be made … and then to present to subscribers a monthly financial account … to
> expel members who fail to pay their contributions … Why, **this is a very
> paradise for the police**; for nothing would be easier for them than to
> penetrate into such a secrecy of a 'central factory fund', confiscate the
> money, and arrest the best people."

and his alternative is not "be more transparent":

> "Would it not be simpler to issue one-kopek or two-kopek coupons bearing the
> official stamp of a well-known (very narrow and very secret) organisation, **or
> to make collections without coupons of any kind and to print reports in a
> certain agreed code in an illegal paper?** The object would thereby be attained,
> but it would be a hundred times more difficult for the gendarmes to pick up
> clues."

That is the whole tension of Mechanic 4, stated as a technical choice about
bookkeeping, in 1902:

| Dues form | Audit | Police |
|---|---|---|
| Named roll, monthly accounts, expulsion for arrears | **full** — you know who paid and who is owed | **full** — a list with addresses |
| Coupons with a stamp | partial — you know totals | partial — possession is evidence |
| No coupons, coded reports | **none** — you cannot audit your own treasurer | almost none |

The movement can have accountability or it can have security, and Lenin
explicitly chooses the second while admitting what it costs. **A game that gives
the player both is lying.** And note the corollary Lenin draws — the loose
organisation "is so loose that it is not even definitely formed, and which has
not even an enrolled and registered membership, cannot be called an organisation
at all. Perhaps so. Not the name is important."

### 1.7 Lenin, 1915: legalism is a payroll, not a rot meter

*The Collapse of the Second International* ch. VIII is where `survival_interest`
comes from, and reading it in full changes what the mechanic should be. The
famous line is the diagnosis:

> "the old party — from Legien to Kautsky inclusively — **sacrificed the
> revolutionary aims of the proletariat for the sake of preserving the present
> legal organisations.** … The proletariat's right to revolution was sold for a
> mess of pottage — organisations permitted by the present police law."

But the *mechanism* is in the surrounding paragraphs, and it is not moral decay.
It is a list of things that would be lost:

> "the great and strong parties were frightened by the prospect of **their
> organisations being dissolved, their funds sequestered and their leaders
> arrested** by the government."

and the phenomenology of the official is worth quoting because it is the exact
tone the game's narrator should hit:

> "People are so degraded and stultified by bourgeois legality that they cannot
> even conceive of the need for organisations of another kind … **the mere habit
> that stupid but conscientious philistines have of confining themselves to
> bookkeeping, have created a situation in which, during a crisis, these
> conscientious philistines have proved to be traitors and betrayers.**"

"Confining themselves to bookkeeping." The Kautskyite is not a coward. He is a
**bookkeeper**, and the books are real, and the payroll is real, and the meeting
hall's lease is real.

And Lenin's answer is not austerity. It is duplication, at full price:

> "pure legalism … is now obsolete … **It must be augmented by the creation of an
> illegal basis, an illegal organisation, illegal Social-Democratic work,
> without, however, surrendering a single legal position.** Experience will show
> how this is to be done, if only the desire to take this road exists."

**"Without surrendering a single legal position."** So the correct play is to run
*both* apparatuses, simultaneously, at double cost — and the cost is precisely
what `survival_interest` measures the absence of. A party that has only the legal
apparatus is cheap and captured. A party that has only the illegal apparatus is
expensive and blind. The tax on having both is the game's mid-game difficulty
curve, and it is a bill, not a penalty.

### 1.8 Stalin, 1906: the legal body is a second treasury with a different franchise

*The Class Struggle* (14 November 1906, in *Akhali Droyeba*, the legal
trade-union weekly in Tiflis that Stalin edited and that the Governor of Tiflis
suppressed on 8 January 1907 — roughly eight weeks, two periods) states the
constitutional fact that Mechanic 4 rests on:

> "Most of the workers' unions are, of course, non-party and neutral; but this
> merely means that they are independent of the party only in **financial and
> organisational matters, i.e., they have their own separate funds, their own
> leading bodies, call their own congresses and, officially, are not bound by
> the decisions of political parties.** As regards the ideological dependence of
> the trade unions upon any given political party, such dependence must
> undoubtedly exist and cannot help existing, because … members of different
> parties belong to the unions and inevitably carry their political convictions
> into them."

Read that as a type declaration. A union local is an organization with:

- `budget` — its own, not yours;
- `leading_body` — its own, not your committee;
- `congress` — its own, not your congress;
- `members` — shared with you, and shared with the Democrats, and shared with
  the police.

So a legal institution is not a subsidiary that pays you a dividend. It is a
**coalition partner that happens to hold cash**, and the cash is spent by its own
franchise. That is what `survival_interest` is, and it explains why it cannot be
modelled as "reformist drift": the drift is not in anyone's head. It is in the
minutes of a body you do not control.

And the fragility has a date, not a probability: the paper that carried this
article was suppressed by a governor in eight weeks. A legal apparatus is a
*periodic* income stream with an exogenous termination, and its termination is
the state's decision, made on the state's schedule.

### 1.9 Fortunati: a stipend that covers the cadre and not the cadre's household is a claim on someone else

`research/07` §5 already establishes the mechanism: "When capital buys the male
worker's labor-power with the wage, the latter is not only giving credit on the
use-value of his labor-power, he is also giving credit on the use-value of hers.
**Capital settles two credit debts when it pays the wage.**"

Apply it to the party and the result is the sharpest single consequence in this
briefing. A stipend set at `s_i` replaces **one** worker's wage. It does not
replace:

- the second adult's unpaid labour that made the first adult's wage convertible
  into a reproducible household;
- the childcare that the first adult's wage bought, or the kin network that
  provided it free;
- the eldercare, the cooking, the laundry, the school run.

So a party that stipends a cadre at the cadre's own forgone wage has **not
reproduced the cadre.** It has purchased the cadre's hours and issued a bill to
her household, payable in someone else's unpaid time. That bill is the reason:

- full-time cadres are disproportionately people with no dependents, or with a
  partner who is also paid, or with a partner who is not;
- the party's gender composition is a *material output* of its stipend policy,
  not a hiring preference;
- a party that stipends men at a "family wage" is buying the household's
  reproduction at the price of one wage and getting a dependent housewife for
  free — which is exactly the arrangement `research/07` §5 says Mies finds
  reproduced inside socialist accumulation ("collectivise the mill, leave the
  household, get a second shift and a female cadre base that quietly stops
  coming").

`research/07` §2.1 already names the rendering: "The failure the player must be
able to cause: **socializing production without socializing reproduction.**"
Mechanic 1 is the arithmetic of that failure.

### 1.10 Weinstein: every sink is also a selector

`research/08` §2.1 establishes revenue → recruitment → composition. The corollary
for sinks is the one this briefing adds, and it is a design rule:

> **What you spend on selects who stays.**

A party that pays stipends selects for people who can live on a stipend. A party
that pays in kind selects for people who need food. A party that pays in
*reproduction* — childcare, a kitchen, a clinic — selects for **parents**, which
in the imperial core means it selects for women, and which is the only
recruitment channel that reaches the stratum with the largest unresolved
household claim and therefore the largest `E`.

That is not a diversity mechanic. It is the same arithmetic as everything else in
this file, and it produces the politically correct answer for a material reason,
which is the only reason the game should ever produce it.

### 1.11 Synthesis: what each source kills

| Source | What it establishes | What it kills in the design |
|---|---|---|
| Mao 1934 | Tingchow: extraction without reproduction yields *less* extraction; Changkang 80–88% and 3 yuan/person | Any sink that is a percentage; any split between "economy" and "politics" |
| Mao 1942 | The economy determines finance; extraction must repay; three dated stages | Money as a farmable resource; a stationary burden |
| Mao 1942 | "Better troops and simpler administration": cadre overhead is *non-productive expenditure* | Per-cadre upkeep constants; cadre count as free |
| Mao 1943 | The 9:1 cadre-hours rule; the break-through-at-one-point rule | Maintenance costs; the all-staff headquarters |
| Mao 1945 | Concentrated formations cannot self-provision; self-provisioning stops requisition | Concentration as a free toggle; in-kind payment for the underground |
| Lenin 1919 | "Soft jobs": the cadre is one rung above the labor aristocrat | Defection as a loyalty roll or a morale bar |
| Lenin 1902 | The stipend replaces the wage; few professionals; the fund is a target list | Free volunteer labour; dues with both audit and security |
| Lenin 1915 | Legalism is a payroll and a lease; the answer is *duplication* | `survival_interest` as a rot float |
| Stalin 1906 | A legal body has its own funds, leading body and congress | The union local as a revenue subsidiary |
| Fortunati | The stipend covers one worker, not one household | The cadre as an individual unit; free reproductive labour |
| Weinstein | Revenue selects membership | Any sink that is politically neutral |

---

## 2. The metabolism, stated as books

### 2.1 Three books, one snapshot

Everything in §3 reads from books that already exist, and this is the reason the
mechanics can be integer and coefficient-free.

| Book | Type | What it holds | Where |
|---|---|---|---|
| **Material** | `MaterialCircuitState` | `period`, `inventory`, `capacities`, `labor`, `orders`, `freight`, `corridor_capacities`, `final_demand_orders` | `babylon-material-circuit` |
| **Monetary** | `MonetaryBook` | accounts, `MoneyPosting`, `MoneyTransferReceipt`, `WageAccrualReceipt`, `PurchaseEscrow`, `FundedShift`, `AidCashReserve` | `babylon-material-circuit::accounts` |
| **Household time** | `HouseholdTimeBook` | `policies`, `receipts`, `contributions` | `babylon-material-circuit::household_time` |

Plus the organizer surface, which is where a *person* is: `OrganizerParticipant`
carries `available_hours`, `commitments`, and — this is the part nobody has used
— **`concern`, `objection`, `review_condition`.**

`review_condition` is a promise the party made to a named person, in writing, as
a condition of their continued participation. That is not flavour text. It is the
**reproduction of commitment as a typed field**, and §3.1 uses it.

### 2.2 The identity, and where the sink already lives

`HouseholdTimeReceipt::validate` enforces, per household per period:

```
endowment_hours            = 28 × 24 = 672                    (TICK_DURATION_DAYS = 28)

attended_hours             (the employer's claim: staffing attendance)
+ protected_hours          (the household's own claim: the sick child, the roof)
+ unpaid_allocated_hours   (the movement's claim, granted)
+ contribution_available_hours  (surplus the household could still give)
= endowment_hours

unpaid_requested_hours     = unpaid_allocated_hours + unpaid_unresolved_hours
```

and then three *priority* invariants:

```
protected_unresolved_hours != 0  ⇒  unpaid_allocated = 0  ∧  contribution_available = 0
unpaid_unresolved_hours    != 0  ⇒  contribution_available = 0
```

**Read the first one again. It is a cliff.** The moment a household cannot meet
its own protected claim — one shift missed, one child ill, one eviction notice —
every downstream allocation is forced to zero, by invariant, and the engine will
refuse to write the receipt otherwise.

That is the sink. `unpaid_unresolved_hours` is not derived; it is a receipt field
with a `validate()` that refuses inconsistent states. **Babylon already has a
resource sink that is conservative, integer, per-household, and politically
correct, and `resource-sinks.yaml` does not mention it.**

### 2.3 The conservation statement

> Every hour the movement spends is either an hour a household did not spend on
> its own reproduction, or an hour that the movement's own reproductive
> institutions freed from a household's reproduction.

There is no third source. There is no "volunteer labour" that appears from
nowhere, no reputation that converts into hours, no cadre that works for free
because the player clicked a morale button. And the second clause is the whole
positive loop: **the movement can create hours, but only by taking over
reproduction, and only up to the difference between the collective's
labour-hours-per-service and the sum of the households' individual hours.**

Both terms in that difference are *measured*:

- the household's solo hours: ATUS, `research/14` §2.6 — housework 0.73 h/day,
  cooking 0.67, childcare 0.40, eldercare 0.05, emotional support 0.82;
  **2.67 h/day = 18.7 h/week**, and the gender split is 23.6 h/week for women
  against 13.4 for men, a ratio of 1.76;
- the collective's hours per service: a `MaterialCatalog` production recipe, in
  the same whole hours the rest of the circuit uses.

So the "multiplier" is a **ratio of two observations**, and where the collective
is not more efficient than the household, the kitchen frees nothing and the
mechanic says so.
---

## 3. Five mechanics

Each is given with the claim it models, the snapshot it reads, the integer form,
the evidence class of every term, what the player sees, and the conformance debt
it retires.

Evidence classes follow `ADR258`: **Observed** (measured in the county's own
books or in the named statistical series), **Derived** (a ratio or fold over
observed quantities on the same period-*t* snapshot), **Calibrated** (a historical
figure used as a scenario parameter and declared as such), **Designed** (authored
content).

The permitted operations throughout are `+ − × ÷`, comparison, `min`/`max`, and a
fold over a population. The only permitted constants are `0`, `1`, exact integers
denoting *designed objects* (the goods in Mao's list, the rungs on the wage
ladder) or *durations* (672 hours, 28 days, 13 periods and 364 days per year,
nine-to-one).

---

### Mechanic 1 — The Household Claim Partition

**The claim.** Cadre hours are residual. The movement does not compete against
the state for them; it competes against rent, the second shift, and the commute,
and it loses unless it takes over some of that work.

**Snapshot.** `HouseholdTimePolicy` (`eligible_persons`,
`hours_per_eligible_person`, `protected`, `routine_provisioning`,
`unmet_burdens`), `HouseholdTimeReceipt` (all eight hour fields),
`HouseholdContributionUse` (which organization drew which hours from which
household), ATUS baselines, and the county's rent-burden distribution
(`fact_census_rent_burden`) as the *cash* half of the same claim.

**The integer form.** No new formula is needed for the partition — the engine
computes it. Three things are added:

**(a) The commute belongs inside `routine_provisioning`, not in a formula.**
A commute is provisioning labour a household must perform in order to be
exploitable. Putting it in `routine_provisioning` means it is ranked *ahead* of
the movement's claim, which is correct, and it means `E` needs no separate
computation:

```
E_i  =  (attended_hours_i + protected_hours_i) / 672        [Derived]

        =  1 − (unpaid_allocated_i + contribution_available_i) / 672
```

`E` is then an *output* of the receipt, needs no coefficient, and is used only
for **selection** (which cadre is most exposed to Mechanic 2), never as a decay
rate. This is the single change that retires
`resource-sinks.yaml::sympathizer_labor.passive_decay.life_pressures.rate: 0.02`
and its note "People have jobs, families, survival needs."

**(b) Shared reproduction is a subtraction from `protected_hours`, measured in
the freed hours.** For household `i` served by institution `r` for service `k`:

```
protected_hours_i'  =  protected_hours_i − Σ_k  freed_hours(i, r, k)
freed_hours(i, r, k) = min( atus_daily_hours_k × 7 × 4 ,  receipted_service_hours(i, r, k) )
```

with `atus_daily_hours` from `research/14` §2.6 (Observed: cooking 0.67 → 18 h
per period; childcare 0.40 → 11 h per period; housework 0.73 → 20 h per period),
and `receipted_service_hours` from `HouseholdServiceReceipt` (Observed: did the
kitchen actually serve this household this period, and for how many hours of
service). The `min` matters: an institution that serves a household *worse* than
the household serves itself frees nothing and costs goods and cadre-hours. That
is the failure mode, and it is honest.

The arithmetic is worth stating plainly. A communal kitchen serving 30 households
frees `30 × 18 = 540` hours per period, which is **four-fifths of a full-time
cadre's 672 hours**, from one kitchen. This is why Mao's Changkang township, which
solved firewood, salt, rice and housing, got 80–88% recruitment: it had *created
the hours* in which people could attend.

**(c) The cadre-hours supply is a sum, not a stock.**

```
hours_available(org, t)  =  Σ_{i ∈ members} contribution_available_hours_i,t   [Observed]

hours_cannot_exceed       =  Σ_{i ∈ members} (672 − attended_i,t − protected_i,t)
```

The second line is the ceiling. There is no way to raise it except by lowering
`protected` (reproduction) or `attended` (the wage). Mechanic 1's whole game is
the choice between those two, and the movement cannot make `attended` fall
without a strike, which is Mechanic 5.

**What the player sees.** The Ticker's household page is a **week, laid out**:
wage hours in one block, the second shift in a second block, the commute as a
grey band, sleep as the remainder, and a small dark strip labelled by whoever is
asking for it — the party, the union, the church. No number. The player learns to
read `E` by recognising a week with no dark strip in it.

When a household's protected claim goes unresolved the strip **does not shrink —
it vanishes**, and the name attached to it appears on the *unable to attend* list
in the Liberated Signal with a reason: *"Rosa isn't coming; her mother fell."*
That is the cliff rendered as a sentence, and it is the single most important
rendering in this file.

**How it fails.** The player who builds cadre housing but not childcare has
built a barracks with no second shift. The player who builds childcare but not
housing watches the rent take the household out of the county. The player who
builds both but charges for them has converted a freed hour into a cash claim and
moved the household's protected claim from time to money — which is not nothing,
because a cash claim can be met by the strike fund (Mechanic 5) and a time claim
cannot.

**Conformance debt retired.**
`resource-sinks.yaml::sympathizer_labor.passive_decay.life_pressures`,
`enthusiasm_decay`, and `cadre_labor.passive_decay.burnout` all go.
`reproductive-labor.yaml::tier_1.reproductive_regeneration.regeneration_rate:
0.01` and `solidarity_regeneration_bonus: 0.005` go: a SOLIDARITY edge does not
regenerate wealth at 0.5%; it either frees hours (measurable) or it does nothing.

---

### Mechanic 2 — The Bribe Gradient

**The claim.** Defection is not a probability. It is a **wage comparison at the
household**, and the counter-offer is a real line on a real institution's books.

**Snapshot.**
- `w^P_{j,k}` — the annual pay of poaching rung `k` in county `j`.
  *Observed*: QCEW `avg_annual_pay` by NAICS (`fact_qcew_annual`) and the OEWS
  occupation wage for the specific rung. Three rungs, `k ∈ {1,2,3}`:
  `k=1` union/local staff, `k=2` NGO programme officer, `k=3` public-sector
  professional (teacher, nurse, social worker — the three occupations the party's
  own cadre pool most resembles). Converted to a period by `× 12 / 13`, because
  13 periods of 28 days is 364 days (*Designed*; the residue is absorbed at year
  end, and the conversion is declared rather than implied).
- `m_i,t` — the cadre's actual movement income this period, in `Currency` micros.
  *Observed*: the org's `WageAccrualReceipt` and stipend postings.
- `stipend_requested_i`, `stipend_allocated_i` — *Observed* from the sealed
  `PracticeResourceCapacity` row for stipends (see below).
- Household claim state: `protected_unresolved_hours_i` and
  `unmet_burdens` (*Observed*, `HouseholdTimeReceipt`).
- Edge existence to a poaching institution: `∃ e_{i→p}` (*Observed*, graph).
- Rung eligibility: whether the cadre holds the credential that rung requires
  (*Designed* content on the participant; `organization/cadre-level` is the
  existing proxy).

**The integer form.** Four booleans, no rates:

```
poach_i,t  =  1  iff

  (1)  m_i,t  <  w^P_{j,k(i),t}                              the offer beats the stipend
  (2)  ∧ ( protected_unresolved_hours_i,t > 0
          ∨ ∃ unmet_burden_i,t )                             the household claim is binding
  (3)  ∧ ∃ e_{i→p},  p ∈ poaching institutions               there is a door
  (4)  ∧ stipend_allocated_i,t < stipend_requested_i,t        the party could not match

defections_t  =  Σ_i  poach_i,t
```

Every conjunct is load-bearing and each one is a different design statement:

- **(1) is the gradient.** Not "morale is low." The offer is *higher* than the
  stipend, on the county's own pay tables, and the player can read it.
- **(2) is Fortunati.** A cadre with a resolved household and a small stipend
  does **not** leave. A cadre with an unresolved household and the *same* stipend
  does. This is a falsifiable claim about the model and it is the reason Mechanic
  1 and Mechanic 2 are inseparable: **the bribe only bites where the household is
  already failing.** A party that builds the kitchen can underpay its cadre. A
  party that does not, cannot.
- **(3) is the edge clause of `research/20` §3.5.** No door, no defection. A
  cadre in a county with no NGO and no union has no rung to climb.
- **(4) is the sink.** Defection is not a property of the cadre; it is a property
  of the **stipend row's pro-rata shortfall**. If the org's cash cannot cover
  every stipend, the engine floors them proportionally
  (`PracticeResourceAllocationMode::DivisibleProRata`,
  `PracticeResourceDivisibleLaw::ProportionalFloor`), and the cadres whose
  allocated share fell below the rung they can reach are the ones who leave. The
  player who over-recruits full-timers does not get a "morale penalty." They get
  a list of names, and the list is the arithmetic.

**The pincer, and why there is no correct wage.** Raising one stipend raises
`stipend_requested` for everyone, so beating rung 1 for one cadre can push
another below rung 2. This is conservation, not a nerf, and it means:

- paying at the **top** rung retains everyone and turns the party into an
  employer, whose payroll is Mechanics 4's `survival_interest`;
- paying at the **bottom** rung loses everyone with a door;
- therefore **the correct answer is neither. It is to lower the cadre's household
  claim (Mechanic 1) so that a lower stipend clears the comparison.** That is Mao
  1934, and it is the reason the two mechanics share a document.

**The selection effect, which is the political content.** Rung eligibility is
`k(i)`. A cadre who can reach `k=3` faces a high `w^P`; a cadre who can reach only
`k=1` faces a low one. So the movement's retention is *inversely* related to its
cadres' outside options, and what survives is not the most committed but **the
least employable**.

Say it in the game's own voice, once, in the Wiki, and then never again:

> The ones who stayed were the ones nobody was hiring.

That is Lenin 1919 as a recruitment filter, and the player will discover it by
watching the composition of their own cadre list drift over twenty periods
without being told why. It should be one of the most uncomfortable discoveries in
the game.

**What the player sees.** Never a rate. A **letter**, on the Ticker, in the
Corporate Feed and the Liberated Signal at once:

> **Corporate Feed:** *"Local 174 announces two new community liaison positions.
> Ms. Alvarez, formerly of the tenants' committee, brings 'a wealth of
> neighbourhood relationships.'"*

> **Liberated Signal:** *"Maria took the staff job. She told us on Thursday, in
> the kitchen, with the door shut. Her mother's dialysis is four hundred a month
> and the committee couldn't make it work. Nobody blamed her. Two people stopped
> coming the week after."*

The Intel Stream, underneath, is a receipt:
`PERIOD 19 | DEFECTION 2 | STIPEND ROW: requested 3400 allocated 2100 | RUNG 2 WAGE 41,300 | HOUSEHOLD CLAIM UNRESOLVED`.

**How it fails.** A party that recruits from the credentialed middle loses its
cadre to the credentialed middle, because that is where the doors are. A party
that recruits from the semi-colony keeps its cadre and cannot open the doors it
needs. This is a real strategic bind and it has no clean answer, which is the
point.

**Conformance debt retired.**
`strategy-layer.yaml::traps.liberal_trap.hidden_costs.cadre_demoralization: 0.10
# Best organizers become staffers` — the comment was the mechanic and the number
was wrong. `resource-sinks.yaml::cadre_labor.passive_decay.defection`
(`base_rate 0.01` plus three `+0.0x` modifiers) goes entirely.
`political-economy-liquidity.yaml::revolutionary_fundraising.source_matrix.
liberal_donors.drift_generated: 0.2` goes: donors do not generate drift, they
generate **a different book** (Mechanic 4).

---

### Mechanic 3 — The Underground Metabolism

**The claim.** "Going heavy" is not a posture toggle. It is a per-period **bill**,
paid in the one currency a concentrated apparatus cannot earn, and it is the only
major sink that buys nothing material.

**Snapshot.** `PracticeResourceCapacity` for the clandestine apparatus;
`OrganizerRefusal` counts (specifically `InsufficientCommittedTime`,
`CollectionCashRefused`, `AidReceivingRefused`, and partner `Refuse`/`NoResponse`);
`OrganizerPartnerPolicy`; the org's `MonetaryBook` (rent, documents, travel,
communications as individual postings); `MaterialCircuitState.freight` and
`corridor_capacities` for courier routes; `AidMandate` for external support.

**The integer form.** Split the cadre into concentrated `c` and dispersed `d`.
Mao 1945 supplies the categorisation, not a coefficient:

```
in_kind_capacity(t)   =  reported production hours by dispersed cadre     [Observed]
                         (concentrated cadre report none, by definition)

cash_requirement(t)   =  Σ_{i ∈ concentrated} ( stipend_i + apparatus_overhead_i )
                         [Observed: postings, not a formula]

operational_yield(t)  =  completed practices / (completed + refused-for-consent)
                         [Derived: from OrganizerRefusal and receipts]
```

Then the constraint is a budget constraint, not a rate:

```
c  is feasible  iff  cash_requirement(c)  ≤  org_disposable_cash(t)          [Mechanic 4]
```

**What concentration buys, stated exactly.** `OrganizerChoice` requires a partner's
independent participation (`OrganizerPartnerPolicy::Participate`). A practice
refused for `InsufficientCommittedTime`, or unexecuted because the workplace
partner returned `NoResponse`, is a *capability* the org does not have. A
concentrated cadre is not bound to a partner's wage-hours and can execute where a
dispersed one cannot. So concentration converts **refusals into completions**, and
the player can count the conversion: `refused-for-consent` before and after.

**What concentration costs, stated exactly.** Three effects, one variable:

1. `cash_requirement` rises by `stipend_i + apparatus_overhead_i` per cadre;
2. `in_kind_capacity` falls, because concentrated cadre produce nothing
   (Mao 1945);
3. **continuity is bought, and it is the thing you cannot buy later.** Lenin's
   respawn property (`research/05` §3): after a round-up, "two or three energetic
   persons could in the course of a few weeks establish contact between the common
   centre and new youth circles." Model it as a count, not a rate:
   `periods_to_recontact = f(persons who know the centre and were not seized)`,
   and *that count is exactly `c` truncated by the raid*. A dispersed org loses
   its bench when the state takes the committee. A concentrated one loses the same
   people and keeps the names.

**The cliff, and why `ExclusiveAllOrNone` is the right mode.** A cell is either
underground or it is a list of names in a drawer. So the apparatus row is sealed
`PracticeResourceAllocationMode::ExclusiveAllOrNone`, and when the org's cash
cannot fund `c` stipends the outcome is `ContestedUnallocated` — the engine
records that the claim went unmet rather than pro-rating it. That produces the
correct drama: **the period the money runs short is a naming event, not a decay
tick.** The player does not watch a bar fall. The player is asked who comes out
of the cold, and everyone in the room knows what the answer means.

**The three ways an underfunded apparatus fails, and all three are other
mechanics.** An apparatus whose `cash_requirement` exceeds its replenishment does
not "degrade by 2%." It does the cheaper thing:

- **(a) it demobilises** — cadre return to wage work, and then Mechanic 2 fires
  on them, because their household claim is now being met by an employer and the
  rung is close;
- **(b) it takes institutional money** — Mechanic 4's legal book, with the
  strings and the payroll;
- **(c) it lives off the base** — requisition, which is Mao's "draining the pond,"
  and which Mechanic 5 makes visible as the base's own households going
  unresolved.

**What the player sees.** Never a count of concentrated cadre. A **house**, on the
Physical Map and Topology: rented, in a name that is not the organization's, with
a lease that comes due. Two cars that are not the same two cars. A drop that
moved. And then, when the money runs out, a **meeting**, in a room, with a list
of names and a decision about who is still doing this next month.

**How it fails.** The professional apparatus is the correct answer to a state
with attention to spend, and it is unaffordable. That is not a balance problem;
it is Lenin's actual position ("as small a number … as possible") and it means the
player's real decision is **which three**, not how many.

**Conformance debt retired.**
`resource-sinks.yaml::cadre_labor.maintenance.security` (`cost 0.1 per cadre per
tick under surveillance`) and `maintenance.organization` (`0.05`, with a
`waiver: reduces if cohesion > 0.8`) both go. Cohesion does not waive rent.
`vanguard-economy.yaml::currencies.cadre_labor.constraints.attrition: "Lost in
failed high-risk operations"` survives, and should: that one is a count of people
and it is already honest.

---

### Mechanic 4 — The Two Treasuries

**The claim.** The choice is not "dues vs. grants vs. expropriation" as three
dials with different yields. It is **whose books the money sits on**, and each
location has a different owner, a different audit, a different police exposure,
and a different franchise that decides how it is spent.

**Snapshot.** `MonetaryBook` accounts (`CashAccount`, `AidCashReserve`,
`PurchaseEscrow`, `FundedShift`); `MonetaryBookSnapshot`; the recurring payment
rows (`RecurringEconomy`, `ReplenishmentPolicy`, `DistributionPolicy`,
`TaxPolicy`); `OrganizerCollectionMandate` (`cash_consent`,
`maximum_cash_micros`, `protected_cash_floor_micros`, `collection_hours`);
`AidMandate`; `PracticeInputAuthorityLedger` (whose authority spends what).

**The four books.**

| Book | Owner | Take | Its own standing claim | Police exposure | Franchise |
|---|---|---|---|---|---|
| **Household** | the household | member pledges, capped by `protected_cash_floor_micros` | rent, food, utilities, debt | low | the household |
| **Organization** | the party | dues, paper sales, member pledges | stipends, rent, print, bail | high (a receipt is a record) | the party |
| **Legal institution** | the union local / co-op / paper / hall | dues, contracts, grants, ticket sales | **payroll**, lease, debt service, grant conditions | low | **its own congress** |
| **Illegal economy** | the armed cell | a standing seizure stream (ADR180 R11) | apparatus hours, shares, bribes | highest | the cell |

**The integer form.** For each book `L`:

```
take_L,t        =  Σ receipts into L this period                     [Observed]
standing_L,t    =  Σ L's own obligations, itemised                   [Observed]
disposable_L,t  =  take_L,t − standing_L,t                            [Derived; may be negative]

spendable_by_party_L  =  disposable_L,t   if  authority(L) = party
                        0                 otherwise
```

and the law that makes `survival_interest` a fact rather than a mood:

> **A legal book's standing claim grows to meet its take.**

Not as a rule imposed by the designer, but because hiring is the only way to spend
a growing legal income *usefully*, and Mao 1942 already told us what the hires are
for: "over-elaborate organization, meaningless 'standardization' and red tape." So:

```
standing_{L,t+1}  →  take_{L,t}       (a fixed point, approached by hiring and leasing)
disposable_{L,t}  →  0
```

and what remains is **loyalty purchased by a payroll**. That is `survival_interest`,
and it is a headcount:

```
salaried_staff(L, t)  =  # persons whose income comes from L's standing claim   [Observed]
```

The porch-02 ruling fixes the horizon at 260 periods after constitution. This
briefing adds only *what is counted*: two integers, `salaried_staff` and
`cadre_count`, both readable off the books. When `salaried_staff > cadre_count`,
the shell has already won; the 260-period deadline is then the formal
acknowledgement, not the discovery. And the player can *see* the crossing while
still inside the clock, which is the whole point of a clock.

**How you get money determines who you become — as four concrete consequences.**

**(a) Dues are cheap in money and expensive in hours, and the record is a
liability.** Lenin's two-kopeks rule needs `collection_hours` per member per
period, and the field already exists (`OrganizerCollectionMandate.collection_hours`).
So:

```
net_dues  =  Σ_{i∈members} pledge_i  −  (collection_hours × hours_cost)
```

`hours_cost` is the opportunity cost of a cadre-hour — *Derived*, from what the
same hour would have produced elsewhere this period (the practice it displaced).
And the `take` is only collectable up to `protected_cash_floor_micros`: the engine
already refuses to take the rent, and returns `ProtectedConsumptionUnmet` when it
would. **Dues are structurally small, and the structure is the household's own
reproduction floor.** No cap is needed; the cap is the receipt.

**(b) Institutional money is large and is not yours.** Stalin 1906: separate
funds, separate leading body, own congress. So spending it on a party purpose is
not a `MoneyPosting` the party can make; it is a **policy decision by a body the
party does not control**, and the engine's expression of that is a
`PracticeInputAuthorityLedger` entry owned by a different actor. The player's lever
is not the money; it is winning the body's congress, which is an ordinary
organizational problem with an ordinary cost. And the eight-week life of *Akhali
Droyeba* is the calibration for how long a legal stream lasts once it matters.

**(c) Foundation money and wealthy angels flood the node with consumers, and this
is Weinstein's mechanism, not a drift float.** Money that requires no risk attracts
people who require no risk. So the mechanised form is a **composition change** on
the receiving node: the node's `active` count rises, its `cadre-level` falls, and
its `concern`/`objection`/`review_condition` triple becomes generic. There is no
`reformist_drift` scalar; there is a node that now has forty members and two
people who will do the work, and the player can see it in the participant list.
`political-economy-liquidity.yaml`'s `donor_rate`, `collection_efficiency`,
`ideological_alignment` and `drift_generated: 0.2` are all retired by this.

**(d) Expropriation is a standing economy, not a heist, and its degeneracy is a
ratio on its own receipts.** ADR180 R11 is binding: "ALL SEIZURE STAYS UNDER
BUILD. The funding cell's `illegal_economy` means STANDING illegal economies (the
FLN's monthly income), never a liquid heist variant." So the mechanic is an
apparatus with a yield, an upkeep and a *share*:

```
share_to_participants  =  Σ payments to the cell's own personnel / total take   [Observed]
```

That single measured ratio is the bandit/insurgent distinction, and it needs no
moralism. **A cell that pays its own people a share of the take is a business, and
a business needs a bigger take.** Mechanically: high `share` ⇒ the cell's
participants require the next seizure to exceed the last to hold their income ⇒
seizure frequency rises ⇒ state Threads are allocated to the cell ⇒ the org's
`R_j` rises for reasons the player did not choose. Banditry is therefore
**self-accelerating and legible only through tempo**, which is exactly how it
presents in history and exactly how `research/17` models state attention.

The Tiflis illustration, with its status declared. `political-economy-liquidity.yaml`
already asserts "Bolshevik 1907 Tiflis bank robbery: 250,000 rubles"; the commonly
cited total for the Erivansky Square seizure is ~341,000 rubles, of which the
500-ruble notes — the traceable part, which then had to be laundered abroad over
years — are usually given as ~250,000. **This figure is Calibrated historical
reference and was not verified against a primary text in this sweep** (see §9). Its
only design use is as the *upper bound on one period's take by a maximally
prepared apparatus*, which is to say: it is the reason the mechanic must be a
stream with an upkeep and not a button, because a single take that large would
break any budget a player has.

**What the player sees.** The Ticker's **two-column cash book** per book: receipts
on the left, *standing obligations* on the right, and the difference — sometimes
negative — on the bottom line. No percentages. The moment of recognition is the
period the player notices that the right-hand column of the union local's book now
exceeds the party's entire income, and that every name in it is a person who will
vote against them at the next congress.

**How it fails.** The party that refuses institutional money stays poor and stays
itself. The party that takes it becomes an institution and stays solvent. The
party that takes it and *wins the congresses* has done the hardest thing in the
game, and it is not modelled as a special mechanic: it is ordinary organizing
inside a body with its own franchise.

**Conformance debt retired.**
`political-economy-liquidity.yaml::revolutionary_fundraising.source_matrix`
(entire), `corruption_metrics.heat` (already indicted by ADR184 R6),
`corruption_metrics.reformist_drift` (entire), and
`RevolutionaryFinance.dues_income/expropriation_income/donor_income` as a triple
of rates — replaced by four books and two counts.

---

### Mechanic 5 — The Siege Larder

**The claim.** A strike or a besieged base area is not a duration timer. It is a
**stock of divisible goods plus a count of households with a claim**, and
capitalism's weapon is that the claim accrues every period while the stock does
not.

**Snapshot.** `InventoryRow` (the actual stock, in the actual units —
`prepared_food`, `grain`, `water`, `packaged_beverages`, all in kg per
`defines.toml`); `HouseholdNeed` and `HouseholdCohort` (who is on strike and what
each household requires per period, via `required_quantity`); `SellerOffer`
(`unit_price` and `PricePolicy`); `AidMandate` (external solidarity, in goods and
cash, with `AidTransport` so a blockade is expressed as a route stage and not as a
flag); `fact_census_rent_burden` and `fact_census_rent` for the cash claim.

**The integer form.** Two covers, in *periods*, and the endurance is the smaller:

```
goods_claim_g     =  Σ_{i ∈ struck} required_quantity(i, g)                  [Derived]
goods_cover_g     =  floor( inventory_g / goods_claim_g )                     [count of periods]
goods_cover       =  min over g ∈ {food, water, ...}                         [the binding good]

cash_claim        =  Σ_{i ∈ struck} ( rent_i + utilities_i )                  [Observed]
cash_cover        =  floor( org_disposable_cash / cash_claim )                [count of periods]

endurance         =  min( goods_cover, cash_cover )
```

`endurance` is a **count of periods** and it is printable without becoming math:
*"The larder holds eleven periods if nothing changes and the price holds."* That
sentence is the whole UI, and it is honest, because the last clause is a promise
the enemy intends to break.

**Why the price does not hold, with zero design intervention.** `SellerOffer` is
already `PricePolicy::Responsive { minimum, maximum, step, target_stock }`. As the
county's `inventory` of prepared food falls, the responsive policy raises
`unit_price`. So the strike fund's *cash* cost of replacing consumed goods rises
as it consumes them, and `cash_cover` falls faster than `goods_cover`. **The siege
is endogenous.** Nobody wrote a timer.

**Why the eviction clock and the turn clock are the same clock.**
`TICK_DURATION_DAYS = 28`. Rent is monthly. So every turn is exactly one rent
period, and every turn the struck household's protected claim is re-tested:

- the household cannot make rent ⇒ `protected_unresolved_hours > 0` ⇒ **Mechanic
  1's cliff fires** and the household's `contribution_available` goes to zero;
- so the picket line loses a household **every turn the fund cannot cover rent**,
  not gradually;
- and eviction is a permanent loss of the household's *edge*, which is the thing
  the whole model is built on (`research/20` §3.5: no edge, no defection, and
  symmetrically no edge, no participation).

This is the single most important structural fact in Mechanic 5. The turn length
and the rent cycle coincide **because 28 days is a month**, and nobody had to
choose it. The player will feel the rent come due every turn without ever being
told that the calendar is the enemy.

**The genuine strategic fork: concentrate or disperse.** Mao 1945 gives both horns
and neither is a slider.

| | **Concentrated picket** | **Dispersed self-provisioning** |
|---|---|---|
| Coercive yield | high: production actually halts | low: production continues, the strike is a tax |
| Cash requirement | high: every household must be paid in cash | low: households partly feed themselves |
| Price exposure | high: fully exposed to `PricePolicy::Responsive` | low: in-kind, off the market |
| Self-provisioning | **impossible** (Mao 1945: "unable to engage in production to support themselves") | possible, and it is the whole point |
| What breaks it | the treasury | the picket's credibility |

And the calibration for the dispersed horn is the guerrilla-zone ration: "each
person has 0.5 *liang* of cooking oil and salt and 1 *chin* of vegetables per day,
and 1.5 *chin* of meat per month" — a *survivable* basket, not a comfortable one.
Babylon should adopt that basket as the `Designed` self-provisioning floor, because
it is the only historically attested answer to "what does a blockaded unit actually
eat," and because it is small enough to be a real constraint.

**The conversion leg, which is the only sink that returns capacity.** Spending
larder stock as *input* — a communal kitchen, a mill, a market garden, a fuel
co-op — lowers each served household's `protected_hours` next period (Mechanic 1b),
which raises `contribution_available`, which raises the movement's hours. One
expenditure, three periods later, returns **labour, not money.** That is the
revolutionary metabolism in its positive form, and it is the answer to the
assignment's actual question: *what stops the game from becoming spreadsheet
clicking is that the correct play converts stock into a permanently lower
requirement.*

Mao's three dated stages (§1.2) are this curve, in a document: take little while
the base builds strength; take heavily in the blockade; lighten again because the
public economy now produces. The player's burden schedule should have the same
shape, and the shape should be *their* doing.

**What the player sees.** Not a bar. A **store room**, with visible quantities, and
a sentence: *"Eleven periods, if nothing changes and the price holds."* Then, in
period six, the Corporate Feed prints a grocery price rise and the sentence becomes
*"Nine periods."* The player did that to themselves and can work out how.

**How it fails.** A strike that is fed but not defended is dispersed by the police
and its larder is seized. A strike that is defended but not fed is dispersed by
hunger. A strike that is both, and that does not convert, wins and then has nothing
— it has spent the base's surplus and the base is now poorer than before the
strike, which is the *economic* defeat that follows a tactical victory.

**Conformance debt retired.**
`resource-sinks.yaml::crisis_drains` (the whole block: `-20%`, `-30%`, `-40%`,
`-50%`, `-60%` on named events). A crackdown is not a percentage of your cadre; it
is a count of people seized, and `research/17` already models how the state chooses
them.

---

### The reproduction lag (a consequence, not a sixth mechanic)

Cadre reproduction is not a training cost. It is a **promise with a date on it**,
and the existing type already says so.

`OrganizerParticipant` carries `concern`, `objection` and `review_condition`. A
`review_condition` is a condition a participant states for continuing. Examples
the game should generate, in the participant's own words:

> *"I'll keep doing Thursdays as long as we're not just doing the paper."*
> *"I can do the shelter but not the money. Ask me again when there's a treasurer."*
> *"If we go to the county commission again I'm out."*

Then the mechanic is: **a review condition is checked at the period it names, and
if it is unmet, the commitment does not decay — it ends**, with the reason on the
record and in the Wiki. Nothing is subtracted. A person leaves and says why.

Three consequences:

1. **The party's promises become a register**, and the register is a Wiki page:
   every condition, every date, whether it was met. This is the most honest
   "organizational health" readout the game can have, and it is not a stat.
2. **A party that keeps its promises has a lower `stipend_requested`**, because
   participants whose review conditions are met are the ones who renew without
   renegotiation. That is Mao 1934's conversion applied to the *leadership*
   instead of the masses, and it costs nothing but honesty.
3. **A party that breaks them loses specific people at specific times**, and the
   pattern of *which* conditions it broke is its real line. A party that keeps
   breaking "not just the paper" conditions is a paper. A party that keeps breaking
   "not the money" conditions is becoming an NGO. The player's own record tells
   them what they are, and it does so without a single number.

---

## 4. Dramatic decision ceremonies

Format per porch-01: split pane, options side by side, honest summaries of **what
each means**, never what each yields; the seal states what is staked and what is
unknown; outcomes are never previewed. No percentages, no multipliers.

---

### Ceremony 1 — *The Offer*

**Trigger.** A cadre's `poach_i` conditions (1), (2) and (3) are all true and (4)
is about to resolve. Period close is one turn away.

**Pane left.**

> **MARIA ALVAREZ — tenants' committee, four years**
>
> Local 174 has offered her a community liaison post. Forty-one thousand a year,
> dental, a desk. Her mother's dialysis is four hundred a month. The committee
> has been paying Maria three hundred a period and has been late twice.
>
> She has not resigned. She has told you, in the kitchen, with the door shut,
> which is the same thing with a delay on it.

**Options.**

- **Match the offer.** *The committee would have to raise her stipend to something
  it cannot raise for anyone else. Two other people would find out. You would be
  buying one cadre at the price of the argument that you pay everyone the same.*
- **Take over the household claim.** *A kitchen that runs five days, and someone
  to sit with her mother two afternoons. It costs food, a room, and two other
  people's Thursdays — and it makes three hundred a period survivable for Maria
  and for whoever comes after her.*
- **Let her go, and keep the door open.** *She will be inside Local 174 with a
  salary and a list of your names in her head. She has asked whether she can still
  come to the Thursday meeting. You have to decide what to say.*

**The seal.**

> *Staked: Maria's hours, and whether the committee is a place where people stay.
> You will not know whether the kitchen holds until someone's mother is ill in a
> month when the food money is short.*

**The three feeds, at period close.**

- *Corporate Feed:* *"Local 174 Welcomes Community Liaison; 'A Bridge to the
  Neighbourhoods,' Says President."*
- *Liberated Signal:* *"Maria took the job. She came Thursday anyway, and sat at
  the back, and did not speak. Two people stopped coming. One person asked what
  the kitchen would cost."*
- *Intel Stream:* `PERIOD 20 | DEFECTION 2 | STIPEND ROW 3400/2100 | RUNG 2 41300 |
  HOUSEHOLD CLAIM UNRESOLVED`

---

### Ceremony 2 — *The Audit*

**Trigger.** The legal institution's books are subpoenaed, or a `Thread` reaches
the paper's incorporation records. The union local's payroll and the party's
membership roll are in the same filing cabinet because they have been in the same
room for six years.

**Pane left.**

> **THE HALL — 2,140 members, four staff, a lease through June**
>
> The county has asked for the membership list and the dues ledger. The lease is
> in the local's name. The ledger is the only record of who is owed what, and it
> is also a list of names, addresses and employers, in order, by date joined.

**Options.**

- **Comply and hand over the roll.** *The local keeps its charter, its hall and its
  four staff. The party loses the only complete account of its own membership, and
  every name on it is now in a federal file. Nobody is arrested this period.*
- **Destroy the roll and keep the money.** *The subpoena is answered with an
  incomplete production and a lawyer. The local's dues collection has no basis:
  next period nobody knows who is in arrears, so nobody is, so the take falls to
  whatever people volunteer. The payroll is unchanged.*
- **Move the people, keep the paper.** *Rebuild the roll as coded coupons in the
  paper, per Lenin's "reports in a certain agreed code." Two periods of work by
  the three people who can do it, and afterwards the party cannot audit its own
  treasurer — which is the price Lenin named and paid.*

**The seal.**

> *Staked: the local's charter, the party's roll, and the four salaries. Unknown:
> whether the county wants the names or wants the hall. You will find out which
> when the second subpoena arrives, and by then the first decision is spent.*

**Why there is no good answer.** Lenin, 1902, on the fund with monthly accounts:
"this is a very paradise for the police." Stalin, 1906, on the body that holds it:
"their own separate funds, their own leading bodies, call their own congresses."
The player cannot have the audit and the security. The only question is which one
they lose first, and the game should not let them find out in advance.

---

### Ceremony 3 — *The Larder*

**Trigger.** A general strike, period six. `endurance` was eleven. It is now six,
because the price of prepared food in the county rose twice.

**Pane left.**

> **THE STRIKE FUND — period six**
>
> Four thousand one hundred households out. Two thousand two hundred and forty
> rent notices due in eleven days. The store room holds food for six more periods.
> The fund holds enough cash to cover rent **or** to buy food at this week's
> price. Not both. There is a kitchen in the hall that could run five days a week
> if somebody bought the pots.

**Options.**

- **Pay the rent.** *Nobody is evicted this period and the fund is empty. Next
  period the food must be bought on credit from the same people who raised the
  price, and the store room's clock starts falling faster than the rent's.*
- **Buy the food, let the notices run.** *The picket holds this period and next.
  In eleven days some households are served, some are not, and the ones served are
  the ones with an edge to the committee and the ones who know a lawyer. The
  strike's line becomes a line about who the committee protects.*
- **Buy the pots.** *Nobody is paid this period. The kitchen opens in two periods
  and the food requirement per household falls. If the strike lasts past the
  opening, the fund's clock stops falling. If it does not, the pots are scrap and
  the households remember that the committee bought pots.*

**The seal.**

> *Staked: the rent notices, and the answer to "who does the committee protect."
> Unknown: whether the price rises again on Tuesday, and whether the strike lasts
> past the opening.*

**The three feeds.**

- *Corporate Feed:* *"Grocers Cite 'Supply Chain Adjustments' as Local Prices Rise;
  Community Leaders Urge Patience."*
- *Liberated Signal:* *"The price went up twice this month. Nobody raised it. That
  is what a market is. We bought the pots."*
- *Intel Stream:* `PERIOD 31 | STRIKE 4100 HH | RENT DUE 2240 | GOODS COVER 6 |
  CASH COVER 2 | PRICE +2 STEP | KITCHEN PENDING 2`

---

### Ceremony 4 — *The Congress on the Payroll*

**Trigger.** The party is constituted. `salaried_staff` is 40; `cadre_count` is 12.
The clock is running. A cadre school needs two full-time teachers and there is no
money for them that is not already committed to the paper's staff.

**Pane left.**

> **THE PARTY — period 84 of the clock**
>
> The paper has four paid staff. The union local has eleven, and eight of them are
> ours in everything but the paperwork. The hall has a caretaker and a bookkeeper.
> The party has twelve cadre and forty people on a payroll. The cadre school would
> take two of the twelve and would produce three more in a year.

**Options.**

- **Keep the payroll.** *The paper prints, the local holds its contract, and the
  hall stays open. In three periods the payroll will be forty-four, because the
  local is negotiating a new contract and the paper needs a circulation manager.
  The cadre school does not open.*
- **Cut the staff to fund the school.** *Four people lose their incomes in the same
  week. The paper stops printing for a period. The local's leading body — which is
  not yours — meets without you and elects a president who is not yours either.
  The school opens.*
- **Send the staff into the shops.** *They keep their skills, lose their salaries,
  and become dispersed cadre who can self-provision. In six months you will know
  which of the forty were cadre and which were employees. Half of them will not
  come back, and you will not know which half until they do not.*

**The seal.**

> *Staked: the paper, the local, and forty incomes. Known: the payroll is now larger
> than the party. Unknown: which of the forty would still be doing this if it paid
> nothing. You will find out either way.*

**The three feeds.**

- *Corporate Feed:* *"Labour Paper Scales Back Print Run; Cites 'Restructuring.'"*
- *Liberated Signal:* *"We asked forty people to choose. Twelve chose. We have been
  calling ourselves a party of twelve for six years and paying forty. The twelve
  are the party. The forty were the paper."*
- *Intel Stream:* `PERIOD 84 | PAYROLL 40 | CADRE 12 | PAPER HALT 1 | LOCAL CONGRESS
  3 | SCHOOL OPEN 1`

---

## 5. What the player sees

The visibility rule governs (porch-01): *concrete countable world-events may show;
engine-computed abstractions stay buried.* Applied to sinks:

### Ticker

- **The household week**, laid out as a schedule: wage block, second-shift block, a
  grey commute band, sleep, and one small dark strip labelled by whoever is asking.
  No number, no bar. A week with no dark strip is a household with nothing left.
- **The books, two columns each.** Receipts left, *standing obligations* right, the
  difference — sometimes negative — below. Four books: household, party, legal
  institution, illegal economy. The player reads their own capture as a right-hand
  column that has grown past the left.
- **The store room and one sentence.** *"Eleven periods, if nothing changes and the
  price holds."* Then the price changes and the sentence shortens.
- **The disappeared price.** Unchanged from porch-02 and now load-bearing in two
  directions: a good leaves the commodity market when a base area is real (the
  raft), and a good's price *rises* when the larder is eating the county's stock
  (the siege). Same instrument, opposite signs, and the player learns to tell them
  apart.
- **The staff wage.** The Corporate Feed prints it, because it is public. *"Local
  174: community liaison, $41,300."* That is the player's own cadre budget printed
  in the newspaper, as news, and it is the only place the bribe gradient appears
  on a screen.

### Topology

- **Paid edges and given edges look different.** An edge that exists because
  somebody is on a salary is drawn as a line with a small regular mark on it. An
  edge that exists because somebody comes on Thursdays is drawn plain. The player
  who watches a node convert from plain to marked is watching capture happen.
- **A captured node reads as stable, well-lit, and boring.** That is the tell, and
  it should be the most attractive thing on the canvas in the mid-game, because it
  *is* attractive: it works.
- **An unresolved household shows as a household, not a warning.** A named person
  with a line to the institution and a second line to a hospital or a landlord. The
  second line is what will break the first.

### Wiki

- **The promise register.** Every `review_condition` the party has accepted, with
  its date and whether it was met. Sortable by person, by institution, by whether
  it was met. This is the closest thing to an organizational health readout the
  game should own, and it is a list of sentences.
- **The payroll page.** Who is paid, by which book, since when. A party can read its
  own obituary here years before the clock runs out.

### What never shows

`E`, `w^P/m`, `poach` counts, `endurance` as a percentage, `survival_interest` as a
number, `salaried_staff/cadre_count` as a ratio, any decay rate, any modifier, and
any preview of what an option yields. The player reads *"the right-hand column is
bigger than the left-hand column"* and does the rest.

---

## 6. Conformance debt

| Site | Current form | Violation | Replacement |
|---|---|---|---|
| `resource-sinks.yaml::cadre_labor.passive_decay` | `burnout 0.02`, `defection 0.01` + three `+0.0x` modifiers, `death_capture 0.005` | rates on a stock; `better_offers: +0.02 if State offers amnesty` is Mechanic 2 wearing a number | `poach_i` four-boolean conjunction (M2); deaths are a count from `research/17`'s targeting |
| `resource-sinks.yaml::cadre_labor.maintenance` | `security 0.1/cadre/tick`, `organization 0.05`, `waiver` at cohesion > 0.8 | per-cadre constants; cohesion does not waive rent | itemised postings on the org's monetary book (M3) |
| `resource-sinks.yaml::sympathizer_labor.passive_decay` | `enthusiasm_decay 0.03`, `life_pressures 0.02` ("People have jobs, families, survival needs"), `repression_fear`, `disillusionment 10–30%` | the annotation was the mechanic | `HouseholdTimeReceipt` partition and its cliff (M1) |
| `resource-sinks.yaml::reputation` | `attention_decay 0.05`, `scandal_risk 0.02` | a rate on a stock; random draw | reputation as `research/05`'s accumulated observability, spent by exposure |
| `resource-sinks.yaml::theoretical_labor` | `knowledge_atrophy 0.02`, `generational_loss -10%` | a rate on a stock | the promise register and `review_condition` (the reproduction lag, §3); generational loss is a count of unmet conditions |
| `resource-sinks.yaml::crisis_drains` | `-20%`/`-30%`/`-40%`/`-50%`/`-60%` on named events | percentages | counts of persons seized and institutions lost, from the targeting model |
| `resource-sinks.yaml::equilibrium` | `sustainable_range`, `growth_targets: "5% net growth per 10 ticks"` | a designer's desired equilibrium stated as a target | conservation-first pro-rata allocation; there is no target, there is a shortfall |
| `vanguard-economy.yaml::transmission_belt.coherence_factor` | `sigmoid((cadre/sympathizer)/K_COHERENCE)` | ADR173 forbids a stipulated S-curve | `completed / (completed + refused-for-consent)` from `OrganizerRefusal` (M3) |
| `political-economy-liquidity.yaml::revolutionary_fundraising` | `dues_rate`, `collection_efficiency`, `donor_rate`, `ideological_alignment`, `heat_generated 0.3`, `drift_generated 0.2` | magic rates; `heat` and `reformist_drift` are both indicted scalars | four books and two counts (M4) |
| `political-economy-liquidity.yaml::corruption_metrics` | `heat` (`decay 0.05`), `reformist_drift` (`[-1,1]`) | ADR184 R6 retires `heat`; `reformist_drift` is a stored derived quantity | `L`/`K`/`X` for heat; the payroll for drift (M4) |
| `political-economy-liquidity.yaml::operational_burn` | `cadre_count * cadre_upkeep + safe_house_count * safe_house_rent` with defaults `2.0` | per-cadre constant | `cash_requirement = Σ (stipend_i + apparatus_overhead_i)` as postings (M3) |
| `reproductive-labor.yaml::tier_1` | `regeneration_rate 0.01`, `solidarity_regeneration_bonus 0.005`, `capped_extraction` with `subsistence_floor 0.08/0.02` | rates and floors | `freed_hours` subtraction from `protected_hours` (M1b); the floor is the household's own `protected` claim |
| `strategy-layer.yaml::traps.liberal_trap.hidden_costs` | `cadre_demoralization: 0.10 # Best organizers become staffers` | the comment was the mechanic | `poach_i` (M2) |
| `strategy-layer.yaml::traps.*.cost` | `cadre_labor: 10`, `cash: 5000`, `sympathizer_labor: 50` | flat action prices | `PracticeResourceCapacity` requests and `conservation_first()` pro-rata |

---

## 7. Falsifiers

1. **The cliff.** If a campaign sweep shows that households with
   `protected_unresolved_hours > 0` still contribute measurable hours — i.e. if the
   priority invariant is doing no work in outcomes — then the cliff is decorative
   and the whole of Mechanic 1's drama is unearned. Test: run with the invariant
   relaxed to a pro-rata partition and compare cadre-hour supply curves.
2. **The Fortunati conjunct.** Mechanic 2's conjunct (2) — the household claim must
   be binding — is the claim that *the bribe only bites where the household is
   already failing*. If a sweep shows equal defection rates among cadres with
   resolved and unresolved household claims at the same stipend, conjunct (2) is
   false and the model reduces to a wage comparison without a reproduction term.
   That would be a significant negative result and should be reported as one.
3. **The selection effect.** Mechanic 2 predicts that surviving cadre are
   disproportionately those with low outside options. If the engine's cadre
   composition does *not* drift toward lower rung eligibility over twenty periods,
   then either rung eligibility is the wrong proxy for outside options or the wage
   comparison is not binding.
4. **The rent clock.** Mechanic 5's sharpest claim is that the 28-day period makes
   the eviction clock and the turn clock identical, which should produce picket
   attrition *at period boundaries* rather than within periods. If attrition is
   smooth across a period, the 28-day identity is doing no work and the rent claim
   belongs somewhere else.
5. **The nine-to-one rule.** If a sweep shows players who spend *more* than
   one-tenth of cadre hours on extraction doing better than players who hold the
   9:1 line, Mao's causal claim ("if pains are taken with the first task, the second
   will be easy") is falsified in this game's parameter space, and the rule should
   be a discovered regularity rather than a stated law.
6. **The conversion leg.** If buying the pots (Ceremony 3) is never the best move
   across the campaign sweep, then the "sink that returns capacity" is a
   decoration, and the positive metabolism has failed to exist.

---

## 8. Open questions for the porch

1. **Is the personnel unit a household or a person?** The engine's time book is
   per-`FinalDemandPrincipal` (household), the organizer is per-`contributor_id`
   (person), and Fortunati's whole point is that the two are different units
   paying two different debts. Babylon needs a stated answer before Mechanic 2 can
   be built, because `m_i` is a person's income and `protected_hours_i` is a
   household's claim. My reading: keep both, and make the *stipend* the place they
   meet.
2. **Does the wage ladder get a fifth rung?** The assignment names four poaching
   channels (union staff, NGO, grad school, petty-bourgeois career). I have modelled
   three rungs because three are observable in QCEW/OEWS and the fourth (grad
   school) is a *deferral*, not a wage — it pays a stipend and a credential. Is
   deferral a distinct mechanic (the cadre returns in three years, changed) or just
   a defection with a delay?
3. **Who audits the treasurer?** Lenin chose opacity and named the cost. If the
   player chooses coded coupons, the engine has no way to represent "the treasurer
   is stealing" without a hidden variable. Is that acceptable — i.e. is the game
   willing to have an unobservable embezzlement channel? I think yes, and I think it
   is one of the most honest things the game could do, but it needs a Director
   ruling because it is a fog the player cannot penetrate even in principle.
4. **Does the party ever pay a family wage?** §1.9 says a wage for one worker buys
   two workers' labour-power, and that the second is unpaid. A party that pays a
   family wage is therefore buying a housewife. Should that be representable? It is
   historically what every party did, and representing it makes the gender
   consequence visible; not representing it makes the party better than any
   historical party for free.
5. **What is the unit of the legal institution's franchise?** One member, one vote
   at the congress is the union form. A co-op is one member one vote; a nonprofit
   is a board; a paper is an owner. Different forms give the party different
   capture costs, and the choice between them is a real strategic decision the game
   currently has no vocabulary for.
6. **Does `survival_interest` count people or money?** I have argued for a
   headcount (`salaried_staff` vs `cadre_count`) because a payroll is a *number of
   people whose loyalty is purchased*, and money is a proxy that a rich party can
   fail. But the porch-02 ruling's language is about a "constituency," which is
   people. Confirm the headcount.

---

## 9. Sources read

**Repository, read directly.**

`ai/epochs/epoch3/resource-sinks.yaml` (full, 390 lines) ·
`ai/epochs/epoch3/vanguard-economy.yaml` (full, 907 lines) ·
`ai/epochs/epoch3/reproductive-labor.yaml` (full, 220 lines) ·
`ai/epochs/epoch3/political-economy-liquidity.yaml` (income, fundraising,
corruption metrics, fund constants) ·
`ai/epochs/epoch3/strategy-layer.yaml` (the three traps and their hidden costs) ·
`ai/epochs/epoch3/state-attention-economy.yaml` (Threads as allocation, not
expenditure) ·
`ai/decisions/ADR176_director_rulings_batch_gds_dispositions.yaml` (items 37, 38) ·
`ai/decisions/ADR180_gate_clearing_rulings_batch.yaml` (R8–R14) ·
`ai/decisions/ADR184_capacity_belongs_to_organizations.yaml` (full — R1–R7) ·
`ai/decisions/ADR187_article_v_3x3_ratified.yaml` (OQ-1…OQ-5, especially OQ-3:
"replenishment is a SYSTEM consequence, never a verb") ·
`rust/crates/babylon-material-circuit/src/household_time.rs` (full — the partition
and its `validate()`) ·
`rust/crates/babylon-material-circuit/src/recurring/model.rs`
(`RecurringEconomy`, `HouseholdCohort`, `HouseholdStock`, `HouseholdNeed`,
`HouseholdPurchasePolicy`, `SellerOffer`, `PricePolicy`, `ReplenishmentPolicy`) ·
`rust/crates/babylon-material-circuit/src/model.rs` (`MaterialCircuitState`,
`MaintenanceService`, `OrderRow`, `FreightLot`) ·
`rust/crates/babylon-material-circuit/src/aid.rs` (`AidMandate`, `AidTransport`,
`AidOutcome`) ·
`rust/crates/babylon-material-circuit/src/accounts.rs` (`CashAccount`,
`MonetaryBook`, `FundedShift`, `PurchaseEscrow`) ·
`rust/crates/babylon-practice-contract/src/resource.rs` (full —
`conservation_first()`, `DivisibleProRata`, `ExclusiveAllOrNone`,
`ProportionalFloor`, `ContestedUnallocated`) ·
`rust/crates/babylon-practice-contract/src/organizer/types.rs` (full —
`OrganizerParticipant` with `concern`/`objection`/`review_condition`,
`OrganizerChoice`, `OrganizerRefusal`, `OrganizerPreview`,
`OrganizerPeriodTimeWitness`) ·
`rust/crates/babylon-practice-contract/src/organizer/collection.rs` (full —
`OrganizerCollectionMandate`, `protected_cash_floor_micros`, `collection_hours`,
`OrganizerCollectionOutcome`) ·
`rust/crates/babylon-practice-contract/src/strike.rs` (full — the admitted strike
proposal and its `PendingIndependentResolution` participation rows) ·
`content/scenarios/michigan/defines.toml` (`TICK_DURATION_DAYS = 28`,
`WORK_HOURS_PER_PERSON_WEEK = 40`, the commodity dispositions, the process recipes) ·
`docs/gameplay/2026-10-25-porch-01.md` (full) ·
`docs/gameplay/2026-10-25-porch-02.md` (full) ·
`docs/gameplay/porch-handoff.md` (full) ·
`docs/gameplay/00-overview.md` (full) ·
`docs/gameplay/research/05-lenin-witbd-and-vanguard.md` (§2 primitiveness, §3 the
newspaper as protocol, the respawn property) ·
`docs/gameplay/research/07-babylon-books-unequal-exchange-and-reproduction.md`
(§5 Fortunati, Mies, Meillassoux; §2.1 the household week; §2.5 the gender
aristocracy) ·
`docs/gameplay/research/08-babylon-books-networks-policing-and-insurgency.md`
(§2.1 Weinstein, §3.5 the edge clause, R2–R5) ·
`docs/gameplay/research/12-lenin-stalin-vanguard-party-threshold.md` (§1.2 Rule 1,
"supports it financially") ·
`docs/gameplay/research/13-differential-equations-chaos-and-wealth-dynamics.md`
(the magic-number filter) ·
`docs/gameplay/research/14-babylon-data-treasure-trove.md` (§2.6 — the ATUS
household-time baselines and the `E` identity) ·
`docs/gameplay/research/20-reactionary-subject-fascist-militias-and-life-raft-bifurcation.md`
(full — the sibling form: four booleans, no coefficient, and the certificate that
this register is buildable).

**Marxists Internet Archive / MIM text archive, read directly.**

Mao Zedong, *Be Concerned with the Well-Being of the Masses, Pay Attention to
Methods of Work* (27 Jan 1934) — read in full at
`reference/archive/mao/selected-works/volume-1/mswv1_10.htm` on MIA, and
cross-checked against the alternate *Collected Works* translation at
`/media/user/data/mim/textonly/classics/mao/cwcia/cwm4_5.txt`. The two differ in
wording ("Soviet" for "government," "T'ing-chou" for "Tingchow") and agree on
every figure and every item of the goods list; quotations above follow the
*Selected Works* text.
Mao Zedong, *Economic and Financial Problems in the Anti-Japanese War* (Dec 1942)
— read in full at
`reference/archive/mao/selected-works/volume-3/mswv3_12.htm`.
Mao Zedong, *Some Questions Concerning Methods of Leadership* (1 Jun 1943) —
`/media/user/data/mim/textonly/classics/mao/sw3/mswv3_13.html`.
Mao Zedong, *Spread the Campaigns to Reduce Rent, Increase Production and
"Support the Government and Cherish the People" in the Base Areas* (1 Oct 1943) —
`.../sw3/mswv3_15.html` (the nine-to-one rule).
Mao Zedong, *Get Organized!* (29 Nov 1943) — `.../sw3/mswv3_17.html` (the
co-operative as the mass form; "cadres in reserve").
Mao Zedong, *We Must Learn to Do Economic Work* (10 Jan 1945) —
`.../sw3/mswv3_22.html` (labour heroes as the cadre pipeline; the "bridge" role).
Mao Zedong, *Production is Also Possible in the Guerrilla Zone* (31 Jan 1945) —
`.../sw3/mswv3_23.html` (the ration basket; the felt-cap workshop, oil press and
flour mill; 500,000 yuan in seven months).
Mao Zedong, *On Production by the Army for Its Own Support and on the Importance
of the Great Movements for Rectification and for Production* (27 Apr 1945) —
`.../sw3/mswv3_27.html` ("unified leadership and decentralized management";
concentrated formations cannot self-provision; "encroachments upon the property
of the people seldom or never occur").
V. I. Lenin, *What Is To Be Done?* ch. III, ch. IV (including §C "Organisation of
Workers and Organisation of Revolutionaries," the two-kopeks fund and the
"paradise for the police," and "we must arrange that he be maintained by the
Party"), and the Conclusion —
`archive/lenin/works/1901/witbd/{ch02,ch03,concl}.htm` on the local mirror plus
`.../witbd/ch04.htm` on MIA (ch. IV is absent from the local mirror; `research/05`
records the same gap).
V. I. Lenin, *The Collapse of the Second International* ch. VIII (1915) —
`archive/lenin/works/1915/csi/viii.htm`, read in full.
V. I. Lenin, *How the Bourgeoisie Utilises Renegades* (1919), *Collected Works*
vol. 30 p. 30 — `/media/user/data/mim/textonly/classics/lar.txt` ("bribed by
'soft jobs'"), with MIM's own annotation.
J. V. Stalin, *The Class Struggle* (14 Nov 1906), *Works* vol. 1 —
`reference/archive/stalin/works/1906/11/14.htm`, read in full (separate funds,
separate leading bodies, own congresses; and the note that *Akhali Droyeba* was
suppressed by the Governor of Tiflis on 8 January 1907).

**Data, read directly.** `marxist-data-3NF.sqlite` (`/media/user/data/old-hdd/old-hdd/`):
Wayne County (`fips 26163`, `county_id` 1315) — `fact_census_median_income`
$57,223; `fact_census_rent_burden` 247,760 renter households, of which 225,228
computable, **120,041 (53.3%) at ≥30% of income and 66,563 (29.6%) at ≥50%**;
`fact_census_commute` 742,431 workers, 553,436 driving alone, 65,940 carpooling,
17,334 on transit, 78,197 working from home. These are the county's own books and
they are the *Observed* floor under Mechanic 5's cash claim.

**Not read, and named rather than paraphrased.**

- **No primary text for the Tiflis 1907 expropriation was opened in this sweep.**
  The local MIA mirror has no 1905–07 chapter of the *Short Course* (ch. 02–03 are
  absent), and the Tiflis figures circulate in this repository already
  (`political-economy-liquidity.yaml`: "250,000 rubles"). Everything in §3.4(d)
  about Tiflis is flagged **Calibrated historical reference** and should be
  verified against a primary source before it is used as a scenario parameter.
- Stalin, *Foundations of Leninism* ch. VIII ("The Party") is absent from the local
  mirror (`1924/foundations-leninism/` holds ch. 01, 02, 09 only), so nothing above
  is attributed to it. `research/12` records the same gap.
- Mao's *Collected Works* were consulted only as a cross-check on *Be Concerned
  with the Well-Being of the Masses*; no claim above rests on an unquoted page of
  them.
- Olson was not consulted directly. The "consumer" category used throughout is
  Weinstein's, as read in `research/08` §2.1, and the free-rider problem is
  handled structurally (the cliff, the edge clause) rather than with a
  selective-incentive model.

**Guardrail honoured.** No Trotsky. Trotskyism appears nowhere as a source of
mechanics. Theory sources are Mao, Lenin, Stalin, Fortunati as read through
`research/07`, and Weinstein as read through `research/08`. No claim above is
attributed to a file that was not opened.

**One structural note for the porch.** This briefing adds no verb. Every mechanism
above is a *consequence* of what the organization already is — its membership, its
books, its institutions, its payroll, its larder — which is ADR187 OQ-3's ratified
position ("the empty cell is the pedagogy"). If the porch wants a funding button,
that ruling has to be reopened first, and this briefing argues it should not be:
the whole dramatic content of scarcity lives in the fact that there is nothing to
click.
