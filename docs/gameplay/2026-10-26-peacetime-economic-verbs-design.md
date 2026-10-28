# Babylon Peacetime Economic Verbs — the monthly closing meeting

Dated record, 2026-10-26. Status: APPROVED for design (user, 2026-10-26);
implementation explicitly NOT authorized (the PER-354 workhorse owns the
tree). This document is the authority the peacetime gameplay plan will
argue from. Research briefings and specs it rests on:
`docs/gameplay/2026-10-25-porch-01.md`, `docs/gameplay/2026-10-25-porch-02.md`,
`docs/gameplay/2026-10-26-combat-design.md` (§13 OODA loop),
`docs/gameplay/research/05-lenin-witbd-and-vanguard.md`,
`docs/gameplay/research/07-babylon-books-unequal-exchange-and-reproduction.md`,
`docs/gameplay/research/20-reactionary-subject-fascist-militias-and-life-raft-bifurcation.md`,
`docs/gameplay/research/21-opportunist-zoo-adventurists-patsocs-wreckers-and-streamer-complex.md`,
`docs/gameplay/research/23-revolutionary-metabolism-sinks-scarcity-and-cadre-reproduction.md`,
and `ai/epochs/epoch3/{vanguard-economy,reproductive-labor,political-economy-liquidity,resource-sinks,strategy-layer}.yaml`
(with all flat decay floats and sigmoids superseded as recorded in
`research/23`).

## 1. Intent and the why

In most strategy games, peacetime economy is spreadsheet housekeeping:
passive income bars tick up, buildings emit `+5% loyalty`, and sinks are
`-2%` upkeep sliders. That is boring as a game and bankrupt as Marxism.

In Babylon, **every 28-day period is Rent Due Day.** Before a shot is
ever fired—whether the player is running a Maoist mass-line chapter in
Wayne County, a syndicalist strike wave, a prison-ministry network, or a
DSA electoral campaign—the peacetime **Decide** step of the OODA loop
must be a tense, tactile political drama. The movement does not farm
mana; it competes every month against rent, the second shift, the
union/NGO "soft-job" bribe ladder, and the state's surveillance dragnet
for the same sealed 672-hour household week and the same scarce cash.

The player's peacetime economic game is **The Monthly Closing Meeting**:
four concrete, interlocking verbs where every way of getting hours,
keeping people, hiding from Palantir, or halting production stamps its
class character onto what the organization becomes.

## 2. Goals, non-goals, anti-goals

**Goals.**
- G1. Give the peacetime OODA loop (`Read -> Verify -> Allocate -> Seal -> Reckoning -> Long Tail`)
  four concrete player verbs that are as tense and consequential as
  combat loadouts.
- G2. Put all four claims—household reproduction, the wage/stipend
  ladder, clandestine *faux frais*, and strike/siege larders—onto the
  same sealed 672-hour household week and Four Monetary Books so the
  player's choices decide which claim loses.
- G3. Model clandestine infrastructure as Marx's ***faux frais* of
  revolution** (Mao 1945): an all-or-nothing cash sink that produces
  zero immediate goods or members, whose success looks like *nothing
  happened*, and whose neglect ends in a single-night Palantir /
  Lavender / Gospel decapitation sweep.
- G4. Enforce that every sink is a demographic and political selector
  (Weinstein + Fortunati): how you collect money, who you stipend, and
  whether you socialize the second shift determines who stays in your
  organization.
- G5. Replace every flat decay rate in `ai/epochs/epoch3/resource-sinks.yaml`
  with countable integer cliffs: a person who stops coming on Thursday,
  a lease that cannot be paid, a union payroll that outgrows the party,
  or a larder that runs out of food two periods before the boss's bond
  payment comes due.

**Non-goals.**
- No factory-building or bourgeois tycoon loop. The player is an
  organizer and party builder, not a mayor or a CEO.
- No passive stat buildings (`Clinic: +5% support`). An institution only
  works if its shifts, space, and goods are staffed and cleared this
  period.
- No new engine primitive. All four verbs read and write existing
  machinery (`MaterialCircuitState`, `MonetaryBook`, `HouseholdTimeBook`,
  `OrganizerParticipant`, `PracticeInputAuthorityLedger`, `Dossier` $L_c$,
  and `EdgeMedium`).

**Anti-goals (what makes this a failure even if it works).**
- A1. **Upkeep sliders and percentage decay:** Any mechanic where a
  cadre contributes `2%` less because of "burnout" instead of hitting
  the `protected_unresolved_hours != 0` cliff and vanishing from the
  Thursday roster.
- A2. **Charity as a free win (*The Magical Power of Pancakes*):** Any
  mutual-aid building that automatically generates `Cadre Labor` without
  requiring the player to hand governance and shift-scheduling over to
  the masses eating the meals.
- A3. **Risk-free bookkeeping:** Any dues system that gives the player
  both full financial auditability and immunity from police seizure.
- A4. **A visible "Stealth / Security %" bar:** If a HUD bar tells the
  player "Underground Security: 84%," the psychological trap of the
  clandestine *faux frais* is dead. The player must feel the temptation
  to cut the safe house because *nothing happened last month*.

## 3. Constraints (binding)

- C1. **The 672-hour lexicographic cliff (`HouseholdTimeReceipt::validate`):**
  Every household has $28 \times 24 = 672$ hours per period, partitioned
  into `attended_hours + protected_hours + unpaid_allocated_hours + contribution_available_hours = 672`.
  If a single protected hour goes unresolved (`protected_unresolved_hours != 0`),
  `unpaid_allocated` and `contribution_available` drop to **`0`** for
  that period.
- C2. **The economy determines finance (Mao 1942):** Money is never
  farmed from thin air; it sits on one of Four Books (`Household`,
  `Organization`, `Legal Institution`, `Illegal Economy`), each with its
  own owner, standing obligations, audit visibility, police exposure,
  and spending franchise (`PracticeInputAuthorityLedger`).
- C3. **Concentration cannot self-provision (Mao 1945):** Dispersed
  cadres (`d`) keep their day jobs and self-provision in kind;
  concentrated/underground cadres (`c`) report zero production hours and
  must be funded 100% in cash (`ExclusiveAllOrNone`).
- C4. **Visibility rule (Porch 01):** Never display `E` ratios, poach
  booleans, `survival_interest` floats, or security percentages. Show
  the laid-out 168-hour weekly strip, the two-column cash book, the
  named roster of who couldn't come on Thursday, the store-room sentence
  (*"Eleven periods, if nothing changes and the price holds"*), and the
  three narrator feeds.
- C5. **28 days is the monthly rent and lease clock (`TICK_DURATION_DAYS = 28`):**
  Every turn boundary is simultaneously rent day for striking
  households, lease day for safe houses and union halls, and payroll day
  for stipends.
- C6. **No magic constants or sigmoids:** All wages, care hours, and
  rent burdens are read from the live period-$t$ county snapshot and
  offline empirical tables (ATUS 2022 care hours, QCEW/OEWS pay rungs,
  Census rent-burden distributions) using integer arithmetic.

## 4. The Peacetime OODA Loop: The Monthly Closing Meeting

Peacetime play rides the exact seven-step cybernetic OODA loop defined
in `2026-10-26-combat-design.md` §13, instantiated as the organization's
**Monthly Closing Meeting**:

1. **Read (Observe):** Check the **Ticker** (household weekly schedule
   strips, grocery/rent price movements, two-column cash books, the
   *Unable to Attend* list, and the Promise Register of `review_condition`
   dates coming due) and **Topology** (which nodes are flooding with
   Weinstein *Consumers*, where union payrolls are swelling, where State
   attention threads $\Theta$ are thickening).
2. **Verify (Orient):** Spend scarce `Cadre Labor` on social
   investigation (`INVESTIGATE`) and Standing Asks—checking whether a
   new donor or mutual-aid partner is a CIA/foundation front
   (`CONGRESS_FOR_CULTURAL_FREEDOM`), auditing a treasurer where the
   book allows it, or surveying which workplace bottleneck actually pins
   down the local employer.
3. **Allocate & Configure (Decide — The Four Peacetime Verbs):** Across
   your active counties and chapters, execute the four interlocking
   peacetime verbs:
   - **Verb 1:** Staff and govern **Life Raft** institutions (*Service Mode*
     vs. *Mass-Line Mode*).
   - **Verb 2:** Set **Bookkeeping Stances & Stipends** across the Four
     Books (answering soft-job poach offers and household care gaps).
   - **Verb 3:** Fund **The Clandestine *Faux Frais*** (choosing which
     cadres, safe houses, and analog courier relays stay in the cold).
   - **Verb 4:** Call, feed, or convert **Strikes, Rent Strikes &
     Corridor Pinches** against the 28-day Larder Clock.
4. **Seal:** Gavel the monthly meeting closed. Known cash postings and
   hour commitments lock immediately; unresolvable `ExclusiveAllOrNone`
   shortfalls trigger an immediate split-pane Decision Ceremony before
   the tick advances.
5. **Reckoning (Act):** The engine settles the 28-day period:
   `HouseholdTimeReceipt` cliffs fire, `PricePolicy::Responsive` moves
   market prices against strike larders, poaching rungs claim unshielded
   cadres, `L_NSA` / `L_FBI` / `L_PD` sweep exposed digital/surface
   edges, and legal payrolls expand toward their take.
6. **Long Tail:** A kitchen opened in Mass-Line Mode begins returning
   freed household hours and `signature_class >= 2` cadre twins three
   periods later; a safe house cut to save $1,200 in Period 12 surfaces
   in Period 40 when Palantir links the ex-underground cadre's return to
   surface payroll with an old arrest record.

## 5. Verb 1 — Staffing the Life Raft (*Changkang* vs. *The Magical Power of Pancakes*)

### What the player does
In any county where the organization has presence, the player can open
and provision concrete reproductive and dual-power programs from Mao's
1934 Changkang list and the Goods Clause (`research/20`, `23`):
**Communal Kitchen**, **Childcare Co-op**, **Eviction Defense Brigade**,
**People's Clinic**, and **Peer Jury / Dispute Court**.

An institution is not a one-time purchase. Each period it requires a
space (a leased hall, a union basement, or a defended squat), real bulk
goods from the county market or self-provisioning workshops
(`prepared_food`, `grain`, medical supplies), and a **Governance &
Staffing Stance**:

1. **Service / Charity Mode (*The Magical Power of Pancakes*):**
   - You staff the kitchen or clinic using your own scarce `Cadre Labor`
     or a salaried nonprofit coordinator (`Legal Institution` book).
   - **Immediate payoff:** It works cleanly on Day 1. A kitchen serving
     30 households subtracts `18` cooking hours per household per period
     (`540` total freed hours, four-fifths of a full-time cadre's 672-hour
     month), lowering household exhaustion $E_i$ and keeping those
     families off the `protected_unresolved_hours` cliff.
   - **The trap:** Because leadership makes all the decisions and the
     masses are passive beneficiaries (*"replaced the Guru with a
     Nonprofit Executive Director"*), it converts **`0` beneficiaries
     into `Cadre Labor`**, leaves the node a Borgatti–Everett singleton
     (`|signature_class(v)| == 1`), and collapses the instant the
     coordinator is arrested or poached. Worse, until it survives a
     State or militia attack ($S > 0$), it counts as charity ($S = 0$),
     leaving the George Jackson Life Raft term $\mathrm{LR} = 0$.
2. **Mass-Line Co-Governance Mode (*Changkang Township*):**
   - You require the households eating the meals or using the clinic to
     schedule the shifts, keep the inventory, and chair the committee
     themselves (`Supporter Labor` + `OrganizerPartnerPolicy::Participate`).
   - **Upfront friction:** For the first two periods, `receipted_service_hours`
     lags while committees argue, pots go unwashed, and mistakes happen.
   - **The structural payoff:** Three periods in, the shared practice
     forgings **role-equivalent cadre twins (`|signature_class(v)| >= 2`)**,
     reproducing new `Cadre Labor` directly from the stratum with the
     highest prior exhaustion $E_i$ (parents and working-class women).
     When the Sheriff or a fascist militia raids the hall and the
     co-governed base rebuilds it ($S > 0, S^{\text{fail}} = 0$),
     $\mathrm{LR}$ turns positive and flips the county across the Life
     Raft Bifurcation ($\Lambda > 1$), starving the local militia's
     subscription base.

### Mao's 9:1 Rule vs. Tingchow ("Draining the Pond")
If a chapter demands high dues, bond purchases, and picket turnout from
a county where it allocates fewer than **9 hours of reproductive/productive
mass work for every 1 hour of extraction/collection** (Mao 1943), it
triggers the **Tingchow Collapse**: household `protected_unresolved_hours`
spike, delegates stop attending the council, and the chapter gets *less*
money and *fewer* fighters than if it had asked for nothing.

## 6. Verb 2 — Keeping the Four Books & The Bribe Gradient

### Part A: The Four Books and Lenin's 1902 Bookkeeping Dilemma
Money never sits in a generic top-bar counter. On the **Ticker**, the
player manages four distinct two-column ledgers (`Receipts` on the left,
`Standing Obligations` on the right):

| Book | Owner & Franchise | Standing Obligations | What It Selects For |
|---|---|---|---|
| **1. Household** | The household | Rent, food, utilities, debt (capped by `protected_cash_floor_micros`) | Survival floor; engine refuses dues that breach rent |
| **2. Organization** | The Party Committee | Full-time stipends, safe-house leases, print runs, bail | Committed *Investors* (when poor); police evidence if recorded |
| **3. Legal Institution** | Union Local / Co-op / NGO Board (**its own congress**) | **Salaried Staff Payroll**, hall lease, grant compliance | Careerist bookkeepers (`survival_interest` headcount) |
| **4. Illegal Economy** | Armed / Logistics Cell | Cell shares (`share_to_participants`), bribes, gear | Self-accelerating banditry if `share / take` rises |

On the **Organization Book**, the player sets the **Dues & Accounting
Stance** (Lenin, *WITBD* Ch. IV §C):
- **Named Roll & Monthly Audit:** Every ruble/dollar is accounted for;
  arrears are visible and embezzlement is impossible. **Price:** If a
  subpoena (`Ceremony 2: The Audit`) or police raid hits the office, the
  State seizes a complete list of names, addresses, and employers—instant
  transitive-closure exposure in $L_{\text{PD}}$ and $L_{\text{FBI}}$.
- **Stamped Coupons:** You know total cash collected, not who paid.
  Possession of a coupon is physical evidence if a cadre is searched,
  and small discrepancies go unnoticed.
- **Coded Reports in the Paper (No Coupons):** Zero donor list for the
  gendarmes (`0%` membership-roll exposure on seizure). **Price:** You
  cannot audit your own treasurer from the routine ledger. Skimming is
  never a random dice roll—it is an emergent **symptom of two concrete
  conditions** (Director ruling, 2026-10-26):
  1. **An opportunistic / right-deviationist line:** When political
     education is high and the node's line is rectified (`Investor`
     cadres, no unchallenged rightist/economist deviation), coded books
     run clean with zero theft. When opportunistic *Consumers* or a
     rightist deviation rot the node, skimming begins silently.
  2. **Police-protected theft (`Malinovsky` / COINTELPRO hook):** Local
     PD and FBI handlers actively encourage an informant or compromised
     treasurer to steal from the fund and turn a blind eye to the crime
     in exchange for information (using the theft as both payoff and
     blackmail lever).
  3. **Tells on `INVESTIGATE`:** While the coded book itself prints no
     red ink until a crisis empties the drawer, spending `Cadre Labor`
     to `INVESTIGATE` the node surfaces concrete tells: a treasurer
     living above their stipend rung, a gap between paper circulation
     and cash banked, or a pending police charge against the treasurer
     that was quietly dropped.

On the **Legal Institution Book** (Stalin 1906, Lenin 1915), the union
local, co-op, or legal newspaper is **not your subsidiary**—it has its
own leading body and its own congress. Its standing payroll (`salaried_staff`)
naturally expands to consume its incoming take (`standing_{L,t+1} -> take_{L,t}`).
To spend a union local's treasury on a political strike or cadre school,
you cannot just post a transfer; you must hold the votes in its
congress—and every salaried staffer on that book is a vote for preserving
the legal shell under police law (`survival_interest`). When
`salaried_staff > cadre_count`, the player can see on the two-column
book that the tail is now wagging the dog long before the 260-period SPD
calcification clock runs out.

### Part B: The Stipend & Second Shift (The Soft-Job Bribe Gradient)
In the imperial core, cadres do not defect because a "morale" float
decayed; they are poached because the labor-aristocracy / nonprofit
complex offers **soft jobs** one rung up the same wage ladder (Lenin
1919). Every period, each cadre $i$ is tested against four integer
booleans (`research/23` §3.2):
1. Does a local poaching rung $w^P_{j,k}$ (`k=1` union staffer, `k=2`
   NGO program officer, `k=3` public-sector professional) beat the
   cadre's movement income $m_{i,t}$?
2. Is the cadre's household claim unresolved (`protected_unresolved_hours > 0`
   or an unmet medical/rent burden)?
3. Does the cadre have a graph edge to that union/NGO/agency?
4. Did the Party's stipend row pro-rata short (`stipend_allocated < stipend_requested`)?

When all four hold, the player gets ***Ceremony 1: The Offer*** (*"Maria
told us on Thursday, in the kitchen, with the door shut"*). And
**Fortunati's rule is binding**: a stipend set at a single worker's
forgone wage replaces *one* paycheck, not the household's unpaid care
work.
- If you pay high stipends without building kitchens/childcare (Verb 1),
  you turn the party into an employer whose only surviving full-timers
  are people without dependents (or men whose partners perform an unpaid
  second shift), while credentialed cadres with unresolved family claims
  get vacuumed up by Local 174 and foundation NGOs—leaving you to
  discover in the Wiki that *"the ones who stayed were the ones nobody
  was hiring."*
- If you build the Life Raft (Verb 1) so conjunct (2) is false (`protected_unresolved_hours == 0`),
  a modest stipend holds your best organizers against a `$75,000` NGO
  offer because the movement solved the dialysis sitting and the
  Thursday dinners that the NGO paycheck couldn't buy.

## 7. Verb 3 — Paying the Clandestine *Faux Frais* (Going Into the Cold)

### The Mao 1945 & Marx *Faux Frais* Law
In *Capital* Vol. II, Marx defines the ***faux frais* of production**:
incidental operating costs (insurance, bookkeeping, storage, guards)
that add zero surplus value of their own, yet must be deducted from real
wealth so the circuit isn't destroyed.

Mao's April 27, 1945 directive (*On Production by the Army for Its Own
Support*) states the exact revolutionary equivalent:
- **Dispersed cadres (`d`)** stay in their shops and neighborhoods, keep
  their wage jobs, and self-provision in kind. They cost the Party
  treasury zero cash—but their hours are capped by employer attendance,
  and their daily phones, payroll records, and workplace ties sit on the
  open surface (`EdgeMedium::Digital | FinancialWire`).
- **Concentrated / Clandestine cadres and infrastructure (`c`)**—full-time
  underground organizers, safe houses leased in a third party's name,
  two cars that aren't the same two cars, printing basements, and
  `EdgeMedium::Courier | FaceToFace` dead-drop relays—**cannot engage in
  production to support themselves.** They produce **`0` goods, `0` dues,
  and `0` public members**, and must be paid 100% in hard cash every
  28-day period (`cash_requirement(c) = sum(stipend_i + apparatus_overhead_i)`).

### The Psychological Trap: "The Way You Know It's Working Is Nothing Happens"
This is the signature strategic mind-game of Verb 3:
- **When you pay the *faux frais* every month:** It hurts. It eats cash
  that could have bought printing presses, strike food, or bail. And at
  Period Close, **the visible return on that expenditure is silence.**
  Nothing blows up. Why? Because behind the curtain, the NSA's digital
  panopticon (`L_NSA`, which resolves `95%` of `Digital` edges and
  **`0.0%` of `Courier | FaceToFace` edges**) sees nothing to refer to
  the FBI; Lavender and Gospel's targeting queues cannot lock onto an
  unindexed courier relay; and when City PD raids a surface union hall,
  your off-grid continuity core (`c`) survives untouched to re-stitch
  the youth circles in two periods (Lenin's 1902 respawn law).
- **When you cut the *faux frais* because "things have been quiet for a
  year":** For three, five, or ten periods, you feel like a genius. Your
  cash reserve surges! You fund extra rallies! Meanwhile, every surface
  meeting, Venmo dues transfer, and fiery speech is silently writing
  camera footage and metadata edges into the State cells' private
  dossiers ($L_{\text{NSA}} \to L_{\text{FBI}} \to \text{Lavender/Gospel}$).
  Then, on Period 45, the State crosses its action threshold and
  executes a transitive-closure sweep: your entire committee is
  arrested or liquidated in a single night, your printing press is
  sequestered, and because `c == 0`, there is no one left in the cold
  who knows the cipher to rebuild the network.

### The All-or-Nothing Cliff (`ExclusiveAllOrNone`)
You cannot pay 70% of a safe-house lease or keep 70% of a courier's
cover identity. The clandestine apparatus row is governed by
`PracticeResourceAllocationMode::ExclusiveAllOrNone`.

The exact period `cash_requirement(c) > org_disposable_cash(t)`, the
engine does not tick down a `-5% stealth` bar. It fires ***Ceremony 5:
The Safe-House Lease (Who Comes Out of the Cold?)***, forcing the player
to choose on the spot:
1. **Bring named cadres out of the cold** back into surface wage-work
   (saving the cash immediately, but writing their return onto the open
   graph where both the Soft-Job Poach and the FBI's old file are
   waiting);
2. **Tap a compromised book** (begging the Union Local's executive board
   or a foundation grant for emergency funds, handing leverage to the
   legal shell); or
3. **Requisition from the base** ("draining the pond," forcing local
   households' `protected_unresolved_hours > 0` and triggering a
   Tingchow collapse).

## 8. Verb 4 — Weaponizing Circulation (The Larder vs. The Ledger)

### What the player does
When the player calls a **Shop-Floor Strike**, **Tenant Rent Strike**,
**Boycott**, or **Freight Corridor Pinch (`PracticeId::Blockade`)**,
they are not pressing a `-20% GDP` cooldown button. They are starting a
**two-sided material siege** on the 28-day rent and invoice calendar:

- **Your side (The Siege Larder, `research/23` §3.5):** Every striking
  or blockaded household loses its wage flow while its monthly food and
  rent claims keep ticking every 28 days. The Ticker prints your honest
  integer horizon:
  $$\text{endurance} = \min(\text{goods\_cover}, \text{cash\_cover})$$
  rendered as a plain sentence in the store room: *"The larder holds
  eleven periods, if nothing changes and the price holds."*
- **Their side (The Boss & Pentagon Ledger):** A struck plant, landlord
  REIT, or blocked FAF5 rail/port corridor halts `RoutedFreightLot`
  deliveries and starves downstream constant capital ($K$), municipal
  bond covenants, or Pentagon `HeavyGroundManeuver` fuel/ammo tonnage
  (`research/18`, `31`).

### Two Endogenous Twists (Zero Scripted Timers)
1. **The Market Fights Back (`PricePolicy::Responsive`):** As your
   strike fund buys up local `prepared_food` and `grain` to feed the
   picket line, county inventory drops and `PricePolicy::Responsive`
   automatically steps up the unit price. Your `cash_cover` starts
   falling *faster* than one period per turn (*"In period six, the
   Corporate Feed prints a grocery price adjustment and 'Eleven periods'
   becomes 'Six'"*). The only counter is **the Mao 1945 Conversion Leg**:
   spending capital early to open a communal kitchen, flour mill, or
   food co-op (Verb 1) that permanently lowers per-household cash/goods
   burn before prices spike.
2. **The Concentrated vs. Dispersed Picket Fork:**
   - A **Concentrated Picket / Sit-Down Occupation** halts 100% of enemy
     production and blocks scabs, but the strikers cannot self-provision—every
     household must be fed and rent-covered from the Larder. Every month
     the fund falls short of a household's rent, that household hits the
     `protected_unresolved_hours` cliff, gets evicted, and vanishes from
     the picket line permanently.
   - A **Dispersed Slowdown / Guerrilla Work-to-Rule** lets workers keep
     their roof and self-provision on the guerrilla-zone ration basket,
     costing the treasury almost nothing, but only taxes enemy output
     instead of severing the corridor.
3. **The Economism Trap ("30 for 40" vs. Political Strike):**
   If you win a pure wage strike without attaching a political exposure,
   solidarity demand, or corridor blockade, the victory is real—wages
   rise—and if that raise pushes those workers across $w_i > v_i$, you
   have just graduated your own militant shop floor into the **Labor
   Aristocracy**, who will spend the next ten periods defending their
   pension and voting for the County Sheriff (`strategy-layer.yaml`
   Rightist Trap, now grounded in exact `w_i > v_i` CDF math).

## 9. How the Four Verbs Surface (Zero Spreadsheet Popups)

Following the Porch 01 Visibility Rule and the three-author narrator:

- **On the Ticker:**
  - **The 168-Hour Household Strip:** A visual weekly calendar block
    showing `Wage Work`, `Second Shift (Unpaid Care)`, `Commute`,
    `Sleep`, and the thin dark band of `Movement Hours`. When a
    household hits the cliff, the dark band disappears and a name lands
    on the **Unable to Attend** roll (*"Rosa isn't coming; her mother
    fell"*).
  - **The Four Two-Column Cash Books:** Receipts on the left, standing
    obligations on the right, balance at the bottom—where the player can
    literally watch the Union Local's salaried staff column grow past
    the Party's entire cadre count.
  - **The Store Room:** Physical crates/tonnage of grain, prepared food,
    and cash cover alongside the single sentence: *"Eleven periods, if
    nothing changes and the price holds."*
- **On Topology:**
  - **Life Raft & Twin Badges:** Co-governed nodes show redundant twin
    links (`signature_class >= 2`) and battle-tested scars ($S > 0$),
    while *Magical Power of Pancakes* charity nodes glow as fragile
    singletons.
  - **The Cold Houses:** Safe houses and courier relays appear as quiet,
    unindexed analog nodes with a monthly lease tag due at period close.
- **On the Wiki:**
  - **The Promise Register (`review_condition`):** A living table of
    every written promise made to keep a cadre or coalition partner on
    board (*"I'll keep doing Thursdays as long as we're not just doing
    the paper — Check at Period 24"*), recording whether the party kept
    its word or broke it.

### Canonical Ceremony 5 — *The Safe-House Lease (The Faux Frais Shortfall)*

**Trigger.** Period close. The Organization Book's disposable cash is
`$1,800` short of the `ExclusiveAllOrNone` clandestine apparatus row.
Nothing happened last month. Nothing happened the month before.

**Pane left.**

> **THE COLD ROSTER — three safe houses, two couriers, one press basement**
>
> The landlord on Elm Street does not know who rents the second floor,
> only that the envelope arrives on the first of the month in cash. This
> month the envelope is eighteen hundred dollars light. Nothing has
> happened on Elm Street incomprehension-wise for eleven months. The
> courier who sleeps there has not used a phone since April.
>
> You can pay the envelope in full, or you can give up the key today.

**Options.**

- **Give up the Elm Street key and bring Marcus back to the plant.**
  *Eighteen hundred dollars stays in the strike fund. Marcus goes back
  on the Chrysler afternoon shift on Monday, which means he feeds
  himself and puts his name back on a timecard, a tax roll, and a cell
  tower. If nobody was watching Elm Street, you just saved eighteen
  hundred dollars for nothing.*
- **Take the eighteen hundred from Local 600's education fund.**
  *The envelope arrives on time and Marcus stays off the grid. Next
  month the Local's secretary-treasurer sits on the committee that
  reviews what the education fund bought, and his brother-in-law works
  for the county prosecutor.*
- **Levy the eighteen hundred from the ward committees.**
  *The safe house holds. Six families in the third ward miss their
  utility payment this week and will not be at the Thursday meeting.*

**The seal.**

> *Staked: the Elm Street key, Marcus's timecard, and six utility bills.
> Unknown: whether anyone was watching Elm Street, and whether the
> prosecutor's office reads the Local's vouchers. If you were right to
> cut it, nothing will happen next month either.*

## 10. What is left to the builder

- Exact Bevy widget layout for the **Monthly Closing Meeting** tray and
  the four two-column ledger cards on the Ticker screen (within the
  8-color palette parity guard).
- Exact integer unit weights in `content/scenarios/michigan/defines.toml`
  for the Mao 1945 guerrilla-zone self-provisioning ration basket
  (`cooking_oil_salt`, `vegetables`, `meat`).
- Mapping these four peacetime verbs directly into the existing Wave 4
  (`Task 7` & `Task 8`) and Wave 5 (`Task 9`) packets of
  `docs/superpowers/plans/2026-10-25-babylon-gameplay-and-late-empire-plan.md`
  once `PER-354` merges.

## 11. Builder-check rulings (author calls, 2026-10-26)

A builder-check review returned ten architectural questions; eight are
settled here from existing rulings or as author calls, and two go to the
Director (connecting directly into Open Gameplay Questions #2 and #3):

- **R1. Why Charity Mode (*Magical Power of Pancakes*) never hands the
  player free `Cadre Labor`:** In `babylon-material-circuit`, service
  receipts (`HouseholdServiceReceipt`) satisfy household provisioning and
  care burdens so `protected_unresolved_hours == 0` and
  `contribution_available_hours` rises. However, raw
  `contribution_available_hours` from unorganized beneficiary households
  is **`Supporter Labor` (SL)**, never `Cadre Labor` (CL). Only
  **Mass-Line Co-Governance Mode** (`OrganizerPartnerPolicy::Participate`,
  forging `signature_class_size >= 2` twins over 3 periods) converts
  participating households into `Cadre Labor`.
- **R2. `Seal` is final; ceremonies never suspend mid-tick:** Per
  `2026-10-26-combat-design.md` §13, the tick is a pure deterministic
  function and never pauses mid-execution for player input. If a planned
  allocation violates an `ExclusiveAllOrNone` row against known cash on
  hand, the **Monthly Closing Meeting** requires the player to resolve
  ***Ceremony 5: The Safe-House Lease*** *before* `Seal` can be pressed.
  If an unexpected mid-period shock leaves an apparatus row
  `ContestedUnallocated` during Reckoning, the ceremony opens as the
  mandatory first item of the *next* period's Decide step.
- **R3. Personified slots over counted cohorts (no individual simulation
  agents):** Per the Director ruling in `2026-10-26-combat-design.md` §4
  & §7, households and workers are counted county cohorts
  (`national_household_refinement`, `StrikeWorkerCohort`), never
  individual simulation agents. When 2,240 rent notices come due,
  eviction is a cohort-count and edge-weight decrement on the collective
  node, while ceremonies and the *Unable to Attend* roll ("Rosa",
  "Maria", "Marcus") render personified slots from the chapter's
  `OrganizerParticipant` roster or mint names at the loss/defection
  receipt.
- **R4. Mao's 9:1 rule is an emergent regularity, never a hardcoded
  threshold penalty:** Per the Constitutional compact (no second fixed
  response curve), the engine never writes `if ratio < 9 { penalty }`.
  Because dues collection (`collection_hours`) consumes `Cadre Labor` and
  is capped by `protected_cash_floor_micros` (`ProtectedConsumptionUnmet`),
  a chapter that spends its hours on collection without using Verb 1 to
  lower household burdens automatically hits the `ProtectedConsumptionUnmet`
  and `unpaid_unresolved_hours` cliffs—getting less cash and fewer hours
  by pure conservation arithmetic.
- **R5. Monthly rent is a recurring household burden in the extracted
  county snapshot:** County rent burdens (`fact_census_rent_burden`) are
  extracted offline in Wave 1 (`Task 1`) into integer campaign tables. An
  uncovered rent claim on a striking or squeezed household leaves its
  monthly shelter burden unresolved (`protected_unresolved_hours > 0`),
  triggering the `HouseholdTimeReceipt::validate` cliff through existing
  machinery.
- **R6. Wave sequencing for Verb 3 (`EdgeMedium` and `L_NSA` / `L_FBI` /
  Lavender):** Both the cost side and the surveillance/sweep payoff side
  of Verb 3 are in scope; per `2026-10-25-babylon-gameplay-and-late-empire-plan.md`,
  Wave 3 (`Tasks 4–5`) lands `EdgeMedium`, `NsaSignals`, `FbiFieldOffice`,
  and `AirGospelCommand` immediately before Wave 4 (`Task 7`) wires
  `revolutionary_metabolism.rs`. The six falsifiers in `research/23` §7
  serve as deterministic unit-test assertions on `revolutionary_metabolism.rs`,
  not separate runtime game modes.

### Director Rulings (`D1`–`D2`, 2026-10-26)

- **D1. Coded bookkeeping & skimming (Decided):** Skimming under *Coded
  Reports in the Paper* is never a random roll. It occurs if and only if
  (a) the node suffers from an unrectified opportunistic /
  right-deviationist line (low political education / high Weinstein
  *Consumer* share), or (b) the treasurer is a police/FBI informant
  whose handlers encourage the theft and drop charges in exchange for
  intelligence. A well-educated, ideologically loyal cadre apparatus
  runs coded books with zero skimming. Spending `Cadre Labor` on
  `INVESTIGATE` reveals concrete tells (lifestyle above stipend rung,
  print-vs-deposit mismatch, mysteriously dropped police charges) before
  the drawer comes up empty in a crisis.
- **D2. Spending a Legal Institution's treasury:** Resolved via the
  **Negotiation / United-Front (#2)** and **Internal Party Life /
  Congress (#3)** mechanics design.
