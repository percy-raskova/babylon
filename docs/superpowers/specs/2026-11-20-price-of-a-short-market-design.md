# The Price of a Short Market

Date: 20 November 2026. Issue: PER-370. Decision record: ADR312.

## 1. What was asked

The Director asked what Capital says happens in a shortage, and then ruled on 20 November 2026:

> i want the full price form where prices rise within the period until what buyers can pay for
> equals is what there is

This design is that rule for the national economy. In a period in which a private seller has less
than its buyers can pay for at the posted price, the price paid rises, in that same period, to the
first level at which what the buyers can pay for equals what there is. Every buyer pays that one
price. The seller keeps the difference.

The warrant is Capital, Volume III, chapter 10. When demand exceeds supply "one buyer outbids
another, within certain limits, and so raises the price of the commodity for all of them above the
market-value". The demand that counts there is need backed by money, set by how income is divided
between the classes. The purse decides, and those with least money go without first.

## 2. A correction

The households design (section 12) and ADR306 (open question 1) say that a short seller serves its
buyers in the order of their identifiers. That is wrong. The code shares a short stock among the
orders in proportion to what each ordered, and only the last indivisible units go in identifier
order (`transition/outbound/orders.rs`, `limit_allocations` at 282 and `Matrix::augment` in
`residual.rs` at 119). It matches the measurement of 20 November: every Wayne group went without
the same share of a need, whatever its cash.

So this rule replaces sharing in proportion. Sharing in proportion is rationing. It stays in the
engine for the cases this design names in section 7, and it is the natural form of a later
political rule, when a state or an organization imposes rationing on a market.

## 3. Today, in the code

Paths are under `rust/crates/babylon-material-circuit/src/`.

| Step of the period | What happens today |
|---|---|
| `recurring/households.rs:76` `admit_household_orders` | Each household order for a good is admitted at the posted price, for `min(requested, cash / price)`, and that money is set aside. Orders are taken by household, then good. |
| `services/admission.rs:175` `admit` | Each service order, of a household or of a business that needs the service as an input, is admitted the same way, all at once, before any service is produced. |
| `production.rs:393` `execute_production` | For the utility stage, then the local service stage: batches are capped by the funded orders, labor and inputs are shared, and `ServiceClose::allocate` shares the output among the orders in proportion. `sell_grants` settles what was performed and refunds the rest. |
| `transition/state.rs:960` `dispatch_and_replenish` | A first pass shares each seller's stock among household orders and older business orders in proportion. Then each business orders its stock at the posted price (`recurring/firms.rs:121` `replenish`), even from a supplier with nothing, and a second pass ships what there is. The rest waits as a held order. |
| `recurring/prices.rs:113`, `services/market.rs:78` | The posted price moves one step for the next period, inside fixed bounds: up when funded demand went unserved or cost exceeds price, down when stock or capacity is spare. |

Three facts decide the design.

1. The engine's contract says that money set aside for an order keeps its price
   (`contracts/material_circuit_v4.yaml`: "admitted escrows retain their own prices"). The design
   keeps that sentence. It finds the price before the money is set aside, never after.
2. The Director's order of paying (ADR306 R9: food, materials, utility, housing, household
   services, public provision) is the order in which the engine comes to know each supply: goods on
   the shelf when households buy, utility at its stage, the local services at theirs.
3. A household has one seller for each good and each service, and a business one provider for each
   service it takes as an input (`HouseholdPurchasePolicy`, `ServiceInputPolicy`). A business may
   restock one product from several suppliers, in the national world a domestic and a foreign one
   (`ReplenishmentPolicy`). In every case a market is one seller and one product, and its buyers
   are known.
4. In a county with no retailer, the national world gives the retail role to the county's largest
   employer, with its existing people and hours
   (`babylon-persistence/src/national_economy/opening/markets.rs:209`). That site's production draws
   on the same stock and the same hours as its shelf. So goods sold and left on the shelf until the
   shipping pass, as today, could be used up in between.

## 4. The rule

**P1. The market.** A market is one seller, one product and one moment of sale in a period. Its
supply is what the seller has on offer to new buyers at that moment (P6). Its buyers are the
accounts whose policy names that seller for that product.

**P2. A bid.** Each buyer brings three figures.

- What it wants: the quantity it asks for today, before any cash limit. For a household that is its
  need for the period and, for a storable good, the refill of its pantry.
- Its purse: the cash it can commit at that moment. For a household that is all its cash. For a
  business it is its cash above its floor, as today.
- For a business, a limit: the highest price it will pay (P5). A household has none.

At a price `p` a buyer can pay for `min(wanted, floor(purse / p))`, and for nothing when `p` is
above its limit.

**P3. The price.** If the buyers can pay, at the posted price, for no more than the supply, the
sale is at the posted price, as today. Otherwise the price is the lowest price above the posted one
at which what the buyers can pay for no longer exceeds the supply. It is found exactly, in
millionths of a dollar, by bisection. There is one price for every buyer of the market.

**P4. Who gets what.** At that price each buyer gets what it can pay for. Where the demand falls
past the supply in a single step (many buyers with one limit, or equal purses), the price is the
last one before the step, and the buyers who fall away at the step share what is left in proportion
to what each loses there; the last indivisible units go in the engine's canonical order, as its
residual rule already says. Everything on offer is sold. Equal purses share in proportion.

**P5. A business outbids only up to its cost price.** This is the "within certain limits" of
chapter 10, and Volume III, chapter 1: the cost price is the lower limit of a capitalist's selling
price. A business that makes a product with the input pays for the input no more than the price at
which a batch would just cover its cost: the batch's receipts at the business's own posted price,
less the batch's wages and its other inputs at their posted prices, divided by the input's quantity
in a batch. The wage is the site's own for the period: the wages it has funded over the hours it
has funded, a working owner's unpaid hours included. Another input counts at the lowest posted
price among the business's own sellers of it. A merchant pays no more than its own posted price for
the good less its handling wage. The limit is never under the posted price: a business that is
below its cost at posted prices still buys at the posted price, as today, and never bids above it.
A buyer with no selling price that covers its cost, such as a public body, therefore pays the
posted price and no more. Without this limit a single business that wants more than the whole
supply would bid against itself until its cash was gone.

**P6. What is on offer.** The seller's stock or output at the moment of sale, less what it already
owes to orders accepted earlier (P8). For a merchant it is also no more than its hands and its
handling room can pass over at that moment, after the hours and the room that its owed orders will
need, with the products taken in the order of paying.

**P7. The order of paying.** A campaign that clears by price names one order of its products. It is
ADR306 R9's order, with the inputs of business after the needs of households: food, materials,
utility, housing, household services, business services, resources. A buyer's purse reaches the
markets in that order, inside the order of the period's own steps (section 5), and each purchase is
paid before the next market is cleared. So a household short of money goes without in the declared
order, and so does every household of the campaign, not only Wayne's.

**P8. An accepted order is a sale.** Money set aside keeps its price and its quantity. A good that
a household buys is handed over when it is bought: it leaves the shelf, the hours that hand it over
are spent, and the money is paid, all at that moment. Nothing the seller does later in the period
can take it back. A business's goods sold and not yet moved are owed: they are taken out of what
the seller offers afterwards. A business no
longer places a held order with a seller that has nothing; it bids again next period. What the
buyers wanted at the posted price and did not get is recorded (P10) and is what the seller plans
its next production from, as the held orders are today.

**P9. The posted price.** It keeps its rule: one step a period, inside its bounds. It is the price
below which the seller does not sell and around which the paid price moves. It steps up after a
period in which buyers were priced out.

**P10. The record.** Each order's receipt carries the price paid, as today. A short market leaves
one new receipt: the seller, the product, the moment of sale, the posted price, the price paid,
what was on offer, what the buyers could pay for at the posted price, what was sold, and how many
buyers bid and were served.

**P11. Money.** Nothing is created or destroyed. The buyers' extra payments are the seller's
receipts, and reach its owners by the rules that exist: operating income, tax, the company's
payout.

**P12. What does not clear by price.** A product left out of the order of paying, which in the
national world is public provision; a seller with a fixed price; a campaign with no order of
paying; a world without money. There the engine shares in proportion, as today.

**P13. On asking.** A campaign gets the rule only by asking for it (section 8). Without the
asking, every byte is the one of before.

## 5. Where it acts in the period

| Moment | Markets | Buyers | Supply known because |
|---|---|---|---|
| H. Households buy goods (before production) | each retailer's food, then materials | households | the shelf, the hours and the room are read at that moment, and the goods are handed over at once |
| S1. The utility stage | each utility's output | households, and businesses that need utility as an input | the stage's batches have been fitted to labor and inputs |
| S2. The local service stage | housing, household services, business services | households, and businesses that need business services | the same, after the utility they bought |
| R. Businesses restock (after production and the first shipping pass) | each supplier's materials, then resources | businesses | production of the period is in stock |

In H and R the price is found where the order is made today. In H the hand-over moves from the
first shipping pass to the purchase itself (P8, and fact 4 of section 3). In S1 and S2 the admission
of service orders moves from the start of the period into its stage, so that the price is found when
the output is known and before the money is set aside. The batches of a stage are still capped by
what buyers could fund at the posted prices.

## 6. Worked examples

Checked with an exact model over 200,000 random markets: everything on offer is sold, no buyer pays
more than its purse or above its limit, no lower price fits the supply, and more supply never
raises the price.

| Case | Posted | On offer | Buyers: wanted, purse | Price paid | Each gets |
|---|---|---|---|---|---|
| Enough for all | $75 | 300 | 100 each; purses $7,500, $11,250, deep | $75.00 | 100, 100, 100 |
| A fifth short | $75 | 240 | the same | $132.35 | 56, 84, 100 |
| Half short | $75 | 150 | the same | $362.90 | 20, 30, 100 |
| Equal purses | $75 | 5 | 4 each; $300 each | $150.00 | 2, 2, 1 |
| Food at Wayne's scale | $280 | 400,000 | 456,528 with 1x the posted cost; 50,726 with 4x; 173,993 with a half; 19,334 with 3x | $461.25 | 277,130; 50,726; 52,810; 19,334 |
| Two businesses and a household | $100 | 120 | 100, limit $106; 100, limit $245; 50, purse $5,000 | $238.10 | 0, 100, 20 |
| Businesses below cost | $100 | 60 | 100 each, limit under $100 | $100.00 | 30, 30 |
| One buyer, deep purse | $280 | 10 | 1,000; $9,000 | $818.18 | 10 |
| Nothing on offer | $75 | 0 | any | no sale | 0 |

## 7. What it does not price

- **A route.** Carrying is not sold in this engine, so a short route has no price to raise. Orders
  that a route cannot move are shared in proportion, as today, and the unmoved part of a business's
  order waits as an accepted order. A short route shows as a short shelf at its far end, and that
  shelf is priced. A merchant's hands are different: they are part of what it has on offer (P6).
- **Equipment bought as investment.** A company's equipment order keeps today's rule: the posted
  price, and a held order when the maker has none. It has its own budget rule and is the next piece
  of price work.
- **Wages.** The Director has ruled that wages stay.
- **Public provision.** Shared in proportion. That is rationing by a public body.
- **A glut.** The price paid never falls under the posted price in a period. Unsold stock waits, and
  the posted price steps down, as today.

## 8. What a campaign must ask for

A campaign asks for the rule with one key of its policy's `[markets]` section,
`paying_order = [...]`. The engine's catalog then carries a market policy, and the campaign compiles
under a new compiler name. A campaign without the key keeps every byte it has today. The shipped
national world asks for it together with the repair of PER-370, as `national-world-v13`. Household
units, when they come, are `national-world-v14`.

## 9. Consequences to watch

1. **A deep shortage empties purses.** The rule is the Director's sentence taken exactly: buyers bid
   what they can pay. If a county's utility delivers a twentieth of what is wanted, its households
   pay all the cash they have for that twentieth, and then go without housing. The health record
   will show the price paid beside the posted one, so this is measured before it is played.
2. **Thin margins lose the bidding.** At today's designed figures, food's cost is $42 against a
   price of $280, and materials' is $119 against $120. When an input is short, the makers of
   materials are priced out long before the makers of food. That is capital moving to where the
   profit is, and the posted price of materials then steps up. It will show in the record.
3. **Abroad.** A foreign seller's buyers are its own region's retailers and United States
   retailers. A United States retailer's limit comes from United States prices, so it outbids the
   region's own buyers. That is the unequal exchange the game's line describes, arising from the
   rule and not written in.
4. **Public bodies lose the bidding** to private buyers for a short input (P5).
5. **A retailer that is also an employer hands goods over first.** Where a county's shelf is kept by
   its largest employer, the hours that hand goods to households are spent before that site's
   production, where today production takes its hours first.
6. **Two figures still read the posted price.** The County Review values a relief unit at the
   opening price of food, and the organizer's preview of a purchase shows the posted price
   (`national_economy/county_review.rs:206`, `organizer_runtime/material_preview.rs:363`). Neither
   refuses anything. Both are shown to the Director with the measured result, to rule on.

## 10. Approaches

1. **Find the price at the sale (chosen).** The price is found when the buyers bid and the supply is
   known, before money is set aside. The contract's sentence about accepted prices stands. It costs
   moving the admission of service orders into their stage, and handing a household's goods over at
   the purchase.
2. **Re-price held money at the hand-over.** Keep today's admissions and raise the price of money
   already set aside when the stock turns out short. It breaks the contract's sentence, needs an
   order to hold two prices at once when part of it is in transit, and spends a household's spare
   cash on utility before food, against the order of paying.
3. **Serve the deepest purse first at the posted price.** The simple form the Director set aside.
   The seller keeps no scarcity profit.
4. **Households buy goods after production, when the shelf is certain.** It needs no early
   hand-over, but a household would then pay for utility and services before food, against the
   order of paying.
5. **Keep the hand-over at the shipping pass and bar production from goods and hours that are
   owed.** It reaches the same result through four separate guards, in production, maintenance and
   installation, and one missed guard brings back refunds at a price that did not clear.

Within the chosen approach, the price stops at the first level at which demand fits supply, not at
the top of the range of prices that would fit. That is the plain reading of "rise until", and it is
the lower price for buyers wherever the two differ.

## 11. What the Director has not been asked

These are calls of this design, each open to correction: the limit of P5 and its form; that a
public body does not outbid; that equipment bought as investment is left for later; that the order
of paying is one order for the whole campaign; that the posted price keeps its rule; that business
inputs come after household needs in the order; that a household's goods are handed over at the
purchase, before the seller's own production.

The design was checked once against the code by a second reader before the build. Its findings are
in this text: the combined retailer of section 3, the several suppliers of one business, the wage of
P5, and the stored records' own checks of a price (plan Task 7).

## 12. Build order

1. The price rule as one pure function, with the worked examples pinned.
2. The catalog's market policy, its bytes, its validation and the contract text.
3. Households' goods.
4. Services in their stages.
5. Businesses' restocking, the limit of P5 and what is owed.
6. The planning signals and the posted price's reason.
7. The new receipt through the tick's register and the stored records.
8. The policy key, `national-world-v13`, the health record with prices, the standing test.
9. The whole gate, the recorded result, the report to the Director.
